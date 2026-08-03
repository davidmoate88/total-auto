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
- [x] Sixth civils calc module: `calcs/civil/slope_stability.py` — circular
      slip surface stability check via Fellenius' (Ordinary) Method of
      Slices, both DA1 combinations, answering
      `earthworks_and_remediation`'s "Slope stability check"
      `CalculationRequirement`. Deliberately Fellenius rather than Bishop's
      Simplified Method: Bishop's requires solving for the factor
      implicitly (each slice's normal force depends on it), while Fellenius
      is closed-form/non-iterative and well-verified here -- but it is
      KNOWN CONSERVATIVE relative to Bishop's (often overestimating
      utilisation by up to ~15-20%, especially with significant pore
      pressure). Every result carries that caveat, plus an extra warning
      specifically when the governing utilisation lands in the 0.9-1.0
      band, exactly where Fellenius's bias could flip a real PASS into an
      apparent FAIL. Reuses `DA1_C1`/`DA1_C2` from `bearing_capacity.py` --
      the third module this session to share that one implementation
      (after `lateral_earth_pressure.py` and `retaining_wall_stability.py`).
      Slice geometry (weight, base angle, base length, pore pressure) is
      supplied as lenient pasted text, the same pattern as
      `cut_fill_balance.py` -- this module does NOT generate slices from a
      slope profile and trial slip circle; that geometry (circle/ground-
      surface intersection, per-slice depth and base angle) is a
      substantial computational-geometry problem kept deliberately out of
      scope, the same reasoning that kept `retaining_wall_stability.py`'s
      self-weight and `base_plate.py`'s effective area as direct inputs
      rather than derived. 12 new tests, verified against an independently
      hand-derived 3-slice worked example (both DA1 combinations). Verified
      end-to-end in a real browser -- UI result (0.6998) matched the CLI
      run (0.6997, rounding) exactly. 227/227 tests passing. This completes
      all `calculations_required` entries in `earthworks_and_remediation`
      and `retaining_structures` -- civils now has working calcs for every
      section except surface water/SuDS's attenuation volume sizing (open
      item above) and highways/pavement (not yet scoped with any calc).
- [x] First electrical (LV) calc module:
      `calcs/electrical_lv/cable_sizing_voltage_drop.py` -- BS 7671
      Regulation 433.1.1 current-carrying capacity check (`Ib<=In<=Iz`,
      `I2<=1.45*Iz`) and Appendix 4 voltage drop percentage check for a
      single cable run, answering `lv_distribution_and_reticulation`'s
      "Cable sizing and voltage drop" `CalculationRequirement`. First
      module outside civils/structural/geotechnical, and first module in
      a new `calcs/electrical_lv/` package. Extends the "flag, don't guess"
      discipline one level further than `base_plate.py`/
      `surface_water_discharge.py`: BS 7671's cable current-rating and
      voltage-drop tables (Appendix 4) are installation-method- and
      cable-construction-specific and revised between amendments, so none
      of it is embedded -- the tabulated current rating (It) and mV/A/m
      figure are both required direct inputs. What IS implemented
      independently is the arithmetic BS 7671 applies on top of those
      tabulated values: `Iz = It*Ca*Cg*Ci*Cx` correction-factor derating,
      the three Regulation 433.1.1 conditions, and the voltage drop
      percentage check. The protective device's effective operation
      current (I2) defaults to `1.45*In` (standard BS EN 60898/61009 MCB
      assumption, BS 7671 Table 3A) if not supplied, with a warning --
      other device types (e.g. BS 3036 fuses) need I2 supplied directly.
      11 new tests, verified against a hand calculation (governing
      utilisation 0.9456, current-carrying capacity governing) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 238/238 tests passing.
- [x] Second electrical (LV) calc module:
      `calcs/electrical_lv/load_schedule_diversity.py` -- aggregates a
      pasted list of LV loads (name, rated_power_kw, power_factor,
      diversity_factor_percent) into one maximum demand current, answering
      the same section's "Load schedule / diversity" `CalculationRequirement`.
      Combines loads as real/reactive power (`P_total=sum(Pi)`,
      `Q_total=sum(Qi)`, `S_total=sqrt(P_total^2+Q_total^2)`), NOT by summing
      individual load currents directly -- currents at different power
      factors aren't in phase, so naive summation would misstate the
      resultant. `diversity_factor_percent` is a required per-load direct
      input (default 100%, no diversity) -- same "flag, don't guess"
      reasoning as the cable sizing module: BS 7671/the IEE On-Site Guide's
      diversity allowances (Table H1) are worked out for domestic circuit
      types, but this BoD is scoped to plant/industrial distribution, where
      diversity depends on each load's actual operational duty (e.g. a
      standby pump can legitimately carry 0% diversity) -- no single fixed
      table applies. Same lenient-paste-parsed-inside-`calculate()` pattern
      as `cut_fill_balance.py`/`slope_stability.py`. Its maximum demand
      current output is designed to feed directly into
      `cable_sizing_voltage_drop.py`'s `design_current_a` (Ib) -- the first
      calc-to-calc handoff within a single discipline in this repo. 13 new
      tests, verified against a hand-derived 4-load example (P/Q/S totals
      and both three-phase/single-phase maximum demand current) and
      end-to-end in a real browser -- UI result (37.54A) matched the CLI
      run exactly. 251/251 tests passing.
