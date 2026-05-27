"""Ariadne-PyPSA: Annahmen-Substrat der BMBF-Ariadne-Modellfamilie.

Dieses Set bildet die Default-Annahmen des PyPSA-Technology-Data-
Repositories ab — die zentrale Eingabe-Datenbank, die von PyPSA-Eur
und PyPSA-DE konsumiert wird. PyPSA-DE ist das vom BMBF im Rahmen des
Kopernikus-Projekts Ariadne entwickelte Referenzmodell für den
Energiesektor.

Daher die Namensgebung: »Ariadne-PyPSA« bezeichnet das Annahmen-Substrat
der Ariadne-Modellfamilie, technisch realisiert über PyPSA-Tech-Data.
Dies ist KEIN Replikat eines konkreten Ariadne-Szenarios (etwa »Fokus
Strom« oder »Technologiemix«); jene Szenarien überlagern szenario-
spezifische Constraints auf das gemeinsame Annahmen-Substrat.

Methodische Einordnung
----------------------
PyPSA-DE ist als Modell-Framework EE-orientiert (Default-Szenarien gehen
von massivem EE-Ausbau aus, Kernkraft taucht in Standard-Szenarien gar
nicht auf). Die *einzelnen Parameter-Werte* der CSVs sind jedoch sauber
primärquellen-gestützt: Lazard 16.0 (2023) für Nuclear, Danish Energy
Agency für Renewables, ENTSO-E/ENTSOG TYNDP 2024 für Brennstoffpreise.
Auf Parameter-Ebene ist Ariadne nicht atom-feindlich — der Nuclear-CAPEX
10 806 EUR/kW ist fast deckungsgleich mit der enesys-neutralen Setzung
von 11 000 EUR/kW.

Daten-Herkunft
--------------
PyPSA/technology-data Repository:
    https://github.com/PyPSA/technology-data

Trajektorie aus drei Snapshots:
    ``outputs/costs_2030.csv``, ``outputs/costs_2040.csv``,
    ``outputs/costs_2050.csv`` (Stand: master-Branch, 2026-05-21 —
    externe Datenquelle, Datum festgehalten für Reproduzierbarkeit)

Primäre Quellen-Zitate in den CSVs:
    - Lazard 16.0 (2023): Nuclear, Coal
    - Danish Energy Agency: Renewables, OCGT, CCGT, Electrolysis
    - ENTSO-E/ENTSOG TYNDP 2024: Brennstoffpreise (Gas, Coal, Uranium)

Konvention
----------
Werte werden hard-coded eingetragen, nicht zur Laufzeit aus den CSVs
geladen. Begründung: Reproduzierbarkeit ohne externe Datei-Abhängigkeit,
explizite Werte im Code; jedes Update aus dem PyPSA-CSV-Repo erfordert
bewusste Re-Pflege (statt stiller Drift bei externer CSV-Änderung).
"""

from __future__ import annotations

from enesys.core.param_sets._base import ParamSet, TrajectoryValue

# =============================================================================
# 1. ROHWERTE aus PyPSA/technology-data master @ 2026-05-21
# =============================================================================
# CAPEX-Trajektorien in EUR/kW (Preisbasis EUR_2025).
# Stützstellen: 2030 / 2040 / 2050. Wenn nur ein Wert genannt ist, ist
# der Wert über alle drei Jahre konstant (Lazard-Baseline).

_CAPEX_TRAJECTORY: dict[str, TrajectoryValue] = {
    # Erneuerbare — Lerneffekt vorhanden
    "solar-utility": {2030: 482.48, 2040: 403.38, 2050: 367.87},
    "onwind": {2030: 1383.31, 2040: 1305.83, 2050: 1286.47},
    "offwind": {2030: 2114.99, 2040: 1964.42, 2050: 1916.09},
    # Konventionelle — kaum Lerneffekt
    "OCGT": {2030: 581.39, 2040: 565.77, 2050: 550.14},
    "CCGT": {2030: 1108.72, 2040: 1088.68, 2050: 1068.64},
    "nuclear": 10805.70,  # Lazard 16.0 (2023), konstant
    "coal": 4812.02,  # Lazard 16.0 (2023), konstant
    # Wasserstoff — deutlicher Lerneffekt
    "electrolysis": {2030: 1886.00, 2040: 1508.80, 2050: 1257.33},
}

