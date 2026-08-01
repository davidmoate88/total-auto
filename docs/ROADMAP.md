# Roadmap

The long-term goal (from the original brief): a toolkit covering as much of a
"head of project design" role as can be sensibly automated — engineering review,
portfolio tracking, and information/communication flow — with everything else made
as efficient as possible.

## Milestone 1 — Engineering calculation framework (in progress)

- [x] Core framework: calc input/result models, registry pattern, markdown report
      generator.
- [x] First module: geotechnical spread foundation bearing resistance, reworked to
      EN 1997-1 (Eurocode 7) Annex D with UK NA Design Approach 1 (originally built
      as a classic Meyerhof/global-factor-of-safety calc, then superseded — **all
      calcs in this repo are meant to be Eurocode-compliant going forward**).
- [x] Ground model interpreter: SPT/CPT/lab test data -> characteristic phi'/cu/unit
      weight per stratum, using established correlations (Peck-Hanson-Thornburn,
      Liao-Whitman, Stroud, Kulhawy-Mayne) and a simplified "cautious estimate"
      characteristic-value rule consistent with EN 1997-1 §2.4.5.2. Feeds straight
      into the bearing resistance calc.
- [ ] Free-form report-excerpt reading: the current text_input.py is a lenient
      *structured paste* parser (depth/N-value lines etc.), not an NLP reader of
      prose report excerpts — genuinely free-text input is better handled by having
      the excerpt read directly and translated into the paste format, rather than a
      regex trying to extract numbers from natural language.
- [ ] Second geotechnical calc (e.g. settlement, or retaining wall) to prove the
      framework generalises within a discipline — also to EC7 (Annex C for
      retaining structures, etc.).
