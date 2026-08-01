"""
Tests for the single-vertical-rod earth electrode resistance module.
Dwight's formula (R = (rho/(2*pi*L))*(ln(4L/d)-1)) is checked directly
against a hand calculation, not read from any table.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.electrical_lv.earth_electrode_resistance import (
    EarthElectrodeResistanceInput,
    calculate,
)

BASE_KWARGS = dict(
    soil_resistivity_ohm_m=100.0,
    rod_length_m=3.0,
    rod_diameter_mm=16.0,
    target_earth_resistance_ohms=20.0,
)


def _expected_resistance(kwargs):
    d_m = kwargs["rod_diameter_mm"] / 1000.0
    L = kwargs["rod_length_m"]
    rho = kwargs["soil_resistivity_ohm_m"]
    return (rho / (2 * math.pi * L)) * (math.log(4 * L / d_m) - 1)


def test_resistance_matches_hand_calculation():
    result = calculate(EarthElectrodeResistanceInput(**BASE_KWARGS))
    r = next(t.value for t in result.terms if t.label.startswith("Earth electrode resistance"))
    assert r == pytest.approx(_expected_resistance(BASE_KWARGS), rel=1e-9)


def test_utilisation_matches_hand_calculation_and_fails():
    result = calculate(EarthElectrodeResistanceInput(**BASE_KWARGS))
    expected_r = _expected_resistance(BASE_KWARGS)
    expected_utilisation = expected_r / BASE_KWARGS["target_earth_resistance_ohms"]
    assert result.headline.value == pytest.approx(expected_utilisation, rel=1e-9)
    assert "FAIL" in result.headline.note
    assert any(f.category == "safety" and f.severity == "critical" for f in result.risk_flags)


def test_passes_with_a_lenient_target():
    kwargs = dict(BASE_KWARGS, target_earth_resistance_ohms=100.0)
    result = calculate(EarthElectrodeResistanceInput(**kwargs))
    assert "PASS" in result.headline.note
    assert not any(f.category == "safety" for f in result.risk_flags)


def test_longer_rod_reduces_resistance():
    short = calculate(EarthElectrodeResistanceInput(**dict(BASE_KWARGS, rod_length_m=1.5)))
    long = calculate(EarthElectrodeResistanceInput(**dict(BASE_KWARGS, rod_length_m=6.0)))
    r_short = next(t.value for t in short.terms if t.label.startswith("Earth electrode resistance"))
    r_long = next(t.value for t in long.terms if t.label.startswith("Earth electrode resistance"))
    assert r_long < r_short


def test_higher_soil_resistivity_increases_resistance():
    low = calculate(EarthElectrodeResistanceInput(**dict(BASE_KWARGS, soil_resistivity_ohm_m=50.0)))
    high = calculate(EarthElectrodeResistanceInput(**dict(BASE_KWARGS, soil_resistivity_ohm_m=500.0)))
    r_low = next(t.value for t in low.terms if t.label.startswith("Earth electrode resistance"))
    r_high = next(t.value for t in high.terms if t.label.startswith("Earth electrode resistance"))
    assert r_high > r_low


def test_larger_diameter_reduces_resistance_slightly():
    thin = calculate(EarthElectrodeResistanceInput(**dict(BASE_KWARGS, rod_diameter_mm=10.0)))
    thick = calculate(EarthElectrodeResistanceInput(**dict(BASE_KWARGS, rod_diameter_mm=25.0)))
    r_thin = next(t.value for t in thin.terms if t.label.startswith("Earth electrode resistance"))
    r_thick = next(t.value for t in thick.terms if t.label.startswith("Earth electrode resistance"))
    assert r_thick < r_thin


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        EarthElectrodeResistanceInput(**dict(BASE_KWARGS, rod_length_m=0.0))
    with pytest.raises(ValidationError):
        EarthElectrodeResistanceInput(**dict(BASE_KWARGS, target_earth_resistance_ohms=-1.0))


def test_multiple_rod_warning_always_present():
    result = calculate(EarthElectrodeResistanceInput(**BASE_KWARGS))
    assert any("Single vertical driven rod only" in w for w in result.warnings)
