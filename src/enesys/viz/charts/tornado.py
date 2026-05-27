"""Tornado-Sensitivitäts-Chart — Core-Visual, Hebel-Diagnostik.

Side-by-Side-Layout: pro Pfad ein Tornado mit den 8 wichtigsten Hebeln
nach Swing-Größe sortiert. Default-Pfade: EE-GAS (Robustheits-Anker)
und KKW-GAS (Lager-Konkurrent).

Hebel: ``TORNADO_HEBEL`` aus ``enesys.core.path_model`` — jede Variation
zwischen Lager-low und Lager-high, andere Parameter auf
``baseline_camp``-Default.

Branding:
- ``variant="embedded"`` — kein Titel im Bild (umgebende Caption übernimmt)
- ``variant="epub"`` — wie embedded, niedrigere DPI
- ``variant="standalone"`` — Titel + Untertitel + optionaler Brand-Footer
- ``variant="web"`` — SVG-Output
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from enesys.viz.charts._helpers import Variant, add_oss_footer, dpi_for_variant
from enesys.viz.matplotlib_style import (
    PRINT_FONT_SIZE_ANNOT,
    PRINT_FONT_SIZE_BAR_LABEL,
    PRINT_FONT_SIZE_LEGEND,
    STD_FIGSIZE_DOUBLE,
    apply_print_style,
)
from enesys.viz.theme import PATH_COLORS, PATH_LABELS

if TYPE_CHECKING:
    from enesys.viz.brand import BrandConfig


DEFAULT_PATH_PAIR: tuple[str, str] = ("ee_gas", "kkw_gas")

# Schwellwert: Hebel mit Swing < 0,05 ct/kWh werden ausgeblendet
# (Mikro-Wackler, optisch nicht lesbar).
MIN_SWING: float = 0.05
MAX_HEBEL: int = 8


@dataclass(frozen=True)
class PathTornado:
    """Tornado-Daten eines Pfads: Baseline + Hebel-Liste."""

    path_id: str
    baseline: float
    hebel: list[dict]  # je {label, price_low, price_high, swing}


@dataclass(frozen=True)
class TornadoData:
    """Tornado-Daten für ein Pfad-Paar (Side-by-Side)."""

    pfade: tuple[PathTornado, ...]
    camp: str
    year: int


def compute_tornado_data(
    *,
    path_ids: tuple[str, ...] = DEFAULT_PATH_PAIR,
    camp: str = "neutral_default",
    param_set: str | None = None,
    year: int = 2026,
) -> TornadoData:
    """Sammelt Tornado-Daten pro Pfad aus ``tornado_path_analysis``.

    Default-Setting ist der kanonische Rolling-Lebenszyklus 2026-2055.
    Tornado-Bandbreiten in ``TORNADO_LEVERS`` sind als year-agnostische
    Konstanten formuliert; bei einem späteren Start-Jahr (z.B. 2045)
    überschreiben diese Konstanten die Lernkurven-Trajektorie und der
    Bracket schließt die Baseline nicht mehr zuverlässig ein. ``year=2026``
    bleibt damit der robuste Default.

    ``param_set`` lädt ein externes Annahmen-Substrat (z. B. ``"ariadne_pypsa"``)
    aus der ``param_sets``-Registry. Die Bezugsjahr-Werte des Sets werden als
    ``baseline_overrides`` durchgereicht — der Tornado-Vergleich variiert dann
    um diesen verschobenen Punkt.
    """
    from enesys.core.sensitivity import baseline_all_paths, tornado_path_analysis

    baseline_overrides: dict[str, float] | None = None
    if param_set is not None:
        from enesys.core.param_sets import get as _get_param_set

        overrides_per_year = _get_param_set(param_set).overrides_yearly([year])
        baseline_overrides = overrides_per_year.get(year)

    baselines = baseline_all_paths(year=year, camp=camp, param_set=param_set)
    pfade: list[PathTornado] = []
    for path_id in path_ids:
        hebel = tornado_path_analysis(
            path_id,
            year=year,
            baseline_camp=camp,
            baseline_overrides=baseline_overrides,
        )
        display_label = PATH_LABELS[path_id]
        pfade.append(
            PathTornado(
                path_id=path_id,
                baseline=baselines[display_label],
                hebel=hebel,
            )
        )
    return TornadoData(pfade=tuple(pfade), camp=camp, year=year)


def _draw_tornado_panel(ax: Axes, ptornado: PathTornado, *, color: str, variant: Variant) -> None:
    """Zeichnet einen Tornado-Subplot für einen Pfad.

    Subplot-Titel: bei ``embedded`` nur der Pfad-Name (umgebende Caption
    erklärt »Tornado«); bei ``standalone``/``epub`` zusätzlich " · Tornado".
    """
    sig = [r for r in ptornado.hebel if r["swing"] > MIN_SWING][:MAX_HEBEL]
    labels = [r["label"] for r in sig]
    lows = [r["price_low"] for r in sig]
    highs = [r["price_high"] for r in sig]

    y = np.arange(len(labels))
    # `price_low` / `price_high` sind LCOE-Werte und NICHT zwingend
    # numerisch geordnet — bei monoton fallenden Hebeln (z. B.
    # nep_realization_rate: hoher Realgrad → niedrige LCOE) liegt
    # `price_low` oben. Für die x-Achsen-Limits müssen wir deshalb
    # die echten Extrema pro Hebel ziehen, sonst läuft der größte
    # Balken über den Subplot hinaus und seine Beschriftung landet
    # im Nachbar-Panel.
    bar_min = [min(r["price_low"], r["price_high"]) for r in ptornado.hebel]
    bar_max = [max(r["price_low"], r["price_high"]) for r in ptornado.hebel]
    plot_min = min(bar_min) * 0.97
    plot_max = max(bar_max) * 1.05
    plot_range = plot_max - plot_min
    narrow_threshold = plot_range * 0.18
    # Bei schmalen Balken würden zwei separate Labels (lo links, hi rechts)
    # sichtbar überlappen. Ab welcher Spannweite das passiert, hängt von der
    # Achsen-Skala ab — pragmatisch: mindestens 0,6 ct/kWh Spannweite und
    # mindestens 4 % der Plotbreite. Darunter: ein kombiniertes Label rechts.
    tight_threshold = max(0.6, plot_range * 0.04)

    for i, (lo, hi) in enumerate(zip(lows, highs, strict=False)):
        left = min(lo, hi)
        right = max(lo, hi)
        width = right - left
        ax.barh(y[i], width, left=left, color=color, alpha=0.7, edgecolor="black", linewidth=0.5)

        offset = plot_range * 0.005
        if width < tight_threshold:
            ax.text(
                right + offset,
                y[i],
                f"{left:.1f}–{right:.1f}",
                va="center",
                ha="left",
                fontsize=PRINT_FONT_SIZE_BAR_LABEL,
                color="#1a1a1a",
            )
        elif width >= narrow_threshold:
            # Labels INNERHALB des Balkens. Position folgt der geometrischen
            # Anordnung (links = numerisch kleinerer Wert), nicht der
            # ``price_low``/``price_high``-Semantik — sonst wirken Hebel
            # mit monoton-fallender Wirkung (NEP, KKW-Realgrad) optisch
            # vertauscht.
            inset = width * 0.04
            ax.text(
                left + inset,
                y[i],
                f"{left:.1f}",
                va="center",
                ha="left",
                fontsize=PRINT_FONT_SIZE_BAR_LABEL,
                color="#1a1a1a",
            )
            ax.text(
                right - inset,
                y[i],
                f"{right:.1f}",
                va="center",
                ha="right",
                fontsize=PRINT_FONT_SIZE_BAR_LABEL,
                color="#1a1a1a",
            )
        else:
            # Labels AUSSERHALB des Balkens — gleiche Reihenfolge-Logik.
            ax.text(
                left - offset,
                y[i],
                f"{left:.1f}",
                va="center",
                ha="right",
                fontsize=PRINT_FONT_SIZE_BAR_LABEL,
                color="#1a1a1a",
            )
            ax.text(
                right + offset,
                y[i],
                f"{right:.1f}",
                va="center",
                ha="left",
                fontsize=PRINT_FONT_SIZE_BAR_LABEL,
                color="#1a1a1a",
            )

    ax.set_xlim(plot_min, plot_max)
    ax.axvline(
        ptornado.baseline,
        color="black",
        linestyle="--",
        linewidth=1,
        label=f"Baseline {ptornado.baseline:.2f} ct",
    )

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Forward Cost (ct/kWh)", fontsize=PRINT_FONT_SIZE_ANNOT)
    title_text = PATH_LABELS[ptornado.path_id]
    if variant != "embedded":
        title_text = f"{title_text} · Tornado"
    ax.set_title(
        title_text,
        fontsize=PRINT_FONT_SIZE_ANNOT + 2,
        color=color,
        fontweight="bold",
    )
    ax.legend(loc="lower right", fontsize=PRINT_FONT_SIZE_LEGEND)
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)


def render_tornado_sensitivity(
    data: TornadoData,
    out_path: Path | str,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
) -> None:
    """Rendert das Tornado-Side-by-Side für die zwei Default-Pfade."""
    apply_print_style()

    n = len(data.pfade)
    fig, axes = plt.subplots(1, n, figsize=STD_FIGSIZE_DOUBLE, gridspec_kw={"wspace": 0.4})
    if n == 1:
        axes = [axes]

    for ax, ptornado in zip(axes, data.pfade, strict=True):
        color = PATH_COLORS.get(ptornado.path_id, "#888")
        _draw_tornado_panel(ax, ptornado, color=color, variant=variant)

    if variant == "standalone" and title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.99)
        if subtitle:
            fig.text(0.5, 0.94, subtitle, fontsize=11, color="#444", ha="center", style="italic")

    if variant == "standalone" and brand is not None:
        from enesys.viz.brand import add_brand_footer

        add_brand_footer(fig, brand)

    # Side-by-Side-Subplots haben unterschiedliche Achsen-Höhen (legendenbedingt);
    # tight_layout warnt darüber, der Layout-Korrektur unten greift trotzdem.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*not compatible with tight_layout.*")
        plt.tight_layout()
    if variant == "standalone" and title:
        plt.subplots_adjust(top=0.88)
    plt.subplots_adjust(bottom=0.14)
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
