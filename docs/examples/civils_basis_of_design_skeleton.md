# Civils — Basis of Design

## Site and existing conditions

Topographic survey, existing levels, boundaries, and existing utility records — the baseline all other civils elements are measured against.

**Interfaces:**

- **geotechnical**: Existing ground levels needed to establish founding depths and overburden.
- **architectural**: Existing levels constrain finished floor levels and external works design.

## Earthworks and ground remediation

Cut/fill balance, temporary and permanent slope stability, and any ground remediation strategy.

**Applicable standards:**

- BS 6031 — Code of practice for earthworks
- BS EN 1997-1 (UK NA) _Shared with the geotechnical module — slope stability and retaining checks._
- CIRIA C552 _Contaminated land risk assessment / remediation guidance — confirm current CIRIA reference._

**Risk flags:**

- **[HIGH] [temporary_works]** Temporary excavation slopes and any temporary retaining/support during earthworks are a separate design case from the permanent condition — the permanent cut/fill and slope stability design does not itself validate that the construction-stage excavation is safe. (trigger: Any earthworks section by nature involves a temporary excavated condition before the permanent profile/remediation is complete.) — recommended action: Temporary works designer/contractor to assess temporary slope stability per BS 6031 against actual ground conditions and construction sequence.

**Interfaces:**

- **geotechnical**: Ground model (strata, water table) drives cut/fill and slope stability checks — see calcs/geotechnical/.
- **structural**: Remediation strategy may affect founding levels/type.

**Calculations required:**

- Cut/fill balance: Earthwork volumes across the site. (not yet built)
- Slope stability check — to BS EN 1997-1 (not yet built)

## Foul drainage

Foul water strategy, pipe sizing/capacity, and adoption standards.

**Applicable standards:**

- Sewers for Adoption _Confirm current edition — 7th/8th ed. depending on the servicing water company._
- BS EN 752 — Drain and sewer systems outside buildings
- Building Regulations Part H _England & Wales — confirm applicability by jurisdiction._

**Calculations required:**

- Foul flow calculation: Peak foul flow from occupancy/use, pipe sizing. (not yet built)

## Surface water drainage / SuDS

Attenuation sizing, discharge rate limits, climate change allowances, and SuDS/adoption standards — typically the largest civils calculation deliverable.

**Applicable standards:**

- CIRIA C753 — The SuDS Manual
- Non-statutory technical standards for SuDS _Defra — confirm current status/supersession._
- Sewers for Adoption _Confirm current edition._
- BS EN 752

**Interfaces:**

- **geotechnical**: Infiltration rate / ground conditions determine SuDS feasibility (soakaways etc.).
- **flood_risk**: Discharge rate and climate change allowance are usually set by the FRA.

**Calculations required:**

- Attenuation volume sizing: Storage required to limit discharge to the agreed rate. (not yet built)
- Discharge rate calculation: Greenfield/brownfield runoff rate per the governing standard. (not yet built)

## Flood risk

Flood Risk Assessment (FRA) requirements, finished floor levels, and climate change allowances.

**Applicable standards:**

- NPPF — National Planning Policy Framework _Flood risk sequential/exception test provisions._
- EA climate change allowances guidance _Confirm current published allowances at time of use — these are updated periodically._

**Interfaces:**

- **architectural**: Finished floor levels are typically set from FRA outputs.
- **surface_water_drainage_suds**: Climate change allowance and discharge rate constraints flow into SuDS sizing.

## Highways and access

Site access geometry, visibility splays, junction design, and adoption standards for any new/altered highway.

**Applicable standards:**

- Manual for Streets _MfS / MfS2 — confirm which applies by road classification/authority._
- DMRB — Design Manual for Roads and Bridges _Where the interface is with a trunk road/strategic network._

## External works and pavements

Hard and soft landscaping, and pavement design/loading for roads, parking, and hardstanding.

**Applicable standards:**

- Manual of Contract Documents for Highway Works (MCHW) _For adoptable road pavement specification._
- DMRB CD 226 _Pavement design — confirm current designation, this series is renumbered periodically._

## Utilities coordination

Existing service diversions and new utility connections, coordinated with statutory undertakers.

**Applicable standards:**

- HSG47 — Avoiding Danger from Underground Services _HSE guidance._

**Interfaces:**

- **mechanical_piping**: New utility connections (water, gas) interface with mechanical services entering the building.
- **electrical_lv**: New electrical supply connections coordinated with the DNO.

## Retaining structures

Design of retaining walls/structures — sits on the civils/structural/geotechnical boundary.

**Applicable standards:**

- BS EN 1997-1 (UK NA) _Shared with the geotechnical module._
- CIRIA C760 _Embedded retaining wall design guidance — confirm current CIRIA reference/edition._
- BS EN 1992-1-1 (UK NA) _If reinforced concrete — structural interface._

**Risk flags:**

- **[HIGH] [temporary_works]** Retaining structures very commonly require a staged/propped temporary condition before the permanent structure (permanent props, slab, or anchors) is complete — that temporary condition can be more critical than the permanent one, and is easy to overlook if only the finished structure is designed. (trigger: Retaining wall design typically assumes the completed, fully-propped/anchored condition; intermediate construction stages carry different (often more severe) loading.) — recommended action: Temporary works designer to verify stability at every construction stage, not just the permanent completed condition.

**Interfaces:**

- **geotechnical**: Lateral earth pressures and bearing checks — extends calcs/geotechnical/.
- **structural**: Structural design of the retaining element itself.

**Calculations required:**

- Lateral earth pressure calculation — to BS EN 1997-1 (not yet built)
- Retaining wall stability (sliding/overturning/bearing) — to BS EN 1997-1 (not yet built)

