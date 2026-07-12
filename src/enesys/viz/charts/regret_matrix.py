"""Pfad×Lager-Kostenmatrix — verdichtete Entscheidungs-Sicht.

Ein Raster: Zeilen = die sechs Politik-Pfade, Spalten = die vier Lager-Welten.
Die Zelle zeigt den LCOE, die Zellfarbe codiert die Reue (grün = robust,
gelb-rot = teuer-falsch, gleiche HSL-Skala wie das Web-Dashboard). Rechts
daneben die maximale Reue je Pfad als Balken (echte Null, Faktor-Spread).

Drei Sammler, ein Renderer:

- :func:`compute_regret_matrix_data` — kanonisch (Strom-LCOE, 2026-2055,
  Benchmark = Minimum über alle sechs Pfade). Identisch zur Datenbasis des
  Web-Dashboard-Exports. Sieger nur unter den klimaneutralen Pfaden.
- :func:`compute_fullsystem_matrix_data` — vergleichbares **Paar** über zwei
  Horizonte (Default 2026 vs. 2055): **Voll-System-LCOE** (Strom + Kosten der
  nicht elektrifizierten fossilen Wärme/Mobilität), Benchmark = Minimum über
  alle sechs, **alle sechs als Vollmitglieder ohne Vorurteil**, feste Zeilen-
  reihenfolge. Beide Horizonte unterscheiden sich dann *nur* im Horizont und
  sind direkt nebeneinander lesbar.

Branding:
- ``variant="embedded"`` — kein Titel im Bild (umgebende Caption übernimmt)
- ``variant="epub"`` — wie embedded, niedrigere DPI
- ``variant="standalone"`` — Titel + Untertitel
- ``variant="web"`` — SVG-Output
"""

from __future__ import annotations

import colorsys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from enesys.viz.charts._helpers import (
    Variant,
    add_oss_footer,
    dpi_for_variant,
    figsize_for_variant,
)
from enesys.viz.charts.labels import label as _label
from enesys.viz.matplotlib_style import apply_print_style
from enesys.viz.theme import (
    COLORS,
    FONTS,
    PATH_LABELS,
    get_camp_color,
    get_path_color,
)

if TYPE_CHECKING:
    from enesys.viz.brand import BrandConfig

# Klimaneutrale, aktiv wählbare Pfade — Sieger-Kandidaten der kanonischen Sicht.
_ACTIVE_POLICIES: tuple[str, ...] = ("ee_gas", "ee_h2", "kkw_gas", "kkw_h2")

# Feste Zeilenreihenfolge für das vergleichbare Voll-System-Paar: EE oben,
# KKW Mitte, Referenz-Pfade unten — in *beiden* Horizonten identisch, damit
# das Auge jeden Pfad über die zwei Charts hinweg verfolgen kann.
_FIXED_ROW_ORDER: tuple[str, ...] = (
    "ee_gas",
    "ee_h2",
    "kkw_gas",
    "kkw_h2",
    "bestand",
    "weiterso",
)

# Schaden-Skalierung: ct/kWh → Mrd €/Jahr ist linear; der 30-J-Schaden aus
# ``damage_bn_eur`` wird auf das Jahr heruntergebrochen (Dashboard-Konvention).
_YEARS = 30

# Gemeinsame System-Grenze für den Sektorkopplungs-Mehrkosten-Bezug: die
# Mehrkosten der nicht elektrifizierten Wärme/Mobilität, umgelegt auf den
# voll-elektrifizierten 840-TWh-Bedarf (ct/kWh-Äquivalent, vergleichbar).
_COMMON_SYSTEM_TWH = 840.0

STD_FIGSIZE_MATRIX = (10.5, 5.4)

_T = TypeVar("_T")


@dataclass(frozen=True)
class RegretMatrixData:
    """Pfad×Lager-Reue-Matrix, verdichtet für den Plot.

    ``rows`` sind Politik-Werte (``"ee_gas"`` …); ``worlds`` die Lager-Codes.
    Die verschachtelten Dicts sind ``[policy][world]``. ``cost_basis`` ist
    ``"electricity"`` (kanonisch) oder ``"full_system"`` (Strom + Sektor) und
    steuert nur die Fußnote.
    """

    worlds: tuple[str, ...]
    rows: tuple[str, ...]
    lcoe: dict[str, dict[str, float]]
    regret: dict[str, dict[str, float]]
    is_min: dict[str, dict[str, bool]]
    worst_world: dict[str, str]
    maxreg_ct: dict[str, float]
    maxreg_eur_yr: dict[str, float]
    winner: str
    cost_basis: str = "electricity"


