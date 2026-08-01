from basis_of_design.civils import CIVILS_SECTION_NAMES, build_civils_bod_skeleton
from basis_of_design.core import BasisOfDesignSection
from basis_of_design.electrical_hv import ELECTRICAL_HV_SECTION_NAMES, build_electrical_hv_bod_skeleton
from basis_of_design.electrical_lv import ELECTRICAL_LV_SECTION_NAMES, build_electrical_lv_bod_skeleton
from basis_of_design.mechanical_piping import MECHANICAL_PIPING_SECTION_NAMES, build_mechanical_piping_bod_skeleton
from basis_of_design.render import render_basis_of_design
from basis_of_design.structural import STRUCTURAL_SECTION_NAMES, build_structural_bod_skeleton


def test_civils_skeleton_has_all_nine_sections():
    bod = build_civils_bod_skeleton()
    assert set(bod.sections().keys()) == set(CIVILS_SECTION_NAMES)
    assert len(bod.sections()) == 9


def test_every_section_has_a_scope_and_at_least_one_standard_or_interface():
    bod = build_civils_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.scope, f"{name} has no scope description"
        assert section.standards or section.interfaces, f"{name} has neither standards nor interfaces"


def test_is_populated_distinguishes_skeleton_from_content():
    empty = BasisOfDesignSection(name="Empty section")
    assert not empty.is_populated()

    with_content = BasisOfDesignSection(name="Has content", scope="something")
    with_content.exclusions.append("out of scope item")
    assert with_content.is_populated()


def test_render_includes_project_reference_and_all_section_names():
    bod = build_civils_bod_skeleton(project_reference="PRJ-001")
    report = render_basis_of_design("Civils", bod.sections(), project_reference=bod.project_reference)
    assert "PRJ-001" in report
    for section in bod.sections().values():
        assert section.name in report


def test_render_flags_skeleton_only_sections():
    # Every section in the civils skeleton already carries at least standards or
    # interfaces, so none count as "skeleton-only" under is_populated() -- prove
    # that path instead with a deliberately bare section mixed into a small set.
    sections = {
        "populated": BasisOfDesignSection(name="Populated section", scope="x", exclusions=["out of scope"]),
        "bare": BasisOfDesignSection(name="Bare section", scope="not started yet"),
    }
    report = render_basis_of_design("Civils", sections)
    assert "1 of 2 sections have content" in report
    assert "Bare section" in report
    assert "(Skeleton only — no content added yet.)" in report


def test_civils_skeleton_sections_all_currently_carry_some_content():
    # Documents current behaviour: every section was given at least standards or
    # interfaces when the skeleton was written, so none render as bare/skeleton-only.
    bod = build_civils_bod_skeleton()
    assert all(s.is_populated() for s in bod.sections().values())


def test_civils_detail_pass_populates_criteria_assumptions_exclusions_and_deliverables():
    # 2nd-pass check: every civils section now carries actual design criteria,
    # working assumptions, exclusions, and deliverables -- not just scope/
    # standards/interfaces from the architecture pass.
    bod = build_civils_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.criteria, f"{name} missing criteria"
        assert section.assumptions, f"{name} missing assumptions"
        assert section.exclusions, f"{name} missing exclusions"
        assert section.deliverables, f"{name} missing deliverables"


def test_civils_flood_risk_criterion_matches_agreed_freeboard_convention():
    bod = build_civils_bod_skeleton()
    names = {c.name for c in bod.flood_risk.criteria}
    assert "Finished floor level freeboard" in names


def test_civils_surface_water_criteria_follow_suds_hierarchy():
    bod = build_civils_bod_skeleton()
    hierarchy_criterion = next(
        (c for c in bod.surface_water_drainage_suds.criteria if c.name == "SuDS management train priority"), None
    )
    assert hierarchy_criterion is not None
    assert "infiltration" in hierarchy_criterion.value.lower()


def test_structural_skeleton_has_all_nine_sections():
    bod = build_structural_bod_skeleton()
    assert set(bod.sections().keys()) == set(STRUCTURAL_SECTION_NAMES)
    assert len(bod.sections()) == 9


def test_structural_every_section_has_a_scope_and_at_least_one_standard_or_interface():
    bod = build_structural_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.scope, f"{name} has no scope description"
        assert section.standards or section.interfaces, f"{name} has neither standards nor interfaces"


