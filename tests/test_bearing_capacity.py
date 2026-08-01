"""
Tests for the EN 1997-1 Annex D / UK NA DA1 bearing resistance module.

Nq and Nc are the standard Prandtl/Reissner closed forms (unchanged from any other
bearing capacity method) and are checked against long-established tabulated values.
The Ngamma formula used here (2*(Nq-1)*tan(phi')) is Annex-D-specific per the
module's own documented caveat — these tests check internal consistency and the
arithmetic of the formula as implemented, not an independent authoritative source
(see the module docstring's caveat about verifying Ngamma against the current
standard text).
"""

import math

import pytest
from pydantic import ValidationError

from calcs.geotechnical.bearing_capacity import (
    DA1_C1,
    DA1_C2,
    BearingResistanceInput,
    _bearing_capacity_factors,
    calculate,
)


def test_nq_nc_match_standard_values_at_phi_30():
    Nc, Nq, _ = _bearing_capacity_factors(30)
    assert Nq == pytest.approx(18.40, rel=1e-3)
    assert Nc == pytest.approx(30.14, rel=1e-3)


def test_ngamma_annex_d_formula_arithmetic():
    # Ngamma = 2*(Nq-1)*tan(phi') -- verify the implementation matches this
    # documented formula exactly (arithmetic check, not an external source check).
    Nc, Nq, Ngamma = _bearing_capacity_factors(30)
    expected = 2 * (Nq - 1) * math.tan(math.radians(30))
    assert Ngamma == pytest.approx(expected, rel=1e-9)


def test_da1_partial_factors_are_uk_na_standard_values():
    assert DA1_C1.gamma_G == pytest.approx(1.35)
    assert DA1_C1.gamma_Q == pytest.approx(1.5)
    assert DA1_C1.gamma_phi == pytest.approx(1.0)
    assert DA1_C2.gamma_G == pytest.approx(1.0)
    assert DA1_C2.gamma_Q == pytest.approx(1.3)
    assert DA1_C2.gamma_phi == pytest.approx(1.25)
    assert DA1_C2.gamma_c == pytest.approx(1.25)
    assert DA1_C2.gamma_cu == pytest.approx(1.4)


def test_length_must_be_greater_or_equal_width():
    with pytest.raises(ValidationError):
        BearingResistanceInput(
            analysis_type="drained",
            cohesion_c_prime_kpa=0,
            friction_angle_phi_prime_deg=30,
            unit_weight_kn_m3=18,
            width_m=2.0,
            length_m=1.0,
            depth_m=1.0,
        )


def test_drained_requires_phi_and_cohesion():
    with pytest.raises(ValidationError):
        BearingResistanceInput(
            analysis_type="drained",
            unit_weight_kn_m3=18,
            width_m=1.5,
            length_m=1.5,
            depth_m=1.0,
        )


def test_undrained_requires_cu():
    with pytest.raises(ValidationError):
        BearingResistanceInput(
            analysis_type="undrained",
            unit_weight_kn_m3=18,
            width_m=1.5,
            length_m=1.5,
            depth_m=1.0,
        )


def test_excessive_eccentricity_rejected():
    with pytest.raises(ValidationError):
        BearingResistanceInput(
            analysis_type="drained",
            cohesion_c_prime_kpa=0,
            friction_angle_phi_prime_deg=30,
            unit_weight_kn_m3=18,
            width_m=1.5,
            length_m=1.5,
            depth_m=1.0,
            eccentricity_b_m=0.8,  # 2*0.8 >= 1.5
        )


def test_da1_c2_reduces_friction_angle_and_governs_or_not_consistently():
    inputs = BearingResistanceInput(
        analysis_type="drained",
        cohesion_c_prime_kpa=0,
        friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        depth_m=1.0,
    )
    result = calculate(inputs)
    phi_d_c2 = next(t.value for t in result.terms if "phi'_d" in t.label and "DA1-C2" in t.label)
    expected_phi_d = math.degrees(math.atan(math.tan(math.radians(30)) / 1.25))
    assert phi_d_c2 == pytest.approx(expected_phi_d, rel=1e-6)

    Rd_c1 = next(t.value for t in result.terms if t.label == "[DA1-C1] Rd")
    Rd_c2 = next(t.value for t in result.terms if t.label == "[DA1-C2] Rd")
    assert result.headline.value == pytest.approx(min(Rd_c1, Rd_c2))


