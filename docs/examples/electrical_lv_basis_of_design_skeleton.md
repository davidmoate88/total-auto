# LV Electrical — Basis of Design

## Design standards and general criteria

Overarching LV electrical design basis: wiring regulations, safety regulations, earthing system, and general criteria (voltage/frequency, diversity).

**Applicable standards:**

- BS 7671 — Requirements for Electrical Installations (IET Wiring Regulations) _Confirm current edition/amendment._
- Electricity at Work Regulations 1989
- BS EN 61439-1 — Low-voltage switchgear and controlgear assemblies — general rules

**Design criteria:**

- System voltage: 400/230 V — Standard UK three-phase/single-phase LV distribution voltage — confirm against the actual DNO supply/transformer secondary voltage.
- System frequency: 50 Hz
- Earthing system: TN-S (provisional) — Typical industrial arrangement fed from a dedicated transformer — the actual system depends on the HV/LV earthing decision made in basis_of_design/electrical_hv.py; confirm once that's settled.

**Assumptions:**

- Standard UK LV supply parameters (400/230V, 50Hz) are assumed unless the project specifies a different arrangement.
- A TN-S earthing system is assumed as the default industrial arrangement, pending confirmation of the combined-vs-separate HV/LV earthing decision (see basis_of_design/electrical_hv.py).

**Exclusions:**

- Extra-low voltage (ELV) control/instrumentation power (e.g. 24V DC) — assumed covered under a separate instrumentation/controls scope, not this LV distribution section.

**Deliverables:**

- Electrical design basis statement (report)
- Single line diagram (SLD) (drawing)

## LV distribution and reticulation

Main LV switchboard, distribution boards, and cable route/sizing between them.

**Applicable standards:**

- BS 7671 _Cable sizing/derating — Appendix 4._
- BS EN 61439-2 — Power switchgear and controlgear assemblies

**Design criteria:**

- Maximum voltage drop (power circuits): 5 % — Typical BS 7671 guidance figure — lighting circuits are usually held to a tighter 3%; confirm both against the project's actual requirement.
- Cable derating ambient design temperature: 30 °C — Standard BS 7671 Appendix 4 reference ambient — confirm against actual plant/enclosure ambient conditions, which may be higher near process equipment.

**Assumptions:**

- A standard UK ambient design temperature (30°C) is assumed for cable derating unless site-specific/plant-specific conditions (e.g. proximity to hot process equipment) require a higher figure.

**Exclusions:**

- DC distribution systems — not included unless a specific need is identified (e.g. a solar PV/battery energy storage installation).

**Interfaces:**

- **electrical_hv**: Incoming HV/LV transformer secondary — supply origin for the LV system.
- **utilities_coordination**: New electrical supply/DNO connection coordination (civils basis of design).

**Calculations required:**

- Cable sizing and voltage drop — to BS 7671 (not yet built)
- Load schedule / diversity: Aggregated demand across all LV loads. (not yet built)

**Deliverables:**

- LV distribution single line diagram (drawing)
- Cable schedule (schedule)
- Load schedule (schedule)

## Earthing and bonding

Main earthing terminal, equipotential bonding, and earth fault loop impedance.

**Applicable standards:**

- BS 7671 _Chapter 54 — earthing arrangements and protective conductors._
- BS 7430 — Code of practice for protective earthing of electrical installations

**Design criteria:**

- Maximum earth fault loop impedance: per BS 7671 Table 41.3 — Value depends on protective device type/rating and required disconnection time (0.4s or 5s) — set per final circuit, not a single project-wide figure.
- Minimum main bonding conductor size: per BS 7671 Table 54.8 — Sized from the supply neutral/earthing conductor cross-sectional area — confirm once the incoming supply arrangement is fixed.

**Assumptions:**

- Soil resistivity is assumed from calcs/geotechnical/ characteristic values pending confirmation by a direct resistivity test at the earth electrode location(s).

**Risk flags:**

