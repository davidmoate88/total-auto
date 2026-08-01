"""
Tests for the deck/grating bearing bar loading and deflection module.

The test bearing bar (5mm x 30mm rectangular flat bar) is an idealised
section, not a real catalogue grating -- its Wel/I are computed directly
from rectangular-section formulae so expected values can be independently
hand-derived, the same approach used in test_beam_capacity.py.
"""

import pytest
from pydantic import ValidationError

from calcs.structural.deck_grating import (
    STEEL_YOUNGS_MODULUS_MPA,
    DeckGratingInput,
    calculate,
)

# Idealised 5mm x 30mm rectangular bearing bar.
T, D = 5.0, 30.0
WEL = T * D**2 / 6  # 750 mm^3
I = T * D**3 / 12  # 11250 mm^4


def base_kwargs(**overrides):
    kwargs = dict(
        steel_grade="S275",
        bar_thickness_mm=T,
        bar_spacing_mm=40.0,
        span_m=0.5,
        bar_elastic_modulus_mm3=WEL,
        bar_second_moment_area_mm4=I,
        point_load_bars_engaged=2,
    )
    kwargs.update(overrides)
    return kwargs


def test_bar_section_properties_are_self_consistent():
    assert WEL == pytest.approx(750.0)
    assert I == pytest.approx(11250.0)


def test_tributary_udl_per_bar_matches_spacing_conversion():
    inputs = DeckGratingInput(**base_kwargs(udl_variable_kn_m2=5.0))
    result = calculate(inputs)
    w_per_bar = next(t.value for t in result.terms if t.label.startswith("w per bar"))
    assert w_per_bar == pytest.approx(5.0 * 40.0 / 1000.0)


def test_point_load_split_across_engaged_bars():
    one_bar = calculate(DeckGratingInput(**base_kwargs(point_load_bars_engaged=1)))
    two_bars = calculate(DeckGratingInput(**base_kwargs(point_load_bars_engaged=2)))
    p_one = next(t.value for t in one_bar.terms if t.label.startswith("P per bar"))
    p_two = next(t.value for t in two_bars.terms if t.label.startswith("P per bar"))
    assert p_two == pytest.approx(p_one / 2)


def test_bending_moment_and_stress_match_hand_calculation():
    inputs = DeckGratingInput(**base_kwargs())
    result = calculate(inputs)
    wEd = 1.5 * 5.0 * 40.0 / 1000.0
    PEd = 1.5 * 1.5 / 2
    expected_MEd = wEd * 0.5**2 / 8 + PEd * 0.5 / 4
    expected_sigma = expected_MEd * 1e6 / WEL
    MEd = next(t.value for t in result.terms if t.label.startswith("MEd"))
    sigma = next(t.value for t in result.terms if t.label.startswith("sigma_Ed"))
    assert MEd == pytest.approx(expected_MEd, rel=1e-9)
    assert sigma == pytest.approx(expected_sigma, rel=1e-9)


def test_deflection_matches_superposition_formula():
    inputs = DeckGratingInput(**base_kwargs())
    result = calculate(inputs)
    w_char = 5.0 * 40.0 / 1000.0
    P_char_N = (1.5 / 2) * 1000.0
    L_mm = 500.0
    expected_delta = (
        5 * w_char * L_mm**4 / (384 * STEEL_YOUNGS_MODULUS_MPA * I)
        + P_char_N * L_mm**3 / (48 * STEEL_YOUNGS_MODULUS_MPA * I)
    )
    delta = next(t.value for t in result.terms if t.label.startswith("Deflection ("))
    assert delta == pytest.approx(expected_delta, rel=1e-9)


def test_no_loads_gives_resistance_only_headline():
    inputs = DeckGratingInput(**base_kwargs(udl_variable_kn_m2=0.0, point_load_variable_kn=0.0))
    result = calculate(inputs)
    assert "Allowable elastic stress" in result.headline.label
    assert not any("utilisation" in t.label.lower() for t in result.terms)


def test_default_loads_match_bod_criteria():
    inputs = DeckGratingInput(**base_kwargs())
    assert inputs.udl_variable_kn_m2 == pytest.approx(5.0)
    assert inputs.point_load_variable_kn == pytest.approx(1.5)


def test_utilisation_pass_and_fail():
    light = calculate(DeckGratingInput(**base_kwargs(span_m=0.5, point_load_bars_engaged=2)))
    heavy = calculate(DeckGratingInput(**base_kwargs(span_m=1.0, point_load_bars_engaged=1)))
    bending_light = next(t.value for t in light.terms if t.label == "Bending utilisation")
    bending_heavy = next(t.value for t in heavy.terms if t.label == "Bending utilisation")
    assert bending_light < 1.0
    assert bending_heavy > 1.0
    assert "PASS" in next(t.note for t in light.terms if t.label == "Bending utilisation")
    assert "FAIL" in next(t.note for t in heavy.terms if t.label == "Bending utilisation")
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)
    assert not any(f.category == "code_compliance" for f in light.risk_flags)


def test_governing_utilisation_is_max_of_bending_and_deflection():
    inputs = DeckGratingInput(**base_kwargs())
    result = calculate(inputs)
    bending = next(t.value for t in result.terms if t.label == "Bending utilisation")
    deflection = next(t.value for t in result.terms if t.label == "Deflection utilisation")
    assert result.headline.value == pytest.approx(max(bending, deflection))


def test_yield_strength_override_required_beyond_40mm():
    with pytest.raises(ValidationError):
        DeckGratingInput(**base_kwargs(bar_thickness_mm=45.0))
    inputs = DeckGratingInput(**base_kwargs(bar_thickness_mm=45.0, yield_strength_override_mpa=300.0))
    result = calculate(inputs)
    assert any(t.label == "fy (nominal yield strength)" and t.value == pytest.approx(300.0) for t in result.terms)


def test_wider_bar_spacing_increases_tributary_load_and_utilisation():
    narrow = calculate(DeckGratingInput(**base_kwargs(bar_spacing_mm=20.0)))
    wide = calculate(DeckGratingInput(**base_kwargs(bar_spacing_mm=60.0)))
    bending_narrow = next(t.value for t in narrow.terms if t.label == "Bending utilisation")
    bending_wide = next(t.value for t in wide.terms if t.label == "Bending utilisation")
    assert bending_wide > bending_narrow
