"""Kapazitäts-/Dispatch-Modell mit Mengen-Bilanz pro (Pfad, Jahr, Lager).

Liest aus den Inventaren (TECH/FUEL/PATH_POLICY/DEMAND_CURVES) und
produziert pro (Pfad, Jahr, Lager) eine Mengen-Bilanz mit Kapazitäts-
Aufbau, Dispatch, Brennstoff-Verbrauch und LCOE.

Schicht-Architektur:

- ``PathResult``: Dataclass mit Mengen-Bilanz, LCOE-Schichten,
  Provenance, Sektor-Kopplungs-Externalisierung pro (Pfad, Jahr).
- ``compute_path``: Orchestrator, der pro Jahr Kapazität, Dispatch,
  LCOE und externe Schichten zusammenführt.
- ``_dispatch_and_balance``: Merit-Order-Schleife plus Reserve-Aufbau
  mit endogener Brennstoff-Cap-Erweiterung.
- ``_fuel_used_from_dispatch``: rekonstruiert den Brennstoff-Verbrauch
  aus dem Dispatch.
- ``_compute_lcoe``: Annuität + WACC pro Tech + Sekundär-Schicht +
  CO₂-/VOLL-/Infra-Buckets.
- Auswertungs-Wrapper: ``investment_total_eur_per_path``,
  ``co2_lockin_metric``, ``co2_lockin_report``.

Methodische Konventionen (Kurzform):

- LCOE wird forward gerechnet; Sunk-Costs leben in separaten
  Kontextfeldern und gehen nicht in die Pfad-Vergleichs-Arithmetik ein.
- WACC pro Technologie (Eigen- und Fremdkapital-Mix unterschiedlich
  zwischen PV/Wind und KKW).
- Bridge-Gas läuft als Mengen-Bilanz-Mengen-Aufweichung im Phase-2-
  Stress-Block, nicht als separate Pfad-Strategie.
- Endogene Brennstoff-Cap-Erweiterung in Notfällen (siehe Docstring
  ``_dispatch_and_balance``).

Sensitivität (Baseline, Tornado, Monte-Carlo, Schadens-Asymmetrie)
lebt in :mod:`enesys.core.sensitivity`; die externe Sektor-Kopplungs-
Schicht in :mod:`enesys.core.sector_coupling`. Konsumenten importieren
direkt aus dem jeweiligen Submodul.

Formel-Herleitungen: siehe ``docs/FORMULAS.md``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .dispatch import dispatch_and_balance as _dispatch_and_balance
from .fuel import co2_from_fuels as _co2_from_fuels
from .fuel import co2_price_year as _co2_price_year
from .fuel import resolve_co2_price as _resolve_co2_price
from .fuel import resolve_fuel_price as _resolve_fuel_price
from .inventories import (
    DEMAND_CURVES,
    PATH_POLICY,
    TECH_INVENTORY,
)
from .lcoe import annuity_factor as _annuity_factor
from .lcoe import compute_lcoe as _compute_lcoe
from .lcoe import resolve_tech_field as _resolve_tech_field
from .lcoe import secondary_surcharge as _secondary_surcharge
from .path_ids import PATH_IDS
from .realization_belief import (
    CAMP_H2_WORLD_BELIEF,
    CAMP_NEP_WORLD_BELIEF,
    CAMP_NUCLEAR_WORLD_BELIEF,
    effective_realization,
)
from .sector_coupling import sector_coupling_external
from .system_state import SystemState

# Underscore-Re-Exports: ``_co2_price_year``, ``_resolve_co2_price``,
# ``_resolve_fuel_price``, ``_annuity_factor``, ``_secondary_surcharge``
# werden hier nur für externe Konsumenten (Tests, UI) als Modul-Symbole
# bereitgestellt; intern werden die ``compute_lcoe``- und
# ``resolve_tech_field``-Funktionen aus :mod:`enesys.core.lcoe` /
# :mod:`enesys.core.fuel` direkt genutzt.
__all__ = (
    "PathResult",
    "PATH_LABEL",
    "co2_lockin_metric",
    "co2_lockin_report",
    "compute_path",
    "investment_total_eur_per_path",
    "_annuity_factor",
    "_co2_from_fuels",
    "_co2_price_year",
    "_compute_lcoe",
    "_dispatch_and_balance",
    "_resolve_co2_price",
    "_resolve_fuel_price",
    "_resolve_tech_field",
    "_secondary_surcharge",
)

# ---------------------------------------------------------------------------
# Param-Override-Schicht für Tornado/Monte-Carlo
# ---------------------------------------------------------------------------
#
# LCOE-Schicht: CAPEX, WACC, VLH, OPEX, Brennstoff-Preis, CO2-Preis.
# Mengen-Bilanz-Schicht: nep_realisierung_grad, kkw_realisierung_grad —
# multiplikativ auf installierte Kapazität pro Tech-Kategorie. Wirkt über
# capacity_gw_override in TechEntry.max_dispatch_twh_per_year, damit die
# Mengen-Bilanz mengen-konsistent reagiert (weniger Kapazität → weniger
# Dispatch → mehr Brennstoff-Backup → mehr CO2 → höhere LCOE).

# Tech-Kategorien für Realgrad-Skalierung. nep_realisierung_grad wirkt auf
# EE-Erzeugung (PV, Wind, Bio, Wasser); kkw_realisierung_grad wirkt auf
# KKW-Bestand + KKW-Neubau (EPR und SMR).
_EE_TECHS = frozenset({"pv", "wind_onshore", "wind_offshore", "bio", "wasser"})
_KKW_TECHS = frozenset({"kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"})

# Welt-Belief-Tabellen für die drei Realisierungs-Hebel leben in
# ``enesys.core.realization_belief``. Mechanik: effektive Realisierung =
# min(Politik-Wunsch aus PATH_POLICY, Welt-Belief des Lagers).

#: Alias für die KKW-Welt-Belief-Tabelle (Bestands-Konsumenten).
CAMP_NUCLEAR_REALIZATION = CAMP_NUCLEAR_WORLD_BELIEF


# Battery-Energie-Bilanz: jährlicher RTE-Verlust als Demand-Mehrbedarf.
#
# Im annual-aggregate-Modell ist Battery keine Erzeugungs-Tech (vlh_normal=0;
# Battery liefert Demand-Verschiebung, keine neue Energie). Die RTE-Verluste
# der Tagesarbitrage müssen aber von der Erzeugungs-Seite zusätzlich gedeckt
# werden — sonst rechnet das Modell die Battery-Tagesarbitrage »verlustfrei«,
# was die EE-Pfade strukturell günstiger erscheinen lässt als sie sind.
#
# Modellierung: pro installierter Battery-GW × _BATTERY_DISCHARGE_VLH wird
# das »Discharge-Äquivalent« geschätzt; die RTE-Verluste daraus erhöhen den
# Jahres-Demand der Generatoren um Discharge × (1/RTE − 1). Damit zahlen die
# Pfade mit höherer Battery-Trajektorie automatisch den Mehraufwand für die
# Lade-Verluste. Battery-CAPEX selbst läuft weiterhin über die Sekundär-
# Schicht (Storage-Komponente in :func:`secondary_surcharge`).
#
# Eine vollständige Integration von Battery in die primäre Dispatch-Schleife
# (Battery in ``dispatch_used``, Charge-Pool aus PV/Wind-Überschuss) verlangt
# Stunden-Granularität und ist als eigene Welle nach V1.0 vorgesehen.
_BATTERY_RTE: float = 0.85
"""Round-trip-Efficiency LFP-Battery (AC-AC, inkl. Inverter-Verluste).

