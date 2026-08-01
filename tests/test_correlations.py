import pytest

from calcs.geotechnical.interpretation.correlations import (
    CN_MAX,
    CN_MIN,
    MAX_PHI_DEG,
    cu_from_cpt_cohesive,
    cu_from_n60_cohesive,
    n60_from_raw,
    overburden_correction_factor_cn,
    phi_from_cpt_granular,
    phi_from_n1_60_granular,
)


def test_n60_energy_correction():
    assert n60_from_raw(20, 60) == pytest.approx(20.0)
    assert n60_from_raw(20, 45) == pytest.approx(15.0)


def test_cn_capped_both_ends():
    assert overburden_correction_factor_cn(100) == pytest.approx(1.0)
    assert overburden_correction_factor_cn(1) == CN_MAX
    assert overburden_correction_factor_cn(10000) == CN_MIN


def test_phi_from_n1_60_reasonable_and_capped():
    phi, warnings = phi_from_n1_60_granular(30)
    assert 30 < phi < 40
    assert warnings == []

    phi_high, warnings_high = phi_from_n1_60_granular(150)
    assert phi_high == MAX_PHI_DEG
    assert len(warnings_high) == 1


def test_cu_from_n60():
    assert cu_from_n60_cohesive(10, k_kpa_per_blow=4.0) == pytest.approx(40.0)


def test_phi_from_cpt_reasonable():
    phi, warnings = phi_from_cpt_granular(qc_mpa=10, sigma_v0_eff_kpa=100)
    assert 25 < phi < 45
    assert warnings == []


def test_cu_from_cpt_floors_at_zero_with_warning():
    cu, warnings = cu_from_cpt_cohesive(qc_mpa=0.03, sigma_v0_total_kpa=50, n_kt=17)
    assert cu == 0.0
    assert len(warnings) == 1

    cu_normal, warnings_normal = cu_from_cpt_cohesive(qc_mpa=1.0, sigma_v0_total_kpa=20, n_kt=17)
    assert cu_normal > 0
    assert warnings_normal == []
