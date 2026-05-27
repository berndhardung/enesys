"""Sektor-Kopplungs-Externe-Schicht: fossile Mehrkosten und CO₂ pro Pfad.

Pfade mit niedrigerem Strom-Demand (WEITER-SO, BESTAND) ersetzen die
missing Elektrifizierung durch fossile Wärme + Verbrenner-Mobility.
Diese Kosten + CO₂ fallen außerhalb des Strom-Systems an. Sie laufen
als externe Schicht **parallel** zum Strom-LCOE, keine LCOE-Vermengung.

Hand-Schätzung mit Drei-Quellen-Triangulation (UBA + JEC + AGORA):

- Fossile Wärme: 200 TWh-th × 0,22 t/MWh = 44 Mt/a bei voller Lücke
  (300 TWh = WSO-Lücke). UBA-CO₂-Faktor-Tabelle (BEHG-Basis):
  Erdgas 0,20 t/MWh-th, Heizöl 0,266 t/MWh-th; gewichteter Mix
  2026-2045 0,22-0,24 t/MWh-th. Quelle: UBA-Emissionsfaktoren-
  Tabelle (jährliche Veröffentlichung).
- Verbrenner-Mobility: 100 TWh × 0,30 t/MWh-WTW = 30 Mt/a.
  JEC WTW-Studie v5 (JRC/EUCAR/CONCAWE 2024) für DE-PKW-Diesel/Benzin-
  Mix: TTW ~0,25, WTW (inkl. Vorkette) 0,30-0,32 t/MWh-Treibstoff.
  WTW konsistent zur Strom-Vorkette-Bilanz dieses Modells.
- €-Kosten Wärme: 200 TWh × 80 €/MWh-th = 16 Mrd EUR/a (AGORA-2045
  Wärme-Preise-Korridor 70-90 €/MWh, Mittelpunkt).
- €-Kosten Mobility: 100 TWh × 100 €/MWh = 10 Mrd EUR/a (Sprit-
  Preise inkl. EnSt-äquivalentem Pönale-Anteil, AGORA-2045).
- CO₂-Pönale wird über lager-spezifischen ``_co2_price_year``
  monetarisiert (asymmetrische Welt-Belief-Spreizung
  100/130/150/160 €/t).

Skalierung auf pfad-spezifische Lücke (= 840 − pfad_demand_twh):
Faktor = Lücke / 300 TWh (WSO-Voll-Lücke), linear.

Quellen-Triangulation:

- UBA-Emissionsfaktoren (Erdgas/Heizöl-Mix für Wärme).
- JEC WTW v5 (JRC/EUCAR/CONCAWE 2024, Mobility-WTW).
- AGORA »Klimaneutrales Deutschland 2045« (TWh-Mengen + Preise).
"""

from __future__ import annotations

from enesys.core.path_model import _resolve_co2_price

_DEMAND_FULL_SECTOR_COUPLING_TWH: float = 840.0
"""Strombedarf 2045 bei vollständiger Sektor-Kopplung (EE/KKW-Pfade).
[SRC: BNetzA NEP 2037/2045 Mittelpunkt, Demand-Curve-Anker.]"""

_GAP_FULL_TWH: float = 300.0
"""Pfad-Voll-Lücke für WEITER-SO (Differenz 840 − 540). Skalierungs-
Bezugsgröße für Wärme/Mobility-Aufteilung."""

_FOSSIL_HEAT_TWH_FULL: float = 200.0
"""Fossile Wärme-Menge bei voller Sektor-Kopplungs-Lücke (TWh-th).
[SRC: AGORA »Klimaneutrales Deutschland 2045« 2021, BMWK-Langfrist-
Szenarien T45.]"""

_ICE_MOBILITY_TWH_FULL: float = 100.0
"""Verbrenner-Mobility-Menge bei voller Sektor-Kopplungs-Lücke (TWh).
[SRC: AGORA-2045, Ariadne Kopernikus T45.]"""

_FOSSIL_HEAT_CO2_T_PER_MWH: float = 0.22
"""CO₂-Faktor fossile Wärme (Erdgas/Heizöl-Mix 2026-2045).
[SRC: UBA-CO₂-Emissionsfaktoren-Tabelle, Erdgas 0,20 / Heizöl 0,266
t/MWh-th gewichtet; BEHG-Kalibrier-Basis.]"""

