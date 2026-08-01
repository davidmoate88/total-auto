# LV Electrical — Basis of Design

## Design standards and general criteria

Overarching LV electrical design basis: wiring regulations, safety regulations, earthing system, and general criteria (voltage/frequency, diversity).

**Applicable standards:**

- BS 7671 — Requirements for Electrical Installations (IET Wiring Regulations) _Confirm current edition/amendment._
- Electricity at Work Regulations 1989
- BS EN 61439-1 — Low-voltage switchgear and controlgear assemblies — general rules

## LV distribution and reticulation

Main LV switchboard, distribution boards, and cable route/sizing between them.

**Applicable standards:**

- BS 7671 _Cable sizing/derating — Appendix 4._
- BS EN 61439-2 — Power switchgear and controlgear assemblies

**Interfaces:**

- **electrical_hv**: Incoming HV/LV transformer secondary — supply origin for the LV system.
- **utilities_coordination**: New electrical supply/DNO connection coordination (civils basis of design).

**Calculations required:**

- Cable sizing and voltage drop — to BS 7671 (not yet built)
- Load schedule / diversity: Aggregated demand across all LV loads. (not yet built)

## Earthing and bonding

Main earthing terminal, equipotential bonding, and earth fault loop impedance.

**Applicable standards:**

- BS 7671 _Chapter 54 — earthing arrangements and protective conductors._
- BS 7430 — Code of practice for protective earthing of electrical installations

**Risk flags:**

- **[MEDIUM] [temporary_works]** Temporary electrical supplies and earthing arrangements during construction (before the permanent installation's earthing/bonding is complete and tested) are a distinct, commonly overlooked risk area from the permanent design. (trigger: Construction-phase electrical supplies routinely precede the permanent earthing/bonding installation being complete.) — recommended action: Define temporary supply/earthing arrangements and testing requirements for the construction phase, not just the completed installation.

**Interfaces:**

- **structural**: Structural steelwork bonding.
- **geotechnical**: Soil resistivity affects earth electrode design — see calcs/geotechnical/.

## Motor control and LV switchgear

Motor starters and motor control centres (MCCs) for plant loads (e.g. pumps on the mechanical piping side).

**Applicable standards:**

- BS EN 60947 series — Low-voltage switchgear and controlgear
- BS EN 61439-2 _Shared with LV distribution — MCC assemblies specifically._

**Interfaces:**

- **mechanical_piping**: Motor/pump loads to be scheduled once the mechanical piping BoD is built.

## Standby and backup power

Generators and UPS for critical loads.

**Applicable standards:**

- BS EN 12601 _Reciprocating internal combustion engine driven generating sets — confirm current designation._
- BS EN 62040 series — Uninterruptible power systems (UPS)

## Lighting

Normal and emergency lighting.

**Applicable standards:**

- BS 5266-1 — Emergency lighting — code of practice
- BS EN 12464-1 — Light and lighting of work places

## Small power and containment

Socket outlets and cable containment/trunking systems.

**Applicable standards:**

- BS 7671 _Socket outlet circuit design._
- BS EN 61537 — Cable management — cable tray systems and cable ladder systems _Confirm current designation._

## Hazardous area classification

Area classification and equipment selection for zones with flammable/explosive atmospheres.

**Applicable standards:**

- DSEAR — Dangerous Substances and Explosive Atmospheres Regulations 2002
- UK ATEX _Equipment and Protective Systems Intended for Use in Potentially Explosive Atmospheres Regulations 2016 (UK) / EU ATEX Directive 2014/34/EU — confirm current UK designation and CE/UKCA marking status._
- BS EN 60079-10-1 — Explosive atmospheres — classification of areas — explosive gas atmospheres
- BS EN 60079-14 — Explosive atmospheres — electrical installations design, selection and erection
- BS EN 60079-17 — Explosive atmospheres — electrical installations inspection and maintenance

**Risk flags:**

- **[HIGH] [code_compliance]** Area classification must be established BEFORE electrical equipment selection — selecting standard (non-ATEX-rated) equipment in a zone that turns out to be classified is a fundamental safety non-compliance, not a minor design revision. (trigger: Hazardous area classification depends on process/piping information that may not be finalised when electrical equipment is first specified.) — recommended action: Confirm area classification is complete and signed off before finalising any electrical equipment selection in or near potentially classified zones.

**Interfaces:**

- **mechanical_piping**: Process fluids/materials that could create a hazardous zone must be identified from the piping/process design.
- **structural**: Platform/walkway equipment locations relative to classified zone boundaries.

## Arc flash and electrical safety

Arc flash risk assessment and safe working practices for LV switchgear.

**Applicable standards:**

- HSG85 — Electricity at work — safe working practices _HSE guidance._
- BS EN 50110-1 — Operation of electrical installations
- IEEE 1584 _Arc flash hazard calculation — widely used internationally though not a UK Eurocode/BS; confirm applicability/preference for this portfolio._

