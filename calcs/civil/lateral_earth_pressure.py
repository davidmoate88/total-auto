"""
Lateral earth pressure calculation — Rankine active/passive theory, EN 1997-1
(Eurocode 7), UK National Annex Design Approach 1. Answers
`retaining_structures`'s "Lateral earth pressure calculation"
`CalculationRequirement` in `basis_of_design/civils.py`, and the section's
declared interface ("Lateral earth pressures and bearing checks — extends
calcs/geotechnical/"). Shares the same `DA1_C1`/`DA1_C2` partial factor sets
as `calcs/geotechnical/bearing_capacity.py` (imported, not redefined) so the
two modules' Design Approach 1 treatment can't drift apart.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from geotechnical-engineering literature/training knowledge, not by
reading the purchased BS EN 1997-1 standard text directly -- same caveat as
`bearing_capacity.py`. Rankine's theory itself (Ka/Kp from phi' alone) is
about as well-established as bearing capacity theory gets, but see Known
simplifications below for what this module does NOT attempt (wall friction,
sloping backfill, tension-crack clipping).

Method summary
--------------
Rankine coefficients (level backfill, vertical wall/backface, no wall
friction):

    Ka = (1 - sin(phi')) / (1 + sin(phi')) = tan^2(45 - phi'/2)
    Kp = (1 + sin(phi')) / (1 - sin(phi')) = tan^2(45 + phi'/2)

Active pressure at depth z (effective stress, before adding hydrostatic
water pressure): sigma_a(z) = Ka*sigma_v'(z) + Ka*q - 2*c'*sqrt(Ka), clipped
at 0 (see Known simplifications). Total pressure adds hydrostatic water
pressure below the water table. The resultant thrust Pa and its height of
application above the base are found by decomposing the (piecewise-linear)
pressure diagram into trapezoidal segments at each breakpoint (top, water
table if present, base) -- exact for the modelled (piecewise-linear)
pressure profile, not a numerical approximation.

Both DA1 combinations are computed (factoring phi'/c' for C2, per
`bearing_capacity.py`'s own pattern) -- the GOVERNING case for an active
thrust is the LARGER value (weaker apparent soil strength under DA1-C2 raises
the active pressure), the opposite direction from a resistance check like
bearing capacity, where the governing case is the smaller (lower) resistance.

Known simplifications / not implemented (see Warnings in the result):
- Rankine's theory only -- no wall friction (delta=0), no battered wall face,
  no sloping backfill. Coulomb's more general theory (which handles all
  three) is not implemented. This is conservative for wall friction (ignoring
  friction that would otherwise reduce the active thrust) but not
  automatically conservative for a sloping backfill or battered wall, which
  this module cannot represent at all -- do not use for either case.
- Single homogeneous soil layer behind the wall (characteristic phi'/c'/gamma)
  -- no multi-layer profile (unlike the ground model interpreter feeding
  `bearing_capacity.py`, there is no equivalent ground-model handoff for this
  calc yet).
- The cohesion term is clipped at zero pressure (rather than excluding a
  proper tension-crack depth z_c = 2c'/(gamma*sqrt(Ka)) from the pressure
  diagram and re-deriving the resultant above that depth) -- exact for c'=0
  (fully frictional backfill, the common/recommended case for retaining wall
  backfill specifically to avoid this issue) and increasingly approximate as
  c' grows relative to gamma*H. A warning is raised whenever clipping occurs.
- No seismic/dynamic earth pressure (Mononobe-Okabe or similar) -- static
  case only.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from calcs.geotechnical.bearing_capacity import DA1_C1, DA1_C2, WATER_UNIT_WEIGHT_KN_M3, PartialFactorSet
from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


def rankine_coefficients(phi_deg: float) -> tuple[float, float]:
    """Ka, Kp per Rankine theory (level backfill, vertical wall, no wall friction)."""
    phi = math.radians(phi_deg)
    Ka = (1 - math.sin(phi)) / (1 + math.sin(phi))
    Kp = (1 + math.sin(phi)) / (1 - math.sin(phi))
    return Ka, Kp


def _active_thrust_and_lever_arm(
    phi_deg: float, c_kpa: float, gamma: float, H: float,
    water_table_depth_m: Optional[float], surcharge_kpa: float,
) -> tuple[float, float, bool]:
    """
    Resultant active thrust Pa (kN/m run) and its height of application above
    the base (m), for depth z measured downward from the top of the retained
    height. Returns (Pa, h_bar, was_clipped).
    """
    Ka, _ = rankine_coefficients(phi_deg)
    cohesion_term = 2 * c_kpa * math.sqrt(Ka)
    was_clipped = False

    def effective_vertical_stress(z: float) -> float:
        if water_table_depth_m is None or z <= water_table_depth_m:
            return gamma * z
        gamma_sub = max(gamma - WATER_UNIT_WEIGHT_KN_M3, 0.0)
        return gamma * water_table_depth_m + gamma_sub * (z - water_table_depth_m)

    def water_pressure(z: float) -> float:
        if water_table_depth_m is None or z <= water_table_depth_m:
            return 0.0
        return WATER_UNIT_WEIGHT_KN_M3 * (z - water_table_depth_m)

    def total_pressure(z: float) -> float:
        nonlocal was_clipped
        raw_effective = Ka * effective_vertical_stress(z) + Ka * surcharge_kpa - cohesion_term
        if raw_effective < 0:
            was_clipped = True
        return max(raw_effective, 0.0) + water_pressure(z)

    breakpoints = sorted(set(
        [0.0, H] + ([water_table_depth_m] if water_table_depth_m is not None and 0 < water_table_depth_m < H else [])
    ))

    total_force = 0.0
    total_moment_about_base = 0.0
    for z1, z2 in zip(breakpoints[:-1], breakpoints[1:]):
        p1, p2 = total_pressure(z1), total_pressure(z2)
        seg_force = (p1 + p2) / 2 * (z2 - z1)
        if p1 + p2 > 0:
            centroid_from_z1 = (z2 - z1) * (p1 + 2 * p2) / (3 * (p1 + p2))
        else:
            centroid_from_z1 = (z2 - z1) / 2
        centroid_depth = z1 + centroid_from_z1
        height_above_base = H - centroid_depth
        total_force += seg_force
        total_moment_about_base += seg_force * height_above_base

    h_bar = total_moment_about_base / total_force if total_force > 0 else 0.0
    return total_force, h_bar, was_clipped


class LateralEarthPressureInput(BaseModel):
    friction_angle_phi_prime_deg: float = Field(..., gt=0, le=45, description="Characteristic effective friction angle of the retained soil, phi' (degrees).")
    cohesion_c_prime_kpa: float = Field(0.0, ge=0, description="Characteristic effective cohesion, c' (kPa). 0 (fully frictional backfill) avoids the tension-crack simplification -- see module docstring.")
    unit_weight_kn_m3: float = Field(..., gt=0, description="Characteristic bulk unit weight of the retained soil, gamma (kN/m^3).")

    wall_height_m: float = Field(..., gt=0, description="Total retained height, H (m).")
    water_table_depth_m: Optional[float] = Field(None, ge=0, description="Depth to water table below the top of the retained height (m). Omit if no water table within the retained height.")
    surcharge_kpa: float = Field(0.0, ge=0, description="Uniform characteristic surcharge at ground surface behind the wall (kPa).")

    @model_validator(mode="after")
    def _check_consistency(self) -> "LateralEarthPressureInput":
        if self.water_table_depth_m is not None and self.water_table_depth_m > self.wall_height_m:
            raise ValueError("water_table_depth_m must be <= wall_height_m (or omitted if below the retained height).")
        return self


def _run_combination(inputs: LateralEarthPressureInput, factors: PartialFactorSet) -> tuple[float, float, float, float, bool]:
    phi_d = math.degrees(math.atan(math.tan(math.radians(inputs.friction_angle_phi_prime_deg)) / factors.gamma_phi))
    c_d = inputs.cohesion_c_prime_kpa / factors.gamma_c
    Pa, h_bar, clipped = _active_thrust_and_lever_arm(
        phi_d, c_d, inputs.unit_weight_kn_m3, inputs.wall_height_m, inputs.water_table_depth_m, inputs.surcharge_kpa,
    )
    return Pa, h_bar, phi_d, c_d, clipped


def calculate(inputs: LateralEarthPressureInput) -> CalcResult:
    warnings: list[str] = [
        "Verify the Rankine formulae and DA1 partial factors used here against the current "
        "edition of EN 1997-1 and the UK National Annex before relying on this for a real design "
        "submission -- see the module docstring.",
        "Rankine's theory only -- no wall friction, wall batter, or sloping backfill. Not "
        "conservative for a sloping backfill or battered wall; do not use for either case.",
        "Single homogeneous soil layer assumed behind the wall (no multi-layer ground model).",
    ]
    risk_flags: list[DesignRiskFlag] = []

    Ka_k, Kp_k = rankine_coefficients(inputs.friction_angle_phi_prime_deg)
    terms: list[Term] = [
        Term("Ka (characteristic)", Ka_k, note="(1-sin(phi'_k))/(1+sin(phi'_k))"),
        Term("Kp (characteristic)", Kp_k, note="(1+sin(phi'_k))/(1-sin(phi'_k))"),
    ]

    Pa_c1, h_bar_c1, phi_d_c1, c_d_c1, clipped_c1 = _run_combination(inputs, DA1_C1)
    Pa_c2, h_bar_c2, phi_d_c2, c_d_c2, clipped_c2 = _run_combination(inputs, DA1_C2)

    terms.append(Term("[DA1-C1, unfactored] phi'_d", phi_d_c1, unit="deg"))
    terms.append(Term("[DA1-C1] Pa (active thrust)", Pa_c1, unit="kN/m", note=f"h_bar={h_bar_c1:.3g}m above base"))
    terms.append(Term("[DA1-C2, factored] phi'_d", phi_d_c2, unit="deg"))
    terms.append(Term("[DA1-C2] Pa (active thrust)", Pa_c2, unit="kN/m", note=f"h_bar={h_bar_c2:.3g}m above base"))

    if clipped_c1 or clipped_c2:
        warnings.append(
            "Cohesion term drove the computed pressure negative at some depth in at least one "
            "combination -- clipped to zero there. This is exact only for c'=0; for c'>0 this "
            "may overestimate the active thrust reduction from cohesion (see module docstring's "
            "tension-crack caveat)."
        )

    governing_label = "DA1-C2" if Pa_c2 >= Pa_c1 else "DA1-C1"
    Pa_governing = max(Pa_c1, Pa_c2)
    h_bar_governing = h_bar_c2 if governing_label == "DA1-C2" else h_bar_c1

    headline = Term(
        f"Pa (design active thrust, {governing_label} governs)", Pa_governing, unit="kN/m",
        note=f"Larger of DA1-C1/DA1-C2 -- the governing (more onerous) case for a destabilising action. Acts {h_bar_governing:.3g}m above the base.",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Rankine active earth pressure, EN 1997-1 UK NA Design Approach 1 (DA1-C1 & DA1-C2)",
        references=[
            "BS EN 1997-1:2004+A1:2013, Eurocode 7: Geotechnical design — Part 1: General rules.",
            "UK National Annex to BS EN 1997-1:2004+A1:2013.",
            "Rankine, W.J.M., 1857 — classical earth pressure theory, near-universally reproduced in geotechnical references.",
        ],
    )


MODULE = CalcModule(
    key="civil_lateral_earth_pressure_ec7",
    name="Lateral Earth Pressure Calculation (Rankine, EN 1997-1, UK NA, DA1)",
    discipline="Civils",
    description=(
        "Rankine active earth pressure coefficient and resultant thrust (both DA1 combinations) "
        "for a retaining wall, accounting for water table and surcharge, to EN 1997-1 with UK "
        "National Annex partial factors."
    ),
    input_model=LateralEarthPressureInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.civil.lateral_earth_pressure
    example = LateralEarthPressureInput(
        friction_angle_phi_prime_deg=30,
        cohesion_c_prime_kpa=0,
        unit_weight_kn_m3=18,
        wall_height_m=3.0,
        surcharge_kpa=10.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
