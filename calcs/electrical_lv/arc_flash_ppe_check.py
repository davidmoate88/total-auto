"""
Arc flash PPE category check and dangerous-energy screening. Answers
`arc_flash_and_electrical_safety`'s "PPE category framework" and "Arc flash
study trigger" `DesignCriterion` entries in
`basis_of_design/electrical_lv.py`, and feeds its "Arc flash warning label
schedule" `Deliverable`.

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN, MORE SO THAN
ANY OTHER MODULE IN THIS REPO ***
This module deliberately does NOT calculate arc flash incident energy.
Every other calc module in this repo embeds a formula I have high
independent-verification confidence in (Manning's equation, Rankine earth
pressure theory, the Fellenius method, Ohm's-law-based voltage drop) and
flags genuinely uncertain individual VALUES as required direct inputs. Arc
flash incident energy is different in kind, not just degree: the governing
method (IEEE 1584-2018) is a multi-parameter empirical regression with
equipment-class-specific coefficients (electrode configuration, enclosure
size, working distance exponents per Table 5 of that standard) that are not
something this author can reproduce from training knowledge with the
confidence this repo's other formulae carry -- and unlike a failed
structural/geotechnical utilisation check (which gets caught by a
reviewer/site inspection before anyone is exposed to it), an arc flash
incident energy number governs what PPE a worker actually wears while doing
live/energised work. A wrong number here has a direct, immediate injury
pathway that no other calculation in this repo has. Getting this
importantly wrong is a materially different risk than getting a bearing
utilisation wrong, so the ordinary "flag one uncertain value, compute the
rest" pattern used everywhere else in this repo is NOT applied here --
INCIDENT ENERGY ITSELF IS THE REQUIRED DIRECT INPUT, computed externally by
a competent person using IEEE 1584-2018 (or an equivalent recognised
method) or proprietary arc flash study software, never by this module.

What this module DOES do, which is safe, well-defined bookkeeping once a
qualified arc flash study has already produced an incident energy figure:
- Compares the incident energy against the well-established ~1.2 cal/cm^2
  second-degree burn threshold (the Stoll curve value near-universally
  cited across NFPA 70E/IEEE 1584/OSHA guidance as the basis for the arc
  flash boundary concept) to flag whether PPE/boundary marking applies at
  all.
- Classifies the incident energy into illustrative PPE category bands
  (commonly cited cal/cm^2 thresholds from older NFPA 70E hazard/risk
  category tables) -- these band boundaries are DIRECT INPUTS with
  illustrative defaults, not fixed constants, because (a) NFPA 70E has
  moved between editions from named "hazard/risk categories" toward
  arc-rated-PPE-by-cal/cm^2 in places, and (b) the exact current banding is
  exactly the kind of standard-text detail this repo's "flag, don't guess"
  discipline applies to elsewhere (see calcs/electrical_lv/
  cable_sizing_voltage_drop.py's BS 7671 table caveats). Confirm the actual
  bands against the current NFPA 70E edition and the project's actual PPE
  inventory/manufacturer arc ratings before relying on the category label.
- Raises a critical safety flag if the incident energy exceeds the
  project's stated dangerous-energy threshold (illustrative default 40
  cal/cm^2, the top of the traditional Category 4 band, above which
  energised work is generally considered too hazardous for any practical
  PPE) -- recommending de-energised work or additional engineering
  controls rather than a PPE-based control alone.

Known simplifications / not implemented (see Warnings in the result):
- Does NOT calculate incident energy or arc flash boundary distance -- both
  are direct inputs / external study outputs, see above.
- Does NOT determine whether a given board/MCC needs an arc flash study in
  the first place (the "Arc flash study trigger" criterion's prospective-
  fault-level threshold) -- that is a project-specific policy threshold
  compared directly against a switchboard's known fault level, simple
  enough not to need a dedicated calc, and is not computed here.
- PPE category band boundaries are illustrative direct inputs, not fixed
  constants -- confirm against the current NFPA 70E edition.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag

SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2 = 1.2  # Stoll curve -- near-universally cited across NFPA 70E/IEEE 1584/OSHA guidance


class ArcFlashPpeCheckInput(BaseModel):
    incident_energy_cal_cm2: float = Field(
        ..., gt=0,
        description="Incident energy (cal/cm^2) at working distance, from an external IEEE 1584-2018 (or equivalent) "
        "arc flash study -- this module does NOT calculate incident energy itself, see module docstring.",
    )
    category_1_max_cal_cm2: float = Field(4.0, gt=0, description="Illustrative upper bound of PPE Category 1 -- confirm against the current NFPA 70E edition/project PPE inventory.")
    category_2_max_cal_cm2: float = Field(8.0, gt=0, description="Illustrative upper bound of PPE Category 2.")
    category_3_max_cal_cm2: float = Field(25.0, gt=0, description="Illustrative upper bound of PPE Category 3.")
    category_4_max_cal_cm2: float = Field(40.0, gt=0, description="Illustrative upper bound of PPE Category 4 -- above this, energised work is generally considered too hazardous for practical PPE alone.")


def calculate(inputs: ArcFlashPpeCheckInput) -> CalcResult:
    warnings: list[str] = [
        "This module does NOT calculate incident energy -- incident_energy_cal_cm2 must come from a competent "
        "person's IEEE 1584-2018 (or equivalent) arc flash study. See module docstring for why this repo's "
        "usual 'compute the formula, flag one uncertain value' pattern is deliberately NOT used here.",
        "PPE category band boundaries are illustrative direct inputs -- confirm against the current NFPA 70E "
        "edition and the project's actual PPE inventory/manufacturer arc ratings.",
        "Does not determine whether a board/MCC needs an arc flash study in the first place (the 'Arc flash "
        "study trigger' criterion) -- that is a separate prospective-fault-level threshold comparison.",
        "Does not calculate arc flash boundary distance -- that is also an external study output.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    E = inputs.incident_energy_cal_cm2
    terms: list[Term] = [
        Term("Second-degree burn threshold", SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2, unit="cal/cm^2", note="Stoll curve, ~1s exposure -- basis of the arc flash boundary concept"),
    ]

    exceeds_burn_threshold = E >= SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2
    terms.append(Term(
        "Exceeds second-degree burn threshold", 1.0 if exceeds_burn_threshold else 0.0,
        note="Arc flash boundary marking/PPE applies" if exceeds_burn_threshold else "Below the burn threshold",
    ))

    bands = [
        (inputs.category_1_max_cal_cm2, "Category 1"),
        (inputs.category_2_max_cal_cm2, "Category 2"),
        (inputs.category_3_max_cal_cm2, "Category 3"),
        (inputs.category_4_max_cal_cm2, "Category 4"),
    ]
    ppe_category = "Dangerous — exceeds Category 4"
    for max_energy, label in bands:
        if E <= max_energy:
            ppe_category = label
            break

    if E > inputs.category_4_max_cal_cm2:
        warnings.append(
            f"Incident energy ({E:.2f} cal/cm^2) exceeds the Category 4 threshold ({inputs.category_4_max_cal_cm2:.2f} "
            "cal/cm^2) -- energised work at this location is generally considered too hazardous for PPE alone."
        )
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="critical",
            description=f"Incident energy ({E:.2f} cal/cm^2) exceeds the dangerous-energy threshold ({inputs.category_4_max_cal_cm2:.2f} cal/cm^2).",
            trigger=f"incident_energy={E:.2f}cal/cm^2 > category_4_max={inputs.category_4_max_cal_cm2:.2f}cal/cm^2",
            recommended_action="De-energise before work, or apply additional engineering controls (current-limiting devices, remote racking/switching, arc-resistant switchgear) rather than relying on PPE alone.",
            source_reference="electrical_lv_arc_flash_ppe_check",
        ))
    elif exceeds_burn_threshold:
        risk_flags.append(DesignRiskFlag(
            category="safety", severity="medium",
            description=f"Incident energy ({E:.2f} cal/cm^2) exceeds the second-degree burn threshold -- arc flash boundary marking and PPE ({ppe_category}) are required.",
            trigger=f"incident_energy={E:.2f}cal/cm^2 >= {SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2}cal/cm^2",
            recommended_action=f"Ensure PPE rated for at least {ppe_category} ({E:.2f} cal/cm^2) is specified and an arc flash warning label is fitted, per the 'Arc flash warning label schedule' deliverable.",
            source_reference="electrical_lv_arc_flash_ppe_check",
        ))

    terms.append(Term("PPE category", 0.0, note=ppe_category))

    headline = Term(
        "Incident energy", E, unit="cal/cm^2",
        note=f"{ppe_category}" + (" -- DANGEROUS, exceeds practical PPE" if E > inputs.category_4_max_cal_cm2 else ""),
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="PPE category classification and dangerous-energy screening from an externally-supplied IEEE 1584 incident energy figure",
        references=[
            "IEEE 1584-2018, Guide for Performing Arc-Flash Hazard Calculations -- governing method for the incident energy INPUT this module requires (not reproduced here).",
            "NFPA 70E, Standard for Electrical Safety in the Workplace -- PPE category framework (illustrative bands, confirm current edition).",
            "Stoll, A.M. & Chianta, M.A., 1968 -- basis of the ~1.2 cal/cm^2 second-degree burn threshold.",
        ],
    )


MODULE = CalcModule(
    key="electrical_lv_arc_flash_ppe_check",
    name="Arc Flash PPE Category Check (Incident Energy as Direct Input)",
    discipline="Electrical (LV)",
    description=(
        "Classifies an externally-supplied IEEE 1584 incident energy figure into an illustrative PPE category "
        "band and raises a critical safety flag above a dangerous-energy threshold. Does NOT calculate incident "
        "energy itself -- see module docstring for why."
    ),
    input_model=ArcFlashPpeCheckInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.electrical_lv.arc_flash_ppe_check
    example = ArcFlashPpeCheckInput(incident_energy_cal_cm2=6.5)
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.4f} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
