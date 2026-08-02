"""
Streamlit UI for total-auto's engineering calculation tools.

Navigation: a sidebar discipline selector (Ground model interpreter,
Geotechnical, Structural, Civils, Electrical (LV), Electrical (HV),
Mechanical Piping) scopes the main area to that discipline's modules only,
shown as `st.tabs()`. With 26 registered calc modules across six
disciplines, one flat row of tabs (the original design) had become the
single biggest usability problem in the app -- this groups by
`CalcModule.discipline` (already a required field, no new metadata needed)
so each tab row stays short (max ~7) regardless of how many more modules
get added.

Cross-module handoffs: several calc modules are explicitly designed to
consume another module's output (e.g. `load_schedule_diversity.py`'s
maximum demand current feeding `cable_sizing_voltage_drop.py`'s design
current -- see those modules' docstrings for the full list). Previously
only the ground-model-interpreter -> bearing-resistance handoff actually
worked in the UI; `CALC_HANDOFFS` below declares the rest and a generic
mechanism (`_apply_handoffs`) pushes values into a per-target-module
prefill store after any source module's result is computed, keyed off the
same "Set <field>?"-aware form-prefill support `_field_widget` already had
for the ground-model case (now generalised rather than special-cased).

External data import: `render_import_sidebar()` accepts a JSON file (sidebar
expander, "Import extracted data") keyed by module key -> {field: value},
matching `calcs.schema_export`'s output shape, and feeds it into the same
generic prefill store `_apply_handoffs` writes to -- one mechanism serving
both calc-to-calc handoffs and externally-supplied data. This is the
counterpart to the `.claude/skills/fill-calc-inputs-from-drawings/` skill,
which reads a source document (a GA, an SLD, a schedule) and produces a
JSON file in this exact shape for a competent person to review and import
here -- see that skill's SKILL.md for the full "flag, don't guess" contract
it follows (never invents a value; a field it isn't confident about is
simply absent from the JSON, left for direct manual entry, same discipline
every calc module in this repo already applies to its own uncertain
inputs).

One tab per module in calcs.registry.CALC_REGISTRY, form auto-built from
the module's pydantic input model (see _field_widget) — per the design
principle in docs/ARCHITECTURE.md: "app.py just discovers registered calc
modules and renders a form + result for whichever one is selected...
adding a new discipline means adding a new module + registering it — the
app and report generator don't change."

The generic form (_field_widget) introspects each pydantic v2 field's
annotation, default, and constraint metadata (Ge/Gt/Le/Lt) to pick a
Streamlit widget: selectbox for Literal, checkbox for bool, number_input for
int/float (with min/max from gt/ge/lt/le where present), text_area
otherwise (handles both single-line and pasted multi-line content).
Optional[...] fields get a "Set <field>?" checkbox so the user can
explicitly omit them (submitting None) rather than being forced to enter a
sentinel value that might itself fail validation (e.g. a gt=0 field can't
default to 0 to mean "omit"). This trades the hand-laid-out columns/expanders
the original bearing-resistance-specific tab had for genericity across every
registered module — deliberate, since hand-laying-out a form per module
doesn't scale to twenty-six (and growing) calc modules.

Run with: streamlit run app.py
"""

from __future__ import annotations

import json
import typing
from datetime import datetime, timezone
from typing import Literal, Optional

import streamlit as st
from pydantic import ValidationError
from pydantic_core import PydanticUndefined

from calcs.geotechnical.bearing_capacity import MODULE as BEARING_MODULE
from calcs.geotechnical.interpretation.ground_model import interpret_stratum, to_bearing_resistance_kwargs
from calcs.geotechnical.interpretation.models import SiteInvestigation, Stratum
from calcs.geotechnical.interpretation.text_input import (
    parse_cpt_lines,
    parse_lab_lines,
    parse_spt_lines,
)
from calcs.registry import CALC_REGISTRY, get_module
from core.calc_base import CalcModule
from core.report import render_report

DISCIPLINE_ORDER = ["Geotechnical", "Structural", "Civils", "Electrical (LV)", "Electrical (HV)", "Mechanical Piping"]

