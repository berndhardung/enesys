"""Fraunhofer-ISE-Stromgestehungskosten 2024: deutsches, EE-nahes Substrat.

Drittes Annahmen-Substrat neben ``ariadne_pypsa`` (PyPSA/Ariadne) und
``nea_pcge`` (IEA/NEA). Es schließt eine bewusste Lücke: ein
*deutsches*, mit eigener Methodik gerechnetes Kosten-Substrat aus der
EE-nahen Debatte, das gleichwohl Kernkraft mit abdeckt.

Quelle ≠ Lager
--------------
Die Fraunhofer-ISE-Studie ist eine *Quelle*, kein politisches Lager.
Ihr EE-freundliches Schlagzeilen-Ergebnis (»PV und Wind sind unter allen
Kraftwerksarten am günstigsten«) entsteht nicht aus verzerrten Kosten-
Inputs, sondern aus einer System-Annahme: in einem EE-dominierten
Energiesystem sinken die Volllaststunden regelbarer Kraftwerke (Tab. 4),
wodurch deren Fixkosten auf weniger kWh umgelegt werden. Auf der reinen
*Parameter*-Ebene ist die Studie nicht atom-feindlich — die Kernkraft-
CAPEX-Mitte (~11 000 EUR/kW aus dem Band 6 000–16 000) ist nahezu
deckungsgleich mit der enesys-neutralen Setzung von 11 000 EUR/kW und mit
dem Ariadne/Lazard-Wert (10 806).

Konsequenz für dieses Substrat: Importiert werden die *Kosten*-Parameter
(CAPEX, WACC, OPEX, Brennstoffpreise). Die ISE-eigene VLH-Annahme wird
NICHT als Override eingespielt — symmetrisch zu den beiden anderen
Substraten, die VLH ebenfalls dem enesys-System-State überlassen. So
bleibt der Quervergleich apples-to-apples: getauscht wird allein das
Kosten-Substrat, nicht die System-Logik. Die sinkende-VLH-Annahme ist als
Caveat dokumentiert; sie ist die eigentliche Pointe der ISE-Studie, aber
sie gehört in die System-Modellierung, nicht in ein Tech-Kosten-Substrat.

Daten-Herkunft
--------------
Fraunhofer ISE (Juli 2024), »Studie: Stromgestehungskosten Erneuerbare
Energien«, Kost et al. (8. Auflage der Reihe). Deutschland, reale Preise
Bezugsjahr 2024.
https://www.ise.fraunhofer.de/de/veroeffentlichungen/studien/studie-stromgestehungskosten-erneuerbare-energien.html

Verwendete Tabellen:
    - Tab. 1: Spezifische Anlagenkosten (CAPEX) EUR/kW, Stand 2024,
      Bandbreite niedrig–hoch je Technologie.
    - Tab. 2: Inputparameter — WACC real (Inflationsannahme 1,8 % p.a.),
      OPEX fix [EUR/kW/a], OPEX var [EUR/kWh], Lebensdauer.
    - Tab. 5: Brennstoffpreis-Trajektorien 2024/2030/2035/2040/2045
      [EUR/MWh_th].

Preisbasis und Konvention
-------------------------
ISE rechnet real in EUR_2024. enesys-Konvention ist EUR_2025; die Werte
werden mit einem dokumentierten realen Uplift (deutsche HICP ~2 %)
auf EUR_2025 normiert, damit der Vergleich mit Ariadne/NEA fair bleibt.
Werte hard-coded im Code, nicht zur Laufzeit aus dem PDF geladen — jede
neue ISE-Edition erfordert bewusste Re-Pflege.
"""

from __future__ import annotations

from enesys.core.param_sets._base import ParamSet, TrajectoryValue

# =============================================================================
# 1. ROHWERTE aus ISE-2024 — reale EUR_2024
# =============================================================================
# CAPEX-Mittelwerte je Technologie in EUR_2024/kW. In Klammern das von der
# Studie angegebene Band niedrig–hoch (Tab. 1); als Punktwert wird die
# Bandmitte verwendet. Die große LCOE-Spreizung der Studie rührt genau aus
# diesen Bändern (kombiniert mit dem VLH-Band) — siehe Caveats.

_CAPEX_EUR_2024: dict[str, float] = {
    "pv_freiflaeche": 800.0,  # Tab. 1: 700–900 (Freifläche > 1 MWp)
    "wind_onshore": 1600.0,  # Tab. 1: 1300–1900
    "wind_offshore": 2800.0,  # Tab. 1: 2200–3400 (inkl. Netzanbindung)
    "biogas": 4341.0,  # Tab. 1: 2894–5788
    "steinkohle": 2000.0,  # Tab. 1: 1700–2300 (Steinkohle, nicht Braunkohle)
    "gud": 1100.0,  # Tab. 1: 900–1300 (GuD/CCGT)
    "gasturbine": 575.0,  # Tab. 1: 450–700 (GT/OCGT)
    "kernkraft": 11000.0,  # Tab. 1: 6000–16000 (Neubau, 1200 MW)
}

