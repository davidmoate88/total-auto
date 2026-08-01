"""
Shared interfaces for engineering calculation modules.

Every calc module in `calcs/` follows the same shape:

    - An input model (pydantic BaseModel) describing what the engineer supplies.
    - A `calculate(inputs) -> CalcResult` function that does the work.
    - A CalcResult carrying every intermediate term, not just the headline answer,
      so the output can actually be checked by a reviewer.

Modules register themselves in `CALC_REGISTRY` (see `calcs/registry.py`) so the
UI (`app.py`) and any future portfolio/reporting tooling can discover and run them
without needing to know about each discipline individually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Term:
    """One labelled intermediate value in a calculation, kept for review purposes."""

    label: str
    value: float
    unit: str = ""
    note: str = ""

    def formatted(self, precision: int = 3) -> str:
        val = f"{self.value:.{precision}g}"
        unit = f" {self.unit}" if self.unit else ""
        note = f" — {self.note}" if self.note else ""
        return f"{self.label} = {val}{unit}{note}"


@dataclass
class CalcResult:
    """
    Standard result shape for any calc module.

    `headline` is the single most important output (e.g. allowable bearing
    capacity). `terms` holds every intermediate value in the order they were
    derived, so the full working can be reconstructed by a reviewer. `warnings`
    surfaces anything the calculation wants to flag (out-of-range inputs, an
    assumption that was applied, etc.) without stopping execution.
    """

    headline: Term
    terms: list[Term] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    method: str = ""
    references: list[str] = field(default_factory=list)


@dataclass
class CalcModule:
    """Metadata + entry point for one registered calculation."""

    key: str
    name: str
    discipline: str
    description: str
    input_model: type
    calculate: Callable[[Any], CalcResult]
