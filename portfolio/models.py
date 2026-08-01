"""
Data model for the project portfolio domain — cost, programme, buildability,
constraints, risk, contacts, and feasibility per project.

ARCHITECTURE STUB: this is the data contract only. No logic yet (no cost
rollups, no risk scoring, no portfolio-level views) — see docs/ROADMAP.md
Milestone 3. Getting the shape of the data right first means the eventual
dashboard, reporting, and any calc-module integration (e.g. attaching a
bearing resistance report to a project's buildability notes) can all be built
against a stable contract rather than shifting sand.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

FeasibilityStatus = Literal["not_started", "in_progress", "feasible", "feasible_with_conditions", "not_feasible"]
RiskLevel = Literal["low", "medium", "high"]
CostStage = Literal["order_of_cost", "cost_plan", "tender", "actual"]
ConstraintCategory = Literal["planning", "access", "ground_conditions", "services", "heritage", "environmental", "other"]


class Contact(BaseModel):
    name: str
    organisation: Optional[str] = None
    role: Optional[str] = Field(None, description="e.g. client, architect, structural engineer, contractor, cost consultant.")
    email: Optional[str] = None
    phone: Optional[str] = None


class CostItem(BaseModel):
    description: str
    estimated_cost_gbp: float = Field(..., ge=0)
    stage: CostStage
    notes: Optional[str] = None


class ProgrammeMilestone(BaseModel):
    name: str
    target_date: Optional[date] = None
    status: Literal["not_started", "in_progress", "complete", "delayed"] = "not_started"


class Constraint(BaseModel):
    description: str
    category: ConstraintCategory
    severity: RiskLevel
    resolved: bool = False


class Risk(BaseModel):
    description: str
    likelihood: RiskLevel
    impact: RiskLevel
    mitigation: Optional[str] = None
    owner: Optional[str] = None
    status: Literal["open", "mitigated", "closed"] = "open"


class BuildabilityNote(BaseModel):
    description: str
    discipline: Optional[str] = Field(None, description="e.g. structural, geotechnical, MEP, civil.")
    severity: RiskLevel
    # Optional link to a calc module's report, once calc <-> portfolio integration exists
    # (see docs/ARCHITECTURE.md) — e.g. "geotech_bearing_resistance_ec7:project-42-footing-3".
    related_calc_reference: Optional[str] = None


class Project(BaseModel):
    reference: str = Field(..., description="Unique project/job reference.")
    name: str
    stage: Optional[str] = Field(None, description="Design stage descriptor — left free-text rather than assuming a specific stage framework.")
    feasibility_status: FeasibilityStatus = "not_started"

    contacts: list[Contact] = Field(default_factory=list)
    costs: list[CostItem] = Field(default_factory=list)
    programme: list[ProgrammeMilestone] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    buildability_notes: list[BuildabilityNote] = Field(default_factory=list)

    notes: Optional[str] = None


class Portfolio(BaseModel):
    projects: list[Project] = Field(default_factory=list)

    def get(self, reference: str) -> Optional[Project]:
        return next((p for p in self.projects if p.reference == reference), None)
