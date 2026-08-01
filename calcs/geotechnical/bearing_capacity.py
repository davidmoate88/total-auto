"""
Spread foundation bearing resistance — EN 1997-1 (Eurocode 7) Annex D, using the
UK National Annex's Design Approach 1 (DA1).

*** IMPORTANT — READ BEFORE RELYING ON THIS FOR REAL DESIGN ***
This module implements the Annex D bearing resistance formulae and UK NA DA1
partial factors as commonly reproduced in UK geotechnical design references
(e.g. Bond & Harris, "Decoding Eurocode 7"; ICE/ISE design guidance). It was
NOT built by reading the purchased BS EN 1997-1 standard text directly (that
text isn't available to check against here). In particular the Nγ bearing
capacity factor formula varies between references that are all loosely
"Eurocode-based" (Annex D vs. Vesic 1973 use different coefficients) — the
formula used below is flagged at the point of use. A chartered engineer
should verify every formula and partial factor against the current edition
of EN 1997-1 Annex D and the UK National Annex (and any relevant National
Annex amendments) before this is used for a real calculation submitted for
approval.

Method summary
--------------
Design Approach 1 requires checking BOTH combinations and taking the more
onerous (lower) resulting design bearing resistance:

    DA1-C1 = A1 "+" M1 "+" R1   (factor the actions; soil parameters unfactored)
    DA1-C2 = A2 "+" M2 "+" R1   (soil parameters factored/reduced; actions less
                                  onerous than C1, except R1 = 1.0 for spread
                                  foundations under UK NA in both combinations)

Bearing resistance (drained, Annex D):

    R/A' = c'*Nc*bc*sc*ic + q'*Nq*bq*sq*iq + 0.5*gamma'*B'*Ngamma*bgamma*sgamma*igamma

Bearing resistance (undrained, Annex D):

    R/A' = (pi + 2)*cu*bc*sc*ic + q

Where B', L', A' = B'*L' are the *effective* width/length/area accounting for
load eccentricity (Meyerhof's effective area method), and b/s/i are base
inclination, shape, and load inclination factors respectively.

Known simplifications / not implemented (see Warnings in the result):
- No depth factor — Annex D's bearing resistance formula does not include one
  (this is a deliberate, well-documented feature of Annex D, not an omission
  on our part — depth effects above founding level are treated as unreliable
  unless separately justified).
- Level ground assumed (no ground/slope inclination factors).
- Horizontal load is assumed to act parallel to the B' (width) direction only.
- Water table handled as a single boundary within a single assumed soil unit
  weight profile above founding level (not a multi-layer profile — see the
  ground-model interpretation module for multi-layer overburden handling).
- Settlement (SLS) is not checked — this is a ULS bearing resistance check only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from core.calc_base import CalcModule, CalcResult, Term

WATER_UNIT_WEIGHT_KN_M3 = 9.81


@dataclass(frozen=True)
class PartialFactorSet:
    """One DA1 combination's partial factors (UK National Annex to EN 1997-1)."""

    label: str
    gamma_G: float  # on unfavourable permanent actions (Set A)
    gamma_Q: float  # on unfavourable variable actions (Set A)
    gamma_phi: float  # on tan(phi'), Set M
    gamma_c: float  # on c', Set M
    gamma_cu: float  # on cu, Set M
    gamma_R: float = 1.0  # Set R1 — 1.0 for spread foundations, both combinations, UK NA


DA1_C1 = PartialFactorSet("DA1-C1 (A1+M1+R1)", gamma_G=1.35, gamma_Q=1.5, gamma_phi=1.0, gamma_c=1.0, gamma_cu=1.0)
DA1_C2 = PartialFactorSet("DA1-C2 (A2+M2+R1)", gamma_G=1.0, gamma_Q=1.3, gamma_phi=1.25, gamma_c=1.25, gamma_cu=1.4)


