"""Merit-Order-Dispatch und Brennstoff-Mengen-Bilanz pro (Pfad, Jahr, Lager).

Dispatch ist eine schlanke Merit-Order-Schleife. Die Politik pro Tech
(Kapazität, VLH, Brennstoff-Bedarf, Demand-Cap, Phaseout-Fade) lebt zentral
in ``TechEntry.max_dispatch_twh_per_year``; das Modell fragt nur, wie viel
jede Tech maximal liefern kann, und füllt die Demand der Reihenfolge nach.
Stunden-Stress wird separat in ``extensions/winter_stress.winter_stress_balance``
geprüft — die Jahres-Bilanz beschreibt die Mengen-Konsistenz, nicht die
Spitzenlast-Adäquanz.

Architektur-Referenz: § 3.1 (Normalbetrieb pro Jahr). ADRs 7 (Jahres-
Aggregat), 8 (Multi-Fuel), 9 (Dauer-vs-Boost).

Funktionen:

- :func:`dispatch_and_balance`: Merit-Order-Schleife plus Reserve-Aufbau
  mit endogener Brennstoff-Cap-Erweiterung.
- :func:`fuel_used_from_dispatch`: rekonstruiert den Brennstoff-Verbrauch
  aus dem Dispatch.
- :func:`initial_fuel_caps_th`: Single-Source-Berechnung der Brennstoff-
  Caps unter Politik-Multiplikator + H2-Realgrad.
"""

from __future__ import annotations

from .inventories import FUEL_INVENTORY, TECH_INVENTORY
from .inventories.path_policy import PathPolicyEntry
from .system_state import SystemState, fuel_cap_mode, is_emergency_or_stress

# Volllaststunden-Annahme für den Selbst-Reserve-Aufbau (h/a).
#
# Die annual-aggregate-Mengen-Bilanz erfasst die Lücke nach der Merit-
# Order-Schleife als einen Jahres-TWh-Wert. Physisch entsteht diese Lücke
# überwiegend in konzentrierten Dunkelflauten-Phasen (Wetter-Stress,
# 500-1500 h/a für Spitzenlast-Backup in DE). Würde der Reserve-Aufbau
# die Backup-Kapazität durch ``vlh_normal`` (3500 h/a für gas_h2ready)
# teilen, käme ein Faktor 3-7 zu wenig Peak-Kapazität heraus — und damit
# zu wenig CAPEX-Annuität, weil reale Backup-Kraftwerke deutlich tiefere
# VLH erreichen als Grundlast-Anlagen.
#
# Wert 1000 h/a: empirische Bandbreite deutscher Gas-Peaker (BNetzA-
# Monitoring 2024, Kraftwerksliste Spitzenlast-Kategorie). Bildet die
# Peak-Charakteristik des Backup-Aufbaus im annual-aggregate-Modell
# korrekt ab, ohne in stündliche Auflösung zu wechseln.
#
# [SRC: BNetzA-Monitoring-Bericht 2024 (Kraftwerksliste, Spitzenlast-
# VLH); Fraunhofer ISE Stromgestehungskosten 2024 (Gas-Peaker-VLH-
# Bandbreite 500-2000 h); ENTSO-E Power Statistics Report 2024.]
_PHASE3_BACKUP_VLH_PEAK: float = 1000.0


def initial_fuel_caps_th(
    year: int,
    camp: str,
    policy: PathPolicyEntry,
    system_state: SystemState,
    h2_realization_rate: float,
) -> dict[str, float]:
    """Single-Source-Berechnung der initial verfügbaren Brennstoff-Caps
    pro Brennstoff (thermische TWh).

    Wendet alle Modifier konsistent an:
    - ``fuel_cap_mode`` (NORMAL → duration_max, SCARCITY-policy → boost_max,
      DUNKELFLAUTE → boost_max)
    - ``policy.fuel_cap_multipliers`` (pfad-spezifische Infrastruktur,
      z.B. BESTAND LNG ×2 analog LNG-Beschleunigungsausbau 2022/2023)
    - ``h2_realization_rate`` (Politik-Hebel auf H2-Brennstoffe)

    Wird sowohl von :func:`fuel_used_from_dispatch` als auch von
    :func:`dispatch_and_balance` für den Reserve-Aufbau genutzt — beide
    Dispatch-Schichten rechnen so gegen dieselbe Cap-Definition.
    """
    caps: dict[str, float] = {}
    for fuel_id, fuel in FUEL_INVENTORY.items():
        mode = fuel_cap_mode(fuel_id, policy, system_state)
        cap = (
            fuel.boost_max_twh_per_year(year, camp)
            if mode == "boost"
            else fuel.duration_max_twh_per_year(year, camp)
        )
        cap *= policy.fuel_cap_multipliers.get(fuel_id, 1.0)
        if fuel_id in ("h2_inland", "h2_import"):
            cap *= h2_realization_rate
        caps[fuel_id] = cap
    return caps


