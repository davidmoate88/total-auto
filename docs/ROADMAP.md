# Roadmap

The long-term goal (from the original brief): a toolkit covering as much of a
"head of project design" role as can be sensibly automated — engineering review,
portfolio tracking, and information/communication flow — with everything else made
as efficient as possible.

For practical, day-to-day guidance on actually working through a project
with what's built so far, see `docs/guides/` — this document is the build
plan, not a user manual.

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
- [x] First structural calc module: `calcs/structural/beam_capacity.py` — a
      simply-supported steel I/H-section beam bending/shear/deflection check to
      EN 1993-1-1 (UK NA), following the same shape as `bearing_capacity.py`
      (pydantic input, full `Term` working, explicit ULS combination factors,
      shared `DesignRiskFlag` mechanism) and answering
      `primary_steel_frame`'s "Beam/column member capacity checks"
      `CalculationRequirement` in `basis_of_design/structural.py` (now wired via
      `calc_module_reference` — the first real use of that field). Scoped to
      bending-dominant beam checks only: cross-section classification (Table
      5.2, Class 1-3; Class 4 raises a critical risk flag rather than being
      silently mishandled), Mc,Rd, Vpl,Rd, and a deflection check against a
      configurable span/N limit. Lateral-torsional buckling, the
      high-shear/bending interaction (SS6.2.8), and column/combined-axial
      checks are explicitly flagged as not implemented rather than
      approximated — same "flag, don't hide" pattern as the Ngamma caveat in
      `bearing_capacity.py`. 18 new tests, all verified against independently
      hand-derivable values (an idealised test section with geometry-derived
      A/Iy/Wel/Wpl, the same approach used for Nq/Nc in the geotechnical
      tests). Wired into the Streamlit UI (see below).
- [x] Second structural calc module: `calcs/structural/column_capacity.py` —
      cross-section compression resistance (SS6.2.4) and flexural buckling
      resistance about both principal axes (SS6.3.1) for a rolled steel I/H
      column, to EN 1993-1-1 (UK NA), completing `primary_steel_frame`'s
      "beam/column member capacity checks" as the "column" half — now split
      into two separate `CalculationRequirement` entries in
      `basis_of_design/structural.py` (beam -> `structural_beam_capacity_ec3`,
      column -> `structural_column_capacity_ec3`) since they're two distinct
      modules, not one. Deliberately scoped to PURE AXIAL COMPRESSION —
      combined bending+axial (a true beam-column, SS6.3.3) is explicitly
      flagged as not covered by either module rather than approximated by
      summing utilisations, which would not be a valid EN 1993-1-1 check.
      Buckling curve auto-selection (Table 6.2) is restricted to rolled I/H
      sections with h/b>1.2 and tf<=40mm (the common case); outside that,
      the module requires explicit curve overrides rather than guessing. 20
      new tests, including one that specifically confirms the web
      classification uses the stricter uniform-compression row (33/38/42
      epsilon) rather than the bending row (72/83/124 epsilon) the beam
      module uses for the same c/t ratio — the two modules' classification
      logic is intentionally NOT shared/copy-pasted, since they classify a
      genuinely different stress condition. Not yet wired into the
      Streamlit UI.
- [x] Third structural calc module: `calcs/structural/bolted_shear_connection.py`
      — bolt shear and bearing resistance (EN 1993-1-8 Table 3.4) for a
      concentrically-loaded bolt group, answering `primary_steel_frame`'s
      "Connection design" `CalculationRequirement`. Scoped to pure concentric
      shear only — no moment/eccentricity, no block tearing (SS3.10.2), no
      connected-ply gross/net section capacity. Notable departure from the
      other three calc modules' confidence pattern: this author's
      recollection of Table 3.4's alpha_v (shear resistance factor) by bolt
      grade and shear-plane location was genuinely inconsistent across
      attempts to recall it, so rather than embed a guessed lookup table (as
      done for fy in the beam/column modules, where confidence was high),
      `shear_resistance_factor_alpha_v` is a REQUIRED direct input with no
      default — a stricter application of the same "flag, don't guess"
      principle used throughout this repo, one level further than the
      default-plus-override pattern used elsewhere. 15 new tests, arithmetic
      verified by hand against the module's own documented alpha_b/k1
      formulae. Wired into the Streamlit UI (see below).
