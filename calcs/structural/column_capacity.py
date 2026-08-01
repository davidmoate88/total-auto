"""
Steel column axial buckling capacity check — EN 1993-1-1 (Eurocode 3), UK
National Annex. Completes, together with `calcs/structural/beam_capacity.py`,
`primary_steel_frame`'s "Beam/column member capacity checks"
`CalculationRequirement` in `basis_of_design/structural.py` -- this module is
the "column" half, scoped to PURE AXIAL COMPRESSION only (see Known
simplifications). Bending is `beam_capacity.py`'s job; a member carrying both
at once (a true "beam-column") needs the combined check neither module
performs -- see below.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from structural-engineering literature/training knowledge, not by
reading the purchased BS EN 1993-1-1 standard text directly -- same caveat,
and same reason for it, as `bearing_capacity.py` and `beam_capacity.py`. In
particular the Table 5.2 web-in-compression classification limits (33/38/42
epsilon), the Table 6.2 buckling curve selection (restricted here to rolled
I/H sections with h/b > 1.2 and tf <= 40mm), the Table 6.1 imperfection
factors, and gamma_M1 = 1.0 (UK NA) are commonly reproduced constants, not
independently re-derived -- verify against the current standard text and UK
NA before real use. Section properties (A, Iy, Iz) are catalogue inputs, not
derived from geometry, for the same reason given in `beam_capacity.py`'s
docstring.

Method summary
--------------
Cross-section (stub) compression resistance (SS6.2.4):

    Nc,Rd = A*fy / gamma_M0                                (Class 1-3)

Flexural buckling resistance about each principal axis (SS6.3.1):

    lambda_1 = 93.9*epsilon
    lambda_bar = (Lcr/i) / lambda_1
    phi = 0.5*[1 + alpha*(lambda_bar - 0.2) + lambda_bar^2]
    chi = 1 / (phi + sqrt(phi^2 - lambda_bar^2))            (chi <= 1.0)
    Nb,Rd = chi*A*fy / gamma_M1

computed independently for y-y and z-z; the governing (lower) value is the
member's axial buckling resistance. alpha (imperfection factor) is selected
from the buckling curve (Table 6.2) via Table 6.1 (a0=0.13, a=0.21, b=0.34,
c=0.49, d=0.76).

Known simplifications / not implemented (see Warnings in the result):
- PURE AXIAL COMPRESSION ONLY. Combined bending + axial compression (a true
  "beam-column") requires the EN 1993-1-1 SS6.3.3 interaction check (equivalent
  uniform moment factors, Annex A/B interaction coefficients) -- genuinely one
  of the more involved parts of EN 1993-1-1, and NOT implemented here. If a
  member carries significant bending as well as axial load, this module's
  Nb,Rd and `beam_capacity.py`'s Mc,Rd are each individually valid as
  stand-alone checks but do NOT combine into a valid member check by simply
  summing utilisations -- do the full SS6.3.3 check separately.
- Web classification for the Table 5.2 c/t check uses the UNIFORM COMPRESSION
  row (33/38/42*epsilon), which is the correct row for a pure axial member --
  if this module is ever extended to combined actions, the web classification
  would need revisiting (a web under combined bending+compression uses a
  different, stress-gradient-dependent row).
- Buckling curve auto-selection (Table 6.2) is restricted to rolled I/H
  sections with h/b > 1.2 and flange thickness <= 40mm (curve a about y-y,
  curve b about z-z) -- the most common case for light industrial columns.
  Outside that range, supply `buckling_curve_y_override` /
  `buckling_curve_z_override` directly rather than have this module guess.
- Class 4 (slender) sections are not supported -- same critical-risk-flag
  fallback pattern as `beam_capacity.py`.
- Torsional and torsional-flexural buckling (relevant to some open sections,
  e.g. angles/channels) are not checked -- this module assumes flexural
  buckling governs, valid for doubly-symmetric I/H sections.
"""

from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from calcs.structural.beam_capacity import _lookup_yield_strength_mpa
from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

GAMMA_M0 = 1.0  # UK NA to BS EN 1993-1-1, cross-section resistance
GAMMA_M1 = 1.0  # UK NA to BS EN 1993-1-1, member buckling resistance

IMPERFECTION_FACTORS: dict[str, float] = {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}
BucklingCurve = Literal["a0", "a", "b", "c", "d"]


