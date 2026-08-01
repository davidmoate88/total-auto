"""
Tests for the substation earth grid resistance / touch/step potential
check. Sverak's grid resistance formula and the IEEE 80 tolerable
touch/step voltage formulas are checked directly against a hand
calculation -- the actual mesh/step voltage inputs are treated as opaque
external study outputs (see module docstring for why), not derived here.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.electrical_hv.substation_earthing_touch_step import (
    BODY_WEIGHT_CONSTANTS,
    SubstationEarthingTouchStepInput,
    calculate,
)

BASE_KWARGS = dict(
    soil_resistivity_ohm_m=100.0,
    grid_area_m2=400.0,
    total_buried_conductor_length_m=200.0,
    burial_depth_m=0.5,
    target_grid_resistance_ohms=5.0,
    surface_layer_resistivity_ohm_m=3000.0,
    surface_layer_thickness_m=0.1,
    fault_clearance_time_s=0.5,
    actual_mesh_voltage_v=400.0,
    actual_step_voltage_v=1500.0,
)


def _expected_rg(k):
    rho, A, Lt, h = k["soil_resistivity_ohm_m"], k["grid_area_m2"], k["total_buried_conductor_length_m"], k["burial_depth_m"]
    return rho * (1 / Lt + (1 / math.sqrt(20 * A)) * (1 + 1 / (1 + h * math.sqrt(20 / A))))


def _expected_cs(k):
    rho, rho_s, hs = k["soil_resistivity_ohm_m"], k["surface_layer_resistivity_ohm_m"], k["surface_layer_thickness_m"]
    return 1 - 0.09 * (1 - rho / rho_s) / (2 * hs + 0.09)


def _expected_tolerable(k, body_weight=50):
    cs = _expected_cs(k)
    rho_s, ts = k["surface_layer_resistivity_ohm_m"], k["fault_clearance_time_s"]
    kfac = BODY_WEIGHT_CONSTANTS[body_weight]
    touch = (1000 + 1.5 * cs * rho_s) * kfac / math.sqrt(ts)
    step = (1000 + 6.0 * cs * rho_s) * kfac / math.sqrt(ts)
    return touch, step


def test_grid_resistance_matches_hand_calculation():
    result = calculate(SubstationEarthingTouchStepInput(**BASE_KWARGS))
    rg = next(t.value for t in result.terms if t.label.startswith("Grid resistance to"))
    assert rg == pytest.approx(_expected_rg(BASE_KWARGS), rel=1e-9)


def test_cs_matches_hand_calculation():
    result = calculate(SubstationEarthingTouchStepInput(**BASE_KWARGS))
    cs = next(t.value for t in result.terms if t.label.startswith("Cs"))
    assert cs == pytest.approx(_expected_cs(BASE_KWARGS), rel=1e-9)


def test_tolerable_touch_and_step_voltage_match_hand_calculation():
    result = calculate(SubstationEarthingTouchStepInput(**BASE_KWARGS))
    expected_touch, expected_step = _expected_tolerable(BASE_KWARGS)
    touch = next(t.value for t in result.terms if t.label.startswith("Tolerable touch"))
    step = next(t.value for t in result.terms if t.label.startswith("Tolerable step"))
    assert touch == pytest.approx(expected_touch, rel=1e-9)
    assert step == pytest.approx(expected_step, rel=1e-9)


def test_70kg_body_weight_uses_different_constant():
    result_50 = calculate(SubstationEarthingTouchStepInput(**BASE_KWARGS))
    result_70 = calculate(SubstationEarthingTouchStepInput(**dict(BASE_KWARGS, body_weight_kg=70)))
    touch_50 = next(t.value for t in result_50.terms if t.label.startswith("Tolerable touch"))
    touch_70 = next(t.value for t in result_70.terms if t.label.startswith("Tolerable touch"))
    assert touch_70 > touch_50  # 70kg constant (0.157) > 50kg constant (0.116)


def test_all_pass_gives_pass_headline_governed_by_step_voltage():
    result = calculate(SubstationEarthingTouchStepInput(**BASE_KWARGS))
    assert "PASS" in result.headline.note
    assert "step voltage" in result.headline.note
    assert not any(f.category == "safety" for f in result.risk_flags)


def test_undersized_grid_fails_grid_resistance():
    kwargs = dict(BASE_KWARGS, target_grid_resistance_ohms=1.0)  # Rg ~2.62 > 1.0
    result = calculate(SubstationEarthingTouchStepInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any("FAILS grid resistance" in w for w in result.warnings)
    assert any(f.category == "safety" and f.severity == "critical" for f in result.risk_flags)


def test_excessive_actual_touch_voltage_fails():
    kwargs = dict(BASE_KWARGS, actual_mesh_voltage_v=900.0)  # exceeds ~681V tolerable
    result = calculate(SubstationEarthingTouchStepInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any("FAILS touch voltage" in w for w in result.warnings)


def test_excessive_actual_step_voltage_fails():
    kwargs = dict(BASE_KWARGS, actual_step_voltage_v=3000.0)  # exceeds ~2231V tolerable
    result = calculate(SubstationEarthingTouchStepInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any("FAILS step voltage" in w for w in result.warnings)


def test_larger_surface_layer_resistivity_increases_tolerable_voltage():
    low = calculate(SubstationEarthingTouchStepInput(**dict(BASE_KWARGS, surface_layer_resistivity_ohm_m=100.0)))
    high = calculate(SubstationEarthingTouchStepInput(**dict(BASE_KWARGS, surface_layer_resistivity_ohm_m=5000.0)))
    touch_low = next(t.value for t in low.terms if t.label.startswith("Tolerable touch"))
    touch_high = next(t.value for t in high.terms if t.label.startswith("Tolerable touch"))
    assert touch_high > touch_low


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        SubstationEarthingTouchStepInput(**dict(BASE_KWARGS, grid_area_m2=0.0))
    with pytest.raises(ValidationError):
        SubstationEarthingTouchStepInput(**dict(BASE_KWARGS, actual_mesh_voltage_v=-1.0))
