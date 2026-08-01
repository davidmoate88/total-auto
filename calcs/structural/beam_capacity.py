"""
Simply-supported steel beam member capacity check — EN 1993-1-1 (Eurocode 3),
UK National Annex. Answers `primary_steel_frame`'s "Beam/column member capacity
checks" `CalculationRequirement` in `basis_of_design/structural.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from structural-engineering literature/training knowledge, not by reading
the purchased BS EN 1993-1-1 standard text directly (not available to check
against here) — same caveat, and same reason for it, as
`calcs/geotechnical/bearing_capacity.py`. In particular:
- The cross-section classification limits (Table 5.2: 72/83/124*epsilon for
  internal parts in bending, 9/10/14*epsilon for outstand flanges in
  compression) and the nominal yield strength table (Table 3.1) are commonly
  reproduced constants, not independently re-derived — verify against the
  current standard text and UK NA before real use.
- Section properties (A, Iy, Wel,y, Wpl,y) are NOT computed from h/b/tw/tf here
  — they're taken as direct inputs, the same way an engineer would read them
  from a manufacturer's catalogue (e.g. the SCI "Blue Book"), because a rolled
  section's real properties (fillets, root radii, tolerances) are more
  reliably sourced from the catalogue than reconstructed from nominal
  dimensions. h/b/tw/tf/r are used ONLY for cross-section classification
  (Table 5.2), which the code Sheets define geometrically.

Method summary
--------------
For a simply-supported beam under a UDL and/or a single point load at midspan:

    MEd = wEd*L^2/8 + PEd*L/4      (design bending moment)
    VEd = wEd*L/2 + PEd/2          (design shear force)

with wEd = gamma_G*Gk_udl + gamma_Q*Qk_udl, PEd = gamma_G*Gk_point + gamma_Q*Qk_point,
gamma_G=1.35, gamma_Q=1.5 (BS EN 1990 UK NA, expression 6.10, the same combination
used in `calcs/geotechnical/bearing_capacity.py`'s DA1-C1).

Cross-section classified per Table 5.2 (web: internal part in bending; flanges:
outstand parts in compression) using c/t ratios derived from h/b/tw/tf/r.
Bending resistance Mc,Rd uses Wpl,y for Class 1/2, Wel,y for Class 3 (Class 4 is
NOT supported — see Known simplifications). Shear resistance Vpl,Rd uses the
standard rolled-I/H-section shear area formula. Deflection is checked against
span/`deflection_limit_denominator` using the unfactored (characteristic)
combination.

Known simplifications / not implemented (see Warnings in the result):
- No lateral-torsional buckling (LTB) check (EN 1993-1-1 §6.3.2). The beam is
  assumed continuously laterally restrained (e.g. by continuously-fixed
  decking/grating) unless `continuously_restrained=False`, in which case a
  warning is raised that LTB must be checked separately — this module does
  not do it.
- Class 4 (slender) sections are not supported — effective section properties
  (EN 1993-1-5) are not computed. If classification returns Class 4, a
  critical risk flag is raised and the Class-3-style elastic check is run
  anyway as a (non-conservative, unsafe to rely on) placeholder — the result
  must not be used without a proper effective-section recalculation.
- Combined bending+shear interaction (EN 1993-1-1 §6.2.8) is not implemented.
  If VEd > 0.5*Vpl,Rd, a warning is raised that the bending resistance may
  need reducing and this module does not do that reduction.
- fy (Table 3.1) is only tabulated here for the flange/web thickness up to
  40mm — beyond that, supply `yield_strength_override_mpa` directly rather
  than have this module guess.
- Deflection uses the full unfactored (Gk+Qk) combination on both UDL and
  point load together — not split into separate serviceability combinations
  (e.g. imposed-load-only deflection) a project may specifically require.
- Axial force / combined bending+axial (column) checks are not covered — this
  is a beam (bending-dominant) check only, despite `primary_steel_frame`
  naming "beam/column" together. Combined bending+axial is a separate check,
  now built as `calcs/structural/beam_column_interaction.py` (EN 1993-1-1
  SS6.3.3), which consumes this module's My,Rd output as one of its inputs.
"""

