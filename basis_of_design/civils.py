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
this skeleton is meant to be handed off for. The same caveat applies to the
criteria values below (accuracy tolerances, freeboard allowances, design life
figures, etc.): these are typical/illustrative starting values drawn from
common UK practice, not confirmed project- or client-specific figures — every
one should be checked against the actual project brief, local authority/water
company requirements, and current guidance before being relied on.

This is the detail pass (2nd pass) on top of the architecture-pass skeleton:
criteria, assumptions, exclusions, and deliverables are now populated per
section. Calculation logic itself (the corresponding `calcs/civil/` modules)
is not yet built — `calculations_required` entries name what's needed but
`calc_module_reference` stays unset until those modules exist.
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
    scoped, and given a starter list of applicable standards, known
    cross-discipline interfaces, illustrative design criteria, working
    assumptions, exclusions, and deliverables. All of this is a starting point
    to confirm/refine per project — see the module docstring caveat.
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
            criteria=[
                DesignCriterion(name="Survey vertical accuracy", value="±10", unit="mm", notes="Typical topographic survey tolerance — confirm against the project survey brief."),
                DesignCriterion(name="Survey horizontal accuracy", value="±20", unit="mm"),
                DesignCriterion(name="Survey datum", value="Ordnance Survey Newlyn Datum (OSGB36)", notes="Confirm project datum — some sites use a local site grid instead."),
                DesignCriterion(name="Utility survey quality level", value="PAS 128 Quality Level B/A", notes="Target verification level for buried service records before detailed design proceeds."),
            ],
            assumptions=[
                Assumption(description="Existing statutory undertaker utility records are indicative only until verified by trial holes/GPR survey (PAS 128)."),
                Assumption(description="No presumption of undiscovered services is made until a PAS 128 survey is complete."),
            ],
            exclusions=[
                "Detailed measured building survey of existing structures — assumed covered by the architectural/structural survey scope.",
            ],
            deliverables=[
                Deliverable(name="Topographic survey drawing", format="drawing"),
                Deliverable(name="Existing utility record drawing", format="drawing", description="Composite of all statutory undertaker records obtained."),
                Deliverable(name="Site boundary / red line plan", format="drawing"),
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
                CalculationRequirement(
                    name="Cut/fill balance", description="Earthwork volumes across the site.",
                    calc_module_reference="civil_cut_fill_balance",
                ),
                CalculationRequirement(name="Slope stability check", standard_reference="BS EN 1997-1"),
            ],
            criteria=[
                DesignCriterion(name="Permanent slope angle", value="to be confirmed from ground model", notes="Set per BS 6031 once characteristic ground parameters are available from calcs/geotechnical/."),
                DesignCriterion(name="Cut/fill tolerance", value="±0", unit="m³", notes="Target a balanced cut/fill unless import/export is explicitly agreed — reduces haulage cost/risk."),
                DesignCriterion(name="Contamination screening trigger", value="Phase 1 desk study", notes="Threshold for commissioning a Phase 2 intrusive investigation, per CLR11-style guidance."),
            ],
            assumptions=[
                Assumption(description="Site-won material is assumed suitable for reuse as engineered fill, subject to geotechnical testing confirming it."),
                Assumption(description="No contamination is assumed present unless a Phase 1 desk study identifies a plausible source-pathway-receptor linkage."),
            ],
            exclusions=[
                "Detailed remediation design/validation (specialist remediation contractor scope) — this section covers strategy only, not detailed remediation engineering.",
            ],
            deliverables=[
                Deliverable(name="Earthworks specification", format="specification"),
                Deliverable(name="Cut/fill volume schedule", format="schedule"),
                Deliverable(name="Remediation strategy report", format="report", description="Only where contamination risk is identified."),
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
                CalculationRequirement(
                    name="Foul flow calculation", description="Peak foul flow from occupancy/use, pipe sizing.",
                    calc_module_reference="civil_foul_drainage_flow",
                    standard_reference="Sewers for Adoption",
                ),
            ],
            criteria=[
                DesignCriterion(name="Minimum self-cleansing velocity", value="0.75", unit="m/s", notes="Typical Sewers for Adoption / Building Regs criterion at design flow."),
                DesignCriterion(name="Minimum cover depth (adoptable)", value="1.2", unit="m", notes="Typical under highway — confirm against the specific water company's design/construction guidance."),
                DesignCriterion(name="Minimum pipe gradient", value="1:80 (150mm dia.)", notes="Illustrative — actual minimum gradient is diameter-dependent per the governing standard."),
            ],
            assumptions=[
                Assumption(description="Foul flow rates are based on occupancy/use rates per BS EN 752 / Sewers for Adoption guidance, to be confirmed once an occupancy schedule is available."),
                Assumption(description="Connection to the existing public foul sewer is assumed available at adequate capacity — to be confirmed by a sewer capacity check/pre-development enquiry with the water company."),
            ],
            exclusions=[
                "Trade effluent pre-treatment design — specialist scope, only required if a trade effluent consent is triggered.",
            ],
            deliverables=[
                Deliverable(name="Foul drainage layout drawing", format="drawing"),
                Deliverable(name="Foul drainage calculation report", format="calculation report"),
                Deliverable(name="Sewer adoption submission pack", format="report", description="Only where the network is to be offered for adoption (S104 or equivalent)."),
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
            criteria=[
                DesignCriterion(name="Discharge rate", value="Greenfield QBAR (or local authority/LLFA-specified rate)", notes="Confirm the governing rate with the Lead Local Flood Authority — some set a fixed litres/second/hectare cap instead."),
                DesignCriterion(name="Climate change allowance", value="to be confirmed against current EA guidance", notes="These published allowances are updated periodically — do not hard-code a percentage without checking the current figure."),
                DesignCriterion(name="Design storm return period (attenuation)", value="1 in 100 year + climate change", notes="With a 1 in 30 year check for surcharge-free performance, per common SuDS practice."),
                DesignCriterion(name="SuDS management train priority", value="Infiltration > attenuation/detention > controlled discharge", notes="Per the CIRIA C753 SuDS hierarchy — confirm feasibility of each tier before committing to the next."),
            ],
            assumptions=[
                Assumption(description="Infiltration testing (BRE Digest 365 falling-head test) is assumed required to confirm SuDS feasibility, pending the ground model."),
                Assumption(description="Existing surface water sewer/watercourse is assumed to have available capacity for any residual controlled discharge, pending confirmation."),
            ],
            exclusions=[
                "Long-term SuDS maintenance/adoption legal agreement drafting — a legal, not engineering, deliverable (the maintenance schedule itself is still produced, see deliverables).",
            ],
            deliverables=[
                Deliverable(name="Drainage strategy report", format="report"),
                Deliverable(name="Attenuation sizing calculation", format="calculation report"),
                Deliverable(name="SuDS maintenance schedule", format="schedule"),
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
            criteria=[
                DesignCriterion(name="Finished floor level freeboard", value="300", unit="mm", notes="Typical minimum above the design flood level (1 in 100 year + climate change) — confirm against the LLFA/EA's specific requirement for the site."),
                DesignCriterion(name="Flood zone classification", value="to be confirmed from the current EA flood map", notes="Drives whether a full FRA and sequential/exception test are required at all."),
            ],
            assumptions=[
                Assumption(description="The site is provisionally assumed Flood Zone 1 (low probability) pending confirmation from the current EA flood map for planning."),
            ],
            exclusions=[
                "Detailed hydraulic/hydrological modelling of adjacent watercourses — specialist flood consultant scope, only required if the site interacts directly with a modelled watercourse.",
            ],
            deliverables=[
                Deliverable(name="Flood Risk Assessment report", format="report"),
                Deliverable(name="Finished floor level drawing", format="drawing"),
            ],
        ),
        highways_and_access=BasisOfDesignSection(
            name="Highways and access",
            scope="Site access geometry, visibility splays, junction design, and adoption standards for any new/altered highway.",
            standards=[
                Standard(code="Manual for Streets", notes="MfS / MfS2 — confirm which applies by road classification/authority."),
                Standard(code="DMRB", title="Design Manual for Roads and Bridges", notes="Where the interface is with a trunk road/strategic network."),
            ],
            criteria=[
                DesignCriterion(name="Visibility splay (x-distance)", value="2.4", unit="m", notes="Typical stopping-sight-distance x-dimension per Manual for Streets — y-distance depends on design speed and must be set per site."),
                DesignCriterion(name="Design vehicle for swept path", value="to be confirmed (e.g. articulated HGV, fire tender)", notes="Governs junction/access geometry — set once the site's servicing/emergency access requirements are known."),
            ],
            assumptions=[
                Assumption(description="Access design assumes the current posted speed limit/classification of the adjoining highway applies, unless a Stage 1 Road Safety Audit indicates otherwise."),
            ],
            exclusions=[
                "Traffic impact assessment / transport statement — specialist transport planner scope, not produced by this civils BoD.",
            ],
            deliverables=[
                Deliverable(name="Access/junction general arrangement drawing", format="drawing"),
                Deliverable(name="Swept path analysis drawings", format="drawing"),
                Deliverable(name="Visibility splay drawing", format="drawing"),
            ],
        ),
        external_works_and_pavements=BasisOfDesignSection(
            name="External works and pavements",
            scope="Hard and soft landscaping, and pavement design/loading for roads, parking, and hardstanding.",
            standards=[
                Standard(code="Manual of Contract Documents for Highway Works (MCHW)", notes="For adoptable road pavement specification."),
                Standard(code="DMRB CD 226", notes="Pavement design — confirm current designation, this series is renumbered periodically."),
            ],
            criteria=[
                DesignCriterion(name="Pavement design life", value="40", unit="years", notes="Typical for an adoptable road — private hardstanding may use a shorter design life, confirm per area."),
                DesignCriterion(name="Design traffic loading", value="to be confirmed", unit="msa (million standard axles)", notes="Set from the actual traffic/servicing regime for the site, per DMRB CD 226."),
            ],
            assumptions=[
                Assumption(description="Subgrade CBR value is assumed from the geotechnical ground model, pending confirmation by in-situ/laboratory CBR testing."),
            ],
            exclusions=[
                "Soft landscape planting design — landscape architect scope.",
            ],
            deliverables=[
                Deliverable(name="Pavement construction detail drawings", format="drawing"),
                Deliverable(name="External works layout drawing", format="drawing"),
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
            criteria=[
                DesignCriterion(name="Minimum service clearance (crossing)", value="to be confirmed per NJUG/street works guidance", notes="Depends on the specific pair of services crossing — no single figure applies across all combinations."),
            ],
            assumptions=[
                Assumption(description="Existing utility positions are assumed per statutory undertaker records until physically verified by trial holes/GPR survey."),
            ],
            exclusions=[
                "Detailed design of the utility company's own network upstream of the site connection point.",
            ],
            deliverables=[
                Deliverable(name="Utilities coordination drawing", format="drawing", description="Composite of all services, new and existing."),
                Deliverable(name="Service diversion strategy", format="report", description="Only where an existing service must be diverted."),
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
                CalculationRequirement(
                    name="Lateral earth pressure calculation", standard_reference="BS EN 1997-1",
                    calc_module_reference="civil_lateral_earth_pressure_ec7",
                    description="Rankine active thrust, both DA1 combinations, calcs/civil/lateral_earth_pressure.py. Wall friction, batter, and sloping backfill are not covered -- see that module's docstring.",
                ),
                CalculationRequirement(
                    name="Retaining wall stability (sliding/overturning/bearing)", standard_reference="BS EN 1997-1",
                    calc_module_reference="civil_retaining_wall_stability_ec7",
                    description="Sliding/overturning/bearing utilisation, both DA1 combinations, calcs/civil/retaining_wall_stability.py. Self-weight and allowable bearing pressure are direct inputs -- see that module's docstring.",
                ),
            ],
            criteria=[
                DesignCriterion(name="Design working life category", value="50", unit="years", notes="BS EN 1990 category 4 (typical for building-associated structures) — confirm if a different category applies."),
                DesignCriterion(name="Surcharge loading allowance", value="to be confirmed", unit="kN/m²", notes="Set from actual adjacent loading (traffic, storage, plant) once the layout is known — do not assume a nominal figure without checking."),
            ],
            assumptions=[
                Assumption(description="Retaining wall type (e.g. gravity, embedded cantilever, propped) is assumed to be determined by height and space constraints, to be confirmed once the layout is finalised."),
            ],
            exclusions=[
                "Detailed reinforcement/connection detailing — that is calc/detail-stage output, not part of this basis of design.",
            ],
            deliverables=[
                Deliverable(name="Retaining structure calculation report", format="calculation report"),
                Deliverable(name="Retaining structure general arrangement drawing", format="drawing"),
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
