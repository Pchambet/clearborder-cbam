#!/usr/bin/env python3
"""Worked example for the README: why the 20 % cap on estimates must be measured on emissions.

An illustrative complex good: 1 t of welded steel tube (CN 7306) made from
1,060 kg of hot-rolled coil bought from two suppliers. Supplier A (electric arc
furnace) shares installation data; supplier B shares nothing, so its coil is
reported with an estimated value. All numbers are illustrative inputs chosen for
readability, not Commission default values.

The script runs the real engine, sweeps the share of coil bought from supplier B,
and writes docs/figures/estimation-cap.png and docs/worked-example.json at the
repository root.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.cbam_engine import MIN_ACTUAL_SHARE, PrecursorData, ProductEmissionData, calculate_see

REPO_ROOT = Path(__file__).resolve().parents[2]
FIGURES = REPO_ROOT / "docs" / "figures"

OUTPUT_KG = 1000.0
DIRECT_EMISSIONS = 120.0  # kg CO2e at the tube mill, installation data
COIL_KG = 1060.0
SEE_SUPPLIER_A = 0.60  # kg CO2e/kg, actual (EAF route)
SEE_SUPPLIER_B = 2.30  # kg CO2e/kg, estimated
BASE_CASE_B_KG = 210.0

INK, TEAL, AMBER, SLATE, GRID = "#0f172a", "#0d9488", "#d97706", "#64748b", "#e2e8f0"


def good(share_b: float) -> ProductEmissionData:
    """The tube when a fraction ``share_b`` of the coil mass comes from supplier B."""
    return ProductEmissionData(
        attr_em=DIRECT_EMISSIONS,
        activity_level=OUTPUT_KG,
        precursors=[
            PrecursorData(COIL_KG * (1 - share_b), SEE_SUPPLIER_A, is_real_data=True),
            PrecursorData(COIL_KG * share_b, SEE_SUPPLIER_B, is_real_data=False),
        ],
    )


def estimated_emission_share(share_b: float) -> float:
    return 1 - calculate_see(good(share_b))["real_data_ratio"]


def breach_point(lo: float = 0.0, hi: float = 1.0) -> float:
    """Smallest supplier-B mass share at which the emissions-based cap is breached (bisection)."""
    cap = 1 - MIN_ACTUAL_SHARE
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if estimated_emission_share(mid) <= cap else (lo, mid)
    return hi


def main() -> None:
    base_share = BASE_CASE_B_KG / COIL_KG
    base = calculate_see(good(base_share))
    breach = breach_point()
    summary = {
        "inputs": {
            "output_kg": OUTPUT_KG,
            "direct_emissions_kg_co2e": DIRECT_EMISSIONS,
            "coil_kg": COIL_KG,
            "see_supplier_a_actual": SEE_SUPPLIER_A,
            "see_supplier_b_estimated": SEE_SUPPLIER_B,
            "supplier_b_kg": BASE_CASE_B_KG,
        },
        "see_kg_co2e_per_kg": base["see_per_kg"],
        "total_embedded_emissions_kg_co2e": base["total_emissions_kg_co2e"],
        "estimated_share_by_mass": round(base_share, 4),
        "estimated_share_by_emissions": round(1 - base["real_data_ratio"], 4),
        "compliant_by_mass": base_share <= 1 - MIN_ACTUAL_SHARE,
        "compliant_by_emissions": base["rule_80_20_compliant"],
        "breach_supplier_b_mass_share": round(breach, 4),
    }

    FIGURES.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "docs" / "worked-example.json").write_text(json.dumps(summary, indent=2) + "\n")

    xs = [i / 1000 for i in range(301)]
    ys = [estimated_emission_share(x) for x in xs]

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
    fig.patch.set_facecolor("white")
    ax.plot([x * 100 for x in xs], [y * 100 for y in ys], color=TEAL, lw=2.4)
    ax.plot([0, 30], [0, 30], color=SLATE, lw=1.6, ls="--")
    ax.axhline(20, color=AMBER, lw=1.4)
    ax.text(0.5, 21, "20 % cap on estimates", color=AMBER, ha="left", va="bottom", fontsize=9)
    ax.text(21, 60, "share of embedded emissions\n(what the regulation caps)", color=TEAL, fontsize=9)
    ax.text(21, 9, "share of precursor mass\n(what the first version checked)", color=SLATE, fontsize=9)

    ax.scatter([breach * 100], [20], color=TEAL, zorder=3, s=28)
    ax.annotate(
        f"breached at {breach * 100:.1f} % of coil mass",
        xy=(breach * 100, 20),
        xytext=(breach * 100 + 1.5, 4),
        fontsize=9,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.8},
    )
    est = summary["estimated_share_by_emissions"] * 100
    ax.scatter([base_share * 100], [est], color=INK, zorder=3, s=28)
    ax.annotate(
        f"{BASE_CASE_B_KG:.0f} kg of 1,060 kg: {base_share * 100:.1f} % by mass,\n{est:.1f} % by emissions",
        xy=(base_share * 100, est),
        xytext=(base_share * 100 + 1.2, est - 13),
        fontsize=9,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.8},
    )

    ax.set_xlim(0, 30)
    ax.set_ylim(0, 75)
    ax.set_xlabel("Coil bought from the supplier without data (% of coil mass)", color=INK)
    ax.set_ylabel("Estimated share (%)", color=INK)
    ax.set_title(
        f"A mass-based check passes a tube whose embedded emissions are {est:.0f} % estimated",
        loc="left",
        fontsize=11,
        color=INK,
    )
    ax.grid(color=GRID, lw=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(SLATE)
    ax.tick_params(colors=SLATE)
    fig.tight_layout()
    fig.savefig(FIGURES / "estimation-cap.png", facecolor="white")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