def test_structural_scope_excludes_multi_storey_building_elements():
    # Sanity-check the deliberate scope pivot (industrial access steelwork, not
    # occupied multi-storey buildings) is actually recorded, not just implied.
    bod = build_structural_bod_skeleton()
    criteria_section = bod.design_standards_and_criteria
    assert any("multi-storey" in e.lower() or "parked" in e.lower() for e in criteria_section.exclusions)


def test_structural_render_includes_project_reference_and_all_section_names():
    bod = build_structural_bod_skeleton(project_reference="PRJ-002")
    report = render_basis_of_design("Structural", bod.sections(), project_reference=bod.project_reference)
    assert "PRJ-002" in report
    for section in bod.sections().values():
        assert section.name in report


def test_structural_detail_pass_populates_criteria_assumptions_exclusions_and_deliverables():
    # 2nd-pass check: every structural section now carries actual design
    # criteria, working assumptions, exclusions, and deliverables -- not just
    # scope/standards/interfaces from the architecture pass.
    bod = build_structural_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.criteria, f"{name} missing criteria"
        assert section.assumptions, f"{name} missing assumptions"
        assert section.exclusions, f"{name} missing exclusions"
        assert section.deliverables, f"{name} missing deliverables"


def test_structural_scope_still_excludes_multi_storey_after_detail_pass():
    # The scope pivot (industrial access steelwork, not occupied multi-storey
    # buildings) must survive the detail pass, not just the architecture pass.
    bod = build_structural_bod_skeleton()
    criteria_section = bod.design_standards_and_criteria
    assert any("multi-storey" in e.lower() or "parked" in e.lower() for e in criteria_section.exclusions)


def test_structural_platforms_criteria_include_minimum_walkway_width():
    bod = build_structural_bod_skeleton()
    names = {c.name for c in bod.platforms_and_walkways.criteria}
    assert "Minimum clear walkway width" in names


def test_civils_flags_temporary_works_risk_on_earthworks_and_retaining_structures():
    bod = build_civils_bod_skeleton()
    assert any(f.category == "temporary_works" for f in bod.earthworks_and_remediation.risk_flags)
    assert any(f.category == "temporary_works" for f in bod.retaining_structures.risk_flags)
    # Sections with no inherent temporary-works implication shouldn't carry the flag.
    assert not any(f.category == "temporary_works" for f in bod.flood_risk.risk_flags)


def test_structural_flags_temporary_works_and_installation_safety_risk():
    bod = build_structural_bod_skeleton()
    assert any(f.category == "temporary_works" for f in bod.primary_steel_frame.risk_flags)
    assert any(f.category == "temporary_works" for f in bod.substructure_and_foundations.risk_flags)
    assert any(f.category == "safety" for f in bod.platforms_and_walkways.risk_flags)


def test_risk_flags_render_in_civils_and_structural_reports():
    civils = build_civils_bod_skeleton()
    structural = build_structural_bod_skeleton()
    civils_report = render_basis_of_design("Civils", civils.sections())
    structural_report = render_basis_of_design("Structural", structural.sections())
    assert "**Risk flags:**" in civils_report
    assert "**Risk flags:**" in structural_report
    assert "[HIGH] [temporary_works]" in civils_report
    assert "[HIGH] [temporary_works]" in structural_report
    assert "[HIGH] [safety]" in structural_report


def test_electrical_lv_skeleton_has_all_nine_sections():
    bod = build_electrical_lv_bod_skeleton()
    assert set(bod.sections().keys()) == set(ELECTRICAL_LV_SECTION_NAMES)
    assert len(bod.sections()) == 9


def test_electrical_lv_every_section_has_a_scope_and_at_least_one_standard_or_interface():
    bod = build_electrical_lv_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.scope, f"{name} has no scope description"
        assert section.standards or section.interfaces, f"{name} has neither standards nor interfaces"


def test_electrical_lv_includes_hazardous_area_classification_with_code_compliance_flag():
    bod = build_electrical_lv_bod_skeleton()
    assert bod.hazardous_area_classification.standards
    assert any(f.category == "code_compliance" and f.severity == "high" for f in bod.hazardous_area_classification.risk_flags)


def test_electrical_lv_flags_temporary_works_on_earthing_and_bonding():
    bod = build_electrical_lv_bod_skeleton()
    assert any(f.category == "temporary_works" for f in bod.earthing_and_bonding.risk_flags)


