"""
Earth electrode resistance — single vertical driven rod, Dwight's formula.
Answers `earthing_and_bonding`'s "Main earthing terminal" scope item in
`basis_of_design/electrical_lv.py`, using the soil resistivity interface
already declared there (`Interface(with_discipline="geotechnical", ...)`).

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module covers ONE electrode configuration only: a single vertical rod
driven into uniform soil (Dwight, 1936 -- reproduced near-verbatim in BS
7430 and IEEE Std 142, the "IEEE Green Book", and about as close to a
universally-agreed textbook formula as earthing calculations get, which is
why it's embedded here rather than made a direct input). It does NOT cover:
- Multiple rods in parallel -- simply dividing a single rod's resistance by
  the rod count is WRONG (mutual coupling between nearby electrodes means
  the reduction is always less than proportional); the correct treatment
  needs the rods' spacing/arrangement via formulae (e.g. Schwarz, Sunde)
  this author does not have confident, generalisable recall of. If one rod
  isn't enough, get a competent person to design the multi-rod/grid
  arrangement rather than dividing this module's answer by N.
- Plate, strip/tape, or mesh/grid electrodes -- different formulae entirely.
- Layered (non-uniform) soil -- this assumes a single characteristic soil
  resistivity value for the full rod depth, per the existing
  `calcs/geotechnical/` interface; a real site often has resistivity
  varying with depth (a multi-layer Wenner test would show this).
- HV substation earth grid design (touch/step potential compliance,
  BS EN 50522 / IEEE 80) -- `basis_of_design/electrical_hv.py`'s
  "Substation earth resistance target" needs a proper multi-electrode mesh
  grid design with touch/step voltage calculations, which this single-rod
  formula would badly understate if used as a substitute. This module is
  NOT wired to that BoD section for that reason -- see that module's own
  docstring caveats if a HV earthing calc is built later.

Method summary
--------------
For a single vertical rod of length L and diameter d, driven into soil of
resistivity rho (Dwight's formula):

    R = (rho / (2*pi*L)) * (ln(4*L/d) - 1)

checked against a project-specific target earth resistance (no single fixed
value applies -- BS 7430 gives illustrative figures for different earthing
arrangements, but the actual target depends on the system earthing
arrangement (TT/TN) and protective device sensitivity, so it is a required
direct input here, same reasoning as `earth_fault_loop_impedance.py`'s
`max_zs_ohms`).

Known simplifications / not implemented (see Warnings in the result):
- Single vertical rod only -- see above for what is NOT covered.
- Uniform soil resistivity assumed for the full rod depth.
- Does not size the earthing conductor/tape connecting the electrode to the
  main earthing terminal (BS 7671 Table 54.7/54.8 -- a separate check).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class EarthElectrodeResistanceInput(BaseModel):
    soil_resistivity_ohm_m: float = Field(..., gt=0, description="Characteristic soil resistivity, rho (ohm.m) -- from calcs/geotechnical/ or a Wenner resistivity test at the electrode location.")
    rod_length_m: float = Field(..., gt=0, description="Driven rod length, L (m).")
    rod_diameter_mm: float = Field(..., gt=0, description="Rod diameter, d (mm).")
    target_earth_resistance_ohms: float = Field(..., gt=0, description="Target maximum earth electrode resistance (ohm) -- project/system-specific (depends on earthing arrangement TT/TN and protective device sensitivity), not a fixed constant. See module docstring.")


def calculate(inputs: EarthElectrodeResistanceInput) -> CalcResult:
    warnings: list[str] = [
        "Single vertical driven rod only -- does NOT cover multiple rods (mutual coupling makes simple "
        "division by rod count wrong), plate/strip/mesh electrodes, or layered soil. See module docstring.",
        "Not wired to HV substation earthing -- a substation earth grid needs a proper multi-electrode mesh "
        "design with touch/step potential compliance (BS EN 50522/IEEE 80), which this single-rod formula "
        "would badly understate if used as a substitute.",
        "Does not size the earthing conductor/tape connecting the electrode to the main earthing terminal "
        "(BS 7671 Table 54.7/54.8).",
    ]
    risk_flags: list[DesignRiskFlag] = []

    d_m = inputs.rod_diameter_mm / 1000.0
    L = inputs.rod_length_m
    R = (inputs.soil_resistivity_ohm_m / (2 * math.pi * L)) * (math.log(4 * L / d_m) - 1)

    terms: list[Term] = [
        Term("Earth electrode resistance", R, unit="ohm", note="Dwight's formula: (rho/(2*pi*L))*(ln(4L/d)-1)"),
    ]

    utilisation = R / inputs.target_earth_resistance_ohms
    terms.append(Term("Utilisation", utilisation, note=f"R/target -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"))

    if utilisation > 1.0:
        warnings.append(
            f"FAILS: earth electrode resistance ({R:.2f} ohm) exceeds the target ({inputs.target_earth_resistance_ohms:.2f} ohm)."
        )
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Earth electrode resistance ({R:.2f} ohm) exceeds the target maximum ({inputs.target_earth_resistance_ohms:.2f} ohm).",
            trigger=f"R={R:.2f}ohm > target={inputs.target_earth_resistance_ohms:.2f}ohm",
            recommended_action="Drive a longer rod, use multiple rods (professionally designed for mutual coupling, not this module's answer divided by N), or improve soil conductivity (e.g. bentonite backfill) -- get a competent person to design a multi-electrode arrangement if a single rod cannot meet the target.",
            source_reference="electrical_lv_earth_electrode_resistance",
        ))

    headline = Term(
        "Utilisation", utilisation,
        note=("PASS" if utilisation <= 1.0 else "FAIL") + " -- earth electrode resistance/target (Dwight's formula, single rod)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Dwight's formula (1936) for a single vertical driven earth rod, checked against a target earth resistance",
        references=[
            "BS 7430, Code of practice for protective earthing of electrical installations -- Annex, single rod electrode resistance.",
            "IEEE Std 142 (Green Book), Recommended Practice for Grounding of Industrial and Commercial Power Systems.",
            "Dwight, H.B., 1936 -- 'Calculation of Resistances to Ground', AIEE Transactions.",
        ],
    )


MODULE = CalcModule(
    key="electrical_lv_earth_electrode_resistance",
    name="Earth Electrode Resistance (Single Rod, Dwight's Formula)",
    discipline="Electrical (LV)",
    description=(
        "R = (rho/(2*pi*L))*(ln(4L/d)-1) for a single vertical driven earth rod, checked against a target "
        "earth resistance. Single rod only -- does not cover multiple rods, mesh/grid electrodes, or HV "
        "substation earthing, see module docstring."
    ),
    input_model=EarthElectrodeResistanceInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_lv.earth_electrode_resistance
    example = EarthElectrodeResistanceInput(
        soil_resistivity_ohm_m=100.0,
        rod_length_m=3.0,
        rod_diameter_mm=16.0,
        target_earth_resistance_ohms=20.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
