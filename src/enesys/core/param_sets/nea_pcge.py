"""NEA-IEA PCGE 2020: atom-orientiertes Annahmen-Substrat.

Symmetrisches Gegenstück zu ``ariadne_pypsa.py`` (EE-leaning). Die
methodische Asymmetrie ist beabsichtigt: PCGE bewertet Kernkraft inkl.
Long-Term Operation (LTO) sehr günstig, weil die LTO-Overnight-Investments
auf der bereits amortisierten Bestandsflotte aufsetzen (Sunk-Discount im
LCOE-Framework). Ein robustes Pfad-Ranking unter beiden Substraten ist
das Ziel der Quervalidierung.

Daten-Herkunft
--------------
IEA/NEA (2020), »Projected Costs of Generating Electricity 2020«, 9th Ed.,
OECD Publishing, Paris. https://doi.org/10.1787/a6002f3b-en
223 Seiten, Stand 9. Dez. 2020.

Auswahl-Entscheidungen
----------------------
Region: OECD-Europa (Median), weil DE in den relevanten Substrat-Tech-
Tabellen fehlt (Tab. 3.2/3.3/3.4/3.5/3.6 enthalten keine DE-Datenpunkte;
einziger DE-Eintrag in Tab. 3.7a ist Hydro Run-of-river ≥5 MW, hier
nicht relevant). OECD-Europa-Sample = AT, BE, DK, FI, FR, HU, IT, NL,
NO, SK, SE, CH. Für Coal hat kein EU-Land geliefert → globaler OECD-
Median (AU/JP/US 650 MW-Konfigurationen).

WACC: 7 % real (PCGE-Standardspalte; 3 % und 10 % sind ebenfalls
verfügbar). Bei 10 % explodieren Nuclear-LCOEs (Tab. 3.13a).

Preisbasis: USD 2018 (PCGE-Tab. 2.2 dokumentiert FX-Konversion aller
nationalen Submissions auf 2018-Durchschnittskurs).

Currency-Konversion zu enesys-Konvention EUR_2025
-------------------------------------------------
Real-zu-real-Pfad (Caveat #12 in der PDF-Extraktion):
    Schritt 1: USD_2018 in EUR_2018 mit 2018-FX (~0.847 EUR/USD, ECB-Tagesmittel)
    Schritt 2: EUR_2018 in EUR_2025 mit Euro-HICP-Kumulinflation (~+21 %)
    Faktor: 0.847 × 1.21 ≈ 1.025

Nominal-zu-nominal-Pfad konvergiert nur bei stabiler Kreuzkurs-Phase;
divergiert hier um einige Prozent wegen EUR/USD-Bewegung zwischen 2018 und 2025.

Trajektorien
------------
PCGE 2020 liefert KEINE 2030/2040/2050-Trajektorien — alle Werte sind
Stichwerte für Commissioning 2025. Annex A1 dokumentiert nur die
Lernraten zur historischen Datenharmonisierung _auf_ 2025, das ist kein
Forward-Forecast. Konsequenz: alle Werte hier zeitkonstant; bewusste
Abwesenheit von EE-Lernrate.

Konvention
----------
Werte hard-coded im Code, nicht zur Laufzeit aus PDF/CSV geladen. Jede
PCGE-Edition-Welle (sobald die 10. Edition erscheint) erfordert bewusste
Re-Pflege.
"""

from __future__ import annotations

from enesys.core.param_sets._base import ParamSet, TrajectoryValue

# =============================================================================
# 1. ROHWERTE aus PCGE 2020 — OECD-Europa-Median, WACC 7 %, USD_2018
# =============================================================================

# Overnight CAPEX in USD_2018/kW. Quelle: Tab. 3.2–3.6.
_CAPEX_USD_2018: dict[str, float] = {
    # Renewables — EU-Median
    "solar_pv_utility": 807.0,  # Median aus DK(534,623), FR(708), HU(964),
    # IT(827,836), NL(807). Tab. 3.5.
    "onshore_wind": 1444.0,  # Median aus AT/BE/DK/FI/FR/IT/NL/NO/SE. Tab. 3.6a.
    "offshore_wind": 2361.0,  # Median aus BE(2361×2), DK(1721,2012), FR(3069). Tab. 3.6b.
    # Konventionelle — EU-Median
    "ccgt": 870.0,  # Median aus BE(767,974,1009), IT(590). Tab. 3.2a.
    # Romania(254) als Tieflohn-Outlier ausgeschlossen.
    "ocgt": 560.0,  # Median aus BE(531,590,670), IT(325). Tab. 3.2b.
    # Nuclear — siehe Caveats #6, #13
    "nuclear_gen3_new": 5466.0,  # Median aus FR-EPR(4013), Slovak-Rep(6920). Tab. 3.4a.
    # Korea(2157)+Russia(2271) als Nicht-OECD-EU ausgeschl.
    "nuclear_lto": 550.0,  # Median aus CH(550), FR(629), SE(444). Tab. 3.4b.
    # EGLTO-Range: 450–950 USD/kW.
    # Coal — globaler OECD-Median, weil 0 EU-Datenpunkte
    "coal": 2478.0,  # Arith. Mittel AU(2433)/JP(2419)/US-650MW(2582).
    # KR(1151) als Tieflohn-Outlier ausgeschlossen.
}

