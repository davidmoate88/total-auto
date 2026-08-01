"""
Tracks, per project, which basis-of-design sections (and the one built
geotechnical calc) are resolved — and derives what's actually unblocked to
work on next from that, using the dependency graph in `integration/graph.py`.

This is deliberately not a persistence layer (see docs/ARCHITECTURE.md "What
deliberately hasn't been built yet") — `ProjectProcessState` is an in-memory
model a caller populates and queries within a session, same as every other
model in this repo. Nothing here auto-resolves anything: an external node
(the DNO's fault level statement, process flow data) only counts as resolved
once something explicitly marks it so, same as a section — the model has no
way to know a real-world input has actually arrived except being told.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from integration.graph import DependencyGraph

ResolutionStatus = Literal["not_started", "in_progress", "resolved"]


class ProjectProcessState(BaseModel):
    project_reference: Optional[str] = None
    statuses: dict[str, ResolutionStatus] = Field(default_factory=dict)

    def status_of(self, node_id: str) -> ResolutionStatus:
        return self.statuses.get(node_id, "not_started")

    def set_status(self, node_id: str, status: ResolutionStatus) -> None:
        self.statuses[node_id] = status


class BlockedSection(BaseModel):
    section_id: str
    unresolved_upstream: list[str]


def unblocked_sections(graph: DependencyGraph, state: ProjectProcessState) -> list[str]:
    """
    Sections not yet resolved, where every upstream node IS resolved — i.e.
    what can actually be worked on right now. A section with no upstream
    dependencies at all (23 of the 44 built so far) is always unblocked.
    """
    result = []
    for section_id in graph.sections:
        if state.status_of(section_id) == "resolved":
            continue
        upstream = graph.upstream_of(section_id)
        if all(state.status_of(u) == "resolved" for u in upstream):
            result.append(section_id)
    return sorted(result)


def blocked_sections(graph: DependencyGraph, state: ProjectProcessState) -> list[BlockedSection]:
    """The complement of unblocked_sections() — what's stuck, and specifically on what."""
    result = []
    for section_id in graph.sections:
        if state.status_of(section_id) == "resolved":
            continue
        unresolved = [u for u in graph.upstream_of(section_id) if state.status_of(u) != "resolved"]
        if unresolved:
            result.append(BlockedSection(section_id=section_id, unresolved_upstream=unresolved))
    return sorted(result, key=lambda b: b.section_id)


def progress_summary(graph: DependencyGraph, state: ProjectProcessState) -> dict[str, dict[str, int]]:
    """Section count by status, grouped by discipline — a quick 'where are we' view."""
    summary: dict[str, dict[str, int]] = {}
    for section_id, info in graph.sections.items():
        status = state.status_of(section_id)
        bucket = summary.setdefault(info.discipline, {"not_started": 0, "in_progress": 0, "resolved": 0})
        bucket[status] += 1
    return summary