def fuel_used_from_dispatch(
    dispatch_used: dict[str, float],
    year: int,
    path_id: str,
    camp: str,
    policy: PathPolicyEntry,
    *,
    system_state: SystemState | None = None,
    h2_realization_rate: float = 1.0,
    fuel_cap_expansion_th: dict[str, float] | None = None,
) -> dict[str, float]:
    """Rekonstruiert fuel_used aus dispatch_used.

    ``system_state`` steuert Brennstoff-Cap-Modus
    (NORMAL/SCARCITY/DUNKELFLAUTE); die Logik lebt in
    ``core.system_state.fuel_cap_mode``. Phaseout-Glättung im Nicht-
    NORMAL-State greift nur für ``policy.boost_policy``-Fuels.

    ``h2_realization_rate`` wirkt multiplikativ auf H2-Brennstoff-
    Verfügbarkeit (h2_inland, h2_import). Politik-Hebel symmetrisch zu
    nep_realization_rate / nuclear_realization_rate.

    ``fuel_cap_expansion_th`` optional: die endogen aufgebaute
    Cap-Erweiterung pro Brennstoff. Wird zu den initialen Caps addiert,
    damit die Brennstoff-Buchhaltung den erweiterten Dispatch konsistent
    abbildet.
    """
    if system_state is None:
        system_state = SystemState.NORMAL

    fuel_used: dict[str, float] = dict.fromkeys(FUEL_INVENTORY, 0.0)
    fuel_remaining_th = initial_fuel_caps_th(year, camp, policy, system_state, h2_realization_rate)
    if fuel_cap_expansion_th:
        for f, extra in fuel_cap_expansion_th.items():
            fuel_remaining_th[f] = fuel_remaining_th.get(f, 0.0) + extra

    for tech_id, electricity_total in dispatch_used.items():
        if electricity_total <= 1e-9:
            continue
        tech = TECH_INVENTORY[tech_id]
        if not tech.fuel_set:
            continue
        eta_el = tech.efficiency_el
        fuel_order = tech._fuel_order_path_specific(path_id, policy)

        electricity_remaining = electricity_total
        for fuel_id in fuel_order:
            if electricity_remaining <= 1e-9:
                break
            fc = policy.fuel_constraints.get(fuel_id, "")
            if fc in ("stop", "forbidden"):
                continue
            in_emergency_or_stress = is_emergency_or_stress(
                system_state
            ) and policy.boost_policy.get(fuel_id, False)
            # Notfall-Aufweichung asymmetrisch nach Stress-Typ
            # (siehe TechEntry.max_dispatch_twh_per_year):
            # DUNKELFLAUTE → 0,3 (physikalisch, Pipeline/LNG-Stress).
            # SCARCITY (wirtschaftlicher Versorgungs-Notfall) → 0,5: politische Mitte
            # zwischen voller Klimaambition und voller Erdgas-Aufweichung.
            emergency_floor = 0.3 if system_state is SystemState.DUNKELFLAUTE else 0.5
            fade_factor = 1.0
            if fc.startswith("phaseout_"):
                phaseout_year = int(fc.split("_", 1)[1])
                fade_start = max(2026, phaseout_year - 10)
                if year >= phaseout_year:
                    if not in_emergency_or_stress:
                        continue
                    fade_factor = emergency_floor
                elif year > fade_start:
                    if in_emergency_or_stress:
                        progress = (year - fade_start) / max(1, phaseout_year - fade_start)
                        fade_factor = 1.0 - progress * (1.0 - emergency_floor)
                    else:
                        fade_factor = (phaseout_year - year) / max(1, phaseout_year - fade_start)
            available_th = fuel_remaining_th.get(fuel_id, 0.0) * fade_factor
            if available_th <= 0:
                continue
            electricity_from_fuel_max = available_th * eta_el
            electricity_dispatched = min(electricity_from_fuel_max, electricity_remaining)
            thermal = electricity_dispatched / eta_el if eta_el > 0 else 0.0
            fuel_used[fuel_id] += thermal
            fuel_remaining_th[fuel_id] = max(0.0, fuel_remaining_th[fuel_id] - thermal)
            electricity_remaining -= electricity_dispatched

    return fuel_used


