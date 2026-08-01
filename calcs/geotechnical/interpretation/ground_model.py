"""
Combines raw site investigation data (SPT, CPT, lab tests) for one stratum into
a single set of characteristic design parameters, using the correlations in
`correlations.py` and a simplified "cautious estimate" rule consistent with
EN 1997-1 §2.4.5.2's definition of characteristic value.

Characteristic value rule (documented simplification — see module docstring
in correlations.py for the same caveat): for a pool of derived/measured values
for one parameter within a stratum,

    n < 3:  characteristic = minimum observed value
    n >= 3: characteristic = min(mean - 1 standard deviation, minimum observed value)

This is a defensible, transparent proxy for engineering judgement — not a
substitute for it. EN 1997-1 characteristic value selection should account for
spatial variability, the governing failure mechanism, and engineering
experience of the specific site/soil, which this simplified statistical rule
does not attempt to capture.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from calcs.geotechnical.interpretation.correlations import (
    WATER_UNIT_WEIGHT_KN_M3,
    cu_from_cpt_cohesive,
    cu_from_n60_cohesive,
    n60_from_raw,
    overburden_correction_factor_cn,
    phi_from_cpt_granular,
    phi_from_n1_60_granular,
)
from calcs.geotechnical.interpretation.models import SiteInvestigation, Stratum


@dataclass
class DesignParameters:
    phi_deg: Optional[float]
    c_kpa: Optional[float]
    cu_kpa: Optional[float]
    unit_weight_kn_m3: float
    warnings: list[str] = field(default_factory=list)


def characteristic_value(values: list[float]) -> tuple[float, str]:
    if not values:
        raise ValueError("No data available to derive a characteristic value.")
    if len(values) < 3:
        char = min(values)
        note = f"n={len(values)} (<3 points): characteristic = minimum observed value = {char:.3g}"
    else:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        candidate = mean - stdev
        char = min(candidate, min(values))
        note = (
            f"n={len(values)}: characteristic = min(mean-1sd={candidate:.3g}, "
            f"min_observed={min(values):.3g}) = {char:.3g} (mean={mean:.3g}, sd={stdev:.3g})"
        )
    return char, note


def _layer_unit_weight_for_overburden(stratum: Stratum) -> float:
    lab_uw = [t.unit_weight_kn_m3 for t in stratum.lab_tests if t.unit_weight_kn_m3 is not None]
    if lab_uw:
        return sum(lab_uw) / len(lab_uw)
    return stratum.assumed_unit_weight_kn_m3


def overburden_profile_kpa(
    depth_m: float, strata: list[Stratum], water_table_depth_m: Optional[float]
) -> tuple[float, float]:
    """Returns (total_overburden_kpa, effective_overburden_kpa) at the given depth,
    walking the full layered profile from the surface down."""
    ordered = sorted(strata, key=lambda s: s.top_depth_m)
    total = 0.0
    effective = 0.0
    for layer in ordered:
        if layer.top_depth_m >= depth_m:
            break
        layer_base = min(layer.base_depth_m, depth_m)
        thickness = layer_base - layer.top_depth_m
        if thickness <= 0:
            continue
        gamma = _layer_unit_weight_for_overburden(layer)
        total += gamma * thickness
        if water_table_depth_m is None:
            effective += gamma * thickness
        else:
            dry_thickness = max(0.0, min(layer_base, water_table_depth_m) - layer.top_depth_m)
            wet_thickness = thickness - dry_thickness
            gamma_sub = max(gamma - WATER_UNIT_WEIGHT_KN_M3, 0.0)
            effective += gamma * dry_thickness + gamma_sub * wet_thickness
    return total, effective


def interpret_stratum(site: SiteInvestigation, stratum: Stratum) -> tuple[DesignParameters, list[str]]:
    """
    Derive characteristic phi'/cu/c'/unit weight for one stratum from its SPT,
    CPT, and lab test data, using the overburden profile of the full site
    (shallower strata matter for the stress-dependent correlations even though
    only this stratum's own readings are interpreted).
    """
    notes: list[str] = []
    warnings: list[str] = []
    phi_pool: list[float] = []
    cu_pool: list[float] = []
    c_pool: list[float] = []
    uw_pool: list[float] = [t.unit_weight_kn_m3 for t in stratum.lab_tests if t.unit_weight_kn_m3 is not None]

    for r in stratum.spt_readings:
        n60 = n60_from_raw(r.n_value, r.energy_ratio_pct)
        _, sigma_eff = overburden_profile_kpa(r.depth_m, site.strata, site.water_table_depth_m)
        if stratum.behavior == "granular":
            cn = overburden_correction_factor_cn(sigma_eff)
            n1_60 = n60 * cn
            phi_point, w = phi_from_n1_60_granular(n1_60)
            warnings.extend(w)
            phi_pool.append(phi_point)
            notes.append(
                f"SPT @ {r.depth_m}m: N={r.n_value} -> N60={n60:.1f} -> CN={cn:.2f} -> "
                f"N1,60={n1_60:.1f} -> phi'={phi_point:.1f} deg (Peck-Hanson-Thornburn)"
            )
        else:
            cu_point = cu_from_n60_cohesive(n60)
            cu_pool.append(cu_point)
            notes.append(f"SPT @ {r.depth_m}m: N={r.n_value} -> N60={n60:.1f} -> Cu={cu_point:.1f} kPa (Stroud, k=4.0)")

    for r in stratum.cpt_readings:
        sigma_total, sigma_eff = overburden_profile_kpa(r.depth_m, site.strata, site.water_table_depth_m)
        if stratum.behavior == "granular":
            phi_point, w = phi_from_cpt_granular(r.qc_mpa, sigma_eff)
            warnings.extend(w)
            phi_pool.append(phi_point)
            notes.append(f"CPT @ {r.depth_m}m: qc={r.qc_mpa} MPa -> phi'={phi_point:.1f} deg (Kulhawy-Mayne)")
        else:
            cu_point, w = cu_from_cpt_cohesive(r.qc_mpa, sigma_total)
            warnings.extend(w)
            cu_pool.append(cu_point)
            notes.append(f"CPT @ {r.depth_m}m: qc={r.qc_mpa} MPa -> Cu={cu_point:.1f} kPa (Nkt=17)")

    for t in stratum.lab_tests:
        if t.phi_deg is not None:
            phi_pool.append(t.phi_deg)
            notes.append(f"Lab ({t.test_type}) @ {t.depth_m}m: measured phi'={t.phi_deg} deg")
        if t.c_kpa is not None:
            c_pool.append(t.c_kpa)
            notes.append(f"Lab ({t.test_type}) @ {t.depth_m}m: measured c'={t.c_kpa} kPa")
        if t.cu_kpa is not None:
            cu_pool.append(t.cu_kpa)
            notes.append(f"Lab ({t.test_type}) @ {t.depth_m}m: measured cu={t.cu_kpa} kPa")

    phi_char = c_char = cu_char = None

    if stratum.behavior == "granular":
        if phi_pool:
            phi_char, note = characteristic_value(phi_pool)
            notes.append(f"phi' characteristic value: {note}")
        else:
            warnings.append(f"Stratum '{stratum.name}': no SPT/CPT/lab data to derive phi' — none returned.")
        if c_pool:
            c_char, note = characteristic_value(c_pool)
            notes.append(f"c' characteristic value: {note}")
        else:
            c_char = 0.0
    else:
        if cu_pool:
            cu_char, note = characteristic_value(cu_pool)
            notes.append(f"cu characteristic value: {note}")
        else:
            warnings.append(f"Stratum '{stratum.name}': no SPT/CPT/lab data to derive cu — none returned.")

    if uw_pool:
        uw_char, note = characteristic_value(uw_pool)
        notes.append(f"Unit weight characteristic value: {note}")
    else:
        uw_char = stratum.assumed_unit_weight_kn_m3
        warnings.append(
            f"Stratum '{stratum.name}': no lab bulk density data — using the assumed unit weight "
            f"({stratum.assumed_unit_weight_kn_m3} kN/m^3) supplied for this stratum."
        )

    return DesignParameters(phi_deg=phi_char, c_kpa=c_char, cu_kpa=cu_char, unit_weight_kn_m3=uw_char, warnings=warnings), notes


def to_bearing_resistance_kwargs(dp: DesignParameters) -> dict:
    """Convert derived DesignParameters into kwargs for BearingResistanceInput."""
    if dp.cu_kpa is not None:
        return {
            "analysis_type": "undrained",
            "undrained_shear_strength_cu_kpa": dp.cu_kpa,
            "unit_weight_kn_m3": dp.unit_weight_kn_m3,
        }
    return {
        "analysis_type": "drained",
        "cohesion_c_prime_kpa": dp.c_kpa or 0.0,
        "friction_angle_phi_prime_deg": dp.phi_deg,
        "unit_weight_kn_m3": dp.unit_weight_kn_m3,
    }
