# Structural — Basis of Design

## Design standards and general criteria

Overarching design basis for industrial access steelwork (platforms, walkways, stairs, ladders, handrails) and its supporting frame. Multi-storey/occupied-building structural elements (floor vibration for building floors, lateral stability/sway, roof structure, fire engineering) are out of scope for now per project direction — parked, not deleted.

**Applicable standards:**

- BS EN 1990 (UK NA) — Basis of structural design
- BS EN 1991-1-1 (UK NA) — Actions on structures — densities, self-weight, imposed loads
- BS EN 1993-1-1 (UK NA) — Design of steel structures — general rules
- Machinery Directive 2006/42/EC _EU — confirm UK equivalent designation/status (Supply of Machinery (Safety) Regulations 2008, and current CE/UKCA marking requirement)._
- BS EN ISO 12100 — Safety of machinery — general principles for risk assessment and risk reduction

**Design criteria:**

- Design working life: 25 years — Typical for industrial access/plant structures (BS EN 1990 shorter design life category) — confirm the client/insurer-required figure; occupied buildings would normally use 50.
- Consequence class: CC2 (BS EN 1990 Annex B) — Typical for industrial access structures with limited occupancy — confirm against the specific structure's failure consequences.
- Imposed load category: Category E (storage/industrial) — BS EN 1991-1-1 imposed load category — confirm against actual platform use (access/maintenance only vs. storage).

**Assumptions:**

- The structure is treated as a 'non-building structure' for BS EN 1990 consequence-class purposes unless a client/insurer requirement says otherwise.
- Post-Brexit UK marking regime is assumed to be UKCA under the Supply of Machinery (Safety) Regulations 2008, unless the project also requires CE marking for an export/EU market.

**Exclusions:**

- Multi-storey/occupied-building structural design (floor vibration, lateral sway, roof structure, fire engineering) — parked, see docs/ROADMAP.md.
- Seismic design — not typically governing for UK sites; excluded unless the specific site/client requires it.

**Deliverables:**

- Design basis statement (report)
- General arrangement drawing suite (drawing)

## Substructure and foundations

Foundations and base connections (base plates, holding-down bolts) supporting platform/walkway steelwork.

**Applicable standards:**

- BS EN 1997-1 (UK NA) _Shared with the geotechnical module._
- BS EN 1993-1-8 (UK NA) — Design of joints — base plate/holding-down bolt design.

**Design criteria:**

- Minimum founding depth: to be confirmed from ground model — Set from calcs/geotechnical/ characteristic parameters and frost depth once the ground model exists for the site.
- Base plate bearing pressure limit: to be confirmed N/mm² — Governed by the concrete/grout bearing capacity beneath the base plate, not the steel design itself.

**Assumptions:**

- Ground conditions are assumed per calcs/geotechnical/ characteristic parameters until a site-specific investigation confirms them at each foundation location.
- Isolated pad/strip foundations are assumed adequate; piling is not anticipated unless the ground model or loading indicates otherwise.

**Risk flags:**

- **[MEDIUM] [temporary_works]** Foundation excavation for platform/walkway supports may require temporary excavation support depending on depth and ground conditions — not assessed by the permanent foundation/base plate design itself. (trigger: Any foundation involves an excavated construction stage distinct from the permanent buried condition.) — recommended action: Confirm excavation depth against the geotechnical ground model (calcs/geotechnical/) and safe unsupported-excavation guidance; involve a temporary works designer if in doubt.

**Exclusions:**

- Piled foundation design — only introduced if pad/strip foundations prove inadequate; not designed by default.

**Interfaces:**

- **geotechnical**: Bearing resistance for platform/walkway support foundations — see calcs/geotechnical/.

**Calculations required:**

- Base plate / holding-down bolt design — to BS EN 1993-1-8 (not yet built)

**Deliverables:**

- Foundation/base plate general arrangement drawing (drawing)
- Foundation design calculation report (calculation report)

## Primary steel frame

Supporting steelwork (beams, columns, bracing) for platforms and walkways.

**Applicable standards:**

- BS EN 1993-1-1 (UK NA) — General rules and rules for buildings
- BS EN 1993-1-8 (UK NA) — Design of joints

**Design criteria:**

- Vertical deflection limit (platforms): span/200 — Typical serviceability limit for industrial access platforms — confirm against project-specific serviceability requirements.
- Steel grade: S355 — Typical structural steel grade for this application — confirm availability/preference with the fabricator.
- Wind loading basis: to be confirmed from BS EN 1991-1-4 site parameters — Standard UK inland site assumed as a default; coastal/exposed/high-altitude sites require a site-specific wind assessment.

