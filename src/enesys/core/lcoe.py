"""LCOE-Berechnung pro (Pfad, Jahr, Lager) inklusive Sekundär-Schicht.

Architektur-Referenz: § 4 (LCOE-Herleitung). ADRs 3 (Sekundär-Schicht),
14 (WACC pro Tech).

Pro Tech: CAPEX-Annuität + OPEX-fix + OPEX-var.
Pro Brennstoff: Brennstoff-Kosten + CO2-Pönale.
Sekundär-Schicht: Netz + Speicher (alle is_storage=True-Techs) + Stabilität.
Plus Profile-Cost-Aufschlag (Lager-Sensi), VOLL-Pönale (Fallback-
Pönale, wenn auch das Backup ausgelastet ist) und Infrastruktur-
CAPEX-Aufschlag für endogene Brennstoff-Cap-Erweiterung.

Funktionen:

- :func:`resolve_tech_field`: Lookup eines TechEntry-Feldes mit
  Override-Vorrang (CAPEX, OPEX, WACC etc.).
- :func:`annuity_factor`: Annuitätenfaktor pro Jahr.
- :func:`secondary_surcharge`: Sekundär-Schicht-Aufschlag aus Mengen.
- :func:`compute_lcoe`: LCOE pro Pfad-Jahr aus Capacity + Dispatch +
  Fuel-Used.
"""

from __future__ import annotations

from .fuel import resolve_co2_price, resolve_fuel_price
from .inventories import FUEL_INVENTORY, TECH_INVENTORY
from .inventories.tech_inventory import TechEntry


def resolve_tech_field(
    tech: TechEntry,
    field: str,
    year: int,
    camp: str,
    overrides: dict[str, float] | None,
) -> float:
    """Lookup eines TechEntry-Feldes mit Override-Vorrang.

    Override-Key-Form: ``"<tech_id>.<field>"``. Wenn vorhanden, hat der
    Override absoluten Vorrang vor dem TechEntry-Wert/Callable. Sonst:
    Callable wird mit (year, lager) aufgerufen, Konstante wird direkt
    zurückgegeben.
    """
    if overrides:
        key = f"{tech.tech_id}.{field}"
        if key in overrides:
            return overrides[key]
    attr = getattr(tech, field)
    return attr(year, camp) if callable(attr) else attr


def annuity_factor(wacc: float, years: int) -> float:
    """Annuitätenfaktor pro Jahr für gegebene Lebensdauer und WACC."""
    # ZeroDivision-Guard für years=0 (Sensi-Konfigurationen mit Lifetime-Edge-Cases).
    years = max(1, years)
    if wacc == 0:
        return 1.0 / years
    return wacc / (1.0 - (1.0 + wacc) ** -years)


