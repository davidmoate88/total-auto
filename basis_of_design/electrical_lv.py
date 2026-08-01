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
periodic amendments — confirm the current edition/amendment before use. The
same caveat applies to the criteria values added in the detail pass below
(voltage drop limits, lux levels, IP ratings, changeover times, etc.) — these
are illustrative values drawn from common UK industrial practice, not
confirmed project- or client-specific figures, and every one should be
checked against the actual project brief and current standard text before
being relied on.

This is the detail pass (2nd pass) on top of the architecture-pass skeleton:
criteria, assumptions, exclusions, and deliverables are now populated per
section. Calculation logic itself (the corresponding `calcs/electrical_lv/`
modules) is being built incrementally -- `calculations_required` entries
name what's needed and `calc_module_reference` is set once the matching
module exists (see calcs/electrical_lv/cable_sizing_voltage_drop.py for the
first one); the rest remain unset until built.
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
    Structurally complete ElectricalLVBasisOfDesign, with design criteria,
    assumptions, exclusions, and deliverables populated per section.
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
            criteria=[
                DesignCriterion(name="System voltage", value="400/230", unit="V", notes="Standard UK three-phase/single-phase LV distribution voltage — confirm against the actual DNO supply/transformer secondary voltage."),
                DesignCriterion(name="System frequency", value="50", unit="Hz"),
                DesignCriterion(name="Earthing system", value="TN-S (provisional)", notes="Typical industrial arrangement fed from a dedicated transformer — the actual system depends on the HV/LV earthing decision made in basis_of_design/electrical_hv.py; confirm once that's settled."),
            ],
            assumptions=[
                Assumption(description="Standard UK LV supply parameters (400/230V, 50Hz) are assumed unless the project specifies a different arrangement."),
                Assumption(description="A TN-S earthing system is assumed as the default industrial arrangement, pending confirmation of the combined-vs-separate HV/LV earthing decision (see basis_of_design/electrical_hv.py)."),
            ],
            exclusions=[
                "Extra-low voltage (ELV) control/instrumentation power (e.g. 24V DC) — assumed covered under a separate instrumentation/controls scope, not this LV distribution section.",
            ],
            deliverables=[
                Deliverable(name="Electrical design basis statement", format="report"),
                Deliverable(name="Single line diagram (SLD)", format="drawing"),
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
                CalculationRequirement(
                    name="Cable sizing and voltage drop",
                    description="BS 7671 Reg 433.1.1 current-carrying capacity check (Ib<=In<=Iz, I2<=1.45*Iz) and Appendix 4 voltage drop check, calcs/electrical_lv/cable_sizing_voltage_drop.py. Tabulated current rating (It) and mV/A/m are direct inputs, not derived -- see that module's docstring.",
                    standard_reference="BS 7671",
                    calc_module_reference="electrical_lv_cable_sizing_voltage_drop",
                ),
                CalculationRequirement(name="Load schedule / diversity", description="Aggregated demand across all LV loads."),
            ],
            criteria=[
                DesignCriterion(name="Maximum voltage drop (power circuits)", value="5", unit="%", notes="Typical BS 7671 guidance figure — lighting circuits are usually held to a tighter 3%; confirm both against the project's actual requirement."),
                DesignCriterion(name="Cable derating ambient design temperature", value="30", unit="°C", notes="Standard BS 7671 Appendix 4 reference ambient — confirm against actual plant/enclosure ambient conditions, which may be higher near process equipment."),
            ],
            assumptions=[
                Assumption(description="A standard UK ambient design temperature (30°C) is assumed for cable derating unless site-specific/plant-specific conditions (e.g. proximity to hot process equipment) require a higher figure."),
            ],
            exclusions=[
                "DC distribution systems — not included unless a specific need is identified (e.g. a solar PV/battery energy storage installation).",
            ],
            deliverables=[
                Deliverable(name="LV distribution single line diagram", format="drawing"),
                Deliverable(name="Cable schedule", format="schedule"),
                Deliverable(name="Load schedule", format="schedule"),
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
            criteria=[
                DesignCriterion(name="Maximum earth fault loop impedance", value="per BS 7671 Table 41.3", notes="Value depends on protective device type/rating and required disconnection time (0.4s or 5s) — set per final circuit, not a single project-wide figure."),
                DesignCriterion(name="Minimum main bonding conductor size", value="per BS 7671 Table 54.8", notes="Sized from the supply neutral/earthing conductor cross-sectional area — confirm once the incoming supply arrangement is fixed."),
            ],
            assumptions=[
                Assumption(description="Soil resistivity is assumed from calcs/geotechnical/ characteristic values pending confirmation by a direct resistivity test at the earth electrode location(s)."),
            ],
            exclusions=[
                "Lightning protection system design (BS EN 62305) — a separate discipline/scope, only included if specifically requested for this project.",
            ],
            deliverables=[
                Deliverable(name="Earthing and bonding layout drawing", format="drawing"),
                Deliverable(name="Earth fault loop impedance calculation", format="calculation report"),
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
            criteria=[
                DesignCriterion(name="Direct-on-line (DOL) starting threshold", value="5.5", unit="kW", notes="Typical threshold above which soft-start/VSD starting is considered instead of DOL, to limit supply disturbance — confirm against the actual site supply fault level/capacity."),
                DesignCriterion(name="Minimum enclosure IP rating", value="IP54", notes="Typical minimum for industrial MCC/motor enclosures — confirm against the specific area's washdown/dust/hazardous-area requirements, which may require a higher rating."),
            ],
            assumptions=[
                Assumption(description="Motor loads and quantities are assumed to be confirmed once the mechanical piping discipline's pump/equipment schedule exists — this section cannot finalise MCC sizing independently of that input."),
            ],
            exclusions=[
                "Variable speed drive (VSD) harmonic mitigation design — only included if VSDs are specified for specific loads, not a default assumption.",
            ],
            deliverables=[
                Deliverable(name="Motor control centre (MCC) schedule", format="schedule"),
                Deliverable(name="Motor starter schedule", format="schedule"),
            ],
        ),
        standby_and_backup_power=BasisOfDesignSection(
            name="Standby and backup power",
            scope="Generators and UPS for critical loads.",
            standards=[
                Standard(code="BS EN 12601", notes="Reciprocating internal combustion engine driven generating sets — confirm current designation."),
                Standard(code="BS EN 62040 series", title="Uninterruptible power systems (UPS)"),
            ],
            criteria=[
                DesignCriterion(name="Generator changeover time", value="15", unit="seconds", notes="Typical target for automatic mains failure (AMF) changeover — confirm against the actual criticality of the loads served."),
                DesignCriterion(name="UPS autonomy time", value="10–30", unit="minutes", notes="Typical range for control/critical instrumentation loads — set per the specific criticality and any generator start/changeover bridging requirement."),
            ],
            assumptions=[
                Assumption(description="Standby generation is assumed sized for essential/life-safety loads only, not the full site load, unless a full-site-backup requirement is explicitly stated."),
            ],
            exclusions=[
                "Renewable generation / battery energy storage system (BESS) design — not included unless specifically requested for this project.",
            ],
            deliverables=[
                Deliverable(name="Standby power single line diagram", format="drawing"),
                Deliverable(name="Generator/UPS sizing calculation", format="calculation report"),
            ],
        ),
        lighting=BasisOfDesignSection(
            name="Lighting",
            scope="Normal and emergency lighting.",
            standards=[
                Standard(code="BS 5266-1", title="Emergency lighting — code of practice"),
                Standard(code="BS EN 12464-1", title="Light and lighting of work places"),
            ],
            criteria=[
                DesignCriterion(name="General industrial area illuminance", value="200–300", unit="lux", notes="Typical BS EN 12464-1 range for general industrial areas — specific task areas (control rooms, inspection points) may require a higher level."),
                DesignCriterion(name="Emergency lighting duration", value="3", unit="hours", notes="Standard non-domestic minimum per BS 5266-1 — confirm against the specific building/area risk assessment."),
            ],
            assumptions=[
                Assumption(description="A standard maintained emergency lighting scheme is assumed (rather than non-maintained/stand-by escape lighting only), pending the site-specific emergency lighting risk assessment."),
            ],
            exclusions=[
                "Architectural or decorative lighting design — not part of this industrial-focused basis of design.",
            ],
            deliverables=[
                Deliverable(name="Lighting layout drawing", format="drawing"),
                Deliverable(name="Lighting calculation (illuminance levels)", format="calculation report"),
            ],
        ),
        small_power_and_containment=BasisOfDesignSection(
            name="Small power and containment",
            scope="Socket outlets and cable containment/trunking systems.",
            standards=[
                Standard(code="BS 7671", notes="Socket outlet circuit design."),
                Standard(code="BS EN 61537", title="Cable management — cable tray systems and cable ladder systems", notes="Confirm current designation."),
            ],
            criteria=[
                DesignCriterion(name="Socket outlet circuit rating", value="32A ring / 20A radial (typical)", notes="Illustrative only — actual circuit design depends on the specific outlets/loads served."),
                DesignCriterion(name="Cable containment maximum fill factor", value="45", unit="%", notes="Typical design target to allow for future additions — confirm against the project's own cable management standard."),
            ],
            assumptions=[
                Assumption(description="Cable containment routes are assumed coordinated with mechanical piping and structural steelwork to avoid clashes, pending a 3D model coordination review once all disciplines have routed their services."),
            ],
            exclusions=[
                "IT/data cabling containment — assumed to sit under a separate ELV/IT systems scope, not this LV small power section.",
            ],
            deliverables=[
                Deliverable(name="Small power layout drawing", format="drawing"),
                Deliverable(name="Cable containment layout drawing", format="drawing"),
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
            criteria=[
                DesignCriterion(name="Zone classification categories", value="Zone 0/1/2 (gas/vapour) or Zone 20/21/22 (dust)", notes="Per BS EN 60079-10-1 — the actual zone extents/categories can only be set once process fluid/material data is available from the mechanical piping discipline."),
                DesignCriterion(name="Equipment protection level (EPL) required", value="to be confirmed per zone", notes="Set from the zone classification once established — e.g. Ga/Gb/Gc for gas zones."),
            ],
            assumptions=[
                Assumption(description="Process fluid/material flammability data is assumed to be supplied by the mechanical piping/process discipline; this section does not itself generate that data."),
                Assumption(description="A gas/vapour hazard only is assumed by default; combustible dust classification is not assumed unless a specific dust-generating process is identified."),
            ],
            exclusions=[
                "Combustible dust explosion classification (Zone 20/21/22) — only included if a dust-generating process is specifically identified; gas/vapour classification is the default scope.",
            ],
            deliverables=[
                Deliverable(name="Hazardous area classification drawing (zone plan)", format="drawing"),
                Deliverable(name="Equipment selection schedule for classified zones", format="schedule"),
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
            criteria=[
                DesignCriterion(name="Arc flash study trigger", value="all boards/MCCs above a minimum prospective fault level (to be confirmed)", notes="Threshold below which an arc flash study is not considered necessary — set per the project's electrical safety policy/client standard."),
                DesignCriterion(name="PPE category framework", value="to be confirmed — IEEE 1584/NFPA 70E or an equivalent UK-recognised method", notes="Sets incident energy bands and corresponding PPE categories once the arc flash study is complete."),
            ],
            assumptions=[
                Assumption(description="An arc flash study is assumed required for the main LV switchboard and all MCCs above a minimum fault level threshold, to be confirmed against the project's electrical safety policy."),
            ],
            exclusions=[
                "HV arc flash assessment — covered separately under basis_of_design/electrical_hv.py, not extrapolated from this LV assessment.",
            ],
            deliverables=[
                Deliverable(name="Arc flash risk assessment report", format="report"),
                Deliverable(name="Arc flash warning label schedule", format="schedule"),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.electrical_lv  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_electrical_lv_bod_skeleton()
    print(render_basis_of_design("LV Electrical", bod.sections()))
