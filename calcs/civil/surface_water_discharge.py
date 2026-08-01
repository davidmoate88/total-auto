"""
Surface water discharge rate check and flow control orifice sizing. Answers
`surface_water_drainage_suds`'s "Discharge rate calculation"
`CalculationRequirement` in `basis_of_design/civils.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module deliberately does NOT derive the permitted/greenfield discharge
rate itself (e.g. via the IH124 method, QBAR = 0.00108*AREA^0.89*SAAR^1.17*
SOIL^2.17, or the ICP SuDS Manual method) -- that calculation needs
site-specific SAAR/SOIL data normally sourced from the FEH (Flood Estimation
Handbook) webservice, and this author was not confident enough in the exact
empirical coefficients to embed them as fact (unlike, say, the Rankine or
Manning's formulae elsewhere in this repo, which are simple enough to
verify independently). `permitted_discharge_rate_l_s` is therefore a
REQUIRED DIRECT INPUT -- obtain it from the FEH webservice, a IH124/ICP SuDS
Manual calculation done externally, or the Lead Local Flood Authority's
stated rate, and supply it directly.

What this module DOES calculate, with higher confidence, is what a real
drainage design needs once that rate is known: whether it meets the common
LLFA practical minimum, and the flow control orifice size needed to achieve
it -- both well-established, verifiable hydraulics, unlike the empirical
runoff-rate methods above.

Method summary
--------------
Discharge rate per hectare (for comparison against an LLFA rate cap
expressed per hectare):

    rate_per_ha = permitted_discharge_rate_l_s / site_area_ha

Flow control orifice sizing (sharp-edged circular orifice, standard
hydraulics):

    Q = Cd * A * sqrt(2*g*h)   =>   A = Q / (Cd*sqrt(2*g*h))
    diameter = sqrt(4*A/pi)

using Cd = 0.61 (standard discharge coefficient for a thin sharp-edged
circular orifice) by default, at the design head h (depth of water above
the orifice centreline at the attenuation feature's maximum operating
level).

Known simplifications / not implemented (see Warnings in the result):
- permitted_discharge_rate_l_s is a direct input, not derived -- see above.
  This module does not compute a greenfield/brownfield runoff rate.
- Attenuation volume sizing (the storage required to limit discharge to
  this rate across the design storm envelope) is a SEPARATE
  `CalculationRequirement` in the same BoD section and is NOT built --
  needs the FSR/FEH rainfall depth-duration-frequency model, a distinct
  empirical dataset this module does not have. Tracked as an open item.
- The practical minimum discharge (default 5 l/s) and minimum practical
  orifice diameter (default 75mm, below which a vortex flow control device
  such as a Hydro-Brake is typically used instead of a plain orifice plate)
  are illustrative defaults commonly cited in UK SuDS guidance -- confirm
  against the specific LLFA's current standing advice.
- A single circular sharp-edged orifice only -- no vortex flow control
  device (Hydro-Brake) performance curve, no multi-stage control.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

GRAVITY_M_S2 = 9.81
SHARP_EDGED_ORIFICE_CD = 0.61  # standard discharge coefficient, thin sharp-edged circular orifice


class SurfaceWaterDischargeInput(BaseModel):
    permitted_discharge_rate_l_s: float = Field(
        ..., gt=0,
        description="Agreed/permitted discharge rate (l/s) -- from an external FEH/IH124/ICP SuDS Manual calculation or the LLFA's stated rate. NOT derived by this module -- see module docstring.",
    )
    site_area_ha: float = Field(..., gt=0, description="Total site area (hectares) -- for expressing the rate per hectare.")
    minimum_practical_discharge_l_s: float = Field(5.0, gt=0, description="Typical LLFA practical minimum discharge rate (l/s), regardless of the calculated permitted rate -- confirm against the specific LLFA's current standing advice.")

    design_head_m: float = Field(..., gt=0, description="Depth of water above the orifice centreline at the attenuation feature's maximum operating (design) water level, h (m).")
    discharge_coefficient: float = Field(SHARP_EDGED_ORIFICE_CD, gt=0, le=1.0, description="Orifice discharge coefficient, Cd -- 0.61 is standard for a thin sharp-edged circular orifice.")
    minimum_practical_orifice_diameter_mm: float = Field(75.0, gt=0, description="Below this, a plain orifice plate is typically considered impractical (blockage risk) and a vortex flow control device (e.g. Hydro-Brake) is used instead -- confirm against the specific product/guidance in use.")


def calculate(inputs: SurfaceWaterDischargeInput) -> CalcResult:
    warnings: list[str] = [
        "permitted_discharge_rate_l_s is a direct input, not derived -- this module does not "
        "compute a greenfield/brownfield runoff rate. See module docstring.",
        "Attenuation volume sizing (storage required to limit discharge to this rate) is a "
        "separate, NOT YET BUILT calc -- needs the FSR/FEH rainfall depth-duration-frequency "
        "model. Tracked as an open item.",
        "Single circular sharp-edged orifice only -- no vortex flow control device (Hydro-Brake) "
        "performance curve.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    rate_per_ha = inputs.permitted_discharge_rate_l_s / inputs.site_area_ha
    terms: list[Term] = [
        Term("Discharge rate per hectare", rate_per_ha, unit="l/s/ha", note="permitted rate / site area"),
    ]

    if inputs.permitted_discharge_rate_l_s < inputs.minimum_practical_discharge_l_s:
        warnings.append(
            f"Permitted discharge rate ({inputs.permitted_discharge_rate_l_s:g} l/s) is below the "
            f"typical LLFA practical minimum ({inputs.minimum_practical_discharge_l_s:g} l/s) -- "
            "confirm whether the LLFA will accept the calculated rate or require the practical minimum instead."
        )
        risk_flags.append(
            DesignRiskFlag(
                category="code_compliance",
                severity="medium",
                description=f"Permitted discharge rate ({inputs.permitted_discharge_rate_l_s:g} l/s) is below the typical LLFA practical minimum ({inputs.minimum_practical_discharge_l_s:g} l/s).",
                trigger=f"permitted_discharge_rate_l_s ({inputs.permitted_discharge_rate_l_s:g}) < minimum_practical_discharge_l_s ({inputs.minimum_practical_discharge_l_s:g})",
                recommended_action="Confirm the applicable minimum discharge rate with the LLFA before finalising the flow control design.",
                source_reference="civil_surface_water_discharge_rate",
            )
        )

    Q_m3_s = inputs.permitted_discharge_rate_l_s / 1000.0
    A_m2 = Q_m3_s / (inputs.discharge_coefficient * math.sqrt(2 * GRAVITY_M_S2 * inputs.design_head_m))
    diameter_mm = math.sqrt(4 * A_m2 / math.pi) * 1000.0

    terms.append(Term("Required orifice area", A_m2, unit="m^2", note="Q / (Cd*sqrt(2*g*h))"))
    terms.append(Term("Required orifice diameter", diameter_mm, unit="mm"))

    if diameter_mm < inputs.minimum_practical_orifice_diameter_mm:
        warnings.append(
            f"Required orifice diameter ({diameter_mm:.1f} mm) is below the practical minimum "
            f"({inputs.minimum_practical_orifice_diameter_mm:g} mm) -- consider a vortex flow "
            "control device (e.g. Hydro-Brake) instead of a plain orifice plate to reduce blockage risk."
        )
        risk_flags.append(
            DesignRiskFlag(
                category="buildability",
                severity="medium",
                description=f"Required orifice diameter ({diameter_mm:.1f} mm) is below the practical minimum ({inputs.minimum_practical_orifice_diameter_mm:g} mm) -- blockage risk.",
                trigger=f"diameter ({diameter_mm:.1f}mm) < minimum_practical_orifice_diameter_mm ({inputs.minimum_practical_orifice_diameter_mm:g}mm)",
                recommended_action="Consider a vortex flow control device (e.g. Hydro-Brake) instead of a plain orifice plate.",
                source_reference="civil_surface_water_discharge_rate",
            )
        )

    headline = Term(
        "Required orifice diameter", diameter_mm, unit="mm",
        note=f"For {inputs.permitted_discharge_rate_l_s:g} l/s at {inputs.design_head_m:g}m head, Cd={inputs.discharge_coefficient:g}",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Surface water discharge rate check and sharp-edged orifice flow control sizing",
        references=[
            "CIRIA C753, The SuDS Manual.",
            "Standard sharp-edged orifice discharge equation, Q = Cd*A*sqrt(2*g*h) -- near-universal in hydraulics texts.",
        ],
    )


MODULE = CalcModule(
    key="civil_surface_water_discharge_rate",
    name="Surface Water Discharge Rate Check and Orifice Sizing",
    discipline="Civils",
    description=(
        "Practical-minimum discharge check and flow control orifice sizing from a permitted "
        "discharge rate (supplied directly, e.g. from an external FEH/IH124 calculation)."
    ),
    input_model=SurfaceWaterDischargeInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.civil.surface_water_discharge
    example = SurfaceWaterDischargeInput(
        permitted_discharge_rate_l_s=12.0,
        site_area_ha=2.5,
        design_head_m=1.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