# FOM in % von CAPEX/Jahr (PCGE-Konvention). Reverse-Engineering aus
# Tab. 3.11–3.15 (LCOE-Breakdown O&M-Spalte) × Capacity-Factor × 8760 h ÷ CAPEX.
# Workaround-Annahme: gesamte O&M-Summe ist Fixed (überschätzt FOM, unter-
# schätzt VOM für thermische Tech — siehe Caveat #9 im _FEHLT-Dict).
_FOM_PCT: dict[str, float] = {
    "solar_pv_utility": 1.9,
    "onshore_wind": 3.6,
    "offshore_wind": 3.3,
    "ccgt": 5.8,
    "ocgt": 3.8,
    "nuclear_gen3_new": 2.0,
    "nuclear_lto": 15.5,  # Tab. 8.1 EGLTO explizit: FOM=85 USD/kW/a.
    # Bezug auf CAPEX 550: 85 / 550 = 15.45 % (gerundet 15.5).
    "coal": 2.9,
}

# VOM in USD_2018/MWh — nur dort gesetzt, wo PCGE saubere Trennung liefert.
# Tab. 3.11ff geben nur O&M-Summen; Trennung Fixed/Variable nicht möglich
# außer für nuclear_lto (Tab. 8.1 explizit).
_VOM_USD_2018_MWH: dict[str, float] = {
    "solar_pv_utility": 0.0,  # PCGE-Konvention: keine VOM für PV/Wind
    "onshore_wind": 0.0,
    "offshore_wind": 0.0,
    "nuclear_lto": 1.5,  # Tab. 8.1 EGLTO. Druckfehler-Anmerkung im PDF
    # (»USD 1.5/kWh«) — Plausibilität: USD 1.5/MWh.
    # ccgt, ocgt, nuclear_gen3_new, coal: NICHT gesetzt — VOM fließt in
    # _FOM_PCT-Annäherung. Override-Override würde doppelt zählen.
}

# Brennstoffpreise in USD_2018/MWh_thermisch. Quelle: Tab. 2.1 (Europe).
# Coal 6 000 kcal/kg entspricht 6.973 MWh_th/t; Gas 1 MBtu entspricht 0.29307 MWh_th.
_FUEL_USD_2018_MWH_TH: dict[str, float] = {
    "gas": 27.30,  # Europa: 8 USD/MBtu geteilt durch 0.29307 MBtu/MWh_th
    "coal": 10.76,  # Europa: 75 USD/t geteilt durch 6.973 MWh_th/t (6000 kcal/kg)
    "uranium": 3.08,  # 9.33 USD/MWh_el × 0.33 thermal eff in USD/MWh_th.
    # ACHTUNG: PCGE gibt nuclear-fuel-cycle in USD/MWh_el;
    # Konversion hier vorausgesetzt, dass enesys den
    # uran-Preis pro MWh_th einliest und Wirkungsgrad
    # separat in tech_inventory führt.
}

# Einheitlicher WACC (real, ohne Inflation). PCGE-Standardspalte 7 %.
# Achtung: TechEntry.wacc_pct ist als ANTEIL kodiert (0.07 = 7 %).
_WACC_SHARE: float = 0.07

# Currency-Konversion USD_2018 in EUR_2025, real-zu-real-Pfad (Caveat #12).
# 2018-FX ~0.847 EUR/USD × Euro-HICP-Kumulinflation der Periode 2018 bis 2025
# (~+21 %).
_USD_2018_TO_EUR_2025: float = 0.847 * 1.21


# =============================================================================
# 2. MAPPING — PCGE-Tech-Namen auf enesys-Tech-IDs
# =============================================================================
# Wichtige Tech-Splittung gegenüber Ariadne: PCGE differenziert intrinsisch
# zwischen nuclear_lto (Bestand-Verlängerung) und nuclear_gen3_new (EPR-
# Klasse). Mapping daher genauer als Ariadnes pauschales »nuclear« → alle
# drei kkw-Techs.