[SRC: BNEF-2025-ESS LFP-Datenblatt 84-86 %; konservativer Mittelwert.]"""


def _battery_rte_loss_twh(
    battery_gw: float,
    camp: str,
    param_overrides: dict[str, float] | None = None,
) -> float:
    """RTE-Verlust als zusätzlicher Demand-Bedarf für die Generatoren.

    Annual-aggregate-Schätzung: Battery-GW × Discharge-VLH × (1/RTE − 1).
    Wirkt nur, wenn Battery-Kapazität installiert ist; greift über alle
    Pfade symmetrisch entlang ihrer TECH_INVENTORY["battery"]-Cap-
    Trajektorie. Die Discharge-VLH ist lager-spezifisch (CAMP_RANGES-
    Sensi-Achse ``battery_discharge_vlh``): höhere Tagesarbitrage in
    EE-dominierten Lagern, niedrigere in KKW-/Bestand-Lagern mit
    Grundlast-Glättung.

    ``param_overrides["battery_discharge_vlh"]`` überschreibt den
    Lager-Default — Tornado/Monte-Carlo können den VLH-Hebel als Sensi-
    Achse durchfahren.

    **Kosten-Asymmetrie ist Modell-Artefakt, nicht Tech-Effekt.** Die
    Mengen-Wirkung ist pfad-symmetrisch (gleiche Battery-Cap → gleicher
    Δ-TWh-Bedarf an die Generatoren). In ct/kWh kommt eine asymmetrische
    Wirkung dadurch zustande, dass die zusätzliche Erzeugung zum Pfad-
    spezifischen Strom-Mix-Preis verrechnet wird — KKW-Pfade mit teurem
    Mix verteuern sich pro RTE-Verlust-TWh stärker als EE-Pfade. Das ist
    keine Aussage über »Battery trifft KKW härter«, sondern eine direkte
    Konsequenz der Mengen-Bilanz × Pfad-Mix-Preis.
    """
    if battery_gw <= 0.0:
        return 0.0
    if param_overrides and "battery_discharge_vlh" in param_overrides:
        vlh = float(param_overrides["battery_discharge_vlh"])
    else:
        from .camp_ranges import CAMP_RANGES

        vlh_spec = CAMP_RANGES["battery_discharge_vlh"]
        vlh = float(vlh_spec.get(camp, vlh_spec["neutral_default"]))  # type: ignore[arg-type]
    discharge_twh = battery_gw * vlh / 1000.0
    return discharge_twh * (1.0 / _BATTERY_RTE - 1.0)


def _apply_realization_rate_overrides(
    tech_id: str,
    raw_capacity_gw: float,
    overrides: dict[str, float] | None,
    existing_share_gw: float = 0.0,  # [MODEL: 0 = Standard-Behavior wenn Aufrufer nichts übergibt; compute_path liefert tech.auslauf_kurve(year)]
) -> float:
    """Realisierungsgrad-Skalierung auf installierte Tech-Kapazität.

    - ``nep_realisierung_grad``: multiplikativ auf EE-Techs.
    - ``kkw_realisierung_grad``: multiplikativ auf KKW-Techs.

    Default-Wert ist 1.0 (kein Realgrad-Effekt). Realgrad < 1 reduziert
    die effektive Kapazität — über ``capacity_gw_override`` an
    ``TechEntry.max_dispatch_twh_per_year`` durchgereicht zieht das die
    Mengen-Bilanz mengen-konsistent nach (weniger Dispatch → mehr
    Brennstoff-Backup → höhere LCOE auf den betroffenen Pfaden).

    Realgrad wirkt nur auf den **Zubau** ab 2026,
    nicht auf den 2026-Bestand. Begründung: Politik im Jahr 2026 kann
    nicht rückwirkend bereits installierte Kapazität (z. B. 95 GW PV per
    Ende 2025) reduzieren. ``bestand_anteil_gw`` gibt den Bestand-Anteil
    der raw_capacity_gw an, der nicht skaliert wird.
    """
    if not overrides:
        return raw_capacity_gw
    zubau_anteil_gw = max(0.0, raw_capacity_gw - existing_share_gw)
    if tech_id in _EE_TECHS and "nep_realization_rate" in overrides:
        return existing_share_gw + zubau_anteil_gw * overrides["nep_realization_rate"]
    if tech_id in _KKW_TECHS and "nuclear_realization_rate" in overrides:
        return existing_share_gw + zubau_anteil_gw * overrides["nuclear_realization_rate"]
    return raw_capacity_gw


# Resolver-Schicht (TechEntry/FuelEntry/CO₂-Preis mit Override-Vorrang)
# lebt in :mod:`enesys.core.lcoe` und :mod:`enesys.core.fuel`; siehe
# Top-Import-Block für die Underscore-Aliase.


# ---------------------------------------------------------------------------
# Datenmodell — PathResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PathResult:
    """Schatten-Ergebnis pro (Pfad, Jahr, Lager).

    Ein Eintrag pro Pfad-Jahr-Lager-Kombination. `lcoe_components` zerlegt
    den `lcoe_ct_kwh` in die fünf Kostenarten (CAPEX-Annuität, OPEX-fix,
    OPEX-var, Brennstoff, CO2-Pönale) plus Sekundär-Aufschlag (Speicher /
    Netz / Stabilität).

    `capacity_buildup`, `dispatch_used` und `fuel_used` machen die Mengen-
    Bilanz transparent: Welche Kapazität ist verbaut, wie viel Strom liefert
    sie, welcher Brennstoff wird konsumiert. Die Mengen-Bilanz schließt
    per Konstruktion auf `demand_twh` (±0,1 %, abgedeckt durch die
    Coverage-Matrix-Tests in `tests/consistency/test_coverage_matrix.py`).

    co2_mt aggregiert über `fuel_used × FuelEntry.co2_t_per_mwh_th`. Sekundär-
    Quellen (Stabilität, Netz) sind in `lcoe_components["sekundaer"]` enthalten,
    nicht in co2_mt.

    `system_state`:
    NORMAL = Normalbetrieb (dauer_max + vlh_normal), DUNKELFLAUTE =
    Stress-Kurzfrist (boost_max + vlh_max_boost). Stress-Resultate sind
    die Mengen-Bilanz-Basis für `extensions/winter_stress.winter_stress_balance`.
    """

    path_id: str
    year: int
    camp: str
    demand_twh: float
    capacity_buildup: dict[str, float]  # tech_id -> GW installiert
    dispatch_used: dict[str, float]  # tech_id -> TWh erzeugt
    fuel_used: dict[str, float]  # fuel_id -> TWh verbraucht (thermisch)
    co2_mt: float
    lcoe_components: dict[
        str, float
    ]  # capex_annuity / opex_fix / opex_var / fuel / co2 / sekundaer
    lcoe_ct_kwh: float
    mix_by_technology: dict[str, float] = field(default_factory=dict)
    """Pro-Tech-Anteil an der Strom-Erzeugung des Jahres
    (``dispatch_used[tech] / sum(dispatch_used)``). Summiert auf ~1.
    Kanonische Schnittstelle für Mix-Visualisierungen (Hochlauf-Plots,
    Stack-Charts): Chart-Generatoren lesen den Mix aus diesem Feld,
    statt eigene Skalierungs-Trajektorien zu pflegen. Aggregationen
    über Jahres-Bereiche liefern :func:`enesys.core.path_aggregations.snapshot_mix`,
    :func:`mean_mix`, :func:`steady_state_mix`."""
    provenance: tuple[str, ...] = field(default_factory=tuple)
    """Liste der konsumierten Inventar-Source-Tags. Befüllt aus
    `TechEntry.source` / `FuelEntry.source` der eingesetzten Komponenten.
    Konvergenz-Kriterium: jeder LCOE-Wert ist auf seine Primärquellen
    zurückführbar."""
    system_state: str = "normal"  # [MODEL: SystemState-Enum-Wert (normal/scarcity/dunkelflaute). PathResult speichert den effektiven State des Aufrufs.]
    """SystemState-Enum-Wert als String. Dispatch lief unter diesem State;
    Reserve-Aufbau und endogene Brennstoff-Cap-Erweiterung greifen nur
    bei NORMAL-Aufruf."""
    unserved_twh: float = 0.0  # [MODEL: Nach Reserve-Aufbau und endogener Cap-Erweiterung verbleibender ungedeckter Demand; in lcoe_components['voll_unserved'] mit _VOLL_EUR_PER_MWH bepreist.]
    """Verbleibender ungedeckter Demand nach Reserve-Aufbau und endogener
    Brennstoff-Cap-Erweiterung. Wird in ``lcoe_components['voll_unserved']``
    mit ``_VOLL_EUR_PER_MWH`` bepreist."""

    sector_coupling_external_eur_per_year: float = 0.0  # [MODEL: Externe Sektor-Kopplungs-Kosten parallel zu Strom-LCOE, Hand-Schätzung mit Drei-Quellen-Triangulation UBA+JEC+AGORA (siehe enesys.core.sector_coupling). Default 0 = keine Lücke (aktive Pfade mit 840 TWh Demand).]
    """Externe Sektor-Kopplungs-Kosten für Pfade mit Strom-Demand
    < 840 TWh (WEITER-SO 540, BESTAND 510). Fossile Wärme +
    Verbrenner-Mobility + CO₂-Pönale. Diese Schicht ist **parallel**
    zum Strom-LCOE, NICHT in lcoe_ct_kwh enthalten. Für aktive Pfade
    (840 TWh Demand) ist der Wert 0.

    [SRC: AGORA-2045 + JEC WTW v5 + UBA-Emissionsfaktoren- Triangulation, siehe ``enesys.core.sector_coupling``.]"""

    co2_external_mt_per_year: float = 0.0  # [MODEL: Externe CO2-Mengen aus fossiler Waerme (0,22 t/MWh-th UBA) + Verbrenner-Mobility (0,30 t/MWh-WTW JEC). Default 0 = keine Luecke (aktive Pfade).]
    """Externe CO₂-Mengen aus fossiler Wärme + Verbrenner-Mobility (Mt/a).
    Begleitet `sektor_kopplung_extern_eur_per_year`, ist **nicht** in
    `co2_mt` (Strom-System-CO₂) enthalten. Für aktive Pfade (840 TWh
    Demand) = 0."""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def _merge_year_overrides(
    year: int,
    set_yearly: dict[int, dict[str, float]],
    param_overrides: dict[str, float] | None,
    param_overrides_yearly: dict[int, dict[str, float]] | None,
) -> dict[str, float] | None:
    """Effektive Overrides für ein Jahr aus drei Quellen mergen.

    Priorität (niedrig → hoch): ``set_yearly[year]`` (ParamSet-Trajektorie)
    → ``param_overrides`` (konstant über alle Jahre) →
    ``param_overrides_yearly[year]`` (jahres-spezifisch).
    Gibt ``None`` zurück, wenn keine Quelle Werte für dieses Jahr liefert.
    """
    if not (set_yearly or param_overrides or param_overrides_yearly):
        return None
    merged = dict(set_yearly.get(year, {}))
    if param_overrides:
        merged.update(param_overrides)
    if param_overrides_yearly and year in param_overrides_yearly:
        merged.update(param_overrides_yearly[year])
    return merged or None


def _build_capacity_for_year(
    year: int,
    path_id: str,
    camp: str,
    year_overrides: dict[str, float] | None,
) -> dict[str, float]:
    """Pro-Tech-Kapazität für ein Jahr inklusive Realgrad-Override.

    Liest die Roh-Kapazität aus ``TechEntry.capacity_gw`` und wendet die
    Realgrad-Skalierung (`nep_realization_rate` / `nuclear_realization_rate`)
    multiplikativ auf den Zubau-Anteil an.
    """
    capacity: dict[str, float] = {}
    for tech_id, tech in TECH_INVENTORY.items():
        raw = tech.capacity_gw(year, path_id, camp)
        bestand = tech.existing_share_now(year, path_id, camp)
        capacity[tech_id] = _apply_realization_rate_overrides(
            tech_id,
            raw,
            year_overrides,
            existing_share_gw=bestand,
        )
    return capacity


def compute_path(
    path_id: str,
    years: Iterable[int],
    camp: str = "neutral_default",
    *,
    system_state: SystemState | None = None,
    param_overrides: dict[str, float] | None = None,
    param_overrides_yearly: dict[int, dict[str, float]] | None = None,
    param_set: str | None = None,
) -> list[PathResult]:
    """Schatten-Pipeline für einen Pfad über ein Jahres-Intervall.

    Schritte pro Jahr (§ 3.1 Architektur-Design):

    1. Kapazitäts-Aufbau pro Tech: `TechEntry.bestand_gw_2026` +
       `auslauf_kurve` + akkumulierter `max_zubau_gw_per_year`.
    2. Demand: `DEMAND_CURVES[path_id]` summiert base + Elektrifizierungs-
       Zusatz.
    3. Dispatch: `PATH_POLICY[path_id].dispatch_priority` × Brennstoff-
       Verfügbarkeit aus `FUEL_INVENTORY` (Merit-Order pro Stunde-Äquivalent
       als Jahres-Aggregat).
    4. LCOE: Annuität pro Tech (WACC aus `TechEntry.wacc_pct`) +
       OPEX + Brennstoff-Kosten + CO2-Pönale + Sekundär-Schicht.

    `camp` ist einer der vier Schlüssel aus `CAMP_RANGES` (siehe
    `core/camp_ranges.py`): ``neutral_default``, ``ee_optimistic``,
    ``atom_optimistic``, ``bestand_optimistic``.

    `param_overrides` erlaubt feinkörnige Parameter-Variation für
    Tornado/Monte-Carlo. Flacher Namespace mit
    Punkt-Separator:

    - ``"<tech_id>.<field>"``: TechEntry-Field-Override (capex_eur_kw,
      wacc_pct, vlh_normal, opex_fix_eur_kw_a, opex_var_eur_mwh).
    - ``"<fuel_id>.preis_eur_mwh"``: Brennstoff-Preis-Override.
    - ``"co2_price_eur_t"``: globaler CO₂-Preis (überschreibt Lager-
      Default).

    None (Default) = kein Override, Standard-Verhalten.

    `param_overrides_yearly` erlaubt jahres-spezifische Overrides
    (``dict[int, dict[str, float]]``). Hat Vorrang vor ``param_overrides``
    pro Jahr und überschreibt eventuelle ``param_set``-Trajektorien-Werte.

    `param_set` lädt ein externes Annahmen-Substrat aus der ``param_sets``-
    Registry (z.B. ``"ariadne_pypsa"``). Die Trajektorie wird über die
    angeforderten Jahre interpoliert und als Override-Basis verwendet —
    ``param_overrides`` und ``param_overrides_yearly`` haben höhere
    Priorität und überschreiben Set-Werte pro Jahr.

    Vorrang pro Jahr (niedrig → hoch):
      ``param_set`` (Trajektorie) → ``param_overrides`` (konstant)
      → ``param_overrides_yearly[year]`` (pro Jahr).
    Override hat Vorrang vor Lager und vor TechEntry.

    Realgrad-Overrides (``nep_realisierung_grad``,
    ``kkw_realisierung_grad``) sind Mengen-Bilanz-Eingriff: sie
    skalieren ``max_dispatch_twh_per_year`` und Brennstoff-Backup
    mit, nicht nur die LCOE-Schicht.

    `system_state`:
    NORMAL = Normalbetrieb, Brennstoff-Mengen aus
    `FuelEntry.dauer_max_twh_per_year` und VLH aus `TechEntry.vlh_normal`.
    DUNKELFLAUTE = Stress-Kurzfrist, Brennstoff-Mengen aus
    `FuelEntry.boost_max_twh_per_year` und VLH aus `TechEntry.vlh_max_boost`
    (Fallback: `vlh_normal` wenn `vlh_max_boost` None ist). Stress-Resultate
    sind die Mengen-Bilanz-Basis für `winter_stress.winter_stress_balance` und sollten nicht
    direkt als LCOE-Aussage interpretiert werden — der LCOE-Wert im
    Stress-Lauf ist der Spitzen-Erzeugungs-LCOE, kein Jahres-Durchschnitt.
    """
    if path_id not in PATH_POLICY:
        raise ValueError(f"Unbekannter Pfad {path_id!r}; verfügbar: {sorted(PATH_POLICY)}")

    policy = PATH_POLICY[path_id]
    curve = DEMAND_CURVES[path_id]
    requested_years = list(years)
    if not requested_years:
        return []

    # default_policy implizit als param_override aktivieren.
    # PolicySetting-Felder werden via setdefault durchgereicht — ein
    # expliziter Aufrufer-Override (z.B. regret_decision_tree-Szenarien)
    # hat Vorrang.
    if policy.default_policy is not None:
        overrides = dict(param_overrides or {})
        # Einheitlicher Min-Operator zwischen Pfad-Politik und
        # Lager-Welt-Belief für die drei Realisierungs-Hebel.
        # Pfad-Politik darf aktiv drosseln (BESTAND drückt unter Belief),
        # Welt darf skeptisch sein (Atom-Lager drosselt EE-Politik).
        overrides.setdefault(
            "nep_realization_rate",
            effective_realization(
                policy.default_policy.nep_realization_rate,
                CAMP_NEP_WORLD_BELIEF,
                camp,
            ),
        )
        overrides.setdefault(
            "nuclear_realization_rate",
            effective_realization(
                policy.default_policy.nuclear_realization_rate,
                CAMP_NUCLEAR_WORLD_BELIEF,
                camp,
            ),
        )
        overrides.setdefault(
            "h2_realization_rate",
            effective_realization(
                policy.default_policy.h2_realization_rate,
                CAMP_H2_WORLD_BELIEF,
                camp,
            ),
        )
        param_overrides = overrides

    # Akkumulation startet 2026 unabhängig vom Range-Input. So funktioniert
    # die Pipeline auch bei nicht-zusammenhängenden Jahres-Listen
    # (z.B. nur [2045, 2055] für Schnell-Schätzungen). Kapazität pro Tech
    # liest sich aus ``TechEntry.capacity_gw`` als Single Source.
    from .system_state import SystemState

    effective_state = system_state if system_state is not None else SystemState.NORMAL

    # h2_realization_rate als operativer Politik-Hebel. Resolved aus
    # param_overrides (Monte-Carlo/Tornado) oder policy.default_policy.
    # Wirkt multiplikativ auf h2_inland/h2_import-Verfügbarkeit in
    # ``TechEntry._max_electricity_from_fuel`` und
    # ``_fuel_used_from_dispatch``.
    if param_overrides and "h2_realization_rate" in param_overrides:
        h2_rate = float(param_overrides["h2_realization_rate"])
    elif policy.default_policy is not None:
        h2_rate = float(policy.default_policy.h2_realization_rate)
    else:
        h2_rate = 1.0

    # ParamSet-Trajektorie als Override-Basis auflösen (vor dem Year-Loop).
    # Set-Werte haben niedrigere Priorität als param_overrides und
    # param_overrides_yearly — beides wird im Loop oben drauf gemerged.
    if param_set is not None:
        from enesys.core.param_sets import get as _get_param_set

        set_yearly = _get_param_set(param_set).overrides_yearly(requested_years)
    else:
        set_yearly = {}

    results: list[PathResult] = []
    for year in requested_years:
        year_overrides = _merge_year_overrides(
            year, set_yearly, param_overrides, param_overrides_yearly
        )
        capacity = _build_capacity_for_year(year, path_id, camp, year_overrides)
        demand_twh = curve.base_demand_twh(year) + curve.electrification_extra_twh(year, camp)
        # Battery-RTE-Verlust als zusätzlicher Demand-Bedarf für die
        # Generatoren (annual-aggregate-Modellierung der Tagesarbitrage-
        # Verluste). Discharge-VLH ist lager-spezifisch über die
        # CAMP_RANGES-Sensi-Achse ``battery_discharge_vlh``.
        demand_twh += _battery_rte_loss_twh(
            capacity.get("battery", 0.0), camp, param_overrides=year_overrides
        )
        (
            dispatch_used,
            fuel_used,
            self_reserve_gw,
            unserved_twh,
            fuel_cap_expansion_th,
        ) = _dispatch_and_balance(
            year,
            path_id,
            camp,
            demand_twh,
            policy,
            system_state=effective_state,
            capacity_override=capacity,
            h2_realization_rate=h2_rate,
        )
        # Reserve-Aufbau geht in die Capacity-Bilanz ein
        for tech_id, extra_gw in self_reserve_gw.items():
            capacity[tech_id] = capacity.get(tech_id, 0.0) + extra_gw
        lcoe_components, lcoe_ct_kwh, provenance = _compute_lcoe(
            year,
            path_id,
            camp,
            capacity,
            dispatch_used,
            fuel_used,
            param_overrides=year_overrides,
            unserved_twh=unserved_twh,
            demand_twh=demand_twh,
            fuel_cap_expansion_th=fuel_cap_expansion_th,
        )
        co2_mt = _co2_from_fuels(fuel_used)

        total_dispatch = sum(dispatch_used.values())
        if total_dispatch > 0:
            mix_by_technology = {
                tech_id: twh / total_dispatch for tech_id, twh in dispatch_used.items() if twh > 0
            }
        else:
            mix_by_technology = {}

        # Externe Sektor-Kopplungs-Schicht parallel zum Strom-LCOE.
        # Wirkt nicht auf lcoe_ct_kwh.
        sk_extern_eur, co2_extern_mt = sector_coupling_external(
            year=year,
            demand_twh=demand_twh,
            path_id=path_id,
            camp=camp,
            param_overrides=year_overrides,
        )

        results.append(
            PathResult(
                path_id=path_id,
                year=year,
                camp=camp,
                demand_twh=demand_twh,
                capacity_buildup=dict(capacity),
                dispatch_used=dict(dispatch_used),
                fuel_used=dict(fuel_used),
                co2_mt=co2_mt,
                lcoe_components=dict(lcoe_components),
                lcoe_ct_kwh=lcoe_ct_kwh,
                mix_by_technology=mix_by_technology,
                provenance=provenance,
                system_state=effective_state.value,
                unserved_twh=unserved_twh,
                sector_coupling_external_eur_per_year=sk_extern_eur,
                co2_external_mt_per_year=co2_extern_mt,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Dispatch + Mengen-Bilanz
# ---------------------------------------------------------------------------
#
# Dispatch-Logik (dispatch_and_balance, fuel_used_from_dispatch,
# initial_fuel_caps_th) lebt in :mod:`enesys.core.dispatch`.
# ``dispatch_and_balance`` ist als ``_dispatch_and_balance`` im
# Modul-Top-Import verfügbar.


# ---------------------------------------------------------------------------
# Pfad-Reihenfolge + Labels
# ---------------------------------------------------------------------------


# Modul-lokaler Alias für die kanonische Sechs-Pfade-Reihenfolge —
# Single Source of Truth in core.path_ids.PATH_IDS.
_PATH_ORDER = PATH_IDS

_PATH_LABEL: dict[str, str] = {
    "weiterso": "WEITER-SO",
    "bestand": "BESTAND",
    "ee_gas": "EE-GAS",
    "ee_h2": "EE-H2",
    "kkw_gas": "KKW-GAS",
    "kkw_h2": "KKW-H2",
}


# ---------------------------------------------------------------------------
# Investitionsvolumen-Total pro Pfad (Modell-Soll-Funktion)
# ---------------------------------------------------------------------------


def investment_total_eur_per_path(
    path_id: str,
    *,
    camp: str = "neutral_default",
    period_start: int = 2026,  # [MODEL: Modell-Start-Jahr — Konvention für alle Pfad-Trajektorien]
    period_end: int = 2045,  # [SRC: KSG-2021] Klimaneutralitäts-Frist
) -> float:
    """Total nominales Investitionsvolumen (Erzeugungs-CAPEX) pro Pfad.

    Summiert Zubau-CAPEX über die Periode: ΔGW pro Jahr × CAPEX_eur_kw
    des Zubau-Jahres × 1e6 (Unit-Umrechnung GW→kW) über alle Techs im
    TECH_INVENTORY. Der initiale 2026-Bestand wird als Vor-Modell-Bestand
    gewertet und nicht eingerechnet — erst Δ ab period_start+1 zählt als
    Investition. CAPEX-Werte folgen Lernkurven (PV, Wind, Batterie,
    Elektrolyse) und Lager-Setzung (KKW-WACC etc.), pro Zubau-Jahr
    aufgelöst.

    Diese Größe deckt ausschließlich die Erzeugungs-Schicht (Schicht 1
    der Vier-Schichten-LCOE-Architektur). Netz-Investitionen (Schicht 3)
    und Speicher (Schicht 2) sind als Sekundär-Aufschlag in ct/kWh
    integriert, nicht als direkte GW × CAPEX — sie werden hier nicht
    summiert. Pfad-Komplett-Investitionsvolumina inklusive Trassen und
    Speicher liegen deutlich über dem Erzeugungs-Anteil dieser Funktion.

    Args:
        path_id: Pfad-Identifier (z.B. "ee_gas", "kkw_h2").
        camp: Lager-Schlüssel (default neutral_default).
        period_start: Erstes Jahr der Investitions-Periode (default 2026).
        period_end: Letztes Jahr (default 2045 = Klimaneutralitäts-Frist).

    Returns:
        Total nominales Erzeugungs-Investitionsvolumen in EUR.
    """
    years = list(range(period_start, period_end + 1))
    results = compute_path(path_id, years, camp=camp)
    if not results:
        return 0.0

    prev_capacity: dict[str, float] = dict(results[0].capacity_buildup)
    total_capex_eur = 0.0

    for r in results[1:]:
        for tech_id, gw in r.capacity_buildup.items():
            delta_gw = gw - prev_capacity.get(tech_id, 0.0)
            if delta_gw <= 0:
                continue
            tech = TECH_INVENTORY[tech_id]
            capex = _resolve_tech_field(tech, "capex_eur_kw", r.year, camp, None)
            total_capex_eur += delta_gw * 1e6 * capex
        prev_capacity = dict(r.capacity_buildup)

    return total_capex_eur


# ---------------------------------------------------------------------------
# CO₂-Lock-in-Kennzahl (BESTAND-Referenz-Verstärkung)
# ---------------------------------------------------------------------------


def co2_lockin_metric(
    path_id: str,
    *,
    camp: str = "neutral_default",
    start_year: int = 2026,
    end_year: int = 2055,
    lockin_threshold_year: int = 2045,
) -> dict[str, str | float]:
    """CO₂-Lock-in-Kennzahl pro Pfad — System-Boundary (Strom + extern).

    Liefert Aggregate aus der CO₂-Trajektorie mit System-Boundary
    (Strom-Sektor + externe Sektor-Kopplungs-Emissionen aus
    fossiler Heizung/Mobility, die durch den Pfad-Mix nicht ersetzt
    werden):

    - ``kumuliert_total_mt``: Σ (Strom-CO₂ + Extern-CO₂) über
      `start_year`..`end_year`. System-Boundary, methodisch korrekt
      gegen WEITER-SO/BESTAND, die fossile Sektor-Kopplung weiter
      tragen.
    - ``kumuliert_strom_mt`` / ``kumuliert_extern_mt``: Auftrennung
      Strom-Sektor und externe Sektor-Kopplung — für Transparenz.
    - ``kumuliert_lockin_mt``: Σ Gesamt-CO₂ über
      `lockin_threshold_year`..`end_year` — Lock-in-Anteil nach 2045.
    - ``co2_rate_endjahr_mt``: Strom-CO₂ @ `end_year` (Endzustand,
      Mt/a; ohne extern, weil im Steady-State Sektor-Kopplung in den
      aktiven Pfaden abgeschlossen ist).

    Methodischer Hintergrund: ``r.co2_mt`` rechnet nur den Strom-Sektor.
    Pfade mit voller Sektor-Kopplung (EE-GAS, EE-H2, KKW-GAS, KKW-H2)
    ziehen Heizung+Mobility in den Strom-Sektor und tragen deren
    CO₂-Last über den Strom-Mix; WEITER-SO und BESTAND lassen Heizung
    und Mobility extern fossil weiterlaufen, die Emissionen tauchen
    aber nicht in ``r.co2_mt`` auf — sie sind in
    ``r.co2_external_mt_per_year`` ausgewiesen. System-Boundary
    aggregiert beide Komponenten und ergibt den ehrlichen
    Klima-Vergleich über alle sechs Pfade.

    BESTAND und WEITER-SO sind im System-Boundary klare Lock-in-Kings
    (~4,4–4,9 Gt 30y); die aktiven Pfade liegen bei 2,7–3,3 Gt mit
    EE-H2 als Klima-Sieger.

    [SRC: BESTAND (path_policy.py BESTAND-derivation): Kapazitätsmarkt-Garantie 2,3 GW/a Erdgas-Neubau 2026-2035, Lebensdauer 40 a → strukturelles CO₂-Lock-in. Diese Kennzahl exponiert die Lock-in-Mengen.]
    """
    years = list(range(start_year, end_year + 1))
    results = compute_path(path_id, years, camp=camp)
    strom_per_year = {r.year: r.co2_mt for r in results}
    extern_per_year = {r.year: r.co2_external_mt_per_year for r in results}
    total_per_year = {y: strom_per_year[y] + extern_per_year[y] for y in years}
    kum_strom = sum(strom_per_year[y] for y in years)
    kum_extern = sum(extern_per_year[y] for y in years)
    kum_total = sum(total_per_year[y] for y in years)
    kum_lockin = sum(total_per_year[y] for y in years if y >= lockin_threshold_year)
    return {
        "path": path_id,
        "lager": camp,
        "kumuliert_total_mt": kum_total,
        "kumuliert_strom_mt": kum_strom,
        "kumuliert_extern_mt": kum_extern,
        "kumuliert_lockin_mt": kum_lockin,
        "co2_rate_endjahr_mt": strom_per_year[end_year],
        "start_year": start_year,
        "end_year": end_year,
        "lockin_threshold_year": lockin_threshold_year,
    }


def co2_lockin_report(
    *,
    paths: tuple[str, ...] | None = None,
    camp: str = "neutral_default",
    start_year: int = 2026,
    end_year: int = 2055,
    lockin_threshold_year: int = 2045,
) -> list[dict]:
    """CO₂-Lock-in-Vergleich über alle sechs Pfade.

    Sortiert nach `kumuliert_lockin_mt` absteigend — BESTAND oben,
    EE-H2/KKW-H2 unten. Materialisiert die Aussage »BESTAND erkauft
    Versorgung durch CO₂-Lock-in«.
    """
    if paths is None:
        paths = PATH_IDS
    rows = [
        co2_lockin_metric(
            p,
            camp=camp,
            start_year=start_year,
            end_year=end_year,
            lockin_threshold_year=lockin_threshold_year,
        )
        for p in paths
    ]
    rows.sort(key=lambda r: r["kumuliert_lockin_mt"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Forward-Cost-Wrapper
# ---------------------------------------------------------------------------


PATH_LABEL: dict[str, str] = dict(_PATH_LABEL)
"""Public Mapping Pfad-ID (lowercase) → Anzeige-Label (uppercase).

Sechs-Pfade-Sprache: WEITER-SO, BESTAND, EE-GAS, EE-H2, KKW-GAS, KKW-H2.
"""
