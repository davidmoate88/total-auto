"""
Extracts cross-discipline "open items" — pending inputs that show up as
"to be confirmed" / "pending" / "provisional" language inside a basis-of-
design section's criteria and assumptions — into a single register.

This doesn't add any new information: every open item traces back to text
already written during the detail pass (see docs/ROADMAP.md Milestone 1a).
What's new is collecting scattered notes like "to be confirmed from the LV
load schedule", spread across five separate modules, into one list a person
(or the eventual portfolio/actions tooling) can actually work through.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from basis_of_design.civils import build_civils_bod_skeleton
from basis_of_design.electrical_hv import build_electrical_hv_bod_skeleton
from basis_of_design.electrical_lv import build_electrical_lv_bod_skeleton
from basis_of_design.mechanical_piping import build_mechanical_piping_bod_skeleton
from basis_of_design.structural import build_structural_bod_skeleton
from comms.meeting_minutes.models import ActionItem

_BUILDERS = {
    "civils": build_civils_bod_skeleton,
    "structural": build_structural_bod_skeleton,
    "electrical_lv": build_electrical_lv_bod_skeleton,
    "electrical_hv": build_electrical_hv_bod_skeleton,
    "mechanical_piping": build_mechanical_piping_bod_skeleton,
}

# Deliberately a tight, high-precision keyword list rather than free-text
# NLP — a missed open item is safer than a settled criterion wrongly
# flagged as still pending, for something meant to become an actual to-do
# list. Extend this list if a discipline's wording style produces misses
# once this is used for real (tests/test_integration.py documents the
# current count as a baseline to notice drift against).
_PENDING_MARKERS = [
    "to be confirmed",
    "pending",
    "provisional",
    "not yet",
    "once the",
    "assumed until",
    "cannot be finalised",
    "cannot be set without",
]


class OpenItem(BaseModel):
    discipline: str
    section: str
    section_name: str
    item_type: str  # "criterion" | "assumption"
    text: str
    source_reference: str


def _matches(*texts: Optional[str]) -> bool:
    joined = " ".join(t for t in texts if t).lower()
    return any(marker in joined for marker in _PENDING_MARKERS)


def extract_open_items() -> list[OpenItem]:
    items: list[OpenItem] = []
    for discipline, builder in _BUILDERS.items():
        bod = builder()
        for section_key, section in bod.sections().items():
            for c in section.criteria:
                if _matches(c.value, c.notes):
                    note = f" — {c.notes}" if c.notes else ""
                    items.append(
                        OpenItem(
                            discipline=discipline,
                            section=section_key,
                            section_name=section.name,
                            item_type="criterion",
                            text=f"{c.name}: {c.value}{note}",
                            source_reference=f"basis_of_design.{discipline}:{section_key}",
                        )
                    )
            for a in section.assumptions:
                if _matches(a.description, a.notes):
                    note = f" ({a.notes})" if a.notes else ""
                    items.append(
                        OpenItem(
                            discipline=discipline,
                            section=section_key,
                            section_name=section.name,
                            item_type="assumption",
                            text=f"{a.description}{note}",
                            source_reference=f"basis_of_design.{discipline}:{section_key}",
                        )
                    )
    return items


def open_items_as_action_items(items: list[OpenItem], project_reference: Optional[str] = None) -> list[ActionItem]:
    """
    Converts open items into `comms.meeting_minutes.models.ActionItem` — the
    first real wiring of this open-items register into the actions/portfolio
    scaffolding described in docs/ARCHITECTURE.md's "Intended integration
    points" section, rather than just noting the seam exists.
    """
    return [
        ActionItem(
            description=f"[{item.discipline}/{item.section_name}] {item.text}",
            related_project_reference=project_reference,
        )
        for item in items
    ]


def render_open_items_register(items: list[OpenItem]) -> str:
    """Body content only (no top-level title) — callers embed this under their own heading."""
    lines = [f"*{len(items)} open items across all disciplines.*", ""]
    by_discipline: dict[str, list[OpenItem]] = {}
    for item in items:
        by_discipline.setdefault(item.discipline, []).append(item)
    for discipline, disc_items in by_discipline.items():
        lines.append(f"### {discipline} ({len(disc_items)})")
        lines.append("")
        for item in disc_items:
            lines.append(f"- **{item.section_name}** [{item.item_type}]: {item.text}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    # python3 -m integration.open_items  -- prints the full open items register.
    print(render_open_items_register(extract_open_items()))
