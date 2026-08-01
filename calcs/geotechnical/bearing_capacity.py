"""
Shallow foundation ultimate & allowable bearing capacity — Meyerhof's general
bearing capacity method.

Reference: Meyerhof, G.G. (1963); as presented in Das, B.M., "Principles of
Foundation Engineering" (standard geotechnical engineering textbook formulation).

    qu = c*Nc*Fcs*Fcd*Fci + q*Nq*Fqs*Fqd*Fqi + 0.5*gamma*B*Ngamma*Fgs*Fgd*Fgi

where q = effective overburden pressure at founding level (gamma * Df).

Scope / limitations (see Warnings in the result, and docs/ROADMAP.md):
- Assumes a dry / fully drained soil profile — no groundwater table adjustment.
- Assumes a rigid, shallow strip/rectangular/square footing (Df <= B, roughly).
- Does not check settlement (serviceability) — bearing capacity (ultimate limit
  state) only. Settlement is a separate, planned calc module.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from core.calc_base import CalcModule, CalcResult, Term


class BearingCapacityInput(BaseModel):
    cohesion_kpa: float = Field(
        ..., ge=0, description="Soil cohesion, c (kPa). Use 0 for cohesionless (sand)."
    )
    friction_angle_deg: float = Field(
        ..., ge=0, le=45, description="Effective friction angle, phi (degrees)."
    )
    unit_weight_kn_m3: float = Field(
        ..., gt=0, description="Soil unit weight, gamma (kN/m^3)."
    )
    width_m: float = Field(..., gt=0, description="Footing width, B (m).")
    length_m: float = Field(
        ..., gt=0, description="Footing length, L (m). Use L = B for a square footing."
    )
    depth_m: float = Field(..., ge=0, description="Founding depth, Df (m).")
    factor_of_safety: float = Field(
        3.0, ge=1.0, description="Factor of safety applied to net ultimate bearing capacity."
    )
    load_inclination_deg: float = Field(
        0.0, ge=0, lt=90, description="Load inclination from vertical, beta (degrees)."
    )

    @model_validator(mode="after")
    def _check_geometry(self) -> "BearingCapacityInput":
        if self.length_m < self.width_m:
            raise ValueError(
                "length_m must be >= width_m — by convention B is the shorter side. "
                "Swap the two values."
            )
        return self


def _bearing_capacity_factors(phi_deg: float) -> tuple[float, float, float]:
    """Return (Nc, Nq, Ngamma) for the given friction angle, Meyerhof's method."""
    if phi_deg == 0:
        return 5.14, 1.0, 0.0
    phi = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(phi)) * math.tan(math.radians(45 + phi_deg / 2)) ** 2
    Nc = (Nq - 1) / math.tan(phi)
    Ngamma = (Nq - 1) * math.tan(math.radians(1.4 * phi_deg))
    return Nc, Nq, Ngamma


def _shape_factors(phi_deg: float, B: float, L: float, Kp: float) -> tuple[float, float, float]:
    Fcs = 1 + 0.2 * Kp * (B / L)
    if phi_deg > 10:
        Fqs = Fgs = 1 + 0.1 * Kp * (B / L)
    else:
        Fqs = Fgs = 1.0
    return Fcs, Fqs, Fgs


def _depth_factors(phi_deg: float, Df: float, B: float, Kp: float) -> tuple[float, float, float]:
    Fcd = 1 + 0.2 * math.sqrt(Kp) * (Df / B)
    if phi_deg > 10:
        Fqd = Fgd = 1 + 0.1 * math.sqrt(Kp) * (Df / B)
    else:
        Fqd = Fgd = 1.0
    return Fcd, Fqd, Fgd


def _inclination_factors(phi_deg: float, beta_deg: float) -> tuple[float, float, float]:
    Fci = Fqi = (1 - beta_deg / 90) ** 2
    if phi_deg > 0:
        Fgi = (1 - beta_deg / phi_deg) ** 2
    else:
        Fgi = 0.0 if beta_deg > 0 else 1.0
    return Fci, Fqi, Fgi


