"""
Tests for the EN 1993-1-1 SS6.3.3 beam-column interaction check. Equations
(6.61)/(6.62) are checked directly against a hand calculation -- the
k-factors themselves are treated as opaque required inputs (see module
docstring for why), not derived or verified here.
"""

import pytest
from pydantic import ValidationError

from calcs.structural.beam_column_interaction import (
    BeamColumnInteractionInput,
    calculate,
)

BASE_KWARGS = dict(
    design_axial_force_ned_kn=200.0,
    axial_buckling_resistance_y_nb_y_rd_kn=500.0,
    axial_buckling_resistance_z_nb_z_rd_kn=350.0,
    design_moment_y_my_ed_knm=80.0,
    moment_resistance_y_my_rd_knm=150.0,
    design_moment_z_mz_ed_knm=10.0,
    moment_resistance_z_mz_rd_knm=40.0,
    k_yy=0.9,
    k_yz=0.6,
    k_zy=0.6,
    k_zz=0.9,
)


def _expected_uc1(k):
    return k["design_axial_force_ned_kn"] / k["axial_buckling_resistance_y_nb_y_rd_kn"] \
        + k["k_yy"] * k["design_moment_y_my_ed_knm"] / k["moment_resistance_y_my_rd_knm"] \
        + k["k_yz"] * k["design_moment_z_mz_ed_knm"] / k["moment_resistance_z_mz_rd_knm"]


def _expected_uc2(k):
    return k["design_axial_force_ned_kn"] / k["axial_buckling_resistance_z_nb_z_rd_kn"] \
        + k["k_zy"] * k["design_moment_y_my_ed_knm"] / k["moment_resistance_y_my_rd_knm"] \
        + k["k_zz"] * k["design_moment_z_mz_ed_knm"] / k["moment_resistance_z_mz_rd_knm"]


def test_uc1_matches_hand_calculation():
    result = calculate(BeamColumnInteractionInput(**BASE_KWARGS))
    uc1 = next(t.value for t in result.terms if t.label.startswith("UC1"))
    assert uc1 == pytest.approx(_expected_uc1(BASE_KWARGS), rel=1e-9)


def test_uc2_matches_hand_calculation():
    result = calculate(BeamColumnInteractionInput(**BASE_KWARGS))
    uc2 = next(t.value for t in result.terms if t.label.startswith("UC2"))
    assert uc2 == pytest.approx(_expected_uc2(BASE_KWARGS), rel=1e-9)


def test_governing_utilisation_is_the_larger_of_uc1_uc2():
    result = calculate(BeamColumnInteractionInput(**BASE_KWARGS))
    expected_uc1 = _expected_uc1(BASE_KWARGS)
    expected_uc2 = _expected_uc2(BASE_KWARGS)
    assert result.headline.value == pytest.approx(max(expected_uc1, expected_uc2), rel=1e-9)
    assert "6.62" in result.headline.note  # UC2 governs for this example


def test_fails_and_raises_critical_code_compliance_flag():
    result = calculate(BeamColumnInteractionInput(**BASE_KWARGS))
    assert "FAIL" in result.headline.note
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)


def test_passes_with_lower_loading():
    kwargs = dict(BASE_KWARGS, design_axial_force_ned_kn=50.0, design_moment_y_my_ed_knm=20.0, design_moment_z_mz_ed_knm=2.0)
    result = calculate(BeamColumnInteractionInput(**kwargs))
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_zero_minor_axis_moment_ignores_mz_rd_value():
    kwargs_low_mz_rd = dict(BASE_KWARGS, design_moment_z_mz_ed_knm=0.0, moment_resistance_z_mz_rd_knm=1.0)
    kwargs_high_mz_rd = dict(BASE_KWARGS, design_moment_z_mz_ed_knm=0.0, moment_resistance_z_mz_rd_knm=1000.0)
    result_low = calculate(BeamColumnInteractionInput(**kwargs_low_mz_rd))
    result_high = calculate(BeamColumnInteractionInput(**kwargs_high_mz_rd))
    assert result_low.headline.value == pytest.approx(result_high.headline.value, rel=1e-9)


def test_uc1_governs_when_z_axis_resistance_much_higher():
    kwargs = dict(BASE_KWARGS, axial_buckling_resistance_z_nb_z_rd_kn=5000.0)
    result = calculate(BeamColumnInteractionInput(**kwargs))
    assert "6.61" in result.headline.note


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        BeamColumnInteractionInput(**dict(BASE_KWARGS, design_axial_force_ned_kn=0.0))
    with pytest.raises(ValidationError):
        BeamColumnInteractionInput(**dict(BASE_KWARGS, k_yy=0.0))
