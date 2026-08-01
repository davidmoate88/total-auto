"""
Tests for the BS 7671 LV cable sizing / voltage drop module. The three
Regulation 433.1.1 conditions and the voltage drop arithmetic are hand-
verifiable directly from the inputs (not read from any BS 7671 table), which
is what's checked here.
"""

import pytest

from calcs.electrical_lv.cable_sizing_voltage_drop import (
    STANDARD_MCB_I2_FACTOR,
    CableSizingVoltageDropInput,
    calculate,
)

BASE_KWARGS = dict(
    design_current_a=28.0,
    protective_device_rating_a=32.0,
    tabulated_current_rating_a=36.0,
    rating_factor_ambient_temperature=0.94,
    cable_length_m=45.0,
    mv_per_a_per_m=1.5,
    nominal_voltage_v=230.0,
)


def test_iz_applies_all_correction_factors():
    result = calculate(CableSizingVoltageDropInput(**BASE_KWARGS))
    iz = next(t.value for t in result.terms if t.label.startswith("Iz"))
    assert iz == pytest.approx(36.0 * 0.94, rel=1e-9)


def test_default_i2_assumes_standard_mcb_factor():
    result = calculate(CableSizingVoltageDropInput(**BASE_KWARGS))
    i2 = next(t.value for t in result.terms if t.label.startswith("I2"))
    assert i2 == pytest.approx(STANDARD_MCB_I2_FACTOR * 32.0, rel=1e-9)
    assert any("device_i2_a not supplied" in w for w in result.warnings)


def test_supplied_i2_overrides_default_and_suppresses_warning():
    kwargs = dict(BASE_KWARGS, device_i2_a=50.0)
    result = calculate(CableSizingVoltageDropInput(**kwargs))
    i2 = next(t.value for t in result.terms if t.label.startswith("I2"))
    assert i2 == pytest.approx(50.0)
    assert not any("device_i2_a not supplied" in w for w in result.warnings)


def test_voltage_drop_matches_hand_calculation():
    result = calculate(CableSizingVoltageDropInput(**BASE_KWARGS))
    vd = next(t.value for t in result.terms if t.label == "Vd (voltage drop)")
    vd_percent = next(t.value for t in result.terms if t.label.startswith("Vd%"))
    expected_vd = 1.5 * 28.0 * 45.0 / 1000.0
    assert vd == pytest.approx(expected_vd, rel=1e-9)
    assert vd_percent == pytest.approx(expected_vd / 230.0 * 100.0, rel=1e-9)


def test_all_conditions_pass_gives_pass_headline():
    result = calculate(CableSizingVoltageDropInput(**BASE_KWARGS))
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_device_rating_below_design_current_fails_condition_1():
    kwargs = dict(BASE_KWARGS, design_current_a=35.0)  # Ib > In=32
    result = calculate(CableSizingVoltageDropInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any("Ib <= In" in w for w in result.warnings)
    assert any(f.severity == "critical" for f in result.risk_flags)


def test_undersized_cable_fails_condition_1_in_le_iz():
    kwargs = dict(BASE_KWARGS, tabulated_current_rating_a=20.0)  # Iz < In=32
    result = calculate(CableSizingVoltageDropInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any("In <= Iz" in w for w in result.warnings)


def test_high_i2_fails_condition_2():
    kwargs = dict(BASE_KWARGS, device_i2_a=200.0)
    result = calculate(CableSizingVoltageDropInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any("I2 <= 1.45*Iz" in w for w in result.warnings)


def test_long_cable_run_fails_voltage_drop():
    kwargs = dict(BASE_KWARGS, cable_length_m=500.0)
    result = calculate(CableSizingVoltageDropInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert "voltage drop" in result.headline.note
    assert any(f.description.startswith("Voltage drop") for f in result.risk_flags)


def test_governing_check_picks_the_higher_utilisation():
    # Voltage drop is deliberately made the binding constraint here.
    kwargs = dict(BASE_KWARGS, cable_length_m=200.0, tabulated_current_rating_a=100.0, rating_factor_ambient_temperature=1.0)
    result = calculate(CableSizingVoltageDropInput(**kwargs))
    current_u = next(t.value for t in result.terms if t.label == "Current-carrying utilisation")
    vd_u = next(t.value for t in result.terms if t.label == "Voltage drop utilisation")
    assert vd_u > current_u
    assert "voltage drop" in result.headline.note
    assert result.headline.value == pytest.approx(vd_u)


def test_zero_inputs_rejected_by_validation():
    with pytest.raises(Exception):
        CableSizingVoltageDropInput(**dict(BASE_KWARGS, design_current_a=0.0))
