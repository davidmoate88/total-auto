"""
PED/PESR pressure equipment classification and conformity assessment
check — Pressure Equipment Directive 2014/68/EU (EU) and the Pressure
Equipment (Safety) Regulations 2016 (UK, the post-Brexit implementation of
the same technical content, differing mainly in CE vs UKCA marking).
Answers `design_standards_and_criteria`'s "Piping class/category"
`DesignCriterion` ("PED Article 13 category / ASME B31.3 fluid service
category") in `basis_of_design/mechanical_piping.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module deliberately does NOT derive the PED/PESR category (SEP, I,
II, or III) from pressure/diameter/fluid group. PED Annex II sets the
category via four SEPARATE graphical boundary charts for piping (Tables
6-9: Group 1 gas, Group 2 gas, Group 1 liquid, Group 2 liquid), each with
its own specific PS-vs-DN boundary lines -- exactly the kind of
easy-to-transpose-between-tables numeric detail this repo's "flag, don't
guess" discipline exists to avoid (see `cable_sizing_voltage_drop.py`'s BS
7671 tables, or IEEE 1584's incident energy model). Getting this wrong
carries real regulatory weight -- an incorrect category could mean skipping
required notified body conformity assessment before a system is placed
into service, a genuine legal compliance failure, not just a design error
a reviewer catches. `ped_category` is therefore a REQUIRED direct input,
determined externally by checking the applicable Annex II table for the
line's fluid group, PS, and DN.

What this module DOES compute directly, with high confidence: the PED
Article 2(1) scope threshold itself. Equipment with a maximum allowable
pressure PS not exceeding 0.5 bar is excluded from PED/PESR entirely --
this is the single most consistently and universally cited figure in the
Directive (the literal definition of "pressure equipment" it applies to),
unlike the category boundary charts. Below this, the Directive's
conformity assessment/CE-UKCA marking requirements simply do not apply
(sound engineering practice still applies as a general safety duty).

Method summary
--------------
    in_scope = PS > 0.5 bar

If in scope, the externally-supplied `ped_category` drives simple,
well-defined downstream bookkeeping: SEP (Article 4.3, sound engineering
practice) does not require notified body conformity assessment or CE/UKCA
marking; Categories I, II, and III do (with increasing conformity
assessment rigour, not evaluated here -- see the specific module/route
requirement in PED Annex III / PESR Schedule 5, a further "read the
Directive" step this module does not attempt to reproduce either).

Known simplifications / not implemented (see Warnings in the result):
- Does NOT derive the PED/PESR category itself -- `ped_category` is a
  required direct input, see above.
- Does NOT determine the specific conformity assessment module/route
  (Annex III) applicable within a category -- flags only that one applies.
- Does NOT determine UK Pressure Systems Safety Regulations 2000 written
  scheme of examination applicability -- a related but separate UK
  in-service inspection requirement with its own scope rules; confirm with
  a competent person.
- Treats PED and PESR as equivalent for classification purposes (PESR is
  modelled closely on PED's technical content) -- confirm which actually
  governs per this discipline's own "Governing piping code" criterion, and
  whether CE or UKCA marking applies.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

PED_SCOPE_THRESHOLD_BAR = 0.5  # PED Article 2(1) / PESR reg 3 -- equipment at or below this PS is outside scope


class PedPesrClassificationCheckInput(BaseModel):
    max_allowable_pressure_bar_g: float = Field(..., gt=0, description="Maximum allowable pressure, PS (bar gauge).")
    nominal_diameter_dn: float = Field(..., gt=0, description="Nominal diameter, DN (mm) -- for record-keeping alongside the category; not used to derive it.")
    fluid_group: Literal[1, 2] = Field(..., description="CLP Regulation fluid hazard group -- Group 1 (dangerous: explosive/flammable/toxic/oxidising) or Group 2 (all other fluids, including steam and most utilities). A hazard classification judgement, not derived by this module.")
    ped_category: Literal["SEP", "I", "II", "III"] = Field(
        ...,
        description="PED/PESR category for this line, already determined externally from PED Annex II Tables 6-9 for the stated fluid group/PS/DN. NOT derived by this module -- see module docstring for why.",
    )


def calculate(inputs: PedPesrClassificationCheckInput) -> CalcResult:
    warnings: list[str] = [
        "ped_category is a required direct input, determined externally from PED Annex II Tables 6-9 -- this "
        "module does NOT derive it from pressure/diameter/fluid group. See module docstring.",
        "Does not determine the specific conformity assessment module/route (Annex III) within a category.",
        "Does not determine UK PSSR 2000 written scheme of examination applicability -- a separate, related "
        "UK in-service inspection requirement.",
        "Treats PED and PESR as equivalent for classification purposes -- confirm which actually governs and "
        "whether CE or UKCA marking applies.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    PS = inputs.max_allowable_pressure_bar_g
    in_scope = PS > PED_SCOPE_THRESHOLD_BAR

    terms: list[Term] = [
        Term("PED/PESR scope threshold", PED_SCOPE_THRESHOLD_BAR, unit="bar g", note="Article 2(1) -- PS not exceeding this is outside scope"),
        Term("In scope", 1.0 if in_scope else 0.0, note="PS > 0.5 bar" if in_scope else "PS <= 0.5 bar -- outside PED/PESR scope"),
    ]

    if not in_scope:
        headline = Term(
            "In scope", 0.0,
            note=f"OUTSIDE PED/PESR scope (PS={PS:.2f} bar g <= {PED_SCOPE_THRESHOLD_BAR} bar) -- no conformity assessment/CE-UKCA marking required; sound engineering practice still applies",
        )
        return CalcResult(
            headline=headline,
            terms=terms,
            warnings=warnings,
            risk_flags=risk_flags,
            method="PED Article 2(1)/PESR scope threshold check",
            references=[
                "Directive 2014/68/EU (Pressure Equipment Directive), Article 2(1).",
                "Pressure Equipment (Safety) Regulations 2016 (UK).",
            ],
        )

    requires_notified_body = inputs.ped_category != "SEP"
    terms.append(Term("Requires notified body conformity assessment", 1.0 if requires_notified_body else 0.0, note=f"Category {inputs.ped_category}"))

    if requires_notified_body:
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="high",
            description=f"Category {inputs.ped_category} pressure piping requires notified/approved body conformity assessment and CE/UKCA marking before being placed into service.",
            trigger=f"ped_category={inputs.ped_category} (not SEP), PS={PS:.2f} bar g in scope",
            recommended_action="Engage a notified (EU)/approved (UK) body early -- this affects programme, not just documentation, and confirm the specific Annex III conformity assessment module/route for this category.",
            source_reference="mechanical_piping_ped_pesr_classification_check",
        ))
    else:
        warnings.append(
            "Category SEP (Article 4.3): no notified body conformity assessment or CE/UKCA marking required, "
            "but the equipment must still be designed and manufactured in accordance with sound engineering "
            "practice, and the manufacturer must provide adequate instructions for use."
        )

    if inputs.fluid_group == 1:
        warnings.append(
            "Group 1 (dangerous fluid) service -- PED Annex II sets materially lower category boundaries for "
            "Group 1 than Group 2 at the same PS x DN; confirm the category was determined from the correct "
            "Group 1 table (6 for gas, 8 for liquid), not a Group 2 table."
        )

    headline = Term(
        "In scope", 1.0,
        note=f"IN SCOPE, Category {inputs.ped_category} -- " + ("notified body conformity assessment required" if requires_notified_body else "SEP, no notified body required"),
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="PED Article 2(1)/PESR scope threshold check, plus downstream conformity assessment bookkeeping from an externally-determined category",
        references=[
            "Directive 2014/68/EU (Pressure Equipment Directive), Articles 2(1), 4.3, 13, Annex II/III.",
            "Pressure Equipment (Safety) Regulations 2016 (UK).",
        ],
    )


MODULE = CalcModule(
    key="mechanical_piping_ped_pesr_classification_check",
    name="PED/PESR Pressure Equipment Classification Check",
    discipline="Mechanical Piping",
    description=(
        "PED Article 2(1)/PESR scope threshold (PS > 0.5 bar) computed directly, plus conformity assessment "
        "bookkeeping from an externally-determined PED/PESR category. Does NOT derive the category itself -- "
        "see module docstring."
    ),
    input_model=PedPesrClassificationCheckInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.mechanical_piping.ped_pesr_classification_check
    example = PedPesrClassificationCheckInput(
        max_allowable_pressure_bar_g=16.0,
        nominal_diameter_dn=100.0,
        fluid_group=2,
        ped_category="II",
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
