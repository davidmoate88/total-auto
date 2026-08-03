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
| `calcs/structural/` | Structural calc modules (EN 1992/1993/1995) | **Six modules built** — `beam_capacity.py` (EN 1993-1-1 bending/shear/deflection), `column_capacity.py` (EN 1993-1-1 axial buckling resistance, both principal axes), `beam_column_interaction.py` (EN 1993-1-1 SS6.3.3 combined bending+axial interaction, equations 6.61/6.62 — k-factors are required direct inputs, see below), `bolted_shear_connection.py` (EN 1993-1-8 concentric bolt group shear/bearing), `base_plate.py` (EN 1993-1-8 base plate bearing + HD bolt tension), `deck_grating.py` (BS EN 1991-1-1 imposed loads, elastic bearing-bar stress/deflection check). All verified, all wired into the Streamlit UI via the generic form (see below). Block tearing, base plate bending, and moment connections not yet built |
| `calcs/civil/` | Civil calc modules (drainage, earthworks, retaining structures) | **Six modules built** — `lateral_earth_pressure.py` (Rankine active thrust, both DA1 combinations), `retaining_wall_stability.py` (sliding/overturning/bearing, reusing the first module's active-thrust function and the geotechnical module's DA1 factor sets), `foul_drainage.py` (population-based peak flow, Manning's-equation pipe capacity/self-cleansing check — Sewers for Adoption-based, not Eurocode), `cut_fill_balance.py` (grid-method earthwork volume balance from pasted grid-point data — not a safety check, a cost/logistics one), `surface_water_discharge.py` (practical-minimum discharge check + flow control orifice sizing — takes the permitted discharge rate as a direct input, does not derive it), `slope_stability.py` (Fellenius Method of Slices, both DA1 combinations, slice geometry as a direct input — see below). All verified, all wired into the Streamlit UI. Attenuation volume sizing (needs the FSR/FEH rainfall model — see docs/ROADMAP.md's open items) and highways/pavement calcs not yet built |
| `calcs/electrical_lv/` | LV electrical calc modules | **Six modules built** — `cable_sizing_voltage_drop.py` (BS 7671 Reg 433.1.1 current-carrying capacity check + Appendix 4 voltage drop check, single cable run), `load_schedule_diversity.py` (P/Q real+reactive power aggregation of diversified loads to a maximum demand current, feeding directly into the first module's `design_current_a`), `earth_fault_loop_impedance.py` (BS 7671 Chapter 41 Zs check against the tabulated maximum for automatic disconnection), `arc_flash_ppe_check.py` (PPE category classification from an externally-supplied IEEE 1584 incident energy figure — deliberately does NOT calculate incident energy itself), `earth_electrode_resistance.py` (Dwight's formula, single vertical driven rod earth resistance), `motor_starting.py` (starting current + simplified Ist/Isc voltage dip check against a permissible limit, plus a DOL-threshold risk flag — closes the gap previously skipped per project direction). All verified, all wired into the Streamlit UI. All named `calculations_required` entries for this discipline are now built |
| `calcs/electrical_hv/` | HV electrical calc modules | **Four modules built** — `transformer_sizing.py` (candidate transformer rating checked against LV demand plus a growth margin, HV/LV full-load current — the first cross-discipline calc-to-calc handoff, taking LV demand from `load_schedule_diversity.py`'s output), `protection_grading.py` (IEC 60255-151 IDMT relay operating times, upstream/downstream grading margin check — curve constants embedded directly, unlike this discipline's other modules), `arc_flash_ppe_check.py` (required PPE arc rating vs a practical PPE limit from an externally-supplied incident energy figure — deliberately shaped differently from the LV arc flash module), `substation_earthing_touch_step.py` (Sverak grid resistance + IEEE 80 tolerable touch/step voltage, checked against an externally-supplied actual mesh/step voltage). All verified, all wired into the Streamlit UI. All named `calculations_required` entries for this discipline are now built |
| `calcs/mechanical_piping/` | Mechanical piping calc modules | **Four modules built** — `line_sizing_velocity_check.py` (actual velocity vs the API RP 14E erosional velocity limit and a target velocity range — the fifth and final discipline to get a working calc), `pipe_stress_check.py` (ASME B31.3 sustained stress + thermal expansion stress range check from externally-supplied resultant moments — does not perform flexibility analysis), `ped_pesr_classification_check.py` (PED Article 2(1) scope threshold computed directly, conformity assessment bookkeeping from an externally-determined category), `support_load_schedule.py` (per-support reaction load aggregation, unfactored, for handover to structural — see below). All verified, all wired into the Streamlit UI. All named `calculations_required` entries for this discipline are now built |
| `basis_of_design/` | Discipline basis-of-design shape + civils/structural/LV+HV electrical/mechanical piping, architecture AND detail passes | **All five agreed disciplines fully detailed** — civils, structural, LV electrical, HV electrical, mechanical piping all have criteria/assumptions/exclusions/deliverables populated. The corresponding `calcs/<discipline>/` modules (beyond geotechnical) are being built incrementally |
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

## The Streamlit UI (`app.py`)

`app.py` originally special-cased the one calc that existed (bearing
resistance) with a hand-laid-out form. With four more `calcs/structural/`
modules built, that stopped scaling — `app.py` now discovers every module in
`calcs.registry.CALC_REGISTRY` and builds each one's form generically
(`_field_widget`), rather than hand-writing a form per module. This is the
design principle already stated below ("the app... doesn't change" when a new
discipline is added) actually being followed, not just asserted.

`_field_widget` introspects a pydantic v2 field's annotation, default, and
constraint metadata (`Ge`/`Gt`/`Le`/`Lt`) to pick a widget: `st.selectbox` for
`Literal[...]`, `st.checkbox` for `bool`, `st.number_input` for `int`/`float`
(with `min_value`/`max_value` from `gt`/`ge`/`lt`/`le` where present),
`st.text_input` otherwise. `Optional[...]` fields get a "Set `<field>`?"
checkbox rather than a sentinel value, since a `gt=0` field genuinely has no
safe zero-value to mean "omit this" — the checkbox toggles between
`st.text_input`/`st.number_input`/etc. and passing `None` straight through.

The trade-off: the original bearing-resistance tab's hand-laid-out columns
and expanders (grouping eccentricity/loads together) are gone — every module
now gets one flat form. That's a deliberate scope reduction in favour of
genericity across five (and growing) modules rather than bespoke layout code
per module; nothing stops a later pass adding layout hints to the generic
renderer if the flat form proves annoying in practice.