def test_electrical_lv_render_includes_project_reference_and_all_section_names():
    bod = build_electrical_lv_bod_skeleton(project_reference="PRJ-003")
    report = render_basis_of_design("LV Electrical", bod.sections(), project_reference=bod.project_reference)
    assert "PRJ-003" in report
    for section in bod.sections().values():
        assert section.name in report


def test_electrical_lv_detail_pass_populates_criteria_assumptions_exclusions_and_deliverables():
    # 2nd-pass check: every LV electrical section now carries actual design
    # criteria, working assumptions, exclusions, and deliverables -- not just
    # scope/standards/interfaces from the architecture pass.
    bod = build_electrical_lv_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.criteria, f"{name} missing criteria"
        assert section.assumptions, f"{name} missing assumptions"
        assert section.exclusions, f"{name} missing exclusions"
        assert section.deliverables, f"{name} missing deliverables"


def test_electrical_lv_hazardous_area_criteria_still_present_after_detail_pass():
    # The hazardous area classification standards/risk flag must survive the
    # detail pass, not just the architecture pass.
    bod = build_electrical_lv_bod_skeleton()
    assert bod.hazardous_area_classification.standards
    assert any(f.category == "code_compliance" and f.severity == "high" for f in bod.hazardous_area_classification.risk_flags)
    names = {c.name for c in bod.hazardous_area_classification.criteria}
    assert "Zone classification categories" in names


def test_electrical_lv_design_criteria_includes_system_voltage():
    bod = build_electrical_lv_bod_skeleton()
    names = {c.name for c in bod.design_standards_and_criteria.criteria}
    assert "System voltage" in names


def test_electrical_hv_skeleton_has_all_eight_sections():
    bod = build_electrical_hv_bod_skeleton()
    assert set(bod.sections().keys()) == set(ELECTRICAL_HV_SECTION_NAMES)
    assert len(bod.sections()) == 8


def test_electrical_hv_every_section_has_a_scope_and_at_least_one_standard_or_interface():
    bod = build_electrical_hv_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.scope, f"{name} has no scope description"
        assert section.standards or section.interfaces, f"{name} has neither standards nor interfaces"


def test_electrical_hv_flags_temporary_works_on_substation_cutover():
    bod = build_electrical_hv_bod_skeleton()
    assert any(f.category == "temporary_works" for f in bod.substations_and_switchgear.risk_flags)


def test_electrical_hv_flags_safety_on_earthing_and_arc_flash():
    bod = build_electrical_hv_bod_skeleton()
    assert any(f.category == "safety" and f.severity == "high" for f in bod.hv_earthing_and_touch_step_potential.risk_flags)
    assert any(f.category == "safety" and f.severity == "high" for f in bod.arc_flash_and_hv_safety.risk_flags)


def test_electrical_hv_interfaces_with_lv_via_transformers():
    bod = build_electrical_hv_bod_skeleton()
    assert any(i.with_discipline == "electrical_lv" for i in bod.transformers.interfaces)


def test_electrical_hv_render_includes_project_reference_and_all_section_names():
    bod = build_electrical_hv_bod_skeleton(project_reference="PRJ-004")
    report = render_basis_of_design("HV Electrical", bod.sections(), project_reference=bod.project_reference)
    assert "PRJ-004" in report
    for section in bod.sections().values():
        assert section.name in report


def test_electrical_hv_detail_pass_populates_criteria_assumptions_exclusions_and_deliverables():
    # 2nd-pass check: every HV electrical section now carries actual design
    # criteria, working assumptions, exclusions, and deliverables -- not just
    # scope/standards/interfaces from the architecture pass.
    bod = build_electrical_hv_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.criteria, f"{name} missing criteria"
        assert section.assumptions, f"{name} missing assumptions"
        assert section.exclusions, f"{name} missing exclusions"
        assert section.deliverables, f"{name} missing deliverables"


def test_electrical_hv_voltage_class_still_generic_after_detail_pass():
    # The "kept generic across HV voltage classes" scope decision must survive
    # the detail pass, not just the architecture pass.
    bod = build_electrical_hv_bod_skeleton()
    voltage_criterion = next(
        (c for c in bod.design_standards_and_criteria.criteria if c.name == "HV voltage class"), None
    )
    assert voltage_criterion is not None
    assert "generic" in voltage_criterion.value.lower()
    assert any("generic" in e.lower() for e in bod.design_standards_and_criteria.exclusions)


