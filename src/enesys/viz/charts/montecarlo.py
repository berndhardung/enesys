"""Monte-Carlo-Chart — Core-Visual, Robustheits-Diagnostik.

Zweispalt-Layout:
1. Violin-Plot: LCOE-Verteilung pro Pfad aus N Annahmen-Konstellationen
2. Bar-Chart: P(EE-GAS günstiger als anderer Pfad) je anderem Pfad

Daten-Sammler: ``monte_carlo_all_paths`` aus ``enesys.core.path_model``.
Default: 3 000 Samples, Uniform-Verteilung über Hebel-low/high, Seed 42.

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
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from enesys.viz.charts._helpers import Variant, add_oss_footer, dpi_for_variant
from enesys.viz.matplotlib_style import (
    PRINT_FONT_SIZE_ANNOT,
    PRINT_FONT_SIZE_BAR_LABEL,
    PRINT_FONT_SIZE_LEGEND,
    STD_FIGSIZE_DOUBLE,
    apply_print_style,
)
from enesys.viz.theme import PATH_COLORS

if TYPE_CHECKING:
    from enesys.viz.brand import BrandConfig


# Pfad-Reihenfolge im Violin-Plot: EE-Pfade links, KKW-Pfade Mitte,
# Referenz-Pfade (WEITER-SO, BESTAND) rechts. Public-Label, weil
# ``monte_carlo_all_paths`` Display-Label-Keys liefert.
DEFAULT_PATH_NAMES: tuple[str, ...] = (
    "EE-GAS",
    "EE-H2",
    "KKW-GAS",
    "KKW-H2",
    "BESTAND",
    "WEITER-SO",
)

# Reference-Pfad für das Wahrscheinlichkeits-Panel (P(REF gewinnt vs. X))
DEFAULT_REFERENCE: str = "EE-GAS"


@dataclass(frozen=True)
class MonteCarloData:
    """Monte-Carlo-Verteilungen pro Pfad + Win-Probabilities gegen Referenz."""

    n_runs: int
    seed: int
    camp: str
    year: int
    path_names: tuple[str, ...]
    reference: str
    prices_per_path: dict[str, list[float]]
    mean_per_path: dict[str, float]
    p_reference_wins_vs: dict[str, float]


def compute_monte_carlo_data(
    *,
    n_runs: int = 500,
    n_year_samples: int = 6,
    seed: int = 42,
    camp: str = "neutral_default",
    param_set: str | None = None,
    year: int = 2026,
    path_names: tuple[str, ...] = DEFAULT_PATH_NAMES,
    reference: str = DEFAULT_REFERENCE,
) -> MonteCarloData:
    """Sammelt Monte-Carlo-Verteilungen aus ``monte_carlo_all_paths``.

    Default-Setting ist der kanonische Rolling-Lebenszyklus 2026-2055
    mit Trapez-Approximation über 6 Stützjahre und 500 Sample-Läufen.
    Volle Auflösung über ``n_runs=3000, n_year_samples=30``.

    ``param_set`` lädt ein externes Annahmen-Substrat (z. B. ``"ariadne_pypsa"``)
    und reicht es als ``baseline_overrides`` durch — die Hebel-Variationen
    laufen dann um diesen verschobenen Punkt.
    """
    from enesys.core.sensitivity import monte_carlo_all_paths

    baseline_overrides: dict[str, float] | None = None
    if param_set is not None:
        from enesys.core.param_sets import get as _get_param_set

        overrides_per_year = _get_param_set(param_set).overrides_yearly([year])
        baseline_overrides = overrides_per_year.get(year)

    mc = monte_carlo_all_paths(
        year=year,
        baseline_camp=camp,
        n_runs=n_runs,
        n_year_samples=n_year_samples,
        seed=seed,
        baseline_overrides=baseline_overrides,
    )
    return MonteCarloData(
        n_runs=n_runs,
        seed=seed,
        camp=camp if param_set is None else f"{camp}+{param_set}",
        year=year,
        path_names=path_names,
        reference=reference,
        prices_per_path={p: list(mc["prices_per_path"][p]) for p in path_names},
        mean_per_path={p: mc["mean_per_path"][p] for p in path_names},
        p_reference_wins_vs={
            p: mc[f"p_{reference.lower().replace('-', '_')}_wins_vs"][p]
            for p in path_names
            if p != reference
        },
    )


def _draw_violin_panel(ax: Axes, data: MonteCarloData, *, variant: Variant) -> None:
    """Zeichnet das Violin-Panel (LCOE-Verteilung pro Pfad).

    Subplot-Titel: bei ``embedded`` ausgelassen (umgebende Caption erklärt),
    bei ``standalone``/``epub`` mit Konstellationen-Zahl.
    """
    samples = [data.prices_per_path[p] for p in data.path_names]
    parts: Any = ax.violinplot(samples, showmeans=True, showmedians=False)

    for i, pc in enumerate(parts["bodies"]):
        path_id = _name_to_id(data.path_names[i])
        pc.set_facecolor(PATH_COLORS.get(path_id, "#888"))
        pc.set_alpha(0.6)
        pc.set_edgecolor("black")

    parts["cmeans"].set_color("black")
    parts["cmaxes"].set_color("#666")
    parts["cmins"].set_color("#666")
    parts["cbars"].set_color("#666")

    for i, name in enumerate(data.path_names):
        mean = data.mean_per_path[name]
        ax.text(
            i + 1,
            mean,
            f"  ⌀ {mean:.2f}",
            va="center",
            ha="left",
            fontsize=PRINT_FONT_SIZE_BAR_LABEL,
            fontweight="bold",
        )

    ax.set_xticks(range(1, len(data.path_names) + 1))
    ax.set_xticklabels(data.path_names)
    ax.set_ylabel("Forward Cost (ct/kWh)", fontsize=PRINT_FONT_SIZE_ANNOT)
    if variant != "embedded":
        ax.set_title(
            f"LCOE-Verteilung über {data.n_runs} Annahmen-Konstellationen",
            fontsize=PRINT_FONT_SIZE_ANNOT + 2,
            fontweight="bold",
        )
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)


def _draw_winprob_panel(ax: Axes, data: MonteCarloData, *, variant: Variant) -> None:
    """Zeichnet das Win-Probability-Panel.

    Subplot-Titel: bei ``embedded`` ausgelassen (umgebende Caption erklärt),
    bei ``standalone``/``epub`` mit Robustheits-Frage.
    """
    others = [p for p in data.path_names if p != data.reference]
    p_wins = [data.p_reference_wins_vs[p] * 100 for p in others]

    bars = ax.barh(
        others,
        p_wins,
        color=[PATH_COLORS.get(_name_to_id(p), "#888") for p in others],
        alpha=0.7,
        edgecolor="black",
        linewidth=0.5,
    )
    for bar, p in zip(bars, p_wins, strict=False):
        ax.text(
            p + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f" {p:.1f} %",
            va="center",
            ha="left",
            fontsize=PRINT_FONT_SIZE_BAR_LABEL,
            fontweight="bold",
        )

    ax.axvline(50, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax.axvline(95, color="green", linestyle=":", linewidth=1, alpha=0.7, label="95 %-Schwelle")
    ax.set_xlim(0, 105)
    ax.set_xlabel(
        f"P({data.reference} günstiger als anderer Pfad) in %", fontsize=PRINT_FONT_SIZE_ANNOT
    )
    if variant != "embedded":
        ax.set_title(
            f"Wie robust ist {data.reference}?",
            fontsize=PRINT_FONT_SIZE_ANNOT + 2,
            fontweight="bold",
        )
    ax.legend(loc="lower right", fontsize=PRINT_FONT_SIZE_LEGEND)
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    ax.invert_yaxis()


def _name_to_id(display_label: str) -> str:
    """Display-Label »EE-GAS« → pfad_id »ee_gas« (für Theme-Lookup)."""
    return display_label.lower().replace("-", "_")


def render_monte_carlo(
    data: MonteCarloData,
    out_path: Path | str,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
) -> None:
    """Rendert das Monte-Carlo-Side-by-Side (Violin + Win-Probability)."""
    apply_print_style()

    fig, (ax_violin, ax_bar) = plt.subplots(
        1, 2, figsize=STD_FIGSIZE_DOUBLE, gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.3}
    )

    _draw_violin_panel(ax_violin, data, variant=variant)
    _draw_winprob_panel(ax_bar, data, variant=variant)

    if variant == "standalone" and title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.99)
        if subtitle:
            fig.text(0.5, 0.94, subtitle, fontsize=11, color="#444", ha="center", style="italic")

    if variant == "standalone" and brand is not None:
        from enesys.viz.brand import add_brand_footer

        add_brand_footer(fig, brand)

    # Drei Subplots in unterschiedlicher Höhe (Histogramme + Boxplot);
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