def compute_regret_matrix_data() -> RegretMatrixData:
    """Kanonische Savage-Minimax-Reue-Matrix (Strom-LCOE, 2026-2055).

    Benchmark = Minimum über alle sechs Pfade; Sieger nur unter den klima-
    neutralen Pfaden. Identisch zur Datenbasis des Web-Dashboard-Exports.
    """
    from enesys.core.regret_decision_tree import (
        CAMP_WORLDS,
        PolicyChoice,
        compute_regret_matrix,
        damage_bn_eur,
        minimax_regret_per_policy,
    )

    matrix = compute_regret_matrix()
    maxreg = minimax_regret_per_policy(matrix)
    cell = {(c.policy, c.world): c for c in matrix}

    policies = list(PolicyChoice)
    rows = tuple(p.value for p in sorted(policies, key=lambda p: maxreg[p]))
    winner = min((PolicyChoice(pid) for pid in _ACTIVE_POLICIES), key=lambda p: maxreg[p])

    def _nest(getter: Callable[[Any], _T]) -> dict[str, dict[str, _T]]:
        return {p.value: {w: getter(cell[(p, w)]) for w in CAMP_WORLDS} for p in policies}

    return RegretMatrixData(
        worlds=tuple(CAMP_WORLDS),
        rows=rows,
        lcoe=_nest(lambda rc: rc.lcoe_30y_mean_ct_kwh),
        regret=_nest(lambda rc: rc.regret_ct_kwh),
        is_min=_nest(lambda rc: rc.is_minimum),
        worst_world={
            p.value: max(CAMP_WORLDS, key=lambda w: cell[(p, w)].regret_ct_kwh) for p in policies
        },
        maxreg_ct={p.value: maxreg[p] for p in policies},
        maxreg_eur_yr={p.value: damage_bn_eur(maxreg[p]) / _YEARS for p in policies},
        winner=winner.value,
        cost_basis="electricity",
    )


def compute_fullsystem_matrix_data(start_year: int = 2026) -> RegretMatrixData:
    """Voll-System-Matrix über einen Horizont (``start_year`` … +30 J).

    Ein Glied des vergleichbaren Horizont-Paars (Default 2026; das intergene-
    rationale Pendant ruft ``start_year=2055``). Identische Methodik in beiden
    Horizonten, damit nur der Horizont den Unterschied macht:

    - **Voll-System-LCOE** = Strom-LCOE + Sektorkopplungs-Mehrkosten der nicht
      elektrifizierten fossilen Wärme/Mobilität (auf die gemeinsame 840-TWh-
      Grenze umgelegt). Damit werden teil- und voll-elektrifizierte Pfade auf
      derselben Energie-Dienstleistungs-Grenze verglichen.
    - **Benchmark = Minimum über alle sechs** — alle sechs sind Vollmitglieder
      ohne Vorurteil. Der Sektor-Aufschlag (statt Ausschluss) sorgt dafür, dass
      kein »Nichtstun«-Pfad billig gewinnt: er verliert an den Zahlen.
    - **Feste Zeilenreihenfolge** (EE / KKW / Referenz) in beiden Horizonten.
    """
    from enesys.core.path_model import compute_path
    from enesys.core.regret_decision_tree import (
        CAMP_WORLDS,
        PolicyChoice,
        damage_bn_eur,
    )

    policies = [p.value for p in PolicyChoice]
    worlds = tuple(CAMP_WORLDS)
    years = list(range(start_year, start_year + _YEARS))

    full: dict[str, dict[str, float]] = {}
    for p in policies:
        full[p] = {}
        for w in worlds:
            res = compute_path(p, years, camp=w)
            n = len(res)
            elec = sum(r.lcoe_ct_kwh for r in res) / n
            sk_eur = sum(r.sector_coupling_external_eur_per_year for r in res) / n
            full[p][w] = elec + sk_eur / (_COMMON_SYSTEM_TWH * 1e9) * 100

    world_min = {w: min(full[p][w] for p in policies) for w in worlds}
    regret = {p: {w: full[p][w] - world_min[w] for w in worlds} for p in policies}
    is_min = {p: {w: full[p][w] == world_min[w] for w in worlds} for p in policies}
    maxreg = {p: max(regret[p][w] for w in worlds) for p in policies}
    worst_world = {p: max(worlds, key=lambda w: regret[p][w]) for p in policies}
    winner = min(policies, key=lambda p: maxreg[p])

    return RegretMatrixData(
        worlds=worlds,
        rows=_FIXED_ROW_ORDER,
        lcoe=full,
        regret=regret,
        is_min=is_min,
        worst_world=worst_world,
        maxreg_ct=maxreg,
        maxreg_eur_yr={p: damage_bn_eur(maxreg[p]) / _YEARS for p in policies},
        winner=winner,
        cost_basis="full_system",
    )


