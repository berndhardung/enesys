"""Sensitivitäts-Datenstrukturen für die sechs Pfade.

Modul-Rolle
-----------
Reine Daten-Container und konstante Setzungen für die Pfad-Sensitivität.
Berechnungslogik (LCOE, Tornado, Monte-Carlo, Schadens-Asymmetrie) lebt
in ``core.path_model`` (Mengen-Bilanz-Schicht). Hier verbleibt:

- Pfad-Namen und -Farben (``PATH_NAMES``, ``PATH_COLORS``)
- Erzeugungsmixes pro Pfad (``PATH_MIXES``)
- Lager-Bandbreiten und Tornado-Parameter (``CAMP_RANGES_2045``,
  ``TORNADO_PARAMS``)
- Snapshot-Dataclass (``PathSnapshotParams``) für UI-Bridge
- Schadens-Skalierungs-Formel (``damage_asymmetry_eur``)
- Bridge-Phase-Konstanten (``BRIDGE_PHASE_BIS_JAHR``,
  ``BRIDGE_MEHREMISSIONEN_KKW_VS_EE_MT``,
  ``TOTAL_MEHREMISSIONEN_KKW_VS_EE_MT``) für die strukturelle Aussage
  zur 30-Jahres-CO₂-Asymmetrie KKW-GAS vs. EE-GAS.

Konsumenten: ``core.path_model`` (Mengen-Bilanz), UI-Bridge,
Konsistenz-Tests.
"""

from dataclasses import dataclass

from .camp_ranges import CAMP_RANGES, camp_range

PATH_NAMES = ["WEITER-SO", "EE-GAS", "EE-H2", "KKW-GAS", "KKW-H2", "BESTAND"]
PATH_COLORS = {
    "WEITER-SO": "#7F7F7F",
    "EE-GAS": "#2E7D32",
    "EE-H2": "#66BB6A",
    "KKW-GAS": "#FFA000",
    "KKW-H2": "#E65100",
    # BESTAND-Lager-Pure-Play. Erdig-braun für die fossile
    # Bestandskontinuität (semantischer Kontrast zu WEITER-SO-Grau,
    # das die Status-quo-Fortschreibung darstellt).
    "BESTAND": "#6D4C41",
}


# Snapshot-Mix-Annahmen für jeden der sechs Pfade.
# Anteile der Gesamterzeugung. Müssen pro Pfad zu 1.0 summieren.
# Historischer Bezugspunkt aus dem Hauptmodell 2045-Stützjahr.
PATH_MIXES = {
    "WEITER-SO": {
        "pv": 0.20,
        "wind_onshore": 0.15,
        "wind_offshore": 0.05,
        "biomass": 0.04,
        "hydro": 0.03,
        "nuclear": 0.0,
        "kohle_backup": 0.20,  # Kohle-Restanteil 2045 (sinkend)
        "gas_backup": 0.33,  # Erdgas wachsend
    },
    "EE-GAS": {
        "pv": 0.40,
        "wind_onshore": 0.30,
        "wind_offshore": 0.15,
        "biomass": 0.04,
        "hydro": 0.03,
        "nuclear": 0.0,
        "gas_backup": 0.08,  # Gas+Bio-Methan+SNG (graduell grün)
    },
    "EE-H2": {
        "pv": 0.40,
        "wind_onshore": 0.30,
        "wind_offshore": 0.15,
        "biomass": 0.04,
        "hydro": 0.03,
        "nuclear": 0.0,
        "h2_backup": 0.08,
    },
    "KKW-GAS": {
        "pv": 0.25,
        "wind_onshore": 0.18,
        "wind_offshore": 0.10,
        "biomass": 0.03,
        "hydro": 0.03,
        "nuclear": 0.35,
        "gas_backup": 0.06,
    },
    "KKW-H2": {
        "pv": 0.25,
        "wind_onshore": 0.18,
        "wind_offshore": 0.10,
        "biomass": 0.03,
        "hydro": 0.03,
        "nuclear": 0.35,
        "h2_backup": 0.06,
    },
    # BESTAND als sechster Pfad. Bestands-Lager-Pure-Play:
    # Erdgas-dominant (~50 %), gedämpfter EE-Ausbau (~32 %), 10 %
    # Importe (LNG-Mix), 0 % Kohle (KVBG), 0 % Atom, kleiner Restbackup.
    # Mengen-Bilanz:
    #   0.18 + 0.10 + 0.04 + 0.03 + 0.03 + 0.50 + 0.10 + 0.02 = 1.00
    # Konsistent zu BestandParams (path_model.py) und AnhangC2055Params.
    "BESTAND": {
        "pv": 0.18,
        "wind_onshore": 0.10,
        "wind_offshore": 0.04,
        "biomass": 0.03,
        "hydro": 0.03,
        "nuclear": 0.0,
        "kohle_backup": 0.0,  # Entscheidung: kein Kohle-Backup in EE-Pfaden
        "gas_backup": 0.50,  # Erdgas-Programm (Bestand + Neubau ohne H2-ready)
        "import_share": 0.10,  # LNG-Mix als gas-äquivalente Lieferung
        "rest_backup": 0.02,  # Restbackup, klein weil Gas (0.50) hochflexibel
    },
}


