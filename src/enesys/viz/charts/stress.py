"""Stresstest-Hochlauf-Chart — Core-Visual, Sicherheits-Anker.

2×3-Grid pro Pfad: Dunkelflauten-Coverage 2026–2055 (Stack der Backup-
Schichten, schwarze gestrichelte Linie für Spitzenbedarf, rot-schraffierter
Bereich für Defizit). Datenpfad nutzt ``winter_stress_balance`` aus
``enesys.extensions.winter_stress``.

Stack-Reihenfolge pro Pfad folgt der ``PATH_POLICY.dispatch_priority``;
``gas_h2ready`` wird brennstoff-gewichtet (Erdgas vs. H₂) in zwei Sub-
Schichten gesplittet. Default-Fallback (kein Brennstoff dispatched) ist
pfad-spezifisch: H₂-Pfade fallen auf H₂, sonst auf Erdgas.

Branding:
- ``variant="embedded"`` — kein Titel im Bild (umgebende Caption übernimmt)
- ``variant="epub"`` — wie embedded, niedrigere DPI
- ``variant="standalone"`` — Titel + Untertitel + optionaler Brand-Footer
- ``variant="web"`` — SVG-Output
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from enesys.core.fuel import split_gas_h2ready_by_fuel
from enesys.viz.charts._helpers import Variant, add_oss_footer, dpi_for_variant
from enesys.viz.matplotlib_style import (
    PRINT_FONT_SIZE_ANNOT,
    PRINT_FONT_SIZE_LEGEND,
    apply_print_style,
)
from enesys.viz.theme import (
    MENGENBILANZ_SCHICHT_COLORS,
    MENGENBILANZ_SCHICHT_LABELS,
    PATH_COLORS,
    PATH_LABELS,
)

if TYPE_CHECKING:
    from enesys.viz.brand import BrandConfig


GRID_ORDER: tuple[tuple[str, ...], ...] = (
    ("weiterso", "ee_gas", "kkw_gas"),
    ("bestand", "ee_h2", "kkw_h2"),
)

STUETZJAHRE: tuple[int, ...] = tuple(range(2026, 2056, 2))

# Stress-Schicht-Liste — Stack-Reihenfolge wird pro Pfad aus der
# Modell-dispatch_priority abgeleitet (siehe ``_stress_order_from_model``).
STRESS_LAYER_ORDER: tuple[str, ...] = (
    "wasser",
    "kkw",
    "ee_supply",
    "bio",
    "battery",
    "importe",
    "kohle",
    "erdgas_bestand",
    "gas_h2ready_erdgas",
    "gas_h2ready_h2",
    "dsm",
    "strategische_reserve",
)

_STRESS_LAYER_TECH_IDS: dict[str, tuple[str, ...]] = {
    "wasser": ("wasser",),
    "kkw": ("kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"),
    "ee_supply": ("pv", "wind_onshore", "wind_offshore"),
    "bio": ("bio",),
    "battery": ("battery",),
    "dsm": ("dsm",),
    "kohle": ("kohle",),
    "erdgas_bestand": ("erdgas_bestand",),
    "importe": ("importe",),
    "strategische_reserve": ("strategische_reserve",),
}
_STRESS_TECH_TO_LAYER: dict[str, str] = {
    tid: layer for layer, tids in _STRESS_LAYER_TECH_IDS.items() for tid in tids
}

STRESS_LAYER_SOURCE: dict[str, str] = {
    "wasser": "wasser",
    "ee_supply": "_ee_supply",
    "battery": "_battery",
    "dsm": "dsm",
    "kkw": "_kkw_total",
    "bio": "bio",
    "kohle": "kohle",
    "erdgas_bestand": "erdgas_bestand",
    "gas_h2ready_erdgas": "gas_h2ready_erdgas",
    "gas_h2ready_h2": "gas_h2ready_h2",
    "importe": "importe",
    "strategische_reserve": "strategische_reserve",
}

_STRESS_TO_MENGENBILANZ_KEY: dict[str, str] = {
    "wasser": "hydro",
    "ee_supply": "ee_supply",
    "battery": "battery",
    "dsm": "dsm",
    "kkw": "kkw",
    "bio": "biomasse",
    "kohle": "kohle",
    "erdgas_bestand": "erdgas_bestand",
    "gas_h2ready_erdgas": "gas_h2ready_erdgas",
    "gas_h2ready_h2": "gas_h2ready_h2",
    "importe": "importe",
    "strategische_reserve": "strategische_reserve",
}
STRESS_LAYER_LABELS: dict[str, str] = {
    k: MENGENBILANZ_SCHICHT_LABELS[v] for k, v in _STRESS_TO_MENGENBILANZ_KEY.items()
}
STRESS_LAYER_COLORS: dict[str, str] = {
    k: MENGENBILANZ_SCHICHT_COLORS[v] for k, v in _STRESS_TO_MENGENBILANZ_KEY.items()
}


@dataclass(frozen=True)
class PathStress:
    """Stress-Daten eines Pfads über die Stützjahre (alle Werte in GW)."""

    peak_demand_gw: list[float]
    jahres_demand_twh: list[float]
    coverage: dict[str, list[float]]
    deficit_gw: list[float]


@dataclass(frozen=True)
class StressRampupData:
    """Stresstest-Hochlauf-Daten pro Pfad."""

    years: tuple[int, ...]
    path_stress: dict[str, PathStress]
    camp: str


def _stress_order_from_model(path_id: str) -> list[str]:
    """Stack-Reihenfolge für Stress-Chart aus ``PATH_POLICY.dispatch_priority``.

    ``gas_h2ready`` wird in zwei Sub-Schichten (Erdgas + H₂) gesplittet.
    """
    from enesys.core.inventories import PATH_POLICY

    policy = PATH_POLICY[path_id]
    seen: set[str] = set()
    order: list[str] = []
    for tech_id in policy.dispatch_priority:
        if tech_id == "gas_h2ready":
            for sub in ("gas_h2ready_erdgas", "gas_h2ready_h2"):
                if sub not in seen:
                    order.append(sub)
                    seen.add(sub)
            continue
        layer = _STRESS_TECH_TO_LAYER.get(tech_id)
        if layer is None or layer in seen:
            continue
        order.append(layer)
        seen.add(layer)
    return order


def collect_path_stress(
    path_id: str, *, camp: str = "neutral_default", param_set: str | None = None
) -> PathStress:
    """Sammelt Stress-Coverage pro Stützjahr für einen Pfad.

    Greedy-Stack: pro Schicht wird nur so viel gestapelt wie noch zum Decken
    des Spitzenbedarfs fehlt — der Stack zeigt eine Versorgungs-Mengen-Bilanz,
    nicht die verfügbare Reserve.
    """
    from enesys.core.demand import Demand
    from enesys.core.inventories import PATH_POLICY
    from enesys.core.inventories.demand_curves import realgrad_hochlauf_skalierung
    from enesys.extensions.winter_stress import (
        BIOMASS_FLEX_GW,
        lole_p95_winter_stress_params,
        winter_stress_balance,
    )

    demand = Demand()
    # Chart-Default: LOLE-P95 (BMWK-Reliability-Norm 2,77 h/a, EU-VO
    # 2019/943 Art. 25; 10-Tage-DKF, PV 3 % / Wind 8 % CF, 97 % Backup,
    # 2 Events).
    ws = lole_p95_winter_stress_params()

    peak_demand_gw: list[float] = []
    jahres_demand_twh: list[float] = []
    coverage: dict[str, list[float]] = {s: [0.0] * len(STUETZJAHRE) for s in STRESS_LAYER_ORDER}
    deficit_gw: list[float] = []

    for idx, year in enumerate(STUETZJAHRE):
        elec_skal = realgrad_hochlauf_skalierung(path_id, year)
        results = winter_stress_balance(
            year,
            demand,
            camp,
            paths=(path_id,),
            ws=ws,
            electrification_scaling=elec_skal,
            param_set=param_set,
        )
        if path_id not in results:
            peak_demand_gw.append(0.0)
            jahres_demand_twh.append(0.0)
            deficit_gw.append(0.0)
            continue
        r = results[path_id]
        peak_demand_gw.append(r.peak_demand_gw)
        jahres_demand_twh.append(r.path_result.demand_twh)

        gas_h2ready_total = r.backup_by_tech_gw.get("gas_h2ready", 0.0)
        # Pfad-spez. Default für den Fall ohne Brennstoff-Verbrauch:
        # H₂-Pfade fallen auf H₂, sonst auf Erdgas.
        policy = PATH_POLICY[path_id]
        ambition = (
            policy.default_policy.h2_program_ambition if policy.default_policy else "gedämpft"
        )
        gas_h2_erdgas, gas_h2_h2 = split_gas_h2ready_by_fuel(
            gas_h2ready_total,
            r.path_result.fuel_used,
            h2_default_fallback=(ambition == "voll"),
        )

        raw_values: dict[str, float] = {
            "wasser": r.backup_by_tech_gw.get("wasser", 0.0),
            "_ee_supply": r.ee_supply_gw,
            "_battery": 0.0,
            "dsm": r.backup_by_tech_gw.get("dsm", 0.0),
            "_kkw_total": (
                r.backup_by_tech_gw.get("kkw_bestand", 0.0)
                + r.backup_by_tech_gw.get("kkw_neubau_epr", 0.0)
                + r.backup_by_tech_gw.get("kkw_neubau_smr", 0.0)
            ),
            "bio": r.backup_by_tech_gw.get("bio", 0.0),
            "kohle": r.backup_by_tech_gw.get("kohle", 0.0),
            "erdgas_bestand": r.backup_by_tech_gw.get("erdgas_bestand", 0.0),
            "gas_h2ready_erdgas": gas_h2_erdgas,
            "gas_h2ready_h2": gas_h2_h2,
            "importe": r.backup_by_tech_gw.get("importe", 0.0),
        }
        tech_sum = sum(r.backup_by_tech_gw.values())
        bat_estimate = max(0.0, r.backup_total_gw - tech_sum - BIOMASS_FLEX_GW)
        raw_values["_battery"] = bat_estimate

        remaining = r.peak_demand_gw
        for layer in STRESS_LAYER_ORDER:
            source = STRESS_LAYER_SOURCE[layer]
            available = raw_values.get(source, 0.0)
            contribution = min(available, remaining)
            coverage[layer][idx] = contribution
            remaining -= contribution
            if remaining <= 0:
                remaining = 0.0
        deficit_gw.append(remaining)

    return PathStress(
        peak_demand_gw=peak_demand_gw,
        jahres_demand_twh=jahres_demand_twh,
        coverage=coverage,
        deficit_gw=deficit_gw,
    )


def compute_stress_rampup_data(
    *,
    camp: str = "neutral_default",
    param_set: str | None = None,
) -> StressRampupData:
    """Sammelt Stress-Coverage für alle sechs Pfade aus dem 2×3-Grid.

    ``param_set`` lädt ein externes Annahmen-Substrat (z. B. ``"ariadne_pypsa"``).
    """
    path_stress: dict[str, PathStress] = {}
    for row in GRID_ORDER:
        for path_id in row:
            path_stress[path_id] = collect_path_stress(path_id, camp=camp, param_set=param_set)
    return StressRampupData(years=STUETZJAHRE, path_stress=path_stress, camp=camp)


def _plot_path_subplot(
    ax: Axes,
    ax2: Axes,
    years: list[int],
    stress: PathStress,
    path_id: str,
) -> None:
    path_layers = _stress_order_from_model(path_id)
    bottom = np.zeros(len(years))
    for layer in path_layers:
        values = np.array(stress.coverage[layer])
        if values.sum() < 0.5:
            continue
        ax.bar(
            years,
            values,
            bottom=bottom,
            label=STRESS_LAYER_LABELS[layer],
            color=STRESS_LAYER_COLORS[layer],
            alpha=0.85,
            width=1.5,
            linewidth=0,
        )
        bottom += values

    ax.plot(
        years,
        stress.peak_demand_gw,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="Spitzenbedarf (Dunkelflaute)",
    )

    for x, b, d in zip(years, bottom, stress.deficit_gw, strict=True):
        if d > 0.1:
            ax.bar(
                [x],
                [d],
                bottom=[b],
                color="none",
                edgecolor="red",
                hatch="///",
                width=1.5,
                linewidth=0.6,
            )

    # rechte Y-Achse bleibt leer: Jahres-TWh gehören semantisch ins
    # Mix-Chart, nicht in den Stresstest.
    ax2.set_yticks([])

    label = PATH_LABELS.get(path_id, path_id)
    color = PATH_COLORS.get(path_id, "black")
    ax.set_title(label, fontsize=PRINT_FONT_SIZE_ANNOT + 2, color=color, fontweight="bold")

    ax.set_ylim(0, 160)
    ax.set_xlim(2024, 2056)
    ax.grid(alpha=0.25, axis="y")
    ax.set_xticks([2026, 2030, 2035, 2040, 2045, 2050, 2055])


def render_stress_rampup_grid(
    data: StressRampupData,
    out_path: Path | str,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
) -> None:
    """Rendert das 2×3-Grid Stresstest-Hochlauf 2026–2055 pro Pfad."""
    apply_print_style()

    years = list(data.years)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    axes2 = [[ax.twinx() for ax in row] for row in axes]

    for r, row in enumerate(GRID_ORDER):
        for c, path_id in enumerate(row):
            ax = axes[r, c]
            ax2 = axes2[r][c]
            _plot_path_subplot(ax, ax2, years, data.path_stress[path_id], path_id)
            if c == 0:
                ax.set_ylabel("GW (Dunkelflauten-Mittel)", fontsize=PRINT_FONT_SIZE_ANNOT)
            if r == 1:
                ax.set_xlabel("Jahr", fontsize=PRINT_FONT_SIZE_ANNOT)

    seen: set[str] = set()
    legend_h: list = []
    legend_l: list[str] = []
    for ax in axes.flat:
        for h, lbl in zip(*ax.get_legend_handles_labels(), strict=False):
            if lbl not in seen:
                seen.add(lbl)
                legend_h.append(h)
                legend_l.append(lbl)
    legend_h.append(mpatches.Patch(facecolor="none", edgecolor="red", hatch="///"))
    legend_l.append("Defizit")

    fig.legend(
        legend_h,
        legend_l,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=6,
        fontsize=PRINT_FONT_SIZE_LEGEND,
        frameon=False,
    )

    if variant == "standalone" and title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.995)
        if subtitle:
            fig.text(0.5, 0.955, subtitle, fontsize=11, color="#444", ha="center", style="italic")

    if variant == "standalone" and brand is not None:
        from enesys.viz.brand import add_brand_footer

        add_brand_footer(fig, brand)

    plt.tight_layout(rect=(0, 0.06, 1, 0.96 if variant == "standalone" and title else 1.0))
    add_oss_footer(fig)

    out_path = Path(out_path)
    dpi = dpi_for_variant(variant)
    if variant == "web":
        if out_path.suffix.lower() != ".svg":
            out_path = out_path.with_suffix(".svg")
        fig.savefig(out_path, bbox_inches="tight")
    else:
        if out_path.suffix.lower() != ".png":
            out_path = out_path.with_suffix(".png")
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