def calculate(inputs: BearingCapacityInput) -> CalcResult:
    c = inputs.cohesion_kpa
    phi_deg = inputs.friction_angle_deg
    gamma = inputs.unit_weight_kn_m3
    B = inputs.width_m
    L = inputs.length_m
    Df = inputs.depth_m
    FS = inputs.factor_of_safety
    beta = inputs.load_inclination_deg

    warnings: list[str] = [
        "Assumes a dry, fully drained soil profile with no groundwater table within "
        "the zone of influence. If groundwater is present at or above founding level, "
        "unit weight terms need adjusting for submerged/buoyant conditions — not "
        "handled by this module.",
        "Ultimate limit state (bearing capacity) only — settlement (serviceability) "
        "is not checked here.",
    ]
    if beta > 0 and phi_deg == 0 and beta != 0:
        warnings.append(
            "Load inclination factor for the gamma term is undefined for phi=0 with "
            "an inclined load; Fgi has been set to 0 (conservative)."
        )
    if Df > B:
        warnings.append(
            f"Depth Df ({Df} m) exceeds width B ({B} m) — Meyerhof's shallow foundation "
            "assumptions become less reliable for deep/pile-like foundations; review "
            "applicability."
        )

    Nc, Nq, Ngamma = _bearing_capacity_factors(phi_deg)
    Kp = math.tan(math.radians(45 + phi_deg / 2)) ** 2

    Fcs, Fqs, Fgs = _shape_factors(phi_deg, B, L, Kp)
    Fcd, Fqd, Fgd = _depth_factors(phi_deg, Df, B, Kp)
    Fci, Fqi, Fgi = _inclination_factors(phi_deg, beta)

    q = gamma * Df  # effective overburden at founding level

    term_c = c * Nc * Fcs * Fcd * Fci
    term_q = q * Nq * Fqs * Fqd * Fqi
    term_gamma = 0.5 * gamma * B * Ngamma * Fgs * Fgd * Fgi

    qu = term_c + term_q + term_gamma
    qnet_u = qu - q
    qnet_all = qnet_u / FS
    qall_gross = qnet_all + q
    Qall = qall_gross * B * L

    terms = [
        Term("Kp (passive coefficient)", Kp, note="tan^2(45 + phi/2)"),
        Term("Nc", Nc, note="bearing capacity factor — cohesion term"),
        Term("Nq", Nq, note="bearing capacity factor — surcharge term"),
        Term("Ngamma", Ngamma, note="bearing capacity factor — unit weight term (Meyerhof)"),
        Term("Fcs", Fcs, note="shape factor — cohesion term"),
        Term("Fqs", Fqs, note="shape factor — surcharge term"),
        Term("Fgs", Fgs, note="shape factor — unit weight term"),
        Term("Fcd", Fcd, note="depth factor — cohesion term"),
        Term("Fqd", Fqd, note="depth factor — surcharge term"),
        Term("Fgd", Fgd, note="depth factor — unit weight term"),
        Term("Fci", Fci, note="inclination factor — cohesion term"),
        Term("Fqi", Fqi, note="inclination factor — surcharge term"),
        Term("Fgi", Fgi, note="inclination factor — unit weight term"),
        Term("q", q, unit="kPa", note="effective overburden at founding level (gamma * Df)"),
        Term("c term", term_c, unit="kPa", note="c * Nc * Fcs * Fcd * Fci"),
        Term("q term", term_q, unit="kPa", note="q * Nq * Fqs * Fqd * Fqi"),
        Term("gamma term", term_gamma, unit="kPa", note="0.5 * gamma * B * Ngamma * Fgs * Fgd * Fgi"),
        Term("qu (gross ultimate)", qu, unit="kPa"),
        Term("qnet(u) (net ultimate)", qnet_u, unit="kPa", note="qu - q"),
        Term("qnet(all) (net allowable)", qnet_all, unit="kPa", note=f"qnet(u) / FS, FS={FS}"),
        Term("qall (gross allowable)", qall_gross, unit="kPa", note="qnet(all) + q"),
    ]

    headline = Term(
        "Allowable bearing pressure (qall)",
        qall_gross,
        unit="kPa",
        note=f"Allowable load capacity Qall = {Qall:.4g} kN for {B}m x {L}m footing",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        method="Meyerhof general bearing capacity equation (shallow foundations)",
        references=[
            "Meyerhof, G.G. (1963). 'Some recent research on the bearing capacity of "
            "foundations.' Canadian Geotechnical Journal.",
            "Das, B.M. 'Principles of Foundation Engineering' — standard reference "
            "formulation for bearing capacity, shape, depth and inclination factors.",
        ],
    )


MODULE = CalcModule(
    key="geotech_bearing_capacity",
    name="Shallow Foundation Bearing Capacity (Meyerhof)",
    discipline="Geotechnical",
    description=(
        "Ultimate and allowable bearing capacity for a shallow strip/rectangular/"
        "square footing, using Meyerhof's general bearing capacity equation with "
        "shape, depth and load-inclination factors."
    ),
    input_model=BearingCapacityInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.geotechnical.bearing_capacity
    example = BearingCapacityInput(
        cohesion_kpa=0,
        friction_angle_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        depth_m=1.0,
        factor_of_safety=3.0,
    )
    result = calculate(example)
    print(f"qall = {result.headline.value:.2f} {result.headline.unit}")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
