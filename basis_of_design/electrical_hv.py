"""
HV (high voltage) electrical basis of design — the incoming supply and
step-down side of the plant electrical system, complementing
`electrical_lv.py`. Kept generic across common industrial HV voltage classes
(6.6kV/11kV/33kV) rather than fixed to one, per project direction — the
specific voltage is a per-project choice, not a discipline-scope decision.

*** Verify before real use *** — same caveat as every other basis_of_design
module: standards below are populated from training knowledge, not verified
against current standard texts in this environment. HV work in particular
often also runs under a duty-holder's own "Safety Rules" / Authorised Person
regime alongside the published standards — confirm what governs for the
specific network operator/site. The same caveat applies to the criteria
values added in the detail pass below (protection grading margins, cable
bending radii, transformer vector group/cooling class, etc.) — these are
illustrative values drawn from common UK industrial HV practice, not
confirmed project- or client-specific figures, and every one should be
checked against the actual project brief, DNO connection offer, and current
standard text before being relied on.

This is the detail pass (2nd pass) on top of the architecture-pass skeleton:
criteria, assumptions, exclusions, and deliverables are now populated per
section. Calculation logic itself (the corresponding `calcs/electrical_hv/`
modules) is being built incrementally -- `calculations_required` entries
name what's needed and `calc_module_reference` is set once the matching
module exists (see calcs/electrical_hv/transformer_sizing.py,
calcs/electrical_hv/protection_grading.py,
calcs/electrical_hv/arc_flash_ppe_check.py, and
calcs/electrical_hv/substation_earthing_touch_step.py for the first four);
the rest remain unset until built.
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

ELECTRICAL_HV_SECTION_NAMES = [
    "design_standards_and_criteria",
    "hv_incoming_supply_and_connection",
    "substations_and_switchgear",
    "transformers",
    "protection_and_control",
    "hv_cabling_and_cable_management",
    "hv_earthing_and_touch_step_potential",
    "arc_flash_and_hv_safety",
]


class ElectricalHVBasisOfDesign(BaseModel):
    project_reference: Optional[str] = Field(None, description="Links to portfolio.models.Project.reference.")

    design_standards_and_criteria: BasisOfDesignSection
    hv_incoming_supply_and_connection: BasisOfDesignSection
    substations_and_switchgear: BasisOfDesignSection
    transformers: BasisOfDesignSection
    protection_and_control: BasisOfDesignSection
    hv_cabling_and_cable_management: BasisOfDesignSection
    hv_earthing_and_touch_step_potential: BasisOfDesignSection
    arc_flash_and_hv_safety: BasisOfDesignSection

    def sections(self) -> dict[str, BasisOfDesignSection]:
        return {name: getattr(self, name) for name in ELECTRICAL_HV_SECTION_NAMES}


def build_electrical_hv_bod_skeleton(project_reference: Optional[str] = None) -> ElectricalHVBasisOfDesign:
    """
    Structurally complete ElectricalHVBasisOfDesign, with design criteria,
    assumptions, exclusions, and deliverables populated per section.
    """
    return ElectricalHVBasisOfDesign(
        project_reference=project_reference,
        design_standards_and_criteria=BasisOfDesignSection(
            name="Design standards and general criteria",
            scope="Overarching HV design basis: safety/quality regulations, insulation coordination, system voltage class, fault level, and earthing system philosophy.",
            standards=[
                Standard(code="ESQCR", title="Electricity Safety, Quality and Continuity Regulations 2002"),
                Standard(code="BS EN 60071 series", title="Insulation co-ordination"),
                Standard(code="Electricity at Work Regulations 1989", notes="Shared with the LV electrical module."),
            ],
            criteria=[
                DesignCriterion(name="HV voltage class", value="6.6kV / 11kV / 33kV (kept generic)", notes="Kept generic per project direction — the specific class is confirmed per project from the DNO connection offer/site requirement, not fixed by this basis of design."),
                DesignCriterion(name="System fault level", value="to be confirmed from the DNO connection offer/fault level statement", notes="Not calculated independently — obtained from the network operator, since it depends on their upstream network configuration."),
                DesignCriterion(name="Insulation level (BIL)", value="per BS EN 60071, dependent on voltage class", notes="Basic impulse insulation level — set once the HV voltage class is confirmed for the project."),
            ],
            assumptions=[
                Assumption(description="The specific HV voltage class is assumed to be confirmed per project rather than fixed by this basis of design, per the generic-across-voltage-classes scope decision."),
                Assumption(description="System fault level is assumed to be obtained from the DNO's connection offer/fault level statement rather than calculated independently."),
            ],
            exclusions=[
                "Commitment to a specific HV voltage class — deliberately kept generic per project direction; see module docstring.",
            ],
            deliverables=[
                Deliverable(name="HV electrical design basis statement", format="report"),
                Deliverable(name="Single line diagram (HV)", format="drawing"),
            ],
        ),
        hv_incoming_supply_and_connection=BasisOfDesignSection(
            name="HV incoming supply and connection",
            scope="DNO/IDNO connection agreement, point of connection, and metering.",
            standards=[
                Standard(code="ENA Engineering Recommendations", notes="Confirm which specific EREC applies (connection design/planning) for the network operator involved."),
            ],
            interfaces=[
                Interface(with_discipline="utilities_coordination", description="New HV supply connection coordinated with the DNO (civils basis of design)."),
            ],
            criteria=[
                DesignCriterion(name="Connection point", value="to be confirmed via DNO connection application", notes="Set by the DNO's connection offer once submitted — not a value this basis of design can set independently."),
                DesignCriterion(name="Metering arrangement", value="HV metering (CT/VT metering)", notes="Typical arrangement for a direct HV connection — confirm against the specific network operator's metering requirements."),
            ],
            assumptions=[
                Assumption(description="A new HV connection is assumed required (rather than an extension of an existing private HV network) unless site information indicates otherwise."),
            ],
            exclusions=[
                "The DNO's own upstream network reinforcement — outside this project's design scope, even where it's a consequence of the new connection.",
            ],
            deliverables=[
                Deliverable(name="Connection agreement/application pack", format="report"),
                Deliverable(name="Metering arrangement drawing", format="drawing"),
            ],
        ),
        substations_and_switchgear=BasisOfDesignSection(
            name="Substations and switchgear",
            scope="HV switchgear (ring main units, circuit breakers) and substation buildings/enclosures.",
            standards=[
                Standard(code="BS EN 62271 series", title="High-voltage switchgear and controlgear"),
                Standard(code="BS 7354", title="Design of high-voltage open-terminal stations"),
            ],
            interfaces=[
                Interface(with_discipline="civils", description="Substation building/enclosure foundations and access."),
            ],
            criteria=[
                DesignCriterion(name="Switchgear topology", value="ring main unit (RMU), single incoming supply (provisional)", notes="Typical for a single HV connection — confirm ring/radial topology against the site's actual reliability/redundancy requirement."),
                DesignCriterion(name="Substation ingress protection", value="to be confirmed (indoor building vs. outdoor enclosure)", notes="Set once the substation location/type is fixed with civils/structural."),
            ],
            assumptions=[
                Assumption(description="Substation location and space allowance are assumed to be coordinated with civils and structural, pending a confirmed site layout."),
            ],
            exclusions=[
                "SF6 environmental/phase-out considerations for gas-insulated switchgear — only addressed if a specific supplier or environmental policy requires it.",
            ],
            deliverables=[
                Deliverable(name="Substation general arrangement drawing", format="drawing"),
                Deliverable(name="Switchgear specification", format="specification"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="medium",
                    description=(
                        "Cutting over from an existing supply/switchgear to a new substation is "
                        "typically a distinct, carefully sequenced temporary/parallel-operation "
                        "condition (with defined outage windows) — not covered by the completed, "
                        "permanent switchgear design on its own."
                    ),
                    trigger="Any substation replacement/extension involves a transition period between the existing and new arrangement.",
                    recommended_action="Define the cutover/energisation sequence and outage requirements explicitly, coordinated with the site's Authorised Person regime.",
                    source_reference="basis_of_design.electrical_hv:substations_and_switchgear",
                ),
            ],
        ),
        transformers=BasisOfDesignSection(
            name="Transformers",
            scope="HV/LV transformers stepping down to the LV distribution system.",
            standards=[
                Standard(code="BS EN 60076 series", title="Power transformers"),
            ],
            interfaces=[
                Interface(with_discipline="electrical_lv", description="Transformer secondary is the supply origin for LV distribution — see basis_of_design/electrical_lv.py."),
            ],
            calculations_required=[
                CalculationRequirement(
                    name="Transformer sizing check",
                    description="LV demand plus growth margin checked against a candidate transformer rating, and HV/LV full-load current, calcs/electrical_hv/transformer_sizing.py. Takes LV demand directly from electrical_lv's load_schedule_diversity.py output -- the first cross-discipline calc-to-calc handoff in this repo. Does not select a standard preferred size -- checks a candidate rating supplied directly, see that module's docstring.",
                    standard_reference="BS EN 60076",
                    calc_module_reference="electrical_hv_transformer_sizing",
                ),
            ],
            criteria=[
                DesignCriterion(name="Transformer rating", value="to be confirmed from the LV load schedule plus diversity", notes="Cannot be finalised independently of basis_of_design/electrical_lv.py's load schedule and diversity assumptions."),
                DesignCriterion(name="Vector group", value="Dyn11", notes="Typical for UK industrial HV/LV step-down distribution transformers — confirm against the specific earthing arrangement decided in hv_earthing_and_touch_step_potential."),
                DesignCriterion(name="Cooling class", value="ONAN (oil-natural air-natural)", notes="Typical for this rating range — forced-air cooling (ONAF) only considered if a higher rating requires it."),
            ],
            assumptions=[
                Assumption(description="An oil-filled transformer is assumed as the default; a dry-type transformer is only assumed necessary if a specific fire/environmental constraint applies (e.g. an indoor plant room with restricted oil containment)."),
            ],
            exclusions=[
                "Dry-type transformer design — not included by default (oil-filled is assumed); only added if a specific project constraint requires it.",
            ],
            deliverables=[
                Deliverable(name="Transformer schedule", format="schedule"),
                Deliverable(name="Transformer bay/plinth general arrangement drawing", format="drawing"),
            ],
        ),
        protection_and_control=BasisOfDesignSection(
            name="Protection and control",
            scope="Protection relays and discrimination/grading studies.",
            standards=[
                Standard(code="BS EN 60255 series", title="Measuring relays and protection equipment"),
            ],
            calculations_required=[
                CalculationRequirement(
                    name="Protection discrimination/grading study",
                    description="Confirms protection devices operate selectively across the HV/LV system. IEC 60255-151 IDMT relay operating times for an upstream/downstream pair at a stated fault current, checked for adequate grading margin, calcs/electrical_hv/protection_grading.py. One relay pair at one fault current only -- not a full multi-stage study across the fault current range, see that module's docstring.",
                    standard_reference="IEC 60255-151",
                    calc_module_reference="electrical_hv_protection_grading",
                ),
            ],
            criteria=[
                DesignCriterion(name="Protection grading margin", value="0.2–0.4", unit="s", notes="Typical discrimination margin between successive protection stages — confirm against the project's protection philosophy and relay manufacturer's recommendations."),
                DesignCriterion(name="Protection relay technology", value="numerical/IED", notes="Modern default over electromechanical relays — confirm compatibility with any existing site protection scheme being extended."),
            ],
            assumptions=[
                Assumption(description="A standard radial discrimination protection philosophy is assumed, rather than a loop/ring protection scheme, unless the site's supply topology requires otherwise."),
            ],
            exclusions=[
                "SCADA/remote control system integration — assumed to sit under a separate controls/instrumentation scope, unless explicitly required as part of this HV protection and control section.",
            ],
            deliverables=[
                Deliverable(name="Protection and discrimination study report", format="calculation report"),
                Deliverable(name="Protection relay settings schedule", format="schedule"),
            ],
        ),
        hv_cabling_and_cable_management=BasisOfDesignSection(
            name="HV cabling and cable management",
            scope="HV cable specification and routing.",
            standards=[
                Standard(code="BS 6622", title="Cables with extruded insulation for rated voltages up to 33kV", notes="Confirm current part/edition."),
                Standard(code="BS 7870 series", title="LV and MV polymeric insulated cables", notes="Confirm applicable parts."),
            ],
            interfaces=[
                Interface(with_discipline="civils", description="Cable route/ducting coordinated with earthworks and utilities."),
            ],
            criteria=[
                DesignCriterion(name="Cable insulation/conductor", value="XLPE insulated, copper or aluminium conductor (to be confirmed)", notes="Conductor material is typically a cost/weight trade-off decision — confirm project preference."),
                DesignCriterion(name="Minimum bending radius", value="12–15x cable diameter (typical for XLPE HV cable)", notes="Confirm against the specific cable manufacturer's data sheet once a cable is selected."),
            ],
            assumptions=[
                Assumption(description="Cable route length/topology is assumed to be coordinated with civils utilities coordination and structural cable management, pending a routing study once the site layout is confirmed."),
            ],
            exclusions=[
                "Submarine/subsea cable design — not applicable to this land-based industrial scope.",
            ],
            deliverables=[
                Deliverable(name="HV cable route drawing", format="drawing"),
                Deliverable(name="HV cable schedule", format="schedule"),
            ],
        ),
        hv_earthing_and_touch_step_potential=BasisOfDesignSection(
            name="HV earthing and touch/step potential",
            scope="Substation earthing design, distinct from the LV earthing and bonding section — governed by touch/step potential criteria specific to HV.",
            standards=[
                Standard(code="BS EN 50522", title="Earthing of power installations exceeding 1kV AC"),
                Standard(code="ENA EREC S34", title="A guide for assessing the rise of earth potential at substation sites", notes="Confirm current designation/edition."),
                Standard(code="BS 7354", notes="Shared with substations/switchgear — earthing design for open-terminal stations."),
            ],
            interfaces=[
                Interface(with_discipline="geotechnical", description="Soil resistivity drives earth electrode design — see calcs/geotechnical/."),
                Interface(with_discipline="electrical_lv", description="Whether HV and LV earthing systems are combined or kept separate is decided here."),
            ],
            calculations_required=[
                CalculationRequirement(
                    name="Substation earth grid resistance and touch/step potential check",
                    description="Sverak's grid resistance formula and IEEE 80 tolerable touch/step voltage limits, checked against a target grid resistance and an externally-supplied actual mesh/step voltage, calcs/electrical_hv/substation_earthing_touch_step.py. Actual mesh/step voltage is a required direct input -- the Km/Ks/Kii/Kh geometric correction factors needed to derive it are not reproduced here, see that module's docstring.",
                    standard_reference="IEEE 80 / BS EN 50522",
                    calc_module_reference="electrical_hv_substation_earthing_touch_step",
                ),
            ],
            criteria=[
                DesignCriterion(name="Touch/step potential limits", value="per BS EN 50522, based on fault clearance time and body resistance model", notes="No single project-wide figure — calculated from the specific fault clearance time and earthing arrangement once the protection study is complete."),
                DesignCriterion(name="Substation earth resistance target", value="to be confirmed from soil resistivity survey and earth grid design", notes="Cannot be set without a site-specific soil resistivity survey — see assumptions."),
            ],
            assumptions=[
                Assumption(description="Earth grid design is assumed to require a soil resistivity survey (multi-layer Wenner test) rather than an assumed single value, given the safety-critical nature of touch/step potential compliance."),
            ],
            exclusions=[
                "Rise of earth potential (REOP) transfer risk to telecoms/other networks beyond the site boundary — only assessed if a specific interface is identified (an ENA EREC S36-style transferred REOP assessment).",
            ],
            deliverables=[
                Deliverable(name="HV earthing design report", format="report"),
                Deliverable(name="Earth grid layout drawing", format="drawing"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="safety",
                    severity="high",
                    description=(
                        "Whether the HV and LV earthing systems are combined or kept separate is a "
                        "safety-critical decision (risk of a HV earth fault transferring a dangerous "
                        "potential rise onto LV equipment/exposed metalwork) governed by BS EN 50522 — "
                        "it must be explicitly assessed, not assumed by default."
                    ),
                    trigger="Any site with both HV and LV earthing systems present.",
                    recommended_action="Explicitly assess and document the combined-vs-separate earthing decision per BS EN 50522, informed by soil resistivity data.",
                    source_reference="basis_of_design.electrical_hv:hv_earthing_and_touch_step_potential",
                ),
            ],
        ),
        arc_flash_and_hv_safety=BasisOfDesignSection(
            name="Arc flash and HV safety",
            scope="HV-specific safe isolation procedures and arc flash risk — typically far more severe consequence than LV.",
            standards=[
                Standard(code="HSG85", notes="Shared with LV electrical — HSE guidance, electricity at work safe working practices."),
                Standard(code="BS EN 50110-1", notes="Shared with LV electrical — operation of electrical installations."),
            ],
            calculations_required=[
                CalculationRequirement(
                    name="HV PPE requirement check",
                    description="Reports the required PPE arc rating (== an externally-supplied HV-specific incident energy figure) and flags when it exceeds a practical arc-rated PPE limit, calcs/electrical_hv/arc_flash_ppe_check.py. Deliberately does NOT calculate incident energy itself, and is shaped differently from the LV arc flash module (no LV-style Category 1-4 banding) since HV incident energies routinely exceed that framework -- see that module's docstring.",
                    standard_reference="IEEE 1584 / BS EN 50110-1",
                    calc_module_reference="electrical_hv_arc_flash_ppe_check",
                ),
            ],
            criteria=[
                DesignCriterion(name="HV arc flash calculation method", value="to be confirmed — IEEE 1584 or an equivalent HV-specific method", notes="Confirm which method/tool is used for the incident energy calculation; not all LV-oriented tools extend cleanly to HV switchgear."),
                DesignCriterion(name="Minimum PPE category for HV switching", value="to be confirmed from the study", notes="Typically a higher category than the equivalent LV assessment — set once the HV-specific study is complete."),
            ],
            assumptions=[
                Assumption(description="HV switching operations are assumed to be carried out only by an Authorised Person under the site's Safety Rules regime, not general electrical staff."),
            ],
            exclusions=[
                "LV arc flash assessment — covered separately under basis_of_design/electrical_lv.py, not merged into this HV-specific study.",
            ],
            deliverables=[
                Deliverable(name="HV arc flash risk assessment report", format="report"),
                Deliverable(name="Safety Rules / Authorised Person procedure document", format="report"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="safety",
                    severity="high",
                    description=(
                        "HV arc flash incident energy levels are typically far higher than LV — PPE "
                        "categorisation and safe working procedures need a dedicated HV assessment, "
                        "not an assumption that the LV arc flash study or PPE category carries over."
                    ),
                    trigger="Any HV switchgear/switching operation.",
                    recommended_action="Commission a dedicated HV arc flash study; do not extrapolate from an LV assessment.",
                    source_reference="basis_of_design.electrical_hv:arc_flash_and_hv_safety",
                ),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.electrical_hv  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_electrical_hv_bod_skeleton()
    print(render_basis_of_design("HV Electrical", bod.sections()))
