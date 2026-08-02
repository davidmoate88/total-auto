"""
Motor starting current and voltage dip check — the "electrical_lv's motor
starting" gap explicitly deferred in docs/ROADMAP.md ("skipped per project
direction for now") and flagged in
`calcs/electrical_lv/load_schedule_diversity.py`'s own docstring ("Motor
starting current (inrush) is not considered ... see the separate motor
control/switchgear starting-method criteria in the BoD"). Answers
`motor_control_and_switchgear`'s "Direct-on-line (DOL) starting threshold"
`DesignCriterion` in `basis_of_design/electrical_lv.py` with an actual
calculation rather than a bare criterion value.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module does NOT embed a "typical" starting current multiplier (e.g.
"DOL motors start at ~6x FLC") -- the actual starting current depends on
the specific motor design and starting method (DOL/star-delta/soft-start/
VSD each produce a materially different starting current), so
`starting_current_multiplier` is a REQUIRED direct input, read from the
motor's own datasheet/nameplate starting characteristics -- same reasoning
as `cable_sizing_voltage_drop.py`'s `tabulated_current_rating_a`. Likewise
`source_fault_current_a` is a required direct input from a fault level
study (DNO data or an internal fault level calc), not derived here -- same
convention as `calcs/electrical_hv/protection_grading.py`'s
`fault_current_a`.

Method summary
--------------
Starting current, from the motor's rated full load current (FLC) and its
starting current multiplier (Ist/FLC, method-dependent, supplied directly):

    I_start = full_load_current_a * starting_current_multiplier

Voltage dip at the point of connection during starting, using the
simplified source-impedance approximation (source modelled as an ideal
voltage behind a fixed source impedance; the starting current is treated as
a step draw against that same impedance) -- a standard first-pass
industrial motor-starting check, NOT a full network power-flow study:

    voltage_dip_percent = (I_start / source_fault_current_a) * 100

    utilisation = voltage_dip_percent / max_permissible_voltage_dip_percent

Known simplifications / not implemented (see Warnings in the result):
- voltage_dip_percent is a simplified Ist/Isc approximation -- it assumes
  the source impedance dominates and ignores motor/cable impedance between
  the point of connection and the motor terminals, and ignores any other
  load already running. It is conservative for a single motor starting
  alone from a stiff source, but is not a substitute for a proper network
  study on a weak/isolated (e.g. generator) supply.
- Does not check multiple motors starting simultaneously (sequential/group
  starting studies) -- a single motor start only.
- Does not itself size a soft-starter/VSD -- only flags when a DOL start
  exceeds the DOL threshold criterion.
- Does not check motor/cable thermal withstand during the starting
  transient (locked rotor thermal limit) -- see the motor manufacturer's
  own thermal starting-time data for that check.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class MotorStartingInput(BaseModel):
    motor_rated_power_kw: float = Field(..., gt=0, description="Motor rated (nameplate) power (kW).")
    full_load_current_a: float = Field(..., gt=0, description="Motor rated full load current, FLC (A), from the motor nameplate/datasheet.")
    starting_current_multiplier: float = Field(..., gt=0, description="Starting current as a multiple of FLC (Ist/FLC) for the specific motor and starting method -- from the motor manufacturer's datasheet, NOT a fixed table value (DOL/star-delta/soft-start/VSD each give a materially different figure).")
    starting_method: Literal["dol", "star_delta", "soft_start", "vsd"] = Field("dol", description="Starting method used for the DOL-threshold check below -- does not itself change the voltage dip calculation (starting_current_multiplier already reflects the method).")
    source_fault_current_a: float = Field(..., gt=0, description="Prospective fault current at the point of connection, Isc (A) -- from a fault level study (DNO data or an internal fault level calc), not derived here.")
    max_permissible_voltage_dip_percent: float = Field(10.0, gt=0, description="Maximum acceptable starting voltage dip at the point of connection (%) -- illustrative default, confirm against the project's actual criterion (equipment sensitivity, generator vs. grid supply, ER P28 if DNO-connected).")
    dol_starting_threshold_kw: float = Field(5.5, gt=0, description="Motor power above which reduced-voltage/soft starting is considered instead of DOL, matching basis_of_design/electrical_lv.py's 'Direct-on-line (DOL) starting threshold' criterion -- illustrative default, confirm against the actual site supply capacity.")


def calculate(inputs: MotorStartingInput) -> CalcResult:
    warnings: list[str] = [
        "starting_current_multiplier and source_fault_current_a are required direct inputs -- this module does "
        "not embed a 'typical' starting current multiplier or derive the source fault current.",
        "voltage_dip_percent is a simplified Ist/Isc source-impedance approximation -- ignores motor/cable "
        "impedance between the point of connection and the motor terminals, other running load, and multiple "
        "motors starting together. Not a substitute for a full network study on a weak/isolated supply.",
        "Does not check motor/cable thermal withstand during the starting transient -- see the motor "
        "manufacturer's own locked-rotor thermal-time data for that check.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    i_start = inputs.full_load_current_a * inputs.starting_current_multiplier
    voltage_dip_percent = (i_start / inputs.source_fault_current_a) * 100.0
    utilisation = voltage_dip_percent / inputs.max_permissible_voltage_dip_percent

    terms: list[Term] = [
        Term("Starting current", i_start, unit="A", note="full_load_current_a*starting_current_multiplier"),
        Term("Voltage dip at point of connection", voltage_dip_percent, unit="%", note="(I_start/source_fault_current_a)*100"),
        Term("Utilisation", utilisation, note=f"voltage_dip/max_permissible -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"),
    ]

    if utilisation > 1.0:
        warnings.append(
            f"FAILS: starting voltage dip ({voltage_dip_percent:.1f}%) exceeds the permitted "
            f"{inputs.max_permissible_voltage_dip_percent:.1f}%."
        )
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="high",
            description=f"Starting voltage dip ({voltage_dip_percent:.1f}%) exceeds the permitted "
                        f"{inputs.max_permissible_voltage_dip_percent:.1f}% at the point of connection.",
            trigger=f"voltage_dip_percent={voltage_dip_percent:.1f} > max_permissible={inputs.max_permissible_voltage_dip_percent:.1f}",
            recommended_action="Consider reduced-voltage starting (star-delta/soft-start) or a VSD to reduce starting current, or confirm a stiffer point of connection.",
            source_reference="electrical_lv_motor_starting",
        ))

    if inputs.starting_method == "dol" and inputs.motor_rated_power_kw > inputs.dol_starting_threshold_kw:
        risk_flags.append(DesignRiskFlag(
            category="assumption_sensitivity", severity="medium",
            description=f"DOL starting selected for a {inputs.motor_rated_power_kw:.1f}kW motor, above the "
                        f"{inputs.dol_starting_threshold_kw:.1f}kW DOL threshold criterion.",
            trigger=f"motor_rated_power_kw={inputs.motor_rated_power_kw:.1f} > dol_starting_threshold_kw={inputs.dol_starting_threshold_kw:.1f}",
            recommended_action="Consider reduced-voltage/soft starting or a VSD for this motor instead of DOL, per basis_of_design/electrical_lv.py's motor_control_and_switchgear criterion.",
            source_reference="electrical_lv_motor_starting",
        ))

    headline = Term(
        "Utilisation", utilisation,
        note=("PASS" if utilisation <= 1.0 else "FAIL") + " -- starting voltage dip/max permissible voltage dip",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Starting current from FLC x starting multiplier; voltage dip from a simplified Ist/Isc source-impedance approximation, checked against a permissible dip limit",
        references=[
            "IEC 60034-12, Rotating electrical machines -- Starting performance of single-speed three-phase cage induction motors.",
            "ENA Engineering Recommendation P28, Planning limits for voltage fluctuations caused by industrial, commercial and domestic equipment in the United Kingdom -- relevant when the point of connection is a DNO supply.",
        ],
    )


MODULE = CalcModule(
    key="electrical_lv_motor_starting",
    name="Motor Starting Current and Voltage Dip Check",
    discipline="Electrical (LV)",
    description=(
        "Starting current from FLC and a motor/method-specific starting multiplier, and the resulting "
        "voltage dip at the point of connection via a simplified source-impedance approximation, checked "
        "against a permissible dip limit -- also flags a DOL start above the project's DOL threshold. "
        "starting_current_multiplier and source_fault_current_a are required direct inputs -- see module docstring."
    ),
    input_model=MotorStartingInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_lv.motor_starting
    example = MotorStartingInput(
        motor_rated_power_kw=7.5,
        full_load_current_a=14.5,
        starting_current_multiplier=6.5,
        source_fault_current_a=2500.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
    for f in result.risk_flags:
        print("FLAG:", f.severity, f.category, f.description)