def test_electrical_hv_transformer_criteria_reference_lv_load_schedule():
    bod = build_electrical_hv_bod_skeleton()
    rating_criterion = next((c for c in bod.transformers.criteria if c.name == "Transformer rating"), None)
    assert rating_criterion is not None
    assert "lv load schedule" in rating_criterion.value.lower()


def test_mechanical_piping_skeleton_has_all_nine_sections():
    bod = build_mechanical_piping_bod_skeleton()
    assert set(bod.sections().keys()) == set(MECHANICAL_PIPING_SECTION_NAMES)
    assert len(bod.sections()) == 9


def test_mechanical_piping_every_section_has_a_scope_and_at_least_one_standard_or_interface():
    bod = build_mechanical_piping_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.scope, f"{name} has no scope description"
        assert section.standards or section.interfaces, f"{name} has neither standards nor interfaces"


def test_mechanical_piping_lists_both_governing_codes_generically():
    # Project direction: keep the governing piping code generic -- list both
    # ASME B31.3 and BS EN 13480 rather than committing to one.
    bod = build_mechanical_piping_bod_skeleton()
    codes = [s.code for s in bod.design_standards_and_criteria.standards]
    assert "ASME B31.3" in codes
    assert "BS EN 13480" in codes


def test_mechanical_piping_flags_temporary_works_on_stress_analysis_and_supports():
    bod = build_mechanical_piping_bod_skeleton()
    assert any(f.category == "temporary_works" for f in bod.pipe_stress_analysis_and_supports.risk_flags)


def test_mechanical_piping_flags_safety_on_pressure_testing():
    bod = build_mechanical_piping_bod_skeleton()
    assert any(f.category == "safety" and f.severity == "high" for f in bod.pressure_testing_and_inspection.risk_flags)


def test_mechanical_piping_flags_code_compliance_on_hazardous_area_interface():
    bod = build_mechanical_piping_bod_skeleton()
    assert any(
        f.category == "code_compliance" and f.severity == "high"
        for f in bod.supports_structural_and_hazardous_area_interfaces.risk_flags
    )


def test_mechanical_piping_interfaces_with_structural_and_electrical_lv():
    bod = build_mechanical_piping_bod_skeleton()
    assert any(i.with_discipline == "structural" for i in bod.pipe_stress_analysis_and_supports.interfaces)
    assert any(i.with_discipline == "electrical_lv" for i in bod.supports_structural_and_hazardous_area_interfaces.interfaces)


def test_mechanical_piping_render_includes_project_reference_and_all_section_names():
    bod = build_mechanical_piping_bod_skeleton(project_reference="PRJ-005")
    report = render_basis_of_design("Mechanical Piping", bod.sections(), project_reference=bod.project_reference)
    assert "PRJ-005" in report
    for section in bod.sections().values():
        assert section.name in report


def test_mechanical_piping_detail_pass_populates_criteria_assumptions_exclusions_and_deliverables():
    # 2nd-pass check: every mechanical piping section now carries actual
    # design criteria, working assumptions, exclusions, and deliverables --
    # not just scope/standards/interfaces from the architecture pass. This
    # completes the detail pass across all five agreed disciplines.
    bod = build_mechanical_piping_bod_skeleton()
    for name, section in bod.sections().items():
        assert section.criteria, f"{name} missing criteria"
        assert section.assumptions, f"{name} missing assumptions"
        assert section.exclusions, f"{name} missing exclusions"
        assert section.deliverables, f"{name} missing deliverables"


def test_mechanical_piping_governing_code_still_generic_after_detail_pass():
    # The "keep generic -- list both" governing-code decision must survive
    # the detail pass, not just the architecture pass.
    bod = build_mechanical_piping_bod_skeleton()
    codes = [s.code for s in bod.design_standards_and_criteria.standards]
    assert "ASME B31.3" in codes
    assert "BS EN 13480" in codes
    code_criterion = next(
        (c for c in bod.design_standards_and_criteria.criteria if c.name == "Governing piping code"), None
    )
    assert code_criterion is not None
    assert "generic" in code_criterion.value.lower()


def test_mechanical_piping_hydrotest_criterion_present():
    bod = build_mechanical_piping_bod_skeleton()
    names = {c.name for c in bod.pressure_testing_and_inspection.criteria}
    assert "Hydrotest pressure" in names