# Fixe Betriebskosten in %/Jahr von CAPEX (PyPSA-Konvention).
# Bei der Konversion zu EUR/kW/a in build_trajectories() berechnet,
# damit die Trajektorie konsistent zur CAPEX-Trajektorie bleibt.
_FOM_PCT: dict[str, float] = {
    "solar-utility": 2.48,
    "onwind": 1.22,
    "offwind": 2.32,
    "nuclear": 1.27,
    "OCGT": 1.78,
    "CCGT": 3.35,
    "coal": 1.31,
    "electrolysis": 4.00,
}

# Variable Betriebskosten in EUR/MWh (zeitkonstant in PyPSA-CSVs).
_VOM_EUR_MWH: dict[str, float] = {
    "nuclear": 4.46,
    "OCGT": 6.01,
    "CCGT": 5.61,
    "coal": 4.10,
    "onwind": 1.80,
    "offwind": 0.03,
    "solar-utility": 0.01,
}

# Brennstoffpreise in EUR/MWh_th — Trajektorie 2030/2040/2050.
# Wo nur 2030+2050 gegeben sind, interpoliert _resolve_at linear.
_FUEL_TRAJECTORY: dict[str, TrajectoryValue] = {
    "gas": {2030: 28.42, 2040: 25.59, 2050: 22.76},
    "coal": {2030: 7.82, 2050: 6.72},  # leichte Reduktion
    "uranium": 7.45,  # Lazard, konstant
    "lignite": 7.94,  # konstant in PyPSA-CSVs
}

# Einheitlicher Kapitalkostensatz nach PyPSA-Konvention (5.36% real).
# Achtung: TechEntry.wacc_pct ist trotz Namens als ANTEIL kodiert
# (0.0536 = 5.36%), nicht als Prozent-Zahl.
_WACC_SHARE: float = 0.0536


# =============================================================================
# 2. MAPPING — PyPSA-Tech-Namen auf enesys-Tech-IDs
# =============================================================================
# Vorsicht bei 1:n-Mappings: PyPSA hat eine pauschale ``"nuclear"``-
# Kategorie, enesys differenziert kkw_bestand / kkw_neubau_epr /
# kkw_neubau_smr. Alle drei bekommen denselben PyPSA-CAPEX, weil PyPSAs
# Quelle (Lazard 16.0) zwischen den Varianten ebenfalls nicht
# unterscheidet.

_TECH_MAPPING: dict[str, tuple[str, ...]] = {
    "solar-utility": ("pv",),
    "onwind": ("wind_onshore",),
    "offwind": ("wind_offshore",),
    "nuclear": ("kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"),
    "OCGT": ("erdgas_bestand",),
    "CCGT": ("gas_h2ready",),
    "coal": ("kohle",),
}

# enesys-Fuel-IDs: erdgas_inland / erdgas_import / lng / h2_inland /
# h2_import / bio_strom / uran / steinkohle / braunkohle.
# PyPSA differenziert nicht zwischen den drei Gas-Quellen — wir mappen
# auf erdgas_import als heute dominante Quelle.
_FUEL_MAPPING: dict[str, str] = {
    "gas": "erdgas_import",
    "uranium": "uran",
    "coal": "steinkohle",
    "lignite": "braunkohle",
}


# =============================================================================
# 3. BUILD-FUNKTION
# =============================================================================


def _scale_capex_to_opex_fix(capex: TrajectoryValue, fom_pct: float) -> TrajectoryValue:
    """Wendet FOM% auf eine CAPEX-Trajektorie an → EUR/kW/a.

    Wenn CAPEX zeitkonstant: opex_fix zeitkonstant.
    Wenn CAPEX Trajektorie: opex_fix folgt der CAPEX-Trajektorie.
    """
    if isinstance(capex, (int, float)):
        return float(capex) * fom_pct / 100.0
    return {year: value * fom_pct / 100.0 for year, value in capex.items()}


