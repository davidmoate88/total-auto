"""
Renders any discipline's basis of design (a collection of named
BasisOfDesignSection instances) into a single markdown document — the "one
all-encompassing output" a discipline BoD is meant to produce once its
sections are filled in.
"""

from __future__ import annotations

from basis_of_design.core import BasisOfDesignSection


def render_basis_of_design(discipline_name: str, sections: dict[str, BasisOfDesignSection], project_reference: str | None = None) -> str:
    lines: list[str] = [f"# {discipline_name} — Basis of Design"]
    if project_reference:
        lines.append(f"\n**Project reference:** {project_reference}")
    lines.append("")

    populated = [s for s in sections.values() if s.is_populated()]
    skeleton = [s for s in sections.values() if not s.is_populated()]
    if skeleton:
        lines.append(
            f"*{len(populated)} of {len(sections)} sections have content; "
            f"{len(skeleton)} are still skeleton-only: "
            f"{', '.join(s.name for s in skeleton)}.*\n"
        )

    for section in sections.values():
        lines.append(f"## {section.name}")
        if section.scope:
            lines.append(f"\n{section.scope}\n")

        if section.standards:
            lines.append("**Applicable standards:**\n")
            for s in section.standards:
                na = f" ({s.national_annex})" if s.national_annex else ""
                title = f" — {s.title}" if s.title else ""
                note = f" _{s.notes}_" if s.notes else ""
                lines.append(f"- {s.code}{na}{title}{note}")
            lines.append("")

        if section.criteria:
            lines.append("**Design criteria:**\n")
            for c in section.criteria:
                val = f"{c.value} {c.unit}".strip() if c.value else "(TBC)"
                note = f" — {c.notes}" if c.notes else ""
                lines.append(f"- {c.name}: {val}{note}")
            lines.append("")

        if section.assumptions:
            lines.append("**Assumptions:**\n")
            for a in section.assumptions:
                note = f" ({a.notes})" if a.notes else ""
                lines.append(f"- {a.description}{note}")
            lines.append("")

        if section.exclusions:
            lines.append("**Exclusions:**\n")
            for e in section.exclusions:
                lines.append(f"- {e}")
            lines.append("")

        if section.interfaces:
            lines.append("**Interfaces:**\n")
            for i in section.interfaces:
                lines.append(f"- **{i.with_discipline}**: {i.description}")
            lines.append("")

        if section.calculations_required:
            lines.append("**Calculations required:**\n")
            for calc in section.calculations_required:
                ref = f" (module: `{calc.calc_module_reference}`)" if calc.calc_module_reference else " (not yet built)"
                std = f" — to {calc.standard_reference}" if calc.standard_reference else ""
                desc = f": {calc.description}" if calc.description else ""
                lines.append(f"- {calc.name}{std}{desc}{ref}")
            lines.append("")

        if section.deliverables:
            lines.append("**Deliverables:**\n")
            for d in section.deliverables:
                fmt = f" ({d.format})" if d.format else ""
                desc = f" — {d.description}" if d.description else ""
                lines.append(f"- {d.name}{fmt}{desc}")
            lines.append("")

        if not section.is_populated():
            lines.append("*(Skeleton only — no content added yet.)*\n")

    return "\n".join(lines)
