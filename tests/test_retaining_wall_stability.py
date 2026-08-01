"""
Tests for the retaining wall stability (sliding/overturning/bearing) module.

Reuses lateral_earth_pressure.py's already-tested rankine_coefficients() and
_active_thrust_and_lever_arm() to independently re-derive expected sliding/
overturning/bearing values, rather than re-asserting the module's own
arithmetic against itself.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.civil.lateral_earth_pressure import _active_thrust_and_lever_arm, rankine_coefficients
from calcs.geotechnical.bearing_capacity import DA1_C1, DA1_C2
from calcs.civil.retaining_wall_stability import RetainingWallStabilityInput, calculate


def base_kwargs(**overrides):
    kwargs = dict(
        friction_angle_phi_prime_deg=30, cohesion_c_prime_kpa=0, unit_weight_kn_m3=18,
        wall_height_m=3.0, surcharge_kpa=10.0,
        friction_angle_phi_prime_front_deg=30, unit_weight_front_kn_m3=18, embedment_depth_m=0.8,
        base_width_m=2.2, self_weight_kn_m=85.0, self_weight_lever_arm_from_toe_m=1.1,
        base_friction_coefficient=0.5, allowable_bearing_pressure_kpa=150.0,
    )
    kwargs.update(overrides)
    return kwargs


def _expected_combination(inputs_kwargs: dict, factors):
    phi_d = math.degrees(math.atan(math.tan(math.radians(inputs_kwargs["friction_angle_phi_prime_deg"])) / factors.gamma_phi))
    c_d = inputs_kwargs["cohesion_c_prime_kpa"] / factors.gamma_c
    Pa, h_bar, _ = _active_thrust_and_lever_arm(
        phi_d, c_d, inputs_kwargs["unit_weight_kn_m3"], inputs_kwargs["wall_height_m"],
        inputs_kwargs.get("water_table_depth_m"), inputs_kwargs["surcharge_kpa"],
    )
    phi_front_d = math.degrees(math.atan(math.tan(math.radians(inputs_kwargs["friction_angle_phi_prime_front_deg"])) / factors.gamma_phi))
    _, Kp_front_d = rankine_coefficients(phi_front_d)
    D = inputs_kwargs["embedment_depth_m"]
    Pp = 0.5 * Kp_front_d * inputs_kwargs["unit_weight_front_kn_m3"] * D**2
    N = inputs_kwargs["self_weight_kn_m"]
    sliding_resistance = N * inputs_kwargs["base_friction_coefficient"] + Pp
    sliding_util = Pa / sliding_resistance
    overturning_resisting = N * inputs_kwargs["self_weight_lever_arm_from_toe_m"] + Pp * D / 3
    overturning_util = (Pa * h_bar) / overturning_resisting
    return {"Pa": Pa, "h_bar": h_bar, "sliding_util": sliding_util, "overturning_util": overturning_util}


def test_sliding_utilisation_matches_independent_hand_calculation():
    kwargs = base_kwargs()
    result = calculate(RetainingWallStabilityInput(**kwargs))
    expected_c1 = _expected_combination(kwargs, DA1_C1)
    expected_c2 = _expected_combination(kwargs, DA1_C2)

    u_c1 = next(t.value for t in result.terms if t.label == "[DA1-C1] Sliding utilisation")
    u_c2 = next(t.value for t in result.terms if t.label == "[DA1-C2] Sliding utilisation")
    assert u_c1 == pytest.approx(expected_c1["sliding_util"], rel=1e-6)
    assert u_c2 == pytest.approx(expected_c2["sliding_util"], rel=1e-6)


def test_overturning_utilisation_matches_independent_hand_calculation():
    kwargs = base_kwargs()
    result = calculate(RetainingWallStabilityInput(**kwargs))
    expected_c1 = _expected_combination(kwargs, DA1_C1)
    expected_c2 = _expected_combination(kwargs, DA1_C2)

    u_c1 = next(t.value for t in result.terms if t.label == "[DA1-C1] Overturning utilisation")
    u_c2 = next(t.value for t in result.terms if t.label == "[DA1-C2] Overturning utilisation")
    assert u_c1 == pytest.approx(expected_c1["overturning_util"], rel=1e-6)
    assert u_c2 == pytest.approx(expected_c2["overturning_util"], rel=1e-6)


def test_da1_c2_governs_sliding_for_this_symmetric_case():
    # Weaker factored soil strength (both retained and passive sides) under
    # DA1-C2 reduces passive resistance and raises active thrust -> C2 governs.
    result = calculate(RetainingWallStabilityInput(**base_kwargs()))
    governing = next(t for t in result.terms if t.label == "Sliding utilisation (governing)")
    assert "DA1-C2" in governing.note


def test_more_self_weight_improves_sliding_and_overturning_but_worsens_bearing():
    # A classic retaining wall design trade-off: more self-weight improves
    # friction (sliding) and resisting moment (overturning) but directly
    # increases the bearing demand on the founding material -- the module
    # should reflect this real trade-off, not "more weight is free stability."
    light = calculate(RetainingWallStabilityInput(**base_kwargs(self_weight_kn_m=85.0)))
    heavy = calculate(RetainingWallStabilityInput(**base_kwargs(self_weight_kn_m=200.0)))
    for label in ("Sliding utilisation (governing)", "Overturning utilisation (governing)"):
        u_light = next(t.value for t in light.terms if t.label == label)
        u_heavy = next(t.value for t in heavy.terms if t.label == label)
        assert u_heavy < u_light

    bearing_light = next(t.value for t in light.terms if t.label == "Bearing utilisation (governing)")
    bearing_heavy = next(t.value for t in heavy.terms if t.label == "Bearing utilisation (governing)")
    assert bearing_heavy > bearing_light


def test_deeper_embedment_improves_sliding_and_overturning():
    shallow = calculate(RetainingWallStabilityInput(**base_kwargs(embedment_depth_m=0.3)))
    deep = calculate(RetainingWallStabilityInput(**base_kwargs(embedment_depth_m=1.2)))
    for label in ("Sliding utilisation (governing)", "Overturning utilisation (governing)"):
        u_shallow = next(t.value for t in shallow.terms if t.label == label)
        u_deep = next(t.value for t in deep.terms if t.label == label)
        assert u_deep < u_shallow


def test_eccentricity_and_middle_third_flag():
    inputs = RetainingWallStabilityInput(**base_kwargs())
    result = calculate(inputs)
    e_c1 = next(t for t in result.terms if t.label == "Eccentricity e [DA1-C1]")
    B = 2.2
    if abs(e_c1.value) > B / 6:
        assert "OUTSIDE" in e_c1.note
        assert any("middle third" in w for w in result.warnings)
    else:
        assert "within" in e_c1.note


def test_utilisation_fail_raises_critical_risk_flag():
    weak = calculate(RetainingWallStabilityInput(**base_kwargs(
        self_weight_kn_m=10.0, base_friction_coefficient=0.2, embedment_depth_m=0.1,
    )))
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in weak.risk_flags)
    assert any("FAILS" in w for w in weak.warnings)


def test_healthy_wall_passes_with_no_critical_flags():
    healthy = calculate(RetainingWallStabilityInput(**base_kwargs(self_weight_kn_m=200.0, base_width_m=3.0, self_weight_lever_arm_from_toe_m=1.5)))
    assert not any(f.category == "code_compliance" for f in healthy.risk_flags)
    governing = healthy.headline.value
    assert governing <= 1.0


def test_governing_check_is_max_across_three_checks():
    result = calculate(RetainingWallStabilityInput(**base_kwargs()))
    sliding = next(t.value for t in result.terms if t.label == "Sliding utilisation (governing)")
    overturning = next(t.value for t in result.terms if t.label == "Overturning utilisation (governing)")
    bearing = next(t.value for t in result.terms if t.label == "Bearing utilisation (governing)")
    assert result.headline.value == pytest.approx(max(sliding, overturning, bearing))


def test_self_weight_lever_arm_cannot_exceed_base_width():
    with pytest.raises(ValidationError):
        RetainingWallStabilityInput(**base_kwargs(self_weight_lever_arm_from_toe_m=5.0, base_width_m=2.2))


def test_water_table_deeper_than_wall_height_rejected():
    with pytest.raises(ValidationError):
        RetainingWallStabilityInput(**base_kwargs(water_table_depth_m=10.0, wall_height_m=3.0))
