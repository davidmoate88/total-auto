"""
Tests for the BS 7671 Chapter 41 earth fault loop impedance (Zs) module.
Zs = Ze + (R1+R2)*temperature_correction_factor is checked directly against
a hand calculation, not read from any BS 7671 table.
"""

import pytest
from pydantic import ValidationError

from calcs.electrical_lv.earth_fault_loop_impedance import (
    STANDARD_TEMPERATURE_CORRECTION_FACTOR,
    EarthFaultLoopImpedanceInput,
    calculate,
)

BASE_KWARGS = dict(
    external_loop_impedance_ze_ohms=0.35,
    phase_conductor_resistance_ohms_per_km=1.83,
    cpc_resistance_ohms_per_km=4.61,
    cable_length_m=25.0,
    max_zs_ohms=1.09,
)


def _expected_zs(kwargs):
    length_km = kwargs["cable_length_m"] / 1000.0
    r1 = kwargs["phase_conductor_resistance_ohms_per_km"] * length_km
    r2 = kwargs["cpc_resistance_ohms_per_km"] * length_km
    factor = kwargs.get("temperature_correction_factor", STANDARD_TEMPERATURE_CORRECTION_FACTOR)
    return kwargs["external_loop_impedance_ze_ohms"] + (r1 + r2) * factor


def test_r1_r2_match_hand_calculation():
    result = calculate(EarthFaultLoopImpedanceInput(**BASE_KWARGS))
    r1 = next(t.value for t in result.terms if t.label.startswith("R1"))
    r2 = next(t.value for t in result.terms if t.label.startswith("R2"))
    assert r1 == pytest.approx(1.83 * 0.025, rel=1e-9)
    assert r2 == pytest.approx(4.61 * 0.025, rel=1e-9)


def test_zs_matches_hand_calculation_with_default_temperature_factor():
    result = calculate(EarthFaultLoopImpedanceInput(**BASE_KWARGS))
    zs = next(t.value for t in result.terms if t.label.startswith("Zs"))
    assert zs == pytest.approx(_expected_zs(BASE_KWARGS), rel=1e-9)


def test_default_temperature_correction_factor_is_1_20():
    assert STANDARD_TEMPERATURE_CORRECTION_FACTOR == pytest.approx(1.20)


def test_custom_temperature_correction_factor_applied():
    kwargs = dict(BASE_KWARGS, temperature_correction_factor=1.0)
    result = calculate(EarthFaultLoopImpedanceInput(**kwargs))
    zs = next(t.value for t in result.terms if t.label.startswith("Zs"))
    assert zs == pytest.approx(_expected_zs(kwargs), rel=1e-9)
    # No correction applied -- Zs should be lower than with the default 1.20 factor.
    default_result = calculate(EarthFaultLoopImpedanceInput(**BASE_KWARGS))
    default_zs = next(t.value for t in default_result.terms if t.label.startswith("Zs"))
    assert zs < default_zs


def test_utilisation_pass_matches_hand_calculation():
    result = calculate(EarthFaultLoopImpedanceInput(**BASE_KWARGS))
    expected_zs = _expected_zs(BASE_KWARGS)
    expected_utilisation = expected_zs / BASE_KWARGS["max_zs_ohms"]
    assert result.headline.value == pytest.approx(expected_utilisation, rel=1e-9)
    assert "PASS" in result.headline.note
    assert not any(f.category == "safety" for f in result.risk_flags)


def test_zs_exceeding_max_fails_and_raises_safety_flag():
    kwargs = dict(BASE_KWARGS, max_zs_ohms=0.2)  # much lower than the computed Zs
    result = calculate(EarthFaultLoopImpedanceInput(**kwargs))
    assert "FAIL" in result.headline.note
    assert result.headline.value > 1.0
    assert any(f.category == "safety" and f.severity == "critical" for f in result.risk_flags)
    assert any("FAILS" in w for w in result.warnings)


def test_higher_ze_increases_zs():
    low_ze = calculate(EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, external_loop_impedance_ze_ohms=0.1)))
    high_ze = calculate(EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, external_loop_impedance_ze_ohms=0.8)))
    zs_low = next(t.value for t in low_ze.terms if t.label.startswith("Zs"))
    zs_high = next(t.value for t in high_ze.terms if t.label.startswith("Zs"))
    assert zs_high > zs_low


def test_longer_cable_run_increases_zs():
    short = calculate(EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, cable_length_m=10.0)))
    long = calculate(EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, cable_length_m=100.0)))
    zs_short = next(t.value for t in short.terms if t.label.startswith("Zs"))
    zs_long = next(t.value for t in long.terms if t.label.startswith("Zs"))
    assert zs_long > zs_short


def test_larger_conductors_reduce_zs():
    # Larger CSA -> lower resistance per km -> lower Zs.
    small_csa = calculate(EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, phase_conductor_resistance_ohms_per_km=7.41, cpc_resistance_ohms_per_km=12.10)))
    large_csa = calculate(EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, phase_conductor_resistance_ohms_per_km=1.15, cpc_resistance_ohms_per_km=1.83)))
    zs_small = next(t.value for t in small_csa.terms if t.label.startswith("Zs"))
    zs_large = next(t.value for t in large_csa.terms if t.label.startswith("Zs"))
    assert zs_large < zs_small


def test_zero_or_negative_inputs_rejected_by_validation():
    with pytest.raises(ValidationError):
        EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, cable_length_m=0.0))
    with pytest.raises(ValidationError):
        EarthFaultLoopImpedanceInput(**dict(BASE_KWARGS, max_zs_ohms=-1.0))