# PV-Freifläche besitzt eine Lernkurve: 2045 sinkt die Anlageninvestition
# laut Studie auf 457–588 EUR/kW (Bandmitte ~522). Stützstellen 2024/2045.
_PV_CAPEX_TRAJECTORY_EUR_2024: dict[int, float] = {2024: 800.0, 2045: 522.0}

# Realer WACC als ANTEIL (Tab. 2; 0.078 = 7,8 %). enesys' TechEntry.wacc_pct
# ist trotz des Namens als Anteil kodiert.
_WACC_SHARE: dict[str, float] = {
    "pv_freiflaeche": 0.035,  # PV Freifläche real 3,5 %
    "wind_onshore": 0.039,  # real 3,9 %
    "wind_offshore": 0.060,  # real 6,0 %
    "biogas": 0.042,  # real 4,2 %
    "steinkohle": 0.068,  # real 6,8 %
    "gud": 0.064,  # real 6,4 %
    "gasturbine": 0.064,  # real 6,4 %
    "kernkraft": 0.078,  # real 7,8 % (höchster WACC im ISE-Set)
}

# Fixe Betriebskosten in EUR_2024/kW/a (Tab. 2). Biogas ist in der Studie
# als »4 % von CAPEX« angegeben → in build_trajectories berechnet.
_OPEX_FIX_EUR_2024: dict[str, float] = {
    "pv_freiflaeche": 13.3,
    "wind_onshore": 32.0,
    "wind_offshore": 39.0,
    "steinkohle": 37.0,
    "gud": 20.0,
    "gasturbine": 23.0,
    "kernkraft": 100.0,
}
_BIOGAS_FOM_PCT: float = 4.0  # Tab. 2: »4 % von CAPEX«

# Variable Betriebskosten in EUR_2024/kWh (Tab. 2). Umrechnung in EUR/MWh
# (×1000) erfolgt in build_trajectories. Brennstoffkosten sind hierin NICHT
# enthalten (separat über _FUEL_TRAJECTORY).
_OPEX_VAR_EUR_2024_KWH: dict[str, float] = {
    "pv_freiflaeche": 0.0,
    "wind_onshore": 0.007,
    "wind_offshore": 0.008,
    "biogas": 0.004,
    "steinkohle": 0.005,
    "gud": 0.005,
    "gasturbine": 0.004,
    "kernkraft": 0.007,
}

# Brennstoffpreis-Trajektorien in EUR_2024/MWh_th (Tab. 5). Wo nur ein Wert
# genannt ist, ist der Preis über alle Stützjahre konstant.
_FUEL_TRAJECTORY_EUR_2024: dict[str, TrajectoryValue] = {
    "erdgas": {2024: 38.0, 2030: 27.0, 2045: 27.0},  # Rückgang nach Krise
    "steinkohle": 11.6,  # konstant
    "braunkohle": 2.3,  # konstant
    "uran": 8.0,  # konstant
    "h2_gruen": {2024: 150.0, 2030: 150.0, 2035: 129.0, 2040: 111.0, 2045: 100.0},
    "biogas_substrat": {2024: 87.5, 2030: 99.6, 2035: 103.3, 2040: 106.7, 2045: 110.2},
}

# Realer Uplift EUR_2024 → EUR_2025 (deutsche HICP ~2 %). Wird auf alle
# monetären Größen angewandt, NICHT auf den WACC-Anteil.
_EUR_2024_TO_2025: float = 1.02


# =============================================================================
# 2. MAPPING — ISE-Tech-Namen auf enesys-Tech-IDs
# =============================================================================
# enesys »pv« = PV-Freifläche (Utility-Scale), analog zu Ariadne/NEA. Die
# ISE-Dach-/Agri-Varianten bleiben außen vor (Netz-PV dominiert die Pfade).
# enesys »kohle« = Steinkohle (Lazard-/Substrat-Konvention, nicht Braunkohle).
# 1:n bei Kernkraft: ISE modelliert nur Neubau (1200 MW); alle drei kkw-Techs
# bekommen denselben Neubau-Wert (wie Ariadne). Für kkw_bestand überschätzt
# das die Lebensverlängerung — Caveat.