def dispatch_and_balance(
    year: int,
    path_id: str,
    camp: str,
    demand_twh: float,
    policy: PathPolicyEntry,
    *,
    system_state: SystemState | None = None,
    capacity_override: dict[str, float] | None = None,
    h2_realization_rate: float = 1.0,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], float, dict[str, float]]:
    """Merit-Order-Dispatch (Jahres-Aggregat).

    ``system_state`` steuert die Dispatch-Bedingungen. Die Merit-Order-
    Schleife nutzt den übergebenen State (Default NORMAL). Reserve-Aufbau
    und endogene Brennstoff-Cap-Auto-Skalierung greifen nur bei NORMAL-
    Aufruf — bei DUNKELFLAUTE oder SCARCITY liefert die Funktion einen
    reinen Stress-Snapshot.

    Rückgabe:
    ``(dispatch_used, fuel_used, selbst_reserve_gw, unserved_twh,
    fuel_cap_expansion_th)``.

    ``selbst_reserve_gw`` (Dict tech_id → extra GW) wird im Orchestrator
    in capacity_buildup aufgenommen. ``fuel_cap_expansion_th`` (Dict
    fuel_id → extra TWh thermisch) erfasst die endogen aufgebaute
    Infrastruktur-Erweiterung — pro TWh fällt der
    ``_INFRA_EXPANSION_EUR_PER_MWH``-Aufschlag im LCOE an.
    ``unserved_twh`` triggert die VOLL-Pönale für unvermeidbare Restlücken
    (z.B. wenn keine boost_policy-Fuels verfügbar sind).
    """
    if system_state is None:
        system_state = SystemState.NORMAL

    dispatch_used: dict[str, float] = dict.fromkeys(TECH_INVENTORY, 0.0)
    remaining = demand_twh

    for tech_id in policy.dispatch_priority:
        if remaining <= 1e-9:
            break
        tech = TECH_INVENTORY[tech_id]
        cap_override = capacity_override.get(tech_id) if capacity_override is not None else None
        max_verfuegbar = tech.max_dispatch_twh_per_year(
            year,
            path_id,
            camp,
            system_state=system_state,
            capacity_gw_override=cap_override,
            h2_realization_rate=h2_realization_rate,
        )
        dispatched = min(max_verfuegbar, remaining)
        dispatch_used[tech_id] += dispatched
        remaining -= dispatched

    # Reserve-Aufbau + endogene Brennstoff-Cap-Erweiterung bei Restdemand.
    #
    # Wenn nach der Merit-Order-Schleife noch Demand offen ist, baut die
    # Politik zusätzliche Reserve-Kapazität in einem Backup-Tech auf
    # (gas_h2ready oder erdgas_bestand je nach Pfad-Erlaubnis). Brennstoff-
    # Cap wird parallel bedarfsgerecht erweitert; beides mit Preisschild:
    #
    # - Backup-Kapazität über _PHASE3_BACKUP_VLH_PEAK dimensioniert
    #   (peak-aware, weil Annual-Lücken physisch konzentriert auftreten).
    # - Brennstoff-Cap-Erweiterung über _INFRA_EXPANSION_EUR_PER_MWH
    #   bepreist (Terminal-CAPEX + Spot-Beschaffung).
    #
    # Reserve-Tech-Auswahl nach Pfad-Politik-Charakter:
    # - gas_h2ready, falls vom Pfad erlaubt (klimaneutraler CCGT-Neubau):
    #   EE-/KKW-Pfade.
    # - sonst erdgas_bestand (Bestands-Lifetime-Extension): WEITER-SO,
    #   BESTAND.
    # - sonst kein Reserve-Aufbau (Restdemand bleibt als unserved_twh
    #   für VOLL-Pönale).
    #
    # Greift nur bei NORMAL-Aufruf — Stress-State-Aufrufe (DUNKELFLAUTE)
    # liefern reine Stress-Snapshots.
    self_reserve_gw: dict[str, float] = {}
    fuel_cap_expansion_th: dict[str, float] = {}
    if remaining > 1.0 and system_state is SystemState.NORMAL:
        reserve_tech_id = None
        for candidate in ("gas_h2ready", "erdgas_bestand"):
            if candidate not in TECH_INVENTORY:
                continue
            if policy.tech_constraints.get(candidate, "") == "forbidden":
                continue
            t = TECH_INVENTORY[candidate]
            if not t.fuel_set or t.vlh_normal <= 0:
                continue
            reserve_tech_id = candidate
            break
        if reserve_tech_id is not None:
            reserve_tech = TECH_INVENTORY[reserve_tech_id]

            # Verbleibende Brennstoff-Caps nach der Merit-Order-Schleife
            # berechnen, damit der Reserve-Aufbau nur den noch nicht
            # verbrauchten Brennstoff in Reserve-Tech umwandelt.
            fuel_used_so_far = fuel_used_from_dispatch(
                dispatch_used,
                year,
                path_id,
                camp,
                policy,
                system_state=system_state,
                h2_realization_rate=h2_realization_rate,
            )
            caps_initial = initial_fuel_caps_th(
                year,
                camp,
                policy,
                SystemState.SCARCITY,
                h2_realization_rate,
            )
            fuel_remaining_th = {
                f: max(0.0, caps_initial.get(f, 0.0) - fuel_used_so_far.get(f, 0.0))
                for f in caps_initial
            }

            fuel_electricity_max_total = reserve_tech._max_electricity_from_fuel(
                float("inf"),
                year,
                path_id,
                camp,
                policy,
                FUEL_INVENTORY,
                system_state=SystemState.SCARCITY,
                h2_realization_rate=h2_realization_rate,
                fuel_remaining_th=fuel_remaining_th,
            )
            reserve_electricity = min(remaining, fuel_electricity_max_total)
            if reserve_electricity > 1e-9:
                # Peak-aware Dimensionierung: Annual-Lücken treten physisch
                # konzentriert auf (Dunkelflauten). Backup-VLH 1000 h/a
                # statt vlh_normal 3500 h/a bildet die Peak-Charakteristik
                # im annual-aggregate-Modell korrekt ab (siehe
                # _PHASE3_BACKUP_VLH_PEAK).
                extra_gw = reserve_electricity * 1000.0 / _PHASE3_BACKUP_VLH_PEAK
                self_reserve_gw[reserve_tech_id] = extra_gw
                dispatch_used[reserve_tech_id] += reserve_electricity
                remaining -= reserve_electricity

            # Endogene Brennstoff-Cap-Erweiterung: wenn nach normaler Reserve
            # noch remaining > 0, baut die Politik zusätzliche LNG-/Erdgas-
            # Import-Infrastruktur. Bedarfsgerecht skaliert, mit Preisschild.
            # Verteilt auf boost_policy-erlaubte Backup-Fuels in Reihenfolge
            # LNG → Erdgas-Import → Erdgas-Inland (LNG zuerst, weil
            # Terminal-Bau die schnellste Politik-Reaktion ist).
            if remaining > 1.0:
                if reserve_tech.efficiency_el > 0:
                    expansion_th_needed = remaining / reserve_tech.efficiency_el
                else:
                    expansion_th_needed = 0.0
                for exp_fuel in ("lng", "erdgas_import", "erdgas_inland"):
                    if expansion_th_needed <= 1e-9:
                        break
                    if not policy.boost_policy.get(exp_fuel, False):
                        continue
                    fuel_cap_expansion_th[exp_fuel] = (
                        fuel_cap_expansion_th.get(exp_fuel, 0.0) + expansion_th_needed
                    )
                    fuel_remaining_th[exp_fuel] = (
                        fuel_remaining_th.get(exp_fuel, 0.0) + expansion_th_needed
                    )
                    expansion_th_needed = 0.0
                if fuel_cap_expansion_th:
                    fuel_electricity_max_total_v2 = reserve_tech._max_electricity_from_fuel(
                        float("inf"),
                        year,
                        path_id,
                        camp,
                        policy,
                        FUEL_INVENTORY,
                        system_state=SystemState.SCARCITY,
                        h2_realization_rate=h2_realization_rate,
                        fuel_remaining_th=fuel_remaining_th,
                    )
                    extra_reserve = min(
                        remaining,
                        fuel_electricity_max_total_v2 - reserve_electricity,
                    )
                    if extra_reserve > 1e-9:
                        extra_gw_add = extra_reserve * 1000.0 / _PHASE3_BACKUP_VLH_PEAK
                        self_reserve_gw[reserve_tech_id] = (
                            self_reserve_gw.get(reserve_tech_id, 0.0) + extra_gw_add
                        )
                        dispatch_used[reserve_tech_id] += extra_reserve
                        remaining -= extra_reserve

    fuel_state = system_state
    fuel_used = fuel_used_from_dispatch(
        dispatch_used,
        year,
        path_id,
        camp,
        policy,
        system_state=fuel_state,
        h2_realization_rate=h2_realization_rate,
        fuel_cap_expansion_th=fuel_cap_expansion_th,
    )
    return dispatch_used, fuel_used, self_reserve_gw, remaining, fuel_cap_expansion_th
