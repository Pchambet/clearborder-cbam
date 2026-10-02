"""CBAM embedded-emissions engine (Regulation (EU) 2023/956, Annex IV).

Specific embedded emissions of a good g:

    SEE_g = (AttrEm_g + EE_InpMat) / AL_g
    EE_InpMat = sum_i M_i * SEE_i        (over the relevant precursors i)

The functions here are pure (no I/O, no database) so the arithmetic can be tested
against hand-computed cases and reused by the API, the scripts and the dashboard.

Estimation cap. During the transitional period, Implementing Regulation (EU)
2023/1773 lets a declarant use estimations, including default values, for complex
goods only as long as they stay within 20 % of the good's *total embedded
emissions*. The cap is therefore measured on emissions, not on precursor mass: a
light precursor with a high default SEE can breach it on its own. Direct
(attributed) emissions are installation data and count as actual data.
"""

from dataclasses import dataclass, field

MIN_ACTUAL_SHARE = 0.80  # i.e. estimations may cover at most 20 % of embedded emissions


@dataclass
class PrecursorData:
    """One precursor line of a bill of materials."""

    mass_kg: float
    see_per_kg: float  # specific embedded emissions of the precursor, kg CO2e/kg
    is_real_data: bool  # True = installation data, False = estimate or default value


@dataclass
class ProductEmissionData:
    """Inputs needed to compute the SEE of one good."""

    attr_em: float  # emissions attributed to the production process, kg CO2e
    activity_level: float  # AL_g, mass of good produced, kg
    precursors: list[PrecursorData] = field(default_factory=list)
    installation_id: str | None = None


def calculate_ee_inp_mat(precursors: list[PrecursorData]) -> tuple[float, float, float]:
    """Return (EE_InpMat, emissions from actual data, emissions from estimates), kg CO2e."""
    actual = sum(p.mass_kg * p.see_per_kg for p in precursors if p.is_real_data)
    estimated = sum(p.mass_kg * p.see_per_kg for p in precursors if not p.is_real_data)
    return actual + estimated, actual, estimated


def validate_80_20_rule(actual_emissions: float, total_emissions: float) -> tuple[bool, float]:
    """Check the estimation cap on embedded emissions.

    Returns (compliant, share of total embedded emissions backed by actual data).
    A good with zero embedded emissions has nothing estimated and is compliant.
    """
    if total_emissions <= 0:
        return True, 1.0
    share = actual_emissions / total_emissions
    return share >= MIN_ACTUAL_SHARE, share


def calculate_see(data: ProductEmissionData) -> dict:
    """Compute the specific embedded emissions (SEE) of one good.

    Returns a dict with see_per_kg, ee_inp_mat, attr_em, activity_level,
    total_emissions_kg_co2e, real_data_ratio (share of embedded emissions from
    actual data), rule_80_20_compliant and warnings.
    """
    if data.activity_level <= 0:
        raise ValueError("Activity level (AL_g) must be strictly positive")

    ee_inp_mat, actual_precursors, _ = calculate_ee_inp_mat(data.precursors)
    total = data.attr_em + ee_inp_mat

    warnings: list[str] = []
    compliant, real_data_ratio = True, 1.0
    if data.precursors:  # the estimation cap only concerns complex goods
        compliant, real_data_ratio = validate_80_20_rule(data.attr_em + actual_precursors, total)
        if not compliant:
            warnings.append(
                f"80/20 rule not met: {real_data_ratio * 100:.1f}% of embedded emissions "
                "come from actual data (at least 80% required for complex goods)"
            )

    return {
        "see_per_kg": round(total / data.activity_level, 6),
        "ee_inp_mat": round(ee_inp_mat, 6),
        "attr_em": data.attr_em,
        "activity_level": data.activity_level,
        "rule_80_20_compliant": compliant,
        "real_data_ratio": round(real_data_ratio, 4),
        "warnings": warnings,
        "total_emissions_kg_co2e": round(total, 6),
    }


def calculate_see_recursive(bom_tree: dict) -> dict:
    """Compute SEE for a nested bill of materials.

    A precursor whose ``see_per_kg`` is None takes the SEE computed from its own
    ``nested_bom``; precursors with neither are ignored.

        {"attr_em": float, "activity_level": float,
         "precursors": [{"mass_kg": float, "see_per_kg": float | None,
                         "is_real_data": bool, "nested_bom": dict | None}]}
    """
    precursors = []
    for p in bom_tree.get("precursors", []):
        see_per_kg = p.get("see_per_kg")
        if see_per_kg is None and p.get("nested_bom"):
            see_per_kg = calculate_see_recursive(p["nested_bom"])["see_per_kg"]
        if see_per_kg is not None:
            precursors.append(
                PrecursorData(
                    mass_kg=p["mass_kg"],
                    see_per_kg=see_per_kg,
                    is_real_data=p.get("is_real_data", False),
                )
            )

    return calculate_see(
        ProductEmissionData(
            attr_em=bom_tree.get("attr_em", 0),
            activity_level=bom_tree["activity_level"],
            precursors=precursors,
        )
    )
