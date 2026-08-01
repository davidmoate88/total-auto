# HV electrical — working guide

The incoming supply and step-down side of the plant electrical system,
complementing LV electrical. Kept **generic across common industrial HV
voltage classes** (6.6kV/11kV/33kV) rather than fixed to one — the specific
voltage is a per-project decision made once you have a DNO connection offer,
not a discipline-scope decision baked into this module.

## Where this sits in the process

**Part of the four-way concurrent cluster** (civils, LV electrical, HV
electrical, mechanical piping — see `docs/guides/README.md`). HV and LV
electrical are in fact each other's tightest coupling within that cluster:
`transformers` interfaces directly with LV distribution (the transformer
secondary literally is LV's supply origin), and
`hv_earthing_and_touch_step_potential` is where the combined-vs-separate
HV/LV earthing decision gets made — a decision LV electrical's own earthing
section is waiting on. Work these two disciplines together, not sequentially.

## Working through the eight sections

1. **`design_standards_and_criteria` first** — the HV voltage class stays
   deliberately generic in the skeleton, but on a real project this is one
   of the first things to actually pin down (from the DNO connection offer),
   because insulation level, switchgear rating, and cable spec all cascade
   from it.
2. **`hv_incoming_supply_and_connection`** — get the DNO connection
   application moving early; connection point and fault level both come
   from the DNO, not from anything this repo can calculate.
3. **`substations_and_switchgear`, `transformers`** — transformer rating
   can't actually be finalised until LV electrical's load schedule exists
   (see that discipline's `lv_distribution_and_reticulation` section) —
   this is a genuine two-way dependency, not a one-off lookup.
4. **`protection_and_control`, `hv_cabling_and_cable_management`** —
   standards-driven once the switchgear/transformer arrangement is fixed.
5. **`hv_earthing_and_touch_step_potential` — prioritise this alongside
   hazardous area classification in LV electrical.** Both are the two
   highest-stakes sections in the whole electrical scope. This one needs a
   soil resistivity survey (not an assumed value) before it can be signed
   off — get that survey commissioned early, it's on the critical path.
6. **`arc_flash_and_hv_safety` last** — needs the protection study to be
   meaningful, and is explicitly its own study, not an extrapolation from
   the LV arc flash assessment.

## Risk flags to actually read, not skim

- `substations_and_switchgear` (**temporary_works, medium**) — cutting over
  to a new substation is a distinct, carefully sequenced temporary/parallel
  operation with defined outage windows, coordinated with the site's
  Authorised Person regime — not something the permanent switchgear design
  covers on its own.
- `hv_earthing_and_touch_step_potential` (**safety, high**) — combined vs.
  separate HV/LV earthing is safety-critical (risk of a HV earth fault
  transferring dangerous potential onto LV equipment) and must be explicitly
  assessed per BS EN 50522, not assumed by default.
- `arc_flash_and_hv_safety` (**safety, high**) — HV incident energy levels
  are typically far higher than LV. This needs its own dedicated study.

## Adapting the skeleton for a real project

```python
from basis_of_design.electrical_hv import build_electrical_hv_bod_skeleton

bod = build_electrical_hv_bod_skeleton(project_reference="PRJ-042")

# Pin down the voltage class once the DNO connection offer is in hand
for c in bod.design_standards_and_criteria.criteria:
    if c.name == "HV voltage class":
        c.value, c.notes = "11kV", "Confirmed per DNO connection offer dated [date]."

# Record the fault level once the DNO's statement arrives -- this also
# resolves an open item flagged by integration/open_items.py
for c in bod.design_standards_and_criteria.criteria:
    if c.name == "System fault level":
        c.value, c.unit = "250", "MVA"
```

## Common pitfalls

- Don't let "kept generic across voltage classes" become an excuse to leave
  the voltage class unconfirmed past the point where the DNO connection
  offer actually specifies it — generic is the discipline's *starting*
  scope, not a permanent state for a real project.
- HV work often runs under a duty-holder's own Safety Rules / Authorised
  Person regime on top of the published standards — the module docstring
  flags this explicitly; confirm what actually governs for the specific
  network operator/site before assuming the standards list alone is
  sufficient.