class ColumnCapacityInput(BaseModel):
    steel_grade: Literal["S235", "S275", "S355", "S460"] = Field(
        "S355", description="Nominal steel grade (BS EN 10025-2)."
    )
    yield_strength_override_mpa: Optional[float] = Field(
        None, gt=0,
        description="Supply directly to bypass the built-in Table 3.1 lookup -- required if the governing element thickness exceeds 40mm.",
    )

    # Section geometry (mm) -- classification only, see module docstring.
    section_depth_mm: float = Field(..., gt=0, description="Overall section depth, h (mm).")
    section_width_mm: float = Field(..., gt=0, description="Flange width, b (mm).")
    web_thickness_mm: float = Field(..., gt=0, description="Web thickness, tw (mm).")
    flange_thickness_mm: float = Field(..., gt=0, description="Flange thickness, tf (mm).")
    root_radius_mm: float = Field(0.0, ge=0, description="Root radius, r (mm). Default 0 is conservative if unknown.")

    # Section properties (mm units) -- catalogue inputs, not derived. See module docstring.
    area_mm2: float = Field(..., gt=0, description="Cross-sectional area, A (mm^2).")
    second_moment_area_y_mm4: float = Field(..., gt=0, description="Second moment of area about the major (y-y) axis, Iy (mm^4).")
    second_moment_area_z_mm4: float = Field(..., gt=0, description="Second moment of area about the minor (z-z) axis, Iz (mm^4).")

    member_length_m: float = Field(..., gt=0, description="System length of the member, L (m).")
    effective_length_factor_y: float = Field(
        1.0, gt=0, description="Buckling length factor about y-y, ky. Common values: 0.5 fixed-fixed, 0.7 fixed-pinned, 1.0 pinned-pinned, 2.0 fixed-free (cantilever).",
    )
    effective_length_factor_z: float = Field(
        1.0, gt=0, description="Buckling length factor about z-z, kz. Same guidance as ky.",
    )

    buckling_curve_y_override: Optional[BucklingCurve] = Field(
        None, description="Override Table 6.2 auto-selection for y-y buckling -- required if h/b <= 1.2 or tf > 40mm.",
    )
    buckling_curve_z_override: Optional[BucklingCurve] = Field(
        None, description="Override Table 6.2 auto-selection for z-z buckling -- required if h/b <= 1.2 or tf > 40mm.",
    )

    axial_permanent_load_kn: float = Field(0.0, ge=0, description="Characteristic permanent axial compression, NGk (kN).")
    axial_variable_load_kn: float = Field(0.0, ge=0, description="Characteristic variable axial compression, NQk (kN).")

    @model_validator(mode="after")
    def _check_consistency(self) -> "ColumnCapacityInput":
        if self.flange_thickness_mm >= self.section_depth_mm / 2:
            raise ValueError("flange_thickness_mm must be less than half section_depth_mm.")
        if self.web_thickness_mm >= self.section_width_mm:
            raise ValueError("web_thickness_mm must be less than section_width_mm.")
        governing_thickness = max(self.flange_thickness_mm, self.web_thickness_mm)
        if self.yield_strength_override_mpa is None and governing_thickness > 40.0:
            raise ValueError(
                f"Governing thickness ({governing_thickness} mm) exceeds the built-in Table 3.1 "
                "range (40mm) -- supply yield_strength_override_mpa directly."
            )
        h_over_b = self.section_depth_mm / self.section_width_mm
        auto_selectable = h_over_b > 1.2 and self.flange_thickness_mm <= 40.0
        if not auto_selectable and (self.buckling_curve_y_override is None or self.buckling_curve_z_override is None):
            raise ValueError(
                f"h/b = {h_over_b:.2f} and/or tf = {self.flange_thickness_mm}mm fall outside the "
                "auto-selectable Table 6.2 range (h/b > 1.2, tf <= 40mm) -- supply both "
                "buckling_curve_y_override and buckling_curve_z_override directly."
            )
        return self


def _classify_section(inputs: ColumnCapacityInput, epsilon: float) -> tuple[int, int, int, float, float]:
    """
    Cross-section classification per EN 1993-1-1 Table 5.2 -- web as an
    internal part under UNIFORM COMPRESSION (33/38/42*epsilon), flange as an
    outstand part under compression (9/10/14*epsilon, same as beam_capacity.py).
    """
    h, b, tw, tf, r = (
        inputs.section_depth_mm, inputs.section_width_mm,
        inputs.web_thickness_mm, inputs.flange_thickness_mm, inputs.root_radius_mm,
    )
    c_web = h - 2 * tf - 2 * r
    web_ratio = c_web / tw
    if web_ratio <= 33 * epsilon:
        web_class = 1
    elif web_ratio <= 38 * epsilon:
        web_class = 2
    elif web_ratio <= 42 * epsilon:
        web_class = 3
    else:
        web_class = 4

    c_flange = (b - tw - 2 * r) / 2
    flange_ratio = c_flange / tf
    if flange_ratio <= 9 * epsilon:
        flange_class = 1
    elif flange_ratio <= 10 * epsilon:
        flange_class = 2
    elif flange_ratio <= 14 * epsilon:
        flange_class = 3
    else:
        flange_class = 4

    section_class = max(web_class, flange_class)
    return section_class, web_class, flange_class, web_ratio, flange_ratio