@dataclass
class PathSnapshotParams:
    """Forward-Cost-Parameter für die 6-Pfad-Bewertung.

    Wird von der Mengen-Bilanz-Schicht (``core.path_model``) als
    Slider-Bridge-Datenstruktur konsumiert. Die LCOE-Berechnung selbst
    läuft in ``core.path_model`` (``compute_path``,
    ``baseline_all_paths``, ``tornado_path_analysis``,
    ``monte_carlo_all_paths``).

    Parametersätze:
    - LCOE pro Erzeugungstechnologie (ct/kWh)
    - Storage-Aufschläge (Kurz: Batterie, Saison: H2 oder Gas)
    - System-Aufschläge (Netz, CO2-Pönale)
    - Mix-Bezogen: KKW-Volllaststunden, Grünanteil-Gas
    """

    # Erzeugung (ct/kWh) — Defaults sind Mittelpunkte der LAGER_RANGES-Spannweiten
    pv_lcoe: float = 6.0  # [SRC: ISE-2024 — Mittelwert PV-LCOE 2045 nach Lernkurve]
    wind_onshore_lcoe: float = 6.5  # [SRC: ISE-2024 — Wind-onshore LCOE-Erwartung 2045]
    wind_offshore_lcoe: float = 9.0  # [SRC: ISE-2024 — Wind-offshore LCOE-Erwartung 2045]
    biomass_lcoe: float = 13.0  # [SRC: AGEB-2024 / FNR-Bioenergie-Berichte]
    hydro_lcoe: float = 6.0  # [SRC: ISE-2024 — Wasserkraft-Bestand-LCOE]
    nuclear_lcoe: float = (
        14.0  # [CALIBRATED: zwischen KERND-2024 Plan-LCOE 9 ct und EDF-HPC realisierten 17 ct]
    )

    # KKW-Volllaststunden (beeinflusst effektive LCOE im 80%-EE-System)
    nuclear_full_load_hours: float = (
        6500  # [CALIBRATED: zwischen ISE-2024 EE-System-Wert ~5500 und KERND-historisch ~7500]
    )

    # Backup (ct/kWh, mengen-gewichtet)
    h2_storage_lcoe: float = 32.0  # H2-Saisonspeicher  [CALIBRATED: BMWK-H2-STRATEGIE-2023 + DIW-H2-2026 Importpreise + Speicherkosten]
    gas_backup_lcoe: float = (
        14.0  # Erdgas + CO2-Pönale  [CALIBRATED: BNETZA-VS-2025 + CO2-Pönale 120 EUR/t]
    )
    kohle_backup_lcoe: float = (
        10.0  # Kohle (nur in WEITER-SO)  [CALIBRATED: Bestandskohle-LCOE inkl. CO2-Pönale]
    )

    # Speicher (Kurz)
    battery_lcos: float = 7.0  # [SRC: BNEF-2025-ESS — LCOS-Erwartung 2045 nach Lernkurve]

    # System (ct/kWh) — kalibriert für 2045-Forward-Cost
    grid_surcharge: float = 5.5  # Netz (mit Trassenausbau)  [SRC: BNETZA-VS-2025 — Bandbreite 6-9 ct, EE-optimistisches Ende]
    co2_price_eur_t: float = 120.0  # CO2-Preis in EUR/t (LAGER_RANGES-konsistent)  [SRC: EU-ETS-2026 — Erwartungspfad ETS-Preis 2045]
    # Hinweis: Stromsteuer/MwSt/Vertrieb gehören zum Endverbraucherpreis,
    # nicht zur volkswirtschaftlichen Forward Cost (siehe Forward-Cost-Methodik).
    # Sie sind deshalb nicht im Forward-Cost-Begriff dieses Modells enthalten.

    # Pfad-spezifisch
    weiterso_kohle_share: float = 0.20  # Kohle-Restanteil in WEITER-SO 2045  [ASSUMPTION: WEITER-SO-Pfad mit verzögertem Kohleausstieg vs. KVBG-Phaseout-Pfad]
    ee_gas_green_share: float = 0.0  # Anteil Bio-Methan/SNG in EE-GAS-Backup  [ASSUMPTION: konservative Default — Sensitivitätsparameter für grünen Hochlauf]
    bridge_gas_in_kkw: float = 0.0  # Bridge-Anteil 2045 (=0, weil KKW läuft)  [MODEL: in 2045 ist KKW vollständig in Betrieb, Bridge-Phase abgeschlossen]

    # KKW-WACC-Sensi-Hebel.
    # Neutraler Default 0,090 (Hinkley-realistisch ohne RAB).
    # Bandbreite 0,07 (Sizewell-RAB) bis 0,10 (Privatinvestor).
    wacc_nuclear: float = 0.090  # [SRC: CALIBRATED:HPC-Helm-Oxford+Sizewell-RAB]

    # NEP-Realisierungsgrad-Sensi-Hebel.
    # Default 0,65 entspricht dokumentiertem Realisierungsgrad der
    # ENLAG-Vorhaben (BNETZA-Quartalsmonitoring Q4 2025) und ist
    # Mittelwert der Lager-Range 0,4-0,9.
    nep_realization_rate: float = 0.65  # [SRC: BNETZA-MON-Q4-2025, ENLAG-WIKI]

    # KKW-Realisierungsgrad als symmetrisches Pendant zu
    # nep_realisierung_grad. Default 0,40 = empirisches Mittel
    # westlicher FOAK-Reaktoren. Lager-Range: 0,2 (Hinkley-Realität)
    # bis 1,0 (KKW-Lager-Optimum).
    nuclear_realization_rate: float = 0.40  # [SRC: WNA-2025]


