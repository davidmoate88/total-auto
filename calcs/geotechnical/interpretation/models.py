"""
Data models for site investigation input: SPT/CPT readings, lab test results,
and the stratum/site structures they're organised into.

These describe raw or lightly-processed investigation data. Deriving design
parameters (phi', c', cu, unit weight) from this data happens in
`ground_model.py`; the correlations themselves live in `correlations.py`.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SoilBehavior = Literal["granular", "cohesive"]
LabTestType = Literal["triaxial_cu", "triaxial_uu", "direct_shear", "unconfined_compression", "bulk_density"]


class SPTReading(BaseModel):
    depth_m: float = Field(..., ge=0)
    n_value: float = Field(..., ge=0, description="Raw (field) SPT N-value, blows/300mm.")
    energy_ratio_pct: float = Field(60.0, gt=0, le=100, description="Hammer energy ratio, % (60 = standard reference).")


class CPTReading(BaseModel):
    depth_m: float = Field(..., ge=0)
    qc_mpa: float = Field(..., ge=0, description="Cone tip resistance, qc (MPa).")
    fs_kpa: Optional[float] = Field(None, ge=0, description="Sleeve friction, fs (kPa) — not currently used in the correlations.")


class LabTestResult(BaseModel):
    depth_m: float = Field(..., ge=0)
    test_type: LabTestType
    phi_deg: Optional[float] = Field(None, gt=0, le=45)
    c_kpa: Optional[float] = Field(None, ge=0)
    cu_kpa: Optional[float] = Field(None, gt=0)
    unit_weight_kn_m3: Optional[float] = Field(None, gt=0)

    @model_validator(mode="after")
    def _check_has_relevant_result(self) -> "LabTestResult":
        has_any = any(v is not None for v in (self.phi_deg, self.c_kpa, self.cu_kpa, self.unit_weight_kn_m3))
        if not has_any:
            raise ValueError("Lab test result has no phi/c/cu/unit_weight value recorded.")
        return self


class Stratum(BaseModel):
    name: str
    top_depth_m: float = Field(..., ge=0)
    base_depth_m: float = Field(..., gt=0)
    behavior: SoilBehavior
    assumed_unit_weight_kn_m3: float = Field(
        ..., gt=0,
        description="Best-estimate bulk unit weight used for overburden stress calcs, "
        "overridden per-point by lab bulk_density results where available.",
    )
    spt_readings: list[SPTReading] = Field(default_factory=list)
    cpt_readings: list[CPTReading] = Field(default_factory=list)
    lab_tests: list[LabTestResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_depths(self) -> "Stratum":
        if self.base_depth_m <= self.top_depth_m:
            raise ValueError("base_depth_m must be greater than top_depth_m.")
        for label, readings in (("SPT", self.spt_readings), ("CPT", self.cpt_readings), ("lab test", self.lab_tests)):
            for r in readings:
                if not (self.top_depth_m <= r.depth_m <= self.base_depth_m):
                    raise ValueError(
                        f"{label} reading at {r.depth_m} m falls outside stratum '{self.name}' "
                        f"depth range [{self.top_depth_m}, {self.base_depth_m}] m."
                    )
        return self


class SiteInvestigation(BaseModel):
    water_table_depth_m: Optional[float] = Field(None, ge=0, description="Depth to water table (m bgl). None = no water table encountered.")
    strata: list[Stratum] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_strata_contiguous(self) -> "SiteInvestigation":
        ordered = sorted(self.strata, key=lambda s: s.top_depth_m)
        for a, b in zip(ordered, ordered[1:]):
            if abs(a.base_depth_m - b.top_depth_m) > 1e-6:
                raise ValueError(
                    f"Strata are not contiguous: '{a.name}' ends at {a.base_depth_m} m but "
                    f"'{b.name}' starts at {b.top_depth_m} m. Overburden calculations assume "
                    "a continuous layered profile with no gaps or overlaps."
                )
        return self