- [ ] First structural calc module, to the relevant Eurocode (EN 1992 concrete /
      EN 1993 steel / EN 1995 timber depending on what's needed first).
- [ ] PDF export of the review sheet (currently markdown only).
- [ ] Independent verification of the Annex D formulae/DA1 partial factors used in
      `bearing_capacity.py` against the actual current BS EN 1997-1 standard text
      and UK National Annex — flagged as an open item in the module's own docstring.
- [x] Shared risk-flagging mechanism (`core/risk.py`'s `DesignRiskFlag`), wired into
      both `CalcResult` and `BasisOfDesignSection`, with a first-class
      `temporary_works` category. Retrofitted into `bearing_capacity.py` (founding
      depth -> temporary_works flag; failed utilisation -> critical code_compliance
      flag) and into the civils/structural BoD skeletons wherever a permanent design
      genuinely implies a distinct, riskier construction-stage condition.

## Milestone 1a — Discipline basis of design (complete)

Agreed approach: work through each discipline's basis of design one at a time,
each split into its "necessary elements" first as an all-encompassing
structural skeleton (scope + standards + interfaces per element), with the
detailed criteria/calculation content filled in afterwards, in Claude Code.
Order agreed: **civils → structural → LV electrical → HV electrical →
mechanical piping**.

- [x] Shared `BasisOfDesignSection` shape + markdown renderer (`basis_of_design/core.py`, `render.py`).
- [x] Civils basis of design skeleton — 9 sections agreed: site & existing
      conditions, earthworks & remediation, foul drainage, surface water
      drainage/SuDS, flood risk, highways & access, external works &
      pavements, utilities coordination, retaining structures. Each has scope,
      a starter list of applicable UK standards (flagged for verification,
      same caveat as the geotechnical module), and known cross-discipline
      interfaces; criteria/assumptions/deliverables left empty for the detail pass.
- [x] Structural basis of design skeleton — scope explicitly narrowed to
      **industrial access steelwork** (platforms, walkways, stairs, ladders,
      handrails/guard-rails, supporting steel frame), not multi-storey/occupied
      buildings — that's parked, not deleted. 9 sections: design standards &
      criteria, substructure & foundations, primary steel frame, platforms &
      walkways, stairs & ladders, handrails & guard-rails, structural integrity
      & robustness, temporary works, movement/tolerances/durability. Spans both
      the structural Eurocodes (EN 1990/1991/1993) and the machinery/access
      safety standards (EN ISO 14122 series, Machinery Directive) — see
      `structural.py`'s docstring for the standards-verification caveat.
- [x] LV electrical basis of design skeleton — scoped to plant/industrial LV
      distribution (not commercial building electrical services), consistent
      with the civils/structural scope. 9 sections: design standards &
      criteria, LV distribution & reticulation, earthing & bonding, motor
      control & switchgear, standby/backup power, lighting, small power &
      containment, hazardous area classification (ATEX/DSEAR, BS EN 60079
      series — confirmed relevant to this portfolio), arc flash & electrical
      safety. Flags temporary works risk on earthing/bonding (construction-
      phase temporary supplies) and a code_compliance risk on hazardous area
      classification (area classification must precede equipment selection).
- [x] HV electrical basis of design skeleton — 8 sections: design standards &
      criteria, HV incoming supply & connection, substations & switchgear,
      transformers (interfacing with LV distribution), protection & control,
      HV cabling & cable management, HV earthing & touch/step potential
      (distinct from LV earthing/bonding — BS EN 50522, ENA EREC S34), and
      arc flash & HV safety. Kept generic across common industrial HV voltage
      classes (6.6kV/11kV/33kV) per project direction, rather than fixed to
      one. Flags temporary works risk on substation cutover/energisation
      sequencing, and safety risk on the combined-vs-separate HV/LV earthing
      decision and on HV arc flash needing its own dedicated study (not
      inherited from an LV assessment).
- [x] Mechanical piping basis of design skeleton — 9 sections: design
      standards & criteria (governing code kept generic — both ASME B31.3 and
      BS EN 13480 listed, per project direction), pipe sizing & flow, pipe
      stress analysis & supports, material selection & corrosion, valves &
      specialty items, flanges/gaskets/bolting, pressure testing & inspection,
      insulation & heat tracing, and a final supports/structural interface/
      hazardous area interface section. Flags temporary_works risk on pipe
      stress analysis & supports (temporary support during erection), a high
      safety risk on pressure testing & inspection (hydrotest is itself a
      hazardous activity), and a high code_compliance risk on the final
      section (mirrors the LV electrical hazardous-area-classification-must-
      precede-equipment-selection risk, at the piping/electrical boundary).
      This completes all five disciplines in the agreed order.
- [ ] Multi-storey/occupied-building structural elements (floor vibration,
      lateral stability/sway, roof structure, fire engineering) — parked per
      project owner's direction; revisit if a future project needs them.
- [x] Detail pass, civils — every section now carries illustrative design
      criteria (survey tolerances, discharge rate/climate change allowance,
      freeboard, pavement design life, etc.), working assumptions, exclusions,
      and deliverables, on top of the architecture-pass scope/standards/
      interfaces. Values are drawn from common UK practice, not confirmed
      project-specific figures — same "verify before real use" caveat as the
      standards lists, called out explicitly in `civils.py`'s docstring.
      Fixed a real rendering bug found while generating the updated example
      doc: a `DesignCriterion` with a value but no unit rendered the literal
      string `"None"` after it (`render.py`'s criteria formatting assumed
      `unit` was always set).
- [x] Detail pass, structural — every section now carries illustrative design
      criteria (design working life/consequence class, deflection limits and
      steel grade, platform loading and minimum walkway width, stair/ladder
      pitch, guard-rail height/load/gap limits, notional horizontal
      robustness load, expansion joint spacing and galvanizing thickness,
      etc.), working assumptions, exclusions, and deliverables, on top of the
      architecture-pass scope/standards/interfaces. Same illustrative-values
      caveat as civils — confirmed in `structural.py`'s updated docstring.
      The multi-storey/occupied-building exclusion (the original scope pivot)
      is retained and explicitly re-tested to confirm it survives the detail
      pass, not just the architecture pass.
- [x] Detail pass, LV electrical — every section now carries illustrative
      design criteria (system voltage/frequency/earthing system, voltage drop
      and cable derating ambient, earth fault loop impedance/bonding
      conductor sizing, DOL starting threshold and enclosure IP rating,
      generator changeover time and UPS autonomy, illuminance levels and
      emergency lighting duration, socket circuit rating and containment
      fill factor, zone classification categories, arc flash study trigger),
      working assumptions, exclusions, and deliverables. Same
      illustrative-values caveat as civils/structural. The hazardous area
      classification standards/risk flag (the project-specific addition to
      this discipline) are retained and re-tested to confirm they survive
      the detail pass.
- [x] Detail pass, HV electrical — every section now carries illustrative
      design criteria (HV voltage class kept explicitly generic, system
      fault level sourced from the DNO connection offer, switchgear
      topology, transformer rating tied to the LV load schedule/vector
      group/cooling class, protection grading margin, cable bending
      radius, touch/step potential basis, HV arc flash calculation method),
      working assumptions, exclusions, and deliverables. Same
      illustrative-values caveat as the other three disciplines done so far.
      The "kept generic across voltage classes" scope decision and the
      cross-discipline transformer/LV-load-schedule interface are retained
      and re-tested to confirm they survive the detail pass.
- [x] Detail pass, mechanical piping — every section now carries illustrative
      design criteria (governing code kept explicitly generic, design
      pressure/temperature/piping category sourced from process data,
      erosional velocity and target liquid velocity, sustained stress
      allowable and support spacing, corrosion allowance and MDMT, valve
      pressure class and actuation default, flange rating/gasket
      type/bolting material, hydrotest pressure factor and NDT extent,
      personnel-protection insulation trigger temperature, and the
      support-load-handover/coordination-review basis for the final
      cross-discipline section), working assumptions, exclusions, and
      deliverables. Same illustrative-values caveat as the other four
      disciplines. The "keep generic — list both governing codes" decision
      is retained and re-tested to confirm it survives the detail pass.
      **This completes the detail pass across all five agreed disciplines.**
- [ ] Build the corresponding `calcs/<discipline>/` modules referenced by
      each section's `calculations_required` entries — deferred to Claude
      Code per the project owner's direction; not started for any discipline
      beyond geotechnical. With the detail pass now complete for all five
      disciplines, this (plus independent verification of every "illustrative
      value" flagged throughout the detail passes against actual current
      standard texts/project requirements) is the natural next piece of work.

## Milestone 1b — Cross-discipline process flow & integration layer (complete)

With all five disciplines' basis of design fully detailed, the next question
raised was no longer "what does discipline X say" but "how does this all fit
together — what order do the inputs/outputs actually need to happen in, and
how do five separate documents become one coherent project view". Built as
a new `integration/` package, entirely derived from data already declared in
`basis_of_design/` (no new domain knowledge invented):

- [x] **Dependency graph** (`integration/graph.py`) — every `Interface`
      entry across all 44 sections (33 of them) turned into one directed
      graph, with automatic resolution of `with_discipline` referring to a
      whole discipline, a specific section, or an external actor not
      modelled in this repo (process, architectural, contractor). Includes
      Tarjan's SCC algorithm for discipline-level cycle detection and a
      Mermaid flowchart renderer.
- [x] **The actual dependency finding** (not asserted, derived): geotechnical
      is the one true starting point (nothing depends back on it);
      structural depends only on geotechnical and can be sequenced right
      after it, independently; but **civils, electrical_lv, electrical_hv,
      and mechanical_piping form one mutually-dependent cluster** with no
      valid strict order among them — they need iterative/concurrent
      co-design, not a one-pass pipeline. This matches how these
      disciplines are actually coordinated on a real project; the graph
      just makes it explicit.
- [x] **Resolution-state tracking** (`integration/process_state.py`) —
      `ProjectProcessState` tracks not_started/in_progress/resolved per
      graph node; `unblocked_sections()`/`blocked_sections()` derive what's
      actually workable right now vs. stuck (and on what) from that state.
      Not a persistence layer — in-memory, same as every other model here.
- [x] **Open items / RFI register** (`integration/open_items.py`) — scans
      every section's criteria/assumptions for pending-input language ("to
      be confirmed", "pending", "provisional", etc.) and collects them into
      one list (53 found across all five disciplines) instead of five
      separate documents read by eye. `open_items_as_action_items()` wires
      this directly into `comms.meeting_minutes.models.ActionItem` — the
      first of docs/ARCHITECTURE.md's "Intended integration points" to
      actually be built, not just noted.
- [x] **Combined master document** (`integration/master_document.py`) — one
      project-level document stitching the process-flow narrative, the
      Mermaid diagram, the open items register, and all five disciplines'
      full basis of design output together (see
      `docs/examples/master_basis_of_design.md` and
      `docs/examples/process_flow_and_open_items.md`).
- [x] 13 new tests (`tests/test_integration.py`) covering graph construction,
      cycle detection (including that structural is correctly excluded from
      the cycle), unblock/block derivation, open items extraction/
      conversion, and the combined document.

## Milestone 2 — Meeting minutes → actions

- [ ] Ingest a transcript (text file to start).
- [ ] Extract structured minutes: attendees, topics, decisions.
- [ ] Extract actions with owner + due date.
- [ ] Reminder mechanism (initially: exportable task list; later: scheduled nudges).

## Milestone 3 — Project portfolio dashboard

- [ ] Data model for a project: cost, time/programme, buildability notes, constraints,
      risks, contacts, feasibility status.
- [ ] Import from spreadsheet trackers.
- [ ] Portfolio-level view: status across all live projects, flagged risks/constraints.

## Milestone 4 — Information flow (email / comms triage)

- [ ] Connector to inbox (Outlook/Gmail) once available.
- [ ] Summarize + prioritize incoming project emails.
- [ ] Draft responses for routine items.

## Design decisions log

- **Framework over one-off scripts**: every calc module follows the same
  input/calculate/result/report shape so the eventual dashboard and report tooling
  work uniformly across disciplines, instead of bespoke code per calc.
- **Streamlit for the UI**: fastest way to get a real usable interface without
  committing to a heavier web stack before the shape of the full tool is known. Easy
  to replace later if the project grows into something needing a proper frontend.
- **Markdown reports first, PDF later**: markdown is enough to prove the "review-ready
  output" pattern; PDF export is a formatting layer on top, not a redesign.
- **Eurocode compliance is a hard requirement, not a nice-to-have**: every calc module
  going forward targets the relevant Eurocode part + UK National Annex (confirmed as
  the governing jurisdiction). Where a formula/factor can't be verified with high
  confidence against the actual standard text in this environment, that uncertainty
  is surfaced explicitly (module docstring + result warnings), not hidden — see
  `bearing_capacity.py` for the pattern (specifically the Ngamma factor caveat).
- **Ground parameters are "characteristic", partial factors are applied downstream**:
  the interpretation layer (SPT/CPT/lab -> phi'/cu/unit weight) only ever produces
  characteristic values; DA1 partial factors are applied inside the bearing
  resistance calc itself. This keeps the EC7 "characteristic vs design value"
  separation architecturally explicit rather than muddled together in one function.
- **Basis of design is a separate artifact from a calc module**: `basis_of_design/`
  captures scope/standards/criteria/interfaces/deliverables for a whole discipline;
  `calcs/<discipline>/` performs one specific calculation. A `CalculationRequirement`
  in a BoD section can reference a `calcs/` module by key once it exists
  (`calc_module_reference`), but the BoD doesn't perform calculations itself.
- **Architecture before detail, explicitly, per discipline**: each discipline's BoD
  is built as an all-encompassing skeleton first (every section named, scoped, with
  known standards/interfaces) before any section gets criteria/assumptions/deliverable
  detail filled in. This was an explicit project-owner decision, not a shortcut —
  the detail pass is intentionally deferred to a later, separate piece of work.
- **One risk-flagging mechanism, shared across calcs and BoDs**: `core/risk.py`'s
  `DesignRiskFlag` is used identically by `CalcResult.risk_flags` and
  `BasisOfDesignSection.risk_flags`, rather than each domain inventing its own
  ad-hoc "warnings" shape. `temporary_works` is a named category specifically
  because a design's permanent-condition analysis routinely doesn't cover its
  (often more critical) construction-stage condition — see docs/ARCHITECTURE.md.
- **Derive the process flow from existing data, don't hand-author a new
  dependency model**: `integration/graph.py` is built entirely by
  introspecting the `Interface` entries each discipline already declares,
  rather than a person separately asserting "X depends on Y" a second time
  in a new format. This means the graph can't drift out of sync with the
  BoDs (there's only one place dependency information is ever written), and
  it caught something a hand-authored sequence would likely have gotten
  wrong or missed entirely: civils/electrical_lv/electrical_hv/mechanical_piping
  form a genuine mutually-dependent cluster, not a chain — verified with
  Tarjan's SCC algorithm rather than eyeballed.
- **Orchestration tells you what's unblocked, it doesn't run anything**:
  `integration/process_state.py` deliberately has no side effects — it's a
  pure function of (graph, resolution state) -> (what can proceed, what's
  stuck on what). Nothing auto-resolves an external input (a DNO fault level
  statement, process flow data); the model has no way to know a real-world
  input has actually arrived except being told, same as any other status
  field in this repo.
- **Open items extraction favours precision over recall**: `integration/
  open_items.py`'s pending-input keyword list is deliberately tight — a
  missed open item is safer than a settled criterion wrongly flagged as
  still pending, for something meant to become an actual to-do list (and,
  via `open_items_as_action_items()`, an actual `ActionItem`). Extend the
  keyword list if a discipline's wording style produces misses once used
  for real, rather than switching to free-text NLP.