_TECH_MAPPING: dict[str, tuple[str, ...]] = {
    "solar_pv_utility": ("pv",),
    "onshore_wind": ("wind_onshore",),
    "offshore_wind": ("wind_offshore",),
    "ccgt": ("gas_h2ready",),
    "ocgt": ("erdgas_bestand",),
    "coal": ("kohle",),
    # LTO ≙ enesys' kkw_bestand (Bestand-Lebensverlängerung)
    "nuclear_lto": ("kkw_bestand",),
    # Gen-III-New ≙ kkw_neubau_epr; SMR als bewusste Annäherung mit-
    # gemappt, weil PCGE keine SMR-Werte hat (Caveat #7 im _FEHLT-Dict).
    "nuclear_gen3_new": ("kkw_neubau_epr", "kkw_neubau_smr"),
}

# enesys-Fuel-IDs: erdgas_inland / erdgas_import / lng / h2_inland /
# h2_import / bio_strom / uran / steinkohle / braunkohle.
# PCGE differenziert nicht zwischen Gas-Quellen — Mapping auf erdgas_import
# als heute dominante DE-Quelle (analog Ariadne).
_FUEL_MAPPING: dict[str, str] = {
    "gas": "erdgas_import",
    "coal": "steinkohle",
    "uranium": "uran",
}


# =============================================================================
# 3. BUILD-FUNKTION
# =============================================================================


def _to_eur_2025(value_usd_2018: float) -> float:
    """Konvertiert USD_2018 in EUR_2025 (real-zu-real-Pfad)."""
    return value_usd_2018 * _USD_2018_TO_EUR_2025


def build_trajectories() -> dict[str, TrajectoryValue]:
    """Konstruiert das Trajektorien-Dict für ``ParamSet.trajectories_factory``.

    Returns
    -------
    Dict mit Override-Keys ``"<tech_id>.<field>"`` bzw.
    ``"<fuel_id>.preis_eur_mwh"``. Werte sind float (PCGE ist Stichwert,
    keine Trajektorien — bewusst konstant über Reference-Years).
    """
    t: dict[str, TrajectoryValue] = {}

    for pcge_name, enesys_ids in _TECH_MAPPING.items():
        capex_eur = _to_eur_2025(_CAPEX_USD_2018[pcge_name])
        fom_pct = _FOM_PCT[pcge_name]
        opex_fix = capex_eur * fom_pct / 100.0
        vom_usd = _VOM_USD_2018_MWH.get(pcge_name)

        for enesys_id in enesys_ids:
            t[f"{enesys_id}.capex_eur_kw"] = capex_eur
            t[f"{enesys_id}.wacc_pct"] = _WACC_SHARE
            t[f"{enesys_id}.opex_fix_eur_kw_a"] = opex_fix
            if vom_usd is not None:
                t[f"{enesys_id}.opex_var_eur_mwh"] = _to_eur_2025(vom_usd)

    for pcge_fuel, enesys_fuel in _FUEL_MAPPING.items():
        t[f"{enesys_fuel}.preis_eur_mwh"] = _to_eur_2025(_FUEL_USD_2018_MWH_TH[pcge_fuel])

    return t


# =============================================================================
# 4. PARAMSET-INSTANZ
# =============================================================================

