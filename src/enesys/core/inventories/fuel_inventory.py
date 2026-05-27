"""Schema für `FUEL_INVENTORY`.

Brennstoff-Tabelle pro mengenbegrenzten Brennstoff.

PV, Wind, Wasser und Geothermie sind hier nicht erfasst — sie sind in
`TECH_INVENTORY` Brennstoff-äquivalent (Ressource = Standort = nicht
mengenbegrenzt im hier modellierten Umfang).

"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

MengenCallable = Callable[[int, str], float]  # (year, lager) -> twh
PreisCallable = Callable[[int, str], float]  # (year, lager) -> eur_mwh


@dataclass(frozen=True)
class FuelEntry:
    """Schema für einen Eintrag in `FUEL_INVENTORY`.

    Dauer-vs.-Boost-Trennung: `dauer_max` ist die
    Normalbetriebs-Höchstmenge pro Jahr, `boost_max` die
    Stress-Kurzfrist-Höchstmenge (Boost-Brennstoff für Dunkelflaute).
    `boost_max` kann gleich `dauer_max` sein bei Brennstoffen ohne
    Boost-Reserve.
    """

    fuel_id: str
    duration_max_twh_per_year: MengenCallable
    boost_max_twh_per_year: MengenCallable
    price_eur_mwh: PreisCallable
    co2_t_per_mwh_th: float
    source: str = ""
    derivation: str = ""

    def __post_init__(self) -> None:
        if not self.source and not self.derivation:
            raise ValueError(
                f"FuelEntry {self.fuel_id!r} muss source oder derivation "
                f"tragen (Magic-Number-Verbot)."
            )


FUEL_INVENTORY: dict[str, FuelEntry] = {}
"""Brennstoff-Inventar. Quellen an Primärquellen rückgekoppelt:
BVEG-Jahresbericht-2024 (Erdgas-Inland), BAFA-Großhandels-Statistik
(Erdgas-Preise), BMWK-LNGG + BNetzA-Terminal-Plan (LNG),
IEA-Gas-Market-Report-2024 (LNG-Spot), BMWK-Wasserstoff-Strategie-
Update-2023 + DENA-H2-Bilanz (H2-Inland-Trajektorien),
BNetzA-Kernnetz-Plan-2024 + H2Global-Auktionen-2024 (H2-Import),
UBA-2022-Biomassepotenziale + DBFZ-2023 + FNR-2024 (Bio-Strom),
WNA-2025 (Uran), BMWK-T45-Szenarien-2023 (Bedarfs-Trajektorien).

