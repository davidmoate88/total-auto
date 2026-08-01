# Geotechnical — working guide

The only discipline in this repo with a real, executable calculation behind
it, not just a basis of design skeleton. Everything else depends on it
(directly or via the ground model it produces) and it depends on nothing
else here — always start here on a real project.

## What it actually does

Two pieces, chained together:

1. **Ground model interpretation** (`calcs/geotechnical/interpretation/`) —
   takes raw site investigation data (SPT blow counts, CPT cone resistance,
   lab test results, or a structured free-text paste) per soil stratum, and
   derives **characteristic** design parameters: friction angle (phi'),
   cohesion (c'), undrained shear strength (cu), and unit weight.
2. **Bearing resistance calculation** (`calcs/geotechnical/bearing_capacity.py`)
   — takes those characteristic parameters and computes the allowable
   bearing resistance of a spread foundation to **EN 1997-1 (Eurocode 7)
   Annex D, UK National Annex, Design Approach 1** (both DA1 combinations,
   C1 and C2 — the governing case is whichever gives the lower resistance).

## Running it

```bash
# Full UI: paste site investigation data, pick a stratum, run the calc
streamlit run app.py

# Or drive the calc module directly with your own BearingResistanceInput
python3 -m calcs.geotechnical.bearing_capacity
```

## Step by step: from site investigation data to a bearing resistance report

1. **Enter your raw data per stratum.** Any mix of SPT (`SPTReading`: depth,
   raw N, energy ratio), CPT (`CPTReading`: depth, qc), and lab test results
   (`LabTestResult`) is accepted — see `interpretation/models.py`'s
   `Stratum`/`SiteInvestigation` shapes, or just paste structured lines via
   `text_input.py`'s `parse_spt_lines()`/`parse_cpt_lines()`/`parse_lab_lines()`
   if you're working from a borehole log rather than typing data in by hand.
   **This is a lenient structured-paste parser, not a free-text NLP reader**
   — it expects depth/value lines, not prose lifted straight from a ground
   investigation report. If you're starting from a report excerpt, translate
   it into the paste format first (see `docs/ROADMAP.md`'s open item on this).

2. **Let `interpret_stratum()` derive characteristic values.** This applies
   the established correlations (Peck-Hanson-Thornburn for phi' from N1,60;
   Liao-Whitman for the overburden correction CN; Stroud for cu from N60;
   Kulhawy-Mayne for phi'/cu from CPT qc) and then a **conservative,
   lower-bound characteristic value rule**: fewer than 3 readings uses the
   minimum observed value; 3 or more uses `min(mean − 1×stdev, min observed)`.
   This is deliberately cautious, per your own instruction earlier in this
   project — if a stratum only has 2 SPT readings, don't expect the
   characteristic value to be an average.

3. **Feed the result straight into the bearing calc** via
   `to_bearing_resistance_kwargs()` — this is the seam that keeps
   "characteristic value derivation" and "design value / partial factor
   application" architecturally separate (a deliberate EC7 modelling choice,
   see `docs/ARCHITECTURE.md` principle 4). Don't skip this and hand-type
   phi'/cu into `BearingResistanceInput` unless you're deliberately
   overriding the derived value for a reason you can defend.

4. **Fill in `BearingResistanceInput`'s remaining fields** — these are
   genuinely project-specific and have no default derivation: `width_m`/
   `length_m` (footing plan, B ≤ L by convention), `depth_m` (founding
   depth), any load eccentricity, base inclination, and the characteristic
   loads (`characteristic_permanent_load_kn`, `characteristic_variable_load_kn`,
   `characteristic_horizontal_load_kn`). Leave the loads at 0 if you only
   want the resistance side (no utilisation check) — the calc still runs,
   it just skips the "does this footing actually work" verdict.

5. **Read the result.** `calculate()` returns every intermediate `Term` for
   both DA1 combinations (C1: unfactored soil parameters; C2: factored/
   reduced soil parameters), not just the final answer — the governing case
   is `min(Rd_C1, Rd_C2)`. Turn it into a review-ready sheet with
   `core/report.py`'s `render_report()`.

## What to actually watch for

- **The Ngamma factor caveat.** `bearing_capacity.py`'s docstring flags this
  explicitly: the Ngamma formula used (`2*(Nq-1)*tan(phi')`) differs from
  Vesic's original (`2*(Nq+1)*tan(phi')`), and hasn't been independently
  verified against the current purchased BS EN 1997-1 text in this
  environment. Don't take this on faith for a real design — check it.
- **Two risk flags fire automatically, read both.** A `temporary_works` flag
  fires whenever `depth_m >= 1.0` (the excavation itself is a distinct,
  often more critical, construction-stage condition — see
  `docs/ARCHITECTURE.md`'s risk-flagging section). A `critical` severity
  `code_compliance` flag fires if the governing utilisation exceeds 1.0 —
  i.e. the calc is telling you the footing fails, not just warning you.
- **"Characteristic" is not "average."** If you're used to eyeballing a
  mean SPT N-value, the deliberately conservative rule above will usually
  give you something lower — that's correct, not a bug, and it's exactly
  the "take assumptions" behaviour you asked for.

## Where this feeds next

Every other discipline that references geotechnical (structural's
foundations, civils' earthworks/retaining structures, both electrical
disciplines' earthing/earth-electrode design) is waiting on this ground
model and bearing resistance output specifically — check
`integration/graph.py`'s `upstream_of("section:structural.substructure_and_foundations")`
(and similar) if you want the exact list rather than taking this guide's
word for it.
