"""
Shared shape for a "basis of design" (BoD) — the document that states what
standards, criteria, and assumptions a discipline's design and calculations
are working to. Every discipline (civils, structural, LV/HV electrical,
mechanical piping) gets its own BoD model built from these same building
blocks, so the pattern only needs designing once.

A BoD is organised into named *sections* (e.g. civils' "surface water
drainage" or structural's "primary steel frame") — each section carries the
same seven things:

    scope           what this section covers and explicitly does not
    standards       applicable codes/standards (with National Annex where relevant)
    criteria        the actual design parameters/numbers
    assumptions     what was relied on that isn't independently verified here
    exclusions      explicitly out of scope
    interfaces      what this section needs from / gives to other disciplines
    calculations    the calc checks required to substantiate the design
    deliverables    what comes out the other end (drawings, schedules, reports)

This module defines the shape only. Discipline modules (`civils.py`, and
later `structural.py`, `electrical_lv.py`, `electrical_hv.py`,
`mechanical_piping.py`) define which sections exist for that discipline and
provide a skeleton-builder function that returns a structurally complete but
content-light instance — the "architecture, not the detail" for now, per
docs/ROADMAP.md.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from core.risk import DesignRiskFlag


class Standard(BaseModel):
    code: str = Field(..., description="e.g. 'BS EN 1997-1', 'CIRIA C753'.")
    title: Optional[str] = None
    national_annex: Optional[str] = Field(None, description="e.g. 'UK NA' — omit if not code-specific.")
    notes: Optional[str] = None


class DesignCriterion(BaseModel):
    name: str
    value: Optional[str] = Field(None, description="Left as a string to accommodate ranges/qualitative values as well as numbers.")
    unit: Optional[str] = None
    notes: Optional[str] = None


class Assumption(BaseModel):
    description: str
    notes: Optional[str] = None


class Interface(BaseModel):
    with_discipline: str = Field(..., description="e.g. 'geotechnical', 'structural'.")
    description: str = Field(..., description="What this section needs from, or gives to, that discipline.")


class CalculationRequirement(BaseModel):
    name: str
    description: Optional[str] = None
    standard_reference: Optional[str] = Field(None, description="Which Standard (by code) this calc must satisfy.")
    calc_module_reference: Optional[str] = Field(
        None, description="Key of the calcs/ module that performs this, once it exists (e.g. 'geotech_bearing_resistance_ec7')."
    )


class Deliverable(BaseModel):
    name: str
    format: Optional[str] = Field(None, description="e.g. 'drawing', 'schedule', 'calculation report'.")
    description: Optional[str] = None


class BasisOfDesignSection(BaseModel):
    """One element of a discipline's basis of design (e.g. civils' 'earthworks')."""

    name: str
    scope: Optional[str] = None
    standards: list[Standard] = Field(default_factory=list)
    criteria: list[DesignCriterion] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    interfaces: list[Interface] = Field(default_factory=list)
    calculations_required: list[CalculationRequirement] = Field(default_factory=list)
    deliverables: list[Deliverable] = Field(default_factory=list)
    risk_flags: list[DesignRiskFlag] = Field(
        default_factory=list,
        description="Structured risk flags for this section (see core/risk.py) — e.g. where this "
        "element's permanent design implies a distinct, riskier temporary/construction-stage condition.",
    )

    def is_populated(self) -> bool:
        """True once any content beyond the bare scope/name has been added — used to
        distinguish a still-skeleton section from one that's actually been worked up."""
        return any([self.standards, self.criteria, self.assumptions, self.exclusions, self.interfaces, self.calculations_required, self.deliverables, self.risk_flags])