# Sekundär-Schicht-Konstanten (Mengen-Sekundär).
# Die Sekundär-Schicht wird aus drei Komponenten zusammengesetzt, die
# aus der Mengen-Bilanz abgeleitet sind:
#
# 1. **Netz** — Basis-Aufschlag plus EE-induzierter Erweiterungs-Anteil.
#    `netz = NETZ_BASIS + NETZ_EE_AUFSCHLAG × EE-Fluktuations-Anteil`.
#    [SRC: BNetzA-Monitoring-Bericht 2024 Netzentgelte-Ist ~6,4 ct/kWh
#    Haushalt + Übertragungs-Anteil; BMWK-Netzentwicklungsplan-Strom 2037+
#    Investitionsbedarf 230-280 Mrd EUR rolling 20 Jahre → ~3 ct/kWh
#    Aufschlag für Voll-EE-System.]
# 2. **Speicher** — Annuität auf installierte Batterie-Kapazität pro
#    Total-Dispatch (Pfad-Jahr).
#    [SRC: BNEF-NEO-2024 Battery-CAPEX ~600 €/kW (Lithium-Ion 4h),
#    annuity 0,08; Lernkurve nicht modelliert.]
# 3. **Stabilität** — Regelreserve + Schwarzstart-Fähigkeit, skaliert
#    mit Volatilitäts-Anteil.
#    [SRC: GridStabilityParams aus path_model.py, ENTSO-E SO GL
#    Regelreserve-Methodologie.]
_GRID_BASE_CT_KWH: float = 4.0
"""Basis-Netzentgelt für nicht-EE-getragenes System.
[SRC: BNetzA-Monitoring 2024 Netzentgelt-Anteil Strompreis-Haushalt
ohne EEG ~6,4 ct, Industrie 3-4 ct; Default 4,0 als gewichteter Mittel.]"""
_GRID_EE_SURCHARGE_CT_KWH: float = 2.0
"""Maximaler EE-induzierter Netz-Aufschlag bei 100 % fluktuierender EE.
[SRC: BMWK-Netzentwicklungsplan-Strom 2037 Investitionsbedarf 230-280 Mrd
EUR / 20 Jahre / 600-700 TWh Demand ≈ 1,8-2,3 ct/kWh.
Wert 2,0 = Mittel der Literatur.]"""
# Batterie-CAPEX + Annuität liest direkt aus TECH_INVENTORY["battery"]
# (Lernkurven-Trajektorie und Lager-WACC), nicht aus Modul-Konstanten.
_STABILITY_BASE_CT_KWH: float = 1.0
"""Stabilitäts-Basis (Regelreserve + Schwarzstart).
[SRC: GridStabilityParams aus path_model.py.]"""
_STABILITY_EE_VOLATILITY_FACTOR: float = 0.5
"""EE-Volatilität-Aufschlag auf Stabilität (max 50 % bei 100 % EE)."""

_VOLL_EUR_PER_MWH: float = 80.0
"""Marginale Brennstoff-Beschaffungs-Kostenklasse für unvermeidbare Strom-
Defizite nach Reserve-Aufbau und Fuel-Cap-Auto-Skalierung. Greift nur,
wenn auch die endogene Cap-Erweiterung die Lücke nicht schließen kann
(z.B. weil keine `boost_policy`-Fuels für den Pfad erlaubt sind).
Wert ~80 €/MWh = LNG-Spot-Aufschlag (50-100 €/MWh) plus Investitions-
Marge für beschleunigten Terminal-Bau.

Methodische Trennung:
- **Kurzfristige Stunden-Spikes** (Sturm-Ausfall, Cold-Snap-Spitze):
  greift die SCARCITY/DUNKELFLAUTE-Notfall-Mechanik mit Boost-Brennstoff-
  Aufweichung plus realer Spot-Beschaffung im Markt. Die VOLL-Pönale ist
  nicht der richtige Anker für solche Spikes — dort gilt das ACER-VOLL-
  Modell (1.000-25.000 €/MWh) als Lastabwurf-Anker.
- **Strukturell vorhersehbare Defizite**: werden durch die endogene
  Fuel-Cap-Auto-Skalierung abgedeckt; die Politik baut LNG-Infrastruktur
  proaktiv aus und zahlt den `_INFRA_EXPANSION_EUR_PER_MWH`-Aufschlag.

[SRC: BAFA-LNG-Statistik 2024 (LNG-Spot 40-80 €/MWh); BMWK LNG-
Beschleunigungsausbau 2022/2023 als Präzedenz; Hanseatic Energy Hub
Stade Investitions-Kosten (Terminal-Bau ~500 Mio EUR für 13 Mrd m³/a).]"""