- [x] Fourth structural calc module: `calcs/structural/base_plate.py` —
      concrete/grout bearing utilisation under a concentric column base
      plate, and HD bolt tension utilisation under net uplift, to EN 1993-1-8
      (UK NA), answering `substructure_and_foundations`'s "Base plate /
      holding-down bolt design" `CalculationRequirement` — the foundation
      end of the load path `column_capacity.py` checks the member for. Same
      "required direct input over guessed formula" discipline as the
      connection module: EN 1993-1-8 SS6.2.5's T-stub-in-compression
      effective-area geometry for an I-section footprint was judged not
      reconstructible with sufficient confidence from memory, so
      `base_plate_effective_area_mm2` and `design_bearing_strength_mpa` are
      both required direct inputs rather than derived. The HD bolt tension
      check (Table 3.4, Ft,Rd=0.9*fub*As/gamma_M2) is higher-confidence and
      fully implemented. Base plate bending itself is not checked. 10 new
      tests, arithmetic verified by hand. Wired into the Streamlit UI (see below).
- [x] Wired all five `calcs/` modules into the Streamlit UI (`app.py`) — the
      original app hand-laid-out a form for the one calc that existed
      (bearing resistance); with four more modules built since, that stopped
      scaling. `app.py` now discovers every module in
      `calcs.registry.CALC_REGISTRY` and auto-builds each one's form from its
      pydantic input model: widget type (selectbox/checkbox/number_input/
      text_input) chosen from the field's annotation and constraint metadata,
      `Optional[...]` fields getting a "Set `<field>`?" toggle rather than a
      sentinel value that might itself fail validation. Verified in a real
      browser (per the "start the dev server, use the feature" rule) across
      all six tabs, not just imported/compiled. Found and fixed a real bug in
      the process: the ground-model-interpreter → bearing-resistance prefill
      handoff silently stopped updating on a second interpretation, because
      Streamlit widgets only apply a changed `value=` the first time a given
      widget `key` renders — fixed with a `bearing_prefill_version` counter
      folded into the key. See `docs/ARCHITECTURE.md`'s "The Streamlit UI"
      section for the full mechanism and trade-off (a flat auto-generated
      form per module, replacing the original tab's hand-laid-out columns/
      expanders).
- [x] Fifth structural calc module: `calcs/structural/deck_grating.py` — the
      first `platforms_and_walkways` module, answering "Deck/grating loading
      and deflection check". Models grating as bearing bars spanning
      simply-supported between primary supports, each picking up a tributary
      width from the panel's BS EN 1991-1-1 imposed UDL/point load (defaults
      match the platforms_and_walkways BoD criteria: 5.0 kN/m², 1.5 kN),
      checked via an ELASTIC stress method (no cross-section classification/
      plastic modulus — the right method for thin flat bearing bars, and
      deliberately distinct from `beam_capacity.py`'s classification-based
      approach for rolled I/H sections). Shear and the concentrated load's
      spread across bearing bars are direct inputs/simplifications, flagged
      rather than derived. Imports `STEEL_YOUNGS_MODULUS_MPA` and the fy
      lookup from `beam_capacity.py` rather than duplicating them. 11 new
      tests, verified against an idealised rectangular bar section (Wel, I
      computed directly from t/d, same approach as the other modules'
      idealised I-sections). Verified working end-to-end in a real browser
      (governing utilisation matched the CLI run exactly: 0.7273 vs 0.727).
