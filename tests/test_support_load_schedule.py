"""
Tests for the pipe support load schedule. Aggregation (totals, governing
support) and the optional allowable-reaction screening check are verified
directly against a hand calculation.
"""

import pytest
from pydantic import ValidationError

from calcs.mechanical_piping.support_load_schedule import (
    Support,
    SupportLoadScheduleInput,
    _parse_supports,
    calculate,
)

SAMPLE_SUPPORTS = (
    "S1, 12.5, 3.2\n"
    "S2, 18.0, 5.5\n"
    "S3, 9.8, 2.1\n"
)


def test_parser_extracts_all_valid_lines():
    supports, unparsed = _parse_supports(SAMPLE_SUPPORTS)
    assert len(supports) == 3
    assert unparsed == []
    assert supports[0].support_id == "S1"
    assert supports[0].sustained_vertical_kn == pytest.approx(12.5)


def test_parser_reports_unparseable_lines():
    text = SAMPLE_SUPPORTS + "garbage\nS4, -5, 2.0\n"
    supports, unparsed = _parse_supports(text)
    assert len(supports) == 3
    assert len(unparsed) == 2


def test_total_and_governing_reactions_match_hand_calculation():
    result = calculate(SupportLoadScheduleInput(supports_text=SAMPLE_SUPPORTS))
    total = next(t.value for t in result.terms if t.label.startswith("Total sustained"))
    governing_v = next(t.value for t in result.terms if t.label.startswith("Governing vertical"))
    governing_h = next(t.value for t in result.terms if t.label.startswith("Governing horizontal"))
    assert total == pytest.approx(12.5 + 18.0 + 9.8, rel=1e-9)
    assert governing_v == pytest.approx(18.0)
    assert governing_h == pytest.approx(5.5)
    assert "S2" in next(t.note for t in result.terms if t.label.startswith("Governing vertical"))


def test_number_of_supports_matches_parsed_count():
    result = calculate(SupportLoadScheduleInput(supports_text=SAMPLE_SUPPORTS))
    n = next(t.value for t in result.terms if t.label == "Number of supports")
    assert n == 3.0


def test_no_allowable_limit_reports_governing_reaction_as_headline():
    result = calculate(SupportLoadScheduleInput(supports_text=SAMPLE_SUPPORTS))
    assert result.headline.label == "Governing vertical reaction"
    assert result.headline.value == pytest.approx(18.0)
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_allowable_limit_passes_and_matches_hand_calculation():
    result = calculate(SupportLoadScheduleInput(supports_text=SAMPLE_SUPPORTS, max_allowable_vertical_reaction_kn=20.0))
    assert result.headline.value == pytest.approx(18.0 / 20.0, rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_allowable_limit_below_governing_fails():
    result = calculate(SupportLoadScheduleInput(supports_text=SAMPLE_SUPPORTS, max_allowable_vertical_reaction_kn=15.0))
    assert result.headline.value == pytest.approx(18.0 / 15.0, rel=1e-9)
    assert "FAIL" in result.headline.note
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in result.risk_flags)


def test_no_valid_supports_returns_zero_with_warning():
    result = calculate(SupportLoadScheduleInput(supports_text="garbage\nmore garbage"))
    assert result.headline.value == pytest.approx(0.0)
    assert any("No valid supports parsed" in w for w in result.warnings)


def test_blank_supports_text_rejected():
    with pytest.raises(ValidationError):
        SupportLoadScheduleInput(supports_text="   ")


def test_negative_sustained_load_rejected_by_support_model():
    with pytest.raises(ValidationError):
        Support(support_id="S1", sustained_vertical_kn=-5.0, occasional_horizontal_kn=1.0)
