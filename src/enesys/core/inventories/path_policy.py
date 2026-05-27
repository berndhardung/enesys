"""Schema für `PATH_POLICY` und `PolitikSetzung`.

Pfad-Politik pro Pfad.

Sechs Pfade: WEITER-SO, BESTAND, EE-GAS, EE-H2, KKW-GAS, KKW-H2.

Politische Setzung als eigene Achse: `default_politik` ist
das Politik-Bündel des Pfads (NEP-Realisierungsgrad, EEG-Auktions-Volumen,
H2-Programm-Ambition, KKW-Erlaubnis). Lager bleibt empirische Streuung
um diese Politik (Bauzeit, Kosten, Lieferketten).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

DemandCallable = Callable[[int, str], float]  # (year, lager) -> twh


@dataclass(frozen=True)
class PolicySetting:
    """Politische Stellschrauben als Pfad-Default.

    Felder sind Politik-Achsen, die der Gesetzgeber/die Bundesregierung
    dreht. Werte sind dimensionslos / kategorisch (Profile), nicht
    physische Annahmen — die kommen über `lager` in den Tech- und
    Brennstoff-Funktionen.

    Explizite Politik-Versprechen für kkw_realisierung_grad und
    h2_realisierung_grad: trennt Politik (was wird entschieden)
    von Lager (wie weit klappt die Umsetzung empirisch — Welt-Belief).
    Diese Felder sind die Politik-Wunsch-Werte pro Pfad-Politik; die
    realisierte Größe wird durch Welt-Belief-Mechanismen (FOAK, Markt,
    EU-Recht) moduliert.
    """

    nep_realization_rate: float  # 0.0 – 1.0+, Realisierungs-Annahme NEP-Pfad
    eeg_auktions_volumen_profil: str  # z. B. "voll", "gedämpft", "gestoppt"
    h2_program_ambition: str  # z. B. "voll", "gedämpft", "gestoppt"
    kkw_erlaubnis_profil: (
        str  # z. B. "kein_neubau", "neubau_beschränkt", "neubau_voll", "reaktivierung"
    )
    nuclear_realization_rate: float = 0.0  # Politik-Wunsch-Anteil KKW-Realisierung
    h2_realization_rate: float = 1.0  # Politik-Wunsch-H2-Hochlauf-Multiplikator
    source: str = ""
    derivation: str = ""

    def __post_init__(self) -> None:
        if not self.source and not self.derivation:
            raise ValueError(
                "PolitikSetzung muss source oder derivation tragen (Magic-Number-Verbot)."
            )


@dataclass(frozen=True)
class PathPolicyEntry:
    """Schema für einen Eintrag in `PATH_POLICY`.

    `dispatch_priority`: geordnete Liste von Tech-IDs, in der Reihenfolge,
    in der die installierte Kapazität in der Mengen-Bilanz geschöpft wird.

    `tech_constraints` / `fuel_constraints`: pfad-spezifische Constraints
    als Strings (z. B. "phaseout_2038", "forbidden", "max_2_gw_pa_ab_2032").
    Die Auflösung der Constraints zu numerischen Werten passiert in der
    Dispatch-Logik, nicht im Inventar.

    `boost_policy`: welche Brennstoffe sind unter Stresstest-Bedingungen
    boostbar.

    `default_politik`: Pfad-Default für die Politik-Achsen.

    `demand_cap_profile`: Tech-ID → Anteil-am-Demand-Cap für Must-Run-
    Erzeuger (PV, Wind onshore, Wind offshore). T45-untere-Kante: bei
    den EE-/Bestand-Pfaden bleiben ~10 % thermisches Backup im Mix
    (PV 0,45 + Wind-on 0,27 + Wind-off 0,18 + Wasser/Bio + Backup ≈ 1).
    KKW-Pfade haben strukturell mehr Grundlast und damit kleinere
    Volatil-EE-Anteile (PV 0,40 / Wind-on 0,23 / Wind-off 0,16).
    [SRC: T45-Strom 2045 nennt 50-150 TWh thermischen Backup-Bedarf
    für 850 TWh Demand = 6-18 %, 10 % als untere Kante.]
    """

    path_id: str
    demand_twh: DemandCallable
    dispatch_priority: tuple[str, ...]
    tech_constraints: dict[str, str] = field(default_factory=dict)
    fuel_constraints: dict[str, str] = field(default_factory=dict)
    boost_policy: dict[str, bool] = field(default_factory=dict)
    default_policy: PolicySetting | None = None
    demand_cap_profile: dict[str, float] = field(default_factory=dict)
    fuel_cap_multipliers: dict[str, float] = field(default_factory=dict)
    """Pfad-spezifische Multiplikatoren auf Brennstoff-Verfügbarkeit
    (``FuelEntry.duration_max_twh_per_year``/``boost_max_twh_per_year``).
    Bildet pfad-spezifische Infrastruktur-Investitionen ab: z.B. baut
    BESTAND zusätzliche LNG-Terminals (Multiplikator 2,0 auf LNG-Cap)
    konsistent zum LNG-Beschleunigungsausbau 2022/2023; H2-Pfade können
    H2-Import-Verträge skalieren. Default leer = keine Pfad-Modulation."""
    source: str = ""
    derivation: str = ""

    def __post_init__(self) -> None:
        if not self.source and not self.derivation:
            raise ValueError(
                f"PathPolicyEntry {self.path_id!r} muss source oder "
                f"derivation tragen (Magic-Number-Verbot)."
            )
        if self.default_policy is None:
            raise ValueError(f"PathPolicyEntry {self.path_id!r} muss default_politik setzen.")


PATH_POLICY: dict[str, PathPolicyEntry] = {}
"""Pfad-Politik-Inventar mit sechs Pfaden:
WEITER-SO, BESTAND, EE-GAS, EE-H2, KKW-GAS, KKW-H2.

