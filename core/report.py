"""
Turns a CalcResult into a review-ready markdown calculation sheet — the same shape
a checker/approver would expect to see on a real project: inputs, method, full
working, headline result, and any warnings or references.
"""

from __future__ import annotations

from datetime import datetime

from core.calc_base import CalcModule, CalcResult


def render_report(
    module: CalcModule,
    inputs: object,
    result: CalcResult,
    generated_at: str | None = None,
) -> str:
    """
    Build a markdown calculation sheet.

    `generated_at` is injected (rather than computed with datetime.now() at call
    time by default) so output is reproducible in tests; callers in the app pass
    the real current time.
    """
    ts = generated_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append(f"# {module.name}")
    lines.append("")
    lines.append(f"**Discipline:** {module.discipline}  ")
    lines.append(f"**Method:** {result.method}  ")
    lines.append(f"**Generated:** {ts}")
    lines.append("")

    lines.append("## Inputs")
    lines.append("")
    for field_name, value in _iter_fields(inputs):
        lines.append(f"- **{field_name}**: {value}")
    lines.append("")

    lines.append("## Working")
    lines.append("")
    for term in result.terms:
        lines.append(f"- {term.formatted()}")
    lines.append("")

    lines.append("## Result")
    lines.append("")
    lines.append(f"**{result.headline.formatted(precision=4)}**")
    lines.append("")

    if result.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in result.warnings:
            lines.append(f"- ⚠ {w}")
        lines.append("")

    if result.references:
        lines.append("## References")
        lines.append("")
        for r in result.references:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)


def _iter_fields(inputs: object):
    # Works with pydantic v1 or v2 models, or any object exposing __dict__.
    if hasattr(inputs, "model_dump"):
        data = inputs.model_dump()
    elif hasattr(inputs, "dict"):
        data = inputs.dict()
    else:
        data = vars(inputs)
    for key, value in data.items():
        yield key, value
