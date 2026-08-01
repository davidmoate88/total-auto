"""
Tests for the HV arc flash PPE requirement check. This module deliberately
does NOT calculate incident energy (see module docstring) -- these tests
only verify the downstream required-PPE-rating/practical-limit logic
against a fixed, directly-supplied incident energy figure.
"""

import pytest

from calcs.electrical_hv.arc_flash_ppe_check import (
    SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2,
    HVArcFlashPpeCheckInput,
    calculate,
)


def test_below_burn_threshold_no_safety_flag():
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=0.5))
    exceeds = next(t.value for t in result.terms if t.label.startswith("Exceeds second-degree"))
    assert exceeds == 0.0
    assert not any(f.category == "safety" for f in result.risk_flags)


def test_at_or_above_burn_threshold_raises_high_safety_flag():
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=SECOND_DEGREE_BURN_THRESHOLD_CAL_CM2))
    exceeds = next(t.value for t in result.terms if t.label.startswith("Exceeds second-degree"))
    assert exceeds == 1.0
    assert any(f.category == "safety" and f.severity == "high" for f in result.risk_flags)


def test_required_ppe_rating_equals_incident_energy():
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=55.0))
    required = next(t.value for t in result.terms if t.label == "Required PPE arc rating")
    assert required == pytest.approx(55.0)
    assert result.headline.value == pytest.approx(55.0)


def test_within_practical_limit_gives_ppe_required_headline():
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=55.0))
    assert result.headline.note == "PPE required"


def test_exceeds_practical_limit_is_dangerous_and_critical_flag():
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=150.0))
    assert "DANGEROUS" in result.headline.note
    assert any(f.category == "safety" and f.severity == "critical" for f in result.risk_flags)
    # High-severity "PPE required" flag should not also be present once critical governs.
    severities = {f.severity for f in result.risk_flags if f.category == "safety"}
    assert severities == {"critical"}


def test_custom_practical_limit_changes_the_boundary():
    kwargs_default = HVArcFlashPpeCheckInput(incident_energy_cal_cm2=55.0)
    kwargs_lower_limit = HVArcFlashPpeCheckInput(incident_energy_cal_cm2=55.0, practical_ppe_arc_rating_limit_cal_cm2=40.0)
    result_default = calculate(kwargs_default)
    result_lower_limit = calculate(kwargs_lower_limit)
    assert "DANGEROUS" not in result_default.headline.note
    assert "DANGEROUS" in result_lower_limit.headline.note


def test_boundary_value_at_practical_limit_is_not_dangerous():
    # Exactly at the limit should still be within practical PPE range (> is the failure condition, not >=).
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=100.0, practical_ppe_arc_rating_limit_cal_cm2=100.0))
    exceeds = next(t.value for t in result.terms if t.label.startswith("Exceeds practical"))
    assert exceeds == 0.0


def test_hv_uses_high_severity_not_medium_for_ppe_required_case():
    # Distinct from the equivalent LV module, which uses medium severity for the same scenario.
    result = calculate(HVArcFlashPpeCheckInput(incident_energy_cal_cm2=10.0))
    flag = next(f for f in result.risk_flags if f.category == "safety")
    assert flag.severity == "high"
