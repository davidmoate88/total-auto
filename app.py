"""
Streamlit UI: lists registered calc modules, renders a form built from each
module's pydantic input model, runs the calculation, and shows/downloads a
review-ready report.

Run with: streamlit run app.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
from pydantic import ValidationError

from calcs.registry import CALC_REGISTRY
from core.report import render_report


def _field_bounds(field) -> tuple[float | None, float | None]:
    """Extract (ge_or_gt, le_or_lt) numeric bounds from a pydantic v2 FieldInfo."""
    lo = hi = None
    for constraint in field.metadata:
        for attr in ("ge", "gt"):
            if hasattr(constraint, attr):
                lo = getattr(constraint, attr)
        for attr in ("le", "lt"):
            if hasattr(constraint, attr):
                hi = getattr(constraint, attr)
    return lo, hi


def render_input_form(input_model, key_prefix: str) -> dict:
    values = {}
    for field_name, field in input_model.model_fields.items():
        lo, hi = _field_bounds(field)
        default = field.default if field.default is not None else 0.0
        label = field_name.replace("_", " ")
        if field.description:
            label = f"{label} — {field.description}"
        values[field_name] = st.number_input(
            label,
            value=float(default),
            min_value=float(lo) if lo is not None else None,
            max_value=float(hi) if hi is not None else None,
            key=f"{key_prefix}_{field_name}",
        )
    return values


def main() -> None:
    st.set_page_config(page_title="total-auto", layout="centered")
    st.title("total-auto — engineering calculations")
    st.caption(
        "Milestone 1: a small, extensible framework for engineering calc modules. "
        "See docs/ROADMAP.md for what's planned beyond this."
    )

    if not CALC_REGISTRY:
        st.warning("No calc modules registered yet.")
        return

    module_names = {m.name: m for m in CALC_REGISTRY}
    selected_name = st.selectbox("Calculation", list(module_names.keys()))
    module = module_names[selected_name]

    st.markdown(f"**Discipline:** {module.discipline}")
    st.markdown(module.description)

    with st.form(key=f"form_{module.key}"):
        raw_values = render_input_form(module.input_model, key_prefix=module.key)
        submitted = st.form_submit_button("Calculate")

    if not submitted:
        return

    try:
        validated_inputs = module.input_model(**raw_values)
    except ValidationError as exc:
        st.error("Input validation failed:")
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            st.error(f"- {loc}: {err['msg']}")
        return

    result = module.calculate(validated_inputs)

    st.subheader("Result")
    st.metric(result.headline.label, f"{result.headline.value:.4g} {result.headline.unit}")
    if result.headline.note:
        st.caption(result.headline.note)

    if result.warnings:
        for w in result.warnings:
            st.warning(w)

    with st.expander("Full working"):
        for term in result.terms:
            st.text(term.formatted())

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report_md = render_report(module, validated_inputs, result, generated_at=generated_at)

    with st.expander("Review-ready report (markdown)"):
        st.code(report_md, language="markdown")

    st.download_button(
        "Download report (.md)",
        data=report_md,
        file_name=f"{module.key}_report.md",
        mime="text/markdown",
    )


if __name__ == "__main__":
    main()