# =====================================================================
# Tornado-Parameter-Liste (von Bridge/UI konsumiert für Slider-Mapping)
# =====================================================================

TORNADO_PARAMS = [
    "pv_lcoe",
    "wind_onshore_lcoe",
    "wind_offshore_lcoe",
    "nuclear_lcoe",
    "nuclear_full_load_hours",
    "h2_storage_lcoe",
    "battery_lcos",
    "grid_surcharge",
    "co2_price_eur_t",
    "wacc_nuclear",
    "nep_realization_rate",
    "nuclear_realization_rate",
]


# 2045-spezifische Lager-Bandbreiten-Overrides.
#
# Die LAGER_RANGES in lager_ranges.py beschreiben die aktuellen Lager-
# Positionen für *heute* (2026). Für die 2045-Snapshot-Bewertung müssen
# einzelne Bandbreiten transformiert werden, weil sich Defaults über die
# Zeit verschieben (z. B. Netzkosten sinken durch Trassenausbau,
# NIMBY-Lockerung, Bürgerenergie-Reform).
#
# Format: {param_name: (ee_optimistic_2045, atom_optimistic_2045)}
CAMP_RANGES_2045 = {
    # Netz: heute 6-9 ct (Default 7), 2045 nach Trassenausbau 4,5-7,5 ct
    # (Default 5,5). EE-Lager: schneller Ausbau, NIMBY-Lockerung.
    # Atom-Lager: weiterhin Verzögerungen, Erdkabel-Mehrkosten.
    "grid_surcharge": (4.5, 7.5),  # (ee_optimistic, atom_optimistic)
}


