"""
Stitches the five discipline basis-of-design skeletons, the cross-discipline
dependency graph, and the open-items register into one project-level
document — the "single coherent solution" view across everything built so
far in `basis_of_design/`.

This intentionally doesn't replace each discipline's own
`render_basis_of_design()` output (see docs/examples/) — it sits a level
above, answering "how does this all fit together" rather than "what does
discipline X say on its own".
"""

from __future__ import annotations

from typing import Optional

from basis_of_design.civils import build_civils_bod_skeleton
from basis_of_design.electrical_hv import build_electrical_hv_bod_skeleton
from basis_of_design.electrical_lv import build_electrical_lv_bod_skeleton
from basis_of_design.mechanical_piping import build_mechanical_piping_bod_skeleton
from basis_of_design.render import render_basis_of_design
from basis_of_design.structural import build_structural_bod_skeleton
from integration.graph import build_dependency_graph
from integration.open_items import extract_open_items, render_open_items_register

_DISCIPLINE_TITLES = {
    "civils": "Civils",
    "structural": "Structural",
    "electrical_lv": "LV Electrical",
    "electrical_hv": "HV Electrical",
    "mechanical_piping": "Mechanical Piping",
}

_BUILDERS = {
    "civils": build_civils_bod_skeleton,
    "structural": build_structural_bod_skeleton,
    "electrical_lv": build_electrical_lv_bod_skeleton,
    "electrical_hv": build_electrical_hv_bod_skeleton,
    "mechanical_piping": build_mechanical_piping_bod_skeleton,
}


def render_process_flow_summary() -> str:
    """
    The "how does this all fit together" narrative on its own: dependency
    order, the mutually-dependent discipline cluster, the Mermaid diagram,
    and the open items register — without re-rendering all five full basis
    of design documents underneath it. Useful on its own (docs/examples/) and
    reused as the top of render_master_basis_of_design() below.
    """
    graph = build_dependency_graph()
    cycles = graph.find_discipline_cycles()
    open_items = extract_open_items()

    lines = ["## Process flow — discipline dependency order\n"]
    lines.append(
        "Derived directly from the `Interface` entries already declared in each "
        "discipline's basis of design (see `integration/graph.py`) — not a separately "
        "asserted opinion about sequencing.\n"
    )
    lines.append(
        "**Geotechnical** (the one built calc module) is the one true starting point — "
        "civils, structural, and both electrical disciplines all depend on it (ground "
        "model, bearing resistance, soil resistivity), and nothing depends back on it.\n"
    )
    lines.append(
        "**Structural** depends only on geotechnical (plus an external contractor for "
        "temporary works) and nothing loops back into it from the graph — it can be "
        "sequenced right after geotechnical and developed largely independently from "
        "there.\n"
    )
    for cluster in cycles:
        lines.append(
            f"**{', '.join(cluster)}** mutually depend on each other — each one's basis "
            "of design references at least one of the others, and following the edges "
            "far enough loops back to the start. This is not a strict pipeline: these "
            "four disciplines need iterative/concurrent co-design. Use "
            "`integration.process_state` to see what's actually unblocked at any point "
            "rather than assuming a fixed hand-off order between them.\n"
        )
    lines.append("```mermaid")
    lines.append(graph.to_mermaid())
    lines.append("```\n")

    lines.append("## Open items / RFI register\n")
    lines.append(
        f"{len(open_items)} pending inputs found across all five disciplines' criteria "
        'and assumptions (e.g. "to be confirmed from the DNO connection offer") — see '
        "`integration/open_items.py`. Full register:\n"
    )
    lines.append(render_open_items_register(open_items))

    return "\n".join(lines)


def render_master_basis_of_design(project_reference: Optional[str] = None) -> str:
    lines = ["# Project Basis of Design — Combined", ""]
    if project_reference:
        lines.append(f"**Project reference:** {project_reference}\n")
    lines.append(
        "One project-level view across all five disciplines: how they depend on each "
        "other, what's still an open input, and each discipline's own basis of design "
        "in full.\n"
    )

    lines.append(render_process_flow_summary())

    for discipline, builder in _BUILDERS.items():
        bod = builder()
        title = _DISCIPLINE_TITLES[discipline]
        lines.append(f"## {title} — full basis of design\n")
        lines.append(render_basis_of_design(title, bod.sections()))

    return "\n".join(lines)


if __name__ == "__main__":
    # python3 -m integration.master_document  -- prints the full combined project document.
    print(render_master_basis_of_design())
