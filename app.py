"""
Streamlit UI for total-auto's geotechnical tools.

Two tabs:
  1. Ground model interpreter — paste SPT/CPT/lab site investigation data per
     stratum, get derived characteristic design parameters, hand off to the
     bearing resistance calc.
  2. Bearing resistance calculator — EN 1997-1 Annex D / UK NA DA1, run directly
     with known parameters or pre-filled from the ground model interpreter.

NOTE: this module was written without a live Streamlit instance available in
the build environment (no network access to install it) — the interpretation
logic and bearing resistance calc are independently verified (see tests/ and
docs/ROADMAP.md), but this UI wiring itself has not been visually run. Flag
any layout/behaviour issues you hit and they can be fixed quickly.

Run with: streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from pydantic import ValidationError

from calcs.geotechnical.bearing_capacity import BearingResistanceInput, MODULE as BEARING_MODULE
from calcs.geotechnical.interpretation.ground_model import interpret_stratum, to_bearing_resistance_kwargs
from calcs.geotechnical.interpretation.models import SiteInvestigation, Stratum
from calcs.geotechnical.interpretation.text_input import (
    parse_cpt_lines,
    parse_lab_lines,
    parse_spt_lines,
)
from core.report import render_report


def render_bearing_resistance_tab() -> None:
    st.subheader(BEARING_MODULE.name)
    st.caption(BEARING_MODULE.description)

    prefill = st.session_state.get("bearing_prefill", {})

    with st.form("bearing_resistance_form"):
        analysis_type = st.selectbox(
            "Analysis type", ["drained", "undrained"],
            index=0 if prefill.get("analysis_type", "drained") == "drained" else 1,
        )

        col1, col2 = st.columns(2)
        with col1:
            cohesion_c_prime_kpa = st.number_input(
                "c' — effective cohesion (kPa, drained only)",
                value=float(prefill.get("cohesion_c_prime_kpa") or 0.0), min_value=0.0,
            )
            friction_angle_phi_prime_deg = st.number_input(
                "phi' — effective friction angle (deg, drained only)",
                value=float(prefill.get("friction_angle_phi_prime_deg") or 30.0), min_value=0.1, max_value=45.0,
            )
        with col2:
            undrained_shear_strength_cu_kpa = st.number_input(
                "cu — undrained shear strength (kPa, undrained only)",
                value=float(prefill.get("undrained_shear_strength_cu_kpa") or 0.0), min_value=0.0,
            )
            unit_weight_kn_m3 = st.number_input(
                "gamma — bulk unit weight (kN/m^3)",
                value=float(prefill.get("unit_weight_kn_m3") or 18.0), min_value=0.1,
            )

        has_water_table = st.checkbox("Water table present above founding level?", value=False)
        water_table_depth_m = st.number_input("Water table depth (m bgl)", value=1.0, min_value=0.0) if has_water_table else None

        st.markdown("**Footing geometry**")
        gcol1, gcol2, gcol3 = st.columns(3)
        with gcol1:
            width_m = st.number_input("Width B (m)", value=1.5, min_value=0.01)
        with gcol2:
            length_m = st.number_input("Length L (m, >= B)", value=1.5, min_value=0.01)
        with gcol3:
            depth_m = st.number_input("Founding depth D (m)", value=1.0, min_value=0.0)

        with st.expander("Eccentricity, base inclination (optional)"):
            ecol1, ecol2, ecol3 = st.columns(3)
            with ecol1:
                eccentricity_b_m = st.number_input("Eccentricity eB (m)", value=0.0, min_value=0.0)
            with ecol2:
                eccentricity_l_m = st.number_input("Eccentricity eL (m)", value=0.0, min_value=0.0)
            with ecol3:
                base_inclination_deg = st.number_input("Base inclination alpha (deg)", value=0.0, min_value=0.0, max_value=44.0)

        with st.expander("Design loads (optional — leave at 0 for resistance-only, no pass/fail check)"):
            lcol1, lcol2, lcol3 = st.columns(3)
            with lcol1:
                Gk = st.number_input("Gk — characteristic permanent load (kN)", value=0.0, min_value=0.0)
            with lcol2:
                Qk = st.number_input("Qk — characteristic variable load (kN)", value=0.0, min_value=0.0)
            with lcol3:
                Hk = st.number_input("Hk — characteristic horizontal load (kN)", value=0.0, min_value=0.0)
            h_is_variable = st.checkbox("Horizontal load is a variable action (e.g. wind)", value=True)

        submitted = st.form_submit_button("Calculate design bearing resistance")

    if not submitted:
        return

    try:
        inputs = BearingResistanceInput(
            analysis_type=analysis_type,
            cohesion_c_prime_kpa=cohesion_c_prime_kpa if analysis_type == "drained" else None,
            friction_angle_phi_prime_deg=friction_angle_phi_prime_deg if analysis_type == "drained" else None,
            undrained_shear_strength_cu_kpa=undrained_shear_strength_cu_kpa if analysis_type == "undrained" else None,
            unit_weight_kn_m3=unit_weight_kn_m3,
            water_table_depth_m=water_table_depth_m,
            width_m=width_m,
            length_m=length_m,
            depth_m=depth_m,
            eccentricity_b_m=eccentricity_b_m,
            eccentricity_l_m=eccentricity_l_m,
            base_inclination_deg=base_inclination_deg,
            characteristic_permanent_load_kn=Gk,
            characteristic_variable_load_kn=Qk,
            characteristic_horizontal_load_kn=Hk,
            horizontal_load_is_variable=h_is_variable,
        )
    except ValidationError as exc:
        st.error("Input validation failed:")
        for err in exc.errors():
            st.error(f"- {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")
        return

    result = BEARING_MODULE.calculate(inputs)
    _render_result(BEARING_MODULE, inputs, result)


def _render_result(module, inputs, result) -> None:
    st.subheader("Result")
    st.metric(result.headline.label, f"{result.headline.value:.4g} {result.headline.unit}")
    if result.headline.note:
        st.caption(result.headline.note)

    for w in result.warnings:
        st.warning(w)

    with st.expander("Full working (both DA1 combinations)"):
        for term in result.terms:
            st.text(term.formatted())

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report_md = render_report(module, inputs, result, generated_at=generated_at)
    with st.expander("Review-ready report (markdown)"):
        st.code(report_md, language="markdown")
    st.download_button("Download report (.md)", data=report_md, file_name=f"{module.key}_report.md", mime="text/markdown")


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
        st.success("Derived parameters saved — switch to the Bearing resistance tab; they'll be pre-filled.")


def main() -> None:
    st.set_page_config(page_title="total-auto", layout="centered")
    st.title("total-auto — geotechnical tools")
    st.caption(
        "Milestone 1 (extended): ground model interpretation feeding an EN 1997-1 "
        "Annex D bearing resistance calc. See docs/ROADMAP.md for what's planned beyond this."
    )

    tab1, tab2 = st.tabs(["Ground model interpreter", "Bearing resistance calculator"])
    with tab1:
        render_ground_model_tab()
    with tab2:
        render_bearing_resistance_tab()


if __name__ == "__main__":
    main()