# Declarative calc-to-calc handoffs: (source_module_key, source_selector, target_module_key, target_field_name).
# source_selector is the literal string "headline", or a Term.label to match exactly
# among the source module's result.terms. Add an entry here whenever a module's
# docstring says "feed this into <other module>'s <field>" -- see e.g.
# calcs/electrical_lv/load_schedule_diversity.py, calcs/structural/column_capacity.py.
CALC_HANDOFFS: list[tuple[str, str, str, str]] = [
    ("electrical_lv_load_schedule_diversity", "headline", "electrical_lv_cable_sizing_voltage_drop", "design_current_a"),
    ("electrical_lv_load_schedule_diversity", "S total (diversified demand, apparent power)", "electrical_hv_transformer_sizing", "lv_demand_kva"),
    ("structural_beam_capacity_ec3", "Mc,Rd (bending resistance)", "structural_beam_column_interaction_ec3", "moment_resistance_y_my_rd_knm"),
    ("structural_column_capacity_ec3", "[y-y] Nb,Rd", "structural_beam_column_interaction_ec3", "axial_buckling_resistance_y_nb_y_rd_kn"),
    ("structural_column_capacity_ec3", "[z-z] Nb,Rd", "structural_beam_column_interaction_ec3", "axial_buckling_resistance_z_nb_z_rd_kn"),
]


def _extract_numeric_bounds(field_info) -> dict:
    bounds: dict = {}
    for constraint in getattr(field_info, "metadata", None) or []:
        name = type(constraint).__name__
        if name == "Gt":
            bounds["min_value"] = constraint.gt
        elif name == "Ge":
            bounds["min_value"] = constraint.ge
        elif name == "Lt":
            bounds["max_value"] = constraint.lt
        elif name == "Le":
            bounds["max_value"] = constraint.le
    return bounds


def _field_widget(field_name: str, field_info, prefill: dict, key_prefix: str):
    """
    Render one Streamlit widget for a pydantic v2 field, chosen from its
    annotation/default/constraint metadata -- see module docstring for the
    widget-selection rules and the Optional[...] "Set <field>?" pattern.
    """
    annotation = field_info.annotation
    origin = typing.get_origin(annotation)
    inner = annotation
    is_optional = False
    if origin is typing.Union:
        non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            is_optional = True
            inner = non_none[0]
            origin = typing.get_origin(inner)

    label = field_name.replace("_", " ")
    help_text = field_info.description
    default = None if field_info.default is PydanticUndefined else field_info.default
    prefill_value = prefill.get(field_name)
    key = f"{key_prefix}__{field_name}"

    if is_optional:
        provide = st.checkbox(f"Set {label}?", value=prefill_value is not None, key=f"{key}__toggle")
        if not provide:
            return None

    if origin is Literal:
        options = list(typing.get_args(inner))
        value_for_index = prefill_value if prefill_value in options else default
        index = options.index(value_for_index) if value_for_index in options else 0
        return st.selectbox(label, options, index=index, help=help_text, key=key)

    if inner is bool:
        value = prefill_value if prefill_value is not None else bool(default) if default is not None else False
        return st.checkbox(label, value=bool(value), help=help_text, key=key)

    if inner in (int, float):
        bounds = _extract_numeric_bounds(field_info)
        raw_value = prefill_value if prefill_value is not None else (default if default is not None else 0)
        cast = int if inner is int else float
        widget_kwargs = {k: cast(v) for k, v in bounds.items()}
        if inner is int:
            widget_kwargs["step"] = 1
        return st.number_input(label, value=cast(raw_value), help=help_text, key=key, **widget_kwargs)

    # text_area rather than text_input: no registered module has used a plain str
    # field before cut_fill_balance.py's multi-line pasted grid data, and a text_area
    # degrades gracefully for single-line content too -- no reason to special-case.
    value = prefill_value if prefill_value is not None else (default or "")
    return st.text_area(label, value=str(value), help=help_text, key=key)


def _prefill_store() -> dict[str, dict]:
    return st.session_state.setdefault("calc_prefill", {})


def _prefill_versions() -> dict[str, int]:
    return st.session_state.setdefault("calc_prefill_version", {})


def _set_prefill(target_key: str, field_name: str, value) -> None:
    """
    Write one field's value into target_key's prefill store and bump its version
    (see _field_widget's key-versioning comment for why the version bump matters).
    Shared by _apply_handoffs (calc-to-calc) and render_import_sidebar (externally
    supplied JSON) -- both are "push a value into some target module's form"
    operations, just with a different source.
    """
    _prefill_store().setdefault(target_key, {})[field_name] = value
    versions = _prefill_versions()
    versions[target_key] = versions.get(target_key, 0) + 1