NEA_PCGE = ParamSet(
    name="nea_pcge",
    description=(
        "IEA/NEA PCGE 2020, 9. Edition — atom-orientiertes Annahmen-Substrat "
        "(OECD-Europa-Median, WACC 7 % real, USD_2018 → EUR_2025 real-zu-real)"
    ),
    source=(
        "IEA/NEA (2020), »Projected Costs of Generating Electricity 2020«, "
        "OECD Publishing, Paris. https://doi.org/10.1787/a6002f3b-en — "
        "Tab. 3.2/3.3/3.4/3.5/3.6 (Country-Submissions Overnight-CAPEX), "
        "Tab. 2.1 (Brennstoffpreise Europe), Tab. 8.1 (LTO FOM/VOM explizit)"
    ),
    reference_years=(2030, 2040, 2050),
    currency_year=2025,
    trajectories_factory=build_trajectories,
    caveats=(
        "PCGE rechnet LCOE über gesamte Lebenszeit mit Sunk-Discount für LTO; "
        "enesys rechnet Forward-Cost. Bei Übernahme der LTO-CAPEX bekommst du "
        "atom-leaning-Werte, die die bereits amortisierte Bestandsflotte "
        "implizit subventionieren — genau diese methodische Asymmetrie ist "
        "die Pointe des Substrats.",
        "Deutschland fehlt in PCGE-2020 für alle Substrat-Techs außer Hydro. "
        "Daher OECD-Europa-Median; für Coal globaler OECD-Median (0 EU-Daten).",
        "WACC 7 % real ist PCGE-Standardspalte. Direkter Vergleich mit Ariadne/"
        "PyPSA (5.36 % real) ist nur nach WACC-Korrektur fair — der WACC-"
        "Unterschied allein erklärt einen Teil der nuklearen LCOE-Asymmetrie.",
        "PCGE 2020 ist Stichtag-2025-Commissioning-Snapshot. KEINE Trajektorien "
        "für 2030/2040/2050 — alle Werte zeitkonstant. Bewusste Abwesenheit von "
        "EE-Lernrate erzeugt PV/Wind-Werte, die deutlich über 2030er-Ariadne-"
        "Schätzungen liegen.",
        "Speicher (Li-Ion/ACAES/Pumped, Tab. 3.9) sind im PDF, aber Kap. 6 zeigt "
        "LCOS-Methodik als nicht-kompatibel mit LCOE-Framework. Bewusst nicht "
        "im Substrat.",
        "LTO-CAPEX 550 USD/kW (CH-Median, EGLTO-Range 450–950) entspricht "
        "dem unteren Range-Ende. Defensiveres Substrat wäre 950 USD/kW (oberes "
        "Ende, Risk-Aufschlag für deutsche Konvoi-Reaktoren nach Stillstand). "
        "Auswahl 550 = symmetrisch zum atom-orientierten Argument.",
        "SMR (Section 8.4) ist im PCGE qualitativ behandelt, ohne konkrete "
        "CAPEX-Werte. kkw_neubau_smr wird hier auf nuclear_gen3_new gemappt — "
        "bewusste Annäherung, kein PCGE-Datum.",
        "Carbon-Aufschlag 30 USD/tCO2 ist in den LCOE-Tabellen 3.11ff bereits "
        "eingepreist (~25 USD/MWh für Kohle, ~10 für Gas). Die Overnight-CAPEX-"
        "Tabellen 3.2–3.6 sind davon unberührt; nur diese werden hier verwendet.",
        "FOM/VOM-Trennung nicht durchgehend: nur Nuclear-LTO hat saubere Werte "
        "aus Tab. 8.1. Für CCGT/OCGT/Coal/Nuclear-New ist _FOM_PCT eine "
        "Reverse-Engineering-Annäherung (»alle O&M ist Fixed«) — überschätzt "
        "FOM, unterschätzt VOM für thermische Tech.",
        "Edition-Recency: PCGE 2020 ist stand Mai 2026 noch immer aktuelle "
        "Edition. 10. Edition wäre 2025 fällig gewesen; NEA-Serien-Seite "
        "trägt seit August 2022 »no longer being actively updated«. "
        "Country-Submissions reflektieren ~2019er-Datenstand und kennen "
        "Vogtle-3/-4 (~16 100 USD/kW nominal) und Hinkley-Point-C-Repricing "
        "(~18 100 USD/kW nominal) nicht. Offshore-Wind-Inflations-Repricing "
        "seit 2022 fehlt ebenfalls.",
        "Flamanville-Diskrepanz innerhalb desselben Reports: Tab. 3.4a (FR-"
        "Submission NOAK) gibt EPR = 4 013 USD/kW, Tab. 8.2 (Flamanville-3 "
        "actual FOAK) = 8 620 USD/kW — Faktor 2.1×. Der Substrat-Median "
        "5 466 USD/kW liegt zwischen beiden, näher am Optimismus. Wer den "
        "Substrat noch atom-skeptischer kalibrieren will, sollte Tab. 8.2 "
        "als Quelle wählen.",
        "Inflations- und FX-Pfad gewählt: real-zu-real "
        "(USD_2018 × 0.847 EUR/USD × 1.21 Euro-HICP = × 1.025). "
        "Konsistent mit Ariadne/PyPSA, das ebenfalls Real-Preise führt.",
    ),
)


# =============================================================================
# 5. INSPEKTIONS-CLI
# =============================================================================
#
# Aufruf:    python -m enesys.core.param_sets.nea_pcge
# Zweck:     schnelle Sichtprüfung der erzeugten Overrides ohne Modell-Lauf.


def _main() -> None:
    print(NEA_PCGE.summary())
    print()
    print(f"USD_2018 → EUR_2025 Konversionsfaktor: {_USD_2018_TO_EUR_2025:.4f}")
    print()
    print("Generierte Overrides für 2045 (zeitkonstant — PCGE-Snapshot):")
    for key, value in sorted(NEA_PCGE.overrides(year=2045).items()):
        print(f"  {key:<40} = {value:>10.2f}")


if __name__ == "__main__":
    _main()
