"""
enesys — UI-State-Datenklassen und Eingabe-Parameter.

Dieses Modul stellt die Datenklassen bereit, die UI, Tests und Examples
als Eingabe-Container nutzen (Demand, ForwardCostParams, TimePathParams,
FlexibilityParams, GridStabilityParams, EeMixParams, WeiterSoParams,
BestandParams, LagerH2Params, PathResult). Die Mengen-Bilanz-Pipeline
(``compute_path``, Dispatch, LCOE) liegt in ``core.path_model``.

``_compute_demand_year`` und ``_DemandYear`` bleiben hier als
Demand-Trajektorie-Helfer für das Streamlit-Hochlauf-Cockpit.

Pfade:
    WEITER-SO  — Status quo, Kohle bis 2038, Erdgas wachsend
    EE-GAS     — 100 % EE + fossiles Gas-Backup
    EE-H2      — 100 % EE + H2-Saisonspeicher (CO2-frei)
    KKW-GAS    — EE + KKW (IBN 2036-2050 je Lager) + Bridge-Gas + fossiles Gas-Backup
    KKW-H2     — EE + KKW (IBN 2036-2050 je Lager) + Bridge-H2 + H2-Backup (CO2-frei)
    BESTAND    — Bestands-Lager-Pure-Play (Erdgas-Neubau + KVBG-Kohle)

Backup-Konvention: »Gas« heißt durchgängig fossiles Erdgas mit
CO2-Pönale. »H2« ist die CO2-freie Backup-Option.

Konvention: ct/kWh, GW, TWh, Mt CO2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ===========================================================================
# 1. EXPLIZITE ELEKTRIFIZIERUNGS-SCHICHT  (in core/demand.py)
# ===========================================================================
#
# Demand-Klassen leben in core/demand.py. Neue Aufrufer importieren
# direkt von dort.
from enesys.core.demand import Demand as Demand
from enesys.core.demand import HeatingParams as HeatingParams
from enesys.core.demand import IndustryParams as IndustryParams
from enesys.core.demand import MobilityParams as MobilityParams

# ===========================================================================
# MODELL-WEITE ZEITKONSTANTEN
# ===========================================================================
#
# Diese Konstanten werden an mehreren Stellen im Modell und in
# Begleitdokumenten referenziert. Sie hier zentral zu definieren
# ist drift-präventiv:
# wenn z.B. der EE-Kapazitäts-Basisjahr-Wert sich ändert (etwa bei
# einer Neukalibrierung gegen aktuelle BNETZA-MASTR-Daten), muss nur
# eine Stelle angepasst werden — nicht jede Funktion einzeln.
#
# Die Funktionen in TimePathParams (`nuclear_capacity`, `ee_capacity`,
# `battery_capacity`) referenzieren diese Konstanten, statt
# Magic-Numbers zu verwenden.

NUCLEAR_RAMPUP_TARGET_YEAR: int = 2050
"""Endjahr des linearen KKW-Hochlaufs.

Die kanonischen Lager-IBN-Jahre 2036–2050 leben in
`core.inventories.tech_inventory.KKW_EPR_APPROVAL_YEAR` plus
sqrt-Streckung nach Realgrad. Ab `NUCLEAR_RAMPUP_TARGET_YEAR` gilt
`nuclear_target_gw_2050` als konstanter Endwert.

**Reaktor-Aufteilung:** EPR und SMR sind in
`core.inventories.tech_inventory` als zwei getrennte Technologien
modelliert (`kkw_neubau_epr` mit CAPEX 14.000 €/kW und Plan-Bauzeit
7 a, `kkw_neubau_smr` mit CAPEX 11.500 €/kW und Plan-Bauzeit 5 a;
beide mit eigenem Approval-Jahr und sqrt-gestreckter Bauzeit). Die
24-GW-Zielkapazität wird mengenmäßig auf beide Tech-Klassen verteilt
(siehe `_kkw_neubau_epr_max_zubau_gw_per_year` und das SMR-Pendant);
die hier gepflegte Konstante steuert nur das Hochlauf-Endjahr.

**Reaktor-Tempo:** Eine 24-GW-Flotte aus 6 Großreaktoren à 4 GW über
8 Jahre Hochlauf entspricht einem Inbetriebnahme-Tempo von etwa einem
Reaktor pro 1,3 Jahre. Frankreich hat sein historisches Aufbau-Tempo
1980-1990 mit einem Reaktor pro Jahr erreicht, China 2010-2020
ähnliche Raten. Eine deutsche Realisierung ohne bestehende
KKW-Lieferkette setzt eine entsprechende industriepolitische
Mobilisierung voraus.

**Replacement-Logik:** Reaktor-Lifetime im Modell 60 Jahre (siehe
`nuclear_lifetime` in `ForwardCostParams`). Erste Reaktoren müssten
frühestens 2096+ ersetzt werden — außerhalb des Modell-Horizonts
2055. Replacement-Annahmen sind nicht parametrisiert; das
Steady-State 2055 nimmt an, dass die 24-GW-Flotte zwischen 2050 und
2055 unverändert läuft.
"""

EE_CAPACITY_BASE_YEAR: int = 2024
"""Basis-Jahr für die EE-Kapazitäts-Hochrechnung.

Die installierten Kapazitäten in `ee_capacity()` (PV 95 GW, Wind
onshore 62 GW, Wind offshore 9 GW) sind Stand Ende 2024 nach
BNETZA-MASTR. Der Hochlauf in `ee_capacity()` rechnet Zubau
linear ab diesem Basisjahr.
"""

BATTERY_ADDITIONS_BASE_YEAR: int = 2026
"""Basis-Jahr für den Batterie-Zubau-Pfad.

In `battery_capacity()` startet der exponentielle Hochlauf in
diesem Jahr. Der 2037-Zwischenstützwert (`battery_target_gw_2037`)
wird aus diesem Basisjahr extrapoliert.
"""

NUCLEAR_POLITICAL_DECISION_YEAR: int = 2026
"""Hypothetisches Jahr einer politischen KKW-Wieder-Einstiegs-Entscheidung.

Das Modell nimmt für KKW-Pfade an, dass eine politische Entscheidung
**heute** (2026) getroffen würde. `nuclear_first_unit_year` ist daraus
abgeleitet als `KKW_POLITISCHE_ENTSCHEIDUNG_JAHR + KKW_PLANUNG_JAHRE +
nuclear_buildout_years`.
"""

NUCLEAR_PLANNING_YEARS: int = 6
"""Planungs-/Genehmigungs-Jahre vor Baubeginn.

Zeit zwischen politischer Entscheidung und tatsächlichem Baubeginn:
Standortwahl, Genehmigungsverfahren, KTA-Update, Brennstoff-Lieferketten,
Operator-Aufstellung. Default 6 Jahre — HPC brauchte zwischen
Ankündigung 2010 und Baubeginn 2018 acht Jahre, in DE ohne KKW-Liefer-
ketten + Wieder-Einstiegs-KTA realistisch eher 6-8.

