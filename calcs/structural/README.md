# calcs/structural/

Structural calc modules — status: **placeholder, no modules yet**.

Target codes: EN 1993 (steel), EN 1992 (concrete), EN 1995 (timber) — UK National
Annex, matching the Eurocode-compliance requirement that applies across this whole
repo (see the caveat in `calcs/geotechnical/bearing_capacity.py` for how that's
documented/flagged in practice).

## Pattern to follow

Copy the shape of `calcs/geotechnical/bearing_capacity.py`:

1. A pydantic input model with characteristic values + `model_validator` checks
   for internal consistency.
2. A `calculate(inputs) -> CalcResult` function that keeps every intermediate term
   (via `core.calc_base.Term`), not just the headline answer.
3. Partial factors / combinations applied explicitly and labelled in the output
   (see how DA1-C1/C2 are both shown in the geotechnical module) — never silently
   collapsed into one number without showing which combination governed.
4. A `MODULE = CalcModule(...)` registration, added to `calcs/registry.py`.
5. A test file in `tests/` validating bearing-capacity-factor-style constants
   against known values, plus edge cases (validation errors, governing case
   selection, warnings).

First candidate: a simply-supported beam capacity check (EN 1993 for a steel
section, or EN 1992 for a concrete one — whichever is more useful first).
