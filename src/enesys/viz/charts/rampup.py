"""Mix-Hochlauf-Chart — Core-Visual, Hochlauf-Anker.

2×3-Grid pro Pfad: jährliche Stromerzeugungs-Mengen 2026–2055 nach Schicht
(PV, Wind onshore/offshore, Wasserkraft, Biomasse, Batterie/DSM, Importe,
KKW, Kohle, Erdgas-Bestand, gas_h2ready aufgeteilt nach Brennstoff, strate-
gische Reserve). Strombedarf als gestrichelte schwarze Linie.

Stack-Reihenfolge pro Pfad folgt der ``PATH_POLICY.dispatch_priority``;
``gas_h2ready`` wird brennstoff-gewichtet (Erdgas vs. H₂) in zwei Sub-
Schichten gesplittet, damit der H₂-Einsatz in den H₂-Pfaden grafisch
unterscheidbar bleibt.

Branding:
- ``variant="embedded"`` — kein Titel im Bild (umgebende Caption übernimmt)
- ``variant="epub"`` — wie standalone, niedrigere DPI
- ``variant="standalone"`` — Titel + Untertitel + optionaler Brand-Footer
- ``variant="web"`` — SVG-Output
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


# Pfad-Reihenfolge im Grid (Zeile 1: WEITER-SO + GAS-Pfade,
# Zeile 2: BESTAND + H2-Pfade).
GRID_ORDER: tuple[tuple[str, ...], ...] = (
    ("weiterso", "ee_gas", "kkw_gas"),
    ("bestand", "ee_h2", "kkw_h2"),
)

# Stützjahre alle 2 Jahre. Feinere Auflösung zeigt Kohle-Phaseout-Dynamik
# und KKW-Hochlauf nach Lager-Startjahr besser.
STUETZJAHRE: tuple[int, ...] = tuple(range(2026, 2056, 2))

# Tech-Mapping pro Schicht. ``gas_h2ready`` wird brennstoff-gewichtet
# in zwei Sub-Schichten gesplittet (``gas_h2ready_erdgas`` und
# ``gas_h2ready_h2``), damit der H₂-Einsatz in den H₂-Pfaden grafisch
# unterscheidbar bleibt.
LAYER_TECH_IDS: dict[str, tuple[str, ...]] = {
    "pv": ("pv",),
    "wind_on": ("wind_onshore",),
    "wind_off": ("wind_offshore",),
    "biomasse": ("bio",),
    "hydro": ("wasser",),
    "battery": ("battery",),
    "dsm": ("dsm",),
    "importe": ("importe",),
    "kkw": ("kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"),
    "kohle": ("kohle",),
    "erdgas_bestand": ("erdgas_bestand",),
    "gas_h2ready_erdgas": ("gas_h2ready",),
    "gas_h2ready_h2": ("gas_h2ready",),
    "strategische_reserve": ("strategische_reserve",),
}

# Inverse Map: Tech-ID → Schicht-Key. gas_h2ready zeigt auf die
# erdgas-Sub-Schicht; die h2-Sub-Schicht wird im Sammler logisch ergänzt.
_TECH_TO_LAYER: dict[str, str] = {
    "pv": "pv",
    "wind_onshore": "wind_on",
    "wind_offshore": "wind_off",
    "bio": "biomasse",
    "wasser": "hydro",
    "battery": "battery",
    "dsm": "dsm",
    "importe": "importe",
    "kkw_bestand": "kkw",
    "kkw_neubau_epr": "kkw",
    "kkw_neubau_smr": "kkw",
    "kohle": "kohle",
    "erdgas_bestand": "erdgas_bestand",
    "gas_h2ready": "gas_h2ready_erdgas",
    "strategische_reserve": "strategische_reserve",
}

LAYER_ORDER: tuple[str, ...] = tuple(LAYER_TECH_IDS.keys())


@dataclass(frozen=True)
class MixRampupData:
    """Mix-Hochlauf-Daten: pro Pfad und Schicht ein TWh-Vektor über die Stützjahre."""

    years: tuple[int, ...]
    layers_per_path: dict[str, dict[str, list[float]]]
    demand_per_path: dict[str, list[float]]
    camp: str


def _layer_value(layer: str, r: Any) -> float:
    """Sammelt den TWh-Wert für eine Schicht aus dem PathResult.

    Sonderfall ``gas_h2ready_erdgas`` / ``gas_h2ready_h2``: ``dispatch_used``
    wird über ``split_gas_h2ready_by_fuel`` nach Brennstoff-Anteil
    aufgeteilt.
    """
    if layer in ("gas_h2ready_erdgas", "gas_h2ready_h2"):
        erdgas_share, h2_share = split_gas_h2ready_by_fuel(
            r.dispatch_used.get("gas_h2ready", 0.0),
            r.fuel_used,
        )
        return erdgas_share if layer == "gas_h2ready_erdgas" else h2_share
    return sum(r.dispatch_used.get(t, 0.0) for t in LAYER_TECH_IDS[layer])


def _layer_order_from_model(path_id: str) -> list[str]:
    """Stack-Reihenfolge pro Pfad aus ``PATH_POLICY.dispatch_priority``.

    ``gas_h2ready`` wird an seiner Position in zwei Sub-Schichten
    gesplittet; die Reihenfolge der beiden Sub-Schichten kommt aus
    :func:`enesys.core.inventories.tech_inventory.gas_h2ready_sub_layer_order`,
    die ihrerseits die Pfad-Charakter-Logik ``h2_program_ambition``
    spiegelt (H2-Pfade: H2 unten; GAS-Pfade: Erdgas unten).
    """
    from enesys.core.inventories import PATH_POLICY
    from enesys.core.inventories.tech_inventory import gas_h2ready_sub_layer_order

    policy = PATH_POLICY[path_id]
    seen: set[str] = set()
    order: list[str] = []
    sub_order = gas_h2ready_sub_layer_order(path_id)
    for tech_id in policy.dispatch_priority:
        if tech_id == "gas_h2ready":
            for sub in sub_order:
                if sub not in seen:
                    order.append(sub)
                    seen.add(sub)
            continue
        layer = _TECH_TO_LAYER.get(tech_id)
        if layer is None or layer in seen:
            continue
        order.append(layer)
        seen.add(layer)
    return order


def compute_mix_rampup_data(
    *,
    camp: str = "neutral_default",
    param_set: str | None = None,
    years: tuple[int, ...] = STUETZJAHRE,
) -> MixRampupData:
    """Sammelt die Mix-Schichten pro Pfad und Stützjahr aus ``compute_path``.

    ``param_set`` lädt ein externes Annahmen-Substrat (z. B. ``"ariadne_pypsa"``).
    """
    from enesys.core.path_model import compute_path

    year_list = list(years)
    layers_per_path: dict[str, dict[str, list[float]]] = {}
    demand_per_path: dict[str, list[float]] = {}
    for row in GRID_ORDER:
        for path_id in row:
            results = compute_path(path_id, year_list, camp=camp, param_set=param_set)
            layers: dict[str, list[float]] = {s: [] for s in LAYER_ORDER}
            demand: list[float] = []
            for r in results:
                demand.append(r.demand_twh)
                for s in LAYER_ORDER:
                    layers[s].append(_layer_value(s, r))
            layers_per_path[path_id] = layers
            demand_per_path[path_id] = demand
    return MixRampupData(
        years=tuple(year_list),
        layers_per_path=layers_per_path,
        demand_per_path=demand_per_path,
        camp=camp,
    )


def _plot_path_subplot(
    ax: Axes,
    years: list[int],
    layers: dict[str, list[float]],
    demand: list[float],
    path_id: str,
    *,
    bar_width: float = 1.5,
) -> None:
    """Zeichnet einen Pfad in eine Subplot-Achse (Stack + Bedarfslinie + Titel).

    Falls die Schicht-Summe pro Jahr den Strombedarf nicht deckt (Mengen-
    Defizit), wird die Lücke rot-schraffiert obendrauf gezeichnet — analog
    zum Stresstest-Chart.
    """
    path_layers = _layer_order_from_model(path_id)
    bottom = np.zeros(len(years))
    for s in path_layers:
        values = np.array(layers[s])
        values = np.maximum(values, 0)
        if values.sum() < 0.5:
            continue
        ax.bar(
            years,
            values,
            bottom=bottom,
            width=bar_width,
            color=MENGENBILANZ_SCHICHT_COLORS[s],
            label=MENGENBILANZ_SCHICHT_LABELS[s],
            linewidth=0,
        )
        bottom += values

    deficit = np.maximum(0.0, np.array(demand) - bottom)
    for x, b, d in zip(years, bottom, deficit, strict=True):
        if d > 0.5:
            ax.bar(
                [x],
                [d],
                bottom=[b],
                color="none",
                edgecolor="red",
                hatch="///",
                width=bar_width,
                linewidth=0.6,
            )

    ax.plot(years, demand, color="black", linestyle="--", linewidth=0.9, label="Strombedarf")

    label = PATH_LABELS.get(path_id, path_id)
    color = PATH_COLORS.get(path_id, "black")
    ax.set_title(label, fontsize=PRINT_FONT_SIZE_ANNOT + 2, color=color, fontweight="bold")

    ax.set_ylim(0, 950)
    ax.set_xlim(2024, 2056)
    ax.grid(alpha=0.25, axis="y")
    ax.set_xticks([2026, 2030, 2035, 2040, 2045, 2050, 2055])


def render_mix_rampup_grid(
    data: MixRampupData,
    out_path: Path | str,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
) -> None:
    """Rendert das 2×3-Grid Mix-Hochlauf 2026–2055 pro Pfad.

    ``variant="embedded"`` (default) zeichnet ohne Gesamt-Titel und ohne
    Brand-Footer; Pfad-Titel pro Subplot bleiben (sie tragen Information,
    kein Bild-Titel). ``variant="standalone"`` zeichnet optional einen
    Gesamt-Titel + Brand-Footer für eigenständige Veröffentlichung.
    """
    apply_print_style()

    years = list(data.years)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    for r, row in enumerate(GRID_ORDER):
        for c, path_id in enumerate(row):
            ax = axes[r, c]
            _plot_path_subplot(
                ax,
                years,
                data.layers_per_path[path_id],
                data.demand_per_path[path_id],
                path_id,
            )
            if c == 0:
                ax.set_ylabel("Stromerzeugung (TWh/a)", fontsize=PRINT_FONT_SIZE_ANNOT)
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