from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

STEEL_YOUNGS_MODULUS_MPA = 210_000.0
GAMMA_M0 = 1.0  # UK NA to BS EN 1993-1-1, cross-section resistance
SHEAR_AREA_ETA = 1.0  # conservative default per EN 1993-1-5 SS1.1; UK NA permits up to 1.2 for S235-S460

# BS EN 1993-1-1 Table 3.1 nominal yield strength fy (MPa), by grade and
# nominal thickness of the element under consideration. Only tabulated up to
# 40mm -- see module docstring.
_YIELD_STRENGTH_TABLE: dict[str, list[tuple[float, float]]] = {
    # (thickness upper bound mm, fy MPa), checked in order
    "S235": [(16.0, 235.0), (40.0, 225.0)],
    "S275": [(16.0, 275.0), (40.0, 265.0)],
    "S355": [(16.0, 355.0), (40.0, 345.0)],
    "S460": [(16.0, 460.0), (40.0, 440.0)],
}


def _lookup_yield_strength_mpa(grade: str, governing_thickness_mm: float) -> float:
    for upper_bound, fy in _YIELD_STRENGTH_TABLE[grade]:
        if governing_thickness_mm <= upper_bound:
            return fy
    raise ValueError(
        f"No tabulated fy for grade {grade} at thickness {governing_thickness_mm} mm "
        "(table only covers up to 40mm) -- this should have been caught by input validation."
    )


class BeamCapacityInput(BaseModel):
    steel_grade: Literal["S235", "S275", "S355", "S460"] = Field(
        "S355", description="Nominal steel grade (BS EN 10025-2)."
    )
    yield_strength_override_mpa: Optional[float] = Field(
        None, gt=0,
        description=(
            "Supply directly to bypass the built-in Table 3.1 lookup -- required if the "
            "governing element thickness exceeds 40mm, or for a non-standard/mill-certified fy."
        ),
    )

    # Section geometry (mm) -- classification only, see module docstring.
    section_depth_mm: float = Field(..., gt=0, description="Overall section depth, h (mm).")
    section_width_mm: float = Field(..., gt=0, description="Flange width, b (mm).")
    web_thickness_mm: float = Field(..., gt=0, description="Web thickness, tw (mm).")
    flange_thickness_mm: float = Field(..., gt=0, description="Flange thickness, tf (mm).")
    root_radius_mm: float = Field(
        0.0, ge=0,
        description="Root radius, r (mm). Default 0 is a conservative (worse-classification) assumption if unknown.",
    )

    # Section properties (mm units) -- from a catalogue, not derived here. See module docstring.
    area_mm2: float = Field(..., gt=0, description="Cross-sectional area, A (mm^2).")
    second_moment_area_mm4: float = Field(..., gt=0, description="Second moment of area about the major axis, Iy (mm^4).")
    elastic_modulus_mm3: float = Field(..., gt=0, description="Elastic section modulus, Wel,y (mm^3).")
    plastic_modulus_mm3: float = Field(..., gt=0, description="Plastic section modulus, Wpl,y (mm^3).")

    span_m: float = Field(..., gt=0, description="Simply-supported span, L (m).")

    udl_permanent_kn_m: float = Field(0.0, ge=0, description="Characteristic permanent UDL, Gk (kN/m).")
    udl_variable_kn_m: float = Field(0.0, ge=0, description="Characteristic variable UDL, Qk (kN/m).")
    point_load_permanent_kn: float = Field(0.0, ge=0, description="Characteristic permanent point load at midspan, Gk (kN).")
    point_load_variable_kn: float = Field(0.0, ge=0, description="Characteristic variable point load at midspan, Qk (kN).")

    continuously_restrained: bool = Field(
        True,
        description="Continuous lateral restraint to the compression flange (e.g. fixed decking). If False, LTB must be checked separately -- not done by this module.",
    )
    deflection_limit_denominator: float = Field(
        200.0, gt=0, description="Serviceability deflection limit as span/N -- default matches basis_of_design.structural's platform criterion.",
    )

    @model_validator(mode="after")
    def _check_consistency(self) -> "BeamCapacityInput":
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
        return self