_TECH_MAPPING: dict[str, tuple[str, ...]] = {
    "pv_freiflaeche": ("pv",),
    "wind_onshore": ("wind_onshore",),
    "wind_offshore": ("wind_offshore",),
    "biogas": ("bio",),
    "steinkohle": ("kohle",),
    "gud": ("gas_h2ready",),
    "gasturbine": ("erdgas_bestand",),
    "kernkraft": ("kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"),
}

# enesys-Fuel-IDs: erdgas_inland / erdgas_import / lng / h2_inland /
# h2_import / bio_strom / uran / steinkohle / braunkohle.
# ISE führt einen Gaspreis → erdgas_import (heute dominante DE-Quelle, analog
# Ariadne/NEA). Grüner Wasserstoff → h2_import UND h2_inland (ISE führt einen
# einzigen Grün-H2-Preis, unabhängig von der Herkunft).
_FUEL_MAPPING: dict[str, tuple[str, ...]] = {
    "erdgas": ("erdgas_import",),
    "steinkohle": ("steinkohle",),
    "braunkohle": ("braunkohle",),
    "uran": ("uran",),
    "h2_gruen": ("h2_import", "h2_inland"),
    "biogas_substrat": ("bio_strom",),
}


# =============================================================================
# 3. BUILD-FUNKTION
# =============================================================================


def _to_eur_2025(value: TrajectoryValue) -> TrajectoryValue:
    """Skaliert einen EUR_2024-Wert (float oder Trajektorie) auf EUR_2025."""
    if isinstance(value, (int, float)):
        return float(value) * _EUR_2024_TO_2025
    return {year: v * _EUR_2024_TO_2025 for year, v in value.items()}


def build_trajectories() -> dict[str, TrajectoryValue]:
    """Konstruiert das Trajektorien-Dict für ``ParamSet.trajectories_factory``.

    Returns
    -------
    Dict mit Override-Keys ``"<tech_id>.<field>"`` bzw.
    ``"<fuel_id>.preis_eur_mwh"``. CAPEX/OPEX/Fuel in EUR_2025; WACC als
    Anteil. PV trägt eine Lernkurve, sonst überwiegend zeitkonstant
    (ISE-2024-Snapshot mit publizierten Stützstellen).
    """
    t: dict[str, TrajectoryValue] = {}

    for ise_name, enesys_ids in _TECH_MAPPING.items():
        # CAPEX: PV-Freifläche als Trajektorie, sonst konstante Bandmitte.
        if ise_name == "pv_freiflaeche":
            capex = _to_eur_2025(dict(_PV_CAPEX_TRAJECTORY_EUR_2024))
        else:
            capex = _to_eur_2025(_CAPEX_EUR_2024[ise_name])

        wacc = _WACC_SHARE[ise_name]

        # OPEX fix: Biogas als % von CAPEX, sonst absoluter Wert.
        if ise_name == "biogas":
            capex_mid = _CAPEX_EUR_2024[ise_name] * _EUR_2024_TO_2025
            opex_fix: float = capex_mid * _BIOGAS_FOM_PCT / 100.0
        else:
            opex_fix = _OPEX_FIX_EUR_2024[ise_name] * _EUR_2024_TO_2025

        opex_var_mwh = _OPEX_VAR_EUR_2024_KWH[ise_name] * _EUR_2024_TO_2025 * 1000.0

        for enesys_id in enesys_ids:
            t[f"{enesys_id}.capex_eur_kw"] = capex
            t[f"{enesys_id}.wacc_pct"] = wacc
            t[f"{enesys_id}.opex_fix_eur_kw_a"] = opex_fix
            t[f"{enesys_id}.opex_var_eur_mwh"] = opex_var_mwh

    for ise_fuel, enesys_fuels in _FUEL_MAPPING.items():
        price = _to_eur_2025(_FUEL_TRAJECTORY_EUR_2024[ise_fuel])
        for enesys_fuel in enesys_fuels:
            t[f"{enesys_fuel}.preis_eur_mwh"] = price

    return t


# =============================================================================
# 4. PARAMSET-INSTANZ
# =============================================================================

