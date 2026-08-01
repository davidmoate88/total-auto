# HV Electrical — Basis of Design

## Design standards and general criteria

Overarching HV design basis: safety/quality regulations, insulation coordination, system voltage class, fault level, and earthing system philosophy.

**Applicable standards:**

- ESQCR — Electricity Safety, Quality and Continuity Regulations 2002
- BS EN 60071 series — Insulation co-ordination
- Electricity at Work Regulations 1989 _Shared with the LV electrical module._

**Design criteria:**

- HV voltage class: 6.6kV / 11kV / 33kV (kept generic) — Kept generic per project direction — the specific class is confirmed per project from the DNO connection offer/site requirement, not fixed by this basis of design.
- System fault level: to be confirmed from the DNO connection offer/fault level statement — Not calculated independently — obtained from the network operator, since it depends on their upstream network configuration.
- Insulation level (BIL): per BS EN 60071, dependent on voltage class — Basic impulse insulation level — set once the HV voltage class is confirmed for the project.

**Assumptions:**

- The specific HV voltage class is assumed to be confirmed per project rather than fixed by this basis of design, per the generic-across-voltage-classes scope decision.
- System fault level is assumed to be obtained from the DNO's connection offer/fault level statement rather than calculated independently.

**Exclusions:**

- Commitment to a specific HV voltage class — deliberately kept generic per project direction; see module docstring.

**Deliverables:**

- HV electrical design basis statement (report)
- Single line diagram (HV) (drawing)

## HV incoming supply and connection

DNO/IDNO connection agreement, point of connection, and metering.

**Applicable standards:**

- ENA Engineering Recommendations _Confirm which specific EREC applies (connection design/planning) for the network operator involved._

**Design criteria:**

- Connection point: to be confirmed via DNO connection application — Set by the DNO's connection offer once submitted — not a value this basis of design can set independently.
- Metering arrangement: HV metering (CT/VT metering) — Typical arrangement for a direct HV connection — confirm against the specific network operator's metering requirements.

**Assumptions:**

- A new HV connection is assumed required (rather than an extension of an existing private HV network) unless site information indicates otherwise.

**Exclusions:**

- The DNO's own upstream network reinforcement — outside this project's design scope, even where it's a consequence of the new connection.

**Interfaces:**

- **utilities_coordination**: New HV supply connection coordinated with the DNO (civils basis of design).

**Deliverables:**

- Connection agreement/application pack (report)
- Metering arrangement drawing (drawing)

## Substations and switchgear

HV switchgear (ring main units, circuit breakers) and substation buildings/enclosures.

**Applicable standards:**

- BS EN 62271 series — High-voltage switchgear and controlgear
- BS 7354 — Design of high-voltage open-terminal stations

**Design criteria:**

- Switchgear topology: ring main unit (RMU), single incoming supply (provisional) — Typical for a single HV connection — confirm ring/radial topology against the site's actual reliability/redundancy requirement.
- Substation ingress protection: to be confirmed (indoor building vs. outdoor enclosure) — Set once the substation location/type is fixed with civils/structural.

**Assumptions:**

- Substation location and space allowance are assumed to be coordinated with civils and structural, pending a confirmed site layout.

**Risk flags:**

- **[MEDIUM] [temporary_works]** Cutting over from an existing supply/switchgear to a new substation is typically a distinct, carefully sequenced temporary/parallel-operation condition (with defined outage windows) — not covered by the completed, permanent switchgear design on its own. (trigger: Any substation replacement/extension involves a transition period between the existing and new arrangement.) — recommended action: Define the cutover/energisation sequence and outage requirements explicitly, coordinated with the site's Authorised Person regime.

**Exclusions:**

- SF6 environmental/phase-out considerations for gas-insulated switchgear — only addressed if a specific supplier or environmental policy requires it.

**Interfaces:**

- **civils**: Substation building/enclosure foundations and access.

**Deliverables:**

- Substation general arrangement drawing (drawing)
- Switchgear specification (specification)

## Transformers

HV/LV transformers stepping down to the LV distribution system.

**Applicable standards:**

- BS EN 60076 series — Power transformers

**Design criteria:**

- Transformer rating: to be confirmed from the LV load schedule plus diversity — Cannot be finalised independently of basis_of_design/electrical_lv.py's load schedule and diversity assumptions.
- Vector group: Dyn11 — Typical for UK industrial HV/LV step-down distribution transformers — confirm against the specific earthing arrangement decided in hv_earthing_and_touch_step_potential.
- Cooling class: ONAN (oil-natural air-natural) — Typical for this rating range — forced-air cooling (ONAF) only considered if a higher rating requires it.

**Assumptions:**

- An oil-filled transformer is assumed as the default; a dry-type transformer is only assumed necessary if a specific fire/environmental constraint applies (e.g. an indoor plant room with restricted oil containment).

**Exclusions:**

- Dry-type transformer design — not included by default (oil-filled is assumed); only added if a specific project constraint requires it.

**Interfaces:**

- **electrical_lv**: Transformer secondary is the supply origin for LV distribution — see basis_of_design/electrical_lv.py.

**Deliverables:**

- Transformer schedule (schedule)
- Transformer bay/plinth general arrangement drawing (drawing)

## Protection and control

Protection relays and discrimination/grading studies.

**Applicable standards:**

- BS EN 60255 series — Measuring relays and protection equipment

**Design criteria:**