def _buckling_reduction_factor(lambda_bar: float, alpha: float) -> float:
    if lambda_bar <= 0.2:
        return 1.0
    phi = 0.5 * (1 + alpha * (lambda_bar - 0.2) + lambda_bar**2)
    chi = 1.0 / (phi + math.sqrt(max(phi**2 - lambda_bar**2, 0.0)))
    return min(chi, 1.0)


def calculate(inputs: ColumnCapacityInput) -> CalcResult:
    warnings: list[str] = [
        "Verify all Table 5.2/6.1/6.2 constants and gamma_M1 used here against the current "
        "edition of EN 1993-1-1 and the UK National Annex before relying on this for a real "
        "design submission -- see the module docstring.",
        "PURE AXIAL COMPRESSION ONLY -- this module does not perform the EN 1993-1-1 SS6.3.3 "
        "combined bending+axial interaction check. If this member also carries significant "
        "bending, the axial buckling resistance below is not, on its own, a valid member check.",
        "Torsional/torsional-flexural buckling is not checked -- flexural buckling is assumed to "
        "govern (valid for doubly-symmetric I/H sections only).",
    ]
    risk_flags: list[DesignRiskFlag] = []

    governing_thickness = max(inputs.flange_thickness_mm, inputs.web_thickness_mm)
    if inputs.yield_strength_override_mpa is not None:
        fy = inputs.yield_strength_override_mpa
        fy_note = "user-supplied override"
    else:
        fy = _lookup_yield_strength_mpa(inputs.steel_grade, governing_thickness)
        fy_note = f"Table 3.1, {inputs.steel_grade}, t={governing_thickness:g}mm"

    epsilon = math.sqrt(235.0 / fy)
    section_class, web_class, flange_class, web_ratio, flange_ratio = _classify_section(inputs, epsilon)

    terms: list[Term] = [
        Term("fy (nominal yield strength)", fy, unit="MPa", note=fy_note),
        Term("epsilon", epsilon, note="sqrt(235/fy)"),
        Term("Web c/t ratio (uniform compression)", web_ratio, note=f"Class {web_class}"),
        Term("Flange c/t ratio (outstand compression)", flange_ratio, note=f"Class {flange_class}"),
        Term("Section class (governing)", section_class, note="max(web class, flange class)"),
    ]

    if section_class == 4:
        risk_flags.append(
            DesignRiskFlag(
                category="code_compliance",
                severity="critical",
                description=(
                    "Section classifies as Class 4 (slender) -- this module does not compute "
                    "effective section properties (EN 1993-1-5) and has fallen back to using the "
                    "GROSS area for Nc,Rd/Nb,Rd. That is NON-CONSERVATIVE for a genuinely Class 4 "
                    "section and must not be relied on."
                ),
                trigger=f"Web class {web_class}, flange class {flange_class} -> governing Class 4.",
                recommended_action="Recompute effective section properties per EN 1993-1-5 (or select a stockier section) before proceeding.",
                source_reference="structural_column_capacity_ec3",
            )
        )
        warnings.append("Section is Class 4 -- Nc,Rd/Nb,Rd below use the gross area as a placeholder, NOT a valid EN 1993-1-5 effective-section check.")

    Nc_Rd_N = inputs.area_mm2 * fy / GAMMA_M0
    Nc_Rd_kN = Nc_Rd_N / 1e3
    terms.append(Term("Nc,Rd (cross-section compression resistance)", Nc_Rd_kN, unit="kN", note="A*fy/gamma_M0"))

    h_over_b = inputs.section_depth_mm / inputs.section_width_mm
    lambda_1 = 93.9 * epsilon
    terms.append(Term("h/b", h_over_b))
    terms.append(Term("lambda_1", lambda_1, note="93.9*epsilon"))

    results_per_axis = {}
    for axis, I, k, curve_override in (
        ("y-y", inputs.second_moment_area_y_mm4, inputs.effective_length_factor_y, inputs.buckling_curve_y_override),
        ("z-z", inputs.second_moment_area_z_mm4, inputs.effective_length_factor_z, inputs.buckling_curve_z_override),
    ):
        if curve_override is not None:
            curve = curve_override
            curve_note = "user override"
        elif h_over_b > 1.2 and inputs.flange_thickness_mm <= 40.0:
            curve = "a" if axis == "y-y" else "b"
            curve_note = "Table 6.2, rolled I-section, h/b>1.2, tf<=40mm"
        else:
            raise AssertionError("unreachable -- eligibility enforced by model_validator")
        alpha = IMPERFECTION_FACTORS[curve]

        i_axis = math.sqrt(I / inputs.area_mm2)
        Lcr_mm = k * inputs.member_length_m * 1000.0
        lambda_bar = (Lcr_mm / i_axis) / lambda_1
        chi = _buckling_reduction_factor(lambda_bar, alpha)
        Nb_Rd_kN = chi * inputs.area_mm2 * fy / GAMMA_M1 / 1e3

        terms.append(Term(f"[{axis}] Buckling curve", 0, note=f"{curve} (alpha={alpha}) -- {curve_note}"))
        terms.append(Term(f"[{axis}] i (radius of gyration)", i_axis, unit="mm"))
        terms.append(Term(f"[{axis}] Lcr (effective length)", Lcr_mm / 1000.0, unit="m", note=f"k={k:g}"))
        terms.append(Term(f"[{axis}] lambda_bar (non-dim. slenderness)", lambda_bar))
        terms.append(Term(f"[{axis}] chi (reduction factor)", chi))
        terms.append(Term(f"[{axis}] Nb,Rd", Nb_Rd_kN, unit="kN"))
        results_per_axis[axis] = Nb_Rd_kN

    governing_axis = min(results_per_axis, key=results_per_axis.get)
    Nb_Rd_governing = results_per_axis[governing_axis]
    terms.append(Term("Nb,Rd (governing)", Nb_Rd_governing, unit="kN", note=f"min of y-y/z-z -- {governing_axis} governs"))

    NEd = 1.35 * inputs.axial_permanent_load_kn + 1.5 * inputs.axial_variable_load_kn
    if NEd > 0:
        terms.append(Term("NEd (design axial compression)", NEd, unit="kN", note=f"1.35*{inputs.axial_permanent_load_kn:g} + 1.5*{inputs.axial_variable_load_kn:g}"))
        utilisation = NEd / Nb_Rd_governing
        terms.append(
            Term(
                "Utilisation", utilisation,
                note=f"NEd/Nb,Rd -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if utilisation > 1.0:
            warnings.append(f"ULS check FAILS: axial utilisation = {utilisation:.2f}.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical",
                    description=f"ULS member buckling check fails: NEd/Nb,Rd = {utilisation:.2f} (must be <= 1.0).",
                    trigger=f"NEd={NEd:.1f}kN, Nb,Rd={Nb_Rd_governing:.1f}kN ({governing_axis} governs)",
                    recommended_action="Increase section size, reduce effective length (additional restraint), or review the design.",
                    source_reference="structural_column_capacity_ec3",
                )
            )
        headline = Term(
            "Utilisation", utilisation,
            note=("PASS" if utilisation <= 1.0 else "FAIL") + f" -- NEd/Nb,Rd ({governing_axis} governs)",
        )
    else:
        headline = Term(
            "Nb,Rd (governing axial buckling resistance)", Nb_Rd_governing, unit="kN",
            note=f"No axial load supplied -- resistance-only, {governing_axis} governs.",
        )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="EN 1993-1-1 axial buckling resistance check (SS6.2.4, SS6.3.1), UK NA",
        references=[
            "BS EN 1993-1-1:2005+A1:2014, Eurocode 3: Design of steel structures — Part 1-1: General rules and rules for buildings.",
            "UK National Annex to BS EN 1993-1-1.",
            "BS EN 1990:2002+A1:2005 and UK NA, expression 6.10, for the 1.35Gk+1.5Qk ULS combination.",
        ],
    )


MODULE = CalcModule(
    key="structural_column_capacity_ec3",
    name="Steel Column Axial Buckling Capacity Check (EN 1993-1-1, UK NA)",
    discipline="Structural",
    description=(
        "Cross-section compression resistance and flexural buckling resistance (both principal "
        "axes) for a rolled steel I/H-section column under pure axial compression, to EN 1993-1-1 "
        "with UK National Annex partial factors. Does not cover combined bending+axial (SS6.3.3)."
    ),
    input_model=ColumnCapacityInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.structural.column_capacity
    # Illustrative 200x100 idealised I-section (not a real catalogue section) -- same
    # section as beam_capacity.py's example, with an assumed Iz for the worked example.
    example = ColumnCapacityInput(
        steel_grade="S275",
        section_depth_mm=200, section_width_mm=100,
        web_thickness_mm=6, flange_thickness_mm=10, root_radius_mm=8,
        area_mm2=3080, second_moment_area_y_mm4=20_982_667, second_moment_area_z_mm4=1_669_907,
        member_length_m=3.0,
        axial_permanent_load_kn=80.0, axial_variable_load_kn=40.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
