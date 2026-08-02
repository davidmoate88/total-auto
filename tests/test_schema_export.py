"""
Tests for the calc module schema export. This is infrastructure for the
"fill-calc-inputs-from-drawings" skill (and the app's JSON import feature),
not a calc module itself -- these tests check the export shape/filtering
logic, not any engineering content.
"""

from calcs.registry import CALC_REGISTRY, get_module
from calcs.schema_export import export_schema


def test_exports_every_registered_module_by_default():
    schema = export_schema(CALC_REGISTRY)
    assert set(schema.keys()) == {m.key for m in CALC_REGISTRY}


def test_field_metadata_matches_a_known_required_field():
    module = get_module("electrical_hv_transformer_sizing")
    schema = export_schema([module])
    field = schema[module.key]["fields"]["lv_demand_kva"]
    assert field["type"] == "float"
    assert field["required"] is True
    assert field["default"] is None
    assert "S total" in field["description"]


def test_field_metadata_matches_a_known_optional_field_with_default():
    module = get_module("electrical_hv_transformer_sizing")
    schema = export_schema([module])
    field = schema[module.key]["fields"]["growth_margin_percent"]
    assert field["required"] is False
    assert field["default"] == 20.0


def test_literal_field_reports_allowed_values():
    module = get_module("electrical_hv_protection_grading")
    schema = export_schema([module])
    field = schema[module.key]["fields"]["downstream_curve_type"]
    assert field["type"] == "literal"
    assert set(field["allowed_values"]) == {"standard_inverse", "very_inverse", "extremely_inverse", "long_time_inverse"}


def test_optional_python_field_flagged_distinctly_from_required_or_defaulted():
    module = get_module("electrical_lv_cable_sizing_voltage_drop")
    schema = export_schema([module])
    field = schema[module.key]["fields"]["device_i2_a"]
    assert field["optional_field"] is True
    assert field["required"] is False


def test_str_field_type_reported_correctly():
    module = get_module("electrical_lv_load_schedule_diversity")
    schema = export_schema([module])
    field = schema[module.key]["fields"]["loads_text"]
    assert field["type"] == "str"
    assert field["required"] is True


def test_top_level_schema_carries_module_metadata():
    module = get_module("electrical_hv_transformer_sizing")
    schema = export_schema([module])
    entry = schema[module.key]
    assert entry["name"] == module.name
    assert entry["discipline"] == module.discipline
    assert entry["description"] == module.description


def test_export_is_json_serialisable():
    import json
    schema = export_schema(CALC_REGISTRY)
    json.dumps(schema)  # raises if anything non-serialisable slipped in
