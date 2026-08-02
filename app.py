"""
Streamlit UI for total-auto's engineering calculation tools.

Navigation: a searchable catalog. `app.py` used to group modules into a
sidebar discipline selector + `st.tabs()` per discipline, but that stopped
scaling once the catalog grew past ~25 modules spread thin across just six
disciplines -- finding a specific calc meant knowing which discipline
bucket it lived in first. This replaces that with one flat, searchable list
(`render_catalog`): every registered module (plus the ground model
interpreter, which isn't a `calcs.registry` module) shown as a card with its
name/discipline/description, filterable by a text search (matches name,
discipline, or description) and/or a discipline dropdown. Opening a card
(`render_module_detail`) shows that one calc's form full-width, with a
"Back to catalog" control -- `st.session_state["selected_key"]` is the only
piece of navigation state, replacing the old radio-plus-tabs pair.

Cross-module handoffs: several calc modules are explicitly designed to
consume another module's output (e.g. `load_schedule_diversity.py`'s
maximum demand current feeding `cable_sizing_voltage_drop.py`'s design
current -- see those modules' docstrings for the full list). `CALC_HANDOFFS`
below declares them and a generic mechanism (`_apply_handoffs`) pushes
values into a per-target-module prefill store after any source module's
result is computed, keyed off the same "Set <field>?"-aware form-prefill
support `_field_widget` already had for the ground-model case (generalised
rather than special-cased). With the tab layout gone, a handoff's target
module isn't visibly "one click away" the way an adjacent tab was -- so the
post-run notice now includes an "Open <target> ->" button that jumps
straight into the target module's detail view (via `selected_key`) instead
of just naming it and leaving the user to find it in the catalog by hand.

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

One detail view per module in calcs.registry.CALC_REGISTRY, form
auto-built from the module's pydantic input model (see _field_widget) —
per the design principle in docs/ARCHITECTURE.md: "app.py just discovers
registered calc modules and renders a form + result for whichever one is
selected... adding a new discipline means adding a new module + registering
it — the app and report generator don't change." That principle is exactly
why the catalog rewrite below didn't need to touch `_field_widget`,
`render_calc_module_tab`, `_apply_handoffs`, or `render_import_sidebar` at
all -- `CalcModule.discipline` was already the only piece of "where does
this belong" metadata anything needed, whether that metadata drove a tab
row (before) or a filter dropdown (now).

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
doesn't scale to twenty-seven (and growing) calc modules.

Run with: streamlit run app.py
"""

from __future__ import annotations

import json
import typing
from dataclasses import dataclass
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

GROUND_MODEL_KEY = "_ground_model_interpreter"


@dataclass(frozen=True)
class CatalogEntry:
    """One row in the searchable catalog -- either a registered CalcModule, or the
    ground model interpreter (a bespoke tab, not a calcs.registry module, so it
    doesn't have a CalcModule to draw this from)."""

    key: str
    name: str
    discipline: str
    description: str


GROUND_MODEL_ENTRY = CatalogEntry(
    key=GROUND_MODEL_KEY,
    name="Ground model interpreter",
    discipline="Geotechnical",
    description=(
        "Build a full layered soil profile from pasted SPT/CPT/lab site investigation data (or import one "
        "from a GI report), interpret it as one profile so overburden stress is correct across every layer, "
        "and derive characteristic design parameters (phi', cu, unit weight) per stratum, then hand any one "
        "off to the bearing resistance calc."
    ),
)

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


def _gi_strata() -> list[dict]:
    """The ground model tab's in-progress site profile: a list of raw stratum dicts
    (name/behavior/depths/unit weight/paste-text), built up by 'Add stratum to
    profile' and/or the GI import expander, parsed into real Stratum objects only
    at 'Interpret full profile' time -- see render_ground_model_tab."""
    return st.session_state.setdefault("gi_strata", [])


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
        # below because the catalog only ever renders ONE module's detail view per
        # script execution -- a target module's widgets simply aren't built this
        # run to pick up the freshly-updated prefill store, unlike the old sibling-
        # tabs layout where same-discipline targets at least shared a run.
        # st.rerun() discards the one-shot `submitted` flag, so the result has to
        # survive in session_state to still render after the restart.
        st.session_state[result_key] = (inputs, result, handed_off_to)
        if handed_off_to:
            st.rerun()

    stored = st.session_state.get(result_key)
    if stored:
        inputs, result, handed_off_to = stored
        _render_result(module, inputs, result)
        if handed_off_to:
            names = ", ".join(m.name for m in handed_off_to)
            st.info(f"Value(s) handed off — prefilled into: {names}.")
            for target in handed_off_to:
                if st.button(f"Open {target.name} →", key=f"jump__{module.key}__{target.key}"):
                    st.session_state["selected_key"] = target.key
                    st.rerun()


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


