"""
Tests for the Fellenius Method of Slices slope stability module.

The Fellenius formula (Sum[c'*l + (W*cosa - u*l)*tanphi'] / Sum[W*sina]) is
checked here against an independently hand-derived 3-slice example, the
same "derive independently" approach used throughout this repo -- not a
full slip-circle geometry check (this module deliberately doesn't generate
slice geometry itself, see the module docstring).
"""

import math

import pytest
from pydantic import ValidationError

from calcs.civil.slope_stability import Slice, SlopeStabilityInput, _fellenius_utilisation, _parse_slices, calculate

SAMPLE_SLICES = (
    "100, 30, 2.0, 10\n"
    "150, 15, 2.2, 15\n"
    "80, -5, 1.8, 5\n"
)


def _hand_derived_c1():
    # phi'=25 (unfactored), c'=5 (unfactored) -- see module docstring's worked example.
    phi = math.radians(25.0)
    slices = [
        (100.0, 30.0, 2.0, 10.0),
        (150.0, 15.0, 2.2, 15.0),
        (80.0, -5.0, 1.8, 5.0),
    ]
    resisting = sum(5.0 * l + (w * math.cos(math.radians(a)) - u * l) * math.tan(phi) for w, a, l, u in slices)
    driving = sum(w * math.sin(math.radians(a)) for w, a, l, u in slices)
    return resisting, driving


def test_parser_extracts_all_valid_lines_with_pore_pressure():
    slices, unparsed = _parse_slices(SAMPLE_SLICES)
    assert len(slices) == 3
    assert unparsed == []
    assert slices[0].pore_pressure_kpa == pytest.approx(10.0)


def test_parser_defaults_pore_pressure_to_zero_when_omitted():
    slices, unparsed = _parse_slices("120, 20, 2.0\n")
    assert len(slices) == 1
    assert unparsed == []
    assert slices[0].pore_pressure_kpa == pytest.approx(0.0)


def test_parser_reports_unparseable_lines():
    text = SAMPLE_SLICES + "garbage\n-50, 20, 2.0, 5\n"
    slices, unparsed = _parse_slices(text)
    assert len(slices) == 3
    assert len(unparsed) == 2


def test_fellenius_utilisation_matches_hand_derivation_da1_c1():
    slices, _ = _parse_slices(SAMPLE_SLICES)
    utilisation, resisting, driving = _fellenius_utilisation(slices, phi_d_deg=25.0, c_d_kpa=5.0)
    expected_resisting, expected_driving = _hand_derived_c1()
    assert resisting == pytest.approx(expected_resisting, rel=1e-9)
    assert driving == pytest.approx(expected_driving, rel=1e-9)
    assert utilisation == pytest.approx(expected_driving / expected_resisting, rel=1e-9)


def test_negative_base_angle_reduces_driving_force():
    # Slice 3 has a negative base angle (resisting zone near the toe) -- confirm
    # it reduces total driving force rather than adding to it.
    all_slices, _ = _parse_slices(SAMPLE_SLICES)
    without_slice_3, _ = _parse_slices("100, 30, 2.0, 10\n150, 15, 2.2, 15\n")
    _, _, driving_with = _fellenius_utilisation(all_slices, 25.0, 5.0)
    _, _, driving_without = _fellenius_utilisation(without_slice_3, 25.0, 5.0)
    assert driving_with < driving_without  # slice 3's negative contribution reduces the total


def test_da1_c2_governs_with_higher_utilisation():
    result = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=25, cohesion_c_prime_kpa=5, slices_text=SAMPLE_SLICES))
    util_c1 = next(t.value for t in result.terms if t.label == "[DA1-C1] Utilisation")
    util_c2 = next(t.value for t in result.terms if t.label == "[DA1-C2] Utilisation")
    assert util_c2 > util_c1
    assert result.headline.value == pytest.approx(util_c2)
    assert "DA1-C2" in result.headline.note


def test_utilisation_pass_and_fail():
    stable = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=35, cohesion_c_prime_kpa=10, slices_text=SAMPLE_SLICES))
    unstable = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=10, cohesion_c_prime_kpa=0, slices_text=SAMPLE_SLICES))
    util_stable = next(t.value for t in stable.terms if t.label == "Governing utilisation")
    util_unstable = next(t.value for t in unstable.terms if t.label == "Governing utilisation")
    assert util_stable < 1.0
    assert util_unstable > 1.0
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in unstable.risk_flags)
    assert not any(f.category == "code_compliance" for f in stable.risk_flags)


def test_marginal_utilisation_gets_bishop_recommendation_warning():
    # Tune phi' so the governing utilisation lands in the 0.9-1.0 "marginal" band.
    result = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=21, cohesion_c_prime_kpa=1, slices_text=SAMPLE_SLICES))
    util = next(t.value for t in result.terms if t.label == "Governing utilisation")
    if 0.9 < util <= 1.0:
        assert any("Bishop" in w for w in result.warnings)


def test_more_cohesion_or_friction_reduces_utilisation():
    weak = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=20, cohesion_c_prime_kpa=0, slices_text=SAMPLE_SLICES))
    strong = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=35, cohesion_c_prime_kpa=15, slices_text=SAMPLE_SLICES))
    util_weak = next(t.value for t in weak.terms if t.label == "Governing utilisation")
    util_strong = next(t.value for t in strong.terms if t.label == "Governing utilisation")
    assert util_strong < util_weak


def test_no_valid_slices_returns_infinite_utilisation_with_warning():
    result = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=30, slices_text="garbage\nmore garbage"))
    assert result.headline.value == float("inf")
    assert any("No valid slices parsed" in w for w in result.warnings)


def test_blank_slices_text_rejected():
    with pytest.raises(ValidationError):
        SlopeStabilityInput(friction_angle_phi_prime_deg=30, slices_text="   ")


def test_fellenius_warning_and_bishop_caveat_always_present():
    result = calculate(SlopeStabilityInput(friction_angle_phi_prime_deg=30, slices_text=SAMPLE_SLICES))
    assert any("Fellenius" in w and "CONSERVATIVE" in w for w in result.warnings)
