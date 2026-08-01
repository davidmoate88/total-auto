"""
Cut/fill earthwork volume balance — grid method. Answers
`earthworks_and_remediation`'s "Cut/fill balance" `CalculationRequirement`
("Earthwork volumes across the site") in `basis_of_design/civils.py`, and
that section's stated "±0 m³" balanced-target criterion.

Not Eurocode-based -- earthwork quantity takeoff is basic solid geometry
(the grid/four-point method, a long-standing, near-universal approach in UK
earthworks practice, e.g. as described in BS 6031), not a code-governed
calculation the way a bearing or bending check is. The one place this module
is genuinely uncertain is the cut-to-fill conversion factor (bulking on
excavation vs shrinkage on recompaction) -- see Known simplifications.

Method summary
--------------
For each grid point i (existing level, proposed/formation level, tributary
area -- the plan area that point represents, e.g. from a regular survey grid
or a triangulated surface model computed externally):

    depth_i = existing_level_i - proposed_level_i
    depth_i > 0  ->  CUT of depth_i over area_i
    depth_i < 0  ->  FILL of |depth_i| over area_i

    cut_volume_in_situ   = sum(depth_i * area_i) over cut points
    fill_volume_required = sum(|depth_i| * area_i) over fill points  (already
                            the compacted volume needed, since it's measured
                            to the proposed/compacted formation level)

    cut_volume_compacted_equivalent = cut_volume_in_situ * cut_to_fill_conversion_factor
    net_balance = cut_volume_compacted_equivalent - fill_volume_required
                  (positive = surplus material to export, negative = deficit to import)

Grid point data is supplied as lenient pasted text (one point per line:
`existing_level, proposed_level, area`), the same "structured paste, not
free-form NLP" pattern as `calcs/geotechnical/interpretation/text_input.py` --
unparseable lines are reported as warnings, not silently dropped, and this
module's own `calculate()` does that parsing/reporting itself (there is no
bespoke UI tab for this module the way the ground model interpreter has one
-- it's a registered `calcs/` module like any other, so the parsing and its
warnings have to live inside `calculate()` to reach the generic Streamlit
form's result rendering).

Known simplifications / not implemented (see Warnings in the result):
- `cut_to_fill_conversion_factor` (bulking/shrinkage) is a DIRECT INPUT
  (default 1.0, i.e. no adjustment) -- the true factor depends on soil type,
  compaction method, and target relative compaction, and this author does
  not have confident, generalisable figures to embed. Confirm from a
  geotechnical report or trial compaction data before relying on the
  compacted-equivalent cut volume for import/export planning.
- Grid/tributary-area method only -- this module does NOT triangulate a
  surface or compute areas itself; `area_m2` per point is a direct input,
  computed externally (survey grid cell size, or a TIN/GIS tool).
- No allowance for topsoil strip/re-spread (often tracked as a separate,
  shallower balance), services/foundation exclusion volumes, or haul
  route/cost. This is a volumetric balance only.
- No slope stability check -- see the separate "Slope stability check"
  `CalculationRequirement` in the same BoD section (not yet built).
- This is a COST/LOGISTICS consideration, not a safety check -- unlike
  every other calc module in this repo, an imbalance here does not raise a
  `code_compliance` risk flag (there is no code compliance question), only
  a `buildability` one, and only when the imbalance is large relative to
  the total volume moved.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from core.calc_base import CalcModule, CalcResult, Term
from core.risk import DesignRiskFlag


class GridPoint(BaseModel):
    existing_level_m: float
    proposed_level_m: float
    tributary_area_m2: float = Field(..., gt=0)


def _parse_grid_points(text: str) -> tuple[list[GridPoint], list[str]]:
    """Lenient 'existing_level, proposed_level, area' per-line parser -- see module docstring."""
    points: list[GridPoint] = []
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
            existing, proposed, area = (float(p) for p in parts)
            if area <= 0:
                unparsed.append(raw_line)
                continue
            points.append(GridPoint(existing_level_m=existing, proposed_level_m=proposed, tributary_area_m2=area))
        except ValueError:
            unparsed.append(raw_line)
    return points, unparsed


class CutFillBalanceInput(BaseModel):
    grid_points_text: str = Field(
        ...,
        description="One grid point per line: 'existing_level_m, proposed_level_m, area_m2'. "
        "e.g. '12.50, 11.00, 25.0' -- lenient paste parser, unparseable lines are reported as warnings, not dropped silently.",
    )
    cut_to_fill_conversion_factor: float = Field(
        1.0, gt=0,
        description="Converts in-situ cut volume to compacted-fill-equivalent volume (bulking/shrinkage). "
        "1.0 = no adjustment. Confirm from a geotechnical report/trial compaction data -- see module docstring.",
    )
    large_imbalance_threshold_pct: float = Field(
        10.0, gt=0, le=100,
        description="Flag if the net surplus/deficit exceeds this percentage of total volume moved -- informational (buildability/cost), not a pass/fail safety check.",
    )

    @field_validator("grid_points_text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("grid_points_text must not be blank.")
        return v


def calculate(inputs: CutFillBalanceInput) -> CalcResult:
    warnings: list[str] = [
        "Grid/tributary-area method only -- area_m2 per point is a direct input, not derived from "
        "a surface model. cut_to_fill_conversion_factor (bulking/shrinkage) is a direct input, "
        "default 1.0 (no adjustment) -- confirm the true factor from geotechnical data.",
        "No topsoil strip/re-spread, services/foundation exclusion volumes, haul route/cost, or "
        "slope stability check -- this is a volumetric balance only.",
    ]
    risk_flags: list[DesignRiskFlag] = []

    points, unparsed = _parse_grid_points(inputs.grid_points_text)
    for u in unparsed:
        warnings.append(f"Could not parse grid point line: '{u}' -- expected 'existing_level, proposed_level, area' (3 comma-separated numbers, area > 0).")

    if not points:
        warnings.append("No valid grid points parsed -- cannot compute a cut/fill balance.")
        return CalcResult(
            headline=Term("Net balance", 0.0, unit="m^3", note="No valid grid points parsed"),
            terms=[],
            warnings=warnings,
            risk_flags=risk_flags,
            method="Cut/fill earthwork volume balance, grid method",
            references=["BS 6031, Code of practice for earthworks."],
        )

    cut_volume_in_situ = sum((p.existing_level_m - p.proposed_level_m) * p.tributary_area_m2 for p in points if p.existing_level_m > p.proposed_level_m)
    fill_volume_required = sum((p.proposed_level_m - p.existing_level_m) * p.tributary_area_m2 for p in points if p.proposed_level_m > p.existing_level_m)
    cut_points = sum(1 for p in points if p.existing_level_m > p.proposed_level_m)
    fill_points = sum(1 for p in points if p.proposed_level_m > p.existing_level_m)
    balanced_points = len(points) - cut_points - fill_points

    cut_volume_compacted_equivalent = cut_volume_in_situ * inputs.cut_to_fill_conversion_factor

    terms: list[Term] = [
        Term("Grid points parsed", len(points), note=f"{cut_points} cut, {fill_points} fill, {balanced_points} balanced"),
        Term("Cut volume (in-situ)", cut_volume_in_situ, unit="m^3"),
        Term("Cut volume (compacted-equivalent)", cut_volume_compacted_equivalent, unit="m^3", note=f"conversion factor {inputs.cut_to_fill_conversion_factor:g}"),
        Term("Fill volume (required, compacted)", fill_volume_required, unit="m^3"),
    ]

    net_balance = cut_volume_compacted_equivalent - fill_volume_required
    total_moved = cut_volume_compacted_equivalent + fill_volume_required
    imbalance_pct = abs(net_balance) / total_moved * 100 if total_moved > 0 else 0.0

    balance_note = "surplus (export required)" if net_balance > 0 else ("deficit (import required)" if net_balance < 0 else "balanced")
    terms.append(Term("Net balance", net_balance, unit="m^3", note=balance_note))
    terms.append(Term("Imbalance", imbalance_pct, unit="%", note="|net balance| / total volume moved"))

    if imbalance_pct > inputs.large_imbalance_threshold_pct:
        warnings.append(
            f"Net balance ({net_balance:+.1f} m^3) is {imbalance_pct:.1f}% of total volume moved, "
            f"exceeding the {inputs.large_imbalance_threshold_pct:g}% review threshold -- likely "
            "material import/export cost implication worth reviewing against the site strategy."
        )
        risk_flags.append(
            DesignRiskFlag(
                category="buildability",
                severity="medium",
                description=f"Cut/fill balance shows a {imbalance_pct:.1f}% imbalance ({balance_note}) -- {abs(net_balance):.1f} m^3.",
                trigger=f"Imbalance {imbalance_pct:.1f}% exceeds the {inputs.large_imbalance_threshold_pct:g}% threshold.",
                recommended_action="Review against the target ±0 m^3 balance criterion -- consider formation level/profile adjustments to reduce import/export haulage.",
                source_reference="civil_cut_fill_balance",
            )
        )

    headline = Term(
        "Net balance", net_balance, unit="m^3",
        note=f"{balance_note} -- {imbalance_pct:.1f}% of total volume moved",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        risk_flags=risk_flags,
        method="Cut/fill earthwork volume balance, grid method",
        references=[
            "BS 6031, Code of practice for earthworks.",
        ],
    )


MODULE = CalcModule(
    key="civil_cut_fill_balance",
    name="Cut/Fill Earthwork Volume Balance (Grid Method)",
    discipline="Civils",
    description=(
        "Cut and fill volumes and net balance across a site from pasted grid-point data "
        "(existing/proposed levels + tributary area), grid method. Not Eurocode-based -- a "
        "quantity takeoff and cost/logistics consideration, not a safety check."
    ),
    input_model=CutFillBalanceInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.civil.cut_fill_balance
    example = CutFillBalanceInput(
        grid_points_text=(
            "12.50, 11.00, 100\n"
            "12.20, 11.00, 100\n"
            "11.80, 11.00, 100\n"
            "11.40, 11.20, 100\n"
            "11.00, 11.40, 100\n"
            "10.80, 11.50, 100\n"
        ),
    )
    result = calculate(example)
    print(f"{result.headline.label} = {result.headline.value:.3f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
