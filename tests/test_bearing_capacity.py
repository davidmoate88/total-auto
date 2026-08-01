"""
Tests for the Meyerhof bearing capacity module.

The bearing capacity factor assertions (Nc, Nq, Ngamma at phi=0 and phi=30) are
checked against standard tabulated values found in any geotechnical engineering
reference (e.g. Das, "Principles of Foundation Engineering") — these are
well-established closed-form results, not fitted/approximate numbers.
"""

import math

import pytest
from pydantic import ValidationError

from calcs.geotechnical.bearing_capacity import (
    BearingCapacityInput,
    _bearing_capacity_factors,
    calculate,
)


def test_bearing_factors_phi_zero():
    Nc, Nq, Ngamma = _bearing_capacity_factors(0)
    assert Nc == pytest.approx(5.14, rel=1e-6)
    assert Nq == pytest.approx(1.0, rel=1e-6)
    assert Ngamma == pytest.approx(0.0, abs=1e-9)


def test_bearing_factors_phi_30():
    # Standard tabulated values at phi = 30 degrees (Meyerhof Ngamma).
    Nc, Nq, Ngamma = _bearing_capacity_factors(30)
    assert Nq == pytest.approx(18.40, rel=1e-3)
    assert Nc == pytest.approx(30.14, rel=1e-3)
    assert Ngamma == pytest.approx(15.67, rel=1e-3)


def test_bearing_factors_phi_20():
    # Second reference point away from the two special cases above.
    Nc, Nq, Ngamma = _bearing_capacity_factors(20)
    assert Nq == pytest.approx(6.40, rel=1e-2)
    assert Nc == pytest.approx(14.83, rel=1e-2)
    assert Ngamma == pytest.approx(2.87, rel=2e-2)


def test_length_must_be_greater_or_equal_width():
    with pytest.raises(ValidationError):
        BearingCapacityInput(
            cohesion_kpa=0,
            friction_angle_deg=30,
            unit_weight_kn_m3=18,
            width_m=2.0,
            length_m=1.0,  # invalid: L < B
            depth_m=1.0,
        )


def test_square_footing_end_to_end_sane_output():
    inputs = BearingCapacityInput(
        cohesion_kpa=0,
        friction_angle_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        depth_m=1.0,
        factor_of_safety=3.0,
    )
    result = calculate(inputs)

    # Gross ultimate bearing capacity must exceed the overburden alone —
    # otherwise the soil would offer no net capacity at all.
    q = 18 * 1.0
    qu = next(t.value for t in result.terms if t.label == "qu (gross ultimate)")
    assert qu > q

    # Allowable pressure must be positive and less than the ultimate value.
    assert 0 < result.headline.value < qu

    # A dry-condition and ULS-only warning should always be present.
    assert any("groundwater" in w for w in result.warnings)
    assert any("settlement" in w for w in result.warnings)


def test_cohesive_soil_phi_zero_undrained():
    # Purely cohesive (undrained) case: phi = 0, so Nq=1, Ngamma=0 and the
    # gamma term must vanish entirely regardless of unit weight or footing size.
    inputs = BearingCapacityInput(
        cohesion_kpa=50,
        friction_angle_deg=0,
        unit_weight_kn_m3=19,
        width_m=2.0,
        length_m=2.0,
        depth_m=1.5,
        factor_of_safety=3.0,
    )
    result = calculate(inputs)
    gamma_term = next(t.value for t in result.terms if t.label == "gamma term")
    assert gamma_term == pytest.approx(0.0, abs=1e-9)


def test_depth_factor_increases_with_depth():
    """Deeper founding depth should increase capacity, all else equal."""
    base = dict(
        cohesion_kpa=0,
        friction_angle_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        factor_of_safety=3.0,
    )
    shallow = calculate(BearingCapacityInput(**base, depth_m=0.5))
    deep = calculate(BearingCapacityInput(**base, depth_m=2.0))
    assert deep.headline.value > shallow.headline.value