Offene Datenlücken (Uran-Detailstudie, Kohle-KVBG-Trajektorie für
Kraftwerke-Bestand) sind in den jeweiligen Funktions-Docstrings
markiert.
"""


# ---------------------------------------------------------------------------
# Brennstoff-Befüllung
# ---------------------------------------------------------------------------


# === Erdgas-Inland ========================================================
#
# DE-Inland-Gasförderung ist klein und rückläufig (BVEG-Statistik).
# 2024: ~2 TWh, sinkt durch Lagerstätten-Erschöpfung.


def _erdgas_inland_dauer_max(year: int, _camp: str) -> float:
    """Erdgas-Inland-Förderung. Linear 5 TWh/a (2026) → 1 TWh/a (2055).

    [SRC: BVEG (Bundesverband Erdgas, Erdöl und Geoenergie) Jahresbericht
    2024 — Inland-Förderung 2023 ~2,1 TWh; LBEG-Niedersachsen-Förder-
    statistik 2024 dokumentiert Lagerstätten-Erschöpfung ~5-8 %/a.
    Trajektorie 5→1 TWh/a entspricht ca. -5 %/a Auslauf-Rate, am unteren
    Rand der LBEG-Bandbreite; konservativ-höherer 2026-Startwert
    berücksichtigt offene Lagerstätten in NDS-Ost + Schleswig-Holstein.]
    """
    if year <= 2026:
        return 5.0
    if year >= 2055:
        return 1.0
    progress = (year - 2026) / (2055 - 2026)
    return 5.0 + progress * (1.0 - 5.0)


def _erdgas_inland_boost_max(year: int, camp: str) -> float:
    """Erdgas-Inland kann nicht geboosted werden (Lagerstätten-Limit)."""
    return _erdgas_inland_dauer_max(year, camp)


def _erdgas_inland_preis(_year: int, camp: str) -> float:
    """Erdgas-Inland-Preis ≈ Markt-Spot. Default 35 €/MWh, Bandbreite
    25-50 nach Lager.

    [SRC: BAFA-Erdgas-Preise 2024 (Großhandel-Mittel ~33 €/MWh nach
    Energie-Krise-Nachlauf), IEA-Welt-Preise Bandbreite Q4 2024.
    Lager-Spreizung folgt LAGER_RANGES-Konvention: ee_optimistic 50 €/MWh
    = höhere Importpreise erwartet, atom_optimistic 25 €/MWh = stabile
    Welt-Märkte angenommen. ETS-CO2-Aufschlag separat in Dispatch via
    co2_t_per_mwh_th × CO2-Preis aus LAGER_RANGES.]
    """
    camp_values = {
        "neutral_default": 35.0,
        "ee_optimistic": 50.0,
        "atom_optimistic": 25.0,
        "bestand_optimistic": 30.0,
    }
    return camp_values.get(camp, 35.0)


FUEL_INVENTORY["erdgas_inland"] = FuelEntry(
    fuel_id="erdgas_inland",
    duration_max_twh_per_year=_erdgas_inland_dauer_max,
    boost_max_twh_per_year=_erdgas_inland_boost_max,
    price_eur_mwh=_erdgas_inland_preis,
    co2_t_per_mwh_th=0.202,
    source=(
        "BVEG Jahresbericht 2024 (Inland-Förderung 2,1 TWh, Trajektorie). "
        "BAFA-Erdgas-Preise 2024. "
        "UBA Emissionsfaktor Erdgas 0,202 t CO2/MWh_th (Energiebilanz-"
        "Konvention)."
    ),
    derivation=(
        "Trajektorie 5→1 TWh/a über 2026-2055 entspricht -5 %/a Auslauf-"
        "Rate am unteren Rand der LBEG-Bandbreite (5-8 %/a). Lager-"
        "spezifische Preise (25-50 €/MWh) folgen LAGER_RANGES-Konvention. "
        "co2_t_per_mwh_th=0,202: UBA-Energiebilanz-Konvention für Erdgas-"
        "Verbrennung, identisch mit Erdgas-Import."
    ),
)


# === Erdgas-Import (Pipeline) =============================================


def _erdgas_import_dauer_max(year: int, _camp: str) -> float:
    """Erdgas-Import-Pipeline-Kapazität. BNetzA-Monitoring 2024:
    Import-Kapazität ~1.000 TWh/a. Tatsächlicher Import 2024 ~700 TWh,
    sinkt durch Wärmewende.

    Trajektorie 500 TWh/a (2026) → 100 TWh/a (2055): 2026-Wert spiegelt
    bereits Reduktion gegenüber 2024-Ist um ~30 % (Wärmepumpen-Hochlauf
    nach GEG-2024 + Industrie-Dekarbonisierung); 2055-Endwert 100 TWh
    folgt BMWK-Langfrist-Szenarien (Klimaneutralität-Ziel mit Restbedarf
    Industrie-Hochtemperatur-Prozesse + Gas-Kraftwerke-Reserve).

    [SRC: BNetzA-Monitoring-Bericht 2024, BMWK Langfrist-Szenarien 2023
    (TN-Strom-Szenario, T45-Szenario), Wärmepumpen-Hochlauf-Statistik
    BWP-Branchenstatistik 2024.]
    """
    if year <= 2026:
        return 500.0
    if year >= 2055:
        return 100.0
    progress = (year - 2026) / (2055 - 2026)
    return 500.0 + progress * (100.0 - 500.0)


def _erdgas_import_boost_max(year: int, camp: str) -> float:
    """Erdgas-Import boost = dauer (Pipeline-Kapazität ist hard limit)."""
    return _erdgas_import_dauer_max(year, camp)


def _erdgas_import_preis(_year: int, camp: str) -> float:
    """Pipeline-Erdgas-Preis. 2024 ~35 €/MWh, ETS-CO2-Aufschlag wirkt
    multiplikativ über CO2-Preis × Emissionsfaktor in Dispatch.

    [SRC: BAFA Erdgas-Import-Preise 2024 (Großhandels-Mittel Pipeline-
    Gas TTF/THE ~30-33 €/MWh), IEA Gas Market Report Q4 2024. Default
    30 €/MWh liegt leicht unter Inland wegen Pipeline-Skaleneffekten
    bei Großmengen-Import. ETS-CO2-Aufschlag separat in Dispatch.]
    """
    camp_values = {
        "neutral_default": 30.0,
        "ee_optimistic": 45.0,
        "atom_optimistic": 22.0,
        "bestand_optimistic": 28.0,
    }
    return camp_values.get(camp, 30.0)


FUEL_INVENTORY["erdgas_import"] = FuelEntry(
    fuel_id="erdgas_import",
    duration_max_twh_per_year=_erdgas_import_dauer_max,
    boost_max_twh_per_year=_erdgas_import_boost_max,
    price_eur_mwh=_erdgas_import_preis,
    co2_t_per_mwh_th=0.202,
    source=(
        "BNetzA-Monitoring 2024 (Pipeline-Import-Kapazität ~1.000 TWh/a, "
        "tatsächlicher Import ~700 TWh). "
        "BAFA-Erdgas-Preise. "
        "UBA Emissionsfaktor Erdgas 0,202 t CO2/MWh_th."
    ),
    derivation=(
        "Trajektorie 500→100 TWh/a folgt BMWK-Langfrist-Szenarien-Pfad "
        "(TN-Strom + T45 als Endwert-Anker bei 80-120 TWh Restbedarf). "
        "Pfad-Politik kann Verbrauch stark beeinflussen — "
        "das im Dispatch über demand-driven-Verbrauch statt fester "
        "Trajektorie. "
        "Boost = dauer: Pipeline-Kapazität ist hard limit, nicht "
        "kurzfristig erweiterbar (im Gegensatz zu LNG)."
    ),
)


# === LNG ==================================================================


def _lng_dauer_max(year: int, _camp: str) -> float:
    """LNG-Verträge-Kapazität. 2026 ~50 TWh/a (Wilhelmshaven, Brunsbüttel,
    Stade), wächst auf ~150 TWh/a bis 2030 (FSRU-Ausbauplan), dann
    Plateau bzw. Rückgang mit Wärmewende.

    [SRC: BMWK LNG-Beschleunigungsgesetz 2022 (LNGG, BGBl. I S. 802);
    BNetzA-Monitoring 2024 dokumentiert Terminal-Kapazitäten: Wilhelms-
    haven I (6,5 Mrd. m³/a ≈ 70 TWh, davon ~50 TWh nutzbar 2026),
    Brunsbüttel + Stade FSRU jeweils ~5 Mrd. m³ Plan-Stufe; festes
    Terminal Stade ab 2027 (Hanseatic Energy Hub 13,3 Mrd. m³).
    2030-Plateauwert ~150 TWh entspricht Vollausbau aller Terminal-
    Genehmigungen; Rückgang auf 60 TWh @ 2055 folgt BMWK-Wärmewende-
    Pfad (T45-Szenario).]
    """
    if year <= 2026:
        return 50.0
    if year <= 2030:
        progress = (year - 2026) / (2030 - 2026)
        return 50.0 + progress * (150.0 - 50.0)
    if year >= 2055:
        return 60.0
    progress = (year - 2030) / (2055 - 2030)
    return 150.0 + progress * (60.0 - 150.0)


def _lng_boost_max(year: int, _camp: str) -> float:
    """LNG-Boost: 200 TWh/a kurzfristig (Tanker-Spot-Umleitung,
    World-LNG-Markt 600 TWh/a). Strukturell höher als dauer.

    [SRC: IEA Gas Trade Statistics 2024 (Welt-LNG-Handel 580 Mt =
    ~700 TWh/a Welt-Kapazität); IEA Gas Market Report Q4 2024.
    Boost-Verfügbarkeit für DE 200 TWh/a entspricht ~30 % des Welt-
    Spot-Marktes-Anteils, der theoretisch via Atlantik-Tanker-Routen-
    Umleitung erreichbar wäre; konservativer Anker gegen Engpass-
    Szenario (2022-Winter-Erfahrung mit Spot-Umleitung von ~80 TWh/a
    skaliert auf Voll-Kapazität).]
    """
    base = _lng_dauer_max(year, "neutral_default")
    return max(base, 200.0)


def _lng_preis(_year: int, camp: str) -> float:
    """LNG-Spot-Preis. Höher als Pipeline-Gas (Liquefaction + Transport
    + Markt-Volatilität).

    [SRC: BAFA-LNG-Statistik 2024, IEA-Welt-LNG-Preise. Default 50 €/MWh,
    Bandbreite 40-80 nach Marktlage.]
    """
    camp_values = {
        "neutral_default": 50.0,
        "ee_optimistic": 75.0,
        "atom_optimistic": 40.0,
        "bestand_optimistic": 45.0,
    }
    return camp_values.get(camp, 50.0)


FUEL_INVENTORY["lng"] = FuelEntry(
    fuel_id="lng",
    duration_max_twh_per_year=_lng_dauer_max,
    boost_max_twh_per_year=_lng_boost_max,
    price_eur_mwh=_lng_preis,
    co2_t_per_mwh_th=0.205,
    source=(
        "BMWK LNG-Beschleunigungsgesetz 2022. "
        "BNetzA-Monitoring 2024 (Terminal-Ausbau Wilhelmshaven, "
        "Brunsbüttel, Stade). "
        "IEA Gas Trade Statistics 2024 (Welt-LNG ~700 TWh/a). "
        "BAFA-LNG-Preis-Statistik. "
        "UBA Emissionsfaktor LNG 0,205 t CO2/MWh_th (leicht höher als "
        "Pipeline-Gas wegen Liquefaction)."
    ),
    derivation=(
        "Trajektorie 50→150→60 TWh/a folgt BNetzA-Terminal-Ausbauplan "
        "(Wilhelmshaven I/II, Brunsbüttel, Stade FSRU, Stade festes "
        "Terminal ab 2027) plus BMWK-T45-Wärmewende-Rückbau. "
        "Boost 200 TWh/a aus IEA-Welt-LNG-Spot-Marktanteil-Skalierung. "
        "Die Dauer-vs-Boost-Trennung operationalisiert sich hier am "
        "deutlichsten — LNG-Spot-Reserve ist genau der Fall, für den "
        "die Trennung konzipiert ist."
    ),
)


# === H2-Inland (Elektrolyse-Produktion) ===================================


def _h2_inland_dauer_max(year: int, camp: str) -> float:
    """H2-Inland-Produktion verfügbar für den STROMSEKTOR.

    Trajektorie nach BMWK Wasserstoff-Strategie × Industrie-Vorrang-Quote:
    1 TWh @ 2026 → 20 TWh @ 2030 (von 40 TWh Brutto-Produktion, ~50 %
    für Strom-Backup) → 100 TWh @ 2045 (von ~200 TWh Brutto-Produktion,
    ~50 % für Strom-Backup nach Industrie/Verkehr-Vorrang).

    Verfügbare H2-Brutto-Menge nach BMWK-Strategie (50 GW × 4.000 VLH ≈
    200 TWh @ 2045) gegenüber dem Strom-Sektor-Anteil halbiert: T45-Strom
    2045 weist für den Stromsektor
    nur 50-100 TWh H2 aus — der Rest geht in Industrie (Stahl, Chemie),
    Verkehr (Schwerlast, Schiff, Luft) und Wärme. Realitätscheck 2024:
    Elektrolyseur-Aufbau <1 GW (von 10-GW-2030-Ziel) — Hochlauf läuft
    deutlich langsamer als BMWK-Strategie unterstellt.

    Lager-Variation: ee_optimistic skaliert nach oben, atom_optimistic
    drosselt (Atom-Lager glaubt nicht an Elektrolyse-Hochlauf).

    [SRC: BMWK Nationale Wasserstoff-Strategie Update Juli 2023 (10 GW
    Elektrolyse-Kapazität @ 2030 Brutto-Ziel); BMWK Langfrist-Szenarien
    T45-Strom 2045 (H2-Stromsektor-Anteil 50-100 TWh als Korridor);
    DENA-H2-Bilanz 2024 (VLH-Ankerwert 4.000 h); Lager-Multiplikatoren
    (1,3 / 0,6 / 0,4) folgen LAGER-Glaubens-Spreizung zum Realisierungs-
    grad. Industrie-Vorrang als operative Annahme: ~50 % der Brutto-
    Produktion bleibt für Stromsektor übrig.]
    """
    base_2030 = 20.0  # halbiert von 40 (50 % Stromsektor-Anteil)
    base_2045 = 100.0  # halbiert von 200 (50 % Stromsektor-Anteil)
    lager_mult = {
        "neutral_default": 1.0,
        "ee_optimistic": 1.3,
        "atom_optimistic": 0.6,
        "bestand_optimistic": 0.4,
    }.get(camp, 1.0)
    if year <= 2026:
        return 1.0 * lager_mult
    if year <= 2030:
        progress = (year - 2026) / (2030 - 2026)
        return (1.0 + progress * (base_2030 - 1.0)) * lager_mult
    if year >= 2045:
        return base_2045 * lager_mult
    progress = (year - 2030) / (2045 - 2030)
    return (base_2030 + progress * (base_2045 - base_2030)) * lager_mult


def _h2_inland_boost_max(year: int, camp: str) -> float:
    """H2-Inland kann boost = dauer, weil Elektrolyseure am Kapazitäts-
    Limit laufen müssen für maximale Produktion. Kurzfristige Boost-
    Reserve: H2-Speicher (Salzkavernen).

    Plausi: boost = dauer × 1,2 wegen Speicher-Entnahme.
    """
    return _h2_inland_dauer_max(year, camp) * 1.2


def _h2_inland_preis(year: int, camp: str) -> float:
    """H2-Inland-Erzeugungskosten. Heute 150-200 €/MWh; mit Elektrolyseur-
    Lernkurve und Strompreis-Trajektorie sinkend auf 80-120 €/MWh @ 2045.

    [SRC: EWI-2024 H2-Studie »Wasserstoff in Deutschland 2024«,
    BMWK-H2-Strategie Update 2023 (Preis-Bandbreite Anhang B),
    Hydrogen Council Path to Hydrogen Competitiveness 2024-Update.
    2026-Bandbreite 150-200 €/MWh entspricht heutigen Elektrolyseur-
    CAPEX 1.500-2.000 €/kW + EE-Strompreis 60-80 €/MWh; 2045-Bandbreite
    80-130 €/MWh folgt IEA-NZE-Lernkurve auf 500 €/kW + EE-Strom-
    Kostenreduktion auf 40-50 €/MWh.]
    """
    lager_2026 = {
        "neutral_default": 180.0,
        "ee_optimistic": 150.0,
        "atom_optimistic": 200.0,
        "bestand_optimistic": 200.0,
    }
    lager_2045 = {
        "neutral_default": 100.0,
        "ee_optimistic": 80.0,
        "atom_optimistic": 130.0,
        "bestand_optimistic": 130.0,
    }
    p_start = lager_2026.get(camp, 180.0)
    p_end = lager_2045.get(camp, 100.0)
    if year <= 2026:
        return p_start
    if year >= 2045:
        return p_end
    progress = (year - 2026) / (2045 - 2026)
    return p_start + progress * (p_end - p_start)


FUEL_INVENTORY["h2_inland"] = FuelEntry(
    fuel_id="h2_inland",
    duration_max_twh_per_year=_h2_inland_dauer_max,
    boost_max_twh_per_year=_h2_inland_boost_max,
    price_eur_mwh=_h2_inland_preis,
    co2_t_per_mwh_th=0.0,
    source=(
        "BMWK Nationale Wasserstoff-Strategie Update 2023 (10 GW @ 2030 Ziel). "
        "EWI-2024 H2-Studie (H2-Preis-Trajektorie). "
        "Wasserstoff-Inland aus Elektrolyse mit erneuerbarem Strom → "
        "co2 = 0 (Konvention grüner H2)."
    ),
    derivation=(
        "Trajektorie 1→40→200 TWh/a folgt BMWK-Strategie-Ziel × VLH 4.000 h. "
        "Lager-Multiplikatoren (1,3 / 0,6 / 0,4) folgen LAGER-Glaubens-"
        "Spreizung zum Realisierungsgrad (EE-Lager glaubt an Übererfüllung "
        "analog nep_realisierung_grad 0,85; Atom-/BESTAND-Lager 40-60 %). "
        "Boost = dauer × 1,2: Salzkavernen-Speicher-Reserve "
        "(BBPlG-2023 + GeoSpeicher-Studie DBI-Untergrund-2024 — "
        "Norddeutschland-Kapazität ~20 % der Jahres-Produktion)."
    ),
)


# === H2-Import =============================================================


def _h2_import_dauer_max(year: int, camp: str) -> float:
    """H2-Import-Kapazität verfügbar für den STROMSEKTOR.

    Kernnetz Bau bis 2032 (BNetzA), Hochlauf danach. 2026 = 0, 2032 =
    5 TWh, 2045 = 50 TWh (halbiert von ursprünglich 100 TWh, weil
    Industrie/Verkehr Vorrang haben — siehe `_h2_inland_dauer_max`
    Halbierung, siehe _h2_inland_dauer_max).

    [SRC: BMWK Wasserstoff-Importstrategie 2024 (Brutto-Importziel
    ~100 TWh @ 2045); BNetzA Wasserstoff-Kernnetz 2024 (9.700 km bis
    2032). 50 % Stromsektor-Anteil, Rest Industrie/
    Verkehr.]
    """
    base_2032 = 5.0  # halbiert von 10
    base_2045 = 50.0  # halbiert von 100
    lager_mult = {
        "neutral_default": 1.0,
        "ee_optimistic": 1.5,
        "atom_optimistic": 0.5,
        "bestand_optimistic": 0.3,
    }.get(camp, 1.0)
    if year < 2032:
        return 0.0
    if year <= 2032:
        return base_2032 * lager_mult
    if year >= 2045:
        return base_2045 * lager_mult
    progress = (year - 2032) / (2045 - 2032)
    return (base_2032 + progress * (base_2045 - base_2032)) * lager_mult


def _h2_import_boost_max(year: int, camp: str) -> float:
    """H2-Import boost = dauer (Pipeline-Kapazität hard limit, ähnlich
    Erdgas-Import)."""
    return _h2_import_dauer_max(year, camp)


def _h2_import_preis(_year: int, camp: str) -> float:
    """H2-Import-Preis. Tendenziell günstiger als Inland-Produktion
    (sonnenreiche Herkunftsländer mit niedrigerem Strompreis).

    [SRC: BMWK-Importstrategie 2024, IEA Hydrogen Outlook 2024.]
    """
    camp_values = {
        "neutral_default": 120.0,
        "ee_optimistic": 90.0,
        "atom_optimistic": 150.0,
        "bestand_optimistic": 150.0,
    }
    return camp_values.get(camp, 120.0)


FUEL_INVENTORY["h2_import"] = FuelEntry(
    fuel_id="h2_import",
    duration_max_twh_per_year=_h2_import_dauer_max,
    boost_max_twh_per_year=_h2_import_boost_max,
    price_eur_mwh=_h2_import_preis,
    co2_t_per_mwh_th=0.0,
    source=(
        "BMWK Wasserstoff-Importstrategie 2024. "
        "BNetzA Wasserstoff-Kernnetz 2024 (~9.700 km bis 2032). "
        "IEA Hydrogen Outlook 2024."
    ),
    derivation=(
        "Trajektorie 0→10→100 TWh/a folgt BNetzA-Kernnetz-Aufbauplan "
        "(9.700 km bis 2032 + Importzubindungen Rotterdam/Wilhelmshaven/"
        "Lubmin nach 2032). H2Global-Auktionen 2024 als Volumen-Indikator "
        "(Anlauf-Volumina ~0,3 TWh/a). Lager-Multiplikatoren "
        "spiegeln Glaubens-Spreizung zur Import-Realisierung: EE 1,5 "
        "(Importpartner-Kooperation stabil), Atom 0,5 (Geopolitisches "
        "Risiko hoch eingestuft), BESTAND 0,3 (importskeptisch)."
    ),
)


# === Bio-Strom (Brennstoff) ===============================================


def _bio_strom_dauer_max(_year: int, camp: str) -> float:
    """Bio-Strom-Brennstoff-Verfügbarkeit. UBA-Bio-Potenzial-Studie 2030
    sieht ~80 TWh/a für Strom-Verwendung als Obergrenze.

    [SRC: UBA-2022 »Biomassepotenziale in Deutschland« (Tabelle 5.1
    nennt Stromverwendungs-Obergrenze ~80 TWh/a aus nachhaltigen
    Quellen); DBFZ-2023 Strom-Verwendungs-Anteil ~50-60 TWh/a real-
    plausibel (Konkurrenz mit Wärme + stoffliche Nutzung). Default
    50 TWh/a entspricht DBFZ-konservativer Strom-Allokation,
    Lager-Spreizung 40-70 TWh/a folgt Konkurrenz-Annahmen.]
    """
    camp_values = {
        "neutral_default": 50.0,
        "ee_optimistic": 70.0,
        "atom_optimistic": 40.0,
        "bestand_optimistic": 50.0,
    }
    return camp_values.get(camp, 50.0)


def _bio_strom_boost_max(year: int, camp: str) -> float:
    """Bio-Strom kann unter Stress hochgefahren werden (Brennstoff-Lager
    vorhanden, Verbrennung scalable). Boost = dauer × 1,5 als Plausi."""
    return _bio_strom_dauer_max(year, camp) * 1.5


def _bio_strom_preis(_year: int, camp: str) -> float:
    """Bio-Brennstoff-Preis. Mittlere Werte aus FNR (Fachagentur
    Nachwachsende Rohstoffe) Holz-/Stroh-Preise.

    [SRC: FNR Brennstoff-Statistik 2024 (Hackschnitzel 30-35 €/MWh,
    Pellets 60-80 €/MWh, Stroh 20-30 €/MWh, Mischwerte für Bio-KWK
    Mittel ~70-90 €/MWh inkl. Logistik); DEHSt-Bericht-2024 für
    Energieholz-Markt-Spreizung. Default 90 €/MWh entspricht oberem
    Mittel (Pellets-dominierte Versorgung), Lager-Spreizung 75-110
    folgt Konkurrenz mit Wärmemarkt (ee_optimistic: Bio-Strom-
    Priorisierung → günstige Allokation; atom_optimistic: Wärme-
    Konkurrenz → teurer).]
    """
    camp_values = {
        "neutral_default": 90.0,
        "ee_optimistic": 75.0,
        "atom_optimistic": 110.0,
        "bestand_optimistic": 100.0,
    }
    return camp_values.get(camp, 90.0)


FUEL_INVENTORY["bio_strom"] = FuelEntry(
    fuel_id="bio_strom",
    duration_max_twh_per_year=_bio_strom_dauer_max,
    boost_max_twh_per_year=_bio_strom_boost_max,
    price_eur_mwh=_bio_strom_preis,
    co2_t_per_mwh_th=0.03,
    source=(
        "UBA Bio-Potenzial-Studie (~80 TWh/a Strom-Verwendung als "
        "Obergrenze). "
        "FNR Brennstoff-Statistik 2024."
    ),
    derivation=(
        "co2 0,03 t/MWh_th: nicht null wegen Verbrennungs-Lecks und "
        "Anbau-Emissionen, die nicht durch Pflanzen-Wachstum kompensiert "
        "werden. UBA-Methodik-Konvention. "
        "Boost = dauer × 1,5: Bio-Brennstoff-Lager kann unter Stress "
        "stärker entnommen werden."
    ),
)


# === Uran ==================================================================


def _uran_dauer_max(_year: int, _camp: str) -> float:
    """Uran-Verfügbarkeit faktisch unlimitiert (Weltmarkt, geringe Mengen
    pro MWh). Plausi-Obergrenze 500 TWh/a (deutlich über deutschem KKW-
    Bedarf bei Maximalausbau ~200 TWh).

    [SRC: WNA-2025 (Welt-Uran-Markt 60.000-80.000 t/a Förderung, würde
    1.000+ TWh/a stützen). WNA-Detailstudie nicht direkt zitiert.]
    """
    return 500.0


def _uran_boost_max(year: int, camp: str) -> float:
    """Uran-Boost = dauer (kein kurzfristiger Markt-Engpass für DE
    relevant)."""
    return _uran_dauer_max(year, camp)


def _uran_preis(_year: int, _camp: str) -> float:
    """Uran-Brennstoffpreis pro MWh_th sehr gering (~5 €/MWh_th).
    Brennelement-Wechsel-Kosten sind in opex_var der KKW-Tech.

    [SRC: WNA-2025, NEA-Uranium-Resources-2024.]
    """
    return 5.0


FUEL_INVENTORY["uran"] = FuelEntry(
    fuel_id="uran",
    duration_max_twh_per_year=_uran_dauer_max,
    boost_max_twh_per_year=_uran_boost_max,
    price_eur_mwh=_uran_preis,
    co2_t_per_mwh_th=0.0,
    source=(
        "WNA-2025 World Nuclear Association Statistik. "
        "NEA Uranium Resources, Production and Demand 2024."
    ),
    derivation=(
        "Welt-Uran-Markt für DE faktisch unlimitiert; Plausi-Obergrenze "
        "500 TWh/a deutlich über deutschem KKW-Maximal-Bedarf. "
        "Preis 5 €/MWh_th: Brennstoffkosten KKW historisch niedrig "
        "(Brennelement-Wechsel-Kosten in opex_var der Tech). "
        "co2 = 0 für Spaltungs-Reaktion (Kernspaltung emittiert kein "
        "CO2; Lebenszyklus-Emissionen aus Bau/Rückbau in CAPEX der Tech)."
    ),
)


# === Steinkohle ============================================================


def _steinkohle_dauer_max(year: int, _camp: str) -> float:
    """Steinkohle-Verbrauch. KVBG-Phaseout bis 2038 → linear 100 TWh/a
    (2026) → 0 (2038), danach 0.

    [SRC: KVBG, BGBl. I 2020 S. 1818; AGEB-2024 Steinkohle-Verbrauch
    Stromerzeugung.]
    """
    if year <= 2026:
        return 100.0
    if year >= 2038:
        return 0.0
    progress = (2038 - year) / (2038 - 2026)
    return 100.0 * progress


def _steinkohle_boost_max(year: int, camp: str) -> float:
    return _steinkohle_dauer_max(year, camp)


def _steinkohle_preis(_year: int, camp: str) -> float:
    """Steinkohle-Importpreis. ARA-Index plus DE-Transport.

    [SRC: BAFA-Steinkohle-Statistik, ARA-Index. Default 40 €/MWh.]
    """
    camp_values = {
        "neutral_default": 40.0,
        "ee_optimistic": 55.0,
        "atom_optimistic": 30.0,
        "bestand_optimistic": 35.0,
    }
    return camp_values.get(camp, 40.0)


FUEL_INVENTORY["steinkohle"] = FuelEntry(
    fuel_id="steinkohle",
    duration_max_twh_per_year=_steinkohle_dauer_max,
    boost_max_twh_per_year=_steinkohle_boost_max,
    price_eur_mwh=_steinkohle_preis,
    co2_t_per_mwh_th=0.338,
    source=(
        "KVBG, BGBl. I 2020 S. 1818 (Phaseout 2038). "
        "AGEB-2024 Stromerzeugung Steinkohle. "
        "BAFA-Steinkohle-Statistik (ARA-Index). "
        "UBA Emissionsfaktor Steinkohle 0,338 t CO2/MWh_th."
    ),
    derivation=(
        "Trajektorie 100→0 TWh/a folgt KVBG-Phaseout linear. "
        "Datenlücke: KVBG-Stilllegungs-Pfad nicht direkt aus "
        "BNetzA-Statistik zitieren."
    ),
)


# === Braunkohle ============================================================


def _braunkohle_dauer_max(year: int, _camp: str) -> float:
    """Braunkohle-Verbrauch. KVBG-Phaseout bis 2038 → linear 150 TWh/a
    (2026) → 0 (2038).

    [SRC: KVBG, BGBl. I 2020 S. 1818 (Phaseout 2038, lineare Konvention).
    AGEB-2024 Braunkohle-Stromerzeugung 2023 ~83 TWh; konservativ höherer
    2026-Startwert 150 TWh über Kraftwerks-Brennstoff-Energiebilanz
    (Bruttobrennstoff/η_el ≈ 83 TWh / 0,38 ≈ 218 TWh thermisch — Wert
    150 berücksichtigt Phaseout-Vorlauf 2024-2026 + Krisen-Reserve-Stand).]
    """
    if year <= 2026:
        return 150.0
    if year >= 2038:
        return 0.0
    progress = (2038 - year) / (2038 - 2026)
    return 150.0 * progress


def _braunkohle_boost_max(year: int, camp: str) -> float:
    return _braunkohle_dauer_max(year, camp)


def _braunkohle_preis(_year: int, _camp: str) -> float:
    """Braunkohle-Inlandspreis. Sehr günstig (Tagebau direkt am Kraftwerk).

    [SRC: BVEG / DEBRIV-Statistik 2024. Default 12 €/MWh.]
    """
    return 12.0


FUEL_INVENTORY["braunkohle"] = FuelEntry(
    fuel_id="braunkohle",
    duration_max_twh_per_year=_braunkohle_dauer_max,
    boost_max_twh_per_year=_braunkohle_boost_max,
    price_eur_mwh=_braunkohle_preis,
    co2_t_per_mwh_th=0.403,
    source=(
        "KVBG, BGBl. I 2020 S. 1818 (Phaseout 2038). "
        "AGEB-2024 Stromerzeugung Braunkohle. "
        "DEBRIV-Statistik (Tagebau-Kostenstrukturen). "
        "UBA Emissionsfaktor Braunkohle 0,403 t CO2/MWh_th."
    ),
    derivation=(
        "Trajektorie 150→0 TWh/a folgt KVBG-Phaseout linear. "
        "Preis 12 €/MWh ohne Lager-Spreizung: Tagebau-Inlands-"
        "Wertschöpfungskette stabil bis Phaseout."
    ),
)
