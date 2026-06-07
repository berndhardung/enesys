"""Bilingual chart labels (DE / EN).

Centralises the strings that appear *inside* the matplotlib figures
(axis labels, panel titles, legend entries) so the Streamlit compare
view can render the same chart in either language.

Lookup convention: dotted ``{chart_id}.{role}`` keys, e.g.
``rampup.ylabel`` or ``trajectory.spread_ylabel``. The ``ChartLang``
literal mirrors :data:`enesys.ui.i18n.Lang` but is duplicated here so
``viz/charts/`` does not depend on the UI layer.
"""

from __future__ import annotations

from typing import Literal

ChartLang = Literal["de", "en"]


CHART_LABELS: dict[ChartLang, dict[str, str]] = {
    "de": {
        # --- shared ---
        "common.year": "Jahr",
        "common.deficit_legend": "Defizit",
        # --- rampup (mix_rampup_grid) ---
        "rampup.ylabel": "Stromerzeugung (TWh/a)",
        "rampup.demand_legend": "Strombedarf",
        # --- stress (stress_rampup_grid) ---
        "stress.ylabel": "GW (Dunkelflauten-Mittel)",
        "stress.peak_demand_legend": "Spitzenbedarf (Dunkelflaute)",
        # --- trajectory (lcoe_trajectory) ---
        "trajectory.window_label": "{n}-Jahre-Rolling-LCOE",
        "trajectory.ylabel_unit": "(ct/kWh)",
        "trajectory.xlabel": "Investitions-Startjahr",
        "trajectory.main_title": "Lebenszyklus-LCOE je Investitions-Startjahr ({start}–{end})",
        "trajectory.spread_ylabel": "Pfad-Spannweite max − min (ct/kWh)",
        "trajectory.spread_title": "Pfad-Spannweite",
        # --- tornado (tornado_sensitivity) ---
        "tornado.xlabel": "Forward Cost (ct/kWh)",
        "tornado.subtitle_suffix": " · Tornado",
        # --- montecarlo ---
        "montecarlo.ylabel": "Forward Cost (ct/kWh)",
        "montecarlo.violin_title": "LCOE-Verteilung pro Pfad",
        "montecarlo.winprob_xlabel": "Gewinnwahrscheinlichkeit vs. {ref}",
        "montecarlo.winprob_title": "Gewinn­wahrscheinlichkeit",
        # --- build_time ---
        "build_time.fid_lead_time": "FID-Vorlauf (Politik-Beschluss → Spatenstich)",
        "build_time.planned": "Geplante Bauzeit",
        "build_time.realised": "Realisierte / laufende Bauzeit",
        "build_time.corridor": "Empirie-Korridor (Gesamt-Frist {low}–{high} Jahre)",
        "build_time.ylabel": "Jahre vom Politik-Beschluss bis IBN",
    },
    "en": {
        # --- shared ---
        "common.year": "Year",
        "common.deficit_legend": "Deficit",
        # --- rampup ---
        "rampup.ylabel": "Generation (TWh/yr)",
        "rampup.demand_legend": "Demand",
        # --- stress ---
        "stress.ylabel": "GW (dark-doldrum average)",
        "stress.peak_demand_legend": "Peak demand (dark doldrum)",
        # --- trajectory ---
        "trajectory.window_label": "{n}-year rolling LCOE",
        "trajectory.ylabel_unit": "(ct/kWh)",
        "trajectory.xlabel": "Investment start year",
        "trajectory.main_title": "Lifecycle LCOE per investment start year ({start}–{end})",
        "trajectory.spread_ylabel": "Path spread max − min (ct/kWh)",
        "trajectory.spread_title": "Path spread",
        # --- tornado ---
        "tornado.xlabel": "Forward cost (ct/kWh)",
        "tornado.subtitle_suffix": " · Tornado",
        # --- montecarlo ---
        "montecarlo.ylabel": "Forward cost (ct/kWh)",
        "montecarlo.violin_title": "LCOE distribution per path",
        "montecarlo.winprob_xlabel": "Win probability vs. {ref}",
        "montecarlo.winprob_title": "Win probability",
        # --- build_time ---
        "build_time.fid_lead_time": "FID lead time (decision → groundbreaking)",
        "build_time.planned": "Planned construction time",
        "build_time.realised": "Realised / current construction time",
        "build_time.corridor": "Empirical corridor (total lead time {low}–{high} years)",
        "build_time.ylabel": "Years from political decision to IBN",
    },
}


# Tornado lever labels are baked into the model data structure
# (``core.sensitivity.TORNADO_LEVERS``) as German strings. This map
# translates the displayed text post-hoc — keyed by the German label,
# value is the English equivalent. Falls back to the German label if a
# new lever is added without an English translation.
TORNADO_LEVER_LABEL_DE_TO_EN: dict[str, str] = {
    "PV-CAPEX": "PV CAPEX",
    "Wind-Onshore-CAPEX (±25 %)": "Wind onshore CAPEX (±25 %)",
    "Wind-Offshore-CAPEX (±25 %)": "Wind offshore CAPEX (±25 %)",
    "KKW-EPR-CAPEX": "Nuclear EPR CAPEX",
    "KKW-SMR-CAPEX": "Nuclear SMR CAPEX",
    "Gas-H2-Ready-CAPEX (±25 %)": "Gas H₂-ready CAPEX (±25 %)",
    "Batterie-CAPEX (±25 %)": "Battery CAPEX (±25 %)",
    "PV-WACC": "PV WACC",
    "Wind-Onshore-WACC": "Wind onshore WACC",
    "KKW-EPR-WACC": "Nuclear EPR WACC",
    "KKW-SMR-WACC": "Nuclear SMR WACC",
    "Gas-H2-Ready-WACC": "Gas H₂-ready WACC",
    "Batterie-WACC": "Battery WACC",
    "CO₂-Preis €/t": "CO₂ price €/t",
    "Erdgas-Preis €/MWh": "Natural gas price €/MWh",
    "H₂-Inland-Preis €/MWh": "Domestic H₂ price €/MWh",
    "H₂-Import-Preis €/MWh": "Imported H₂ price €/MWh",
    "NEP-Realisierungsgrad": "NEP realisation rate",
    "KKW-Realisierungsgrad": "Nuclear realisation rate",
}


def translate_tornado_lever_label(de_label: str, lang: str = "de") -> str:
    """Translate a TORNADO_LEVERS label to the requested language.

    The core ``TORNADO_LEVERS`` table is German-only; this function
    translates the third-tuple-element labels post-hoc for the
    Streamlit EN render path.
    """
    if lang != "en":
        return de_label
    return TORNADO_LEVER_LABEL_DE_TO_EN.get(de_label, de_label)


def label(key: str, lang: str = "de", **fmt: object) -> str:
    """Look up a chart label by dotted key, optionally formatting placeholders.

    ``lang`` is accepted as a plain ``str`` (not the ``ChartLang``
    literal) so callers in the rendering layer can pass through the
    Streamlit-side ``Lang`` without an explicit cast; unknown codes
    fall back to the German label (defensive against typos and partial
    translations).
    """
    table = CHART_LABELS.get(lang) if lang in CHART_LABELS else None
    if table is None:
        table = CHART_LABELS["de"]
    template = table.get(key) or CHART_LABELS["de"].get(key, key)
    if fmt:
        return template.format(**fmt)
    return template


__all__ = [
    "CHART_LABELS",
    "ChartLang",
    "TORNADO_LEVER_LABEL_DE_TO_EN",
    "label",
    "translate_tornado_lever_label",
]
