"""
Tests for the EN 1993-1-1 steel beam member capacity module.

The classification limits (72/83/124*epsilon, 9/10/14*epsilon) and Table 3.1
yield strengths are commonly reproduced constants, checked here for arithmetic
consistency with the module's own documented formulae, not against an
independent authoritative source (see the module docstring's caveat).

The test section (h=200, b=100, tw=6, tf=10, r=8) is an IDEALISED I-section,
not a real catalogue section -- its A/Iy/Wel,y/Wpl,y are computed directly
from rectangular flange/web geometry (ignoring fillets) so the expected
values can be independently hand-derived and cross-checked here, the same
approach test_bearing_capacity.py uses for Nq/Nc at phi=30.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.structural.beam_capacity import (
    GAMMA_M0,
    STEEL_YOUNGS_MODULUS_MPA,
    BeamCapacityInput,
    _classify_section,
    _lookup_yield_strength_mpa,
    _shear_area_mm2,
    calculate,
)

# Idealised test section -- see module docstring above.
H, B, TW, TF, R = 200.0, 100.0, 6.0, 10.0, 8.0
A = 2 * B * TF + (H - 2 * TF) * TW  # 3080 mm^2
IY = (B * H**3 - (B - TW) * (H - 2 * TF) ** 3) / 12  # ~2.0983e7 mm^4
WEL_Y = IY / (H / 2)
WPL_Y = B * TF * (H - TF) + TW * (H - 2 * TF) ** 2 / 4  # 238,600 mm^3


def base_kwargs(**overrides):
    kwargs = dict(
        steel_grade="S275",
        section_depth_mm=H, section_width_mm=B,
        web_thickness_mm=TW, flange_thickness_mm=TF, root_radius_mm=R,
        area_mm2=A, second_moment_area_mm4=IY,
        elastic_modulus_mm3=WEL_Y, plastic_modulus_mm3=WPL_Y,
        span_m=4.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_section_properties_are_self_consistent():
    # Sanity check the test fixture itself before trusting it in other tests.
    assert A == pytest.approx(3080.0)
    assert WPL_Y == pytest.approx(238_600.0)
    assert WEL_Y == pytest.approx(209_826.67, rel=1e-4)


def test_yield_strength_lookup_matches_table_3_1_bands():
    assert _lookup_yield_strength_mpa("S275", 10.0) == pytest.approx(275.0)
    assert _lookup_yield_strength_mpa("S275", 16.0) == pytest.approx(275.0)
    assert _lookup_yield_strength_mpa("S275", 25.0) == pytest.approx(265.0)
    assert _lookup_yield_strength_mpa("S355", 40.0) == pytest.approx(345.0)


def test_yield_strength_override_bypasses_table_beyond_40mm():
    with pytest.raises(ValidationError):
        BeamCapacityInput(**base_kwargs(flange_thickness_mm=45.0, section_depth_mm=250.0))
    # Should succeed once an override is supplied.
    inputs = BeamCapacityInput(**base_kwargs(flange_thickness_mm=45.0, section_depth_mm=250.0, yield_strength_override_mpa=300.0))
    result = calculate(inputs)
    assert any(t.label == "fy (nominal yield strength)" and t.value == pytest.approx(300.0) for t in result.terms)


def test_classification_matches_hand_calculation_for_test_section():
    fy = 275.0
    epsilon = math.sqrt(235.0 / fy)
    inputs = BeamCapacityInput(**base_kwargs())
    section_class, web_class, flange_class, web_ratio, flange_ratio = _classify_section(inputs, epsilon)

    expected_web_ratio = (H - 2 * TF - 2 * R) / TW  # 164/6 = 27.33
    expected_flange_ratio = ((B - TW - 2 * R) / 2) / TF  # 39/10 = 3.9
    assert web_ratio == pytest.approx(expected_web_ratio)
    assert flange_ratio == pytest.approx(expected_flange_ratio)
    assert web_class == 1  # 27.3 << 72*0.9246
    assert flange_class == 1  # 3.9 << 9*0.9246
    assert section_class == 1


def test_bending_resistance_uses_plastic_modulus_for_class_1():
    inputs = BeamCapacityInput(**base_kwargs())
    result = calculate(inputs)
    fy = 275.0
    expected_Mc_Rd_kNm = WPL_Y * fy / GAMMA_M0 / 1e6
    mc_rd = next(t for t in result.terms if t.label.startswith("Mc,Rd"))
    assert mc_rd.value == pytest.approx(expected_Mc_Rd_kNm, rel=1e-9)
    assert "Wpl,y" in mc_rd.note


def test_shear_resistance_matches_hand_calculation():
    inputs = BeamCapacityInput(**base_kwargs())
    Av = _shear_area_mm2(inputs)
    hw = H - 2 * TF
    expected_Av = max(A - 2 * B * TF + (TW + 2 * R) * TF, 1.0 * hw * TW)
    assert Av == pytest.approx(expected_Av)
    assert Av == pytest.approx(1300.0)

    result = calculate(inputs)
    fy = 275.0
    expected_Vpl_Rd_kN = Av * (fy / math.sqrt(3)) / GAMMA_M0 / 1e3
    vpl_rd = next(t for t in result.terms if t.label.startswith("Vpl,Rd"))
    assert vpl_rd.value == pytest.approx(expected_Vpl_Rd_kN, rel=1e-9)


def test_no_loads_gives_resistance_only_headline():
    inputs = BeamCapacityInput(**base_kwargs())
    result = calculate(inputs)
    assert "Mc,Rd" in result.headline.label
    assert not any("utilisation" in t.label.lower() for t in result.terms)


def test_design_moment_and_shear_arithmetic():
    inputs = BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0))
    result = calculate(inputs)
    L = 4.0
    wEd = 1.35 * 2.0 + 1.5 * 3.0
    expected_MEd = wEd * L**2 / 8
    expected_VEd = wEd * L / 2
    MEd = next(t.value for t in result.terms if t.label.startswith("MEd"))
    VEd = next(t.value for t in result.terms if t.label.startswith("VEd"))
    assert MEd == pytest.approx(expected_MEd)
    assert VEd == pytest.approx(expected_VEd)


def test_point_load_adds_to_udl_effects():
    udl_only = calculate(BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0)))
    with_point = calculate(BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0, point_load_variable_kn=5.0)))
    MEd_udl = next(t.value for t in udl_only.terms if t.label.startswith("MEd"))
    MEd_point = next(t.value for t in with_point.terms if t.label.startswith("MEd"))
    L = 4.0
    PEd = 1.5 * 5.0
    assert MEd_point == pytest.approx(MEd_udl + PEd * L / 4)


def test_deflection_matches_superposition_formula():
    inputs = BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0, point_load_variable_kn=1.0))
    result = calculate(inputs)
    L_mm = 4.0 * 1000.0
    w_char = 5.0  # kN/m == N/mm
    P_char_N = 1.0 * 1000.0
    expected_delta = (
        5 * w_char * L_mm**4 / (384 * STEEL_YOUNGS_MODULUS_MPA * IY)
        + P_char_N * L_mm**3 / (48 * STEEL_YOUNGS_MODULUS_MPA * IY)
    )
    delta_term = next(t for t in result.terms if t.label.startswith("Deflection ("))
    assert delta_term.value == pytest.approx(expected_delta, rel=1e-9)


def test_deflection_limit_denominator_is_configurable():
    default = calculate(BeamCapacityInput(**base_kwargs(udl_variable_kn_m=1.0)))
    tighter = calculate(BeamCapacityInput(**base_kwargs(udl_variable_kn_m=1.0, deflection_limit_denominator=360.0)))
    util_default = next(t.value for t in default.terms if t.label == "Deflection utilisation")
    util_tighter = next(t.value for t in tighter.terms if t.label == "Deflection utilisation")
    assert util_tighter == pytest.approx(util_default * (360.0 / 200.0), rel=1e-9)


def test_utilisation_pass_and_fail():
    light = calculate(BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0)))
    heavy = calculate(BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=40.0, udl_variable_kn_m=40.0)))

    bending_light = next(t.value for t in light.terms if t.label == "Bending utilisation")
    bending_heavy = next(t.value for t in heavy.terms if t.label == "Bending utilisation")
    assert bending_light < 1.0
    assert bending_heavy > 1.0
    assert "PASS" in next(t.note for t in light.terms if t.label == "Bending utilisation")
    assert "FAIL" in next(t.note for t in heavy.terms if t.label == "Bending utilisation")
    assert any("FAILS" in w for w in heavy.warnings)
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)
    assert not any(f.category == "code_compliance" for f in light.risk_flags)


def test_governing_utilisation_is_max_of_the_three_checks():
    inputs = BeamCapacityInput(**base_kwargs(udl_permanent_kn_m=2.0, udl_variable_kn_m=3.0))
    result = calculate(inputs)
    bending = next(t.value for t in result.terms if t.label == "Bending utilisation")
    shear = next(t.value for t in result.terms if t.label == "Shear utilisation")
    deflection = next(t.value for t in result.terms if t.label == "Deflection utilisation")
    assert result.headline.value == pytest.approx(max(bending, shear, deflection))


def test_unrestrained_beam_raises_safety_risk_flag_and_warning():
    restrained = calculate(BeamCapacityInput(**base_kwargs()))
    unrestrained = calculate(BeamCapacityInput(**base_kwargs(continuously_restrained=False)))
    assert not any(f.category == "safety" for f in restrained.risk_flags)
    assert any(f.category == "safety" and f.severity == "high" for f in unrestrained.risk_flags)
    assert any("lateral-torsional buckling" in w.lower() for w in unrestrained.warnings)


def test_high_shear_utilisation_warns_about_interaction_not_checked():
    # Short, heavily point-loaded beam -> high shear utilisation relative to bending.
    inputs = BeamCapacityInput(**base_kwargs(span_m=1.0, point_load_variable_kn=150.0))
    result = calculate(inputs)
    shear_util = next(t.value for t in result.terms if t.label == "Shear utilisation")
    assert shear_util > 0.5
    assert any("SS6.2.8" in w for w in result.warnings)


def test_class_4_section_raises_critical_risk_flag():
    # Very thin, deep web -> pushes web classification to Class 4.
    inputs = BeamCapacityInput(**base_kwargs(
        section_depth_mm=600.0, web_thickness_mm=2.0, root_radius_mm=0.0,
        area_mm2=A, second_moment_area_mm4=IY, elastic_modulus_mm3=WEL_Y, plastic_modulus_mm3=WPL_Y,
    ))
    result = calculate(inputs)
    section_class_term = next(t for t in result.terms if t.label.startswith("Section class"))
    assert section_class_term.value == 4
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)
    assert any("Class 4" in w for w in result.warnings)


def test_flange_not_thinner_than_web_ratio_validation():
    with pytest.raises(ValidationError):
        BeamCapacityInput(**base_kwargs(flange_thickness_mm=250.0))  # >= half of depth (200)


def test_web_thickness_must_be_less_than_section_width():
    with pytest.raises(ValidationError):
        BeamCapacityInput(**base_kwargs(web_thickness_mm=150.0))  # >= section_width_mm (100)