def build_trajectories() -> dict[str, TrajectoryValue]:
    """Konstruiert das Trajektorien-Dict für ``ParamSet.trajectories_factory``.

    Returns
    -------
    Dict mit Override-Keys im Format ``"<tech_id>.<field>"`` oder
    ``"<fuel_id>.preis_eur_mwh"``. Werte sind float (zeitkonstant) oder
    dict[int, float] (Stützstellen).
    """
    t: dict[str, TrajectoryValue] = {}

    for pypsa_name, enesys_ids in _TECH_MAPPING.items():
        capex = _CAPEX_TRAJECTORY[pypsa_name]
        fom = _FOM_PCT.get(pypsa_name)
        vom = _VOM_EUR_MWH.get(pypsa_name)

        for enesys_id in enesys_ids:
            t[f"{enesys_id}.capex_eur_kw"] = capex
            t[f"{enesys_id}.wacc_pct"] = _WACC_SHARE
            if fom is not None:
                t[f"{enesys_id}.opex_fix_eur_kw_a"] = _scale_capex_to_opex_fix(capex, fom)
            if vom is not None:
                t[f"{enesys_id}.opex_var_eur_mwh"] = vom

    for pypsa_fuel, enesys_fuel in _FUEL_MAPPING.items():
        t[f"{enesys_fuel}.preis_eur_mwh"] = _FUEL_TRAJECTORY[pypsa_fuel]

    return t


# =============================================================================
# 4. PARAMSET-INSTANZ
# =============================================================================

ARIADNE_PYPSA = ParamSet(
    name="ariadne_pypsa",
    description=(
        "PyPSA-Tech-Data Default-Annahmen 2030/2040/2050 — Annahmen-Substrat "
        "der BMBF-Ariadne-Modellfamilie"
    ),
    source=(
        "PyPSA/technology-data master @ 2026-05-21; primary citations: "
        "Lazard 16.0 (nuclear, coal), Danish Energy Agency (renewables, gas, "
        "electrolysis), ENTSO-E/ENTSOG TYNDP 2024 (fuel prices)"
    ),
    reference_years=(2030, 2040, 2050),
    currency_year=2025,
    trajectories_factory=build_trajectories,
    caveats=(
        "PyPSA-DE ist als Framework EE-orientiert (Default-Szenarien ohne Kernkraft); "
        "die Parameter-Werte sind jedoch primärquellen-gestützt und nicht atom-feindlich.",
        "Kein Replikat eines konkreten Ariadne-Szenarios — nur das Annahmen-Substrat.",
        "PyPSA modelliert Bauzeit-Verzögerung nicht als CAPEX-Multiplier; "
        "enesys' 17-Jahre-Flamanville-Empirie wird daher nicht abgebildet.",
        "Einheitlicher WACC 5.36% real — enesys differenziert sonst tech-spezifisch.",
        "Renewables-CAPEX basiert auf Danish-Energy-Agency-Studien mit langsamem "
        "Update-Zyklus, reflektiert nicht BNEF-Februar-2026-Anhebung.",
        "Speicher-Werte (Batterie, H2-Storage) sind im PyPSA-CSV vorhanden, werden "
        "aber nicht als Overrides exponiert — enesys modelliert Speicher auf "
        "LCOE-Aggregat-Ebene, nicht auf CAPEX-Komponentenebene.",
        "1:n-Mapping bei Nuclear: PyPSA hat nur 'nuclear'-Kategorie; enesys' drei "
        "Nuclear-Tech-IDs bekommen alle den gleichen Lazard-Wert.",
    ),
)


# =============================================================================
# 5. INSPEKTIONS-CLI
# =============================================================================
#
# Aufruf:    python -m enesys.core.param_sets.ariadne_pypsa
# Zweck:     schnelle Sichtprüfung der erzeugten Overrides ohne Modell-Lauf.


def _main() -> None:
    print(ARIADNE_PYPSA.summary())
    print()
    print("Generierte Overrides für 2045 (interpoliert):")
    for key, value in sorted(ARIADNE_PYPSA.overrides(year=2045).items()):
        print(f"  {key:<40} = {value:>10.2f}")


if __name__ == "__main__":
    _main()
