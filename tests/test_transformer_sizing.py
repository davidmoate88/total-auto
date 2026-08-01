"""
Tests for the HV/LV transformer sizing check. Required capacity, utilisation,
and full-load current are checked directly against a hand calculation.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.electrical_hv.transformer_sizing import (
    TransformerSizingInput,
    calculate,
)

BASE_KWARGS = dict(
    lv_demand_kva=26.0,
    rated_transformer_kva=100.0,
    hv_voltage_kv=11.0,
)


def test_required_capacity_applies_default_growth_margin():
    result = calculate(TransformerSizingInput(**BASE_KWARGS))
    required = next(t.value for t in result.terms if t.label.startswith("Required capacity"))
    assert required == pytest.approx(26.0 * 1.20, rel=1e-9)


def test_utilisation_matches_hand_calculation_and_passes():
    result = calculate(TransformerSizingInput(**BASE_KWARGS))
    expected_utilisation = (26.0 * 1.20) / 100.0
    assert result.headline.value == pytest.approx(expected_utilisation, rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_hv_full_load_current_matches_hand_calculation():
    result = calculate(TransformerSizingInput(**BASE_KWARGS))
    i_hv = next(t.value for t in result.terms if t.label.startswith("HV full-load current"))
    assert i_hv == pytest.approx(100.0 / (math.sqrt(3) * 11.0), rel=1e-9)


def test_lv_full_load_current_matches_hand_calculation_with_default_voltage():
    result = calculate(TransformerSizingInput(**BASE_KWARGS))
    i_lv = next(t.value for t in result.terms if t.label.startswith("LV full-load current"))
    assert i_lv == pytest.approx(100.0 / (math.sqrt(3) * 0.400), rel=1e-9)


def test_custom_lv_voltage_changes_lv_current_only():
    result = calculate(TransformerSizingInput(**dict(BASE_KWARGS, lv_voltage_kv=0.433)))
    i_lv = next(t.value for t in result.terms if t.label.startswith("LV full-load current"))
    i_hv = next(t.value for t in result.terms if t.label.startswith("HV full-load current"))
    assert i_lv == pytest.approx(100.0 / (math.sqrt(3) * 0.433), rel=1e-9)
    assert i_hv == pytest.approx(100.0 / (math.sqrt(3) * 11.0), rel=1e-9)


def test_undersized_transformer_fails_and_raises_critical_flag():
    kwargs = dict(BASE_KWARGS, rated_transformer_kva=20.0)  # required=31.2 > 20
    result = calculate(TransformerSizingInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)


def test_zero_growth_margin_reduces_required_capacity_to_demand():
    result = calculate(TransformerSizingInput(**dict(BASE_KWARGS, growth_margin_percent=0.0)))
    required = next(t.value for t in result.terms if t.label.startswith("Required capacity"))
    assert required == pytest.approx(26.0, rel=1e-9)


def test_higher_growth_margin_increases_utilisation():
    low_margin = calculate(TransformerSizingInput(**dict(BASE_KWARGS, growth_margin_percent=0.0)))
    high_margin = calculate(TransformerSizingInput(**dict(BASE_KWARGS, growth_margin_percent=50.0)))
    assert high_margin.headline.value > low_margin.headline.value


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        TransformerSizingInput(**dict(BASE_KWARGS, lv_demand_kva=0.0))
    with pytest.raises(ValidationError):
        TransformerSizingInput(**dict(BASE_KWARGS, hv_voltage_kv=-1.0))
