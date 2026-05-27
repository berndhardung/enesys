"""SystemState-Enum + per-Tech Multiplier-Logik.

Drei System-Zustände mit physikalischer Semantik.

Drei Zustände:

- ``NORMAL``: Status Quo Jahres-Bilanz. EE liefert vlh_normal, Battery
  ist nicht VLH-getragen (Energie-Cap), Importe Status-Quo-Saldo.
- ``SCARCITY``: Struktureller Politik-Notfall. Backup-Brennstoffe in
  ``policy.boost_policy`` dürfen boost_max nutzen; alle anderen Techs
  bleiben auf vlh_normal. KEIN VLH-Boost für Speicher/DSM/Importe.
- ``DUNKELFLAUTE``: Winter-Wetter-Stress. PV/Wind reduziert (× 0,3),
  Strom-Importe reduziert (× 0,5, EU-korreliert), Battery erschöpft (0),
  DSM bei physical-cap, Gas/Erdgas-Bestand Boost erlaubt.

Die Logik wirkt über zwei Helper-Funktionen, die aus
``TechEntry.max_dispatch_twh_per_year`` und ``_max_strom_aus_fuel``
aufgerufen werden:

- ``flh_multiplier_for_state(tech_id, state)``: VLH-Faktor (0..1+)
- ``fuel_cap_mode(fuel_id, policy, state)``: ``"dauer"`` oder ``"boost"``
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .inventories.path_policy import PathPolicyEntry


class SystemState(Enum):
    """Physischer System-Zustand für Dispatch-Bilanz.

    Methodische Setzung: Battery/DSM/Importe dürfen im Dunkelflaute-
    Stress nicht künstlich boosten (»unsichtbare Reserve«-Artefakt).
    """

    NORMAL = "normal"
    SCARCITY = "scarcity"
    DUNKELFLAUTE = "dunkelflaute"


# Pro-Tech-VLH-Multiplier-Tabelle.
# Tech-Klassen mit ähnlicher Stress-Reaktion:
# - "ee": PV/Wind fluktuiert mit Wetter (Dunkelflaute reduziert)
# - "speicher": Battery hat Energie-Cap, nicht VLH-Cap → 0 in Stress
# - "dsm": Demand-Shifting bei physikalischer Cap; in Stress aktiviert
# - "import": Strom-Saldo, EU-korreliert → in Dunkelflaute reduziert
# - "grundlast": KKW/Bio/Wasser/Bestand laufen weitgehend wetterunabhängig
# - "thermisch_flex": Gas/Erdgas-Bestand/gas_h2ready/Kohle können boosten
#
# Multiplier wirkt auf vlh_normal (NORMAL=1.0). Für DUNKELFLAUTE-Werte
# < 1 wird Wetterstress simuliert; > 1 erlaubt Lastfolge-Boost.
#
# [SRC: ENTSO-E SO-GL Auslegungs-Norm; AGORA Dunkelflaute-Studie 2024.]
_TECH_KLASSE: dict[str, str] = {
    "pv": "ee",
    "wind_onshore": "ee",
    "wind_offshore": "ee",
    "wasser": "grundlast",
    "bio": "grundlast",
    "kkw_bestand": "grundlast",
    "kkw_neubau_epr": "grundlast",
    "kkw_neubau_smr": "grundlast",
    "battery": "speicher",
    "dsm": "dsm",
    "importe": "import",
    "erdgas_bestand": "thermisch_flex",
    "gas_h2ready": "thermisch_flex",
    "kohle": "thermisch_flex",
    "strategische_reserve": "thermisch_flex",
}

# VLH-Multiplier pro Tech-Klasse × SystemState.
_VLH_MULT: dict[str, dict[SystemState, float]] = {
    "ee": {
        SystemState.NORMAL: 1.0,
        SystemState.SCARCITY: 1.0,
        # Empirisch dokumentiert sind PV ≈ 0,05-0,10 × Jahresmittel und
        # Wind onshore ≈ 0,15-0,25 × Jahresmittel über 10-14-Tage-
        # Dunkelflauten. Gewichtet über EE-Mix-Verhältnis landet man bei
        # 0,15-0,25 (konservativ-realistisch).
        # [SRC: DWD-Dunkelflauten-Auswertung Januar 2010; Heide/Hess
        # (ZSW) Multi-Wochen-Statistik; ENTSO-E Winter Outlook 2024/25.]
        SystemState.DUNKELFLAUTE: 0.25,
    },
    "grundlast": {
        SystemState.NORMAL: 1.0,
        SystemState.SCARCITY: 1.0,
        SystemState.DUNKELFLAUTE: 1.0,  # wetterunabhängig
    },
    "speicher": {
        # Battery: keine VLH-Multiplier-Wirkung; die CAPEX-Annuität läuft
        # über lcoe.secondary_surcharge (is_storage=True-Iteration).
        # vlh_normal=0 (per Tech-Inventory) bleibt 0 in jedem State.
        SystemState.NORMAL: 1.0,
        SystemState.SCARCITY: 1.0,
        SystemState.DUNKELFLAUTE: 1.0,
    },
    "dsm": {
        # DSM: in NORMAL nur Spitzenlast-Reserve (300h Default), in
        # SCARCITY/DUNKELFLAUTE auf physical-cap aktiviert (5× ≈ 1500h).
        # 1500h ist physical-cap (BNetzA-Aktivierungs-Statistik 2024),
        # NICHT künstlicher Boost.
        SystemState.NORMAL: 1.0,
        SystemState.SCARCITY: 5.0,
        SystemState.DUNKELFLAUTE: 5.0,
    },
    "import": {
        # Strom-Import: NORMAL = Status-Quo-Saldo. Kein Boost in SCARCITY
        # (Politik-Notfall ändert NTC-Verfügbarkeit nicht). DUNKELFLAUTE
        # reduziert (EU-korrelierte Wetter-Knappheit).
        # Wert 0,35: ENTSO-E TYNDP 2024 »Adverse Weather« zeigt für
        # Nordwest-Europa-Korrelations-Ereignisse Import-Verfügbarkeits-
        # rückgänge von 60-80 % (FR mit KKW-Revisionen + Heizlast, NL/BE/DK
        # simultan importierend). 0,35 ist konservative obere Kante der
        # Korridor-Mitte.
        # [SRC: ENTSO-E TYNDP 2024 Adverse Weather Scenario; ENTSO-E Winter
        # Outlook 2024/25; ERAA 2024 Scarcity-Szenarien.]
        SystemState.NORMAL: 1.0,
        SystemState.SCARCITY: 1.0,
        SystemState.DUNKELFLAUTE: 0.35,
    },
    "thermisch_flex": {
        # Gas/Kohle/Bestand: VLH-Boost erlaubt nur in DUNKELFLAUTE.
        # In SCARCITY läuft Anlage auf vlh_normal — der Notfall öffnet
        # nur die Brennstoff-Cap (s. fuel_cap_mode), nicht die VLH.
        SystemState.NORMAL: 1.0,
        SystemState.SCARCITY: 1.0,
        SystemState.DUNKELFLAUTE: None,  # → vlh_max_boost falls vorhanden
    },
}


def flh_multiplier_for_state(tech_id: str, state: SystemState) -> float | None:
    """Liefert VLH-Multiplier für (tech_id, state).

    Rückgabe ``None`` signalisiert: nutze ``vlh_max_boost`` direkt
    (statt ``vlh_normal × Multiplier``). Wird von
    ``TechEntry.max_dispatch_twh_per_year`` als Spezialfall behandelt.

    Default für unbekannte Techs: 1.0 (kein Stress-Effekt).
    """
    klasse = _TECH_KLASSE.get(tech_id, "grundlast")
    return _VLH_MULT[klasse][state]


def fuel_cap_mode(fuel_id: str, policy: PathPolicyEntry, state: SystemState) -> str:
    """Liefert ``"boost"`` oder ``"dauer"`` für Brennstoff-Cap.

    - NORMAL: immer ``"dauer"`` (regulatorische Cap).
    - SCARCITY: ``"boost"`` falls ``fuel_id in policy.boost_policy`` (LNG,
      h2_import, erdgas_import), sonst ``"dauer"``.
    - DUNKELFLAUTE: ``"boost"`` für alle Brennstoffe (Winter-Stress
      operativer Cap-Aufweichung).
    """
    if state is SystemState.NORMAL:
        return "dauer"
    if state is SystemState.DUNKELFLAUTE:
        return "boost"
    # SCARCITY
    if policy.boost_policy.get(fuel_id, False):
        return "boost"
    return "dauer"


def is_emergency_or_stress(state: SystemState) -> bool:
    """Hilfs-Prädikat: SystemState != NORMAL.

    Wird von Phaseout-Fade-Logik (F3-Glättung) gebraucht. In NORMAL läuft
    Phaseout regulär aus; in SCARCITY/DUNKELFLAUTE wird er gedämpft
    weiter erlaubt (linear 1,0 → 0,3 über das 10-Jahre-Fade-Fenster).
    """
    return state is not SystemState.NORMAL