# Forward-Rückstellungen für neu gebaute KKW (HPC-CfD-Struktur-Anker).
# Greift nur auf kkw_neubau_epr und kkw_neubau_smr — kkw_bestand liefen
# vor dem Modell und haben ihre Decommissioning-Beiträge im KENFO-Fonds
# (sunk_repository_fund_bn) historisch abgelegt.
#
# Lager-Bandbreite über CAMP_RANGES-Sensi-Achsen
# ``nuclear_decom_provision_eur_mwh`` und ``nuclear_waste_transfer_eur_mwh``.
# Lager-Spreizung spiegelt die HPC-CfD-Vertragsbandbreite +
# NEA-Cross-Validation: atom_optimistic 2,0+1,0 (HPC-Untergrenze),
# neutral 3,5+1,5 (Mid-Range), ee_optimistic 10,0+4,0 (NEA-Korridor-
# Obergrenze plus Liability-Externalisierung).
_NUCLEAR_NEUBAU_TECH_IDS: frozenset[str] = frozenset({"kkw_neubau_epr", "kkw_neubau_smr"})
"""Tech-IDs für KKW-Neubau, die die Forward-Rückstellungs-Aufschläge
tragen. kkw_bestand (kein Eintrag) liefen vor dem Modell, KENFO-Fonds
deckt deren Rückstellungen historisch (siehe sunk_*-Doku-Felder)."""


def _nuclear_provision_eur_per_mwh(
    camp: str, param_overrides: dict[str, float] | None = None
) -> float:
    """Decommissioning + Endlager-Waste-Transfer-Beitrag pro MWh KKW-Neubau-Output.

    Liest aus CAMP_RANGES ``nuclear_decom_provision_eur_mwh`` und
    ``nuclear_waste_transfer_eur_mwh``; ``param_overrides`` haben Vorrang
    für Tornado/Monte-Carlo-Sensitivität.
    """
    from .camp_ranges import CAMP_RANGES

    def _resolve(key: str) -> float:
        if param_overrides and key in param_overrides:
            return float(param_overrides[key])
        spec = CAMP_RANGES[key]
        return float(spec.get(camp, spec["neutral_default"]))  # type: ignore[arg-type]

    return _resolve("nuclear_decom_provision_eur_mwh") + _resolve("nuclear_waste_transfer_eur_mwh")


_INFRA_EXPANSION_EUR_PER_MWH: float = 80.0
"""Aufschlag pro thermischer MWh für die endogene Brennstoff-Cap-Erweiterung
im Reserve-Aufbau. Wenn ein Pfad seine Politik-Wahl strukturell auf Gas-Backup
(LNG, Erdgas-Import) stützt, baut die Politik die Infrastruktur dafür auf
(FSRU-Terminals, Pipeline-Upgrades) und beschafft den zusätzlichen
Brennstoff am Spot. Beide Komponenten zusammen ≈ 80 €/MWh:
LNG-Spot-Aufschlag 40-80 €/MWh plus Terminal-CAPEX-Annuität 5-15 €/MWh
plus Pipeline-Operations-Marge.

Methodisch zentral: dieser Aufschlag wird in jeder TWh, die über die
default-Brennstoff-Cap hinaus dispatched wird, fällig. Pfad-Politik
bekommt damit das Preisschild der eigenen Infrastruktur-Wahl: BESTAND
und GAS-Pfade zahlen chronisch teure Terminal-Kosten, EE-/H2-Pfade
vermeiden sie durch klimaneutrales Backup-Substrat.

[SRC: BAFA-LNG-Statistik 2024; BMWK LNG-Beschleunigungsausbau 2022/2023
als Präzedenz für Bauzeit + Kostenklasse; Hanseatic Energy Hub Stade
500 Mio EUR / 13 Mrd m³/a Investitions-Anker; ENTSOG TYNDP 2024 für
Pipeline-Upgrade-Kostenklassen.]"""


