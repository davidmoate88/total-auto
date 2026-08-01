"""
LV (low voltage) electrical basis of design — scoped to plant/industrial
electrical distribution consistent with the civils/structural scope already
built (access steelwork, mechanical piping context), rather than commercial
building electrical services. Includes hazardous area classification per
project direction.

*** Verify before real use *** — same caveat as every other basis_of_design
module: standards below are populated from training knowledge of commonly-
cited UK/international electrical references, not verified against current
standard texts in this environment. BS 7671 in particular is revised via
periodic amendments — confirm the current edition/amendment before use.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from basis_of_design.core import BasisOfDesignSection, CalculationRequirement, Interface, Standard
from core.risk import DesignRiskFlag

ELECTRICAL_LV_SECTION_NAMES = [
    "design_standards_and_criteria",
    "lv_distribution_and_reticulation",
    "earthing_and_bonding",
    "motor_control_and_switchgear",
    "standby_and_backup_power",
    "lighting",
    "small_power_and_containment",
    "hazardous_area_classification",
    "arc_flash_and_electrical_safety",
]


class ElectricalLVBasisOfDesign(BaseModel):
    project_reference: Optional[str] = Field(None, description="Links to portfolio.models.Project.reference.")

    design_standards_and_criteria: BasisOfDesignSection
    lv_distribution_and_reticulation: BasisOfDesignSection
    earthing_and_bonding: BasisOfDesignSection
    motor_control_and_switchgear: BasisOfDesignSection
    standby_and_backup_power: BasisOfDesignSection
    lighting: BasisOfDesignSection
    small_power_and_containment: BasisOfDesignSection
    hazardous_area_classification: BasisOfDesignSection
    arc_flash_and_electrical_safety: BasisOfDesignSection

    def sections(self) -> dict[str, BasisOfDesignSection]:
        return {name: getattr(self, name) for name in ELECTRICAL_LV_SECTION_NAMES}


def build_electrical_lv_bod_skeleton(project_reference: Optional[str] = None) -> ElectricalLVBasisOfDesign:
    """
    Structurally complete ElectricalLVBasisOfDesign. Criteria, assumptions,
    exclusions, and deliverables left empty for the detail pass.
    """
    return ElectricalLVBasisOfDesign(
        project_reference=project_reference,
        design_standards_and_criteria=BasisOfDesignSection(
            name="Design standards and general criteria",
            scope="Overarching LV electrical design basis: wiring regulations, safety regulations, earthing system, and general criteria (voltage/frequency, diversity).",
            standards=[
                Standard(code="BS 7671", title="Requirements for Electrical Installations (IET Wiring Regulations)", notes="Confirm current edition/amendment."),
                Standard(code="Electricity at Work Regulations 1989"),
                Standard(code="BS EN 61439-1", title="Low-voltage switchgear and controlgear assemblies — general rules"),
            ],
        ),
        lv_distribution_and_reticulation=BasisOfDesignSection(
            name="LV distribution and reticulation",
            scope="Main LV switchboard, distribution boards, and cable route/sizing between them.",
            standards=[
                Standard(code="BS 7671", notes="Cable sizing/derating — Appendix 4."),
                Standard(code="BS EN 61439-2", title="Power switchgear and controlgear assemblies"),
            ],
            interfaces=[
                Interface(with_discipline="electrical_hv", description="Incoming HV/LV transformer secondary — supply origin for the LV system."),
                Interface(with_discipline="utilities_coordination", description="New electrical supply/DNO connection coordination (civils basis of design)."),
            ],
            calculations_required=[
                CalculationRequirement(name="Cable sizing and voltage drop", standard_reference="BS 7671"),
                CalculationRequirement(name="Load schedule / diversity", description="Aggregated demand across all LV loads."),
            ],
        ),
        earthing_and_bonding=BasisOfDesignSection(
            name="Earthing and bonding",
            scope="Main earthing terminal, equipotential bonding, and earth fault loop impedance.",
            standards=[
                Standard(code="BS 7671", notes="Chapter 54 — earthing arrangements and protective conductors."),
                Standard(code="BS 7430", title="Code of practice for protective earthing of electrical installations"),
            ],
            interfaces=[
                Interface(with_discipline="structural", description="Structural steelwork bonding."),
                Interface(with_discipline="geotechnical", description="Soil resistivity affects earth electrode design — see calcs/geotechnical/."),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="medium",
                    description=(
                        "Temporary electrical supplies and earthing arrangements during construction "
                        "(before the permanent installation's earthing/bonding is complete and tested) "
                        "are a distinct, commonly overlooked risk area from the permanent design."
                    ),
                    trigger="Construction-phase electrical supplies routinely precede the permanent earthing/bonding installation being complete.",
                    recommended_action="Define temporary supply/earthing arrangements and testing requirements for the construction phase, not just the completed installation.",
                    source_reference="basis_of_design.electrical_lv:earthing_and_bonding",
                ),
            ],
        ),
        motor_control_and_switchgear=BasisOfDesignSection(
            name="Motor control and LV switchgear",
            scope="Motor starters and motor control centres (MCCs) for plant loads (e.g. pumps on the mechanical piping side).",
            standards=[
                Standard(code="BS EN 60947 series", title="Low-voltage switchgear and controlgear"),
                Standard(code="BS EN 61439-2", notes="Shared with LV distribution — MCC assemblies specifically."),
            ],
            interfaces=[
                Interface(with_discipline="mechanical_piping", description="Motor/pump loads to be scheduled once the mechanical piping BoD is built."),
            ],
        ),
        standby_and_backup_power=BasisOfDesignSection(
            name="Standby and backup power",
            scope="Generators and UPS for critical loads.",
            standards=[
                Standard(code="BS EN 12601", notes="Reciprocating internal combustion engine driven generating sets — confirm current designation."),
                Standard(code="BS EN 62040 series", title="Uninterruptible power systems (UPS)"),
            ],
        ),
        lighting=BasisOfDesignSection(
            name="Lighting",
            scope="Normal and emergency lighting.",
            standards=[
                Standard(code="BS 5266-1", title="Emergency lighting — code of practice"),
                Standard(code="BS EN 12464-1", title="Light and lighting of work places"),
            ],
        ),
        small_power_and_containment=BasisOfDesignSection(
            name="Small power and containment",
            scope="Socket outlets and cable containment/trunking systems.",
            standards=[
                Standard(code="BS 7671", notes="Socket outlet circuit design."),
                Standard(code="BS EN 61537", title="Cable management — cable tray systems and cable ladder systems", notes="Confirm current designation."),
            ],
        ),
        hazardous_area_classification=BasisOfDesignSection(
            name="Hazardous area classification",
            scope="Area classification and equipment selection for zones with flammable/explosive atmospheres.",
            standards=[
                Standard(code="DSEAR", title="Dangerous Substances and Explosive Atmospheres Regulations 2002"),
                Standard(code="UK ATEX", notes="Equipment and Protective Systems Intended for Use in Potentially Explosive Atmospheres Regulations 2016 (UK) / EU ATEX Directive 2014/34/EU — confirm current UK designation and CE/UKCA marking status."),
                Standard(code="BS EN 60079-10-1", title="Explosive atmospheres — classification of areas — explosive gas atmospheres"),
                Standard(code="BS EN 60079-14", title="Explosive atmospheres — electrical installations design, selection and erection"),
                Standard(code="BS EN 60079-17", title="Explosive atmospheres — electrical installations inspection and maintenance"),
            ],
            interfaces=[
                Interface(with_discipline="mechanical_piping", description="Process fluids/materials that could create a hazardous zone must be identified from the piping/process design."),
                Interface(with_discipline="structural", description="Platform/walkway equipment locations relative to classified zone boundaries."),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="code_compliance",
                    severity="high",
                    description=(
                        "Area classification must be established BEFORE electrical equipment "
                        "selection — selecting standard (non-ATEX-rated) equipment in a zone that "
                        "turns out to be classified is a fundamental safety non-compliance, not a "
                        "minor design revision."
                    ),
                    trigger="Hazardous area classification depends on process/piping information that may not be finalised when electrical equipment is first specified.",
                    recommended_action="Confirm area classification is complete and signed off before finalising any electrical equipment selection in or near potentially classified zones.",
                    source_reference="basis_of_design.electrical_lv:hazardous_area_classification",
                ),
            ],
        ),
        arc_flash_and_electrical_safety=BasisOfDesignSection(
            name="Arc flash and electrical safety",
            scope="Arc flash risk assessment and safe working practices for LV switchgear.",
            standards=[
                Standard(code="HSG85", title="Electricity at work — safe working practices", notes="HSE guidance."),
                Standard(code="BS EN 50110-1", title="Operation of electrical installations"),
                Standard(code="IEEE 1584", notes="Arc flash hazard calculation — widely used internationally though not a UK Eurocode/BS; confirm applicability/preference for this portfolio."),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.electrical_lv  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_electrical_lv_bod_skeleton()
    print(render_basis_of_design("LV Electrical", bod.sections()))
