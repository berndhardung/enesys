"""Plotly-Adapter für die Visual-Style-Single-Source.

Spiegelt `viz.matplotlib_style` auf Plotly: dieselbe Palette, dieselbe
Schrift-Hierarchie, dieselbe Grid-Disziplin. Wird in Streamlit-Pages via
`apply_plotly_style(fig)` nach dem `fig = px.line(...)` o.ä. aufgerufen,
damit alle Charts konsistent aussehen.
"""

from __future__ import annotations

from typing import Any

from enesys.viz.theme import COLORS, FONTS


def plotly_template() -> dict[str, Any]:
    """Liefert ein Plotly-Template-Dict mit den zentralen Layout-Werten.

    Verwendung als globales Template:

        import plotly.io as pio
        from enesys.viz.plotly_style import plotly_template
        pio.templates["energiesystem"] = plotly_template()
        pio.templates.default = "energiesystem"
    """
    return {
        "layout": {
            "paper_bgcolor": COLORS["bg"],
            "plot_bgcolor": COLORS["bg"],
            "font": {
                "family": FONTS["main_sans"],
                "size": FONTS["size_tick"],
                "color": COLORS["text_dark"],
            },
            "title": {"font": {"size": FONTS["size_title"], "color": COLORS["text_dark"]}},
            "xaxis": {
                "gridcolor": COLORS["grid"],
                "linecolor": COLORS["text_muted"],
                "tickcolor": COLORS["text_muted"],
                "tickfont": {"color": COLORS["text_muted"]},
                "title": {"font": {"color": COLORS["text_dark"]}},
                "zeroline": False,
            },
            "yaxis": {
                "gridcolor": COLORS["grid"],
                "linecolor": COLORS["text_muted"],
                "tickcolor": COLORS["text_muted"],
                "tickfont": {"color": COLORS["text_muted"]},
                "title": {"font": {"color": COLORS["text_dark"]}},
                "zeroline": False,
            },
            "colorway": [
                COLORS["pfad_ee_gas"],
                COLORS["pfad_ee_h2"],
                COLORS["pfad_kkw_gas"],
                COLORS["pfad_kkw_h2"],
                COLORS["pfad_bestand"],
                COLORS["pfad_weiter_so"],
            ],
            "legend": {
                "font": {"size": FONTS["size_legend"], "color": COLORS["text_dark"]},
                "bgcolor": "rgba(0,0,0,0)",
            },
        }
    }


def apply_plotly_style(fig: Any) -> Any:
    """Wendet das Plotly-Template auf eine Figure an.

    Sollte in jeder Streamlit-Page nach Chart-Aufbau aufgerufen werden,
    bevor `st.plotly_chart(fig, ...)`. Gibt die Figure zurück, damit
    Method-Chaining möglich ist.
    """
    layout = plotly_template()["layout"]
    fig.update_layout(**layout)
    return fig