Zusammen mit `nuclear_buildout_years` (Default 12) ergibt sich
`nuclear_first_unit_year = 2026 + 6 + 12 = 2044`.
"""

# ===========================================================================
# 2. ZEITACHSE: VERFÜGBARKEITSPROFILE
# ===========================================================================


# fmt: off
# Inline-Kommentar-Tags ([SRC: ...] / [CALIBRATED] / [ASSUMPTION: ...] etc.)
# müssen auf derselben Zeile stehen wie die Felddefinition, damit
# core/source_trace.py:DEFAULT_FIELD_PATTERN sie erkennt. ruff format würde
# Zeilen über 100 Zeichen umbrechen und damit den Validator brechen.
# Die Datei ist daher format-geschützt; ruff check (Lint) gilt weiterhin.

# ===========================================================================
# H₂-Lager-Parameter als Sub-Dataclass
# ===========================================================================
#
#
# Drei Lager-Welten für die NWS-H₂-Hochlauf-Trajektorie und die
# zugehörige Industrie-H₂-Konkurrenz. Eingebettet in TimePathParams
# als Sub-Objekt `lager_h2`, analog zum `kkw_realisierung_grad`-Muster
# (eigenständiger benannter Hebel mit klarer Lager-Range).
#
# Die drei Trajektorien sind nicht symmetrisch um den NWS-Plan, sondern
# tragen drei methodisch eigenständige Welt-Bilder:
#
# - ee_optimistic: NWS-Plan vollständig erfüllt, Importe wie spezifiziert.
#   EWI-2026-Optimum, BMWK-NWS-2023-Pfad-A.
# - neutral: NWS-Plan teilweise erfüllt; Verzögerungen in Hochlauf-Phase
#   2030-2035, Plateau-Erreichen ~5 Jahre später als Plan. Konservativer
#   Mittelpunkt nach Plausi-Check 2.
# - skeptisch: substantielle NWS-Lücke; Pfade entsprechen DIW-2026 und
#   BNetzA-H2-Verstromung-2024-Pessimum. KKW-Pfade laufen 30 Jahre
#   strukturell ohne H₂-Backup.
#
# Industrie-Trajektorien sind lager-abhängig: in
# skeptischer Welt verzögert auch der Industrie-Hochlauf, weil DRI
# und Chemie auf H₂-Preis und -Verfügbarkeit reagieren. Skalierung:
# skeptisch ~70 % von neutral; ee_optimistic ~110 % von neutral.
#
# Quellen-Tags pro Stützstelle: siehe `docs/SOURCES.md`.

@dataclass
class CampH2Params:
    """H₂-Lager-Parameter für Bridge-Phase und Backup-Verfügbarkeit.

    Drei Lager-Welten (ee_optimistic / neutral / skeptisch) für die
    NWS-Hochlauf-Trajektorie und die zugehörige Industrie-H₂-Konkurrenz.
    Default ist »neutral« — Mittelpunkt aus BNetzA-/DENA-/DIW-Bandbreite
    mit ~5 J Plateau-Verzögerung gegenüber dem NWS-Plan.

    Verwendung:
        lager = LagerH2Params(h2_lager="skeptisch")
        tp = TimePathParams(lager_h2=lager)

    Mechanik:
        Die Methode `time_p.h2_brennstoff_capacity(year)` (siehe
        TimePathParams) liest aus `lager_h2.nws_active()` die aktive
        NWS-Trajektorie und liefert TWh-Mengen. Die LCOE-TWh-Bilanz mit
        Industrie-Konkurrenz baut darauf auf.

    BESTAND-Kopplung:
        Der BESTAND-Pfad nutzt strukturell `h2_lager="skeptisch"`,
        unabhängig vom Default des Param-Objekts (BESTAND hat keine
        eigene H₂-strategische Position). Die Kopplung erfolgt im
        BESTAND-Pfad-Compute, nicht in dieser Klasse.

    Erweiterbarkeit:
        Folge-Felder (`backup_demand_twh` als Konstante, und
        `h2_avail_share_stresstest` hartcodiert auf 1,0) werden bewusst
        nicht als Felder geführt. Nur Lager-spezifische Trajektorien
        leben hier.

    [SRC: docs/SOURCES.md]
    """
    h2_camp: str = "neutral"  # [SRC: BMWK-H2-STRATEGIE-2023, DIW-H2-2026, EWI-2024 — drei-Lager-Mittelpunkt nach Plausi-Check 2]
    """Aktive Lager-Welt: »ee_optimistic«, »neutral« (Default), »skeptisch«.

    Wirkt als Schalter über `nws_active()` und `industrie_active()`.
    BESTAND-Pfad überschreibt diesen Wert intern auf »skeptisch«.

    Range: drei diskrete Werte (kein Slider, sondern Lager-Wahl).
    """

    # NWS-Stützstellen pro Lager (TWh H₂-Brennstoff-Kapazität).
    # Quellen-Tags pro Stützstelle in docs/SOURCES.md.
    nws_pivots_ee_optimistic: dict = field(default_factory=lambda: {
        2026: 20.0,   # [SRC: BMWK-NWS-2023-Pfad-A, Hochlauf-Anfang]
        2030: 80.0,   # [SRC: BMWK-NWS-2023, NWS-Plan 5 GW Elektrolyse + Importe]
        2035: 150.0,  # [SRC: BMWK-NWS-2023, 10 GW Elektrolyse-Ziel + Voll-Hochlauf]
        2040: 220.0,  # [SRC: EWI-2026 Optimum-Variante]
        2045: 280.0,  # [ASSUMPTION: linear-EWI-Pfad-A]
        2050: 320.0,  # [ASSUMPTION: Plateau bei klimaneutraler Vollversorgung]
        2055: 350.0,  # [ASSUMPTION: leichter Wachstum bis Steady-State]
    })
    """Optimistisches Lager: NWS-Plan vollständig erfüllt, EWI-Pfad-A.

    Quellen: BMWK-NWS-2023, EWI-2026, BMWK-Importstrategie-2024.
    Quellen-Tags pro Stützstelle in `docs/SOURCES.md`.
    """

    nws_pivots_neutral: dict = field(default_factory=lambda: {
        2026: 15.0,   # [SRC: BNetzA-H2-Verstromung-2024 mittlere Erwartung]
        2030: 60.0,   # [CALIBRATED: NWS-Plan minus 25 % realistische Verzögerung]
        2035: 120.0,  # [SRC: DENA-H2-2025-OKT mittlere Variante]
        2040: 180.0,  # [SRC: DIW-2026 mittlere Erwartung]
        2045: 240.0,  # [ASSUMPTION: linear nach DENA-DIW-Mittel]
        2050: 280.0,  # [ASSUMPTION: Plateau-Erreichen ~5 J später als Plan]
        2055: 310.0,  # [ASSUMPTION: leichter Wachstum bis Steady-State]
    })
    """Neutrales Lager: NWS teilweise erfüllt, Worst-Case-robuster Mittelpunkt.

    Quellen: BNetzA-H2-Verstromung-2024, DENA-H2-2025-OKT, DIW-2026.
    Plateau-Erreichen ~5 Jahre später als optimistischer NWS-Plan.
    Quellen-Tags pro Stützstelle in `docs/SOURCES.md`.
    """

    nws_pivots_skeptical: dict = field(default_factory=lambda: {
        2026: 10.0,   # [SRC: BNetzA-H2-Verstromung-2024 Pessimum]
        2030: 30.0,   # [SRC: DIW-2026 skeptisch (NWS-Lücke 50 %)]
        2035: 70.0,   # [SRC: EWI-2026 Pessimum-Variante]
        2040: 110.0,  # [ASSUMPTION: linear-NWS-Lücke fortgesetzt]
        2045: 150.0,  # [ASSUMPTION: Plateau ~50 % unter Plan]
        2050: 180.0,  # [ASSUMPTION: strukturelle H2-Lücke bis 2050]
        2055: 200.0,  # [ASSUMPTION: leichter Wachstum, kein Voll-Hochlauf]
    })
    """Skeptisches Lager: substantielle NWS-Lücke, DIW-2026/BNetzA-Pessimum.

    Quellen: DIW-2026, BNetzA-H2-Verstromung-2024-Pessimum, EWI-2026-Pessimum.
    Strukturelle Lücke bis 2050 (~50 % unter NWS-Plan). KKW-Pfade laufen
    in dieser Welt 30 J ohne signifikanten H₂-Backup.
    Quellen-Tags pro Stützstelle in `docs/SOURCES.md`.
    """

    # Industrie-Stützstellen pro Lager (lager-abhängig).
    # Skalierung: skeptisch ~70 % von neutral; ee_optimistic ~110 %.
    # Begründung: DRI-Stahl und Chemie reagieren auf H₂-Preis/-Verfügbarkeit;
    # in skeptischer NWS-Welt verzögert sich auch der Industrie-Hochlauf.
    industry_pivots_ee_optimistic: dict = field(default_factory=lambda: {
        2026: 33.0,   # [CALIBRATED: 110 % der neutralen Industrie-Mengen]
        2030: 88.0,   # [CALIBRATED: NWS-Industrie-Plan-A optimistisch]
        2035: 132.0,  # [CALIBRATED: 110 % von neutral, EWI-Pfad-A]
        2040: 165.0,  # [CALIBRATED: DRI-Stahl + Chemie voll-Hochlauf]
        2045: 187.0,  # [CALIBRATED: Industrie-Plateau hochgesetzt]
        2050: 198.0,  # [CALIBRATED: nahe Sättigung]
        2055: 204.0,  # [CALIBRATED: Sättigung]
    })
    """Industrie-H₂ in optimistischer NWS-Welt (~110 % von neutral).

    Industrie zieht voll auf, weil H₂ verfügbar und preislich attraktiv
    ist. Quellen: BMWK-NWS-2023-Industrie-Pfad-A, EWI-2026, BCG-2024
    (DRI-Stahl-Hochlauf).
    """

    industry_pivots_neutral: dict = field(default_factory=lambda: {
        2026: 30.0,   # [SRC: BMWK-NWS-2023 Industrie-Plan-Mittel]
        2030: 80.0,   # [SRC: BCG-2024 DRI-Hochlauf-Mittelfall]
        2035: 120.0,  # [SRC: BMWK-NWS-2023 Industrie-2035-Soll]
        2040: 150.0,  # [SRC: DENA-H2-2025-OKT mittlere Industrie-Variante]
        2045: 170.0,  # [ASSUMPTION: linear DRI/Chemie-Hochlauf]
        2050: 180.0,  # [ASSUMPTION: nahe Sättigung]
        2055: 185.0,  # [ASSUMPTION: Sättigung]
    })
    """Industrie-H₂ in neutraler NWS-Welt (BMWK-NWS-2023 Mittel).

    Quellen: BMWK-NWS-2023-Industrie, BCG-2024-DRI-Hochlauf,
    DENA-H2-2025-OKT.
    """

    industry_pivots_skeptical: dict = field(default_factory=lambda: {
        2026: 21.0,   # [CALIBRATED: 70 % der neutralen Industrie-Mengen]
        2030: 56.0,   # [CALIBRATED: DRI-Verzögerung wegen H₂-Knappheit]
        2035: 84.0,   # [CALIBRATED: Industrie wartet auf billigen H₂]
        2040: 105.0,  # [CALIBRATED: 70 % von neutral, DIW-2026 Industrie]
        2045: 119.0,  # [CALIBRATED: anhaltende H₂-Knappheit drückt Hochlauf]
        2050: 126.0,  # [CALIBRATED: Plateau auf reduziertem Niveau]
        2055: 130.0,  # [CALIBRATED: schleichende Sättigung]
    })
    """Industrie-H₂ in skeptischer NWS-Welt (~70 % von neutral).

    Industrie reagiert auf H₂-Preis/-Verfügbarkeit
    (»DRI wartet auf billigen H₂«). In skeptischer NWS-Welt verzögert
    sich der Industrie-Hochlauf strukturell. Quellen: DIW-2026
    (skeptisch), BNetzA-H2-Verstromung-2024 (Pessimum-Annahmen).
    """

    def _validate_camp(self, camp: str) -> None:
        """Hilfs-Methode: Prüft, dass `lager` ein zulässiger Wert ist."""
        if camp not in ("ee_optimistic", "neutral", "skeptisch"):
            raise ValueError(
                f"Ungültiger h2_lager-Wert: {camp!r}. "
                "Erlaubt: 'ee_optimistic', 'neutral', 'skeptisch'."
            )

    def nws_active(self, camp: str | None = None) -> dict:
        """Liefert die aktive NWS-Stützstellen-Trajektorie.

        Args:
            lager: Optionaler Override. Wenn None, wird `self.h2_lager`
                verwendet. BESTAND-Pfad ruft mit `lager="skeptisch"`
                auf, um seine strukturelle Lager-Bindung durchzusetzen.

        Returns:
            Stützstellen-Dict {Jahr: TWh_H2_Brennstoff}.
        """
        eff = camp if camp is not None else self.h2_camp
        self._validate_camp(eff)
        if eff == "ee_optimistic":
            return self.nws_pivots_ee_optimistic
        if eff == "neutral":
            return self.nws_pivots_neutral
        return self.nws_pivots_skeptical

    def industry_active(self, camp: str | None = None) -> dict:
        """Liefert die aktive Industrie-H₂-Stützstellen-Trajektorie.

        Args:
            lager: Optionaler Override (wie `nws_active`). BESTAND-Pfad
                ruft mit `lager="skeptisch"` auf.

        Returns:
            Stützstellen-Dict {Jahr: TWh_H2_Industrie}.
        """
        eff = camp if camp is not None else self.h2_camp
        self._validate_camp(eff)
        if eff == "ee_optimistic":
            return self.industry_pivots_ee_optimistic
        if eff == "neutral":
            return self.industry_pivots_neutral
        return self.industry_pivots_skeptical


@dataclass
class TimePathParams:
    """Bauzeit, Zubau-Raten, Verfügbarkeit pro Jahr"""
    # KKW Neubau in DE (hypothetisch)
    nuclear_first_unit_year: int = 2044       # 2026 + KKW_PLANUNG_JAHRE (6) + nuclear_buildout_years (12) = 2044 [CALIBRATED: gegen EDF-HPC und COURDESCOMPTES-FLAM]
    nuclear_buildout_years: int = 12          # Plan-Bauzeit pro Anlage  [CALIBRATED: optimistische Plan-LCOE-Annahme; reale Bauzeit Hinkley/Flamanville: 13-17 Jahre]
    nuclear_target_gw_2050: float = 24.0      # Plan-Zielkapazität bei KKW_HOCHLAUF_ZIELJAHR (2050)  [ASSUMPTION: Modell-Setzung; nuclear_capacity() macht linearen Ramp von effective_first_unit_year bis effective_endyear]

    # KKW-Realisierungsgrad als symmetrisches Pendant zu
    # nep_realisierung_grad. Default 0,40 ist Empirisch-Mittel der
    # westlichen FOAK-Reaktoren (OL3 18 J, Flamanville 17 J, Hinkley
    # 13 J Plan / EDF-2024-Stand 17+ J real, Vogtle 14-15 J), mit
    # moderater Lernkurven-Korrektur für DE-Kontext (etablierte
    # Lieferketten via FR/UK).
    #
    # Mechanik: sqrt-symmetrische Aufteilung auf zwei multiplikative
    # Achsen (Bauzeit-Streckung × Trefferquoten-Reduktion).
    # Bei realgrad=1,0: Plan-Bauzeit 12 J + Plan-Zielkapa 24 GW (Lager-Optimum).
    # Bei realgrad=0,40: Bauzeit 19 J + Zielkapa 15,2 GW.
    #
    # Quellen: WNA Reactor Database 2025, OECD-NEA REDCOST 2020,
    #   Helm-Oxford 2024, TVO/EDF/Georgia-Power Annual Reports 2023-2024.
    nuclear_realization_rate: float = 0.40  # [SRC: WNA-2024, OECD-NEA-2019, EDF-HPC, IWR-FR-2025]
    """KKW-Realisierungsgrad (Output-Verhältnis: realisiert/geplant).

    Default 0,40: Empirisch-Mittel westlicher FOAK-Reaktoren mit moderater
    Lernkurven-Korrektur. Wirkt multiplikativ via sqrt auf Bauzeit
    und Zielkapazität.

    Lager-Range: 0,2 (Hinkley-Realität ohne Intervention) - 1,0 (KKW-Lager-Optimum,
    Plan-Bauzeit erfüllt mit FOAK-Lernkurven-Kompensation).

    [SRC: WNA-2025, OECD-NEA-REDCOST-2020, Helm-Oxford-2024]
    """

    # EE Zubau
    pv_additions_gw_per_year: float = 18.0       # 2024 Niveau  [SRC: BNETZA-MASTR-2024 — installierte PV-Leistung 2024]
    wind_onshore_additions_gw_per_year: float = 8.0  # [SRC: EEG-2023 — Ausschreibungsvolumen 2030 entspricht ~8 GW/a]
    wind_offshore_additions_gw_per_year: float = 4.0  # [SRC: EEG-2023 — Offshore-Ausbau-Pfad nach WindSeeG]

    # Batteriespeicher
    battery_additions_gw_per_year_2026: float = 8.0  # [SRC: BNEF-2025-ESS — Großspeicher-Zubau-Erwartung]
    battery_additions_growth_pct: float = 0.20    # Wachstumsrate  [CALIBRATED: BNEF-2025-ESS Markttrend]
    battery_target_gw_2037: float = 72.0     # [SRC: MODO-2025 — Inertia-Bedarf Studie]

    # H2-Backup
    h2_capacity_target_gw_2035: float = 20.0  # [SRC: BMWK-H2-STRATEGIE-2023 — 20 GW H2-Backup-Ziel 2035]
    h2_capacity_target_gw_2045: float = 50.0  # [ASSUMPTION: linearer Hochlauf vom 2035-Ziel zur klimaneutralen Vollversorgung]

    # H₂-Lager-Sub-Parameter.
    # Drei Lager-Welten für NWS-Hochlauf-Trajektorie und
    # Industrie-H₂-Konkurrenz. Default »neutral« = Mittelpunkt aus
    # BNetzA-/DENA-/DIW-Bandbreite. Siehe Klasse LagerH2Params oben.
    camp_h2: CampH2Params = field(default_factory=CampH2Params)  #

    def _nuclear_effective_buildout_years(self) -> float:
        """Effektive KKW-Bauzeit nach Realisierungsgrad-Streckung.

        sqrt-symmetrische Aufteilung: jede Achse (Bauzeit, Zielkapa) trägt
        sqrt(realgrad) bei. Bei realgrad=1,0: Plan-Bauzeit. Bei realgrad=0,40:
        Bauzeit gestreckt auf 12/sqrt(0,40) = 19 J.
        """
        # Clamp gegen ZeroDivisionError bei programmatischen Aufrufern, die
        # nuclear_realization_rate=0.0 setzen (UI clamped via V3_SLIDER_SPEC).
        return self.nuclear_buildout_years / math.sqrt(max(1e-9, self.nuclear_realization_rate))

    def _nuclear_effective_first_unit_year(self) -> int:
        """Effektives Inbetriebnahme-Jahr des ersten KKW (UI-State-Pfad).

        Plan-Erstinbetriebnahme + Bauzeit-Streckungs-Differenz. Die
        kanonischen Lager-IBN-Jahre laufen über
        ``tech_inventory._kkw_epr_startjahr(camp)``; diese Methode
        dient UI-State-Berechnungen und Slider-Anzeigen.
        """
        delta = int(round(self._nuclear_effective_buildout_years() - self.nuclear_buildout_years))
        return self.nuclear_first_unit_year + delta

    def _nuclear_effective_target_gw(self) -> float:
        """Effektive Ziel-Kapazität nach Trefferquoten-Reduktion.

        sqrt-symmetrische Aufteilung. Bei realgrad=1,0: Plan-Zielkapa
        (24 GW). Bei realgrad=0,40: 24 × sqrt(0,40) = 15,2 GW.
        """
        return self.nuclear_target_gw_2050 * math.sqrt(self.nuclear_realization_rate)

    def _nuclear_effective_endyear(self) -> int:
        """Effektives Hochlauf-Endjahr.

        Plan-Endjahr (KKW_HOCHLAUF_ZIELJAHR=2050) + Bauzeit-Streckungs-Differenz,
        weil der Hochlauf der Folge-Reaktoren genauso gestreckt wird wie der
        des ersten. Bei realgrad=1,0: 2050. Bei realgrad=0,40: 2050+(19-12)=2057.
        """
        delta = int(round(self._nuclear_effective_buildout_years() - self.nuclear_buildout_years))
        return NUCLEAR_RAMPUP_TARGET_YEAR + delta

    def nuclear_capacity(self, year: int) -> float:
        """KKW-Kapazität in GW im Jahr `year` (für KKW-Pfade).

        Berücksichtigt kkw_realisierung_grad mittels sqrt-symmetrischer
        Aufteilung auf Bauzeit-Streckung und Trefferquoten-Reduktion. Bei
        kkw_realisierung_grad=1,0 (KKW-Lager-Optimum) wird der Plan-Default
        wiederhergestellt.
        """
        eff_first = self._nuclear_effective_first_unit_year()
        eff_end = self._nuclear_effective_endyear()
        eff_target = self._nuclear_effective_target_gw()

        if year < eff_first:
            return 0.0
        if year >= eff_end:
            return eff_target
        # Linear ramp zwischen effektivem first_unit und effektivem endyear
        progress = (year - eff_first) / (eff_end - eff_first)
        return eff_target * progress

    def ee_capacity(self, year: int, base_year: int = EE_CAPACITY_BASE_YEAR) -> dict[str, float]:
        """EE-Kapazität in GW im Jahr `year`"""
        years_passed = max(0, year - base_year)
        return {
            "pv": 95.0 + self.pv_additions_gw_per_year * years_passed,
            "wind_onshore": 62.0 + self.wind_onshore_additions_gw_per_year * years_passed,
            "wind_offshore": 9.0 + self.wind_offshore_additions_gw_per_year * years_passed,
        }

    def battery_capacity(self, year: int, base_year: int = BATTERY_ADDITIONS_BASE_YEAR) -> float:
        if year < base_year:
            return 1.0
        years_passed = year - base_year
        cap = self.battery_additions_gw_per_year_2026
        for _ in range(years_passed):
            cap = cap * (1 + self.battery_additions_growth_pct)
        return min(cap * years_passed, self.battery_target_gw_2037 * 1.5)

    # -------------------------------------------------------------------
    # Bridge-Phase Time-Paths (Aktionen C.1-C.4 aus Bridge-Phase-Modell)
    #
    # Drei Kapazitäts-Klassen + Kohle-Bestand werden als zeit-abhängige
    # Stützstellen-Tabellen mit linearer Interpolation modelliert.
    # Quellenbelegung in den Methoden-Docstrings.
    # -------------------------------------------------------------------

    @staticmethod
    def _interp(year: int, stuetzstellen: dict[int, float]) -> float:
        """Lineare Interpolation zwischen Jahres-Stützstellen.

        Vor erster Stützstelle: erster Wert. Nach letzter: letzter Wert.
        """
        years = sorted(stuetzstellen.keys())
        if year <= years[0]:
            return stuetzstellen[years[0]]
        if year >= years[-1]:
            return stuetzstellen[years[-1]]
        for i in range(len(years) - 1):
            y0, y1 = years[i], years[i + 1]
            if y0 <= year <= y1:
                v0, v1 = stuetzstellen[y0], stuetzstellen[y1]
                t = (year - y0) / (y1 - y0)
                return v0 + t * (v1 - v0)
        return stuetzstellen[years[-1]]  # unreachable

    def coal_existing_capacity(
        self,
        year: int,
        *,
        scenario: str,
    ) -> float:
        """Kohle-Bestand in GW (Steinkohle + Braunkohle).

        Time-Path Kohle-Bestand, drei Szenarien:

        - ``"weiterso"`` — gesetzlicher KVBG-Pfad bis 2038. Stützstellen
          33 / 25 / 10 / 0 GW für 2026 / 2030 / 2035 / 2038.
        - ``"bestand"`` — KVBG-Pfad bis 2038, identisch zu ``"weiterso"``.
          Bestands-Lager kann KVBG-Bundesgesetz nicht parlamentarisch
          rückrollen, folgt also demselben gesetzlichen Pfad.
        - ``"active"`` — aktive Pfade (EE-/KKW-Programme) mit Mitte-Wert
          2034. Stützstellen 33 / 22 / 11 / 0 GW für 2026 / 2030 / 2032 /
          2034. Mitte-Wert als gewichteter Durchschnitt aus Rheinisches
          Revier 2030 und Lausitz/Mitteldeutsch 2038, plus markt-
          getriebener Steinkohle-Auslauf 2030-2032 — Herleitung in
          ``docs/methodik/bridge_phase_parameters.md``.

        Quellen: BNetzA-Monitoring 2024 (Stand Ende 2024: 16 GW Stein-
        + 17 GW Braunkohle = 33 GW), KVBG (BGBl. I S. 1818, 8.8.2020,
        § 4 Abs. 1: Zielniveau 2038 = 0 GW), Koalitionsvertrag CDU/CSU/SPD
        April 2025 (bestätigt KVBG-2038 explizit), Bundesregierung
        24.12.2022 (vorgezogener Ausstieg Rheinisches Revier 2030).

        """
        if scenario == "weiterso" or scenario == "bestand":
            # KVBG-Pfad: 33 → 0 GW über 2026-2038
            return self._interp(year, {
                2026: 33.0, 2030: 25.0, 2035: 10.0, 2038: 0.0, 2050: 0.0,
            })
        if scenario == "active":
            # Mitte-Wert: gewichteter Durchschnitt 2034
            return self._interp(year, {
                2026: 33.0, 2030: 22.0, 2032: 11.0, 2034: 0.0, 2050: 0.0,
            })
        raise ValueError(
            f"Unbekanntes scenario={scenario!r}. "
            f"Erlaubt: 'weiterso', 'bestand', 'active'."
        )

    def gas_existing_capacity(self, year: int) -> float:
        """Erdgas-Bestand in GW. Identisch für alle fünf Pfade.

        Aktion C.2: Erdgas-Kraftwerke werden in EE-Pfaden nicht
        zwangsweise abgeschaltet, sondern laufen mit niedrigeren
        Volllaststunden als Backup. Bestand reduziert sich durch
        Alters-Stilllegung.

        Quelle: BNetzA-Monitoring 2024 (Stand Ende 2024: ~31 GW).
        """
        return self._interp(year, {
            2026: 31.0, 2030: 30.0, 2035: 28.0, 2040: 25.0,
            2045: 22.0, 2050: 18.0,
        })

    def h2ready_capacity(self, year: int) -> float:
        """H2-ready GuD-Neubau in GW (Kraftwerksstrategie 2026).

        Aktion C.3 + C.5c: Identisch in allen vier Nicht-WEITER-SO-
        Pfaden. Kraftwerksstrategie 2026 ist eine politische Setzung,
        sie haengt nicht von der Pfad-Wahl ab. WEITER-SO: 0 GW Neubau.

        2030: 6 GW = Kraftwerksstrategie minus realistische Verzoegerung
        (KWBG-Plan: 12 GW bis 2034, erste Inbetriebnahme 2030, letzte 2034).

        Quelle: BMWE Kraftwerksstrategie 2026 (Eckpunkte Januar 2026).
        """
        return self._interp(year, {
            2026: 0.0, 2030: 6.0, 2035: 12.0, 2040: 16.0,
            2045: 20.0, 2050: 22.0,
        })

    def h2_fuel_capacity(self, year: int) -> float:
        """Backup-faehige H2-Leistung in GW (was *tatsaechlich* mit H2 fahren kann).

        Aktion C.4: Begrenzt durch Elektrolyse-Kapazitaet, H2-Importe und
        H2-Speicher. Pro 1 GW H2-Kraftwerk in 10-taegiger Dunkelflaute
        (240 h Volllast) bei 55-58 % Wirkungsgrad ~ 0,4 TWh H2-Reserve.

        Quellen:
        - Nationale Wasserstoff-Strategie Update 2023 (BMWK):
          Elektrolyse 5 GW bis 2030, 10 GW bis 2035
        - Wasserstoff-Importstrategie 2024 (BMWK): signifikante Importe
          ab 2030, Voll-Hochlauf 2035-2040
        - Wasserstoff-Kernnetz BNetzA 2024: ~9.700 km bis 2032

        2030: 3 GW = erste 5 GW Elektrolyse abzueglich Industrie-Konkurrenz.

        Die GW-Trajektorie ist lager-unabhängig. Die Lager-Architektur
        (`lager_h2`) liefert TWh-Mengen für die LCOE-Bilanz; diese
        Funktion bedient die GW-Schwellen-Logik.
        """
        return self._interp(year, {
            2026: 0.5, 2030: 3.0, 2035: 10.0, 2040: 20.0,
            2045: 30.0, 2050: 40.0,
        })

    def nws_fuel_twh(
        self,
        year: int,
        *,
        camp_override: str | None = None,
    ) -> float:
        """H₂-Brennstoff-Mengen in TWh nach aktiver Lager-Trajektorie.

        Liest aus `self.lager_h2.nws_active(lager_override)` die aktive
        NWS-Stützstellen-Trajektorie und interpoliert linear für `year`.

        Diese Funktion ist die **Lager-empfindliche** Schwester-Methode
        zu `h2_brennstoff_capacity` (die GW-basiert und lager-unabhängig
        bleibt). Sie geht in die TWh-Bilanz des LCOE ein, um die
        Industrie-Konkurrenz korrekt abzuziehen und das Doppelnarrativ-
        Argument LCOE-vs-CO₂ zu stützen.

        Args:
            year: Stützjahr.
            lager_override: Optional. Wenn gesetzt, wird statt
                `self.lager_h2.h2_lager` das übergebene Lager verwendet.
                Verwendung: BESTAND-Pfad ruft mit
                `lager_override="skeptisch"`.

        Returns:
            TWh H₂-Brennstoff-Mengen für das aktive Lager im Jahr `year`.

        Quellen pro Stützstelle: siehe `docs/SOURCES.md`.
        """
        stuetzstellen = self.camp_h2.nws_active(camp_override)
        return self._interp(year, stuetzstellen)

    def industry_h2_twh(
        self,
        year: int,
        *,
        camp_override: str | None = None,
    ) -> float:
        """Industrie-H₂-Bedarf in TWh nach aktiver Lager-Trajektorie.

        Schwester-Methode zu `nws_brennstoff_twh`: liefert die
        Industrie-H₂-Konkurrenz-Mengen für das aktive Lager.

        Industrie-Trajektorie ist lager-abhängig. In
        skeptischer Welt verzögert auch der Industrie-Hochlauf, weil
        DRI/Chemie auf H₂-Preis und -Verfügbarkeit reagieren.

        Args:
            year: Stützjahr.
            lager_override: Optional, analog `nws_brennstoff_twh`.

        Returns:
            TWh Industrie-H₂-Bedarf für das aktive Lager im Jahr `year`.
        """
        stuetzstellen = self.camp_h2.industry_active(camp_override)
        return self._interp(year, stuetzstellen)

    def h2_availability_share(
        self,
        year: int,
        *,
        path_share: float = 0.5,
    ) -> float:
        """H2-Verfügbarkeitsanteil für einen Pfad in einem Jahr.

        Antwortet die Frage: Welcher Anteil der gebauten H2-ready-Anlagen
        kann tatsächlich mit H2 betrieben werden, gegeben dass der
        verfügbare H2-Brennstoff zwischen mehreren Pfaden geteilt wird?

        Methodische Konsistenz: Diese Funktion kapselt die Bilanz-Logik,
        die bereits in `_compute_lcoe_ee_h2` und `_compute_lcoe_kkw_h2`
        (path_model.py) verwendet wird, sodass Mix-Hochlauf-Chart und
        Stress-Hochlauf-Chart mit demselben Verfügbarkeitsmodell rechnen.

        Args:
            year: Stützjahr.
            path_share: Anteil des H2-Brennstoffs, der dem fragenden Pfad
                zur Verfügung steht. Default 0.5 = gleichgewichtige
                Aufteilung zwischen EE-H2 und KKW-H2.

        Returns:
            0.0 (kein H2 verfügbar oder keine H2-ready-Anlagen) bis 1.0
            (volle Versorgung). Im Modell-Default niemals exakt 1.0,
            weil h2_brennstoff_capacity stets unter h2ready_capacity bleibt.

        Quellen für die zugrundeliegende H2-Trajektorie (`h2_brennstoff_capacity`):
        - Nationale Wasserstoff-Strategie Update 2023 (BMWK):
          5 GW Elektrolyse bis 2030, 10 GW bis 2035
        - Wasserstoff-Importstrategie 2024 (BMWK): signifikante Importe
          ab 2030, Voll-Hochlauf 2035-2040
        - Wasserstoff-Kernnetz BNetzA 2024: ~9.700 km bis 2032
        """
        h2ready = self.h2ready_capacity(year)
        if h2ready <= 0:
            return 0.0
        h2_brenn = self.h2_fuel_capacity(year)
        return min(h2_brenn * path_share, h2ready) / h2ready

    # TWh-Bilanz-Methode für die LCOE-Berechnung. Trennt sich bewusst
    # von h2_availability_share (GW-Schwelle), die weiterhin im Stresstest
    # und Mix-Hochlauf-Chart verwendet wird (Lose
    # Kopplung von LCOE-Engine und Stresstest-Engine).
    # Backup-Demand als Konstante (statt Param-Threading).
    # Begründung: 800 TWh × 0,08 = 64 TWh, Effekt auf Endwerte < 0,2 ct —
    # Aufwand-Wert-Verhältnis schlecht. Vereinfachung mit quantifizierter
    # Robustheits-Bound.
    _BACKUP_DEMAND_TWH_CONSTANT: float = 64.0  # = 800 TWh × 0,08

    def h2_availability_share_twh(
        self,
        year: int,
        *,
        camp_override: str | None = None,
    ) -> float:
        """H₂-Verfügbarkeits-Anteil aus TWh-Bilanz mit Industrie-Konkurrenz.

        TWh-Mengen-Bilanz, die Industrie-H₂-Konkurrenz explizit abzieht.
        Wird ausschließlich in den LCOE-Compute-Funktionen
        `_compute_ee_h2` und `_compute_kkw_h2` verwendet — der Stresstest
        und das Mix-Hochlauf-Chart bleiben bei der GW-Schwellen-Logik
        von `h2_availability_share` (Lose
        Kopplung).

        Mechanik:
            verfügbar_twh = max(0, nws_brennstoff_twh(year)
                                  - industrie_h2_twh(year))
            avail = min(1.0, verfügbar_twh / backup_demand_konstant)

        Wenn `h2ready_capacity(year) == 0`, ist der Anteil 0 (kein
        H₂-fähiges Backup-Equipment im Stützjahr).

        Args:
            year: Stützjahr.
            lager_override: Optional. BESTAND-Pfad ruft mit
                `lager_override="skeptisch"`.
                Sonst wird `self.lager_h2.h2_lager` verwendet.

        Returns:
            H₂-Verfügbarkeits-Anteil zwischen 0,0 und 1,0.
            In neutraler Welt mit Industrie-Konkurrenz typisch:
            2030: 0,0 (Industrie zieht alles weg);
            2035: 0,5; 2045: 1,0 (Backup-Bedarf gedeckt).

        Quellen pro Stützstelle siehe `docs/SOURCES.md`.
        """
        h2ready = self.h2ready_capacity(year)
        if h2ready <= 0:
            return 0.0

        # TWh-Bilanz: NWS-Verfügbarkeit minus Industrie-Konkurrenz
        nws_twh = self.nws_fuel_twh(year, camp_override=camp_override)
        ind_twh = self.industry_h2_twh(year, camp_override=camp_override)
        available_twh = max(0.0, nws_twh - ind_twh)

        # Backup-Bedarf als Konstante.
        if self._BACKUP_DEMAND_TWH_CONSTANT <= 0:
            return 1.0
        share = available_twh / self._BACKUP_DEMAND_TWH_CONSTANT
        return min(1.0, share)

    def h2_availability_share_stresstest(self, year: int) -> float:
        """H₂-Verfügbarkeits-Anteil für den Stresstest.

        Stresstest-spezifischer Wrapper um `h2_availability_share`, der
        den Pfad-Anteil hartcodiert auf 1,0 setzt — die fünf Pfade
        werden im Stresstest als **Alternativen** verglichen, nicht als
        gleichzeitig existierende Pfade. Ein Pfad bekommt darum vollen
        H₂-Pool, nicht halbierten.

        Mechanik: ruft `self.h2_availability_share(year, path_share=1.0)`
        auf und garantiert damit, dass der Aufrufer keinen abweichenden
        Wert übergeben kann. Lager-blind (Lose Kopplung
        zur LCOE-Engine — der Stresstest liest **nicht** das aktive
        Lager).

        Args:
            year: Stützjahr.

        Returns:
            H₂-Verfügbarkeits-Anteil zwischen 0,0 und 1,0 in
            GW-Schwellen-Logik mit `path_share=1.0`.
        """
        return self.h2_availability_share(year, path_share=1.0)

    def bestand_gas_capacity(self, year: int) -> float:
        """Erdgas-Kapazität in GW im BESTAND-Pfad (Bestand + Neubau, ohne H2-ready).

        BESTAND ist der einzige Pfad mit aktivem Erdgas-Neubau-Programm.
        Alle anderen Pfade nutzen `gas_bestand_capacity()` (= reiner
        Bestandsverlauf mit Alters-Stilllegung).

        Trajektorie: 31 GW (2026, identisch mit Bestand) → 36 GW (2030,
        leichter Neubau) → 45 GW (2040) → 50 GW (2055, Programm-Ziel).

        Differenz zu `gas_bestand_capacity()`:
        - Bestand-Pfad fällt von 31 → 18 GW über 2026-2050 (Alters-Abgang)
        - BESTAND wächst von 31 → 50 GW (aktiver Neubau, ohne H2-ready)
        - Differenz 2050: ~32 GW Neubau-Programm

        Quellen: BDI-2024 (Erdgas-Programm), KVBG (Kohle-Phaseout treibt
        Gas-Lücke), BNetzA-Monitoring 2024 (Bestand 2026).
        """
        return self._interp(year, {
            2026: 31.0, 2030: 36.0, 2035: 40.0, 2040: 45.0,
            2045: 47.0, 2050: 49.0, 2055: 50.0,
        })


# ===========================================================================
# 3. FORWARD COSTS (keine Sunk Costs)
# ===========================================================================

@dataclass
class ForwardCostParams:
    """Forward Costs für die Investitionsentscheidung

    PRINZIP: Bestehende Anlagen (PV-Park 2018, Off-Wind 2020, alte Gas-KW)
    sind SUNK. Sie laufen weiter zu ihren O&M-Kosten, aber ihre CAPEX
    zählt nicht für neue Investitionsentscheidungen.

    Diese Parameter beschreiben NEUBAU heute mit Forward-View.

    PREISBASIS:

    Alle CAPEX-/OPEX-/Brennstoff-Werte sind in **realer Kaufkraft Stand
    2025/26**. Das Modell rechnet **real, nicht nominal** — Inflation ist
    explizit nicht modelliert. Konsequenzen:

    - **WACC ist real, nicht nominal.** wacc_nuclear = 0,090 entspricht
      einer realen Kapitalkostenforderung. Ein nominaler WACC inklusive
      2 % p.a. ECB-Inflationsziel läge bei ~11 %.
    - **CAPEX/OPEX werden NICHT mit Inflations-Index aufgezinst.**
      pv_capex = 700 €/kW gilt 2026 ebenso wie 2055 — in 2025-Preisen.
      Lernkurven sind explizit modelliert (siehe pv_capex_eur_kw_endjahr,
      Lager-Felder PV_LERNKURVE_*); allgemeine Inflation nicht.
    - **CO₂-Preis-Trajektorie ist real.** co2_price_eur_t_2030 = 100 ist
      ein 2025-Preisniveau-Wert; die EU-ETS-Trajektorie wird real
      fortgeschrieben.
    - **Keine Wechselkurs-Annahmen.** USD-Quellen (BNEF, IEA) werden mit
      heutigem EUR/USD-Mittelwert übersetzt; FX-Drift nicht modelliert.

    **Wirkung der Inflations-Annahme.** Da das Modell real rechnet, ist
    die Inflations-Erwartung nur an einer Stelle relevant: der Differenz
    zwischen realer und nominaler WACC. Eine höhere Inflations-Erwartung
    senkt die reale WACC für gegebene nominale Kapitalkosten — wirkt
    aber proportional auf alle Pfade und verändert die Pfad-Reihenfolge
    nicht. Inflations-Sensitivität ist damit methodisch nachgeordnet.

    QUELLEN (siehe SOURCES.md für vollständige Diskussion):
    - PV/Wind CAPEX: Fraunhofer ISE Stromgestehungskosten 2024 (Juli)
    - Battery CAPEX: BloombergNEF Energy Storage Cost Survey 2025 (10. Dez 2025)
    - Nuclear CAPEX: Hinkley Point C Realität ~18.000 €/kW, Modell-Default 11.000 — konservative Setzung am unteren Ende der historischen EU-EPR-Bandbreite (KKW-Pfade werden dadurch eher günstiger gerechnet als die Hinkley-Realität nahelegen würde)
    - WACC: Anpassung nach Risikoprofil (höher für KKW wegen Bauzeit-Unsicherheit)
    - VLH: Realistische Werte für DE-Standorte, KKW: ISE-Annahme für 80%-EE-System
    """
    # CAPEX (€/kW)
    pv_capex_eur_kw: float = 700              # [SRC: ISE-2024, Bandbreite 530-1.600]
    pv_capex_eur_kw_endjahr: float = 700       # [MODEL: keine Lernkurve, heutige Werte gelten bis 2055; Lager PV_LERNKURVE_* siehe Modul-Ende]
    pv_capex_lernkurve_endjahr: int = 2045     # [SRC: ISE-2024] Plateau-Punkt der linearen Lernkurve, ISE-Studienzeitraum
    wind_onshore_capex_eur_kw: float = 1_400   # [SRC: ISE-2024, Bandbreite 1.300-1.900]
    wind_offshore_capex_eur_kw: float = 3_000  # [SRC: ISE-2024]
    nuclear_capex_eur_kw: float = 14_000  # Mitte HPC ~18.000 / Sizewell-FOAK ~10.000  [SRC: EDF-HPC, COURDESCOMPTES-FLAM]
    battery_capex_eur_kwh: float = 110         # [SRC: BNEF-2025-ESS, 117 USD/kWh turnkey]
    h2_gas_turbine_capex_eur_kw: float = 1_100 # [SRC: VDE-2023]

    # OPEX (€/kW/Jahr)
    pv_opex_eur_kw_year: float = 12            # [SRC: ISE-2024]
    wind_onshore_opex_eur_kw_year: float = 35  # [SRC: ISE-2024]
    wind_offshore_opex_eur_kw_year: float = 90 # [SRC: ISE-2024, höher wegen See]
    nuclear_opex_eur_kw_year: float = 130      # [SRC: ISE-2024, EDF-Daten]

    # Lebensdauer
    pv_lifetime: int = 30                      # [SRC: ISE-2024]
    wind_onshore_lifetime: int = 25            # [SRC: ISE-2024]
    wind_offshore_lifetime: int = 25           # [SRC: ISE-2024]
    nuclear_lifetime: int = 60  # EPR-Design  [CALIBRATED: vendor specification]
    battery_lifetime_cycles: int = 6_000       # [SRC: BNEF-2025-ESS, LFP-Chemie]

    # WACC nach Technologie (Risikoprämie!)
    # Default-Werte hier; vollständige Provenance (Bandbreiten, Quellen-
    # Tags, Begründungen) in core/wacc.py WACC_TABLE. Konsistenz-Test in
    # tests/core/test_wacc_consistency.py erzwingt Synchronität.
    # Vollständige methodische Diskussion in docs/SOURCES.md
    # Abschnitt C.
    wacc_pv: float = 0.05  # [CALIBRATED:IRENA-2024-WACC, siehe core.wacc]
    wacc_wind: float = 0.06  # [CALIBRATED:IRENA-2024, siehe core.wacc]
    wacc_nuclear: float = 0.090  # [CALIBRATED: HPC-Helm-Oxford + Sizewell-RAB, siehe core.wacc]
    wacc_battery: float = 0.07  # [CALIBRATED:BNEF-2025-ESS-implizit, siehe core.wacc]

    # Volllaststunden
    pv_vlh: float = 1050                       # [SRC: ISE-2024, DE-Mittel]
    wind_onshore_vlh: float = 2200             # [SRC: ISE-2024, DE-Mittel]
    wind_offshore_vlh: float = 4200            # [SRC: ISE-2024]
    nuclear_vlh: float = 6500  # in 80%-EE-System realistisch <8000  [SRC: ISE-2024]
                                                # KernD argumentiert 7.500-8.000 (historisch)

    # Forward-Rückstellungen für neu gebaute KKW (LCOE-aktiv, opex_var-Schicht)
    # Strukturell analog zum HPC-CfD-Modell: Decommissioning-Fund-Beitrag +
    # Waste-Transfer-Price werden während der Betriebsphase pro MWh Output
    # eingezahlt und decken die nach der Stilllegung anfallenden Verbindlich-
    # keiten ab. Wirken nur auf kkw_neubau_epr und kkw_neubau_smr.
    nuclear_decom_provision_eur_mwh: float = 3.5  # [SRC: EDF-HPC-CfD Funded Decommissioning Programme £2-3/MWh; Mid-Range-Anker]
    nuclear_waste_transfer_eur_mwh: float = 1.5   # [SRC: EDF-HPC-CfD Waste Transfer Price £1-2/MWh; Mid-Range-Anker]

    # Historische Vorbelastungen (DOKU-ONLY: NICHT Teil der LCOE-Rechnung)
    # Werte werden für Buch-Anhang / Anker-Tabellen aufgeführt, fließen
    # aber nicht in compute_path ein — forward-LCOE ist per Definition
    # forward-only, sunk costs gehören nicht in die Pfad-Vergleichs-Arithmetik.
    sunk_nuclear_decommissioning_bn: float = 5.7  # [DOKU-ONLY: BMUV-Rückbau-Berichte 2024, offene Verbindlichkeiten jenseits des KENFO-Fonds]
    sunk_repository_fund_bn: float = 24.0  # [DOKU-ONLY: KENFO-2024, 24,1 Mrd. eingezahlt 2017]
    sunk_eeg_legacy_bn: float = 270.0  # [DOKU-ONLY: BMWK-EEG-Konto-Berichte 2000-2022, kumulierte Förderzahlungen]

    # Symmetrische fossile Stranded-/Legacy-Marker (DOKU-ONLY).
    # Die hauptsächliche fossile Externalisierung läuft schon über CO₂-
    # Pönale (co2_price_eur_t × fuel-Emissionsfaktor). Diese Felder
    # dokumentieren zusätzliche Stranded-Asset-Risiken für Reviewer-
    # Symmetrie; methodisch heikel (Sensi-Welle nach V1.0).
    fossile_pipeline_stranded_bn: float = 40.0  # [DOKU-ONLY: Gas-Pipeline-Rückbau + LNG-Terminal-Lock-in, Reviewer-Schätz-Korridor 30-50 Mrd]
    fossile_coal_legacy_bn: float = 30.0  # [DOKU-ONLY: Braunkohle-Tagebau-Folgekosten, Reviewer-Schätz-Korridor 25-40 Mrd]


def annuity_factor(wacc: float, years: int) -> float:
    """Annuitätenfaktor"""
    # ZeroDivision-Guard für years=0 (Sensi-Konfigurationen mit Lifetime-Edge-Cases).
    years = max(1, years)
    if wacc == 0:
        return 1 / years
    return wacc / (1 - (1 + wacc) ** -years)


def lcoe_forward(capex_eur_kw: float, opex_eur_kw_year: float,
                 wacc: float, lifetime: int, vlh: float,
                 fuel_eur_mwh: float = 0,  # default arg  [CALIBRATED: function default]
                 efficiency: float = 1.0) -> float:  # default arg  [CALIBRATED: function default]
    """LCOE in ct/kWh, ohne historische Sunk Costs."""
    annuity = annuity_factor(wacc, lifetime)
    fixed_per_kw_year = capex_eur_kw * annuity + opex_eur_kw_year
    # ZeroDivision-Guard für vlh=0 und
    # efficiency=0 (Sensi-Konfigurationen mit extremen Drosselungen).
    fixed_per_kwh = fixed_per_kw_year / max(1e-9, vlh)  # €/kWh
    fuel_per_kwh = fuel_eur_mwh / 1000 / max(1e-9, efficiency)  # €/kWh
    return (fixed_per_kwh + fuel_per_kwh) * 100  # ct/kWh


def pv_capex_year(fc: ForwardCostParams, year: int) -> float:
    """PV-CAPEX in einem Jahr unter Berücksichtigung der Lernkurve.

    Lineare Interpolation zwischen ``fc.pv_capex_eur_kw`` (gilt 2026)
    und ``fc.pv_capex_eur_kw_endjahr`` (gilt ab ``fc.pv_capex_lernkurve_endjahr``).
    Vor 2026: gilt 2026-Wert. Nach Endjahr: Plateau auf Endjahr-Wert.

    Default-Verhalten: ``pv_capex_eur_kw_endjahr = pv_capex_eur_kw``,
    also keine Lernkurve aktiv. Vorgesehene Lager:
    PV_LERNKURVE_ISE_MITTEL_2045, PV_LERNKURVE_BNEF_NZS_MEDIAN,
    PV_LERNKURVE_AGGRESSIV (siehe Modul-Ende).

    Beispiel:
        >>> fc = ForwardCostParams(**PV_LERNKURVE_ISE_MITTEL_2045)
        >>> pv_capex_year(fc, 2026)  # noqa: F821
        700.0
        >>> pv_capex_year(fc, 2045)  # noqa: F821
        510.0
        >>> pv_capex_year(fc, 2055)  # noqa: F821 — Plateau
        510.0
    """
    start_year = 2026
    end_year = fc.pv_capex_lernkurve_endjahr
    if year <= start_year:
        return fc.pv_capex_eur_kw
    if year >= end_year:
        return fc.pv_capex_eur_kw_endjahr
    progress = (year - start_year) / (end_year - start_year)
    return fc.pv_capex_eur_kw + progress * (fc.pv_capex_eur_kw_endjahr - fc.pv_capex_eur_kw)


# ===========================================================================
# 4. ASYMMETRISCHE FLEXIBILISIERUNG
# ===========================================================================

@dataclass
class FlexibilityParams:
    """Pfad-spezifische Flexibilisierungs-Anteile (UI-Slider-State).

    Trägt die Streamlit-Slider-Anteile für DSM, V2G und Smart-Heating pro
    Pfad-Klasse. Die DSM-Rabatte selbst laufen über die CAMP_RANGES-Sensi-
    Achsen ``dsm_ee_ct_kwh`` / ``dsm_kkw_ct_kwh`` / ``dsm_misch_ct_kwh``
    (siehe :mod:`enesys.extensions.profile_costs`) — die hier gehaltenen
    Shares sind UI-State für eine Visualisierungs-Schicht, nicht direkt in
    der LCOE-Rechnung verbucht.
    """

    # EE-Pfade (EE-H2, EE-GAS): höheres Flex-Niveau
    ee_dsm_share: float = 0.20  # Anteil der Last über DSM steuerbar  [CALIBRATED: BNETZA-AGNES-2026 Smart-Meter-Rollout-Pfad]
    ee_v2g_share: float = 0.10  # Vehicle-to-Grid Anteil  [ASSUMPTION: 10% der E-PKW V2G-fähig 2045 — konservativ ggü. Industrie-Studien]
    ee_smart_heating_share: float = 0.40  # Wärmepumpen mit Steuerung  [ASSUMPTION: 40% steuerbare WP — gemäß §14a EnWG-Rollout]

    # KKW-Pfade (KKW-GAS, KKW-H2): niedrigeres Flex-Niveau
    kkw_dsm_share: float = 0.10  # [ASSUMPTION: KKW-Bandlast reduziert DSM-Bedarf um Faktor 2 ggü. EE-Pfaden]
    kkw_v2g_share: float = 0.05  # [ASSUMPTION: V2G in KKW-Pfaden weniger relevant, weil Bandlast verfügbar]
    kkw_smart_heating_share: float = 0.20  # [ASSUMPTION: Smart-Heating-Bedarf halbiert in KKW-Pfaden]


@dataclass
class GridStabilityParams:
    """Netzstabilität: Trägheit (Inertia), Frequenzhaltung, Schwarzstart

    Quelle: Modo Energy 11/2025 + DE TSO Inertia-Procurement Jan 2026

    Bedarf DE: ~30 GW Inertia-Service in 2027, ~72 GW in 2037
    Lieferanten: Synchrongeneratoren (KKW, Gas), Synchron-Kondensatoren,
                 Grid-Forming-Batterien, Schwungräder

    Kosten: Grid-Forming BESS: ~5% CAPEX-Aufschlag, dafür 8-17 k€/MW/a Erlös
    Synchron-Kondensatoren: 50-100 €/kVA CAPEX
    KKW als Beiprodukt: 0 marginale Kosten (nur wenn KKW eh läuft)
    """
    inertia_demand_gw_2030: float = 50.0     # [SRC: MODO-2025 — Inertia-Bedarf-Trajektorie]
    inertia_demand_gw_2045: float = 80.0     # [SRC: MODO-2025 — Inertia-Bedarf 100%-EE-System]

    # Versorgung in EE-Pfaden (ohne KKW-Synchrongenerator)
    ee_grid_forming_battery_capex_uplift: float = 0.05  # 5% Aufschlag  [CALIBRATED: BNEF-2025-ESS GFM-vs-Standard-Batterie]
    ee_synchronous_condenser_eur_kva: float = 75   # [CALIBRATED: Industrie-Standardwerte 50-100 €/kVA, Mitte des Bands]
    ee_synchronous_condenser_share: float = 0.30  # 30% via SynCon, 70% via GFM-BESS  [ASSUMPTION: Modell-Mix für 2045]

    # Versorgung in KKW-Pfaden (KKW-Synchrongenerator + GFM-BESS)
    nuclear_inertia_share: float = 0.30
    """30 % durch KKW-Synchrongenerator.

    [ASSUMPTION: KKW-Mix nur ~3-4 GW in KKW-GAS, deutlich unter
    50 %-Bedarf; realistische Inertia-Beitrags-Quote.]"""

    nuclear_gfm_share: float = 0.70
    """70 % Restbedarf via GFM-BESS gedeckt.

    [ASSUMPTION: Symmetrische Setzung
    kkw_gfm_share = 1 - kkw_inertia_share.]"""

    # Schwarzstart
    blackstart_surcharge_ct_kwh: float = 0.05  # [CALIBRATED: BNETZA-VS-2025 — Schwarzstart-Reserve-Kosten]

    # WEITER-SO: konventionelle Kraftwerke liefern Synchron-Trägheit als Beiprodukt
    weiterso_stability_surcharge_ct_kwh: float = 0.02  # [ASSUMPTION: nur Schwarzstart-Reserve, Inertia gratis aus Bestand]

    # Versorgungs-Schwelle: akzeptables Restdefizit im Stresstest in GW.
    # Lager-abhängig — Default ist die neutrale Mitte (Modell-Default).
    #
    # Lager-Range (für LAGER_RANGES und Tornado/Sensi):
    #   Bestand-Lager:    0-5 GW   "kein Industrie-Lastabwurf"
    #   Mitte (Default): 10-15 GW  "ERAA + politisch verteilbares DSM Stufe 1-2"
    #   EE-Lager:        15-25 GW  "DSM als Werkzeug der Energiewende"
    #   KKW-Lager:       5-10 GW   "Atom als Grundlast, kein DSM-Vertrauen"
    #
    # Quellen: ENTSO-E ERAA (LOLE-Standard), § 13 EnWG (DSM-Lastabwurf-Reserve),
    # § 51 EnWG (Versorgungssicherheits-Standard).
    supply_threshold_gw: float = 12.0  # [SRC: ERAA + BNetzA-VS-2025 — neutrale Mitte]

    def stability_surcharge_ee_ct_kwh(self, demand_twh: float) -> float:
        """Stabilitäts-Aufschlag für EE-Pfade (ohne KKW) in ct/kWh

        Annahme: 5% CAPEX-Aufschlag auf Speicher * Speicheranteil
                 + Synchron-Kondensatoren
        """
        # Zentrale BNetzA-Bedarfsabschätzung: 30 GW * 8-17 k€/MW/a = 240-510 Mio €/a
        # Für DE-Stromsystem ~ 800 TWh wären das 0.03-0.06 ct/kWh
        gfm_kosten = 0.04  # ct/kWh  [SRC: BNetzA-Bedarfsabschätzung Grid-Forming-Marktrolle, Mittelwert der 0,03-0,06-ct/kWh-Bandbreite]
        syncon_kosten = self.ee_synchronous_condenser_share * 0.02  # ct/kWh
        return gfm_kosten + syncon_kosten + self.blackstart_surcharge_ct_kwh

    def stability_surcharge_nuclear_ct_kwh(self, demand_twh: float) -> float:
        """Stabilitäts-Aufschlag für KKW-Pfade in ct/kWh

        KKW liefert Inertia mit -> günstiger als EE-Pfade. Aber: KKW läuft
        eh, marginal kostet das nichts ZUSÄTZLICH.
        Vorteil: ~50% des Stability-Aufschlags entfällt.
        """
        return (self.stability_surcharge_ee_ct_kwh(demand_twh)
                * (1 - self.nuclear_inertia_share))

    def stability_surcharge_weiterso_ct_kwh(self, demand_twh: float) -> float:
        """Stabilitäts-Aufschlag für WEITER-SO in ct/kWh.

        Konventionelle Kraftwerke (Kohle, Gas, KKW soweit vorhanden) liefern
        Synchron-Trägheit als Beiprodukt. Der Stabilitäts-Aufschlag besteht
        praktisch nur aus Schwarzstart-Reserve.
        """
        return self.weiterso_stability_surcharge_ct_kwh


# ===========================================================================
# 6. PFAD-INTEGRATION 2026 -> 2045
# ===========================================================================

@dataclass
class EeMixParams:
    """EE-Aufteilungsschlüssel beim Kohle-Auslauf — Mix-Trajektorie 2026-2055.

    Wenn Kohle aus dem Mix fällt (KVBG bis 2038 für WEITER-SO/BESTAND;
    aktiver Phaseout bis ws.aktiv_phaseout_year für die vier aktiven
    Pfade), wird der freigewordene Anteil auf PV / Wind-on / Wind-off
    verteilt. Die drei Anteile müssen sich auf 1.0 summieren.

    Default 0,5 / 0,3 / 0,2 spiegelt die heutige PV-dominante DE-Ausbau-
    Realität (BNetzA 2025: PV-Zubau 17,5 GW/a > Wind-onshore 4,5 GW/a >
    Wind-offshore 1,5 GW/a — Verhältnis ~5:1,3:0,4 — heute fast pure-PV,
    aber Mittel über 2026-2055 mit Wind-Beschleunigung wirkt 50/30/20
    plausibel). Alternativ-Setzung: BMWK setzt 30 GW Wind-Off bis 2045,
    das entspricht 0,3 statt 0,2 — als Lager-Schalter konfigurierbar.

    Methodik: Slider-Reaktion mit LAGER_RANGES-Anbindung möglich (zwei
    Hebel: pv_share_of_freed, wind_off_share_of_freed; wind_on ergibt
    sich als Rest).
    """
    pv_share: float = 0.50      # [SRC: BNetzA-2024 — PV-Zubau-Dominanz 17,5 GW/a]
    wind_on_share: float = 0.30  # [SRC: BNetzA-2024 — Wind-Onshore-Realität 4,5 GW/a]
    wind_off_share: float = 0.20 # [ASSUMPTION: konsistent mit BMWK-Ziel 30 GW Wind-Off bis 2045]


@dataclass
class WeiterSoParams:
    """WEITER-SO baseline parameters: continuation of current trends.

    Calibrated against 2025 actuals from BNetzA, Destatis, BDEW, and Fraunhofer ISE:
    - 438 TWh total generation, 58.6% renewable share
    - PV-Zubau 17.5 GW/year (high), Wind onshore 4.5 GW/year (bottleneck)
    - Erdgas-Anteil stieg 2025 auf 16.1% (höchster Wert seit 2018)
    - Kohle stagniert bei 22.1%
    - Importüberschuss 21.9 TWh (sinkend von 28.3 TWh in 2024)

    WEITER-SO bedeutet: keine Kraftwerksstrategie über 12 GW hinaus,
    Kohle bis 2038, Gas-Anteil wächst weiter, Wind-Engpass bleibt.
    """
    pv_additions_gw_per_year: float = 16.0          # [SRC: ISE-2024, BNetzA Trend 2025]
    wind_onshore_additions_gw_per_year: float = 4.5  # [SRC: BNetzA-2024, real 2025]
    wind_offshore_additions_gw_per_year: float = 1.5 # [SRC: BNetzA-2024, langsam]

    coal_phaseout_year: int = 2038              # [SRC: KVBG]
    active_phaseout_year: int = 2030              # [ASSUMPTION: KVBG-Idealpfad — aktive Pfade Kohle-Auslauf bis 2030]
    coal_initial_share: float = 0.22            # [SRC: AGEB-2024, real 2025]
    gas_growth_pct_per_year: float = 0.04     # [SRC: BNetzA-2024]
    co2_price_eur_t_2030: float = 120.0          # [SRC: EU-ETS-2026; konsistent mit _co2_preis_year-Default]

    import_share_2030: float = 0.10              # [SRC: BNetzA-2024]


@dataclass
class BestandParams:
    """BESTAND-Pfad-Parameter: aktive fossile Kontinuität, Erdgas-dominant.

    BESTAND ist das Bestands-Lager-Pure-Play: aktive politische Wahl gegen
    den Energiewende-Pfad, kein Status-quo-Drift wie WEITER-SO. Im Modell
    abgegrenzt durch:

    - Kohle folgt KVBG-Pfad bis 2038 (Bestands-Lager kann das KVBG-
      Bundesgesetz parlamentarisch nicht rückrollen)
    - Erdgas-Anteil erhöht (~50 % statt 16-40 % wie WEITER-SO), aktiv
      ausgebaut auf ~50 GW (Bestand 35 + Neubau 15, ohne H2-ready)
    - EE-Ausbau gedämpft (nicht gestoppt — politisch unrealistisch, weil
      EEG-Bestandsverträge aktiv)
    - Importanteil moderat (LNG + Pipeline-Mix, ~10 %)
    - Atom: 0 % (Bestands-Lager-Definition, kein Atom-Programm)

    USA-Realitätsanker: Das Bestands-Lager-Programm ist nicht hypothetisch —
    USA betreiben 2024 ein System mit Erdgas 43 %, EE 24-25 %, Kernkraft
    18 %, Kohle 15 % (EIA 2025). Übertragung schwerer wegen Brennstoff-
    Verfügbarkeit (USA 95 % Eigenproduktion vs. DE 5 %), EU-Klimaregulierung
    und parlamentarischer Mehrheit. Das BESTAND-Programm ist Möglichkeits-
    Beweis, kein 1:1-Vorbild.
    """
    # Erdgas: aktiver Hauptpfad, ~50 % Erzeugung
    gas_share_2030: float = 0.45              # [SRC: BDI-2024 — Bestands-Lager-Position]
    gas_share_2055: float = 0.50              # [SRC: BDI-2024 — Programm-Endzustand]

    # EE: gedämpfter Ausbau, kein Stop (Bestand-Anlagen laufen weiter)
    ee_additions_dampening: float = 0.50             # 50 % der Mitte-Trajektorie  [ASSUMPTION: Bestands-Lager-Position »EEG entschärfen«]
    ee_share_initial: float = 0.59               # [SRC: AGEB-2024 — Start-Mix wie WEITER-SO]
    ee_share_target_2055: float = 0.32           # [ASSUMPTION: gedämpfter Ausbau, 30-35 % Programm-Ziel]

    # Importe: LNG + Pipeline (kein Russland-Reset im Hauptpfad)
    import_share: float = 0.10                   # [SRC: ENTSO-E TYNDP — moderate Importannahme]

    # CO2-Preis: Bestands-Lager-Position »EU-ETS-Trajektorie aufweichen«
    co2_price_eur_t_2030: float = 120.0          # [SRC: EU-ETS-2026; konsistent mit _co2_preis_year-Default (atom_optimistic/bestand_optimistic-Härtung)]

    # Backup-Architektur (für Stresstest und Versorgungs-Schwelle)
    gas_new_build_target_gw_2055: float = 15.0      # [SRC: BDI-2024 — Erdgas-Neubau-Programm ohne H2-ready]

    # Kohle: KVBG-Pfad bis 2038 — KVBG-Bundesgesetz ist parlamentarisch
    # nicht im Bestands-Lager allein rückrollbar; BESTAND folgt also dem
    # gesetzlichen Pfad. Sensi-Variante »BESTAND-Kohle-Reaktivierung«
    # bleibt für Tornado-Hebel separat.
    coal_initial_share: float = 0.22            # [SRC: AGEB-2024 — Start-Anteil 2026, identisch zu WEITER-SO]
    coal_phaseout_year: int = 2038              # [SRC: KVBG, KoalV CDU/CSU/SPD April 2025]


# ===========================================================================
# Pfad-Mix-Konstanten
# ===========================================================================
#
# Mengen-gewichtete Erzeugungs-Mix-Anteile pro Pfad. Jeder Mix muss zu
# 1.0 summieren. Bei Änderungen die Coverage-Matrix-Tests
# (tests/consistency/test_coverage_matrix.py) neu durchspielen.
#
# Vergleich zu PATH_MIXES in path_sensitivity.py: Dort sind die Mixes
# für das Snapshot-Modell (2045) definiert; hier für das Pfadmodell
# (2026-2055-Trajektorie). EE-GAS und EE-H2 müssen identische EE-Mixes
# haben (Pfad-Symmetrie); KKW-Pfade haben dynamische nuc_share/
# bridge_gas_share-Aufteilung mit konstanter Summe 0.35.

# EE-GAS und EE-H2: identischer EE-Mix, unterschiedliches Backup
EE_MIX = {
    "pv": 0.40,
    "wind_onshore": 0.30,
    "wind_offshore": 0.15,
    "biomass": 0.04,
    "hydro": 0.03,
    # backup: 0.08 (Gas oder H2, in compute_path über ab_backup_share)
}

# KKW-GAS und KKW-H2: identischer EE-Anteil, dynamischer KKW/Bridge-Anteil
KKW_MIX_EE = {
    "pv": 0.25,
    "wind_onshore": 0.18,
    "wind_offshore": 0.10,
    "biomass": 0.03,
    "hydro": 0.03,
    # nuc + bridge_gas: konstant 0.35 (siehe nuc_share-Berechnung)
    # h2_sekundaer: 0.06 (in compute_path explizit)
}

# WEITER-SO innerer EE-Mix (multipliziert mit ee_share_weiterso)
WEITERSO_EE_INNER_MIX = {
    "pv": 0.50,
    "wind_onshore": 0.30,
    "wind_offshore": 0.10,
    "biomass": 0.10,
}

# BESTAND innerer EE-Mix (multipliziert mit ee_share_bestand).
# Anders als WEITER-SO: höherer Wind-Onshore-Anteil, weil Bestands-Lager
# nicht gegen EE-Ausbau ist, sondern gegen *forcierten* EE-Ausbau —
# bestehende EEG-Verträge laufen weiter, neue Auktionen werden gedämpft.
# Mix bleibt damit näher am Mitte-Pfad als WEITER-SO.
BESTAND_EE_INNER_MIX = {
    "pv": 0.42,
    "wind_onshore": 0.32,
    "wind_offshore": 0.16,
    "biomass": 0.10,
}

# Hilfs-Konstanten für die Pfad-Berechnung
BIOMASS_LCOE_CT = 14.0       # [SRC: ISE-2024]
HYDRO_LCOE_CT = 6.0          # Bestand-Wasserkraft [SRC: BMWi-Wasserkraft]
KKW_H2_SECONDARY_SHARE = 0.06  # [ASSUMPTION: H2-Spitzenlast in KKW-Pfaden]
KKW_TOTAL_BACKUP_SHARE = 0.35  # nuc_share + bridge_gas_share, konstante Summe  [ASSUMPTION: Modell-Strukturwahl, identisch zum non-EE-Anteil im EE-GAS+H2-Mengen-Bilanz-Test (35% vs 65% EE)]


# ===========================================================================
# Mix-Trajektorie für Visualisierung
# ===========================================================================
#
# Single source of truth für Mix-Hochlauf-Charts (mix_hochlauf_grid,
# 4_vier_schichten_stack). Die pfad-spezifischen Endzustands-Mixes
# leben in ``streamlit_rampup.PATH_END_2055``.
#
# Methodik:
#   - Endzustand 2055 ist die ideale LCOE-Mengen-Bilanz aus EE_MIX /
#     KKW_MIX_EE / WEITERSO_EE_INNER_MIX / BESTAND_EE_INNER_MIX plus
#     Parameter-Endwerten (ws/bp).
#   - Trajektorie 2026 → 2055: linearer Mix STATUS_QUO_2026_MIX → Pfad-Endzustand
#     für PV / Wind / Bio / Hydro / Importe; pfad-spezifische Modell-Trajektorien
#     überschreiben für:
#       Kohle  — KVBG-Phaseout (dem.kohle_share_weiterso bzw. KVBG-Trajektorie)
#       Erdgas — ws-Drift, BESTAND-Wachstum, KKW-Bridge-Gas
#       KKW    — tp.nuclear_capacity-Time-Path über dem.nuc_share
#       H2     — tp.h2_availability_share_twh-Aufteilung
#
# Konsistenz LCOE ↔ Plot:
#   Das LCOE-Modell rechnet weiterhin Steady-State (mit KKW-Trajektorie als
#   Ausnahme). Plot-Trajektorie ist Visualisierungs-Layer obendrauf — Anhang-A
#   trennt »Snapshot 2055« (Plot) und »Steady-State 2055-2085« (LCOE) bereits
#   methodisch. Eine Vollintegration (LCOE rechnet pro Jahr mit Mix-Trajektorie)
#   ist als künftige Erweiterung vorgesehen.

MIX_LAYERS: tuple[str, ...] = (
    "pv", "wind_on", "wind_off", "biomasse", "hydro",
    "kohle", "erdgas", "kkw",
    "h2_auf_h2", "h2_auf_gas",
    "importe",
)

# AGEB-2024 Stromerzeugungsmix — Status-Quo-Eintritt aller Pfade in 2026
# [SRC: AGEB-2024, Stromerzeugungsmix Deutschland]
# Sonstige 7 % (Heizöl, Pumpspeicher, etc.) sind in "importe" gerollt
# (gemeinsam mit dem Import-Saldo), weil sie im Modell keine eigene
# Schicht haben.
STATUS_QUO_2026_MIX: dict[str, float] = {
    "pv": 0.12,
    "wind_on": 0.24,
    "wind_off": 0.05,
    "biomasse": 0.07,
    "hydro": 0.04,
    "kohle": 0.22,
    "erdgas": 0.16,
    "kkw": 0.0,
    "h2_auf_h2": 0.0,
    "h2_auf_gas": 0.0,
    "importe": 0.10,
}

# Pfad-Endzustände 2055 — alle Werte sind aus existierenden Modell-Konstanten
# (EE_MIX, KKW_MIX_EE, WEITERSO_EE_INNER_MIX, BESTAND_EE_INNER_MIX) und
# Parameter-Defaults (WeiterSoParams, BestandParams) arithmetisch hergeleitet.
# Keine neuen Annahmen — pro Wert ist die Herleitung als Inline-Kommentar
# dokumentiert, sodass die Quelle bis zum [SRC: …]-Eintrag in der jeweiligen
# Param-Dataclass nachvollziehbar ist.
# Default-Backup-Anteil für EE-GAS / EE-H2 (= ab_backup_share in compute_path-
# Signatur, Z. 2227). Hier als Modul-Konstante hochgezogen, damit der
# Endzustands-Builder dieselbe Größe nutzt und nicht zweimal driften kann.
EE_BACKUP_SHARE_DEFAULT: float = 0.08

# WEITER-SO Erdgas-Cap aus _compute_demand_year (Z. 1700): erdgas-Drift wird
# bei diesem Wert gekappt, das ist der Endwert für 2055.
WEITERSO_GAS_CAP_2055: float = 0.40

# WEITER-SO Erdgas-Startwert 2026 (AGEB-2024, Erdgas-Stromerzeugung in DE).
# Hardcoded in _compute_demand_year:1700 als 0.16. Hier zentral, damit die
# Trajektorie-Berechnung und das LCOE-Modell dieselbe Zahl nutzen.
WEITERSO_GAS_START_2026: float = 0.16


@dataclass
class _DemandYear:
    """Demand-Trajektorie für ein einzelnes Jahr.

    Enthält drei Demand-Werte:
    - active_twh: für die drei voll-elektrifizierenden Pfade
      (EE-GAS, EE-H2, KKW-GAS, KKW-H2 — Skalierung 1,00)
    - bestand_twh: für BESTAND (Skalierung 0,85 — Bestands-Lager
      koppelt langsamer als aktive Programme: schwächere Wärmepumpen-
      Verbreitung, langsamere E-Mob-Adaption, kein H2-ready-Programm;
      konsistent zur Stress-Modell-Bremse.)
    - weiterso_twh: für WEITER-SO (Skalierung 0,60)

    Plus die Mix-Anteile, die aus Jahres-Position und ws-Parametern
    folgen.
    """
    active_twh: float
    bestand_twh: float
    weiterso_twh: float
    scaling: float
    bestand_scaling: float
    weiterso_scaling: float
    nuc_gw: float
    nuc_share: float
    bridge_gas_share: float
    coal_share_weiterso: float
    gas_share_weiterso: float


def _compute_demand_year(
    demand: Demand,
    time_p: TimePathParams,
    ws: WeiterSoParams,
    year: int,
    scaling: float,
    *,
    demand_consensus_scaling: float = 1.0,  # [MODEL: Sensi-Achse, 1.0=858 TWh Modell-Default, 1.23=953 BNetzA-NEP, 1.59=1100 Konsens-Mitte, 2.01=1270 Agora KNDE]
) -> _DemandYear:
    """Demand-Trajektorie und Mix-Anteile für ein Jahr.

    Pfad-agnostisch im Sinne, dass die fünf Pfade alle aus den hier
    berechneten Werten konsumieren — aber WEITER-SO bekommt seine
    eigene Demand-Linie (60%-Skalierung), die KKW-Pfade nutzen
    nuc_share, bridge_gas_share, etc.

    Konsens-Diskrepanz-Sensi: Mit ``demand_konsens_skalierung`` lassen
    sich die elektrifizierten
    Demand-Komponenten (Mobilität, Wärme, Industrie-Neu inkl.
    Direktelektrifizierung und H2-Strom) skalieren, ohne den
    klassischen Sockel (220 TWh HH+Gewerbe + 230 TWh klassisch
    Industrie = 450 TWh) zu verändern. Nur die elektrifizierten
    408 TWh skalieren. Daraus ergeben sich die folgenden
    Stützstellen (Modell-Default 858 TWh = 450 const + 408 elek):

    - 1,00 = 858 TWh (Modell-Default, nahe BNetzA-NEP-Pfad)
    - 1,23 ≈ 953 TWh (BNetzA NEP 2037/2045)
    - 1,59 ≈ 1.100 TWh (Konsens-Mitte: Ariadne / DIW)
    - 2,01 ≈ 1.270 TWh (Konsens-hoch: Agora KNDE)
    - 2,33 ≈ 1.400 TWh (BEE-Maximum)

    Sensitivitäts-Architektur für Strombedarf-Skalierung über die
    Stützstellen-Bandbreite. Befund aus dem Sensitivitäts-Lauf:
    Pfad-LCOEs sind strukturell invariant gegen die
    Strombedarf-Skalierung — die einzigen Demand-Abhängigkeiten
    (KKW-Anteil als GW/TWh und Stabilitäts-Aufschläge) ändern den
    LCOE um ≤0,1 ct selbst bei Skalierung auf Agora KNDE. Die
    Pfad-Reihenfolge ist robust.
    """
    weiterso_scaling = scaling * 0.60
    # BESTAND-Sektorkopplungs-Bremse 0.85: Bestands-Lager-Programm fährt
    # aktive Erdgas-Erweiterung, aber nicht aktive Sektorkopplung
    # (langsamere Wärmepumpen, langsamere E-Mob-Adaption, kein H2-ready-
    # Programm). Konsistent zur Bremse 0.85 im Stress-Modell
    # (winter_stress.py).
    bestand_scaling = scaling * 0.85

    base_demand = demand.base_household_commercial_twh
    base_industry = demand.industry.classic_electricity_twh
    target_mob = demand.mobility.electricity_consumption_twh() * demand_consensus_scaling
    target_heat = demand.heating.electricity_consumption_twh() * demand_consensus_scaling
    target_industry_neu = ((demand.industry.electricity_consumption_twh()
                            - base_industry)
                           * demand_consensus_scaling)

    demand_active_twh = (base_demand
                         + base_industry
                         + target_mob * scaling
                         + target_heat * scaling
                         + target_industry_neu * scaling)
    demand_bestand_twh = (base_demand
                          + base_industry
                          + target_mob * bestand_scaling
                          + target_heat * bestand_scaling
                          + target_industry_neu * bestand_scaling)
    demand_weiterso_twh = (base_demand
                           + base_industry
                           + target_mob * weiterso_scaling
                           + target_heat * weiterso_scaling
                           + target_industry_neu * weiterso_scaling)

    # KKW-Verfügbarkeit (gilt für KKW-GAS und KKW-H2)
    nuc_gw = time_p.nuclear_capacity(year)
    nuc_share = min(0.35, nuc_gw * 6500 / 1000 / demand_active_twh)
    bridge_gas_share = max(0, 0.35 - nuc_share)

    # WEITER-SO: Kohle phasing out, Erdgas wachsend
    years_until_phaseout = max(0, ws.coal_phaseout_year - year)
    coal_share_weiterso = ws.coal_initial_share * (
        years_until_phaseout / max(1, ws.coal_phaseout_year - 2026)
    )
    coal_share_weiterso = max(0, coal_share_weiterso)
    gas_share_weiterso = min(0.40, 0.16 + ws.gas_growth_pct_per_year
                                 * max(0, year - 2026))

    return _DemandYear(
        active_twh=demand_active_twh,
        bestand_twh=demand_bestand_twh,
        weiterso_twh=demand_weiterso_twh,
        scaling=scaling,
        bestand_scaling=bestand_scaling,
        weiterso_scaling=weiterso_scaling,
        nuc_gw=nuc_gw,
        nuc_share=nuc_share,
        bridge_gas_share=bridge_gas_share,
        coal_share_weiterso=coal_share_weiterso,
        gas_share_weiterso=gas_share_weiterso,
    )

# ===========================================================================
# 8. PV-LERNKURVEN-LAGER
# ===========================================================================
#
# Vier optionale Sensi-Lager für die PV-Lernkurve. Default des Modells
# ist KEINE Lernkurve (pv_capex_eur_kw_endjahr = pv_capex_eur_kw = 700),
# d.h. heutige ISE-2024-Werte gelten bis 2055. Die Lager sind als
# kwargs-Dict gedacht: ForwardCostParams(**PV_LERNKURVE_ISE_MITTEL_2045).
#
# Hintergrund: ISE 2024 zeigt für PV-Freifläche LCOE-Rückgang von
# 4,1-6,9 ct (2024) auf 3,1-5,0 ct (2045) — implizite CAPEX-Reduktion
# auf ~510 €/kW (Mittel) bzw. <460 €/kW (untere Grenze). BNEF-NZS-Median
# nimmt 350 €/kW an. Wind- und KKW-CAPEX werden bewusst NICHT mit
# Lernkurve modelliert, da ISE-2024 dort keine signifikanten Reduktionen
# zeigt (Wind) bzw. CAPEX standortabhängig statt lernkurven-abhängig
# ist (KKW: Faktor 5 Spreizung China-Inland 2.300 vs Flamanville 11.700).
#
# Methodische Einordnung der Lager:

PV_LERNKURVE_KONSERVATIV: dict[str, float] = {"pv_capex_eur_kw_endjahr": 700.0}
"""PV-CAPEX 2045 = 700 €/kW (heutige Werte bleiben). Default-Modell-Verhalten,
expliziter Sensi-Anker für »keine Lernkurven-Wette«-Argumentation.
[SRC: ISE-2024 Stromgestehungskosten erneuerbare Energien Juli 2024, Tabelle 1]"""

PV_LERNKURVE_ISE_MITTEL_2045: dict[str, float] = {"pv_capex_eur_kw_endjahr": 510.0}
"""PV-CAPEX 2045 = 510 €/kW (LCOE ~3,95 ct). ISE-Studien-Mittelwert 2045
für PV-Freifläche nach Lernkurven-Modell der Studie.
[SRC: ISE-2024 Studie Stromgestehungskosten erneuerbare Energien Juli 2024, Zusammenfassung S. 4: »Stromgestehungskosten zwischen 3,1 und 5,0 €Cent/kWh
bei Freiflächenanlagen« in 2045; CAPEX-Untergrenze »unter 460 EUR/kW«]"""

PV_LERNKURVE_BNEF_NZS_MEDIAN: dict[str, float] = {"pv_capex_eur_kw_endjahr": 350.0}
"""PV-CAPEX 2050 = 350 €/kW (LCOE ~3,07 ct). BNEF-Net-Zero-Median.
Identisch zum Anhang-C-Default (= aggressives Lernkurven-Szenario).
[SRC: BNEF-NEO-2024 Net-Zero-Scenario, Bandbreite 200-450 €/kW, Median 350]"""

PV_LERNKURVE_AGGRESSIV: dict[str, float] = {"pv_capex_eur_kw_endjahr": 200.0}
"""PV-CAPEX 2050 = 200 €/kW (LCOE ~2,24 ct). Untere Grenze BNEF-NZS,
LUT-Studie min. Tail-Annahme — nur für extreme Sensi-Tests.
[SRC: BNEF-NEO-2024 Net-Zero-Scenario untere Grenze; LUT University 2026
"PV CAPEX could fall to 192 USD/kW by 2050" (~166 €/kW)]"""
