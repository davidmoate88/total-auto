# Architecture

total-auto is organised as independent domain packages, each with its own data
contract, so the system can grow one piece at a time without earlier pieces
needing rework. This doc is the map — what exists, what's stubbed, and how the
pieces are meant to connect once they're all built out.

## Domain map

| Package | Purpose | Status |
|---|---|---|
| `calcs/geotechnical/` | Ground investigation interpretation + EC7 bearing resistance | **Built** — working calc, verified logic, Streamlit UI |
| `calcs/structural/` | Structural calc modules (EN 1992/1993/1995) | Placeholder — README + pattern only |
| `calcs/civil/` | Civil calc modules (drainage, earthworks) | Placeholder — README + pattern only |
| `basis_of_design/` | Discipline basis-of-design shape + civils/structural/LV+HV electrical/mechanical piping skeletons | **All five agreed disciplines built** — civils, structural, LV electrical, HV electrical, mechanical piping. Milestone 1a's architecture pass is complete; detail pass (criteria/assumptions/deliverables, calcs/ modules) is next |
| `portfolio/` | Project portfolio: cost, programme, risk, constraints, contacts, feasibility | Data model only (`models.py`), no logic |
| `comms/meeting_minutes/` | Transcript → structured minutes → actions | Data model + interface stub (`extract_minutes()` raises `NotImplementedError`) |
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
at each current output shape). The detail pass is now under way, one
discipline at a time: **`civils.py`, `structural.py`, `electrical_lv.py`, and
`electrical_hv.py` now have criteria, assumptions, exclusions, and
deliverables populated.** Civils covers survey tolerances, SuDS
discharge/climate-change criteria, flood freeboard, pavement design life,
retaining wall design working life, etc. Structural covers design working
life/consequence class, platform loading and minimum walkway width,
stair/ladder pitch, guard-rail height/load/gap limits, notional horizontal
robustness load, expansion joint spacing and galvanizing coating thickness,
etc. LV electrical covers system voltage/frequency/earthing system, voltage
drop and cable derating ambient, earth fault loop impedance/bonding
conductor sizing, motor starting threshold and enclosure IP rating,
generator changeover/UPS autonomy, lighting levels, hazardous area zone
classification categories, and arc flash study trigger. HV electrical
covers the voltage class (kept explicitly generic, per project direction),
fault level sourced from the DNO connection offer, switchgear topology,
transformer rating tied directly to the LV load schedule, protection
grading margin, HV cable bending radius, touch/step potential basis, and
HV arc flash calculation method — same "verify before real use" caveat as
their standards lists in all four cases, since these are illustrative
UK-practice starting values, not confirmed project- or client-specific
figures. Mechanical piping still has its architecture-pass skeleton only,
pending the same detail treatment — the last of the five. The corresponding
`calcs/<discipline>/` modules (beyond geotechnical) are not yet built for any
discipline.

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

## Intended integration points (not yet wired up)

These are the seams the domains are expected to connect through once they're
built out — noted here so future work doesn't reinvent the shape:

- `portfolio.models.BuildabilityNote.related_calc_reference` — a free-text
  placeholder field meant to reference a specific calc module's report (e.g.
  `"geotech_bearing_resistance_ec7:project-42-footing-3"`), so a project's
  buildability notes can point at the calculation that backs them up.
- `comms.meeting_minutes.models.ActionItem.related_project_reference` and
  `comms.email_triage.models.EmailSummary.related_project_reference` — both
  point at `portfolio.models.Project.reference`, so actions and emails can be
  filed against a specific portfolio project once the portfolio import/dashboard
  exists.
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
