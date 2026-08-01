"""
Column base plate bearing and holding-down (HD) bolt tension check — EN
1993-1-8 (Eurocode 3, Part 1-8), UK National Annex. Answers
`substructure_and_foundations`'s "Base plate / holding-down bolt design"
`CalculationRequirement` in `basis_of_design/structural.py` -- the
foundation-facing end of the same load path `column_capacity.py` checks the
member for (that module's design axial load, NEd, is the natural input to
this one's bearing check).

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Built from structural-engineering literature/training knowledge, not by
reading the purchased BS EN 1993-1-8 standard text directly -- same caveat as
the other `calcs/structural/` modules. One SPECIFIC, DELIBERATE scope
reduction here, beyond the usual caveat: EN 1993-1-8 SS6.2.5's "effective
area" (T-stub-in-compression) method for a base plate's effective bearing
area around an I-section footprint involves effective-width geometry (flange
and web strips, with potential overlap between them) that this author is not
confident of reconstructing correctly without the standard text or a
reference figure in front of them. Rather than implement that geometry with
material uncertainty, `base_plate_effective_area_mm2` is a REQUIRED DIRECT
INPUT -- compute it externally (by the T-stub method, or conservatively as
the full nominal plate area only if a wider check confirms that's reasonable
for the specific plate/column geometry) and supply it directly. Similarly
`design_bearing_strength_mpa` (fjd, the concrete/grout bearing strength under
the joint coefficient beta_j) is a required direct input rather than derived
from fck here. This module's real computational content is therefore the
ULS bearing utilisation check and the (higher-confidence) HD bolt tension
check, not effective-area or bearing-strength derivation -- see Known
simplifications.

Method summary
--------------
Concrete/grout bearing under the base plate:

    Nj,Rd = fjd * Aeff                       (both supplied directly, see above)

Holding-down bolt tension under net uplift (only relevant if the column can
see net tension, e.g. from wind):

    Ft,Rd = 0.9 * fub * As / gamma_M2         (EN 1993-1-8 Table 3.4, per bolt)

assumed shared equally across `number_of_hd_bolts` (concentric uplift only --
see Known simplifications).

Known simplifications / not implemented (see Warnings in the result):
- Effective bearing area (Aeff) and design bearing strength (fjd) are DIRECT
  INPUTS, not derived by this module -- see above. This module checks
  bearing utilisation given those values; it does not perform the full
  EN 1993-1-8 SS6.2.5 base plate sizing method.
- Base plate BENDING (the plate itself spanning between the column profile
  and its edge, or between HD bolts) is NOT checked -- only the concrete
  bearing and the bolts' tension resistance.
- Net uplift is taken as already resolved (self-weight vs wind, etc.) into
  the two characteristic uplift inputs supplied -- this module applies
  standard unfavourable ULS factors (1.35/1.5) to whatever is supplied, it
  does not itself perform a favourable/unfavourable permanent-action
  sensitivity check for the uplift case.
- HD bolt group assumed to share uplift tension equally (concentric) -- not
  valid for a base plate with significant applied moment, where bolt rows
  see unequal tension. Prying action is not checked.
- Combined bearing + moment (the fully general base plate case) is not
  covered -- this module addresses concentric axial bearing and, separately,
  concentric uplift tension, matching `column_capacity.py`'s own pure-axial
  scope.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

GAMMA_M2 = 1.25  # UK NA to BS EN 1993-1-8, resistance of bolts in tension

# fub (ultimate tensile strength, MPa) per EN ISO 898-1 bolt property class --
# definitional (grade X.Y => fub = 100*X MPa), same table as beam_capacity.py/
# bolted_shear_connection.py.
_BOLT_GRADE_FUB: dict[str, float] = {"4.6": 400.0, "5.6": 500.0, "8.8": 800.0, "10.9": 1000.0}


class BasePlateInput(BaseModel):
    base_plate_effective_area_mm2: float = Field(
        ..., gt=0,
        description="Effective bearing area, Aeff (mm^2) -- compute externally per EN 1993-1-8 SS6.2.5 (T-stub-in-compression) or conservatively as the full nominal plate area only if confirmed reasonable for the specific geometry. NOT derived by this module -- see docstring.",
    )
    design_bearing_strength_mpa: float = Field(
        ..., gt=0,
        description="Design bearing strength of the joint material, fjd (MPa) -- e.g. concrete/grout bearing strength incorporating the joint coefficient beta_j per EN 1993-1-8 SS6.2.5. NOT derived by this module -- see docstring.",
    )

    axial_permanent_load_kn: float = Field(0.0, ge=0, description="Characteristic permanent axial compression on the base, NGk (kN).")
    axial_variable_load_kn: float = Field(0.0, ge=0, description="Characteristic variable axial compression on the base, NQk (kN).")

    uplift_permanent_kn: float = Field(0.0, ge=0, description="Characteristic net permanent uplift (tension) on the base, if any (kN).")
    uplift_variable_kn: float = Field(0.0, ge=0, description="Characteristic net variable uplift (tension) on the base, e.g. from wind (kN).")
    number_of_hd_bolts: int = Field(4, ge=1, description="Holding-down bolts assumed to share uplift tension equally (concentric only).")
    hd_bolt_grade: Literal["4.6", "5.6", "8.8", "10.9"] = Field("4.6", description="HD bolt property class (EN ISO 898-1) -- 4.6 is common for anchor/HD bolts.")
    hd_bolt_tensile_stress_area_mm2: Optional[float] = Field(
        None, gt=0, description="Tensile stress area, As (mm^2), per HD bolt -- required if any uplift is supplied.",
    )

    @model_validator(mode="after")
    def _check_consistency(self) -> "BasePlateInput":
        if (self.uplift_permanent_kn > 0 or self.uplift_variable_kn > 0) and self.hd_bolt_tensile_stress_area_mm2 is None:
            raise ValueError("hd_bolt_tensile_stress_area_mm2 is required when uplift_permanent_kn or uplift_variable_kn is supplied.")
        return self


def calculate(inputs: BasePlateInput) -> CalcResult:
    warnings: list[str] = [
        "base_plate_effective_area_mm2 and design_bearing_strength_mpa are direct inputs, not "
        "derived by this module -- see the module docstring for why (T-stub effective-area "
        "geometry not implemented with sufficient confidence).",
        "Base plate bending (the plate spanning between the column profile/HD bolts and its edge) "
        "is NOT checked -- only concrete/grout bearing and HD bolt tension.",
        "Combined bearing + applied moment is not covered -- concentric axial bearing and "
        "concentric uplift tension are checked separately, matching column_capacity.py's own "
        "pure-axial scope.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    Nj_Rd_kN = inputs.design_bearing_strength_mpa * inputs.base_plate_effective_area_mm2 / 1e3
    terms: list[Term] = [
        Term("Nj,Rd (bearing resistance)", Nj_Rd_kN, unit="kN", note="fjd * Aeff"),
    ]

    NEd = 1.35 * inputs.axial_permanent_load_kn + 1.5 * inputs.axial_variable_load_kn
    bearing_utilisation: Optional[float] = None
    if NEd > 0:
        terms.append(Term("NEd (design axial compression)", NEd, unit="kN", note=f"1.35*{inputs.axial_permanent_load_kn:g} + 1.5*{inputs.axial_variable_load_kn:g}"))
        bearing_utilisation = NEd / Nj_Rd_kN
        terms.append(
            Term(
                "Bearing utilisation", bearing_utilisation,
                note=f"NEd/Nj,Rd -- {'PASS' if bearing_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if bearing_utilisation > 1.0:
            warnings.append(f"ULS bearing check FAILS: utilisation = {bearing_utilisation:.2f}.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical",
                    description=f"ULS base plate bearing check fails: NEd/Nj,Rd = {bearing_utilisation:.2f} (must be <= 1.0).",
                    trigger=f"NEd={NEd:.1f}kN, Nj,Rd={Nj_Rd_kN:.1f}kN",
                    recommended_action="Increase base plate area/bearing strength (thicker grout bed, larger plate) or reduce column load.",
                    source_reference="structural_base_plate_ec3",
                )
            )

    tension_utilisation: Optional[float] = None
    if inputs.uplift_permanent_kn > 0 or inputs.uplift_variable_kn > 0:
        fub = _BOLT_GRADE_FUB[inputs.hd_bolt_grade]
        Ft_Rd_per_bolt_kN = 0.9 * fub * inputs.hd_bolt_tensile_stress_area_mm2 / GAMMA_M2 / 1e3
        group_tension_resistance_kN = Ft_Rd_per_bolt_kN * inputs.number_of_hd_bolts
        terms.append(Term("fub (HD bolt ultimate strength)", fub, unit="MPa", note=f"grade {inputs.hd_bolt_grade}"))
        terms.append(Term("Ft,Rd (tension resistance, per HD bolt)", Ft_Rd_per_bolt_kN, unit="kN", note="0.9*fub*As/gamma_M2"))
        terms.append(Term("HD bolt group tension resistance", group_tension_resistance_kN, unit="kN", note=f"{inputs.number_of_hd_bolts} bolt(s), equally shared (concentric uplift)"))

        NEd_uplift = 1.35 * inputs.uplift_permanent_kn + 1.5 * inputs.uplift_variable_kn
        terms.append(Term("NEd,uplift (design net uplift)", NEd_uplift, unit="kN", note=f"1.35*{inputs.uplift_permanent_kn:g} + 1.5*{inputs.uplift_variable_kn:g}"))
        tension_utilisation = NEd_uplift / group_tension_resistance_kN
        terms.append(
            Term(
                "HD bolt tension utilisation", tension_utilisation,
                note=f"NEd,uplift/group resistance -- {'PASS' if tension_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if tension_utilisation > 1.0:
            warnings.append(f"ULS HD bolt tension check FAILS: utilisation = {tension_utilisation:.2f}.")
            risk_flags.append(
                DesignRiskFlag(
                    category="code_compliance",
                    severity="critical",
                    description=f"ULS HD bolt tension check fails: NEd,uplift/group resistance = {tension_utilisation:.2f} (must be <= 1.0).",
                    trigger=f"NEd,uplift={NEd_uplift:.1f}kN, group resistance={group_tension_resistance_kN:.1f}kN",
                    recommended_action="Increase HD bolt size/grade/count or review the uplift loading.",
                    source_reference="structural_base_plate_ec3",
                )
            )

    utilisations = [u for u in (bearing_utilisation, tension_utilisation) if u is not None]
    if utilisations:
        governing = max(utilisations)
        headline = Term(
            "Governing utilisation", governing,
            note=("PASS" if governing <= 1.0 else "FAIL") + " -- max of bearing/HD bolt tension utilisation",
        )
    else:
        headline = Term(
            "Nj,Rd (bearing resistance)", Nj_Rd_kN, unit="kN",
            note="No loads supplied -- resistance-only, no utilisation check.",
        )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="EN 1993-1-8 base plate bearing and HD bolt tension check, UK NA",
        references=[
            "BS EN 1993-1-8:2005, Eurocode 3: Design of steel structures — Part 1-8: Design of joints, SS6.2.5 (base plates), Table 3.4 (bolt tension).",
            "UK National Annex to BS EN 1993-1-8.",
            "BS EN 1990:2002+A1:2005 and UK NA, expression 6.10, for the 1.35Gk+1.5Qk ULS combination.",
        ],
    )


MODULE = CalcModule(
    key="structural_base_plate_ec3",
    name="Column Base Plate Bearing and HD Bolt Tension Check (EN 1993-1-8, UK NA)",
    discipline="Structural",
    description=(
        "Concrete/grout bearing utilisation under a concentric column base plate, and holding-down "
        "bolt tension utilisation under net uplift, to EN 1993-1-8 with UK National Annex partial "
        "factors. Effective bearing area and bearing strength are direct inputs -- see module docstring."
    ),
    input_model=BasePlateInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.structural.base_plate
    # Illustrative 300x300mm base plate, C25/30 grout bed, 4no M20 grade 4.6 HD bolts.
    example = BasePlateInput(
        base_plate_effective_area_mm2=90_000,  # 300x300mm, illustrative -- see docstring caveat
        design_bearing_strength_mpa=11.3,  # illustrative fjd for C25/30 concrete -- confirm before real use
        axial_permanent_load_kn=80.0, axial_variable_load_kn=40.0,
        uplift_variable_kn=15.0,  # e.g. wind uplift case
        hd_bolt_tensile_stress_area_mm2=245.0,  # M20, illustrative
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
