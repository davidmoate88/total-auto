"""
Cross-discipline process-flow graph — derived from the `Interface` entries
already declared inside each `basis_of_design/<discipline>.py` skeleton.

This module doesn't invent any new dependency information: every edge it
produces traces back to an actual `Interface(with_discipline=...)` entry a
discipline's basis-of-design skeleton already carries (30 of them, across
the five disciplines, as of the detail pass). What's new is turning that
scattered, per-section information into one queryable graph — so "what has
to happen before what" and "what's stuck waiting on what" can be answered
directly instead of read off five separate documents by eye.

*** Read before extending *** — `with_discipline` on an `Interface` is used
inconsistently across the five discipline modules: sometimes it names a
whole discipline (e.g. "structural"), sometimes a specific section within a
discipline (civils' "utilities_coordination", "flood_risk"), and sometimes
an external actor this repo doesn't model at all ("process", "architectural",
"contractor / temporary works designer"). `_resolve_target()` below handles
all three cases, but there's no namespacing enforced across section names —
if a future discipline introduces a section name that collides with one in
another discipline, resolution could silently pick the wrong owner (first
discipline registered in `DISCIPLINES` wins ties). None of the 44 section
names in the five disciplines built so far collide in a way that matters
(verified in tests/test_integration.py), but this is worth knowing before
adding a sixth discipline.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from basis_of_design.civils import CIVILS_SECTION_NAMES, build_civils_bod_skeleton
from basis_of_design.electrical_hv import ELECTRICAL_HV_SECTION_NAMES, build_electrical_hv_bod_skeleton
from basis_of_design.electrical_lv import ELECTRICAL_LV_SECTION_NAMES, build_electrical_lv_bod_skeleton
from basis_of_design.mechanical_piping import MECHANICAL_PIPING_SECTION_NAMES, build_mechanical_piping_bod_skeleton
from basis_of_design.structural import STRUCTURAL_SECTION_NAMES, build_structural_bod_skeleton

NodeKind = Literal["discipline", "section", "calc", "external"]

# The five basis_of_design disciplines this graph is built from, in the
# order they were originally agreed and built — NOT necessarily the order
# they can be *executed* in. find_discipline_cycles() below is the actual
# answer to "what order should this happen in" (some of these mutually
# depend on each other and can't be strictly ordered at all).
DISCIPLINES = {
    "civils": (CIVILS_SECTION_NAMES, build_civils_bod_skeleton),
    "structural": (STRUCTURAL_SECTION_NAMES, build_structural_bod_skeleton),
    "electrical_lv": (ELECTRICAL_LV_SECTION_NAMES, build_electrical_lv_bod_skeleton),
    "electrical_hv": (ELECTRICAL_HV_SECTION_NAMES, build_electrical_hv_bod_skeleton),
    "mechanical_piping": (MECHANICAL_PIPING_SECTION_NAMES, build_mechanical_piping_bod_skeleton),
}

# The one built calc module this graph knows about outside basis_of_design/,
# keyed the same way calcs/registry.py keys it.
GEOTECHNICAL_CALC_KEY = "geotech_bearing_resistance_ec7"


class NodeRef(BaseModel):
    kind: NodeKind
    discipline: Optional[str] = None
    section: Optional[str] = None
    label: Optional[str] = Field(None, description="Display label, mainly for calc/external nodes.")

    @property
    def id(self) -> str:
        if self.kind == "section":
            return f"section:{self.discipline}.{self.section}"
        if self.kind == "discipline":
            return f"discipline:{self.discipline}"
        if self.kind == "calc":
            return f"calc:{self.discipline}"
        return f"external:{self.label}"


class DependencyEdge(BaseModel):
    from_section: str = Field(..., description="Section node id this edge originates from.")
    to_node: str = Field(..., description="Node id this section depends on.")
    description: str


class SectionInfo(BaseModel):
    id: str
    discipline: str
    section: str
    name: str


class DependencyGraph(BaseModel):
    sections: dict[str, SectionInfo] = Field(default_factory=dict)
    node_labels: dict[str, str] = Field(default_factory=dict)
    edges: list[DependencyEdge] = Field(default_factory=list)

    def upstream_of(self, node_id: str) -> list[str]:
        """Nodes `node_id` depends on (must be resolved before it can be)."""
        return sorted({e.to_node for e in self.edges if e.from_section == node_id})

    def downstream_of(self, node_id: str) -> list[str]:
        """Sections whose completion depends on `node_id` being resolved first."""
        return sorted({e.from_section for e in self.edges if e.to_node == node_id})

    def discipline_edges(self) -> set[tuple[str, str]]:
        """Collapsed discipline-to-discipline edges (deduplicated), for the high-level view."""
        out: set[tuple[str, str]] = set()
        for e in self.edges:
            from_discipline = self.sections[e.from_section].discipline
            to_discipline = _discipline_of_node(e.to_node)
            if to_discipline and to_discipline != from_discipline:
                out.add((from_discipline, to_discipline))
        return out

    def find_discipline_cycles(self) -> list[list[str]]:
        """
        Strongly-connected components (size > 1) among the five disciplines.
        A discipline appearing in one of these clusters cannot be strictly
        sequenced before/after the others in the cluster — they depend on
        each other and need iterative/concurrent co-design, not a one-pass
        pipeline.
        """
        return _tarjan_scc(list(DISCIPLINES.keys()), self.discipline_edges())

    def to_mermaid(self) -> str:
        """
        Discipline-level flowchart (Mermaid). Not the full section-level
        graph — that's 30+ edges and unreadable as a diagram; use
        upstream_of()/downstream_of() for section-level queries instead.
        """

        def mermaid_id_for(node_id: str) -> str:
            return "n_" + "".join(ch if ch.isalnum() else "_" for ch in node_id)

        disc_edges: set[tuple[str, str]] = set()
        special_targets: dict[str, str] = {}
        special_edges: set[tuple[str, str]] = set()

        for e in self.edges:
            from_disc = self.sections[e.from_section].discipline
            to_disc = _discipline_of_node(e.to_node)
            if to_disc:
                if to_disc != from_disc:
                    disc_edges.add((from_disc, to_disc))
            else:
                mid = mermaid_id_for(e.to_node)
                special_targets[mid] = self.node_labels.get(e.to_node, e.to_node)
                special_edges.add((from_disc, mid))

        lines = ["flowchart LR"]
        for disc in DISCIPLINES:
            lines.append(f'    {disc}(["{disc}"])')
        for mid, label in sorted(special_targets.items()):
            is_calc = label.lower().startswith("geotechnical")
            open_b, close_b = ("{{", "}}") if is_calc else ("[/", "/]")
            lines.append(f'    {mid}{open_b}"{label}"{close_b}')
        for a, b in sorted(disc_edges):
            lines.append(f"    {a} --> {b}")
        for a, mid in sorted(special_edges):
            lines.append(f"    {a} --> {mid}")
        return "\n".join(lines)


def _discipline_of_node(node_id: str) -> Optional[str]:
    if node_id.startswith("discipline:"):
        return node_id.split(":", 1)[1]
    if node_id.startswith("section:"):
        return node_id.split(":", 1)[1].split(".")[0]
    return None


def _resolve_target(with_discipline: str, section_owner: dict[str, str]) -> NodeRef:
    key = with_discipline.strip()
    if key in DISCIPLINES:
        return NodeRef(kind="discipline", discipline=key)
    if key == "geotechnical":
        return NodeRef(kind="calc", discipline=GEOTECHNICAL_CALC_KEY, label="Geotechnical (calc, built)")
    if key in section_owner:
        return NodeRef(kind="section", discipline=section_owner[key], section=key)
    return NodeRef(kind="external", label=key)


def _tarjan_scc(nodes: list[str], edges: set[tuple[str, str]]) -> list[list[str]]:
    """Standard Tarjan's strongly-connected-components algorithm, returning only
    components with more than one member (genuine cycles, not trivial self-loops)."""
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    for a, b in edges:
        adjacency.setdefault(a, []).append(b)

    index_counter = [0]
    stack: list[str] = []
    lowlink: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    result: list[list[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in adjacency.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == v:
                    break
            result.append(component)

    for n in nodes:
        if n not in index:
            strongconnect(n)

    return [sorted(c) for c in result if len(c) > 1]


def build_dependency_graph() -> DependencyGraph:
    """
    Builds the full section-level dependency graph by instantiating every
    discipline's skeleton (via its `build_*_bod_skeleton()` function) and
    walking each section's `interfaces` list. This is metadata extraction
    only — it doesn't run any calculations or require real project data.
    """
    graph = DependencyGraph()

    section_owner: dict[str, str] = {}
    for disc, (names, _builder) in DISCIPLINES.items():
        for name in names:
            section_owner.setdefault(name, disc)

    for disc, (_names, builder) in DISCIPLINES.items():
        bod = builder()
        for section_key, section in bod.sections().items():
            node_id = f"section:{disc}.{section_key}"
            graph.sections[node_id] = SectionInfo(id=node_id, discipline=disc, section=section_key, name=section.name)
            graph.node_labels[node_id] = f"{disc}.{section.name}"
            for interface in section.interfaces:
                target = _resolve_target(interface.with_discipline, section_owner)
                graph.node_labels.setdefault(target.id, target.label or target.discipline or interface.with_discipline)
                graph.edges.append(DependencyEdge(from_section=node_id, to_node=target.id, description=interface.description))

    graph.node_labels.setdefault(f"calc:{GEOTECHNICAL_CALC_KEY}", "Geotechnical (calc, built)")

    return graph


if __name__ == "__main__":
    # python3 -m integration.graph  -- prints the discipline-level Mermaid flowchart.
    g = build_dependency_graph()
    print(g.to_mermaid())
    cycles = g.find_discipline_cycles()
    if cycles:
        print("\nMutually-dependent discipline clusters (not a strict pipeline):")
        for cluster in cycles:
            print(f"  - {', '.join(cluster)}")
