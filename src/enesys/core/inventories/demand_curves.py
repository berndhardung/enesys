"""Schema für `DEMAND_CURVES`.

Demand-Trajektorie pro Pfad.

`base_demand_twh` ist der Strom-Demand ohne Sektor-Kopplung (historisch
fortgeschrieben, AGEB-Basis). `elektrifizierung_zusatz_twh` ist
pfad-abhängig: WEITER-SO und BESTAND haben kleinen Zusatz (programmatisch
gebremst), EE- und KKW-Pfade vollen Zusatz aus Wärmepumpen, E-Mobilität
und H2-Industrie.

Demand-Asymmetrie zwischen BESTAND und EE-Pfaden ergibt sich aus der
Politik-Setzung, nicht aus einem globalen Skalierungs-Faktor.

Realgrad-Kopplung (Drei-Schichten-Architektur):
Politik-Soll-Plateau-Jahr ist 2045 (Klimaneutralität). Die effektive
Hochlauf-Rate skaliert mit `_SEKTOR_KOPPLUNG_REALGRAD` (separat von
path_policy.nep_realisierung_grad, weil Sektor-Kopplungs-Strom auch durch
KKW-Backup getragen werden kann). Damit ergibt sich pro Pfad ein
effektives Plateau-Jahr = 2026 + 19 / sektor_kopplung_realgrad.
Physikalisches Argument: Sektor-Kopplungs-Last (WP, E-Mob, Industrie-
Elektrifizierung) kann nicht schneller hochlaufen als verfügbarer Strom.
In EE-Pfaden begrenzt der EE-Hochlauf direkt; in KKW-Pfaden tragen
KKW-Backup + politischer EE-Anteil zusammen. Aktive Pfade teilen
daher den Sektor-Kopplungs-Realgrad 0,85. Ohne diese Kopplung wären
Demand-Soll und Erzeugungs-Realgrad entkoppelt — das erzeugte einen
artifiziellen 2045-Backup-Stress (KKW-H2-LCOE-Knick durch Erdgas-
`phaseout_2045` × Demand-Plateau am gleichen Datum).

"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

BaseDemandCallable = Callable[[int], float]  # (year) -> twh
ZusatzCallable = Callable[[int, str], float]  # (year, lager) -> twh


@dataclass(frozen=True)
class DemandCurve:
    """Schema für einen Eintrag in `DEMAND_CURVES`."""

    path_id: str
    base_demand_twh: BaseDemandCallable
    electrification_extra_twh: ZusatzCallable
    source: str = ""
    derivation: str = ""

    def __post_init__(self) -> None:
        if not self.source and not self.derivation:
            raise ValueError(
                f"DemandCurve {self.path_id!r} muss source oder derivation "
                f"tragen (Magic-Number-Verbot)."
            )


DEMAND_CURVES: dict[str, DemandCurve] = {}
"""Demand-Trajektorie pro Pfad. Plausi-Setzungen auf Basis AGEB-2024
+ path_model.py Sektor-Kopplungs-Konvention.

