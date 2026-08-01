"""
Tests for the Rankine lateral earth pressure module.

Ka/Kp are the standard closed-form Rankine coefficients, checked against
long-established tabulated values (e.g. phi'=30 -> Ka=1/3 exactly, a
textbook value). The active-thrust integration is checked by hand-deriving
the trapezoidal decomposition for simple cases (dry, no cohesion; with
surcharge; with a water table), the same "derive independently, don't just
re-assert the implementation" approach used in test_bearing_capacity.py.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.civil.lateral_earth_pressure import (
    LateralEarthPressureInput,
    _active_thrust_and_lever_arm,
    calculate,
    rankine_coefficients,
)


def test_ka_kp_match_textbook_values_at_phi_30():
    Ka, Kp = rankine_coefficients(30)
    assert Ka == pytest.approx(1.0 / 3.0, rel=1e-3)
    assert Kp == pytest.approx(3.0, rel=1e-3)


def test_ka_kp_are_reciprocal():
    Ka, Kp = rankine_coefficients(25)
    assert Ka * Kp == pytest.approx(1.0, rel=1e-9)


def test_dry_no_cohesion_thrust_matches_classic_triangle_formula():
    # Pa = 0.5*Ka*gamma*H^2, acting at H/3 above the base -- the textbook
    # dry/no-surcharge/no-cohesion triangular pressure diagram result.
    phi, gamma, H = 30.0, 18.0, 3.0
    Ka, _ = rankine_coefficients(phi)
    expected_Pa = 0.5 * Ka * gamma * H**2
    expected_h_bar = H / 3

    Pa, h_bar, clipped = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, None, 0.0)
    assert Pa == pytest.approx(expected_Pa, rel=1e-9)
    assert h_bar == pytest.approx(expected_h_bar, rel=1e-9)
    assert not clipped


def test_surcharge_adds_rectangular_block_at_half_height():
    # A uniform surcharge contributes a rectangular pressure block Ka*q*H,
    # acting at exactly H/2 above the base, superposed on the triangle.
    phi, gamma, H, q = 30.0, 18.0, 3.0, 10.0
    Ka, _ = rankine_coefficients(phi)
    triangle_force = 0.5 * Ka * gamma * H**2
    triangle_h_bar = H / 3
    surcharge_force = Ka * q * H
    surcharge_h_bar = H / 2
    expected_Pa = triangle_force + surcharge_force
    expected_moment = triangle_force * triangle_h_bar + surcharge_force * surcharge_h_bar
    expected_h_bar = expected_moment / expected_Pa

    Pa, h_bar, _ = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, None, q)
    assert Pa == pytest.approx(expected_Pa, rel=1e-9)
    assert h_bar == pytest.approx(expected_h_bar, rel=1e-9)


def test_cohesion_reduces_thrust_and_flags_clipping_when_it_would_go_negative():
    phi, gamma, H = 30.0, 18.0, 3.0
    Pa_no_cohesion, _, clipped_none = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, None, 0.0)
    Pa_with_cohesion, _, clipped_some = _active_thrust_and_lever_arm(phi, 5.0, gamma, H, None, 0.0)
    assert Pa_with_cohesion < Pa_no_cohesion
    assert not clipped_none
    # A large cohesion relative to gamma*H drives near-surface pressure negative.
    _, _, clipped_large = _active_thrust_and_lever_arm(phi, 50.0, gamma, H, None, 0.0)
    assert clipped_large


def test_water_table_adds_hydrostatic_component():
    phi, gamma, H = 30.0, 18.0, 4.0
    Pa_dry, _, _ = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, None, 0.0)
    Pa_with_water, _, _ = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, 2.0, 0.0)
    assert Pa_with_water > Pa_dry


def test_water_table_at_full_depth_matches_no_water_table():
    phi, gamma, H = 30.0, 18.0, 3.0
    Pa_none, h_bar_none, _ = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, None, 0.0)
    Pa_at_base, h_bar_at_base, _ = _active_thrust_and_lever_arm(phi, 0.0, gamma, H, H, 0.0)
    assert Pa_none == pytest.approx(Pa_at_base, rel=1e-9)
    assert h_bar_none == pytest.approx(h_bar_at_base, rel=1e-9)


def test_da1_c2_produces_higher_thrust_than_c1_and_governs():
    inputs = LateralEarthPressureInput(
        friction_angle_phi_prime_deg=30, cohesion_c_prime_kpa=0, unit_weight_kn_m3=18,
        wall_height_m=3.0, surcharge_kpa=10.0,
    )
    result = calculate(inputs)
    Pa_c1 = next(t.value for t in result.terms if t.label == "[DA1-C1] Pa (active thrust)")
    Pa_c2 = next(t.value for t in result.terms if t.label == "[DA1-C2] Pa (active thrust)")
    assert Pa_c2 > Pa_c1
    assert result.headline.value == pytest.approx(Pa_c2)
    assert "DA1-C2" in result.headline.label


def test_water_table_deeper_than_wall_height_rejected():
    with pytest.raises(ValidationError):
        LateralEarthPressureInput(
            friction_angle_phi_prime_deg=30, unit_weight_kn_m3=18,
            wall_height_m=3.0, water_table_depth_m=4.0,
        )


def test_headline_reports_correct_height_of_application():
    inputs = LateralEarthPressureInput(
        friction_angle_phi_prime_deg=30, cohesion_c_prime_kpa=0, unit_weight_kn_m3=18,
        wall_height_m=3.0,
    )
    result = calculate(inputs)
    h_bar_c2 = next(t for t in result.terms if t.label == "[DA1-C2] Pa (active thrust)")
    reported_h_bar = float(h_bar_c2.note.split("h_bar=")[1].split("m")[0])
    # Dry, no surcharge/cohesion -> classic H/3 point of application, for any phi'.
    assert reported_h_bar == pytest.approx(3.0 / 3, rel=1e-2)
