from integration.graph import GEOTECHNICAL_CALC_KEY, build_dependency_graph
from integration.master_document import render_master_basis_of_design
from integration.open_items import extract_open_items, open_items_as_action_items, render_open_items_register
from integration.process_state import ProjectProcessState, blocked_sections, progress_summary, unblocked_sections


def test_dependency_graph_has_one_section_node_per_built_discipline_section():
    # 9 (civils) + 9 (structural) + 9 (lv) + 8 (hv) + 9 (mechanical piping) = 44
    graph = build_dependency_graph()
    assert len(graph.sections) == 44


def test_dependency_graph_edge_count_matches_declared_interfaces():
    # Every Interface() already declared across the five discipline modules
    # becomes exactly one edge -- 33 as of the detail pass. If this drifts,
    # it means an interface was added/removed without the graph noticing,
    # or the resolution logic double/under-counted something.
    graph = build_dependency_graph()
    assert len(graph.edges) == 33


def test_structural_foundations_depends_on_the_built_geotechnical_calc():
    graph = build_dependency_graph()
    upstream = graph.upstream_of("section:structural.substructure_and_foundations")
    assert f"calc:{GEOTECHNICAL_CALC_KEY}" in upstream


def test_discipline_cycle_detection_finds_the_mutually_dependent_cluster():
    # civils, electrical_hv, electrical_lv, and mechanical_piping each
    # reference at least one of the others (utilities coordination, hazardous
    # area classification, transformer/LV supply, pipe routing) and the
    # references loop back round -- they can't be strictly sequenced.
    graph = build_dependency_graph()
    cycles = graph.find_discipline_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"civils", "electrical_hv", "electrical_lv", "mechanical_piping"}


def test_structural_is_not_part_of_any_discipline_cycle():
    # Structural only depends on geotechnical (a calc, not a BoD discipline)
    # and an external contractor -- nothing in the graph loops back into it.
    graph = build_dependency_graph()
    cycles = graph.find_discipline_cycles()
    assert all("structural" not in cluster for cluster in cycles)


def test_mermaid_output_includes_all_five_disciplines_and_the_calc_node():
    graph = build_dependency_graph()
    mermaid = graph.to_mermaid()
    assert mermaid.startswith("flowchart LR")
    for disc in ["civils", "structural", "electrical_lv", "electrical_hv", "mechanical_piping"]:
        assert disc in mermaid
    assert "Geotechnical" in mermaid


def test_unblocked_and_blocked_sections_partition_all_sections_at_project_start():
    graph = build_dependency_graph()
    state = ProjectProcessState(project_reference="PRJ-TEST")
    unblocked = unblocked_sections(graph, state)
    blocked = blocked_sections(graph, state)
    assert len(unblocked) + len(blocked) == len(graph.sections)
    assert set(unblocked).isdisjoint({b.section_id for b in blocked})


def test_resolving_geotechnical_calc_unblocks_a_dependent_section():
    graph = build_dependency_graph()
    state = ProjectProcessState()
    target = "section:structural.substructure_and_foundations"
    assert target not in unblocked_sections(graph, state)  # blocked at start

    state.set_status(f"calc:{GEOTECHNICAL_CALC_KEY}", "resolved")
    assert target in unblocked_sections(graph, state)


def test_progress_summary_counts_every_section_exactly_once_per_discipline():
    graph = build_dependency_graph()
    state = ProjectProcessState()
    summary = progress_summary(graph, state)
    assert set(summary.keys()) == {"civils", "structural", "electrical_lv", "electrical_hv", "mechanical_piping"}
    totals = {disc: sum(counts.values()) for disc, counts in summary.items()}
    assert totals == {"civils": 9, "structural": 9, "electrical_lv": 9, "electrical_hv": 8, "mechanical_piping": 9}


def test_open_items_extraction_finds_pending_criteria_and_assumptions():
    items = extract_open_items()
    assert len(items) > 0
    assert all(item.discipline in {"civils", "structural", "electrical_lv", "electrical_hv", "mechanical_piping"} for item in items)
    assert all(item.item_type in {"criterion", "assumption"} for item in items)


def test_open_items_convert_to_action_items_with_project_reference():
    items = extract_open_items()
    actions = open_items_as_action_items(items, project_reference="PRJ-001")
    assert len(actions) == len(items)
    assert all(a.related_project_reference == "PRJ-001" for a in actions)
    assert all(a.status == "open" for a in actions)


def test_open_items_register_renders_count_and_per_discipline_sections():
    items = extract_open_items()
    register = render_open_items_register(items)
    assert str(len(items)) in register
    for discipline in {i.discipline for i in items}:
        assert f"### {discipline}" in register


def test_master_document_includes_process_flow_open_items_and_all_disciplines():
    doc = render_master_basis_of_design(project_reference="PRJ-006")
    assert "PRJ-006" in doc
    assert "Process flow" in doc
    assert "Open items / RFI register" in doc
    assert "```mermaid" in doc
    for title in ["Civils", "Structural", "LV Electrical", "HV Electrical", "Mechanical Piping"]:
        assert f"## {title} — full basis of design" in doc
