"""
Pipe sustained stress and thermal expansion stress range check — ASME
B31.3 SS302.3.5. Answers `pipe_stress_analysis_and_supports`'s "Pipe
flexibility/stress analysis" `CalculationRequirement` in
`basis_of_design/mechanical_piping.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module does NOT perform a flexibility analysis. Determining the
resultant moments a piping system's supports/anchors impose on a given
point requires solving the system's full stiffness matrix (a 3D structural
analysis of the actual routed geometry, restraints, and thermal growth) --
genuinely needs dedicated software (CAESAR II, AutoPIPE, or equivalent),
not something reducible to a formula, in the same way this repo doesn't
attempt full building-frame analysis. What this module DOES do is the
STRESS EVALUATION step that follows a flexibility analysis: given the
resultant moments at a point (already computed externally), apply ASME
B31.3's sustained stress and thermal expansion stress range equations,
which are well-documented, consistently-reproduced formulas -- the same
confidence tier as `beam_column_interaction.py`'s equations (6.61)/(6.62),
where the governing equations are embedded but the case-specific inputs
(there, k-factors; here, resultant moments) are required direct inputs.

Also required direct inputs, for the same "flag, don't guess" reasoning as
elsewhere in this repo:
- Stress intensification factors (SIFs) -- B31.3 Appendix D derives these
  per fitting type/geometry (elbow radius, tee branch ratio, etc.), a
  genuinely case-specific lookup this module does not reproduce.
- Allowable stresses Sc/Sh -- B31.3 Table A-1 / BS EN 13480-3, material-
  and temperature-dependent tabulated values, same treatment as
  `cable_sizing_voltage_drop.py`'s tabulated cable rating.
- Wall thickness -- ASME B36.10M pipe schedule data, same treatment as
  `line_sizing_velocity_check.py`.

Method summary
--------------
Section modulus of the pipe cross-section (computed from OD/wall
thickness, standard hollow-cylinder mechanics -- high confidence, no
tables involved):

    Di = Do - 2*t
    Z = pi*(Do^4 - Di^4) / (32*Do)

Sustained longitudinal stress (SS302.3.5(c), Eq 17):

    SL = P*Do/(4*t) + 0.75*i*Ma/Z          <=  Sh

Thermal expansion stress range (SS302.3.5(d), Eq 1a/13):

    Sb = sqrt((ii*Mi)^2 + (io*Mo)^2) / Z
    St = Mt / (2*Z)
    SE = sqrt(Sb^2 + 4*St^2)                <=  SA

    f  = min(1.0, 6.0*N^-0.2)               (stress range reduction factor,
                                              N = design displacement cycles)
    SA = f*(1.25*(Sc+Sh) - SL)              (Eq 1b -- credits unused
                                              sustained capacity when Sh>SL)

Known simplifications / not implemented (see Warnings in the result):
- Does NOT perform flexibility analysis -- resultant moments (Ma, Mi, Mo,
  Mt) are required direct inputs from an external analysis, see above.
- SIFs (ii, io, and the sustained-case i) and allowable stresses (Sc, Sh)
  are required direct inputs, not derived from fitting geometry or
  material/temperature lookup tables.
- Occasional loads (wind, seismic, relief valve reaction) are NOT checked
  -- sustained and thermal expansion only, per this discipline's own scope.
- Does not determine whether a full formal flexibility analysis is
  required in the first place (B31.3's simplified screening criterion for
  small/simple systems) -- this module assumes one has already been done.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class PipeStressCheckInput(BaseModel):
    design_pressure_mpa: float = Field(..., gt=0, description="Internal design pressure, P (MPa).")
    outside_diameter_mm: float = Field(..., gt=0, description="Pipe outside diameter, Do (mm).")
    wall_thickness_mm: float = Field(..., gt=0, description="Wall thickness, t (mm) -- from ASME B36.10M for the selected nominal size/schedule, not derived by this module.")

    resultant_sustained_moment_ma_nm: float = Field(..., ge=0, description="Resultant moment due to sustained (weight) loads, Ma (N.m), at the point being checked -- from an external flexibility analysis.")
    sif_sustained_i: float = Field(..., gt=0, description="Stress intensification factor for the sustained-load check, i -- B31.3 Appendix D for the fitting type at this point (straight pipe i=1.0). Not derived by this module.")
    allowable_stress_hot_sh_mpa: float = Field(..., gt=0, description="Basic allowable stress at the maximum (hot) metal temperature, Sh (MPa) -- B31.3 Table A-1/BS EN 13480-3, material- and temperature-dependent. Not derived by this module.")
    allowable_stress_cold_sc_mpa: float = Field(..., gt=0, description="Basic allowable stress at minimum (cold/ambient) metal temperature, Sc (MPa) -- same table as Sh.")

    resultant_in_plane_moment_mi_nm: float = Field(..., ge=0, description="Resultant in-plane bending moment from thermal expansion, Mi (N.m).")
    resultant_out_plane_moment_mo_nm: float = Field(..., ge=0, description="Resultant out-of-plane bending moment from thermal expansion, Mo (N.m).")
    resultant_torsional_moment_mt_nm: float = Field(..., ge=0, description="Resultant torsional moment from thermal expansion, Mt (N.m).")
    sif_in_plane_ii: float = Field(..., gt=0, description="In-plane stress intensification factor, ii -- B31.3 Appendix D for the fitting type. Not derived by this module.")
    sif_out_plane_io: float = Field(..., gt=0, description="Out-of-plane stress intensification factor, io -- B31.3 Appendix D for the fitting type. Not derived by this module.")

    design_cycles_n: float = Field(7000.0, gt=0, description="Number of significant displacement stress range cycles expected over the design life, N -- illustrative default (f=1.0 threshold), confirm against the project's actual expected thermal cycling.")


def calculate(inputs: PipeStressCheckInput) -> CalcResult:
    warnings: list[str] = [
        "Does NOT perform flexibility analysis -- resultant moments (Ma, Mi, Mo, Mt) are required direct "
        "inputs from an external analysis (e.g. CAESAR II). See module docstring.",
        "SIFs and allowable stresses (Sc, Sh) are required direct inputs, not derived from fitting geometry "
        "or material/temperature lookup tables.",
        "Occasional loads (wind, seismic, relief valve reaction) are NOT checked -- sustained and thermal "
        "expansion only.",
        "Does not determine whether a full formal flexibility analysis is required in the first place -- "
        "assumes one has already been done.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    P = inputs.design_pressure_mpa
    Do = inputs.outside_diameter_mm
    t = inputs.wall_thickness_mm
    Di = Do - 2 * t
    Z = math.pi * (Do**4 - Di**4) / (32 * Do)

    terms: list[Term] = [
        Term("Section modulus", Z, unit="mm^3", note="pi*(Do^4-Di^4)/(32*Do)"),
    ]

    Ma_Nmm = inputs.resultant_sustained_moment_ma_nm * 1000.0
    SL = P * Do / (4 * t) + 0.75 * inputs.sif_sustained_i * Ma_Nmm / Z
    SL_utilisation = SL / inputs.allowable_stress_hot_sh_mpa

    terms.append(Term("Sustained stress, SL", SL, unit="MPa", note="P*Do/(4t) + 0.75*i*Ma/Z"))
    terms.append(Term("Sustained utilisation", SL_utilisation, note=f"SL/Sh -- {'PASS' if SL_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"))

    Mi_Nmm = inputs.resultant_in_plane_moment_mi_nm * 1000.0
    Mo_Nmm = inputs.resultant_out_plane_moment_mo_nm * 1000.0
    Mt_Nmm = inputs.resultant_torsional_moment_mt_nm * 1000.0
    Sb = math.sqrt((inputs.sif_in_plane_ii * Mi_Nmm) ** 2 + (inputs.sif_out_plane_io * Mo_Nmm) ** 2) / Z
    St = Mt_Nmm / (2 * Z)
    SE = math.sqrt(Sb**2 + 4 * St**2)

    f = min(1.0, 6.0 * inputs.design_cycles_n**-0.2)
    Sc, Sh = inputs.allowable_stress_cold_sc_mpa, inputs.allowable_stress_hot_sh_mpa
    SA = f * (1.25 * (Sc + Sh) - SL)
    SE_utilisation = SE / SA if SA > 0 else float("inf")

    terms.append(Term("Stress range reduction factor, f", f, note="min(1.0, 6.0*N^-0.2)"))
    terms.append(Term("Allowable stress range, SA", SA, unit="MPa", note="f*(1.25*(Sc+Sh)-SL)"))
    terms.append(Term("Expansion stress range, SE", SE, unit="MPa", note="sqrt(Sb^2+4*St^2)"))
    terms.append(Term("Expansion utilisation", SE_utilisation, note=f"SE/SA -- {'PASS' if SE_utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"))

    if SL_utilisation > 1.0:
        warnings.append(f"FAILS sustained stress: SL ({SL:.1f} MPa) exceeds Sh ({Sh:.1f} MPa).")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Sustained stress SL ({SL:.1f} MPa) exceeds the hot allowable stress Sh ({Sh:.1f} MPa).",
            trigger=f"SL={SL:.1f}MPa > Sh={Sh:.1f}MPa",
            recommended_action="Increase wall thickness, add supports to reduce the sustained moment, or reroute to reduce span.",
            source_reference="mechanical_piping_pipe_stress_check",
        ))
    if SE_utilisation > 1.0:
        warnings.append(f"FAILS thermal expansion stress range: SE ({SE:.1f} MPa) exceeds SA ({SA:.1f} MPa).")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Thermal expansion stress range SE ({SE:.1f} MPa) exceeds the allowable stress range SA ({SA:.1f} MPa).",
            trigger=f"SE={SE:.1f}MPa > SA={SA:.1f}MPa",
            recommended_action="Add flexibility (expansion loops, changes of direction), relocate anchors/restraints, or reduce the expected cycle count if achievable.",
            source_reference="mechanical_piping_pipe_stress_check",
        ))

    governing = max(SL_utilisation, SE_utilisation)
    governing_check = "sustained stress" if SL_utilisation >= SE_utilisation else "thermal expansion stress range"

    headline = Term(
        "Governing utilisation", governing,
        note=("PASS" if governing <= 1.0 else "FAIL") + f" -- max(sustained, thermal expansion), governed by {governing_check} (ASME B31.3)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="ASME B31.3 SS302.3.5 sustained stress (Eq 17) and thermal expansion stress range (Eq 1a/13) check, from externally-supplied resultant moments",
        references=[
            "ASME B31.3, Process Piping -- Chapter II, Part 3, Section 302.3.5.",
        ],
    )


MODULE = CalcModule(
    key="mechanical_piping_pipe_stress_check",
    name="Pipe Sustained Stress and Thermal Expansion Stress Range Check (ASME B31.3)",
    discipline="Mechanical Piping",
    description=(
        "ASME B31.3 sustained stress (Eq 17) and thermal expansion stress range (Eq 1a/13) check from "
        "externally-supplied resultant moments -- does not perform flexibility analysis, see module docstring."
    ),
    input_model=PipeStressCheckInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.mechanical_piping.pipe_stress_check
    example = PipeStressCheckInput(
        design_pressure_mpa=2.0,
        outside_diameter_mm=114.3,
        wall_thickness_mm=6.02,
        resultant_sustained_moment_ma_nm=500.0,
        sif_sustained_i=1.5,
        allowable_stress_hot_sh_mpa=110.0,
        allowable_stress_cold_sc_mpa=150.0,
        resultant_in_plane_moment_mi_nm=800.0,
        resultant_out_plane_moment_mo_nm=600.0,
        resultant_torsional_moment_mt_nm=300.0,
        sif_in_plane_ii=1.8,
        sif_out_plane_io=1.5,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
