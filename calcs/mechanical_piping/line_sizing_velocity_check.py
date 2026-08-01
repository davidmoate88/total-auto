"""
Pipe line sizing / velocity and erosional velocity check — answers
`pipe_sizing_and_flow`'s "Line sizing / velocity check"
`CalculationRequirement` in `basis_of_design/mechanical_piping.py`. The
first `calcs/mechanical_piping/` module.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Scoped to VELOCITY AND EROSIONAL VELOCITY only, not pressure drop -- the
CalculationRequirement names both, but pressure drop (Darcy-Weisbach with a
Colebrook-White/Moody friction factor) is a distinct, more involved
calculation with its own genuinely iterative solution method, deliberately
left for a separate future module rather than folded in here and done
half-way.

`actual_internal_diameter_mm` is a required direct input -- standard pipe
schedule internal diameters come from ASME B36.10M tables (wall thickness
by nominal size/schedule), which this module does NOT embed, for the same
"flag, don't guess" reasoning as `cable_sizing_voltage_drop.py`'s tabulated
cable current rating. Look up the actual internal diameter for the
selected nominal pipe size/schedule and supply it directly.

Method summary
--------------
Actual velocity from flow rate and the supplied internal diameter:

    V = Q / A,   A = pi/4 * D^2

Erosional velocity limit, API RP 14E (`Ve = C/sqrt(rho)`, in imperial units
natively -- density is converted to lb/ft^3 using the exact physical unit
conversion 1 kg/m^3 = 0.062428 lb/ft^3, then the resulting ft/s result is
converted back to m/s using the exact conversion 1 ft = 0.3048 m; only the
empirical constant C itself, not the unit conversion, is a direct input):

    Ve (ft/s) = C / sqrt(rho_lb_ft3)
    Ve (m/s)  = Ve (ft/s) * 0.3048

C is a required direct input (illustrative default 100, API RP 14E's
typical value for continuous service -- 125 is commonly cited for
intermittent service; this is fluid/service-dependent, not a fixed
constant, matching this discipline's own "Erosional velocity limit"
criterion, which states there is no single project-wide figure).

Actual velocity is checked against the erosional limit (hard limit,
critical if exceeded) and against a target velocity range (soft guidance,
`buildability` flag if outside -- too slow risks settling/fouling, too
fast-but-below-erosional risks excess pressure drop/noise/vibration,
neither is an immediate safety issue the way exceeding the erosional limit
is).

Known simplifications / not implemented (see Warnings in the result):
- Pressure drop is NOT calculated -- velocity and erosional velocity only,
  see above.
- `actual_internal_diameter_mm` is a required direct input, not derived
  from a nominal pipe size/schedule -- see above.
- Single-phase flow only -- two-phase sizing methodology is explicitly
  excluded from this discipline's scope in the BoD.
- API RP 14E's erosional velocity guidance is itself contested in later
  practice for some services (sometimes considered overly conservative) --
  treat as an illustrative screening check, not a definitive erosion-rate
  prediction.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

KG_M3_TO_LB_FT3 = 0.062428  # exact physical unit conversion
FT_TO_M = 0.3048  # exact physical unit conversion


class LineSizingVelocityCheckInput(BaseModel):
    flow_rate_m3_h: float = Field(..., gt=0, description="Volumetric flow rate, Q (m^3/h).")
    actual_internal_diameter_mm: float = Field(..., gt=0, description="Actual/selected pipe internal diameter (mm) -- from ASME B36.10M for the chosen nominal size/schedule. Not derived by this module, see module docstring.")
    fluid_density_kg_m3: float = Field(..., gt=0, description="Fluid density, rho (kg/m^3).")
    erosional_velocity_constant_c: float = Field(100.0, gt=0, description="API RP 14E empirical constant, C -- illustrative default 100 (continuous service); 125 is commonly cited for intermittent service. Fluid/service-dependent, confirm per project.")
    min_target_velocity_m_s: float = Field(3.0, gt=0, description="Minimum target design velocity (m/s) -- illustrative, matches this discipline's own 'Target liquid velocity' criterion range (3-5 m/s). Below this risks settling/fouling.")
    max_target_velocity_m_s: float = Field(5.0, gt=0, description="Maximum target design velocity (m/s) -- illustrative, matches this discipline's own 'Target liquid velocity' criterion range (3-5 m/s). Above this (but below the erosional limit) risks excess pressure drop/noise/vibration.")


def calculate(inputs: LineSizingVelocityCheckInput) -> CalcResult:
    warnings: list[str] = [
        "Pressure drop is NOT calculated -- velocity and erosional velocity only. See module docstring.",
        "actual_internal_diameter_mm is a required direct input from ASME B36.10M -- not derived from a "
        "nominal pipe size/schedule by this module.",
        "API RP 14E's erosional velocity guidance is itself contested in later practice for some services -- "
        "treat as an illustrative screening check.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    Q_m3_s = inputs.flow_rate_m3_h / 3600.0
    D_m = inputs.actual_internal_diameter_mm / 1000.0
    A = math.pi / 4 * D_m**2
    V = Q_m3_s / A

    rho_lb_ft3 = inputs.fluid_density_kg_m3 * KG_M3_TO_LB_FT3
    Ve_ft_s = inputs.erosional_velocity_constant_c / math.sqrt(rho_lb_ft3)
    Ve_m_s = Ve_ft_s * FT_TO_M

    erosional_utilisation = V / Ve_m_s

    terms: list[Term] = [
        Term("Actual velocity", V, unit="m/s", note="Q/A"),
        Term("Erosional velocity limit", Ve_m_s, unit="m/s", note="API RP 14E, C/sqrt(rho)"),
        Term("Erosional utilisation", erosional_utilisation, note=f"V/Ve -- {'PASS' if erosional_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"),
    ]

    if erosional_utilisation > 1.0:
        warnings.append(f"FAILS: actual velocity ({V:.2f} m/s) exceeds the erosional velocity limit ({Ve_m_s:.2f} m/s).")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Actual velocity ({V:.2f} m/s) exceeds the API RP 14E erosional velocity limit ({Ve_m_s:.2f} m/s) -- erosion/wall-thinning risk.",
            trigger=f"V={V:.2f}m/s > Ve={Ve_m_s:.2f}m/s",
            recommended_action="Increase pipe diameter to reduce velocity, or confirm the erosional velocity constant C is appropriate for the actual service.",
            source_reference="mechanical_piping_line_sizing_velocity_check",
        ))

    outside_target_range = not (inputs.min_target_velocity_m_s <= V <= inputs.max_target_velocity_m_s)
    if outside_target_range:
        direction = "below the minimum" if V < inputs.min_target_velocity_m_s else "above the maximum"
        warnings.append(f"Actual velocity ({V:.2f} m/s) is {direction} target range ({inputs.min_target_velocity_m_s}-{inputs.max_target_velocity_m_s} m/s).")
        risk_flags.append(DesignRiskFlag(
            category="buildability", severity="low",
            description=f"Actual velocity ({V:.2f} m/s) is {direction} the target design range ({inputs.min_target_velocity_m_s}-{inputs.max_target_velocity_m_s} m/s).",
            trigger=f"V={V:.2f}m/s outside [{inputs.min_target_velocity_m_s}, {inputs.max_target_velocity_m_s}]m/s",
            recommended_action="Below target: check for settling/fouling risk. Above target (but below erosional): check pressure drop, noise, and vibration implications.",
            source_reference="mechanical_piping_line_sizing_velocity_check",
        ))

    headline = Term(
        "Erosional utilisation", erosional_utilisation,
        note=("PASS" if erosional_utilisation <= 1.0 else "FAIL") + " -- actual velocity/erosional velocity limit (API RP 14E)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Actual velocity from flow rate/internal diameter, checked against the API RP 14E erosional velocity limit and a target velocity range",
        references=[
            "API RP 14E, Recommended Practice for Design and Installation of Offshore Production Platform Piping Systems -- erosional velocity guidance.",
            "ASME B31.3, Process Piping.",
        ],
    )


MODULE = CalcModule(
    key="mechanical_piping_line_sizing_velocity_check",
    name="Pipe Line Sizing / Velocity Check (API RP 14E)",
    discipline="Mechanical Piping",
    description=(
        "Actual velocity from flow rate/internal diameter, checked against the API RP 14E erosional velocity "
        "limit and a target velocity range. Pressure drop is not calculated -- velocity/erosion only, see "
        "module docstring."
    ),
    input_model=LineSizingVelocityCheckInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.mechanical_piping.line_sizing_velocity_check
    example = LineSizingVelocityCheckInput(
        flow_rate_m3_h=100.0,
        actual_internal_diameter_mm=100.0,
        fluid_density_kg_m3=1000.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
