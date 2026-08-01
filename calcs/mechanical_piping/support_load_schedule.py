"""
Pipe support load schedule — aggregates per-support reaction loads for
handover to the structural discipline. Answers
`pipe_stress_analysis_and_supports`'s "Support load schedule"
`CalculationRequirement` in `basis_of_design/mechanical_piping.py`, and
`supports_structural_and_hazardous_area_interfaces`'s "Support load
handover format" `DesignCriterion` ("line list with support loads, by
support point").

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Support reactions come from the SAME external flexibility analysis
(CAESAR II or equivalent) that supplies `calcs/mechanical_piping/
pipe_stress_check.py`'s resultant moments -- this module does not derive
them from that module's output (different quantities: stress-check moments
at a point vs. reaction forces at a support), it aggregates and screens
values already computed elsewhere.

Loads are handed over UNFACTORED, per real handover practice -- a support
load schedule is not pre-combined with structural's own partial factors;
the receiving structural engineer combines these with whatever else acts
on that support (steelwork self-weight, other equipment, wind on the
structure itself) before applying EN 1990/BS EN 1991 partial factors
themselves, the same way `calcs/structural/beam_capacity.py`/
`column_capacity.py` take separate permanent/variable loads rather than a
single pre-factored figure.

`occasional_horizontal_kn` per support is treated as a single, ALREADY-
COMBINED resultant occasional load (thermal friction/anchor force, wind,
seismic -- whichever combination governs per the project's load
combination philosophy) -- this module does NOT decompose or combine
separate occasional load cases; that combination judgement is the piping
engineer's, supplied here as one number per support.

Method summary
--------------
For each support point (sustained vertical load, occasional horizontal
load):

    total_sustained_vertical = sum(sustained_vertical_i)
    governing support (vertical) = support with max(sustained_vertical_i)
    governing support (horizontal) = support with max(occasional_horizontal_i)

If a maximum allowable vertical reaction is supplied (a single, uniform
screening limit, NOT a per-support capacity lookup -- see Known
simplifications), the governing vertical reaction is checked against it.

Known simplifications / not implemented (see Warnings in the result):
- Support reactions are required direct inputs from an external
  flexibility analysis -- not derived here, see above.
- occasional_horizontal_kn is a single already-combined resultant value
  per support, not decomposed by load case.
- max_allowable_vertical_reaction_kn, if supplied, is ONE uniform limit
  applied to every support -- if different supports have different actual
  structural capacities (common once steelwork sizes vary), check the
  governing support reported here against that specific support's actual
  capacity directly, rather than relying on this screening check alone.
- Only the vertical reaction is checked against a limit -- horizontal is
  reported for information/for the structural discipline's own combined
  check, not screened here.
- Loads are unfactored (as handed over in real practice) -- see above.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class Support(BaseModel):
    support_id: str
    sustained_vertical_kn: float = Field(..., gt=0)
    occasional_horizontal_kn: float = Field(..., ge=0)


def _parse_supports(text: str) -> tuple[list[Support], list[str]]:
    """Lenient 'support_id, sustained_vertical_kn, occasional_horizontal_kn' per-line parser -- see module docstring."""
    supports: list[Support] = []
    unparsed: list[str] = []
    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            unparsed.append(raw_line)
            continue
        try:
            support_id = parts[0]
            sustained_vertical = float(parts[1])
            occasional_horizontal = float(parts[2])
            if not support_id or sustained_vertical <= 0 or occasional_horizontal < 0:
                unparsed.append(raw_line)
                continue
            supports.append(Support(support_id=support_id, sustained_vertical_kn=sustained_vertical, occasional_horizontal_kn=occasional_horizontal))
        except ValueError:
            unparsed.append(raw_line)
    return supports, unparsed


class SupportLoadScheduleInput(BaseModel):
    supports_text: str = Field(
        ...,
        description="One support per line: 'support_id, sustained_vertical_kn, occasional_horizontal_kn'. "
        "e.g. 'S1, 12.5, 3.2' -- lenient paste parser, unparseable lines are reported as warnings, not dropped silently.",
    )
    max_allowable_vertical_reaction_kn: Optional[float] = Field(
        None, gt=0,
        description="Optional uniform screening limit (kN) applied to the governing vertical reaction across all supports. "
        "Not a per-support capacity lookup -- see module docstring.",
    )

    @field_validator("supports_text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("supports_text must not be blank.")
        return v


def calculate(inputs: SupportLoadScheduleInput) -> CalcResult:
    warnings: list[str] = [
        "Support reactions are required direct inputs from an external flexibility analysis (e.g. CAESAR II) "
        "-- not derived by this module. See module docstring.",
        "occasional_horizontal_kn per support is a single already-combined resultant value, not decomposed by "
        "load case (thermal friction/anchor, wind, seismic).",
        "Loads are handed over unfactored -- the structural discipline combines these with its own loads and "
        "applies partial factors, same as calcs/structural/beam_capacity.py/column_capacity.py.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    supports, unparsed = _parse_supports(inputs.supports_text)
    for u in unparsed:
        warnings.append(f"Could not parse support line: '{u}' -- expected 'support_id, sustained_vertical_kn, occasional_horizontal_kn'.")

    if not supports:
        warnings.append("No valid supports parsed -- cannot build a load schedule.")
        return CalcResult(
            headline=Term("Governing vertical reaction", 0.0, unit="kN", note="No valid supports parsed"),
            warnings=warnings,
            risk_flags=risk_flags,
            method="Pipe support load schedule aggregation",
        )

    total_vertical = sum(s.sustained_vertical_kn for s in supports)
    governing_vertical = max(supports, key=lambda s: s.sustained_vertical_kn)
    governing_horizontal = max(supports, key=lambda s: s.occasional_horizontal_kn)

    terms: list[Term] = [
        Term("Number of supports", float(len(supports))),
        Term("Total sustained vertical load", total_vertical, unit="kN", note="sum across all supports"),
        Term("Governing vertical reaction", governing_vertical.sustained_vertical_kn, unit="kN", note=f"support {governing_vertical.support_id}"),
        Term("Governing horizontal reaction", governing_horizontal.occasional_horizontal_kn, unit="kN", note=f"support {governing_horizontal.support_id}"),
    ]

    if inputs.max_allowable_vertical_reaction_kn is not None:
        utilisation = governing_vertical.sustained_vertical_kn / inputs.max_allowable_vertical_reaction_kn
        terms.append(Term(
            "Utilisation", utilisation,
            note=f"governing/allowable -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
        ))
        if utilisation > 1.0:
            warnings.append(
                f"FAILS: governing vertical reaction ({governing_vertical.sustained_vertical_kn:.2f} kN, "
                f"support {governing_vertical.support_id}) exceeds the allowable ({inputs.max_allowable_vertical_reaction_kn:.2f} kN)."
            )
            risk_flags.append(DesignRiskFlag(
                category="code_compliance", severity="critical",
                description=f"Governing vertical reaction ({governing_vertical.sustained_vertical_kn:.2f} kN at support {governing_vertical.support_id}) exceeds the allowable ({inputs.max_allowable_vertical_reaction_kn:.2f} kN).",
                trigger=f"reaction={governing_vertical.sustained_vertical_kn:.2f}kN > allowable={inputs.max_allowable_vertical_reaction_kn:.2f}kN at support {governing_vertical.support_id}",
                recommended_action="Add an intermediate support, reroute to redistribute load, or confirm the actual structural capacity at this specific support with the structural discipline.",
                source_reference="mechanical_piping_support_load_schedule",
            ))
        headline = Term(
            "Utilisation", utilisation,
            note=("PASS" if utilisation <= 1.0 else "FAIL") + f" -- governing reaction ({governing_vertical.support_id})/allowable",
        )
    else:
        headline = Term(
            "Governing vertical reaction", governing_vertical.sustained_vertical_kn, unit="kN",
            note=f"support {governing_vertical.support_id} -- no allowable limit supplied, reporting governing reaction only",
        )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Per-support reaction load aggregation, optional screening against a uniform allowable vertical reaction",
        references=[
            "ASME B31.3, Process Piping.",
            "MSS SP-58, Pipe hangers and supports.",
        ],
    )


MODULE = CalcModule(
    key="mechanical_piping_support_load_schedule",
    name="Pipe Support Load Schedule",
    discipline="Mechanical Piping",
    description=(
        "Aggregates per-support reaction loads (sustained vertical, occasional horizontal) into a schedule "
        "for handover to structural, with an optional screening check against a uniform allowable vertical "
        "reaction. Support reactions are required direct inputs -- see module docstring."
    ),
    input_model=SupportLoadScheduleInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.mechanical_piping.support_load_schedule
    example = SupportLoadScheduleInput(
        supports_text=(
            "S1, 12.5, 3.2\n"
            "S2, 18.0, 5.5\n"
            "S3, 9.8, 2.1\n"
        ),
        max_allowable_vertical_reaction_kn=20.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
