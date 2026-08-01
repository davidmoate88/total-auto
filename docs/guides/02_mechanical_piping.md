# Mechanical piping — working guide

Industrial/plant process piping — nine sections from design standards
through to the final cross-discipline interface section. Governing piping
code is kept **deliberately generic**: both ASME B31.3 and BS EN 13480 are
listed rather than one being chosen, since which one actually governs is a
project/client/jurisdiction decision, not a discipline-scope one.

## Where this sits in the process

**Part of the four-way concurrent cluster** (civils, LV electrical, HV
electrical, mechanical piping — see `docs/guides/README.md`). This
discipline is the one that reaches into the other three the most: it
interfaces with structural (pipe rack/support loads), electrical LV
(hazardous area classification and trace heating), and civils (buried
routing and utilities). It also depends on an external `process` input this
repo deliberately doesn't model — line sizing and pressure/temperature
design conditions have to come from process data/P&IDs you bring in, not
from anything generated here.

## Working through the nine sections

1. **`design_standards_and_criteria` first** — governing code, design
   pressure/temperature, and piping category all cascade from process data.
   If you don't have process data yet, this section (and most of what
   follows) is genuinely blocked, not just under-filled — check
   `integration.process_state` rather than guessing at placeholder numbers.
2. **`pipe_sizing_and_flow`** — needs the same process data. Erosional
   velocity and pressure drop limits are calculated per line, not set once
   for the whole project.
3. **`pipe_stress_analysis_and_supports`** — this is where the interface
   with structural becomes concrete: support loads calculated here are
   literally an input to structural's steelwork design. Don't finalise this
   section without coordinating support locations with structural first.
4. **`material_selection_and_corrosion`, `valves_and_specialty_items`,
   `flanges_gaskets_and_bolting`** — standards-driven once line class/
   pressure rating is fixed from the first two sections.
5. **`pressure_testing_and_inspection`** — carries the highest-severity risk
   flag in this discipline (below); don't leave this to the end just
   because it feels like a late-stage activity.
6. **`insulation_and_heat_tracing`** — interfaces directly with LV
   electrical (trace heating is an LV small-power item, and any trace
   heating in a classified zone needs BS EN 60079-30 compliance).
7. **`supports_structural_and_hazardous_area_interfaces` last, and
   revisited continuously** — this section exists specifically to force
   the structural and hazardous-area coordination checks, not as a normal
   one-pass section. Treat it the same way you treat civils'
   `utilities_coordination` — a living record you keep returning to.

## Risk flags to actually read, not skim

- `pipe_stress_analysis_and_supports` (**temporary_works, medium**) —
  pipework is often erected in spans before its permanent supports are all
  in, or temporarily supported/blinded during tie-ins. The completed stress
  analysis doesn't cover this construction-stage condition.
- `pressure_testing_and_inspection` (**safety, high**) — hydrotest/pneumatic
  testing is itself a hazardous activity (stored energy, test rig/blind
  flange failure) separate from the system's normal operating risk. Define
  test method, pressure, duration, and exclusion zone explicitly before
  construction — don't leave this to whoever's on site that day.
- `supports_structural_and_hazardous_area_interfaces` (**code_compliance,
  high**) — mirrors LV electrical's hazardous area risk exactly, at the
  piping/electrical boundary: don't finalise equipment selection for
  anything electrical associated with piping before classification is
  actually signed off.

## Adapting the skeleton for a real project

```python
from basis_of_design.mechanical_piping import build_mechanical_piping_bod_skeleton

bod = build_mechanical_piping_bod_skeleton(project_reference="PRJ-042")

# Settle the governing code once the client/jurisdiction is actually known
for c in bod.design_standards_and_criteria.criteria:
    if c.name == "Governing piping code":
        c.value, c.notes = "ASME B31.3", "Client is US-headquartered and specified ASME throughout the site."

# Record process data once it exists -- resolves several open items at once
for c in bod.design_standards_and_criteria.criteria:
    if c.name == "Design pressure":
        c.value, c.unit = "10.5", "barg"
```

## Common pitfalls

- Don't let the "kept generic — list both" governing code decision drift
  into actually using both codes' requirements interchangeably on the same
  line — pick one per project/line and be explicit about which, since the
  two codes' factors (hydrotest multiplier, NDT extent) aren't identical.
- The `process` interface (P&IDs, flow data, fluid properties) is the one
  input in this whole repo that's deliberately never generated here —
  don't try to back-derive it from a piping calc; it has to come in as a
  real input, same as the DNO connection offer does for HV electrical.
