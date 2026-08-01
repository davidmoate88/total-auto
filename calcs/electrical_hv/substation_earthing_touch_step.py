"""
Substation earth grid resistance and touch/step potential compliance
check — IEEE 80 / BS EN 50522. Answers `hv_earthing_and_touch_step_potential`'s
"Touch/step potential limits" and "Substation earth resistance target"
`DesignCriterion` entries in `basis_of_design/electrical_hv.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
IEEE 80 substation earth grid design splits into two genuinely different
tiers of confidence, and this module treats them differently on purpose:

1. TOLERABLE touch/step voltage limits (body-resistance-based formulas,
   IEEE 80 Eq 27/32/33-family) and grid resistance to remote earth
   (Sverak's simplified formula) are among the most consistently
   reproduced equations in grounding design literature -- comparable in
   universality to `earth_electrode_resistance.py`'s Dwight formula or
   `protection_grading.py`'s IEC 60255-151 curve constants. They are
   EMBEDDED here directly, with the same "verify before use" caveat as
   every constant in this repo, not made a required input.

2. The ACTUAL mesh (touch) voltage and step voltage AT THE GRID are a
   completely different matter -- deriving them needs IEEE 80's geometric
   correction factors (Km, Ks, Kii, Kh, the irregularity factor n, corner-
   vs-edge-vs-interior mesh corrections), a genuinely complex, multi-case
   empirical procedure this author does not have confident, generalisable
   recall of -- the same "flag, don't guess" reasoning as
   `beam_column_interaction.py`'s Annex A/B k-factors and IEEE 1584's
   incident energy model. `actual_mesh_voltage_v` and `actual_step_voltage_v`
   are therefore REQUIRED direct inputs from a proper external IEEE 80/
   BS EN 50522 grid study -- this module does NOT derive them from grid
   geometry.

Method summary
--------------
Grid resistance to remote earth, Sverak's simplified formula (grid
conductors + rods combined into one total buried length):

    Rg = rho * [1/Lt + (1/sqrt(20*A)) * (1 + 1/(1 + h*sqrt(20/A)))]

checked against a target grid resistance (project-specific, required
direct input, matching this section's "Substation earth resistance target"
criterion -- no single fixed value applies).

Surface layer derating factor and tolerable touch/step voltage (IEEE 80,
for a person of the stated body weight):

    Cs = 1 - 0.09*(1 - rho/rho_s) / (2*hs + 0.09)

    50kg:  E_touch = (1000 + 1.5*Cs*rho_s) * 0.116/sqrt(ts)
           E_step  = (1000 + 6.0*Cs*rho_s) * 0.116/sqrt(ts)
    70kg:  E_touch = (1000 + 1.5*Cs*rho_s) * 0.157/sqrt(ts)
           E_step  = (1000 + 6.0*Cs*rho_s) * 0.157/sqrt(ts)

where rho is the native soil resistivity, rho_s/hs are the surface layer
(e.g. crushed rock) resistivity/thickness, and ts is the fault clearance
time. The externally-supplied actual mesh/step voltages are checked
against these tolerable limits.

Known simplifications / not implemented (see Warnings in the result):
- actual_mesh_voltage_v/actual_step_voltage_v are required direct inputs
  from a proper external grid study -- NOT derived from grid geometry, see
  above.
- Sverak's formula is a reasonable single-equation ESTIMATE for a fairly
  uniform, roughly rectangular grid -- not valid for highly irregular grid
  shapes, where the more detailed Schwarz method (separate grid+rod
  system equations) would be needed for real accuracy.
- Uniform soil resistivity assumed (no multi-layer soil model).
- Does not compute ground potential rise (GPR) or transferred/rise-of-
  earth-potential (REOP) risk to telecoms/other networks -- REOP is
  already explicitly excluded from this section's scope in the BoD.
- Does not select surfacing material or determine required surface layer
  thickness -- rho_s and hs are direct inputs.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

BODY_WEIGHT_CONSTANTS: dict[int, float] = {50: 0.116, 70: 0.157}  # IEEE 80 -- k in E = (...)*k/sqrt(ts)


class SubstationEarthingTouchStepInput(BaseModel):
    soil_resistivity_ohm_m: float = Field(..., gt=0, description="Native soil resistivity, rho (ohm.m) -- from calcs/geotechnical/ or a Wenner resistivity test.")
    grid_area_m2: float = Field(..., gt=0, description="Plan area enclosed by the earth grid, A (m^2).")
    total_buried_conductor_length_m: float = Field(..., gt=0, description="Total buried conductor length, Lt (m) -- grid conductors plus any earth rods, combined.")
    burial_depth_m: float = Field(..., gt=0, description="Grid conductor burial depth, h (m).")
    target_grid_resistance_ohms: float = Field(..., gt=0, description="Target maximum grid resistance to remote earth (ohm) -- project-specific, matches this section's 'Substation earth resistance target' criterion. No single fixed value applies.")

    surface_layer_resistivity_ohm_m: float = Field(..., gt=0, description="Resistivity of the surface layer material (e.g. crushed rock/gravel surfacing), rho_s (ohm.m).")
    surface_layer_thickness_m: float = Field(..., gt=0, description="Surface layer thickness, hs (m).")
    fault_clearance_time_s: float = Field(..., gt=0, description="Fault clearance time, ts (s) -- from the protection grading study, e.g. calcs/electrical_hv/protection_grading.py.")
    body_weight_kg: Literal[50, 70] = Field(50, description="IEEE 80 body weight case for the tolerable touch/step voltage formulas.")

    actual_mesh_voltage_v: float = Field(..., gt=0, description="Actual mesh (touch) voltage at the grid, Em (V) -- from a proper external IEEE 80/BS EN 50522 grid study. NOT derived by this module, see module docstring.")
    actual_step_voltage_v: float = Field(..., gt=0, description="Actual step voltage at the grid, Es (V) -- from a proper external IEEE 80/BS EN 50522 grid study. NOT derived by this module, see module docstring.")


def calculate(inputs: SubstationEarthingTouchStepInput) -> CalcResult:
    warnings: list[str] = [
        "actual_mesh_voltage_v and actual_step_voltage_v are required direct inputs from a proper external "
        "IEEE 80/BS EN 50522 grid study -- this module does NOT derive them from grid geometry (the Km/Ks/Kii/Kh "
        "geometric correction factors are genuinely complex and not reproduced here). See module docstring.",
        "Grid resistance uses Sverak's simplified formula -- a reasonable estimate for a fairly uniform, "
        "roughly rectangular grid, not a substitute for the Schwarz method on a highly irregular grid shape.",
        "Uniform soil resistivity assumed -- no multi-layer soil model.",
        "Does not compute ground potential rise (GPR) or transferred/rise-of-earth-potential (REOP) risk -- "
        "REOP is already excluded from this section's scope.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    A = inputs.grid_area_m2
    Lt = inputs.total_buried_conductor_length_m
    h = inputs.burial_depth_m
    rho = inputs.soil_resistivity_ohm_m
    Rg = rho * (1 / Lt + (1 / math.sqrt(20 * A)) * (1 + 1 / (1 + h * math.sqrt(20 / A))))
    grid_utilisation = Rg / inputs.target_grid_resistance_ohms

    terms: list[Term] = [
        Term("Grid resistance to remote earth", Rg, unit="ohm", note="Sverak's formula"),
        Term("Grid resistance utilisation", grid_utilisation, note=f"Rg/target -- {'PASS' if grid_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"),
    ]

    rho_s = inputs.surface_layer_resistivity_ohm_m
    hs = inputs.surface_layer_thickness_m
    ts = inputs.fault_clearance_time_s
    Cs = 1 - 0.09 * (1 - rho / rho_s) / (2 * hs + 0.09)
    k = BODY_WEIGHT_CONSTANTS[inputs.body_weight_kg]
    E_touch_tolerable = (1000 + 1.5 * Cs * rho_s) * k / math.sqrt(ts)
    E_step_tolerable = (1000 + 6.0 * Cs * rho_s) * k / math.sqrt(ts)

    touch_utilisation = inputs.actual_mesh_voltage_v / E_touch_tolerable
    step_utilisation = inputs.actual_step_voltage_v / E_step_tolerable

    terms.append(Term("Cs (surface layer derating factor)", Cs))
    terms.append(Term("Tolerable touch voltage", E_touch_tolerable, unit="V", note=f"{inputs.body_weight_kg}kg body weight"))
    terms.append(Term("Tolerable step voltage", E_step_tolerable, unit="V", note=f"{inputs.body_weight_kg}kg body weight"))
    terms.append(Term("Touch voltage utilisation", touch_utilisation, note=f"actual/tolerable -- {'PASS' if touch_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"))
    terms.append(Term("Step voltage utilisation", step_utilisation, note=f"actual/tolerable -- {'PASS' if step_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"))

    if grid_utilisation > 1.0:
        warnings.append(f"FAILS grid resistance: {Rg:.3f} ohm exceeds the target ({inputs.target_grid_resistance_ohms:.3f} ohm).")
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Grid resistance ({Rg:.3f} ohm) exceeds the target maximum ({inputs.target_grid_resistance_ohms:.3f} ohm).",
            trigger=f"Rg={Rg:.3f}ohm > target={inputs.target_grid_resistance_ohms:.3f}ohm",
            recommended_action="Increase grid area, add earth rods/conductors (more buried length), or improve soil conductivity.",
            source_reference="electrical_hv_substation_earthing_touch_step",
        ))
    if touch_utilisation > 1.0:
        warnings.append(f"FAILS touch voltage: actual ({inputs.actual_mesh_voltage_v:.1f}V) exceeds tolerable ({E_touch_tolerable:.1f}V).")
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Actual mesh (touch) voltage ({inputs.actual_mesh_voltage_v:.1f}V) exceeds the tolerable limit ({E_touch_tolerable:.1f}V) for a {inputs.body_weight_kg}kg body weight at {ts}s fault clearance.",
            trigger=f"Em={inputs.actual_mesh_voltage_v:.1f}V > tolerable={E_touch_tolerable:.1f}V",
            recommended_action="Reduce grid resistance/GPR (finer mesh spacing, more rods, lower burial resistivity), increase surface layer thickness/resistivity, or reduce fault clearance time.",
            source_reference="electrical_hv_substation_earthing_touch_step",
        ))
    if step_utilisation > 1.0:
        warnings.append(f"FAILS step voltage: actual ({inputs.actual_step_voltage_v:.1f}V) exceeds tolerable ({E_step_tolerable:.1f}V).")
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Actual step voltage ({inputs.actual_step_voltage_v:.1f}V) exceeds the tolerable limit ({E_step_tolerable:.1f}V) for a {inputs.body_weight_kg}kg body weight at {ts}s fault clearance.",
            trigger=f"Es={inputs.actual_step_voltage_v:.1f}V > tolerable={E_step_tolerable:.1f}V",
            recommended_action="Reduce grid resistance/GPR, increase surface layer thickness/resistivity, or reduce fault clearance time.",
            source_reference="electrical_hv_substation_earthing_touch_step",
        ))

    governing = max(grid_utilisation, touch_utilisation, step_utilisation)
    if governing == grid_utilisation:
        governing_check = "grid resistance"
    elif governing == touch_utilisation:
        governing_check = "touch voltage"
    else:
        governing_check = "step voltage"

    headline = Term(
        "Governing utilisation", governing,
        note=("PASS" if governing <= 1.0 else "FAIL") + f" -- max(grid resistance, touch voltage, step voltage), governed by {governing_check}",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Sverak's grid resistance formula + IEEE 80 tolerable touch/step voltage, checked against an externally-supplied actual mesh/step voltage",
        references=[
            "IEEE Std 80, IEEE Guide for Safety in AC Substation Grounding.",
            "BS EN 50522, Earthing of power installations exceeding 1kV AC.",
            "Sverak, J.G., 'Simplified Analysis of Electrical Gradients Above a Ground Grid' -- basis of the grid resistance formula.",
        ],
    )


MODULE = CalcModule(
    key="electrical_hv_substation_earthing_touch_step",
    name="Substation Earth Grid Resistance and Touch/Step Potential Check (IEEE 80, BS EN 50522)",
    discipline="Electrical (HV)",
    description=(
        "Sverak's grid resistance formula and IEEE 80 tolerable touch/step voltage limits, checked against a "
        "target grid resistance and an externally-supplied actual mesh/step voltage. Actual mesh/step voltage "
        "is a required direct input -- this module does not derive it from grid geometry, see module docstring."
    ),
    input_model=SubstationEarthingTouchStepInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_hv.substation_earthing_touch_step
    example = SubstationEarthingTouchStepInput(
        soil_resistivity_ohm_m=100.0,
        grid_area_m2=400.0,
        total_buried_conductor_length_m=200.0,
        burial_depth_m=0.5,
        target_grid_resistance_ohms=5.0,
        surface_layer_resistivity_ohm_m=3000.0,
        surface_layer_thickness_m=0.1,
        fault_clearance_time_s=0.5,
        actual_mesh_voltage_v=400.0,
        actual_step_voltage_v=1500.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