Demand-Asymmetrie zwischen Pfaden kommt aus
`elektrifizierung_zusatz_twh`, nicht aus einem Skalierungs-Faktor.
"""


# ---------------------------------------------------------------------------
# Befüllung pro Pfad
# ---------------------------------------------------------------------------


def _base_demand_twh(year: int) -> float:
    """Strom-Basis-Demand ohne Sektor-Kopplung. AGEB-2024-Stand
    ~470 TWh, leicht steigend mit BIP-Wachstum und Bevölkerungs-
    Stabilität.

    [SRC: AGEB-2024 Bruttostromverbrauch DE 2024 ≈ 470 TWh.
    Trend-Fortschreibung +0,3 %/a → ~500 TWh @ 2055.]
    """
    if year <= 2026:
        return 470.0
    if year >= 2055:
        return 500.0
    progress = (year - 2026) / (2055 - 2026)
    return 470.0 + progress * (500.0 - 470.0)


# Soll-Plateau-Werte pro Pfad (politische Setzung — Plateau-Wert in TWh).
# Aktive Pfade (EE/KKW): 350 (volle Sektor-Kopplung, AGEB+T45-Zerlegung
# WP 150 + E-Mob 120 + Industrie 80). WEITER-SO: 50 (BNetzA-Trend-Szenario
# 2022 passive Adoption). BESTAND: 20 (DIW BESTAND-Szenario 2023, aktiv-
# anti-elektrifizierend). Plateau-Wert bleibt politisches Soll;
# Hochlauf-Rate skaliert mit nep_realisierung_grad (Drei-Schichten-Logik).
_PLATEAU_TWH_PRO_PFAD: dict[str, float] = {
    "ee_gas": 350.0,
    "ee_h2": 350.0,
    "kkw_gas": 350.0,
    "kkw_h2": 350.0,
    "weiterso": 50.0,
    "bestand": 20.0,
}

# Politisches Soll-Plateau-Jahr: KSG-2021 Klimaneutralitäts-Frist.
_SOLL_PLATEAU_JAHR = 2045
_SOLL_HOCHLAUF_DAUER = _SOLL_PLATEAU_JAHR - 2026  # 19 Jahre Politik-Soll

# Sektor-Kopplungs-Hochlauf-Realgrad pro Pfad. Treibt die effektive
# Hochlauf-Rate der WP/E-Mob/Industrie-Strom-Last (= "Wie schnell kommt
# die zusätzliche Strom-Nachfrage aus der Sektor-Kopplung?").
#
# Konzeptuell GETRENNT von path_policy.nep_realisierung_grad, das die
# EE-Erzeugungs-Realisierung bezeichnet (= "Wie viel von der NEP-Soll-
# EE-Kapazität wird real gebaut?"). Aktive Pfade (EE/KKW) teilen sich
# den gleichen Sektor-Kopplungs-Hochlauf 0,85, weil:
#   - in EE-Pfaden trägt der EE-Hochlauf selbst die Sektor-Kopplungs-Last
#   - in KKW-Pfaden trägt KKW-Backup zusätzlich zum (politik-bedingt
#     niedrigeren) EE-Hochlauf die Last
# Beide Pfade haben damit die gleiche Sektor-Kopplungs-Trajektorie. Eine
# KKW-Politik darf nicht über den Demand-Hochlauf für ihre weniger
# ambitionierte EE-Ambition "doppelt bestraft" werden.
#
# WSO/BESTAND nutzen den path_policy.nep_realisierung_grad direkt, weil
# dort der EE-Hochlauf-Mangel reale Sektor-Kopplungs-Bremse ist
# (politisch gewollt: kein WP-Programm, kein E-Mob-Push).
#
# Invariante (geprüft in tests/architecture/test_demand_curves_realization_rate_sync.py):
#   _SEKTOR_KOPPLUNG_REALGRAD[pid] >= path_policy[pid].nep_realisierung_grad
# Der Demand-Hochlauf darf nicht langsamer sein als die EE-Erzeugung
# (sonst entstünde fossiler Backup-Bedarf trotz vorhandenem EE-Strom).
_SEKTOR_KOPPLUNG_REALGRAD: dict[str, float] = {
    "ee_gas": 0.85,
    "ee_h2": 0.85,
    "kkw_gas": 0.85,  # KKW-Backup trägt Sektor-Kopplung mit
    "kkw_h2": 0.85,  # KKW-Backup trägt Sektor-Kopplung mit
    "weiterso": 0.45,
    "bestand": 0.30,
}

# Lager-Multiplikator nur für aktive Pfade (EE/KKW). Spiegelt
# welt-spezifische Hochlauf-Geschwindigkeits-Annahmen: EE-Welt schneller
# in WP/E-Mob-Verbreitung, Atom/Bestand-Welt langsamer.
_LAGER_MULT_AKTIV: dict[str, float] = {
    "neutral_default": 1.0,
    "ee_optimistic": 1.1,
    "atom_optimistic": 0.9,
    "bestand_optimistic": 0.85,
}


def realgrad_hochlauf_skalierung(path_id: str, year: int) -> float:
    """Hochlauf-Fortschritt 0,0 (≤2026) → 1,0 (effektives Plateau-Jahr).

    Konsistent zur realgrad-gekoppelten `elektrifizierung_zusatz_twh`-Closure:
    Plateau-Jahr = 2026 + 19 / nep_realisierung_grad. Bei nep_grad < 1
    entsprechend späterer Plateau-Termin.

    Anwendungsfall: Sektor-Kopplungs-Peak-Demand-Berechnung im Winter-Stress
    (Wärmepumpen-Strom + E-Mob-Strom). Diese Skalierung gibt den Hochlauf-
    Fortschritt 0→1 zurück, parallel zum Jahres-Demand-Verlauf, damit Peak-
    Demand-GW und Jahres-Demand-TWh konsistent zur selben Pfad-Politik
    hochlaufen.

    Beispiele (effektives Plateau-Jahr):
      ee_gas/ee_h2 (0,85)       → 2048,4
      kkw_gas/kkw_h2 (0,85)     → 2048,4 (KKW-Backup trägt Sektor-Kopplung
                                   parallel zum reduzierten EE-Hochlauf)
      weiterso (0,45)           → 2068,2 (außerhalb LCOE-Fenster, politisch)
      bestand (0,30)            → 2089,3 (außerhalb LCOE-Fenster, politisch)
    """
    nep_grad = _SEKTOR_KOPPLUNG_REALGRAD[path_id]
    if year <= 2026 or nep_grad <= 0:
        return 0.0
    eff_jahre_zum_plateau = _SOLL_HOCHLAUF_DAUER / nep_grad
    progress = (year - 2026) / eff_jahre_zum_plateau
    return min(1.0, progress)


def _make_zusatz_realgrad_gekoppelt(
    plateau_twh: float, nep_grad: float, *, lager_sensitiv: bool
) -> Callable[[int, str], float]:
    """Factory: pfad-spezifische `elektrifizierung_zusatz_twh`-Closure.

    Drei-Schichten-Logik:
      Politik-Soll-Rate = plateau_twh / 19a (Politik-Soll-Plateau @ 2045)
      Effektive Rate    = Soll-Rate × nep_realisierung_grad
      Plateau-Jahr      = 2026 + eff_plateau / eff_rate (lager-abhängig)

    Bei nep_grad = 1,0 ergibt sich Plateau @ 2045 (= heutige Politik-Soll-
    Linie); bei nep_grad < 1,0 entsprechend späterer Plateau-Termin.

    `lager_sensitiv=True` für aktive Pfade (EE/KKW) — Welt-Modulator
    skaliert den Plateau-Wert. Für WEITER-SO/BESTAND ist die Demand bereits
    politisch gedämpft (50/20 TWh statt 350), eine zusätzliche Welt-
    Modulation wäre Double-Counting → False.

    Linearer Hochlauf bis Plateau erreicht, dann Plateau-Cap. Hochlauf-
    Rate ist pfad-konstant (``eff_rate``); Lager skaliert nur das Plateau.
    Höheres Plateau (ee_optimistic) → späteres Plateau-Jahr; niedrigeres
    Plateau (bestand_optimistic) → früheres Plateau-Jahr.
    """
    soll_rate = plateau_twh / _SOLL_HOCHLAUF_DAUER
    eff_rate = soll_rate * nep_grad

    def _zusatz(year: int, camp: str) -> float:
        if year <= 2026:
            return 0.0
        mult = _LAGER_MULT_AKTIV.get(camp, 1.0) if lager_sensitiv else 1.0
        eff_plateau = plateau_twh * mult
        if eff_rate <= 0:
            return 0.0
        return min(eff_plateau, (year - 2026) * eff_rate)

    return _zusatz


# Sektor-Kopplungs-Zerlegung — aktive Pfade (EE/KKW).
# [SRC: AGEB-2024 + BMWK-Langfrist-Szenarien T45-Strom 2023 zerlegen
# Sektor-Kopplungs-Zusatz @ 2045 in drei Blöcke:
# – Wärmepumpen-Strom: ~150 TWh (6 Mio. WP × 25 MWh/a-Mittel nach
#   BWP-Branchenstatistik 2024 + Hochlauf bis 2045);
# – E-Mob-Strom: ~120 TWh (45 Mio. BEVs × 2,5-3 MWh/a nach Ariadne-
#   Mobilitäts-Szenarien 2024);
# – Industrie-Direkt-Strom (ohne H2-Elektrolyse): ~80 TWh (Hochtemp-
#   Prozesse, DRI-Stahl, Wärme-Plasma); DIW »Strombedarf der Industrie« 2024.
# Summe ≈ 350 TWh; H2-Elektrolyse-Strom-Bedarf wird über die H2-Brennstoff-
# Trajektorie (FUEL_INVENTORY["h2_inland"].price_eur_mwh inklusive
# Elektrolyseur-CAPEX-Umlage) implizit erfasst.]
#
# WEITER-SO 50 TWh: BNetzA-Trend-Szenario 2022 passive Adoption ohne
# aktives WP-/E-Mob-Programm (~14 % des aktiven Zusatzes).
# BESTAND 20 TWh: DIW BESTAND-Szenario 2023, aktiv-anti-elektrifizierend
# (~6 % des aktiven Zusatzes — Premium-EVs + Restmodernisierung + Anlauf-DRI).


_DEMAND_SOURCE = (
    "AGEB-2024 Bruttostromverbrauch DE (Basis ~470 TWh). "
    "BMWK-Langfrist-Szenarien T45-Strom 2023 + Ariadne-Mobilitäts-"
    "Szenarien 2024 + BWP-Branchenstatistik 2024 + DIW-Studie "
    "»Strombedarf der Industrie« 2024 für aktive Sektor-Kopplungs-"
    "Komponenten (WP 150 + E-Mob 120 + Industrie 80 = 350 TWh @ 2045). "
    "BNetzA-Trend-Szenario 2022 für WEITER-SO-Vergleich. "
    "DIW-BESTAND-Szenario-Analyse 2023 für BESTAND-Restbestände. "
    "path_model.py Aktiv-Demand-Variante (Demand 2045 ~858 TWh). "
    "Demand-Asymmetrie kommt aus Politik-Profil, nicht aus globalem "
    "Skalierungs-Faktor."
)

_DEMAND_DERIVATION_BASE = (
    "base_demand linear 470→500 TWh ist Trend-Fortschreibung auf Basis "
    "AGEB-2024 mit +0,3 %/a (BIP × Effizienz-Kompensation-Gleichgewicht). "
    "Sektor-Kopplungs-Zusatz skaliert zwischen 20 TWh (BESTAND, "
    "Restbestände trotz Politik-Stop) und 350 TWh (aktive Pfade, "
    "BMWK-T45-Pfad konservativ gerundet)."
)


def _zusatz_for(path_id: str) -> Callable[[int, str], float]:
    """Realgrad-gekoppelte Zusatz-Closure für einen Pfad."""
    return _make_zusatz_realgrad_gekoppelt(
        _PLATEAU_TWH_PRO_PFAD[path_id],
        _SEKTOR_KOPPLUNG_REALGRAD[path_id],
        lager_sensitiv=path_id in ("ee_gas", "ee_h2", "kkw_gas", "kkw_h2"),
    )


def _realgrad_kopplung_suffix(path_id: str) -> str:
    nep = _SEKTOR_KOPPLUNG_REALGRAD[path_id]
    plateau_eff = 2026 + 19 / nep
    return f" [Realgrad-Kopplung: nep_grad={nep} → effektives Plateau-Jahr ≈ {plateau_eff:.1f}.]"


DEMAND_CURVES["ee_gas"] = DemandCurve(
    path_id="ee_gas",
    base_demand_twh=_base_demand_twh,
    electrification_extra_twh=_zusatz_for("ee_gas"),
    source=_DEMAND_SOURCE,
    derivation=_DEMAND_DERIVATION_BASE
    + " EE-GAS: volle Sektor-Kopplung (350 TWh-Plateau-Soll)."
    + _realgrad_kopplung_suffix("ee_gas"),
)

DEMAND_CURVES["ee_h2"] = DemandCurve(
    path_id="ee_h2",
    base_demand_twh=_base_demand_twh,
    electrification_extra_twh=_zusatz_for("ee_h2"),
    source=_DEMAND_SOURCE,
    derivation=_DEMAND_DERIVATION_BASE + " EE-H2: volle Sektor-Kopplung (350 TWh-Plateau-Soll). "
    "Zusätzliche H2-Industrie-Strom-Last wird über die H2-Brennstoff-"
    'Trajektorie erfasst (FUEL_INVENTORY["h2_inland"]-Preis-Komponente).'
    + _realgrad_kopplung_suffix("ee_h2"),
)

DEMAND_CURVES["kkw_gas"] = DemandCurve(
    path_id="kkw_gas",
    base_demand_twh=_base_demand_twh,
    electrification_extra_twh=_zusatz_for("kkw_gas"),
    source=_DEMAND_SOURCE,
    derivation=_DEMAND_DERIVATION_BASE
    + " KKW-GAS: volle Sektor-Kopplung (350 TWh-Plateau-Soll), KKW-Grundlast "
    "deckt Teil der Last." + _realgrad_kopplung_suffix("kkw_gas"),
)

DEMAND_CURVES["kkw_h2"] = DemandCurve(
    path_id="kkw_h2",
    base_demand_twh=_base_demand_twh,
    electrification_extra_twh=_zusatz_for("kkw_h2"),
    source=_DEMAND_SOURCE,
    derivation=_DEMAND_DERIVATION_BASE
    + " KKW-H2: volle Sektor-Kopplung (350 TWh-Plateau-Soll) + H2-Industrie-Last."
    + _realgrad_kopplung_suffix("kkw_h2"),
)

DEMAND_CURVES["weiterso"] = DemandCurve(
    path_id="weiterso",
    base_demand_twh=_base_demand_twh,
    electrification_extra_twh=_zusatz_for("weiterso"),
    source=_DEMAND_SOURCE,
    derivation=_DEMAND_DERIVATION_BASE
    + " WEITER-SO: gedämpfter Sektor-Kopplungs-Zusatz (50 TWh-Plateau-Soll). "
    "Drift-Pfad ohne aktive Wärmewende, ohne E-Mob-Push." + _realgrad_kopplung_suffix("weiterso"),
)

DEMAND_CURVES["bestand"] = DemandCurve(
    path_id="bestand",
    base_demand_twh=_base_demand_twh,
    electrification_extra_twh=_zusatz_for("bestand"),
    source=_DEMAND_SOURCE,
    derivation=_DEMAND_DERIVATION_BASE
    + " BESTAND: stark gedämpfter Zusatz (20 TWh-Plateau-Soll) — "
    "aktiv-anti-elektrifizierende Politik (kein WP-Programm, kein E-Mob-"
    "Push, keine EEG-Auktionen)." + _realgrad_kopplung_suffix("bestand"),
)
