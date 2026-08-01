"""
Central registry of available calc modules. The UI (`app.py`) and any future
tooling discover calcs through this list rather than importing each module by
name — adding a new discipline/calc means writing the module and adding one
line here.
"""

from calcs.geotechnical.bearing_capacity import MODULE as GEOTECH_BEARING_CAPACITY
from calcs.structural.base_plate import MODULE as STRUCTURAL_BASE_PLATE
from calcs.structural.beam_capacity import MODULE as STRUCTURAL_BEAM_CAPACITY
from calcs.structural.bolted_shear_connection import MODULE as STRUCTURAL_BOLTED_SHEAR_CONNECTION
from calcs.structural.column_capacity import MODULE as STRUCTURAL_COLUMN_CAPACITY
from core.calc_base import CalcModule

CALC_REGISTRY: list[CalcModule] = [
    GEOTECH_BEARING_CAPACITY,
    STRUCTURAL_BEAM_CAPACITY,
    STRUCTURAL_COLUMN_CAPACITY,
    STRUCTURAL_BOLTED_SHEAR_CONNECTION,
    STRUCTURAL_BASE_PLATE,
]


def get_module(key: str) -> CalcModule:
    for module in CALC_REGISTRY:
        if module.key == key:
            return module
    raise KeyError(f"No calc module registered with key '{key}'")
