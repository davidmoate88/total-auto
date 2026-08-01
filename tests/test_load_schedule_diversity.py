"""
Tests for the LV load schedule / diversity module. The P/Q aggregation is
hand-verified here against an independently derived 4-load example (the
same "derive independently" approach used throughout this repo), not just
checked for "it ran without erroring".
"""

import math

import pytest
from pydantic import ValidationError

from calcs.electrical_lv.load_schedule_diversity import (
    Load,
    LoadScheduleInput,
    _parse_loads,
    calculate,
)

SAMPLE_LOADS = (
    "Duty pump, 15, 0.85, 100\n"
    "Standby pump, 15, 0.85, 0\n"
    "Lighting, 5, 0.95, 66\n"
    "Small power, 8, 0.8, 50\n"
)


def _hand_derived():
    loads = [
        (15.0, 0.85, 1.00),
        (15.0, 0.85, 0.00),
        (5.0, 0.95, 0.66),
        (8.0, 0.80, 0.50),
    ]
    P_total = sum(p * d for p, pf, d in loads)
    Q_total = sum((p * d) * math.tan(math.acos(pf)) for p, pf, d in loads)
    S_total = math.hypot(P_total, Q_total)
    connected = sum(p for p, pf, d in loads)
    return P_total, Q_total, S_total, connected


def test_parser_extracts_all_valid_lines_with_diversity():
    loads, unparsed = _parse_loads(SAMPLE_LOADS)
    assert len(loads) == 4
    assert unparsed == []
    assert loads[0].diversity_factor_percent == pytest.approx(100.0)
    assert loads[1].diversity_factor_percent == pytest.approx(0.0)


def test_parser_defaults_diversity_to_100_when_omitted():
    loads, unparsed = _parse_loads("Fan, 3, 0.9\n")
    assert len(loads) == 1
    assert unparsed == []
    assert loads[0].diversity_factor_percent == pytest.approx(100.0)


def test_parser_reports_unparseable_lines():
    text = SAMPLE_LOADS + "garbage\nBad load, -5, 0.9, 100\n"
    loads, unparsed = _parse_loads(text)
    assert len(loads) == 4
    assert len(unparsed) == 2


def test_p_q_s_totals_match_hand_derivation():
    result = calculate(LoadScheduleInput(loads_text=SAMPLE_LOADS))
    expected_P, expected_Q, expected_S, expected_connected = _hand_derived()

    P_total = next(t.value for t in result.terms if t.label.startswith("P total"))
    Q_total = next(t.value for t in result.terms if t.label.startswith("Q total"))
    S_total = next(t.value for t in result.terms if t.label.startswith("S total"))
    connected = next(t.value for t in result.terms if t.label.startswith("Connected load"))

    assert P_total == pytest.approx(expected_P, rel=1e-9)
    assert Q_total == pytest.approx(expected_Q, rel=1e-9)
    assert S_total == pytest.approx(expected_S, rel=1e-9)
    assert connected == pytest.approx(expected_connected, rel=1e-9)


def test_maximum_demand_current_matches_hand_derivation_three_phase():
    result = calculate(LoadScheduleInput(loads_text=SAMPLE_LOADS, system_voltage_v=400.0, number_of_phases=3))
    _, _, expected_S, _ = _hand_derived()
    expected_current = expected_S * 1000.0 / (math.sqrt(3) * 400.0)
    assert result.headline.value == pytest.approx(expected_current, rel=1e-9)


def test_single_phase_uses_v_not_sqrt3_v():
    result = calculate(LoadScheduleInput(loads_text=SAMPLE_LOADS, system_voltage_v=230.0, number_of_phases=1))
    _, _, expected_S, _ = _hand_derived()
    expected_current = expected_S * 1000.0 / 230.0
    assert result.headline.value == pytest.approx(expected_current, rel=1e-9)


def test_overall_diversity_factor_below_one_when_diversity_applied():
    result = calculate(LoadScheduleInput(loads_text=SAMPLE_LOADS))
    overall_diversity = next(t.value for t in result.terms if t.label == "Overall diversity factor")
    _, _, _, expected_connected = _hand_derived()
    expected_P, *_ = _hand_derived()
    assert overall_diversity == pytest.approx(expected_P / expected_connected, rel=1e-9)
    assert overall_diversity < 1.0


def test_no_diversity_applied_triggers_warning():
    text = "Load A, 10, 0.9, 100\nLoad B, 5, 0.9, 100\n"
    result = calculate(LoadScheduleInput(loads_text=text))
    assert any("No diversity applied" in w for w in result.warnings)


def test_some_diversity_applied_suppresses_no_diversity_warning():
    result = calculate(LoadScheduleInput(loads_text=SAMPLE_LOADS))
    assert not any("No diversity applied" in w for w in result.warnings)


def test_unity_power_factor_gives_zero_reactive_power():
    result = calculate(LoadScheduleInput(loads_text="Resistive heater, 10, 1.0, 100\n"))
    Q_total = next(t.value for t in result.terms if t.label.startswith("Q total"))
    P_total = next(t.value for t in result.terms if t.label.startswith("P total"))
    S_total = next(t.value for t in result.terms if t.label.startswith("S total"))
    assert Q_total == pytest.approx(0.0, abs=1e-9)
    assert S_total == pytest.approx(P_total, rel=1e-9)


def test_no_valid_loads_returns_zero_with_warning():
    result = calculate(LoadScheduleInput(loads_text="garbage\nmore garbage"))
    assert result.headline.value == pytest.approx(0.0)
    assert any("No valid loads parsed" in w for w in result.warnings)


def test_blank_loads_text_rejected():
    with pytest.raises(ValidationError):
        LoadScheduleInput(loads_text="   ")


def test_out_of_range_power_factor_rejected_by_model():
    with pytest.raises(ValidationError):
        Load(name="Bad", rated_power_kw=10.0, power_factor=1.5)
