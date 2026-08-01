"""
Empirical correlations for deriving geotechnical design parameters from SPT/CPT
data. These are independent, long-established empirical relationships from the
geotechnical literature — Eurocode 7 does not itself define or mandate ground
parameter correlations; it requires (EN 1997-1 §2.4.5.2) that a *characteristic*
value be "a cautious estimate of the value affecting the occurrence of the
limit state". The correlations here produce per-point estimates; combining
those into a single cautious characteristic value per stratum is handled in
`ground_model.py`.

*** Verify before real use *** — as with the bearing resistance module, these
formulae are reproduced from standard geotechnical references (Peck, Hanson &
Thornburn 1974; Liao & Whitman 1986; Stroud 1974; Kulhawy & Mayne 1990) as
commonly presented in textbooks/design guides, not cross-checked against the
original papers directly in this environment. Treat derived parameters as a
first estimate to sense-check against local experience and the ground
investigation report's own recommendations, not a replacement for engineering
judgement.

References:
- Peck, R.B., Hanson, W.E., Thornburn, T.H. (1974). Foundation Engineering.
- Liao, S.S.C. & Whitman, R.V. (1986). Overburden correction factors for SPT in sand.
- Stroud, M.A. (1974). SPT in insensitive clays.
- Kulhawy, F.H. & Mayne, P.W. (1990). Manual on Estimating Soil Properties for
  Foundation Design, EPRI.
"""

from __future__ import annotations

import math

WATER_UNIT_WEIGHT_KN_M3 = 9.81
ATMOSPHERIC_PRESSURE_KPA = 100.0

# Practical caps applied to keep formulae from extrapolating into physically
# implausible territory at very high N-values / qc — documented, not silent.
MAX_PHI_DEG = 45.0
CN_MIN, CN_MAX = 0.4, 2.0


def n60_from_raw(n_raw: float, energy_ratio_pct: float) -> float:
    """Energy-correct a raw field SPT N-value to the N60 reference (60% energy ratio)."""
    return n_raw * (energy_ratio_pct / 60.0)


def overburden_correction_factor_cn(effective_overburden_kpa: float) -> float:
    """
    Liao & Whitman (1986) overburden correction factor for SPT in granular soils:
    CN = sqrt(Pa / sigma'v), capped to [0.4, 2.0] per common practice guidance.
    """
    sigma = max(effective_overburden_kpa, 1.0)  # avoid division blow-up near surface
    cn = math.sqrt(ATMOSPHERIC_PRESSURE_KPA / sigma)
    return min(max(cn, CN_MIN), CN_MAX)


def phi_from_n1_60_granular(n1_60: float) -> tuple[float, list[str]]:
    """
    Peck, Hanson & Thornburn (1974) empirical fit for effective friction angle
    of granular soils from the overburden- and energy-corrected SPT blowcount:

        phi' (deg) = 27.1 + 0.3*N1,60 - 0.00054*(N1,60)^2

    Capped at MAX_PHI_DEG with a warning if the raw formula would extrapolate
    beyond a physically plausible range for very high N1,60.
    """
    warnings: list[str] = []
    phi = 27.1 + 0.3 * n1_60 - 0.00054 * n1_60**2
    if phi > MAX_PHI_DEG:
        warnings.append(
            f"Peck-Hanson-Thornburn formula gave phi'={phi:.1f} deg at N1,60={n1_60:.1f}, "
            f"beyond the physically plausible range for natural sands — capped at {MAX_PHI_DEG} deg."
        )
        phi = MAX_PHI_DEG
    return phi, warnings


def cu_from_n60_cohesive(n60: float, k_kpa_per_blow: float = 4.0) -> float:
    """
    Stroud (1974) correlation for undrained shear strength of insensitive clays:
    Cu = k * N60, with k commonly cited in the range ~3.5-6.5 kPa/blow depending
    on plasticity. Default k=4.0 is a conservative mid-low value; pass a
    different k if local correlation data (e.g. from the site investigation
    report) suggests otherwise.
    """
    return k_kpa_per_blow * n60


def phi_from_cpt_granular(qc_mpa: float, sigma_v0_eff_kpa: float) -> tuple[float, list[str]]:
    """
    Kulhawy & Mayne (1990) correlation for effective friction angle of granular
    soils from CPT cone resistance:

        phi' (deg) = atan[0.1 + 0.38*log10(qc / sigma'v0)]

    qc and sigma'v0 in the same units (kPa here). A minimum effective stress
    floor is applied to avoid a singularity at very shallow depth.
    """
    warnings: list[str] = []
    qc_kpa = qc_mpa * 1000.0
    sigma_eff = max(sigma_v0_eff_kpa, 5.0)
    if sigma_v0_eff_kpa < 5.0:
        warnings.append(
            f"Effective overburden at this depth ({sigma_v0_eff_kpa:.1f} kPa) is very low; "
            "floored to 5 kPa to keep the CPT correlation stable near the surface."
        )
    ratio = max(qc_kpa / sigma_eff, 1e-6)
    phi_rad = math.atan(0.1 + 0.38 * math.log10(ratio))
    phi = math.degrees(phi_rad)
    if phi > MAX_PHI_DEG:
        warnings.append(
            f"Kulhawy-Mayne formula gave phi'={phi:.1f} deg — capped at {MAX_PHI_DEG} deg."
        )
        phi = MAX_PHI_DEG
    return phi, warnings


def cu_from_cpt_cohesive(qc_mpa: float, sigma_v0_total_kpa: float, n_kt: float = 17.0) -> tuple[float, list[str]]:
    """
    Standard CPT net-cone-resistance approach for undrained shear strength:

        Cu = (qc - sigma_v0) / Nkt

    Nkt (cone factor) is commonly taken in the range 10-20; 17 is used here as
    a reasonable single mid-range default — override if local correlation data
    is available. Floors Cu at 0 with a warning rather than returning a
    nonsensical negative value.
    """
    warnings: list[str] = []
    qc_kpa = qc_mpa * 1000.0
    cu = (qc_kpa - sigma_v0_total_kpa) / n_kt
    if cu < 0:
        warnings.append(
            f"Net cone resistance non-positive at this depth (qc={qc_kpa:.0f} kPa, "
            f"sigma_v0={sigma_v0_total_kpa:.0f} kPa) — Cu floored to 0; check qc/depth data."
        )
        cu = 0.0
    return cu, warnings
