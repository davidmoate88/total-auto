---
name: fill-ground-model-from-gi-report
description: Reads a ground investigation (GI) report -- borehole/trial pit logs, SPT/CPT in-situ test results, laboratory test results -- and produces a JSON file that populates total-auto's Ground model interpreter with a full layered soil profile, via the tool's "Import GI-derived strata" expander. Use when the user provides a GI report/factual report/borehole logs and wants them turned into a ground model, or asks to "fill in" / "populate" / "transpose" the ground model interpreter from a document.
---

# Fill ground model from a GI report

Reads a ground investigation (GI) report and produces a JSON file that
populates total-auto's Streamlit "Ground model interpreter" tool (via its
"Import GI-derived strata (JSON)" expander in `app.py`) with a full,
multi-layer soil profile in one go, rather than the engineer retyping each
stratum's SPT/CPT/lab data by hand.

**The single rule that matters more than any other in this skill: never
guess.** This mirrors `.claude/skills/fill-calc-inputs-from-drawings/`'s
governing rule exactly, applied one level up: not just individual readings,
but stratum *boundaries* and *behaviour classifications* too. A value,
reading, boundary, or classification you cannot read with real confidence
from the source document must be **left out of the output entirely** -- not
guessed, not interpolated between two readings, not assumed from a "typical"
soil description. An omitted stratum or reading just means the engineer adds
or corrects it by hand in the app, exactly as if this skill had never run
for that piece -- a safe, expected outcome. A wrong stratum boundary or a
misclassified behaviour (granular vs cohesive) silently changes which
correlation formula runs and which overburden stress every deeper stratum
sees -- worse than an empty field, because nothing about the output looks
incomplete.

## Step 1 -- read the live model and format rules (always, every run)

Unlike `fill-calc-inputs-from-drawings`, there's no `calcs.schema_export` CLI
here -- the Ground model interpreter isn't a registered `calcs.registry`
module, it's a bespoke tool with its own data shapes. Read these two files
directly before extracting anything; both are short, and field
names/constraints/paste-format rules can change as the app evolves, so never
rely on a remembered shape, including any example shown later in this file:

- `calcs/geotechnical/interpretation/models.py` -- the authoritative
  `Stratum`/`SiteInvestigation` field names, types, and constraints (e.g.
  `top_depth_m`/`base_depth_m`/`behavior`/`assumed_unit_weight_kn_m3` are
  all REQUIRED on `Stratum`; `SiteInvestigation` requires strata to be
  depth-contiguous with no gaps or overlaps -- read its `_check_strata_contiguous`
  validator).
- `calcs/geotechnical/interpretation/text_input.py` -- the authoritative
  paste-text format each of `spt_text`/`cpt_text`/`lab_text` must follow
  (its own module docstring explains the lenient line parser's exact
  tolerances). Do not invent your own format -- an unparsed line is silently
  reported back to the engineer as a warning rather than used, so getting
  the format right the first time matters.

## Step 2 -- identify every stratum, and every borehole/trial pit

Use the `Read` tool -- it handles PDFs and images directly. Read the entire
report before extracting anything; a stratum's classification is often only
correctly interpretable alongside the borehole log's legend, the site
location plan, or a laboratory test summary table elsewhere in the same
document.

A real GI report is not one profile -- it's usually several borehole/trial
pit logs across a site, and their stratification commonly differs between
locations (that's real ground variability, not a extraction error). This
tool produces ONE layered profile per interpretation run, so:

- **Pick ONE borehole/trial pit log as the representative profile** --
  prefer the deepest, most complete log, or the one nearest the structure
  being designed if that's stated/inferable. State which one you picked and
  why in the extraction notes (Step 5).
- **Do not blend or average stratification across multiple boreholes** --
  picking a boundary depth as some average of two logs' differing readings
  is exactly the kind of invented number this skill's central rule
  forbids. If boreholes disagree materially, say so explicitly in the
  extraction notes rather than silently reconciling them.
- If the user tells you which borehole/trial pit to use, use that one
  instead of guessing which is "representative."

## Step 3 -- map each stratum's boundaries, behaviour, and readings

For the chosen borehole/trial pit log, walk it top to bottom. For each
described layer, ask the same question `fill-calc-inputs-from-drawings`
asks per field: *can I point to the specific place in the source document
where this is stated, unambiguously?*

- **Top/base depth** -- directly stated on the log (or the previous
  stratum's base depth continues into this one's top, per the tool's own
  contiguous-profile requirement). If the log shows a gradational/uncertain
  transition over a depth range, use your best single stated split point
  only if the log itself commits to one -- otherwise leave that stratum
  (and everything below it, since depths must chain) out and note the
  ambiguity.
- **Behaviour (`granular` vs `cohesive`)** -- from the log's own soil
  description, using standard BS 5930 description conventions: SAND/GRAVEL
  (loose/medium dense/dense, etc.) is `granular`; CLAY/SILT (soft/firm/stiff,
  etc.) is `cohesive`. A description that's genuinely mixed (e.g. "sandy
  CLAY", "clayey SAND") should be classified by its *named* soil (the
  capitalised principal soil type in BS 5930 convention is the noun, e.g.
  "sandy CLAY" -> cohesive) -- but if the log's own wording is genuinely
  ambiguous about which behaviour governs, leave that stratum out and flag
  it rather than guess.
