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
specific network operator/site.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from basis_of_design.core import BasisOfDesignSection, CalculationRequirement, Interface, Standard
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
    Structurally complete ElectricalHVBasisOfDesign. Criteria, assumptions,
    exclusions, and deliverables left empty for the detail pass.
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
        ),
        protection_and_control=BasisOfDesignSection(
            name="Protection and control",
            scope="Protection relays and discrimination/grading studies.",
            standards=[
                Standard(code="BS EN 60255 series", title="Measuring relays and protection equipment"),
            ],
            calculations_required=[
                CalculationRequirement(name="Protection discrimination/grading study", description="Confirms protection devices operate selectively across the HV/LV system."),
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