def _classify_section(inputs: BeamCapacityInput, epsilon: float) -> tuple[int, int, int, float, float]:
    """
    Cross-section classification per EN 1993-1-1 Table 5.2 (web: internal
    compression part in bending; flange: outstand part in uniform compression).
    Returns (section_class, web_class, flange_class, web_ratio, flange_ratio).
    """
    h, b, tw, tf, r = (
        inputs.section_depth_mm, inputs.section_width_mm,
        inputs.web_thickness_mm, inputs.flange_thickness_mm, inputs.root_radius_mm,
    )
    c_web = h - 2 * tf - 2 * r
    web_ratio = c_web / tw
    if web_ratio <= 72 * epsilon:
        web_class = 1
    elif web_ratio <= 83 * epsilon:
        web_class = 2
    elif web_ratio <= 124 * epsilon:
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


def _shear_area_mm2(inputs: BeamCapacityInput) -> float:
    """Av for a rolled I/H section, load parallel to the web (EN 1993-1-1 SS6.2.6(3))."""
    A, b, tf, tw, r = (
        inputs.area_mm2, inputs.section_width_mm, inputs.flange_thickness_mm,
        inputs.web_thickness_mm, inputs.root_radius_mm,
    )
    hw = inputs.section_depth_mm - 2 * tf
    formula_value = A - 2 * b * tf + (tw + 2 * r) * tf
    floor_value = SHEAR_AREA_ETA * hw * tw
    return max(formula_value, floor_value)