def camp_range_2045(param: str) -> tuple:
    """Liefert (lo, hi) für einen Parameter, mit 2045-Override falls
    vorhanden, sonst LAGER_RANGES-Bandbreite.

    Rückgabe ist immer (numerisch_kleiner, numerisch_größer).
    """
    if param in CAMP_RANGES_2045:
        a, b = CAMP_RANGES_2045[param]
        return (min(a, b), max(a, b))
    return camp_range(param)


def camp_value_2045(param: str, camp: str) -> float:
    """Liefert den lager-spezifischen Wert für 2045.

    lager: 'ee_optimistic', 'atom_optimistic', oder 'bestand_optimistic'.

    Für 'ee_optimistic' und 'atom_optimistic' wird zuerst LAGER_RANGES_2045
    geprüft (2045-Override) und dann LAGER_RANGES als Fallback. Für
    'bestand_optimistic' gibt es keine 2045-Overrides — wir nutzen direkt
    den LAGER_RANGES-Wert.
    """

    def _as_float(value: object) -> float:
        assert isinstance(value, int | float), (
            f"Erwarte numerischen Lager-Wert, bekam {type(value)}"
        )
        return float(value)

    if camp == "bestand_optimistic":
        return _as_float(CAMP_RANGES[param][camp])

    if param in CAMP_RANGES_2045:
        ee_val, atom_val = CAMP_RANGES_2045[param]
        if camp == "ee_optimistic":
            return ee_val
        elif camp == "atom_optimistic":
            return atom_val
        else:
            raise ValueError(f"Unbekanntes Lager: {camp}")
    return _as_float(CAMP_RANGES[param][camp])


# =====================================================================
# Lager-Presets als PathSnapshotParams (von Bridge/UI konsumiert)
# =====================================================================


def camp_preset_params(preset: str) -> PathSnapshotParams:
    """Lager-Preset als PathSnapshotParams.

    Presets:
    - 'neutral' = alle Defaults
    - 'ee_lager' = alle Parameter auf EE-optimistische Werte
    - 'atom_lager' = alle Parameter auf Atom-optimistische Werte
    - 'bestand_lager' = alle Parameter auf BESTAND-optimistische Werte
    - 'worst_case_ee' = EE-pessimistische Werte (höchste EE-LCOE,
      H2 teuer, Batterie teuer)
    """
    p = PathSnapshotParams()

    if preset == "neutral":
        return p

    if preset == "ee_lager":
        for key in TORNADO_PARAMS:
            if key not in CAMP_RANGES:
                continue
            setattr(p, key, camp_value_2045(key, "ee_optimistic"))
        return p

    if preset == "atom_lager":
        for key in TORNADO_PARAMS:
            if key not in CAMP_RANGES:
                continue
            setattr(p, key, camp_value_2045(key, "atom_optimistic"))
        return p

    if preset == "bestand_lager":
        # Bestands-Lager-Pure-Play.
        for key in TORNADO_PARAMS:
            if key not in CAMP_RANGES:
                continue
            spec = CAMP_RANGES[key]
            if "bestand_optimistic" in spec:
                setattr(p, key, camp_value_2045(key, "bestand_optimistic"))
            else:
                # Fallback: atom_optimistic, weil Bestands-Lager dem
                # Atom-Lager in EE-/H2-Skepsis ähnelt.
                setattr(p, key, camp_value_2045(key, "atom_optimistic"))
        return p

    if preset == "worst_case_ee":
        # Schlechtester Fall für EE: hohe PV-/Wind-LCOE, teure Batterie,
        # teures H2 — also Atom-optimistische Werte für EE-Hebel.
        # Aber: KKW-LCOE bleibt EE-optimistisch (also hoch), damit auch
        # KKW-Pfade nicht künstlich gut aussehen.
        for key in [
            "pv_lcoe",
            "wind_onshore_lcoe",
            "wind_offshore_lcoe",
            "h2_storage_lcoe",
            "battery_lcos",
        ]:
            setattr(p, key, camp_value_2045(key, "atom_optimistic"))
        for key in ["nuclear_lcoe", "nuclear_full_load_hours"]:
            setattr(p, key, camp_value_2045(key, "ee_optimistic"))
        return p

    raise ValueError(f"Unbekanntes Preset: {preset}")


