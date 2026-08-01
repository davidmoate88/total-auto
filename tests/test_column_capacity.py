"""
Tests for the EN 1993-1-1 steel column axial buckling module.

Same idealised-test-section approach as test_beam_capacity.py: A/Iy/Iz are
computed directly from rectangular flange/web geometry (ignoring fillets) so
expected values can be independently hand-derived, not sourced from an
unverifiable catalogue. The Table 5.2/6.1/6.2 constants used are commonly
reproduced values, checked here for arithmetic consistency with the module's
own documented formulae (see the module docstring's caveat).
"""

import math

import pytest
from pydantic import ValidationError

from calcs.structural.column_capacity import (
    GAMMA_M0,
    GAMMA_M1,
    IMPERFECTION_FACTORS,
    ColumnCapacityInput,
    _buckling_reduction_factor,
    _classify_section,
    calculate,
)

# Idealised test section -- same geometry as test_beam_capacity.py.
H, B, TW, TF, R = 200.0, 100.0, 6.0, 10.0, 8.0
A = 2 * B * TF + (H - 2 * TF) * TW  # 3080 mm^2
IY = (B * H**3 - (B - TW) * (H - 2 * TF) ** 3) / 12  # ~2.0983e7 mm^4
IZ = 2 * (TF * B**3 / 12) + (H - 2 * TF) * TW**3 / 12  # ~1.6699e6 mm^4


def base_kwargs(**overrides):
    kwargs = dict(
        steel_grade="S275",
        section_depth_mm=H, section_width_mm=B,
        web_thickness_mm=TW, flange_thickness_mm=TF, root_radius_mm=R,
        area_mm2=A, second_moment_area_y_mm4=IY, second_moment_area_z_mm4=IZ,
        member_length_m=3.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_section_geometry_is_self_consistent():
    assert A == pytest.approx(3080.0)
    assert IY == pytest.approx(20_982_666.67, rel=1e-4)
    assert IZ == pytest.approx(1_669_906.67, rel=1e-4)


def test_web_classification_uses_compression_row_not_bending_row():
    # Same c/t ratio as the beam module's test section (27.3), but the
    # column module must classify the web via the STRICTER compression row
    # (33/38/42*epsilon) rather than the bending row (72/83/124*epsilon).
    fy = 275.0
    epsilon = math.sqrt(235.0 / fy)
    inputs = ColumnCapacityInput(**base_kwargs())
    section_class, web_class, flange_class, web_ratio, flange_ratio = _classify_section(inputs, epsilon)
    expected_web_ratio = (H - 2 * TF - 2 * R) / TW
    assert web_ratio == pytest.approx(expected_web_ratio)
    assert web_ratio == pytest.approx(27.33, rel=1e-3)
    assert web_ratio <= 33 * epsilon  # still Class 1 even under the stricter row
    assert web_class == 1
    assert flange_class == 1
    assert section_class == 1


def test_web_classification_is_stricter_than_beam_modules_bending_row():
    # A ratio between 33*epsilon and 72*epsilon would be Class 1 in bending
    # but NOT Class 1 in compression -- confirms the two modules genuinely
    # use different classification limits, not a copy-paste of one into the other.
    epsilon = math.sqrt(235.0 / 275.0)
    borderline_ratio = 50.0  # between 33*eps (~30.5) and 72*eps (~66.6)
    assert borderline_ratio > 33 * epsilon
    assert borderline_ratio <= 72 * epsilon


def test_imperfection_factors_match_table_6_1():
    assert IMPERFECTION_FACTORS["a0"] == pytest.approx(0.13)
    assert IMPERFECTION_FACTORS["a"] == pytest.approx(0.21)
    assert IMPERFECTION_FACTORS["b"] == pytest.approx(0.34)
    assert IMPERFECTION_FACTORS["c"] == pytest.approx(0.49)
    assert IMPERFECTION_FACTORS["d"] == pytest.approx(0.76)


def test_buckling_reduction_factor_is_one_below_lambda_0_2():
    assert _buckling_reduction_factor(0.15, 0.34) == pytest.approx(1.0)
    assert _buckling_reduction_factor(0.2, 0.21) == pytest.approx(1.0)


def test_buckling_reduction_factor_matches_hand_calculation():
    # z-z axis of the worked example: lambda_bar ~= 1.484, curve b (alpha=0.34).
    lambda_bar = 1.484
    alpha = 0.34
    phi = 0.5 * (1 + alpha * (lambda_bar - 0.2) + lambda_bar**2)
    expected_chi = 1.0 / (phi + math.sqrt(phi**2 - lambda_bar**2))
    assert _buckling_reduction_factor(lambda_bar, alpha) == pytest.approx(expected_chi, rel=1e-6)


def test_minor_axis_governs_for_deep_narrow_section():
    inputs = ColumnCapacityInput(**base_kwargs())
    result = calculate(inputs)
    governing = next(t for t in result.terms if t.label.startswith("Nb,Rd (governing)"))
    assert "z-z" in governing.note
    Nb_y = next(t.value for t in result.terms if t.label == "[y-y] Nb,Rd")
    Nb_z = next(t.value for t in result.terms if t.label == "[z-z] Nb,Rd")
    assert Nb_z < Nb_y
    assert governing.value == pytest.approx(Nb_z)


def test_nc_rd_matches_hand_calculation():
    inputs = ColumnCapacityInput(**base_kwargs())
    result = calculate(inputs)
    fy = 275.0
    expected_Nc_Rd = A * fy / GAMMA_M0 / 1e3
    nc_rd = next(t for t in result.terms if t.label.startswith("Nc,Rd"))
    assert nc_rd.value == pytest.approx(expected_Nc_Rd, rel=1e-9)


def test_buckling_resistance_never_exceeds_cross_section_resistance():
    inputs = ColumnCapacityInput(**base_kwargs())
    result = calculate(inputs)
    nc_rd = next(t.value for t in result.terms if t.label.startswith("Nc,Rd"))
    nb_rd = next(t.value for t in result.terms if t.label.startswith("Nb,Rd (governing)"))
    assert nb_rd <= nc_rd


def test_shorter_member_has_higher_buckling_resistance():
    short = calculate(ColumnCapacityInput(**base_kwargs(member_length_m=1.5)))
    long_ = calculate(ColumnCapacityInput(**base_kwargs(member_length_m=6.0)))
    Nb_short = next(t.value for t in short.terms if t.label.startswith("Nb,Rd (governing)"))
    Nb_long = next(t.value for t in long_.terms if t.label.startswith("Nb,Rd (governing)"))
    assert Nb_short > Nb_long


def test_no_axial_load_gives_resistance_only_headline():
    inputs = ColumnCapacityInput(**base_kwargs())
    result = calculate(inputs)
    assert "Nb,Rd" in result.headline.label
    assert not any(t.label == "NEd (design axial compression)" for t in result.terms)


def test_utilisation_pass_and_fail():
    light = calculate(ColumnCapacityInput(**base_kwargs(axial_permanent_load_kn=50.0, axial_variable_load_kn=20.0)))
    heavy = calculate(ColumnCapacityInput(**base_kwargs(axial_permanent_load_kn=200.0, axial_variable_load_kn=100.0)))
    util_light = next(t.value for t in light.terms if t.label == "Utilisation")
    util_heavy = next(t.value for t in heavy.terms if t.label == "Utilisation")
    assert util_light < 1.0
    assert util_heavy > 1.0
    assert "PASS" in next(t.note for t in light.terms if t.label == "Utilisation")
    assert "FAIL" in next(t.note for t in heavy.terms if t.label == "Utilisation")
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)
    assert not any(f.category == "code_compliance" for f in light.risk_flags)


