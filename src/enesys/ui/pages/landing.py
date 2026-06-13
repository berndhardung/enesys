"""Landing page — overview of the six paths and the headline finding.

Renders the headline-finding table anchored against BESTAND (the
politically defended status quo) and a brief explainer of the six paths.
The numbers are hardcoded to match the README; consistency is enforced
by ``tests/architecture/test_doku_hygiene.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from enesys.ui.i18n import load_texts, render_sidebar_lang_toggle
from enesys.version import get_base_version

QP_LANG = "lang"


@dataclass(frozen=True)
class PathRow:
    label: str
    cost_ct_kwh: float
    co2_mt: int
    delta_vs_bestand: str
    delta_vs_bestand_en: str
    highlight: bool = False


# Mirror of the headline-finding table in README.md (rolling 2026-2055,
# neutral_default camp, system-boundary CO₂).
HEADLINE_ROWS: tuple[PathRow, ...] = (
    PathRow(
        label="EE-GAS",
        cost_ct_kwh=16.79,
        co2_mt=2937,
        delta_vs_bestand="spart 1.933 Mt (−40 %)",
        delta_vs_bestand_en="saves 1,933 Mt (−40 %)",
        highlight=True,
    ),
    PathRow(
        label="WEITER-SO",
        cost_ct_kwh=16.97,
        co2_mt=4432,
        delta_vs_bestand="spart 438 Mt (Status quo ohne Entscheidung)",
        delta_vs_bestand_en="saves 438 Mt (status quo without decision)",
    ),
    PathRow(
        label="EE-H2",
        cost_ct_kwh=17.26,
        co2_mt=2689,
        delta_vs_bestand="spart 2.181 Mt (−45 %)",
        delta_vs_bestand_en="saves 2,181 Mt (−45 %)",
    ),
    PathRow(
        label="BESTAND",
        cost_ct_kwh=17.33,
        co2_mt=4870,
        delta_vs_bestand="(Baseline — politisch verteidigter Status quo)",
        delta_vs_bestand_en="(baseline — politically defended status-quo)",
    ),
    PathRow(
        label="KKW-GAS",
        cost_ct_kwh=17.57,
        co2_mt=3312,
        delta_vs_bestand="spart 1.558 Mt",
        delta_vs_bestand_en="saves 1,558 Mt",
    ),
    PathRow(
        label="KKW-H2",
        cost_ct_kwh=17.82,
        co2_mt=3022,
        delta_vs_bestand="spart 1.848 Mt",
        delta_vs_bestand_en="saves 1,848 Mt",
    ),
)


def _render_headline_table(lang: str) -> None:
    header = (
        ["Modell", "Kosten (Rolling 30 Jahre)", "Kumuliertes CO₂ (System-Grenze)", "vs BESTAND"]
        if lang == "de"
        else ["Model", "Cost (Rolling 30 years)", "Cumulative CO₂ (system boundary)", "vs BESTAND"]
    )
    lines: list[str] = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join("---" for _ in header) + "|")
    cost_unit = "ct/kWh"
    for row in HEADLINE_ROWS:
        label = f"**{row.label}**" if row.highlight else row.label
        cost = (
            f"**{row.cost_ct_kwh:.2f} {cost_unit}**"
            if row.highlight
            else f"{row.cost_ct_kwh:.2f} {cost_unit}"
        )
        co2 = f"**{row.co2_mt:,} Mt**" if row.highlight else f"{row.co2_mt:,} Mt"
        if lang == "de":
            co2 = co2.replace(",", ".")
        delta_text = row.delta_vs_bestand if lang == "de" else row.delta_vs_bestand_en
        delta = f"**{delta_text}**" if row.highlight else delta_text
        lines.append(f"| {label} | {cost} | {co2} | {delta} |")
    st.markdown("\n".join(lines))


def _render_paths_matrix(lang: str) -> None:
    """Render the 6-path × 2-axis matrix (base-load × backup)."""
    st.markdown("### " + ("The six paths" if lang == "en" else "Die sechs Pfade"))
    if lang == "en":
        st.markdown(
            "Two independent strategy axes: **base-load technology** "
            "(coal/gas, existing fleet, renewables, renewables + nuclear) "
            "and **backup fuel** (natural gas or hydrogen). The six "
            "pathways below cover the realistic combinations."
        )
        header = ["", "**Backup: Gas**", "**Backup: H₂**"]
        rows = [
            ["**Status quo / inaction**", "WEITER-SO", "—"],
            ["**Existing-fleet emphasis**", "BESTAND", "—"],
            ["**Renewables-only**", "EE-GAS", "EE-H2"],
            ["**Renewables + nuclear**", "KKW-GAS", "KKW-H2"],
        ]
    else:
        st.markdown(
            "Zwei unabhängige Strategie-Achsen: **Grundlast-Technologie** "
            "(Kohle/Gas, Bestand, Erneuerbare, Erneuerbare + Kernkraft) "
            "und **Backup-Brennstoff** (Erdgas oder Wasserstoff). Die sechs "
            "Pfade decken die realistischen Kombinationen ab."
        )
        header = ["", "**Backup: Gas**", "**Backup: H₂**"]
        rows = [
            ["**Status quo / Inaktion**", "WEITER-SO", "—"],
            ["**Bestands-Fokus**", "BESTAND", "—"],
            ["**Nur Erneuerbare**", "EE-GAS", "EE-H2"],
            ["**Erneuerbare + Kernkraft**", "KKW-GAS", "KKW-H2"],
        ]
    lines = ["| " + " | ".join(header) + " |", "|---|---|---|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    st.markdown("\n".join(lines))


def _render_camps(lang: str) -> None:
    """Render the camp-system explainer."""
    st.markdown("### " + ("The five camps" if lang == "en" else "Die fünf Lager"))
    if lang == "en":
        st.markdown(
            "Each pathway is evaluated under **five parameter camps** — "
            "each camp encodes a coherent worldview about how renewables, "
            "nuclear and fossil bridge technologies will evolve. The same "
            "model, run under different camps, produces different rankings — "
            "that is the symmetric sensitivity this app is built around."
        )
        st.markdown(
            "- **Neutral (Default)** — empirical midpoint, no political bias.\n"
            "- **EE camp** — optimistic on renewables build-out, "
            "  high CO₂ price.\n"
            "- **Nuclear camp** — optimistic on new-build nuclear, "
            "  low nuclear WACC.\n"
            "- **Existing-fleet camp** — pragmatic-conservative, slow "
            "  realisation rates.\n"
            "- **WEITER-SO** — status-quo extrapolation: market-driven, "
            "  no programme."
        )
    else:
        st.markdown(
            "Jeder Pfad wird unter **fünf Annahmen-Lagern** ausgewertet — "
            "jedes Lager kodiert eine in sich konsistente Welt-Anschauung "
            "darüber, wie sich Erneuerbare, Kernkraft und fossile "
            "Brücken-Technologien entwickeln. Dasselbe Modell unter "
            "unterschiedlichen Lagern liefert unterschiedliche Rankings — "
            "das ist die symmetrische Sensitivität, um die das Dashboard "
            "gebaut ist."
        )
        st.markdown(
            "- **Neutral (Default)** — empirische Mitte, keine "
            "  politische Färbung.\n"
            "- **EE-Lager** — optimistisch zum EE-Ausbau, hoher CO₂-Preis.\n"
            "- **Atom-Lager** — optimistisch zum KKW-Neubau, niedrige "
            "  KKW-WACC.\n"
            "- **Bestand-Lager** — pragmatisch-konservativ, gedämpfte "
            "  Realisierungsgrade.\n"
            "- **WEITER-SO** — Status-quo-Fortschreibung: markt-getrieben, "
            "  kein Programm."
        )


def _render_howto(lang: str) -> None:
    """Render a brief usage guide."""
    st.markdown("### " + ("How to use this" if lang == "en" else "So nutzt du das"))
    if lang == "en":
        st.markdown(
            "1. **Charts** — pick an anchor camp on the left and a variant "
            "   camp on the right; six core charts render side by side.\n"
            "2. **Override any slider** in the sidebar to push a single "
            "   assumption away from the variant camp's default — the "
            "   chart caption shows the override inline.\n"
            "3. **Sources** — every default in the model is one click away "
            "   from its primary citation. Slider tooltips deep-link there."
        )
    else:
        st.markdown(
            "1. **Charts** — links ein Anker-Lager wählen, rechts ein "
            "   Vergleichs-Lager; sechs Kern-Charts erscheinen nebeneinander.\n"
            "2. **Slider in der Sidebar überschreiben**, um eine Annahme "
            "   vom Variant-Lager-Default wegzuziehen — die Caption über "
            "   dem Chart zeigt den Override inline.\n"
            "3. **Sources** — jeder Default-Wert ist mit einem Klick mit "
            "   seiner Primärquelle verlinkt. Slider-Tooltips zeigen "
            "   dorthin."
        )


def _render_continue(lang: str) -> None:
    """Render the call-to-action navigation buttons."""
    st.markdown("### " + ("Continue" if lang == "en" else "Weiter"))
    col_charts, col_sources = st.columns(2)
    with col_charts:
        label = "📊 Open the charts" if lang == "en" else "📊 Charts öffnen"
        sub = (
            "Compare two camps side by side. Override any assumption."
            if lang == "en"
            else "Zwei Lager nebeneinander vergleichen. Jede Annahme überschreiben."
        )
        st.markdown(f"#### [{label}](charts?lang={lang})")
        st.markdown(sub)
    with col_sources:
        label = "📚 Browse the sources" if lang == "en" else "📚 Quellen durchsehen"
        sub = (
            "Every default in the model, backed by a primary citation."
            if lang == "en"
            else "Jeder Default im Modell, mit Primärquelle belegt."
        )
        st.markdown(f"#### [{label}](sources?lang={lang})")
        st.markdown(sub)


def render_landing_page() -> None:
    """Render the landing page (entry symbol consumed by st.navigation)."""
    lang = render_sidebar_lang_toggle()
    texts = load_texts(lang)

    title = (
        "enesys — Architecture of Germany's power system"
        if lang == "en"
        else "enesys — Architektur des Energiesystems"
    )
    st.title(title)

    intro_de = (
        "Ein offenes Modell vergleicht **sechs Pfade** für die deutsche "
        "Stromversorgung über 30 Jahre (2026–2055). Jeder Pfad kombiniert "
        "eine Erzeugungs­strategie (Erneuerbare, Kohle/Gas, Kernkraft) mit "
        "einer Backup-Strategie (Erdgas, Wasserstoff)."
    )
    intro_en = (
        "An open model compares **six pathways** for Germany's power supply "
        "over a 30-year horizon (2026–2055). Each pathway combines a "
        "generation strategy (renewables, coal/gas, nuclear) with a backup "
        "strategy (natural gas, hydrogen)."
    )
    st.markdown(intro_en if lang == "en" else intro_de)

    st.markdown("### " + ("Headline finding" if lang == "en" else "Kern­befund"))
    if lang == "en":
        st.markdown(
            "Rolling 30-year LCOE under default assumptions (``neutral_default`` "
            "camp); CO₂ on the **system boundary** — power-sector emissions plus "
            "external sector-coupling emissions from heating and mobility that "
            "remain fossil in WEITER-SO/BESTAND."
        )
    else:
        st.markdown(
            "Rolling-LCOE über 30 Jahre unter Default-Annahmen (Lager "
            "``neutral_default``); CO₂ auf der **System-Grenze** — "
            "Stromsektor-Emissionen plus externe Sektor-Kopplungs-Emissionen "
            "aus Heizung und Mobilität, die in WEITER-SO/BESTAND fossil bleiben."
        )
    _render_headline_table(lang)

    if lang == "en":
        st.markdown(
            "**EE-GAS is the cost optimum** and reduces cumulative CO₂ by "
            "40 % versus BESTAND, the politically defended status-quo path. "
            "**EE-H2** has the lowest CO₂, but the H₂ bonus over EE-GAS is "
            "small in the bridge phase (~250 Mt, −8 %). **WEITER-SO** is a "
            "status-quo extrapolation — what happens if no decision is taken — "
            "not a programme."
        )
    else:
        st.markdown(
            "**EE-GAS ist das Kostenoptimum** und senkt das kumulierte CO₂ "
            "um 40 % gegenüber BESTAND, dem politisch verteidigten Status quo. "
            "**EE-H2** hat das niedrigste CO₂, aber der H₂-Bonus über EE-GAS "
            "ist in der Brücken-Phase klein (~250 Mt, −8 %). **WEITER-SO** ist "
            "eine Status-quo-Fortschreibung — was geschieht, wenn keine "
            "Entscheidung getroffen wird — kein Programm."
        )

    st.divider()
    _render_paths_matrix(lang)

    st.divider()
    _render_camps(lang)

    st.divider()
    _render_howto(lang)

    st.divider()
    _render_continue(lang)

    st.divider()
    legal_label = "Legal & disclaimer" if lang == "en" else "Rechtliches & Haftung"
    with st.expander(legal_label):
        st.markdown(texts.RECHTLICHES_HAFTUNG_EXPANDER)
    license_label = "MIT License" if lang == "en" else "MIT-Lizenz"
    st.caption(
        f"enesys · {get_base_version()} · {license_label} · "
        f"[GitHub](https://github.com/berndhardung/enesys)"
    )


__all__ = ["render_landing_page"]