# =====================================================================
# Schadens-Skalierungs-Formel (pure Mathematik, kein Modell-Bezug)
# =====================================================================


def damage_asymmetry_eur(
    diff_ct_per_kwh: float,
    demand_twh_per_year: float = 858.0,
    jahre: int = 30,
) -> float:
    """Geld-Schaden in Mrd EUR über die Pfad-Lebenszeit.

    Eine LCOE-Differenz von Δ ct/kWh über jahre Jahre bei
    demand_twh_per_year TWh/Jahr ergibt:
        Schaden_Mrd = Δ_ct_kwh / 100 × demand_twh × jahre

    Defaults orientieren sich am Modell-Default:
      - 858 TWh: path_model.py-Default (Modell-Bandbreite 858-953 TWh,
        unterhalb NEP-2025-Untergrenze 948).
      - 30 Jahre: Hauptmodell-Zeithorizont 2026-2055.

    >>> round(damage_asymmetry_eur(1.0), 0)
    257.0
    >>> round(damage_asymmetry_eur(2.85), 0)
    734.0
    """
    return diff_ct_per_kwh / 100.0 * demand_twh_per_year * jahre


# =====================================================================
# Bridge-Mehremissionen-Konstanten — Snapshot des Modell-Outputs.
# Werte sind aus ``compute_path`` für neutral_default reproduzierbar:
# kumulierte Differenz KKW-GAS minus EE-GAS, Bridge-Phase 2026-2046
# (vor erster KKW-Inbetriebnahme im Plan-Szenario; mit Default
# kkw_realisierungs_grad=0,40 verschiebt sich die erste KKW auf 2046+,
# die semantische Bridge-Definition bleibt).
#
# Diese Konstanten dienen als Verweis-Punkt für strukturelle Aussagen
# (Bridge-Anteil an Total ~85 %: die KKW-Inbetriebnahme-Verzögerung
# trägt den Hauptteil der KKW-GAS-Mehremissionen strukturell in die
# Bridge-Phase). Drift gegenüber dem aktuellen Modell-Lauf wird durch
# Anker-Tests im Privat-Tree gegen ein ±10-Mt-Toleranzband geprüft;
# externe Nutzer können die Werte über ``compute_path`` jederzeit selbst
# nachrechnen.
# =====================================================================
BRIDGE_PHASE_BIS_JAHR = 2046  # EPR-IBN im neutral_default-Lager
BRIDGE_MEHREMISSIONEN_KKW_VS_EE_MT = 265  # kumulierte Strom-CO₂-Differenz 2026-2046, neutral_default (Bridge: extern-CO₂ in EE-GAS und KKW-GAS identisch)
TOTAL_MEHREMISSIONEN_KKW_VS_EE_MT = 374  # kumulierte Strom-CO₂-Differenz 2026-2055, neutral_default
