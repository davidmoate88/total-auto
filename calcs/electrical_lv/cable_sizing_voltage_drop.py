"""
LV cable sizing and voltage drop check — BS 7671 current-carrying capacity
(Regulation 433.1.1) and voltage drop (Appendix 4). Answers
`lv_distribution_and_reticulation`'s "Cable sizing and voltage drop"
`CalculationRequirement` in `basis_of_design/electrical_lv.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
BS 7671's cable current-carrying capacity tables (Appendix 4, e.g. Table
4D1A/4D2A) and voltage drop tables (e.g. Table 4D1B/4D2B, mV/A/m per cable
type/size/installation method) are extensive, method-of-installation- and
cable-construction-specific, and change between amendments. Reproducing
specific table values from training knowledge risks silently getting them
wrong in a way that looks authoritative -- following this repo's established
"flag, don't guess" discipline (see calcs/structural/base_plate.py,
calcs/civil/surface_water_discharge.py), this module does NOT embed those
tables. The tabulated current rating (It) and the voltage drop figure
(mV/A/m) are REQUIRED direct inputs -- look them up from the current BS 7671
Appendix 4 tables (or manufacturer's cable data) for the actual cable type,
size, and installation method, and supply them here. What this module DOES
implement independently and verifiably is the arithmetic BS 7671 applies to
those tabulated values: the correction-factor derating, the three-condition
check of Regulation 433.1.1, and the voltage drop percentage check.

Method summary
--------------
Effective (corrected) current-carrying capacity:

    Iz = It * Ca * Cg * Ci * Cx

where It is the tabulated rating for the selected cable/installation method,
and Ca/Cg/Ci are the standard BS 7671 rating factors for ambient temperature,
grouping, and thermal insulation respectively (Cx is a free "any other
correction factor" multiplier, e.g. for conduit in insulation or a
semi-enclosed-fuse protective device, default 1.0).

BS 7671 Regulation 433.1.1 requires, for the protective device:

    Ib <= In <= Iz           (condition 1: device covers load, device does
                               not exceed the corrected cable capacity)
    I2 <= 1.45 * Iz           (condition 2: overload protection)

where Ib is the design current, In is the protective device's nominal
rating, and I2 is the device's current causing effective operation (for a
BS EN 60898/61009 MCB, I2 = 1.45*In is the standard assumption per BS 7671
Table 3A and applied here by default if not supplied directly -- for other
device types, e.g. BS 3036 semi-enclosed fuses, I2 is higher and must be
supplied).

Voltage drop (single run, one cable size, using the tabulated mV/A/m figure
for the specific cable/installation method):

    Vd = mV_per_A_per_m * Ib * L / 1000        (volts)
    Vd% = Vd / nominal_voltage_v * 100

checked against a maximum allowable voltage drop percentage (BS 7671
Appendix 4 guidance is commonly 5% for power / 3% for lighting from the
origin of the installation -- this is a project-specific criterion, not a
fixed regulatory limit, and matches the illustrative default already set in
this discipline's own BoD criteria).

Known simplifications / not implemented (see Warnings in the result):
- Does not derive It or mV/A/m from cable size/type/installation method --
  both are required direct inputs, see above.
- Single cable run only -- no ring final circuit, no distribution board
  cumulative voltage drop across multiple sections of a circuit.
- Does not check earth fault loop impedance / disconnection time (Zs) --
  see `earthing_and_bonding`'s separate BoD criteria; not yet a built calc.
- I2 = 1.45*In default assumes a BS EN 60898/61009 MCB -- override
  `device_i2_a` directly for other protective device types.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

STANDARD_MCB_I2_FACTOR = 1.45  # BS 7671 Table 3A, BS EN 60898/61009 MCBs -- I2 = 1.45*In


class CableSizingVoltageDropInput(BaseModel):
    design_current_a: float = Field(..., gt=0, description="Design (load) current, Ib (A).")
    protective_device_rating_a: float = Field(..., gt=0, description="Protective device nominal current rating, In (A).")
    device_i2_a: Optional[float] = Field(
        None, gt=0,
        description="Protective device's current causing effective operation, I2 (A). Leave blank to assume a "
        "standard BS EN 60898/61009 MCB (I2 = 1.45*In per BS 7671 Table 3A) -- supply directly for other device "
        "types (e.g. BS 3036 semi-enclosed fuses, I2 is higher).",
    )

    tabulated_current_rating_a: float = Field(..., gt=0, description="Tabulated current-carrying capacity, It (A), from BS 7671 Appendix 4 for the selected cable size/type/installation method.")
    rating_factor_ambient_temperature: float = Field(1.0, gt=0, description="Ca, ambient temperature correction factor (BS 7671 Appendix 4).")
    rating_factor_grouping: float = Field(1.0, gt=0, description="Cg, grouping correction factor (BS 7671 Appendix 4).")
    rating_factor_thermal_insulation: float = Field(1.0, gt=0, description="Ci, thermal insulation correction factor (BS 7671 Appendix 4).")
    rating_factor_other: float = Field(1.0, gt=0, description="Cx, any other applicable correction factor not covered above (default 1.0 if none applies).")

    cable_length_m: float = Field(..., gt=0, description="Single-run cable route length, L (m).")
    mv_per_a_per_m: float = Field(..., gt=0, description="Tabulated voltage drop figure, mV/A/m, from BS 7671 Appendix 4 for the selected cable size/type/installation method.")
    nominal_voltage_v: float = Field(230.0, gt=0, description="Nominal voltage at the origin of the circuit (V) -- 230V single-phase or 400V three-phase.")
    max_voltage_drop_percent: float = Field(5.0, gt=0, description="Maximum allowable voltage drop (%) from the origin of the installation -- BS 7671 guidance is commonly 5% power / 3% lighting; confirm against the project's criterion.")


def calculate(inputs: CableSizingVoltageDropInput) -> CalcResult:
    warnings: list[str] = [
        "Tabulated current rating (It) and voltage drop figure (mV/A/m) are direct inputs, not derived by this "
        "module -- confirm both against the current BS 7671 Appendix 4 tables for the actual cable size/type/"
        "installation method. See module docstring.",
        "Single cable run only -- does not accumulate voltage drop across a ring final circuit or multiple "
        "distribution board sections.",
        "Does not check earth fault loop impedance / disconnection time (Zs) -- a separate check.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    Ca, Cg, Ci, Cx = (
        inputs.rating_factor_ambient_temperature,
        inputs.rating_factor_grouping,
        inputs.rating_factor_thermal_insulation,
        inputs.rating_factor_other,
    )
    Iz = inputs.tabulated_current_rating_a * Ca * Cg * Ci * Cx

    terms: list[Term] = [
        Term("Iz (corrected current-carrying capacity)", Iz, unit="A", note="It * Ca * Cg * Ci * Cx"),
    ]

    if inputs.device_i2_a is not None:
        I2 = inputs.device_i2_a
        i2_note = "supplied directly"
    else:
        I2 = STANDARD_MCB_I2_FACTOR * inputs.protective_device_rating_a
        i2_note = f"assumed {STANDARD_MCB_I2_FACTOR}*In (standard BS EN 60898/61009 MCB, BS 7671 Table 3A)"
        warnings.append(
            f"device_i2_a not supplied -- assumed I2 = {STANDARD_MCB_I2_FACTOR}*In ({I2:.2f}A) for a standard "
            "MCB. Supply directly if a different protective device type (e.g. a BS 3036 fuse) is used."
        )
    terms.append(Term("I2 (device effective operation current)", I2, unit="A", note=i2_note))

    ib_le_in = inputs.design_current_a <= inputs.protective_device_rating_a
    in_le_iz = inputs.protective_device_rating_a <= Iz
    i2_le_1_45iz = I2 <= STANDARD_MCB_I2_FACTOR * Iz

    terms.append(Term("Ib <= In", 1.0 if ib_le_in else 0.0, note=f"{inputs.design_current_a:.2f}A <= {inputs.protective_device_rating_a:.2f}A -- {'PASS' if ib_le_in else 'FAIL'}"))
    terms.append(Term("In <= Iz", 1.0 if in_le_iz else 0.0, note=f"{inputs.protective_device_rating_a:.2f}A <= {Iz:.2f}A -- {'PASS' if in_le_iz else 'FAIL'}"))
    terms.append(Term("I2 <= 1.45*Iz", 1.0 if i2_le_1_45iz else 0.0, note=f"{I2:.2f}A <= {STANDARD_MCB_I2_FACTOR * Iz:.2f}A -- {'PASS' if i2_le_1_45iz else 'FAIL'}"))

    current_utilisation = inputs.protective_device_rating_a / Iz
    terms.append(Term("Current-carrying utilisation", current_utilisation, note="In/Iz"))

    if not ib_le_in:
        warnings.append(f"FAILS Ib <= In: design current ({inputs.design_current_a:.2f}A) exceeds the protective device rating ({inputs.protective_device_rating_a:.2f}A).")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Design current ({inputs.design_current_a:.2f}A) exceeds protective device rating ({inputs.protective_device_rating_a:.2f}A) -- BS 7671 Reg 433.1.1 condition 1 fails.",
            trigger=f"Ib={inputs.design_current_a:.2f}A > In={inputs.protective_device_rating_a:.2f}A",
            recommended_action="Select a higher-rated protective device, or reduce the design load.",
            source_reference="electrical_lv_cable_sizing_voltage_drop",
        ))
    if not in_le_iz:
        warnings.append(f"FAILS In <= Iz: protective device rating ({inputs.protective_device_rating_a:.2f}A) exceeds the corrected cable capacity ({Iz:.2f}A).")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Protective device rating ({inputs.protective_device_rating_a:.2f}A) exceeds corrected cable capacity Iz ({Iz:.2f}A) -- BS 7671 Reg 433.1.1 condition 1 fails.",
            trigger=f"In={inputs.protective_device_rating_a:.2f}A > Iz={Iz:.2f}A",
            recommended_action="Increase cable size (It) or reduce derating (improve Ca/Cg/Ci), or select a lower-rated device.",
            source_reference="electrical_lv_cable_sizing_voltage_drop",
        ))
    if not i2_le_1_45iz:
        warnings.append(f"FAILS I2 <= 1.45*Iz: device effective operation current ({I2:.2f}A) exceeds 1.45*Iz ({STANDARD_MCB_I2_FACTOR * Iz:.2f}A) -- overload protection condition 2.")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Device I2 ({I2:.2f}A) exceeds 1.45*Iz ({STANDARD_MCB_I2_FACTOR * Iz:.2f}A) -- BS 7671 Reg 433.1.1 condition 2 (overload protection) fails.",
            trigger=f"I2={I2:.2f}A > 1.45*Iz={STANDARD_MCB_I2_FACTOR * Iz:.2f}A",
            recommended_action="Increase cable size (It) or reduce derating, or select a protective device with a lower I2.",
            source_reference="electrical_lv_cable_sizing_voltage_drop",
        ))

    Vd_v = inputs.mv_per_a_per_m * inputs.design_current_a * inputs.cable_length_m / 1000.0
    Vd_percent = Vd_v / inputs.nominal_voltage_v * 100.0
    voltage_drop_utilisation = Vd_percent / inputs.max_voltage_drop_percent

    terms.append(Term("Vd (voltage drop)", Vd_v, unit="V", note="mV/A/m * Ib * L / 1000"))
    terms.append(Term("Vd% (voltage drop)", Vd_percent, unit="%", note=f"{'PASS' if Vd_percent <= inputs.max_voltage_drop_percent else 'FAIL'} (<= {inputs.max_voltage_drop_percent}% required)"))
    terms.append(Term("Voltage drop utilisation", voltage_drop_utilisation, note="Vd%/max allowable Vd%"))

    if Vd_percent > inputs.max_voltage_drop_percent:
        warnings.append(f"FAILS voltage drop check: {Vd_percent:.2f}% exceeds the maximum allowable {inputs.max_voltage_drop_percent}%.")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="high",
            description=f"Voltage drop ({Vd_percent:.2f}%) exceeds the maximum allowable ({inputs.max_voltage_drop_percent}%).",
            trigger=f"Vd%={Vd_percent:.2f}% > max={inputs.max_voltage_drop_percent}%",
            recommended_action="Increase cable size (reduces mV/A/m), reduce cable length/route, or reduce the design load.",
            source_reference="electrical_lv_cable_sizing_voltage_drop",
        ))

    governing_utilisation = max(current_utilisation, voltage_drop_utilisation)
    governing_check = "current-carrying capacity" if current_utilisation >= voltage_drop_utilisation else "voltage drop"
    all_conditions_pass = ib_le_in and in_le_iz and i2_le_1_45iz and Vd_percent <= inputs.max_voltage_drop_percent

    headline = Term(
        "Governing utilisation", governing_utilisation,
        note=(("PASS" if all_conditions_pass else "FAIL") + f" -- governed by {governing_check}"),
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="BS 7671 Regulation 433.1.1 current-carrying capacity check + Appendix 4 voltage drop check, single cable run",
        references=[
            "BS 7671, Requirements for Electrical Installations (IET Wiring Regulations) -- Regulation 433.1.1, Appendix 4.",
        ],
    )


MODULE = CalcModule(
    key="electrical_lv_cable_sizing_voltage_drop",
    name="LV Cable Sizing and Voltage Drop Check (BS 7671)",
    discipline="Electrical (LV)",
    description=(
        "BS 7671 Regulation 433.1.1 current-carrying capacity check (Ib<=In<=Iz, I2<=1.45*Iz) and Appendix 4 "
        "voltage drop check for a single cable run. Tabulated current rating and mV/A/m figure are required "
        "direct inputs -- this module does not embed BS 7671's cable tables, see module docstring."
    ),
    input_model=CableSizingVoltageDropInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_lv.cable_sizing_voltage_drop
    example = CableSizingVoltageDropInput(
        design_current_a=28.0,
        protective_device_rating_a=32.0,
        tabulated_current_rating_a=36.0,
        rating_factor_ambient_temperature=0.94,
        cable_length_m=45.0,
        mv_per_a_per_m=1.5,
        nominal_voltage_v=230.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
