"""Single-Source-of-Truth für externe Quellenwerte.

Diese Datei enthält **alle** Default-Werte aus externen Quellen wie der
BDEW-Strompreisanalyse und dem Destatis-Mikrozensus, die für die
Consumer-Brücke (Übersetzung Forward Cost → Endverbraucherpreis)
gebraucht werden.

**Beim nächsten Update einer externen Quelle nur diese Datei anfassen:**

1. Werte unten in den entsprechenden Konstanten-Block aktualisieren.
2. ``stand`` und ``url`` im selben Block nachziehen.
3. Im SOURCES.md einen neuen Tag anlegen (z.B. ``BDEW-STROMPREISE-2027``)
   und ``source_tag`` hier auf den neuen Tag setzen.
4. ``python -m enesys.extensions.consumers export`` aufrufen,
   um ``dist/external_sources.json`` neu zu generieren.
5. ``pytest tests/extensions/test_external_sources.py`` zur Konsistenz-
   Prüfung.

Die Consumer-Brücke (Endverbraucherpreis) hängt direkt an diesen
Werten. Der Forward Cost (volkswirtschaftliche Sicht) ist davon
**nicht** betroffen — diese Datei liefert nur Vergleichswerte für
die Übersetzung in eine Stromrechnung.

Konsumenten dieser Daten (z.B. das Web-Dashboard) holen sich
``dist/external_sources.json`` aus dem neutralen Build-Output-Verzeichnis.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path

from enesys.core.source_trace import find_repo_root

# ===========================================================================
# Quellen-Stand
# ===========================================================================


@dataclass(frozen=True)
class SourceStatus:
    """Metadaten zu einer externen Quelle."""

    source_tag: str  # SRC-Tag, muss in docs/SOURCES.md existieren
    publication: str  # Bibliographische Bezeichnung
    stand: str  # Datum oder Periode (z.B. "Mai 2026")
    url: str  # URL zur Online-Quelle
    methodik: str = ""  # optionale Methodik-Note (z.B. wie der Wert ermittelt wurde)


# ===========================================================================
# BDEW-Strompreisanalyse Mai 2026 — Haushalte und Industrie
# ===========================================================================
#
# WICHTIG: Beim Update auf eine spätere BDEW-Strompreisanalyse alle Werte
# in BDEW_2026 nachziehen, source_tag auf den neuen SOURCES.md-Tag setzen,
# und das JSON-Export-Script laufen lassen.

BDEW_2026_SOURCE = SourceStatus(
    source_tag="BDEW-STROMPREISE-2026",
    publication="BDEW: Strompreisanalyse Mai 2026 — Haushalte und Industrie",
    stand="Mai 2026",
    url="https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/",
    methodik=(
        "Gewichteter Durchschnitt aller verfügbaren Tarife "
        "(Tarifprodukte und Grundversorgung), inkl. Neukundentarife. "
        "Vertragsstruktur nach BNetzA. Basis: Haushalt 3.500 kWh/Jahr, "
        "Grundpreis anteilig enthalten. Industrie: einfacher Durchschnitt "
        "aus 5 Abnahmefällen 160.000 kWh/a bis 20 Mio. kWh/a, "
        "Mittelspannungs-Entnahme, Lieferstart Folgehalbjahr."
    ),
)


@dataclass(frozen=True)
class BdewHouseholdPrice:
    """BDEW-Haushaltsstrompreis-Komposition.

    Alle Werte in ct/kWh, Mittelwert über das Tarifangebot.
    Brutto = Netto + MwSt-Anteil; in der BDEW-Darstellung ist der
    MwSt-Anteil im Block ``steuern_abgaben_umlagen`` enthalten.
    """

    gross: float  # gesamt brutto (inkl. MwSt)
    procurement_sales: float  # Beschaffung & Vertrieb (Lieferanten-Block)
    grid_fees: float  # Netzentgelte
    taxes_charges_levies: float  # Steuern, Abgaben, Umlagen INKL. MwSt-Anteil
    vat_share: float  # MwSt-Anteil am Brutto (in ct/kWh)
    annual_consumption_kwh: int  # Bezugsbasis für die Werte


@dataclass(frozen=True)
class BdewIndustryPrice:
    """BDEW-Industriestrompreis (netto) für verschiedene Verbrauchsklassen."""

    kleine_mittlere: float  # 160.000 kWh - 20 Mio. kWh/Jahr (Neuabschluss)
    mittelgroße: float  # 20 - 70 Mio. kWh/Jahr (Vorjahresdaten, da Halbjahr fehlt)
    große: float  # 70 - 150 Mio. kWh/Jahr (Vorjahresdaten)


# Werte aus BDEW-Strompreisanalyse Mai 2026:
BDEW_2026_HOUSEHOLD = BdewHouseholdPrice(
    gross=37.0,
    procurement_sales=15.2,
    grid_fees=9.3,
    taxes_charges_levies=12.6,
    vat_share=37.0 * 19 / 119,  # 5,91 ct/kWh — MwSt aus Brutto rückgerechnet
    annual_consumption_kwh=3500,
)

BDEW_2026_INDUSTRY = BdewIndustryPrice(
    kleine_mittlere=16.7,
    mittelgroße=15.9,  # Stand 2025, da 2026-Halbjahr noch fehlt
    große=14.4,  # Stand 2025
)


# ===========================================================================
# Aufgeschlüsselte Steuern, Abgaben, Umlagen (Stand 2026)
# ===========================================================================
#
# Der BDEW-Block "Steuern, Abgaben, Umlagen" 12,6 ct/kWh enthält MwSt-Anteil.
# Aufgeschlüsselt (alle netto, ohne MwSt):
#   - Stromsteuer 2,05 ct/kWh (Stromsteuergesetz, unverändert)
#   - Konzessionsabgabe 1,32-2,39 ct/kWh (Mittel ~1,80, gemeindeabhängig)
#   - sonstige Umlagen ~2,84 ct/kWh (KWKG, Offshore, §19, AblaV; EEG-Umlage seit Juli 2022 = 0)
#   - MwSt-Anteil ~5,91 ct/kWh


@dataclass(frozen=True)
class TaxesChargesLevies2026:
    """Aufgeschlüsselte regulatorische Aufschläge (alle netto, ct/kWh)."""

    stromsteuer: float
    konzessionsabgabe: float  # Mittelwert über Gemeindegrößen
    konzessionsabgabe_min: float  # Großstadt
    konzessionsabgabe_max: float  # kleine Gemeinde
    sonstige_umlagen: float  # KWKG + Offshore + §19 + AblaV; EEG-Umlage = 0 seit Juli 2022
    mwst_pct: float  # Mehrwertsteuer in Prozent


TCL_2026 = TaxesChargesLevies2026(
    stromsteuer=2.05,
    konzessionsabgabe=1.80,
    konzessionsabgabe_min=1.32,
    konzessionsabgabe_max=2.39,
    sonstige_umlagen=2.84,  # rückgerechnet aus BDEW-Block 12,6 - 2,05 - 1,80 - 5,91
    mwst_pct=19.0,
)


# ===========================================================================
# Marktaufschlag-Kalibrierung
# ===========================================================================
#
# Der Marktaufschlag ist KEINE direkt extern beobachtbare Größe, sondern
# kalibriert: Differenz zwischen Modell-Forward-Cost und realem Marktpreis.
# Default 4,4 ct/kWh ergibt sich aus: WEITER-SO Brutto = BDEW-Realwert 37,0 ct.
# Wenn sich der BDEW-Realwert ändert, muss der Marktaufschlag neu kalibriert
# werden. Die Kalibrierungs-Logik: setze marktaufschlag so, dass
#   (16.25 - 7.0 + 9.3 + marktaufschlag + 1.5 + 2.05 + 1.80 + 2.84) * 1.19 = 37.0
# → marktaufschlag = 4.4 (gerundet).

MARKET_SURCHARGE_CALIBRATED = 4.4  # ct/kWh, kalibriert auf WEITER-SO heute = 37,0  [CALIBRATED: BDEW-Strompreisanalyse Mai 2026, Endkundenpreis 37,0 ct = Modellforward + Marktaufschlag, siehe Logik oben]


# ===========================================================================
# Destatis Mikrozensus 2024 — Privathaushalte
# ===========================================================================

DESTATIS_2024_SOURCE = SourceStatus(
    source_tag="DESTATIS-MZ-2024",
    publication="Statistisches Bundesamt: Mikrozensus 2024 — Haushalte und Familien",
    stand="2024 (Pressemitteilung 21. Juli 2025)",
    url="https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Haushalte-Familien/_inhalt.html",
    methodik=(
        "Mikrozensus 2024 — jährliche Haushaltserhebung. "
        "Hauptwohnsitzhaushalte: Haushalte, in denen mindestens eine Person "
        "am Hauptwohnsitz gemeldet ist. Werte bestätigt vom Umweltbundesamt: "
        "Bevölkerungsentwicklung und Struktur privater Haushalte (2024)."
    ),
)


@dataclass(frozen=True)
class DestatisHouseholds:
    """Destatis-Daten zu deutschen Privathaushalten."""

    anzahl_privathaushalte: int  # private Hauptwohnsitzhaushalte
    bevoelkerung: int  # Wohnbevölkerung in Deutschland
    mittlere_haushaltsgroesse: float  # Personen pro Haushalt
    anteil_einpersonen_pct: float  # Anteil Einpersonenhaushalte


DESTATIS_2024 = DestatisHouseholds(
    anzahl_privathaushalte=41_000_000,  # 41,0 Mio. (gerundet)
    bevoelkerung=83_600_000,  # 83,6 Mio. (Stichtag 31.12.2024)
    mittlere_haushaltsgroesse=2.0,
    anteil_einpersonen_pct=41.6,
)


# ===========================================================================
# Vorkrisen-Niveau (Vergleichsanker für Energiekrise-Nachhall-Argumentation)
# ===========================================================================

PRE_CRISIS_2021_PROCUREMENT_SALES_CT = 8.3  # ct/kWh  [SRC: BDEW-Strompreisanalyse 2021, Beschaffung+Vertrieb-Komponente vor Energiekrise]


# ===========================================================================
# Export für Web-Dashboard (JSON)
# ===========================================================================


def to_dict() -> dict:
    """Liefert alle Konstanten als nested dict für JSON-Export."""

    def _asdict(obj: object) -> object:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        return obj

    return {
        "_meta": {
            "schema_version": 1,
            "description": (
                "Single-Source-of-Truth für externe Quellenwerte. "
                "Generiert aus src/enesys/external_sources.py — "
                "diese JSON-Datei NICHT manuell editieren."
            ),
        },
        "bdew_2026": {
            "quelle": _asdict(BDEW_2026_SOURCE),
            "haushalt": _asdict(BDEW_2026_HOUSEHOLD),
            "industrie": _asdict(BDEW_2026_INDUSTRY),
        },
        "sau_2026": _asdict(TCL_2026),
        "marktaufschlag_kalibriert": MARKET_SURCHARGE_CALIBRATED,
        "destatis_2024": {
            "quelle": _asdict(DESTATIS_2024_SOURCE),
            "haushalte": _asdict(DESTATIS_2024),
        },
        "vorkrise_2021": {
            "beschaffung_vertrieb_ct": PRE_CRISIS_2021_PROCUREMENT_SALES_CT,
        },
    }


def write_json(target_path: Path | str | None = None) -> Path:
    """Schreibt die Konstanten als JSON.

    Default-Ziel: ``dist/external_sources.json`` relativ zum Repo-Root.
    Das Verzeichnis wird bei Bedarf angelegt.

    Konsumenten (z.B. das Web-Dashboard) holen sich die Datei aus diesem
    neutralen Build-Output-Verzeichnis und kopieren sie an ihren Zielort.
    Damit bleibt das Modell selbst-enthalten und weiß nicht, wer seine
    Outputs verwendet.
    """
    if target_path is None:
        repo_root = find_repo_root(Path(__file__).parent)
        target_path = repo_root / "dist" / "external_sources.json"
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = to_dict()
    target_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target_path


def main() -> None:
    """CLI: ``python -m enesys.extensions.consumers export``"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "export":
        path = write_json()
        print(f"Wrote {path}")
    else:
        # Default: Konstanten als kompakter Text-Report
        print("# consumers.py — Single-Source-of-Truth für externe Quellen\n")
        print(f"## BDEW Strompreisanalyse {BDEW_2026_SOURCE.stand}")
        print(f"   Tag: {BDEW_2026_SOURCE.source_tag}")
        print(f"   URL: {BDEW_2026_SOURCE.url}")
        h = BDEW_2026_HOUSEHOLD
        print(f"   Haushalt brutto: {h.gross} ct/kWh")
        print(f"     = Beschaffung+Vertrieb {h.procurement_sales}")
        print(f"     + Netzentgelte {h.grid_fees}")
        print(f"     + Steuern/Abgaben/Umlagen {h.taxes_charges_levies}")
        print()
        print("## Destatis Mikrozensus")
        print(f"   Tag: {DESTATIS_2024_SOURCE.source_tag}")
        d = DESTATIS_2024
        print(f"   Privathaushalte: {d.anzahl_privathaushalte:,}".replace(",", "."))
        print()
        print(f"## Marktaufschlag (kalibriert): {MARKET_SURCHARGE_CALIBRATED} ct/kWh")
        print()
        print("Aufruf 'python -m enesys.extensions.consumers export'")
        print("schreibt dist/external_sources.json")


if __name__ == "__main__":
    main()
