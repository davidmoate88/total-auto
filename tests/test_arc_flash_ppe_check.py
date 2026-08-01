"""
Tests for the arc flash PPE category check. This module deliberately does
NOT calculate incident energy (see module docstring) -- these tests only
verify the downstream classification/banding logic against a fixed,
directly-supplied incident energy figure.
"""

import pytest

from calcs.electrical_lv.arc_flash_ppe_check import (
    SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2,
    ArcFlashPpeCheckInput,
    calculate,
)


def _ppe_category(result):
    return next(t.note for t in result.terms if t.label == "PPE category")


def test_below_burn_threshold_no_safety_flag():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=0.5))
    exceeds = next(t.value for t in result.terms if t.label.startswith("Exceeds"))
    assert exceeds == 0.0
    assert not any(f.category == "safety" for f in result.risk_flags)


def test_at_or_above_burn_threshold_raises_medium_safety_flag():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2))
    exceeds = next(t.value for t in result.terms if t.label.startswith("Exceeds"))
    assert exceeds == 1.0
    assert any(f.category == "safety" and f.severity == "medium" for f in result.risk_flags)


def test_category_1_classification():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=3.0))
    assert _ppe_category(result) == "Category 1"


def test_category_2_classification():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=6.5))
    assert _ppe_category(result) == "Category 2"


def test_category_3_classification():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=20.0))
    assert _ppe_category(result) == "Category 3"


def test_category_4_classification():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=35.0))
    assert _ppe_category(result) == "Category 4"


def test_exceeds_category_4_is_dangerous_and_critical_flag():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=50.0))
    assert _ppe_category(result) == "Dangerous — exceeds Category 4"
    assert "DANGEROUS" in result.headline.note
    assert any(f.category == "safety" and f.severity == "critical" for f in result.risk_flags)


def test_boundary_value_falls_in_lower_band_inclusive():
    # Exactly at the category 1 max should still classify as Category 1 (<=), not Category 2.
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=4.0))
    assert _ppe_category(result) == "Category 1"


def test_custom_band_boundaries_override_defaults():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=5.0, category_1_max_cal_cm2=10.0))
    assert _ppe_category(result) == "Category 1"


def test_headline_value_equals_incident_energy_input():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=12.34))
    assert result.headline.value == pytest.approx(12.34)


def test_dangerous_energy_takes_precedence_over_medium_flag():
    result = calculate(ArcFlashPpeCheckInput(incident_energy_cal_cm2=45.0))
    severities = {f.severity for f in result.risk_flags if f.category == "safety"}
    assert severities == {"critical"}
