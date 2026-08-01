"""
Tests for the pipe line sizing / velocity check. Actual velocity and the
API RP 14E erosional velocity limit are checked directly against a hand
calculation.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.mechanical_piping.line_sizing_velocity_check import (
    FT_TO_M,
    KG_M3_TO_LB_FT3,
    LineSizingVelocityCheckInput,
    calculate,
)

BASE_KWARGS = dict(
    flow_rate_m3_h=100.0,
    actual_internal_diameter_mm=100.0,
    fluid_density_kg_m3=1000.0,
)


def _expected_velocity(k):
    Q = k["flow_rate_m3_h"] / 3600.0
    D = k["actual_internal_diameter_mm"] / 1000.0
    A = math.pi / 4 * D**2
    return Q / A


def _expected_erosional_velocity(k):
    C = k.get("erosional_velocity_constant_c", 100.0)
    rho_lb_ft3 = k["fluid_density_kg_m3"] * KG_M3_TO_LB_FT3
    return (C / math.sqrt(rho_lb_ft3)) * FT_TO_M


def test_actual_velocity_matches_hand_calculation():
    result = calculate(LineSizingVelocityCheckInput(**BASE_KWARGS))
    v = next(t.value for t in result.terms if t.label == "Actual velocity")
    assert v == pytest.approx(_expected_velocity(BASE_KWARGS), rel=1e-9)


def test_erosional_velocity_matches_hand_calculation():
    result = calculate(LineSizingVelocityCheckInput(**BASE_KWARGS))
    ve = next(t.value for t in result.terms if t.label.startswith("Erosional velocity"))
    assert ve == pytest.approx(_expected_erosional_velocity(BASE_KWARGS), rel=1e-9)


def test_erosional_utilisation_matches_hand_calculation_and_passes():
    result = calculate(LineSizingVelocityCheckInput(**BASE_KWARGS))
    expected_v = _expected_velocity(BASE_KWARGS)
    expected_ve = _expected_erosional_velocity(BASE_KWARGS)
    assert result.headline.value == pytest.approx(expected_v / expected_ve, rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_within_target_range_raises_no_buildability_flag():
    result = calculate(LineSizingVelocityCheckInput(**BASE_KWARGS))
    assert not any(f.category == "buildability" for f in result.risk_flags)


def test_undersized_pipe_exceeds_erosional_limit_and_fails():
    kwargs = dict(BASE_KWARGS, actual_internal_diameter_mm=40.0)  # much smaller bore -> high velocity
    result = calculate(LineSizingVelocityCheckInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert result.headline.value > 1.0
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)


def test_oversized_pipe_below_target_range_raises_buildability_flag():
    kwargs = dict(BASE_KWARGS, actual_internal_diameter_mm=300.0)  # much larger bore -> low velocity
    result = calculate(LineSizingVelocityCheckInput(**kwargs))
    assert any(f.category == "buildability" for f in result.risk_flags)
    assert any("below the minimum" in w for w in result.warnings)


def test_above_target_but_below_erosional_raises_buildability_not_code_compliance():
    # Higher density raises the erosional limit well above the target range,
    # so a velocity above the target max can still pass the erosional check.
    kwargs = dict(BASE_KWARGS, actual_internal_diameter_mm=70.0, fluid_density_kg_m3=200.0)
    result = calculate(LineSizingVelocityCheckInput(**kwargs))
    v = next(t.value for t in result.terms if t.label == "Actual velocity")
    assert v > 5.0
    assert "PASS" in result.headline.note
    assert any(f.category == "buildability" for f in result.risk_flags)
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_higher_density_reduces_erosional_velocity_limit():
    light = calculate(LineSizingVelocityCheckInput(**dict(BASE_KWARGS, fluid_density_kg_m3=100.0)))
    heavy = calculate(LineSizingVelocityCheckInput(**dict(BASE_KWARGS, fluid_density_kg_m3=1500.0)))
    ve_light = next(t.value for t in light.terms if t.label.startswith("Erosional velocity"))
    ve_heavy = next(t.value for t in heavy.terms if t.label.startswith("Erosional velocity"))
    assert ve_heavy < ve_light


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        LineSizingVelocityCheckInput(**dict(BASE_KWARGS, flow_rate_m3_h=0.0))
    with pytest.raises(ValidationError):
        LineSizingVelocityCheckInput(**dict(BASE_KWARGS, fluid_density_kg_m3=-1.0))
