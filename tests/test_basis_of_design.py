from basis_of_design.civils import CIVILS_SECTION_NAMES, build_civils_bod_skeleton
from basis_of_design.core import BasisOfDesignSection
from basis_of_design.electrical_lv import ELECTRICAL_LV_SECTION_NAMES, build_electrical_lv_bod_skeleton
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
