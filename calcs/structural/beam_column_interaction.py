"""
Combined bending and axial compression interaction check — EN 1993-1-1
SS6.3.3, equations (6.61)/(6.62). Answers `primary_steel_frame`'s
"Beam-column combined bending+axial interaction check" `CalculationRequirement`
in `basis_of_design/structural.py`, the gap explicitly flagged in both
`calcs/structural/beam_capacity.py` (bending-only) and
`calcs/structural/column_capacity.py` (axial-only) since neither covers a
member carrying both actions at once.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
EN 1993-1-1 SS6.3.3(4)'s two interaction equations (6.61)/(6.62) themselves
are simple, well-documented linear combinations (reproduced consistently
across textbooks, e.g. the SCI/Steel Construction Institute's publications,
and the Steel Designers' Manual) and are embedded here with the same
confidence as this repo's other Eurocode formulae. The interaction FACTORS
in those equations -- kyy, kyz, kzy, kzz -- are a different matter: EN
1993-1-1's Annex A ("Method 1") and Annex B ("Method 2") derive them from
the member's moment distribution shape (equivalent uniform moment factors
Cmy/Cmz/CmLT), section class, and slenderness, via a genuinely complex,
multi-case procedure this author does not have confident, generalisable
recall of -- getting one of these factors wrong is exactly the kind of
"looks authoritative, silently wrong" risk this repo's "flag, don't guess"
discipline exists to avoid (see `bolted_shear_connection.py`'s alpha_v for
the same reasoning applied to EN 1993-1-8). All four k-factors are
therefore REQUIRED direct inputs -- derive them from EN 1993-1-1 Annex A or
B (or equivalent software) for the actual member/loading before using this
module.

Method summary
--------------
For class 1/2/3 cross-sections (no class 4 effective-section shift, matching
`beam_capacity.py`/`column_capacity.py`'s existing scope), compression
positive, EN 1993-1-1 equations (6.61)/(6.62):

    UC1 = NEd/Nb,y,Rd + kyy*My,Ed/My,Rd + kyz*Mz,Ed/Mz,Rd      (6.61)
    UC2 = NEd/Nb,z,Rd + kzy*My,Ed/My,Rd + kzz*Mz,Ed/Mz,Rd      (6.62)

where Nb,y,Rd/Nb,z,Rd are the member's flexural buckling resistances about
each axis (from `column_capacity.py`'s output) and My,Rd/Mz,Rd are the
bending resistances about each axis. My,Rd is taken as the member's
cross-section bending resistance (from `beam_capacity.py`'s output),
implicitly assuming chi_LT=1 (no lateral-torsional buckling), consistent
with `beam_capacity.py`'s own "continuously laterally-restrained" scope --
if LTB genuinely governs for the member being checked, My,Rd supplied here
must already be the LTB-reduced resistance (chi_LT*My,Rk/gammaM1), not the
plain cross-section resistance. The governing utilisation is the larger of
UC1/UC2.

Known simplifications / not implemented (see Warnings in the result):
- kyy, kyz, kzy, kzz are required direct inputs -- see above.
- Class 1/2/3 sections only -- no class 4 effective-section delta-M shift
  term, consistent with `beam_capacity.py`/`column_capacity.py`.
- Assumes NEd is compressive -- a member in net tension combined with
  bending needs a different check (EN 1993-1-1 SS6.2.1/6.3.3 note 1), not
  this module.
- Assumes chi_LT=1 (no LTB) unless My,Rd is supplied already LTB-reduced --
  see above.
- Uniaxial major-axis bending is the common case in this repo so far
  (neither `beam_capacity.py` nor `deck_grating.py` computes minor-axis
  bending) -- Mz,Ed defaults to 0, in which case Mz,Rd's value doesn't
  affect the result.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class BeamColumnInteractionInput(BaseModel):
    design_axial_force_ned_kn: float = Field(..., gt=0, description="Design axial compressive force, NEd (kN).")
    axial_buckling_resistance_y_nb_y_rd_kn: float = Field(..., gt=0, description="Flexural buckling resistance about the major (y) axis, Nb,y,Rd (kN) -- from calcs/structural/column_capacity.py.")
    axial_buckling_resistance_z_nb_z_rd_kn: float = Field(..., gt=0, description="Flexural buckling resistance about the minor (z) axis, Nb,z,Rd (kN) -- from calcs/structural/column_capacity.py.")

    design_moment_y_my_ed_knm: float = Field(..., gt=0, description="Design bending moment about the major (y) axis, My,Ed (kNm).")
    moment_resistance_y_my_rd_knm: float = Field(..., gt=0, description="Bending resistance about the major (y) axis, My,Rd (kNm) -- from calcs/structural/beam_capacity.py. Assumes chi_LT=1 (no LTB) unless already LTB-reduced, see module docstring.")

    design_moment_z_mz_ed_knm: float = Field(0.0, ge=0, description="Design bending moment about the minor (z) axis, Mz,Ed (kNm) -- 0 for the common uniaxial major-axis-only case.")
    moment_resistance_z_mz_rd_knm: float = Field(..., gt=0, description="Bending resistance about the minor (z) axis, Mz,Rd (kNm). Not used if design_moment_z_mz_ed_knm is 0.")

    k_yy: float = Field(..., gt=0, description="Interaction factor kyy, EN 1993-1-1 Annex A or B -- required direct input, see module docstring.")
    k_yz: float = Field(..., gt=0, description="Interaction factor kyz, EN 1993-1-1 Annex A or B.")
    k_zy: float = Field(..., gt=0, description="Interaction factor kzy, EN 1993-1-1 Annex A or B.")
    k_zz: float = Field(..., gt=0, description="Interaction factor kzz, EN 1993-1-1 Annex A or B.")


def calculate(inputs: BeamColumnInteractionInput) -> CalcResult:
    warnings: list[str] = [
        "k-factors (kyy, kyz, kzy, kzz) are required direct inputs from EN 1993-1-1 Annex A or B (or "
        "equivalent software) -- the complex, form-dependent derivation of these factors is NOT reproduced "
        "by this module. See module docstring.",
        "Class 1/2/3 sections only, chi_LT=1 (no LTB) assumed unless My,Rd is already LTB-reduced, and "
        "assumes NEd is compressive -- see module docstring.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    N = inputs.design_axial_force_ned_kn
    My = inputs.design_moment_y_my_ed_knm
    Mz = inputs.design_moment_z_mz_ed_knm

    UC1 = (
        N / inputs.axial_buckling_resistance_y_nb_y_rd_kn
        + inputs.k_yy * My / inputs.moment_resistance_y_my_rd_knm
        + inputs.k_yz * Mz / inputs.moment_resistance_z_mz_rd_knm
    )
    UC2 = (
        N / inputs.axial_buckling_resistance_z_nb_z_rd_kn
        + inputs.k_zy * My / inputs.moment_resistance_y_my_rd_knm
        + inputs.k_zz * Mz / inputs.moment_resistance_z_mz_rd_knm
    )

    terms: list[Term] = [
        Term("UC1 (eq 6.61, major-axis buckling)", UC1, note=f"{'PASS' if UC1 <= 1.0 else 'FAIL'} (<=1.0 required)"),
        Term("UC2 (eq 6.62, minor-axis buckling)", UC2, note=f"{'PASS' if UC2 <= 1.0 else 'FAIL'} (<=1.0 required)"),
    ]

    governing = max(UC1, UC2)
    governing_eq = "6.61 (major-axis buckling)" if UC1 >= UC2 else "6.62 (minor-axis buckling)"
    terms.append(Term("Governing utilisation", governing, note=f"max(UC1, UC2) -- governed by eq {governing_eq}"))

    if governing > 1.0:
        warnings.append(f"FAILS: governing utilisation {governing:.3f} (eq {governing_eq}) exceeds 1.0.")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Combined bending+axial interaction check fails: governing utilisation {governing:.3f} (eq {governing_eq}).",
            trigger=f"UC1={UC1:.3f}, UC2={UC2:.3f}",
            recommended_action="Increase the member's section size, reduce the axial load or moment, or provide additional lateral/torsional restraint to improve the governing buckling resistance.",
            source_reference="structural_beam_column_interaction_ec3",
        ))

    headline = Term(
        "Governing utilisation", governing,
        note=("PASS" if governing <= 1.0 else "FAIL") + f" -- max(UC1, UC2), governed by eq {governing_eq} (EN 1993-1-1 SS6.3.3)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="EN 1993-1-1 SS6.3.3(4) combined bending and axial compression interaction check, equations (6.61)/(6.62)",
        references=[
            "BS EN 1993-1-1, Eurocode 3: Design of steel structures -- Part 1-1: General rules and rules for buildings, Clause 6.3.3.",
        ],
    )


MODULE = CalcModule(
    key="structural_beam_column_interaction_ec3",
    name="Beam-Column Combined Bending+Axial Interaction Check (EN 1993-1-1 SS6.3.3, UK NA)",
    discipline="Structural",
    description=(
        "UC1/UC2 = N/Nb,Rd + k*M/M,Rd (equations 6.61/6.62) for a member carrying both bending and axial "
        "compression. k-factors are required direct inputs from EN 1993-1-1 Annex A/B -- see module docstring."
    ),
    input_model=BeamColumnInteractionInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.structural.beam_column_interaction
    example = BeamColumnInteractionInput(
        design_axial_force_ned_kn=200.0,
        axial_buckling_resistance_y_nb_y_rd_kn=500.0,
        axial_buckling_resistance_z_nb_z_rd_kn=350.0,
        design_moment_y_my_ed_knm=80.0,
        moment_resistance_y_my_rd_knm=150.0,
        design_moment_z_mz_ed_knm=10.0,
        moment_resistance_z_mz_rd_knm=40.0,
        k_yy=0.9,
        k_yz=0.6,
        k_zy=0.6,
        k_zz=0.9,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