def calculate(inputs: BeamCapacityInput) -> CalcResult:
    warnings: list[str] = [
        "Verify all Table 5.2 classification limits, Table 3.1 yield strengths, and the shear "
        "area formula used here against the current edition of EN 1993-1-1 and the UK National "
        "Annex before relying on this for a real design submission -- see the module docstring.",
        "No lateral-torsional buckling (EN 1993-1-1 SS6.3.2) check is performed -- see below.",
        "No combined bending+shear interaction (SS6.2.8) reduction is performed -- see below.",
        "Axial force / column checks are not covered -- this is a bending-dominant beam check only.",
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
        Term("Web c/t ratio", web_ratio, note=f"Class {web_class}"),
        Term("Flange c/t ratio", flange_ratio, note=f"Class {flange_class}"),
        Term("Section class (governing)", section_class, note="max(web class, flange class)"),
    ]

    if section_class == 4:
        risk_flags.append(
            DesignRiskFlag(
                category="code_compliance",
                severity="critical",
                description=(
                    "Section classifies as Class 4 (slender) -- this module does not compute "
                    "effective section properties (EN 1993-1-5) and has fallen back to an elastic "
                    "(Class-3-style) check using the GROSS section modulus. That check is "
                    "NON-CONSERVATIVE for a genuinely Class 4 section and must not be relied on."
                ),
                trigger=f"Web class {web_class}, flange class {flange_class} -> governing Class 4.",
                recommended_action="Recompute effective section properties per EN 1993-1-5 (or select a stockier section) before proceeding.",
                source_reference="structural_beam_capacity_ec3",
            )
        )
        warnings.append(
            "Section is Class 4 -- bending resistance below uses the gross elastic modulus as a "
            "placeholder, NOT a valid EN 1993-1-5 effective-section check. Do not rely on this result."
        )

    Mc_Rd_Nmm = (inputs.plastic_modulus_mm3 if section_class in (1, 2) else inputs.elastic_modulus_mm3) * fy / GAMMA_M0
    Mc_Rd_kNm = Mc_Rd_Nmm / 1e6
    modulus_used = "Wpl,y (plastic)" if section_class in (1, 2) else "Wel,y (elastic)"
    terms.append(Term("Mc,Rd (bending resistance)", Mc_Rd_kNm, unit="kNm", note=modulus_used))

    Av_mm2 = _shear_area_mm2(inputs)
    Vpl_Rd_N = Av_mm2 * (fy / math.sqrt(3)) / GAMMA_M0
    Vpl_Rd_kN = Vpl_Rd_N / 1e3
    terms.append(Term("Av (shear area)", Av_mm2, unit="mm^2"))
    terms.append(Term("Vpl,Rd (shear resistance)", Vpl_Rd_kN, unit="kN"))

    if not inputs.continuously_restrained:
        warnings.append(
            "continuously_restrained=False -- lateral-torsional buckling (EN 1993-1-1 SS6.3.2) "
            "governs for a laterally-unrestrained compression flange and is NOT checked by this "
            "module. Mc,Rd above is a cross-section (in-plane) resistance only, not Mb,Rd."
        )
        risk_flags.append(
            DesignRiskFlag(
                category="safety",
                severity="high",
                description=(
                    "Beam is not continuously laterally restrained -- lateral-torsional buckling "
                    "resistance (Mb,Rd) has not been checked and may govern well below the "
                    "in-plane Mc,Rd reported here."
                ),
                trigger="continuously_restrained=False",
                recommended_action="Check lateral-torsional buckling resistance per EN 1993-1-1 SS6.3.2 (restraint spacing, section properties) before relying on Mc,Rd.",
                source_reference="structural_beam_capacity_ec3",
            )
        )

    gamma_G, gamma_Q = 1.35, 1.5
    wEd = gamma_G * inputs.udl_permanent_kn_m + gamma_Q * inputs.udl_variable_kn_m
    PEd = gamma_G * inputs.point_load_permanent_kn + gamma_Q * inputs.point_load_variable_kn
    L = inputs.span_m

    any_load = any([
        inputs.udl_permanent_kn_m, inputs.udl_variable_kn_m,
        inputs.point_load_permanent_kn, inputs.point_load_variable_kn,
    ])

    if any_load:
        MEd = wEd * L**2 / 8 + PEd * L / 4
        VEd = wEd * L / 2 + PEd / 2
        terms.append(Term("wEd (design UDL)", wEd, unit="kN/m", note=f"1.35*{inputs.udl_permanent_kn_m:g} + 1.5*{inputs.udl_variable_kn_m:g}"))
        terms.append(Term("PEd (design point load)", PEd, unit="kN", note=f"1.35*{inputs.point_load_permanent_kn:g} + 1.5*{inputs.point_load_variable_kn:g}"))
        terms.append(Term("MEd (design bending moment)", MEd, unit="kNm", note="wEd*L^2/8 + PEd*L/4"))
        terms.append(Term("VEd (design shear force)", VEd, unit="kN", note="wEd*L/2 + PEd/2"))

        bending_utilisation = MEd / Mc_Rd_kNm
        terms.append(
            Term(
                "Bending utilisation", bending_utilisation,
                note=f"MEd/Mc,Rd -- {'PASS' if bending_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        shear_utilisation = VEd / Vpl_Rd_kN
        terms.append(
            Term(
                "Shear utilisation", shear_utilisation,
                note=f"VEd/Vpl,Rd -- {'PASS' if shear_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )

        if shear_utilisation > 0.5:
            warnings.append(
                f"Shear utilisation ({shear_utilisation:.2f}) exceeds 0.5 -- EN 1993-1-1 SS6.2.8 "
                "requires a reduced bending resistance check (high shear + high moment "
                "interaction), which this module does not perform. Bending utilisation above may "
                "be unconservative if it is also close to 1.0."
            )

        failed = bending_utilisation > 1.0 or shear_utilisation > 1.0
        if failed:
            failing = []
            if bending_utilisation > 1.0:
                failing.append(f"bending ({bending_utilisation:.2f})")
            if shear_utilisation > 1.0:
                failing.append(f"shear ({shear_utilisation:.2f})")
            warnings.append(f"ULS check FAILS: {', '.join(failing)} utilisation exceeds 1.0.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical",
                    description=f"ULS member capacity check fails: {', '.join(failing)} utilisation exceeds 1.0.",
                    trigger=f"MEd/Mc,Rd={bending_utilisation:.2f}, VEd/Vpl,Rd={shear_utilisation:.2f}",
                    recommended_action="Increase section size, reduce span/loading, or review the design.",
                    source_reference="structural_beam_capacity_ec3",
                )
            )

        w_char = inputs.udl_permanent_kn_m + inputs.udl_variable_kn_m  # kN/m == N/mm numerically
        P_char_N = (inputs.point_load_permanent_kn + inputs.point_load_variable_kn) * 1000.0
        L_mm = L * 1000.0
        I = inputs.second_moment_area_mm4
        delta_udl_mm = 5 * w_char * L_mm**4 / (384 * STEEL_YOUNGS_MODULUS_MPA * I)
        delta_point_mm = P_char_N * L_mm**3 / (48 * STEEL_YOUNGS_MODULUS_MPA * I)
        delta_total_mm = delta_udl_mm + delta_point_mm
        delta_limit_mm = L_mm / inputs.deflection_limit_denominator
        deflection_utilisation = delta_total_mm / delta_limit_mm

        terms.append(Term("Deflection (unfactored, characteristic)", delta_total_mm, unit="mm", note="5wL^4/384EI + PL^3/48EI"))
        terms.append(Term(f"Deflection limit (span/{inputs.deflection_limit_denominator:g})", delta_limit_mm, unit="mm"))
        terms.append(
            Term(
                "Deflection utilisation", deflection_utilisation,
                note=f"{'PASS' if deflection_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if deflection_utilisation > 1.0:
            warnings.append(f"SLS deflection check FAILS: utilisation = {deflection_utilisation:.2f}.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="high",
                    description=f"SLS deflection check fails: utilisation = {deflection_utilisation:.2f} (limit span/{inputs.deflection_limit_denominator:g}).",
                    trigger=f"delta={delta_total_mm:.1f}mm > limit={delta_limit_mm:.1f}mm",
                    recommended_action="Increase section stiffness (Iy), reduce span, or review the serviceability limit with the client.",
                    source_reference="structural_beam_capacity_ec3",
                )
            )

        governing_utilisation = max(bending_utilisation, shear_utilisation, deflection_utilisation)
        headline = Term(
            "Governing utilisation", governing_utilisation,
            note=("PASS" if governing_utilisation <= 1.0 else "FAIL") + " -- max of bending/shear/deflection utilisation",
        )
    else:
        headline = Term(
            "Mc,Rd (bending resistance)", Mc_Rd_kNm, unit="kNm",
            note="No loads supplied -- resistance-only, no utilisation check.",
        )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="EN 1993-1-1 member capacity check (bending, shear, deflection), UK NA",
        references=[
            "BS EN 1993-1-1:2005+A1:2014, Eurocode 3: Design of steel structures — Part 1-1: General rules and rules for buildings.",
            "UK National Annex to BS EN 1993-1-1.",
            "BS EN 1990:2002+A1:2005 and UK NA, expression 6.10, for the 1.35Gk+1.5Qk ULS combination.",
        ],
    )


MODULE = CalcModule(
    key="structural_beam_capacity_ec3",
    name="Steel Beam Member Capacity Check (EN 1993-1-1, UK NA)",
    discipline="Structural",
    description=(
        "Bending, shear, and deflection check for a simply-supported, continuously "
        "laterally-restrained steel I/H-section beam under UDL and/or a midspan point load, "
        "to EN 1993-1-1 with UK National Annex partial factors."
    ),
    input_model=BeamCapacityInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.structural.beam_capacity
    # Illustrative 200x100 idealised I-section (not a real catalogue section).
    example = BeamCapacityInput(
        steel_grade="S275",
        section_depth_mm=200, section_width_mm=100,
        web_thickness_mm=6, flange_thickness_mm=10, root_radius_mm=8,
        area_mm2=3080, second_moment_area_mm4=20_982_667,
        elastic_modulus_mm3=209_827, plastic_modulus_mm3=238_600,
        span_m=4.0,
        udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