ISE_LCOE = ParamSet(
    name="ise_lcoe",
    description=(
        "Fraunhofer ISE »Stromgestehungskosten Erneuerbare Energien« 2024 — "
        "deutsches, EE-nahes Kosten-Substrat (reale EUR_2024 → EUR_2025), "
        "Kernkraft mit abgedeckt"
    ),
    source=(
        "Fraunhofer ISE (Juli 2024), »Studie: Stromgestehungskosten Erneuerbare "
        "Energien«, Kost et al. — Tab. 1 (spezifische Anlagenkosten CAPEX), "
        "Tab. 2 (WACC real / OPEX / Lebensdauer), Tab. 5 (Brennstoffpreise). "
        "https://www.ise.fraunhofer.de/de/veroeffentlichungen/studien/"
        "studie-stromgestehungskosten-erneuerbare-energien.html"
    ),
    reference_years=(2024, 2035, 2045),
    currency_year=2025,
    trajectories_factory=build_trajectories,
    caveats=(
        "ISE ist eine Quelle, kein Lager. Ihr EE-freundliches Ergebnis entsteht "
        "aus einer System-Annahme (sinkende VLH regelbarer Kraftwerke im EE-"
        "System, Tab. 4), nicht aus verzerrten Kosten-Inputs. Auf Parameter-"
        "Ebene ist die Kernkraft-CAPEX-Mitte (~11 000 EUR/kW) deckungsgleich "
        "mit der enesys-neutralen Setzung und mit Ariadne/Lazard.",
        "Die ISE-VLH-Annahme (Kernkraft/Kohle/GuD sinken bis 2045 auf 2 000–"
        "4 000 h/a) wird NICHT als Override importiert — symmetrisch zu "
        "Ariadne/NEA, die VLH ebenfalls dem enesys-System-State überlassen. "
        "Damit bleibt der Quervergleich apples-to-apples; getauscht wird allein "
        "das Kosten-Substrat. Wer die ISE-VLH-Wirkung sehen will, muss sie über "
        "den enesys-Realisierungsgrad/System-State setzen, nicht hier.",
        "CAPEX-Punktwerte sind Bandmitten der ISE-Bänder (Tab. 1). Die große "
        "LCOE-Spreizung der Studie (Kernkraft 13,6–49,0 ct/kWh) rührt aus der "
        "Kombination von CAPEX-Band (6 000–16 000) und VLH-Band — beides wird "
        "hier auf je einen Punktwert reduziert.",
        "1:n-Mapping bei Kernkraft: ISE modelliert nur Neubau (1200 MW); alle "
        "drei enesys-kkw-Techs bekommen denselben Neubau-Wert. Für kkw_bestand "
        "(Lebensverlängerung) überschätzt das die CAPEX.",
        "WACC technologiespezifisch und real (Inflationsannahme 1,8 % p.a.): "
        "PV 3,5 % bis Kernkraft 7,8 %. Der Spread ist Teil der ISE-Methodik "
        "(höheres Investorenrisiko bei kapitalintensiven Technologien) und "
        "differiert von Ariadnes einheitlichem 5,36 % und NEAs einheitlichem "
        "7 %.",
        "Preisbasis real EUR_2024; Normierung auf EUR_2025 über realen Uplift "
        "×1,02 (deutsche HICP ~2 %). Konsistent mit der Real-Preis-Führung von "
        "Ariadne/NEA.",
        "CO2-Preis-Trajektorie der Studie (Tab. 7: unterer Pfad von 75 auf 175, "
        "oberer von 90 auf 375 EUR/t bis 2045) wird NICHT als globaler co2_price_eur_t-Override "
        "eingespielt — wie bei Ariadne/NEA bleibt der CO2-Preis eine "
        "Politik-Variable des enesys-Defaults, nicht Teil des Tech-Substrats.",
        "Speicher (Batterie), Brennstoffzelle, Agri-/Dach-PV, feste Biomasse, "
        "Wasserstoff-Gasturbine und Wärmeauskopplung sind in der Studie "
        "enthalten, werden aber nicht gemappt — enesys hat dafür keine 1:1-"
        "Tech-IDs bzw. modelliert Speicher auf Aggregat-Ebene.",
        "ISE rechnet reinen Technologie-LCOE ohne System-Effekte (Netz, Backup, "
        "Speicher) und ohne externalisierte Kosten (Endlagerung, Rückbau). Das "
        "ist die methodische Grenze der Quelle, kein Defizit des Substrats.",
    ),
)


# =============================================================================
# 5. INSPEKTIONS-CLI
# =============================================================================
#
# Aufruf:    python -m enesys.core.param_sets.ise_lcoe
# Zweck:     schnelle Sichtprüfung der erzeugten Overrides ohne Modell-Lauf.


def _main() -> None:
    print(ISE_LCOE.summary())
    print()
    print(f"EUR_2024 → EUR_2025 Uplift: {_EUR_2024_TO_2025:.3f}")
    print()
    print("Generierte Overrides für 2045 (interpoliert):")
    for key, value in sorted(ISE_LCOE.overrides(year=2045).items()):
        print(f"  {key:<40} = {value:>10.3f}")


if __name__ == "__main__":
    _main()