- [x] Third electrical (LV) calc module:
      `calcs/electrical_lv/earth_fault_loop_impedance.py` -- BS 7671
      Chapter 41 automatic disconnection of supply check:
      `Zs = Ze + (R1+R2)*temperature_correction_factor`, checked against the
      maximum permitted Zs for the protective device's disconnection time,
      answering `earthing_and_bonding`'s "Earth fault loop impedance
      calculation" `CalculationRequirement` and its "Maximum earth fault
      loop impedance" `DesignCriterion` (previously criteria-only, no
      calc). Same "flag, don't guess" reasoning as the cable sizing module:
      the maximum-Zs tables (41.2-41.5) are device-curve-specific and the
      conductor resistance-per-length figures (Appendix 14/Table I1) are
      size-specific, so `max_zs_ohms` and both resistance-per-km inputs are
      required direct inputs. The one constant applied by default is the
      1.20 temperature correction factor BS 7671 Appendix 14 commonly cites
      (20C tabulated/measured resistance -> normal operating temperature)
      -- a single well-established conversion, not a proprietary table
      lookup, so it ships as an overridable default. A failed check raises
      a `safety` risk flag (not `code_compliance`) -- excessive Zs means the
      protective device may not disconnect a fault within the required
      time, a direct shock-risk consequence, matching how `beam_capacity.py`
      already uses that category for a structural overstress. 10 new tests,
      verified against a hand calculation (utilisation 0.4983, PASS) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 261/261 tests passing.
