"""Rolling-LCOE trajectory chart — Anchor 1 core visual.

2-panel layout:

1. Rolling-30-year LCOE per investment start year (inline labels).
2. Rolling-30-year LCOE spread across paths per start year (max − min).

Every value shown is a 30-year lifecycle LCOE for a path that is
"locked in" at the given start year. The per-year forward-cost view
(annualised LCOE in a single calendar year) is deliberately omitted:
it mixes amortised CAPEX with current OPEX in a way that does not
map onto end-customer prices and invites a spot-price reading the
model does not support.

Branding variants:
- ``variant="embedded"`` — no title in the figure (surrounding caption
  carries the message).
- ``variant="epub"`` — like embedded, lower DPI.
- ``variant="standalone"`` — title + subtitle + optional brand footer.
- ``variant="web"`` — SVG output.

Data collection lives in ``compute_trajectory_data()`` so that Streamlit
can drive a Plotly renderer off the same data layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from enesys.viz.charts._helpers import (
    Variant,
    add_endpoint_marker,
    add_inline_label,
    add_oss_footer,
    apply_path_style,
    dpi_for_variant,
)
from enesys.viz.matplotlib_style import (
    PRINT_FONT_SIZE_ANNOT,
    STD_FIGSIZE_DOUBLE,
    apply_print_style,
)
from enesys.viz.theme import PATH_LABELS

if TYPE_CHECKING:
    from enesys.viz.brand import BrandConfig


# Path order in the legend: EE first, then KKW, then reductio paths
# (BESTAND, WEITER-SO).
PATH_ORDER: tuple[str, ...] = ("ee_gas", "ee_h2", "kkw_gas", "kkw_h2", "bestand", "weiterso")

DEFAULT_ROLLING_WINDOW = 30


@dataclass(frozen=True)
class TrajectoryData:
    """Rolling-LCOE per start year for several paths.

    ``rolling_lcoe[pid]`` is a list of mean LCOE values over the window
    ``(Y, Y + rolling_window - 1)`` for each start year ``Y`` in
    ``years``. Length matches ``len(years)``.
    """

    years: list[int]
    rolling_lcoe: dict[str, list[float]]
    rolling_window: int
    demand_twh: list[float]


def compute_trajectory_data(
    *,
    years_range: range = range(2026, 2056),
    camp: str = "neutral_default",
    param_set: str | None = None,
    path_ids: tuple[str, ...] = PATH_ORDER,
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
) -> TrajectoryData:
    """Pre-compute rolling-LCOE trajectories for the chart.

    For each path, runs ``compute_path`` over an extended range
    ``[years_range[0], years_range[-1] + rolling_window - 1]`` so that the
    rolling mean for the last start year sees its full window. Then
    averages annual LCOE inside each ``(Y, Y + rolling_window - 1)``
    window to produce one value per start year.

    ``param_set`` loads an external assumption substrate (e.g.
    ``"ariadne_pypsa"``) from the ``param_sets`` registry; when set, it
    overrides per-year camp defaults.
    """
    from enesys.core.path_model import compute_path

    years = list(years_range)
    if not years:
        raise ValueError("years_range must be non-empty")
    extended_years = list(range(years[0], years[-1] + rolling_window))
    raw = {
        pid: compute_path(pid, extended_years, camp=camp, param_set=param_set) for pid in path_ids
    }
    all_lcoe = {pid: [r.lcoe_ct_kwh for r in raw[pid]] for pid in path_ids}
    rolling = {
        pid: [
            sum(all_lcoe[pid][i : i + rolling_window]) / rolling_window for i in range(len(years))
        ]
        for pid in path_ids
    }
    demand_twh = [r.demand_twh for r in raw[path_ids[0]][: len(years)]]
    return TrajectoryData(
        years=years,
        rolling_lcoe=rolling,
        rolling_window=rolling_window,
        demand_twh=demand_twh,
    )


def render_lcoe_trajectory(
    data: TrajectoryData,
    out_path: Path | str,
    *,
    variant: Variant = "embedded",
    title: str | None = None,
    subtitle: str | None = None,
    brand: BrandConfig | None = None,
    inline_labels: bool = True,
) -> None:
    """Render the rolling-LCOE trajectory chart (2-panel layout).

    Parameters
    ----------
    data : TrajectoryData
        From :func:`compute_trajectory_data`.
    out_path : Path | str
        Output path. ``.svg`` for ``variant="web"``, ``.png`` otherwise.
    variant : Variant
        Render preset.
    title, subtitle : optional
        Drawn only when ``variant="standalone"``.
    brand : BrandConfig | None
        Brand config for the standalone footer.
    inline_labels : bool
        When True, label each path at its rightmost endpoint instead of
        drawing a legend.
    """
    apply_print_style()

    fig, (ax_main, ax_spread) = plt.subplots(1, 2, figsize=STD_FIGSIZE_DOUBLE)

    start_year = data.years[0]
    end_year = data.years[-1]
    window_label = f"{data.rolling_window}-year rolling LCOE"

    # === Panel 1: Rolling-LCOE per start year ===
    for path_id in PATH_ORDER:
        if path_id not in data.rolling_lcoe:
            continue
        values = data.rolling_lcoe[path_id]
        (line,) = ax_main.plot(data.years, values)
        apply_path_style(line, path_id, linewidth=2.4)
        add_endpoint_marker(ax_main, data.years[-1], values[-1], path_id, size=70)
        if inline_labels:
            add_inline_label(
                ax_main,
                data.years[-1],
                values[-1],
                PATH_LABELS[path_id],
                path_id,
                fontsize=PRINT_FONT_SIZE_ANNOT,
                dx=0.4,
            )

    ax_main.set_ylabel(f"{window_label} (ct/kWh)", fontsize=PRINT_FONT_SIZE_ANNOT)
    ax_main.set_xlabel("Investment start year", fontsize=PRINT_FONT_SIZE_ANNOT)
    ax_main.set_xlim(data.years[0], data.years[-1] + (3.5 if inline_labels else 0))
    ax_main.grid(True, linestyle=":", alpha=0.35)
    if variant != "embedded":
        ax_main.set_title(
            f"Lifecycle LCOE per investment start year ({start_year}–{end_year})",
            fontsize=PRINT_FONT_SIZE_ANNOT,
        )

    # === Panel 2: Spread (max − min) per start year ===
    spread = []
    for i in range(len(data.years)):
        vals = [data.rolling_lcoe[p][i] for p in data.rolling_lcoe]
        spread.append(max(vals) - min(vals))
    ax_spread.plot(data.years, spread, color="#2A2A2A", linewidth=2.0)
    ax_spread.fill_between(data.years, 0, spread, color="#2A2A2A", alpha=0.12)
    ax_spread.set_ylabel("Path spread max − min (ct/kWh)", fontsize=PRINT_FONT_SIZE_ANNOT)
    ax_spread.set_xlabel("Investment start year", fontsize=PRINT_FONT_SIZE_ANNOT)
    ax_spread.set_xlim(data.years[0], data.years[-1])
    ax_spread.grid(True, linestyle=":", alpha=0.35)
    if variant != "embedded":
        ax_spread.set_title("Path spread", fontsize=PRINT_FONT_SIZE_ANNOT)

    # === Title block (standalone only) ===
    if variant == "standalone" and title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.99)
        if subtitle:
            fig.text(0.5, 0.94, subtitle, fontsize=11, color="#444", ha="center", style="italic")

    if variant == "standalone" and brand is not None:
        fig.text(
            0.98,
            0.01,
            f"{brand.domain} · {brand.title}",
            fontsize=8,
            color="#666",
            ha="right",
            alpha=0.7,
        )

    plt.tight_layout()
    if variant == "standalone" and title:
        plt.subplots_adjust(top=0.90)
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