**Assumptions:**

- Wind loading is assumed derivable from standard UK terrain/altitude parameters; a site-specific wind assessment is assumed only necessary for coastal/exposed/high-altitude sites.

**Risk flags:**

- **[HIGH] [temporary_works]** The frame design assumes the complete, fully-connected, fully-braced structure — intermediate erection stages (before all bracing/connections are made) are not automatically stable and are a distinct design case. (trigger: Steelwork is erected member-by-member; the design's stability assumptions only hold once erection is complete.) — recommended action: Temporary works designer/erection contractor to verify stability at each erection stage (see temporary_works section) — do not assume the permanent design covers construction-stage stability.

**Exclusions:**

- Seismic design of the primary frame — see design_standards_and_criteria exclusions.

**Calculations required:**

- Beam/column member capacity checks — to BS EN 1993-1-1 (not yet built)
- Connection design — to BS EN 1993-1-8 (not yet built)

**Deliverables:**

- Steelwork general arrangement drawing (drawing)
- Member/connection design calculation report (calculation report)

## Platforms and walkways

Decking/flooring specification and loading for working platforms and walkways.

**Applicable standards:**

- BS EN ISO 14122-2 — Safety of machinery — permanent means of access — working platforms and walkways
- BS EN 1991-1-1 (UK NA) _Imposed load requirements for platforms/walkways._
- BS 4592 _Industrial type flooring, walkways and stair treads (grating/chequer plate specification) — confirm current part/edition._

**Design criteria:**

- Minimum clear walkway width: 600 mm — BS EN ISO 14122-2 minimum for a walkway — confirm exact figure and whether a wider width applies for maintenance access/escape route requirements.
- Uniformly distributed load: 5.0 kN/m² — Typical industrial platform/walkway loading — confirm against actual use (access/maintenance only vs. laydown/storage).
- Concentrated (point) load: 1.5 kN — Typical minimum concentrated load check on decking/grating, applied over a nominal contact area — confirm against BS 4592/project spec.

**Assumptions:**

- Platform/walkway use is classified as pedestrian access and maintenance only, not material storage or laydown, unless stated otherwise for a specific platform.

**Risk flags:**

- **[HIGH] [safety]** Working at height before permanent fall protection (handrails/guard-rails) is installed is a distinct installation-sequence safety risk, separate from the completed platform's design. (trigger: Decking/grating is typically installed before its permanent guard-rails are fitted.) — recommended action: Define temporary edge protection or fall-arrest requirements for the installation sequence, coordinated with the handrails_and_guardrails section.

**Exclusions:**

- Fork-lift truck or other vehicle loading — not included unless a specific platform is explicitly required to carry it.

**Calculations required:**

- Deck/grating loading and deflection check — to BS EN 1991-1-1 (not yet built)

**Deliverables:**

- Platform/walkway general arrangement drawing (drawing)
- Deck/grating specification schedule (schedule)

## Stairs and ladders

Geometry (pitch, rise/going) and loading for stairs, stepladders, and fixed ladders providing access.

**Applicable standards:**

- BS EN ISO 14122-3 — Stairs, stepladders and guard-rails
- BS EN ISO 14122-4 — Fixed ladders

**Design criteria:**

- Stair pitch (preferred range): 30–38° — Typical permissible range for industrial stairs per BS EN ISO 14122-3 — confirm exact limits and any steeper-pitch/stepladder allowance.
- Fixed ladder pitch: 75–90° — BS EN ISO 14122-4 range for a fixed ladder (as opposed to a stepladder or stair) — confirm exact boundary values.
- Minimum clear stair/ladder width: 600 mm — Confirm exact figure per part and any escape-route width uplift.

**Assumptions:**

- Stairs are used in preference to ladders wherever headroom/space allows, following the EN ISO 14122 access-equipment hierarchy (platforms > stairs > stepladders > fixed ladders).

**Exclusions:**

- Powered/mobile access equipment (mobile elevated work platforms, scaffold towers) — not part of a fixed access structure design.

**Deliverables:**

- Stair/ladder general arrangement drawing (drawing)
- Stair/ladder calculation report (calculation report)

## Handrails and guard-rails

Guard-rail/handrail height, loading, gap limits, and toe-boards for platforms, walkways, and stairs.

**Applicable standards:**

- BS EN ISO 14122-3 _Guard-rail requirements — shared with the stairs/ladders section._
- BS 6180 _Barriers in and about buildings — may apply instead of/alongside EN ISO 14122-3 depending on building-vs-machinery classification; confirm which governs per installation._

**Design criteria:**

- Guard-rail top height: 1100 mm — Minimum per BS EN ISO 14122-3 — confirm exact figure and any higher requirement from a client standard.
- Guard-rail horizontal design load: 0.3–1.0 kN/m — Range depends on classification/exposure per BS EN ISO 14122-3 — confirm the governing value for the specific installation.
- Maximum gap (mid-rail/toe-board): 500 mm — Typical maximum unprotected gap — confirm exact figure, including toe-board height requirement.

**Assumptions:**

- Guard-rails/handrails are assumed required on all open edges with a fall height above the generic UK work-at-height threshold (typically 2m, but risk-assessed case by case).

**Exclusions:**

- Glazed or solid balustrade panel systems (an architectural feature) — this section covers open guard-rail/handrail systems only.

**Calculations required:**

- Guard-rail horizontal load check — to BS EN ISO 14122-3 (not yet built)

**Deliverables:**

- Handrail/guard-rail general arrangement drawing (drawing)
- Handrail/guard-rail load calculation (calculation report)

## Structural integrity and robustness

Robustness considerations scaled to access-structure risk (connection redundancy, corrosion allowance) — not full building disproportionate-collapse design.

**Applicable standards:**

- BS EN 1991-1-7 (UK NA) _Accidental actions — apply only the parts relevant to an access structure, not full building consequence-class robustness._

**Design criteria:**

- Notional horizontal load: 1% — Of vertical load, applied per BS EN 1993-1-1 robustness/imperfection provisions, as a minimum horizontal robustness check — confirm applicability.

**Assumptions:**

- Full building-scale disproportionate-collapse provisions (BS EN 1991-1-7 building consequence classes) are assumed not applicable, given the structure's industrial access use and limited occupancy.

**Exclusions:**

- Progressive collapse / disproportionate collapse analysis for occupied buildings — out of scope, see design_standards_and_criteria exclusions.

**Deliverables:**

- Robustness statement (report)

## Temporary works

Erection/lifting sequence and temporary stability requirements during construction — typically contractor-designed, with performance requirements set here.

**Applicable standards:**

- BS 5975 — Code of practice for temporary works procedures and the permissible stress design of falsework

**Design criteria:**

- Permissible unbraced erection stage duration: to be confirmed by contractor — Not a fixed design value — the erection contractor sets this once the erection method statement is developed, informed by the performance requirements in this section.

**Assumptions:**

- The erection contractor is assumed to hold appropriate temporary works coordination competency (per BS 5975) and to develop the detailed temporary works design themselves.

**Exclusions:**

- Detailed temporary works design itself (falsework calculations, propping schemes, etc.) — the contractor's design responsibility, not produced as part of this basis of design.

**Interfaces:**

- **contractor / temporary works designer**: This section states performance requirements; detailed temporary works design is typically the contractor's responsibility.

**Deliverables:**

- Temporary works performance requirements schedule (schedule) — Handed to the erection contractor as the basis for their own temporary works design.

## Movement, tolerances, and durability

Thermal movement/expansion joints for long walkway runs, construction tolerances, and corrosion protection.

**Applicable standards:**

- BS EN ISO 1461 — Hot dip galvanized coatings on iron and steel articles
- BS EN 1993-1-1 (UK NA) _Corrosion/durability provisions within the general steel design rules._
- BS EN 1090-2 — Execution of steel structures — technical requirements _Governs fabrication/erection tolerances — confirm execution class (EXC1–EXC4) for this structure._
- BS EN ISO 12944 — Corrosion protection of steel structures by protective paint systems _Reference only if a paint system is used instead of/alongside galvanizing._

**Design criteria:**

- Expansion joint spacing (long walkway runs): 30–40 m — Typical spacing subject to a thermal movement calculation — confirm against the actual run length and ambient temperature range for the site.
- Galvanizing minimum coating thickness: 85 microns — Typical minimum per BS EN ISO 1461 for steel over 6mm thick — confirm against actual section thicknesses used.
- Corrosivity environment category: C3 (indoor/covered industrial) — Per BS EN ISO 12944 — confirm category per site; external/coastal sites typically require C4/C5.

**Assumptions:**

- Hot-dip galvanizing to BS EN ISO 1461 is assumed as the default corrosion protection system, rather than a painted/duplex system, unless the project specifies otherwise.

**Exclusions:**

- Painted or duplex (paint-over-galvanizing) coating systems — not included by default; only introduced if specifically required (e.g. for colour-coding or a more aggressive environment).

**Deliverables:**

- Corrosion protection specification (specification)
- Movement joint detail drawing (drawing)