def secondary_surcharge(
    capacity: dict[str, float],
    dispatch_used: dict[str, float],
    total_dispatch_twh: float,
    year: int,
    camp: str,
    param_overrides: dict[str, float] | None = None,
) -> tuple[float, tuple[str, ...]]:
    """Sekundär-Schicht-Aufschlag pro Pfad-Jahr in ct/kWh aus Mengen.

    Drei Komponenten:
    - Netz: ``NETZ_BASIS + NETZ_EE_AUFSCHLAG × ee_fluktuations_anteil``.
    - Speicher: Summe über alle ``is_storage=True``-Techs im
      TECH_INVENTORY (heute nur ``battery``):
      ``Σ storage_gw × CAPEX × annuity / total_dispatch_kwh``.
      CAPEX/WACC kommen pro Tech aus dem TechEntry (Lernkurven-
      Trajektorie + Lager-WACC, Override-Pfad analog zu den
      Primär-Techs). Neue Speicher-Techs werden ohne Patch in dieser
      Funktion durch das ``is_storage``-Flag aufgenommen.
    - Stabilität: ``STABILITAET_BASIS × (1 + EE_FAKTOR × ee_anteil)``.

    `ee_fluktuations_anteil` = (PV + Wind-On + Wind-Off-Dispatch) /
    Total-Dispatch. Fluktuierende EE treiben Netz- und Stabilitäts-Anteil.
    `storage_gw` ist die installierte Speicher-Kapazität aus
    Capacity-Buildup (Demand-aware gekappt).

    Rückgabe: ``(surcharge_ct, secondary_provenance)`` — die zweite
    Komponente sammelt die Source-Tags der hier verwendeten Speicher-
    Techs, damit der Caller sie zur Haupt-Schleifen-Provenance addieren
    kann.
    """
    if total_dispatch_twh <= 1e-9:
        return _GRID_BASE_CT_KWH + _STABILITY_BASE_CT_KWH, ()

    fluktuations_dispatch = (
        dispatch_used.get("pv", 0.0)
        + dispatch_used.get("wind_onshore", 0.0)
        + dispatch_used.get("wind_offshore", 0.0)
    )
    ee_anteil = min(fluktuations_dispatch / total_dispatch_twh, 1.0)

    netz_ct = _GRID_BASE_CT_KWH + _GRID_EE_SURCHARGE_CT_KWH * ee_anteil

    # Speicher-Komponente: über alle is_storage=True-Techs summieren.
    # Aktuell nur ``battery`` markiert; Erweiterung (z.B. saisonale
    # Speicher) folgt demselben Schema, ohne weiteren Patch in
    # ``secondary_surcharge`` zu brauchen.
    total_dispatch_kwh = total_dispatch_twh * 1e9
    speicher_ct = 0.0
    secondary_provenance_parts: list[str] = []
    for storage_tech_id, storage_tech in TECH_INVENTORY.items():
        if not storage_tech.is_storage:
            continue
        storage_gw = capacity.get(storage_tech_id, 0.0)
        if storage_gw <= 0.0:
            continue
        storage_capex = resolve_tech_field(
            storage_tech, "capex_eur_kw", year, camp, param_overrides
        )
        storage_wacc = resolve_tech_field(storage_tech, "wacc_pct", year, camp, param_overrides)
        storage_annuity = annuity_factor(storage_wacc, storage_tech.lifetime_years)
        storage_eur_per_year = storage_gw * 1e6 * storage_capex * storage_annuity
        speicher_ct += storage_eur_per_year * 100.0 / total_dispatch_kwh
        if storage_tech.source:
            first_line = storage_tech.source.splitlines()[0].strip()
            secondary_provenance_parts.append(f"{storage_tech_id}: {first_line[:80]}")

    stabilitaet_ct = _STABILITY_BASE_CT_KWH * (1.0 + _STABILITY_EE_VOLATILITY_FACTOR * ee_anteil)

    return netz_ct + speicher_ct + stabilitaet_ct, tuple(secondary_provenance_parts)


