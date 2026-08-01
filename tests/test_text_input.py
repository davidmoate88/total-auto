from calcs.geotechnical.interpretation.text_input import parse_cpt_lines, parse_lab_lines, parse_spt_lines


def test_parse_spt_lines_tolerant_of_units_and_flags_garbage():
    text = "# comment\n1.0, 8\n2.0m, 14\n3.0 22 45\ngarbage line here"
    readings, unparsed = parse_spt_lines(text)
    assert len(readings) == 3
    assert readings[1].depth_m == 2.0
    assert readings[2].energy_ratio_pct == 45
    assert unparsed == ["garbage line here"]


def test_parse_cpt_lines():
    readings, unparsed = parse_cpt_lines("1.0, 3.2\n2.0, 5.6, 40\nnonsense")
    assert len(readings) == 2
    assert readings[1].fs_kpa == 40
    assert unparsed == ["nonsense"]


def test_parse_lab_lines_rejects_unknown_type_and_bad_shape():
    text = (
        "2.5, triaxial_cu, phi=28, c=2\n"
        "3.0, bulk_density, unit_weight=19.2\n"
        "4.0, bogus_type, phi=20\n"
        "no commas here at all"
    )
    results, unparsed = parse_lab_lines(text)
    assert len(results) == 2
    assert results[0].phi_deg == 28 and results[0].c_kpa == 2
    assert results[1].unit_weight_kn_m3 == 19.2
    assert len(unparsed) == 2
