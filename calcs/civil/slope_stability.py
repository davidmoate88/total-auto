"""
Circular slip surface slope stability check — Fellenius (Ordinary/Swedish)
Method of Slices, EN 1997-1 (Eurocode 7), UK National Annex Design Approach
1. Answers `earthworks_and_remediation`'s "Slope stability check"
`CalculationRequirement` in `basis_of_design/civils.py`. Reuses
`calcs/geotechnical/bearing_capacity.py`'s `DA1_C1`/`DA1_C2` factor sets --
the same shared Design Approach 1 implementation `retaining_wall_stability.py`
already reuses, not a third copy of the same partial factors.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from geotechnical-engineering literature/training knowledge, not by
reading the purchased BS EN 1997-1 standard text directly -- same caveat as
the other geotechnical/civils modules. One specific, deliberate method
choice matters here: this module uses FELLENIUS' method (the "Ordinary
Method of Slices"), not Bishop's Simplified Method. Fellenius is simpler
(non-iterative -- Bishop's requires solving for the factor implicitly since
each slice's normal force depends on it) and its formula is verified here
with high confidence, but it is KNOWN TO BE CONSERVATIVE relative to
Bishop's -- often underestimating the true factor of safety (equivalently,
overestimating utilisation) by up to ~15-20%, especially for effective
stress analyses with significant pore pressure. Bishop's Simplified Method
is the more commonly accepted method in current UK practice and is NOT
implemented here -- treat a FAIL (or a marginal PASS) from this module as
"needs a Bishop's-method check," not as a final answer either way.

Method summary
--------------
For a circular slip surface divided into vertical slices (slice geometry
supplied directly -- see Known simplifications), under EC7 DA1, both
combinations are checked by factoring the characteristic shear strength
parameters (the same M1/M2 pattern as every other geotechnical/civils
module in this repo) -- NOT by factoring slice self-weight, base length, or
pore pressure, which are geometric/hydraulic facts DA1's material-factor
approach does not touch:

    phi'_d = atan(tan(phi'_k) / gamma_phi),  c'_d = c'_k / gamma_c

    Sum(resisting) = sum over slices of [c'_d*l_i + (W_i*cos(a_i) - u_i*l_i)*tan(phi'_d)]
    Sum(driving)   = sum over slices of [W_i*sin(a_i)]

    utilisation = Sum(driving) / Sum(resisting)

computed for both DA1-C1 (unfactored) and DA1-C2 (factored) -- the
governing case is the HIGHER utilisation (weaker apparent soil strength
under DA1-C2 typically governs, the same direction as
`lateral_earth_pressure.py`'s active thrust, not the "lower resistance
governs" direction of a spread-footing bearing check).

Slice base angle `a_i` follows the standard Fellenius sign convention:
positive where the slice base dips towards the toe (the driving zone, most
of the circle), negative where it dips the other way (a resisting
contribution near the toe) -- `W*sin(a)` is negative there, correctly
reducing net driving force.

Known simplifications / not implemented (see Warnings in the result):
- FELLENIUS' method, not Bishop's Simplified Method -- see above. Known to
  be conservative; treat results near the utilisation=1.0 boundary as
  needing a Bishop's-method check, not a final answer.
- Slice geometry (weight, base angle, base length, pore pressure) is
  supplied directly as pasted text, one slice per line -- this module does
  NOT generate slices from a slope profile and a trial slip circle (that
  geometry -- circle/ground-surface intersection, per-slice depth and base
  angle -- is a substantial piece of computational geometry in its own
  right, kept out of scope here to avoid embedding it without independent
  verification). Compute slice data externally (spreadsheet, slope
  stability software, or by hand) and paste it in.
- A SINGLE characteristic phi'/c' is applied to every slice -- no
  multi-layer ground model along the slip surface (unlike the ground model
  interpreter feeding `bearing_capacity.py`, there is no equivalent handoff
  for this calc).
- This module checks ONE trial slip circle (i.e. one slice dataset) --
  finding the CRITICAL (lowest-utilisation... highest-utilisation) circle
  among many trials is a search problem this module does not perform. A
  real slope stability assessment checks many trial circles.
- Circular slip surfaces only -- no non-circular/wedge/planar failure
  mechanisms (translational slides, for example) are checked.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator

from calcs.geotechnical.bearing_capacity import DA1_C1, DA1_C2, PartialFactorSet
from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class Slice(BaseModel):
    weight_kn: float = Field(..., gt=0)
    base_angle_deg: float = Field(..., gt=-90, lt=90)
    base_length_m: float = Field(..., gt=0)
    pore_pressure_kpa: float = Field(0.0, ge=0)


def _parse_slices(text: str) -> tuple[list[Slice], list[str]]:
    """Lenient 'weight_kn, base_angle_deg, base_length_m, pore_pressure_kpa' per-line parser."""
    slices: list[Slice] = []
    unparsed: list[str] = []
    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) not in (3, 4):
            unparsed.append(raw_line)
            continue
        try:
            values = [float(p) for p in parts]
            weight, angle, length = values[0], values[1], values[2]
            pore_pressure = values[3] if len(values) == 4 else 0.0
            if weight <= 0 or length <= 0:
                unparsed.append(raw_line)
                continue
            slices.append(Slice(weight_kn=weight, base_angle_deg=angle, base_length_m=length, pore_pressure_kpa=pore_pressure))
        except ValueError:
            unparsed.append(raw_line)
    return slices, unparsed


def _fellenius_utilisation(slices: list[Slice], phi_d_deg: float, c_d_kpa: float) -> tuple[float, float, float]:
    """Returns (utilisation, sum_resisting, sum_driving) for one set of design shear strength parameters."""
    phi_d = math.radians(phi_d_deg)
    resisting = 0.0
    driving = 0.0
    for s in slices:
        a = math.radians(s.base_angle_deg)
        resisting += c_d_kpa * s.base_length_m + (s.weight_kn * math.cos(a) - s.pore_pressure_kpa * s.base_length_m) * math.tan(phi_d)
        driving += s.weight_kn * math.sin(a)
    utilisation = driving / resisting if resisting > 0 else float("inf")
    return utilisation, resisting, driving


class SlopeStabilityInput(BaseModel):
    friction_angle_phi_prime_deg: float = Field(..., gt=0, le=45, description="Characteristic effective friction angle applied to every slice, phi' (degrees).")
    cohesion_c_prime_kpa: float = Field(0.0, ge=0, description="Characteristic effective cohesion applied to every slice, c' (kPa).")
    slices_text: str = Field(
        ...,
        description="One slice per line: 'weight_kn, base_angle_deg, base_length_m[, pore_pressure_kpa]'. "
        "e.g. '120, 22, 2.1, 15' -- pore pressure optional (defaults to 0). Base angle positive where the slice "
        "base dips towards the toe (driving), negative where it dips the other way (resisting) -- see module docstring.",
    )

    @field_validator("slices_text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("slices_text must not be blank.")
        return v


def calculate(inputs: SlopeStabilityInput) -> CalcResult:
    warnings: list[str] = [
        "Fellenius' method (Ordinary Method of Slices), not Bishop's Simplified Method -- known to "
        "be CONSERVATIVE, often overestimating utilisation by up to ~15-20% vs Bishop's, especially "
        "with significant pore pressure. Treat a marginal result as needing a Bishop's-method check.",
        "Slice geometry is a direct input, not generated from a slope profile and trial slip circle "
        "-- this module does not perform that geometry. See module docstring.",
        "Checks ONE trial slip circle only -- finding the critical circle among many trials is not performed.",
        "Circular slip surfaces only -- no non-circular/wedge/planar failure mechanisms.",
        "A single characteristic phi'/c' is applied to every slice -- no multi-layer ground model.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    slices, unparsed = _parse_slices(inputs.slices_text)
    for u in unparsed:
        warnings.append(f"Could not parse slice line: '{u}' -- expected 'weight_kn, base_angle_deg, base_length_m[, pore_pressure_kpa]'.")

    if not slices:
        warnings.append("No valid slices parsed -- cannot compute a stability check.")
        return CalcResult(
            headline=Term("Governing utilisation", float("inf"), note="No valid slices parsed"),
            terms=[],
            warnings=warnings,
            risk_flags=risk_flags,
            method="Circular slip surface stability check, Fellenius Method of Slices",
            references=["BS EN 1997-1:2004+A1:2013, Eurocode 7: Geotechnical design — Part 1: General rules."],
        )

    terms: list[Term] = [Term("Slices parsed", len(slices))]

    results: dict[str, tuple[float, float, float, float, float]] = {}
    for label, factors in (("DA1-C1", DA1_C1), ("DA1-C2", DA1_C2)):
        phi_d = math.degrees(math.atan(math.tan(math.radians(inputs.friction_angle_phi_prime_deg)) / factors.gamma_phi))
        c_d = inputs.cohesion_c_prime_kpa / factors.gamma_c
        utilisation, resisting, driving = _fellenius_utilisation(slices, phi_d, c_d)
        results[label] = (utilisation, resisting, driving, phi_d, c_d)

        terms.append(Term(f"[{label}] phi'_d", phi_d, unit="deg", note="unfactored" if label == "DA1-C1" else f"atan(tan(phi'_k)/{factors.gamma_phi})"))
        terms.append(Term(f"[{label}] c'_d", c_d, unit="kPa"))
        terms.append(Term(f"[{label}] Sum(resisting)", resisting, unit="kN"))
        terms.append(Term(f"[{label}] Sum(driving)", driving, unit="kN"))
        terms.append(
            Term(
                f"[{label}] Utilisation", utilisation,
                note="PASS" if utilisation <= 1.0 else "FAIL",
            )
        )

    governing_label = "DA1-C2" if results["DA1-C2"][0] >= results["DA1-C1"][0] else "DA1-C1"
    governing_utilisation = max(results["DA1-C1"][0], results["DA1-C2"][0])

    terms.append(
        Term(
            "Governing utilisation", governing_utilisation,
            note=f"{governing_label} governs -- {'PASS' if governing_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
        )
    )

    if governing_utilisation > 1.0:
        warnings.append(f"Slope stability check FAILS: governing utilisation = {governing_utilisation:.2f} ({governing_label}).")
        risk_flags.append(
            DesignRiskFlag(
                category="code_compliance",
                severity="critical",
                description=f"Slope stability check fails: governing utilisation = {governing_utilisation:.2f} ({governing_label}).",
                trigger=f"utilisation exceeds 1.0 under {governing_label}.",
                recommended_action="Reduce slope angle, provide a berm/regrade, install drainage to reduce pore pressure, or check with Bishop's Simplified Method before concluding the slope is unstable (Fellenius is conservative).",
                source_reference="civil_slope_stability_ec7",
            )
        )
    elif governing_utilisation > 0.9:
        warnings.append(
            f"Governing utilisation ({governing_utilisation:.2f}) is close to 1.0 -- given Fellenius' known "
            "conservative bias, this is exactly the marginal case where a Bishop's Simplified Method check "
            "is worth doing before relying on this result either way."
        )

    headline = Term(
        "Governing utilisation", governing_utilisation,
        note=f"{governing_label} -- " + ("PASS" if governing_utilisation <= 1.0 else "FAIL") + " (Fellenius Method of Slices)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Circular slip surface stability check, Fellenius (Ordinary) Method of Slices, EN 1997-1 UK NA DA1-C1 & DA1-C2",
        references=[
            "BS EN 1997-1:2004+A1:2013, Eurocode 7: Geotechnical design — Part 1: General rules.",
            "UK National Annex to BS EN 1997-1:2004+A1:2013.",
            "Fellenius, W., 1936 — classical Ordinary Method of Slices, near-universally reproduced in geotechnical references.",
        ],
    )


MODULE = CalcModule(
    key="civil_slope_stability_ec7",
    name="Slope Stability Check (Fellenius Method of Slices, EN 1997-1, UK NA)",
    discipline="Civils",
    description=(
        "Circular slip surface stability utilisation (both DA1 combinations) via Fellenius' Ordinary "
        "Method of Slices, from directly-supplied slice geometry. Conservative vs Bishop's Simplified "
        "Method, which is not implemented -- see module docstring."
    ),
    input_model=SlopeStabilityInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.civil.slope_stability
    example = SlopeStabilityInput(
        friction_angle_phi_prime_deg=25,
        cohesion_c_prime_kpa=5,
        slices_text=(
            "100, 30, 2.0, 10\n"
            "150, 15, 2.2, 15\n"
            "80, -5, 1.8, 5\n"
        ),
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