_GI_STRATUM_REQUIRED_FIELDS = ("name", "behavior", "top_depth_m", "base_depth_m", "assumed_unit_weight_kn_m3")
_GI_STRATUM_TEXT_FIELDS = ("spt_text", "cpt_text", "lab_text")


def _import_gi_profile(payload: dict) -> tuple[int, list[str]]:
    """
    Populates _gi_strata() from an uploaded GI-derived JSON payload (see
    render_gi_import_expander). A stratum is only importable when all of
    Stratum's own required scalar fields (name/behavior/top_depth_m/
    base_depth_m/assumed_unit_weight_kn_m3) are present -- there's no live
    per-field form to partially prefill the way CalcModule imports have, so
    "skip this stratum, report why, add it by hand" is the safe fallback
    rather than guessing a behavior classification or a unit weight. SPT/CPT/
    lab paste text default to empty (Stratum's own list fields already
    default that way) -- an empty-but-correctly-placed stratum is still
    useful, same as adding one by hand with no data pasted in yet.
    """
    problems: list[str] = []
    added = 0

    water_table = payload.get("water_table_depth_m")
    if water_table is not None:
        try:
            st.session_state["gm_water_table_raw"] = float(water_table)
        except (TypeError, ValueError):
            problems.append(f"'water_table_depth_m': not a number ('{water_table}') -- ignored.")

    raw_strata = payload.get("strata")
    if not isinstance(raw_strata, list):
        problems.append("Expected a top-level 'strata' list -- none found.")
        return added, problems

    recognised = set(_GI_STRATUM_REQUIRED_FIELDS) | set(_GI_STRATUM_TEXT_FIELDS)
    strata = _gi_strata()
    for i, entry in enumerate(raw_strata):
        label = entry.get("name", f"strata[{i}]") if isinstance(entry, dict) else f"strata[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"'{label}': expected an object, got {type(entry).__name__} -- skipped.")
            continue
        missing = [f for f in _GI_STRATUM_REQUIRED_FIELDS if entry.get(f) in (None, "")]
        if missing:
            problems.append(f"'{label}': missing required field(s) {', '.join(missing)} -- skipped, add manually.")
            continue
        if entry["behavior"] not in ("granular", "cohesive"):
            problems.append(f"'{label}': behavior must be 'granular' or 'cohesive', got '{entry['behavior']}' -- skipped.")
            continue
        for key in entry:
            if key not in recognised:
                problems.append(f"'{label}.{key}': not a recognised field -- ignored.")
        try:
            strata.append({
                "name": str(entry["name"]),
                "behavior": entry["behavior"],
                "top_depth_m": float(entry["top_depth_m"]),
                "base_depth_m": float(entry["base_depth_m"]),
                "assumed_unit_weight_kn_m3": float(entry["assumed_unit_weight_kn_m3"]),
                "spt_text": str(entry.get("spt_text") or ""),
                "cpt_text": str(entry.get("cpt_text") or ""),
                "lab_text": str(entry.get("lab_text") or ""),
            })
        except (TypeError, ValueError) as exc:
            problems.append(f"'{label}': {exc} -- skipped.")
            continue
        added += 1

    return added, problems


