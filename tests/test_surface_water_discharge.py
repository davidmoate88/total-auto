"""
Tests for the surface water discharge rate check / orifice sizing module.

The orifice equation (Q = Cd*A*sqrt(2*g*h)) is a standard, well-established
hydraulics formula, checked here for arithmetic consistency with the
module's own documented formula (see the module docstring's caveat that
permitted_discharge_rate_l_s itself is a direct input, not derived).
"""

import math

import pytest

from calcs.civil.surface_water_discharge import (
    GRAVITY_M_S2,
    SHARP_EDGED_ORIFICE_CD,
    SurfaceWaterDischargeInput,
    calculate,
)


def base_kwargs(**overrides):
    kwargs = dict(
        permitted_discharge_rate_l_s=12.0,
        site_area_ha=2.5,
        design_head_m=1.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_rate_per_hectare_matches_hand_calculation():
    inputs = SurfaceWaterDischargeInput(**base_kwargs())
    result = calculate(inputs)
    rate_per_ha = next(t.value for t in result.terms if t.label.startswith("Discharge rate per hectare"))
    assert rate_per_ha == pytest.approx(12.0 / 2.5)


def test_orifice_diameter_matches_hand_calculation():
    inputs = SurfaceWaterDischargeInput(**base_kwargs())
    result = calculate(inputs)

    Q = 12.0 / 1000.0
    A_expected = Q / (SHARP_EDGED_ORIFICE_CD * math.sqrt(2 * GRAVITY_M_S2 * 1.0))
    diameter_expected_mm = math.sqrt(4 * A_expected / math.pi) * 1000.0

    A = next(t.value for t in result.terms if t.label.startswith("Required orifice area"))
    diameter = next(t.value for t in result.terms if t.label.startswith("Required orifice diameter"))
    assert A == pytest.approx(A_expected, rel=1e-9)
    assert diameter == pytest.approx(diameter_expected_mm, rel=1e-9)
    assert result.headline.value == pytest.approx(diameter_expected_mm, rel=1e-9)


def test_higher_head_reduces_required_orifice_diameter():
    shallow = calculate(SurfaceWaterDischargeInput(**base_kwargs(design_head_m=0.5)))
    deep = calculate(SurfaceWaterDischargeInput(**base_kwargs(design_head_m=2.0)))
    d_shallow = next(t.value for t in shallow.terms if t.label.startswith("Required orifice diameter"))
    d_deep = next(t.value for t in deep.terms if t.label.startswith("Required orifice diameter"))
    assert d_deep < d_shallow


def test_higher_rate_increases_required_orifice_diameter():
    low = calculate(SurfaceWaterDischargeInput(**base_kwargs(permitted_discharge_rate_l_s=5.0)))
    high = calculate(SurfaceWaterDischargeInput(**base_kwargs(permitted_discharge_rate_l_s=50.0)))
    d_low = next(t.value for t in low.terms if t.label.startswith("Required orifice diameter"))
    d_high = next(t.value for t in high.terms if t.label.startswith("Required orifice diameter"))
    assert d_high > d_low


def test_below_minimum_discharge_raises_code_compliance_flag():
    below = calculate(SurfaceWaterDischargeInput(**base_kwargs(permitted_discharge_rate_l_s=2.0)))
    above = calculate(SurfaceWaterDischargeInput(**base_kwargs(permitted_discharge_rate_l_s=12.0)))
    assert any(f.category == "code_compliance" and f.severity == "medium" for f in below.risk_flags)
    assert not any(f.category == "code_compliance" for f in above.risk_flags)
    assert any("practical minimum" in w for w in below.warnings)


def test_small_orifice_raises_buildability_flag_for_vortex_device():
    # Small rate + deep head -> small orifice diameter, below the practical minimum.
    small = calculate(SurfaceWaterDischargeInput(**base_kwargs(permitted_discharge_rate_l_s=5.0, design_head_m=3.0)))
    diameter = next(t.value for t in small.terms if t.label.startswith("Required orifice diameter"))
    assert diameter < 75.0
    assert any(f.category == "buildability" and f.severity == "medium" for f in small.risk_flags)
    assert any("Hydro-Brake" in w for w in small.warnings)


def test_large_orifice_raises_no_buildability_flag():
    large = calculate(SurfaceWaterDischargeInput(**base_kwargs(permitted_discharge_rate_l_s=50.0, design_head_m=0.5)))
    diameter = next(t.value for t in large.terms if t.label.startswith("Required orifice diameter"))
    assert diameter > 75.0
    assert not any(f.category == "buildability" for f in large.risk_flags)


def test_custom_discharge_coefficient_changes_result():
    default_cd = calculate(SurfaceWaterDischargeInput(**base_kwargs()))
    lower_cd = calculate(SurfaceWaterDischargeInput(**base_kwargs(discharge_coefficient=0.5)))
    d_default = next(t.value for t in default_cd.terms if t.label.startswith("Required orifice diameter"))
    d_lower = next(t.value for t in lower_cd.terms if t.label.startswith("Required orifice diameter"))
    # Lower Cd -> larger required area/diameter for the same target flow.
    assert d_lower > d_default