class BearingResistanceInput(BaseModel):
    analysis_type: Literal["drained", "undrained"] = Field(
        ..., description="'drained' uses c'/phi' (effective stress); 'undrained' uses cu (total stress)."
    )

    # Drained parameters (characteristic values)
    cohesion_c_prime_kpa: Optional[float] = Field(
        None, ge=0, description="Characteristic effective cohesion, c' (kPa). Drained analysis only."
    )
    friction_angle_phi_prime_deg: Optional[float] = Field(
        None, gt=0, le=45, description="Characteristic effective friction angle, phi' (degrees). Drained analysis only."
    )

    # Undrained parameter (characteristic value)
    undrained_shear_strength_cu_kpa: Optional[float] = Field(
        None, gt=0, description="Characteristic undrained shear strength, cu (kPa). Undrained analysis only."
    )

    unit_weight_kn_m3: float = Field(..., gt=0, description="Characteristic bulk unit weight, gamma (kN/m^3).")
    water_table_depth_m: Optional[float] = Field(
        None, ge=0, description="Depth to water table (m bgl). Omit if no water table above founding level."
    )

    width_m: float = Field(..., gt=0, description="Footing width, B (m).")
    length_m: float = Field(..., gt=0, description="Footing length, L (m). Use L = B for a square footing.")
    depth_m: float = Field(..., ge=0, description="Founding depth, D (m).")

    eccentricity_b_m: float = Field(0.0, ge=0, description="Load eccentricity in the B direction, eB (m).")
    eccentricity_l_m: float = Field(0.0, ge=0, description="Load eccentricity in the L direction, eL (m).")
    base_inclination_deg: float = Field(0.0, ge=0, lt=45, description="Footing base inclination from horizontal, alpha (degrees).")

    characteristic_permanent_load_kn: float = Field(
        0.0, ge=0, description="Characteristic permanent vertical action, Gk (kN). 0 = resistance-only, no verification."
    )
    characteristic_variable_load_kn: float = Field(
        0.0, ge=0, description="Characteristic variable vertical action, Qk (kN)."
    )
    characteristic_horizontal_load_kn: float = Field(
        0.0, ge=0, description="Characteristic horizontal action, Hk (kN), assumed parallel to B."
    )
    horizontal_load_is_variable: bool = Field(
        True, description="Classify Hk as a variable action (True, e.g. wind) or permanent (False)."
    )

    @model_validator(mode="after")
    def _check_consistency(self) -> "BearingResistanceInput":
        if self.length_m < self.width_m:
            raise ValueError("length_m must be >= width_m — by convention B is the shorter side.")
        if self.analysis_type == "drained":
            if self.cohesion_c_prime_kpa is None or self.friction_angle_phi_prime_deg is None:
                raise ValueError("Drained analysis requires cohesion_c_prime_kpa and friction_angle_phi_prime_deg.")
        else:
            if self.undrained_shear_strength_cu_kpa is None:
                raise ValueError("Undrained analysis requires undrained_shear_strength_cu_kpa.")
        if self.eccentricity_b_m * 2 >= self.width_m:
            raise ValueError("eccentricity_b_m too large — effective width B' = B - 2*eB would be <= 0.")
        if self.eccentricity_l_m * 2 >= self.length_m:
            raise ValueError("eccentricity_l_m too large — effective length L' = L - 2*eL would be <= 0.")
        return self


def _bearing_capacity_factors(phi_deg: float) -> tuple[float, float, float]:
    """
    Nc, Nq, Ngamma per EN 1997-1 Annex D.

    Nq, Nc are the standard Prandtl/Reissner closed forms used near-universally
    across bearing capacity methods. Ngamma = 2*(Nq-1)*tan(phi') is the specific
    form commonly reproduced for Annex D — NOTE this differs from Vesic's
    original (1973) Ngamma = 2*(Nq+1)*tan(phi') and from Meyerhof/Hansen forms.
    Verify against the current EN 1997-1 Annex D text (see module docstring).
    """
    phi = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(phi)) * math.tan(math.radians(45 + phi_deg / 2)) ** 2
    Nc = (Nq - 1) / math.tan(phi)
    Ngamma = 2 * (Nq - 1) * math.tan(phi)
    return Nc, Nq, Ngamma


