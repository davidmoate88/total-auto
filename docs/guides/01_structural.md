# Structural — working guide

Scoped to **industrial access steelwork** — platforms, walkways, stairs,
ladders, handrails/guard-rails, and the steel frame supporting them — not
multi-storey/occupied buildings (that's explicitly parked, not deleted; see
`docs/ROADMAP.md` if a future project needs it). Spans two standard families
at once: the structural Eurocodes (EN 1990/1991/1993) for the steelwork
itself, and the machinery/access safety standards (EN ISO 14122 series,
under the Machinery Directive) for the access equipment's geometry and
safety requirements.

## Where this sits in the process

Depends **only** on geotechnical (foundation bearing resistance) and an
external temporary works contractor for construction-stage design. Nothing
in this repo loops back into structural — once geotechnical's ground model
and bearing resistance are available, structural can be developed largely
on its own, sequenced right after it. This is the one discipline here that
*isn't* part of the four-way concurrent cluster (see `docs/guides/README.md`)
— don't wait on civils/electrical/mechanical piping to make progress here.

## Working through the nine sections

Roughly three groups, in a sensible working order:

1. **Get the basis right first: `design_standards_and_criteria`.** Design
   working life, consequence class, and imposed load category all flow
   downstream into the member/connection calcs — settle these before
   sizing anything. The multi-storey exclusion lives here too; if a project
   ever needs those elements back in scope, this is the section to revisit.
2. **The load path: `substructure_and_foundations` → `primary_steel_frame`
   → `platforms_and_walkways` → `stairs_and_ladders` → `handrails_and_guardrails`.**
   This mirrors how the structure is actually built — foundations, then
   frame, then the access equipment it carries. `substructure_and_foundations`
   is the one section with a direct interface out (to geotechnical); the
   rest of this chain is mostly internal, standards-driven sizing.
3. **The cross-cutting checks: `structural_integrity_and_robustness`,
   `temporary_works`, `movement_tolerances_and_durability`.** These apply
   across the whole structure rather than to one element — do them once
   the load path above is roughed out, not before.

## Risk flags to actually read, not skim

- `substructure_and_foundations` (**temporary_works, medium**) — foundation
  excavation may need temporary support depending on depth/ground
  conditions; the permanent foundation design doesn't cover this.
- `primary_steel_frame` (**temporary_works, high**) — the frame design
  assumes the complete, fully-braced structure. Intermediate erection
  stages are a genuinely different stability case, and this is flagged
  high for a reason: partially-erected steelwork failures are a real,
  recurring cause of construction accidents.
- `platforms_and_walkways` (**safety, high**) — decking is routinely
  installed before its permanent guard-rails. This is a working-at-height
  risk, not just a design nicety; coordinate temporary edge protection
  explicitly with whoever's actually erecting it.

## Adapting the skeleton for a real project

The values in `structural.py` are illustrative (design working life,
deflection limits, platform loading, guard-rail heights, and so on) — every
one is called out in the module's own docstring as "verify before real use."
`build_structural_bod_skeleton()` returns an ordinary (mutable) pydantic
model, so overriding a value for a real project doesn't mean editing the
source file — it means building the skeleton, then setting what you've
actually confirmed:

```python
from basis_of_design.structural import build_structural_bod_skeleton

bod = build_structural_bod_skeleton(project_reference="PRJ-042")

# Override an illustrative value with a confirmed, project-specific one
for c in bod.platforms_and_walkways.criteria:
    if c.name == "Uniformly distributed load":
        c.value, c.unit, c.notes = "7.5", "kN/m²", "Confirmed with client for laydown use, not just access."

# Record a project-specific assumption once you've actually made one
from basis_of_design.core import Assumption
bod.primary_steel_frame.assumptions.append(
    Assumption(description="Site is not coastal/exposed — standard UK wind terrain parameters confirmed adequate.")
)
```

Regenerate the markdown with `render_basis_of_design()` (or
`python3 -m basis_of_design.structural`) once you've made your edits — the
skeleton isn't a one-shot template, it's meant to be built on in place.

## Common pitfalls

- Don't confuse this discipline's scope with a full building structural
  BoD — if a project genuinely needs floor vibration, lateral sway, roof
  structure, or fire engineering coverage, that's explicitly out of scope
  here (see `design_standards_and_criteria`'s exclusions) and needs
  separate treatment, not a stretched reading of this module.
- The EN ISO 14122 part numbers (platforms/walkways = part 2, stairs/
  stepladders/guard-rails = part 3, fixed ladders = part 4) are populated
  from training knowledge, not verified against current standard texts —
  confirm the exact part/clause before quoting a specific dimension to a
  client or contractor.
