"""
Structural basis of design — scoped, per direction, to **industrial access
steelwork**: platforms, walkways, stairs, ladders, and handrails/guard-rails,
plus the steel frame supporting them. Multi-storey/occupied-building structural
elements (floor vibration for building floors, lateral stability/sway for tall
structures, roof structure, fire engineering interface) are deliberately parked
for now, not deleted — see docs/ROADMAP.md.

This scope sits across two standard families simultaneously, which is the
main thing that makes it different from a typical building structural BoD:
the structural Eurocodes (EN 1990/1991/1993) govern the steelwork design
itself, while the machinery/access safety standards (principally the
EN ISO 14122 series, sitting under the Machinery Directive / UK Supply of
Machinery (Safety) Regulations) govern the geometry and safety requirements
of the access equipment itself (platform/walkway dimensions, stair pitch,
guard-rail heights and loads, ladder rungs, etc.).

*** Verify before real use *** — same caveat as `civils.py` and the
geotechnical module: the standards listed below (particularly the exact
EN ISO 14122 part numbers and their scope, and the current UK machinery
regulations designation post-Brexit — CE vs UKCA marking) are populated from
training knowledge, not verified against the current standard texts in this
environment. Confirm current editions/designations before real use.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from basis_of_design.core import BasisOfDesignSection, CalculationRequirement, Interface, Standard

STRUCTURAL_SECTION_NAMES = [
    "design_standards_and_criteria",
    "substructure_and_foundations",
    "primary_steel_frame",
    "platforms_and_walkways",
    "stairs_and_ladders",
    "handrails_and_guardrails",
    "structural_integrity_and_robustness",
    "temporary_works",
    "movement_tolerances_and_durability",
]


class StructuralBasisOfDesign(BaseModel):
    project_reference: Optional[str] = Field(None, description="Links to portfolio.models.Project.reference.")

    design_standards_and_criteria: BasisOfDesignSection
    substructure_and_foundations: BasisOfDesignSection
    primary_steel_frame: BasisOfDesignSection
    platforms_and_walkways: BasisOfDesignSection
    stairs_and_ladders: BasisOfDesignSection
    handrails_and_guardrails: BasisOfDesignSection
    structural_integrity_and_robustness: BasisOfDesignSection
    temporary_works: BasisOfDesignSection
    movement_tolerances_and_durability: BasisOfDesignSection

    def sections(self) -> dict[str, BasisOfDesignSection]:
        return {name: getattr(self, name) for name in STRUCTURAL_SECTION_NAMES}


def build_structural_bod_skeleton(project_reference: Optional[str] = None) -> StructuralBasisOfDesign:
    """
    Structurally complete StructuralBasisOfDesign, scoped to industrial access
    steelwork (platforms/walkways/stairs/ladders/handrails). Criteria,
    assumptions, exclusions, and deliverables left empty for the detail pass.
    """
    return StructuralBasisOfDesign(
        project_reference=project_reference,
        design_standards_and_criteria=BasisOfDesignSection(
            name="Design standards and general criteria",
            scope=(
                "Overarching design basis for industrial access steelwork (platforms, walkways, stairs, "
                "ladders, handrails) and its supporting frame. Multi-storey/occupied-building structural "
                "elements (floor vibration for building floors, lateral stability/sway, roof structure, "
                "fire engineering) are out of scope for now per project direction — parked, not deleted."
            ),
            standards=[
                Standard(code="BS EN 1990", national_annex="UK NA", title="Basis of structural design"),
                Standard(code="BS EN 1991-1-1", national_annex="UK NA", title="Actions on structures — densities, self-weight, imposed loads"),
                Standard(code="BS EN 1993-1-1", national_annex="UK NA", title="Design of steel structures — general rules"),
                Standard(code="Machinery Directive 2006/42/EC", notes="EU — confirm UK equivalent designation/status (Supply of Machinery (Safety) Regulations 2008, and current CE/UKCA marking requirement)."),
                Standard(code="BS EN ISO 12100", title="Safety of machinery — general principles for risk assessment and risk reduction"),
            ],
            exclusions=[
                "Multi-storey/occupied-building structural design (floor vibration, lateral sway, roof structure, fire engineering) — parked, see docs/ROADMAP.md.",
            ],
        ),
        substructure_and_foundations=BasisOfDesignSection(
            name="Substructure and foundations",
            scope="Foundations and base connections (base plates, holding-down bolts) supporting platform/walkway steelwork.",
            standards=[
                Standard(code="BS EN 1997-1", national_annex="UK NA", notes="Shared with the geotechnical module."),
                Standard(code="BS EN 1993-1-8", national_annex="UK NA", title="Design of joints — base plate/holding-down bolt design."),
            ],
            interfaces=[
                Interface(with_discipline="geotechnical", description="Bearing resistance for platform/walkway support foundations — see calcs/geotechnical/."),
            ],
            calculations_required=[
                CalculationRequirement(name="Base plate / holding-down bolt design", standard_reference="BS EN 1993-1-8"),
            ],
        ),
        primary_steel_frame=BasisOfDesignSection(
            name="Primary steel frame",
            scope="Supporting steelwork (beams, columns, bracing) for platforms and walkways.",
            standards=[
                Standard(code="BS EN 1993-1-1", national_annex="UK NA", title="General rules and rules for buildings"),
                Standard(code="BS EN 1993-1-8", national_annex="UK NA", title="Design of joints"),
            ],
            calculations_required=[
                CalculationRequirement(name="Beam/column member capacity checks", standard_reference="BS EN 1993-1-1"),
                CalculationRequirement(name="Connection design", standard_reference="BS EN 1993-1-8"),
            ],
        ),
        platforms_and_walkways=BasisOfDesignSection(
            name="Platforms and walkways",
            scope="Decking/flooring specification and loading for working platforms and walkways.",
            standards=[
                Standard(code="BS EN ISO 14122-2", title="Safety of machinery — permanent means of access — working platforms and walkways"),
                Standard(code="BS EN 1991-1-1", national_annex="UK NA", notes="Imposed load requirements for platforms/walkways."),
                Standard(code="BS 4592", notes="Industrial type flooring, walkways and stair treads (grating/chequer plate specification) — confirm current part/edition."),
            ],
            calculations_required=[
                CalculationRequirement(name="Deck/grating loading and deflection check", standard_reference="BS EN 1991-1-1"),
            ],
        ),
        stairs_and_ladders=BasisOfDesignSection(
            name="Stairs and ladders",
            scope="Geometry (pitch, rise/going) and loading for stairs, stepladders, and fixed ladders providing access.",
            standards=[
                Standard(code="BS EN ISO 14122-3", title="Stairs, stepladders and guard-rails"),
                Standard(code="BS EN ISO 14122-4", title="Fixed ladders"),
            ],
        ),
        handrails_and_guardrails=BasisOfDesignSection(
            name="Handrails and guard-rails",
            scope="Guard-rail/handrail height, loading, gap limits, and toe-boards for platforms, walkways, and stairs.",
            standards=[
                Standard(code="BS EN ISO 14122-3", notes="Guard-rail requirements — shared with the stairs/ladders section."),
                Standard(code="BS 6180", notes="Barriers in and about buildings — may apply instead of/alongside EN ISO 14122-3 depending on building-vs-machinery classification; confirm which governs per installation."),
            ],
            calculations_required=[
                CalculationRequirement(name="Guard-rail horizontal load check", standard_reference="BS EN ISO 14122-3"),
            ],
        ),
        structural_integrity_and_robustness=BasisOfDesignSection(
            name="Structural integrity and robustness",
            scope="Robustness considerations scaled to access-structure risk (connection redundancy, corrosion allowance) — not full building disproportionate-collapse design.",
            standards=[
                Standard(code="BS EN 1991-1-7", national_annex="UK NA", notes="Accidental actions — apply only the parts relevant to an access structure, not full building consequence-class robustness."),
            ],
        ),
        temporary_works=BasisOfDesignSection(
            name="Temporary works",
            scope="Erection/lifting sequence and temporary stability requirements during construction — typically contractor-designed, with performance requirements set here.",
            standards=[
                Standard(code="BS 5975", title="Code of practice for temporary works procedures and the permissible stress design of falsework"),
            ],
            interfaces=[
                Interface(with_discipline="contractor / temporary works designer", description="This section states performance requirements; detailed temporary works design is typically the contractor's responsibility."),
            ],
        ),
        movement_tolerances_and_durability=BasisOfDesignSection(
            name="Movement, tolerances, and durability",
            scope="Thermal movement/expansion joints for long walkway runs, construction tolerances, and corrosion protection.",
            standards=[
                Standard(code="BS EN ISO 1461", title="Hot dip galvanized coatings on iron and steel articles"),
                Standard(code="BS EN 1993-1-1", national_annex="UK NA", notes="Corrosion/durability provisions within the general steel design rules."),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.structural  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_structural_bod_skeleton()
    print(render_basis_of_design("Structural", bod.sections()))