def _effective_overburden_kpa(gamma: float, depth_m: float, water_table_depth_m: Optional[float]) -> float:
    """Single-layer effective overburden at founding depth, accounting for one water table boundary."""
    if water_table_depth_m is None or water_table_depth_m >= depth_m:
        return gamma * depth_m
    dry_thickness = water_table_depth_m
    submerged_thickness = depth_m - water_table_depth_m
    gamma_sub = max(gamma - WATER_UNIT_WEIGHT_KN_M3, 0.0)
    return gamma * dry_thickness + gamma_sub * submerged_thickness


def _total_overburden_kpa(gamma: float, depth_m: float) -> float:
    """Total (unfactored-for-buoyancy) overburden — used as the 'q' term in the undrained formula."""
    return gamma * depth_m


def _compute_combination(
    inputs: BearingResistanceInput,
    factors: PartialFactorSet,
) -> tuple[float, dict, list[str], list[Term]]:
    """
    Run one DA1 combination. Returns (design bearing resistance Rd in kPa,
    dict of labelled intermediate values for the report, warnings raised).
    """
    warnings: list[str] = []
    B = inputs.width_m
    L = inputs.length_m
    D = inputs.depth_m

    B_eff = B - 2 * inputs.eccentricity_b_m
    L_eff = L - 2 * inputs.eccentricity_l_m
    A_eff = B_eff * L_eff
    alpha = math.radians(inputs.base_inclination_deg)

    # Design actions for this combination.
    Vd = factors.gamma_G * inputs.characteristic_permanent_load_kn + factors.gamma_Q * inputs.characteristic_variable_load_kn
    if inputs.horizontal_load_is_variable:
        Hd = factors.gamma_Q * inputs.characteristic_horizontal_load_kn
    else:
        Hd = factors.gamma_G * inputs.characteristic_horizontal_load_kn

    values: dict[str, float] = {
        "B_eff": B_eff, "L_eff": L_eff, "A_eff": A_eff, "Vd": Vd, "Hd": Hd,
    }

    if inputs.analysis_type == "undrained":
        cu_d = inputs.undrained_shear_strength_cu_kpa / factors.gamma_cu
        q = _total_overburden_kpa(inputs.unit_weight_kn_m3, D)

        sc = 1 + 0.2 * (B_eff / L_eff)
        bc = 1 - (2 * alpha) / (math.pi + 2)

        if Vd > 0 and A_eff * cu_d > 0:
            base = 1 - Hd / (A_eff * cu_d)
            if base < 0:
                warnings.append(
                    "Horizontal action exceeds the assumed sliding/inclination capacity "
                    "(undrained ic base term went negative) — clipped to 0. This likely means "
                    "sliding resistance (a separate ULS check, not performed by this module) "
                    "governs, not bearing resistance."
                )
                base = 0.0
            ic = 0.5 * (1 + math.sqrt(base))
        else:
            ic = 1.0

        Rd = (math.pi + 2) * cu_d * bc * sc * ic + q

        values.update({"cu_d": cu_d, "q": q, "sc": sc, "bc": bc, "ic": ic})
        method_terms = [
            Term("cu,d (design undrained shear strength)", cu_d, unit="kPa", note=f"cu,k / {factors.gamma_cu}"),
            Term("q (total overburden at founding level)", q, unit="kPa"),
            Term("sc (shape factor)", sc, note="1 + 0.2*(B'/L')"),
            Term("bc (base inclination factor)", bc),
            Term("ic (load inclination factor)", ic),
        ]
    else:
        phi_k = inputs.friction_angle_phi_prime_deg
        phi_d_rad = math.atan(math.tan(math.radians(phi_k)) / factors.gamma_phi)
        phi_d_deg = math.degrees(phi_d_rad)
        c_d = inputs.cohesion_c_prime_kpa / factors.gamma_c

        Nc, Nq, Ngamma = _bearing_capacity_factors(phi_d_deg)
        q_prime = _effective_overburden_kpa(inputs.unit_weight_kn_m3, D, inputs.water_table_depth_m)

        sq = 1 + (B_eff / L_eff) * math.sin(phi_d_rad)
        sgamma = 1 - 0.3 * (B_eff / L_eff)
        sc = (sq * Nq - 1) / (Nq - 1) if Nq != 1 else 1.0

        bq = bgamma = (1 - alpha * math.tan(phi_d_rad)) ** 2
        bc = bq - (1 - bq) / (Nc * math.tan(phi_d_rad)) if phi_d_rad != 0 else 1.0

        m = (2 + (B_eff / L_eff)) / (1 + (B_eff / L_eff))
        denom = Vd + A_eff * c_d / math.tan(phi_d_rad) if phi_d_rad != 0 else Vd
        if Vd > 0 and denom > 0:
            base = 1 - Hd / denom
            if base < 0:
                warnings.append(
                    "Horizontal action exceeds the assumed sliding/inclination capacity "
                    "(drained iq/igamma base term went negative) — clipped to 0. This likely "
                    "means sliding resistance (a separate ULS check, not performed by this "
                    "module) governs, not bearing resistance."
                )
                base = 0.0
            iq = base**m
            igamma = base ** (m + 1)
            ic = iq - (1 - iq) / (Nc * math.tan(phi_d_rad)) if phi_d_rad != 0 else 1.0
        else:
            iq = igamma = ic = 1.0

        term_c = c_d * Nc * bc * sc * ic
        term_q = q_prime * Nq * bq * sq * iq
        term_gamma = 0.5 * inputs.unit_weight_kn_m3 * B_eff * Ngamma * bgamma * sgamma * igamma
        Rd = term_c + term_q + term_gamma

        values.update({
            "phi_d_deg": phi_d_deg, "c_d": c_d, "Nc": Nc, "Nq": Nq, "Ngamma": Ngamma,
            "q_prime": q_prime, "sq": sq, "sgamma": sgamma, "sc": sc,
            "bq": bq, "bgamma": bgamma, "bc": bc, "iq": iq, "igamma": igamma, "ic": ic,
        })
        method_terms = [
            Term("phi'_d (design friction angle)", phi_d_deg, unit="deg", note=f"atan(tan(phi'_k)/{factors.gamma_phi})"),
            Term("c'_d (design cohesion)", c_d, unit="kPa", note=f"c'_k / {factors.gamma_c}"),
            Term("Nc, Nq, Ngamma", Nq, note=f"Nc={Nc:.3g}, Nq={Nq:.3g}, Ngamma={Ngamma:.3g}"),
            Term("q' (effective overburden)", q_prime, unit="kPa"),
            Term("Shape factors sc/sq/sgamma", sc, note=f"sc={sc:.3g}, sq={sq:.3g}, sgamma={sgamma:.3g}"),
            Term("Base inclination bc/bq/bgamma", bc, note=f"bc={bc:.3g}, bq={bq:.3g}, bgamma={bgamma:.3g}"),
            Term("Load inclination ic/iq/igamma", ic, note=f"ic={ic:.3g}, iq={iq:.3g}, igamma={igamma:.3g}"),
        ]

    values["Rd"] = Rd
    return Rd, values, warnings, method_terms