_ICE_CO2_T_PER_MWH: float = 0.30
"""CO₂-Faktor Verbrenner-Mobility (PKW-Diesel/Benzin-Mix Well-to-Wheel).
[SRC: JEC WTW v5 (JRC/EUCAR/CONCAWE 2024), Probas-Datenbank UBA.]"""

_FOSSIL_HEAT_EUR_PER_MWH: float = 80.0
"""€-Kosten fossile Wärme (Erdgas + Heizöl mit Vorkette).
[SRC: AGORA-2045 Wärme-Preise-Korridor 70-90 €/MWh, Mittelpunkt.]"""

_ICE_EUR_PER_MWH: float = 100.0
"""€-Kosten Verbrenner-Mobility (Sprit-Preise inkl. EnSt-äquivalent).
[SRC: AGORA-2045, BMWK-Mobility-Strategie.]"""

# Strom-Substitutions-Mengen für die Mehrkosten-Bilanz. Statt fossile
# Brutto-Kosten ausweisen wir die *Differenz* zur elektrischen
# Alternative (Wärmepumpe + E-Mobility), weil das die methodisch saubere
# Lesart der Lager-Asymmetrie ist. Eine reine Brutto-Lesart würde
# fossil-brutto gegen null vergleichen statt gegen elektrisch-effizient
# und damit die Externalisierung systematisch überzeichnen.

_HEATPUMP_ELECTRICITY_TWH_FULL: float = 67.0
"""Strom-Bedarf der elektrischen Wärme-Substitution bei voller
Sektor-Kopplungs-Lücke. 200 TWh-th-Wärmenutzen / COP 3 = ~67 TWh-el.
[SRC: BWP-Branchenstatistik 2024 (WP-COP-Mittel 3,0 in DE-Bestand-
Mix), AGORA »Klimaneutrales Deutschland 2045« 2021 (Wärme-Bedarf
200 TWh-th @ 2045 bei Vollelektrifizierung).]"""

_EMOB_ELECTRICITY_TWH_FULL: float = 30.0
"""Strom-Bedarf der elektrischen Mobility-Substitution bei voller
Sektor-Kopplungs-Lücke. 100 TWh-WTW-Verbrenner ersetzt durch
~30 TWh-el (E-Antriebs-WTW + Drive-Effizienz-Vorteil Faktor ~3,3).
[SRC: Ariadne Kopernikus T45-Szenarien (E-Mob-Effizienz 2045),
JEC WTW v5 (JRC/EUCAR/CONCAWE 2024, Vergleichs-Effizienzen).]"""

_SUBSTITUTION_ELECTRICITY_EUR_PER_MWH: float = 150.0
"""€-Kosten für Substitutions-Strom (Wärmepumpe + E-Mobility) pro
MWh-el. 150 €/MWh = 15 ct/kWh, konservativer Mittelpunkt-Anker im
Korridor der aktiven Pfad-LCOE 2045 (neutral_default).
[SRC: MODEL-DEFAULT, Korridor 14,8-20,4 ct/kWh @ 2045 über alle vier
Lager. Sensi-Variation über `param_overrides["substitutions_strom_eur_mwh"]`.]"""


