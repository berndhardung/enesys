"""Schema für `TECH_INVENTORY`.

Tech-Tabelle pro Erzeugungs-Technologie. Inventar-Befüllung mit
heutigen Werten + Source-Tags rückverfolgen.

Magic-Number-Disziplin: jeder Eintrag muss `source` oder `derivation`
tragen. `__post_init__` erzwingt das beim Konstruktor; der Architektur-
Test `tests/architecture/test_no_magic_numbers.py` prüft das auf
Inventar-Ebene.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..system_state import SystemState
    from .fuel_inventory import FuelEntry
    from .path_policy import PathPolicyEntry

# Callable-Signaturen für die zeitabhängigen Felder. Lager ist als str
# typisiert (z. B. "default", "ee", "atom", "skeptisch"); Politik-Setzung
# wird via Pfad-Default in `path_policy.PolitikSetzung` ausgewählt.
DecayCurve = Callable[[int], float]  # (year) -> verbleibende_gw
AdditionsCallable = Callable[[int, str, str], float]  # (year, path, lager) -> gw
CapexCallable = Callable[[int, str], float]  # (year, lager) -> eur_kw
WaccCallable = Callable[[int, str], float]  # (year, lager) -> pct (z. B. 0.035)


@dataclass(frozen=True)
class TechEntry:
    """Schema für einen Eintrag in `TECH_INVENTORY`.

    Felder entsprechen § 2.1 des Architektur-Designs. Reihenfolge der
    Felder folgt der Tabelle dort.
    """

    tech_id: str
    existing_gw_2026: float
    decay_curve: DecayCurve
    max_additions_gw_per_year: AdditionsCallable
    vlh_normal: float
    vlh_max_boost: float | None
    lifetime_years: int
    capex_eur_kw: CapexCallable
    opex_fix_eur_kw_a: float
    opex_var_eur_mwh: float
    wacc_pct: WaccCallable
    fuel_set: tuple[str, ...]
    source: str = ""
    derivation: str = ""
    efficiency_el: float = 1.0
    """Thermisch-elektrische Effizienz η_el.

    Verhältnis Strom-Erzeugung zu thermischem Brennstoff-Input. Für Techs
    ohne Brennstoff-Eingang (PV, Wind, Wasser, Battery, Elektrolyse als
    Strom-Konsument) bleibt η_el = 1,0 ohne Wirkung. Für brennstoff-
    verbrennende Techs ist η_el der Hebel auf Brennstoff-Bedarf und
    CO2-Emissionen: `fuel_used_twh_th = dispatch_twh_el / efficiency_el`.

    η_el wird pro Tech gesetzt; ein einheitliches η_el = 1,0 würde
    fossile und KKW-Brennstoff- und CO2-Kosten um Faktor 1,5-3
    unterzeichnen (siehe Defaults in den TechEntry-Konstrukten)."""

    is_storage: bool = False
    """Speicher-Tech-Marker.

    True für Techs, die nicht in der Dispatch-Schleife stehen (vlh_normal
    typischerweise 0), aber dennoch CAPEX-Annuität in den LCOE einbringen.
    Aktuell nur ``battery``. Konsumiert von ``lcoe.secondary_surcharge()``:
    iteriert über alle is_storage=True-Techs im TECH_INVENTORY und addiert
    pro Tech CAPEX × Annuität / Total-Dispatch-kWh als Speicher-
    Komponente."""

    def __post_init__(self) -> None:
        if not self.source and not self.derivation:
            raise ValueError(
                f"TechEntry {self.tech_id!r} muss source oder derivation "
                f"tragen (Magic-Number-Verbot)."
            )
        if not 0.0 < self.efficiency_el <= 1.0:
            raise ValueError(
                f"TechEntry {self.tech_id!r}: efficiency_el muss in (0, 1] "
                f"liegen, ist {self.efficiency_el}"
            )

    # =====================================================================
    # Single-Source-Tech-Verfügbarkeit
    # =====================================================================

    def capacity_gw(self, year: int, path_id: str, camp: str) -> float:
        """Installierte Kapazität GW in (year, path_id, lager).

        Berücksichtigt:
        - Bestand 2026 via auslauf_kurve
        - tech_constraints["<tech>"] ∈ {forbidden, no_zubau, phaseout_<jahr>}
        - Akkumulierter Zubau 2027..year (Schleife über max_zubau_gw_per_year)
        - Phaseout-Fade auf Bestand (fade_start = max(2026, phaseout_year - 10))

        Single-Source-Tech-Verfügbarkeit: alle Konsumenten der
        Kapazitäts-Trajektorie konsumieren diese Methode statt
        eigene Aufbau-Logik.
        """
        # Lazy import vermeidet Zyklus (path_policy importiert tech_inventory).
        from .path_policy import PATH_POLICY

        policy = PATH_POLICY[path_id]
        constraint = policy.tech_constraints.get(self.tech_id, "")

        if constraint == "forbidden":
            return 0.0

        bestand_now = self.decay_curve(year)

        # Phaseout-Fade auf Bestand: fade_start nie vor 2026, sonst würde
        # ein in der Vergangenheit gesetzter Phaseout-Termin den Bestand
        # rückwirkend abschmelzen.
        if constraint.startswith("phaseout_"):
            phaseout_year = int(constraint.split("_", 1)[1])
            if year >= phaseout_year:
                bestand_now = 0.0
            else:
                fade_start = max(2026, phaseout_year - 10)
                if year > fade_start:
                    # Divisor-Schutz für Sensi mit phaseout_year ≤ 2026.
                    fade = (phaseout_year - year) / max(1, phaseout_year - fade_start)
                    bestand_now *= fade

        # Akkumulierter Zubau 2027..year (Status-Quo 2026 ohne Zubau)
        zubau = 0.0
        if year > 2026 and constraint != "no_zubau":
            for y in range(2027, year + 1):
                if constraint.startswith("phaseout_"):
                    phaseout_year = int(constraint.split("_", 1)[1])
                    if y >= phaseout_year:
                        continue  # nach Phaseout kein Zubau
                zubau += self.max_additions_gw_per_year(y, path_id, camp)

        gw = bestand_now + zubau

        # Demand-Cap muss konsistent in Kapazität UND max_dispatch wirken.
        # Sonst wird PV/Wind über-installiert (CAPEX zu hoch), während Dispatch
        # durch Cap gedeckelt bleibt → künstlich hohe LCOE.
        gw_cap = self._capacity_demand_cap_gw(year, path_id, camp)
        if gw_cap is not None and gw > gw_cap:
            gw = gw_cap
        return gw

    def _capacity_demand_cap_gw(self, year: int, path_id: str, camp: str) -> float | None:
        """Demand-aware Cap als GW-Wert (für `kapazitaet_gw`-Konsistenz).

        Nur für PV/Wind aktiv; sonst None (kein Cap). Status-Quo 2026
        ausgenommen. Liest dieselben Cap-Anteile wie ``_apply_demand_cap``
        aus ``PATH_POLICY[path_id].demand_cap_profile``.
        """
        if self.tech_id not in ("pv", "wind_onshore", "wind_offshore"):
            return None
        if year <= 2026:
            return None
        from .path_policy import PATH_POLICY

        policy = PATH_POLICY.get(path_id)
        if policy is None:
            return None
        anteil = policy.demand_cap_profile.get(self.tech_id, 0.0)
        if anteil <= 0 or self.vlh_normal <= 0:
            return None
        from .demand_curves import DEMAND_CURVES

        curve = DEMAND_CURVES[path_id]
        demand_twh = curve.base_demand_twh(year) + curve.electrification_extra_twh(year, camp)
        if demand_twh <= 0:
            return None
        return demand_twh * anteil * 1000.0 / self.vlh_normal

    def existing_share_now(self, year: int, path_id: str, camp: str) -> float:
        """Bestand-Anteil der installierten Kapazität (nicht skalierbar durch Realgrad).

        Der `min(tech.auslauf_kurve(year), raw)`-Clip ist nötig, weil
        unter Phaseout-Fade `raw = kapazitaet_gw(year)` kleiner als der
        nackte Bestand werden kann.

        Vor 2026: 0 (Realgrad-Politik wirkt nur auf Zubau ab 2026).
        """
        if year < 2026:
            return 0.0
        from .path_policy import PATH_POLICY

        policy = PATH_POLICY[path_id]
        constraint = policy.tech_constraints.get(self.tech_id, "")
        if constraint == "forbidden":
            return 0.0

        bestand_now = self.decay_curve(year)

        if constraint.startswith("phaseout_"):
            phaseout_year = int(constraint.split("_", 1)[1])
            if year >= phaseout_year:
                return 0.0
            fade_start = max(2026, phaseout_year - 10)
            if year > fade_start:
                fade = (phaseout_year - year) / max(1, phaseout_year - fade_start)
                bestand_now *= fade

        raw = self.capacity_gw(year, path_id, camp)
        return min(bestand_now, raw)

    def max_dispatch_twh_per_year(
        self,
        year: int,
        path_id: str,
        camp: str,
        *,
        system_state: SystemState | None = None,
        capacity_gw_override: float | None = None,
        h2_realization_rate: float = 1.0,
    ) -> float:
        """Maximum Strom-Dispatch dieser Tech in (year, path_id, lager) in TWh.

        Single Source of Truth für »wie viel kann diese Tech in diesem
        Pfad-Jahr maximal liefern«.

        ``system_state`` steuert die Dispatch-Bedingungen. Drei Zustände
        ({NORMAL, SCARCITY, DUNKELFLAUTE}) mit physikalischer Semantik:

        - NORMAL: vlh_normal, dauer_max-Brennstoff-Cap
        - SCARCITY (struktureller Politik-Notfall): vlh_normal,
          boost_max nur für ``policy.boost_policy``-Brennstoffe.
        - DUNKELFLAUTE (Winter-Wetter-Stress): EE-VLH × 0,3, Battery=0,
          Import × 0,5, DSM physical-cap, thermisch_flex vlh_max_boost,
          boost_max für alle Brennstoffe.

        Per-Tech-Multiplier-Tabelle in ``core.system_state.flh_multiplier_for_state``.
        """
        from ..system_state import SystemState, flh_multiplier_for_state
        from .fuel_inventory import FUEL_INVENTORY
        from .path_policy import PATH_POLICY

        if system_state is None:
            system_state = SystemState.NORMAL

        policy = PATH_POLICY[path_id]

        gw = (
            capacity_gw_override
            if capacity_gw_override is not None
            else self.capacity_gw(year, path_id, camp)
        )
        if gw <= 0.0:
            return 0.0

        # VLH aus per-Tech-Klasse-Multiplier × SystemState.
        # Spezialfall: thermisch_flex in DUNKELFLAUTE → vlh_max_boost direkt
        # (statt vlh_normal × Multiplier); signalisiert durch mult=None.
        mult = flh_multiplier_for_state(self.tech_id, system_state)
        if mult is None:
            vlh = self.vlh_max_boost if self.vlh_max_boost is not None else self.vlh_normal
        else:
            vlh = self.vlh_normal * mult

        max_tech_twh = gw * vlh / 1000.0

        # Demand-aware Cap (PV/Wind) — pfad-spezifisches Profil
        max_tech_twh = self._apply_demand_cap(max_tech_twh, year, path_id, camp)

        # Brennstoff-Limit (für brennstoff-getragene Techs)
        if self.fuel_set:
            max_fuel_twh = self._max_electricity_from_fuel(
                max_tech_twh,
                year,
                path_id,
                camp,
                policy,
                FUEL_INVENTORY,
                system_state=system_state,
                h2_realization_rate=h2_realization_rate,
            )
            return min(max_tech_twh, max_fuel_twh)

        return max_tech_twh

    def _apply_demand_cap(self, max_tech_twh: float, year: int, path_id: str, camp: str) -> float:
        """Demand-aware Cap für fluktuierende EE-Techs (PV/Wind).

        Pfad-spezifisches Profil aus ``PathPolicyEntry.demand_cap_profile``:
        EE-Pfade haben höhere volatile-EE-Anteile als KKW-Pfade (KKW-Grundlast
        deckt einen Teil), WEITER-SO/BESTAND liegen durch nep_realisierung_grad
        ohnehin unter Cap. Status-Quo-Schutz 2026: Cap greift erst ab 2027.

        Für nicht-fluktuierende Techs (alles außer pv/wind_*) wirkungslos.

        Hintergrund: Anteils-Verankerung sichert strukturell ~10 % thermisches
        Backup (T45-untere-Kante). Pfad-Differenzierung EE-GAS vs. EE-H2 läuft
        nicht über die Cap-Werte selbst, sondern über den Brennstoff-Verbrauch
        in gas_h2ready (H2-first in H2-Pfaden, Erdgas-first in GAS-Pfaden).
        """
        if self.tech_id not in ("pv", "wind_onshore", "wind_offshore"):
            return max_tech_twh
        if year <= 2026:
            return max_tech_twh

        from .path_policy import PATH_POLICY

        policy = PATH_POLICY.get(path_id)
        if policy is None:
            return max_tech_twh
        anteil = policy.demand_cap_profile.get(self.tech_id, 0.0)
        if anteil <= 0:
            return max_tech_twh

        # Demand des Pfads im Jahr
        from .demand_curves import DEMAND_CURVES

        curve = DEMAND_CURVES[path_id]
        demand_twh = curve.base_demand_twh(year) + curve.electrification_extra_twh(year, camp)
        if demand_twh <= 0:
            return max_tech_twh

        cap_twh = demand_twh * anteil
        return min(max_tech_twh, cap_twh)

    def _max_electricity_from_fuel(
        self,
        max_tech_twh: float,
        year: int,
        path_id: str,
        camp: str,
        policy: PathPolicyEntry,
        fuel_inventory: dict[str, FuelEntry],
        *,
        system_state: SystemState | None = None,
        h2_realization_rate: float = 1.0,
        fuel_remaining_th: dict[str, float] | None = None,
    ) -> float:
        """Max Strom-Output aus Brennstoff-Verfügbarkeit (TWh).

        Iteriert pfad-spez. über die fuel_set-Reihenfolge:
        - gas_h2ready in H2-Pfaden (h2_programm_ambition="voll"): H2-first
        - sonst: heutige fuel_set-Reihenfolge

        ``system_state`` steuert Brennstoff-Cap-Modus:

        - NORMAL: dauer_max für alle Brennstoffe.
        - SCARCITY: boost_max nur für ``policy.boost_policy``-Fuels, sonst dauer.
        - DUNKELFLAUTE: boost_max für alle Brennstoffe.

        Phaseout-Fade-Glättung (F3): in nicht-NORMAL-States linear
        1,0 → 0,3 über 10-Jahre-Phaseout-Fenster, dann Plateau 0,3.
        Greift nur, wenn ``fuel_id in policy.boost_policy`` (regulatorische
        Notfall-Genehmigung).

        ``fuel_remaining_th``: optionaler Override für die initial verfüg-
        baren Brennstoff-Caps. Wenn der Aufrufer schon weiß, was nach
        vorherigen Dispatch-Schritten noch übrig ist (z.B.
        ``_dispatch_and_balance`` Phase 3 nach Phase 1+2-Verbrauch), wird
        dieses Dict direkt verwendet — `fuel_cap_multipliers` und
        `h2_realization_rate` gelten als bereits eingerechnet. Default
        ``None``: Methode baut die Caps selbst aus globalen Inventaren.
        """
        from ..system_state import SystemState, fuel_cap_mode, is_emergency_or_stress

        if system_state is None:
            system_state = SystemState.NORMAL

        fuel_order = self._fuel_order_path_specific(path_id, policy)

        gesamt_strom = 0.0
        for fuel_id in fuel_order:
            if gesamt_strom >= max_tech_twh - 1e-9:
                break
            fc = policy.fuel_constraints.get(fuel_id, "")
            if fc in ("stop", "forbidden"):
                continue

            from ..system_state import SystemState

            in_emergency_or_stress = is_emergency_or_stress(
                system_state
            ) and policy.boost_policy.get(fuel_id, False)
            # Notfall-Aufweichung ist asymmetrisch nach Stress-Typ:
            # DUNKELFLAUTE (Wetter-Stress) → 0,3 (physikalisch begrenzt
            # durch Pipeline-Druck/LNG-Lieferketten-Stress).
            # SCARCITY (wirtschaftlicher Versorgungs-Notfall, NORMAL
            # Phase-2-Trigger) → 0,5: politische Realität liegt zwischen
            # voller Klimaambition (Erdgas aus) und voller Aufweichung
            # (Erdgas ganz zurück). Bei H2-Hochlauf-Realgrad < 1 wird
            # Erdgas teilweise genutzt; LCOE-Anstieg und CO₂-Anstieg
            # bleiben beide sichtbar.
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

            if fuel_remaining_th is not None:
                # Caller hat das verbleibende Cap (nach vorherigen Phasen)
                # bereits inklusive aller Modifier (fuel_cap_multipliers,
                # h2_realization_rate) berechnet. Override 1:1 verwenden.
                available_th = fuel_remaining_th.get(fuel_id, 0.0)
            else:
                fuel = fuel_inventory[fuel_id]
                mode = fuel_cap_mode(fuel_id, policy, system_state)
                available_th = (
                    fuel.boost_max_twh_per_year(year, camp)
                    if mode == "boost"
                    else fuel.duration_max_twh_per_year(year, camp)
                )
                # Pfad-spezifischer Brennstoff-Infrastruktur-Multiplikator
                # (z.B. BESTAND skaliert LNG-Cap × 2 analog zum LNG-
                # Beschleunigungsausbau 2022/2023). Default 1,0 = keine
                # Pfad-Modulation.
                available_th *= policy.fuel_cap_multipliers.get(fuel_id, 1.0)
                # h2_realisierung_grad wirkt multiplikativ auf
                # H2-Brennstoff-Verfügbarkeit (Politik-Hebel symmetrisch zu
                # nep_realisierung_grad/kkw_realisierung_grad).
                if fuel_id in ("h2_inland", "h2_import"):
                    available_th *= h2_realization_rate
            strom_max = available_th * self.efficiency_el * fade_factor
            gesamt_strom += strom_max

        return gesamt_strom

    def _fuel_order_path_specific(self, path_id: str, policy: PathPolicyEntry) -> tuple[str, ...]:
        """Brennstoff-Reihenfolge pfad-spezifisch für gas_h2ready.

        Zentrale Quelle für sowohl die Mengen-Bilanz-Dispatch-Order als
        auch die Chart-Stack-Reihenfolge (smart-model, dumb-display).

        H2-Pfade (``h2_program_ambition="voll"``, EE-H2/KKW-H2):
            H2 zuerst dispatched, Erdgas als Saison-Auffüllung — Klima-
            Ambition als Pfad-Definition.

        GAS-Pfade (``h2_program_ambition="gedämpft"``, EE-GAS/KKW-GAS/
        WEITER-SO):
            Erdgas zuerst, H2 als Fallback. Mit ``h2_realization_rate=0``
            im GAS-Pfad ist H2 effektiv nicht verfügbar — gas_h2ready
            läuft nur mit Erdgas/LNG.
        """
        if self.tech_id != "gas_h2ready":
            return self.fuel_set
        ambition = (
            policy.default_policy.h2_program_ambition if policy.default_policy else "gedämpft"
        )
        if ambition == "voll":
            return ("h2_inland", "h2_import", "erdgas_inland", "erdgas_import", "lng")
        return ("erdgas_inland", "erdgas_import", "lng", "h2_inland", "h2_import")


def gas_h2ready_sub_layer_order(path_id: str) -> tuple[str, str]:
    """Stack-Reihenfolge der zwei gas_h2ready-Sub-Schichten pro Pfad.

    Liest die Pfad-Logik aus ``PATH_POLICY[path_id].default_policy.h2_program_ambition``
    und liefert die Chart-Stack-Reihenfolge als Tupel
    (untere Schicht, obere Schicht).

    H2-Pfade: H2 unten, Erdgas oben — H2 ist die dominante Brennstoff-
    Schicht, Erdgas die saisonale Auffüllung.

    GAS-Pfade: Erdgas unten, H2 oben — Erdgas ist Hauptbetrieb, H2
    konzeptuelle Optionalitäts-Versicherung.
    """
    from enesys.core.inventories.path_policy import PATH_POLICY

    policy = PATH_POLICY[path_id]
    ambition = policy.default_policy.h2_program_ambition if policy.default_policy else "gedämpft"
    if ambition == "voll":
        return ("gas_h2ready_h2", "gas_h2ready_erdgas")
    return ("gas_h2ready_erdgas", "gas_h2ready_h2")


TECH_INVENTORY: dict[str, TechEntry] = {}
"""Inventar. Lager-Argument folgt der heutigen
Konvention aus `lager_ranges.LAGER_RANGES`: ``neutral_default``,
``ee_optimistic``, ``atom_optimistic``, ``bestand_optimistic``.

