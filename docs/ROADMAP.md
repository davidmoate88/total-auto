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

## Milestone 1a — Discipline basis of design (in progress)

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
- [ ] LV electrical basis of design skeleton.
- [ ] HV electrical basis of design skeleton.
- [ ] Mechanical piping basis of design skeleton.
- [ ] Multi-storey/occupied-building structural elements (floor vibration,
      lateral stability/sway, roof structure, fire engineering) — parked per
      project owner's direction; revisit if a future project needs them.
- [ ] Detail pass on civils and structural (fill in criteria/assumptions/
      deliverables per section, build the corresponding calcs/ modules) —
      deferred to Claude Code per the project owner's direction.

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