- **[MEDIUM] [temporary_works]** Temporary electrical supplies and earthing arrangements during construction (before the permanent installation's earthing/bonding is complete and tested) are a distinct, commonly overlooked risk area from the permanent design. (trigger: Construction-phase electrical supplies routinely precede the permanent earthing/bonding installation being complete.) — recommended action: Define temporary supply/earthing arrangements and testing requirements for the construction phase, not just the completed installation.

**Exclusions:**

- Lightning protection system design (BS EN 62305) — a separate discipline/scope, only included if specifically requested for this project.

**Interfaces:**

- **structural**: Structural steelwork bonding.
- **geotechnical**: Soil resistivity affects earth electrode design — see calcs/geotechnical/.

**Deliverables:**

- Earthing and bonding layout drawing (drawing)
- Earth fault loop impedance calculation (calculation report)

## Motor control and LV switchgear

Motor starters and motor control centres (MCCs) for plant loads (e.g. pumps on the mechanical piping side).

**Applicable standards:**

- BS EN 60947 series — Low-voltage switchgear and controlgear
- BS EN 61439-2 _Shared with LV distribution — MCC assemblies specifically._

**Design criteria:**

- Direct-on-line (DOL) starting threshold: 5.5 kW — Typical threshold above which soft-start/VSD starting is considered instead of DOL, to limit supply disturbance — confirm against the actual site supply fault level/capacity.
- Minimum enclosure IP rating: IP54 — Typical minimum for industrial MCC/motor enclosures — confirm against the specific area's washdown/dust/hazardous-area requirements, which may require a higher rating.

**Assumptions:**

- Motor loads and quantities are assumed to be confirmed once the mechanical piping discipline's pump/equipment schedule exists — this section cannot finalise MCC sizing independently of that input.

**Exclusions:**

- Variable speed drive (VSD) harmonic mitigation design — only included if VSDs are specified for specific loads, not a default assumption.

**Interfaces:**

- **mechanical_piping**: Motor/pump loads to be scheduled once the mechanical piping BoD is built.

**Deliverables:**

- Motor control centre (MCC) schedule (schedule)
- Motor starter schedule (schedule)

## Standby and backup power

Generators and UPS for critical loads.

**Applicable standards:**

- BS EN 12601 _Reciprocating internal combustion engine driven generating sets — confirm current designation._
- BS EN 62040 series — Uninterruptible power systems (UPS)

**Design criteria:**

- Generator changeover time: 15 seconds — Typical target for automatic mains failure (AMF) changeover — confirm against the actual criticality of the loads served.
- UPS autonomy time: 10–30 minutes — Typical range for control/critical instrumentation loads — set per the specific criticality and any generator start/changeover bridging requirement.

**Assumptions:**

- Standby generation is assumed sized for essential/life-safety loads only, not the full site load, unless a full-site-backup requirement is explicitly stated.

**Exclusions:**

- Renewable generation / battery energy storage system (BESS) design — not included unless specifically requested for this project.

**Deliverables:**

- Standby power single line diagram (drawing)
- Generator/UPS sizing calculation (calculation report)

## Lighting

Normal and emergency lighting.

**Applicable standards:**

- BS 5266-1 — Emergency lighting — code of practice
- BS EN 12464-1 — Light and lighting of work places

**Design criteria:**

- General industrial area illuminance: 200–300 lux — Typical BS EN 12464-1 range for general industrial areas — specific task areas (control rooms, inspection points) may require a higher level.
- Emergency lighting duration: 3 hours — Standard non-domestic minimum per BS 5266-1 — confirm against the specific building/area risk assessment.

**Assumptions:**

- A standard maintained emergency lighting scheme is assumed (rather than non-maintained/stand-by escape lighting only), pending the site-specific emergency lighting risk assessment.

**Exclusions:**

- Architectural or decorative lighting design — not part of this industrial-focused basis of design.

**Deliverables:**

- Lighting layout drawing (drawing)
- Lighting calculation (illuminance levels) (calculation report)

## Small power and containment

Socket outlets and cable containment/trunking systems.

**Applicable standards:**

- BS 7671 _Socket outlet circuit design._
- BS EN 61537 — Cable management — cable tray systems and cable ladder systems _Confirm current designation._

**Design criteria:**

- Socket outlet circuit rating: 32A ring / 20A radial (typical) — Illustrative only — actual circuit design depends on the specific outlets/loads served.
- Cable containment maximum fill factor: 45 % — Typical design target to allow for future additions — confirm against the project's own cable management standard.

**Assumptions:**

- Cable containment routes are assumed coordinated with mechanical piping and structural steelwork to avoid clashes, pending a 3D model coordination review once all disciplines have routed their services.

**Exclusions:**

- IT/data cabling containment — assumed to sit under a separate ELV/IT systems scope, not this LV small power section.

**Deliverables:**

- Small power layout drawing (drawing)
- Cable containment layout drawing (drawing)

## Hazardous area classification

Area classification and equipment selection for zones with flammable/explosive atmospheres.

**Applicable standards:**

- DSEAR — Dangerous Substances and Explosive Atmospheres Regulations 2002
- UK ATEX _Equipment and Protective Systems Intended for Use in Potentially Explosive Atmospheres Regulations 2016 (UK) / EU ATEX Directive 2014/34/EU — confirm current UK designation and CE/UKCA marking status._
- BS EN 60079-10-1 — Explosive atmospheres — classification of areas — explosive gas atmospheres
- BS EN 60079-14 — Explosive atmospheres — electrical installations design, selection and erection
- BS EN 60079-17 — Explosive atmospheres — electrical installations inspection and maintenance

**Design criteria:**

- Zone classification categories: Zone 0/1/2 (gas/vapour) or Zone 20/21/22 (dust) — Per BS EN 60079-10-1 — the actual zone extents/categories can only be set once process fluid/material data is available from the mechanical piping discipline.
- Equipment protection level (EPL) required: to be confirmed per zone — Set from the zone classification once established — e.g. Ga/Gb/Gc for gas zones.

**Assumptions:**

- Process fluid/material flammability data is assumed to be supplied by the mechanical piping/process discipline; this section does not itself generate that data.
- A gas/vapour hazard only is assumed by default; combustible dust classification is not assumed unless a specific dust-generating process is identified.

**Risk flags:**

- **[HIGH] [code_compliance]** Area classification must be established BEFORE electrical equipment selection — selecting standard (non-ATEX-rated) equipment in a zone that turns out to be classified is a fundamental safety non-compliance, not a minor design revision. (trigger: Hazardous area classification depends on process/piping information that may not be finalised when electrical equipment is first specified.) — recommended action: Confirm area classification is complete and signed off before finalising any electrical equipment selection in or near potentially classified zones.

**Exclusions:**

- Combustible dust explosion classification (Zone 20/21/22) — only included if a dust-generating process is specifically identified; gas/vapour classification is the default scope.

**Interfaces:**

- **mechanical_piping**: Process fluids/materials that could create a hazardous zone must be identified from the piping/process design.
- **structural**: Platform/walkway equipment locations relative to classified zone boundaries.

**Deliverables:**

- Hazardous area classification drawing (zone plan) (drawing)
- Equipment selection schedule for classified zones (schedule)

## Arc flash and electrical safety

Arc flash risk assessment and safe working practices for LV switchgear.

**Applicable standards:**

- HSG85 — Electricity at work — safe working practices _HSE guidance._
- BS EN 50110-1 — Operation of electrical installations
- IEEE 1584 _Arc flash hazard calculation — widely used internationally though not a UK Eurocode/BS; confirm applicability/preference for this portfolio._

**Design criteria:**

- Arc flash study trigger: all boards/MCCs above a minimum prospective fault level (to be confirmed) — Threshold below which an arc flash study is not considered necessary — set per the project's electrical safety policy/client standard.
- PPE category framework: to be confirmed — IEEE 1584/NFPA 70E or an equivalent UK-recognised method — Sets incident energy bands and corresponding PPE categories once the arc flash study is complete.

**Assumptions:**

- An arc flash study is assumed required for the main LV switchboard and all MCCs above a minimum fault level threshold, to be confirmed against the project's electrical safety policy.

**Exclusions:**

- HV arc flash assessment — covered separately under basis_of_design/electrical_hv.py, not extrapolated from this LV assessment.

**Deliverables:**

- Arc flash risk assessment report (report)
- Arc flash warning label schedule (schedule)

