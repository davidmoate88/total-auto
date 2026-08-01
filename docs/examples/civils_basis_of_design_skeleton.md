# Civils — Basis of Design

## Site and existing conditions

Topographic survey, existing levels, boundaries, and existing utility records — the baseline all other civils elements are measured against.

**Design criteria:**

- Survey vertical accuracy: ±10 mm — Typical topographic survey tolerance — confirm against the project survey brief.
- Survey horizontal accuracy: ±20 mm
- Survey datum: Ordnance Survey Newlyn Datum (OSGB36) — Confirm project datum — some sites use a local site grid instead.
- Utility survey quality level: PAS 128 Quality Level B/A — Target verification level for buried service records before detailed design proceeds.

**Assumptions:**

- Existing statutory undertaker utility records are indicative only until verified by trial holes/GPR survey (PAS 128).
- No presumption of undiscovered services is made until a PAS 128 survey is complete.

**Exclusions:**

- Detailed measured building survey of existing structures — assumed covered by the architectural/structural survey scope.

**Interfaces:**

- **geotechnical**: Existing ground levels needed to establish founding depths and overburden.
- **architectural**: Existing levels constrain finished floor levels and external works design.

**Deliverables:**

- Topographic survey drawing (drawing)
- Existing utility record drawing (drawing) — Composite of all statutory undertaker records obtained.
- Site boundary / red line plan (drawing)

## Earthworks and ground remediation

Cut/fill balance, temporary and permanent slope stability, and any ground remediation strategy.

**Applicable standards:**

- BS 6031 — Code of practice for earthworks
- BS EN 1997-1 (UK NA) _Shared with the geotechnical module — slope stability and retaining checks._
- CIRIA C552 _Contaminated land risk assessment / remediation guidance — confirm current CIRIA reference._

**Design criteria:**

- Permanent slope angle: to be confirmed from ground model — Set per BS 6031 once characteristic ground parameters are available from calcs/geotechnical/.
- Cut/fill tolerance: ±0 m³ — Target a balanced cut/fill unless import/export is explicitly agreed — reduces haulage cost/risk.
- Contamination screening trigger: Phase 1 desk study — Threshold for commissioning a Phase 2 intrusive investigation, per CLR11-style guidance.

**Assumptions:**

- Site-won material is assumed suitable for reuse as engineered fill, subject to geotechnical testing confirming it.
- No contamination is assumed present unless a Phase 1 desk study identifies a plausible source-pathway-receptor linkage.

**Risk flags:**

- **[HIGH] [temporary_works]** Temporary excavation slopes and any temporary retaining/support during earthworks are a separate design case from the permanent condition — the permanent cut/fill and slope stability design does not itself validate that the construction-stage excavation is safe. (trigger: Any earthworks section by nature involves a temporary excavated condition before the permanent profile/remediation is complete.) — recommended action: Temporary works designer/contractor to assess temporary slope stability per BS 6031 against actual ground conditions and construction sequence.

**Exclusions:**

- Detailed remediation design/validation (specialist remediation contractor scope) — this section covers strategy only, not detailed remediation engineering.

**Interfaces:**

- **geotechnical**: Ground model (strata, water table) drives cut/fill and slope stability checks — see calcs/geotechnical/.
- **structural**: Remediation strategy may affect founding levels/type.

**Calculations required:**

- Cut/fill balance: Earthwork volumes across the site. (not yet built)
- Slope stability check — to BS EN 1997-1 (not yet built)

**Deliverables:**

- Earthworks specification (specification)
- Cut/fill volume schedule (schedule)
- Remediation strategy report (report) — Only where contamination risk is identified.

## Foul drainage

Foul water strategy, pipe sizing/capacity, and adoption standards.

**Applicable standards:**

- Sewers for Adoption _Confirm current edition — 7th/8th ed. depending on the servicing water company._
- BS EN 752 — Drain and sewer systems outside buildings
- Building Regulations Part H _England & Wales — confirm applicability by jurisdiction._

**Design criteria:**

- Minimum self-cleansing velocity: 0.75 m/s — Typical Sewers for Adoption / Building Regs criterion at design flow.
- Minimum cover depth (adoptable): 1.2 m — Typical under highway — confirm against the specific water company's design/construction guidance.
- Minimum pipe gradient: 1:80 (150mm dia.) — Illustrative — actual minimum gradient is diameter-dependent per the governing standard.

**Assumptions:**

