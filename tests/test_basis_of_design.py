from basis_of_design.civils import CIVILS_SECTION_NAMES, build_civils_bod_skeleton
from basis_of_design.core import BasisOfDesignSection
from basis_of_design.render import render_basis_of_design


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
