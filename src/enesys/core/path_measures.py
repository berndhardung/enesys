"""Kanonisches Maßnahmen-Inventar je Politik — „Was müsste passieren?".

Liefert je Politik die Vorbedingungs-Liste: Maßnahmen mit Adressat
(``V`` = Verbraucher / ``P`` = Politik), Hebel-Typ (``H`` = bindender
Modell-Hebel, dessen Variation die Pfad-Reue bewegt / ``K`` = narrativer
Kontext ohne Hebel), Abhängigkeits-Typ und Quellen-Tag.

Die konditionale Leitidee: jede Welt ist ein Versprechen mit Vorbedingungen —
erfüllt man sie nicht, hält die Kostenannahme dieses Pfades nicht. Der
``H``-Anspruch gilt nur für bindende Modell-Hebel; reine Kontext-Items ohne
Hebel (Dach-PV, dynamische Tarife) sind nicht enthalten.

Gerechnete Größen (LNG-Importmenge, ETS-Budget) werden aus dem Modell
abgeleitet und **gerundet** als griffige Größenordnung gezeigt — nicht
erfunden, keine Scheinpräzision. Das Winter-Defizit für die Abschaltlast-Zeile
wird von außen hereingereicht (der Aufrufer hat den Stresstest-Lauf schon).

Das Dashboard rendert nur diesen Export — keine Maßnahmen-Arithmetik im
Frontend.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fuel import co2_price_year
from .path_model import compute_path

_CAMP = "neutral_default"
_YEARS: tuple[int, ...] = tuple(range(2026, 2056))
_SNAPSHOT_YEAR = 2045
_GAS_FUELS: tuple[str, ...] = ("erdgas_inland", "erdgas_import", "lng")
_KWH_PER_M3_ERDGAS = 10.0  # Heizwert Erdgas; 1 TWh = 0,1 Mrd m³

_EE_SOCKEL_PATHS = ("ee_gas", "ee_h2")
_KKW_PATHS = ("kkw_gas", "kkw_h2")
_FOSSIL_PATHS = ("weiterso", "bestand")


@dataclass(frozen=True)
class Measure:
    """Ein Eintrag der „Was müsste passieren?"-Liste.

    Sprache: Deutsch; Englisch ist Frontend-i18n.
    ``quelle`` trägt echte ``SOURCES.md``-Tags; modell-abgeleitete Größen sind
    mit ``Modell:`` markiert, rein qualitative Vorbedingungen mit ``—``.
    """

    text: str
    adressat: str  # "V" | "P"
    hebel: str  # "H" | "K"
    typ: str  # "rate" | "binaer" | "folge" | "voraussetzung"
    quelle: str
    wert: str | None = None  # gerundete Größenordnung, z. B. "~26 Mrd m³/a"


# ---------------------------------------------------------------------------
# Gerechnete Größen (aus dem Modell, gerundet gezeigt)
# ---------------------------------------------------------------------------


def gas_twh_snapshot(pid: str) -> float:
    """Fossile Gasmenge (thermisch, TWh) im Zieljahr 2045."""
    r = compute_path(pid, [_SNAPSHOT_YEAR], camp=_CAMP)[0]
    return sum(r.fuel_used.get(f, 0.0) for f in _GAS_FUELS)


def lng_mrd_m3_per_year(pid: str) -> float:
    """Gas-Importmenge als Mrd m³/a (1 TWh = 0,1 Mrd m³ bei ~10 kWh/m³)."""
    return gas_twh_snapshot(pid) / _KWH_PER_M3_ERDGAS


def ets_budget_mrd_eur(pid: str) -> float:
    """Kumuliertes ETS-Budget 2026–2055 in Mrd €.

    ``Σ (co2_mt × co2_price_year)`` — dasselbe Integral wie die CO₂-System-
    Schicht der LCOE, damit der €-Betrag konsistent zur Kosten-Reue ist
    (Single Source, keine Pauschal-Konstante). Mt × €/t = M€; ``/1000`` → Mrd €.
    """
    results = compute_path(pid, list(_YEARS), camp=_CAMP)
    m_eur = sum(
        r.co2_mt * co2_price_year(year, _CAMP) for r, year in zip(results, _YEARS, strict=True)
    )
    return m_eur / 1000.0


def _round_lng(pid: str) -> str:
    return f"~{round(lng_mrd_m3_per_year(pid))} Mrd m³/a"


def _round_ets(pid: str) -> str:
    return f"~{round(ets_budget_mrd_eur(pid), -1):.0f} Mrd € bis 2055"


# ---------------------------------------------------------------------------
# Bausteine
# ---------------------------------------------------------------------------


def _ee_sockel() -> list[Measure]:
    """Gemeinsamer EE-Sockel — alle aktiven Pfade, KKW erbt ihn."""
    return [
        Measure(
            "EE & Netze ausbauen — Zubau über 17 GW/a (Ziel 22), Netz-Realisierungsgrad über 0,65",
            "P",
            "H",
            "rate",
            "EEG-2023; BNETZA-MASTR-2024",
        ),
        Measure(
            "Heizung und Mobilität elektrifizieren (Wärmepumpe, E-Auto)",
            "V",
            "H",
            "rate",
            "AGORA-2045",
        ),
        Measure(
            "H2-Hochlauf entscheiden (Speicher/Backup)",
            "P",
            "H",
            "rate",
            "BMWK-H2-STRATEGIE-2023",
        ),
    ]


def _kkw_zusatz() -> list[Measure]:
    """KKW-Zusatz — zusätzlich zum EE-Sockel."""
    return [
        Measure(
            "Bau & Finanzierung sichern — Realisierungsgrad 0,40 und einen "
            "verteidigbaren WACC, der nur über RAB/CfD/Bürgschaft kommt "
            "(staatliche Risiko-Übernahme, kein freier Wert)",
            "P",
            "H",
            "rate",
            "NAO-HPC-2017; WNA-2025",
        ),
        Measure(
            "Genehmigung um 2029 (damit die Inbetriebnahme erreichbar ist)",
            "P",
            "K",
            "binaer",
            "WNA-2025",
        ),
    ]


def _fossil_block(pid: str, max_deficit_gw: float) -> list[Measure]:
    """Referenzpfade WEITER-SO / BESTAND — echte, bezifferte Folgen."""
    measures = [
        Measure(
            "Verzicht auf flächendeckende Elektrifizierung einplanen — "
            "die Strommengen bleiben ungedeckt",
            "V",
            "H",
            "folge",
            "AGORA-2045",
        ),
        Measure(
            "Fossil weiterbetreiben — LNG-Import und ETS-Budget tragen",
            "P",
            "H",
            "rate",
            "EU-ETS-2026",
            wert=f"{_round_lng(pid)} · {_round_ets(pid)}",
        ),
        Measure(
            "Geopolitische Importstabilität (langfristige Lieferverträge)",
            "P",
            "K",
            "voraussetzung",
            "—",
        ),
    ]
    if pid == "weiterso":
        measures.append(
            Measure(
                "Abschaltlast-Verträge bei der Industrie sichern (Interruptible Loads)",
                "P",
                "H",
                "binaer",
                "Modell: winter_stress",
                wert=f"~{round(max_deficit_gw)} GW",
            )
        )
    if pid == "bestand":
        measures.append(
            Measure(
                "Klima- und Rechts-Ausschluss tragen — versorgungssicher, "
                "aber der KVBG-Kohleausstieg erzwingt den Umbau ohnehin",
                "P",
                "K",
                "folge",
                "KVBG",
            )
        )
    return measures


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def path_measures(pid: str, *, max_deficit_gw: float = 0.0) -> list[Measure]:
    """Maßnahmen-Liste („Was müsste passieren?") für eine Politik.

    ``max_deficit_gw``: max. Winter-Stresstest-Defizit des Pfades über die
    Jahre — vom Aufrufer hereingereicht (der den Stresstest-Lauf schon hat).
    Nur für die WEITER-SO-Abschaltlast-Zeile relevant.
    """
    if pid in _EE_SOCKEL_PATHS:
        return _ee_sockel()
    if pid in _KKW_PATHS:
        return _ee_sockel() + _kkw_zusatz()
    if pid in _FOSSIL_PATHS:
        return _fossil_block(pid, max_deficit_gw)
    raise ValueError(f"Unbekannte Politik: {pid!r}")
