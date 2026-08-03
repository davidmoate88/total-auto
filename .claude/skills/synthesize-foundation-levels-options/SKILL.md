---
name: synthesize-foundation-levels-options
description: Reads a dump of client/project documents (GI reports, FRA, drainage calculations, planning documents, Employer's Requirements) and synthesizes what they already state or support about foundation type/depth and site levels, cross-referenced to the relevant calcs/geotechnical/, calcs/civil/, and calcs/structural/ modules for the engineer to actually run. Does NOT derive a foundation solution or a level itself. Use when the user wants foundation or levels options synthesized/summarized from project documents, or asks what a document set says about foundations, ground conditions, or site levels.
---

# Synthesize foundation and levels options

Reads a set of project documents and produces a synthesis of what they
already state or support about foundation solutions and site levels --
**not a new engineering conclusion this skill invents itself.** Every
figure or recommendation in the output traces back to something a specific
source document actually says, or points at the specific `calcs/` module
an engineer should run to actually derive one.

**Why this skill doesn't derive a foundation solution or a level itself:**
every calc module and every other skill in this repo follows a "flag,
don't guess" discipline for exactly this reason -- a foundation type/depth
or a design level is a real engineering decision with real consequences if
wrong, and it needs to come from an actual calculation
(`calcs/geotechnical/bearing_capacity.py`, a piling design, a levels/
drainage balance) run by a competent engineer against project-specific
inputs, not synthesized from a document summary. This skill's job stops at
*collecting what the documents already say* and *pointing at what to run
next* -- see `docs/ARCHITECTURE.md`'s note on this skill's scope if you're
extending it; deliberately narrower than it might first look.

## Step 1 -- read every document

Use the `Read` tool -- it handles PDFs and images directly. Work through
the whole document set: GI reports, Flood Risk Assessments (FRA), drainage
calculations, planning documents (decision notice, planning statement,
any levels/massing conditions), Employer's Requirements (ERs), and the
contract if it states loading, footprint, or performance requirements.
Read everything before writing anything down -- a GI report's own
recommendations section is often only fully interpretable alongside its
ground conditions summary and the borehole logs behind it.

## Step 2 -- transcribe what the GI report already says about foundations

Most GI reports include the geotechnical engineer's own recommendations --
often literally a "Geotechnical Recommendations" or "Foundation
Recommendations" section. This is the single most valuable source for this
skill, because it's a professional engineering opinion the client has
already paid for and already has in hand -- transcribe it directly rather
than deriving your own:

- **Foundation type(s) discussed or recommended**, and the stated reason
  (e.g. "shallow foundations considered unsuitable due to risk of
  differential settlement in the Alluvium; piled foundations recommended
  to transfer load to the London Clay Formation").
- **Any stated depth, bearing stratum, or capacity figure**, with the exact
  wording -- don't round, don't convert units unless clearly safe to do so
  (e.g. stating both if a document mixes m and mm), don't fill in a number
  the report only implies.
- **Any stated exclusions or caveats** the report itself makes (e.g. "this
  is a preliminary/tender-stage recommendation only", "detailed piling
  design should be undertaken once loads are confirmed") -- these matter
  as much as the recommendation itself, since they set how far the
  document's own author expected this to be relied on.
- **Ground conditions relevant to foundation choice** even where no
  explicit recommendation is given -- made ground extent, groundwater
  depth, contamination affecting foundation choice, obstructions.

If the GI report gives no foundation recommendation at all (common for a
purely factual/ground-conditions-only report), say so explicitly rather
than inferring one from the stratigraphy yourself -- that inference is
exactly `calcs/geotechnical/bearing_capacity.py`'s job (fed from
`fill-ground-model-from-gi-report`'s output), not this skill's.

## Step 3 -- transcribe stated levels information

From the FRA, drainage calculations, and planning documents:

- **Flood-related level requirements** -- flood zone classification, any
  stated finished floor level (FFL) requirement (e.g. "300 mm above the
  1-in-100-year plus climate change flood level"), any stated design flood
  level itself.
- **Existing and proposed ground levels**, where stated -- site survey
  levels, proposed formation/finished levels from drainage calculations or
  civils drawings referenced in the documents.
- **Drainage invert levels/gradients**, where these constrain achievable
  foundation or slab levels (e.g. a stated minimum cover to a drainage run
  that limits how shallow a foundation can be in that area).
- **Any planning condition affecting levels** -- maximum height above a
  stated datum, restrictions on ground raising/lowering.

Record the source and location for each (document + page/section/drawing
reference), same as `build-constraints-register`'s Step 2 -- these are
often the same source documents and the same discipline reading this skill
runs alongside.

## Step 4 -- cross-reference the relevant calc modules

For whatever foundation type(s)/levels questions the documents raise,
point at the specific `calcs/` module(s) that would actually verify or
size a candidate solution -- current keys (confirm against
`calcs/registry.py`, which may have grown since this was written):

- **Shallow foundation, if genuinely still a live option** --
  `geotech_bearing_resistance_ec7` (EN 1997-1 Annex D bearing resistance,
  DA1) -- needs characteristic ground parameters, which
  `fill-ground-model-from-gi-report` + the Ground model interpreter
  produce from the GI data.
- **Retaining structures, if levels differences imply one** --
  `civil_lateral_earth_pressure_ec7` and
  `civil_retaining_wall_stability_ec7`.
- **Slope stability, if the site has or will have significant level
  changes/cut slopes** -- `civil_slope_stability_ec7`.
- **Cut/fill balance for achieving proposed levels** --
  `civil_cut_fill_balance`.
- **Surface water discharge/attenuation implications of levels/drainage
  constraints** -- `civil_surface_water_discharge_rate`.
- **Column base plate / holding-down bolt design, once a foundation
  type and structural loads are confirmed** -- `structural_base_plate_ec3`
  (needs `structural_column_capacity_ec3`'s design axial load as an
  input -- see that module's own docstring for the load-path handoff).
- **Piled foundations** -- not currently covered by any `calcs/` module in
  this repo (see `docs/ROADMAP.md` for what's built) -- note this
  explicitly as a gap if the GI recommends piling, rather than silently
  omitting the cross-reference.

Only list the modules that are actually relevant to what Steps 2-3 found --
don't pad the list with every geotechnical/civils module regardless of
relevance.

## Step 5 -- write the synthesis

A short markdown document, not a database table (unlike the register
skills) -- this is a narrative synthesis, closer in shape to a technical
note than a register:

1. **What the documents say about foundations** -- the GI's own
   recommendation (or its absence), with exact source references.
2. **What the documents say about levels** -- flood/FFL requirements,
   existing/proposed levels, drainage constraints, with exact source
   references.
3. **Relevant calcs to run next**, from Step 4, each with a one-line note
   on what input it needs that these documents do/don't already supply.
4. **Open items** -- anything Steps 2-3 needed but didn't find (no stated
   FFL requirement despite an FRA being present; a GI recommendation with
   no stated bearing capacity figure to substantiate it; a contradiction
   between two documents' stated levels) -- these are exactly the kind of
   "to be confirmed" items `integration/open_items.py` already collects
   from the basis-of-design layer; this skill's open items are the same
   category of thing, one level upstream, from source documents rather
   than from a BoD skeleton.

Save the synthesis somewhere the user can find it -- ask where they'd like
it if not obvious, otherwise use the project's scratchpad location if one
is configured, or the current working directory with a clear name like
`foundation_levels_synthesis.md`.

## Scope

Any project document set with GI/FRA/drainage/levels content is in scope.
Explicitly out of scope, by design, not oversight: selecting a foundation
type, deriving a foundation depth/capacity, deriving a design level, or
producing any other number this skill didn't find already stated in a
source document. If the user wants an actual foundation design, the answer
is "run the cross-referenced `calcs/` modules with real project inputs" --
this skill gets them to that starting line, it doesn't cross the finish
line for them.