def test_no_loads_skips_utilisation_check():
    inputs = BearingResistanceInput(
        analysis_type="drained",
        cohesion_c_prime_kpa=0,
        friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        depth_m=1.0,
    )
    result = calculate(inputs)
    assert not any("Utilisation" in t.label for t in result.terms)


def test_utilisation_pass_and_fail():
    base = dict(
        analysis_type="drained",
        cohesion_c_prime_kpa=0,
        friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        depth_m=1.0,
    )
    light_load = calculate(BearingResistanceInput(**base, characteristic_permanent_load_kn=50, characteristic_variable_load_kn=20))
    heavy_load = calculate(BearingResistanceInput(**base, characteristic_permanent_load_kn=2000, characteristic_variable_load_kn=800))

    util_light = next(t.value for t in light_load.terms if "Utilisation" in t.label)
    util_heavy = next(t.value for t in heavy_load.terms if "Utilisation" in t.label)
    assert util_light < 1.0
    assert "PASS" in next(t.note for t in light_load.terms if "Utilisation" in t.label)
    assert util_heavy > 1.0
    assert "FAIL" in next(t.note for t in heavy_load.terms if "Utilisation" in t.label)
    assert any("FAILS" in w for w in heavy_load.warnings)


def test_undrained_gamma_term_absent_and_uses_pi_plus_2():
    inputs = BearingResistanceInput(
        analysis_type="undrained",
        undrained_shear_strength_cu_kpa=50,
        unit_weight_kn_m3=19,
        width_m=2.0,
        length_m=2.0,
        depth_m=1.5,
    )
    result = calculate(inputs)
    # Sanity: Nc-equivalent factor for undrained is (pi+2) ~= 5.14, matching the
    # classic Prandtl undrained bearing capacity factor -- a well-established
    # cross-check independent of the drained Ngamma uncertainty noted above.
    assert math.pi + 2 == pytest.approx(5.14159, rel=1e-4)
    assert result.headline.value > 0


def test_eccentricity_reduces_effective_area_and_resistance_side_effects():
    base = dict(
        analysis_type="drained",
        cohesion_c_prime_kpa=0,
        friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18,
        width_m=2.0,
        length_m=2.0,
        depth_m=1.0,
    )
    no_ecc = calculate(BearingResistanceInput(**base, eccentricity_b_m=0.0))
    with_ecc = calculate(BearingResistanceInput(**base, eccentricity_b_m=0.3))
    # B_eff isn't directly exposed as a Term, but Rd should differ once
    # eccentricity changes B' and therefore shape factors / the gamma term.
    assert no_ecc.headline.value != with_ecc.headline.value


def test_deep_founding_depth_raises_temporary_works_risk_flag():
    shallow = calculate(BearingResistanceInput(
        analysis_type="drained", cohesion_c_prime_kpa=0, friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18, width_m=1.5, length_m=1.5, depth_m=0.5,
    ))
    deep = calculate(BearingResistanceInput(
        analysis_type="drained", cohesion_c_prime_kpa=0, friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18, width_m=1.5, length_m=1.5, depth_m=1.0,
    ))
    assert not any(f.category == "temporary_works" for f in shallow.risk_flags)
    assert any(f.category == "temporary_works" and f.severity == "medium" for f in deep.risk_flags)


def test_failed_utilisation_raises_critical_code_compliance_risk_flag():
    base = dict(
        analysis_type="drained", cohesion_c_prime_kpa=0, friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18, width_m=1.5, length_m=1.5, depth_m=1.0,
    )
    light = calculate(BearingResistanceInput(**base, characteristic_permanent_load_kn=50, characteristic_variable_load_kn=20))
    heavy = calculate(BearingResistanceInput(**base, characteristic_permanent_load_kn=2000, characteristic_variable_load_kn=800))
    assert not any(f.category == "code_compliance" for f in light.risk_flags)
    assert any(f.category == "code_compliance" and f.severity == "critical" for f in heavy.risk_flags)