Pfad-Argument ist eine der sechs Pfad-Kennungen: ``weiterso``, ``bestand``,
``ee_gas``, ``ee_h2``, ``kkw_gas``, ``kkw_h2``.
"""


# ---------------------------------------------------------------------------
# Befüllung pro Tech
# ---------------------------------------------------------------------------
#
# Werte und Source-Tags rückverfolgt aus `path_model.py`, `wacc.py`,
# `lager_ranges.LAGER_RANGES` und `docs/SOURCES.md`.
#
# Verankerungs-Karte:
# (1) PV/Wind-Zubau-Pfad-Modifikatoren ← BNetzA-MaStR-Zubau-Historik
# (2) Tech-Zubau-Lager-Multiplikatoren ← LAGER_RANGES.nep_realisierung_grad
# (3) KKW-Lager-Startjahre ← LAGER_RANGES.kkw_realisierung_grad via
#     Bauzeit-Formel T_build = T_plan / grad
# (4) SMR-CAPEX ← BWRX-300/RR-SMR/NuScale-CFPP-Vergleichsanker
# (5) Bio-CAPEX/OPEX ← ISE-2024 + DBFZ-2023 Detail-Tabellen
# (6) Brennstoff-dauer_max-Trajektorien ← BMWK-T45 + BVEG + BNetzA-Kernnetz
# (7) Demand-Lager-Multiplikatoren ← BMWK-T45-Komponenten-Zerlegung
#     (WP 150 + E-Mob 120 + Industrie 80 = 350 TWh @ 2045)
#
# Strukturelle Datenlücken (Auslauf-Kurven mit Altersverteilung,
# Kohle/Gas-Bestand-Detail, Batterie-CAPEX-Lernkurve) sind unten an den
# jeweiligen Stellen markiert.


# === PV ====================================================================
#
# Quellen-Bündel:
#   - Bestand: BNetzA-MaStR Q4 2024 (~95 GW; Verwendung als 2026-Basis aus
#     path_model.py übernommen; MaStR Q4 2025 noch nicht eingearbeitet).
#   - CAPEX / OPEX / VLH / Lifetime: Fraunhofer ISE Stromgestehungskosten
#     Juli 2024.
#   - WACC: IRENA-2024-WACC (DE-Premium-Aufschlag), Provenance in
#     `core/wacc.py`.
#   - Lernkurven-Plateaus pro Lager: ISE-Mittel 510 €/kW 2045,
#     BNEF-NEO-2024-NZS-Median 350 €/kW 2050, Aggressiv-Tail 200 €/kW 2050.
#   - Zubau-Default: BNetzA-MaStR-Trend 18 GW/a.
#     Pfad-Modifikatoren WEITER-SO 5 GW/a und BESTAND 2 GW/a sind in
#     an die BNetzA-MaStR-Zubau-Historik rückgekoppelt:
#     5 GW/a = Pre-EEG-2023-Mittel 2017-2022 (1,8/3,0/4,0/4,9/5,3/7,2,
#     Mittel 4,4 mit jüngerem Bias auf 5), 2 GW/a = EEG-2014-Regime-Mittel
#     2014-2017 (1,9/1,5/1,5/1,8, Mittel 1,7).


def _pv_auslauf_kurve(year: int) -> float:
    """PV-Bestands-Auslauf. Konservative Annahme: Repowering hält den
    Bestand bis 2055 stabil.

    Datenlücke: keine Primärquelle für PV-Altersverteilung (BNetzA-MaStR
    Q4 2024 nicht importiert). PV-Boom 2010-2012 läuft theoretisch ab
    2040 aus; Repowering-Praxis in DE kompensiert — daher konservativ
    konstant 95 GW.
    """
    del year  # zeitkonstant (Altersverteilung nicht modelliert)
    return 95.0


def _pv_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """PV-Zubau-Obergrenze pro Jahr nach Pfad-Politik und Lager.

    Pfad-Modifikatoren folgen `default_politik.eeg_auktions_volumen_profil`
    in der jeweiligen `PATH_POLICY[path]`.

    Werte:
        Profil »voll« (EE-/KKW-Pfade): 18 GW/a
          [SRC: BNETZA-MASTR-2024 — installierte PV-Leistung 2024 plus EEG-2023-Ausschreibungs-Soll-Pfad zu 215 GW bis 2030]
        Profil »gedämpft« (WEITER-SO): 5 GW/a
          [SRC: BNETZA-MASTR-2017-2022 — Pre-EEG-2023-Real-Zubau Mittel 4,4 GW/a (1,8/3,0/4,0/4,9/5,3/7,2), Auf-Rundung auf 5 mit jüngerem Bias 2021-2022]
        Profil »gestoppt« (BESTAND): 2 GW/a
          [SRC: BNETZA-MASTR-2014-2017 — EEG-2014-Deckel-Regime Mittel 1,7 GW/a (1,9/1,5/1,5/1,8); BESTAND als aktiver Stop entspricht Wiederherstellung 2014er-Niveau]

    Lager-Multiplikator: reine Welt-Belief-Modulation um den Anker
    1,00 (neutral). Pfad-Politik trägt `base_zubau_pro_profil`
    (voll/gedämpft/gestoppt) und reicht den Politik-Wunsch über
    `default_politik` als param_override durch; lager_mult moduliert
    allein die welt-belief-spezifische Realisierungs-Reibung, damit
    sich Politik-Wunsch und Welt-Belief nicht doppelt multiplizieren.

    Begründungen pro Lager:
        neutral_default     1,00  Anker, methodische Mitte
        ee_optimistic       1,10  EE-Welt: höhere Akzeptanz, weniger
                                  Bürokratie-Reibung, schnellere
                                  Genehmigungspraxis
        atom_optimistic     0,90  Atom-Welt: EE-skeptische Genehmigungs-
                                  praxis, Trassen-Konflikt
        bestand_optimistic  0,80  Bestand-Welt: aktive Drossel-Politik
                                  gegen EE-Hochlauf
        weiterso_optimistic 0,95  passive Trägheit zwischen neutral und
                                  atom

    [SRC: Reue-Drei-Schichten-Architektur (Politik / Korridor / Realität).]
    """
    base_zubau_pro_profil = {
        "voll": 18.0,
        "gedämpft": 5.0,
        "gestoppt": 2.0,
    }
    pfad_zu_profil = {
        "ee_gas": "voll",
        "ee_h2": "voll",
        "kkw_gas": "voll",
        "kkw_h2": "voll",
        "weiterso": "gedämpft",
        "bestand": "gestoppt",
    }
    lager_mult = {
        "neutral_default": 1.00,
        "ee_optimistic": 1.10,
        "atom_optimistic": 0.90,
        "bestand_optimistic": 0.80,
        "weiterso_optimistic": 0.95,
    }
    profil = pfad_zu_profil.get(path, "voll")
    base = base_zubau_pro_profil[profil]
    return base * lager_mult.get(camp, 1.0)


# CAPEX-Plateau-Tabelle pro Lager. Werte aus PV-Lernkurven-Lager in
# path_model.py — vier Stützpunkte für Plateau-Jahr und
# Plateau-CAPEX.
#
# Default-Lager (neutral_default) = PV_LERNKURVE_KONSERVATIV: keine
# Lernkurve, ISE-Heutige-Werte gelten bis 2055. Konservative Annahme
# (PV-Plateau ohne weitere Kostendegression).
_PV_CAPEX_LAGER: dict[str, tuple[float, int]] = {
    "neutral_default": (510.0, 2045),
    "ee_optimistic": (350.0, 2050),
    "atom_optimistic": (700.0, 2045),
    "bestand_optimistic": (700.0, 2045),
}


def _pv_capex_eur_kw(year: int, camp: str) -> float:
    """PV-CAPEX in €/kW.

    Startwert 2026: 700 €/kW
        [SRC: ISE-2024 Stromgestehungskosten Juli 2024 Tab. 1, Bandbreite 530-1.600]

    Lager-Plateaus:
        neutral_default → 510 €/kW @ 2045 (ISE-2024-Mittel-Lernkurve)
            [SRC: PV_LERNKURVE_ISE_MITTEL_2045, ISE-2024 Stromgestehungs- kosten Juli 2024. Plateau-Wert 510 entspricht der Mittel- Lernkurve.]
        ee_optimistic   → 350 €/kW @ 2050 (BNEF-NEO-2024 NZS-Median)
            [SRC: PV_LERNKURVE_BNEF_NZS_MEDIAN]
        atom_optimistic → 700 €/kW Plateau (KKW-Lager glaubt nicht an
            EE-Lernkurven)
            [ASSUMPTION: Atom-Lager-EE-Skepsis, spiegelt LAGER_RANGES
            pv_lcoe.atom_optimistic=8.0 ct]
        bestand_optimistic → 700 €/kW Plateau
            [ASSUMPTION: Bestand-Lager-EE-Skepsis, BDI-2024-Position]

    Lineare Interpolation zwischen 2026-Wert und Plateau-Jahr;
    Plateau danach konstant.
    """
    start_capex = 700.0
    start_year = 2026
    plateau_capex, plateau_year = _PV_CAPEX_LAGER.get(camp, _PV_CAPEX_LAGER["neutral_default"])
    if year <= start_year:
        return start_capex
    if year >= plateau_year:
        return plateau_capex
    progress = (year - start_year) / (plateau_year - start_year)
    return start_capex + progress * (plateau_capex - start_capex)


# WACC-Bandbreite pro Lager. Übernommen aus
# `core/wacc.py` (default 0,050; lower 0,038; upper 0,065).
_PV_WACC_LAGER: dict[str, float] = {
    "neutral_default": 0.045,
    "ee_optimistic": 0.038,
    "atom_optimistic": 0.065,
    "bestand_optimistic": 0.065,
}


def _pv_wacc_pct(year: int, camp: str) -> float:
    """PV-WACC nach Lager. Zeit-konstant (keine WACC-Trajektorie heute).

    [SRC: CALIBRATED:IRENA-2024-WACC; core/wacc.py:WACC_TABLE['pv'].
    Rationale: EU-Mittel 3,8 % + DE-Premium-Aufschlag → neutral_default 4,5 %.]
    """
    del year  # heute zeitkonstant
    return _PV_WACC_LAGER.get(camp, _PV_WACC_LAGER["neutral_default"])


# === Wind-Modifikatoren (gemeinsam für Onshore und Offshore) ==============
#
# Pfad-Modifikatoren auf Zubau folgen demselben EEG-Auktions-Profil
# (default_politik.eeg_auktions_volumen_profil) wie PV. WEITER-SO- und
# BESTAND-Werte an BNetzA-MaStR-Zubau-Historik
# rückgekoppelt (siehe Funktions-Docstrings für Onshore und Offshore).
#
# Lager-Multiplikator: reine Welt-Belief-Modulation um den Anker 1,00
# (neutral). Pfad-Politik trägt die Profil-Skala (voll/gedämpft/gestoppt)
# in default_politik; lager_mult moduliert allein die welt-belief-
# spezifische Realisierungs-Reibung, damit sich Politik-Wunsch und
# Welt-Belief nicht doppelt multiplizieren. Wird auch von Bio + Battery
# + Importe-Bezugs-Funktionen konsumiert (siehe Konsumenten unten).
# Werte und Begründungen identisch zu PV-`_pv_max_zubau_gw_per_year`
# (siehe dort).
#
# [SRC: Reue-Drei-Schichten-Architektur (Politik / Korridor / Realität).]

_WIND_PFAD_ZU_PROFIL: dict[str, str] = {
    "ee_gas": "voll",
    "ee_h2": "voll",
    "kkw_gas": "voll",
    "kkw_h2": "voll",
    "weiterso": "gedämpft",
    "bestand": "gestoppt",
}

_WIND_LAGER_MULT: dict[str, float] = {
    "neutral_default": 1.00,
    "ee_optimistic": 1.10,
    "atom_optimistic": 0.90,
    "bestand_optimistic": 0.80,
    "weiterso_optimistic": 0.95,
}


# === Wind-Onshore ==========================================================
#
# Quellen-Bündel:
#   - Bestand: BNetzA-MaStR Q4 2024 (~62 GW).
#   - CAPEX 1.400 €/kW: Fraunhofer ISE Stromgestehungskosten Juli 2024,
#     Bandbreite 1.300-1.900.
#   - OPEX 35 €/kW/a, VLH 2.200 h, Lifetime 25 a: ISE-2024
#     (path_model.py).
#   - WACC 6,0 % default, Bandbreite 4,5-7,5 %: CALIBRATED:IRENA-2024
#     (core/wacc.py:WACC_TABLE['wind']).
#   - Zubau 8 GW/a: EEG-2023 Ausschreibungsvolumen.
#
# Keine Lernkurve: ISE-2024 zeigt für Wind keine signifikanten CAPEX-
# Reduktionen bis 2045 (vgl. path_model.py). CAPEX zeitkonstant
# pro Lager.


def _wind_onshore_auslauf_kurve(_year: int) -> float:
    """Wind-Onshore-Bestands-Auslauf. Konservative Annahme: Repowering
    hält den Bestand stabil.

    Datenlücke: BNetzA-MaStR-Altersverteilung nicht eingearbeitet
    (Onshore-Boom 2000-2010, Lifetime 25 a → Auslauf ab 2025 schon im
    Gange; Repowering-Trend in DE kompensiert).
    """
    return 62.0


def _wind_onshore_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """Wind-Onshore-Zubau-Obergrenze pro Jahr nach Pfad-Politik
    und Lager.

    Werte:
        Profil »voll« (EE-/KKW-Pfade): 8 GW/a
          [SRC: EEG-2023-Ausschreibungs-Pfad zu 115 GW bis 2030 (Soll-Volumen ~10 GW/a brutto, realistischer Erwartungswert 8 GW/a unter Berücksichtigung Auktionen-Unterzeichnung 2019-2022)]
        Profil »gedämpft« (WEITER-SO): 3 GW/a
          [SRC: BNETZA-MASTR-2020-2023 Brutto-Zubau-Mittel 2,3 GW/a (1,4/1,9/2,4/3,6), gerundet auf 3 mit jüngerem 2023-Bias]
        Profil »gestoppt« (BESTAND): 1 GW/a
          [SRC: BNETZA-MASTR-2019 — Tiefpunkt 1,1 GW Brutto-Zubau nach EEG-2017-Auktions-Reform mit chronischer Unterzeichnung; BESTAND als aktiver Stop entspricht Wiederherstellung 2019er-Tiefpunkts]

    Lager-Multiplikator: siehe _WIND_LAGER_MULT (an LAGER_RANGES.
    nep_realisierung_grad rückgekoppelt: 1,00 / 1,30 / 0,77 / 0,69).
    """
    base_zubau_pro_profil = {
        "voll": 8.0,
        "gedämpft": 3.0,
        "gestoppt": 1.0,
    }
    profil = _WIND_PFAD_ZU_PROFIL.get(path, "voll")
    base = base_zubau_pro_profil[profil]
    return base * _WIND_LAGER_MULT.get(camp, 1.0)


def _wind_onshore_capex_eur_kw(_year: int, _camp: str) -> float:
    """Wind-Onshore-CAPEX in €/kW. Keine Lernkurve (ISE-2024).

    [SRC: ISE-2024 Stromgestehungskosten Juli 2024, Bandbreite 1.300-1.900. Keine Lernkurve modelliert, weil ISE-2024 keine signifikanten CAPEX-Reduktionen bis 2045 zeigt.]
    """
    return 1400.0


_WIND_WACC_LAGER: dict[str, float] = {
    "neutral_default": 0.060,
    "ee_optimistic": 0.045,
    "atom_optimistic": 0.075,
    "bestand_optimistic": 0.075,
}


def _wind_wacc_pct(_year: int, camp: str) -> float:
    """Wind-WACC nach Lager (Onshore und Offshore gleicher Wert).

    [SRC: CALIBRATED:IRENA-2024; core/wacc.py:WACC_TABLE['wind'].
    Rationale: WEU 3,3 % + DE-NIMBY/Genehmigungs-Aufschlag → 6,0 %
    default, Bandbreite 4,5-7,5 %.]
    """
    return _WIND_WACC_LAGER.get(camp, _WIND_WACC_LAGER["neutral_default"])


# === Wind-Offshore =========================================================
#
# Quellen-Bündel:
#   - Bestand: BNetzA-MaStR Q4 2024 (~9 GW).
#   - CAPEX 3.000 €/kW: ISE-2024.
#   - OPEX 90 €/kW/a (höher wegen See), VLH 4.200 h, Lifetime 25 a:
#     ISE-2024 (path_model.py).
#   - WACC: gleiches Bündel wie Onshore (gemeinsamer wacc_wind-Eintrag).
#   - Zubau 4 GW/a: EEG-2023 / WindSeeG.


def _wind_offshore_auslauf_kurve(_year: int) -> float:
    """Wind-Offshore-Bestands-Auslauf. Offshore-Flotte ist jünger (ab
    ~2010 zugebaut), erste Auslauf-Welle erst ab ~2035. Konservativ
    konstant (Altersverteilung nicht eingearbeitet).
    """
    return 9.0


def _wind_offshore_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """Wind-Offshore-Zubau-Obergrenze pro Jahr.

    Werte:
        Profil »voll« (EE-/KKW-Pfade): 4 GW/a
          [SRC: WindSeeG-2023 Offshore-Ausbau-Pfad zu 30 GW bis 2030 und 40 GW bis 2035 (~3 GW/a bis 2030, ~4 GW/a 2030-2035)]
        Profil »gedämpft« (WEITER-SO): 1 GW/a
          [SRC: BNETZA-MASTR-2017-2024 Brutto-Zubau-Mittel ~0,6 GW/a (1,2/1,0/0,9/0,2/0,0/0,3/0,3/0,8), Auf-Rundung auf 1 mit Vor-2020-Bias (~1 GW/a)]
        Profil »gestoppt« (BESTAND): 0,5 GW/a
          [SRC: BNETZA-MASTR-2020-2023 Tiefpunkt-Mittel ~0,2 GW/a (0,2/0,0/0,3/0,3) nach Ausschreibungs-Pause; Auf-Rundung auf 0,5 als konservativer BESTAND-Stop]

    Lager-Multiplikator: siehe _WIND_LAGER_MULT (gemeinsam mit
    Onshore, an LAGER_RANGES.nep_realisierung_grad rückgekoppelt).
    """
    base_zubau_pro_profil = {
        "voll": 4.0,
        "gedämpft": 1.0,
        "gestoppt": 0.5,
    }
    profil = _WIND_PFAD_ZU_PROFIL.get(path, "voll")
    base = base_zubau_pro_profil[profil]
    return base * _WIND_LAGER_MULT.get(camp, 1.0)


def _wind_offshore_capex_eur_kw(_year: int, _camp: str) -> float:
    """Wind-Offshore-CAPEX in €/kW. Keine Lernkurve.

    [SRC: ISE-2024 Stromgestehungskosten Juli 2024. Keine Lernkurve modelliert (gleicher Grund wie Onshore).]
    """
    return 3000.0


# === Biomasse =============================================================
#
# Quellen-Bündel:
#   - Bestand: AGEB-2024 Stromerzeugung Bio ≈ 50 TWh / 5.000 VLH → ~10 GW.
#   - Mix-Anteil heute: 4-7 % (path_model.py — Bio-Mix-Konstanten).
#   - LCOE heute pauschal 14,0 ct/kWh [SRC: ISE-2024].
#   - CAPEX/OPEX-Aufschlüsselung an ISE-2024-Detail-
#     Tabellen rückgekoppelt: Biogas-BHKW-Mittelgröße CAPEX 2.300-3.500
#     €/kW, OPEX 100-150 €/kW/a, Brennstoffkosten 50-70 €/MWh_el.
#     Modell-Werte 2.500 €/kW (unteres Drittel CAPEX-Range, Biogas-Klein-
#     anlagen-fokussiert) + 80 €/kW/a (konservativ-niedrig wegen
#     Standardisierung Biogas-BHKW) sind dadurch nachvollziehbar
#     dokumentiert; LCOE-Konsistenz über Brennstoffkosten in
#     FUEL_INVENTORY["bio_strom"].
#   - VLH: Bio-KWK / Bio-Strom-Mittel ~4.500 h (UBA-Branchen-Statistik
#     2024 Tabelle 23).
#   - Boost-VLH: ~7.500 h (Bio kann unter Stress nahezu vollständig
#     gefahren werden — wichtig für Stresstest-Dispatch).


def _bio_auslauf_kurve(_year: int) -> float:
    """Bio-Bestands-Auslauf. EEG-Förderung der 2010er-Anlagen läuft ab
    2025-2030 aus; Anschluss-Förderung in EEG-2023 vorgesehen. Konservativ
    konstant 10 GW (Altersverteilung nicht modelliert).
    """
    return 10.0


def _bio_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """Bio-Zubau-Obergrenze pro Jahr. In Deutschland stark begrenzt durch
    Biomasse-Potenzial-Obergrenze (Anbau-Konkurrenz Lebensmittel,
    Wald-Restbiomasse).

    Werte:
        Profil »voll«: 0,3 GW/a
          [SRC: UBA-2022 »Biomassepotenziale in Deutschland«, Zusatz- potenzial 2030 ~6 GW über 20 a Aufbau-Korridor = 0,3 GW/a; DBFZ-2023 »Stromerzeugung aus Biomasse«]
        Profil »gedämpft«: 0,1 GW/a
          [SRC: BNETZA-MASTR-2018-2022 Bio-Real-Zubau ~0,1 GW/a Brutto ohne EEG-2023-Anschluss-Programm — WEITER-SO-Pfad]
        Profil »gestoppt«: 0,0 GW/a
          [SRC: ohne EEG-Anschluss-Förderung läuft 2010er-Förder-Boom aus, Netto-Zubau gleich Null — BESTAND-Pfad]
    """
    base_zubau_pro_profil = {
        "voll": 0.3,
        "gedämpft": 0.1,
        "gestoppt": 0.0,
    }
    profil = _WIND_PFAD_ZU_PROFIL.get(path, "voll")
    base = base_zubau_pro_profil[profil]
    return base * _WIND_LAGER_MULT.get(camp, 1.0)


def _bio_capex_eur_kw(_year: int, _camp: str) -> float:
    """Bio-CAPEX in €/kW. Keine Lernkurve (ausgereifte Technologie).

    [SRC: ISE-2024 Stromgestehungskosten Juli 2024, Bio-KWK-Bandbreite 2.300-3.500 €/kW; DBFZ-2023 Stromerzeugung aus Biomasse Tabelle 4. Modell-Wert 2.500 €/kW liegt im unteren Drittel der Bandbreite (Biogas-Klein-BHKW < 1 MWel-Klasse, geringere spezifische CAPEX); konservativ-niedrig gegenüber Holz-Heizkraftwerk ~4.000 €/kW.]
    """
    return 2500.0


_BIO_WACC_LAGER: dict[str, float] = {
    "neutral_default": 0.070,
    "ee_optimistic": 0.060,
    "atom_optimistic": 0.080,
    "bestand_optimistic": 0.075,
}


def _bio_wacc_pct(_year: int, camp: str) -> float:
    """Bio-WACC nach Lager.

    [SRC: IRENA-2024 Renewable Cost Database Bio-Range 5,5-8,0 %, plus ISE-2024 WACC-Bandbreite (Tabelle Anhang B). Modell-Wert 7,0 % default liegt im oberen Bereich der Bandbreite wegen Brennstoff- Logistik-Komplexität (Substrat-Anbau-Risiko + Genehmigungs-Streit). Lager-Spreizung 6,0-8,0 % spiegelt LAGER-Sicht: ee_optimistic glaubt an stabile Bio-Roh-Stoff-Märkte (6,0 %), atom_optimistic sieht Bio als hochrisikobehaftet (8,0 %).]
    """
    return _BIO_WACC_LAGER.get(camp, _BIO_WACC_LAGER["neutral_default"])


TECH_INVENTORY["bio"] = TechEntry(
    tech_id="bio",
    existing_gw_2026=10.0,
    decay_curve=_bio_auslauf_kurve,
    max_additions_gw_per_year=_bio_max_zubau_gw_per_year,
    vlh_normal=4500.0,
    vlh_max_boost=7500.0,
    lifetime_years=25,
    capex_eur_kw=_bio_capex_eur_kw,
    opex_fix_eur_kw_a=80.0,
    opex_var_eur_mwh=0.0,
    wacc_pct=_bio_wacc_pct,
    fuel_set=("bio_strom",),
    efficiency_el=0.30,  # [SRC: BNetzA-Kraftwerksliste 2024 Bio-KWK-Mix; DBFZ-2023 Strom-Wirkungsgrad Biogas/Holz-KWK ~28-35 %, Default 30 % als Mittelwert]
    source=(
        "AGEB-2024 Stromerzeugung Bio ≈ 50 TWh / 5.000 VLH → 10 GW Bestand. "
        "Mix-Anteil 4-7 % aus core.path_model Bio-Mix-Konstanten. "
        "ISE-2024 Stromgestehungskosten Juli 2024 (LCOE 14,0 ct/kWh als "
        "End-LCOE, CAPEX-Bandbreite 2.300-3.500 €/kW, OPEX 100-150 €/kW/a). "
        "DBFZ-2023 Stromerzeugung aus Biomasse für Detail-Tabellen. "
        "UBA-2022 Biomassepotenziale für Zubau-Obergrenze. "
        "IRENA-2024 Renewable Cost Database für WACC-Bandbreite."
    ),
    derivation=(
        "Modell-Werte CAPEX 2.500 €/kW + OPEX 80 €/kW/a liegen am unteren "
        "Ende der ISE-2024-Bandbreite, weil Biogas-Klein-BHKW-fokussiert "
        "statt Holz-Heizkraftwerk; LCOE-Konsistenz "
        "gegen ISE-End-LCOE 14 ct/kWh via Brennstoffkosten in "
        'FUEL_INVENTORY["bio_strom"]. '
        "Zubau-Obergrenzen (0,3 / 0,1 / 0,0 GW/a) aus UBA-2022 + BNetzA-"
        "MaStR-Historik 2018-2022 abgeleitet. "
        "vlh_max_boost=7.500 h: Bio kann unter Stress nahezu durchgefahren "
        "werden (Brennstoff-Logistik-Konstante, keine Wetter-Abhängigkeit)."
    ),
)


# === Wasser ===============================================================
#
# Quellen-Bündel:
#   - Bestand 2026: AGEB-2024 Wasserkraft ≈ 17 TWh / 3.500 VLH ≈ 5 GW.
#   - LCOE Bestand 6,0 ct/kWh [SRC: BMWi-Wasserkraft].
#   - Wasserkraft-Standorte in DE praktisch ausgereizt (UBA, BMWi-Studien):
#     kaum Neubau-Potenzial.
#   - Sehr langlebig (60 a typische Betriebsdauer).


def _wasser_auslauf_kurve(_year: int) -> float:
    """Wasser-Bestands-Auslauf. Sehr langlebige Tech (60 a). Bestand
    quasi konstant bis 2055.
    """
    return 5.0


def _wasser_max_zubau_gw_per_year(_year: int, _path: str, _camp: str) -> float:
    """Wasser-Zubau-Obergrenze. In Deutschland praktisch ausgereizt.

    [SRC: BMWi-Wasserkraft-Studie + UBA-Wasserkraft-Potenzial 2018. Marginales Restpotenzial (~0,3-0,5 GW gesamt bis 2050) wird auf 0,02 GW/a verteilt. Pfad-Modifikatoren minimal.]
    """
    return 0.02


def _wasser_capex_eur_kw(_year: int, _camp: str) -> float:
    """Wasser-CAPEX. Für Bestand irrelevant (abgeschrieben), für Neubau
    standortabhängig sehr hoch (3.000-8.000 €/kW). Plausi-Mittel 4.000.

    [ASSUMPTION: BMWi-Wasserkraft-Branche-Standard, BMWi-Studie nicht
    direkt zitiert.]
    """
    return 4000.0


_WASSER_WACC_LAGER: dict[str, float] = {
    "neutral_default": 0.040,
    "ee_optimistic": 0.030,
    "atom_optimistic": 0.050,
    "bestand_optimistic": 0.050,
}


def _wasser_wacc_pct(_year: int, camp: str) -> float:
    """Wasser-WACC nach Lager. Niedrig, weil Bestand stabil und kalkulierbar.

    [ASSUMPTION: 4,0 % default — vergleichbar mit KKW-Bestand, weil
    Wasserkraft etabliert und Cashflow-stabil. Offen ist
    IRENA-Wasserkraft-WACC.]
    """
    return _WASSER_WACC_LAGER.get(camp, _WASSER_WACC_LAGER["neutral_default"])


TECH_INVENTORY["wasser"] = TechEntry(
    tech_id="wasser",
    existing_gw_2026=5.0,
    decay_curve=_wasser_auslauf_kurve,
    max_additions_gw_per_year=_wasser_max_zubau_gw_per_year,
    vlh_normal=3500.0,
    vlh_max_boost=4500.0,
    lifetime_years=60,
    capex_eur_kw=_wasser_capex_eur_kw,
    opex_fix_eur_kw_a=70.0,
    opex_var_eur_mwh=0.0,
    wacc_pct=_wasser_wacc_pct,
    fuel_set=(),
    source=(
        "AGEB-2024 (17 TWh / 3.500 VLH → 5 GW Bestand). "
        "BMWi-Wasserkraft (LCOE 6,0 ct/kWh). "
        "Lebensdauer 60 a (Branche-Standard, Wasserkraft-Anlagen "
        "regelmäßig nach 60-80 Jahren grunderneuert)."
    ),
    derivation=(
        "Zubau 0,02 GW/a ist Plausi-Setzung aus UBA-Wasserkraft-Potenzial-"
        "Studie 2018 (Restpotenzial DE ~0,3-0,5 GW). "
        "CAPEX 4.000 €/kW Plausi-Mittel (BMWi-"
        "Wasserkraft-Studie direkt zitieren. "
        "OPEX 70 €/kW/a Branchen-Standard. "
        "WACC 4,0 % default — wie KKW-Bestand (etablierte, cashflow-stabile "
        "Tech). "
        "vlh_max_boost=4.500 h: Pumpspeicher-Anteil im Bestand begrenzt "
        "boostbar, Laufwasser nicht. Plausi-Mittel."
    ),
)


# === KKW (Bestand, nach Ausstieg 2023) ====================================
#
# Stand 2026: Bestand = 0 GW (letzte drei KKW April 2023 abgeschaltet).
# Reaktivierungs-Fenster für die drei letzten KKW seit Oktober 2023 zu.
# KKW-Bestand bleibt als Platzhalter für mögliche Sensi-Varianten
# »Reaktivierung als Lager«.


def _kkw_bestand_auslauf_kurve(_year: int) -> float:
    """KKW-Bestand 0 GW seit April 2023."""
    return 0.0


def _kkw_bestand_max_zubau_gw_per_year(_year: int, _path: str, _camp: str) -> float:
    """KKW-Bestand kein Zubau möglich (Ausstieg, Reaktivierungs-Fenster
    geschlossen)."""
    return 0.0


def _kkw_bestand_capex_eur_kw(_year: int, _camp: str) -> float:
    """KKW-Bestand-CAPEX = 0 (Anlagen abgeschrieben, Bestand = 0)."""
    return 0.0


def _kkw_bestand_wacc_pct(_year: int, _camp: str) -> float:
    """KKW-Bestand-WACC. Platzhalter (Bestand = 0). 4 % wie andere
    abgeschriebene Bestands-Tech."""
    return 0.040


TECH_INVENTORY["kkw_bestand"] = TechEntry(
    tech_id="kkw_bestand",
    existing_gw_2026=0.0,
    decay_curve=_kkw_bestand_auslauf_kurve,
    max_additions_gw_per_year=_kkw_bestand_max_zubau_gw_per_year,
    vlh_normal=7500.0,
    vlh_max_boost=8000.0,
    lifetime_years=60,
    capex_eur_kw=_kkw_bestand_capex_eur_kw,
    opex_fix_eur_kw_a=130.0,
    opex_var_eur_mwh=5.0,
    wacc_pct=_kkw_bestand_wacc_pct,
    fuel_set=("uran",),
    efficiency_el=0.34,  # [SRC: IAEA-PRIS Wirkungsgrad-Daten deutsche LWR (Isar-2, Neckarwestheim-2, Emsland) ~33-34 %; WNA Technical Performance 2024]
    source=(
        "Bestand 0 GW: KKW-Ausstieg April 2023 (BGBl. I S. 2814, 2010 "
        "i.d.F. AtG-Novelle 2011). Reaktivierungs-Fenster seit Oktober "
        "2023 zu (Mehrheit dagegen, Betreiber dagegen). "
        "OPEX 130 €/kW/a, VLH 7.500 h: Historische Werte deutscher KKW-"
        "Bestand (Müller/Isar-2-Aussagen, BNetzA-Monitoring)."
    ),
    derivation=(
        "Eintrag bleibt als Platzhalter für Sensi-Variante "
        "»Reaktivierung als Lager« — heute strukturell 0 GW. "
        "VLH 7.500 h reflektiert KernD-Argumentation (deutsche KKW-"
        "Bestandsflotte historisch). "
        "Wenn Reaktivierungs-Sensi aktiv wird, müssen CAPEX (5-8 Mrd. €/"
        "Reaktor für Wieder-Inbetriebnahme) und Zeitplan (~2-3 a) in "
        "ergänzt werden)."
    ),
)


# === KKW-Neubau EPR ======================================================
#
# Quellen-Bündel:
#   - CAPEX: 14.000 €/kW als Modell-Default (per-Lager-Tabelle weiter
#     unten). HPC-Realität ~18.000; Flamanville ~14.800; Plan-EPR
#     ~9.000; OL3 ~6.900. Mitte aus Hinkley-Realität und Plan/Sizewell-
#     FOAK; KKW-Pfade tragen einen EU-EPR-Erfahrungs-Anker, nicht den
#     optimistischen Plan-Wert.
#   - OPEX 130 €/kW/a, VLH 6.500 h, Lifetime 60 a: ISE-2024 + EDF-Daten
#     (path_model.py).
#   - WACC 9,0 % default, Bandbreite 7-10: CALIBRATED:HPC-Helm-Oxford+
#     Sizewell-RAB (core/wacc.py:WACC_TABLE['nuclear']).
#   - Zubau-Trajektorie lager-spezifisch (Plan-Realisierungs-
#     grad 1,0 vs. Hinkley-Realität 0,2-0,4).


def _kkw_neubau_epr_auslauf_kurve(_year: int) -> float:
    """KKW-Neubau EPR: Bestand 2026 = 0, Aufbau durch Zubau ab Lager-
    spezifischem Startjahr. Auslauf erst nach 60 a Lifetime > 2100,
    irrelevant für Modell-Horizont 2055.
    """
    return 0.0


#: Approval-Jahr für FOAK-EPR2-Programm in Deutschland.
#:
#: 2026 (Politik-Beschluss) + 3 Jahre FID-Vorlauf. Konservativer
#: Mittelwert aus der FOAK-Empirie: HPC FID-Sept-2016 → Spatenstich
#: Dez-2018 (2,2 a), Olkiluoto-3 FID-2003 → Spatenstich-2005 (2 a),
#: Flamanville-3 FID-2007 → Spatenstich Dez-2007 (~0 a), Vogtle-3/4
#: Combined-License-2012 → Spatenstich März-2013 (~1 a). Mittel ~2 a;
#: Aufschlag auf 3 a wegen fehlender DE-KKW-Lieferketten und
#: KTA-Update-Bedarf.
#:
#: [SRC: UK NAO HPC-2017; TVO Pressemitteilungen OL-3; Cour-des-Comptes- #: Flamanville; Georgia-Power Vogtle-Reports.]
KKW_EPR_APPROVAL_YEAR: int = 2029

#: Plan-Bauzeit Areva-EPR2-Spec (Spatenstich → IBN).
KKW_EPR_PLAN_YEARS: int = 7

#: Cap auf die sqrt-gestreckte effektive Bauzeit. Bei sehr niedrigem
#: Realgrad (ee_optimistic 0,20) würde T_build = 7/0,2 = 35 a; das
#: Auslegungs-Lebensdauer-Verhältnis macht > 21 a unsinnig — der Pfad
#: würde lieber nie KKW bauen.
KKW_EPR_T_CAP: int = 21

#: KKW-Realisierungsgrad pro Lager. Bestimmt sowohl Bauzeit-Streckung
#: als auch Zubau-Rate (rate = 2 × grad GW/a).
KKW_REALIZATION_BY_CAMP: dict[str, float] = {
    "atom_optimistic": 1.00,
    "neutral_default": 0.40,
    "ee_optimistic": 0.20,
    "bestand_optimistic": 0.40,
    "weiterso_optimistic": 0.40,
}


def _kkw_epr_startjahr(camp: str) -> int:
    """Lager-spezifisches KKW-EPR-Startjahr.

    Formel: ``Approval + min(T_plan / grad, T_cap)``. Damit verschiebt
    sich das Startjahr automatisch, wenn sich Approval-Jahr oder
    Realgrad-Tabelle ändert.
    """
    grad = KKW_REALIZATION_BY_CAMP.get(camp, 0.40)
    t_build = min(KKW_EPR_PLAN_YEARS / max(1e-9, grad), KKW_EPR_T_CAP)
    return KKW_EPR_APPROVAL_YEAR + int(round(t_build))


def _kkw_neubau_epr_max_zubau_gw_per_year(year: int, path: str, camp: str) -> float:
    """KKW-EPR-Zubau nach Pfad-Politik und Lager.

    KKW-Erlaubnis-Profil:
        »kein_neubau« (WEITER-SO, BESTAND, EE-GAS, EE-H2): 0 GW/a
        »neubau_voll« (KKW-GAS, KKW-H2): Lager-multiplizierte Zubau-Rate
        ab Lager-Startjahr.

    Lager-Startjahr (): hergeleitet aus
    ``CAMP_RANGES.kkw_realisierung_grad`` mit Formel
    ``Startjahr = Approval + min(T_plan / grad, T_cap)``. Mit Approval
    2029, T_plan 7 a, T_cap 21 a:

    +----------------------+--------+----------+
    | Lager                | T_build| Startjahr|
    +======================+========+==========+
    | atom_optimistic      |  7 a   |   2036   |
    +----------------------+--------+----------+
    | neutral_default      | 17,5 a |   2046   |
    +----------------------+--------+----------+
    | ee_optimistic        | 21 a   |   2050   |
    +----------------------+--------+----------+
    | bestand_optimistic   | 17,5 a |   2046   |
    +----------------------+--------+----------+

    **Lager-Multiplikator auf Zubau-Rate:** ``rate = 2 × grad``, sodass
    neutral_default 0,8 GW/a fährt. Die Lager-Spreizung wirkt damit
    über die Zubau-Geschwindigkeit, nicht nur über das Startjahr.

    [SRC: ``CAMP_RANGES.kkw_realisierung_grad`` (siehe core/camp_ranges.py); reale FOAK-Bauzeiten OL3/Flam/HPC/Vogtle; Areva-EPR-Vendor-Spec (7 a Plan-Bauzeit); UK NAO HPC-2017 (FID-Vorlauf).]
    """
    if path not in ("kkw_gas", "kkw_h2"):
        return 0.0
    startjahr = _kkw_epr_startjahr(camp)
    if year < startjahr:
        return 0.0
    lager_mult = KKW_REALIZATION_BY_CAMP.get(camp, 0.40)
    return 2.0 * lager_mult


_KKW_EPR_CAPEX_LAGER: dict[str, float] = {
    "neutral_default": 14000.0,
    "atom_optimistic": 9000.0,
    "ee_optimistic": 16000.0,
    "bestand_optimistic": 16000.0,
}


def _kkw_neubau_epr_capex_eur_kw(_year: int, camp: str) -> float:
    """KKW-EPR-CAPEX nach Lager. Sehr breite Spreizung wegen realisierter
    Bauzeit-Inflation HPC (~18.000), Flamanville (~14.800), Sizewell-Plan
    (~9.000).

    [SRC: EDF-HPC, COURDESCOMPTES-FLAM, vendor specifications. Neutral_default 14.000 = Mitte zwischen HPC ~18.000 und Sizewell-FOAK ~10.000.]
    """
    return _KKW_EPR_CAPEX_LAGER.get(camp, _KKW_EPR_CAPEX_LAGER["neutral_default"])


_KKW_VLH_LAGER: dict[str, float] = {
    "neutral_default": 5500.0,
    "atom_optimistic": 7800.0,
    "ee_optimistic": 5500.0,
    "bestand_optimistic": 7800.0,
}


def _kkw_vlh_per_lager(camp: str) -> float:
    """KKW-VLH nach Lager (EPR und SMR gleich).

    [SRC: LAGER_RANGES.nuclear_full_load_hours in lager_ranges.py. Rationale: 80%-EE-System drosselt KKW → neutral_default 5.500 (ISE-2024). atom_optimistic 7.800 (KKW-privilegiert), ee_optimistic 5.500.]
    """
    return _KKW_VLH_LAGER.get(camp, _KKW_VLH_LAGER["neutral_default"])


_KKW_WACC_LAGER: dict[str, float] = {
    "neutral_default": 0.090,
    "atom_optimistic": 0.070,
    "ee_optimistic": 0.100,
    "bestand_optimistic": 0.100,
}


def _kkw_wacc_pct(_year: int, camp: str) -> float:
    """KKW-WACC nach Lager (EPR und SMR mit gleichem Bandbreiten-Profil).

    [SRC: CALIBRATED:HPC-Helm-Oxford+Sizewell-RAB; core/wacc.py: WACC_TABLE['nuclear']. Rationale: HPC real 9 %, Sizewell-RAB 7 %
    (mit staatlicher Risiko-Externalisierung), Privat-Investor 10 %.]
    """
    return _KKW_WACC_LAGER.get(camp, _KKW_WACC_LAGER["neutral_default"])


TECH_INVENTORY["kkw_neubau_epr"] = TechEntry(
    tech_id="kkw_neubau_epr",
    existing_gw_2026=0.0,
    decay_curve=_kkw_neubau_epr_auslauf_kurve,
    max_additions_gw_per_year=_kkw_neubau_epr_max_zubau_gw_per_year,
    vlh_normal=_kkw_vlh_per_lager("neutral_default"),
    vlh_max_boost=_kkw_vlh_per_lager("atom_optimistic"),
    lifetime_years=60,
    capex_eur_kw=_kkw_neubau_epr_capex_eur_kw,
    opex_fix_eur_kw_a=130.0,
    opex_var_eur_mwh=5.0,
    wacc_pct=_kkw_wacc_pct,
    fuel_set=("uran",),
    efficiency_el=0.36,  # [SRC: EDF/Areva EPR-Spezifikation (Olkiluoto-3, Flamanville-3, HPC) Nominal ~36 %; IAEA-PRIS EPR-Klasse Generation III+]
    source=(
        "ForwardCostParams.nuclear_capex_eur_kw (konservativer Anker im "
        "Korridor EDF-HPC, Flamanville-3, Sizewell-C-RAB-Plan). "
        "ISE-2024 + EDF-Daten für OPEX, VLH und Lifetime. "
        "core.wacc.WACC_TABLE['nuclear'] für WACC (Bandbreite "
        "CALIBRATED gegen HPC-Helm-Oxford und Sizewell-RAB). "
        "core.lager_ranges.LAGER_RANGES.nuclear_full_load_hours für "
        "VLH-Lager-Spreizung. FOAK-Bauzeiten-Anker für "
        "KKW-Realisierungsgrad-Trajektorie."
    ),
    derivation=(
        "VLH normal/Boost als feste Werte (neutral 6.500 / atom_opt "
        "7.800); lager-spezifische VLH-Variation über CAMP_RANGES "
        "modelliert. "
        "Lager-Startjahr für Zubau (atom_opt 2034, neutral 2042, "
        "ee_opt/bestand_opt 2048) rückgekoppelt an "
        "CAMP_RANGES.kkw_realisierung_grad via T_build=T_plan/grad mit "
        "T_plan=7 a EPR-Vendor + Approval 2029, T_cap=21 a politischer "
        "Horizont (siehe Funktions-Docstring _kkw_neubau_epr_max_zubau). "
        "Zubau-Rate 2 GW/a ab Startjahr: 24 GW Ziel @ 2055 / ~12 a Aufbau. "
        "opex_var 5 €/MWh: Branchen-Standard für Verschleiß + Brennelement-"
        "Wechsel-Anteil, der nicht in Brennstoffkosten steckt."
    ),
)


# === KKW-Neubau SMR =======================================================
#
# SMR (Small Modular Reactor) als separate Tech wegen anderer Kosten-
# und Größen-Profile. Vendor-Pläne (BWRX-300, NuScale, Rolls-Royce SMR)
# sehen niedrigere CAPEX pro kW als EPR vor, aber FOAK-Realität noch
# ungewiss.


def _kkw_neubau_smr_auslauf_kurve(_year: int) -> float:
    return 0.0


#: SMR-Approval-Jahr (analog EPR, FID-Vorlauf 3 a aus 2026er Politik-
#: Beschluss).
KKW_SMR_APPROVAL_YEAR: int = 2029

#: Plan-Bauzeit SMR (BWRX-300 OPG-Plan, RR-SMR UK-GBN-Programm).
KKW_SMR_PLAN_YEARS: int = 5

#: Cap auf SMR-Bauzeit (geringere Verzögerungs-Reserve nach
#: IAEA-2024 Status Report Annex G).
KKW_SMR_T_CAP: int = 17


def _kkw_smr_startjahr(camp: str) -> int:
    """SMR-Startjahr analog EPR — Approval + sqrt-gestreckte Bauzeit."""
    grad = KKW_REALIZATION_BY_CAMP.get(camp, 0.40)
    t_build = min(KKW_SMR_PLAN_YEARS / max(1e-9, grad), KKW_SMR_T_CAP)
    return KKW_SMR_APPROVAL_YEAR + int(round(t_build))


def _kkw_neubau_smr_max_zubau_gw_per_year(year: int, path: str, camp: str) -> float:
    """SMR-Zubau. Frühere Verfügbarkeit als EPR (Vendor-Pläne ab ~2032),
    kleinere Einheiten → Zubau-Rate niedriger pro Anlage, aber mehr
    Anlagen.

    Lager-Startjahr aus ``_kkw_smr_startjahr(camp)``. Mit Approval 2029,
    T_plan 5 a, T_cap 17 a:

    +----------------------+---------+----------+
    | Lager                | T_build | Startjahr|
    +======================+=========+==========+
    | atom_optimistic      |   5 a   |   2034   |
    +----------------------+---------+----------+
    | neutral_default      | 12,5 a  |   2042   |
    +----------------------+---------+----------+
    | ee_optimistic        | 17 a    |   2046   |
    +----------------------+---------+----------+
    | bestand_optimistic   | 12,5 a  |   2042   |
    +----------------------+---------+----------+

    [SRC: WNA-2025 SMR-Übersicht; BWRX-300 OPG-Darlington-IESO-Filings 2024; Rolls-Royce-SMR UK-GBN-Programm 2024; IAEA-2024 Status Report NR-T-1.18.]

    Zubau-Rate: ``0,8 × grad`` GW/a. Analog zu EPR — die Lager-Spreizung
    wirkt sowohl über Startjahr als auch über die Zubau-Geschwindigkeit.
    """
    if path not in ("kkw_gas", "kkw_h2"):
        return 0.0
    startjahr = _kkw_smr_startjahr(camp)
    if year < startjahr:
        return 0.0
    lager_mult = KKW_REALIZATION_BY_CAMP.get(camp, 0.40)
    return 0.8 * lager_mult


_KKW_SMR_CAPEX_LAGER: dict[str, float] = {
    "neutral_default": 11500.0,
    "atom_optimistic": 6000.0,
    "ee_optimistic": 14000.0,
    "bestand_optimistic": 14000.0,
}


def _kkw_neubau_smr_capex_eur_kw(_year: int, camp: str) -> float:
    """SMR-CAPEX nach Lager.

    [SRC: BWRX-300 OPG-Darlington — IESO-Regulatorische-Unterlagen 2024 nennen Konstruktions-CAPEX ~3,0 Mrd. CAD für 300 MW (~9.000 CAD/kW ≈ 6.200 €/kW Plan-Spec); RR-SMR UK-GBN-Programm ~2,0 Mrd. GBP für 470 MW (~4.500 €/kW Vendor-Plan ohne Kontingenz); NuScale-Carbon-Free-Power-Project 2023 vor Cancel ~89 USD/MWh entspricht ~14.000 €/kW FOAK-Realität. Lager-Werte: atom_optimistic: 6.000 €/kW (Vendor-Plan-optimistisch nth-of- a-kind nach BWRX-300/RR-SMR-Vor-Spezifikation) neutral_default: 11.500 €/kW (Mittel zwischen BWRX-300/RR-SMR-Vendor-Plan und NuScale-FOAK-Realität) ee_optimistic: 14.000 €/kW (FOAK-Realität, NuScale-CFPP pre-Cancel-Niveau) bestand_optimistic: 14.000 €/kW (= ee_optimistic, keine eigene Position) Quellen-Konsistenz: WNA-2025 SMR-Übersicht und OECD-NEA-REDCOST- 2020 Spreizung 4.000-15.000 €/kW als Bandbreiten-Plausi.]
    """
    return _KKW_SMR_CAPEX_LAGER.get(camp, _KKW_SMR_CAPEX_LAGER["neutral_default"])


TECH_INVENTORY["kkw_neubau_smr"] = TechEntry(
    tech_id="kkw_neubau_smr",
    existing_gw_2026=0.0,
    decay_curve=_kkw_neubau_smr_auslauf_kurve,
    max_additions_gw_per_year=_kkw_neubau_smr_max_zubau_gw_per_year,
    vlh_normal=_kkw_vlh_per_lager("neutral_default"),
    vlh_max_boost=_kkw_vlh_per_lager("atom_optimistic"),
    lifetime_years=40,
    capex_eur_kw=_kkw_neubau_smr_capex_eur_kw,
    opex_fix_eur_kw_a=140.0,
    opex_var_eur_mwh=5.0,
    wacc_pct=_kkw_wacc_pct,
    fuel_set=("uran",),
    efficiency_el=0.33,  # [SRC: BWRX-300 (GE-Hitachi), NuScale-VOYGR, RR-SMR Datenblätter — typischer SMR-LWR-Wirkungsgrad 32-34 %, Default 33 %]
    source=(
        "WNA-2025 SMR-Übersicht (Vendor-Pläne BWRX-300, NuScale, Rolls-"
        "Royce SMR). "
        "BWRX-300 OPG-Darlington IESO-Filings 2024 (~9.000 CAD/kW ≈ "
        "6.200 €/kW). RR-SMR UK-GBN-Programm 2024 (~4.500 €/kW Vendor-"
        "Plan). NuScale-CFPP 2023 (~14.000 €/kW FOAK-Realität vor Cancel). "
        "OECD-NEA-REDCOST-2020 für FOAK-vs-nth-of-a-kind-Spreizung. "
        "IAEA-2024 Status Report NR-T-1.18 für T_cap-Verzögerungs-Reserve. "
        "WACC und VLH wie EPR (core/wacc.py, LAGER_RANGES.nuclear_full_"
        "load_hours). Startjahre rückgekoppelt an LAGER_RANGES."
        "kkw_realisierung_grad analog EPR."
    ),
    derivation=(
        "Lebensdauer 40 a statt 60 a für EPR — Plausi-Setzung (kleinere "
        "Standardisierung, möglicher Modul-Tausch); OECD-NEA-2023-Empfehlung "
        "40-60 a, untere Bandbreite konservativ. "
        "OPEX fix 140 €/kW/a (10 €/kW/a über EPR) wegen Fixkosten-Sprung "
        "kleinerer Einheiten (Personal- und Sicherheits-Fixkostenanteil "
        "schlägt bei 300 MW relativ höher durch als bei 1.600 MW)."
    ),
)


# === Batterie-Speicher ====================================================
#
# Hinweis: Batterie ist konzeptionell keine reine »Erzeugungs«-Tech,
# sondern Demand-Shifter / Spitzenlast-Lieferant. Sie ist als
# Tech-Eintrag mit ``is_storage=True``-Flag modelliert; CAPEX-Annuität
# läuft über ``lcoe.secondary_surcharge``, Dispatch bleibt bei 0.


def _battery_auslauf_kurve(_year: int) -> float:
    """Batterie-Bestand: heute kleiner Bestand (~8 GW BNEF-2025-Trend).
    Konservativ konstant; Lifecycle-Auslauf nach ~15 a, Repowering üblich.

    [SRC: BNEF-2025-ESS Outlook + BSW-Solar/BVES Statistik 2024 (Batteriespeicher-Bestand Großbatterien + Heimspeicher DE 2024 ~8 GW nutzbare Spitzenleistung); 15-a-Lebensdauer aus BNEF-2025 LFP-Zyklen- Garantie 6.000 cycles. Repowering-Konvention: Zellen-Tausch behält PCS/Trafo/Anschluss → faktisch konstanter Bestand bis Zubau erfasst.]
    """
    return 8.0


def _battery_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """Batterie-Zubau nach BNEF-2025-ESS-Trend.

    Werte:
        Profil »voll« (EE-/KKW-Pfade): 8 GW/a default mit 20 % Wachstum
          [SRC: BNEF-2025-ESS battery_zubau_*-Defaults, Ziel 72 GW @ 2037 MODO-2025]
        Profil »gedämpft«: 3 GW/a
        Profil »gestoppt«: 1 GW/a
    """
    base_zubau_pro_profil = {
        "voll": 8.0,
        "gedämpft": 3.0,
        "gestoppt": 1.0,
    }
    profil = _WIND_PFAD_ZU_PROFIL.get(path, "voll")
    base = base_zubau_pro_profil[profil]
    return base * _WIND_LAGER_MULT.get(camp, 1.0)


def _battery_capex_eur_kw(year: int, _camp: str) -> float:
    """Batterie-CAPEX in €/kW (4-h-System-Konvention).

    [SRC: BNEF-2025-ESS turnkey 110 €/kWh × 4-h-Dimensionierung ≈ 440 €/kW. Plus Lernkurve 5 %/a aus path_model.py (battery_capex × 0.95^t).]
    """
    base_capex_kw_2026 = 440.0
    if year <= 2026:
        return base_capex_kw_2026
    return base_capex_kw_2026 * (0.95 ** (year - 2026))


def _battery_wacc_pct(_year: int, camp: str) -> float:
    """Batterie-WACC nach Lager.

    [SRC: CALIBRATED:BNEF-2025-ESS-implizit; core/wacc.py:WACC_TABLE['battery'].
    Rationale: oberhalb PV (Asset-Klasse-Neuheit), unterhalb KKW (kürzere
    Bauzeit, etablierte Lieferkette).]
    """
    camp_values = {
        "neutral_default": 0.070,
        "ee_optimistic": 0.060,
        "atom_optimistic": 0.085,
        "bestand_optimistic": 0.085,
    }
    return camp_values.get(camp, camp_values["neutral_default"])


TECH_INVENTORY["battery"] = TechEntry(
    tech_id="battery",
    existing_gw_2026=8.0,
    decay_curve=_battery_auslauf_kurve,
    max_additions_gw_per_year=_battery_max_zubau_gw_per_year,
    # Batterie ist im Normalbetrieb netto null: vlh_normal=0 setzt
    # Batterie-Mix-Dispatch auf 0 → keine Doppelzählung mit PV/Wind
    # im Stack. Batterie-Kosten laufen weiterhin über _secondary_surcharge
    # (Speicher-Komponente aus installierter Kapazität × CAPEX × Annuität).
    # Stress-Chart nutzt vlh_max_boost weiter über winter_stress_balance.
    # Eine Integration in die primäre Dispatch-Schleife verlangt eine
    # konsistente Energie-Bilanz (Charge-Pool aus PV/Wind-Überschuss +
    # RTE-Verlust als Demand-Mehrbedarf), die im annual-aggregate-Modell
    # nicht trivial abzubilden ist.
    vlh_normal=0.0,
    vlh_max_boost=1500.0,
    lifetime_years=15,
    capex_eur_kw=_battery_capex_eur_kw,
    opex_fix_eur_kw_a=10.0,
    opex_var_eur_mwh=0.0,
    wacc_pct=_battery_wacc_pct,
    fuel_set=(),
    is_storage=True,
    source=(
        "BNEF-2025-ESS (CAPEX 110 €/kWh turnkey LFP, Lifetime 6.000 cycles "
        "≈ 15 a). "
        "MODO-2025 Inertia-Bedarf-Studie (Ziel 72 GW @ 2037; "
        "path_model.py). "
        "core/wacc.py:WACC_TABLE['battery'] (WACC 7,0 % default, Bandbreite "
        "6,0-8,5 %)."
    ),
    derivation=(
        "Batterie ist Demand-Shifter (Round-Trip-Verluste ~15 %, Netto-"
        "Energie-Beitrag ≤ 0). vlh_normal=0 hält das Modell konsistent: "
        "Batterie liefert keinen Strom in der Jahres-Mengen-Bilanz, "
        "sondern verschiebt PV/Wind-Überschuss zeitlich (was bereits im "
        "Demand-aware Cap der fluktuierenden EE berücksichtigt ist). "
        "is_storage=True markiert den Sonderfall: lcoe.secondary_surcharge "
        "iteriert über alle is_storage-Techs und addiert deren CAPEX-"
        "Annuität als Speicher-Komponente. "
        "CAPEX €/kW über 4-h-Konvention (110 €/kWh × 4 h ≈ 440 €/kW). "
        "vlh_max_boost=1500 h: Dunkelflauten-Spitzen-Anteil im Stress-Chart "
        "(winter_stress_balance nutzt BATTERY_DURATION_HOURS / Dunkelflauten-"
        "Dauer). Lernkurve 5 %/a aus path_model.py."
    ),
)


# === DSM (Demand-Side-Management) =========================================
#
# DSM ist als reine Demand-Shifter-Tech modelliert — kein Brennstoff,
# niedrige VLH (nur Spitzenlast-Reserve), CAPEX nur für Steuerungs-
# technik + Vertrags-Vergütung. Aktivierung als Tech mit eigener
# Akkumulation und VLH (kein heuristischer Anteil-Aufschlag mehr).
#
# Quellen-Bündel:
#   - BNetzA-Monitoring-Bericht 2024: DSM-Verträge ~4-5 GW heute zugelassen
#     (Reduzierbare Lasten nach § 13a EnWG, AbLaV-Verordnung).
#   - BMWK-Strategie »Demand Response in DE 2030« 2024: Ziel 10 GW @ 2030
#     (Industrie-Lastflex + Aggregatoren).
#   - ENTSO-E SO GL Regelreserve-Methodologie: DSM-Vergütungs-Niveau
#     50-200 €/MWh (mittel 100 €/MWh als opex_var-Anker).
#   - Heutige DSM-Aktivierungs-Zeit ~2 h/Aktivierung × ~150 Aktivierungen/a
#     = 300 h VLH normal. Im Stress (Dunkelflaute) deutlich länger
#     abrufbar (1.500 h boost).


def _dsm_auslauf_kurve(_year: int) -> float:
    """DSM-Bestand 2026 ~10 GW: 5 GW AbLaV-Verträge (BNetzA § 13a EnWG)
    + 5 GW Spannungsabsenkungs-Reserve (Stufe 1 des BNetzA-Engpass-
    Stufenkonzepts; 5 % von ~100 GW Peak via automatischer ÜNB-Maßnahme).
    Beide Mechanismen sind Demand-Side-Reduktion in Dunkelflauten und
    werden hier konzeptuell zusammengeführt. Bleibt konstant.

    [SRC: BNetzA Monitoring 2024 AbLaV ~5 GW; BNetzA Stufenkonzept Stufe 1 Spannungsabsenkung 3-5 % Last automatisch über ÜNB-Schalter ~5 GW.]
    """
    return 10.0


def _dsm_max_zubau_gw_per_year(year: int, _path: str, camp: str) -> float:
    """DSM-Zubau pfad-neutral, Lager-Multiplikator aus Flex-Realisierung.

    DSM braucht eine maximale Verfügbarkeit. Trajektorie mit Sättigung
    bei ~17-18 GW (BNetzA-Realität-Anker + Spannungsabsenkungs-Bestand).

    - 2026-2030 (Hochlauf-Phase): 1,5 GW/a × Lager-Mult.
      Begründung: BMWK-Demand-Response-Strategie 2024 nennt 10 GW AbLaV
      @ 2030, ausgehend von ~5 GW AbLaV heute → 1,2-1,5 GW/a Aufbau.
      (Spannungsabsenkungs-Bestand wächst nicht — physikalisch begrenzt.)
    - 2030-2040 (Sättigungs-Phase): 0,3 GW/a × Lager-Mult.
      Begründung: Industrie-Aggregator-Wachstum, abnehmender Grenznutzen
      neuer Verträge.
    - Ab 2040: 0 GW/a. Sättigung AbLaV-Anteil ~13 GW + Spannungsabsenkung
      ~5 GW = ~17-18 GW gesamt.
      Begründung: technisches Potential industrieller Lastflex in DE
      ~15-20 GW (BMWK-DR-Studie, Fraunhofer-ISI-2023).
    """
    lager_mult = {
        "neutral_default": 1.0,
        "ee_optimistic": 1.3,
        "atom_optimistic": 0.7,
        "bestand_optimistic": 0.6,
    }.get(camp, 1.0)
    if year < 2026:
        return 0.0
    if year < 2030:
        return 1.5 * lager_mult
    if year < 2040:
        return 0.3 * lager_mult
    return 0.0  # Sättigung


def _dsm_capex_eur_kw(_year: int, camp: str) -> float:
    """DSM-CAPEX. Sehr niedrig — primär Steuerungstechnik + Aggregator-
    Plattform. Plausi-Setzung 100 €/kW.

    [SRC: BMWK-DR-Strategie 2024 nennt Investitionsbedarf ~5-10 Mrd € für 10 GW Aufbau (500-1.000 €/kW) inkl. Steuerungstechnik + Anreiz- Vergütungs-Vorlauf; Default 100 €/kW als asset-light Mittel (Vertrags-Aggregation, keine Hardware-Investitionen).]
    """
    camp_values = {
        "neutral_default": 100.0,
        "ee_optimistic": 80.0,
        "atom_optimistic": 130.0,
        "bestand_optimistic": 120.0,
    }
    return camp_values.get(camp, 100.0)


def _dsm_wacc_pct(_year: int, camp: str) -> float:
    """DSM-WACC analog Batterie (Demand-Shifter, ähnliches Risikoprofil).

    [SRC: Plausi-Anker analog `_battery_wacc_pct` (BNEF-2025-ESS-implizit). Asset-light DSM (Steuerungstechnik + Vergütungs-Pool) hat sogar geringeres Capex-Risiko als Batterie — leichter Abschlag 0,5 pp ggü. Batterie-WACC.]
    """
    camp_values = {
        "neutral_default": 0.065,
        "ee_optimistic": 0.055,
        "atom_optimistic": 0.080,
        "bestand_optimistic": 0.080,
    }
    return camp_values.get(camp, 0.065)


_max_zubau_pfad_mult: dict[str, float] = {"voll": 1.0}


TECH_INVENTORY["dsm"] = TechEntry(
    tech_id="dsm",
    existing_gw_2026=10.0,
    decay_curve=_dsm_auslauf_kurve,
    max_additions_gw_per_year=_dsm_max_zubau_gw_per_year,
    vlh_normal=300.0,  # DSM nur Spitzenlast-Reserve, nicht Dauerlast
    vlh_max_boost=1500.0,  # in Dunkelflaute deutlich länger abrufbar
    lifetime_years=20,
    capex_eur_kw=_dsm_capex_eur_kw,
    opex_fix_eur_kw_a=5.0,  # Wartung Steuerungstechnik
    opex_var_eur_mwh=100.0,  # DSM-Aktivierungs-Preis ~100 €/MWh (ENTSO-E-Mittel)
    wacc_pct=_dsm_wacc_pct,
    fuel_set=(),  # Demand-Shifter, kein Brennstoff
    source=(
        "BNetzA-Monitoring-Bericht 2024 (DSM-Verträge ~5 GW nach § 13a EnWG, "
        "AbLaV-Verordnung). "
        "BNetzA-Engpass-Stufenkonzept Stufe 1 (Spannungsabsenkung 3-5 % "
        "via ÜNB-Schalter, ~5 GW automatisch in Dunkelflaute). "
        "BMWK-Strategie Demand Response 2030 (Ziel 10 GW AbLaV-Pool). "
        "ENTSO-E SO GL Regelreserve-Methodologie (Vergütungs-Niveau "
        "50-200 €/MWh). "
        "Konvention Stresstest: DSM 10-18 GW abrufbar in der "
        "Dunkelflaute (winter_stress.py)."
    ),
    derivation=(
        "DSM-Block als Tech mit eigener Akkumulation und VLH. "
        "vlh_normal=300 h: Spitzenlast-Reserve, nicht Dauerlast (BNetzA-"
        "Aktivierungs-Statistik: ~150 Aktivierungen/a × ~2 h). "
        "vlh_max_boost=1.500 h: in Dunkelflaute deutlich länger abrufbar. "
        "Lager-Multiplikator (1,3 / 0,7 / 0,6) folgt Glaubens-Spreizung "
        "zum Industrie-Flex-Hochlauf. "
        "efficiency_el=1,0 (kein Brennstoff)."
    ),
)


# === Strategische Reserve (BNetzA-Kapazitätsreserve § 13b EnWG) ===========
#
# Stufe 4 des BNetzA-Engpass-Stufenkonzepts: stillgelegte Kraftwerke, die
# nur in physischen Notfällen aktiviert werden (nicht am Markt). Politisch
# garantiert über § 13b EnWG; überlebt den Kohle-Phaseout 2032 als Notfall-
# Reserve mit Erdgas-Brennstoff.
#
# Vorhaltungs-OPEX bleiben niedrig (Warm-Erhaltung); Aktivierungs-OPEX
# hoch (Notfall-Brennstoff + Verschleiß). VLH normal = 0 (außerhalb
# DUNKELFLAUTE nicht aktiv); vlh_max_boost = 200 h für Dunkelflauten-
# Notfälle (BNetzA-Aktivierungs-Empirie 2021/22).


def _strategische_reserve_auslauf_kurve(_year: int) -> float:
    """Strategische Reserve 3,3 GW (BNetzA-Monitoring 2024). Konstant über
    den Modell-Horizont, weil § 13b EnWG-Reserve politisch garantiert.

    [SRC: BNetzA Bedarfsanalyse Kapazitätsreserve 2024 (~3,3 GW Steinkohle + Gas, Verträge bis mindestens 2031); § 13b EnWG erlaubt fortgesetzte Reservevorhaltung jenseits Kohle-Phaseout.]
    """
    return 3.3


def _strategische_reserve_max_zubau_gw_per_year(_year: int, _path: str, _camp: str) -> float:
    """Kein Zubau — politisch fixiertes Reservevolumen ~3 GW.

    [SRC: BNetzA-Methodik §13b: Bedarfsanalyse erlaubt Volumen-Anpassung nach Markt-Lage, aber kein systematischer Aufbau über Modell-Horizont.]
    """
    return 0.0


def _strategische_reserve_capex_eur_kw(_year: int, camp: str) -> float:
    """Sehr niedrig — Reaktivierung Bestand-Anlagen, kein Neubau.

    [SRC: BNetzA Kapazitätsreserve-Vergütungs-Methodik 2024 nennt Reaktivierungs-Aufwand ~50-80 €/kW für Steinkohle/Gas-Bestand; Default 50 €/kW im neutralen Lager.]
    """
    camp_values = {
        "neutral_default": 50.0,
        "ee_optimistic": 50.0,
        "atom_optimistic": 50.0,
        "bestand_optimistic": 50.0,
    }
    return camp_values.get(camp, 50.0)


def _strategische_reserve_wacc_pct(_year: int, camp: str) -> float:
    """Reserve-WACC: regulierte Vergütung mit niedrigerem Risiko."""
    camp_values = {
        "neutral_default": 0.055,
        "ee_optimistic": 0.050,
        "atom_optimistic": 0.060,
        "bestand_optimistic": 0.060,
    }
    return camp_values.get(camp, 0.055)


TECH_INVENTORY["strategische_reserve"] = TechEntry(
    tech_id="strategische_reserve",
    existing_gw_2026=3.3,
    decay_curve=_strategische_reserve_auslauf_kurve,
    max_additions_gw_per_year=_strategische_reserve_max_zubau_gw_per_year,
    vlh_normal=0.0,  # nie regulär dispatched
    vlh_max_boost=200.0,  # nur Dunkelflauten-Aktivierung (BNetzA-Empirie)
    lifetime_years=30,
    capex_eur_kw=_strategische_reserve_capex_eur_kw,
    opex_fix_eur_kw_a=30.0,  # Warm-Erhaltung Bestand-Anlagen
    opex_var_eur_mwh=300.0,  # Notfall-Brennstoff + Verschleiß
    wacc_pct=_strategische_reserve_wacc_pct,
    fuel_set=("erdgas_inland",),  # Notfall-Brennstoff (Steinkohle-Reserve
    # läuft mit Phaseout 2032 aus; ab dann reine Erdgas-Reserve gemäß § 13b)
    efficiency_el=0.40,  # ältere Bestand-Anlagen, schlechter als Neubau-Gas
    source=(
        "BNetzA Bedarfsanalyse Kapazitätsreserve 2024 (Volumen ~3,3 GW). "
        "§ 13b EnWG (gesetzliche Grundlage für Reservevorhaltung jenseits "
        "Markt). "
        "BNetzA-Engpass-Stufenkonzept Stufe 4. "
        "ACER VOLL-Methodologie 2018 (Notfall-Vergütungs-Korridor)."
    ),
    derivation=(
        "Strategische Reserve als eigene Tech-Klasse — Mengen-Bilanz "
        "trennt Markt-Kraftwerke (gas_h2ready, erdgas_bestand) von "
        "Reserve-Kraftwerken (strategische_reserve). vlh_normal=0 stellt "
        "sicher, dass die Reserve nicht regulär dispatched wird; "
        "vlh_max_boost=200 h erlaubt Dunkelflauten-Aktivierung. "
        "efficiency_el=0,40 spiegelt ältere Bestand-Anlagen (Steinkohle/"
        "Gas-Block 1990er-2000er); opex_var=300 €/MWh = Notfall-Vergütungs-"
        "Niveau."
    ),
)


# === Importe (Strom-Import-Saldo) =========================================
#
# Importe sind als reguläre Tech modelliert. AGEB-2024 zeigt: DE ist
# saisonal Netto-Importeur (Strom-Import-Saldo ~10-30 TWh/a), ENTSO-E-
# Kupplungs-Kapazität ~30 GW NTC zu Nachbarländern.
#
# Importe sind keine klassische Erzeugungs-Tech (keine eigene Kraftwerks-
# Investition), sondern Strom-Markt-Bezug aus Nachbarländern. CAPEX = 0
# (Netzkopplung schon vorhanden, BNetzA-NABEG-Trasse), opex_var =
# durchschnittlicher Import-Strompreis ~60 €/MWh, fuel_set leer.
#
# Quellen:
#   - BNetzA-Monitoring 2024: NTC-Kapazitäten DE-Nachbarn ~25-30 GW.
#   - AGEB-2024: Strom-Import-Saldo 2024 ~32 TWh (Netto-Importeur).
#   - ENTSO-E ERAA 2024: Import-Verfügbarkeit in Wetter-Stress ~70 % NTC.
#   - Eurostat ENERGY-2024: Mittel-Import-Spotpreise EU-DE ~50-80 €/MWh.


def _importe_auslauf_kurve(_year: int) -> float:
    """Import-NTC-Kapazität konstant bei 10 GW (Mittel über die NTC-
    Anteile zu Nachbarländern, gewichtet mit historischer Auslastung).
    Real-NTC ist ~25-30 GW, aber nur ~30-40 % im Schnitt für Importe
    nutzbar (zeitliche Asynchronität EE-Anteile in Nachbarländern).

    [SRC: BNetzA-Monitoringbericht 2024 (NTC-Werte DE-Nachbarn 25-30 GW physikalisch); ENTSO-E ERAA 2024 (saisonale Verfügbarkeit ~70 % NTC in Wetter-Stress, ~30-40 % im Jahres-Mittel wegen zeitlicher Asyn- chronität EE-Profile Nachbarländer). 10-GW-Konvention deckt sich mit AGEB-2024-Strom-Import-Saldo 32 TWh / VLH 2.000 h ≈ 16 GW äquivalent; konservativer 10-GW-Anker, weil VLH untere Bandbreite.]
    """
    return 10.0


def _importe_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """Import-NTC-Ausbau analog BNetzA NABEG-Trassen: 0,3 GW/a in EE-
    Pfaden, 0,2 GW/a in KKW/WEITER-SO/BESTAND (weniger Netzkupplungs-
    Investition).
    """
    lager_mult = {
        "neutral_default": 1.0,
        "ee_optimistic": 1.3,
        "atom_optimistic": 0.7,
        "bestand_optimistic": 0.5,
    }.get(camp, 1.0)
    if path in ("ee_gas", "ee_h2"):
        base = 0.3
    elif path in ("kkw_gas", "kkw_h2"):
        base = 0.2
    else:  # weiterso, bestand
        base = 0.15
    return base * lager_mult


def _importe_capex_eur_kw(_year: int, _camp: str) -> float:
    """Import-CAPEX = 0. Netzkupplungen sind bereits vorhanden, Netz-
    Ausbau-Kosten gehören in die Sekundär-Schicht (Netz-Aufschlag), nicht
    in die Tech-CAPEX.

    [SRC: BNetzA-NABEG-Trasse-Status 2024 (Bestandsnetz-Konvention) + Tech/Sekundär-Trennung. Tech-CAPEX = 0 vermeidet Doppelzählung mit Netz-Aufschlag in `_sekundaer_aufschlag`.]
    """
    return 0.0


def _importe_wacc_pct(_year: int, _camp: str) -> float:
    """Import-WACC nicht anwendbar (kein CAPEX). Konvention: 0,05.

    [SRC: Konvention bei CAPEX=0 — WACC bleibt im Schema gefordert und auf risikofreien Bond-Yield-Anker 5 % gesetzt; wirkt nicht auf LCOE solange capex_eur_kw=0.]
    """
    return 0.05


TECH_INVENTORY["importe"] = TechEntry(
    tech_id="importe",
    existing_gw_2026=10.0,
    decay_curve=_importe_auslauf_kurve,
    max_additions_gw_per_year=_importe_max_zubau_gw_per_year,
    vlh_normal=2000.0,  # Importe sind nicht voll ausgelastet
    vlh_max_boost=4000.0,  # In Stress-Wetter intensiver
    lifetime_years=40,  # Netzkupplungen, langfristig
    capex_eur_kw=_importe_capex_eur_kw,
    opex_fix_eur_kw_a=2.0,  # Wartung Kupplungs-Stationen
    opex_var_eur_mwh=75.0,  # Annual-Mittel mit Stress-Spike-Beimischung (BNetzA-Engpass-Bericht 2024, Epex-Spike-Episoden 2020-2024)
    wacc_pct=_importe_wacc_pct,
    fuel_set=(),  # Strom-Markt, kein Brennstoff
    source=(
        "BNetzA-Monitoring 2024 (NTC ~25-30 GW DE-Nachbarn). "
        "AGEB-2024 (Strom-Import-Saldo ~32 TWh). "
        "ENTSO-E ERAA 2024 (Import-Verfügbarkeit ~70 % NTC im Wetter-Stress). "
        "Eurostat ENERGY-2024 (Import-Spotpreise 50-80 €/MWh Basis-Niveau). "
        "BNetzA-Engpass-Bericht 2024 (Wetter-Stress-Spike-Episoden 2020-2024: "
        "100-2000 €/MWh in Dunkelflauten, Beimischung in Annual-Mittel "
        "≈ +15 €/MWh)."
    ),
    derivation=(
        "Importe als reguläre Tech. "
        "Bestand 10 GW = effektive Import-Auslastung aus 25-30 GW NTC "
        "(30-40 % nutzbar wegen zeitlicher Asynchronität EE-Nachbarn). "
        "vlh_normal=2.000 h = Import-Saldo 32 TWh / NTC-Kapazität ≈ "
        "20 % VLH-Äquivalent. CAPEX=0 (Netzkupplung bereits da). "
        "opex_var=75 €/MWh = Spotpreis-Mittel 60 €/MWh plus Stress-Spike-"
        "Beimischung 15 €/MWh: in Wetter-Stress-Episoden (~3-5 % der "
        "Jahresstunden, Korrelation EU-weit) steigen Spot-Preise auf "
        "100-2000 €/MWh; die annual-aggregate-Bilanz mischt diese "
        "Stress-Anteile in den Effektivpreis ein. Lager-Spreizung folgt "
        "geopolitischer Glaubens-Streuung an Versorgungs-Sicherheit."
    ),
)


# === Kohle (Bestand) ======================================================
#
# Quellen-Bündel:
#   - Bestand 2026: ~33 GW (16 GW Steinkohle + 17 GW Braunkohle, BNetzA-
#     Monitoring 2024 + path_model.py).
#   - Auslauf-Trajektorie: KVBG (Bundesgesetzblatt 2020 I S. 1818) →
#     Phaseout bis spätestens 2038.
#   - Kein Neubau (politisch ausgeschlossen seit KVBG).
#   - VLH: ~5.000 h heute, sinkt mit EE-Hochlauf weiter.
#   - Boost-VLH: ~6.500 h (alte Kohle ist nicht beliebig boostbar).


def _kohle_auslauf_kurve(year: int) -> float:
    """Kohle-Auslauf nach KVBG. Linear 33 GW (2026) → 0 GW (2038).

    [SRC: KVBG, BGBl. I 2020 S. 1818. Stützstellen aus path_model.py (KVBG-Trajektorie 16 GW Steinkohle + 17 GW Braunkohle Phaseout 2038).]
    """
    if year <= 2026:
        return 33.0
    if year >= 2038:
        return 0.0
    progress = (2038 - year) / (2038 - 2026)
    return 33.0 * progress


def _kohle_max_zubau_gw_per_year(_year: int, _path: str, _camp: str) -> float:
    """Kohle-Zubau = 0 in allen Pfaden und Lagern. KVBG schließt
    Neubau aus.

    [SRC: KVBG 2020 §§ 4 ff.]
    """
    return 0.0


def _kohle_capex_eur_kw(_year: int, _camp: str) -> float:
    """Kohle-CAPEX = 0. Bestand ist abgeschrieben, kein Neubau.

    [SRC: Forward-Cost-Konvention für abgeschriebenen Bestand (Tech/Sekundär-Trennung). KVBG 2020 §§ 4 ff verbietet Neubau → bestand_gw_2026=33 ist Endstand, sinkt auf 0 @ 2038 ohne neue CAPEX-Belastung. Konsistent mit `_kkw_bestand_capex_eur_kw` und `_erdgas_bestand_capex_eur_kw`.]
    """
    return 0.0


_KOHLE_WACC_LAGER: dict[str, float] = {
    "neutral_default": 0.040,
    "ee_optimistic": 0.030,
    "atom_optimistic": 0.050,
    "bestand_optimistic": 0.050,
}


def _kohle_wacc_pct(_year: int, camp: str) -> float:
    """Kohle-WACC nach Lager. Niedrig (Bestand, abgeschrieben).

    [SRC: Forward-Cost-Konvention für abgeschriebenen Bestand analog KKW-Bestand und Wasser (siehe `_kkw_bestand_wacc_pct`, `_wasser_wacc_pct`). Cashflow-stabil bis KVBG-Phaseout 2038, kein Refinanzierungs-Risiko; Bandbreite 3-5 % entspricht Anleihen-Niveau für Bestand-Erzeuger (BNetzA-Kraftwerksstilllegungs-Vergütungs-Modell + Kohle-Aus- Sicherheitsbereitschaft AbschG 2020). Lager-Spreizung wie KKW-Bestand.]
    """
    return _KOHLE_WACC_LAGER.get(camp, _KOHLE_WACC_LAGER["neutral_default"])


TECH_INVENTORY["kohle"] = TechEntry(
    tech_id="kohle",
    existing_gw_2026=33.0,
    decay_curve=_kohle_auslauf_kurve,
    max_additions_gw_per_year=_kohle_max_zubau_gw_per_year,
    vlh_normal=5000.0,
    vlh_max_boost=6500.0,
    lifetime_years=40,
    capex_eur_kw=_kohle_capex_eur_kw,
    opex_fix_eur_kw_a=35.0,
    opex_var_eur_mwh=3.0,
    wacc_pct=_kohle_wacc_pct,
    fuel_set=("steinkohle", "braunkohle"),
    efficiency_el=0.38,  # [SRC: BNetzA-Kraftwerksliste 2024 Steinkohle-Bestand-Mix ~38 %, Braunkohle-Mix ~37 %; AGEB-2024 Energiebilanz Strom/Brennstoff-Verhältnis]
    source=(
        "BNetzA-Monitoring 2024 (Bestand 33 GW). "
        "KVBG, BGBl. I 2020 S. 1818 (Phaseout 2038, Auslauf-Trajektorie). "
        "Branchen-Standard OPEX für Bestand-Kohle (~35 €/kW/a fix, ~3 €/MWh "
        "var). VLH 5.000 h heute mit Trend zu weiter sinkend."
    ),
    derivation=(
        "CAPEX 0: Bestand abgeschrieben, kein Neubau (KVBG-Verbot). "
        "Forward-Cost-Konvention. "
        "WACC 4,0 % default: Cashflow-stabil bis Phaseout, niedrige "
        "Refinanzierungs-Last. "
        "vlh_max_boost=6.500 h: Bestand-Kohle ist nicht beliebig boostbar; "
        "Plausi-Setzung auf Basis BNetzA-Stress-Test-Berichten. "
        "OPEX-Werte sind Branchen-Standard ohne direkte Quelle "
        "(ISE-2024 oder BNetzA-Detailbericht nicht direkt zitiert)."
    ),
)


# === Erdgas (Bestand) =====================================================
#
# Quellen-Bündel:
#   - Bestand 2026: 31 GW (BNetzA-Monitoring 2024).
#   - Auslauf: nicht durch Gesetz erzwungen; folgt natürlicher Lebensdauer.
#     path_model.py hat Auslauf-Trajektorie mit Stützstellen.
#   - VLH normal: ~3.500 h (flexibel, Spitzenlast + Mittelast).
#   - Boost-VLH: ~7.000 h (Gas ist die boostbarste fossile Tech).
#   - fuel_set: Multi-Fuel — Inland-Erdgas, Import-Pipeline-Gas, LNG.


def _erdgas_bestand_auslauf_kurve(year: int) -> float:
    """Erdgas-Bestands-Auslauf. Linear 31 GW (2026) → ~10 GW (2055),
    folgt natürlicher Lebensdauer der ~25 a alten Bestandsflotte.

    [SRC: path_model.py Auslauf-Trajektorie. Branchen-Annahme: Bestandskraftwerke laufen ~40 a, viele aus 1990er-2000er-Jahren → Stilllegungs-Welle 2030-2050. Eine BNetzA-Detail-Altersverteilung würde die Stützstellen schärfer kalibrieren.]
    """
    if year <= 2026:
        return 31.0
    if year >= 2055:
        return 10.0
    progress = (year - 2026) / (2055 - 2026)
    return 31.0 + progress * (10.0 - 31.0)


def _erdgas_bestand_max_zubau_gw_per_year(year: int, path: str, _camp: str) -> float:
    """Erdgas-Bestand-Zubau pfad-spezifisch.

    - Aktive Pfade (EE-GAS/H2, KKW-GAS/H2, WEITER-SO): 0. Neue Anlagen
      kommen als »gas_h2ready« (BMWE-Kraftwerksstrategie 2026 fordert
      H2-ready für Neubau).
    - **BESTAND**: aktiver Erdgas-Bestand-Neubau ohne H2-ready ist Teil
      der Bestands-Lager-Programm-Definition. Da gas_h2ready in BESTAND
      verboten ist, deckt erdgas_bestand-Zubau die Backup-Last allein.
      Zubau-Trajektorie: 3 GW/a (2026-2040, Hochlauf-Phase) plus
      1 GW/a (2040-2055, Sektor-Kopplungs-Plateau-Phase). Das deckt die
      wachsende Demand des aktiv elektrifizierenden BESTAND-Pfades —
      Programm-konsistent: »wenn Erdgas der einzige Backup ist, baue
      ihn ausreichend, statt Spot-Pönale zu zahlen«.

    [SRC: BESTAND-Lager-Programm-Definition (aktive Erdgas-Erweiterung 36→50 GW Hochlauf-Phase, plus Plateau-Erweiterung ~15 GW bis 2055 zur Mengen-Bilanz-Schließung).]
    """
    if path == "bestand":
        if year < 2026:
            return 0.0
        if year < 2040:
            return 3.0  # 3 GW/a Hochlauf-Phase 2026-2040 (→50 GW Plateau-Eintritt)
        return 1.0  # 1 GW/a Plateau-Erweiterung bis 2055 (Demand-Deckung)
    del year
    return 0.0


def _erdgas_bestand_capex_eur_kw(_year: int, camp: str) -> float:
    """Erdgas-Bestand-CAPEX als Misch-Wert aus abgeschriebenem Bestand
    (0 €/kW) und BESTAND-Pfad-Neubau (800 €/kW OCGT-Vendor-Preis).

    Misch-Verhältnis grob: BESTAND-Pfad 2045 hat ca. 17 GW Bestand-
    Auslauf + 42 GW Neubau = 71 % Neubau-Anteil → effektiver Misch-
    CAPEX ~ 800 × 0,5 = 400 €/kW. Lager-Spreizung 350-450.

    Achtung: in aktiven Pfaden (EE-GAS/H2, KKW-GAS/H2, WEITER-SO) bleibt
    erdgas_bestand-Tech nur Bestand (kein Zubau, siehe
    _erdgas_bestand_max_zubau_gw_per_year), daher überzeichnet die
    400-€/kW-CAPEX dort minimal die Bestand-Annuität. Eine feinere
    Trennung Bestand vs. Neubau ließe sich durch zwei separate Techs
    (erdgas_bestand_alt + erdgas_bestand_neubau) abbilden.

    [SRC: BMWE-Kraftwerksstrategie 2026 (OCGT-Vendor-Preise GE LMS100, Siemens-SGT-800); Misch-Argument aus Bestand+Neubau.]
    """
    camp_values = {
        "neutral_default": 400.0,
        "ee_optimistic": 450.0,
        "atom_optimistic": 350.0,
        "bestand_optimistic": 375.0,
    }
    return camp_values.get(camp, 400.0)


def _gas_wacc_pct(_year: int, camp: str) -> float:
    """Gas-WACC nach Lager (Bestand und H2-ready Neubau gleicher Wert).

    [ASSUMPTION: 7,0 % default — vergleichbar mit Bio, weil Gas-Anlagen
    kalkulierbares Cashflow-Profil haben (Spitzenlast-Preise gut
    prognostizierbar). H2-ready Neubau hat leicht höheres Risiko
    (Multi-Fuel-Komplexität) → siehe gas_h2ready WACC unten.]
    """
    camp_values = {
        "neutral_default": 0.070,
        "ee_optimistic": 0.060,
        "atom_optimistic": 0.080,
        "bestand_optimistic": 0.080,
    }
    return camp_values.get(camp, camp_values["neutral_default"])


TECH_INVENTORY["erdgas_bestand"] = TechEntry(
    tech_id="erdgas_bestand",
    existing_gw_2026=31.0,
    decay_curve=_erdgas_bestand_auslauf_kurve,
    max_additions_gw_per_year=_erdgas_bestand_max_zubau_gw_per_year,
    vlh_normal=3500.0,
    vlh_max_boost=7000.0,
    lifetime_years=40,
    capex_eur_kw=_erdgas_bestand_capex_eur_kw,
    opex_fix_eur_kw_a=25.0,
    opex_var_eur_mwh=3.0,
    wacc_pct=_gas_wacc_pct,
    fuel_set=("erdgas_inland", "erdgas_import", "lng"),
    efficiency_el=0.42,  # [SRC: BNetzA-Kraftwerksliste 2024 Bestand-Mix aus OCGT (η~0,38) + CCGT (η~0,55), gewichtet ~42 % für Bestand-Flotte vor CCGT-Anteil-Anstieg]
    source=(
        "BNetzA-Monitoring 2024 (Bestand 31 GW). "
        "path_model.py Auslauf-Trajektorie. "
        "BMWE-Kraftwerksstrategie 2026 (kein reiner Erdgas-Neubau mehr). "
        "Branchen-Standard OPEX für Bestandsflotte."
    ),
    derivation=(
        "CAPEX 0: Bestand abgeschrieben. "
        "Auslauf 31→10 GW über 2026-2055 ist Annahme aus natürlicher "
        "Lebensdauer (40 a, viele Anlagen aus 1990er-2000er); "
        "BNetzA-Altersverteilung der Gas-Flotte nicht eingearbeitet. "
        "vlh_max_boost=7.000 h: Gas ist boostbarste fossile Tech. "
        "fuel_set Multi-Fuel: Anlagen können je nach Markt "
        "Inland-Erdgas, Import-Pipeline-Gas oder LNG verbrennen."
    ),
)


# === Gas H2-ready (Neubau) ================================================
#
# Quellen-Bündel:
#   - Bestand 2026: 0 (Neubau-Tech, Plan ab 2026 nach BMWE-Kraftwerks-
#     strategie 2026 mit Zielband 6-22 GW).
#   - CAPEX 1.100 €/kW: VDE-2023 (h2_gas_turbine_capex).
#   - VLH wie Erdgas-Bestand (flexibel disponiert).
#   - fuel_set: Multi-Fuel inkl. H2-Inland und H2-Import.
#   - WACC: leicht höher als Erdgas-Bestand wegen Multi-Fuel-Tech-Neuheit.


def _gas_h2ready_auslauf_kurve(_year: int) -> float:
    """Gas-H2-ready hat keinen Bestand 2026 (Neubau-Tech). Bestand
    entsteht durch Zubau ab 2026; Auslauf entlang Lebensdauer 35 a.

    Liefert konservativ 0 — die Zubau-Funktion übernimmt den
    Bestandsaufbau in der Dispatch-Pipeline.
    """
    return 0.0


def _gas_h2ready_max_zubau_gw_per_year(_year: int, path: str, camp: str) -> float:
    """Gas-H2-ready-Zubau — »delivered rate« aus Drei-Quellen-Triangulation.

    Werte:
        Profil »voll« (EE-/KKW-Pfade): 0,8 GW/a
        Profil »gedämpft« (WEITER-SO): 0,3 GW/a
        Profil »gestoppt« (BESTAND): 0,0 GW/a

    Lager-Multiplikator wie EE-Techs.

    [SRC-TRIANGULATION:

    (1) **BMWK-Kraftwerksstrategie 2024 (Brutto-Zielband):**
        10 GW H2-ready bis 2030, 22 GW bis 2040. Linear gerechnet
        wäre das ~1,5–2,0 GW/a in der Ramp-up-Phase. Das ist aber
        Brutto-Politik-Ziel ohne Reibungs-Berücksichtigung.

    (2) **KSV-Runde-1 delivered rate (BNetzA 2025):**
        Erste KSV-Ausschreibungsrunde (Kraftwerkssicherheits-
        Verordnung 2024) hat ~5 GW H2-ready ausgeschrieben, davon
        Zuschlag <2 GW realistisch in 2-3 Jahre Bauzeit. Das ist
        die »delivered rate« ohne Politik-Wunschdenken.

    (3) **BNetzA-Kraftwerksliste (laufend gepflegt):**
        Kommerzielle H2-ready-Projekte im Bau/Genehmigung 2024-2025
        liegen unter 1 GW/a realisierter Inbetriebnahme; das
        Politik-Ziel 10 GW @ 2030 wird im BMWK-Monitoring-Bericht
        2025 als gefährdet eingestuft.

    Triangulation: BMWK-Ziel ~2 GW/a (Brutto), KSV-Runde-1 ~0,7 GW/a
    (delivered), BNetzA-Realisierung ~0,5–1,0 GW/a. Konservativ
    geometrisches Mittel + Modell-Default-Korridor = 0,8 GW/a.

    Über 30 Jahre (2026-2055) ergibt das ~24 GW H2-ready @ 2055 —
    konsistent zu T45-Strom 2045 H2-ready-Korridor 15-25 GW.

    ]"""
    base_zubau_pro_profil = {
        "voll": 0.8,
        "gedämpft": 0.3,
        "gestoppt": 0.0,
    }
    profil = _WIND_PFAD_ZU_PROFIL.get(path, "voll")
    base = base_zubau_pro_profil[profil]
    return base * _WIND_LAGER_MULT.get(camp, 1.0)


def _gas_h2ready_capex_eur_kw(_year: int, _camp: str) -> float:
    """Gas-H2-ready-CAPEX. Keine Lernkurve modelliert (etablierte
    Gasturbinen-Tech mit H2-Brenner-Erweiterung).

    [SRC: VDE-2023 (h2_gas_turbine_capex_eur_kw 1.100).]
    """
    return 1100.0


def _gas_h2ready_wacc_pct(_year: int, camp: str) -> float:
    """Gas-H2-ready-WACC. Leicht höher als Erdgas-Bestand wegen Multi-
    Fuel-Tech-Neuheit (Brennstoff-Markt-Unsicherheit H2).

    [SRC: Plausi-Setzung 7,5 % default — Aufschlag 0,5 pp gegen `_gas_wacc_pct`. Begründung Multi-Fuel-Brennstoff-Markt-Unsicherheit: H2-Liefer-Verträge sind heute nicht etabliert (H2Global-Auktionen 2024 nur Anlauf-Volumina), Investoren preisen das ein.]
    """
    camp_values = {
        "neutral_default": 0.075,
        "ee_optimistic": 0.065,
        "atom_optimistic": 0.085,
        "bestand_optimistic": 0.085,
    }
    return camp_values.get(camp, camp_values["neutral_default"])


TECH_INVENTORY["gas_h2ready"] = TechEntry(
    tech_id="gas_h2ready",
    existing_gw_2026=0.0,
    decay_curve=_gas_h2ready_auslauf_kurve,
    max_additions_gw_per_year=_gas_h2ready_max_zubau_gw_per_year,
    vlh_normal=3500.0,
    vlh_max_boost=7000.0,
    lifetime_years=35,
    capex_eur_kw=_gas_h2ready_capex_eur_kw,
    opex_fix_eur_kw_a=25.0,
    opex_var_eur_mwh=3.0,
    wacc_pct=_gas_h2ready_wacc_pct,
    # H2-Dispatch zuerst, Erdgas als Fallback. H2 wird graduell genutzt
    # sobald verfügbar, statt erst nach vollem Erdgas-Phaseout-Fade. In
    # Pfaden ohne H2-Programm (WEITER-SO, BESTAND: H2 als "stop" in
    # fuel_constraints) wird H2 übersprungen, Erdgas dispatched. In
    # EE-GAS/KKW-GAS (H2-Programm "gedämpft") wird H2 wo verfügbar genutzt,
    # weil gas_h2ready H2-ready ist und die Verfügbarkeits-Quote über
    # h2_inland/h2_import dauer_max-Kurve gesteuert wird (bewusst auf
    # 100/50 TWh @ 2045 reduziert wegen Industrie-Vorrang).
    fuel_set=(
        "h2_inland",
        "h2_import",
        "erdgas_inland",
        "erdgas_import",
        "lng",
    ),
    efficiency_el=0.55,  # [SRC: Siemens SGT-9000HL / GE-9HA / Mitsubishi-M701JAC CCGT-Neubau h2-ready ~55-60 %, Default 55 % als unteres CCGT-Klasse; BMWE Kraftwerksstrategie 2026 H2-ready-Anforderung]
    source=(
        "BMWE-Kraftwerksstrategie 2026 (Zielband 6-22 GW; siehe "
        "core.path_model H2-ready-Stützstellen). "
        "VDE-2023 für CAPEX (ForwardCostParams.h2_gas_turbine_capex_eur_kw). "
        "Multi-Fuel-Konvention."
    ),
    derivation=(
        "Bestand 2026 = 0: reine Neubau-Tech. Zubau-Trajektorie via "
        "max_zubau_gw_per_year und Lager-Multiplikator. "
        "WACC 7,5 % default: Aufschlag 0,5 pp gegen Erdgas-Bestand wegen "
        "Multi-Fuel-Tech-Neuheit (H2-Brennstoff-Markt-Unsicherheit). "
        "Auslauf-Kurve konstant 0 — der Bestandsaufbau erfolgt in der "
        "Dispatch-Pipeline aus akkumuliertem Zubau."
    ),
)


TECH_INVENTORY["wind_onshore"] = TechEntry(
    tech_id="wind_onshore",
    existing_gw_2026=62.0,
    decay_curve=_wind_onshore_auslauf_kurve,
    max_additions_gw_per_year=_wind_onshore_max_zubau_gw_per_year,
    vlh_normal=2200.0,
    vlh_max_boost=None,
    lifetime_years=25,
    capex_eur_kw=_wind_onshore_capex_eur_kw,
    opex_fix_eur_kw_a=35.0,
    opex_var_eur_mwh=0.0,
    wacc_pct=_wind_wacc_pct,
    fuel_set=(),
    source=(
        "BNetzA-MaStR Q4 2024 (Bestand 62 GW). "
        "Fraunhofer ISE Stromgestehungskosten Juli 2024 "
        "(CAPEX 1.400 €/kW Bandbreite 1.300-1.900, OPEX 35 €/kW/a, "
        "VLH 2.200 h, Lifetime 25 a,933,939,957). "
        "IRENA-2024 + DE-NIMBY-Aufschlag (WACC 6,0 %, Bandbreite "
        "4,5-7,5 %; core/wacc.py:WACC_TABLE['wind']). "
        "EEG-2023 (Zubau-Default 8 GW/a). "
        "ISE-2024 zeigt keine Lernkurve bis 2045 → CAPEX zeitkonstant."
    ),
    derivation=(
        "Auslauf-Kurve konservativ konstant — "
        "BNetzA-MaStR-Altersverteilung importieren (Onshore-Boom "
        "2000-2010 läuft ab 2025 aus, Repowering-Trend kompensiert). "
        "Pfad-Modifikatoren für max_zubau (»gedämpft« 3 GW/a, »gestoppt« "
        "1 GW/a) sind Modell-Setzungen ohne EEG-Auktions-Quelle. "
        "Lager-Multiplikatoren wie PV (1.3/0.9/0.7) als Plausi-Setzung. "
        "opex_var_eur_mwh=0: ISE-2024-Konvention."
    ),
)

TECH_INVENTORY["wind_offshore"] = TechEntry(
    tech_id="wind_offshore",
    existing_gw_2026=9.0,
    decay_curve=_wind_offshore_auslauf_kurve,
    max_additions_gw_per_year=_wind_offshore_max_zubau_gw_per_year,
    vlh_normal=4200.0,
    vlh_max_boost=None,
    lifetime_years=25,
    capex_eur_kw=_wind_offshore_capex_eur_kw,
    opex_fix_eur_kw_a=90.0,
    opex_var_eur_mwh=0.0,
    wacc_pct=_wind_wacc_pct,
    fuel_set=(),
    source=(
        "BNetzA-MaStR Q4 2024 (Bestand 9 GW). "
        "Fraunhofer ISE Stromgestehungskosten Juli 2024 "
        "(CAPEX 3.000 €/kW, OPEX 90 €/kW/a inkl. See-Aufschlag, "
        "VLH 4.200 h, Lifetime 25 a,934,940,958). "
        "IRENA-2024 (WACC wie Onshore; core/wacc.py:WACC_TABLE['wind']). "
        "EEG-2023 / WindSeeG (Zubau-Default 4 GW/a)."
    ),
    derivation=(
        "Auslauf-Kurve konservativ konstant — Offshore-Flotte ist jünger "
        "(ab 2010), erste Auslauf-Welle erst ab 2035. "
        "Pfad-Modifikatoren wie Onshore (»gedämpft« 1 GW/a, »gestoppt« "
        "0,5 GW/a) sind Modell-Setzungen ohne Quelle. "
        "Lager-Multiplikatoren wie PV/Onshore. "
        "opex_var_eur_mwh=0: ISE-2024-Konvention."
    ),
)

TECH_INVENTORY["pv"] = TechEntry(
    tech_id="pv",
    existing_gw_2026=95.0,
    decay_curve=_pv_auslauf_kurve,
    max_additions_gw_per_year=_pv_max_zubau_gw_per_year,
    vlh_normal=1050.0,
    vlh_max_boost=None,
    lifetime_years=30,
    capex_eur_kw=_pv_capex_eur_kw,
    opex_fix_eur_kw_a=12.0,
    opex_var_eur_mwh=0.0,
    wacc_pct=_pv_wacc_pct,
    fuel_set=(),
    source=(
        "BNetzA-MaStR Q4 2024 (Bestand 95 GW). "
        "Fraunhofer ISE Stromgestehungskosten Juli 2024 "
        "(CAPEX 700 €/kW, OPEX 12 €/kW/a, VLH 1050 h, Lifetime 30 a; "
        "path_model.py). "
        "IRENA-2024-WACC + DE-Premium (WACC 5,0 %, Bandbreite 3,8-6,5 %; "
        "core/wacc.py:WACC_TABLE['pv']). "
        "ISE-2024-Lernkurve + BNEF-NEO-2024-NZS-Median "
        "(Plateau-CAPEX 700/350 €/kW pro Lager). "
        "EEG-2023 (Zubau-Default 18 GW/a)."
    ),
    derivation=(
        "Auslauf-Kurve konservativ (Repowering kompensiert) — "
        "BNetzA-MaStR-Altersverteilung nicht eingearbeitet. "
        "Pfad-Modifikatoren für max_zubau (»gedämpft« 5 GW/a, »gestoppt« "
        "2 GW/a) sind heutige Modell-Setzungen ohne EEG-Auktions-Quelle. "
        "Lager-Multiplikatoren auf Zubau (1.3/0.9/0.7) sind Plausi-Setzungen "
        "spiegelnd LAGER_RANGES.pv_lcoe-Verhältnisse. "
        "opex_var_eur_mwh=0: ISE-2024 weist für PV keine variablen "
        "Betriebskosten separat aus."
    ),
)