- [x] First two `calcs/civil/` modules, answering `retaining_structures`'s
      two `calculations_required` entries in one deliberately-paired build
      (same pattern as the beam/column pair):
      - `calcs/civil/lateral_earth_pressure.py` — Rankine active earth
        pressure coefficient and resultant thrust, both DA1 combinations
        (mirroring `bearing_capacity.py`'s own DA1-C1/DA1-C2 structure — the
        governing case for an active thrust is the LARGER value, the
        opposite direction from a resistance check). Handles water table and
        surcharge; the active-thrust resultant is found by decomposing the
        piecewise-linear pressure diagram into trapezoidal segments at each
        breakpoint (top, water table if present, base) -- exact for the
        modelled profile, not a numerical approximation. Rankine's theory
        only: no wall friction, wall batter, or sloping backfill. Cohesion
        is clipped at zero pressure rather than properly excluding a
        tension-crack depth -- exact for c'=0 (the recommended backfill
        case), increasingly approximate otherwise, flagged when triggered.
        10 new tests, including hand-derivations of the classic
        `0.5*Ka*gamma*H^2` triangle and rectangular-surcharge-block results.
      - `calcs/civil/retaining_wall_stability.py` — sliding/overturning/
        bearing utilisation for a gravity/cantilever wall, both DA1
        combinations. Reuses `lateral_earth_pressure.py`'s
        `rankine_coefficients()` and `_active_thrust_and_lever_arm()`
        directly (recomputing active thrust from characteristic soil
        parameters under each combination's own factored phi'/c', the more
        rigorous approach vs. factoring a single pre-computed thrust value)
        and imports `DA1_C1`/`DA1_C2` directly from
        `bearing_capacity.py` -- one shared DA1 implementation across
        geotechnical and civils. Self-weight/lever-arm, base friction
        coefficient, and allowable bearing pressure are direct inputs
        (each individually flagged, following this session's established
        "flag, don't guess" pattern for constants below full confidence).
        Passive resistance uses a simpler Rankine embedment formula (no
        water table/surcharge on that side). Eccentricity checked against
        the middle-third rule. 11 new tests, independently re-deriving
        expected sliding/overturning values via the reused shared functions
        rather than re-asserting the module's own arithmetic; one test
        documents a genuine, correctly-modelled design trade-off found
        during testing (more self-weight improves sliding/overturning but
        *worsens* bearing demand -- initially written as a test bug
        assuming weight helps everything, caught by the assertion failing
        for the right reason).
      Both verified end-to-end in a real browser (retaining wall stability
      UI result 0.8027 matched the CLI run 0.803 exactly) and wired into
      `basis_of_design/civils.py` via `calc_module_reference`. 186/186 tests
      passing.
- [x] Third civils calc module: `calcs/civil/foul_drainage.py` — population/
      occupancy-based peak foul flow and Manning's-equation full-bore pipe
      capacity/self-cleansing velocity check, answering `foul_drainage`'s
      "Foul flow calculation" `CalculationRequirement`. The first civils
      module that is genuinely NOT Eurocode-based — UK foul sewer design
      follows Sewers for Adoption / water company Design and Construction
      Guidance instead, matching `calcs/civil/README.md`'s own warning that
      drainage sizing varies by sub-discipline more than structural/
      geotechnical does. Uses Manning's equation as an explicitly-flagged
      simplified/preliminary substitute for the Colebrook-White method
      formally required for adoptable UK sewer design; the peak flow factor
      (default 6x DWF) and per-capita flow rate are direct inputs with
      illustrative defaults rather than derived/tabulated values, following
      this session's established "flag, don't guess" discipline. Checks
      against the discipline's own BoD-stated minimum self-cleansing
      velocity (0.75 m/s). 9 new tests, arithmetic verified by hand
      (population->DWF->peak flow, and the Manning's velocity/capacity
      formula independently re-derived). Verified end-to-end in a real
      browser -- UI utilisation (0.1176) matched the CLI run exactly.
      195/195 tests passing.
