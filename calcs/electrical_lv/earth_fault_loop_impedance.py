"""
Earth fault loop impedance (Zs) check — BS 7671 Chapter 41 automatic
disconnection of supply. Answers `earthing_and_bonding`'s "Earth fault loop
impedance calculation" `CalculationRequirement` in
`basis_of_design/electrical_lv.py`, and its "Maximum earth fault loop
impedance" `DesignCriterion` ("per BS 7671 Table 41.3").

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
The maximum permitted Zs (BS 7671 Table 41.2/41.3/41.4/41.5, depending on
protective device type/rating and required disconnection time -- 0.4s for
final circuits <=32A, 5s for distribution circuits/other final circuits) is
device-curve-specific and not embedded here -- following this repo's
established "flag, don't guess" discipline (see
calcs/electrical_lv/cable_sizing_voltage_drop.py), `max_zs_ohms` is a
REQUIRED direct input, looked up from the current BS 7671 table for the
actual protective device. Conductor resistance-per-length figures (BS 7671
Appendix 14/Table I1, or manufacturer cable data) are similarly required
direct inputs, not derived from conductor size alone.

Method summary
--------------
    Zs = Ze + (R1 + R2)

where Ze is the external earth fault loop impedance (source/DNO side, up to
the origin of the installation -- measured or from the DNO's supply data)
and (R1 + R2) is the phase conductor + circuit protective conductor (cpc)
resistance for THIS circuit run:

    R1 = phase_conductor_resistance_ohms_per_km * length_km
    R2 = cpc_resistance_ohms_per_km * length_km

BS 7671 Appendix 14 notes that tabulated/measured conductor resistances are
given at 20°C, while conductors run hotter in normal service -- a
correction factor (commonly cited as 1.20, i.e. resistance rises ~20% at
normal operating temperature) is applied before comparing against the
tabulated maximum Zs:

    Zs = Ze + (R1 + R2) * temperature_correction_factor

checked against `max_zs_ohms`. This is the standard BS 7671 "designer's
method" (as opposed to a post-installation Zs test result, which already
reflects actual operating conditions and would not need the temperature
correction applied).

Known simplifications / not implemented (see Warnings in the result):
- `max_zs_ohms`, conductor resistance-per-length figures, and Ze are all
  required direct inputs -- see above.
- Single cable run only -- no ring final circuit (which combines two
  parallel conductor paths, not a simple series R1+R2).
- Does not check touch voltage / prospective fault current directly --
  relies on the tabulated max Zs already encoding the disconnection-time
  requirement for the stated protective device, per BS 7671's own method.
- Does not size the earthing conductor or check main/supplementary bonding
  conductor cross-sectional area (BS 7671 Table 54.7/54.8) -- a separate
  check.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

STANDARD_TEMPERATURE_CORRECTION_FACTOR = 1.20  # BS 7671 Appendix 14 -- 20C tabulated/measured R -> normal operating temperature


class EarthFaultLoopImpedanceInput(BaseModel):
    external_loop_impedance_ze_ohms: float = Field(..., ge=0, description="Ze, external earth fault loop impedance (source/DNO side up to the installation origin) -- measured or from the DNO's supply data.")
    phase_conductor_resistance_ohms_per_km: float = Field(..., gt=0, description="Phase conductor resistance (ohms/km) for the circuit's conductor size -- from BS 7671 Appendix 14/Table I1 or manufacturer data.")
    cpc_resistance_ohms_per_km: float = Field(..., gt=0, description="Circuit protective conductor (cpc) resistance (ohms/km) for the circuit's cpc size -- from BS 7671 Appendix 14/Table I1 or manufacturer data.")
    cable_length_m: float = Field(..., gt=0, description="Circuit conductor run length, L (m).")
    temperature_correction_factor: float = Field(
        STANDARD_TEMPERATURE_CORRECTION_FACTOR, gt=0,
        description="Corrects 20°C tabulated/measured conductor resistance up to normal operating temperature -- BS 7671 Appendix 14 commonly cites 1.20. Confirm against the current standard text.",
    )
    max_zs_ohms: float = Field(..., gt=0, description="Maximum permitted Zs (ohms) for the protective device type/rating and required disconnection time -- from BS 7671 Table 41.2/41.3/41.4/41.5.")


def calculate(inputs: EarthFaultLoopImpedanceInput) -> CalcResult:
    warnings: list[str] = [
        "max_zs_ohms and both conductor resistance-per-length figures are direct inputs, not derived by this "
        "module -- confirm against the current BS 7671 tables for the actual protective device/conductor "
        "sizes. See module docstring.",
        "Single cable run only -- does not handle a ring final circuit's parallel conductor paths.",
        "Does not size the earthing conductor or check main/supplementary bonding conductor CSA (Table 54.7/54.8).",
    ]
    risk_flags: list[DesignRiskFlag] = []

    length_km = inputs.cable_length_m / 1000.0
    R1 = inputs.phase_conductor_resistance_ohms_per_km * length_km
    R2 = inputs.cpc_resistance_ohms_per_km * length_km
    Zs = inputs.external_loop_impedance_ze_ohms + (R1 + R2) * inputs.temperature_correction_factor

    terms: list[Term] = [
        Term("R1 (phase conductor resistance)", R1, unit="ohm", note="phase resistance/km * length"),
        Term("R2 (cpc resistance)", R2, unit="ohm", note="cpc resistance/km * length"),
        Term("Zs (earth fault loop impedance)", Zs, unit="ohm", note="Ze + (R1+R2)*temperature_correction_factor"),
    ]

    utilisation = Zs / inputs.max_zs_ohms
    terms.append(Term("Utilisation", utilisation, note=f"Zs/max_zs -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"))

    if utilisation > 1.0:
        warnings.append(f"FAILS: Zs ({Zs:.3f} ohm) exceeds the maximum permitted Zs ({inputs.max_zs_ohms:.3f} ohm) -- disconnection within the required time is not assured.")
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Earth fault loop impedance Zs ({Zs:.3f} ohm) exceeds the maximum permitted value ({inputs.max_zs_ohms:.3f} ohm) -- automatic disconnection within the required time (BS 7671 Chapter 41) is not assured.",
            trigger=f"Zs={Zs:.3f}ohm > max_zs={inputs.max_zs_ohms:.3f}ohm",
            recommended_action="Reduce Ze, increase conductor size (reduces R1/R2), shorten the circuit run, or select a protective device with a lower max Zs requirement (e.g. an RCD as additional protection).",
            source_reference="electrical_lv_earth_fault_loop_impedance",
        ))

    headline = Term(
        "Utilisation", utilisation,
        note=("PASS" if utilisation <= 1.0 else "FAIL") + " -- Zs/max permitted Zs (BS 7671 Chapter 41)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="BS 7671 Chapter 41 earth fault loop impedance (Zs) check against tabulated maximum for automatic disconnection of supply",
        references=[
            "BS 7671, Requirements for Electrical Installations (IET Wiring Regulations) -- Chapter 41, Appendix 14, Table 41.2/41.3/41.4/41.5.",
        ],
    )


MODULE = CalcModule(
    key="electrical_lv_earth_fault_loop_impedance",
    name="Earth Fault Loop Impedance Check (Zs, BS 7671 Chapter 41)",
    discipline="Electrical (LV)",
    description=(
        "Zs = Ze + (R1+R2)*temperature_correction_factor, checked against the maximum permitted Zs for the "
        "protective device/disconnection time. Max Zs and conductor resistance-per-length are required direct "
        "inputs -- this module does not embed BS 7671's Zs/conductor resistance tables, see module docstring."
    ),
    input_model=EarthFaultLoopImpedanceInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_lv.earth_fault_loop_impedance
    example = EarthFaultLoopImpedanceInput(
        external_loop_impedance_ze_ohms=0.35,
        phase_conductor_resistance_ohms_per_km=1.83,
        cpc_resistance_ohms_per_km=4.61,
        cable_length_m=25.0,
        max_zs_ohms=1.09,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
