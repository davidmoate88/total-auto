"""
Tests for the ASME B31.3 sustained stress / thermal expansion stress range
check. Each equation is independently re-derived here and checked against
the module's output -- resultant moments/SIFs/allowables are treated as
opaque external inputs (see module docstring for why), not derived.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.mechanical_piping.pipe_stress_check import (
    PipeStressCheckInput,
    calculate,
)

BASE_KWARGS = dict(
    design_pressure_mpa=2.0,
    outside_diameter_mm=114.3,
    wall_thickness_mm=6.02,
    resultant_sustained_moment_ma_nm=500.0,
    sif_sustained_i=1.5,
    allowable_stress_hot_sh_mpa=110.0,
    allowable_stress_cold_sc_mpa=150.0,
    resultant_in_plane_moment_mi_nm=800.0,
    resultant_out_plane_moment_mo_nm=600.0,
    resultant_torsional_moment_mt_nm=300.0,
    sif_in_plane_ii=1.8,
    sif_out_plane_io=1.5,
)


def _expected_z(k):
    Do, t = k["outside_diameter_mm"], k["wall_thickness_mm"]
    Di = Do - 2 * t
    return math.pi * (Do**4 - Di**4) / (32 * Do)


def _expected_sl(k):
    Z = _expected_z(k)
    Ma = k["resultant_sustained_moment_ma_nm"] * 1000.0
    return k["design_pressure_mpa"] * k["outside_diameter_mm"] / (4 * k["wall_thickness_mm"]) + 0.75 * k["sif_sustained_i"] * Ma / Z


def _expected_se_and_sa(k):
    Z = _expected_z(k)
    Mi = k["resultant_in_plane_moment_mi_nm"] * 1000.0
    Mo = k["resultant_out_plane_moment_mo_nm"] * 1000.0
    Mt = k["resultant_torsional_moment_mt_nm"] * 1000.0
    Sb = math.sqrt((k["sif_in_plane_ii"] * Mi) ** 2 + (k["sif_out_plane_io"] * Mo) ** 2) / Z
    St = Mt / (2 * Z)
    SE = math.sqrt(Sb**2 + 4 * St**2)
    N = k.get("design_cycles_n", 7000.0)
    f = min(1.0, 6.0 * N**-0.2)
    SL = _expected_sl(k)
    SA = f * (1.25 * (k["allowable_stress_cold_sc_mpa"] + k["allowable_stress_hot_sh_mpa"]) - SL)
    return SE, SA


def test_section_modulus_matches_hand_calculation():
    result = calculate(PipeStressCheckInput(**BASE_KWARGS))
    z = next(t.value for t in result.terms if t.label == "Section modulus")
    assert z == pytest.approx(_expected_z(BASE_KWARGS), rel=1e-9)


def test_sustained_stress_matches_hand_calculation():
    result = calculate(PipeStressCheckInput(**BASE_KWARGS))
    sl = next(t.value for t in result.terms if t.label.startswith("Sustained stress"))
    assert sl == pytest.approx(_expected_sl(BASE_KWARGS), rel=1e-9)


def test_expansion_stress_range_and_allowable_match_hand_calculation():
    result = calculate(PipeStressCheckInput(**BASE_KWARGS))
    expected_se, expected_sa = _expected_se_and_sa(BASE_KWARGS)
    se = next(t.value for t in result.terms if t.label.startswith("Expansion stress range"))
    sa = next(t.value for t in result.terms if t.label.startswith("Allowable stress range"))
    assert se == pytest.approx(expected_se, rel=1e-9)
    assert sa == pytest.approx(expected_sa, rel=1e-9)


def test_governing_utilisation_matches_hand_calculation_and_passes():
    result = calculate(PipeStressCheckInput(**BASE_KWARGS))
    expected_sl = _expected_sl(BASE_KWARGS)
    expected_se, expected_sa = _expected_se_and_sa(BASE_KWARGS)
    expected_sl_u = expected_sl / BASE_KWARGS["allowable_stress_hot_sh_mpa"]
    expected_se_u = expected_se / expected_sa
    assert result.headline.value == pytest.approx(max(expected_sl_u, expected_se_u), rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_high_sustained_moment_fails_sustained_check():
    # Moderately elevated (not extreme) so SA (Eq 1b) stays positive and the
    # thermal check still passes -- isolates a sustained-only failure.
    kwargs = dict(BASE_KWARGS, resultant_sustained_moment_ma_nm=6500.0)
    result = calculate(PipeStressCheckInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert "sustained stress" in result.headline.note
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)


def test_extreme_sustained_moment_makes_allowable_stress_range_negative():
    # SL so far above Sh that Eq 1b's SA credit term goes negative -- SE/SA
    # correctly reports as infinite utilisation (no thermal margin remains),
    # governed by thermal expansion even though sustained also fails.
    kwargs = dict(BASE_KWARGS, resultant_sustained_moment_ma_nm=50000.0)
    result = calculate(PipeStressCheckInput(**kwargs))
    sa = next(t.value for t in result.terms if t.label.startswith("Allowable stress range"))
    assert sa < 0
    assert result.headline.value == float("inf")
    assert "FAIL" in result.headline.note


def test_high_thermal_moments_fail_expansion_check():
    kwargs = dict(BASE_KWARGS, resultant_in_plane_moment_mi_nm=50000.0, resultant_out_plane_moment_mo_nm=40000.0)
    result = calculate(PipeStressCheckInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert "thermal expansion" in result.headline.note


def test_more_design_cycles_reduces_f_and_allowable_stress_range():
    low_cycles = calculate(PipeStressCheckInput(**dict(BASE_KWARGS, design_cycles_n=1000.0)))
    high_cycles = calculate(PipeStressCheckInput(**dict(BASE_KWARGS, design_cycles_n=100000.0)))
    f_low = next(t.value for t in low_cycles.terms if t.label.startswith("Stress range reduction"))
    f_high = next(t.value for t in high_cycles.terms if t.label.startswith("Stress range reduction"))
    assert f_high < f_low
    assert f_low == pytest.approx(1.0)  # 1000 cycles is well within the f=1.0 cap


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        PipeStressCheckInput(**dict(BASE_KWARGS, design_pressure_mpa=0.0))
    with pytest.raises(ValidationError):
        PipeStressCheckInput(**dict(BASE_KWARGS, sif_sustained_i=-1.0))