def _apply_handoffs(source_key: str, result) -> list[CalcModule]:
    """
    After a module's result is computed, push any CALC_HANDOFFS values declared
    from this module into the target module(s)' prefill store, keyed per field so
    a target fed by multiple source modules (e.g. beam_column_interaction_ec3,
    fed by both beam_capacity_ec3 and column_capacity_ec3) accumulates rather than
    overwrites. Returns the target CalcModules that received a value, for a
    user-facing notice.
    """
    targets: list[CalcModule] = []
    for src_key, selector, target_key, target_field in CALC_HANDOFFS:
        if src_key != source_key:
            continue
        if selector == "headline":
            value = result.headline.value
        else:
            term = next((t for t in result.terms if t.label == selector), None)
            if term is None:
                continue
            value = term.value
        _set_prefill(target_key, target_field, value)
        targets.append(get_module(target_key))
    return targets


def render_import_sidebar() -> None:
    """
    Sidebar "Import extracted data (JSON)" expander -- accepts a JSON file keyed
    by module key -> {field: value}, matching calcs.schema_export's shape (the
    fill-calc-inputs-from-drawings skill's expected output format), and feeds it
    into the same prefill store _apply_handoffs uses. See module docstring.

    Runs before the discipline tabs render each script execution (declared first
    in main()), so a same-run, same-discipline import applies immediately without
    needing st.rerun() -- but st.rerun() is still used after a successful import
    (mirroring the fix in render_calc_module_tab) since ordering assumptions like
    that are exactly the kind of thing that quietly breaks on a future refactor;
    the summary/warnings are persisted to session_state first so they still
    render after the forced rerun discards this execution's own output.
    """
    with st.sidebar.expander("Import extracted data (JSON)"):
        st.caption(
            "Upload a JSON file produced by the 'fill-calc-inputs-from-drawings' skill "
            "(or matching its schema by hand) to prefill one or more modules' forms. "
            "See .claude/skills/fill-calc-inputs-from-drawings/SKILL.md."
        )
        uploaded = st.file_uploader("Import file", type=["json"], key="import_uploader", label_visibility="collapsed")
        if uploaded is not None and st.button("Import", key="import_button"):
            try:
                payload = json.loads(uploaded.getvalue().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                payload = None
                st.session_state["_import_summary"] = (0, [], [f"Could not parse the uploaded file as JSON: {exc}"])

            if payload is not None and not isinstance(payload, dict):
                st.session_state["_import_summary"] = (0, [], ["Expected a top-level JSON object keyed by module key."])
            elif payload is not None:
                imported_fields = 0
                touched_modules: list[str] = []
                problems: list[str] = []
                for module_key, fields in payload.items():
                    try:
                        module = get_module(module_key)
                    except KeyError:
                        problems.append(f"Unknown module key '{module_key}' -- skipped.")
                        continue
                    if not isinstance(fields, dict):
                        problems.append(f"'{module_key}': expected an object of field values, got {type(fields).__name__} -- skipped.")
                        continue
                    valid_fields = module.input_model.model_fields
                    any_field_for_module = False
                    for field_name, value in fields.items():
                        if field_name not in valid_fields:
                            problems.append(f"'{module_key}.{field_name}': not a recognised field -- skipped.")
                            continue
                        _set_prefill(module_key, field_name, value)
                        imported_fields += 1
                        any_field_for_module = True
                    if any_field_for_module:
                        touched_modules.append(module.name)
                st.session_state["_import_summary"] = (imported_fields, touched_modules, problems)
            if st.session_state.get("_import_summary", (0,))[0]:
                st.rerun()

        summary = st.session_state.get("_import_summary")
        if summary:
            imported_fields, touched_modules, problems = summary
            if imported_fields:
                st.success(f"Imported {imported_fields} field(s) across {len(touched_modules)} module(s): {', '.join(touched_modules)}.")
            for p in problems:
                st.warning(p)


def render_calc_module_tab(module: CalcModule) -> None:
    st.subheader(module.name)
    st.caption(module.description)

    prefill = _prefill_store().get(module.key, {})
    # Widget `value=` only takes effect the first time a given key renders -- on later
    # reruns the widget keeps whatever the user last set, ignoring `value=` even if
    # `prefill` has since changed. Folding the prefill version into the key forces a
    # fresh widget (and therefore a fresh `value=`) each time a new prefill arrives.
    prefill_version = _prefill_versions().get(module.key, 0) if prefill else 0
    key_prefix = f"{module.key}__{prefill_version}"

    with st.form(f"calc_form__{module.key}__{prefill_version}"):
        values: dict = {}
        for field_name, field_info in module.input_model.model_fields.items():
            values[field_name] = _field_widget(field_name, field_info, prefill, key_prefix=key_prefix)
        submitted = st.form_submit_button(f"Run: {module.name}")

    result_key = f"last_result__{module.key}"

    if submitted:
        try:
            inputs = module.input_model(**values)
        except ValidationError as exc:
            st.error("Input validation failed:")
            for err in exc.errors():
                st.error(f"- {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")
            st.session_state.pop(result_key, None)
            return

        result = module.calculate(inputs)
        handed_off_to = _apply_handoffs(module.key, result)
        # Stash rather than render inline: a handoff needs an immediate st.rerun()
        # below so any OTHER tab's widgets pick up the freshly-updated prefill store
        # before THEIR value= is applied this run (module iteration order within a
        # discipline, or which discipline is even selected, isn't guaranteed to put
        # the source ahead of every target the way the ground-model prefill always
        # was). st.rerun() discards the one-shot `submitted` flag, so the result has
        # to survive in session_state to still render after the restart.
        st.session_state[result_key] = (inputs, result, handed_off_to)
        if handed_off_to:
            st.rerun()

    stored = st.session_state.get(result_key)
    if stored:
        inputs, result, handed_off_to = stored
        _render_result(module, inputs, result)
        if handed_off_to:
            names = ", ".join(m.name for m in handed_off_to)
            st.info(f"Value(s) handed off — prefilled into: {names}. Switch to that tab to use them.")


def _render_result(module, inputs, result) -> None:
    st.subheader("Result")
    st.metric(result.headline.label, f"{result.headline.value:.4g} {result.headline.unit}")
    if result.headline.note:
        st.caption(result.headline.note)

    for w in result.warnings:
        st.warning(w)

    if result.risk_flags:
        with st.expander(f"Risk flags ({len(result.risk_flags)})", expanded=True):
            for flag in result.risk_flags:
                st.error(f"**[{flag.severity.upper()}] [{flag.category}]** {flag.description}")

    with st.expander("Full working"):
        for term in result.terms:
            st.text(term.formatted())

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report_md = render_report(module, inputs, result, generated_at=generated_at)
    with st.expander("Review-ready report (markdown)"):
        st.code(report_md, language="markdown")
    st.download_button("Download report (.md)", data=report_md, file_name=f"{module.key}_report.md", mime="text/markdown", key=f"download__{module.key}")


def render_ground_model_tab() -> None:
    st.subheader("Ground model interpreter")
    st.caption(
        "Paste site investigation data for one stratum (soil layer) below, one reading per line. "
        "This is a lenient line parser, not free-form report reading — unparsed lines are shown "
        "back to you rather than silently dropped. For a real narrative report excerpt, it's "
        "usually more reliable to have it read directly and translated into this format."
    )

    colA, colB, colC = st.columns(3)
    with colA:
        behavior = st.selectbox("Soil behaviour", ["granular", "cohesive"])
    with colB:
        top_depth_m = st.number_input("Stratum top depth (m)", value=0.0, min_value=0.0)
    with colC:
        base_depth_m = st.number_input("Stratum base depth (m)", value=5.0, min_value=0.01)

    assumed_unit_weight = st.number_input(
        "Assumed/typical bulk unit weight for this stratum (kN/m^3) — used for overburden "
        "stress calcs; overridden by lab bulk density data if provided below",
        value=18.0, min_value=1.0,
    )
    water_table_depth_m_raw = st.number_input("Water table depth (m bgl, 0 = at surface, leave large if none)", value=100.0, min_value=0.0)
    water_table_depth_m = None if water_table_depth_m_raw >= 90 else water_table_depth_m_raw

    st.markdown("**SPT readings** — one per line: `depth, N` or `depth, N, energy_ratio_pct`")
    spt_text = st.text_area("SPT data", placeholder="1.0, 8\n2.0, 14\n3.0, 22, 45", height=100)

    st.markdown("**CPT readings** — one per line: `depth, qc_MPa` or `depth, qc_MPa, fs_kPa`")
    cpt_text = st.text_area("CPT data", placeholder="1.0, 3.2\n2.0, 5.6", height=100)

    st.markdown(
        "**Lab test results** — one per line: `depth, test_type, key=value, key=value...`\n"
        "test_type: triaxial_cu / triaxial_uu / direct_shear / unconfined_compression / bulk_density\n"
        "keys: phi=, c=, cu=, unit_weight="
    )
    lab_text = st.text_area("Lab data", placeholder="2.5, triaxial_cu, phi=28, c=2\n3.0, bulk_density, unit_weight=19.2", height=100)

    if st.button("Interpret this stratum"):
        spt_readings, spt_unparsed = parse_spt_lines(spt_text)
        cpt_readings, cpt_unparsed = parse_cpt_lines(cpt_text)
        lab_tests, lab_unparsed = parse_lab_lines(lab_text)

        for u in spt_unparsed:
            st.warning(f"Could not parse SPT line: '{u}'")
        for u in cpt_unparsed:
            st.warning(f"Could not parse CPT line: '{u}'")
        for u in lab_unparsed:
            st.warning(f"Could not parse lab test line: '{u}'")

        try:
            stratum = Stratum(
                name="stratum_1",
                top_depth_m=top_depth_m,
                base_depth_m=base_depth_m,
                behavior=behavior,
                assumed_unit_weight_kn_m3=assumed_unit_weight,
                spt_readings=spt_readings,
                cpt_readings=cpt_readings,
                lab_tests=lab_tests,
            )
            site = SiteInvestigation(water_table_depth_m=water_table_depth_m, strata=[stratum])
        except ValidationError as exc:
            st.error("Could not build the ground model:")
            for err in exc.errors():
                st.error(f"- {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")
            return

        design_params, notes = interpret_stratum(site, stratum)

        st.subheader("Derived characteristic parameters")
        if design_params.phi_deg is not None:
            st.metric("Characteristic phi' (deg)", f"{design_params.phi_deg:.1f}")
        if design_params.cu_kpa is not None:
            st.metric("Characteristic cu (kPa)", f"{design_params.cu_kpa:.1f}")
        st.metric("Characteristic unit weight (kN/m^3)", f"{design_params.unit_weight_kn_m3:.1f}")

        with st.expander("Derivation notes"):
            for n in notes:
                st.text(n)
        for w in design_params.warnings:
            st.warning(w)

        # Ground-model interpretation re-derives the full set of bearing-resistance
        # prefill fields atomically each time, so replace rather than merge (unlike
        # _apply_handoffs' per-field accumulation for other targets).
        _prefill_store()[BEARING_MODULE.key] = to_bearing_resistance_kwargs(design_params)
        _prefill_versions()[BEARING_MODULE.key] = _prefill_versions().get(BEARING_MODULE.key, 0) + 1
        st.success(f"Derived parameters saved — switch to the '{BEARING_MODULE.name}' tab (under Geotechnical); they'll be pre-filled.")


def _modules_by_discipline() -> dict[str, list[CalcModule]]:
    grouped: dict[str, list[CalcModule]] = {}
    for module in CALC_REGISTRY:
        grouped.setdefault(module.discipline, []).append(module)
    return grouped


def main() -> None:
    st.set_page_config(page_title="total-auto", layout="wide")
    st.title("total-auto — engineering calculation tools")
    st.caption(
        "Ground model interpretation feeds the geotechnical bearing calc; every other module is "
        "discovered from calcs.registry.CALC_REGISTRY and grouped by discipline in the sidebar. "
        "See docs/ROADMAP.md for what's planned beyond this."
    )

    # Runs before the discipline radio/tabs below so a same-run import (see its
    # own docstring) writes to the prefill store before any tab's widgets read it.
    render_import_sidebar()

    grouped = _modules_by_discipline()
    discipline_options = [d for d in DISCIPLINE_ORDER if grouped.get(d)]
    sidebar_labels = ["Ground model interpreter"] + [f"{d} ({len(grouped[d])})" for d in discipline_options]
    selected = st.sidebar.radio("Discipline", sidebar_labels)

    if selected == "Ground model interpreter":
        render_ground_model_tab()
        return

    discipline = discipline_options[sidebar_labels.index(selected) - 1]
    modules = grouped[discipline]
    tabs = st.tabs([module.name for module in modules])
    for tab, module in zip(tabs, modules):
        with tab:
            render_calc_module_tab(module)


if __name__ == "__main__":
    main()