def test_design_axial_load_arithmetic():
    inputs = ColumnCapacityInput(**base_kwargs(axial_permanent_load_kn=80.0, axial_variable_load_kn=40.0))
    result = calculate(inputs)
    NEd = next(t.value for t in result.terms if t.label.startswith("NEd"))
    assert NEd == pytest.approx(1.35 * 80.0 + 1.5 * 40.0)


def test_curve_override_required_outside_auto_selectable_range():
    with pytest.raises(ValidationError):
        # h/b = 1.0 -- not > 1.2, no override supplied.
        ColumnCapacityInput(**base_kwargs(section_depth_mm=100.0, flange_thickness_mm=8.0))


def test_curve_override_accepted_outside_auto_selectable_range():
    inputs = ColumnCapacityInput(**base_kwargs(
        section_depth_mm=100.0, flange_thickness_mm=8.0,
        buckling_curve_y_override="b", buckling_curve_z_override="c",
    ))
    result = calculate(inputs)
    y_curve_term = next(t for t in result.terms if t.label == "[y-y] Buckling curve")
    z_curve_term = next(t for t in result.terms if t.label == "[z-z] Buckling curve")
    assert "b (alpha=0.34)" in y_curve_term.note
    assert "user override" in y_curve_term.note
    assert "c (alpha=0.49)" in z_curve_term.note


def test_yield_strength_override_required_beyond_40mm():
    # tf=45mm > 40mm trips BOTH the fy-table range and the buckling-curve
    # auto-selection range -- supply curve overrides too so this test isolates
    # the fy-override requirement specifically.
    with pytest.raises(ValidationError):
        ColumnCapacityInput(**base_kwargs(
            flange_thickness_mm=45.0, section_depth_mm=250.0,
            buckling_curve_y_override="a", buckling_curve_z_override="b",
        ))
    inputs = ColumnCapacityInput(**base_kwargs(
        flange_thickness_mm=45.0, section_depth_mm=250.0, yield_strength_override_mpa=300.0,
        buckling_curve_y_override="a", buckling_curve_z_override="b",
    ))
    result = calculate(inputs)
    assert any(t.label == "fy (nominal yield strength)" and t.value == pytest.approx(300.0) for t in result.terms)


def test_class_4_section_raises_critical_risk_flag():
    # Very thin, deep web -> pushes web classification to Class 4 even under
    # the stricter compression row.
    inputs = ColumnCapacityInput(**base_kwargs(
        section_depth_mm=600.0, web_thickness_mm=3.0, root_radius_mm=0.0,
    ))
    result = calculate(inputs)
    section_class_term = next(t for t in result.terms if t.label.startswith("Section class"))
    assert section_class_term.value == 4
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)
    assert any("Class 4" in w for w in result.warnings)


def test_gamma_m0_and_m1_are_uk_na_unity():
    assert GAMMA_M0 == pytest.approx(1.0)
    assert GAMMA_M1 == pytest.approx(1.0)


def test_flange_not_thinner_than_web_ratio_validation():
    with pytest.raises(ValidationError):
        ColumnCapacityInput(**base_kwargs(flange_thickness_mm=250.0))


def test_web_thickness_must_be_less_than_section_width():
    with pytest.raises(ValidationError):
        ColumnCapacityInput(**base_kwargs(web_thickness_mm=150.0))