def _regret_bg(regret_ct: float) -> tuple[float, float, float]:
    """Zell-Hintergrund aus der Reue — grün (0) bis rot (hoch).

    Repliziert exakt die HSL-Skala des Web-Dashboards
    (``hsl(130 − ct·20, 58 %, 88 %)``), damit Matrix und Web-Tabelle wie
    Geschwister wirken. colorsys nutzt HLS-Reihenfolge.
    """
    hue = max(0.0, 130.0 - max(0.0, regret_ct) * 20.0)
    return colorsys.hls_to_rgb(hue / 360.0, 0.88, 0.58)


def _fmt(value: float, decimals: int, lang: str) -> str:
    """Zahl mit sprach-passendem Dezimaltrenner (DE-Komma, EN-Punkt)."""
    s = f"{value:.{decimals}f}"
    return s.replace(".", ",") if lang != "en" else s


def _draw_matrix_panel(ax: Axes, data: RegretMatrixData, *, cell_value: str, lang: str) -> None:
    """Zeichnet das Raster: farbige Reue-Zellen, LCOE-Zahl, ★ am Welt-Minimum."""
    worlds = data.worlds
    rows = data.rows
    ax.set_xlim(0, len(worlds))
    ax.set_ylim(len(rows), 0)  # erste Zeile oben

    for r, policy in enumerate(rows):
        for c, world in enumerate(worlds):
            regret = data.regret[policy][world]
            ax.add_patch(
                mpatches.Rectangle(
                    (c, r),
                    1,
                    1,
                    facecolor=_regret_bg(regret),
                    edgecolor=COLORS["bg"],
                    linewidth=1.5,
                    zorder=2,
                )
            )
            is_min = data.is_min[policy][world]
            shown = data.lcoe[policy][world] if cell_value == "lcoe" else regret
            ax.text(
                c + 0.5,
                r + 0.5,
                ("★ " if is_min else "") + _fmt(shown, 1, lang),
                ha="center",
                va="center",
                fontsize=FONTS["size_axis_label"],
                fontweight="bold" if is_min else "normal",
                color=COLORS["text_dark"],
                zorder=5,
            )

    for c, world in enumerate(worlds):
        ax.text(
            c + 0.5,
            -0.12,
            _label(f"regret_matrix.world.{world}", lang),
            ha="center",
            va="bottom",
            fontsize=FONTS["size_axis_label"],
            fontweight="bold",
            color=get_camp_color(world),
        )

    for r, policy in enumerate(rows):
        ax.text(
            -0.08,
            r + 0.5,
            PATH_LABELS[policy],
            ha="right",
            va="center",
            fontsize=FONTS["size_axis_label"],
            fontweight="bold",
            color=COLORS["accent_green"] if policy == data.winner else COLORS["text_dark"],
        )

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])


