# Civils — working guide

Nine sections covering a building project's civils scope: site/existing
conditions, earthworks/remediation, foul drainage, surface water/SuDS,
flood risk, highways/access, external works/pavements, utilities
coordination, and retaining structures.

## Where this sits in the process

**Part of the four-way concurrent cluster** — civils, LV electrical, HV
electrical, and mechanical piping mutually depend on each other (see
`docs/guides/README.md`). Specifically: `utilities_coordination` interfaces
directly with LV electrical and mechanical piping (new service connections),
and HV electrical references civils back via its own substations/cabling
sections — so the loop closes through all four even though
`utilities_coordination` itself only names two of them explicitly. There's
no valid order to fix among these four — develop them concurrently and use
the open items register (`python3 -m integration.open_items`) to see what's
actually stuck at any point, not a fixed hand-off sequence.

Two sections also depend directly on **geotechnical** (which should already
be under way, being the one true starting point): `earthworks_and_remediation`
and `retaining_structures` both need the ground model before their slope
stability/lateral earth pressure calculations can proceed.

## Working through the nine sections

1. **`site_and_existing_conditions` first, genuinely first.** Everything
   else in civils (and several other disciplines) assumes existing levels
   and utility records are known. This is also the one section with real,
   immediate practical advice: commission the PAS 128 utility survey early
   — the skeleton's own assumption is that statutory undertaker records are
   "indicative only" until verified, and that verification has a real lead
   time.
2. **`earthworks_and_remediation` and `retaining_structures`** — both need
   the geotechnical ground model; both carry a high-severity
   `temporary_works` risk flag (see below). Don't finalise either without
   checking `calcs/geotechnical/` output first.
3. **`foul_drainage`, `surface_water_drainage_suds`, `flood_risk`** — these
   three interact tightly (climate change allowance and discharge rate
   constraints flow from flood risk into SuDS sizing) — work them as a
   sub-group, not in isolation from each other.
4. **`highways_and_access`, `external_works_and_pavements`** — largely
   self-contained once the site layout is fixed.
5. **`utilities_coordination`** — do this *after* you have a first-pass
   view from LV electrical, HV electrical, and mechanical piping on what
   new connections they actually need. This section is the literal hub of
   the four-way cluster; treat it as a living document you keep returning
   to, not a one-pass section like the others.

## Risk flags to actually read, not skim

- `earthworks_and_remediation` (**temporary_works, high**) — temporary
  excavation slopes are a distinct design case from the permanent cut/fill
  profile. This is exactly the "permanent design forgets its construction
  stage" failure mode described in `docs/ARCHITECTURE.md`.
- `retaining_structures` (**temporary_works, high**) — a staged/propped
  temporary condition (before permanent props/anchors are in) is often
  *more* critical than the finished wall. Don't let a retaining wall design
  ship without a construction-stage stability check.

## Adapting the skeleton for a real project

```python
from basis_of_design.civils import build_civils_bod_skeleton

bod = build_civils_bod_skeleton(project_reference="PRJ-042")

# Confirm a criterion that was illustrative in the skeleton
for c in bod.flood_risk.criteria:
    if c.name == "Finished floor level freeboard":
        c.value, c.notes = "450", "Confirmed with the LLFA for this watercourse — higher than the 300mm default."

# Mark an exclusion as resolved / no longer applicable, or add a new one
bod.surface_water_drainage_suds.exclusions.append(
    "Attenuation tank adoption — client confirmed private ownership/maintenance, not offered for adoption."
)
```

## Common pitfalls

- `utilities_coordination` names other disciplines by section-name-like
  strings ("electrical_lv", "mechanical_piping") that the dependency graph
  resolves automatically — if you rename a section in another discipline's
  module without checking `integration/graph.py`'s resolution logic, this
  reference could silently point at the wrong thing (see that module's own
  docstring caveat on section-name collisions).
- The Sewers for Adoption edition, current EA climate change allowances,
  and CIRIA reference numbers are all flagged "confirm current" for a
  reason — these are the civils standards most likely to have moved since
  this was written. Check them before quoting a specific figure externally.