- [x] Fourth civils calc module: `calcs/civil/cut_fill_balance.py` —
      grid-method cut/fill earthwork volume balance, answering
      `earthworks_and_remediation`'s "Cut/fill balance" (earthwork volumes
      across the site) `CalculationRequirement` and that section's own
      "±0 m³" balanced-target criterion. Site-wide grid-point data (existing
      level, proposed level, tributary area) is supplied as lenient pasted
      text -- one point per line, parsed the same way
      `calcs/geotechnical/interpretation/text_input.py` parses SPT/CPT data,
      but with the parsing and its unparsed-line warnings living inside the
      module's own `calculate()` (a registered `calcs/` module has no
      bespoke UI tab the way the ground model interpreter does, so that's
      the only place warnings can reach the generic Streamlit form's
      result rendering). This required one small, deliberate generic-UI
      change: no previously-registered module had a plain `str` field, so
      `app.py`'s fallback widget rendered `st.text_input` (single-line,
      useless for pasting many grid points) -- changed to `st.text_area`,
      verified safe since no other module's rendering was affected. Also
      the first calc module in this repo where an imbalance is a cost/
      logistics consideration, not a safety one -- it raises a
      `buildability` risk flag rather than `code_compliance`, a deliberate
      category distinction (see `core/risk.py`'s categories) from every
      other module built this session. The cut-to-fill conversion factor
      (bulking/shrinkage) is a direct input, default 1.0 -- this author
      doesn't have confident, generalisable figures to embed (highly
      soil/compaction-method dependent). 12 new tests, hand-derived volume
      arithmetic on a fully-worked 6-point grid. Verified end-to-end in a
      real browser, including the new text_area rendering correctly for
      multi-line pasted input -- UI net balance (260 m³) matched the CLI
      run exactly. 207/207 tests passing.
- [x] Fifth civils calc module: `calcs/civil/surface_water_discharge.py` —
      answers `surface_water_drainage_suds`'s "Discharge rate calculation"
      `CalculationRequirement`, per the project owner's explicit direction
      that this NOT attempt to derive the greenfield/brownfield runoff rate
      itself: the IH124/ICP SuDS Manual empirical methods need SAAR/SOIL
      data from the FEH webservice and coefficients this author judged not
      confidently reproducible from memory (unlike the Rankine/Manning's
      formulae elsewhere, simple enough to verify independently).
      `permitted_discharge_rate_l_s` is a required direct input instead --
      computed externally and entered directly. What the module DOES
      calculate, with high confidence: a check against the common LLFA
      practical minimum discharge (5 l/s, illustrative default) and flow
      control orifice sizing via the standard sharp-edged-orifice equation
      (`Q = Cd*A*sqrt(2*g*h)`, `Cd=0.61`) -- turning the given rate into an
      actionable deliverable (an orifice diameter) rather than just
      echoing it back. Flags a vortex flow control device (Hydro-Brake)
      as an alternative when the required orifice would be impractically
      small (<75mm default). 8 new tests, arithmetic verified by hand.
      Verified end-to-end in a real browser -- UI result (75.2mm) matched
      the CLI run exactly. 215/215 tests passing.
      The section's OTHER requirement, "Attenuation volume sizing" (storage
      to limit discharge to the agreed rate), needs the FSR/FEH rainfall
      depth-duration-frequency model -- a distinct empirical dataset, not a
      formula -- and per the project owner's explicit direction is left
      NOT BUILT, tracked as an open item in this roadmap rather than attempted with
      unverified figures.
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
      Code per the project owner's direction. **In progress**: structural has
      five modules built and wired (`beam_capacity.py`, `column_capacity.py`,
      `bolted_shear_connection.py`, `base_plate.py`, `deck_grating.py`), and
      civils has its first five (`lateral_earth_pressure.py`,
      `retaining_wall_stability.py`, `foul_drainage.py`,
      `cut_fill_balance.py`, `surface_water_discharge.py`) -- see Milestone 1
      above for all.
      Remaining: the beam-column combined bending+axial interaction, block
      tearing, base plate bending, civils attenuation volume sizing (open
      open item -- needs the FSR/FEH rainfall model)/slope-stability/
      highways calcs, and all calcs for electrical_lv/electrical_hv/
      mechanical_piping. Independent verification of every
      "illustrative value" flagged throughout the detail passes against
      actual current
      standard texts/project requirements is still outstanding for all
      disciplines.

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