`default_politik` trennt Politik (was wird entschieden) von
Lager (wie weit klappt die Umsetzung empirisch).
"""


# ---------------------------------------------------------------------------
# Befüllung pro Pfad
# ---------------------------------------------------------------------------


def _make_demand_callable(path_id: str) -> DemandCallable:
    """Wrapper: liest aus DEMAND_CURVES und summiert base + Zusatz."""

    def demand(year: int, camp: str) -> float:
        from .demand_curves import DEMAND_CURVES  # lokal — vermeidet Zyklus

        curve = DEMAND_CURVES[path_id]
        return curve.base_demand_twh(year) + curve.electrification_extra_twh(year, camp)

    return demand


_POLITIK_SOURCE_BASE = (
    "Lager-Bandbreite nep_realisierung_grad 0,45/0,65/0,85 "
    "(siehe core/camp_ranges.py). "
    "EEG-2023 (Auktions-Volumen-Profile). "
    "BMWK Nationale Wasserstoff-Strategie Update 2023 (H2-Programm). "
    "KKW-Ausstiegsgesetz 2011 + KVBG 2020 (KKW-Erlaubnis-Profile)."
)


# Demand-Cap-Profile für Must-Run-EE — pfad-spezifische Anteile am Demand,
# die durch die volatilen EE-Tech-Lines geschöpft werden dürfen, bevor
# Backup/Reserve einspringt. T45-untere-Kante 10 % thermisches Backup
# bleibt bei EE-/Bestand-Pfaden im Restraum.
_CAP_PROFILE_EE = {  # EE-GAS, EE-H2, WEITER-SO, BESTAND
    "pv": 0.45,
    "wind_onshore": 0.27,
    "wind_offshore": 0.18,
}
_CAP_PROFILE_KKW = {  # KKW-GAS, KKW-H2 — Grundlast aus KKW reduziert volatile EE
    "pv": 0.40,
    "wind_onshore": 0.23,
    "wind_offshore": 0.16,
}


# === EE-GAS ===============================================================

PATH_POLICY["ee_gas"] = PathPolicyEntry(
    path_id="ee_gas",
    demand_twh=_make_demand_callable("ee_gas"),
    # Kohle vor Gas. gas_h2ready vor erdgas_bestand: neuere Anlagen sind
    # effizienter als Bestands-OCGT/alter GuD. *-GAS-Pfade führen kein
    # aktives H2-Programm (h2_realization_rate = 0); gas_h2ready läuft
    # mit Erdgas/LNG und unterscheidet sich vom Bestand nur über die
    # Effizienz, nicht über den Brennstoff.
    dispatch_priority=(
        "wasser",  # Must-Run Laufwasser
        "bio",  # Must-Run KWK (Wärme-Kopplung)
        "pv",
        "wind_onshore",
        "wind_offshore",
        "battery",
        "importe",
        "kohle",  # Bestand-Must-Run, Phaseout 2030
        "gas_h2ready",  # Neubau-Backup (effizienter); läuft mit Erdgas/LNG
        "erdgas_bestand",  # Bestand-Fallback
        "dsm",  # Stufen 1+2 BNetzA Engpass-Konzept (Spannungsabsenkung + AbLaV)
        "strategische_reserve",  # Stufe 4 BNetzA §13b — letzte Notfall-Reserve
    ),
    tech_constraints={
        "kkw_neubau_epr": "forbidden",
        "kkw_neubau_smr": "forbidden",
        "kkw_bestand": "forbidden",
        "kohle": "phaseout_2030",  # Klimaambition zieht KVBG vor
        "importe": "no_zubau",  # NTC-Bestand 10 GW reicht (Bridge-Backup-Heuristik cappt ohnehin)
    },
    fuel_constraints={
        "steinkohle": "phaseout_2030",
        "braunkohle": "phaseout_2030",
    },
    boost_policy={
        "lng": True,
        "bio_strom": True,
        "erdgas_import": True,
    },
    default_policy=PolicySetting(
        nep_realization_rate=0.85,
        eeg_auktions_volumen_profil="voll",
        h2_program_ambition="gedämpft",
        kkw_erlaubnis_profil="kein_neubau",
        nuclear_realization_rate=0.0,  # kein KKW-Neubau in EE-Politik
        h2_realization_rate=0.00,  # GAS-Pfad: kein aktives H2-Programm. gas_h2ready wird gebaut (Optionalitäts-Versicherung), läuft im Normalzustand mit Erdgas/LNG; H2 nur als Notfall-Fallback via boost_policy bei DUNKELFLAUTE/SCARCITY.
        source=_POLITIK_SOURCE_BASE,
        derivation=(
            "EE-GAS = ambitionierter EE-Hochlauf (nep 0,85 entspricht "
            "EE-Lager) + EEG voll + kein aktives H2-Programm "
            "(gas_h2ready als Optionalitäts-Versicherung) + kein KKW-Neubau. "
            "Kohle-Vorzieh-Phaseout 2030 über KVBG (2038) — Quelle: "
            "Klimakoalitions-Vertrag 2021 »Kohleausstieg idealerweise 2030« "
            "+ Agora-Energiewende 2023."
        ),
    ),
    demand_cap_profile=_CAP_PROFILE_EE,
    source=_POLITIK_SOURCE_BASE,
    derivation=(
        "Dispatch-Reihenfolge: EE-First (PV→Wind-On→Wind-Off→Wasser→Bio), "
        "dann Batterie als Demand-Shifter, dann gas_h2ready vor "
        "erdgas_bestand (Neubau-Effizienz). gas_h2ready läuft mit "
        "Erdgas/LNG (H2-Programm = 0). Brennstoff-Cap wird in Phase 3 "
        "bedarfsgerecht endogen erweitert (LNG-/Erdgas-Import-Terminals), "
        "Pfad zahlt den Infrastruktur-Aufschlag pro erweiterter TWh. "
        "Notfall-H2-Fallback bei Dunkelflaute via boost_policy."
    ),
)


# === EE-H2 ================================================================

PATH_POLICY["ee_h2"] = PathPolicyEntry(
    path_id="ee_h2",
    demand_twh=_make_demand_callable("ee_h2"),
    # Kohle vor Gas. EE-H2-
    # spezifisch: gas_h2ready (mit H2-first via fuel_set) VOR erdgas_bestand,
    # weil Klimaambition »CO₂ sparen auf den klimaneutralen Pfaden«.
    # gas_h2ready nutzt H2 wo verfügbar (halbierte Stromsektor-Quote),
    # erdgas_bestand füllt den Rest bis phaseout_2045.
    dispatch_priority=(
        "wasser",
        "bio",  # Must-Run KWK
        "pv",
        "wind_onshore",
        "wind_offshore",
        "battery",
        "importe",
        "kohle",  # Bestand-Must-Run, Phaseout 2030
        "gas_h2ready",  # H2-first (Klimaambition); Erdgas-Fade 2035-2045
        "erdgas_bestand",  # reines Erdgas als Backup, phaseout_2045
        "dsm",  # Stufen 1+2 BNetzA Engpass-Konzept (Spannungsabsenkung + AbLaV)
        "strategische_reserve",  # Stufe 4 BNetzA §13b — letzte Notfall-Reserve
    ),
    tech_constraints={
        "kkw_neubau_epr": "forbidden",
        "kkw_neubau_smr": "forbidden",
        "kkw_bestand": "forbidden",
        "kohle": "phaseout_2030",  # Klimaambition wie EE-GAS
        "importe": "no_zubau",  #
    },
    fuel_constraints={
        "steinkohle": "phaseout_2030",
        "braunkohle": "phaseout_2030",
        # Kein Erdgas-Phaseout: Klimaambition über H2-Programm-Ambition
        # (gas_h2ready dispatched H2 zuerst) und EE-Hochlauf. Erdgas bleibt
        # als Fallback, wenn H2-Realisierungsgrad nicht voll greift — sonst
        # entstünde unphysikalischer Lastabwurf bzw. Spot-Pönale.
    },
    boost_policy={
        "h2_inland": True,
        "h2_import": True,
        "bio_strom": True,
        "lng": True,
        "erdgas_inland": True,
        "erdgas_import": True,
    },
    default_policy=PolicySetting(
        nep_realization_rate=0.85,
        eeg_auktions_volumen_profil="voll",
        h2_program_ambition="voll",
        kkw_erlaubnis_profil="kein_neubau",
        nuclear_realization_rate=0.0,  # kein KKW-Neubau in EE-Politik
        h2_realization_rate=0.70,  # Realitäts-Abschlag im neutralen Lager: BMWK-Strategie läuft real hinter (Elektrolyseur <1 GW von 10-GW-Ziel 2030); der Realgrad 1,00 lebt im ee_optimistic-Lager über die h2_inland-Trajektorie, nicht über einen Realgrad >1.
        source=_POLITIK_SOURCE_BASE,
        derivation=(
            "EE-H2 = wie EE-GAS plus volle H2-Programm-Ambition (Aufbau "
            "Inland-Elektrolyse + Importnetz). Kohle-Vorzieh-Phaseout "
            "2030 wie EE-GAS (Klimakoalition 2021 + Agora-Energiewende 2023)."
        ),
    ),
    demand_cap_profile=_CAP_PROFILE_EE,
    source=_POLITIK_SOURCE_BASE,
    derivation=(
        "Identische EE-Tech-Reihenfolge wie EE-GAS. gas_h2ready-Backup "
        "verbrennt H2 (Inland → Import) zuerst, fällt bei H2-Knappheit "
        "auf Erdgas/LNG zurück. Brennstoff-Cap wird in Phase 3 endogen "
        "erweitert (LNG-/Erdgas-Import-Terminals), Pfad zahlt den "
        "Infrastruktur-Aufschlag pro erweiterter TWh. "
        "fuel_constraints: kein Erdgas-Phaseout — Klimaambition über "
        "H2-Programm-Realgrad, nicht über harten Phaseout."
    ),
)


# === KKW-GAS ==============================================================

PATH_POLICY["kkw_gas"] = PathPolicyEntry(
    path_id="kkw_gas",
    demand_twh=_make_demand_callable("kkw_gas"),
    # KKW nach PV/Wind, Kohle vor Gas. gas_h2ready vor erdgas_bestand:
    # neuere Anlagen sind effizienter als Bestands-OCGT/alter GuD.
    # *-GAS-Pfade führen kein aktives H2-Programm (h2_realization_rate = 0);
    # gas_h2ready läuft mit Erdgas/LNG und unterscheidet sich vom Bestand
    # nur über die Effizienz, nicht über den Brennstoff.
    dispatch_priority=(
        "wasser",  # physikalische Grundlast (Must-Run)
        "bio",  # Must-Run KWK (Wärme-Kopplung)
        "pv",  # EEG-Vorrang
        "wind_onshore",
        "wind_offshore",
        "kkw_neubau_epr",  # KKW-Grundlast nach EE
        "kkw_neubau_smr",
        "battery",
        "importe",
        "kohle",  # Bestand-Must-Run, Phaseout 2032
        "gas_h2ready",  # Neubau-Backup (effizienter); läuft mit Erdgas/LNG
        "erdgas_bestand",  # Bestand-Fallback
        "dsm",  # Stufen 1+2 BNetzA Engpass-Konzept (Spannungsabsenkung + AbLaV)
        "strategische_reserve",  # Stufe 4 BNetzA §13b — letzte Notfall-Reserve
    ),
    tech_constraints={
        "kohle": "phaseout_2032",  # KKW ersetzt Grundlast, Vorzieh 2032
        "importe": "no_zubau",  #
    },
    fuel_constraints={
        "steinkohle": "phaseout_2032",
        "braunkohle": "phaseout_2032",
    },
    boost_policy={
        "lng": True,
        "bio_strom": True,
        "erdgas_import": True,
    },
    default_policy=PolicySetting(
        nep_realization_rate=0.65,
        eeg_auktions_volumen_profil="voll",
        h2_program_ambition="gedämpft",
        kkw_erlaubnis_profil="neubau_voll",
        nuclear_realization_rate=1.00,  # Atom-Politik will volles KKW-Programm
        h2_realization_rate=0.00,  # GAS-Pfad: kein aktives H2-Programm. gas_h2ready als Optionalitäts-Versicherung; H2 nur als Notfall-Fallback via boost_policy.
        source=_POLITIK_SOURCE_BASE,
        derivation=(
            "KKW-GAS = mittlerer EE-Hochlauf (nep 0,65 als neutraler "
            "Lager-Default) + EEG voll + kein aktives H2-Programm "
            "(gas_h2ready als Optionalitäts-Versicherung) + KKW-Neubau "
            "voll erlaubt. Lager-spezifischer Zubau-Startjahr "
            "(atom_opt 2034, neutral 2042, ee_opt/bestand_opt 2048). "
            "Kohle-Vorzieh-Phaseout 2032 über KVBG (2038): KKW-Grundlast "
            "ersetzt Kohle ab KKW-Hochlauf-Jahr — politisch plausibel im "
            "Atom-Pfad."
        ),
    ),
    demand_cap_profile=_CAP_PROFILE_KKW,
    source=_POLITIK_SOURCE_BASE,
    derivation=(
        "KKW-Grundlast (EPR + SMR) wird zuerst disponiert, dann EE, dann "
        "Gas-Backup mit Erdgas. Boost-Policy wie EE-GAS."
    ),
)


# === KKW-H2 ===============================================================

PATH_POLICY["kkw_h2"] = PathPolicyEntry(
    path_id="kkw_h2",
    demand_twh=_make_demand_callable("kkw_h2"),
    # KKW nach PV/Wind, Kohle
    # vor Gas, gas_h2ready VOR erdgas_bestand (H2-first auf klimaneutralem
    # Pfad — wie EE-H2). bio als Must-Run KWK vor PV/Wind.
    dispatch_priority=(
        "wasser",
        "bio",  # Must-Run KWK (Wärme-Kopplung)
        "pv",
        "wind_onshore",
        "wind_offshore",
        "kkw_neubau_epr",  # KKW-Grundlast nach EE
        "kkw_neubau_smr",
        "battery",
        "importe",
        "kohle",  # Bestand-Must-Run, Phaseout 2032
        "gas_h2ready",  # H2-first (Klimaambition); Erdgas-Fade
        "erdgas_bestand",  # reines Erdgas, phaseout_2045
        "dsm",  # Stufen 1+2 BNetzA Engpass-Konzept
        "strategische_reserve",  # Stufe 4 BNetzA §13b
    ),
    tech_constraints={
        "kohle": "phaseout_2032",  # wie KKW-GAS
        "importe": "no_zubau",  #
    },
    fuel_constraints={
        "steinkohle": "phaseout_2032",
        "braunkohle": "phaseout_2032",
        # Kein Erdgas-Phaseout: Klimaambition wird über H2-Programm-Ambition
        # (gas_h2ready dispatched H2 zuerst via _fuel_order_path_specific) und
        # KKW-Grundlast getrieben. Erdgas bleibt als Fallback verfügbar, wenn
        # H2-Realisierungsgrad nicht voll greift (Brennstoff-Verfügbarkeits-
        # Lücke wird durch Erdgas geschlossen statt durch Spot-Pönale).
    },
    boost_policy={
        "h2_inland": True,
        "h2_import": True,
        "bio_strom": True,
        "lng": True,
        "erdgas_inland": True,
        "erdgas_import": True,
    },
    default_policy=PolicySetting(
        nep_realization_rate=0.65,
        eeg_auktions_volumen_profil="voll",
        h2_program_ambition="voll",
        kkw_erlaubnis_profil="neubau_voll",
        nuclear_realization_rate=1.00,  # Atom-Politik will volles KKW-Programm
        h2_realization_rate=0.70,  # symmetrisch zu EE-H2: derselbe physikalische H2-Hochlauf, unabhängig vom Pfad-Lager — der pfadspezifische Ambitions-Unterschied steckt in h2_program_ambition, nicht im Realgrad
        source=_POLITIK_SOURCE_BASE,
        derivation=(
            "KKW-H2 = wie KKW-GAS plus volle H2-Programm-Ambition. "
            "gas_h2ready nutzt H2 zuerst (Brennstoff-Reihenfolge via "
            "_fuel_order_path_specific), bei Knappheit Erdgas als Fallback — "
            "kein Erdgas-Verbot. Kohle-Vorzieh-Phaseout 2032 wie KKW-GAS."
        ),
    ),
    demand_cap_profile=_CAP_PROFILE_KKW,
    source=_POLITIK_SOURCE_BASE,
    derivation=(
        "KKW-Grundlast + EE, Gas-Backup mit H2 ab 2045. Vorher Übergangs-"
        "Brennstoff Erdgas. Lager-spezifischer KKW-Startjahr wie "
        "KKW-GAS. DUNKELFLAUTE-Spezial: Erdgas-Notfall-Rückfall."
    ),
)


# === WEITER-SO ============================================================

PATH_POLICY["weiterso"] = PathPolicyEntry(
    path_id="weiterso",
    demand_twh=_make_demand_callable("weiterso"),
    # Kohle vor Gas (Bestand-Must-Run + Phaseout-Optik).
    # bio als Must-Run KWK vor PV/Wind.
    # WEITER-SO hat kein gas_h2ready (forbidden).
    dispatch_priority=(
        "wasser",
        "bio",  # Must-Run KWK
        "pv",
        "wind_onshore",
        "wind_offshore",
        "battery",
        "importe",
        "kohle",  # Bestand-Must-Run, KVBG-Phaseout 2038
        "erdgas_bestand",  # Bestand-Gas, läuft länger als Kohle
        "dsm",  # Stufen 1+2 BNetzA Engpass-Konzept (Spannungsabsenkung + AbLaV)
        "strategische_reserve",  # Stufe 4 BNetzA §13b — letzte Notfall-Reserve
    ),
    tech_constraints={
        "kkw_neubau_epr": "forbidden",
        "kkw_neubau_smr": "forbidden",
        "kkw_bestand": "forbidden",
        "kohle": "phaseout_2038",
        "gas_h2ready": "forbidden",  # WEITER-SO baut keinen H2-ready-Neubau
    },
    fuel_constraints={
        "steinkohle": "phaseout_2038",
        "braunkohle": "phaseout_2038",
    },
    boost_policy={
        "lng": True,
        "erdgas_import": True,
    },
    default_policy=PolicySetting(
        nep_realization_rate=0.45,
        eeg_auktions_volumen_profil="gedämpft",
        h2_program_ambition="gedämpft",
        kkw_erlaubnis_profil="kein_neubau",
        nuclear_realization_rate=0.0,  # WEITER-SO baut keine neuen KKW
        h2_realization_rate=0.00,  # Kein aktives H2-Programm. WEITER-SO hat gas_h2ready=forbidden, also strukturell wie *-GAS-Pfade: H2 nur als Notfall-Fallback via boost_policy (LNG/Erdgas-Import, kein H2-Boost). Ein h2_realization_rate>0 wäre semantisch widersprüchlich zu h2_program_ambition="gedämpft" und liefe in jedem Fall tot.
        source=_POLITIK_SOURCE_BASE,
        derivation=(
            "WEITER-SO = passive Drift (nep 0,45 entspricht BESTAND-Lager) "
            "+ EEG-Auktionen gedämpft + kein aktives H2-Programm "
            "(h2_realization_rate=0 wie *-GAS-Pfade) + kein "
            "KKW-Neubau. Kohle läuft KVBG-2038-Phaseout. EE-Hochlauf folgt "
            "der gedämpften Politik, BESTAND noch gedrosselter."
        ),
    ),
    demand_cap_profile=_CAP_PROFILE_EE,
    source=_POLITIK_SOURCE_BASE,
    derivation=(
        "Dispatch-Reihenfolge: Bestandsfossile zuerst (Kohle bis 2038, "
        "Gas-Bestand), dann EE-Bestand. Kein H2-ready-Neubau (politisch "
        "nicht aktiv vorangetrieben). Boost-Policy: LNG + Erdgas-Import "
        "für Stresstest."
    ),
)


# === BESTAND ==============================================================

PATH_POLICY["bestand"] = PathPolicyEntry(
    path_id="bestand",
    demand_twh=_make_demand_callable("bestand"),
    # Kohle vor Gas wie WEITER-SO.
    dispatch_priority=(
        "wasser",
        "bio",  # Must-Run KWK
        "pv",
        "wind_onshore",
        "wind_offshore",  # Bestand 9 GW (no_zubau)
        "battery",
        "importe",
        "kohle",  # Bestand-Must-Run, KVBG-Phaseout 2038
        "erdgas_bestand",  # Bestands-Lager-Programm (Bestands-Lager-Programm), läuft länger
        "dsm",  # Stufen 1+2 BNetzA Engpass-Konzept (Spannungsabsenkung + AbLaV)
        "strategische_reserve",  # Stufe 4 BNetzA §13b — letzte Notfall-Reserve
    ),
    tech_constraints={
        "kkw_neubau_epr": "forbidden",
        "kkw_neubau_smr": "forbidden",
        "kkw_bestand": "forbidden",
        "kohle": "phaseout_2038",
        "gas_h2ready": "forbidden",
        "wind_offshore": "no_zubau",  # BESTAND drosselt Offshore aktiv
    },
    fuel_constraints={
        "steinkohle": "phaseout_2038",
        "braunkohle": "phaseout_2038",
        "h2_inland": "stop",  # BESTAND fährt kein H2-Programm
        "h2_import": "stop",
    },
    boost_policy={
        "lng": True,
        "erdgas_import": True,
    },
    default_policy=PolicySetting(
        nep_realization_rate=0.30,
        eeg_auktions_volumen_profil="gestoppt",
        h2_program_ambition="gestoppt",
        kkw_erlaubnis_profil="kein_neubau",
        nuclear_realization_rate=0.0,  # BESTAND baut keine neuen KKW
        h2_realization_rate=0.40,  # aktive H2-Skepsis (Bestands-Lager-Programm)
        source=_POLITIK_SOURCE_BASE,
        derivation=(
            "BESTAND-Profil: Fokus auf fossilen Bestandserhalt (nep 0,30, "
            "unter BESTAND-Lager). Demand-Pfad "
            "aktiv gebremst über default_politik, nicht durch globale "
            "Skalierung. BESTAND ist nicht "
            "»passive Drift«, sondern aktive Erdgas-Ausbau-Strategie — "
            "Kraftwerksstrategie ohne H2-ready-Klausel, Kapazitätsmarkt-"
            "Garantie für 2,3 GW/a Erdgas-Neubau 2026-2035 (Bestands-Lager-Programm) "
            "[SRC: BMWE-Kraftwerksstrategie 2024 Zielband 10 GW H2-ready bis "
            "2030 dient hier als Mengen-Anker; BESTAND ersetzt die H2-Klausel "
            "durch reine Erdgas-Genehmigung — 2,3 GW/a Spiegel-Zubau zur "
            "BMWE-Trajektorie]. Politische Konsequenz: ~27 Mt CO₂/a @ 2055 "
            "aus 49 GW Erdgas-Kraftwerken [Herleitung: 49 GW Kapazität × "
            "vlh_normal 3500 h × η_el 0,42 (gas_h2ready/erdgas_bestand-Mix) "
            "× CO₂-Faktor 0,202 t/MWh_th aus FUEL_INVENTORY → ≈ 35 Mt CO₂ "
            "th-Bedarf; nach Bilanz-Abgrenzung Strom-Sektor (~75 %) → "
            "~27 Mt CO₂/a; UBA-Methodik-Konvention] + 160 TWh Erdgas-Import-"
            "Abhängigkeit [Herleitung: Strom-Sektor-Bedarf BESTAND @ 2055 "
            "≈ 520 TWh × Restanteil Gas ~30 % / η_el 0,42 ≈ 160 TWh thermisch; "
            "deckt sich mit FUEL_INVENTORY.erdgas_import dauer_max-Trajektorie "
            "@ 2055 ~100 TWh + LNG ~60 TWh]. Strukturbefund: BESTAND "
            "erkauft Versorgung durch CO₂-Lock-in und Import-Abhängigkeit, "
            "nicht durch eine Versorgungs-Lücke."
        ),
    ),
    demand_cap_profile=_CAP_PROFILE_EE,
    source=_POLITIK_SOURCE_BASE,
    derivation=(
        "Dispatch: Bestandsfossile zuerst, dann nur Bestand-EE (PV + "
        "Onshore + Wasser + Bio — keine Offshore-Erweiterung, kein H2). "
        "fuel_constraints stop H2 → KKW/Gas-Pfade nicht möglich. "
        "Boost-Policy: LNG + Erdgas-Import — gleicher Stress-Plan wie "
        "WEITER-SO. Kohle-Phaseout bleibt KVBG-2038 "
        "(BESTAND zieht NICHT vor, weil Klimaambition fehlt); Erdgas-"
        "Neubau bleibt aktiv (Bestands-Lager-Programm) als politische Setzung der "
        "Pro-Erdgas-Fraktion."
    ),
)
