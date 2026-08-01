"""
Tests for the cut/fill earthwork volume balance module.

The grid method's arithmetic (depth*area summation) is basic solid geometry,
checked here by hand-deriving expected volumes for a small, fully-worked
grid, the same "derive independently" approach used throughout this repo.
"""

import pytest
from pydantic import ValidationError

from calcs.civil.cut_fill_balance import CutFillBalanceInput, _parse_grid_points, calculate

SAMPLE_GRID = (
    "12.50, 11.00, 100\n"
    "12.20, 11.00, 100\n"
    "11.80, 11.00, 100\n"
    "11.40, 11.20, 100\n"
    "11.00, 11.40, 100\n"
    "10.80, 11.50, 100\n"
)


def test_parser_extracts_all_valid_lines():
    points, unparsed = _parse_grid_points(SAMPLE_GRID)
    assert len(points) == 6
    assert unparsed == []


def test_parser_reports_unparseable_lines_without_dropping_valid_ones():
    text = SAMPLE_GRID + "not a valid line\n12.0, 11.0\n12.0, 11.0, -5\n"
    points, unparsed = _parse_grid_points(text)
    assert len(points) == 6
    assert len(unparsed) == 3


def test_parser_skips_blank_lines():
    points, unparsed = _parse_grid_points("\n\n12.0, 11.0, 50\n\n")
    assert len(points) == 1
    assert unparsed == []


def test_cut_and_fill_volumes_match_hand_calculation():
    inputs = CutFillBalanceInput(grid_points_text=SAMPLE_GRID)
    result = calculate(inputs)
    cut = next(t.value for t in result.terms if t.label.startswith("Cut volume (in-situ)"))
    fill = next(t.value for t in result.terms if t.label.startswith("Fill volume"))
    assert cut == pytest.approx(150 + 120 + 80 + 20)
    assert fill == pytest.approx(40 + 70)


def test_net_balance_and_imbalance_percentage():
    inputs = CutFillBalanceInput(grid_points_text=SAMPLE_GRID)
    result = calculate(inputs)
    net = next(t.value for t in result.terms if t.label == "Net balance")
    imbalance = next(t.value for t in result.terms if t.label == "Imbalance")
    assert net == pytest.approx(370 - 110)
    assert imbalance == pytest.approx(260 / 480 * 100, rel=1e-6)
    assert result.headline.value == pytest.approx(net)
    assert "surplus" in result.headline.note


def test_conversion_factor_only_scales_cut_volume():
    baseline = calculate(CutFillBalanceInput(grid_points_text=SAMPLE_GRID, cut_to_fill_conversion_factor=1.0))
    scaled = calculate(CutFillBalanceInput(grid_points_text=SAMPLE_GRID, cut_to_fill_conversion_factor=0.9))
    cut_baseline = next(t.value for t in baseline.terms if t.label.startswith("Cut volume (compacted"))
    cut_scaled = next(t.value for t in scaled.terms if t.label.startswith("Cut volume (compacted"))
    fill_baseline = next(t.value for t in baseline.terms if t.label.startswith("Fill volume"))
    fill_scaled = next(t.value for t in scaled.terms if t.label.startswith("Fill volume"))
    assert cut_scaled == pytest.approx(cut_baseline * 0.9)
    assert fill_scaled == pytest.approx(fill_baseline)


def test_exactly_balanced_grid_gives_zero_net_and_zero_imbalance():
    text = "12.0, 11.0, 100\n10.0, 11.0, 100\n"  # cut 100 m^3, fill 100 m^3
    result = calculate(CutFillBalanceInput(grid_points_text=text))
    net = next(t.value for t in result.terms if t.label == "Net balance")
    imbalance = next(t.value for t in result.terms if t.label == "Imbalance")
    assert net == pytest.approx(0.0)
    assert imbalance == pytest.approx(0.0)
    assert "balanced" in result.headline.note


def test_large_imbalance_raises_buildability_risk_flag_not_code_compliance():
    result = calculate(CutFillBalanceInput(grid_points_text=SAMPLE_GRID))
    assert any(f.category == "buildability" and f.severity == "medium" for f in result.risk_flags)
    assert not any(f.category == "code_compliance" for f in result.risk_flags)


def test_small_imbalance_below_threshold_raises_no_flag():
    text = "12.0, 11.0, 100\n10.0, 11.0, 105\n"  # cut 100, fill 105 -> ~2.4% imbalance
    result = calculate(CutFillBalanceInput(grid_points_text=text, large_imbalance_threshold_pct=10.0))
    assert not any(f.category == "buildability" for f in result.risk_flags)


def test_all_unparseable_lines_returns_zero_result_with_warning():
    result = calculate(CutFillBalanceInput(grid_points_text="garbage line\nanother bad one"))
    assert result.headline.value == pytest.approx(0.0)
    assert any("No valid grid points parsed" in w for w in result.warnings)


def test_blank_grid_points_text_rejected():
    with pytest.raises(ValidationError):
        CutFillBalanceInput(grid_points_text="   ")


def test_balanced_points_counted_correctly():
    text = SAMPLE_GRID + "11.0, 11.0, 50\n"  # exactly balanced point
    points, _ = _parse_grid_points(text)
    result = calculate(CutFillBalanceInput(grid_points_text=text))
    count_term = next(t for t in result.terms if t.label == "Grid points parsed")
    assert count_term.value == len(points)
    assert "1 balanced" in count_term.note