- [x] Fourth electrical (LV) calc module:
      `calcs/electrical_lv/arc_flash_ppe_check.py` -- answers
      `arc_flash_and_electrical_safety`'s "PPE category framework"
      `CalculationRequirement` (newly added to that section), but with a
      deliberately different scope from every other module built so far:
      it does NOT calculate arc flash incident energy. IEEE 1584-2018's
      governing method is a multi-parameter empirical regression with
      equipment-class-specific coefficients not safely reproducible from
      memory, and unlike a failed structural/geotechnical check (caught by
      review before anyone is exposed to it), a wrong incident energy
      figure directly sets a worker's PPE for live work -- a real,
      immediate injury pathway distinct from every other calc in this
      repo. So `incident_energy_cal_cm2` is the required direct input
      (from an external IEEE 1584 study), and the module does only the
      safe part downstream: PPE category classification into illustrative
      bands (also direct inputs, since NFPA 70E's current-edition banding
      is the same "flag, don't guess" territory as BS 7671's tables) and a
      critical `safety` flag above a dangerous-energy threshold (default
      40 cal/cm^2), recommending de-energised work over PPE alone. Motor
      starting explicitly skipped per project direction ("do arc flash,
      ignore motor starting"). 11 new tests, verified against manual band
      classification (6.5 cal/cm^2 -> Category 2, medium safety flag) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 272/272 tests passing.
- [x] Fifth electrical (LV) calc module:
      `calcs/electrical_lv/earth_electrode_resistance.py` -- prompted by an
      explicit "have we covered lightning protection risks and earthing"
      question. Lightning protection (BS EN 62305) confirmed still out of
      scope (already excluded in `earthing_and_bonding`'s exclusions, not
      built). Earthing had a real gap: `earth_fault_loop_impedance.py`
      checks a circuit's protective conductor/disconnection time (Zs), not
      the earth electrode that circuit connects to. This module answers
      the "main earthing terminal" scope item via Dwight's formula
      (`R = (rho/(2*pi*L))*(ln(4L/d)-1)`) for a single vertical driven
      rod -- one of the few genuinely universal, textbook-verified earthing
      formulae (BS 7430, IEEE Std 142), so embedded rather than flagged,
      unlike this discipline's other modules. Deliberately narrow scope:
      multiple rods NOT computed (naive division by rod count is wrong due
      to mutual coupling; correct multi-rod/mesh formulae -- Schwarz, Sunde
      -- aren't confidently reproducible), and NOT wired to
      `electrical_hv.py`'s "Substation earth resistance target" criterion,
      since a HV substation earth grid needs a full multi-electrode mesh
      design with touch/step potential compliance (BS EN 50522/IEEE 80)
      that a single rod would badly understate. `target_earth_resistance_ohms`
      is a required direct input (project/system-specific). 8 new tests,
      verified against a hand calculation (rho=100 ohm.m, L=3m, d=16mm ->
      R=29.82 ohm, utilisation 1.491, FAIL against a 20 ohm target) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 280/280 tests passing.
- [x] Sixth structural calc module:
      `calcs/structural/beam_column_interaction.py` -- closes a gap flagged
      since `beam_capacity.py`/`column_capacity.py` were first built: a
      member carrying both bending and axial compression (a true
      "beam-column") needs the EN 1993-1-1 SS6.3.3 interaction check
      (equations 6.61/6.62), which neither single-action module performs.
      Same scale-up of the "flag, don't guess" pattern as arc flash: the
      *equations* themselves are simple and consistently documented, so
      embedded with full confidence, but the interaction k-factors
      (kyy/kyz/kzy/kzz, from EN 1993-1-1 Annex A or B -- a multi-case
      procedure keyed on moment distribution and section class) are
      required direct inputs, not derived. Consumes `column_capacity.py`'s
      `Nb,y,Rd`/`Nb,z,Rd` and `beam_capacity.py`'s `Mc,Rd` directly -- the
      first calc-to-calc handoff within structural. Updated both of those
      modules' docstrings/warnings, which previously said the combined
      check was simply "not implemented," to point at this module instead,
      and added a new "Beam-column combined bending+axial interaction
      check" `CalculationRequirement` to `primary_steel_frame` in
      `basis_of_design/structural.py`. 8 new tests, verified against a hand
      calculation (UC1=1.030, UC2=1.116, governing eq 6.62, FAIL) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 288/288 tests passing.
- [x] First electrical (HV) calc module:
      `calcs/electrical_hv/transformer_sizing.py` -- the first calc built
      outside civils/structural/geotechnical/electrical_lv, and the first
      calc-to-calc handoff that crosses a discipline boundary rather than
      staying within one. Answers `transformers`'s "Transformer rating"
      `DesignCriterion` ("to be confirmed from the LV load schedule plus
      diversity"): checks a candidate transformer rating against LV demand
      plus a growth margin, and computes full-load current on both
      windings via the three-phase power triangle (`I = S/(sqrt(3)*V)`).
      `lv_demand_kva` is designed to be fed directly from
      `calcs/electrical_lv/load_schedule_diversity.py`'s "S total" output
      -- the same relationship already declared as an `Interface` with
      `electrical_lv` in this section's BoD, now backed by an actual data
      handoff. Deliberately does NOT select a standard preferred
      transformer kVA size from a manufacturer's range -- the candidate
      rating is a direct input, checked not derived, same reasoning as
      `surface_water_discharge.py`'s permitted discharge rate.
      `growth_margin_percent` is an illustrative default (20%), same
      reasoning as `foul_drainage.py`'s `peak_flow_factor`. Explicitly out
      of scope: N-1 parallel-transformer redundancy sizing and IEC
      60076-7 thermal/ambient loading derating. 9 new tests, verified
      against a hand calculation (lv_demand=26kVA, rated=100kVA, 11kV/0.4kV
      -> utilisation 0.312 PASS, HV current 5.25A, LV current 144A) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 297/297 tests passing.
- [x] Second electrical (HV) calc module:
      `calcs/electrical_hv/protection_grading.py` -- answers
      `protection_and_control`'s "Protection discrimination/grading study"
      `CalculationRequirement`: IEC 60255-151 IDMT relay operating times
      for an upstream/downstream pair, checked for adequate grading
      margin. Notably the first module in this discipline where the
      governing physics is embedded rather than flagged -- the IDMT
      operating-time formula and its four standard curve constants
      (Standard/Very/Extremely/Long Time Inverse) get the same treatment
      as `column_capacity.py`'s Table 6.1 imperfection factors: a small,
      genuinely universal lookup, since these specific constants are about
      as consistently reproduced across protection engineering literature
      as a constant gets, unlike BS 7671's installation-specific cable
      tables or IEEE 1584's equipment-class-specific regression (both of
      which required the opposite "flag it" treatment elsewhere in this
      discipline). What's genuinely project-specific -- each relay's
      pickup current/TMS (design choices) and the prospective fault
      current (from a separate DNO/network fault level study, per this
      discipline's own criterion) -- are required direct inputs.
      Deliberately scoped to ONE relay pair at ONE fault current, not a
      full multi-stage study across the fault current range, since the
      margin between different curve shapes/settings isn't necessarily
      monotonic with fault current -- flagged explicitly, not overclaimed.
      9 new tests, verified against a hand calculation (SI curve,
      downstream Is=100A/TMS=0.1, upstream Is=200A/TMS=0.2, at 2000A ->
      t_down=0.227s, t_up=0.594s, margin=0.367s, PASS against a 0.3s
      requirement) and end-to-end in a real browser -- UI result matched
      the CLI run exactly. 306/306 tests passing.
- [x] Third electrical (HV) calc module:
      `calcs/electrical_hv/arc_flash_ppe_check.py` -- answers
      `arc_flash_and_hv_safety`'s "HV arc flash calculation method" and
      "Minimum PPE category for HV switching" `DesignCriterion` entries.
      Shares its LV counterpart's core reasoning for not calculating
      incident energy, reinforced by this discipline's own criterion note
      that "not all LV-oriented tools extend cleanly to HV switchgear" --
      incident energy must come from a dedicated HV-specific study, never
      extrapolated from an LV assessment. Deliberately DIFFERENT in shape
      from the LV module, not just re-parameterised: HV incident energies
      routinely exceed the LV module's Category 1-4 banding (tops out
      ~40 cal/cm^2) entirely, so this module instead reports the required
      PPE arc rating directly (== the incident energy) and checks it
      against a practical arc-rated PPE limit (illustrative default 100
      cal/cm^2) -- above which the finding is "PPE cannot protect a worker
      here, use de-energised work/other engineering controls," not "get a
      bigger suit." A "PPE required" finding carries `high` severity here
      (vs LV's `medium`), a deliberate difference reflecting this
      discipline's own existing risk flag that HV arc flash consequences
      are typically far more severe than LV. 8 new tests, verified against
      a hand-checked example (55 cal/cm^2 -> PPE required, high severity;
      150 cal/cm^2 -> exceeds practical limit, critical severity) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 314/314 tests passing.
- [x] Fourth electrical (HV) calc module:
      `calcs/electrical_hv/substation_earthing_touch_step.py` -- answers
      `hv_earthing_and_touch_step_potential`'s "Touch/step potential
      limits" and "Substation earth resistance target" `DesignCriterion`
      entries. IEEE 80 substation earth grid design splits into two
      genuinely different confidence tiers, and this module treats them
      differently on purpose: grid resistance (Sverak's simplified
      formula) and tolerable touch/step voltage (IEEE 80's
      body-resistance-based formulas) are embedded directly -- the same
      confidence tier as `earth_electrode_resistance.py`'s Dwight formula
      and `protection_grading.py`'s IDMT curve constants. The ACTUAL mesh
      (touch) and step voltage at a real grid need IEEE 80's geometric
      correction factors (Km, Ks, Kii, Kh, grid irregularity) -- a
      genuinely complex multi-case procedure in the same "flag, don't
      guess" tier as `beam_column_interaction.py`'s Annex A/B k-factors or
      IEEE 1584's incident energy model -- so those two figures are
      required direct inputs from a proper external grid study, never
      derived here. Three independent checks (grid resistance, touch
      voltage, step voltage) each raise their own critical safety flag on
      failure, with the highest utilisation reported as the governing
      headline -- the same multi-condition/single-governing-headline shape
      as `cable_sizing_voltage_drop.py`. This completes every named
      `calculations_required` entry in `basis_of_design/electrical_hv.py`.
      10 new tests, verified against a hand calculation (rho=100 ohm.m,
      400m^2 grid, Lt=200m, h=0.5m -> Rg=2.62 ohm; Cs=0.7,
      E_touch=680.8V, E_step=2231.1V; governing utilisation 0.6723,
      step voltage governing, PASS) and end-to-end in a real browser --
      UI result matched the CLI run exactly. 324/324 tests passing.
- [x] First mechanical piping calc module:
      `calcs/mechanical_piping/line_sizing_velocity_check.py` -- the fifth
      and final discipline in this repo to get a working calc. Answers
      `pipe_sizing_and_flow`'s "Line sizing / velocity check"
      `CalculationRequirement`. Deliberately scoped to velocity and
      erosional velocity only, not pressure drop, even though the
      requirement names both -- pressure drop (Darcy-Weisbach with a
      Colebrook-White/Moody friction factor) has its own genuinely
      iterative solution method, left for a separate future module rather
      than folded in half-finished, same reasoning as `foul_drainage.py`'s
      full-bore-only scope. Erosional velocity uses API RP 14E's
      `Ve=C/sqrt(rho)`, computed by converting density to lb/ft^3 via an
      *exact* physical unit conversion (0.062428, not a recalled formula)
      so only the empirical constant C itself (illustrative default 100,
      continuous service) is a direct input, matching this discipline's
      own criterion that there's no single project-wide erosional velocity
      figure. `actual_internal_diameter_mm` is also a required direct
      input -- ASME B36.10M pipe schedule tables are not embedded, same
      reasoning as `cable_sizing_voltage_drop.py`'s tabulated cable
      rating. Velocity outside the illustrative 3-5 m/s target range
      raises a `buildability` flag (not `code_compliance`) -- softer than
      exceeding the erosional limit, which raises a critical
      `code_compliance` flag. 9 new tests, verified against a hand
      calculation (100 m^3/h through a 100mm bore, water -> V=3.54m/s,
      Ve=3.86m/s, utilisation 0.917, PASS, within target range) and
      end-to-end in a real browser -- UI result matched the CLI run
      exactly. 333/333 tests passing.
- [x] Second mechanical piping calc module:
      `calcs/mechanical_piping/pipe_stress_check.py` -- answers
      `pipe_stress_analysis_and_supports`'s "Pipe flexibility/stress
      analysis" `CalculationRequirement`: ASME B31.3 sustained stress
      (Eq 17) and thermal expansion stress range (Eq 1a/13). Deliberately
      does NOT perform flexibility analysis -- deriving resultant moments
      needs a full 3D stiffness-matrix solve (CAESAR II or equivalent),
      not a formula. Same split as `beam_column_interaction.py`: governing
      equations embedded with full confidence, case-specific inputs
      (resultant moments Ma/Mi/Mo/Mt, SIFs, allowable stresses Sc/Sh)
      required direct inputs. Section modulus computed internally from
      OD/wall thickness (basic mechanics, no tables). 9 new tests,
      verified against an independently re-derived reference calculation
      (Do=114.3mm, t=6.02mm, P=2.0MPa, Ma=500N.m -> SL=20.2MPa; Mi=800,
      Mo=600, Mt=300N.m -> SE=32.7MPa, SA=305MPa; governing utilisation
      0.183, PASS) and end-to-end in a real browser -- UI result matched
      the CLI run exactly. Also confirmed a genuine edge case in Eq 1b (an
      extreme sustained moment can drive the allowable stress range SA
      negative, correctly reported as infinite thermal utilisation, not a
      bug). 342/342 tests passing.
- [x] Third mechanical piping calc module:
      `calcs/mechanical_piping/ped_pesr_classification_check.py` --
      answers `design_standards_and_criteria`'s "Piping class/category"
      `DesignCriterion` (PED Article 13 / PESR). Deliberately does NOT
      derive the PED/PESR category -- Annex II's four separate graphical
      boundary charts (Group 1/2 gas/liquid) are exactly the kind of
      easy-to-transpose numeric detail this repo avoids embedding, and
      getting it wrong here carries real regulatory weight (skipping
      required notified body assessment is a legal compliance failure).
      What IS computed directly: the PED Article 2(1) scope threshold
      (PS <= 0.5 bar excluded entirely) -- the single most universally
      cited PED figure, the literal scope definition. Above that, category
      is a required direct input, with downstream bookkeeping (notified
      body/CE-UKCA marking requirement, a Group 1 fluid caution). 10 new
      tests, verified against manual classification (16 bar, Category II
      -> in scope, notified body required, critical flag; SEP -> no flag)
      and end-to-end in a real browser (verified the SEP/Group 1 case,
      avoiding the known Streamlit dropdown-click limitation, matching two
      existing pytest cases exactly) -- 352/352 tests passing.
- [x] Fourth mechanical piping calc module:
      `calcs/mechanical_piping/support_load_schedule.py` -- answers
      `pipe_stress_analysis_and_supports`'s "Support load schedule"
      `CalculationRequirement` and `supports_structural_and_hazardous_area_interfaces`'s
      "Support load handover format" criterion. This completes every
      named `calculations_required` entry across
      `basis_of_design/mechanical_piping.py` (4/4 wired). A genuinely
      different shape from this discipline's other modules -- less a
      formula-heavy check, more the actual handover artifact, using the
      lenient-paste pattern already established by
      `cut_fill_balance.py`/`slope_stability.py`. Support reactions come
      from the same external flexibility analysis as
      `pipe_stress_check.py`'s resultant moments but aren't derived from
      that module's output -- different quantities, same upstream source.
      Loads are handed over unfactored, matching real handover practice
      (the structural discipline applies its own partial factors, same
      reasoning as `beam_capacity.py`/`column_capacity.py`'s separate
      permanent/variable inputs). An optional uniform screening limit
      gives a genuine pass/fail check when a support capacity is already
      known, explicit that it's one uniform limit, not a per-support
      capacity lookup. 10 new tests, verified against a hand calculation
      (3 supports, total vertical 40.3kN, governing S2 at 18.0kN,
      utilisation 0.9 PASS against a 20kN limit) and end-to-end in a real
      browser -- UI result (governing reaction 18kN at S2, no limit
      supplied) matched the CLI run exactly. 362/362 tests passing.
- [x] UI: navigation by discipline + real cross-module handoffs -- with all
      five disciplines built out (26 calc modules), `app.py`'s original
      single flat row of 27 tabs (ground model + 26 modules) had become
      the app's biggest usability problem in practice, not just in
      principle -- the same scrolling/hunting friction showed up
      repeatedly during this session's own browser verification passes.
      A `st.sidebar.radio` discipline selector now scopes the main area
      to one discipline's modules at a time (grouped by
      `CalcModule.discipline`, a field every module already carried),
      keeping each `st.tabs()` row to at most ~7. Separately, a
      declarative `CALC_HANDOFFS` list in `app.py` now wires up the
      cross-module handoffs several docstrings already describe (e.g.
      `load_schedule_diversity.py` -> `cable_sizing_voltage_drop.py`,
      `column_capacity.py`/`beam_capacity.py` -> `beam_column_interaction.py`)
      -- previously only the ground-model -> bearing-resistance handoff
      actually worked, hand-wired with its own session-state keys; every
      other handoff was a docstring instruction the user had to act on
      manually. A generic mechanism (`_apply_handoffs`) pushes a source
      module's headline or a named term into the target module's prefill
      store; the ground-model handoff was migrated onto the same
      mechanism rather than left as a separate one. Getting this right
      needed a genuine fix beyond the original bearing-prefill's widget-
      key-versioning trick: with sidebar-scoped rendering and 26 modules,
      a handoff's target isn't guaranteed to render in the same script
      execution as its source (unlike ground model, always structurally
      first) -- `render_calc_module_tab` now persists a submitted result
      into session state and calls `st.rerun()` when a handoff fires, so
      the next execution starts with an already-current prefill store
      before any tab's widgets are built. This was found and fixed during
      verification, not hypothetical: the first browser pass showed
      `cable_sizing_voltage_drop.py`'s `design_current_a` silently staying
      at 0.00 after running `load_schedule_diversity.py`, exactly the
      registry-ordering/no-rerun failure mode described above. Re-verified
      after the fix -- both the same-discipline handoff (LV -> LV) and the
      cross-discipline handoff (LV -> HV) correctly prefilled. 362/362
      tests passing (app.py has no direct pytest coverage; verification
      was end-to-end in a real browser).
- [x] Fill calc inputs from drawings: a schema export + a Claude Code skill
      + a JSON import feature, scoped to the 9 Electrical (LV)/(HV) modules
      first (user's explicit choice over building generically for all five
      disciplines up front). `calcs/schema_export.py` introspects any
      module's pydantic `input_model` and emits each field's type/required/
      default/description (and `allowed_values` for `literal` fields) as
      JSON, with a `--discipline`/`--key` filtering CLI (filters combine as
      AND, documented in `--help` after briefly tripping over the opposite
      assumption while testing). `.claude/skills/fill-calc-inputs-from-
      drawings/SKILL.md` reads a GA/SLD/schedule and produces JSON in that
      same shape -- its central rule extends this repo's "flag, don't
      guess" discipline one level upstream, to extraction itself: a field
      the skill can't confidently read from the source document is left
      out of the output entirely, never guessed or defaulted, exactly
      mirroring how a calc module treats a genuinely uncertain engineering
      value. `app.py`'s new sidebar "Import extracted data (JSON)" expander
      (`render_import_sidebar`) validates each module key/field name against
      the live registry and pydantic models, routes valid fields through
      the same `_set_prefill` helper `CALC_HANDOFFS` uses, and reports
      unknown keys/fields back to the user rather than dropping them
      silently. All three pieces share one source of truth (the live
      pydantic models) rather than three hand-maintained field lists. 8 new
      tests for the schema export; the full pipeline was also verified
      end-to-end in a real browser with a hand-crafted JSON file covering
      both the happy path (4 fields imported across 2 modules, same-
      discipline and cross-discipline prefills both confirmed by inspecting
      actual field values) and the error path (two deliberately-invalid
      module keys correctly flagged, not silently ignored). 370/370 tests
      passing.
- [x] Sixth electrical (LV) calc module: `calcs/electrical_lv/motor_starting.py`
      -- closes the one calc gap in Electrical (LV)/(HV) left open by
      explicit decision, not oversight (this milestone's own arc-flash
      entry above says "do arc flash, ignore motor starting"; the
      load-schedule-diversity module's docstring flagged the same gap and
      pointed here). Starting current
      (`full_load_current_a*starting_current_multiplier`) and voltage dip
      at the point of connection (a simplified `Ist/Isc` source-impedance
      approximation), checked against a permissible dip limit --
      `starting_current_multiplier` and `source_fault_current_a` are
      required direct inputs, not a "typical DOL ~6x FLC" default, since
      DOL/star-delta/soft-start/VSD give materially different starting
      currents for the same motor -- same reasoning as
      `cable_sizing_voltage_drop.py`'s tabulated cable rating and
      `protection_grading.py`'s `fault_current_a`. Also raises an
      `assumption_sensitivity` flag when a DOL start is chosen for a motor
      above the DOL threshold criterion (illustrative default 5.5kW,
      matching `motor_control_and_switchgear`'s existing `DesignCriterion`)
      -- the first calc in this repo to turn one of its own discipline's
      plain criterion values into an actual per-run pass/fail check rather
      than a value only ever displayed. This completes all 9 named
      `calculations_required` entries across Electrical (LV) and
      Electrical (HV). 11 new tests, verified against a hand calculation
      (FLC 14.5A x 6.5 = 94.25A starting current, 3.77% dip against a
      2500A source fault current, utilisation 0.377 PASS; DOL flag
      confirmed firing for a 7.5kW motor above the 5.5kW default threshold
      and confirmed NOT firing for the same motor on a non-DOL method) and
      end-to-end in a real browser. 381/381 tests passing.
- [x] UI: from discipline tabs to a searchable catalog -- with Electrical
      (LV)/(HV) complete and the registry at 28 entries (ground model +
      27 calc modules), the sidebar-radio-plus-`st.tabs()` navigation built
      for the previous milestone (26 modules across six disciplines)
      started showing the opposite problem: finding a specific calc meant
      already knowing which discipline bucket it lived in, which stops
      being obvious once a single discipline itself has six-plus modules.
      `app.py`'s `render_catalog` replaces grouped navigation with one
      flat, searchable list -- every module (plus the ground model
      interpreter, not a `calcs.registry` entry) as a card with its
      name/discipline/description, filtered by free-text search
      (`_filter_entries`, matching name/discipline/description) and/or a
      discipline dropdown. Opening a card sets
      `st.session_state["selected_key"]` and renders that module's form
      full-width (`render_module_detail`) with a "Back to catalog"
      control -- one piece of navigation state where the old design needed
      two (which discipline, which tab within it). None of the generic
      machinery changed (`_field_widget`, `render_calc_module_tab`,
      `_apply_handoffs`, `render_import_sidebar`) -- `CalcModule.discipline`
      was already the only "where does this belong" metadata any of it
      needed, whether that drove a tab row or a filter dropdown. The one
      real gap the rewrite had to close: with tabs, a same-discipline
      handoff target was already visible as a sibling tab; with only one
      module ever rendered per run now, the post-run "handed off" notice
      would otherwise just name a target the user has to find by hand --
      it now also renders an "Open `<target>` ->" button per handed-off
      target (ground model's bearing-resistance handoff got the same
      treatment) that jumps straight into that module's detail view.
      Verified end-to-end in a real browser: searched "motor" and got
      exactly the new module; ran `load_schedule_diversity.py` and
      confirmed both its handoff targets (one same-discipline, one
      cross-discipline into Electrical (HV)) got working "Open ->"
      buttons, with the cross-discipline target's `lv_demand_kva`
      correctly pre-filled at 21.04 (the handed-off S total) after
      clicking through. 381/381 tests passing (app.py has no direct
      pytest coverage; verification was end-to-end in a real browser, per
      this repo's established practice for UI changes).
- [x] Ground model interpreter: multi-stratum profiles -- the user wanted
      to hand Claude a full GI report and get "usable factual data" for the
      calc tools; scoping that turned up a real accuracy gap first. The
      overburden-stress term several correlations depend on (SPT `Cn`, CPT
      phi'/cu) is derived by walking the WHOLE layered profile above a
      point, but `render_ground_model_tab` only ever let an engineer enter
      ONE stratum per run -- so a deeper stratum interpreted alone silently
      understated the weight actually above it on any real multi-layer
      site. `Stratum`/`SiteInvestigation` (`calcs/geotechnical/
      interpretation/models.py`) and `overburden_profile_kpa`/
      `interpret_stratum` were already built and tested for a full profile
      (`tests/test_ground_model.py`'s `_multi_layer_site` fixture) -- only
      the UI had never caught up, so this was purely an `app.py` rework,
      zero calc-logic changes, zero new pytest coverage needed. Replaced
      the single-stratum form with build-then-interpret: "Add a stratum"
      appends to a session-state stratum list ("Profile so far", with
      Remove), "Interpret full profile" builds ONE `SiteInvestigation` from
      the whole list (correct overburden) and runs `interpret_stratum` per
      stratum against it, each with its own "push to bearing resistance"
      button. Caught and fixed a bug before shipping: an initial version
      nested a "push" button's "open" action inside the push button's own
      `if` block -- only reachable in the ONE rerun immediately after ITS
      OWN click, so a click on it a run after the parent's condition
      reverts to `False` is silently dropped. Fixed by combining "set
      prefill" and "navigate" into one click. Verified end-to-end in a real
      browser against the exact `_multi_layer_site` fixture (fill 0-1m
      granular no lab data, sand 1-6m with SPT/CPT/lab bulk density):
      derived sand's phi'=32.5 deg and unit weight=19.0 kN/m^3 (lab-derived,
      overriding the 18.0 assumed default) matching the pytest fixture
      exactly, and confirmed the bearing-resistance prefill carried the
      right per-stratum values (32.52/19.00) through, not fill's. 381/381
      tests passing (no backend changes; browser-verified per the same UI
      convention as above).
- [x] `fill-ground-model-from-gi-report` skill + "Import GI-derived strata
      (JSON)" -- answers the user's original ask directly. Same "flag,
      don't guess" contract as `fill-calc-inputs-from-drawings`, but needed
      its own skill and import path since the ground model interpreter
      isn't a `calcs.registry` module: no `calcs.schema_export` entry for
      it, and the import shape (`water_table_depth_m` + a stratum list)
      doesn't fit the generic sidebar's `module_key -> {field: value}`
      contract. `render_gi_import_expander`/`_import_gi_profile` live
      inside the ground model tab itself. A stratum is only importable
      when all of `Stratum`'s own required fields
      (name/behavior/top_depth_m/base_depth_m/assumed_unit_weight_kn_m3)
      are present -- no live per-field form to partially prefill an
      incomplete one into, unlike the electrical import, so an incomplete
      stratum is skipped whole with exactly why reported, not guessed into
      "working." The skill adds one more "never guess" layer beyond its
      electrical counterpart: a real GI report usually covers several
      boreholes with genuinely different stratification, and blending them
      into one profile would itself be an invented number -- the skill
      picks ONE representative borehole/trial pit log and states which,
      and why, in its extraction notes, rather than averaging boundary
      depths across logs. Verified the import path directly with a Python
      call (bypassing the OS file-picker dialog, which this session's
      browser automation can't drive): fed `_import_gi_profile` the same
      fill/sand fixture data plus a deliberately incomplete third stratum
      (missing `base_depth_m`/`assumed_unit_weight_kn_m3`) -- the two
      complete strata imported intact, the incomplete one correctly
      skipped with a clear "missing required field(s)" message.
- [x] Three document-intake skills: standards register, constraints
      register, foundation/levels synthesis -- scoped down from an
      open-ended "build a skill for basis of design" ask into four
      narrower deliverables from one client document dump (contract, ERs,
      planning docs, GI, FRA, drainage calcs): a risk register (user's own
      XLSX format, not yet provided -- held, not built), a standards
      register, a constraints register, and a foundation/levels options
      synthesis. Two scoping decisions made explicitly with the user
      rather than assumed: separate skills per deliverable (not one
      pipeline, matching this repo's one-skill-one-job pattern) and
      foundation/levels synthesis stops at "what do the documents already
      say, plus which calcs/ module to run next" -- no invented foundation
      type, depth, or level, the one place flagged as a real departure
      from every other module in this repo if scoped the other way.
      `.claude/skills/build-standards-register/` reuses real leverage
      already in the repo: every basis_of_design/*.py module already
      declares its discipline's expected standards (65+ codes across five
      disciplines), read fresh every run, not a hand-maintained copy --
      citations get flagged as not-in-baseline / unexpected-discipline-
      context / possibly-superseded (only when genuinely confident) /
      unidentifiable, never a blanket "wrong."
      `.claude/skills/build-constraints-register/` has no existing model
      to build against, so it proposes a category structure explicitly
      flagged as adjustable.
      `.claude/skills/synthesize-foundation-levels-options/` leans on a
      pattern found testing the ground-model skill against a real GI
      report: GI reports usually already contain the geotechnical
      engineer's own foundation recommendation (the Bramley report's own
      Section 9 recommended piled/helical foundations, with reasons) --
      transcribing that is extraction, not derivation. Cross-references
      the specific calcs/geotechnical/, calcs/civil/, and
      calcs/structural/ module keys relevant to whatever the documents
      raise, and explicitly flags piled foundations as a current calcs/
      gap rather than silently omitting the cross-reference.
- [x] `build-risk-register` skill -- built once the user supplied their own
      template (Newport BESS Risk Register.xlsx, a real, populated 60-row
      project register, not a blank form). Structurally different from the
      other three document-intake skills: needs a content library, not
      just a comparison baseline, since risk register entries come from
      precedent as much as from any one project's documents.
      `.claude/skills/build-risk-register/reference_risk_library.json`
      holds all 60 real entries classified into three tiers: 42
      `tier1_standard` risks (recur on essentially any UK BESS project --
      CDM compliance, fire HSE, security, weather -- reused close to
      verbatim), 15 `tier2_pattern` risks (a recurring type, but original
      wording tied to the source project's own specifics -- a named
      planning condition, DNO process, or supplier -- each carrying an
      adaptation_note on what to re-derive), and 4 `tier3_dated` risks (a
      pandemic, a named conflict -- excluded by default, only reintroduced
      generically if the new project's own documents raise an active
      equivalent). This classification was a judgement call made once,
      up front, not re-derived every run -- flagged in the skill's own
      text as worth periodically refreshing if more project registers get
      delivered over time. The skill still reads the user's template
      *structure* fresh every run (headers, dropdowns, formula patterns,
      next empty row), same discipline as the other three. One narrow,
      explicit exception to "never guess" that the other three don't need:
      Impact/Probability scores are always proposed, never asserted as
      settled -- written into the template's own free-text comments column
      (reusing an existing column, not adding one) prefixed "[DRAFT --
      confirm at risk workshop]", since risk scoring is a genuine team/
      workshop judgement in real practice, not a drafting decision.
      Writing the actual .xlsx defers entirely to the anthropic-skills:xlsx
      skill's own openpyxl/formula-safety/recalc.py guidance rather than
      duplicating it.
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
      six modules built and wired (`beam_capacity.py`, `column_capacity.py`,
      `beam_column_interaction.py`, `bolted_shear_connection.py`,
      `base_plate.py`, `deck_grating.py`), and civils has its first six (`lateral_earth_pressure.py`,
      `retaining_wall_stability.py`, `foul_drainage.py`,
      `cut_fill_balance.py`, `surface_water_discharge.py`,
      `slope_stability.py`), and electrical_lv has its first five
      (`cable_sizing_voltage_drop.py`, BS 7671 Reg 433.1.1 current-carrying
      capacity check + Appendix 4 voltage drop check -- tabulated current
      rating and mV/A/m are required direct inputs, not derived, since BS
      7671's cable tables are installation-method-specific and amendment-
      revised; `load_schedule_diversity.py`, P/Q real+reactive power load
      aggregation to a maximum demand current, feeding its result straight
      into the first module's `design_current_a`; `earth_fault_loop_impedance.py`,
      BS 7671 Chapter 41 Zs check against the tabulated maximum for
      automatic disconnection; `arc_flash_ppe_check.py`, PPE category
      classification from an externally-supplied IEEE 1584 incident energy
      figure -- deliberately does NOT calculate incident energy itself; and
      `earth_electrode_resistance.py`, Dwight's formula for a single
      vertical driven earth rod, closing the gap between circuit-level
      earth fault protection and the actual earth electrode -- see that
      module's docstring), and electrical_hv now has all four of its named
      `calculations_required` entries built (`transformer_sizing.py`,
      candidate transformer rating checked against LV demand plus a growth
      margin, HV/LV full-load current -- the first cross-discipline
      calc-to-calc handoff, taking LV demand directly from
      `load_schedule_diversity.py`'s output; `protection_grading.py`, IEC
      60255-151 IDMT relay operating times and grading margin check -- the
      curve constants themselves are embedded, unlike this discipline's
      other modules, since they're about as universal as protection
      engineering constants get; `arc_flash_ppe_check.py`, required PPE
      arc rating vs a practical PPE limit from an externally-supplied
      incident energy figure -- deliberately shaped differently from the
      LV arc flash module, not just re-parameterised; and
      `substation_earthing_touch_step.py`, Sverak grid resistance + IEEE
      80 tolerable touch/step voltage, checked against an externally-
      supplied actual mesh/step voltage -- splits its scope by confidence
      tier within a single module, embedding the formula, flagging the
      geometry-dependent actual values), and mechanical_piping now has all
      four of its named `calculations_required` entries built
      (`line_sizing_velocity_check.py`, actual velocity vs the API RP 14E
      erosional velocity limit and a target velocity range -- pressure
      drop deliberately left out; `pipe_stress_check.py`, ASME B31.3
      sustained stress + thermal expansion stress range check from
      externally-supplied resultant moments -- does not perform
      flexibility analysis; `ped_pesr_classification_check.py`, PED
      Article 2(1) scope threshold computed directly, conformity
      assessment bookkeeping from an externally-determined category; and
      `support_load_schedule.py`, per-support reaction load aggregation,
      unfactored, for handover to structural -- see those modules'
      docstrings) -- see Milestone 1 above for all.
      Remaining: block tearing, base plate bending, civils attenuation
      volume sizing (open item above -- needs the FSR/FEH rainfall model)
      and highways/pavement calcs. electrical_lv's motor starting, listed
      here as skipped per project direction, was subsequently built --
      see the "Sixth electrical (LV) calc module" entry under Milestone 1
      above.
      Independent verification of every
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
