# total-auto

Automation toolkit for running a portfolio-design / head-of-engineering-design role:
engineering calculations across disciplines, project portfolio tracking (cost, time,
buildability, constraints, risk, feasibility), and information flow (emails, meeting
minutes, actions, reminders).

This repo is being built incrementally. See `docs/ARCHITECTURE.md` for the domain map
(what's built vs. scaffolded), `docs/ROADMAP.md` for the full vision and build order,
**`docs/guides/`** for practical guides to actually working through a project
discipline by discipline (start with `docs/guides/README.md`), and
**`docs/HANDOFF.md` first if you're picking this up in Claude Code** — it has the
exact steps and open items from where this was left off.

## Status

**Milestone 1 (current):** Geotechnical spread foundation bearing resistance,
to **EN 1997-1 (Eurocode 7) Annex D, UK National Annex, Design Approach 1** — built
inside a small extensible framework so future disciplines (structural, civil, etc.)
and eventually the wider portfolio/comms tooling slot in the same way. In front of it
sits a **ground model interpreter**: paste SPT/CPT/lab site investigation data per
soil stratum and it derives characteristic design parameters (phi', cu, unit weight)
using established correlations, then hands them straight to the bearing resistance calc.

**All calculations in this repo are intended to be Eurocode-compliant.** Read the
caveat in `calcs/geotechnical/bearing_capacity.py`'s module docstring before relying
on any of this for a real design — the formulae and partial factors were built from
standard geotechnical literature/training knowledge, not by reading the purchased
BS EN 1997-1 standard text directly, and should be checked against the current
standard and National Annex before use.

**Milestone 1a (complete):** worked discipline-by-discipline through a "basis of
design" (BoD) — the document stating scope, standards, criteria, and interfaces for
a discipline, distinct from a `calcs/` module that performs one specific calculation.
All five agreed disciplines are fully built out, architecture AND detail:
`basis_of_design/civils.py`, `structural.py` (scoped to industrial access
steelwork), `electrical_lv.py` (plant/industrial LV distribution including
hazardous area classification), `electrical_hv.py` (incoming supply/substations/
transformers, kept generic across common HV voltage classes), and
`mechanical_piping.py` (process piping, governing code kept generic — both ASME
B31.3 and BS EN 13480 listed). Every section in every discipline now carries real
design criteria, assumptions, exclusions, and deliverables, not just scope/
standards/interfaces — see `docs/examples/` for a generated look at each
discipline's current output. Each also carries risk flags (`core/risk.py`)
wherever a permanent design implies a distinct, riskier construction-stage or
compliance-sequencing condition.

**All criteria values populated in the detail pass are illustrative starting
points from common UK/industry practice, not confirmed project- or
client-specific figures** — every one is flagged for verification in its
module's docstring, the same "verify before real use" caveat applied
throughout this repo.

**Milestone 1b (complete):** with all five disciplines fully detailed, built
`integration/` — a cross-discipline process-flow and orchestration layer
derived entirely from the `Interface` entries the disciplines already
declare (no new dependency information invented). `integration/graph.py`
turns all 33 of those interfaces into one dependency graph and runs cycle
detection over it; the finding: **geotechnical is the one true starting
point, structural can follow independently right after it, but civils,
LV electrical, HV electrical, and mechanical piping form one mutually-
dependent cluster with no valid strict order among them** — they need
iterative/concurrent co-design, not a one-pass pipeline. `integration/
process_state.py` tracks per-project resolution status and derives what's
actually unblocked to work on right now. `integration/open_items.py` scans
every discipline's criteria/assumptions for "to be confirmed"-style pending
inputs (53 found) and wires them directly into `comms.meeting_minutes.
models.ActionItem` — the first of the "Intended integration points" in
`docs/ARCHITECTURE.md` to actually be built. `integration/master_document.py`
stitches the process-flow narrative, the dependency diagram, the open items
register, and all five disciplines' full output into one combined
project-level document — see `docs/examples/master_basis_of_design.md` and
`docs/examples/process_flow_and_open_items.md`.

**Milestone 1d (in progress):** started building the `calcs/<discipline>/` modules
(beyond geotechnical) that the BoD `calculations_required` entries point at, for
structural so far:
- `calcs/structural/beam_capacity.py` — simply-supported steel I/H-section beam
  bending/shear/deflection check to EN 1993-1-1 (UK NA). Bending-dominant only —
  no lateral-torsional buckling, no axial.
- `calcs/structural/column_capacity.py` — cross-section compression resistance
  and flexural buckling resistance (both principal axes) for the same section
  type, to EN 1993-1-1 (UK NA). Pure axial only.
- `calcs/structural/bolted_shear_connection.py` — bolt shear and bearing
  resistance for a concentrically-loaded bolt group, to EN 1993-1-8 (UK NA).
  No block tearing, no connected-ply capacity, no moment/eccentric
  connections. Notably lower-confidence than the beam/column modules on one
  specific constant (Table 3.4's alpha_v) — flagged prominently, and made a
  required direct input rather than a guessed default; see the module
  docstring.
- `calcs/structural/base_plate.py` — concrete/grout bearing utilisation under
  a concentric column base plate, and HD bolt tension utilisation under net
  uplift, to EN 1993-1-8 (UK NA). Effective bearing area and bearing strength
  are direct inputs rather than derived (same "flag, don't guess" reasoning
  as the connection module's alpha_v, applied to the base-plate effective-area
  geometry this time); ties the load path back from `column_capacity.py`'s
  design axial load to the geotechnical bearing resistance interface already
  declared in this section's BoD.

Beam and column together cover `primary_steel_frame`'s "Beam/column member
capacity checks" as two separate `CalculationRequirement` entries in
`basis_of_design/structural.py` (now wired via `calc_module_reference`, the
first real use of that field) — but a member carrying **both** bending and
axial load at once (a true beam-column) needs the EN 1993-1-1 SS6.3.3
interaction check, which neither module performs; that's flagged explicitly in
both modules' docstrings/warnings rather than approximated. The bolted
connection and base plate modules cover "Connection design" and "Base plate /
holding-down bolt design" similarly.
- `calcs/structural/deck_grating.py` — the first `platforms_and_walkways`
  module: elastic bending stress and deflection check for a grating/decking
  bearing bar spanning between primary supports, to BS EN 1991-1-1 imposed
  loads (defaulting to the platforms_and_walkways BoD criteria: 5.0 kN/m² UDL,
  1.5 kN concentrated load) checked via an EN 1993-1-1 elastic stress method
  (not the classification-based method `beam_capacity.py` uses — appropriate
  for thin flat bearing bars, not rolled I/H sections). Shear and the
  concentrated load's spread across bearing bars are not derived — see the
  module docstring.

**All five `calcs/` modules are now wired into the Streamlit UI.** `app.py` no
longer hand-lays-out a form per module — it discovers every module in
`calcs.registry.CALC_REGISTRY` and auto-builds each one's form from its
pydantic input model (widget type chosen from the field's annotation/
constraints; `Optional[...]` fields get a "Set `<field>`?" toggle instead of a
sentinel value). See `docs/ARCHITECTURE.md`'s "The Streamlit UI" section for
the mechanism and a real bug this surfaced (and fixed) in the ground-model →
bearing-resistance prefill handoff: Streamlit widgets ignore a changed
`value=` on reruns unless the widget's `key` also changes, so a second
ground-model interpretation was silently not updating the bearing tab's
pre-filled fields until a prefill-version counter was added to the key.

**First `calcs/civil/` modules built**, answering `retaining_structures`'s
two `calculations_required` entries:
- `calcs/civil/lateral_earth_pressure.py` — Rankine active earth pressure
  coefficient and resultant thrust (both DA1 combinations), accounting for
  water table and surcharge. No wall friction/batter/sloping backfill
  (Rankine's theory only).
- `calcs/civil/retaining_wall_stability.py` — sliding/overturning/bearing
  utilisation for a gravity/cantilever wall, both DA1 combinations. Reuses
  the earth-pressure module's own active-thrust function (recomputing it
  under each combination's factored soil parameters, the more rigorous
  approach) and imports `DA1_C1`/`DA1_C2` directly from
  `calcs/geotechnical/bearing_capacity.py` — one shared Design Approach 1
  implementation across geotechnical and civils, not a second copy of the
  same partial factors. Self-weight and allowable bearing pressure are
  direct inputs — see the module docstring.

See `docs/ARCHITECTURE.md`'s "Civils calcs and cross-domain DA1 reuse"
section for the full picture.

**Third civils module**: `calcs/civil/foul_drainage.py` — population-based
peak foul flow and Manning's-equation full-bore pipe capacity/self-cleansing
velocity check, answering `foul_drainage`'s "Foul flow calculation"
requirement. Unlike the retaining-wall pair, this is NOT Eurocode-based — UK
foul sewer design follows Sewers for Adoption / water company guidance.
Manning's equation is a simplified/preliminary substitute for the
Colebrook-White method formally required for adoptable sewer design; the
peak flow factor and per-capita flow rate are direct inputs with
illustrative defaults. See the module docstring.

**Fourth civils module**: `calcs/civil/cut_fill_balance.py` — grid-method
cut/fill earthwork volume balance from pasted grid-point data (existing
level, proposed level, tributary area per line — the same lenient-paste
pattern as the ground model interpreter's SPT/CPT parsing, but living
inside the module's own `calculate()` since this is a registered
`calcs/` module, not a bespoke UI tab). Answers `earthworks_and_remediation`'s
"Cut/fill balance" requirement. Prompted a small generic-UI fix: no prior
module had a plain `str` field, so `app.py`'s fallback rendered it as a
single-line `st.text_input`, useless for pasting many grid points — changed
to `st.text_area` (verified safe for every other module). Also the first
module where an imbalance isn't a safety failure — it's a cost/logistics
consideration, so it raises a `buildability` risk flag, not
`code_compliance`, a deliberate category distinction from every other
module built so far. See `docs/ARCHITECTURE.md`'s "Civils calcs" section.

**Fifth civils module**: `calcs/civil/surface_water_discharge.py` — answers
`surface_water_drainage_suds`'s "Discharge rate calculation" requirement,
but deliberately does NOT derive the greenfield/brownfield runoff rate
itself (the IH124/ICP SuDS Manual methods need FEH-webservice-sourced
SAAR/SOIL data and empirical coefficients not confidently reproducible from
memory). `permitted_discharge_rate_l_s` is a required direct input, per
explicit project direction — compute it externally (e.g. via the FEH
webservice) and enter it directly. What the module DOES calculate: a check
against the common LLFA practical minimum (5 l/s) and flow control orifice
sizing via the standard sharp-edged-orifice equation, both well-established
hydraulics. The section's other requirement, "Attenuation volume sizing"
(needs the FSR/FEH rainfall depth-duration-frequency model — a distinct
empirical dataset, not a formula), is **not built** — tracked as an open
item in `docs/ROADMAP.md` rather than attempted with unverified figures.

**Sixth civils module**: `calcs/civil/slope_stability.py` — answers
`earthworks_and_remediation`'s "Slope stability check" via Fellenius'
(Ordinary) Method of Slices, both DA1 combinations, reusing `DA1_C1`/
`DA1_C2` from `bearing_capacity.py` (the third module to share that one
implementation). Deliberately Fellenius, not Bishop's Simplified Method —
simpler (non-iterative) and well-verified here, but KNOWN CONSERVATIVE
relative to Bishop's; every result says so, with an extra warning when the
governing utilisation lands in the 0.9–1.0 band where that bias matters
most. Slice geometry (weight, base angle, base length, pore pressure) is
supplied as lenient pasted text, same pattern as `cut_fill_balance.py` —
this module does not generate slices from a slope profile and trial slip
circle (a substantial computational-geometry problem kept out of scope,
same reasoning as `retaining_wall_stability.py`'s self-weight and
`base_plate.py`'s effective area being direct inputs).

**First electrical (LV) module**: `calcs/electrical_lv/cable_sizing_voltage_drop.py`
— answers `lv_distribution_and_reticulation`'s "Cable sizing and voltage
drop" requirement: BS 7671 Regulation 433.1.1 current-carrying capacity
check (`Ib<=In<=Iz`, `I2<=1.45*Iz`) and the Appendix 4 voltage drop
percentage check, for a single cable run. Continues the "flag, don't guess"
pattern from `base_plate.py`/`surface_water_discharge.py`: BS 7671's cable
current-rating and mV/A/m tables are extensive, installation-method-specific,
and revised between amendments, so this module does NOT embed them — the
tabulated current rating (It) and voltage drop figure (mV/A/m) are required
direct inputs, looked up from the current Appendix 4 tables or manufacturer
data. What the module DOES implement independently is the arithmetic BS 7671
applies on top of those tabulated values: correction-factor derating, the
three-condition Regulation 433.1.1 check, and the voltage drop percentage
against a project criterion (default 5%, matching this discipline's own BoD
criterion). The device's effective operation current (I2) defaults to
1.45×In (a standard BS EN 60898/61009 MCB assumption) if not supplied
directly. First module in a new discipline (`calcs/electrical_lv/`), and
the first calc built outside civils/structural/geotechnical.

**Second electrical (LV) module**: `calcs/electrical_lv/load_schedule_diversity.py`
— answers `lv_distribution_and_reticulation`'s "Load schedule / diversity"
requirement: aggregates a pasted list of LV loads into one maximum demand
current. Correctly combines loads as real/reactive power (`P`/`Q` summed
separately, then `S=sqrt(P²+Q²)`), not by summing individual load currents
directly — currents at different power factors aren't in phase, so naive
summation would misstate the resultant. Same "flag, don't guess" reasoning
as the cable sizing module, one level up: BS 7671/the IEE On-Site Guide give
worked diversity allowances for standard *domestic* circuit types, but this
BoD is scoped to plant/industrial distribution, where diversity depends on
each load's actual operational duty (duty vs. standby plant, intermittent
vs. continuous process equipment) — no single fixed table applies, so
`diversity_factor_percent` is a required per-load direct input (default
100%, i.e. no diversity, the conservative starting point). Same lenient-
paste-parsed-inside-`calculate()` pattern as `cut_fill_balance.py`/
`slope_stability.py`. Its output (maximum demand current) is designed to
feed directly into `cable_sizing_voltage_drop.py`'s `design_current_a` (Ib)
for the main incoming/distribution cable — the first calc-to-calc handoff
within a single discipline in this repo.

**Third electrical (LV) module**: `calcs/electrical_lv/earth_fault_loop_impedance.py`
— answers `earthing_and_bonding`'s "Earth fault loop impedance calculation"
requirement (BS 7671 Chapter 41, automatic disconnection of supply):
`Zs = Ze + (R1+R2)*temperature_correction_factor`, checked against the
maximum permitted Zs for the protective device/disconnection time. Same
"flag, don't guess" pattern as the first module: BS 7671's maximum-Zs tables
(41.2–41.5) are device-curve-specific, and conductor resistance-per-length
figures (Appendix 14/Table I1) are size-specific, so both are required
direct inputs rather than embedded. The one constant this module DOES apply
by default is the 1.20 temperature correction factor BS 7671 Appendix 14
commonly cites (20°C tabulated/measured resistance → normal operating
temperature) — a single well-established conversion, not a proprietary
table lookup, so it ships as an overridable default rather than a required
input, unlike It/mV/A/m/max Zs. A failed Zs check raises a `safety` risk
flag (not `code_compliance`, unlike every other failed-utilisation flag in
`calcs/electrical_lv/` and `calcs/civil/` so far) — an excessive Zs means
the protective device may not disconnect a fault fast enough, a direct
shock-risk consequence rather than a documentation/procedural one, matching
how `beam_capacity.py` already uses the same category for a structural
overstress.

**Fourth electrical (LV) module**: `calcs/electrical_lv/arc_flash_ppe_check.py`
— answers `arc_flash_and_electrical_safety`'s "PPE category framework"
requirement, but with a materially different scope decision from every
other module in this repo: it does NOT calculate arc flash incident energy.
Every other calc here embeds a formula this author has high independent-
verification confidence in and flags individual uncertain *values* as
direct inputs; arc flash incident energy is different in kind, not degree —
the governing method (IEEE 1584-2018) is a multi-parameter empirical
regression with equipment-class-specific coefficients not safely
reproducible from memory, and unlike a failed structural/geotechnical check
(caught by review before anyone is exposed to it), a wrong incident energy
figure directly sets the PPE a worker wears for live work — a real,
immediate injury pathway no other calc in this repo has. So
`incident_energy_cal_cm2` itself is the required direct input (from an
external IEEE 1584 study), and the module does only the safe, well-defined
part downstream of that: classifies it into illustrative PPE category bands
(again direct inputs with illustrative defaults, since NFPA 70E edition
details are exactly the "flag, don't guess" territory this repo already
treats BS 7671 tables the same way) and raises a critical `safety` flag
above a dangerous-energy threshold, recommending de-energised work over
PPE alone. This completes the "circuit design trio plus safety" set for
`calcs/electrical_lv/` at four modules, skipping motor starting for now per
project direction.

The natural next step is more `calcs/<discipline>/` modules (block tearing,
base plate bending, the beam-column interaction check, highways/pavement
civils calcs, motor starting for electrical LV, HV electrical calcs,
mechanical piping calcs) plus independent verification of every
illustrative value flagged throughout the detail passes.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the web UI
streamlit run app.py

# Run a calc engine directly (no UI)
python3 -m calcs.geotechnical.bearing_capacity
python3 -m calcs.structural.beam_capacity
python3 -m calcs.structural.column_capacity
python3 -m calcs.structural.bolted_shear_connection
python3 -m calcs.structural.base_plate
python3 -m calcs.structural.deck_grating
python3 -m calcs.civil.lateral_earth_pressure
python3 -m calcs.civil.retaining_wall_stability
python3 -m calcs.civil.foul_drainage
python3 -m calcs.civil.cut_fill_balance
python3 -m calcs.civil.surface_water_discharge
python3 -m calcs.civil.slope_stability
python3 -m calcs.electrical_lv.cable_sizing_voltage_drop
python3 -m calcs.electrical_lv.load_schedule_diversity
python3 -m calcs.electrical_lv.earth_fault_loop_impedance
python3 -m calcs.electrical_lv.arc_flash_ppe_check

# Print the discipline dependency graph as a Mermaid flowchart
python3 -m integration.graph

# Print the open items / RFI register
python3 -m integration.open_items

# Print the full combined project basis of design (all five disciplines + process flow)
python3 -m integration.master_document

# Run tests
pytest
```

## Project layout

```
total-auto/
├── app.py                          # Streamlit UI — ground model interpreter + auto-generated form per calcs.registry module
├── core/
│   ├── calc_base.py                # Shared interfaces: CalcInput, CalcResult, registry
│   ├── report.py                   # Turns a CalcResult into a review-ready markdown sheet
│   └── risk.py                     # DesignRiskFlag — shared risk-flagging shape (calcs + BoDs)
├── calcs/
│   ├── registry.py                 # Central list of registered calc modules
│   ├── geotechnical/                # BUILT — see below
│   │   ├── bearing_capacity.py     # EN 1997-1 Annex D bearing resistance, UK NA DA1
│   │   └── interpretation/
│   │       ├── models.py           # SPT/CPT/lab test/stratum/site data models
│   │       ├── correlations.py     # SPT/CPT -> phi'/cu empirical correlations
│   │       ├── ground_model.py     # Pools data per stratum -> characteristic design params
│   │       └── text_input.py       # Lenient line-based paste parser (not free-form NLP)
│   ├── structural/                  # FIVE MODULES BUILT — see below
│   │   ├── beam_capacity.py        # EN 1993-1-1 simply-supported beam bending/shear/deflection check, UK NA
│   │   ├── column_capacity.py      # EN 1993-1-1 axial buckling resistance check (both axes), UK NA
│   │   ├── bolted_shear_connection.py  # EN 1993-1-8 concentric bolt group shear/bearing check, UK NA
│   │   ├── base_plate.py           # EN 1993-1-8 base plate bearing + HD bolt tension check, UK NA
│   │   └── deck_grating.py         # BS EN 1991-1-1 loads, EN 1993-1-1 elastic bearing-bar check, UK NA
│   ├── civil/                        # SIX MODULES BUILT — see below
│   │   ├── lateral_earth_pressure.py   # Rankine active earth pressure, EN 1997-1 UK NA DA1
│   │   ├── retaining_wall_stability.py # Sliding/overturning/bearing check, EN 1997-1 UK NA DA1
│   │   ├── foul_drainage.py            # Peak foul flow + Manning's equation pipe capacity check
│   │   ├── cut_fill_balance.py         # Grid-method cut/fill earthwork volume balance
│   │   ├── surface_water_discharge.py  # Discharge rate check + flow control orifice sizing
│   │   └── slope_stability.py          # Fellenius Method of Slices, EN 1997-1 UK NA DA1
│   └── electrical_lv/                # FOUR MODULES BUILT — see below
│       ├── cable_sizing_voltage_drop.py    # BS 7671 Reg 433.1.1 + Appendix 4 voltage drop check
│       ├── load_schedule_diversity.py      # P/Q load aggregation -> maximum demand current
│       ├── earth_fault_loop_impedance.py   # BS 7671 Ch.41 Zs check for automatic disconnection
│       └── arc_flash_ppe_check.py          # PPE category classification (incident energy is a direct input, not derived)
├── basis_of_design/                  # Discipline basis-of-design shape + skeletons
│   ├── core.py                     # Shared BasisOfDesignSection shape
│   ├── render.py                   # Renders any discipline's sections to markdown
│   ├── civils.py                   # BUILT — 9-section civils skeleton
│   ├── structural.py               # BUILT — 9-section skeleton, scoped to industrial access steelwork
│   ├── electrical_lv.py            # BUILT — 9-section skeleton, plant/industrial LV distribution; four calcs wired (cable sizing/voltage drop, load schedule/diversity, earth fault loop impedance, arc flash PPE category)
│   ├── electrical_hv.py            # BUILT — 8-section skeleton, HV incoming supply/substations/transformers
│   └── mechanical_piping.py        # BUILT — 9-section skeleton, process piping (ASME B31.3 / BS EN 13480 generic)
├── integration/                      # BUILT — cross-discipline process flow / orchestration
│   ├── graph.py                    # Interface() entries -> dependency graph, cycle detection, Mermaid
│   ├── process_state.py            # Per-project resolution status -> what's unblocked/blocked
│   ├── open_items.py                # Pending-input extraction -> ActionItem conversion
│   └── master_document.py          # Combined project-level document (all 5 disciplines + process flow)
├── portfolio/                       # DATA MODEL ONLY — Project/Portfolio contract, no logic
├── comms/
│   ├── meeting_minutes/             # DATA MODEL + interface stub (extract_minutes()); ActionItem now also produced by integration/open_items.py
│   └── email_triage/                # DATA MODEL + interface stub (triage_inbox())
├── tests/
│   ├── test_bearing_capacity.py    # Validates EC7 Annex D factors/DA1 partial factors
│   ├── test_beam_capacity.py       # Validates EN 1993-1-1 classification, Mc,Rd/Vpl,Rd, deflection
│   ├── test_column_capacity.py     # Validates EN 1993-1-1 classification, Nc,Rd/Nb,Rd, buckling curves
│   ├── test_bolted_shear_connection.py  # Validates EN 1993-1-8 shear/bearing resistance arithmetic
│   ├── test_base_plate.py          # Validates EN 1993-1-8 base plate bearing / HD bolt tension arithmetic
│   ├── test_deck_grating.py        # Validates bearing bar tributary load, stress, and deflection arithmetic
│   ├── test_lateral_earth_pressure.py   # Validates Rankine Ka/Kp and active thrust decomposition
│   ├── test_retaining_wall_stability.py # Validates sliding/overturning/bearing arithmetic
│   ├── test_foul_drainage.py       # Validates peak flow generation and Manning's equation arithmetic
│   ├── test_cut_fill_balance.py    # Validates grid-method volume arithmetic and paste parsing
│   ├── test_surface_water_discharge.py  # Validates orifice sizing arithmetic
│   ├── test_slope_stability.py     # Validates Fellenius method arithmetic and paste parsing
│   ├── test_cable_sizing_voltage_drop.py  # Validates BS 7671 Reg 433.1.1 conditions and voltage drop arithmetic
│   ├── test_load_schedule_diversity.py    # Validates P/Q load aggregation and paste parsing
│   ├── test_earth_fault_loop_impedance.py # Validates Zs = Ze+(R1+R2)*factor arithmetic and utilisation check
│   ├── test_arc_flash_ppe_check.py        # Validates PPE category banding and dangerous-energy flagging
│   ├── test_correlations.py        # Validates SPT/CPT correlation functions
│   ├── test_ground_model.py        # Validates multi-layer overburden + parameter pooling
│   ├── test_text_input.py          # Validates the paste-format parser
│   ├── test_basis_of_design.py     # Validates all five discipline BoD skeletons + risk flags
│   └── test_integration.py         # Validates the dependency graph, cycle detection, open items, master document
└── docs/
    ├── ARCHITECTURE.md             # Domain map, design principles, integration points
    ├── ROADMAP.md                  # Full vision and build order
    ├── HANDOFF.md                  # Start here if continuing in Claude Code
    ├── examples/                    # Generated output samples per discipline + combined
    └── guides/                      # Practical "how to actually work through this" guides
        ├── README.md                # Index + recommended reading/working order
        ├── 00_geotechnical.md       # The one working calc — run it, read its output
        ├── 01_structural.md        # Clean chain: depends only on geotechnical
        ├── 02_civils.md            # Four-way concurrent cluster (with the next three)
        ├── 02_electrical_lv.md
        ├── 02_electrical_hv.md
        └── 02_mechanical_piping.md
```

## Design principles

- **One calc = one self-contained module.** Each calc module exposes a pydantic input
  model, a `calculate()` function, and a result model with every intermediate term kept
  (not just the final answer) — because engineering output needs to be checkable, not
  just correct.
- **Every result can produce a review sheet.** `core/report.py` turns any calc result
  into a markdown calculation sheet (inputs, method, working, result, references) —
  the same shape a checker/approver would expect on a real project.
- **The UI is a thin layer.** `app.py` just discovers registered calc modules and
  renders a form + result for whichever one is selected. Adding a new discipline means
  adding a new module + registering it — the app and report generator don't change.

## Continuing this project

This was started in a Cowork session without direct access to the `total-auto` GitHub
repo (private repo, no network path from that sandbox). To continue in Claude Code:

1. Get this code onto your machine — either pull it via the Claude desktop app's
   device bridge from this session, or have it delivered as files/zip.
2. `git remote add origin git@github.com:davidmoate88/total-auto.git`
3. If the GitHub repo is empty: `git push -u origin main`.
   If it already has content: pull first and merge/rebase this history in.
4. From there, everything works as an ordinary local git repo — Claude Code, your own
   editor, or a future Cowork session can all keep working on it.
