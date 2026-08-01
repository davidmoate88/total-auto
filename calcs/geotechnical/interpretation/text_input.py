"""
Lenient line-based parsers for pasting site investigation data straight from a
spreadsheet or simplified log — NOT a general natural-language report parser.

Each parser accepts one reading per line, comma- or whitespace-separated,
tolerant of a units suffix stuck directly onto a number (e.g. "1.5m"). Lines
that don't match the expected shape are returned separately as "unparsed" so
they can be shown back to the user for review rather than silently dropped —
this matters because mis-scraped geotechnical numbers feed directly into a
foundation design calculation.

For a genuine free-form report excerpt (prose, tables embedded in narrative
text), this deterministic parser is the wrong tool — that's a case for having
the excerpt read directly and translated into this simple format, rather than
a regex trying to do natural-language extraction on safety-relevant data.
"""

from __future__ import annotations

import re

from calcs.geotechnical.interpretation.models import CPTReading, LabTestResult, SPTReading

_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _to_float(token: str) -> float:
    match = _NUMBER_RE.match(token.strip())
    if not match:
        raise ValueError(f"Not a number: '{token}'")
    return float(match.group())


def _split_line(line: str) -> list[str]:
    if "," in line:
        return [t.strip() for t in line.split(",") if t.strip()]
    return [t.strip() for t in line.split() if t.strip()]


def _iter_data_lines(text: str):
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        yield line


def parse_spt_lines(text: str) -> tuple[list[SPTReading], list[str]]:
    readings: list[SPTReading] = []
    unparsed: list[str] = []
    for line in _iter_data_lines(text):
        tokens = _split_line(line)
        try:
            if len(tokens) == 2:
                depth, n_value = _to_float(tokens[0]), _to_float(tokens[1])
                readings.append(SPTReading(depth_m=depth, n_value=n_value))
            elif len(tokens) == 3:
                depth, n_value, energy = (_to_float(t) for t in tokens)
                readings.append(SPTReading(depth_m=depth, n_value=n_value, energy_ratio_pct=energy))
            else:
                unparsed.append(line)
        except (ValueError, TypeError):
            unparsed.append(line)
    return readings, unparsed


def parse_cpt_lines(text: str) -> tuple[list[CPTReading], list[str]]:
    readings: list[CPTReading] = []
    unparsed: list[str] = []
    for line in _iter_data_lines(text):
        tokens = _split_line(line)
        try:
            if len(tokens) == 2:
                depth, qc = _to_float(tokens[0]), _to_float(tokens[1])
                readings.append(CPTReading(depth_m=depth, qc_mpa=qc))
            elif len(tokens) == 3:
                depth, qc, fs = (_to_float(t) for t in tokens)
                readings.append(CPTReading(depth_m=depth, qc_mpa=qc, fs_kpa=fs))
            else:
                unparsed.append(line)
        except (ValueError, TypeError):
            unparsed.append(line)
    return readings, unparsed


_LAB_KEY_MAP = {
    "phi": "phi_deg",
    "c": "c_kpa",
    "cu": "cu_kpa",
    "unit_weight": "unit_weight_kn_m3",
    "gamma": "unit_weight_kn_m3",
}
_VALID_TEST_TYPES = {"triaxial_cu", "triaxial_uu", "direct_shear", "unconfined_compression", "bulk_density"}


def parse_lab_lines(text: str) -> tuple[list[LabTestResult], list[str]]:
    results: list[LabTestResult] = []
    unparsed: list[str] = []
    for line in _iter_data_lines(text):
        tokens = _split_line(line)
        try:
            if len(tokens) < 3:
                raise ValueError("expected at least depth, test_type, and one key=value")
            depth = _to_float(tokens[0])
            test_type = tokens[1].strip().lower()
            if test_type not in _VALID_TEST_TYPES:
                raise ValueError(f"unknown test_type '{test_type}'")
            kwargs: dict[str, float] = {}
            for tok in tokens[2:]:
                if "=" not in tok:
                    raise ValueError(f"expected key=value, got '{tok}'")
                key, value = tok.split("=", 1)
                key = key.strip().lower()
                if key not in _LAB_KEY_MAP:
                    raise ValueError(f"unknown key '{key}'")
                kwargs[_LAB_KEY_MAP[key]] = _to_float(value)
            results.append(LabTestResult(depth_m=depth, test_type=test_type, **kwargs))
        except (ValueError, TypeError):
            unparsed.append(line)
    return results, unparsed