## Milestone 1c — Practical working guides (complete)

`docs/ARCHITECTURE.md` and `docs/ROADMAP.md` explain the software; neither
tells anyone how to actually sit down and use it on a real project. Added
`docs/guides/` — one guide per discipline (plus geotechnical, the one
working calc) written for two readers at once: day-to-day practical use,
and a colleague/junior engineer who also needs the reasoning, not just the
steps.

- [x] `docs/guides/README.md` — index, and the recommended working order
      derived directly from `integration/graph.py`'s dependency findings
      (not a separately-asserted opinion): geotechnical first, structural
      next (independently), then civils/electrical_lv/electrical_hv/
      mechanical_piping concurrently as the mutually-dependent cluster.
- [x] `docs/guides/00_geotechnical.md` — the one guide covering a real
      calculation rather than a BoD skeleton: how the SPT/CPT/lab
      interpretation pipeline and the DA1 bearing resistance calc actually
      fit together, step by step, plus what to watch for (the Ngamma
      caveat, what "characteristic" actually means here).
- [x] `docs/guides/01_structural.md` and the four `02_*.md` guides — each
      covers where the discipline sits in the process, a practical working
      order through its sections, which risk flags actually matter and why,
      a verified worked code example of overriding an illustrative skeleton
      value for a real project (not just described — every example was
      executed against the actual skeleton to confirm the referenced
      criterion names are real), and common pitfalls aimed at a less
      experienced reader.

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
- **Practical guides are a separate artifact from the architecture docs,
  written for a different reader**: `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`
  explain the software to someone extending it; `docs/guides/` explains the
  *process* to someone using it — the working order, what to actually check,
  and a worked example of moving from an illustrative skeleton value to a
  confirmed project-specific one. Every worked code example in `docs/guides/`
  was executed against the real skeleton before being written down, not just
  described from memory — the same standard applied to everything else in
  this repo (see the "verify" pattern throughout this log).
- **Section properties are a catalogue input, not a derived one**:
  `calcs/structural/beam_capacity.py` takes A/Iy/Wel,y/Wpl,y directly as
  inputs rather than computing them from h/b/tw/tf, unlike the geometric
  values it does derive (the Table 5.2 classification c/t ratios). A rolled
  section's real properties (root radii, fillets, rolling tolerances) are
  more reliably read from a manufacturer's catalogue (e.g. the SCI "Blue
  Book") than reconstructed from nominal dimensions with an idealised
  rectangle formula — the same reasoning as keeping ground parameters
  "characteristic" and partial factors downstream: don't let one layer
  quietly bake in an approximation the next layer's input should really
  supply directly.
- **Flag unimplemented mechanics rather than approximate them**: LTB
  (EN 1993-1-1 SS6.3.2), the high-shear/bending interaction (SS6.2.8), and
  Class 4 effective section properties (EN 1993-1-5) are all genuinely
  relevant to a real steel beam check and are NOT implemented in
  `beam_capacity.py` — each raises an explicit warning (and, for Class 4, a
  critical risk flag) naming exactly what wasn't checked, rather than a
  partial/best-guess implementation that could be mistaken for a complete
  one. Same principle as the Ngamma caveat in `bearing_capacity.py`, applied
  to "not built at all" rather than "built but uncertain."
