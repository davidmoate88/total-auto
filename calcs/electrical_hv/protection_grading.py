"""
Protection discrimination/grading check — IDMT (Inverse Definite Minimum
Time) overcurrent relay operating times, IEC 60255-151, checked for
adequate grading margin between an upstream and downstream relay pair.
Answers `protection_and_control`'s "Protection discrimination/grading
study" `CalculationRequirement` in `basis_of_design/electrical_hv.py`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
The IDMT operating-time formula and its standard curve constants (k, alpha)
are reproduced here with the same confidence as `column_capacity.py`'s
Table 6.1 imperfection factors -- these are among the most consistently
published constants in power systems protection literature (IEC 60255-151,
formerly IEC 60255-3, formerly BS 142), effectively unchanged across
decades and manufacturers, unlike e.g. BS 7671's cable tables (installation-
method-specific, revised between amendments) or IEEE 1584's incident energy
model (equipment-class-specific empirical regression). They are still
"verify before real use" like every constant in this repo, but embedded
directly rather than made a required input. What genuinely IS project-
specific, and therefore required direct inputs, are: each relay's pickup
current and time multiplier setting (TMS) -- design choices, not universal
constants -- and the prospective fault current, which `design_standards_and_criteria`'s
own criterion already states must come from the DNO/network fault level
study, not be calculated independently here.

Method summary
--------------
IEC 60255-151 IDMT operating time, for a relay with curve constants (k,
alpha), pickup current Is, time multiplier setting TMS, seeing fault
current I:

    t = TMS * k / ((I/Is)^alpha - 1)                (I > Is required)

Standard curve constants:

    Standard Inverse (SI):        k=0.14,  alpha=0.02
    Very Inverse (VI):             k=13.5,  alpha=1.0
    Extremely Inverse (EI):        k=80.0,  alpha=2.0
    Long Time Inverse (LTI):       k=120.0, alpha=1.0

Grading margin, at the stated fault current, between an upstream relay
(should operate LATER, backing up the downstream device) and a downstream
relay (should operate FIRST, clearing the fault before the upstream device
sees a need to trip):

    margin = t_upstream - t_downstream

checked against a required grading margin (BS EN 60255 / project protection
philosophy typically 0.2-0.4s, matching this discipline's own "Protection
grading margin" `DesignCriterion` -- a project-specific figure, so a
required direct input here, no embedded default).

Known simplifications / not implemented (see Warnings in the result):
- ONE upstream/downstream relay pair, at ONE stated fault current -- not a
  full multi-stage network study across the full fault current range (the
  margin between two different curve shapes/TMS combinations can vary with
  fault current, so the critical grading point may not be the one checked
  here; a full study checks the margin across the relevant current range).
- Fault current is a required direct input from a separate fault level
  study -- not calculated by this module, per this discipline's own
  "System fault level" criterion.
- IDMT relay operating time only -- does not add breaker interrupting time,
  CT ratio errors, or relay/breaker overshoot margins that a full grading
  study also accounts for.
- Definite-time and instantaneous protection elements are not covered --
  IDMT curves only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

CurveType = Literal["standard_inverse", "very_inverse", "extremely_inverse", "long_time_inverse"]

IDMT_CURVE_CONSTANTS: dict[str, tuple[float, float]] = {
    "standard_inverse": (0.14, 0.02),
    "very_inverse": (13.5, 1.0),
    "extremely_inverse": (80.0, 2.0),
    "long_time_inverse": (120.0, 1.0),
}


def _idmt_operating_time_s(curve_type: str, pickup_current_a: float, tms: float, fault_current_a: float) -> float:
    k, alpha = IDMT_CURVE_CONSTANTS[curve_type]
    ratio = fault_current_a / pickup_current_a
    return tms * k / (ratio**alpha - 1)


class ProtectionGradingInput(BaseModel):
    fault_current_a: float = Field(..., gt=0, description="Prospective fault current at the grading point (A) -- from a DNO/network fault level study, not calculated here.")

    downstream_curve_type: CurveType = Field("standard_inverse", description="Downstream relay's IDMT curve type (IEC 60255-151).")
    downstream_pickup_current_a: float = Field(..., gt=0, description="Downstream relay pickup/plug setting current, Is (A). Must be less than fault_current_a.")
    downstream_tms: float = Field(..., gt=0, description="Downstream relay time multiplier setting (TMS).")

    upstream_curve_type: CurveType = Field("standard_inverse", description="Upstream relay's IDMT curve type (IEC 60255-151).")
    upstream_pickup_current_a: float = Field(..., gt=0, description="Upstream relay pickup/plug setting current, Is (A). Must be less than fault_current_a.")
    upstream_tms: float = Field(..., gt=0, description="Upstream relay time multiplier setting (TMS).")

    required_grading_margin_s: float = Field(0.3, gt=0, description="Minimum required grading margin (s) between upstream and downstream operating times -- project-specific, matches this discipline's 'Protection grading margin' criterion (typically 0.2-0.4s).")


def calculate(inputs: ProtectionGradingInput) -> CalcResult:
    warnings: list[str] = [
        "Single upstream/downstream relay pair at a single stated fault current -- not a full multi-stage "
        "network study across the relevant fault current range. See module docstring.",
        "fault_current_a is a required direct input from a separate DNO/network fault level study, not "
        "calculated by this module.",
        "IDMT relay operating time only -- does not add breaker interrupting time, CT ratio errors, or "
        "relay/breaker overshoot margins.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    if inputs.fault_current_a <= inputs.downstream_pickup_current_a or inputs.fault_current_a <= inputs.upstream_pickup_current_a:
        warnings.append(
            "fault_current_a must exceed both relays' pickup current for either relay to operate -- check "
            "your inputs; no operating time can be computed."
        )
        return CalcResult(
            headline=Term("Grading margin", 0.0, unit="s", note="Cannot compute -- fault current below a relay's pickup current"),
            warnings=warnings,
            risk_flags=risk_flags,
            method="IEC 60255-151 IDMT operating time and grading margin check",
        )

    t_downstream = _idmt_operating_time_s(inputs.downstream_curve_type, inputs.downstream_pickup_current_a, inputs.downstream_tms, inputs.fault_current_a)
    t_upstream = _idmt_operating_time_s(inputs.upstream_curve_type, inputs.upstream_pickup_current_a, inputs.upstream_tms, inputs.fault_current_a)
    margin = t_upstream - t_downstream

    terms: list[Term] = [
        Term("Downstream operating time", t_downstream, unit="s", note=f"{inputs.downstream_curve_type} curve"),
        Term("Upstream operating time", t_upstream, unit="s", note=f"{inputs.upstream_curve_type} curve"),
        Term("Grading margin", margin, unit="s", note=f"{'PASS' if margin >= inputs.required_grading_margin_s else 'FAIL'} (>= {inputs.required_grading_margin_s}s required)"),
    ]

    if margin < inputs.required_grading_margin_s:
        warnings.append(
            f"FAILS: grading margin ({margin:.3f}s) is below the required margin ({inputs.required_grading_margin_s}s) "
            f"at {inputs.fault_current_a:.0f}A -- risk of loss of discrimination (the upstream device could trip "
            "before or alongside the downstream device, unnecessarily de-energising a wider part of the network)."
        )
        risk_flags.append(DesignRiskFlag(
            category="code_compliance", severity="critical",
            description=f"Grading margin ({margin:.3f}s) at {inputs.fault_current_a:.0f}A is below the required margin ({inputs.required_grading_margin_s}s) -- loss of discrimination risk.",
            trigger=f"margin={margin:.3f}s < required={inputs.required_grading_margin_s}s at I={inputs.fault_current_a:.0f}A",
            recommended_action="Increase the upstream relay's TMS, adjust pickup settings, or select a different curve shape for one of the relays; re-check across the full relevant fault current range, not just this one point.",
            source_reference="electrical_hv_protection_grading",
        ))

    headline = Term(
        "Grading margin", margin, unit="s",
        note=("PASS" if margin >= inputs.required_grading_margin_s else "FAIL") + f" -- upstream/downstream IDMT operating time margin at {inputs.fault_current_a:.0f}A",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="IEC 60255-151 IDMT relay operating time, upstream/downstream grading margin check at a single fault current",
        references=[
            "IEC 60255-151, Measuring relays and protection equipment -- Part 151: Functional requirements for over/under current protection.",
            "BS 142 (historic UK designation for the same IDMT curve family, superseded by IEC 60255 series).",
        ],
    )


MODULE = CalcModule(
    key="electrical_hv_protection_grading",
    name="Protection Discrimination/Grading Check (IDMT, IEC 60255-151)",
    discipline="Electrical (HV)",
    description=(
        "IDMT relay operating times (IEC 60255-151 standard curves) for an upstream/downstream relay pair at "
        "a stated fault current, checked for adequate grading margin. Pickup settings, TMS, and fault current "
        "are required direct inputs -- see module docstring."
    ),
    input_model=ProtectionGradingInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_hv.protection_grading
    example = ProtectionGradingInput(
        fault_current_a=2000.0,
        downstream_pickup_current_a=100.0,
        downstream_tms=0.1,
        upstream_pickup_current_a=200.0,
        upstream_tms=0.2,
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
