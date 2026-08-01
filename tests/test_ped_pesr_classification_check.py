"""
Tests for the PED/PESR classification check. This module deliberately does
NOT derive the PED category (see module docstring) -- these tests verify
the scope threshold and downstream conformity-assessment bookkeeping
against a fixed, directly-supplied category.
"""

import pytest

from calcs.mechanical_piping.ped_pesr_classification_check import (
    PED_SCOPE_THRESHOLD_BAR,
    PedPesrClassificationCheckInput,
    calculate,
)

BASE_KWARGS = dict(
    max_allowable_pressure_bar_g=16.0,
    nominal_diameter_dn=100.0,
    fluid_group=2,
    ped_category="II",
)


def test_below_scope_threshold_is_out_of_scope():
    result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, max_allowable_pressure_bar_g=0.3)))
    assert "OUTSIDE" in result.headline.note
    assert result.headline.value == 0.0
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_at_exactly_threshold_is_out_of_scope():
    # PED excludes equipment "not exceeding" 0.5 bar -- exactly at the threshold is still excluded.
    result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, max_allowable_pressure_bar_g=PED_SCOPE_THRESHOLD_BAR)))
    assert "OUTSIDE" in result.headline.note


def test_above_scope_threshold_is_in_scope():
    result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, max_allowable_pressure_bar_g=0.51)))
    assert "IN SCOPE" in result.headline.note
    assert result.headline.value == 1.0


def test_category_ii_requires_notified_body_and_raises_flag():
    result = calculate(PedPesrClassificationCheckInput(**BASE_KWARGS))
    requires = next(t.value for t in result.terms if t.label.startswith("Requires notified body"))
    assert requires == 1.0
    assert any(f.category == "code_compliance" and f.severity == "high" for f in result.risk_flags)


def test_category_sep_does_not_require_notified_body():
    result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, ped_category="SEP")))
    requires = next(t.value for t in result.terms if t.label.startswith("Requires notified body"))
    assert requires == 0.0
    assert not any(f.category == "code_compliance" for f in result.risk_flags)
    assert "SEP" in result.headline.note
    assert any("no notified body" in w for w in result.warnings)


def test_all_non_sep_categories_require_notified_body():
    for category in ("I", "II", "III"):
        result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, ped_category=category)))
        assert any(f.category == "code_compliance" for f in result.risk_flags), f"category {category} should flag"


def test_fluid_group_1_adds_a_warning():
    result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, fluid_group=1)))
    assert any("Group 1" in w for w in result.warnings)


def test_fluid_group_2_does_not_add_group_1_warning():
    result = calculate(PedPesrClassificationCheckInput(**dict(BASE_KWARGS, fluid_group=2)))
    assert not any("Group 1 (dangerous fluid) service" in w for w in result.warnings)


def test_scope_threshold_constant_is_half_a_bar():
    assert PED_SCOPE_THRESHOLD_BAR == pytest.approx(0.5)


def test_zero_or_negative_pressure_rejected_by_validation():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PedPesrClassificationCheckInput(**dict(BASE_KWARGS, max_allowable_pressure_bar_g=0.0))