def _draw_maxregret_bars(
    ax: Axes, data: RegretMatrixData, *, lang: str, bar_xmax: float | None = None
) -> None:
    """Zeichnet die Max-Reue je Pfad als Balken (echte Null, Mrd €/Jahr).

    ``bar_xmax`` pinnt die X-Achse auf einen geteilten Wert — so sind die
    Balkenlängen zwischen zwei Horizont-Charts direkt vergleichbar. Der Sieger
    (niedrigste Max-Reue) bekommt grün + ein »robusteste Wette«-Etikett.
    """
    rows = data.rows
    data_max = max(data.maxreg_eur_yr.values())
    max_eur = max(bar_xmax, data_max * 1.05) if bar_xmax else data_max
    for r, policy in enumerate(rows):
        is_winner = policy == data.winner
        eur_yr = data.maxreg_eur_yr[policy]
        ax.barh(
            r + 0.5,
            eur_yr,
            height=0.6,
            color=get_path_color(PATH_LABELS[policy]),
            edgecolor=COLORS["accent_green"] if is_winner else "none",
            linewidth=1.6 if is_winner else 0,
            zorder=3,
        )
        label = _fmt(eur_yr, 1, lang)
        if is_winner:
            label += "  " + _label("regret_matrix.winner_tag", lang)
        ax.text(
            eur_yr + max_eur * 0.03,
            r + 0.5,
            label,
            ha="left",
            va="center",
            fontsize=FONTS["size_annotation"],
            fontweight="bold" if is_winner else "normal",
            color=COLORS["accent_green"] if is_winner else COLORS["text_dark"],
        )

    ax.set_xlim(0, max_eur * 1.22)
    ax.text(
        0,
        -0.12,
        _label("regret_matrix.bar_header", lang),
        ha="left",
        va="bottom",
        fontsize=FONTS["size_annotation"],
        color=COLORS["text_muted"],
    )
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, labelleft=False)


def render_regret_matrix(
    data: RegretMatrixData,
    out_path: Path | str | None = None,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
    return_fig: bool = False,
    lang: str = "de",
    cell_value: str = "lcoe",
    bar_xmax: float | None = None,
) -> plt.Figure | None:
    """Rendert die Pfad×Lager-Kostenmatrix (Raster + Max-Reue-Balken).

    ``cell_value`` schaltet die Zell-Zahl: ``"lcoe"`` (Default) oder
    ``"regret"``; die Färbung codiert in beiden Fällen die Reue. ``bar_xmax``
    pinnt die Balken-Achse für vergleichbare Horizont-Paare. ``return_fig=True``
    gibt die Figure zurück (für ``st.pyplot``), sonst Speichern nach ``out_path``.
    """
    if cell_value not in ("lcoe", "regret"):
        raise ValueError(f"cell_value muss 'lcoe' oder 'regret' sein, nicht {cell_value!r}")

    apply_print_style()
    figsize = figsize_for_variant(variant, STD_FIGSIZE_MATRIX)
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor(COLORS["bg"])
    gs = fig.add_gridspec(1, 2, width_ratios=(len(data.worlds), 1.6), wspace=0.06)
    ax_matrix = fig.add_subplot(gs[0, 0])
    ax_bars = fig.add_subplot(gs[0, 1], sharey=ax_matrix)

    _draw_matrix_panel(ax_matrix, data, cell_value=cell_value, lang=lang)
    _draw_maxregret_bars(ax_bars, data, lang=lang, bar_xmax=bar_xmax)

    if variant == "standalone" and title:
        fig.text(
            0.04,
            0.95,
            title,
            fontsize=FONTS["size_title"],
            fontweight="bold",
            color=COLORS["text_dark"],
            ha="left",
            va="top",
        )
        if subtitle:
            fig.text(
                0.04,
                0.89,
                subtitle,
                fontsize=FONTS["size_subtitle"],
                color=COLORS["text_muted"],
                ha="left",
                va="top",
            )

    footnote_key = (
        "regret_matrix.footnote_fullsystem"
        if data.cost_basis == "full_system"
        else "regret_matrix.footnote"
    )
    fig.text(
        0.5,
        0.03,
        _label(footnote_key, lang),
        ha="center",
        va="bottom",
        fontsize=int(FONTS["size_annotation"]) - 1,
        color=COLORS["text_muted"],
        style="italic",
    )

    top = 0.80 if (variant == "standalone" and title) else 0.92
    fig.subplots_adjust(left=0.13, right=0.965, top=top, bottom=0.13)

    if variant == "standalone" and brand is not None:
        from enesys.viz.brand import add_brand_footer

        add_brand_footer(fig, brand)
    add_oss_footer(fig)

    if return_fig:
        return fig

    if out_path is None:
        raise ValueError("out_path must be set when return_fig=False")
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
    return None
