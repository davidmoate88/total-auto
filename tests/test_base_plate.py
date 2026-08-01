"""
Tests for the EN 1993-1-8 base plate bearing / HD bolt tension module.

Aeff and fjd are direct inputs (see the module docstring for why), so these
tests focus on the arithmetic the module DOES perform: bearing utilisation,
HD bolt tension resistance (a higher-confidence, standard Table 3.4 formula
shared in form with bolted_shear_connection.py), and combined ULS reporting.
"""

import pytest
from pydantic import ValidationError

from calcs.structural.base_plate import GAMMA_M2, BasePlateInput, calculate


def base_kwargs(**overrides):
    kwargs = dict(
        base_plate_effective_area_mm2=90_000.0,
        design_bearing_strength_mpa=11.3,
    )
    kwargs.update(overrides)
    return kwargs


def test_bearing_resistance_matches_hand_calculation():
    inputs = BasePlateInput(**base_kwargs())
    result = calculate(inputs)
    expected_Nj_Rd = 11.3 * 90_000.0 / 1e3
    Nj_Rd = next(t.value for t in result.terms if t.label.startswith("Nj,Rd"))
    assert Nj_Rd == pytest.approx(expected_Nj_Rd, rel=1e-9)


def test_no_loads_gives_resistance_only_headline():
    inputs = BasePlateInput(**base_kwargs())
    result = calculate(inputs)
    assert "Nj,Rd" in result.headline.label
    assert not any("utilisation" in t.label.lower() for t in result.terms)


def test_bearing_utilisation_pass_and_fail():
    light = calculate(BasePlateInput(**base_kwargs(axial_permanent_load_kn=50.0, axial_variable_load_kn=20.0)))
    heavy = calculate(BasePlateInput(**base_kwargs(axial_permanent_load_kn=500.0, axial_variable_load_kn=400.0)))
    util_light = next(t.value for t in light.terms if t.label == "Bearing utilisation")
    util_heavy = next(t.value for t in heavy.terms if t.label == "Bearing utilisation")
    assert util_light < 1.0
    assert util_heavy > 1.0
    assert "PASS" in next(t.note for t in light.terms if t.label == "Bearing utilisation")
    assert "FAIL" in next(t.note for t in heavy.terms if t.label == "Bearing utilisation")
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)
    assert not any(f.category == "code_compliance" for f in light.risk_flags)


def test_hd_bolt_tension_resistance_matches_hand_calculation():
    inputs = BasePlateInput(**base_kwargs(uplift_variable_kn=15.0, hd_bolt_tensile_stress_area_mm2=245.0))
    result = calculate(inputs)
    expected_Ft_Rd = 0.9 * 400.0 * 245.0 / GAMMA_M2 / 1e3
    Ft_Rd = next(t.value for t in result.terms if t.label.startswith("Ft,Rd"))
    assert Ft_Rd == pytest.approx(expected_Ft_Rd, rel=1e-9)


def test_hd_bolt_group_resistance_scales_with_bolt_count():
    four_bolts = calculate(BasePlateInput(**base_kwargs(uplift_variable_kn=15.0, hd_bolt_tensile_stress_area_mm2=245.0, number_of_hd_bolts=4)))
    two_bolts = calculate(BasePlateInput(**base_kwargs(uplift_variable_kn=15.0, hd_bolt_tensile_stress_area_mm2=245.0, number_of_hd_bolts=2)))
    group_four = next(t.value for t in four_bolts.terms if t.label == "HD bolt group tension resistance")
    group_two = next(t.value for t in two_bolts.terms if t.label == "HD bolt group tension resistance")
    assert group_four == pytest.approx(2 * group_two)


def test_hd_bolt_tensile_area_required_when_uplift_supplied():
    with pytest.raises(ValidationError):
        BasePlateInput(**base_kwargs(uplift_variable_kn=15.0))


def test_no_uplift_skips_hd_bolt_check():
    inputs = BasePlateInput(**base_kwargs(axial_permanent_load_kn=50.0, axial_variable_load_kn=20.0))
    result = calculate(inputs)
    assert not any("HD bolt" in t.label for t in result.terms)


def test_tension_utilisation_pass_and_fail():
    light = calculate(BasePlateInput(**base_kwargs(uplift_variable_kn=15.0, hd_bolt_tensile_stress_area_mm2=245.0)))
    heavy = calculate(BasePlateInput(**base_kwargs(uplift_variable_kn=300.0, hd_bolt_tensile_stress_area_mm2=245.0)))
    util_light = next(t.value for t in light.terms if t.label == "HD bolt tension utilisation")
    util_heavy = next(t.value for t in heavy.terms if t.label == "HD bolt tension utilisation")
    assert util_light < 1.0
    assert util_heavy > 1.0
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)


def test_governing_utilisation_is_max_of_bearing_and_tension():
    inputs = BasePlateInput(**base_kwargs(
        axial_permanent_load_kn=50.0, axial_variable_load_kn=20.0,
        uplift_variable_kn=15.0, hd_bolt_tensile_stress_area_mm2=245.0,
    ))
    result = calculate(inputs)
    bearing = next(t.value for t in result.terms if t.label == "Bearing utilisation")
    tension = next(t.value for t in result.terms if t.label == "HD bolt tension utilisation")
    assert result.headline.value == pytest.approx(max(bearing, tension))


def test_grade_8_8_hd_bolts_use_correct_fub():
    result = calculate(BasePlateInput(**base_kwargs(uplift_variable_kn=15.0, hd_bolt_tensile_stress_area_mm2=245.0, hd_bolt_grade="8.8")))
    fub = next(t.value for t in result.terms if t.label.startswith("fub"))
    assert fub == pytest.approx(800.0)
