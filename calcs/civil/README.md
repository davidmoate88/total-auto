# calcs/civil/

Civil engineering calc modules (drainage, earthworks, pavement) — status:
**placeholder, no modules yet**.

Relevant codes/guidance vary by sub-discipline more than structural/geotechnical
does (e.g. drainage sizing often follows the Wallingford Procedure / Sewers for
Adoption / BS EN 752 rather than an EN 1990-series Eurocode) — confirm the
governing standard per calc before building, same as the National-Annex check
done for the geotechnical module.

## Pattern to follow

Same as `calcs/structural/README.md` — copy the shape of
`calcs/geotechnical/bearing_capacity.py`: pydantic input model, `calculate()`
keeping full working via `Term`, explicit combinations/factors where relevant,
`MODULE` registration in `calcs/registry.py`, and a test file with known-value
checks plus edge cases.
