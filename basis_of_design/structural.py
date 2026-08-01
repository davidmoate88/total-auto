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
environment. Confirm current editions/designations before real use. The same
caveat applies to the criteria values added in the detail pass below (loading
figures, geometry limits, deflection limits, etc.) — these are illustrative
values drawn from common UK industrial practice, not confirmed project- or
client-specific figures, and every one should be checked against the actual
project brief and current standard text before being relied on.

This is the detail pass (2nd pass) on top of the architecture-pass skeleton:
criteria, assumptions, exclusions, and deliverables are now populated per
section. Calculation logic itself (the corresponding `calcs/structural/`
modules) is not yet built — `calculations_required` entries name what's
needed but `calc_module_reference` stays unset until those modules exist.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from basis_of_design.core import (
    Assumption,
    BasisOfDesignSection,
    CalculationRequirement,
    Deliverable,
    DesignCriterion,
    Interface,
    Standard,
)
from core.risk import DesignRiskFlag

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
    steelwork (platforms/walkways/stairs/ladders/handrails), with design
    criteria, assumptions, exclusions, and deliverables populated per section.
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
            criteria=[
                DesignCriterion(name="Design working life", value="25", unit="years", notes="Typical for industrial access/plant structures (BS EN 1990 shorter design life category) — confirm the client/insurer-required figure; occupied buildings would normally use 50."),
                DesignCriterion(name="Consequence class", value="CC2 (BS EN 1990 Annex B)", notes="Typical for industrial access structures with limited occupancy — confirm against the specific structure's failure consequences."),
                DesignCriterion(name="Imposed load category", value="Category E (storage/industrial)", notes="BS EN 1991-1-1 imposed load category — confirm against actual platform use (access/maintenance only vs. storage)."),
            ],
            assumptions=[
                Assumption(description="The structure is treated as a 'non-building structure' for BS EN 1990 consequence-class purposes unless a client/insurer requirement says otherwise."),
                Assumption(description="Post-Brexit UK marking regime is assumed to be UKCA under the Supply of Machinery (Safety) Regulations 2008, unless the project also requires CE marking for an export/EU market."),
            ],
            exclusions=[
                "Multi-storey/occupied-building structural design (floor vibration, lateral sway, roof structure, fire engineering) — parked, see docs/ROADMAP.md.",
                "Seismic design — not typically governing for UK sites; excluded unless the specific site/client requires it.",
            ],
            deliverables=[
                Deliverable(name="Design basis statement", format="report"),
                Deliverable(name="General arrangement drawing suite", format="drawing"),
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
            criteria=[
                DesignCriterion(name="Minimum founding depth", value="to be confirmed from ground model", notes="Set from calcs/geotechnical/ characteristic parameters and frost depth once the ground model exists for the site."),
                DesignCriterion(name="Base plate bearing pressure limit", value="to be confirmed", unit="N/mm²", notes="Governed by the concrete/grout bearing capacity beneath the base plate, not the steel design itself."),
            ],
            assumptions=[
                Assumption(description="Ground conditions are assumed per calcs/geotechnical/ characteristic parameters until a site-specific investigation confirms them at each foundation location."),
                Assumption(description="Isolated pad/strip foundations are assumed adequate; piling is not anticipated unless the ground model or loading indicates otherwise."),
            ],
            exclusions=[
                "Piled foundation design — only introduced if pad/strip foundations prove inadequate; not designed by default.",
            ],
            deliverables=[
                Deliverable(name="Foundation/base plate general arrangement drawing", format="drawing"),
                Deliverable(name="Foundation design calculation report", format="calculation report"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="medium",
                    description=(
                        "Foundation excavation for platform/walkway supports may require temporary "
                        "excavation support depending on depth and ground conditions — not assessed "
                        "by the permanent foundation/base plate design itself."
                    ),
                    trigger="Any foundation involves an excavated construction stage distinct from the permanent buried condition.",
                    recommended_action="Confirm excavation depth against the geotechnical ground model (calcs/geotechnical/) and safe unsupported-excavation guidance; involve a temporary works designer if in doubt.",
                    source_reference="basis_of_design.structural:substructure_and_foundations",
                ),
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
            criteria=[
                DesignCriterion(name="Vertical deflection limit (platforms)", value="span/200", notes="Typical serviceability limit for industrial access platforms — confirm against project-specific serviceability requirements."),
                DesignCriterion(name="Steel grade", value="S355", notes="Typical structural steel grade for this application — confirm availability/preference with the fabricator."),
                DesignCriterion(name="Wind loading basis", value="to be confirmed from BS EN 1991-1-4 site parameters", notes="Standard UK inland site assumed as a default; coastal/exposed/high-altitude sites require a site-specific wind assessment."),
            ],
            assumptions=[
                Assumption(description="Wind loading is assumed derivable from standard UK terrain/altitude parameters; a site-specific wind assessment is assumed only necessary for coastal/exposed/high-altitude sites."),
            ],
            exclusions=[
                "Seismic design of the primary frame — see design_standards_and_criteria exclusions.",
            ],
            deliverables=[
                Deliverable(name="Steelwork general arrangement drawing", format="drawing"),
                Deliverable(name="Member/connection design calculation report", format="calculation report"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="high",
                    description=(
                        "The frame design assumes the complete, fully-connected, fully-braced "
                        "structure — intermediate erection stages (before all bracing/connections "
                        "are made) are not automatically stable and are a distinct design case."
                    ),
                    trigger="Steelwork is erected member-by-member; the design's stability assumptions only hold once erection is complete.",
                    recommended_action="Temporary works designer/erection contractor to verify stability at each erection stage (see temporary_works section) — do not assume the permanent design covers construction-stage stability.",
                    source_reference="basis_of_design.structural:primary_steel_frame",
                ),
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
            criteria=[
                DesignCriterion(name="Minimum clear walkway width", value="600", unit="mm", notes="BS EN ISO 14122-2 minimum for a walkway — confirm exact figure and whether a wider width applies for maintenance access/escape route requirements."),
                DesignCriterion(name="Uniformly distributed load", value="5.0", unit="kN/m²", notes="Typical industrial platform/walkway loading — confirm against actual use (access/maintenance only vs. laydown/storage)."),
                DesignCriterion(name="Concentrated (point) load", value="1.5", unit="kN", notes="Typical minimum concentrated load check on decking/grating, applied over a nominal contact area — confirm against BS 4592/project spec."),
            ],
            assumptions=[
                Assumption(description="Platform/walkway use is classified as pedestrian access and maintenance only, not material storage or laydown, unless stated otherwise for a specific platform."),
            ],
            exclusions=[
                "Fork-lift truck or other vehicle loading — not included unless a specific platform is explicitly required to carry it.",
            ],
            deliverables=[
                Deliverable(name="Platform/walkway general arrangement drawing", format="drawing"),
                Deliverable(name="Deck/grating specification schedule", format="schedule"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="safety",
                    severity="high",
                    description=(
                        "Working at height before permanent fall protection (handrails/guard-rails) is "
                        "installed is a distinct installation-sequence safety risk, separate from the "
                        "completed platform's design."
                    ),
                    trigger="Decking/grating is typically installed before its permanent guard-rails are fitted.",
                    recommended_action="Define temporary edge protection or fall-arrest requirements for the installation sequence, coordinated with the handrails_and_guardrails section.",
                    source_reference="basis_of_design.structural:platforms_and_walkways",
                ),
            ],
        ),
        stairs_and_ladders=BasisOfDesignSection(
            name="Stairs and ladders",
            scope="Geometry (pitch, rise/going) and loading for stairs, stepladders, and fixed ladders providing access.",
            standards=[
                Standard(code="BS EN ISO 14122-3", title="Stairs, stepladders and guard-rails"),
                Standard(code="BS EN ISO 14122-4", title="Fixed ladders"),
            ],
            criteria=[
                DesignCriterion(name="Stair pitch (preferred range)", value="30–38°", notes="Typical permissible range for industrial stairs per BS EN ISO 14122-3 — confirm exact limits and any steeper-pitch/stepladder allowance."),
                DesignCriterion(name="Fixed ladder pitch", value="75–90°", notes="BS EN ISO 14122-4 range for a fixed ladder (as opposed to a stepladder or stair) — confirm exact boundary values."),
                DesignCriterion(name="Minimum clear stair/ladder width", value="600", unit="mm", notes="Confirm exact figure per part and any escape-route width uplift."),
            ],
            assumptions=[
                Assumption(description="Stairs are used in preference to ladders wherever headroom/space allows, following the EN ISO 14122 access-equipment hierarchy (platforms > stairs > stepladders > fixed ladders)."),
            ],
            exclusions=[
                "Powered/mobile access equipment (mobile elevated work platforms, scaffold towers) — not part of a fixed access structure design.",
            ],
            deliverables=[
                Deliverable(name="Stair/ladder general arrangement drawing", format="drawing"),
                Deliverable(name="Stair/ladder calculation report", format="calculation report"),
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
            criteria=[
                DesignCriterion(name="Guard-rail top height", value="1100", unit="mm", notes="Minimum per BS EN ISO 14122-3 — confirm exact figure and any higher requirement from a client standard."),
                DesignCriterion(name="Guard-rail horizontal design load", value="0.3–1.0", unit="kN/m", notes="Range depends on classification/exposure per BS EN ISO 14122-3 — confirm the governing value for the specific installation."),
                DesignCriterion(name="Maximum gap (mid-rail/toe-board)", value="500", unit="mm", notes="Typical maximum unprotected gap — confirm exact figure, including toe-board height requirement."),
            ],
            assumptions=[
                Assumption(description="Guard-rails/handrails are assumed required on all open edges with a fall height above the generic UK work-at-height threshold (typically 2m, but risk-assessed case by case)."),
            ],
            exclusions=[
                "Glazed or solid balustrade panel systems (an architectural feature) — this section covers open guard-rail/handrail systems only.",
            ],
            deliverables=[
                Deliverable(name="Handrail/guard-rail general arrangement drawing", format="drawing"),
                Deliverable(name="Handrail/guard-rail load calculation", format="calculation report"),
            ],
        ),
        structural_integrity_and_robustness=BasisOfDesignSection(
            name="Structural integrity and robustness",
            scope="Robustness considerations scaled to access-structure risk (connection redundancy, corrosion allowance) — not full building disproportionate-collapse design.",
            standards=[
                Standard(code="BS EN 1991-1-7", national_annex="UK NA", notes="Accidental actions — apply only the parts relevant to an access structure, not full building consequence-class robustness."),
            ],
            criteria=[
                DesignCriterion(name="Notional horizontal load", value="1%", notes="Of vertical load, applied per BS EN 1993-1-1 robustness/imperfection provisions, as a minimum horizontal robustness check — confirm applicability."),
            ],
            assumptions=[
                Assumption(description="Full building-scale disproportionate-collapse provisions (BS EN 1991-1-7 building consequence classes) are assumed not applicable, given the structure's industrial access use and limited occupancy."),
            ],
            exclusions=[
                "Progressive collapse / disproportionate collapse analysis for occupied buildings — out of scope, see design_standards_and_criteria exclusions.",
            ],
            deliverables=[
                Deliverable(name="Robustness statement", format="report"),
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
            criteria=[
                DesignCriterion(name="Permissible unbraced erection stage duration", value="to be confirmed by contractor", notes="Not a fixed design value — the erection contractor sets this once the erection method statement is developed, informed by the performance requirements in this section."),
            ],
            assumptions=[
                Assumption(description="The erection contractor is assumed to hold appropriate temporary works coordination competency (per BS 5975) and to develop the detailed temporary works design themselves."),
            ],
            exclusions=[
                "Detailed temporary works design itself (falsework calculations, propping schemes, etc.) — the contractor's design responsibility, not produced as part of this basis of design.",
            ],
            deliverables=[
                Deliverable(name="Temporary works performance requirements schedule", format="schedule", description="Handed to the erection contractor as the basis for their own temporary works design."),
            ],
        ),
        movement_tolerances_and_durability=BasisOfDesignSection(
            name="Movement, tolerances, and durability",
            scope="Thermal movement/expansion joints for long walkway runs, construction tolerances, and corrosion protection.",
            standards=[
                Standard(code="BS EN ISO 1461", title="Hot dip galvanized coatings on iron and steel articles"),
                Standard(code="BS EN 1993-1-1", national_annex="UK NA", notes="Corrosion/durability provisions within the general steel design rules."),
                Standard(code="BS EN 1090-2", title="Execution of steel structures — technical requirements", notes="Governs fabrication/erection tolerances — confirm execution class (EXC1–EXC4) for this structure."),
                Standard(code="BS EN ISO 12944", title="Corrosion protection of steel structures by protective paint systems", notes="Reference only if a paint system is used instead of/alongside galvanizing."),
            ],
            criteria=[
                DesignCriterion(name="Expansion joint spacing (long walkway runs)", value="30–40", unit="m", notes="Typical spacing subject to a thermal movement calculation — confirm against the actual run length and ambient temperature range for the site."),
                DesignCriterion(name="Galvanizing minimum coating thickness", value="85", unit="microns", notes="Typical minimum per BS EN ISO 1461 for steel over 6mm thick — confirm against actual section thicknesses used."),
                DesignCriterion(name="Corrosivity environment category", value="C3 (indoor/covered industrial)", notes="Per BS EN ISO 12944 — confirm category per site; external/coastal sites typically require C4/C5."),
            ],
            assumptions=[
                Assumption(description="Hot-dip galvanizing to BS EN ISO 1461 is assumed as the default corrosion protection system, rather than a painted/duplex system, unless the project specifies otherwise."),
            ],
            exclusions=[
                "Painted or duplex (paint-over-galvanizing) coating systems — not included by default; only introduced if specifically required (e.g. for colour-coding or a more aggressive environment).",
            ],
            deliverables=[
                Deliverable(name="Corrosion protection specification", format="specification"),
                Deliverable(name="Movement joint detail drawing", format="drawing"),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.structural  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_structural_bod_skeleton()
    print(render_basis_of_design("Structural", bod.sections()))
