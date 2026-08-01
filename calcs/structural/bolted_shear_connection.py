"""
Bolted shear connection check — EN 1993-1-8 (Eurocode 3, Part 1-8: Design of
joints), UK National Annex. Answers `primary_steel_frame`'s "Connection
design" `CalculationRequirement` in `basis_of_design/structural.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from structural-engineering literature/training knowledge, not by
reading the purchased BS EN 1993-1-8 standard text directly -- same caveat,
and same reason for it, as `bearing_capacity.py`, `beam_capacity.py`, and
`column_capacity.py`. Confidence here is LOWER than in those modules for one
specific constant: EN 1993-1-8 Table 3.4's shear resistance factor alpha_v
depends on bolt grade AND which portion of the shank the shear plane passes
through, and this author's recollection of the exact grade/shear-plane
combinations was genuinely inconsistent across attempts to recall it while
building this module. Rather than embed a guessed table, `alpha_v` is a
REQUIRED direct input (no default) -- read it off EN 1993-1-8 Table 3.4 for
the actual bolt grade and shear-plane location before using this module. The
bearing-resistance formula (alpha_b, k1) is reproduced with higher confidence
(seen consistently across multiple sources) but should still be verified.

Method summary
--------------
For a bolt group in PURE CONCENTRIC SHEAR (no moment on the group -- see
Known simplifications), assumed to share the applied shear equally:

    Fv,Rd = alpha_v * fub * bolt_shear_area / gamma_M2            (per shear plane, per bolt)
    Fb,Rd = k1 * alpha_b * fu * d * t / gamma_M2                  (bearing, per bolt)

    alpha_b = min(alpha_d, fub/fu, 1.0)
    alpha_d = e1/(3*d0)                    (end bolt, load direction)
            = p1/(3*d0) - 1/4              (inner bolt, load direction)
    k1      = min(2.8*e2/d0 - 1.7, 2.5)    (edge bolt, perpendicular to load)
            = min(1.4*p2/d0 - 1.7, 2.5)    (inner bolt, perpendicular to load)

The governing per-bolt resistance (lower of Fv,Rd*planes and Fb,Rd) is
multiplied by the bolt count for the group resistance. Where a bolt group has
more than one bolt, alpha_d and k1 are each evaluated at BOTH the end/edge
formula and the inner-bolt formula (where applicable) and the lower value is
applied uniformly to all bolts -- a conservative simplification (see below).

Known simplifications / not implemented (see Warnings in the result):
- PURE CONCENTRIC SHEAR ONLY -- the bolt group is assumed to share the
  applied shear equally with no eccentricity/moment on the group. A group
  with significant eccentricity (e.g. a bracket connection) needs the
  elastic/plastic bolt-group moment distribution method, not implemented here.
- Block tearing (EN 1993-1-8 SS3.10.2) is NOT checked -- a common governing
  failure mode for bolt groups near a plate edge/end, genuinely distinct from
  the individual bolt shear/bearing checks performed here.
- The connected plies' own tension/shear capacity (gross and net section) is
  NOT checked -- only the bolts' shear and bearing resistance.
- Combined shear + tension (e.g. a moment connection's bolt rows) is not
  covered -- pure shear only.
- Applying the worst-case alpha_d/k1 uniformly to every bolt in a multi-bolt
  group is conservative but not a full bolt-by-bolt position check -- fine
  for a single row of similar bolts, less so for an irregular layout.
- Prying action (relevant to bolts in tension, not shear) is not applicable
  here and not checked.
"""

from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

GAMMA_M2 = 1.25  # UK NA to BS EN 1993-1-8, resistance of bolts/welds/plates in bearing

# fub (ultimate tensile strength, MPa) per EN ISO 898-1 bolt property class --
# definitional (grade X.Y => fub = 100*X MPa), high confidence.
_BOLT_GRADE_FUB: dict[str, float] = {"4.6": 400.0, "5.6": 500.0, "8.8": 800.0, "10.9": 1000.0}


