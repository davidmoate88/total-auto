"""
Tests for the foul drainage flow and pipe capacity module.

Manning's equation is the standard, well-established open-channel/pipe flow
formula, checked here for arithmetic consistency with the module's own
documented formula (see the module docstring's caveat about Colebrook-White
being the formally-required method for adoptable UK sewer design).
"""

import math

import pytest

from calcs.civil.foul_drainage import (
    MINIMUM_SELF_CLEANSING_VELOCITY_M_S,
    FoulDrainageInput,
    calculate,
)


def base_kwargs(**overrides):
    kwargs = dict(
        population_served=250,
        pipe_diameter_mm=150,
        pipe_gradient=1 / 80,
    )
    kwargs.update(overrides)
    return kwargs


def test_dry_weather_flow_matches_hand_calculation():
    inputs = FoulDrainageInput(**base_kwargs())
    result = calculate(inputs)
    expected_DWF = 250 * 150.0 / 86400.0
    DWF = next(t.value for t in result.terms if t.label.startswith("DWF"))
    assert DWF == pytest.approx(expected_DWF, rel=1e-9)


def test_peak_flow_applies_factor_and_adds_infiltration_after_peaking():
    inputs = FoulDrainageInput(**base_kwargs(peak_flow_factor=5.0, infiltration_allowance_l_s=1.0))
    result = calculate(inputs)
    DWF = next(t.value for t in result.terms if t.label.startswith("DWF"))
    Qp = next(t.value for t in result.terms if t.label.startswith("Qp"))
    assert Qp == pytest.approx(DWF * 5.0 + 1.0, rel=1e-9)


def test_trade_effluent_added_before_peaking():
    without = calculate(FoulDrainageInput(**base_kwargs()))
    with_trade = calculate(FoulDrainageInput(**base_kwargs(trade_effluent_l_s=2.0)))
    DWF_without = next(t.value for t in without.terms if t.label.startswith("DWF"))
    DWF_with = next(t.value for t in with_trade.terms if t.label.startswith("DWF"))
    Qp_without = next(t.value for t in without.terms if t.label.startswith("Qp"))
    Qp_with = next(t.value for t in with_trade.terms if t.label.startswith("Qp"))
    assert DWF_with == pytest.approx(DWF_without + 2.0, rel=1e-9)
    # Trade effluent is added before peaking -> its contribution to Qp is multiplied by peak_flow_factor.
    default_peak_factor = 6.0
    assert Qp_with == pytest.approx(Qp_without + 2.0 * default_peak_factor, rel=1e-9)


def test_manning_velocity_and_capacity_match_hand_calculation():
    inputs = FoulDrainageInput(**base_kwargs())
    result = calculate(inputs)

    D = 0.15
    A = math.pi * D**2 / 4
    R = D / 4
    S = 1 / 80
    n = 0.010
    expected_V = (1 / n) * R ** (2 / 3) * S ** 0.5
    expected_Q_capacity_l_s = expected_V * A * 1000.0

    V = next(t.value for t in result.terms if t.label.startswith("V ("))
    Q_capacity = next(t.value for t in result.terms if t.label.startswith("Q capacity"))
    assert V == pytest.approx(expected_V, rel=1e-9)
    assert Q_capacity == pytest.approx(expected_Q_capacity_l_s, rel=1e-9)


def test_larger_diameter_increases_capacity_and_reduces_utilisation():
    small = calculate(FoulDrainageInput(**base_kwargs(pipe_diameter_mm=100)))
    large = calculate(FoulDrainageInput(**base_kwargs(pipe_diameter_mm=225)))
    util_small = next(t.value for t in small.terms if t.label == "Utilisation")
    util_large = next(t.value for t in large.terms if t.label == "Utilisation")
    assert util_large < util_small


def test_shallow_gradient_triggers_self_cleansing_velocity_warning():
    shallow = calculate(FoulDrainageInput(**base_kwargs(pipe_diameter_mm=300, pipe_gradient=0.0005)))
    V = next(t.value for t in shallow.terms if t.label.startswith("V ("))
    assert V < MINIMUM_SELF_CLEANSING_VELOCITY_M_S
    assert any("self-cleansing" in w for w in shallow.warnings)
    assert any(f.category == "code_compliance" and f.severity == "medium" for f in shallow.risk_flags)


def test_steep_gradient_meets_self_cleansing_velocity_no_warning():
    steep = calculate(FoulDrainageInput(**base_kwargs(pipe_diameter_mm=150, pipe_gradient=1 / 40)))
    V = next(t.value for t in steep.terms if t.label.startswith("V ("))
    assert V >= MINIMUM_SELF_CLEANSING_VELOCITY_M_S
    assert not any("self-cleansing" in w for w in steep.warnings)


def test_utilisation_fail_raises_critical_risk_flag():
    undersized = calculate(FoulDrainageInput(**base_kwargs(population_served=500_000, pipe_diameter_mm=100)))
    util = next(t.value for t in undersized.terms if t.label == "Utilisation")
    assert util > 1.0
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in undersized.risk_flags)
    assert "FAIL" in undersized.headline.note


def test_headline_matches_utilisation_term():
    inputs = FoulDrainageInput(**base_kwargs())
    result = calculate(inputs)
    util = next(t.value for t in result.terms if t.label == "Utilisation")
    assert result.headline.value == pytest.approx(util)
