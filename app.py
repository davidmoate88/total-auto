"""
Streamlit UI for total-auto's engineering calculation tools.

Tabs:
  1. Ground model interpreter — paste SPT/CPT/lab site investigation data per
     stratum, get derived characteristic design parameters, hand off to the
     bearing resistance calc.
  2+. One tab per module in calcs.registry.CALC_REGISTRY, form auto-built from
     the module's pydantic input model (see _render_calc_form) — per the
     design principle in docs/ARCHITECTURE.md: "app.py just discovers
     registered calc modules and renders a form + result for whichever one is
     selected... adding a new discipline means adding a new module +
     registering it — the app and report generator don't change." Previously
     this only special-cased the geotechnical bearing calc directly; that's
     now handled generically like every other registered module (still with
     the ground-model-interpreter prefill handoff wired specifically for it,
     since prefilling is inherently module-specific).

The generic form (_field_widget) introspects each pydantic v2 field's
annotation, default, and constraint metadata (Ge/Gt/Le/Lt) to pick a
Streamlit widget: selectbox for Literal, checkbox for bool, number_input for
int/float (with min/max from gt/ge/lt/le where present), text_input
otherwise. Optional[...] fields get a "Set <field>?" checkbox so the user can
explicitly omit them (submitting None) rather than being forced to enter a
sentinel value that might itself fail validation (e.g. a gt=0 field can't
default to 0 to mean "omit"). This trades the hand-laid-out columns/expanders
the original bearing-resistance-specific tab had for genericity across every
registered module — deliberate, since hand-laying-out a form per module
doesn't scale to five (and growing) calc modules.

Run with: streamlit run app.py
"""

from __future__ import annotations

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
from calcs.registry import CALC_REGISTRY
from core.calc_base import CalcModule
from core.report import render_report


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

    value = prefill_value if prefill_value is not None else (default or "")
    return st.text_input(label, value=str(value), help=help_text, key=key)


def render_calc_module_tab(module: CalcModule) -> None:
    st.subheader(module.name)
    st.caption(module.description)

    prefill = st.session_state.get("bearing_prefill", {}) if module.key == BEARING_MODULE.key else {}
    # Widget `value=` only takes effect the first time a given key renders -- on later
    # reruns the widget keeps whatever the user last set, ignoring `value=` even if
    # `prefill` has since changed. Folding the prefill version into the key forces a
    # fresh widget (and therefore a fresh `value=`) each time a new prefill arrives.
    prefill_version = st.session_state.get("bearing_prefill_version", 0) if prefill else 0
    key_prefix = f"{module.key}__{prefill_version}"

    with st.form(f"calc_form__{module.key}__{prefill_version}"):
        values: dict = {}
        for field_name, field_info in module.input_model.model_fields.items():
            values[field_name] = _field_widget(field_name, field_info, prefill, key_prefix=key_prefix)
        submitted = st.form_submit_button(f"Run: {module.name}")

    if not submitted:
        return

    try:
        inputs = module.input_model(**values)
    except ValidationError as exc:
        st.error("Input validation failed:")
        for err in exc.errors():
            st.error(f"- {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")
        return

    result = module.calculate(inputs)
    _render_result(module, inputs, result)


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

        st.session_state["bearing_prefill"] = to_bearing_resistance_kwargs(design_params)
        st.session_state["bearing_prefill_version"] = st.session_state.get("bearing_prefill_version", 0) + 1
        st.success(f"Derived parameters saved — switch to the '{BEARING_MODULE.name}' tab; they'll be pre-filled.")


def main() -> None:
    st.set_page_config(page_title="total-auto", layout="centered")
    st.title("total-auto — engineering calculation tools")
    st.caption(
        "Ground model interpretation feeds the geotechnical bearing calc; every other tab is a "
        "calc module discovered from calcs.registry.CALC_REGISTRY. See docs/ROADMAP.md for what's "
        "planned beyond this."
    )

    tab_labels = ["Ground model interpreter"] + [module.name for module in CALC_REGISTRY]
    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_ground_model_tab()
    for tab, module in zip(tabs[1:], CALC_REGISTRY):
        with tab:
            render_calc_module_tab(module)


if __name__ == "__main__":
    main()