class BoltedShearConnectionInput(BaseModel):
    bolt_grade: Literal["4.6", "5.6", "8.8", "10.9"] = Field("8.8", description="Bolt property class (EN ISO 898-1).")
    bolt_diameter_mm: float = Field(..., gt=0, description="Nominal bolt diameter, d (mm).")
    bolt_shear_area_mm2: float = Field(
        ..., gt=0,
        description="Area resisting shear at the shear plane -- the tensile stress area if the shear plane passes through the threads, or the gross shank area if through the unthreaded shank. Confirm which applies for the actual bolt/grip length.",
    )
    shear_resistance_factor_alpha_v: float = Field(
        ..., gt=0, le=1.0,
        description="EN 1993-1-8 Table 3.4 alpha_v for this bolt grade and shear-plane location -- REQUIRED, no built-in default (see module docstring). Typically 0.5 or 0.6 depending on grade/shear-plane -- read it directly off Table 3.4.",
    )
    shear_planes_per_bolt: int = Field(1, ge=1, le=2, description="1 = single shear (e.g. fin plate), 2 = double shear (e.g. bolted cover plates).")

    connected_ply_thickness_mm: float = Field(..., gt=0, description="Thickness of the governing (thinnest relevant) connected ply, t (mm).")
    connected_ply_ultimate_strength_mpa: float = Field(..., gt=0, description="Ultimate tensile strength of the connected ply, fu (MPa) -- from the material standard/mill certificate, not looked up here.")

    hole_diameter_mm: float = Field(..., gt=0, description="Bolt hole diameter including clearance, d0 (mm).")
    end_distance_mm: float = Field(..., gt=0, description="End distance in the direction of load transfer, e1 (mm).")
    edge_distance_mm: float = Field(..., gt=0, description="Edge distance perpendicular to the direction of load transfer, e2 (mm).")

    number_of_bolts: int = Field(1, ge=1, description="Bolts in the group, assumed to share the applied shear equally (concentric group only).")
    bolt_pitch_mm: Optional[float] = Field(None, gt=0, description="Spacing between bolts in the direction of load, p1 (mm) -- required if number_of_bolts > 1.")
    bolt_gauge_mm: Optional[float] = Field(None, gt=0, description="Spacing between bolts perpendicular to load, p2 (mm) -- only relevant with more than one bolt per row; omit for a single row.")

    applied_shear_permanent_kn: float = Field(0.0, ge=0, description="Characteristic permanent shear on the group, VGk (kN).")
    applied_shear_variable_kn: float = Field(0.0, ge=0, description="Characteristic variable shear on the group, VQk (kN).")

    @model_validator(mode="after")
    def _check_consistency(self) -> "BoltedShearConnectionInput":
        if self.number_of_bolts > 1 and self.bolt_pitch_mm is None:
            raise ValueError("bolt_pitch_mm is required when number_of_bolts > 1.")
        if self.bolt_diameter_mm >= self.hole_diameter_mm:
            raise ValueError("hole_diameter_mm must exceed bolt_diameter_mm (clearance hole).")
        return self


