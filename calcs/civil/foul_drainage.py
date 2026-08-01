"""
Foul drainage flow and pipe capacity check — population/occupancy-based peak
flow, Manning's equation pipe capacity, self-cleansing velocity check.
Answers `foul_drainage`'s "Foul flow calculation" `CalculationRequirement`
("Peak foul flow from occupancy/use, pipe sizing") in
`basis_of_design/civils.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Unlike the Eurocode-based modules in this repo, UK foul sewer design does
not have a single governing Eurocode -- it follows Sewers for Adoption /
water company Design and Construction Guidance (DCG), built from common UK
drainage-engineering practice, not read from a specific current standard
text. Two specific method choices matter here:
- PIPE CAPACITY uses MANNING'S EQUATION, a simplified/preliminary method.
  Sewers for Adoption / most UK water company DCGs formally require the
  Colebrook-White equation (via WRc/HR Wallingford charts, or proprietary
  drainage design software) for adoptable sewer design -- Manning's and
  Colebrook-White do not always agree, especially at partial flow depths.
  Use this module for a basis-of-design-level preliminary check only; run
  a Colebrook-White-based check (or use proprietary drainage software) for
  a submission-ready adoptable design.
- The PEAK FLOW FACTOR (default 6x dry weather flow) is a commonly-cited
  simplification for small-to-medium UK developments, not a fixed value in
  any single standard -- Sewers for Adoption/water company DCGs may specify
  a different figure (sometimes population-dependent, e.g. via Harmon's
  formula), and per-capita flow rates vary by water company/Building
  Regulations Part G. Both are direct inputs with illustrative defaults --
  confirm against the servicing water company's current DCG before real use.

Method summary
--------------
Dry weather flow (DWF):

    DWF = population * per_capita_flow_l_per_day / 86400 + trade_effluent_l_s

Peak foul flow (infiltration added after peaking, since it's a steady-state
ingress not driven by occupancy):

    Qp = DWF * peak_flow_factor + infiltration_allowance_l_s

Pipe full-bore capacity (Manning's equation, circular pipe flowing full):

    A = pi*D^2/4,  R = D/4  (hydraulic radius, full-bore circular pipe)
    V = (1/n) * R^(2/3) * S^(1/2)
    Q_capacity = V * A

checked against Qp for a utilisation, with a separate check that V meets the
minimum self-cleansing velocity (0.75 m/s, matching this discipline's own
BoD criterion).

Known simplifications / not implemented (see Warnings in the result):
- Manning's equation, not Colebrook-White -- see above.
- Full-bore flow only -- no partial-flow-depth proportional velocity/capacity
  check (a pipe often doesn't need to flow full to achieve self-cleansing
  velocity; conversely a part-full pipe can have a lower velocity than the
  full-bore value calculated here). A full partial-flow analysis needs the
  proportional depth/velocity/discharge charts this module does not
  reproduce.
- No time-of-concentration/hydraulic gradeline check across a network --
  this checks ONE pipe run in isolation.
- Trade effluent and infiltration are user-supplied allowances, not derived
  from a trade effluent consent calculation or an infiltration test.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

MINIMUM_SELF_CLEANSING_VELOCITY_M_S = 0.75  # matches this discipline's own BoD criterion


class FoulDrainageInput(BaseModel):
    population_served: float = Field(..., gt=0, description="Population (or population equivalent) served, P.")
    per_capita_flow_l_per_day: float = Field(150.0, gt=0, description="Per-capita domestic flow allowance (l/head/day) -- confirm against the servicing water company's DCG/Building Regulations Part G.")
    trade_effluent_l_s: float = Field(0.0, ge=0, description="Characteristic trade effluent flow, added to DWF before peaking (l/s).")
    infiltration_allowance_l_s: float = Field(0.0, ge=0, description="Infiltration allowance, added AFTER peaking (steady-state ingress, not occupancy-driven) (l/s).")
    peak_flow_factor: float = Field(6.0, gt=1.0, description="Peak flow multiplier on DWF -- illustrative default, confirm against the servicing water company's DCG (may be population-dependent).")

    pipe_diameter_mm: float = Field(..., gt=0, description="Pipe internal diameter, D (mm).")
    pipe_gradient: float = Field(..., gt=0, lt=1.0, description="Pipe gradient as a decimal fraction, S (e.g. 1 in 80 = 0.0125).")
    mannings_n: float = Field(0.010, gt=0, description="Manning's roughness coefficient -- 0.010 is a standard value for smooth (uPVC/vitrified clay) pipes.")


def calculate(inputs: FoulDrainageInput) -> CalcResult:
    warnings: list[str] = [
        "Pipe capacity uses Manning's equation, a simplified/preliminary method -- Sewers for "
        "Adoption / most UK water company DCGs formally require Colebrook-White for adoptable "
        "sewer design. Use this for a basis-of-design-level check only -- see module docstring.",
        "peak_flow_factor and per_capita_flow_l_per_day are illustrative defaults -- confirm "
        "against the servicing water company's current Design and Construction Guidance.",
        "Full-bore flow only -- no partial-flow-depth proportional velocity/capacity check.",
        "Checks ONE pipe run in isolation -- no network hydraulic gradeline check.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    DWF_l_s = inputs.population_served * inputs.per_capita_flow_l_per_day / 86400.0 + inputs.trade_effluent_l_s
    Qp_l_s = DWF_l_s * inputs.peak_flow_factor + inputs.infiltration_allowance_l_s

    terms: list[Term] = [
        Term("DWF (dry weather flow)", DWF_l_s, unit="l/s", note="population*per_capita/86400 + trade_effluent"),
        Term("Qp (peak foul flow)", Qp_l_s, unit="l/s", note="DWF*peak_flow_factor + infiltration"),
    ]

    D_m = inputs.pipe_diameter_mm / 1000.0
    A = math.pi * D_m**2 / 4
    R = D_m / 4
    V = (1 / inputs.mannings_n) * R ** (2 / 3) * inputs.pipe_gradient ** 0.5
    Q_capacity_m3_s = V * A
    Q_capacity_l_s = Q_capacity_m3_s * 1000.0

    terms.append(Term("A (full-bore area)", A, unit="m^2"))
    terms.append(Term("R (hydraulic radius)", R, unit="m", note="D/4, full-bore circular pipe"))
    terms.append(Term("V (full-bore velocity)", V, unit="m/s", note="Manning's equation"))
    terms.append(Term("Q capacity (full-bore)", Q_capacity_l_s, unit="l/s"))

    if V < MINIMUM_SELF_CLEANSING_VELOCITY_M_S:
        warnings.append(
            f"Full-bore velocity ({V:.2f} m/s) is below the minimum self-cleansing velocity "
            f"({MINIMUM_SELF_CLEANSING_VELOCITY_M_S} m/s) -- risk of sedimentation/blockage. "
            "Increase gradient or reduce diameter."
        )
        risk_flags.append(
            DesignRiskFlag(
                category="code_compliance",
                severity="medium",
                description=f"Full-bore velocity ({V:.2f} m/s) is below the minimum self-cleansing velocity ({MINIMUM_SELF_CLEANSING_VELOCITY_M_S} m/s).",
                trigger=f"V={V:.2f}m/s < {MINIMUM_SELF_CLEANSING_VELOCITY_M_S}m/s",
                recommended_action="Increase pipe gradient or reduce diameter to raise full-bore velocity above the minimum.",
                source_reference="civil_foul_drainage_flow",
            )
        )

    utilisation = Qp_l_s / Q_capacity_l_s
    terms.append(
        Term(
            "Utilisation", utilisation,
            note=f"Qp/Q capacity -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
        )
    )
    if utilisation > 1.0:
        warnings.append(f"Pipe capacity check FAILS: utilisation = {utilisation:.2f}.")
        risk_flags.append(
            DesignRiskFlag(
                category="code_compliance",
                severity="critical",
                description=f"Peak foul flow exceeds full-bore pipe capacity: utilisation = {utilisation:.2f}.",
                trigger=f"Qp={Qp_l_s:.2f}l/s > Q capacity={Q_capacity_l_s:.2f}l/s",
                recommended_action="Increase pipe diameter/gradient or review the flow generation assumptions.",
                source_reference="civil_foul_drainage_flow",
            )
        )

    headline = Term(
        "Utilisation", utilisation,
        note=("PASS" if utilisation <= 1.0 else "FAIL") + " -- Qp/Q capacity (full-bore, Manning's equation)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Population-based peak foul flow, Manning's equation full-bore pipe capacity check",
        references=[
            "Sewers for Adoption (current edition per servicing water company) — governing UK adoptable sewer design guidance.",
            "BS EN 752, Drain and sewer systems outside buildings.",
            "Manning, R., 1891 — classical open-channel/pipe flow formula, near-universally reproduced (preliminary/simplified alternative to Colebrook-White here — see module docstring).",
        ],
    )


MODULE = CalcModule(
    key="civil_foul_drainage_flow",
    name="Foul Drainage Flow and Pipe Capacity Check",
    discipline="Civils",
    description=(
        "Population-based peak foul flow and Manning's-equation full-bore pipe capacity/"
        "self-cleansing velocity check for one pipe run. Preliminary/basis-of-design level -- "
        "Sewers for Adoption formally requires Colebrook-White for adoptable design."
    ),
    input_model=FoulDrainageInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.civil.foul_drainage
    example = FoulDrainageInput(
        population_served=250,
        pipe_diameter_mm=150,
        pipe_gradient=1 / 80,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
