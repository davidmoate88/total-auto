# Structural — Basis of Design

## Design standards and general criteria

Overarching design basis for industrial access steelwork (platforms, walkways, stairs, ladders, handrails) and its supporting frame. Multi-storey/occupied-building structural elements (floor vibration for building floors, lateral stability/sway, roof structure, fire engineering) are out of scope for now per project direction — parked, not deleted.

**Applicable standards:**

- BS EN 1990 (UK NA) — Basis of structural design
- BS EN 1991-1-1 (UK NA) — Actions on structures — densities, self-weight, imposed loads
- BS EN 1993-1-1 (UK NA) — Design of steel structures — general rules
- Machinery Directive 2006/42/EC _EU — confirm UK equivalent designation/status (Supply of Machinery (Safety) Regulations 2008, and current CE/UKCA marking requirement)._
- BS EN ISO 12100 — Safety of machinery — general principles for risk assessment and risk reduction

**Exclusions:**

- Multi-storey/occupied-building structural design (floor vibration, lateral sway, roof structure, fire engineering) — parked, see docs/ROADMAP.md.

## Substructure and foundations

Foundations and base connections (base plates, holding-down bolts) supporting platform/walkway steelwork.

**Applicable standards:**

- BS EN 1997-1 (UK NA) _Shared with the geotechnical module._
- BS EN 1993-1-8 (UK NA) — Design of joints — base plate/holding-down bolt design.

**Interfaces:**

- **geotechnical**: Bearing resistance for platform/walkway support foundations — see calcs/geotechnical/.

**Calculations required:**

- Base plate / holding-down bolt design — to BS EN 1993-1-8 (not yet built)

## Primary steel frame

Supporting steelwork (beams, columns, bracing) for platforms and walkways.

**Applicable standards:**

- BS EN 1993-1-1 (UK NA) — General rules and rules for buildings
- BS EN 1993-1-8 (UK NA) — Design of joints

**Calculations required:**

- Beam/column member capacity checks — to BS EN 1993-1-1 (not yet built)
- Connection design — to BS EN 1993-1-8 (not yet built)

## Platforms and walkways

Decking/flooring specification and loading for working platforms and walkways.

**Applicable standards:**

- BS EN ISO 14122-2 — Safety of machinery — permanent means of access — working platforms and walkways
- BS EN 1991-1-1 (UK NA) _Imposed load requirements for platforms/walkways._
- BS 4592 _Industrial type flooring, walkways and stair treads (grating/chequer plate specification) — confirm current part/edition._

**Calculations required:**

- Deck/grating loading and deflection check — to BS EN 1991-1-1 (not yet built)

## Stairs and ladders

Geometry (pitch, rise/going) and loading for stairs, stepladders, and fixed ladders providing access.

**Applicable standards:**

- BS EN ISO 14122-3 — Stairs, stepladders and guard-rails
- BS EN ISO 14122-4 — Fixed ladders

## Handrails and guard-rails

Guard-rail/handrail height, loading, gap limits, and toe-boards for platforms, walkways, and stairs.

**Applicable standards:**

- BS EN ISO 14122-3 _Guard-rail requirements — shared with the stairs/ladders section._
- BS 6180 _Barriers in and about buildings — may apply instead of/alongside EN ISO 14122-3 depending on building-vs-machinery classification; confirm which governs per installation._

**Calculations required:**

- Guard-rail horizontal load check — to BS EN ISO 14122-3 (not yet built)

## Structural integrity and robustness

Robustness considerations scaled to access-structure risk (connection redundancy, corrosion allowance) — not full building disproportionate-collapse design.

**Applicable standards:**

- BS EN 1991-1-7 (UK NA) _Accidental actions — apply only the parts relevant to an access structure, not full building consequence-class robustness._

## Temporary works

Erection/lifting sequence and temporary stability requirements during construction — typically contractor-designed, with performance requirements set here.

**Applicable standards:**

- BS 5975 — Code of practice for temporary works procedures and the permissible stress design of falsework

**Interfaces:**

- **contractor / temporary works designer**: This section states performance requirements; detailed temporary works design is typically the contractor's responsibility.

## Movement, tolerances, and durability

Thermal movement/expansion joints for long walkway runs, construction tolerances, and corrosion protection.

**Applicable standards:**

- BS EN ISO 1461 — Hot dip galvanized coatings on iron and steel articles
- BS EN 1993-1-1 (UK NA) _Corrosion/durability provisions within the general steel design rules._