def calculate(inputs: BoltedShearConnectionInput) -> CalcResult:
    warnings: list[str] = [
        "Verify the bearing-resistance formula (alpha_b, k1) and gamma_M2 used here against the "
        "current edition of EN 1993-1-8 and the UK National Annex before relying on this for a "
        "real design submission -- see the module docstring. shear_resistance_factor_alpha_v is a "
        "required direct input for this module specifically because this author's recollection of "
        "Table 3.4's grade/shear-plane dependence was not reliable enough to embed as a default.",
        "PURE CONCENTRIC SHEAR ONLY -- no moment/eccentricity on the bolt group is checked. Not "
        "valid for a bracket or other connection with significant eccentricity.",
        "Block tearing (EN 1993-1-8 SS3.10.2) is NOT checked -- a common governing failure mode for "
        "bolt groups near a plate edge/end, separate from the individual bolt checks below.",
        "The connected plies' own tension/shear capacity (gross and net section) is NOT checked -- "
        "only the bolts' shear and bearing resistance.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    fub = _BOLT_GRADE_FUB[inputs.bolt_grade]
    d = inputs.bolt_diameter_mm
    d0 = inputs.hole_diameter_mm
    fu = inputs.connected_ply_ultimate_strength_mpa
    t = inputs.connected_ply_thickness_mm

    terms: list[Term] = [
        Term("fub (bolt ultimate strength)", fub, unit="MPa", note=f"grade {inputs.bolt_grade}"),
    ]

    Fv_Rd_N = inputs.shear_resistance_factor_alpha_v * fub * inputs.bolt_shear_area_mm2 / GAMMA_M2
    Fv_Rd_per_bolt_kN = Fv_Rd_N * inputs.shear_planes_per_bolt / 1e3
    terms.append(Term("Fv,Rd (shear resistance, per shear plane)", Fv_Rd_N / 1e3, unit="kN", note=f"alpha_v={inputs.shear_resistance_factor_alpha_v:g}"))
    terms.append(Term("Fv,Rd (shear resistance, per bolt)", Fv_Rd_per_bolt_kN, unit="kN", note=f"{inputs.shear_planes_per_bolt} shear plane(s)"))

    alpha_d_end = inputs.end_distance_mm / (3 * d0)
    alpha_d_terms = [alpha_d_end]
    if inputs.number_of_bolts > 1:
        alpha_d_inner = inputs.bolt_pitch_mm / (3 * d0) - 0.25
        alpha_d_terms.append(alpha_d_inner)
    alpha_d = min(alpha_d_terms)
    alpha_b = min(alpha_d, fub / fu, 1.0)

    k1_edge = min(2.8 * inputs.edge_distance_mm / d0 - 1.7, 2.5)
    k1_terms = [k1_edge]
    if inputs.bolt_gauge_mm is not None:
        k1_inner = min(1.4 * inputs.bolt_gauge_mm / d0 - 1.7, 2.5)
        k1_terms.append(k1_inner)
    k1 = min(k1_terms)

    terms.append(Term("alpha_d", alpha_d, note="min(e1/(3d0)[, p1/(3d0)-1/4])"))
    terms.append(Term("alpha_b", alpha_b, note="min(alpha_d, fub/fu, 1.0)"))
    terms.append(Term("k1", k1, note="min(2.8*e2/d0-1.7[, 1.4*p2/d0-1.7], 2.5)"))

    Fb_Rd_N = k1 * alpha_b * fu * d * t / GAMMA_M2
    Fb_Rd_per_bolt_kN = Fb_Rd_N / 1e3
    terms.append(Term("Fb,Rd (bearing resistance, per bolt)", Fb_Rd_per_bolt_kN, unit="kN"))

    governing_per_bolt_kN = min(Fv_Rd_per_bolt_kN, Fb_Rd_per_bolt_kN)
    governing_mode = "shear" if Fv_Rd_per_bolt_kN <= Fb_Rd_per_bolt_kN else "bearing"
    terms.append(Term("Governing resistance per bolt", governing_per_bolt_kN, unit="kN", note=f"{governing_mode} governs"))

    group_resistance_kN = governing_per_bolt_kN * inputs.number_of_bolts
    terms.append(Term("Group resistance", group_resistance_kN, unit="kN", note=f"{inputs.number_of_bolts} bolt(s), equally shared (concentric group)"))

    VEd = 1.35 * inputs.applied_shear_permanent_kn + 1.5 * inputs.applied_shear_variable_kn
    if VEd > 0:
        terms.append(Term("VEd (design shear on group)", VEd, unit="kN", note=f"1.35*{inputs.applied_shear_permanent_kn:g} + 1.5*{inputs.applied_shear_variable_kn:g}"))
        utilisation = VEd / group_resistance_kN
        terms.append(
            Term(
                "Utilisation", utilisation,
                note=f"VEd/group resistance -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if utilisation > 1.0:
            warnings.append(f"ULS check FAILS: connection utilisation = {utilisation:.2f}.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical",
                    description=f"ULS bolt group check fails: VEd/group resistance = {utilisation:.2f} (must be <= 1.0).",
                    trigger=f"VEd={VEd:.1f}kN, group resistance={group_resistance_kN:.1f}kN ({governing_mode} governs)",
                    recommended_action="Increase bolt size/grade/count, increase ply thickness, or review edge/end distances -- then re-check block tearing and plate capacity separately (not covered by this module).",
                    source_reference="structural_bolted_shear_connection_ec3",
                )
            )
        headline = Term(
            "Utilisation", utilisation,
            note=("PASS" if utilisation <= 1.0 else "FAIL") + f" -- VEd/group resistance ({governing_mode} governs)",
        )
    else:
        headline = Term(
            "Group resistance", group_resistance_kN, unit="kN",
            note=f"No applied shear supplied -- resistance-only, {governing_mode} governs per bolt.",
        )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="EN 1993-1-8 bolted connection shear and bearing resistance (concentric group), UK NA",
        references=[
            "BS EN 1993-1-8:2005, Eurocode 3: Design of steel structures — Part 1-8: Design of joints, Table 3.4.",
            "UK National Annex to BS EN 1993-1-8.",
            "BS EN 1990:2002+A1:2005 and UK NA, expression 6.10, for the 1.35Gk+1.5Qk ULS combination.",
        ],
    )


MODULE = CalcModule(
    key="structural_bolted_shear_connection_ec3",
    name="Bolted Shear Connection Check (EN 1993-1-8, UK NA)",
    discipline="Structural",
    description=(
        "Bolt shear and bearing resistance for a concentrically-loaded bolt group (no moment/"
        "eccentricity), to EN 1993-1-8 with UK National Annex partial factors. Block tearing and "
        "connected-ply capacity are not covered -- see module docstring."
    ),
    input_model=BoltedShearConnectionInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.structural.bolted_shear_connection
    # Illustrative M20 grade 8.8 bolt group, 2 bolts in a single row, single shear.
    example = BoltedShearConnectionInput(
        bolt_grade="8.8",
        bolt_diameter_mm=20.0,
        bolt_shear_area_mm2=245.0,  # As for M20 (tensile stress area) -- illustrative, confirm for real use.
        shear_resistance_factor_alpha_v=0.6,
        connected_ply_thickness_mm=10.0,
        connected_ply_ultimate_strength_mpa=430.0,  # illustrative S275 fu
        hole_diameter_mm=22.0,
        end_distance_mm=40.0,
        edge_distance_mm=40.0,
        number_of_bolts=2,
        bolt_pitch_mm=60.0,
        applied_shear_permanent_kn=30.0, applied_shear_variable_kn=20.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
