"""
Tests for the EN 1993-1-8 bolted shear connection module.

The alpha_b/k1 bearing-resistance formula is checked here for arithmetic
consistency with the module's own documented formulae (see the module
docstring's caveat about this method's confidence level, and about
alpha_v being a required direct input rather than a built-in table).
"""

import pytest
from pydantic import ValidationError

from calcs.structural.bolted_shear_connection import (
    GAMMA_M2,
    BoltedShearConnectionInput,
    calculate,
)


def base_kwargs(**overrides):
    kwargs = dict(
        bolt_grade="8.8",
        bolt_diameter_mm=20.0,
        bolt_shear_area_mm2=245.0,
        shear_resistance_factor_alpha_v=0.6,
        connected_ply_thickness_mm=10.0,
        connected_ply_ultimate_strength_mpa=430.0,
        hole_diameter_mm=22.0,
        end_distance_mm=40.0,
        edge_distance_mm=40.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_bolt_ultimate_strength_matches_grade_definition():
    inputs = BoltedShearConnectionInput(**base_kwargs())
    result = calculate(inputs)
    fub = next(t.value for t in result.terms if t.label.startswith("fub"))
    assert fub == pytest.approx(800.0)


def test_shear_resistance_matches_hand_calculation():
    inputs = BoltedShearConnectionInput(**base_kwargs())
    result = calculate(inputs)
    expected_Fv_Rd = 0.6 * 800.0 * 245.0 / GAMMA_M2 / 1e3
    Fv_Rd = next(t.value for t in result.terms if t.label == "Fv,Rd (shear resistance, per shear plane)")
    assert Fv_Rd == pytest.approx(expected_Fv_Rd, rel=1e-9)


def test_double_shear_doubles_per_bolt_resistance():
    single = calculate(BoltedShearConnectionInput(**base_kwargs(shear_planes_per_bolt=1)))
    double = calculate(BoltedShearConnectionInput(**base_kwargs(shear_planes_per_bolt=2)))
    Fv_single = next(t.value for t in single.terms if t.label == "Fv,Rd (shear resistance, per bolt)")
    Fv_double = next(t.value for t in double.terms if t.label == "Fv,Rd (shear resistance, per bolt)")
    assert Fv_double == pytest.approx(2 * Fv_single)


def test_bearing_resistance_matches_hand_calculation_single_bolt():
    inputs = BoltedShearConnectionInput(**base_kwargs())
    result = calculate(inputs)

    d0 = 22.0
    alpha_d = 40.0 / (3 * d0)  # end-bolt only, single bolt
    alpha_b = min(alpha_d, 800.0 / 430.0, 1.0)
    k1 = min(2.8 * 40.0 / d0 - 1.7, 2.5)
    expected_Fb_Rd = k1 * alpha_b * 430.0 * 20.0 * 10.0 / GAMMA_M2 / 1e3

    Fb_Rd = next(t.value for t in result.terms if t.label.startswith("Fb,Rd"))
    assert Fb_Rd == pytest.approx(expected_Fb_Rd, rel=1e-9)


def test_multi_bolt_group_uses_lower_of_end_and_inner_alpha_d():
    # end-bolt alpha_d = 40/(3*22) = 0.606; inner-bolt (p1=60) = 60/(3*22)-0.25 = 0.659
    # -> end-bolt formula governs (lower), so alpha_d should match the single-bolt case.
    single = calculate(BoltedShearConnectionInput(**base_kwargs()))
    grouped = calculate(BoltedShearConnectionInput(**base_kwargs(number_of_bolts=2, bolt_pitch_mm=60.0)))
    alpha_d_single = next(t.value for t in single.terms if t.label == "alpha_d")
    alpha_d_grouped = next(t.value for t in grouped.terms if t.label == "alpha_d")
    assert alpha_d_grouped == pytest.approx(alpha_d_single)


def test_tight_pitch_makes_inner_bolt_formula_govern():
    # p1=30 -> inner-bolt alpha_d = 30/(3*22)-0.25 = 0.2045, well below the
    # end-bolt value (0.606) -- inner formula should govern here.
    result = calculate(BoltedShearConnectionInput(**base_kwargs(number_of_bolts=2, bolt_pitch_mm=30.0)))
    alpha_d = next(t.value for t in result.terms if t.label == "alpha_d")
    expected_inner = 30.0 / (3 * 22.0) - 0.25
    assert alpha_d == pytest.approx(expected_inner)


def test_gauge_reduces_k1_when_tight():
    # p2=25 -> inner k1 = 1.4*25/22-1.7 = 0.891, well below the edge value (2.5).
    result = calculate(BoltedShearConnectionInput(**base_kwargs(number_of_bolts=2, bolt_pitch_mm=60.0, bolt_gauge_mm=25.0)))
    k1 = next(t.value for t in result.terms if t.label == "k1")
    expected_k1_inner = 1.4 * 25.0 / 22.0 - 1.7
    assert k1 == pytest.approx(expected_k1_inner)


def test_group_resistance_scales_with_bolt_count():
    one = calculate(BoltedShearConnectionInput(**base_kwargs()))
    three = calculate(BoltedShearConnectionInput(**base_kwargs(number_of_bolts=3, bolt_pitch_mm=60.0)))
    group_one = next(t.value for t in one.terms if t.label == "Group resistance")
    group_three = next(t.value for t in three.terms if t.label == "Group resistance")
    per_bolt_one = next(t.value for t in one.terms if t.label == "Governing resistance per bolt")
    per_bolt_three = next(t.value for t in three.terms if t.label == "Governing resistance per bolt")
    assert group_one == pytest.approx(per_bolt_one)
    assert group_three == pytest.approx(per_bolt_three * 3)


def test_no_load_gives_resistance_only_headline():
    inputs = BoltedShearConnectionInput(**base_kwargs())
    result = calculate(inputs)
    assert "Group resistance" in result.headline.label
    assert not any(t.label == "VEd (design shear on group)" for t in result.terms)


def test_design_shear_arithmetic():
    inputs = BoltedShearConnectionInput(**base_kwargs(applied_shear_permanent_kn=30.0, applied_shear_variable_kn=20.0))
    result = calculate(inputs)
    VEd = next(t.value for t in result.terms if t.label.startswith("VEd"))
    assert VEd == pytest.approx(1.35 * 30.0 + 1.5 * 20.0)


def test_utilisation_pass_and_fail():
    light = calculate(BoltedShearConnectionInput(**base_kwargs(applied_shear_permanent_kn=10.0, applied_shear_variable_kn=5.0)))
    heavy = calculate(BoltedShearConnectionInput(**base_kwargs(applied_shear_permanent_kn=100.0, applied_shear_variable_kn=100.0)))
    util_light = next(t.value for t in light.terms if t.label == "Utilisation")
    util_heavy = next(t.value for t in heavy.terms if t.label == "Utilisation")
    assert util_light < 1.0
    assert util_heavy > 1.0
    assert "PASS" in next(t.note for t in light.terms if t.label == "Utilisation")
    assert "FAIL" in next(t.note for t in heavy.terms if t.label == "Utilisation")
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)
    assert not any(f.category == "code_compliance" for f in light.risk_flags)


def test_governing_mode_reported_correctly():
    # Thin ply with low fu -> bearing should govern over shear.
    result = calculate(BoltedShearConnectionInput(**base_kwargs(connected_ply_thickness_mm=4.0, connected_ply_ultimate_strength_mpa=340.0)))
    governing = next(t for t in result.terms if t.label == "Governing resistance per bolt")
    assert "bearing" in governing.note


def test_pitch_required_when_multiple_bolts():
    with pytest.raises(ValidationError):
        BoltedShearConnectionInput(**base_kwargs(number_of_bolts=2))


def test_hole_diameter_must_exceed_bolt_diameter():
    with pytest.raises(ValidationError):
        BoltedShearConnectionInput(**base_kwargs(hole_diameter_mm=18.0))  # < bolt_diameter_mm (20)


def test_grade_10_9_uses_correct_fub():
    result = calculate(BoltedShearConnectionInput(**base_kwargs(bolt_grade="10.9")))
    fub = next(t.value for t in result.terms if t.label.startswith("fub"))
    assert fub == pytest.approx(1000.0)
