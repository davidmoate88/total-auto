import pytest
from pydantic import ValidationError

from calcs.geotechnical.bearing_capacity import BearingResistanceInput, calculate
from calcs.geotechnical.interpretation.ground_model import (
    characteristic_value,
    interpret_stratum,
    overburden_profile_kpa,
    to_bearing_resistance_kwargs,
)
from calcs.geotechnical.interpretation.models import (
    CPTReading,
    LabTestResult,
    SiteInvestigation,
    SPTReading,
    Stratum,
)


def test_characteristic_value_small_and_large_samples():
    value, _ = characteristic_value([30, 32, 31])
    assert value == pytest.approx(30.0)  # mean-1sd(=30) ties min here
    value_single, _ = characteristic_value([30])
    assert value_single == 30
    with pytest.raises(ValueError):
        characteristic_value([])


def _multi_layer_site():
    fill = Stratum(
        name="fill", top_depth_m=0, base_depth_m=1.0, behavior="granular", assumed_unit_weight_kn_m3=17,
        spt_readings=[SPTReading(depth_m=0.5, n_value=6)],
    )
    sand = Stratum(
        name="sand", top_depth_m=1.0, base_depth_m=6.0, behavior="granular", assumed_unit_weight_kn_m3=18,
        spt_readings=[
            SPTReading(depth_m=2.0, n_value=14),
            SPTReading(depth_m=3.5, n_value=18),
            SPTReading(depth_m=5.0, n_value=25),
        ],
        cpt_readings=[CPTReading(depth_m=2.5, qc_mpa=6.5)],
        lab_tests=[LabTestResult(depth_m=3.0, test_type="bulk_density", unit_weight_kn_m3=19.0)],
    )
    return SiteInvestigation(water_table_depth_m=2.0, strata=[fill, sand])


def test_overburden_profile_accounts_for_water_table_and_lab_unit_weight():
    site = _multi_layer_site()
    total, effective = overburden_profile_kpa(3.5, site.strata, site.water_table_depth_m)
    # fill: 1.0m @ 17 (dry, above water table); sand: lab-derived unit weight 19.0 overrides
    # the assumed 18 for the 2.5m of sand present above 3.5m depth.
    expected_total = 17 * 1.0 + 19 * 2.5
    expected_effective = 17 * 1.0 + 19 * 1.0 + (19 - 9.81) * 1.5
    assert total == pytest.approx(expected_total)
    assert effective == pytest.approx(expected_effective)


def test_interpret_stratum_granular_pools_all_sources_and_hands_off():
    site = _multi_layer_site()
    sand = site.strata[1]
    design_params, notes = interpret_stratum(site, sand)

    assert design_params.phi_deg is not None
    assert design_params.unit_weight_kn_m3 == pytest.approx(19.0)  # from lab bulk density
    assert design_params.warnings == []
    assert len(notes) >= 5  # 3 SPT + 1 CPT + characteristic-value notes at minimum

    kwargs = to_bearing_resistance_kwargs(design_params)
    assert kwargs["analysis_type"] == "drained"

    bc_input = BearingResistanceInput(
        width_m=2.0, length_m=2.0, depth_m=3.5,
        characteristic_permanent_load_kn=300, characteristic_variable_load_kn=100,
        **kwargs,
    )
    result = calculate(bc_input)
    assert result.headline.value > 0


def test_interpret_stratum_cohesive_uses_undrained_path():
    clay = Stratum(
        name="clay", top_depth_m=0, base_depth_m=4.0, behavior="cohesive", assumed_unit_weight_kn_m3=19,
        spt_readings=[SPTReading(depth_m=1.0, n_value=6), SPTReading(depth_m=2.5, n_value=9)],
        lab_tests=[LabTestResult(depth_m=2.0, test_type="triaxial_uu", cu_kpa=55)],
    )
    site = SiteInvestigation(water_table_depth_m=None, strata=[clay])
    design_params, _ = interpret_stratum(site, clay)

    assert design_params.cu_kpa is not None
    assert design_params.phi_deg is None
    kwargs = to_bearing_resistance_kwargs(design_params)
    assert kwargs["analysis_type"] == "undrained"


def test_stratum_rejects_reading_outside_depth_range():
    with pytest.raises(ValidationError):
        Stratum(
            name="bad", top_depth_m=0, base_depth_m=2.0, behavior="granular", assumed_unit_weight_kn_m3=18,
            spt_readings=[SPTReading(depth_m=5.0, n_value=10)],
        )


def test_site_rejects_non_contiguous_strata():
    a = Stratum(name="a", top_depth_m=0, base_depth_m=1.0, behavior="granular", assumed_unit_weight_kn_m3=18)
    b = Stratum(name="b", top_depth_m=1.5, base_depth_m=3.0, behavior="granular", assumed_unit_weight_kn_m3=18)
    with pytest.raises(ValidationError):
        SiteInvestigation(water_table_depth_m=None, strata=[a, b])


def test_lab_test_requires_at_least_one_value():
    with pytest.raises(ValidationError):
        LabTestResult(depth_m=1.0, test_type="triaxial_cu")


def test_no_data_produces_warning_not_crash():
    empty = Stratum(name="empty", top_depth_m=0, base_depth_m=2.0, behavior="granular", assumed_unit_weight_kn_m3=18)
    site = SiteInvestigation(water_table_depth_m=None, strata=[empty])
    design_params, _ = interpret_stratum(site, empty)
    assert design_params.phi_deg is None
    assert any("no spt/cpt/lab data" in w.lower() for w in design_params.warnings)