**Navigation: a searchable catalog.** `app.py` went through two navigation
designs before this one. First, one flat `st.tabs()` row for every module —
broke down once the registry passed ~20 modules (scrolling and hunting for
a specific tab). Then a `st.sidebar.radio` discipline selector scoping each
`st.tabs()` row to ~7 modules — broke down from the other direction once a
single discipline itself grew past a handful of modules (Electrical (LV)
alone is now six): finding one specific calc meant already knowing which
discipline bucket it lived in. The current design (`render_catalog`) drops
grouped navigation entirely in favour of one flat, searchable list: every
`CatalogEntry` (the ground model interpreter — not a `calcs.registry`
module — plus one entry per `CalcModule`) renders as a card with its
name/discipline/description, filtered by a free-text search
(`_filter_entries`, matching name/discipline/description) and/or a
discipline dropdown (`_discipline_sort_index` orders matches so results
still cluster by discipline even though the layout is flat). Selecting a
card's "Open →" button sets `st.session_state["selected_key"]` and reruns;
`main()` branches on whether that key is set to render either
`render_catalog()` or `render_module_detail()` — a single piece of
navigation state where the old design needed two (which discipline, which
tab within it). `CalcModule.discipline` — a required field since the very
first module — is still the only "where does this belong" metadata either
the filter dropdown or the sort order needed; nothing about `_field_widget`,
`render_calc_module_tab`, `_apply_handoffs`, or `render_import_sidebar`
changed across either navigation redesign, because none of them were ever
coupled to how modules get grouped on screen.

**Cross-module handoffs.** Several calc modules are explicitly designed to
consume another module's output — e.g. `load_schedule_diversity.py`'s
maximum demand current feeding `cable_sizing_voltage_drop.py`'s design
current, or `column_capacity.py`/`beam_capacity.py`'s resistances feeding
`beam_column_interaction.py`. Previously only the ground-model-interpreter →
bearing-resistance handoff actually worked in the UI (hand-wired with its
own `bearing_prefill`/`bearing_prefill_version` session-state keys); every
other documented handoff was purely a docstring instruction the user had to
carry between tabs by hand. `CALC_HANDOFFS` in `app.py` now declares each one
as `(source_module_key, source_selector, target_module_key, target_field)`
— `source_selector` is either `"headline"` or a `Term.label` to match
exactly among the source's `result.terms` — and a generic mechanism
(`_apply_handoffs`) pushes the value into a per-target-module prefill store
(`_prefill_store()`/`_prefill_versions()`, replacing the old
bearing-specific pair) after any source module's result is computed. The
ground-model handoff was migrated onto this same generic store rather than
kept as a separate mechanism.

Two Streamlit behaviours had to be worked around together, not separately,
to make this actually work (both reproduced during verification, not
hypothetical):

1. Widgets only apply their `value=` argument the *first* time a given
   widget `key` renders; a later rerun keeps whatever the user last set
   regardless of a changed `value=`. Folding a per-target `prefill_version`
   counter into that module's widget keys forces a genuinely fresh widget
   (and therefore a fresh `value=`) whenever a new prefill arrives — this
   part was already true of the original bearing-specific mechanism.
2. What's new: a handoff's target module isn't guaranteed to render in the
   same script execution as its source — true under the old sidebar+tabs
   design whenever source and target sat in different disciplines (the
   ground-model case never had this problem; it was always tab/discipline
   zero), and now true unconditionally under the catalog, which only ever
   renders ONE module's detail view per run regardless of discipline. A
   target that isn't rendered this run can't pick up a freshly-updated
   prefill store on its own, with no further Streamlit rerun to fix it
   (navigating the catalog is client-side only; it doesn't re-invoke the
   script by itself). `render_calc_module_tab` persists a submitted result
   into `st.session_state["last_result__<key>"]` and calls `st.rerun()`
   immediately after any handoff fires, so the *next* script execution
   starts with an already-current prefill store before the target's
   widgets are ever built — the persisted result is what lets the source
   module's own detail view keep showing its result across that
   self-triggered rerun, since `st.form_submit_button`'s `submitted` flag
   is a one-shot signal that goes back to `False` on the very next run.
   The same rerun-after-handoff result also carries a per-target "Open
   `<target>` →" button (and the ground-model tab's bearing-resistance
   handoff gets the same treatment) — under sidebar+tabs a same-discipline
   target was at least one click away as a sibling tab; under the catalog
   there's no implicit "nearby" module anymore, so the jump has to be
   explicit.

