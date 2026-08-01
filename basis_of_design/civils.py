"""
Civils basis of design — the nine elements agreed as the civils scope for a
building-project design role (site conditions, earthworks, foul & surface
water drainage, flood risk, highways/access, external works, utilities
coordination, retaining structures).

*** Verify before real use *** — the applicable-standards lists below are
populated from training knowledge of commonly-cited UK civils references, the
same way the geotechnical module's references were populated (see that
module's docstring for the same caveat). Treat them as a credible starting
checklist to confirm/update against current editions, not a guaranteed-current
authoritative list — that confirmation is exactly the kind of "detail" work
this skeleton is meant to be handed off for.

Design criteria, full interface descriptions, and calculation parameters are
deliberately left mostly empty (or name-only) — this is the architecture pass,
not the detail pass (see docs/ROADMAP.md and the conversation that produced
this module). Populating those is the next step, either directly or by
building the corresponding calcs/civil/ modules referenced by
`calc_module_reference` once they exist.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from basis_of_design.core import BasisOfDesignSection, CalculationRequirement, Interface, Standard
from core.risk import DesignRiskFlag

CIVILS_SECTION_NAMES = [
    "site_and_existing_conditions",
    "earthworks_and_remediation",
    "foul_drainage",
    "surface_water_drainage_suds",
    "flood_risk",
    "highways_and_access",
    "external_works_and_pavements",
    "utilities_coordination",
    "retaining_structures",
]


class CivilsBasisOfDesign(BaseModel):
    project_reference: Optional[str] = Field(None, description="Links to portfolio.models.Project.reference.")

    site_and_existing_conditions: BasisOfDesignSection
    earthworks_and_remediation: BasisOfDesignSection
    foul_drainage: BasisOfDesignSection
    surface_water_drainage_suds: BasisOfDesignSection
    flood_risk: BasisOfDesignSection
    highways_and_access: BasisOfDesignSection
    external_works_and_pavements: BasisOfDesignSection
    utilities_coordination: BasisOfDesignSection
    retaining_structures: BasisOfDesignSection

    def sections(self) -> dict[str, BasisOfDesignSection]:
        return {name: getattr(self, name) for name in CIVILS_SECTION_NAMES}


def build_civils_bod_skeleton(project_reference: Optional[str] = None) -> CivilsBasisOfDesign:
    """
    Returns a structurally complete CivilsBasisOfDesign: every section named,
    scoped, and given a starter list of applicable standards + known
    cross-discipline interfaces. Criteria, assumptions, exclusions, and
    deliverables are left empty — that's the detail to add per project.
    """
    return CivilsBasisOfDesign(
        project_reference=project_reference,
        site_and_existing_conditions=BasisOfDesignSection(
            name="Site and existing conditions",
            scope="Topographic survey, existing levels, boundaries, and existing utility records — the baseline all other civils elements are measured against.",
            interfaces=[
                Interface(with_discipline="geotechnical", description="Existing ground levels needed to establish founding depths and overburden."),
                Interface(with_discipline="architectural", description="Existing levels constrain finished floor levels and external works design."),
            ],
        ),
        earthworks_and_remediation=BasisOfDesignSection(
            name="Earthworks and ground remediation",
            scope="Cut/fill balance, temporary and permanent slope stability, and any ground remediation strategy.",
            standards=[
                Standard(code="BS 6031", title="Code of practice for earthworks"),
                Standard(code="BS EN 1997-1", national_annex="UK NA", notes="Shared with the geotechnical module — slope stability and retaining checks."),
                Standard(code="CIRIA C552", notes="Contaminated land risk assessment / remediation guidance — confirm current CIRIA reference."),
            ],
            interfaces=[
                Interface(with_discipline="geotechnical", description="Ground model (strata, water table) drives cut/fill and slope stability checks — see calcs/geotechnical/."),
                Interface(with_discipline="structural", description="Remediation strategy may affect founding levels/type."),
            ],
            calculations_required=[
                CalculationRequirement(name="Cut/fill balance", description="Earthwork volumes across the site."),
                CalculationRequirement(name="Slope stability check", standard_reference="BS EN 1997-1"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="high",
                    description=(
                        "Temporary excavation slopes and any temporary retaining/support during "
                        "earthworks are a separate design case from the permanent condition — the "
                        "permanent cut/fill and slope stability design does not itself validate that "
                        "the construction-stage excavation is safe."
                    ),
                    trigger="Any earthworks section by nature involves a temporary excavated condition before the permanent profile/remediation is complete.",
                    recommended_action="Temporary works designer/contractor to assess temporary slope stability per BS 6031 against actual ground conditions and construction sequence.",
                    source_reference="basis_of_design.civils:earthworks_and_remediation",
                ),
            ],
        ),
        foul_drainage=BasisOfDesignSection(
            name="Foul drainage",
            scope="Foul water strategy, pipe sizing/capacity, and adoption standards.",
            standards=[
                Standard(code="Sewers for Adoption", notes="Confirm current edition — 7th/8th ed. depending on the servicing water company."),
                Standard(code="BS EN 752", title="Drain and sewer systems outside buildings"),
                Standard(code="Building Regulations Part H", notes="England & Wales — confirm applicability by jurisdiction."),
            ],
            calculations_required=[
                CalculationRequirement(name="Foul flow calculation", description="Peak foul flow from occupancy/use, pipe sizing."),
            ],
        ),
        surface_water_drainage_suds=BasisOfDesignSection(
            name="Surface water drainage / SuDS",
            scope="Attenuation sizing, discharge rate limits, climate change allowances, and SuDS/adoption standards — typically the largest civils calculation deliverable.",
            standards=[
                Standard(code="CIRIA C753", title="The SuDS Manual"),
                Standard(code="Non-statutory technical standards for SuDS", notes="Defra — confirm current status/supersession."),
                Standard(code="Sewers for Adoption", notes="Confirm current edition."),
                Standard(code="BS EN 752"),
            ],
            interfaces=[
                Interface(with_discipline="geotechnical", description="Infiltration rate / ground conditions determine SuDS feasibility (soakaways etc.)."),
                Interface(with_discipline="flood_risk", description="Discharge rate and climate change allowance are usually set by the FRA."),
            ],
            calculations_required=[
                CalculationRequirement(name="Attenuation volume sizing", description="Storage required to limit discharge to the agreed rate."),
                CalculationRequirement(name="Discharge rate calculation", description="Greenfield/brownfield runoff rate per the governing standard."),
            ],
        ),
        flood_risk=BasisOfDesignSection(
            name="Flood risk",
            scope="Flood Risk Assessment (FRA) requirements, finished floor levels, and climate change allowances.",
            standards=[
                Standard(code="NPPF", title="National Planning Policy Framework", notes="Flood risk sequential/exception test provisions."),
                Standard(code="EA climate change allowances guidance", notes="Confirm current published allowances at time of use — these are updated periodically."),
            ],
            interfaces=[
                Interface(with_discipline="architectural", description="Finished floor levels are typically set from FRA outputs."),
                Interface(with_discipline="surface_water_drainage_suds", description="Climate change allowance and discharge rate constraints flow into SuDS sizing."),
            ],
        ),
        highways_and_access=BasisOfDesignSection(
            name="Highways and access",
            scope="Site access geometry, visibility splays, junction design, and adoption standards for any new/altered highway.",
            standards=[
                Standard(code="Manual for Streets", notes="MfS / MfS2 — confirm which applies by road classification/authority."),
                Standard(code="DMRB", title="Design Manual for Roads and Bridges", notes="Where the interface is with a trunk road/strategic network."),
            ],
        ),
        external_works_and_pavements=BasisOfDesignSection(
            name="External works and pavements",
            scope="Hard and soft landscaping, and pavement design/loading for roads, parking, and hardstanding.",
            standards=[
                Standard(code="Manual of Contract Documents for Highway Works (MCHW)", notes="For adoptable road pavement specification."),
                Standard(code="DMRB CD 226", notes="Pavement design — confirm current designation, this series is renumbered periodically."),
            ],
        ),
        utilities_coordination=BasisOfDesignSection(
            name="Utilities coordination",
            scope="Existing service diversions and new utility connections, coordinated with statutory undertakers.",
            standards=[
                Standard(code="HSG47", title="Avoiding Danger from Underground Services", notes="HSE guidance."),
            ],
            interfaces=[
                Interface(with_discipline="mechanical_piping", description="New utility connections (water, gas) interface with mechanical services entering the building."),
                Interface(with_discipline="electrical_lv", description="New electrical supply connections coordinated with the DNO."),
            ],
        ),
        retaining_structures=BasisOfDesignSection(
            name="Retaining structures",
            scope="Design of retaining walls/structures — sits on the civils/structural/geotechnical boundary.",
            standards=[
                Standard(code="BS EN 1997-1", national_annex="UK NA", notes="Shared with the geotechnical module."),
                Standard(code="CIRIA C760", notes="Embedded retaining wall design guidance — confirm current CIRIA reference/edition."),
                Standard(code="BS EN 1992-1-1", national_annex="UK NA", notes="If reinforced concrete — structural interface."),
            ],
            interfaces=[
                Interface(with_discipline="geotechnical", description="Lateral earth pressures and bearing checks — extends calcs/geotechnical/."),
                Interface(with_discipline="structural", description="Structural design of the retaining element itself."),
            ],
            calculations_required=[
                CalculationRequirement(name="Lateral earth pressure calculation", standard_reference="BS EN 1997-1"),
                CalculationRequirement(name="Retaining wall stability (sliding/overturning/bearing)", standard_reference="BS EN 1997-1"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="high",
                    description=(
                        "Retaining structures very commonly require a staged/propped temporary "
                        "condition before the permanent structure (permanent props, slab, or anchors) "
                        "is complete — that temporary condition can be more critical than the "
                        "permanent one, and is easy to overlook if only the finished structure is designed."
                    ),
                    trigger="Retaining wall design typically assumes the completed, fully-propped/anchored condition; intermediate construction stages carry different (often more severe) loading.",
                    recommended_action="Temporary works designer to verify stability at every construction stage, not just the permanent completed condition.",
                    source_reference="basis_of_design.civils:retaining_structures",
                ),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.civils  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_civils_bod_skeleton()
    print(render_basis_of_design("Civils", bod.sections()))
