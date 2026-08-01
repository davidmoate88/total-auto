"""
Mechanical piping basis of design — the fifth and final discipline in the
agreed order (civils -> structural -> LV electrical -> HV electrical ->
mechanical piping). Scoped to industrial/plant process piping, consistent
with the access-steelwork/electrical scope of the other disciplines (not
domestic/commercial building services pipework).

Governing piping code kept generic, per project direction: both **ASME
B31.3** (Process Piping) and **BS EN 13480** (Metallic industrial piping) are
listed as applicable in `design_standards_and_criteria` rather than
committing to one — the specific project/client/jurisdiction decides which
governs, and a design may need to demonstrate compliance with either
depending on where the plant sits and who the client is.

*** Verify before real use *** — same caveat as every other basis_of_design
module in this repo: the standards below are populated from training
knowledge of commonly-cited piping codes/standards, not verified against
current purchased standard texts in this environment. Treat this as a
credible starting checklist, not a guaranteed-current authoritative list.
The same caveat applies to the criteria values added in the detail pass
below (hydrotest pressure factor, corrosion allowance, erosional velocity,
insulation trigger temperature, etc.) — these are illustrative values drawn
from common piping industry practice, not confirmed project- or
client-specific figures, and every one should be checked against the actual
project brief, process data, and current standard text before being relied
on.

This is the detail pass (2nd pass) on top of the architecture-pass skeleton:
criteria, assumptions, exclusions, and deliverables are now populated per
section. Calculation logic itself (the corresponding `calcs/mechanical_piping/`
modules) is not yet built — `calculations_required` entries name what's
needed but `calc_module_reference` stays unset until those modules exist.
This completes the detail pass across all five agreed disciplines.
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

MECHANICAL_PIPING_SECTION_NAMES = [
    "design_standards_and_criteria",
    "pipe_sizing_and_flow",
    "pipe_stress_analysis_and_supports",
    "material_selection_and_corrosion",
    "valves_and_specialty_items",
    "flanges_gaskets_and_bolting",
    "pressure_testing_and_inspection",
    "insulation_and_heat_tracing",
    "supports_structural_and_hazardous_area_interfaces",
]


class MechanicalPipingBasisOfDesign(BaseModel):
    project_reference: Optional[str] = Field(None, description="Links to portfolio.models.Project.reference.")

    design_standards_and_criteria: BasisOfDesignSection
    pipe_sizing_and_flow: BasisOfDesignSection
    pipe_stress_analysis_and_supports: BasisOfDesignSection
    material_selection_and_corrosion: BasisOfDesignSection
    valves_and_specialty_items: BasisOfDesignSection
    flanges_gaskets_and_bolting: BasisOfDesignSection
    pressure_testing_and_inspection: BasisOfDesignSection
    insulation_and_heat_tracing: BasisOfDesignSection
    supports_structural_and_hazardous_area_interfaces: BasisOfDesignSection

    def sections(self) -> dict[str, BasisOfDesignSection]:
        return {name: getattr(self, name) for name in MECHANICAL_PIPING_SECTION_NAMES}


def build_mechanical_piping_bod_skeleton(project_reference: Optional[str] = None) -> MechanicalPipingBasisOfDesign:
    """
    Structurally complete MechanicalPipingBasisOfDesign, with design criteria,
    assumptions, exclusions, and deliverables populated per section.
    """
    return MechanicalPipingBasisOfDesign(
        project_reference=project_reference,
        design_standards_and_criteria=BasisOfDesignSection(
            name="Design standards and general criteria",
            scope=(
                "Overarching piping design basis: governing piping code, design conditions "
                "(pressure/temperature), pressure equipment regulatory regime, and pipeline "
                "class/category. Kept generic across governing code per project direction — "
                "both ASME B31.3 and BS EN 13480 are listed; the specific project/client/"
                "jurisdiction determines which actually governs."
            ),
            standards=[
                Standard(code="ASME B31.3", title="Process Piping"),
                Standard(code="BS EN 13480", title="Metallic industrial piping (all parts)", national_annex="UK NA where applicable"),
                Standard(code="PED 2014/68/EU", title="Pressure Equipment Directive", notes="EU — confirm applicability."),
                Standard(code="Pressure Equipment (Safety) Regulations 2016", notes="UK implementation of PED post-Brexit."),
                Standard(code="Pressure Systems Safety Regulations 2000", notes="UK — in-service written scheme of examination requirement."),
            ],
            criteria=[
                DesignCriterion(name="Governing piping code", value="ASME B31.3 and BS EN 13480 (kept generic)", notes="Kept generic per project direction — the specific governing code is confirmed per project/client, not fixed by this basis of design."),
                DesignCriterion(name="Design pressure", value="to be confirmed from process data", notes="Set per line from the process design conditions, not a single project-wide figure."),
                DesignCriterion(name="Design temperature", value="to be confirmed from process data", notes="Set per line from the process design conditions; also drives the minimum design metal temperature (MDMT) check in material_selection_and_corrosion."),
                DesignCriterion(name="Piping class/category", value="to be confirmed per line (PED Article 13 category / ASME B31.3 fluid service category)", notes="Governs the applicable testing/inspection rigour — kept generic pending the specific process fluid and pressure/volume data per line."),
            ],
            assumptions=[
                Assumption(description="The governing piping code (ASME B31.3 vs. BS EN 13480) is assumed to be confirmed per project/client, consistent with the deliberate decision to keep this generic rather than fix one."),
                Assumption(description="Process design conditions (pressure and temperature per line) are assumed to be supplied by the process discipline; this section does not itself generate them."),
            ],
            exclusions=[
                "Commitment to a single governing piping code — deliberately kept generic per project direction; see module docstring.",
            ],
            deliverables=[
                Deliverable(name="Piping design basis statement", format="report"),
                Deliverable(name="Line list", format="schedule"),
            ],
        ),
        pipe_sizing_and_flow=BasisOfDesignSection(
            name="Pipe sizing and flow",
            scope="Line sizing from process flow/velocity criteria, pressure drop, and erosional velocity limits.",
            standards=[
                Standard(code="API RP 14E", notes="Erosional velocity guidance — confirm applicability outside oil & gas context."),
            ],
            interfaces=[
                Interface(with_discipline="process", description="Line sizing is driven by process flow data/P&IDs — assumed available as an input, not generated by this discipline."),
            ],
            calculations_required=[
                CalculationRequirement(name="Line sizing / velocity check", description="Pipe internal diameter from flow rate against velocity and pressure drop limits."),
            ],
            criteria=[
                DesignCriterion(name="Erosional velocity limit", value="per API RP 14E c/√ρ formula", notes="Fluid-density-dependent — no single project-wide velocity figure; calculated per line once fluid properties are known."),
                DesignCriterion(name="Target liquid velocity", value="3–5", unit="m/s", notes="Typical design target range for liquid lines, balancing erosion/noise against line size/cost — confirm per specific fluid and erosional velocity check."),
                DesignCriterion(name="Maximum allowable pressure drop", value="to be confirmed per line", notes="Typically constrained by downstream equipment NPSH/control valve authority — set per line, not a single figure."),
            ],
            assumptions=[
                Assumption(description="Process flow rate and fluid property data (P&IDs, process data sheets) are assumed to be supplied as an input from the process discipline; this section sizes lines from that data rather than generating flow rates itself."),
            ],
            exclusions=[
                "Two-phase flow sizing methodology — only addressed if a specific two-phase service is identified; single-phase sizing is the default scope.",
            ],
            deliverables=[
                Deliverable(name="Line sizing calculation report", format="calculation report"),
                Deliverable(name="Piping line list with sizes", format="schedule"),
            ],
        ),
        pipe_stress_analysis_and_supports=BasisOfDesignSection(
            name="Pipe stress analysis and supports",
            scope="Flexibility/stress analysis (thermal expansion, sustained and occasional loads), and support type/spacing.",
            standards=[
                Standard(code="ASME B31.3", notes="Stress analysis provisions — shared with design_standards_and_criteria."),
                Standard(code="BS EN 13480-3", title="Design and calculation"),
                Standard(code="MSS SP-58", title="Pipe hangers and supports", notes="Confirm current edition."),
            ],
            interfaces=[
                Interface(with_discipline="structural", description="Pipe support loads (dead, thermal, occasional) are applied loads on the supporting steelwork — see basis_of_design/structural.py."),
            ],
            calculations_required=[
                CalculationRequirement(name="Pipe flexibility/stress analysis", standard_reference="ASME B31.3"),
                CalculationRequirement(name="Support load schedule", description="Loads passed to the structural discipline per support point."),
            ],
            criteria=[
                DesignCriterion(name="Sustained stress allowable", value="per ASME B31.3 Sh / BS EN 13480-3 allowable stress tables", notes="Material- and temperature-dependent — no single project-wide figure; looked up per pipe material/grade once selected."),
                DesignCriterion(name="Support spacing", value="per MSS SP-58 span tables", notes="Dependent on pipe size/schedule/insulation weight per line — confirm against the specific line list once sizing is complete."),
                DesignCriterion(name="Maximum equipment nozzle load", value="per connected equipment manufacturer's allowable (e.g. NEMA SM23 for pumps)", notes="Set per piece of connected equipment, not a single project-wide figure — confirm with the equipment vendor's data sheet."),
            ],
            assumptions=[
                Assumption(description="The ambient-to-operating temperature differential is assumed to be the governing thermal expansion case, unless a more severe transient (e.g. steam-out, regeneration cycle) is identified for a specific line."),
            ],
            exclusions=[
                "Dynamic/vibration analysis (acoustic-induced vibration, pulsation) — only included if a specific high-risk service (e.g. reciprocating compressor discharge) is identified.",
            ],
            deliverables=[
                Deliverable(name="Pipe stress analysis report", format="calculation report"),
                Deliverable(name="Support location and type schedule", format="schedule"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="temporary_works",
                    severity="medium",
                    description=(
                        "Pipework is often erected in spans before its permanent supports are all "
                        "installed, and can be temporarily supported or left partially unsupported "
                        "during construction/tie-in — a condition the completed stress analysis "
                        "(which assumes all permanent supports in place) does not itself cover."
                    ),
                    trigger="Any piping section installed progressively, or requiring temporary support/blinding during tie-ins.",
                    recommended_action="Contractor/temporary works designer to verify temporary support adequacy for the actual construction sequence, not just the as-designed permanent support arrangement.",
                    source_reference="basis_of_design.mechanical_piping:pipe_stress_analysis_and_supports",
                ),
            ],
        ),
        material_selection_and_corrosion=BasisOfDesignSection(
            name="Material selection and corrosion",
            scope="Pipe/fitting material selection, corrosion allowance, and any material-specific service restrictions (e.g. sour service).",
            standards=[
                Standard(code="ASME B36.10M", title="Welded and Seamless Wrought Steel Pipe"),
                Standard(code="ISO 21457", title="Materials selection for oil and gas production systems", notes="Confirm applicability outside oil & gas."),
                Standard(code="NACE MR0175 / ISO 15156", notes="Sour service material requirements — only where applicable to the process fluid."),
            ],
            criteria=[
                DesignCriterion(name="Corrosion allowance", value="1.5–3", unit="mm", notes="Typical range for carbon steel in non-aggressive service — confirm against a project-specific corrosion study for the actual fluid/environment."),
                DesignCriterion(name="Minimum design metal temperature (MDMT)", value="to be confirmed", notes="Governs whether impact testing is required per ASME B31.3/BS EN 13480 — set from the lowest expected metal temperature (ambient or process, whichever governs)."),
            ],
            assumptions=[
                Assumption(description="Carbon steel is assumed as the default pipe material unless the process fluid/corrosion study indicates a need for an alloy, stainless, or lined pipe material."),
            ],
            exclusions=[
                "Detailed corrosion rate modelling (e.g. de Waard-Milliams for CO2 corrosion) — specialist materials engineering scope, only included if a corrosive service is identified.",
            ],
            deliverables=[
                Deliverable(name="Material selection report", format="report"),
                Deliverable(name="Corrosion allowance schedule (per line)", format="schedule"),
            ],
        ),
        valves_and_specialty_items=BasisOfDesignSection(
            name="Valves and specialty items",
            scope="Valve type/rating selection, actuation, and specialty items (strainers, steam traps, expansion joints, relief devices).",
            standards=[
                Standard(code="API 6D", title="Specification for Pipeline and Piping Valves", notes="Confirm applicability outside pipeline context."),
                Standard(code="BS EN 12266", title="Industrial valves — testing"),
                Standard(code="ASME B16.34", title="Valves — Flanged, Threaded, and Welding End"),
            ],
            criteria=[
                DesignCriterion(name="Valve pressure class", value="matched to line class (e.g. ASME Class 150/300/600 or PN10/16/40)", notes="Set per line from its design pressure/temperature, not a single project-wide class."),
                DesignCriterion(name="Valve actuation", value="manual (default)", notes="Actuated valves (ESD, control) identified individually where a specific control/safety function requires them."),
            ],
            assumptions=[
                Assumption(description="Manual valve operation is assumed as the default; actuated valves are only included where a specific control or emergency shutdown (ESD) function requires them."),
            ],
            exclusions=[
                "Detailed control valve sizing (Cv calculation) — typically an instrumentation/controls discipline scope; only summarised here as a specialty item.",
            ],
            deliverables=[
                Deliverable(name="Valve schedule", format="schedule"),
                Deliverable(name="Specialty item (strainers/traps/relief devices) schedule", format="schedule"),
            ],
        ),
        flanges_gaskets_and_bolting=BasisOfDesignSection(
            name="Flanges, gaskets and bolting",
            scope="Flange rating/facing selection, gasket type, and bolting specification/torque.",
            standards=[
                Standard(code="ASME B16.5", title="Pipe Flanges and Flanged Fittings"),
                Standard(code="BS EN 1092-1", title="Flanges and their joints — Circular flanges for pipes"),
                Standard(code="BS EN 1591-1", title="Flanges and their joints — Design rules for gasketed circular flange connections"),
            ],
            criteria=[
                DesignCriterion(name="Flange rating", value="matched to line class", notes="Set per line, consistent with valves_and_specialty_items' pressure class criterion."),
                DesignCriterion(name="Gasket type", value="spiral wound (hydrocarbon/steam) or full-face rubber (low-pressure water)", notes="Confirm per specific service — these are the two most common defaults, not an exhaustive list."),
                DesignCriterion(name="Bolting material", value="ASTM A193 Grade B7 studs / A194 Grade 2H nuts", notes="Typical default carbon-steel bolting — confirm against MDMT and specific service, which may require low-temperature or alloy bolting."),
            ],
            assumptions=[
                Assumption(description="Standard carbon steel bolting (A193 B7/A194 2H) is assumed unless the MDMT or a specific service requires alloy or low-temperature bolting."),
            ],
            exclusions=[
                "Bolt torque/tensioning procedure development — a construction-stage document, not part of this basis of design.",
            ],
            deliverables=[
                Deliverable(name="Flange/gasket/bolting specification", format="specification"),
                Deliverable(name="Joint schedule", format="schedule"),
            ],
        ),
        pressure_testing_and_inspection=BasisOfDesignSection(
            name="Pressure testing and inspection",
            scope="Hydrostatic/pneumatic test requirements, NDT scope, and in-service inspection/written scheme of examination basis.",
            standards=[
                Standard(code="ASME B31.3", notes="Test pressure provisions — shared with design_standards_and_criteria."),
                Standard(code="BS EN 13480-5", title="Inspection and testing"),
                Standard(code="ASME BPVC Section V / BS EN ISO 17636", notes="Non-destructive examination — confirm which set governs per the chosen piping code."),
                Standard(code="Pressure Systems Safety Regulations 2000", notes="Written scheme of examination for in-service inspection — shared with design_standards_and_criteria."),
            ],
            criteria=[
                DesignCriterion(name="Hydrotest pressure", value="1.5 × design pressure (typical factor)", notes="Confirm the exact multiplier and any temperature correction factor against the governing code (ASME B31.3 vs. BS EN 13480 differ slightly)."),
                DesignCriterion(name="NDT extent", value="to be confirmed per line class/category", notes="Ranges from spot-check (normal fluid service) to 100% (Category M/severe cyclic service) — set per line once its category is confirmed."),
            ],
            assumptions=[
                Assumption(description="Hydrostatic testing is assumed as the default test method; pneumatic testing is only considered where a hydrotest isn't practicable (e.g. water intolerance in the process, or foundation/weight limits)."),
            ],
            exclusions=[
                "In-service inspection interval / written scheme of examination detail — this section covers pre-service testing/NDT only; the ongoing regime is referenced but not detailed here.",
            ],
            deliverables=[
                Deliverable(name="Pressure test procedure/schedule", format="schedule"),
                Deliverable(name="NDT schedule", format="schedule"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="safety",
                    severity="high",
                    description=(
                        "Hydrostatic/pneumatic pressure testing is itself a distinct hazardous "
                        "activity (stored energy, test rig/blind flange failure, exclusion zone "
                        "requirements) separate from the completed system's normal operating risk, "
                        "and is easy to under-specify if only the permanent design condition is considered."
                    ),
                    trigger="Any new or modified pressure system requires a pre-service pressure test.",
                    recommended_action="Define test method (hydro preferred over pneumatic where practicable), test pressure/duration, exclusion zone, and temporary test equipment (blinds, gauges) explicitly before construction.",
                    source_reference="basis_of_design.mechanical_piping:pressure_testing_and_inspection",
                ),
            ],
        ),
        insulation_and_heat_tracing=BasisOfDesignSection(
            name="Insulation and heat tracing",
            scope="Thermal/personnel-protection insulation selection and electrical or steam trace heating design.",
            standards=[
                Standard(code="BS 5970", title="Thermal insulation of pipework and equipment", notes="Confirm current edition."),
                Standard(code="IEEE 515 / BS EN 60079-30", notes="Electrical trace heating — BS EN 60079-30 applies specifically where trace heating is in a classified hazardous area."),
            ],
            interfaces=[
                Interface(with_discipline="electrical_lv", description="Electrical trace heating circuits are LV small power/containment items, and must respect hazardous area classification where applicable."),
            ],
            criteria=[
                DesignCriterion(name="Personnel protection insulation trigger", value="60", unit="°C", notes="Typical UK guidance surface-temperature threshold above which personnel protection insulation is required in normal access areas — confirm exact figure/standard reference for the project."),
                DesignCriterion(name="Heat tracing maintain temperature", value="to be confirmed per fluid", notes="Set from the specific fluid's freeze point/pour point or viscosity requirement — no single project-wide figure."),
            ],
            assumptions=[
                Assumption(description="Personnel protection insulation is assumed required wherever a pipe surface could exceed the personnel-protection temperature threshold within normal access areas."),
            ],
            exclusions=[
                "Acoustic/noise insulation — a different function to thermal insulation; only included if noise criteria are specifically identified for a line.",
            ],
            deliverables=[
                Deliverable(name="Insulation and heat tracing specification", format="specification"),
                Deliverable(name="Heat tracing circuit schedule", format="schedule"),
            ],
        ),
        supports_structural_and_hazardous_area_interfaces=BasisOfDesignSection(
            name="Supports, structural interface, and hazardous area interface",
            scope=(
                "Cross-discipline interface section: pipe rack/support steelwork coordination "
                "with structural, and confirmation that piping/equipment layout and any "
                "electrical items (trace heating, instrumentation) are consistent with the "
                "hazardous area classification set by the electrical discipline."
            ),
            interfaces=[
                Interface(with_discipline="structural", description="Pipe racks and major support steelwork are designed/detailed under basis_of_design/structural.py, loaded from this discipline."),
                Interface(with_discipline="electrical_lv", description="Hazardous area classification (basis_of_design/electrical_lv.py) constrains equipment selection for any electrical items on or near piping (trace heating, instruments, valve actuators)."),
                Interface(with_discipline="civils", description="Below-ground/buried piping routes coordinated with civils utilities coordination and earthworks."),
            ],
            criteria=[
                DesignCriterion(name="Support load handover format", value="line list with support loads, by support point", notes="The format in which loads from pipe_stress_analysis_and_supports are handed to the structural discipline for its steelwork design."),
                DesignCriterion(name="Coordination review trigger", value="at each major design stage (to be confirmed per project programme)", notes="Sets how often piping/structural/electrical interface coordination is formally reviewed — confirm against the project's design review schedule."),
            ],
            assumptions=[
                Assumption(description="Pipe support loads are assumed final only once the stress analysis (pipe_stress_analysis_and_supports) is complete — iterative coordination with the structural discipline is expected before that point, not a single one-off handover."),
            ],
            exclusions=[
                "Detailed structural design of pipe racks/support steelwork itself — performed under basis_of_design/structural.py, not duplicated here.",
            ],
            deliverables=[
                Deliverable(name="Support load schedule (handed to structural)", format="schedule"),
                Deliverable(name="Piping/electrical hazardous area interface coordination record", format="report"),
            ],
            risk_flags=[
                DesignRiskFlag(
                    category="code_compliance",
                    severity="high",
                    description=(
                        "Piping layout, equipment, and any associated electrical items are at risk "
                        "of being specified before hazardous area classification is finalised, "
                        "mirroring the same sequencing risk flagged in the LV electrical basis of "
                        "design — this section exists specifically to force that check at the "
                        "piping/electrical boundary rather than leaving it implicit."
                    ),
                    trigger="Any piping system handling a flammable/combustible fluid, or routed through a classified area.",
                    recommended_action="Confirm hazardous area classification is complete and referenced before finalising equipment selection for any electrical item associated with the piping system.",
                    source_reference="basis_of_design.mechanical_piping:supports_structural_and_hazardous_area_interfaces",
                ),
            ],
        ),
    )


if __name__ == "__main__":
    # python3 -m basis_of_design.mechanical_piping  -- prints the skeleton BoD as markdown.
    from basis_of_design.render import render_basis_of_design

    bod = build_mechanical_piping_bod_skeleton()
    print(render_basis_of_design("Mechanical Piping", bod.sections()))