- **`assumed_unit_weight_kn_m3`** -- only if the log or an accompanying lab
  summary states a bulk density/unit weight *for that specific stratum*.
  This is a REQUIRED field on `Stratum` with no safe default (unlike some
  calc-module defaults elsewhere in this repo), so if genuinely not stated,
  that whole stratum cannot be included in the output JSON -- note it in
  Step 5 as needing the engineer's own typical-value judgement, same as the
  tool's own UI does when a stratum has no lab bulk density data (it warns
  and falls back to whatever the engineer enters).
- **SPT/CPT/lab readings** -- transcribe each into the exact paste format
  from Step 1, one reading per line, only for readings that fall within
  that stratum's own depth range (the tool rejects a reading outside its
  stratum's `[top_depth_m, base_depth_m]`). Include the hammer energy
  ratio for SPT or sleeve friction for CPT only if the log actually states
  a project-specific value different from the parser's own default -- don't
  invent one.
- **`name`** -- a short descriptive label (e.g. "Made Ground", "Sandy
  Gravel", "London Clay") from the log's own terminology, not a generic
  "Stratum N" -- makes the imported profile checkable against the source
  log at a glance.

## Step 4 -- site-level water table depth

One value, from the log's recorded groundwater strike(s)/standpipe/piezometer
reading, not per-stratum. If multiple strikes are recorded (perched water,
seasonal variation, or different boreholes disagreeing), do NOT average or
pick one silently -- leave `water_table_depth_m` out of the JSON and flag
the discrepancy in the extraction notes; the engineer's own judgement about
which condition governs the design case matters here, same reasoning as
`basis_of_design/electrical_lv.py`'s "flag, don't guess" for project-specific
design decisions.

## Step 5 -- write the output JSON

One JSON object:

```json
{
  "water_table_depth_m": 2.0,
  "strata": [
    {
      "name": "Made Ground",
      "behavior": "granular",
      "top_depth_m": 0.0,
      "base_depth_m": 1.0,
      "assumed_unit_weight_kn_m3": 17.0,
      "spt_text": "0.5, 6",
      "cpt_text": "",
      "lab_text": ""
    },
    {
      "name": "Sandy Gravel",
      "behavior": "granular",
      "top_depth_m": 1.0,
      "base_depth_m": 6.0,
      "assumed_unit_weight_kn_m3": 19.0,
      "spt_text": "2.0, 14\n3.5, 18\n5.0, 25",
      "cpt_text": "2.5, 6.5",
      "lab_text": "3.0, bulk_density, unit_weight=19.0"
    }
  ]
}
```

Omit `water_table_depth_m` entirely (not `null`) if not confidently
determinable per Step 4. Every stratum in `strata` MUST have
`name`/`behavior`/`top_depth_m`/`base_depth_m`/`assumed_unit_weight_kn_m3`
present -- the app's import skips (and reports) any stratum missing one of
these, since there's no safe default to fall back on for a required field.
`spt_text`/`cpt_text`/`lab_text` may be empty strings if that stratum
genuinely has no readings of that type. Strata must be listed top-to-bottom
and depth-contiguous (each stratum's `top_depth_m` equal to the previous
stratum's `base_depth_m`) -- if a genuine gap exists in your source log
(rare, but possible with an unlogged interval), that's a reason to stop and
flag it in the extraction notes rather than force strata together.

Save the file somewhere the user can find it -- ask where they'd like it if
not obvious, otherwise use the project's scratchpad location if one is
configured, or the current working directory with a clear name like
`extracted_ground_model.json`.

## Step 6 -- write extraction notes alongside the JSON

Same audit-trail idea as `fill-calc-inputs-from-drawings`'s Step 5, one
level up (about the profile as a whole, not just individual fields):

- **Which borehole/trial pit was used as the representative profile, and
  why** (e.g. "BH2 -- deepest log on site, closest to the proposed
  foundation location per the site plan").
- **Other boreholes/trial pits that exist but weren't used**, and whether
  their stratification looks broadly consistent or materially different --
  this is exactly the kind of thing a reviewer should see before trusting a
  single-borehole profile for design.
- **Every stratum or reading deliberately left out, and why** (ambiguous
  boundary, no stated unit weight, reading outside a stratum's depth range,
  genuinely mixed/unclear soil description).
- **The water table condition**, including any multiple-strike discrepancy
  noted in Step 4.

## Step 7 -- tell the user what to do next

Point them at the Ground model interpreter tool's **"Import GI-derived
strata (JSON)"** expander: upload the file, click **Import**, then review
the added strata in the "Profile so far" list before clicking **"Interpret
full profile"**. Mention the extraction notes file so they check what was
and wasn't included -- same as the electrical skill, an import is a
starting point for the engineer to check and complete, not a finished,
ready-to-run profile. Since a stratum with a missing required field is
skipped entirely (not partially imported), point out explicitly if any
strata from the source log didn't make it into the JSON, so the user knows
to add those by hand rather than assuming the imported profile is complete.

## Scope

Any GI/factual report presented as borehole or trial pit logs with SPT/CPT/
laboratory results is in scope -- this isn't limited by discipline the way
`fill-calc-inputs-from-drawings` is scoped to Electrical (LV)/(HV), since
the Ground model interpreter is a single tool, not a set of per-discipline
calc modules. Out of scope: deriving design parameters yourself (phi'/cu/
unit weight) -- that's `calcs/geotechnical/interpretation/ground_model.py`'s
job, run inside the app after import, not this skill's; and combining data
from multiple boreholes into one blended profile (see Step 2).
