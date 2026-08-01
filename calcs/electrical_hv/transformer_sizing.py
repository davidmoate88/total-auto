"""
HV/LV transformer sizing check — full-load current on both windings, and
utilisation of a candidate transformer rating against LV demand plus a
growth margin. Answers `transformers`'s "Transformer rating" `DesignCriterion`
("to be confirmed from the LV load schedule plus diversity") in
`basis_of_design/electrical_hv.py` -- the first `calcs/electrical_hv/`
module, and the first calc-to-calc handoff ACROSS disciplines in this repo
(LV demand -> HV transformer sizing), distinct from the earlier
`load_schedule_diversity.py` -> `cable_sizing_voltage_drop.py` handoff
which stays within `calcs/electrical_lv/`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module does NOT select a "standard preferred" transformer kVA rating
from a manufacturer's range -- `rated_transformer_kva` is the candidate
rating the engineer has already chosen (or is evaluating), supplied as a
direct input; the module only checks whether that candidate covers the LV
demand plus a growth margin. The growth margin itself
(`growth_margin_percent`) is a project/utility-specific allowance for future
load growth, not a fixed standard value, so it is a direct input with an
illustrative default -- confirm against the project's actual growth
projections, same reasoning as `foul_drainage.py`'s `peak_flow_factor`.

Method summary
--------------
Required capacity, LV demand plus growth margin:

    required_kva = lv_demand_kva * (1 + growth_margin_percent/100)
    utilisation  = required_kva / rated_transformer_kva

Full-load current on each winding (three-phase, S in kVA, V in kV):

    I = S / (sqrt(3) * V)                    (A)

computed for both the HV primary and LV secondary windings at the candidate
transformer's rated kVA.

Known simplifications / not implemented (see Warnings in the result):
- Does not select a standard preferred transformer size -- checks a
  candidate rating only, see above.
- Assumes ONE transformer serving the full LV demand -- does not size for
  N-1 redundancy (where two parallel transformers must each independently
  carry the full load on loss of the other), which needs a different
  target utilisation (typically <=50% of a single unit's rating in a
  duty/standby-equivalent parallel pair).
- Does not apply thermal/ambient loading derating (IEC 60076-7 loading
  guide) -- the nameplate rating is used directly.
- Does not check inrush current or protection/grading implications --
  see the separate "Protection discrimination/grading study"
  `CalculationRequirement` in `protection_and_control`.
- Vector group and cooling class (this section's other criteria) are not
  addressed by this module.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class TransformerSizingInput(BaseModel):
    lv_demand_kva: float = Field(..., gt=0, description="LV maximum demand, apparent power (kVA) -- e.g. from calcs/electrical_lv/load_schedule_diversity.py's 'S total' output.")
    growth_margin_percent: float = Field(20.0, ge=0, description="Allowance for future load growth on top of current demand (%) -- illustrative default, confirm against the project's actual growth projections.")
    rated_transformer_kva: float = Field(..., gt=0, description="Candidate transformer nameplate rating (kVA) being checked -- not derived by this module, see module docstring.")
    hv_voltage_kv: float = Field(..., gt=0, description="HV (primary) voltage, line-to-line (kV).")
    lv_voltage_kv: float = Field(0.400, gt=0, description="LV (secondary) voltage, line-to-line (kV) -- default 0.400 (400V), matching basis_of_design/electrical_lv.py's standard LV system voltage.")


def calculate(inputs: TransformerSizingInput) -> CalcResult:
    warnings: list[str] = [
        "rated_transformer_kva is a candidate rating supplied directly -- this module does not select a "
        "standard preferred transformer size from a manufacturer's range.",
        "growth_margin_percent is a project/utility-specific illustrative default, not a fixed standard value "
        "-- confirm against the project's actual growth projections.",
        "Assumes ONE transformer serving the full LV demand -- does not size for N-1 parallel-transformer "
        "redundancy, which needs a different (lower) target utilisation per unit.",
        "Does not apply thermal/ambient loading derating (IEC 60076-7) -- nameplate rating used directly.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    required_kva = inputs.lv_demand_kva * (1 + inputs.growth_margin_percent / 100.0)
    utilisation = required_kva / inputs.rated_transformer_kva

    terms: list[Term] = [
        Term("Required capacity (demand + growth margin)", required_kva, unit="kVA", note="lv_demand_kva*(1+growth_margin_percent/100)"),
        Term("Utilisation", utilisation, note=f"required/rated -- {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)"),
    ]

    I_hv = inputs.rated_transformer_kva / (math.sqrt(3) * inputs.hv_voltage_kv)
    I_lv = inputs.rated_transformer_kva / (math.sqrt(3) * inputs.lv_voltage_kv)
    terms.append(Term("HV full-load current", I_hv, unit="A", note=f"rated_kVA/(sqrt(3)*{inputs.hv_voltage_kv}kV)"))
    terms.append(Term("LV full-load current", I_lv, unit="A", note=f"rated_kVA/(sqrt(3)*{inputs.lv_voltage_kv}kV)"))

    if utilisation > 1.0:
        warnings.append(f"FAILS: required capacity ({required_kva:.1f} kVA) exceeds the candidate transformer rating ({inputs.rated_transformer_kva:.1f} kVA).")
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Candidate transformer rating ({inputs.rated_transformer_kva:.1f} kVA) is undersized for LV demand plus growth margin ({required_kva:.1f} kVA).",
            trigger=f"required={required_kva:.1f}kVA > rated={inputs.rated_transformer_kva:.1f}kVA",
            recommended_action="Select a larger standard transformer rating, or revisit the growth margin/LV demand assumptions.",
            source_reference="electrical_hv_transformer_sizing",
        ))

    headline = Term(
        "Utilisation", utilisation,
        note=("PASS" if utilisation <= 1.0 else "FAIL") + " -- required capacity (demand+growth margin)/candidate transformer rating",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="LV demand plus growth margin, checked against a candidate transformer rating; full-load current on both windings via the three-phase power triangle",
        references=[
            "BS EN 60076 series, Power transformers.",
        ],
    )


MODULE = CalcModule(
    key="electrical_hv_transformer_sizing",
    name="HV/LV Transformer Sizing Check (Demand + Growth Margin)",
    discipline="Electrical (HV)",
    description=(
        "Checks a candidate transformer rating against LV demand plus a growth margin, and computes HV/LV "
        "full-load currents. Does not select a standard preferred size -- checks a candidate rating supplied "
        "directly, see module docstring."
    ),
    input_model=TransformerSizingInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_hv.transformer_sizing
    example = TransformerSizingInput(
        lv_demand_kva=26.0,
        rated_transformer_kva=100.0,
        hv_voltage_kv=11.0,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
