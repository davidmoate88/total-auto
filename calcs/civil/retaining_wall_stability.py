"""
Retaining wall stability check (sliding/overturning/bearing) — EN 1997-1
(Eurocode 7), UK National Annex Design Approach 1. Answers
`retaining_structures`'s "Retaining wall stability (sliding/overturning/
bearing)" `CalculationRequirement` in `basis_of_design/civils.py`. Reuses
`calcs/civil/lateral_earth_pressure.py`'s `rankine_coefficients()` and
`_active_thrust_and_lever_arm()` (recomputing active thrust from the same
characteristic soil parameters under each DA1 combination, per that module's
own docstring, rather than accepting a single pre-computed Pa) and
`calcs/geotechnical/bearing_capacity.py`'s `DA1_C1`/`DA1_C2` factor sets --
one shared DA1 treatment across geotechnical AND civils, not three separate
reimplementations of the same partial factor table.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from geotechnical-engineering literature/training knowledge, not by
reading the purchased BS EN 1997-1 standard text directly -- same caveat as
`lateral_earth_pressure.py` and `bearing_capacity.py`. See Known
simplifications for several deliberate scope reductions in this module
specifically (self-weight as a direct input, no passive-side water table,
bearing checked against a direct-input allowable pressure).

Method summary
--------------
For each DA1 combination (reusing `lateral_earth_pressure.py`'s dual
treatment):

    Active thrust Pa,d and its height above the base h_bar,d -- from the
    retained-side soil parameters, factored per the combination.

    Passive resistance (embedment zone, front of wall):
        Pp,d = 0.5*Kp,d*gamma_front*D^2 + 2*c'_front,d*sqrt(Kp,d)*D

    Vertical resultant (self-weight only -- see Known simplifications):
        N,d = gamma_G,fav * W    (gamma_G,fav = 1.0, both combinations --
                                   self-weight is a FAVOURABLE permanent
                                   action, UK NA never amplifies it)

    Sliding:      utilisation = Pa,d / (N,d*mu + Pp,d)
    Overturning:  utilisation = (Pa,d*h_bar,d) / (N,d*x_w + Pp,d*D/3)
    Bearing:      e = B/2 - (N,d*x_w - Pa,d*h_bar,d)/N,d
                  B_eff = B - 2*|e|                      (Meyerhof effective width,
                                                            same method as bearing_capacity.py)
                  utilisation = (N,d/B_eff) / allowable_bearing_pressure_kpa

The governing (higher-utilisation) combination is reported for each of the
three checks independently -- unlike `bearing_capacity.py`, where one
combination governs the single resistance check, sliding/overturning/bearing
can each be governed by a DIFFERENT DA1 combination here (a real, documented
characteristic of multi-check DA1 problems, not a bug).

Known simplifications / not implemented (see Warnings in the result):
- Self-weight of the wall+base+soil-on-heel (W) and its lever arm from the
  toe (x_w) are DIRECT INPUTS, not derived from wall/base geometry and
  material density -- computing a concrete/soil quantity take-off is a
  distinct piece of work from the stability check itself; keeping W as an
  input keeps this module's scope to "given the driving and resisting
  forces, is the wall stable" rather than also being a quantities tool.
- Base/soil interface friction coefficient (mu) is a DIRECT INPUT -- EC7
  gives guidance on deriving this from the soil's critical-state friction
  angle and the base material/roughness, but this author's confidence in
  reproducing the exact recommended reduction (as opposed to the general
  concept) was not high enough to embed as a formula. Supply the value
  directly (see the field description for typical guidance).
- Passive resistance assumes NO water table and NO surcharge within the
  embedment depth D (unlike the active side, which the reused
  `lateral_earth_pressure.py` function properly handles for the retained
  side) -- if the embedment zone is below the water table, this
  overestimates passive resistance (uses gamma, not gamma_sub) and should be
  adjusted manually (e.g. supply a reduced `unit_weight_front_kn_m3`).
- Passive resistance's contribution to the OVERTURNING check (Pp,d*D/3) is
  included by default, matching common practice for a preliminary check --
  some engineers/codes conservatively exclude it since passive resistance
  requires wall movement to mobilise. Flagged, not a design decision made
  silently.
- Bearing is checked against a DIRECT-INPUT allowable bearing pressure, not
  a full re-derivation via `bearing_capacity.py`'s Nq/Nc/Ngamma method for
  the effective strip-footing width found here -- run that module separately
  (with `length_m` large relative to `width_m` to approximate a strip
  footing) for a full bearing capacity check, then supply its result here as
  `allowable_bearing_pressure_kpa`.
- Vertical component of the active thrust is ignored (wall backface assumed
  vertical, consistent with `lateral_earth_pressure.py`'s Rankine
  assumptions) -- Pa contributes no vertical action to N,d.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from calcs.civil.lateral_earth_pressure import _active_thrust_and_lever_arm, rankine_coefficients
from calcs.geotechnical.bearing_capacity import DA1_C1, DA1_C2, PartialFactorSet
from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

GAMMA_G_FAVOURABLE = 1.0  # UK NA to BS EN 1997-1 -- favourable permanent actions are never amplified


class RetainingWallStabilityInput(BaseModel):
    # Retained (active) side -- passed straight through to lateral_earth_pressure.py's shared function.
    friction_angle_phi_prime_deg: float = Field(..., gt=0, le=45, description="Characteristic effective friction angle of the retained soil, phi' (degrees).")
    cohesion_c_prime_kpa: float = Field(0.0, ge=0, description="Characteristic effective cohesion of the retained soil, c' (kPa). 0 recommended -- see lateral_earth_pressure.py's docstring.")
    unit_weight_kn_m3: float = Field(..., gt=0, description="Characteristic bulk unit weight of the retained soil, gamma (kN/m^3).")
    wall_height_m: float = Field(..., gt=0, description="Total retained height, H (m).")
    water_table_depth_m: Optional[float] = Field(None, ge=0, description="Depth to water table below the top of the retained height (m). Omit if no water table within the retained height.")
    surcharge_kpa: float = Field(0.0, ge=0, description="Uniform characteristic surcharge behind the wall (kPa).")

    # Passive (front/embedment) side.
    friction_angle_phi_prime_front_deg: float = Field(..., gt=0, le=45, description="Characteristic effective friction angle of the soil in front of the wall (embedment zone), degrees.")
    cohesion_c_prime_front_kpa: float = Field(0.0, ge=0, description="Characteristic effective cohesion of the soil in front of the wall (kPa).")
    unit_weight_front_kn_m3: float = Field(..., gt=0, description="Characteristic bulk unit weight of the soil in front of the wall (kN/m^3). Reduce manually if the embedment zone is below a water table -- see module docstring.")
    embedment_depth_m: float = Field(..., gt=0, description="Depth of embedment in front of the wall providing passive resistance, D (m).")

    # Wall geometry / self-weight.
    base_width_m: float = Field(..., gt=0, description="Base width, B (m).")
    self_weight_kn_m: float = Field(..., gt=0, description="Total self-weight of wall+base+soil-on-heel per metre run, W (kN/m) -- direct input, see module docstring.")
    self_weight_lever_arm_from_toe_m: float = Field(..., ge=0, description="Horizontal distance from the toe to the line of action of W, x_w (m).")
    base_friction_coefficient: float = Field(..., gt=0, le=1.0, description="Base/soil interface friction coefficient, mu = tan(delta) -- direct input, typically informed by tan(phi'_critical-state) for a rough cast-in-situ base, reduced for a smoother interface. See module docstring.")

    allowable_bearing_pressure_kpa: float = Field(..., gt=0, description="Allowable bearing pressure for the founding material (kPa) -- direct input, see module docstring.")

    @model_validator(mode="after")
    def _check_consistency(self) -> "RetainingWallStabilityInput":
        if self.water_table_depth_m is not None and self.water_table_depth_m > self.wall_height_m:
            raise ValueError("water_table_depth_m must be <= wall_height_m (or omitted if below the retained height).")
        if self.self_weight_lever_arm_from_toe_m > self.base_width_m:
            raise ValueError("self_weight_lever_arm_from_toe_m must be <= base_width_m.")
        return self


def _run_combination(inputs: RetainingWallStabilityInput, factors: PartialFactorSet) -> dict:
    phi_d = math.degrees(math.atan(math.tan(math.radians(inputs.friction_angle_phi_prime_deg)) / factors.gamma_phi))
    c_d = inputs.cohesion_c_prime_kpa / factors.gamma_c
    Pa, h_bar, clipped = _active_thrust_and_lever_arm(
        phi_d, c_d, inputs.unit_weight_kn_m3, inputs.wall_height_m, inputs.water_table_depth_m, inputs.surcharge_kpa,
    )

    phi_front_d = math.degrees(math.atan(math.tan(math.radians(inputs.friction_angle_phi_prime_front_deg)) / factors.gamma_phi))
    c_front_d = inputs.cohesion_c_prime_front_kpa / factors.gamma_c
    _, Kp_front_d = rankine_coefficients(phi_front_d)
    D = inputs.embedment_depth_m
    Pp = 0.5 * Kp_front_d * inputs.unit_weight_front_kn_m3 * D**2 + 2 * c_front_d * math.sqrt(Kp_front_d) * D

    N = GAMMA_G_FAVOURABLE * inputs.self_weight_kn_m

    sliding_resistance = N * inputs.base_friction_coefficient + Pp
    sliding_utilisation = Pa / sliding_resistance if sliding_resistance > 0 else float("inf")

    overturning_driving = Pa * h_bar
    overturning_resisting = N * inputs.self_weight_lever_arm_from_toe_m + Pp * D / 3
    overturning_utilisation = overturning_driving / overturning_resisting if overturning_resisting > 0 else float("inf")

    B = inputs.base_width_m
    x_bar = (N * inputs.self_weight_lever_arm_from_toe_m - Pa * h_bar) / N
    e = B / 2 - x_bar
    B_eff = max(B - 2 * abs(e), 0.0)
    bearing_pressure = N / B_eff if B_eff > 0 else float("inf")
    bearing_utilisation = bearing_pressure / inputs.allowable_bearing_pressure_kpa

    return {
        "phi_d": phi_d, "Pa": Pa, "h_bar": h_bar, "clipped": clipped,
        "Kp_front_d": Kp_front_d, "Pp": Pp, "N": N,
        "sliding_utilisation": sliding_utilisation,
        "overturning_utilisation": overturning_utilisation,
        "eccentricity": e, "B_eff": B_eff, "bearing_pressure": bearing_pressure,
        "bearing_utilisation": bearing_utilisation,
    }


def calculate(inputs: RetainingWallStabilityInput) -> CalcResult:
    warnings: list[str] = [
        "Verify the DA1 partial factors and formulae used here against the current edition of "
        "EN 1997-1 and the UK National Annex before relying on this for a real design submission "
        "-- see the module docstring.",
        "Self-weight (W) and its lever arm from the toe are direct inputs, not derived from wall "
        "geometry/density -- this module checks stability given those forces, it is not a "
        "quantities take-off tool.",
        "Passive resistance assumes no water table/surcharge within the embedment depth -- reduce "
        "unit_weight_front_kn_m3 manually if the embedment zone is below a water table.",
        "Passive resistance's contribution to overturning resistance (Pp*D/3) is included by "
        "default -- some engineers/codes conservatively exclude it since passive resistance "
        "requires wall movement to mobilise.",
        "Bearing is checked against a direct-input allowable pressure, not a full EN 1997-1 Annex "
        "D re-derivation -- run bearing_capacity.py separately (large length_m to approximate a "
        "strip footing) for a full bearing capacity check.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    c1 = _run_combination(inputs, DA1_C1)
    c2 = _run_combination(inputs, DA1_C2)

    if c1["clipped"] or c2["clipped"]:
        warnings.append("Cohesion term on the retained side drove pressure negative at some depth in at least one combination -- clipped to zero there (see lateral_earth_pressure.py's tension-crack caveat).")

    terms: list[Term] = []
    checks = [
        ("Sliding", "sliding_utilisation"),
        ("Overturning", "overturning_utilisation"),
        ("Bearing", "bearing_utilisation"),
    ]
    governing_utilisations: dict[str, float] = {}
    for label, key in checks:
        u1, u2 = c1[key], c2[key]
        governing_combo = "DA1-C2" if u2 >= u1 else "DA1-C1"
        governing_u = max(u1, u2)
        governing_utilisations[label] = governing_u
        terms.append(Term(f"[DA1-C1] {label} utilisation", u1, note="PASS" if u1 <= 1.0 else "FAIL"))
        terms.append(Term(f"[DA1-C2] {label} utilisation", u2, note="PASS" if u2 <= 1.0 else "FAIL"))
        terms.append(
            Term(
                f"{label} utilisation (governing)", governing_u,
                note=f"{governing_combo} governs -- {'PASS' if governing_u <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if governing_u > 1.0:
            warnings.append(f"{label} check FAILS: governing utilisation = {governing_u:.2f} ({governing_combo}).")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical",
                    description=f"{label} check fails: governing utilisation = {governing_u:.2f} ({governing_combo}).",
                    trigger=f"{label} utilisation exceeds 1.0 under {governing_combo}.",
                    recommended_action="Review wall geometry, self-weight, embedment depth, or founding material before proceeding.",
                    source_reference="civil_retaining_wall_stability_ec7",
                )
            )

    terms.append(Term("Eccentricity e [DA1-C1]", c1["eccentricity"], unit="m", note=f"B/6 = {inputs.base_width_m/6:.3g}m -- {'within middle third' if abs(c1['eccentricity']) <= inputs.base_width_m/6 else 'OUTSIDE middle third'}"))
    terms.append(Term("Eccentricity e [DA1-C2]", c2["eccentricity"], unit="m", note=f"B/6 = {inputs.base_width_m/6:.3g}m -- {'within middle third' if abs(c2['eccentricity']) <= inputs.base_width_m/6 else 'OUTSIDE middle third'}"))
    if abs(c1["eccentricity"]) > inputs.base_width_m / 6 or abs(c2["eccentricity"]) > inputs.base_width_m / 6:
        warnings.append("Resultant falls outside the middle third of the base in at least one combination -- heel uplift/no-tension condition, the bearing pressure distribution assumed here (uniform over B_eff) becomes less representative.")

    governing_check = max(governing_utilisations, key=governing_utilisations.get)
    governing_value = governing_utilisations[governing_check]
    headline = Term(
        "Governing utilisation", governing_value,
        note=f"{governing_check} -- " + ("PASS" if governing_value <= 1.0 else "FAIL") + " (max of sliding/overturning/bearing)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Retaining wall stability (sliding/overturning/bearing), EN 1997-1 UK NA DA1-C1 & DA1-C2",
        references=[
            "BS EN 1997-1:2004+A1:2013, Eurocode 7: Geotechnical design — Part 1: General rules.",
            "UK National Annex to BS EN 1997-1:2004+A1:2013.",
            "calcs/civil/lateral_earth_pressure.py — active thrust method reused directly.",
        ],
    )


MODULE = CalcModule(
    key="civil_retaining_wall_stability_ec7",
    name="Retaining Wall Stability Check (Sliding/Overturning/Bearing, EN 1997-1, UK NA)",
    discipline="Civils",
    description=(
        "Sliding, overturning, and bearing utilisation for a gravity/cantilever retaining wall "
        "under both DA1 combinations, to EN 1997-1 with UK National Annex partial factors. "
        "Self-weight and allowable bearing pressure are direct inputs -- see module docstring."
    ),
    input_model=RetainingWallStabilityInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.civil.retaining_wall_stability
    example = RetainingWallStabilityInput(
        friction_angle_phi_prime_deg=30, cohesion_c_prime_kpa=0, unit_weight_kn_m3=18,
        wall_height_m=3.0, surcharge_kpa=10.0,
        friction_angle_phi_prime_front_deg=30, unit_weight_front_kn_m3=18, embedment_depth_m=0.8,
        base_width_m=2.2, self_weight_kn_m=85.0, self_weight_lever_arm_from_toe_m=1.1,
        base_friction_coefficient=0.5, allowable_bearing_pressure_kpa=150.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
