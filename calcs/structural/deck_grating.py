"""
Deck/grating bearing bar loading and deflection check — imposed loads to BS
EN 1991-1-1, elastic stress/deflection check to BS EN 1993-1-1. Answers
`platforms_and_walkways`'s "Deck/grating loading and deflection check"
`CalculationRequirement` in `basis_of_design/structural.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from structural-engineering literature/training knowledge, not by
reading the purchased standard texts directly -- same caveat as the other
`calcs/structural/` modules. Bearing bar section properties (Wel, I) are
catalogue inputs, not derived from bar depth/thickness, for the same
"real rolled/pressed section properties are more reliably read from a
manufacturer's data sheet than reconstructed here" reasoning as
`beam_capacity.py`'s section properties -- see that module's docstring.

Method summary
--------------
Open-mesh/bar grating is modelled as a series of parallel bearing bars
spanning simply-supported between primary supports, each picking up a
tributary width equal to `bar_spacing_mm` from the panel's imposed UDL, plus
a share of any concentrated load:

    w_per_bar = udl_kn_m2 * bar_spacing_mm / 1000        (kN/m, per bearing bar)
    P_per_bar = point_load_kn / point_load_bars_engaged  (kN, per bearing bar)

    MEd = wEd_per_bar*L^2/8 + PEd_per_bar*L/4
    sigma_Ed = MEd / Wel                                  (elastic stress -- see below)

checked against fy/gamma_M0, with deflection checked the same way as
`beam_capacity.py` (5wL^4/384EI + PL^3/48EI, unfactored/characteristic).

Known simplifications / not implemented (see Warnings in the result):
- ELASTIC STRESS CHECK ONLY (no cross-section classification, no plastic
  modulus) -- bearing bars are thin flat sections where an elastic check is
  the appropriate/conventional method, unlike the rolled I/H sections
  `beam_capacity.py` classifies.
- Shear is NOT checked -- bending governs for the slender flat-bar spans
  typical of grating (span/depth ratios well beyond where shear would
  govern); not implemented rather than approximated.
- The concentrated load's distribution across `point_load_bars_engaged`
  bearing bars is a direct input (how many bars share it), not derived from
  a load-spreading/contact-area calculation -- confirm this against the
  actual grating type/manufacturer data (or BS 4592) before relying on it.
- No separate check of the grating's cross-bars/welds/clips, or of the
  supporting primary steelwork (that's `beam_capacity.py`'s job) -- this
  module checks the bearing bar spanning between supports only.
- Fixed simply-supported span assumption -- continuous-span gratings (over
  more than two supports) would have a different, generally more favourable,
  moment/deflection profile not modelled here.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from calcs.structural.beam_capacity import STEEL_YOUNGS_MODULUS_MPA, _lookup_yield_strength_mpa
from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

GAMMA_M0 = 1.0  # UK NA to BS EN 1993-1-1, cross-section resistance


class DeckGratingInput(BaseModel):
    steel_grade: Literal["S235", "S275", "S355", "S460"] = Field("S275", description="Bearing bar steel grade (BS EN 10025-2).")
    yield_strength_override_mpa: Optional[float] = Field(
        None, gt=0, description="Supply directly to bypass the built-in Table 3.1 lookup -- required if the bar thickness exceeds 40mm (vanishingly unlikely for grating, but consistent with the other structural modules).",
    )
    bar_thickness_mm: float = Field(..., gt=0, description="Bearing bar thickness, used only for the Table 3.1 fy lookup (mm).")

    bar_spacing_mm: float = Field(..., gt=0, description="Centre-to-centre spacing between load-bearing bars (mm) -- sets each bar's tributary width.")
    span_m: float = Field(..., gt=0, description="Simply-supported span of the bearing bar between primary supports, L (m).")

    bar_elastic_modulus_mm3: float = Field(..., gt=0, description="Elastic section modulus of ONE bearing bar, Wel (mm^3).")
    bar_second_moment_area_mm4: float = Field(..., gt=0, description="Second moment of area of ONE bearing bar, I (mm^4).")

    udl_permanent_kn_m2: float = Field(0.0, ge=0, description="Characteristic permanent UDL on the panel, Gk (kN/m^2) -- typically negligible/omitted for the grating's own self-check.")
    udl_variable_kn_m2: float = Field(5.0, ge=0, description="Characteristic variable (imposed) UDL on the panel, Qk (kN/m^2) -- default matches the platforms_and_walkways BoD criterion.")
    point_load_permanent_kn: float = Field(0.0, ge=0, description="Characteristic permanent concentrated load, Gk (kN).")
    point_load_variable_kn: float = Field(1.5, ge=0, description="Characteristic variable concentrated load, Qk (kN) -- default matches the platforms_and_walkways BoD criterion.")
    point_load_bars_engaged: int = Field(1, ge=1, description="Number of bearing bars assumed to share the concentrated load -- direct input, see module docstring.")

    deflection_limit_denominator: float = Field(200.0, gt=0, description="Serviceability deflection limit as span/N -- default matches the platforms_and_walkways BoD criterion.")

    @model_validator(mode="after")
    def _check_consistency(self) -> "DeckGratingInput":
        if self.yield_strength_override_mpa is None and self.bar_thickness_mm > 40.0:
            raise ValueError(
                f"bar_thickness_mm ({self.bar_thickness_mm} mm) exceeds the built-in Table 3.1 "
                "range (40mm) -- supply yield_strength_override_mpa directly."
            )
        return self


def calculate(inputs: DeckGratingInput) -> CalcResult:
    warnings: list[str] = [
        "Verify fy (Table 3.1) used here against the current edition of EN 1993-1-1 and the UK "
        "National Annex before relying on this for a real design submission.",
        "Elastic stress check only -- no cross-section classification or plastic modulus, "
        "appropriate for thin flat bearing bars but distinct from beam_capacity.py's method.",
        "Shear is NOT checked -- bending governs for typical grating bearing bar span/depth "
        "ratios; not implemented rather than approximated.",
        "The concentrated load's distribution across point_load_bars_engaged bearing bars is a "
        "direct input, not derived from a load-spreading calculation -- confirm against the "
        "actual grating type/manufacturer data.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    if inputs.yield_strength_override_mpa is not None:
        fy = inputs.yield_strength_override_mpa
        fy_note = "user-supplied override"
    else:
        fy = _lookup_yield_strength_mpa(inputs.steel_grade, inputs.bar_thickness_mm)
        fy_note = f"Table 3.1, {inputs.steel_grade}, t={inputs.bar_thickness_mm:g}mm"

    allowable_stress = fy / GAMMA_M0
    terms: list[Term] = [
        Term("fy (nominal yield strength)", fy, unit="MPa", note=fy_note),
        Term("Allowable elastic stress", allowable_stress, unit="MPa", note="fy/gamma_M0"),
    ]

    L = inputs.span_m
    gamma_G, gamma_Q = 1.35, 1.5

    w_per_bar_perm = inputs.udl_permanent_kn_m2 * inputs.bar_spacing_mm / 1000.0
    w_per_bar_var = inputs.udl_variable_kn_m2 * inputs.bar_spacing_mm / 1000.0
    wEd_per_bar = gamma_G * w_per_bar_perm + gamma_Q * w_per_bar_var

    P_per_bar_perm = inputs.point_load_permanent_kn / inputs.point_load_bars_engaged
    P_per_bar_var = inputs.point_load_variable_kn / inputs.point_load_bars_engaged
    PEd_per_bar = gamma_G * P_per_bar_perm + gamma_Q * P_per_bar_var

    terms.append(Term("w per bar (tributary UDL)", w_per_bar_perm + w_per_bar_var, unit="kN/m", note=f"spacing {inputs.bar_spacing_mm:g}mm"))
    terms.append(Term("P per bar (tributary point load)", P_per_bar_perm + P_per_bar_var, unit="kN", note=f"{inputs.point_load_bars_engaged} bar(s) engaged"))
    terms.append(Term("wEd per bar (design UDL)", wEd_per_bar, unit="kN/m"))
    terms.append(Term("PEd per bar (design point load)", PEd_per_bar, unit="kN"))

    MEd = wEd_per_bar * L**2 / 8 + PEd_per_bar * L / 4
    terms.append(Term("MEd (design bending moment, per bar)", MEd, unit="kNm", note="wEd*L^2/8 + PEd*L/4"))

    sigma_Ed = MEd * 1e6 / inputs.bar_elastic_modulus_mm3
    terms.append(Term("sigma_Ed (elastic bending stress)", sigma_Ed, unit="MPa", note="MEd/Wel"))

    any_load = any([
        inputs.udl_permanent_kn_m2, inputs.udl_variable_kn_m2,
        inputs.point_load_permanent_kn, inputs.point_load_variable_kn,
    ])

    if any_load:
        bending_utilisation = sigma_Ed / allowable_stress
        terms.append(
            Term(
                "Bending utilisation", bending_utilisation,
                note=f"sigma_Ed/allowable -- {'PASS' if bending_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )

        w_char = w_per_bar_perm + w_per_bar_var  # kN/m == N/mm numerically
        P_char_N = (P_per_bar_perm + P_per_bar_var) * 1000.0
        L_mm = L * 1000.0
        I = inputs.bar_second_moment_area_mm4
        delta_mm = (
            5 * w_char * L_mm**4 / (384 * STEEL_YOUNGS_MODULUS_MPA * I)
            + P_char_N * L_mm**3 / (48 * STEEL_YOUNGS_MODULUS_MPA * I)
        )
        delta_limit_mm = L_mm / inputs.deflection_limit_denominator
        deflection_utilisation = delta_mm / delta_limit_mm

        terms.append(Term("Deflection (unfactored, characteristic)", delta_mm, unit="mm", note="5wL^4/384EI + PL^3/48EI"))
        terms.append(Term(f"Deflection limit (span/{inputs.deflection_limit_denominator:g})", delta_limit_mm, unit="mm"))
        terms.append(
            Term(
                "Deflection utilisation", deflection_utilisation,
                note=f"{'PASS' if deflection_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )

        failed = bending_utilisation > 1.0 or deflection_utilisation > 1.0
        if failed:
            failing = []
            if bending_utilisation > 1.0:
                failing.append(f"bending ({bending_utilisation:.2f})")
            if deflection_utilisation > 1.0:
                failing.append(f"deflection ({deflection_utilisation:.2f})")
            warnings.append(f"Check FAILS: {', '.join(failing)} utilisation exceeds 1.0.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical" if bending_utilisation > 1.0 else "high",
                    description=f"Bearing bar check fails: {', '.join(failing)} utilisation exceeds 1.0.",
                    trigger=f"sigma_Ed/allowable={bending_utilisation:.2f}, deflection utilisation={deflection_utilisation:.2f}",
                    recommended_action="Reduce bar spacing/span, select a stiffer/stronger bearing bar, or review the loading with the client.",
                    source_reference="structural_deck_grating_ec3",
                )
            )

        governing = max(bending_utilisation, deflection_utilisation)
        headline = Term(
            "Governing utilisation", governing,
            note=("PASS" if governing <= 1.0 else "FAIL") + " -- max of bending/deflection utilisation",
        )
    else:
        headline = Term(
            "Allowable elastic stress", allowable_stress, unit="MPa",
            note="No loads supplied -- resistance-only, no utilisation check.",
        )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Deck/grating bearing bar elastic stress and deflection check, BS EN 1991-1-1 imposed loads / BS EN 1993-1-1 UK NA",
        references=[
            "BS EN 1991-1-1:2002, Eurocode 1: Actions on structures — Part 1-1: General actions — Densities, self-weight, imposed loads for buildings.",
            "BS EN 1993-1-1:2005+A1:2014, Eurocode 3: Design of steel structures — Part 1-1: General rules and rules for buildings.",
            "BS 4592 (series), Industrial type flooring, walkways and stair treads — confirm current part/edition for grating specification.",
            "UK National Annex to BS EN 1993-1-1.",
        ],
    )


MODULE = CalcModule(
    key="structural_deck_grating_ec3",
    name="Deck/Grating Bearing Bar Check (BS EN 1991-1-1 loads, EN 1993-1-1 stress check, UK NA)",
    discipline="Structural",
    description=(
        "Elastic bending stress and deflection check for a grating/decking bearing bar spanning "
        "simply-supported between primary supports, under BS EN 1991-1-1 imposed UDL and a "
        "concentrated load, checked to EN 1993-1-1 with UK National Annex partial factors."
    ),
    input_model=DeckGratingInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.structural.deck_grating
    # Illustrative 30x5mm flat bearing bar (rectangular section), 40mm spacing, 0.5m
    # span between cross-bars/supports -- typical proportions for open-mesh grating.
    example = DeckGratingInput(
        steel_grade="S275",
        bar_thickness_mm=5.0,
        bar_spacing_mm=40.0,
        span_m=0.5,
        bar_elastic_modulus_mm3=750.0,  # 5x30mm rectangular bar: t*d^2/6
        bar_second_moment_area_mm4=11250.0,  # t*d^3/12
        point_load_bars_engaged=2,  # point load contact typically spans more than one bar
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
