# Architecture

total-auto is organised as independent domain packages, each with its own data
contract, so the system can grow one piece at a time without earlier pieces
needing rework. This doc is the map — what exists, what's stubbed, and how the
pieces are meant to connect once they're all built out.

This is the *technical* map. For practical guidance on actually working
through a real project discipline by discipline — what order, what to watch
for, worked examples of overriding the illustrative skeleton values — see
`docs/guides/` instead, starting with `docs/guides/README.md`.

## Domain map

| Package | Purpose | Status |
|---|---|---|
| `calcs/geotechnical/` | Ground investigation interpretation + EC7 bearing resistance | **Built** — working calc, verified logic, Streamlit UI |
| `calcs/structural/` | Structural calc modules (EN 1992/1993/1995) | **Two modules built** — `beam_capacity.py` (EN 1993-1-1 bending/shear/deflection) and `column_capacity.py` (EN 1993-1-1 axial buckling resistance, both principal axes). Both verified, neither wired into the Streamlit UI. Combined bending+axial (SS6.3.3) and connection design (EN 1993-1-8) not yet built |
| `calcs/civil/` | Civil calc modules (drainage, earthworks) | Placeholder — README + pattern only |
| `basis_of_design/` | Discipline basis-of-design shape + civils/structural/LV+HV electrical/mechanical piping, architecture AND detail passes | **All five agreed disciplines fully detailed** — civils, structural, LV electrical, HV electrical, mechanical piping all have criteria/assumptions/exclusions/deliverables populated. The corresponding `calcs/<discipline>/` modules (beyond geotechnical) are next |
| `integration/` | Cross-discipline dependency graph, resolution-state tracking, open-items extraction, and the combined master document | **Built** — dependency graph derived from the 33 `Interface` entries already declared across the five disciplines (44 sections); one discipline-level cycle detected (civils/electrical_lv/electrical_hv/mechanical_piping). See below. |
| `portfolio/` | Project portfolio: cost, programme, risk, constraints, contacts, feasibility | Data model only (`models.py`), no logic |
| `comms/meeting_minutes/` | Transcript → structured minutes → actions | Data model + interface stub (`extract_minutes()` raises `NotImplementedError`); `ActionItem` now also produced directly by `integration.open_items.open_items_as_action_items()` |
| `comms/email_triage/` | Inbox summarization/prioritisation | Data model + interface stub (`triage_inbox()` raises `NotImplementedError`), gated on a connector |
| `core/` | Shared calc framework (input/result models, registry, report generator, risk flagging) | Built, used by `calcs/geotechnical/` |

## Risk flagging (`core/risk.py`)