- Protection grading margin: 0.2–0.4 s — Typical discrimination margin between successive protection stages — confirm against the project's protection philosophy and relay manufacturer's recommendations.
- Protection relay technology: numerical/IED — Modern default over electromechanical relays — confirm compatibility with any existing site protection scheme being extended.

**Assumptions:**

- A standard radial discrimination protection philosophy is assumed, rather than a loop/ring protection scheme, unless the site's supply topology requires otherwise.

**Exclusions:**

- SCADA/remote control system integration — assumed to sit under a separate controls/instrumentation scope, unless explicitly required as part of this HV protection and control section.

**Calculations required:**

- Protection discrimination/grading study: Confirms protection devices operate selectively across the HV/LV system. (not yet built)

**Deliverables:**

- Protection and discrimination study report (calculation report)
- Protection relay settings schedule (schedule)

## HV cabling and cable management

HV cable specification and routing.

**Applicable standards:**

- BS 6622 — Cables with extruded insulation for rated voltages up to 33kV _Confirm current part/edition._
- BS 7870 series — LV and MV polymeric insulated cables _Confirm applicable parts._

**Design criteria:**

- Cable insulation/conductor: XLPE insulated, copper or aluminium conductor (to be confirmed) — Conductor material is typically a cost/weight trade-off decision — confirm project preference.
- Minimum bending radius: 12–15x cable diameter (typical for XLPE HV cable) — Confirm against the specific cable manufacturer's data sheet once a cable is selected.

**Assumptions:**

- Cable route length/topology is assumed to be coordinated with civils utilities coordination and structural cable management, pending a routing study once the site layout is confirmed.

**Exclusions:**

- Submarine/subsea cable design — not applicable to this land-based industrial scope.

**Interfaces:**

- **civils**: Cable route/ducting coordinated with earthworks and utilities.

**Deliverables:**

- HV cable route drawing (drawing)
- HV cable schedule (schedule)

## HV earthing and touch/step potential

Substation earthing design, distinct from the LV earthing and bonding section — governed by touch/step potential criteria specific to HV.

**Applicable standards:**

- BS EN 50522 — Earthing of power installations exceeding 1kV AC
- ENA EREC S34 — A guide for assessing the rise of earth potential at substation sites _Confirm current designation/edition._
- BS 7354 _Shared with substations/switchgear — earthing design for open-terminal stations._

**Design criteria:**

- Touch/step potential limits: per BS EN 50522, based on fault clearance time and body resistance model — No single project-wide figure — calculated from the specific fault clearance time and earthing arrangement once the protection study is complete.
- Substation earth resistance target: to be confirmed from soil resistivity survey and earth grid design — Cannot be set without a site-specific soil resistivity survey — see assumptions.

**Assumptions:**

- Earth grid design is assumed to require a soil resistivity survey (multi-layer Wenner test) rather than an assumed single value, given the safety-critical nature of touch/step potential compliance.

**Risk flags:**

- **[HIGH] [safety]** Whether the HV and LV earthing systems are combined or kept separate is a safety-critical decision (risk of a HV earth fault transferring a dangerous potential rise onto LV equipment/exposed metalwork) governed by BS EN 50522 — it must be explicitly assessed, not assumed by default. (trigger: Any site with both HV and LV earthing systems present.) — recommended action: Explicitly assess and document the combined-vs-separate earthing decision per BS EN 50522, informed by soil resistivity data.

**Exclusions:**

- Rise of earth potential (REOP) transfer risk to telecoms/other networks beyond the site boundary — only assessed if a specific interface is identified (an ENA EREC S36-style transferred REOP assessment).

**Interfaces:**

- **geotechnical**: Soil resistivity drives earth electrode design — see calcs/geotechnical/.
- **electrical_lv**: Whether HV and LV earthing systems are combined or kept separate is decided here.

**Deliverables:**

- HV earthing design report (report)
- Earth grid layout drawing (drawing)

## Arc flash and HV safety

HV-specific safe isolation procedures and arc flash risk — typically far more severe consequence than LV.

**Applicable standards:**

- HSG85 _Shared with LV electrical — HSE guidance, electricity at work safe working practices._
- BS EN 50110-1 _Shared with LV electrical — operation of electrical installations._

**Design criteria:**

- HV arc flash calculation method: to be confirmed — IEEE 1584 or an equivalent HV-specific method — Confirm which method/tool is used for the incident energy calculation; not all LV-oriented tools extend cleanly to HV switchgear.
- Minimum PPE category for HV switching: to be confirmed from the study — Typically a higher category than the equivalent LV assessment — set once the HV-specific study is complete.

**Assumptions:**

- HV switching operations are assumed to be carried out only by an Authorised Person under the site's Safety Rules regime, not general electrical staff.

**Risk flags:**

- **[HIGH] [safety]** HV arc flash incident energy levels are typically far higher than LV — PPE categorisation and safe working procedures need a dedicated HV assessment, not an assumption that the LV arc flash study or PPE category carries over. (trigger: Any HV switchgear/switching operation.) — recommended action: Commission a dedicated HV arc flash study; do not extrapolate from an LV assessment.

**Exclusions:**

- LV arc flash assessment — covered separately under basis_of_design/electrical_lv.py, not merged into this HV-specific study.

**Deliverables:**

- HV arc flash risk assessment report (report)
- Safety Rules / Authorised Person procedure document (report)