- Foul flow rates are based on occupancy/use rates per BS EN 752 / Sewers for Adoption guidance, to be confirmed once an occupancy schedule is available.
- Connection to the existing public foul sewer is assumed available at adequate capacity — to be confirmed by a sewer capacity check/pre-development enquiry with the water company.

**Exclusions:**

- Trade effluent pre-treatment design — specialist scope, only required if a trade effluent consent is triggered.

**Calculations required:**

- Foul flow calculation: Peak foul flow from occupancy/use, pipe sizing. (not yet built)

**Deliverables:**

- Foul drainage layout drawing (drawing)
- Foul drainage calculation report (calculation report)
- Sewer adoption submission pack (report) — Only where the network is to be offered for adoption (S104 or equivalent).

## Surface water drainage / SuDS

Attenuation sizing, discharge rate limits, climate change allowances, and SuDS/adoption standards — typically the largest civils calculation deliverable.

**Applicable standards:**

- CIRIA C753 — The SuDS Manual
- Non-statutory technical standards for SuDS _Defra — confirm current status/supersession._
- Sewers for Adoption _Confirm current edition._
- BS EN 752

**Design criteria:**

- Discharge rate: Greenfield QBAR (or local authority/LLFA-specified rate) — Confirm the governing rate with the Lead Local Flood Authority — some set a fixed litres/second/hectare cap instead.
- Climate change allowance: to be confirmed against current EA guidance — These published allowances are updated periodically — do not hard-code a percentage without checking the current figure.
- Design storm return period (attenuation): 1 in 100 year + climate change — With a 1 in 30 year check for surcharge-free performance, per common SuDS practice.
- SuDS management train priority: Infiltration > attenuation/detention > controlled discharge — Per the CIRIA C753 SuDS hierarchy — confirm feasibility of each tier before committing to the next.

**Assumptions:**

- Infiltration testing (BRE Digest 365 falling-head test) is assumed required to confirm SuDS feasibility, pending the ground model.
- Existing surface water sewer/watercourse is assumed to have available capacity for any residual controlled discharge, pending confirmation.

**Exclusions:**

- Long-term SuDS maintenance/adoption legal agreement drafting — a legal, not engineering, deliverable (the maintenance schedule itself is still produced, see deliverables).

**Interfaces:**

- **geotechnical**: Infiltration rate / ground conditions determine SuDS feasibility (soakaways etc.).
- **flood_risk**: Discharge rate and climate change allowance are usually set by the FRA.

**Calculations required:**

- Attenuation volume sizing: Storage required to limit discharge to the agreed rate. (not yet built)
- Discharge rate calculation: Greenfield/brownfield runoff rate per the governing standard. (not yet built)

**Deliverables:**

- Drainage strategy report (report)
- Attenuation sizing calculation (calculation report)
- SuDS maintenance schedule (schedule)

## Flood risk

Flood Risk Assessment (FRA) requirements, finished floor levels, and climate change allowances.

**Applicable standards:**

- NPPF — National Planning Policy Framework _Flood risk sequential/exception test provisions._
- EA climate change allowances guidance _Confirm current published allowances at time of use — these are updated periodically._

**Design criteria:**

- Finished floor level freeboard: 300 mm — Typical minimum above the design flood level (1 in 100 year + climate change) — confirm against the LLFA/EA's specific requirement for the site.
- Flood zone classification: to be confirmed from the current EA flood map — Drives whether a full FRA and sequential/exception test are required at all.

**Assumptions:**

- The site is provisionally assumed Flood Zone 1 (low probability) pending confirmation from the current EA flood map for planning.

**Exclusions:**

- Detailed hydraulic/hydrological modelling of adjacent watercourses — specialist flood consultant scope, only required if the site interacts directly with a modelled watercourse.

**Interfaces:**

- **architectural**: Finished floor levels are typically set from FRA outputs.
- **surface_water_drainage_suds**: Climate change allowance and discharge rate constraints flow into SuDS sizing.

**Deliverables:**

- Flood Risk Assessment report (report)
- Finished floor level drawing (drawing)

## Highways and access

Site access geometry, visibility splays, junction design, and adoption standards for any new/altered highway.

**Applicable standards:**

- Manual for Streets _MfS / MfS2 — confirm which applies by road classification/authority._
- DMRB — Design Manual for Roads and Bridges _Where the interface is with a trunk road/strategic network._

**Design criteria:**