A shared `DesignRiskFlag` shape (category, severity, description, trigger,
recommended action) is used by both `calcs/` modules (`CalcResult.risk_flags`)
and `basis_of_design/` sections (`BasisOfDesignSection.risk_flags`) — one
mechanism, not a bespoke one per domain. It's distinct from
`portfolio.models.Risk`: a `DesignRiskFlag` is raised automatically at the
point a calculation or BoD section is generated (an "a person should look at
this" signal); a `Risk` is a project-level register entry a person tracks
over time. The intended (not yet wired up) workflow is that flags get
reviewed and the ones that matter get promoted into a project's `Risk`
register — the same pattern as `BuildabilityNote.related_calc_reference`.

`temporary_works` is a first-class category rather than folded into "other",
because it's a specific, recurring failure mode worth naming: a design gets
fully worked up for its permanent, completed condition, and the
construction-stage condition — often more onerous (an unpropped excavation, a
retaining wall before its permanent props are in, steelwork before its
bracing is complete, working at height before guard-rails are fitted) — never
gets a second look unless something forces it. Both `civils.py` (earthworks,
retaining structures) and `structural.py` (substructure excavation, primary
frame erection, platform installation sequence) now flag this explicitly
where it applies; `calcs/geotechnical/bearing_capacity.py` also raises a
`temporary_works` flag for its own founding-depth excavation, and a
`code_compliance` flag when the governing DA1 combination fails its
utilisation check — proving the mechanism works for an actual calculation,
not just BoD skeletons.

## Basis of design (`basis_of_design/`)

A basis of design is the document stating what standards, criteria, and
assumptions a discipline's design/calculations work to — distinct from a
`calcs/` module (which performs one specific calculation). `basis_of_design/core.py`
defines the shared shape every discipline reuses: a `BasisOfDesignSection` carries
scope, applicable standards, design criteria, assumptions, exclusions, interfaces
with other disciplines, required calculations, and deliverables. `render.py`
turns any discipline's sections into one markdown document.

`civils.py` is the first discipline built on this shape — nine sections agreed
directly with the project owner (site conditions, earthworks, foul drainage,
surface water/SuDS, flood risk, highways/access, external works, utilities
coordination, retaining structures), each pre-populated with scope, a starter
list of applicable UK standards, and known cross-discipline interfaces.

`structural.py` is the second, scoped specifically to **industrial access
steelwork** (platforms, walkways, stairs, ladders, handrails/guard-rails, and
their supporting steel frame) rather than multi-storey/occupied-building
structures — that scope was explicitly narrowed by the project owner, with
building-specific elements (floor vibration, lateral stability/sway, roof
structure, fire engineering) parked rather than deleted. This discipline spans
two standard families at once: the structural Eurocodes (EN 1990/1991/1993)
for the steelwork itself, and the machinery/access safety standards
(principally the EN ISO 14122 series, under the Machinery Directive / UK
Supply of Machinery (Safety) Regulations) for the access equipment's geometry
and safety requirements — see `structural.py`'s docstring for the specific
parts and the same "verify before use" caveat as the geotechnical module.

`electrical_lv.py` is the third, scoped to plant/industrial LV distribution
(consistent with the access-steelwork/mechanical-piping context, not
commercial building services): design standards and criteria, LV distribution
and reticulation, earthing and bonding, motor control and switchgear, standby/
backup power, lighting, small power and containment, hazardous area
classification (ATEX/DSEAR, BS EN 60079 series — confirmed as relevant to this
portfolio), and arc flash/electrical safety.

`electrical_hv.py` is the fourth, covering the incoming supply and step-down
side that `electrical_lv.py` draws from: design standards and criteria, HV
incoming supply and connection, substations and switchgear, transformers
(interfacing directly with LV distribution), protection and control, HV
cabling, HV earthing and touch/step potential (a distinct section from LV's
earthing and bonding — governed by BS EN 50522 and ENA EREC S34, since
substation earthing has its own touch/step potential criteria and the
combined-vs-separate HV/LV earthing decision is itself safety-critical), and
arc flash/HV safety. Kept generic across common industrial HV voltage classes
(6.6kV/11kV/33kV) rather than fixed to one, per project direction.

`mechanical_piping.py` is the fifth and last, scoped to industrial/plant
process piping: design standards and criteria (governing piping code kept
generic — both ASME B31.3 and BS EN 13480 listed, per project direction),
pipe sizing and flow, pipe stress analysis and supports (interfacing with
`structural.py` for support steelwork loads), material selection and
corrosion, valves and specialty items, flanges/gaskets/bolting, pressure
testing and inspection, insulation and heat tracing (interfacing with
`electrical_lv.py` for trace heating), and a final cross-cutting section —
supports/structural interface/hazardous area interface — that exists
specifically to force the same equipment-vs-classification sequencing check
already flagged in the LV electrical module, at the piping/electrical boundary.

For all five, criteria, assumptions, and deliverables were initially left
empty — architecture before detail (see docs/examples/ for a generated look
at each current output shape). **The detail pass is now complete for all
five disciplines** — `civils.py`, `structural.py`, `electrical_lv.py`,
`electrical_hv.py`, and `mechanical_piping.py` all have criteria,
assumptions, exclusions, and deliverables populated. Civils covers survey
tolerances, SuDS discharge/climate-change criteria, flood freeboard, pavement
design life, retaining wall design working life, etc. Structural covers
design working life/consequence class, platform loading and minimum walkway
width, stair/ladder pitch, guard-rail height/load/gap limits, notional
horizontal robustness load, expansion joint spacing and galvanizing coating
thickness, etc. LV electrical covers system voltage/frequency/earthing
system, voltage drop and cable derating ambient, earth fault loop
impedance/bonding conductor sizing, motor starting threshold and enclosure
IP rating, generator changeover/UPS autonomy, lighting levels, hazardous
area zone classification categories, and arc flash study trigger. HV
electrical covers the voltage class (kept explicitly generic, per project
direction), fault level sourced from the DNO connection offer, switchgear
topology, transformer rating tied directly to the LV load schedule,
protection grading margin, HV cable bending radius, touch/step potential
basis, and HV arc flash calculation method. Mechanical piping covers the
governing code (kept explicitly generic — both ASME B31.3 and BS EN 13480),
design pressure/temperature/category sourced from process data, erosional
velocity and sustained stress allowable, corrosion allowance and MDMT, valve
pressure class, flange/gasket/bolting selection, hydrotest pressure factor
and NDT extent, personnel-protection insulation trigger temperature, and the
support-load-handover basis for its cross-discipline interface section —
same "verify before real use" caveat as every standards list, since these
are illustrative practice starting values, not confirmed project- or
client-specific figures. The corresponding `calcs/<discipline>/` modules
(beyond geotechnical) are not yet built for any discipline — that, plus
independent verification of every illustrative value flagged throughout the
detail passes, is the natural next piece of work.

## Process flow and cross-discipline integration (`integration/`)

Once all five disciplines had a full basis of design, the next question was
no longer "what does discipline X say" but "how does this all fit together —
what has to happen before what, and how do the five separate documents
become one coherent view of a project". `integration/` answers that without
inventing any new domain knowledge: it's built entirely by introspecting the
`Interface` entries every discipline module already declares.

- **`integration/graph.py`** — walks all 44 sections across the five
  disciplines and turns their 33 `Interface(with_discipline=...)` entries
  into a directed dependency graph. `with_discipline` is used inconsistently
  in the source modules (sometimes a whole discipline, sometimes a specific
  section name, sometimes an external actor like "process" or "architectural"
  that isn't modelled here at all) — `_resolve_target()` normalises all
  three into one of four node kinds (`discipline`, `section`, `calc`,
  `external`). `find_discipline_cycles()` runs Tarjan's strongly-connected-
  components algorithm over the collapsed discipline-level graph, and
  `to_mermaid()` renders the same view as a diagram.

  **The actual finding**, not asserted but derived from the graph:
  geotechnical (the one built calc) is the one true starting point, nothing
  depends back on it. Structural depends only on geotechnical (plus an
  external contractor for temporary works) and nothing loops back into it —
  it can be sequenced right after geotechnical and developed independently.
  But **civils, electrical_lv, electrical_hv, and mechanical_piping form one
  mutually-dependent cluster** — each references at least one of the others
  (utilities coordination, hazardous area classification, transformer/LV
  supply origin, buried pipe routing) and the references loop back round.
  There is no valid strict order among those four; they need iterative,
  concurrent co-design, and pretending otherwise would just be wrong. This
  mirrors how these disciplines are actually coordinated on a real project —
  the graph just makes it explicit instead of leaving it as tribal knowledge.

- **`integration/process_state.py`** — `ProjectProcessState` tracks a
  per-project resolution status (`not_started` / `in_progress` / `resolved`)
  against any node in the graph (a section, the geotechnical calc, or an
  external input). `unblocked_sections()` / `blocked_sections()` derive what
  can actually be worked on right now vs. what's stuck and specifically on
  what, from that state plus the graph — this is the "orchestration" layer:
  it doesn't run anything itself, it tells you what's able to run.
  `progress_summary()` gives a per-discipline section-count-by-status view.
  Nothing here is a persistence layer (see "What deliberately hasn't been
  built yet" below) — it's an in-memory model a caller populates and queries
  within a session, same as every other model in this repo.

- **`integration/open_items.py`** — every section's `criteria`/`assumptions`
  written during the detail pass is scanned for pending-input language
  ("to be confirmed", "pending", "provisional", etc.) and collected into a
  single `OpenItem` register (53 found as of the detail pass, spanning all
  five disciplines) — turning scattered notes like "to be confirmed from the
  LV load schedule" into one list instead of five separate documents read by
  eye. `open_items_as_action_items()` converts these directly into
  `comms.meeting_minutes.models.ActionItem` — the first of the "Intended
  integration points" below to actually be wired rather than just noted.

- **`integration/master_document.py`** — `render_process_flow_summary()`
  produces the dependency-order narrative + Mermaid diagram + open items
  register on its own; `render_master_basis_of_design()` wraps that with all
  five disciplines' full basis-of-design output into one combined
  project-level document (see `docs/examples/master_basis_of_design.md` and
  `docs/examples/process_flow_and_open_items.md`).

## Design principles

1. **Data contract before logic.** Every domain gets a `models.py` (pydantic)
   defining its shape first. `portfolio/` and `comms/*` currently exist as
   contracts only — this is intentional scaffolding, not unfinished work
   pretending to be finished. It means the next build session can write logic
   against a stable, already-reviewed shape instead of designing data models
   and business logic simultaneously.

2. **One calc = one self-contained module**, following `core/calc_base.py`'s
   `CalcModule` pattern: pydantic input model, `calculate()` function, `CalcResult`
   with every intermediate term kept. `calcs/registry.py` is the single place new
   disciplines get wired into the UI.

3. **Eurocode compliance is explicit and flagged, not assumed.** Every calc
   states its governing code + National Annex, and any formula/factor the
   author isn't independently certain of is called out in the module docstring
   and result warnings rather than presented as settled fact (see
   `calcs/geotechnical/bearing_capacity.py`'s Ngamma caveat for the pattern).

4. **Characteristic values flow downstream, partial factors are applied at the
   point of design use.** The ground model interpreter only ever produces
   characteristic phi'/cu/unit weight; DA1 partial factors are applied inside
   the bearing resistance calc. Keep this separation when building further
   calc modules — don't let a data-interpretation layer bake in design-stage
   assumptions.

## Intended integration points

Most of these seams are still just noted for future work — but one is now
actually wired, not just planned:

- **Wired:** `integration.open_items.open_items_as_action_items()` turns the
  open items register directly into `comms.meeting_minutes.models.ActionItem`
  instances, with `related_project_reference` set when a project reference is
  supplied. This is the first real connection between two previously-separate
  domains in this repo.
- `portfolio.models.BuildabilityNote.related_calc_reference` — a free-text
  placeholder field meant to reference a specific calc module's report (e.g.
  `"geotech_bearing_resistance_ec7:project-42-footing-3"`), so a project's
  buildability notes can point at the calculation that backs them up. Not
  wired yet.
- `comms.meeting_minutes.models.ActionItem.related_project_reference` and
  `comms.email_triage.models.EmailSummary.related_project_reference` — both
  point at `portfolio.models.Project.reference`, so actions and emails can be
  filed against a specific portfolio project once the portfolio import/dashboard
  exists. Not wired yet (open-items-derived ActionItems can already carry
  this field — see above — but nothing yet reads it back into a `Project`).
- A future top-level `total_auto/` (or similar) package could own cross-domain
  operations (e.g. "show me every open risk and action item for project X"),
  once there's more than one domain with real data to join across. Not created
  yet — premature until portfolio/comms have actual logic behind them.

## What deliberately hasn't been built yet

- No database / persistence layer — everything is in-memory pydantic models.
  The right persistence choice (flat files, SQLite, something else) is easier
  to pick once real usage patterns exist.
- No auth/multi-user considerations — this is a single-user tool for now.
- No cross-domain UI — `app.py` currently only serves the geotechnical tools.
  A portfolio/comms UI is future work once there's logic behind those models.
