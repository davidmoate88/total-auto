"""
Central registry of available calc modules. The UI (`app.py`) and any future
tooling discover calcs through this list rather than importing each module by
name — adding a new discipline/calc means writing the module and adding one
line here.
"""

from calcs.civil.cut_fill_balance import MODULE as CIVIL_CUT_FILL_BALANCE
from calcs.civil.foul_drainage import MODULE as CIVIL_FOUL_DRAINAGE
from calcs.civil.lateral_earth_pressure import MODULE as CIVIL_LATERAL_EARTH_PRESSURE
from calcs.civil.retaining_wall_stability import MODULE as CIVIL_RETAINING_WALL_STABILITY
from calcs.civil.surface_water_discharge import MODULE as CIVIL_SURFACE_WATER_DISCHARGE
from calcs.geotechnical.bearing_capacity import MODULE as GEOTECH_BEARING_CAPACITY
from calcs.structural.base_plate import MODULE as STRUCTURAL_BASE_PLATE
from calcs.structural.beam_capacity import MODULE as STRUCTURAL_BEAM_CAPACITY
from calcs.structural.bolted_shear_connection import MODULE as STRUCTURAL_BOLTED_SHEAR_CONNECTION
from calcs.structural.column_capacity import MODULE as STRUCTURAL_COLUMN_CAPACITY
from calcs.structural.deck_grating import MODULE as STRUCTURAL_DECK_GRATING
from core.calc_base import CalcModule

CALC_REGISTRY: list[CalcModule] = [
    GEOTECH_BEARING_CAPACITY,
    STRUCTURAL_BEAM_CAPACITY,
    STRUCTURAL_COLUMN_CAPACITY,
    STRUCTURAL_BOLTED_SHEAR_CONNECTION,
    STRUCTURAL_BASE_PLATE,
    STRUCTURAL_DECK_GRATING,
    CIVIL_LATERAL_EARTH_PRESSURE,
    CIVIL_RETAINING_WALL_STABILITY,
    CIVIL_FOUL_DRAINAGE,
    CIVIL_CUT_FILL_BALANCE,
    CIVIL_SURFACE_WATER_DISCHARGE,
]


def get_module(key: str) -> CalcModule:
    for module in CALC_REGISTRY:
        if module.key == key:
            return module
    raise KeyError(f"No calc module registered with key '{key}'")
