---
name: build-constraints-register
description: Reads a dump of client/project documents (contract, Employer's Requirements, planning documents, GI reports, FRA, drainage calculations, and similar) and produces a constraints register -- every site, planning, environmental, ground, utilities, access, and legal/contractual constraint actually stated in the documents, organised by category with its source and design implication. Use when the user provides a set of project documents and asks for a constraints register, or wants site/project constraints identified and tracked.
---

# Build constraints register

Reads a set of project documents and produces a constraints register: every
constraint on the design or construction that the documents actually
state, organised by category, each traceable back to where it came from.

**No existing model in this repo to build against** (unlike
`build-standards-register`, which reuses `basis_of_design/*.py`'s already-
declared standards). The column structure below is a proposed, sensible
default for a UK engineering/planning context -- adjust it freely if the
user has their own preferred format, the same way `build-risk-register`
works from a format the user supplies directly rather than one this skill
invents.

**The governing rule, same as every other skill in this repo: never
guess.** A constraint belongs in the register because a document actually
states it -- a boundary, a limit, a condition, a restriction, an obligation
-- not because it's the kind of thing "a site like this would probably
have." If a document is silent on something you'd expect it to cover (no
stated flood zone, no stated working hours restriction), that silence is
itself worth noting as an open item (Step 5), not filled in with a typical
assumption.

## Step 1 -- read every document

Use the `Read` tool -- it handles PDFs and images directly. Work through
the whole document set: contract, Employer's Requirements (ERs),
specifications, planning conditions/decision notices and any accompanying
planning statement, GI reports, Flood Risk Assessments (FRA), drainage
calculations, ecological/arboricultural surveys, utility searches, and
anything else supplied. A single constraint is often only fully
interpretable alongside a site plan, a drawing referenced elsewhere in the
same document, or a defined term in the contract -- read the whole set
before writing anything down, the same discipline
`fill-ground-model-from-gi-report` applies to a GI report's cross-
referenced tables and logs.

## Step 2 -- identify constraints, by category

Work through each document looking for statements that actually restrict,
condition, or limit the design/construction -- not general project
description. Suggested categories (use what fits what's actually found;
don't force a constraint into a category it doesn't belong in, and don't
invent entries for categories with nothing stated):

- **Planning** -- conditions attached to a permission/decision notice, use
  class restrictions, height/massing limits, S106 or CIL obligations,
  listed building/conservation area status, Tree Preservation Orders,
  required pre-commencement approvals.
- **Environmental** -- flood zone classification and any stated finished-
  floor-level or attenuation requirement, protected species/habitat
  findings, contamination classification, noise/air quality/lighting
  restrictions.
- **Ground/geotechnical** -- made ground, contamination extent, unexploded
  ordnance risk, mining legacy, groundwater conditions -- anything the GI
  or a desk study states as a design constraint (not the full ground
  model itself, which is `fill-ground-model-from-gi-report`'s job -- this
  is the constraint framing: "piling through X requires Y" rather than the
  stratigraphy itself).
- **Utilities/services** -- existing buried or overhead services and their
  stated clearance/easement requirements, wayleaves, required diversions,
  the HV cable clearance noted in a GI report's fieldwork section, for
  example.
- **Access/logistics** -- site access restrictions, stated working hours,
  abnormal load routing, adjacent land use/occupier constraints during
  construction.
- **Legal/contractual** -- title restrictions, rights of way, party wall
  matters, restrictive covenants, anything the contract itself imposes as
  a constraint on the design (a stated budget/programme ceiling counts
  here if the contract frames it as a hard constraint, not just context).

For each constraint found, record:
- **What it actually says**, close to the source wording rather than
  paraphrased into something more general than what's stated.
- **Source document, and where** -- document name/reference and a page,
  clause, condition number, or section, so a reviewer can go straight to
  it.
- **Which discipline(s) it affects**, if that's clear from the constraint
  itself (a flood zone FFL requirement affects civils and structural; an
  HV cable clearance affects electrical and civils/geotechnical, for
  example) -- leave blank rather than guess if it's genuinely unclear
  which disciplines are affected.

## Step 3 -- note the stated design/programme implication, if any

Some constraints come with their own stated implication (a planning
condition that says "no piling within 5 m of the retained tree"; an FRA
that states "finished floor level must be 300 mm above the 1-in-100-year
plus climate change flood level") -- record that implication as stated.
Don't derive an implication the document doesn't actually state yourself
(e.g. don't calculate what a stated FFL requirement means for a specific
proposed slab level -- that's a design step for the engineer, not
transcription).

## Step 4 -- write the constraints register

A markdown table, grouped by category:

| ID | Constraint | Source | Discipline(s) affected | Stated implication |
|---|---|---|---|---|

`ID` is a short sequential reference per category (e.g. `PLAN-01`,
`ENV-01`, `GEO-01`) so constraints can be referenced elsewhere (a risk
register entry, a design report) without repeating the full description.

Save the register somewhere the user can find it -- ask where they'd like
it if not obvious, otherwise use the project's scratchpad location if one
is configured, or the current working directory with a clear name like
`constraints_register.md`.

## Step 5 -- flag genuine silences and contradictions

Separately from the register table:
- **Contradictions between documents** -- e.g. two documents stating
  different flood zone classifications, or a planning condition that
  appears to conflict with an ER requirement. State both, don't resolve
  which governs.
- **Expected-but-silent gaps** -- something a document of that type would
  normally be expected to state but doesn't (e.g. an FRA with no stated
  finished-floor-level requirement, a contract with no stated working
  hours). Only note genuinely notable gaps, not an exhaustive list of
  every possible constraint category that happens not to apply to this
  site.

## Scope

Any project document set is in scope. Out of scope: assessing whether a
constraint is actually satisfiable by the proposed design (that's a design
review decision, not an extraction task), and deriving a specific design
implication the source document doesn't itself state (see Step 3).
