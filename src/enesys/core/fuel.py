"""Brennstoff-Preis-Resolver und CO₂-Bilanz pro Pfad-Jahr.

Resolver-Schicht für die Override-Mechanik (Tornado/Monte-Carlo) auf
Brennstoff-Preise und CO₂-Preise, plus CO₂-Bilanz aus dem
Brennstoff-Verbrauch.

Funktionen:

- :func:`resolve_fuel_price`: ``preis_eur_mwh(year, camp)`` mit
  Override-Vorrang.
- :func:`resolve_co2_price`: CO₂-Preis mit Override-Vorrang.
- :func:`co2_price_year`: Lager-spezifischer CO₂-Preis (real, 2025-EUR).
- :func:`co2_from_fuels`: kumulierte Strom-Sektor-CO₂ aus Brennstoff-
  Verbrauch.
"""

from __future__ import annotations

from .inventories import FUEL_INVENTORY
from .inventories.fuel_inventory import FuelEntry


def resolve_fuel_price(
    fuel: FuelEntry,
    year: int,
    camp: str,
    overrides: dict[str, float] | None,
) -> float:
    """Brennstoff-Preis mit Override-Vorrang.

    Override-Key-Form: ``"<fuel_id>.preis_eur_mwh"``.
    """
    if overrides:
        key = f"{fuel.fuel_id}.preis_eur_mwh"
        if key in overrides:
            return overrides[key]
    return fuel.price_eur_mwh(year, camp)


def resolve_co2_price(
    year: int,
    camp: str,
    overrides: dict[str, float] | None,
) -> float:
    """CO₂-Preis mit Override-Vorrang.

    Override-Key: ``"co2_price_eur_t"``. Wirkt zeitkonstant über alle
    Jahre — Trajektorien-Overrides sind explizit nicht unterstützt
    (würden mehr Struktur brauchen).
    """
    if overrides and "co2_price_eur_t" in overrides:
        return overrides["co2_price_eur_t"]
    return co2_price_year(year, camp)


def co2_price_year(year: int, camp: str) -> float:
    """CO₂-Preis in €/t (real, 2025-EUR-Anker) mit asymmetrischer Welt-
    Belief-Spreizung.

    Welt-Belief-Logik: Der CO₂-Preis ist nicht primär Klimapolitik,
    sondern eine Welt-Aussage über zukünftige ETS-Verschärfung.
    Lager-Belief verschiebt entsprechend:

    - **neutral_default 130 €/t**: Median EU-ETS-2026 Erwartungspfad
      2045 + Ariadne T45-Kopernikus + IEA WEO NZE konvergent.
    - **ee_optimistic 160 €/t**: EE-Welt erwartet stärkere Klimapolitik
      (Fit-for-55-Folgenabschätzung-obere-Kante).
    - **atom_optimistic 150 €/t**: KKW-Investor-Spekulations-Logik —
      KKW-Hochlauf lohnt sich nur, wenn CO₂-Preise hoch sind, der
      Lager-Belief muss konsistent höher als neutral sein.
    - **bestand_optimistic 100 €/t**: BESTAND-Welt-Belief ist »ETS
      wird politisch zurückgedreht« (BEHG-Pause-Erwartung,
      Klima-Rückwärtsgang).

    Quellen-Triangulation:

    - **Primär:** EU-ETS-Erwartungspfad (Fit-for-55-Folgenabschätzung,
      120-150 €/t für 2045 in 2023er Preisen).
    - **Sekundär:** Ariadne Kopernikus T45-Szenarien (Bandbreite
      100-200 €/t je Szenario, peer-reviewed DE-Fokus).
    - **Tertiär:** IEA World Energy Outlook 2024 NZE-Szenario
      (130-180 €/t implizit für DE/EU 2045).

    [SRC: EU-ETS-2026 Erwartungspfad + Ariadne T45 + IEA WEO 2024 NZE.]
    """
    camp_values = {
        "neutral_default": 130.0,
        "ee_optimistic": 160.0,
        "atom_optimistic": 150.0,
        "bestand_optimistic": 100.0,
    }
    del year  # Lager-Spreizung ist zeitkonstant;
    # ETS-Trajektorie pro Jahr ergänzen.
    return camp_values.get(camp, 130.0)


def co2_from_fuels(fuel_used: dict[str, float]) -> float:
    """CO2-Emissionen pro Pfad-Jahr aus Brennstoff-Bilanz.

    Summiert `fuel_used_twh × co2_t_per_mwh_th × 1e6` (TWh × 1e6 = MWh,
    × t/MWh = t).
    Konvertiert in Mt CO2.
    """
    co2_t = 0.0
    for fuel_id, twh in fuel_used.items():
        if twh <= 0:
            continue
        fuel = FUEL_INVENTORY[fuel_id]
        co2_t += fuel.co2_t_per_mwh_th * twh * 1e6
    return co2_t / 1e6  # zurück in Mt


_GAS_H2READY_ERDGAS_FUELS: tuple[str, ...] = ("erdgas_inland", "erdgas_import", "lng")
_GAS_H2READY_H2_FUELS: tuple[str, ...] = ("h2_inland", "h2_import")


def split_gas_h2ready_by_fuel(
    gas_h2ready_total: float,
    fuel_used: dict[str, float],
    *,
    h2_default_fallback: bool = False,
) -> tuple[float, float]:
    """Teilt eine ``gas_h2ready``-Aggregat-Menge nach Brennstoff-Verhältnis.

    Args:
        gas_h2ready_total: aggregierter Dispatch- oder Backup-Wert für
            die ``gas_h2ready``-Tech (TWh oder GW — der Aufrufer behält
            seine eigene Einheit, die Funktion arbeitet linear).
        fuel_used: Brennstoff-Bilanz des Pfad-Jahres
            (``PathResult.fuel_used``); muss die Erdgas-Fuels
            (``erdgas_inland`` / ``erdgas_import`` / ``lng``) und die
            H₂-Fuels (``h2_inland`` / ``h2_import``) als Schlüssel führen.
        h2_default_fallback: wenn keine Brennstoffe verbraucht wurden
            (z.B. weil ``gas_h2ready`` im betreffenden Jahr nicht
            dispatched wurde), wird der Aggregat-Wert komplett dem
            H₂-Anteil (True) oder dem Erdgas-Anteil (False, default)
            zugeordnet. Aufrufer wählen nach Pfad-Politik (H₂-Pfade
            → True, sonst False).

    Returns:
        (erdgas_anteil, h2_anteil) — beide ≥ 0, summieren zu
        ``gas_h2ready_total`` (bis auf Floating-Point-Rundung).
    """
    if gas_h2ready_total <= 1e-9:
        return 0.0, 0.0
    erdgas_th = sum(fuel_used.get(f, 0.0) for f in _GAS_H2READY_ERDGAS_FUELS)
    h2_th = sum(fuel_used.get(f, 0.0) for f in _GAS_H2READY_H2_FUELS)
    share_sum = erdgas_th + h2_th
    if share_sum <= 1e-9:
        if h2_default_fallback:
            return 0.0, gas_h2ready_total
        return gas_h2ready_total, 0.0
    erdgas_share = gas_h2ready_total * erdgas_th / share_sum
    h2_share = gas_h2ready_total * h2_th / share_sum
    return erdgas_share, h2_share
