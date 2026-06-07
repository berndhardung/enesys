"""Reusable chart building blocks — core visuals.

Each module exports a ``render_*`` function with a uniform signature:

    render_X(data, out_path, *, variant="embedded", return_fig=False, **kwargs)

Variants:
- ``embedded``: figure for embedding in surrounding layouts (LaTeX, print,
  HTML), DPI 300, no in-figure title (the surrounding caption carries it)
- ``epub``: e-reader, DPI 150, same layout as embedded
- ``standalone``: one-file figure for standalone publication, DPI 150,
  in-figure title plus optional brand footer via BrandConfig
- ``web``: SVG for interactive frames (notebooks, web embeds), no title

``return_fig=True`` returns the matplotlib ``Figure`` instead of writing
to disk — used by Streamlit to embed via ``st.pyplot``.

The :data:`CHARTS` registry below pairs each chart with its data
provider and a stable ``chart_id`` for deep-linking and i18n lookup.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from enesys.viz.charts.build_time import compute_build_time_data, render_build_time_empirics
from enesys.viz.charts.montecarlo import compute_monte_carlo_data, render_monte_carlo
from enesys.viz.charts.rampup import compute_mix_rampup_data, render_mix_rampup_grid
from enesys.viz.charts.stress import compute_stress_rampup_data, render_stress_rampup_grid
from enesys.viz.charts.tornado import compute_tornado_data, render_tornado_sensitivity
from enesys.viz.charts.trajectory import compute_trajectory_data, render_lcoe_trajectory


@dataclass(frozen=True)
class ChartSpec:
    """Registry entry binding a chart's data provider to its renderer.

    Attributes
    ----------
    chart_id
        Stable kebab-style slug used for deep-linking (``?chart=tornado``)
        and as i18n key prefix.
    title_de, title_en
        Human-readable captions shown above the chart in the UI.
    compute
        Callable that returns the chart's data object. Accepts keyword
        arguments (``camp``, ``param_set``, …) depending on the chart.
    render
        Callable that draws the chart. Must accept ``return_fig: bool``
        and ``variant: str`` keyword arguments.
    varies_with_camp
        When ``True`` the chart is rendered twice (anchor camp vs.
        variant camp) in the Streamlit compare view. When ``False`` it
        is shown once full-width — used for empirical reference charts
        that do not depend on a camp (e.g. build-time empirics).
    """

    chart_id: str
    title_de: str
    title_en: str
    compute: Callable[..., Any]
    render: Callable[..., Any]
    varies_with_camp: bool = True


CHARTS: tuple[ChartSpec, ...] = (
    ChartSpec(
        chart_id="trajectory",
        title_de="Rolling-LCOE-Trajektorie 2026–2055",
        title_en="Rolling LCOE trajectory 2026–2055",
        compute=compute_trajectory_data,
        render=render_lcoe_trajectory,
    ),
    ChartSpec(
        chart_id="rampup",
        title_de="Mix-Hochlauf 2026–2055",
        title_en="Generation mix ramp-up 2026–2055",
        compute=compute_mix_rampup_data,
        render=render_mix_rampup_grid,
    ),
    ChartSpec(
        chart_id="stress",
        title_de="Winter-Stresstest 2026–2055",
        title_en="Winter stress test 2026–2055",
        compute=compute_stress_rampup_data,
        render=render_stress_rampup_grid,
    ),
    ChartSpec(
        chart_id="tornado",
        title_de="Hebel-Tornado 2026",
        title_en="Lever tornado 2026",
        compute=compute_tornado_data,
        render=render_tornado_sensitivity,
    ),
    ChartSpec(
        chart_id="montecarlo",
        title_de="Robustheit (Monte-Carlo)",
        title_en="Robustness (Monte Carlo)",
        compute=compute_monte_carlo_data,
        render=render_monte_carlo,
    ),
    ChartSpec(
        chart_id="build_time",
        title_de="KKW-Bauzeit-Empirie",
        title_en="Nuclear build-time empirics",
        compute=compute_build_time_data,
        render=render_build_time_empirics,
        varies_with_camp=False,
    ),
)


CHARTS_BY_ID: dict[str, ChartSpec] = {spec.chart_id: spec for spec in CHARTS}


__all__ = [
    "CHARTS",
    "CHARTS_BY_ID",
    "ChartSpec",
]
