"""
Tests for the motor starting current/voltage dip check. Starting current,
voltage dip, and utilisation are checked directly against a hand
calculation; the DOL-threshold risk flag is checked for both the trigger
and non-trigger cases (below threshold, above threshold but non-DOL method).
"""

import pytest
from pydantic import ValidationError

from calcs.electrical_lv.motor_starting import MotorStartingInput, calculate

BASE_KWARGS = dict(
    motor_rated_power_kw=7.5,
    full_load_current_a=14.5,
    starting_current_multiplier=6.5,
    source_fault_current_a=2500.0,
)


def test_starting_current_matches_hand_calculation():
    result = calculate(MotorStartingInput(**BASE_KWARGS))
    i_start = next(t.value for t in result.terms if t.label == "Starting current")
    assert i_start == pytest.approx(14.5 * 6.5, rel=1e-9)


def test_voltage_dip_matches_hand_calculation():
    result = calculate(MotorStartingInput(**BASE_KWARGS))
    dip = next(t.value for t in result.terms if t.label.startswith("Voltage dip"))
    expected = (14.5 * 6.5 / 2500.0) * 100.0
    assert dip == pytest.approx(expected, rel=1e-9)


def test_utilisation_passes_within_default_dip_limit():
    result = calculate(MotorStartingInput(**BASE_KWARGS))
    expected_dip = (14.5 * 6.5 / 2500.0) * 100.0
    assert result.headline.value == pytest.approx(expected_dip / 10.0, rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_weak_source_exceeds_dip_limit_and_raises_high_flag():
    kwargs = dict(BASE_KWARGS, source_fault_current_a=500.0)  # dip = 18.85% > 10% default
    result = calculate(MotorStartingInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any(f.category == "code_compliance" and f.severity == "high" for f in result.risk_flags)


def test_dol_start_above_threshold_raises_assumption_sensitivity_flag():
    result = calculate(MotorStartingInput(**BASE_KWARGS))  # 7.5kW > 5.5kW default threshold, method=dol
    assert any(f.category == "assumption_sensitivity" and f.severity == "medium" for f in result.risk_flags)


def test_dol_start_below_threshold_raises_no_flag():
    kwargs = dict(BASE_KWARGS, motor_rated_power_kw=3.0)
    result = calculate(MotorStartingInput(**kwargs))
    assert not any(f.category == "assumption_sensitivity" for f in result.risk_flags)


def test_non_dol_method_above_threshold_raises_no_dol_flag():
    kwargs = dict(BASE_KWARGS, starting_method="vsd")  # still 7.5kW > 5.5kW, but not DOL
    result = calculate(MotorStartingInput(**kwargs))
    assert not any(f.category == "assumption_sensitivity" for f in result.risk_flags)


def test_custom_dol_threshold_suppresses_flag():
    kwargs = dict(BASE_KWARGS, dol_starting_threshold_kw=10.0)  # 7.5kW no longer exceeds
    result = calculate(MotorStartingInput(**kwargs))
    assert not any(f.category == "assumption_sensitivity" for f in result.risk_flags)


def test_custom_dip_limit_changes_utilisation_but_not_dip_percent():
    default_run = calculate(MotorStartingInput(**BASE_KWARGS))
    tight_run = calculate(MotorStartingInput(**dict(BASE_KWARGS, max_permissible_voltage_dip_percent=2.0)))
    dip_default = next(t.value for t in default_run.terms if t.label.startswith("Voltage dip"))
    dip_tight = next(t.value for t in tight_run.terms if t.label.startswith("Voltage dip"))
    assert dip_default == pytest.approx(dip_tight, rel=1e-9)
    assert tight_run.headline.value > default_run.headline.value
    assert "FAIL" in tight_run.headline.note


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        MotorStartingInput(**dict(BASE_KWARGS, full_load_current_a=0.0))
    with pytest.raises(ValidationError):
        MotorStartingInput(**dict(BASE_KWARGS, starting_current_multiplier=-1.0))
    with pytest.raises(ValidationError):
        MotorStartingInput(**dict(BASE_KWARGS, source_fault_current_a=0.0))


def test_invalid_starting_method_rejected_by_validation():
    with pytest.raises(ValidationError):
        MotorStartingInput(**dict(BASE_KWARGS, starting_method="across_the_line"))