def calculate(inputs: BearingResistanceInput) -> CalcResult:
    warnings: list[str] = [
        "Verify all Annex D formulae and DA1 partial factors used here against the current "
        "edition of EN 1997-1 Annex D and the UK National Annex before relying on this for a "
        "real design submission — see the module docstring for specifics (notably the Ngamma "
        "formula, which varies between 'Eurocode-based' references).",
        "No depth factor is applied (Annex D does not include one). Level ground and horizontal "
        "footing base assumed unless base_inclination_deg is set. Horizontal load assumed to act "
        "parallel to the B direction. Settlement (SLS) is not checked — ULS bearing resistance only.",
    ]
    if inputs.depth_m > inputs.width_m:
        warnings.append(
            f"Depth D ({inputs.depth_m} m) exceeds width B ({inputs.width_m} m) — shallow "
            "foundation assumptions become less reliable for deep/pile-like foundations."
        )

    Rd_c1, values_c1, warn_c1, terms_c1 = _compute_combination(inputs, DA1_C1)
    Rd_c2, values_c2, warn_c2, terms_c2 = _compute_combination(inputs, DA1_C2)
    warnings.extend(warn_c1)
    warnings.extend(warn_c2)

    governing_label = "DA1-C1" if Rd_c1 <= Rd_c2 else "DA1-C2"
    Rd_governing = min(Rd_c1, Rd_c2)

    def _prefix(label_terms: list[Term], prefix: str) -> list[Term]:
        return [Term(f"{prefix} {t.label}", t.value, t.unit, t.note) for t in label_terms]

    terms: list[Term] = []
    terms.extend(_prefix(terms_c1, "[DA1-C1, unfactored soil params]"))
    terms.append(Term("[DA1-C1] Rd", Rd_c1, unit="kPa"))
    terms.extend(_prefix(terms_c2, "[DA1-C2, factored/reduced soil params]"))
    terms.append(Term("[DA1-C2] Rd", Rd_c2, unit="kPa"))

    Vd_governing = values_c1["Vd"] if governing_label == "DA1-C1" else values_c2["Vd"]
    A_eff_governing = values_c1["A_eff"] if governing_label == "DA1-C1" else values_c2["A_eff"]
    if Vd_governing > 0:
        utilisation = Vd_governing / (A_eff_governing * Rd_governing)
        terms.append(
            Term(
                "Utilisation (governing combination)",
                utilisation,
                note=f"Vd / (A'*Rd) — {'PASS' if utilisation <= 1.0 else 'FAIL'} (<=1.0 required)",
            )
        )
        if utilisation > 1.0:
            warnings.append(
                f"Governing combination ({governing_label}) FAILS: design vertical action exceeds "
                "design bearing resistance. Increase footing size or review loads/ground parameters."
            )

    headline = Term(
        f"Design bearing resistance Rd ({governing_label} governs)",
        Rd_governing,
        unit="kPa",
        note="Lower of DA1-C1 and DA1-C2 — the governing case per Design Approach 1.",
    )

    return CalcResult(
        headline=headline,
        terms=terms,
        warnings=warnings,
        method="EN 1997-1 Annex D bearing resistance, UK NA Design Approach 1 (DA1-C1 & DA1-C2)",
        references=[
            "BS EN 1997-1:2004+A1:2013, Eurocode 7: Geotechnical design — Part 1: General rules, Annex D.",
            "UK National Annex to BS EN 1997-1:2004+A1:2013.",
            "Bond, A. & Harris, A., 'Decoding Eurocode 7' — widely-used secondary reference for the "
            "Annex D formulae and DA1 worked application in UK practice.",
        ],
    )


MODULE = CalcModule(
    key="geotech_bearing_resistance_ec7",
    name="Spread Foundation Bearing Resistance (EN 1997-1 Annex D, UK NA, DA1)",
    discipline="Geotechnical",
    description=(
        "Design bearing resistance for a shallow/spread footing to EN 1997-1 Annex D, "
        "checked under both DA1 combinations (UK National Annex) with shape, base "
        "inclination, and load inclination factors, and effective area for eccentric loads."
    ),
    input_model=BearingResistanceInput,
    calculate=calculate,
)


if __name__ == "__main__":
    # Quick manual run: python3 -m calcs.geotechnical.bearing_capacity
    example = BearingResistanceInput(
        analysis_type="drained",
        cohesion_c_prime_kpa=0,
        friction_angle_phi_prime_deg=30,
        unit_weight_kn_m3=18,
        width_m=1.5,
        length_m=1.5,
        depth_m=1.0,
        characteristic_permanent_load_kn=300,
        characteristic_variable_load_kn=100,
    )
    result = calculate(example)
    print(f"Rd = {result.headline.value:.2f} {result.headline.unit} ({result.headline.note})")
    for t in result.terms:
        print(" ", t.formatted())
    for w in result.warnings:
        print("WARNING:", w)
