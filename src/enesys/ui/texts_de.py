"""UI text blocks (DE) — German twin of :mod:`texts_en`.

Each block is a module-level string constant referenced from the
Streamlit pages via :func:`enesys.ui.i18n.load_texts`.
"""

from __future__ import annotations

# ===========================================================================
# Monte-Carlo methodology expander
# Used by: compare view, below the robustness chart
# ===========================================================================

MONTE_CARLO_METHODE_EXPANDER = (
    "**Methode:** Monte-Carlo-Analyse mit korreliertem Sampling. "
    "Für jede der 3.000 Iterationen wird **gleichzeitig** für "
    "alle Annahmen ein zufälliger Wert aus seiner plausiblen "
    "Bandbreite gezogen — KKW-Bauzeit, PV-Lernkurve, Gaspreis, "
    "Wasserstoff-Verfügbarkeit und etwa 20 weitere Parameter.\n\n"
    "**Korreliertes Sampling** bedeutet: wenn beispielsweise "
    "der Gaspreis hoch gezogen wird, wird auch die "
    "CO₂-Pönale-Annahme tendenziell höher gezogen — denn "
    "diese Größen sind in der Realität nicht unabhängig.\n\n"
    "**Bandbreiten** stammen aus der `LAGER_RANGES`-"
    "Datenstruktur, die für jeden Parameter die Untergrenze "
    "(typisch EE-Lager-Annahme) und Obergrenze (typisch "
    "Atom-Lager-Annahme) festlegt. Quellen siehe Footer und "
    "`docs/SOURCES.md`.\n\n"
    "**Methodische Quelle:** Robustheits-Methodik in "
    "`docs/methodik/methodology.md`."
)


# ===========================================================================
# Legal and liability disclaimer expander
# Used by: footer on every page
# ===========================================================================

RECHTLICHES_HAFTUNG_EXPANDER = (
    "**Open-Source-Lizenz.** Modell und Dashboard sind unter der "
    "MIT-Lizenz veröffentlicht. Quellcode, Dokumentation und Tests "
    "sind frei verfügbar zur Prüfung, Modifikation und "
    "Wiederverwendung — auch in kommerziellen Projekten — "
    "unter Einhaltung der Lizenzbedingungen.\n\n"
    "**Haftungsausschluss.** Diese Anwendung dient der "
    "Meinungsbildung, der Annahmen-Prüfung und der publizistischen "
    "Diskussion energiepolitischer Fragen. Sie stellt **keine "
    "Anlageberatung** im Sinne des Wertpapierhandelsgesetzes (WpHG), "
    "**keine Rechtsberatung** im Sinne des Rechtsdienstleistungs"
    "gesetzes (RDG) und **keine Steuerberatung** im Sinne des "
    "Steuerberatungsgesetzes (StBerG) dar. "
    "Die Ergebnisse sind Modell-Outputs unter den gewählten "
    "Annahmen, nicht Vorhersagen. Jede Entscheidung auf Basis "
    "dieser Ergebnisse erfolgt in eigener Verantwortung. Der "
    "Autor übernimmt keine Haftung für Schäden, die aus der "
    "Nutzung dieser Software entstehen.\n\n"
    "**Datenquellen.** Default-Werte stammen aus öffentlich "
    "zugänglichen Studien (Fraunhofer ISE, Bundesnetzagentur, "
    "BMWK/BMWE, Cour des Comptes, EWI Köln, EU-Kommission, "
    "BDEW, ZIV) sowie kommerziellen Quellen (BloombergNEF). "
    "Daten werden zitiert, nicht reproduziert — keine Tabellen, "
    "Diagramme oder substanziellen Textauszüge der Originalquellen "
    "sind in dieser Software enthalten. Quellenangaben in Tooltips "
    "und Footer.\n\n"
    "**Datenschutz.** Diese Streamlit-Anwendung speichert keine "
    "personenbezogenen Daten serverseitig. Slider-Eingaben werden "
    "ausschließlich in der lokalen Browser-Session verarbeitet "
    "und beim Schließen des Tabs verworfen. Bei Hosting auf "
    "einem öffentlichen Server gelten die Datenschutzbestimmungen "
    "des jeweiligen Betreibers (Server-Logs, IP-Adressen).\n\n"
    "**Verantwortlich nach §5 DDG und §18 Abs. 2 MStV:** "
    "Dr. Bernd Hardung. Kontakt: bernd@hardung.de. "
    "Vollständiges Impressum mit ladungsfähiger Anschrift: "
    "siehe Impressum-Seite des Hosting-Anbieters bzw. der "
    "betreffenden Domain."
)


__all__ = [
    "MONTE_CARLO_METHODE_EXPANDER",
    "RECHTLICHES_HAFTUNG_EXPANDER",
]