def render_gi_import_expander() -> None:
    """
    Sidebar-style "Import GI-derived strata (JSON)" expander, scoped to this tab
    (not the generic calcs.registry import sidebar) because the shape here --
    water_table_depth_m plus a list of stratum objects -- doesn't fit that
    mechanism's module_key -> {field: value} contract; the ground model
    interpreter isn't a registered CalcModule to begin with. Counterpart to the
    .claude/skills/fill-ground-model-from-gi-report/ skill, same "flag, don't
    guess" contract as fill-calc-inputs-from-drawings.
    """
    with st.expander("Import GI-derived strata (JSON)"):
        st.caption(
            "Upload a JSON file produced by the 'fill-ground-model-from-gi-report' skill (or "
            "matching its shape by hand) to add strata to the profile below without retyping them. "
            "See .claude/skills/fill-ground-model-from-gi-report/SKILL.md."
        )
        uploaded = st.file_uploader("Import file", type=["json"], key="gi_import_uploader", label_visibility="collapsed")
        if uploaded is not None and st.button("Import", key="gi_import_button"):
            try:
                payload = json.loads(uploaded.getvalue().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                st.session_state["_gi_import_summary"] = (0, [f"Could not parse the uploaded file as JSON: {exc}"])
            else:
                if not isinstance(payload, dict):
                    st.session_state["_gi_import_summary"] = (0, ["Expected a top-level JSON object with a 'strata' list."])
                else:
                    st.session_state["_gi_import_summary"] = _import_gi_profile(payload)
            if st.session_state.get("_gi_import_summary", (0,))[0]:
                st.session_state.pop("gi_profile_result", None)
                st.rerun()

        summary = st.session_state.get("_gi_import_summary")
        if summary:
            added, problems = summary
            if added:
                st.success(f"Added {added} stratum/strata to the profile below.")
            for p in problems:
                st.warning(p)


def _interpret_profile(strata_raw: list[dict], water_table_depth_m: Optional[float]) -> None:
    """
    Parses every stratum's paste text, builds ONE SiteInvestigation from all of
    them together (so overburden stress -- and therefore any stress-dependent
    correlation -- is computed across the full profile, not just whichever
    stratum happens to be interpreted), then runs interpret_stratum per
    stratum against that shared site. Stores the outcome in session_state
    (see _render_profile_result) rather than rendering inline, matching
    render_calc_module_tab's pattern -- results need to survive the rerun a
    "push to bearing resistance" button below triggers.
    """
    problems: list[str] = []
    built: list[Stratum] = []
    for s in strata_raw:
        spt_readings, spt_unparsed = parse_spt_lines(s["spt_text"])
        cpt_readings, cpt_unparsed = parse_cpt_lines(s["cpt_text"])
        lab_tests, lab_unparsed = parse_lab_lines(s["lab_text"])
        problems.extend(f"'{s['name']}': could not parse SPT line: '{u}'" for u in spt_unparsed)
        problems.extend(f"'{s['name']}': could not parse CPT line: '{u}'" for u in cpt_unparsed)
        problems.extend(f"'{s['name']}': could not parse lab test line: '{u}'" for u in lab_unparsed)
        try:
            built.append(Stratum(
                name=s["name"], top_depth_m=s["top_depth_m"], base_depth_m=s["base_depth_m"],
                behavior=s["behavior"], assumed_unit_weight_kn_m3=s["assumed_unit_weight_kn_m3"],
                spt_readings=spt_readings, cpt_readings=cpt_readings, lab_tests=lab_tests,
            ))
        except ValidationError as exc:
            for err in exc.errors():
                problems.append(f"'{s['name']}': {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")

    site = None
    if len(built) == len(strata_raw):
        try:
            site = SiteInvestigation(water_table_depth_m=water_table_depth_m, strata=built)
        except ValidationError as exc:
            for err in exc.errors():
                problems.append(f"Profile: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")

    results = []
    if site is not None:
        for stratum in built:
            design_params, notes = interpret_stratum(site, stratum)
            results.append((stratum, design_params, notes))

    st.session_state["gi_profile_result"] = {"problems": problems, "results": results}


def _render_profile_result() -> None:
    stored = st.session_state.get("gi_profile_result")
    if not stored:
        return

    for p in stored["problems"]:
        st.warning(p)
    if not stored["results"]:
        if stored["problems"]:
            st.error("Could not interpret the profile — fix the issue(s) above and try again.")
        return

    st.markdown("### Derived characteristic parameters")
    for i, (stratum, design_params, notes) in enumerate(stored["results"]):
        st.markdown(f"**{stratum.name}** — {stratum.behavior}, {stratum.top_depth_m:.2f}–{stratum.base_depth_m:.2f} m bgl")
        cols = st.columns(3)
        if design_params.phi_deg is not None:
            cols[0].metric("phi' (deg)", f"{design_params.phi_deg:.1f}")
        if design_params.cu_kpa is not None:
            cols[1].metric("cu (kPa)", f"{design_params.cu_kpa:.1f}")
        cols[2].metric("Unit weight (kN/m^3)", f"{design_params.unit_weight_kn_m3:.1f}")

        for w in design_params.warnings:
            st.warning(w)
        with st.expander(f"Derivation notes — {stratum.name}"):
            for n in notes:
                st.text(n)

        # One button, not "push" then a nested "open" — a button rendered only
        # inside another button's if-block only ever gets ONE rerun to be seen
        # in (the same run its parent was clicked), so a second click on it is
        # silently lost once the parent's own condition goes back to False on
        # the very next rerun. Setting the prefill and navigating together in
        # a single click sidesteps that rather than relying on two clicks.
        if st.button(f"Push '{stratum.name}' → open {BEARING_MODULE.name}", key=f"push_bearing__{i}"):
            _prefill_store()[BEARING_MODULE.key] = to_bearing_resistance_kwargs(design_params)
            _prefill_versions()[BEARING_MODULE.key] = _prefill_versions().get(BEARING_MODULE.key, 0) + 1
            st.session_state["selected_key"] = BEARING_MODULE.key
            st.rerun()
        st.divider()


def render_ground_model_tab() -> None:
    st.subheader("Ground model interpreter")
    st.caption(
        "Build a full layered ground model, one stratum (soil layer) at a time, then interpret the "
        "whole profile together — overburden stress, which several correlations depend on, is "
        "calculated across the FULL profile below a given depth, not just the stratum you're "
        "deriving parameters for, so a deeper stratum needs the shallower ones added too for an "
        "accurate result. Paste site investigation data one reading per line — a lenient line "
        "parser, not free-form report reading; unparsed lines are shown back to you rather than "
        "silently dropped. For a real GI report, see the import expander below."
    )

    render_gi_import_expander()

    water_table_depth_m_raw = st.number_input(
        "Water table depth (m bgl, 0 = at surface, leave large if none) — applies to the whole profile",
        value=100.0, min_value=0.0, key="gm_water_table_raw",
    )
    water_table_depth_m = None if water_table_depth_m_raw >= 90 else water_table_depth_m_raw

    strata = _gi_strata()

    st.markdown("### Add a stratum")
    with st.form("gi_add_stratum_form", clear_on_submit=True):
        default_top = strata[-1]["base_depth_m"] if strata else 0.0
        name = st.text_input("Stratum name", value=f"Stratum {len(strata) + 1}")
        colA, colB, colC = st.columns(3)
        with colA:
            behavior = st.selectbox("Soil behaviour", ["granular", "cohesive"])
        with colB:
            top_depth_m = st.number_input("Top depth (m)", value=default_top, min_value=0.0)
        with colC:
            base_depth_m = st.number_input("Base depth (m)", value=default_top + 2.0, min_value=0.01)
        assumed_unit_weight = st.number_input(
            "Assumed/typical bulk unit weight (kN/m^3) — used for overburden stress; overridden "
            "by lab bulk density data if provided below",
            value=18.0, min_value=1.0,
        )
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
        add_submitted = st.form_submit_button("Add stratum to profile")

    if add_submitted:
        if base_depth_m <= top_depth_m:
            st.error("Base depth must be greater than top depth — stratum not added.")
        else:
            strata.append({
                "name": name.strip() or f"Stratum {len(strata) + 1}",
                "behavior": behavior,
                "top_depth_m": top_depth_m,
                "base_depth_m": base_depth_m,
                "assumed_unit_weight_kn_m3": assumed_unit_weight,
                "spt_text": spt_text,
                "cpt_text": cpt_text,
                "lab_text": lab_text,
            })
            st.session_state.pop("gi_profile_result", None)
            st.rerun()

    if not strata:
        st.info("Add at least one stratum above (or import from a GI report) to interpret a profile.")
        return

    st.markdown("### Profile so far")
    for i, s in enumerate(strata):
        cols = st.columns([5, 1])
        cols[0].write(f"**{s['name']}** — {s['behavior']}, {s['top_depth_m']:.2f}–{s['base_depth_m']:.2f} m bgl")
        if cols[1].button("Remove", key=f"remove_stratum__{i}"):
            strata.pop(i)
            st.session_state.pop("gi_profile_result", None)
            st.rerun()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Interpret full profile", key="interpret_profile", type="primary"):
            _interpret_profile(strata, water_table_depth_m)
    with col2:
        if st.button("Clear all strata", key="clear_all_strata"):
            st.session_state["gi_strata"] = []
            st.session_state.pop("gi_profile_result", None)
            st.rerun()

    _render_profile_result()


def _discipline_sort_index(discipline: str) -> int:
    try:
        return DISCIPLINE_ORDER.index(discipline)
    except ValueError:
        return len(DISCIPLINE_ORDER)


def _catalog_entries() -> list[CatalogEntry]:
    """Every catalog row: the ground model interpreter plus one entry per registered
    CalcModule. Order doesn't matter here -- render_catalog does its own sort."""
    entries = [GROUND_MODEL_ENTRY]
    entries.extend(
        CatalogEntry(key=module.key, name=module.name, discipline=module.discipline, description=module.description)
        for module in CALC_REGISTRY
    )
    return entries


def _filter_entries(entries: list[CatalogEntry], query: str, discipline: str) -> list[CatalogEntry]:
    filtered = entries
    if discipline != "All disciplines":
        filtered = [e for e in filtered if e.discipline == discipline]
    q = query.strip().lower()
    if q:
        filtered = [e for e in filtered if q in e.name.lower() or q in e.discipline.lower() or q in e.description.lower()]
    return filtered


def render_catalog() -> None:
    """The catalog home page: search/filter box, then every matching calc as a card
    with an 'Open ->' button that switches into render_module_detail for that key."""
    all_entries = _catalog_entries()
    disciplines_present = sorted({e.discipline for e in all_entries}, key=_discipline_sort_index)

    st.caption(
        f"{len(all_entries)} calc tools across {len(disciplines_present)} disciplines. "
        "Search by name, discipline, or keyword, or filter by discipline, then open one to run it."
    )

    col_search, col_filter = st.columns([3, 1])
    with col_search:
        query = st.text_input(
            "Search calcs", placeholder="Search by name, discipline, or keyword...",
            key="catalog_search", label_visibility="collapsed",
        )
    with col_filter:
        discipline = st.selectbox(
            "Discipline", ["All disciplines"] + disciplines_present,
            key="catalog_discipline_filter", label_visibility="collapsed",
        )

    matches = _filter_entries(all_entries, query, discipline)
    if not matches:
        st.info("No calcs match that search/filter.")
        return

    for entry in sorted(matches, key=lambda e: (_discipline_sort_index(e.discipline), e.name)):
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{entry.name}**")
                st.caption(entry.discipline)
                st.write(entry.description)
            with right:
                if st.button("Open →", key=f"open__{entry.key}", use_container_width=True):
                    st.session_state["selected_key"] = entry.key
                    st.rerun()


def render_module_detail(key: str) -> None:
    """Full-width detail view for one catalog entry -- the ground model interpreter's
    bespoke tab, or a registered CalcModule's auto-built form via render_calc_module_tab."""
    if st.button("← Back to catalog"):
        st.session_state.pop("selected_key", None)
        st.rerun()
    st.divider()

    if key == GROUND_MODEL_KEY:
        render_ground_model_tab()
        return

    try:
        module = get_module(key)
    except KeyError:
        st.error(f"'{key}' isn't a registered calc (it may have been removed or renamed).")
        st.session_state.pop("selected_key", None)
        return
    render_calc_module_tab(module)


def main() -> None:
    st.set_page_config(page_title="total-auto", layout="wide")
    st.title("total-auto — engineering calculation tools")
    st.caption(
        "Search or browse the full calc catalog below and open one to run it. See docs/ROADMAP.md for "
        "what's planned beyond this."
    )

    # Runs before the catalog/detail view below so a same-run import (see its own
    # docstring) writes to the prefill store before any widgets read it.
    render_import_sidebar()

    selected_key = st.session_state.get("selected_key")
    if selected_key:
        render_module_detail(selected_key)
    else:
        render_catalog()


if __name__ == "__main__":
    main()