def sector_coupling_external(
    year: int,
    demand_twh: float,
    path_id: str,
    camp: str,
    param_overrides: dict[str, float] | None = None,
) -> tuple[float, float]:
    """Externe Sektor-Kopplungs-Mehrkosten + CO₂-Mengen pro Pfad-Jahr.

    Mehrkosten-Lesart: Pfade mit Strom-Demand < 840 TWh (WEITER-SO,
    BESTAND) ersetzen die fehlende Elektrifizierung durch fossile Wärme
    + Verbrenner-Mobility; die *Differenz* zu Wärmepumpe + E-Mobility
    (plus CO₂-Pönale) macht die Lager-Asymmetrie der externen Kosten
    sichtbar.

    **WICHTIG:** Diese Schicht wirkt NICHT auf den Strom-LCOE. Sie ist
    parallel als zusätzliche Pfad-Aussage in PathResult eingebaut
    (Felder ``sektor_kopplung_extern_eur_per_year`` und
    ``co2_extern_mt_per_year``). Damit bleibt die Systemgrenze des
    Strom-LCOE methodisch sauber, die Pfad-Vergleichs-Aussage wird
    aber um die Externalisierungs-Schicht ergänzt.

    Returns:
        (eur_per_year, co2_mt_per_year): externe Mehrkosten gegenüber
        Vollelektrifizierung in EUR/a und externe CO₂-Emissionen in
        Mt/a. Beide 0 für Pfade ohne Lücke (aktive EE/KKW-Pfade mit
        840 TWh Demand). Die CO₂-Mengen sind unabhängig von der
        Mehrkosten- vs. Brutto-Lesart — die Differenz-Lesart betrifft
        nur die EUR-Kosten.
    """
    del path_id  # nur für Symmetrie der Aufrufer-Signatur
    del year  # Heute zeitkonstant
    gap_twh = max(0.0, _DEMAND_FULL_SECTOR_COUPLING_TWH - demand_twh)
    # Numerische-Drift-Toleranz. Aktive Pfade haben demand
    # ~839,7 TWh (kleine Trajektorie-Drift gegen 840-Anker). Erst ab
    # ≥ 5 TWh Lücke ist die Externalisierung pfad-strukturell.
    if gap_twh < 5.0 or _GAP_FULL_TWH <= 1e-9:
        return 0.0, 0.0
    scale = gap_twh / _GAP_FULL_TWH

    # Fossile Mengen pro Sektor (TWh)
    heat_twh = _FOSSIL_HEAT_TWH_FULL * scale
    mobility_twh = _ICE_MOBILITY_TWH_FULL * scale

    # CO₂-Mengen (Mt) — unverändert: fossile Emissionen, da elektrische
    # Substitution per Annahme klimaneutral (Strom aus aktiven Pfaden).
    co2_heat_mt = heat_twh * _FOSSIL_HEAT_CO2_T_PER_MWH
    co2_mobility_mt = mobility_twh * _ICE_CO2_T_PER_MWH
    co2_total_mt = co2_heat_mt + co2_mobility_mt

    # Fossile €-Kosten (€/a)
    fossil_heat_eur = heat_twh * 1e6 * _FOSSIL_HEAT_EUR_PER_MWH
    fossil_mobility_eur = mobility_twh * 1e6 * _ICE_EUR_PER_MWH

    # Substitutions-€-Kosten (€/a): elektrische Alternative
    # (Wärmepumpe @ COP 3 + E-Mobility) auf Substitutions-Strom-Preis.
    electricity_heat_twh = _HEATPUMP_ELECTRICITY_TWH_FULL * scale
    electricity_mobility_twh = _EMOB_ELECTRICITY_TWH_FULL * scale
    electricity_eur_per_mwh = (
        param_overrides.get("substitutions_strom_eur_mwh", _SUBSTITUTION_ELECTRICITY_EUR_PER_MWH)
        if param_overrides
        else _SUBSTITUTION_ELECTRICITY_EUR_PER_MWH
    )
    substitution_eur = (
        (electricity_heat_twh + electricity_mobility_twh) * 1e6 * electricity_eur_per_mwh
    )

    # CO₂-Pönale (€/a) — Lager-spezifisch via _co2_price_year
    co2_preis = _resolve_co2_price(year=2045, camp=camp, overrides=param_overrides)
    co2_penalty_eur = co2_total_mt * 1e6 * co2_preis

    # Mehrkosten = (fossile Brutto-Kosten + CO₂-Pönale) − Substitutions-
    # Stromkosten. Bei sehr hohen Substitutions-Strompreisen oder sehr
    # niedrigen fossilen Preisen kann das Vorzeichen kippen; das ist
    # methodisch sinnvoll (»fossiler Pfad wäre dann billiger«) und
    # nicht durch max(0, …) zu unterdrücken.
    extra_costs_eur = (fossil_heat_eur + fossil_mobility_eur + co2_penalty_eur) - substitution_eur
    return extra_costs_eur, co2_total_mt