**External data import (`calcs/schema_export.py` + the
fill-calc-inputs-from-drawings skill).** `CALC_HANDOFFS` wires calc-to-calc
data flow inside the app, but the first data entry for a project still comes
from source documents (GA drawings, SLDs, load/cable schedules) outside it.
`calcs/schema_export.py` introspects any `CalcModule`'s pydantic
`input_model` (`model_fields`, unwrapping `Optional[...]` via
`typing.get_origin`/`typing.Union`, treating `PydanticUndefined` as "no
default = required") and emits a JSON schema per module: field `type`
(`literal`/`bool`/`int`/`float`/`str`), `required`, `optional_field`,
`default`, `description`, and, for `literal` fields, `allowed_values`. It has
a CLI (`python3 -m calcs.schema_export --discipline "..." --key ...`, filters
combine as AND) and is exercised directly by `tests/test_schema_export.py`.

This schema is the shared contract between two consumers that would
otherwise need to agree on field names by hand:

- **`.claude/skills/fill-calc-inputs-from-drawings/SKILL.md`** — a Claude
  Code skill (currently scoped to the 9 Electrical (LV)/(HV) modules; see the
  skill file's own "Scope" section) that reads source documents and produces
  a JSON file keyed by module key, each value an object of populated
  `field_name: value` pairs. Its central rule mirrors the calc modules' own
  "flag, don't guess" discipline one level upstream: a field the skill can't
  confidently read from the source document must be omitted from the output
  entirely, never guessed or defaulted — an omitted field just means the
  engineer fills it in by hand, same as if the skill had never run.
- **`app.py`'s `render_import_sidebar()`** — a sidebar "Import extracted data
  (JSON)" expander (rendered first in `main()`, before the catalog/detail
  view is built, so a same-run import is visible immediately rather than
  needing an extra rerun). It parses the uploaded JSON, validates each
  module key via `get_module` and each field name via
  `module.input_model.model_fields`, routes valid fields through the same
  `_set_prefill` helper `CALC_HANDOFFS` uses (so imported values get the same
  widget-key-versioning treatment as a calc-to-calc handoff), and reports
  unknown module keys/fields back to the user rather than silently dropping
  them.

Because both consumers are driven by the same live pydantic models rather
than a separately-maintained field list, there is exactly one source of
truth for "what fields does this module take" — the schema export, the
skill's instructions, and the app's import validation can't drift apart from
each other the way three hand-written copies would.

**The ground model interpreter: multi-stratum profiles.** `render_ground_model_tab`
originally interpreted exactly one `Stratum` per run, wrapped as
`SiteInvestigation(strata=[stratum])`. This was a real accuracy gap, not
just a UI limitation: `interpret_stratum`'s stress-dependent correlations
(the SPT overburden correction factor `Cn`, the CPT phi'/cu correlations)
derive sigma_eff from `overburden_profile_kpa`, which walks `site.strata` --
so a deeper stratum interpreted alone, with nothing above it in that list,
silently understated the weight of everything actually above it on a real
multi-layer site. The `Stratum`/`SiteInvestigation` models
(`calcs/geotechnical/interpretation/models.py`) were already built for a
full layered profile (`strata: list[Stratum]`, validated contiguous, no
gaps/overlaps) and `overburden_profile_kpa`/`interpret_stratum` were already
tested against a genuine multi-layer fixture
(`tests/test_ground_model.py`'s `_multi_layer_site`) -- only the UI had
never been built out to let an engineer enter more than one stratum.

The rework keeps that backend entirely untouched (zero calc-logic changes,
zero new pytest coverage needed) and replaces the single-stratum form with
a build-then-interpret flow, backed by `_gi_strata()` -- a plain list of raw
stratum dicts in `st.session_state["gi_strata"]`, deliberately NOT a list of
already-constructed `Stratum` objects, so JSON-imported and hand-entered
strata share one representation and one parsing point:

- **"Add a stratum"** (`st.form`, matching `render_calc_module_tab`'s
  atomic-submit pattern) captures one stratum's raw name/behaviour/depths/
  unit weight/paste-text and appends it to `_gi_strata()` -- light
  validation only (`base_depth_m > top_depth_m`); the top-depth default
  auto-continues from the previous stratum's base depth, nudging toward a
  contiguous profile without enforcing it up front.
- **"Interpret full profile"** (`_interpret_profile`) is where the real work
  happens: parses every stratum's paste text (same `parse_spt_lines`/
  `parse_cpt_lines`/`parse_lab_lines` the single-stratum flow always used),
  constructs every `Stratum`, builds ONE `SiteInvestigation` from the
  complete list (this is what makes the overburden profile correct), then
  runs `interpret_stratum` once per stratum against that shared site --
  each stratum's own readings, but the FULL site's overburden. Result is
  stashed in `st.session_state["gi_profile_result"]` rather than rendered
  inline, the same persist-across-reruns reason `render_calc_module_tab`
  stashes into `last_result__<key>`: a "push to bearing resistance" click
  below triggers `st.rerun()`, and the derived parameters need to survive
  that restart to still render.
- **Per-stratum push-to-bearing** -- with N strata now possible instead of
  one, each gets its own button
  (`f"Push '{stratum.name}' → open {BEARING_MODULE.name}"`, key suffixed by
  index). Earlier in this same rework a two-click version of this (a
  "Push" button whose success message contained a nested "Open →" button)
  was caught and fixed before shipping: a button rendered only inside
  another button's `if` block is only reachable in the ONE rerun
  immediately following ITS OWN click -- clicking it a run after its parent
  button's condition has gone back to `False` is silently dropped, because
  the code path that would handle it never executes. Setting the prefill
  and calling `st.session_state["selected_key"] = BEARING_MODULE.key` in a
  single click sidesteps the whole class of bug rather than relying on two
  sequential clicks landing in the right runs.

**`fill-ground-model-from-gi-report` + "Import GI-derived strata (JSON)".**
Counterpart to `fill-calc-inputs-from-drawings`, same "flag, don't guess"
contract, aimed at the ground model interpreter instead of a
`calcs.registry` module -- which is exactly why it needed its own skill and
its own import path rather than reusing the electrical one: there's no
`calcs.schema_export` entry for a tool that isn't a registered `CalcModule`,
and the import shape here (`water_table_depth_m` plus a list of stratum
objects) doesn't fit `render_import_sidebar`'s `module_key -> {field:
value}` contract at all. `render_gi_import_expander`/`_import_gi_profile`
live inside `render_ground_model_tab` itself rather than the global sidebar,
so the control only appears where it's relevant. One design choice worth
calling out: a stratum is only importable when all of `Stratum`'s own
required scalar fields (`name`/`behavior`/`top_depth_m`/`base_depth_m`/
`assumed_unit_weight_kn_m3`) are present -- unlike the electrical import,
there's no live per-field form to partially prefill an already-added
stratum into, so "skip this whole stratum, report exactly why, add it by
hand" is the safe fallback rather than inventing a behaviour classification
or a unit weight to make an incomplete entry "work." The skill itself adds
one more layer to the "never guess" discipline beyond `fill-calc-inputs-
from-drawings`: a real GI report usually covers several boreholes/trial pits
with genuinely different stratification, and blending them into one
profile would itself be an invented number, so the skill picks ONE
representative log and states which (and why) in its extraction notes,
rather than averaging boundary depths across logs.

**Three document-intake skills: standards, constraints, foundation/levels
synthesis.** Scoped from an open-ended ask ("build a skill for basis of
design") into four narrower deliverables from one client document dump
(contract, ERs, planning docs, GI, FRA, drainage calcs): a risk register
(user's own XLSX format, not yet provided -- held), a standards register, a
constraints register, and a foundation/levels options synthesis. Built as
separate skills rather than one pipeline, matching this repo's existing
one-skill-one-job pattern, since the four jobs genuinely need different
source-document handling and different output shapes.

- **`.claude/skills/build-standards-register/`** reuses real data already
  in the repo instead of a hand-maintained comparison list: every
  `basis_of_design/*.py` module already declares its discipline's expected
  standards as `Standard` entries (`basis_of_design/core.py`) -- 65+ codes
  across the five disciplines. The skill's Step 1 reads them fresh every
  run (a `grep` one-liner, not a snapshot baked into the skill file, same
  "read live, not remembered" discipline as `fill-calc-inputs-from-
  drawings`'s schema-export step), then classifies every citation found in
  the source documents as expected / not in the baseline / cited in an
  unexpected discipline's document / possibly superseded (only when
  genuinely confident -- a false "this is outdated" claim is exactly the
  kind of invented confidence this skill exists to avoid) / unidentifiable.
  "Not in the baseline" is deliberately not presented as an error -- it may
  be entirely legitimate, just not something this portfolio's disciplines
  have cited before.
- **`.claude/skills/build-constraints-register/`** has no existing model to
  build against (unlike standards) -- it proposes a category structure
  (Planning/Environmental/Ground/Utilities/Access/Legal) explicitly flagged
  in its own text as adjustable, the same way the risk register works from
  a user-supplied format rather than one this skill invents.
- **`.claude/skills/synthesize-foundation-levels-options/`** is the one
  that needed the most explicit scope discussion, because "derive a
  foundation solution from documents" sits close to the exact kind of
  unverified engineering judgment every calc module and skill in this repo
  deliberately avoids producing. Scoped conservatively, by the user's
  explicit choice over a version that would output actual recommended
  values: the skill transcribes what the documents already state (most
  usefully, a GI report's own foundation recommendation section -- real GI
  reports commonly include one, e.g. "piled foundations recommended,
  helical piles preferred, for the reasons stated" -- discovered while
  testing `fill-ground-model-from-gi-report` against a real report) and
  cross-references the specific `calcs/geotechnical/`, `calcs/civil/`, and
  `calcs/structural/` module keys relevant to what was found, rather than
  deriving a foundation type, depth, or level itself. It explicitly flags
  piled foundations as a current gap in `calcs/` (no module exists yet) --
  surfacing that gap rather than silently dropping the cross-reference is
  the whole point when a GI's own recommendation is exactly the case this
  repo can't yet calculate.

## Civils calcs (`calcs/civil/`) and cross-domain DA1 reuse

The first two `calcs/civil/` modules answer `retaining_structures`'s two
`calculations_required` entries and are deliberately paired the same way
`beam_capacity.py`/`column_capacity.py` were: `lateral_earth_pressure.py`
computes Rankine active thrust (both DA1 combinations, mirroring
`bearing_capacity.py`'s own DA1-C1/DA1-C2 structure), and
`retaining_wall_stability.py` checks sliding/overturning/bearing on top of
it. The reuse goes further than the structural pair, though:
`retaining_wall_stability.py` imports `DA1_C1`/`DA1_C2` directly from
`calcs/geotechnical/bearing_capacity.py` — the SAME partial-factor-set
objects, not a second copy of the same numbers — so Design Approach 1 has
exactly one implementation shared across geotechnical and civils, not three
independent reimplementations that could quietly drift apart. It also
imports `rankine_coefficients()` and `_active_thrust_and_lever_arm()` from
`lateral_earth_pressure.py` and calls them directly (recomputing active
thrust from the same characteristic soil parameters under each DA1
combination) rather than accepting a single pre-computed thrust value — the
more rigorous approach, since DA1-C2 factors the SOIL PARAMETERS before
deriving Ka/Pa, not the final force.

The active-thrust resultant itself (`_active_thrust_and_lever_arm`) is
computed by decomposing the pressure diagram into trapezoidal segments at
each breakpoint (top, water table if present, base) — exact for the modelled
piecewise-linear pressure profile (not a numerical approximation), verified
against the classic closed-form triangle (`0.5*Ka*gamma*H^2` at `H/3`) and
rectangular-surcharge-block results by hand in the test suite.

The third civils module, `foul_drainage.py`, is architecturally different
from the retaining-wall pair in one important way: it is NOT Eurocode-based.
UK foul sewer design follows Sewers for Adoption / water company Design and
Construction Guidance, not a BS EN standard, matching
`calcs/civil/README.md`'s own warning that drainage sizing "varies by
sub-discipline more than structural/geotechnical does." It uses Manning's
equation for pipe capacity (a simplified/preliminary substitute for the
Colebrook-White method Sewers for Adoption formally requires) and treats the
peak flow factor and per-capita flow rate as direct inputs with illustrative
defaults rather than derived/tabulated values — see the module's own
docstring for why.

The fourth, `cut_fill_balance.py`, prompted a small, deliberate generic-UI
extension: it takes site-wide grid-point data (existing level, proposed
level, tributary area — one point per line, lenient-paste-parsed the same
way `calcs/geotechnical/interpretation/text_input.py` parses SPT/CPT data,
but with the parsing living inside the module's own `calculate()` rather
than a bespoke tab, since it's a registered `calcs/` module like any other,
not a special-cased one). No previous module had a plain `str` field, so
`app.py`'s generic form fallback rendered it as `st.text_input`
(single-line) — useless for pasting many grid points. Changed the fallback
to `st.text_area` (verified safe: no other registered module has a plain
`str` field, so nothing else's rendering changes). It's also the first
calc module in this repo where an "imbalance" doesn't mean a safety
failure — cut/fill balance is a cost/logistics consideration, so it raises
a `buildability` risk flag rather than `code_compliance` when the
surplus/deficit is large, a deliberate category distinction from every
other module built so far.

The fifth, `surface_water_discharge.py`, answers `surface_water_drainage_suds`'s
"Discharge rate calculation" `CalculationRequirement` — but deliberately
does NOT derive the greenfield/brownfield runoff rate itself (the IH124/ICP
SuDS Manual empirical methods, which need site-specific SAAR/SOIL data from
the FEH webservice and coefficients this author wasn't confident enough in
to embed). `permitted_discharge_rate_l_s` is a required direct input,
per the project owner's explicit direction (computed externally, e.g. via
the FEH webservice, and entered directly). What the module DOES calculate
is the higher-confidence engineering that follows from that rate: a check
against the common LLFA practical minimum (5 l/s), and flow control orifice
sizing via the standard sharp-edged-orifice equation
(`Q = Cd*A*sqrt(2*g*h)`, `Cd=0.61`) — well-established hydraulics, unlike
the empirical runoff-rate methods. The section's OTHER requirement,
"Attenuation volume sizing," needs the FSR/FEH rainfall depth-duration-
frequency model (a distinct empirical dataset, not a formula) and is not
built — tracked as an open item in docs/ROADMAP.md rather than attempted with
unverified figures, per the same "flag, don't guess" discipline as
everywhere else in this repo.

The sixth, `slope_stability.py`, answers `earthworks_and_remediation`'s
"Slope stability check" via Fellenius' (Ordinary) Method of Slices — a
deliberate choice of the simpler, non-iterative method over Bishop's
Simplified Method (which requires solving for the factor implicitly, since
each slice's normal force depends on it). Fellenius is well-verified here
but is KNOWN CONSERVATIVE relative to Bishop's — the module says so
explicitly in every result, and adds an extra warning when the governing
utilisation lands in the 0.9-1.0 "marginal" band specifically because
that's where Fellenius's bias could flip a real PASS into an apparent FAIL.
Reuses `DA1_C1`/`DA1_C2` from `bearing_capacity.py` — the third module to
share that one implementation (after `lateral_earth_pressure.py` and
`retaining_wall_stability.py`). Like `cut_fill_balance.py`, slice geometry
(weight, base angle, base length, pore pressure) is supplied as lenient
pasted text rather than generated from a slope profile and trial slip
circle — that geometry (finding where a circle intersects a ground surface,
computing per-slice depth and base angle) is a substantial computational-
geometry problem in its own right, kept out of scope to avoid embedding it
without independent verification, the same reasoning that kept
`retaining_wall_stability.py`'s self-weight and `base_plate.py`'s effective
area as direct inputs.

The first `calcs/electrical_lv/` module, `cable_sizing_voltage_drop.py`,
answers `lv_distribution_and_reticulation`'s "Cable sizing and voltage drop"
`CalculationRequirement`: BS 7671 Regulation 433.1.1's three-condition
current-carrying capacity check (`Ib<=In<=Iz`, `I2<=1.45*Iz`) plus the
Appendix 4 voltage drop percentage check, for a single cable run. This is
the first discipline outside civils/structural/geotechnical to get a working
calc, and it extends the "flag, don't guess" pattern one level further than
`base_plate.py`/`surface_water_discharge.py`: those modules take one or two
uncertain *values* as direct inputs, but here the entire *source data* —
BS 7671's cable current-rating tables (Appendix 4, e.g. Table 4D1A) and
voltage drop tables (mV/A/m, e.g. Table 4D1B) — is installation-method- and
cable-construction-specific and revised between amendments, so none of it is
embedded; the tabulated current rating (It) and mV/A/m figure are both
required direct inputs. What the module DOES implement independently and
verifiably is the arithmetic BS 7671 applies on top of those tabulated
values: `Iz = It*Ca*Cg*Ci*Cx` correction-factor derating, the three
Regulation 433.1.1 conditions, and the voltage drop percentage against a
project criterion. The protective device's effective operation current
(I2) defaults to `1.45*In` — the standard BS EN 60898/61009 MCB assumption
per BS 7671 Table 3A — if not supplied directly, with a warning; other
device types (e.g. BS 3036 semi-enclosed fuses) need I2 supplied explicitly
since their I2/In ratio is higher.

The second `calcs/electrical_lv/` module, `load_schedule_diversity.py`,
answers the same section's "Load schedule / diversity"
`CalculationRequirement`: aggregates a pasted list of LV loads into one
maximum demand current. The one non-obvious correctness point: loads are
combined as real and reactive power separately (`P_total = sum(Pi)`,
`Q_total = sum(Qi)`, then `S_total = sqrt(P_total^2 + Q_total^2)`), not by
summing each load's current directly — currents at different power factors
aren't in phase with each other, so a naive current sum would misstate the
resultant. `diversity_factor_percent` is a required per-load direct
input (default 100%, no diversity) for the same reason `It`/`mV/A/m` are
direct inputs in the cable sizing module: BS 7671/the IEE On-Site Guide's
diversity allowances (e.g. Table H1) are worked out for standard *domestic*
circuit types, but this BoD is scoped to plant/industrial distribution,
where diversity depends on each load's actual operational duty (e.g. a
standby pump that never runs concurrently with its duty pair can
legitimately carry 0% diversity) — there is no single applicable fixed
table. Same lenient-paste-parsed-inside-`calculate()` pattern as
`cut_fill_balance.py`/`slope_stability.py`. Its headline output (maximum
demand current) is deliberately shaped to be handed straight to
`cable_sizing_voltage_drop.py`'s `design_current_a` (Ib) for the discipline's
main incoming/distribution cable — the first calc-to-calc handoff within a
single discipline in this repo (distinct from the earlier *cross-discipline*
DA1_C1/DA1_C2 reuse between geotechnical and civils).

The third `calcs/electrical_lv/` module, `earth_fault_loop_impedance.py`,
answers `earthing_and_bonding`'s "Earth fault loop impedance calculation"
`CalculationRequirement` and its "Maximum earth fault loop impedance"
`DesignCriterion`: `Zs = Ze + (R1+R2)*temperature_correction_factor`,
checked against the maximum permitted Zs for the protective device's
required disconnection time (BS 7671 Chapter 41). Same "flag, don't guess"
reasoning as `cable_sizing_voltage_drop.py`: the maximum-Zs tables
(41.2–41.5) are device-curve-specific and the conductor resistance-per-length
figures (Appendix 14/Table I1) are size-specific, so both `max_zs_ohms` and
the two resistance-per-km inputs are required direct inputs rather than
embedded. The one exception is the 1.20 temperature correction factor BS
7671 Appendix 14 commonly cites (20°C tabulated/measured resistance →
normal operating temperature) — unlike a size- or device-specific table
value, this is a single, well-established conversion applied uniformly, so
it ships as an overridable default rather than a required input. A failed
Zs check raises a `safety` risk flag rather than `code_compliance` — the
same category `beam_capacity.py` already uses for a structural overstress,
here because an excessive Zs means the protective device may not disconnect
a fault within the required time, a direct shock-risk consequence rather
than a documentation/procedural gap.

The fourth `calcs/electrical_lv/` module, `arc_flash_ppe_check.py`, answers
`arc_flash_and_electrical_safety`'s "PPE category framework" criterion, but
represents a materially different scope decision from every other module in
this repo, worth calling out explicitly: it does NOT calculate arc flash
incident energy. Every other calc module here embeds a formula this author
has high independent-verification confidence in (Manning's equation,
Rankine earth pressure theory, the Fellenius method, Ohm's-law voltage
drop) and flags individual uncertain *values* as required direct inputs.
Arc flash incident energy is different in kind, not degree: the governing
method (IEEE 1584-2018) is a multi-parameter empirical regression with
equipment-class-specific coefficients (electrode configuration, enclosure
size, working-distance exponents) not safely reproducible from memory —
and unlike a failed structural/geotechnical utilisation check, which a
reviewer catches before anyone is exposed to it, a wrong incident energy
number directly sets the PPE a worker wears for live work. That's a real,
immediate injury pathway no other calculation in this repo has, so the
usual "compute the formula, flag one uncertain value" pattern is
deliberately abandoned here: `incident_energy_cal_cm2` itself is the
required direct input, sourced from an external IEEE 1584 study by a
competent person. What the module DOES compute is the safe, well-defined
part downstream of that figure — classification into illustrative PPE
category bands (again direct inputs with illustrative defaults, since NFPA
70E's exact current-edition banding is the same "flag, don't guess"
territory this repo already applies to BS 7671's tables) and a critical
`safety` flag above a dangerous-energy threshold, recommending
de-energised work or additional engineering controls over PPE alone. Motor
starting, the other remaining `lv_distribution_and_reticulation`-adjacent
calc, was explicitly skipped for now per project direction.

The fifth `calcs/electrical_lv/` module, `earth_electrode_resistance.py`,
was prompted by a direct question about coverage: is lightning protection
and earthing actually covered? Lightning protection (BS EN 62305) is
confirmed still entirely out of scope — `earthing_and_bonding`'s exclusions
already state this explicitly, and nothing new was built for it. Earthing
itself, though, had a real gap: `earth_fault_loop_impedance.py` checks a
*circuit's* protective conductor/disconnection time (Zs), not the earth
*electrode* that circuit's protective conductor ultimately connects to.
`earth_electrode_resistance.py` closes that gap for the "main earthing
terminal" scope item, via Dwight's formula
(`R = (rho/(2*pi*L))*(ln(4L/d)-1)`) for a single vertical driven rod — one
of the few genuinely universal, textbook-verified earthing formulae
(reproduced near-verbatim in BS 7430 and IEEE Std 142), unlike this
discipline's other modules where the governing table/method itself is the
uncertain part. Scoped deliberately narrowly: multiple rods in parallel are
explicitly NOT computed (naive division by rod count is wrong — mutual
coupling between nearby electrodes means the true reduction is always less
than proportional, and the correct multi-rod/mesh formulae — Schwarz,
Sunde — aren't something this author has confident, generalisable recall
of), and the module is deliberately NOT wired to
`basis_of_design/electrical_hv.py`'s "Substation earth resistance target"
criterion: a real HV substation earth grid needs a full multi-electrode
mesh design with touch/step potential compliance (BS EN 50522/IEEE 80),
and using this single-rod answer as a stand-in for that would understate
the real design need. `target_earth_resistance_ohms` is a required direct
input, same reasoning as `earth_fault_loop_impedance.py`'s `max_zs_ohms` —
project/system-specific, not a fixed constant.

The sixth `calcs/electrical_lv/` module, `motor_starting.py`, closes the
one calc gap in this discipline that was left open by explicit decision
rather than oversight: `load_schedule_diversity.py`'s own docstring already
flagged "Motor starting current (inrush) is not considered", and
`docs/ROADMAP.md` recorded it as skipped per project direction. Starting
current is `full_load_current_a * starting_current_multiplier`; voltage
dip at the point of connection is a simplified `(I_start/source_fault_current_a)*100`
source-impedance approximation, checked against a permissible dip limit —
the same shape as `transformer_sizing.py`'s required-capacity/utilisation
check, one module earlier in this same discipline's build order. The
"flag, don't guess" line sits at `starting_current_multiplier`, not the
formula: DOL, star-delta, soft-start, and VSD starting each produce a
materially different multiplier for the *same* motor, so unlike
`transformer_sizing.py`'s `growth_margin_percent` (an illustrative default
that's still directionally reasonable if unconfirmed), there is no
sensible default multiplier to fall back on — it's a required direct input
from the motor's own datasheet, same reasoning as
`cable_sizing_voltage_drop.py`'s tabulated cable rating.
`source_fault_current_a` is likewise required rather than derived, mirroring
`protection_grading.py`'s `fault_current_a` ("from a DNO/network fault
level study, not calculated here"). The module also raises an
`assumption_sensitivity` flag when a DOL start is selected for a motor
above `dol_starting_threshold_kw` (illustrative default 5.5kW) — the first
calc in this repo to turn one of its own discipline's plain
`DesignCriterion` values (`motor_control_and_switchgear`'s "Direct-on-line
(DOL) starting threshold") into an actual per-run pass/fail check, rather
than a value only ever displayed in the rendered basis of design. This
closes out all 9 named `calculations_required` entries across both
Electrical (LV) and Electrical (HV).

The sixth `calcs/structural/` module, `beam_column_interaction.py`, closes a
gap flagged since `beam_capacity.py`/`column_capacity.py` were first built:
a member carrying both bending and axial compression at once (a true
"beam-column") needs the EN 1993-1-1 SS6.3.3 interaction check (equations
6.61/6.62), which neither of those single-action modules performs. The
scope decision here parallels `bolted_shear_connection.py`'s `alpha_v`, but
at a larger scale: rather than one uncertain constant, the whole *method*
for deriving SS6.3.3's interaction factors (`kyy`/`kyz`/`kzy`/`kzz`, from EN
1993-1-1 Annex A or B — a multi-case procedure keyed on equivalent uniform
moment factors, section class, and slenderness) is genuinely complex enough
that this author doesn't have confident, generalisable recall of it, so all
four k-factors are required direct inputs. The two governing equations
themselves, by contrast, are simple and consistently documented across
textbooks, so they're embedded with the same confidence as this repo's
other Eurocode formulae — unlike `arc_flash_ppe_check.py`, where almost
nothing safety-relevant was embeddable, here only the *coefficients* are
flagged, not the *equations*. The module consumes `column_capacity.py`'s
`Nb,y,Rd`/`Nb,z,Rd` and `beam_capacity.py`'s `Mc,Rd` directly as inputs —
the first calc-to-calc handoff within structural, mirroring the pattern
`load_schedule_diversity.py`→`cable_sizing_voltage_drop.py` already
established in `calcs/electrical_lv/`. Both `beam_capacity.py`'s and
`column_capacity.py`'s docstrings/warnings, which previously stated the
combined check was simply "not implemented," were updated to point at this
module instead.

The first `calcs/electrical_hv/` module, `transformer_sizing.py`, answers
`transformers`'s "Transformer rating" `DesignCriterion` ("to be confirmed
from the LV load schedule plus diversity") — the first calc built outside
civils/structural/geotechnical/electrical_lv, and the first calc-to-calc
handoff that crosses a *discipline* boundary rather than staying within
one: `lv_demand_kva` is meant to be fed straight from
`calcs/electrical_lv/load_schedule_diversity.py`'s "S total" output, the
same relationship `hv_incoming_supply_and_connection`/`transformers`
already declare as an `Interface` with `electrical_lv` in the BoD, now
backed by an actual data handoff rather than just a documented dependency.
Checks a candidate transformer rating (a direct input — the module does
NOT select a standard preferred kVA size from a manufacturer's range, same
"check, don't derive" reasoning as `surface_water_discharge.py`'s permitted
discharge rate) against LV demand plus a growth margin (also a direct
input with an illustrative default, since the margin is a project/utility
policy figure, not a fixed standard value), and computes full-load current
on both windings via the plain three-phase power triangle
(`I = S/(sqrt(3)*V)`) — physics this repo already has high confidence in,
no table lookups involved. Explicitly out of scope: N-1 parallel-transformer
redundancy sizing and IEC 60076-7 thermal/ambient loading derating, both
genuinely different (and more involved) calculations than a single-unit
nameplate-rating check.

The second `calcs/electrical_hv/` module, `protection_grading.py`, answers
`protection_and_control`'s "Protection discrimination/grading study"
`CalculationRequirement`: IDMT (Inverse Definite Minimum Time) relay
operating times for an upstream/downstream pair, checked for adequate
grading margin. Notably, this is the first `calcs/electrical_hv/` module
where the governing PHYSICS itself is embedded with high confidence rather
than flagged as a direct input -- the IEC 60255-151 operating-time formula
(`t = TMS*k/((I/Is)^alpha - 1)`) and its four standard curve constants
(Standard/Very/Extremely/Long Time Inverse) get the same treatment as
`column_capacity.py`'s Table 6.1 imperfection factors: a small, genuinely
universal lookup embedded directly, not required as input, because these
specific constants are about as consistently reproduced across protection
engineering literature and decades of manufacturer practice as a constant
gets -- unlike BS 7671's installation-method-specific cable tables or IEEE
1584's equipment-class-specific empirical regression, both of which
required the opposite treatment in this discipline's LV counterpart. What
IS genuinely project-specific here -- each relay's pickup current and TMS
(design choices, not universal constants) and the prospective fault
current (from a separate DNO/network fault level study, per
`design_standards_and_criteria`'s own stated criterion) -- are required
direct inputs. Deliberately scoped to ONE relay pair at ONE fault current,
not a full multi-stage study across the fault current range, since the
margin between two different curve shapes/TMS settings isn't necessarily
monotonic with fault current -- the critical grading point checked here
may not be the actual worst case across the full range, and the module
says so explicitly rather than implying full coverage.

The third `calcs/electrical_hv/` module, `arc_flash_ppe_check.py`, answers
`arc_flash_and_hv_safety`'s "HV arc flash calculation method" and "Minimum
PPE category for HV switching" criteria. It shares its LV counterpart's
core reasoning for not calculating incident energy (see that module's
extensive docstring caveat), reinforced here by this discipline's own
criterion note that "not all LV-oriented tools extend cleanly to HV
switchgear" -- incident energy must come from a dedicated HV-specific
study, never extrapolated from an LV assessment. Where this module
deliberately DIFFERS from the LV version -- not just different default
numbers, a genuinely different shape -- is in how it presents the result:
HV incident energies routinely exceed the LV module's illustrative
Category 1-4 banding (topping out around 40 cal/cm^2) entirely, so forcing
an HV finding through that same framework would just report "Dangerous —
exceeds Category 4" across most of the range where real HV results land,
telling a reviewer nothing useful. Instead this module reports the
required PPE arc rating directly (== the incident energy) and checks it
against a practical arc-rated PPE limit (illustrative default 100 cal/cm^2,
roughly the ceiling of commercially available heavy-duty arc-flash
suits) -- above which the finding isn't "specify a higher category," it's
"PPE cannot protect a worker here, use de-energised work or other
engineering controls instead," which is the genuinely different decision a
reviewer needs to make at HV energies. A "PPE required" finding (below the
practical limit but above the burn threshold) also carries `high` severity
here, one step above the LV module's `medium` for the equivalent finding —
a deliberate, explained difference reflecting `arc_flash_and_hv_safety`'s
own existing risk flag that HV arc flash consequences are typically far
more severe than the equivalent LV finding.

The fourth `calcs/electrical_hv/` module, `substation_earthing_touch_step.py`,
answers `hv_earthing_and_touch_step_potential`'s "Touch/step potential
limits" and "Substation earth resistance target" criteria, and is the
clearest example yet in this repo of a single module deliberately splitting
its scope by confidence tier rather than treating a whole method as either
"embed it" or "flag it". IEEE 80 substation earth grid design has two very
different parts: the grid resistance to remote earth (Sverak's simplified
formula) and the tolerable touch/step voltage limits (IEEE 80's
body-resistance-based formulas, `(1000 + k*Cs*rho_s)*constant/sqrt(ts)`)
are both embedded directly, at the same confidence tier as
`earth_electrode_resistance.py`'s Dwight formula and `protection_grading.py`'s
IDMT curve constants — genuinely universal, consistently-reproduced
equations. But the ACTUAL mesh (touch) and step voltage produced by a real
grid depend on IEEE 80's geometric correction factors (Km, Ks, Kii, Kh, the
grid irregularity factor n) — a multi-case empirical procedure in the same
"flag, don't guess" tier as `beam_column_interaction.py`'s Annex A/B
k-factors or IEEE 1584's incident energy model, so those two figures are
required direct inputs from a proper external grid study, never derived
here. The module runs three independent checks (grid resistance, touch
voltage, step voltage), each capable of raising its own critical safety
flag, with the highest utilisation reported as the governing headline — the
same multi-condition/single-governing-headline shape already established
by `cable_sizing_voltage_drop.py`'s three BS 7671 conditions. This
completes every named `calculations_required` entry across
`basis_of_design/electrical_hv.py`.

The first `calcs/mechanical_piping/` module, `line_sizing_velocity_check.py`,
answers `pipe_sizing_and_flow`'s "Line sizing / velocity check"
`CalculationRequirement` — the fifth and final discipline in this repo to
get a working calc. Deliberately scoped to velocity and erosional velocity
only, not pressure drop, even though the `CalculationRequirement` names
both: pressure drop (Darcy-Weisbach with a Colebrook-White/Moody friction
factor) has its own genuinely iterative solution method, distinct enough
from a straightforward algebraic check that folding it in here would mean
doing it half-way, the same reasoning that kept `foul_drainage.py` to
full-bore capacity only. The erosional velocity limit uses API RP 14E's
`Ve=C/sqrt(rho)`, native to imperial units — handled by converting density
to lb/ft^3 via an *exact* physical unit conversion factor (0.062428, not a
recalled formula) so that the ONLY genuinely uncertain, flagged value is
the empirical constant `C` itself (illustrative default 100 for continuous
service), matching this discipline's own criterion that there's no single
project-wide erosional velocity figure. `actual_internal_diameter_mm` is
also a required direct input — ASME B36.10M's pipe schedule dimensional
tables are exactly the kind of standard-text-specific data this repo
doesn't embed, same reasoning as `cable_sizing_voltage_drop.py`'s
tabulated current rating. A velocity outside the illustrative 3-5 m/s
target range (again matching this discipline's own stated criterion)
raises a `buildability` flag rather than `code_compliance` — settling/
fouling risk if too slow, excess pressure drop/noise if too fast, neither
an immediate safety issue the way exceeding the hard erosional limit is.

The second `calcs/mechanical_piping/` module, `pipe_stress_check.py`,
answers `pipe_stress_analysis_and_supports`'s "Pipe flexibility/stress
analysis" `CalculationRequirement`: ASME B31.3's sustained stress (Eq 17)
and thermal expansion stress range (Eq 1a/13) checks. It deliberately does
NOT perform the flexibility analysis itself -- deriving the resultant
moments a piping system's supports/anchors impose at a given point needs a
full 3D stiffness-matrix solve of the actual routed geometry (CAESAR II or
equivalent), not something reducible to a formula, the same reason this
repo doesn't attempt full building-frame structural analysis. It applies
the same split already established by `beam_column_interaction.py`: the
governing stress equations themselves are well-documented and embedded
with full confidence, while the case-specific inputs feeding them --
there, Annex A/B k-factors; here, resultant moments Ma/Mi/Mo/Mt from an
external analysis, plus SIFs (B31.3 Appendix D, fitting-geometry-dependent)
and allowable stresses Sc/Sh (B31.3 Table A-1, material/temperature-
dependent) -- are required direct inputs. Section modulus IS computed
internally from OD and wall thickness (standard hollow-cylinder mechanics,
high confidence, no tables involved) rather than requested as a separate
input, avoiding a class of user error where a supplied Z doesn't actually
match the supplied Do/t.

The third `calcs/mechanical_piping/` module,
`ped_pesr_classification_check.py`, answers `design_standards_and_criteria`'s
"Piping class/category" `DesignCriterion`. It deliberately does NOT derive
the PED/PESR category (SEP, I, II, III) -- PED Annex II sets it via four
*separate* graphical boundary charts (Group 1/2 gas and liquid), each with
its own PS-vs-DN boundary lines, exactly the kind of easy-to-transpose-
between-tables numeric detail this repo's "flag, don't guess" discipline
exists to avoid, and here the stakes are unusually explicit: an incorrect
category could mean skipping required notified body conformity assessment
before a system is placed into service, a genuine legal compliance
failure rather than a design error a reviewer catches downstream. What IS
computed directly, with high confidence, is the PED Article 2(1) scope
threshold itself (`PS not exceeding 0.5 bar` is excluded from the
Directive entirely) -- arguably the single most universally cited figure
in PED, since it's the literal definition of the equipment the Directive
applies to, unlike the category boundary charts. Above that threshold, the
category is a required direct input, and the module does the safe
downstream bookkeeping: whether notified body conformity assessment/CE-
UKCA marking applies, plus a caution when the fluid is Group 1 (dangerous)
that the category must have come from the correct Group 1 table.

The fourth `calcs/mechanical_piping/` module, `support_load_schedule.py`,
answers `pipe_stress_analysis_and_supports`'s "Support load schedule"
`CalculationRequirement` and `supports_structural_and_hazardous_area_interfaces`'s
"Support load handover format" criterion, and completes every named
`calculations_required` entry across `basis_of_design/mechanical_piping.py`.
It's a genuinely different shape from the other three modules — less a
formula-heavy check, more the actual handover artifact, using the same
lenient-paste pattern already established by `cut_fill_balance.py`/
`slope_stability.py` rather than a single-set-of-numbers input model.
Support reactions come from the same external flexibility analysis
(CAESAR II or equivalent) that supplies `pipe_stress_check.py`'s resultant
moments, but the two aren't derived from each other — a stress-check
moment at a point and a reaction force at a support are different
quantities from the same upstream source, not a calc-to-calc handoff the
way `load_schedule_diversity.py`→`cable_sizing_voltage_drop.py` is. Loads
are handed over *unfactored*, matching real handover practice: the
receiving structural engineer combines these with everything else already
acting on that support before applying their own partial factors, the
same reasoning `beam_capacity.py`/`column_capacity.py` take separate
permanent/variable inputs rather than one pre-combined figure. An optional
uniform screening limit gives the module a genuine pass/fail check when a
support capacity is already known, while being explicit in both the
docstring and the field description that it's a single uniform limit
applied to every support, not a per-support capacity lookup — if
different supports end up with different actual steelwork capacities
(the normal case once sizes vary), the governing support this module
reports should be checked against that specific support's real capacity
directly.

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
- No cross-domain UI — `app.py` serves the ground model interpreter plus every
  registered `calcs/` module (auto-discovered from `calcs.registry.CALC_REGISTRY`
  with a form generated from each module's pydantic input model — see
  `app.py`'s docstring), but nothing from `basis_of_design/`, `portfolio/`, or
  `comms/`. That's future work once there's logic behind those models.
