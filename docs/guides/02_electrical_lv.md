# LV electrical — working guide

Scoped to plant/industrial LV distribution (not commercial building
electrical services) — nine sections from design standards through to arc
flash and electrical safety, including hazardous area classification.

## Where this sits in the process

**Part of the four-way concurrent cluster** (civils, LV electrical, HV
electrical, mechanical piping — see `docs/guides/README.md`). This
discipline is arguably the most tightly coupled member of the cluster:
`lv_distribution_and_reticulation` takes its supply origin from HV
electrical's transformer secondary, `hazardous_area_classification` depends
directly on mechanical piping's process fluid data, `earthing_and_bonding`
depends on geotechnical soil resistivity and structural steelwork bonding,
and `utilities_coordination` (civils) is where the new supply connection
itself gets coordinated. Don't try to finish this discipline in isolation —
it genuinely can't be, by design.

## Working through the nine sections

1. **`design_standards_and_criteria` first** — system voltage/frequency and
   the earthing system choice (provisionally TN-S here) ripple through
   everything downstream. The earthing system in particular isn't really
   settled until HV electrical's combined-vs-separate earthing decision is
   made (`hv_earthing_and_touch_step_potential`) — treat this as
   provisional until that's confirmed, not final.
2. **`lv_distribution_and_reticulation`, `earthing_and_bonding`,
   `motor_control_and_switchgear`** — the core distribution design. Motor/
   pump loads specifically wait on mechanical piping's equipment schedule;
   don't finalise MCC sizing before that exists.
3. **`standby_and_backup_power`, `lighting`, `small_power_and_containment`**
   — mostly self-contained once the main distribution is roughed out.
4. **`hazardous_area_classification` — the section to prioritise, not
   defer.** This is the one with the highest-severity risk flag in this
   discipline, and it's a hard blocker: equipment selection anywhere near a
   potentially classified zone should not proceed until this section is
   actually signed off.
5. **`arc_flash_and_electrical_safety` last** — needs the distribution
   design (fault levels, protection settings) to actually be meaningful.

## Risk flags to actually read, not skim

- `earthing_and_bonding` (**temporary_works, medium**) — construction-phase
  temporary supplies routinely precede the permanent earthing/bonding
  being complete and tested. Define the temporary arrangement explicitly;
  don't assume the permanent design's earthing covers it.
- `hazardous_area_classification` (**code_compliance, high**) — this is the
  single highest-stakes flag across all five disciplines' LV/HV/mechanical
  sections: selecting standard (non-ATEX) equipment in a zone that turns
  out to be classified is a fundamental safety non-compliance, not a minor
  revision. Confirm classification is signed off before any equipment
  selection in or near a potentially classified zone — full stop.

## Adapting the skeleton for a real project

```python
from basis_of_design.electrical_lv import build_electrical_lv_bod_skeleton

bod = build_electrical_lv_bod_skeleton(project_reference="PRJ-042")

# Settle the earthing system once HV electrical's decision is actually made
for c in bod.design_standards_and_criteria.criteria:
    if c.name == "Earthing system":
        c.value, c.notes = "TN-S, confirmed separate from HV earthing", "Per BS EN 50522 assessment — see electrical_hv basis of design."

# Once hazardous area classification is actually signed off, resolve the risk
# flag's underlying concern by recording what was confirmed, not by deleting
# the flag (the flag documents that the check was needed, not that it failed).
from basis_of_design.core import Assumption
bod.hazardous_area_classification.assumptions.append(
    Assumption(description="Zone classification signed off 2025-XX-XX by [name] — Zone 2 around the process piping tie-in points only.")
)
```

## Common pitfalls

- The system voltage/earthing criteria in `design_standards_and_criteria`
  are marked provisional for a real reason (they depend on HV electrical's
  own decisions) — don't let "provisional" quietly become "final" just
  because nobody revisited it.
- BS 7671 is amended periodically — the edition/amendment reference here is
  flagged for confirmation in the module docstring for a reason; don't
  quote a specific regulation number to a client without checking it's
  current.
