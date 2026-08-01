"""
LV load schedule and diversity — aggregated maximum demand across a list of
LV loads, accounting for diversity (not every load runs at full rated power
simultaneously). Answers `lv_distribution_and_reticulation`'s "Load
schedule / diversity" `CalculationRequirement` in
`basis_of_design/electrical_lv.py`. Its output (maximum demand current) is
the natural `design_current_a` (Ib) input to
`calcs/electrical_lv/cable_sizing_voltage_drop.py` for the main incoming/
distribution cable.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
Diversity factors are NOT embedded here. BS 7671/the IEE On-Site Guide give
worked diversity allowances for standard DOMESTIC circuit types (lighting,
socket outlets, cooking, etc. -- e.g. IEE On-Site Guide Table H1), but this
BoD is scoped to plant/industrial LV distribution (see
`basis_of_design/electrical_lv.py`'s module docstring), where diversity
instead depends on the specific operational duty of each load (duty vs.
standby plant, intermittent vs. continuous process equipment, etc.) -- there
is no single fixed table that applies. Each load's `diversity_factor_percent`
is therefore a REQUIRED direct input per load (default 100%, i.e. no
diversity assumed, the conservative starting point) -- confirm against the
actual process operating philosophy / client standard before reducing it.

Method summary
--------------
For each load i (rated power Pi, power factor cos(phi)_i, diversity factor
d_i as a fraction):

    P_diversified_i = Pi * d_i
    Q_diversified_i = P_diversified_i * tan(acos(cos(phi)_i))

Loads combine as real/reactive power (NOT by summing individual load
currents directly -- currents at different power factors are not in phase,
so simple current summation overstates or understates the true resultant):

    P_total = sum(P_diversified_i)              (kW)
    Q_total = sum(Q_diversified_i)               (kVAr)
    S_total = sqrt(P_total^2 + Q_total^2)        (kVA)
    overall_power_factor = P_total / S_total

    connected_load_kw = sum(Pi)                  (undiversified sum, for reference)
    overall_diversity_factor = P_total / connected_load_kw

Maximum demand current, from the aggregated apparent power:

    three-phase:  I = S_total * 1000 / (sqrt(3) * V)
    single-phase: I = S_total * 1000 / V

Load data is supplied as lenient pasted text (one load per line), the same
"structured paste, not free-form NLP" pattern as
`calcs/civil/cut_fill_balance.py` / `calcs/civil/slope_stability.py`.

Known simplifications / not implemented (see Warnings in the result):
- Diversity factors are direct inputs, not derived -- see above.
- Aggregates ALL supplied loads into ONE maximum demand figure (e.g. for a
  main incoming switchboard) -- does not build a hierarchical
  board-by-board/circuit-by-circuit load schedule.
- Motor starting current (inrush) is not considered -- this is a running
  (steady-state) load aggregation only; see the separate motor
  control/switchgear starting-method criteria in the BoD.
- Does not itself select a protective device or cable -- feed the resulting
  maximum demand current into `cable_sizing_voltage_drop.py` as `Ib`.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class Load(BaseModel):
    name: str
    rated_power_kw: float = Field(..., gt=0)
    power_factor: float = Field(..., gt=0, le=1.0)
    diversity_factor_percent: float = Field(100.0, ge=0, le=100.0)


def _parse_loads(text: str) -> tuple[list[Load], list[str]]:
    """Lenient 'name, rated_power_kw, power_factor[, diversity_factor_percent]' per-line parser -- see module docstring."""
    loads: list[Load] = []
    unparsed: list[str] = []
    for raw_line in text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) not in (3, 4):
            unparsed.append(raw_line)
            continue
        try:
            name = parts[0]
            rated_power_kw = float(parts[1])
            power_factor = float(parts[2])
            diversity_factor_percent = float(parts[3]) if len(parts) == 4 else 100.0
            if not name or rated_power_kw <= 0 or not (0 < power_factor <= 1.0) or not (0 <= diversity_factor_percent <= 100.0):
                unparsed.append(raw_line)
                continue
            loads.append(Load(name=name, rated_power_kw=rated_power_kw, power_factor=power_factor, diversity_factor_percent=diversity_factor_percent))
        except ValueError:
            unparsed.append(raw_line)
    return loads, unparsed


class LoadScheduleInput(BaseModel):
    loads_text: str = Field(
        ...,
        description="One load per line: 'name, rated_power_kw, power_factor[, diversity_factor_percent]'. "
        "e.g. 'Duty pump, 15, 0.85, 100' -- diversity_factor_percent defaults to 100 (no diversity) if omitted. "
        "Lenient paste parser, unparseable lines are reported as warnings, not dropped silently.",
    )
    system_voltage_v: float = Field(400.0, gt=0, description="System voltage (V) -- line-to-line for three-phase, or line-to-neutral for single-phase.")
    number_of_phases: Literal[1, 3] = Field(3, description="Number of phases the aggregated maximum demand is drawn across.")

    @field_validator("loads_text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("loads_text must not be blank.")
        return v


def calculate(inputs: LoadScheduleInput) -> CalcResult:
    warnings: list[str] = [
        "diversity_factor_percent per load is a direct input, not derived from any single fixed table -- "
        "this BoD is scoped to plant/industrial LV distribution, where diversity depends on the specific "
        "operational duty of each load. Default (100%, no diversity) is the conservative starting point.",
        "Aggregates all supplied loads into one maximum demand figure -- does not build a hierarchical "
        "board-by-board load schedule.",
        "Motor starting (inrush) current is not considered -- this is a steady-state running load aggregation only.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    loads, unparsed = _parse_loads(inputs.loads_text)
    for u in unparsed:
        warnings.append(f"Could not parse load line: '{u}' -- expected 'name, rated_power_kw, power_factor[, diversity_factor_percent]'.")

    if not loads:
        warnings.append("No valid loads parsed -- cannot compute a load schedule.")
        return CalcResult(
            headline=Term("Maximum demand current", 0.0, unit="A", note="No valid loads parsed"),
            warnings=warnings,
            risk_flags=risk_flags,
            method="LV load schedule and diversity aggregation",
        )

    terms: list[Term] = []
    connected_load_kw = sum(load.rated_power_kw for load in loads)
    P_total_kw = 0.0
    Q_total_kvar = 0.0
    for load in loads:
        d = load.diversity_factor_percent / 100.0
        p_diversified = load.rated_power_kw * d
        q_diversified = p_diversified * math.tan(math.acos(load.power_factor))
        P_total_kw += p_diversified
        Q_total_kvar += q_diversified
        terms.append(Term(
            f"{load.name}: diversified demand", p_diversified, unit="kW",
            note=f"{load.rated_power_kw:.2f}kW * {load.diversity_factor_percent:.0f}%",
        ))

    S_total_kva = math.hypot(P_total_kw, Q_total_kvar)
    overall_power_factor = P_total_kw / S_total_kva if S_total_kva > 0 else 0.0
    overall_diversity_factor = P_total_kw / connected_load_kw if connected_load_kw > 0 else 0.0

    terms.append(Term("Connected load (undiversified)", connected_load_kw, unit="kW", note="sum of rated_power_kw"))
    terms.append(Term("P total (diversified demand, real power)", P_total_kw, unit="kW"))
    terms.append(Term("Q total (diversified demand, reactive power)", Q_total_kvar, unit="kVAr"))
    terms.append(Term("S total (diversified demand, apparent power)", S_total_kva, unit="kVA", note="sqrt(P^2+Q^2)"))
    terms.append(Term("Overall power factor", overall_power_factor, note="P total/S total"))
    terms.append(Term("Overall diversity factor", overall_diversity_factor, note="P total/connected load"))

    if inputs.number_of_phases == 3:
        max_demand_current_a = S_total_kva * 1000.0 / (math.sqrt(3) * inputs.system_voltage_v)
        current_note = "S total*1000/(sqrt(3)*V), three-phase"
    else:
        max_demand_current_a = S_total_kva * 1000.0 / inputs.system_voltage_v
        current_note = "S total*1000/V, single-phase"

    if overall_diversity_factor >= 0.999:
        warnings.append(
            "No diversity applied across any load (overall diversity factor ~100%) -- the maximum demand "
            "figure equals the full connected load and is likely conservative (oversized) for a real "
            "operating philosophy. Confirm and apply per-load diversity where genuinely justified."
        )

    headline = Term(
        "Maximum demand current", max_demand_current_a, unit="A",
        note=current_note + f" -- feed into cable_sizing_voltage_drop.py's design_current_a (Ib)",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Real/reactive power (P/Q) aggregation of diversified LV loads, converted to maximum demand current",
        references=[
            "BS 7671, Requirements for Electrical Installations (IET Wiring Regulations) -- Chapter 31 (design current).",
            "IEE On-Site Guide -- diversity concept (Table H1 gives domestic worked allowances; this module "
            "requires diversity per load directly since it is scoped to plant/industrial distribution).",
        ],
    )


MODULE = CalcModule(
    key="electrical_lv_load_schedule_diversity",
    name="LV Load Schedule and Diversity (Maximum Demand)",
    discipline="Electrical (LV)",
    description=(
        "Aggregates a list of LV loads (with per-load power factor and diversity factor) into a maximum "
        "demand current via real/reactive power summation. Diversity factors are required direct inputs, "
        "not read from a fixed table -- see module docstring."
    ),
    input_model=LoadScheduleInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_lv.load_schedule_diversity
    example = LoadScheduleInput(
        loads_text=(
            "Duty pump, 15, 0.85, 100\n"
            "Standby pump, 15, 0.85, 0\n"
            "Lighting, 5, 0.95, 66\n"
            "Small power, 8, 0.8, 50\n"
        ),
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