def compute_lcoe(
    year: int,
    path_id: str,
    camp: str,
    capacity: dict[str, float],
    dispatch_used: dict[str, float],
    fuel_used: dict[str, float],
    *,
    param_overrides: dict[str, float] | None = None,
    unserved_twh: float = 0.0,  # [MODEL: Ungedeckter Demand nach Reserve-Aufbau und endogener Cap-Erweiterung; 0 = vollständig gedeckt.]
    demand_twh: float = 0.0,  # [MODEL: Pfad-Demand für VOLL-Pönale-Bezugsgröße; 0 = kein VOLL-Pönale aktiv.]
    fuel_cap_expansion_th: dict[str, float]
    | None = None,  # [MODEL: Endogene Cap-Auto-Skalierung aus dem Reserve-Aufbau; pro TWh fällt _INFRA_EXPANSION_EUR_PER_MWH-Aufschlag an.]
) -> tuple[dict[str, float], float, tuple[str, ...]]:
    """LCOE pro Pfad-Jahr aus den Mengen-Bilanz-Komponenten (§ 4 Architektur-
    Design).

    Pro Tech:
    - CAPEX-Annuität: `capex_eur_kw(year, lager) × annuity(wacc, lebensdauer)
      × gw × 1000 / twh_erzeugt` → ct/kWh, gewichtet mit Pfad-Anteil.
    - OPEX-fix: `opex_fix_eur_kw_a × gw × 1000 / twh_erzeugt`.
    - OPEX-var: `opex_var_eur_mwh / 10` ct/kWh.

    Pro Brennstoff:
    - Brennstoff-Kosten: `preis_eur_mwh(year, lager) × fuel_used_twh × 1000
      / total_demand_twh` → ct/kWh.
    - CO2-Pönale: `co2_t_per_mwh_th × CO2-Preis × fuel_used_twh × 1000
      / total_demand_twh`.

    Sekundär-Schicht: pfad-spezifischer ct/kWh-Aufschlag aus
    `_SEKUNDAER_AUFSCHLAG_CT_KWH` (Speicher / Netz / Stabilität als
    aggregierter Aufschlag, getrennt von der Primär-Schleife).

    `provenance` sammelt die Source-Tags aller eingesetzten Techs und
    Brennstoffe.
    """
    total_dispatch_twh = sum(dispatch_used.values())
    if total_dispatch_twh <= 1e-9:
        # Kein Dispatch → kein LCOE definiert; gibt null-Komponenten zurück.
        return ({}, 0.0, ())

    co2_preis = resolve_co2_price(year, camp, param_overrides)
    capex_annuity_total_eur = 0.0
    opex_fix_total_eur = 0.0
    opex_var_total_eur = 0.0
    nuclear_provision_total_eur = 0.0
    fuel_cost_total_eur = 0.0
    co2_cost_total_eur = 0.0
    provenance_set: set[str] = set()

    for tech_id, twh_erzeugt in dispatch_used.items():
        if twh_erzeugt <= 1e-9:
            continue
        tech = TECH_INVENTORY[tech_id]
        gw = capacity.get(tech_id, 0.0)
        if gw <= 0.0:
            continue
        capex = resolve_tech_field(tech, "capex_eur_kw", year, camp, param_overrides)
        wacc = resolve_tech_field(tech, "wacc_pct", year, camp, param_overrides)
        opex_fix = resolve_tech_field(tech, "opex_fix_eur_kw_a", year, camp, param_overrides)
        opex_var = resolve_tech_field(tech, "opex_var_eur_mwh", year, camp, param_overrides)
        annuity = annuity_factor(wacc, tech.lifetime_years)
        # Unit-Umrechnung: gw × 1e6 = kW (1 GW = 1e6 kW). Damit
        # capex × annuity × gw × 1e6 = €/a, weil capex in €/kW.
        capex_annuity_total_eur += capex * annuity * gw * 1e6
        opex_fix_total_eur += opex_fix * gw * 1e6
        # Unit-Umrechnung: twh × 1e6 = MWh (1 TWh = 1e6 MWh). Damit
        # opex_var × twh × 1e6 = €, weil opex_var in €/MWh.
        opex_var_total_eur += opex_var * twh_erzeugt * 1e6
        # Forward-Rückstellungs-Aufschlag für KKW-Neubau (HPC-CfD-Anker):
        # Decommissioning-Fund + Endlager-Waste-Transfer-Beitrag pro MWh
        # Output, internalisiert in die Forward-LCOE. Lager-spezifisch
        # über CAMP_RANGES (atom_opt: 3 €/MWh, neutral: 5, ee_opt: 14).
        if tech_id in _NUCLEAR_NEUBAU_TECH_IDS:
            provision_eur_mwh = _nuclear_provision_eur_per_mwh(camp, param_overrides)
            nuclear_provision_total_eur += provision_eur_mwh * twh_erzeugt * 1e6
        if tech.source:
            provenance_set.add(f"{tech_id}: {tech.source[:80]}")

    for fuel_id, twh_verbraucht in fuel_used.items():
        if twh_verbraucht <= 1e-9:
            continue
        fuel = FUEL_INVENTORY[fuel_id]
        preis = resolve_fuel_price(fuel, year, camp, param_overrides)
        # Unit-Umrechnung: twh × 1e6 = MWh. preis × MWh = €.
        fuel_cost_total_eur += preis * twh_verbraucht * 1e6
        co2_cost_total_eur += fuel.co2_t_per_mwh_th * co2_preis * twh_verbraucht * 1e6
        if fuel.source:
            provenance_set.add(f"{fuel_id}: {fuel.source[:80]}")

    total_dispatch_kwh = total_dispatch_twh * 1e9
    capex_ct = capex_annuity_total_eur * 100.0 / total_dispatch_kwh
    opex_fix_ct = opex_fix_total_eur * 100.0 / total_dispatch_kwh
    opex_var_ct = opex_var_total_eur * 100.0 / total_dispatch_kwh
    nuclear_provision_ct = nuclear_provision_total_eur * 100.0 / total_dispatch_kwh
    fuel_ct = fuel_cost_total_eur * 100.0 / total_dispatch_kwh
    co2_ct = co2_cost_total_eur * 100.0 / total_dispatch_kwh
    sekundaer_ct, secondary_provenance = secondary_surcharge(
        capacity,
        dispatch_used,
        total_dispatch_twh,
        year,
        camp,
        param_overrides,
    )
    provenance_set.update(secondary_provenance)
    from enesys.extensions.profile_costs import combined_surcharge

    profile_ct = combined_surcharge(path_id, camp=camp, param_overrides=param_overrides)

    # VOLL als physische Fallback-Pönale. Greift nur, wenn auch die
    # endogene Cap-Auto-Skalierung die Lücke nicht schließt (z.B. wenn
    # boost_policy für den Pfad keinen Backup-Brennstoff erlaubt).
    voll_ct = 0.0
    if unserved_twh > 1e-9 and demand_twh > 1e-9:
        voll_cost_eur = _VOLL_EUR_PER_MWH * unserved_twh * 1e6
        voll_ct = voll_cost_eur * 100.0 / (demand_twh * 1e9)

    # Infrastruktur-CAPEX-Aufschlag für die endogen aufgebaute Brennstoff-
    # Cap-Erweiterung (LNG-Terminals, Pipeline-Upgrades). Konstante
    # _INFRA_EXPANSION_EUR_PER_MWH siehe Modul-Top.
    fuel_infra_ct = 0.0
    if fuel_cap_expansion_th and demand_twh > 1e-9:
        expansion_total_th = sum(fuel_cap_expansion_th.values())
        if expansion_total_th > 1e-9:
            infra_cost_eur = _INFRA_EXPANSION_EUR_PER_MWH * expansion_total_th * 1e6
            fuel_infra_ct = infra_cost_eur * 100.0 / (demand_twh * 1e9)

    lcoe_total = (
        capex_ct
        + opex_fix_ct
        + opex_var_ct
        + nuclear_provision_ct
        + fuel_ct
        + co2_ct
        + sekundaer_ct
        + profile_ct
        + voll_ct
        + fuel_infra_ct
    )

    components = {
        "capex_annuity": capex_ct,
        "opex_fix": opex_fix_ct,
        "opex_var": opex_var_ct,
        "nuclear_provision": nuclear_provision_ct,
        "fuel": fuel_ct,
        "co2": co2_ct,
        "sekundaer": sekundaer_ct,
        "profile_costs": profile_ct,
        "voll_unserved": voll_ct,
        "fuel_infra_expansion": fuel_infra_ct,
    }
    return components, lcoe_total, tuple(sorted(provenance_set))