- Visibility splay (x-distance): 2.4 m — Typical stopping-sight-distance x-dimension per Manual for Streets — y-distance depends on design speed and must be set per site.
- Design vehicle for swept path: to be confirmed (e.g. articulated HGV, fire tender) — Governs junction/access geometry — set once the site's servicing/emergency access requirements are known.

**Assumptions:**

- Access design assumes the current posted speed limit/classification of the adjoining highway applies, unless a Stage 1 Road Safety Audit indicates otherwise.

**Exclusions:**

- Traffic impact assessment / transport statement — specialist transport planner scope, not produced by this civils BoD.

**Deliverables:**

- Access/junction general arrangement drawing (drawing)
- Swept path analysis drawings (drawing)
- Visibility splay drawing (drawing)

## External works and pavements

Hard and soft landscaping, and pavement design/loading for roads, parking, and hardstanding.

**Applicable standards:**

- Manual of Contract Documents for Highway Works (MCHW) _For adoptable road pavement specification._
- DMRB CD 226 _Pavement design — confirm current designation, this series is renumbered periodically._

**Design criteria:**

- Pavement design life: 40 years — Typical for an adoptable road — private hardstanding may use a shorter design life, confirm per area.
- Design traffic loading: to be confirmed msa (million standard axles) — Set from the actual traffic/servicing regime for the site, per DMRB CD 226.

**Assumptions:**

- Subgrade CBR value is assumed from the geotechnical ground model, pending confirmation by in-situ/laboratory CBR testing.

**Exclusions:**

- Soft landscape planting design — landscape architect scope.

**Deliverables:**

- Pavement construction detail drawings (drawing)
- External works layout drawing (drawing)

## Utilities coordination

Existing service diversions and new utility connections, coordinated with statutory undertakers.

**Applicable standards:**

- HSG47 — Avoiding Danger from Underground Services _HSE guidance._

**Design criteria:**

- Minimum service clearance (crossing): to be confirmed per NJUG/street works guidance — Depends on the specific pair of services crossing — no single figure applies across all combinations.

**Assumptions:**

- Existing utility positions are assumed per statutory undertaker records until physically verified by trial holes/GPR survey.

**Exclusions:**

- Detailed design of the utility company's own network upstream of the site connection point.

**Interfaces:**

- **mechanical_piping**: New utility connections (water, gas) interface with mechanical services entering the building.
- **electrical_lv**: New electrical supply connections coordinated with the DNO.

**Deliverables:**

- Utilities coordination drawing (drawing) — Composite of all services, new and existing.
- Service diversion strategy (report) — Only where an existing service must be diverted.

## Retaining structures

Design of retaining walls/structures — sits on the civils/structural/geotechnical boundary.

**Applicable standards:**

- BS EN 1997-1 (UK NA) _Shared with the geotechnical module._
- CIRIA C760 _Embedded retaining wall design guidance — confirm current CIRIA reference/edition._
- BS EN 1992-1-1 (UK NA) _If reinforced concrete — structural interface._

**Design criteria:**

- Design working life category: 50 years — BS EN 1990 category 4 (typical for building-associated structures) — confirm if a different category applies.
- Surcharge loading allowance: to be confirmed kN/m² — Set from actual adjacent loading (traffic, storage, plant) once the layout is known — do not assume a nominal figure without checking.

**Assumptions:**

- Retaining wall type (e.g. gravity, embedded cantilever, propped) is assumed to be determined by height and space constraints, to be confirmed once the layout is finalised.

**Risk flags:**

- **[HIGH] [temporary_works]** Retaining structures very commonly require a staged/propped temporary condition before the permanent structure (permanent props, slab, or anchors) is complete — that temporary condition can be more critical than the permanent one, and is easy to overlook if only the finished structure is designed. (trigger: Retaining wall design typically assumes the completed, fully-propped/anchored condition; intermediate construction stages carry different (often more severe) loading.) — recommended action: Temporary works designer to verify stability at every construction stage, not just the permanent completed condition.

**Exclusions:**

- Detailed reinforcement/connection detailing — that is calc/detail-stage output, not part of this basis of design.

**Interfaces:**

- **geotechnical**: Lateral earth pressures and bearing checks — extends calcs/geotechnical/.
- **structural**: Structural design of the retaining element itself.

**Calculations required:**

- Lateral earth pressure calculation — to BS EN 1997-1 (not yet built)
- Retaining wall stability (sliding/overturning/bearing) — to BS EN 1997-1 (not yet built)

**Deliverables:**

- Retaining structure calculation report (calculation report)
- Retaining structure general arrangement drawing (drawing)

