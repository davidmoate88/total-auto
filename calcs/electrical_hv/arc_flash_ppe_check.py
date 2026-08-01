"""
HV arc flash PPE requirement and practical-PPE-limit screening. Answers
`arc_flash_and_hv_safety`'s "HV arc flash calculation method" and "Minimum
PPE category for HV switching" `DesignCriterion` entries in
`basis_of_design/electrical_hv.py`, and feeds its "HV arc flash risk
assessment report" `Deliverable`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN, MORE SO THAN
ANY OTHER MODULE IN THIS REPO (see calcs/electrical_lv/arc_flash_ppe_check.py
for the same reasoning applied at LV) ***
This module deliberately does NOT calculate arc flash incident energy, for
the same reasons as its LV counterpart -- IEEE 1584-2018's empirical model
is not something this author can reproduce from memory with the confidence
this repo's other formulae carry, and a wrong incident energy figure has a
direct injury pathway (it sets what PPE a worker wears for live work) that
no ordinary structural/geotechnical utilisation check has. This module goes
further than simply repeating that reasoning: it is DESIGNED DIFFERENTLY
from the LV version, not just re-parameterised, because HV arc flash has a
genuinely different consequence profile that the LV module's shape doesn't
fit well:
- This discipline's own BoD criterion ("HV arc flash calculation method")
  already notes that "not all LV-oriented tools extend cleanly to HV
  switchgear" -- reinforcing that incident energy must come from a
  dedicated HV-specific study (IEEE 1584 or an equivalent HV-specific
  method), never extrapolated from an LV assessment or from this module.
- HV incident energies routinely exceed the traditional LV "PPE Category
  1-4" banding (which tops out around 40 cal/cm^2) entirely -- the LV
  module's illustrative Category framework doesn't meaningfully classify a
  150 cal/cm^2 HV finding, it just says "Dangerous — exceeds Category 4"
  for the whole upper range where HV commonly lands. Rather than force HV
  results through that same LV-shaped framework, this module instead
  reports the required PPE arc rating directly (== the incident energy
  itself) and checks it against a PRACTICAL ARC-RATED PPE LIMIT -- roughly
  the upper bound of what commercially available heavy-duty arc-flash
  PPE/suits can actually provide, above which PPE alone cannot protect a
  worker regardless of category naming, and de-energised work or other
  engineering controls become the only real option. This mirrors how the
  section's own risk flag already frames HV arc flash: "far higher than
  LV... PPE categorisation and safe working procedures need a dedicated HV
  assessment."
- Both `second_degree_burn_threshold_cal_cm2` and
  `practical_ppe_arc_rating_limit_cal_cm2` are illustrative direct inputs
  with defaults, not fixed constants -- the burn threshold (Stoll curve) is
  the same physical constant used at LV, but the practical PPE ceiling
  varies by manufacturer/suit range and must be confirmed against the
  project's actual specified PPE, not assumed from this module's default.

Known simplifications / not implemented (see Warnings in the result):
- Does NOT calculate incident energy or arc flash boundary distance --
  both are direct inputs / external HV-specific study outputs.
- Does NOT determine whether a given HV board/switchgear needs a study in
  the first place -- a project-specific prospective-fault-level threshold
  comparison, not computed here (same scoping decision as the LV module).
- practical_ppe_arc_rating_limit_cal_cm2 is illustrative -- confirm against
  the actual specified PPE/suit manufacturer's rating, not this default.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2 = 1.2  # Stoll curve -- same physical constant as calcs/electrical_lv/arc_flash_ppe_check.py


class HVArcFlashPpeCheckInput(BaseModel):
    incident_energy_cal_cm2: float = Field(
        ..., gt=0,
        description="Incident energy (cal/cm^2) at working distance, from a DEDICATED HV-specific arc flash study "
        "(IEEE 1584-2018 or an equivalent HV-specific method) -- this module does NOT calculate incident energy "
        "itself, and this figure must NOT be extrapolated from an LV assessment. See module docstring.",
    )
    practical_ppe_arc_rating_limit_cal_cm2: float = Field(
        100.0, gt=0,
        description="Illustrative upper bound of commercially available heavy-duty arc-rated PPE (cal/cm^2) -- "
        "confirm against the project's actual specified PPE/suit manufacturer rating, not this default.",
    )


def calculate(inputs: HVArcFlashPpeCheckInput) -> CalcResult:
    warnings: list[str] = [
        "This module does NOT calculate incident energy -- incident_energy_cal_cm2 must come from a dedicated "
        "HV-specific arc flash study (IEEE 1584-2018 or equivalent), never extrapolated from an LV assessment. "
        "See module docstring.",
        "practical_ppe_arc_rating_limit_cal_cm2 is an illustrative default -- confirm against the project's "
        "actual specified PPE/suit manufacturer rating.",
        "Does not determine whether a given HV board/switchgear needs an arc flash study in the first place -- "
        "that is a separate prospective-fault-level threshold comparison.",
        "Does not calculate arc flash boundary distance -- that is also an external study output.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    E = inputs.incident_energy_cal_cm2
    terms: list[Term] = [
        Term("Second-degree burn threshold", SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2, unit="cal/cm^2", note="Stoll curve, ~1s exposure -- same constant as the LV arc flash module"),
        Term("Required PPE arc rating", E, unit="cal/cm^2", note="== incident energy -- PPE must be rated at least this"),
    ]

    exceeds_burn_threshold = E >= SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2
    exceeds_practical_limit = E > inputs.practical_ppe_arc_rating_limit_cal_cm2
    terms.append(Term(
        "Exceeds second-degree burn threshold", 1.0 if exceeds_burn_threshold else 0.0,
        note="Arc flash boundary marking/PPE applies" if exceeds_burn_threshold else "Below the burn threshold",
    ))
    terms.append(Term(
        "Exceeds practical PPE limit", 1.0 if exceeds_practical_limit else 0.0,
        note="No practical arc-rated PPE provides protection" if exceeds_practical_limit else "Within practical PPE range",
    ))

    if exceeds_practical_limit:
        warnings.append(
            f"Incident energy ({E:.2f} cal/cm^2) exceeds the practical arc-rated PPE limit "
            f"({inputs.practical_ppe_arc_rating_limit_cal_cm2:.2f} cal/cm^2) -- PPE alone cannot protect a worker "
            "at this location regardless of category/rating naming."
        )
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Incident energy ({E:.2f} cal/cm^2) exceeds the practical arc-rated PPE limit ({inputs.practical_ppe_arc_rating_limit_cal_cm2:.2f} cal/cm^2).",
            trigger=f"incident_energy={E:.2f}cal/cm^2 > practical_ppe_limit={inputs.practical_ppe_arc_rating_limit_cal_cm2:.2f}cal/cm^2",
            recommended_action="De-energise before work, use remote racking/switching, or specify arc-resistant switchgear -- PPE alone is not a viable control at this incident energy.",
            source_reference="electrical_hv_arc_flash_ppe_check",
        ))
    elif exceeds_burn_threshold:
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="high",
            description=f"Incident energy ({E:.2f} cal/cm^2) exceeds the second-degree burn threshold -- arc flash boundary marking and PPE rated at least {E:.2f} cal/cm^2 are required.",
            trigger=f"incident_energy={E:.2f}cal/cm^2 >= {SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2}cal/cm^2",
            recommended_action=f"Specify PPE rated at least {E:.2f} cal/cm^2 and fit an arc flash warning label, per the 'HV arc flash risk assessment report' deliverable. Severity kept HIGH (not medium, unlike the equivalent LV finding) per this discipline's own risk flag that HV arc flash consequences are typically far more severe than LV.",
            source_reference="electrical_hv_arc_flash_ppe_check",
        ))

    headline = Term(
        "Required PPE arc rating", E, unit="cal/cm^2",
        note="DANGEROUS -- exceeds practical PPE limit" if exceeds_practical_limit else ("PPE required" if exceeds_burn_threshold else "Below burn threshold"),
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Required PPE arc rating and practical-PPE-limit screening from an externally-supplied HV-specific incident energy figure",
        references=[
            "IEEE 1584-2018, Guide for Performing Arc-Flash Hazard Calculations -- governing method for the incident energy INPUT this module requires (not reproduced here); confirm applicability to the specific HV switchgear per this discipline's own criterion.",
            "BS EN 50110-1, Operation of electrical installations.",
            "Stoll, A.M. & Chianta, M.A., 1968 -- basis of the ~1.2 cal/cm^2 second-degree burn threshold.",
        ],
    )


MODULE = CalcModule(
    key="electrical_hv_arc_flash_ppe_check",
    name="HV Arc Flash PPE Requirement Check (Incident Energy as Direct Input)",
    discipline="Electrical (HV)",
    description=(
        "Reports the required PPE arc rating (== an externally-supplied HV-specific incident energy figure) "
        "and flags when it exceeds a practical arc-rated PPE limit, above which PPE alone cannot protect a "
        "worker. Does NOT calculate incident energy itself -- see module docstring for why, and for how this "
        "differs in shape (not just numbers) from the LV arc flash module."
    ),
    input_model=HVArcFlashPpeCheckInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_hv.arc_flash_ppe_check
    example = HVArcFlashPpeCheckInput(incident_energy_cal_cm2=55.0)
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
