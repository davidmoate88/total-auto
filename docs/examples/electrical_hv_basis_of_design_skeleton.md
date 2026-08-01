# HV Electrical — Basis of Design

## Design standards and general criteria

Overarching HV design basis: safety/quality regulations, insulation coordination, system voltage class, fault level, and earthing system philosophy.

**Applicable standards:**

- ESQCR — Electricity Safety, Quality and Continuity Regulations 2002
- BS EN 60071 series — Insulation co-ordination
- Electricity at Work Regulations 1989 _Shared with the LV electrical module._

## HV incoming supply and connection

DNO/IDNO connection agreement, point of connection, and metering.

**Applicable standards:**

- ENA Engineering Recommendations _Confirm which specific EREC applies (connection design/planning) for the network operator involved._

**Interfaces:**

- **utilities_coordination**: New HV supply connection coordinated with the DNO (civils basis of design).

## Substations and switchgear

HV switchgear (ring main units, circuit breakers) and substation buildings/enclosures.

**Applicable standards:**

- BS EN 62271 series — High-voltage switchgear and controlgear
- BS 7354 — Design of high-voltage open-terminal stations

**Risk flags:**

- **[MEDIUM] [temporary_works]** Cutting over from an existing supply/switchgear to a new substation is typically a distinct, carefully sequenced temporary/parallel-operation condition (with defined outage windows) — not covered by the completed, permanent switchgear design on its own. (trigger: Any substation replacement/extension involves a transition period between the existing and new arrangement.) — recommended action: Define the cutover/energisation sequence and outage requirements explicitly, coordinated with the site's Authorised Person regime.

**Interfaces:**

- **civils**: Substation building/enclosure foundations and access.

## Transformers

HV/LV transformers stepping down to the LV distribution system.

**Applicable standards:**

- BS EN 60076 series — Power transformers

**Interfaces:**

- **electrical_lv**: Transformer secondary is the supply origin for LV distribution — see basis_of_design/electrical_lv.py.

## Protection and control

Protection relays and discrimination/grading studies.

**Applicable standards:**

- BS EN 60255 series — Measuring relays and protection equipment

**Calculations required:**

- Protection discrimination/grading study: Confirms protection devices operate selectively across the HV/LV system. (not yet built)

## HV cabling and cable management

HV cable specification and routing.

**Applicable standards:**

- BS 6622 — Cables with extruded insulation for rated voltages up to 33kV _Confirm current part/edition._
- BS 7870 series — LV and MV polymeric insulated cables _Confirm applicable parts._

**Interfaces:**

- **civils**: Cable route/ducting coordinated with earthworks and utilities.

## HV earthing and touch/step potential

Substation earthing design, distinct from the LV earthing and bonding section — governed by touch/step potential criteria specific to HV.

**Applicable standards:**

- BS EN 50522 — Earthing of power installations exceeding 1kV AC
- ENA EREC S34 — A guide for assessing the rise of earth potential at substation sites _Confirm current designation/edition._
- BS 7354 _Shared with substations/switchgear — earthing design for open-terminal stations._

**Risk flags:**

- **[HIGH] [safety]** Whether the HV and LV earthing systems are combined or kept separate is a safety-critical decision (risk of a HV earth fault transferring a dangerous potential rise onto LV equipment/exposed metalwork) governed by BS EN 50522 — it must be explicitly assessed, not assumed by default. (trigger: Any site with both HV and LV earthing systems present.) — recommended action: Explicitly assess and document the combined-vs-separate earthing decision per BS EN 50522, informed by soil resistivity data.

**Interfaces:**

- **geotechnical**: Soil resistivity drives earth electrode design — see calcs/geotechnical/.
- **electrical_lv**: Whether HV and LV earthing systems are combined or kept separate is decided here.

## Arc flash and HV safety

HV-specific safe isolation procedures and arc flash risk — typically far more severe consequence than LV.

**Applicable standards:**

- HSG85 _Shared with LV electrical — HSE guidance, electricity at work safe working practices._
- BS EN 50110-1 _Shared with LV electrical — operation of electrical installations._

**Risk flags:**

- **[HIGH] [safety]** HV arc flash incident energy levels are typically far higher than LV — PPE categorisation and safe working procedures need a dedicated HV assessment, not an assumption that the LV arc flash study or PPE category carries over. (trigger: Any HV switchgear/switching operation.) — recommended action: Commission a dedicated HV arc flash study; do not extrapolate from an LV assessment.

