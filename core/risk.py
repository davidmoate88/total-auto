"""
Shared risk-flagging shape used across calc modules and basis-of-design
sections, so "does this design carry something worth a second look" is
answered the same way everywhere, rather than as ad-hoc free-text warnings
that can't be filtered, counted, or prioritised.

Distinct from `portfolio.models.Risk`: that's a project-level risk register
entry (likelihood/impact/mitigation/owner/status, tracked over time by a
person). A `DesignRiskFlag` is raised automatically by a specific calculation
or basis-of-design section at the point the content is generated — it's the
"a person should look at this" signal, not a tracked register item. The
intended workflow (not yet wired up — see docs/ARCHITECTURE.md) is that a
reviewer looks at the flags a project has accumulated across its calcs/BoDs
and promotes the ones that matter into that project's portfolio.models.Risk
register, same as `BuildabilityNote.related_calc_reference` links a
buildability note back to the calculation that backs it up.

`temporary_works` is a first-class category rather than left to the "other"
bucket, because it's a specific, common failure mode: a design gets fully
worked up for its permanent, completed condition, and the construction-stage
condition — which is often more onerous (an unpropped excavation, a retaining
wall before its permanent props/anchors are in, steelwork before its bracing
is complete) — never gets a second look unless something forces it.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

RiskSeverity = Literal["low", "medium", "high", "critical"]

RiskCategory = Literal[
    "temporary_works",
    "buildability",
    "interface",
    "assumption_sensitivity",
    "code_compliance",
    "ground_conditions",
    "safety",
    "other",
]


class DesignRiskFlag(BaseModel):
    category: RiskCategory
    severity: RiskSeverity
    description: str
    trigger: Optional[str] = Field(None, description="What in the design/input caused this flag to be raised.")
    recommended_action: Optional[str] = None
    source_reference: Optional[str] = Field(
        None, description="Where this came from — e.g. a calc module key or basis-of-design section name."
    )
