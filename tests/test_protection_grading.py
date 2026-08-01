"""
Tests for the IEC 60255-151 IDMT protection grading check. The operating
time formula and standard curve constants are checked directly against a
hand calculation.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.electrical_hv.protection_grading import (
    IDMT_CURVE_CONSTANTS,
    ProtectionGradingInput,
    calculate,
)

BASE_KWARGS = dict(
    fault_current_a=2000.0,
    downstream_pickup_current_a=100.0,
    downstream_tms=0.1,
    upstream_pickup_current_a=200.0,
    upstream_tms=0.2,
)


def _expected_time(curve, pickup, tms, fault):
    k, alpha = IDMT_CURVE_CONSTANTS[curve]
    return tms * k / ((fault / pickup) ** alpha - 1)


def test_downstream_operating_time_matches_hand_calculation():
    result = calculate(ProtectionGradingInput(**BASE_KWARGS))
    t_down = next(t.value for t in result.terms if t.label.startswith("Downstream"))
    expected = _expected_time("standard_inverse", 100.0, 0.1, 2000.0)
    assert t_down == pytest.approx(expected, rel=1e-9)
    assert t_down == pytest.approx(0.22677, abs=1e-4)


def test_upstream_operating_time_matches_hand_calculation():
    result = calculate(ProtectionGradingInput(**BASE_KWARGS))
    t_up = next(t.value for t in result.terms if t.label.startswith("Upstream"))
    expected = _expected_time("standard_inverse", 200.0, 0.2, 2000.0)
    assert t_up == pytest.approx(expected, rel=1e-9)
    assert t_up == pytest.approx(0.59413, abs=1e-4)


def test_grading_margin_matches_hand_calculation_and_passes():
    result = calculate(ProtectionGradingInput(**BASE_KWARGS))
    expected_margin = _expected_time("standard_inverse", 200.0, 0.2, 2000.0) - _expected_time("standard_inverse", 100.0, 0.1, 2000.0)
    assert result.headline.value == pytest.approx(expected_margin, rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_insufficient_margin_fails_and_raises_critical_flag():
    # Equal TMS/pickup ratio-ish settings collapse the margin toward zero.
    kwargs = dict(BASE_KWARGS, upstream_tms=0.11)
    result = calculate(ProtectionGradingInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)


def test_higher_upstream_tms_increases_margin():
    low = calculate(ProtectionGradingInput(**dict(BASE_KWARGS, upstream_tms=0.15)))
    high = calculate(ProtectionGradingInput(**dict(BASE_KWARGS, upstream_tms=0.35)))
    assert high.headline.value > low.headline.value


def test_different_curve_types_change_operating_times():
    si_result = calculate(ProtectionGradingInput(**BASE_KWARGS))
    ei_kwargs = dict(BASE_KWARGS, downstream_curve_type="extremely_inverse", upstream_curve_type="extremely_inverse")
    ei_result = calculate(ProtectionGradingInput(**ei_kwargs))
    t_down_si = next(t.value for t in si_result.terms if t.label.startswith("Downstream"))
    t_down_ei = next(t.value for t in ei_result.terms if t.label.startswith("Downstream"))
    assert t_down_si != pytest.approx(t_down_ei)


def test_fault_current_below_pickup_returns_uncomputable_result():
    kwargs = dict(BASE_KWARGS, fault_current_a=50.0)  # below both pickups
    result = calculate(ProtectionGradingInput(**kwargs))
    assert "Cannot compute" in result.headline.note
    assert any("must exceed both relays' pickup current" in w for w in result.warnings)


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        ProtectionGradingInput(**dict(BASE_KWARGS, fault_current_a=0.0))
    with pytest.raises(ValidationError):
        ProtectionGradingInput(**dict(BASE_KWARGS, downstream_tms=-0.1))


def test_all_four_curve_types_have_constants_defined():
    assert set(IDMT_CURVE_CONSTANTS.keys()) == {"standard_inverse", "very_inverse", "extremely_inverse", "long_time_inverse"}
