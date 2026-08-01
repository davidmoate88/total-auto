"""
Central registry of available calc modules. The UI (`app.py`) and any future
tooling discover calcs through this list rather than importing each module by
name — adding a new discipline/calc means writing the module and adding one
line here.
"""

from calcs.geotechnical.bearing_capacity import MODULE as GEOTECH_BEARING_CAPACITY
from core.calc_base import CalcModule

CALC_REGISTRY: list[CalcModule] = [
    GEOTECH_BEARING_CAPACITY,
]


def get_module(key: str) -> CalcModule:
    for module in CALC_REGISTRY:
        if module.key == key:
            return module
    raise KeyError(f"No calc module registered with key '{key}'")
