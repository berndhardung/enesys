"""Winter-Stress-Test für enesys.

Worst-Case-Analyse für eine kalte Dunkelflaute: stündliche Last gegen
verfügbare Backup-Kapazität, getrennt nach Quellen (KKW, Bridge-Gas,
H2-Backup, Batterien, Importe). Liefert pro Pfad die Deckungsbilanz,
die Energie-Lücke und einen Preisaufschlag.

Konzeptionell ist dies eine eigenständige Analyse-Ebene neben dem
30-Jahres-Forward-Cost-Modell — andere Methodik, andere Zeitauflösung.
Vergleichbar in der Rolle mit `extensions/consumer_bridge.py` (Endkunden-
preis-Brücke): ergänzt das Pfad-Modell, ist aber nicht Teil seiner
Kern-Berechnung.

Stresstest-Härtung ist mit der Factory
`lole_p99_winter_stress_params()` umgesetzt. Der Default-Test
bleibt auf Dezember 2024 kalibriert; die LOLE-P99-Variante belegt
in LOLE-P99-Winter-Stresstest, dass die Pfad-Reihenfolge unter
härteren Annahmen stabil bleibt.

Mengen-Bilanz-Andockung: `winter_stress_balance` konsumiert
`core.path_model.compute_path(..., system_state=DUNKELFLAUTE)` als
konsistente Mengen-Bilanz-Quelle (Kapazitäten + Boost-Brennstoff-
Verfügbarkeit). Damit ist der Stresstest Konsument der
Schatten-Pipeline, keine eigenständige Analyse-Ebene. Die Funktion
`winter_stress_test` liefert die zitierfähige Default-Konfiguration.
"""

from __future__ import annotations

from dataclasses import dataclass

# Forward-References auf Param-Klassen aus path_model. Wir importieren
# sie nur zur Typ-Annotation und vermeiden so einen zirkulären Import,
# weil winter_stress nur Konsumer dieser Klassen ist (kein Konstruktor).
from typing import TYPE_CHECKING

from enesys.core.demand import Demand
from enesys.core.path_ids import PATH_IDS
from enesys.core.system_state import SystemState

if TYPE_CHECKING:  # pragma: no cover
    from enesys.core.path_inputs import TimePathParams
    from enesys.core.path_model import PathResult


# =============================================================================
# Modul-Konstanten
# =============================================================================

# Batterie-Mittelung über 24h. Lithium-Ion-Speicher mit 4h Volllast-
# Reichweite ist der heutige Marktstandard (Tesla Megapack, BYD Cube).
# Mittelung 4/24 = 0.167 = effektive Dauerleistung in 10-Tages-Stresstest.
# Für künftige Lithium-Iron-Phosphate (LFP) oder Iron-Air-Speicher mit
# 24-100h Reichweite müsste dieser Wert angepasst werden.
# Quelle: BNEF Battery Market Outlook 2025; SmartCalc Speicher-Atlas 2024.
BATTERY_DURATION_HOURS: int = 4

# Biomasse-Flex: Stromerzeugung aus Biogas/Holz, die in der Dunkelflaute
# als flexible Reserve verfügbar ist. Heute ~5 GW abrufbar (BNetzA-
# Kraftwerksliste 2024: 8 GW installiert, ca. 60% Verfügbarkeit in
# Winter-Spitze). Konstant über 25 Jahre, weil Biomasse-Bestand
# politisch nicht weiter ausgebaut wird, aber auch nicht zwangsweise
# stillgelegt wird.
# Quelle: BNetzA-Kraftwerksliste 2024, FNR Biomasse-Statistik 2024.
BIOMASS_FLEX_GW: float = 5.0

# WEITER-SO-Bremse auf den EE-Ausbau. Modell-Setzung: WEITER-SO bedeutet
# politische Untätigkeit, die den EE-Ausbau auf etwa 60% der Default-
# Trajektorie reduziert. Begründung: Anhaltende Genehmigungs-Hürden,
# missing Flächenausweisung, gebremste Auktions-Volumina.
# Vergleichbar mit AGORA-Szenario "Politische Untätigkeit 2024" und
# DENA-Leitstudie "Status-quo-Variante".
# Range belegbar zwischen 50% (Worst-Case-Politik) und 70% (träger
# Markt-Hochlauf ohne aktive Förderung). 60% ist mittlerer Wert.
# Quelle: AGORA Energiewende: Klimaneutrales Deutschland 2045 —
# Sensitivität "Verzögerter Ausbau", 2023.
WEITERSO_EE_BRAKE: float = 0.60

# BESTAND hat gedämpften EE-Ausbau. Die BestandParams-Annahme
# ee_zubau_dampening=0,50 betrifft den Zubau, nicht den absoluten
# Bestand: bestehende EE-Anlagen laufen weiter. Im Stresstest 2040
# liegt der EE-Bestand schon bei ~85 % des aktiven Pfads — neue
# Anlagen ab 2026 mit gedämpftem Ausbau hat bis 2040 dann ~70 %
# der vollen EE-Trajektorie erreicht. Wir nehmen 0,85 als
# Stresstest-Faktor (BESTAND-Bestandserhalt + gedämpfter Neubau).
# Damit landet BESTAND bei einem Default-Stresstest-Defizit nahe
# der Spec-Erwartung (3-10 GW), die das Bestands-Lager-Programm
# in seiner Robustheit korrekt abbildet.
BESTAND_EE_FACTOR: float = 0.85


@dataclass
class WinterStressParams:
    """Worst-Case-Annahmen für eine kalte Dunkelflaute.

    Kalibriert an realen Beobachtungen:
    - Dezember 2024: 11 Tage Dunkelflaute (Amprion: längste seit 1982),
      Großhandelspreise bis 960 €/MWh
    - 2025: längste 89 Stunden (Februar), Schnitt 3 Ereignisse/Jahr
    - Bedarf an kalten Tagen: ~2 TWh/Tag statt 1,27 TWh Mittel (+57%)

    Das Modell rechnet mit zwei kombinierten Effekten:
        1. EE-Erzeugung sinkt drastisch (PV nahezu null, Wind 10-20%)
        2. Bedarf steigt: Wärmepumpen mit COP 2.2 statt 3.2, mehr Heizleistung
    """

    duration_hours: float = 240  # 10 Tage (worst case wie Dez 2024)  [SRC: AMPRION-2024-DEZ — 11-tägige Dunkelflaute Dezember 2024]
    pv_capacity_factor: float = 0.03  # PV in Dunkelflaute fast null (3%)  [SRC: DWD-DUNKELFLAUTEN — typischer PV-Capacity-Factor in Hochdrucklage Winter]
    wind_capacity_factor: float = 0.10  # Wind 10% der Nennleistung  [SRC: DWD-DUNKELFLAUTEN — typischer Wind-Capacity-Factor in Hochdrucklage]

    # Wärmepumpe verliert Effizienz bei Frost
    cop_winter: float = 2.2  # statt 3.2 Jahresarbeitszahl  [CALIBRATED: BWP-2024 / ISE-Monitoring Winter-COP bei -10°C]
    heizbedarf_anstieg_faktor: float = 1.8  # Heizbedarf in kalten Wochen  [CALIBRATED: AGEB-Wärmestatistik Lastprofile Winter vs. Mittel]

    # E-Auto: kalter Akku, mehr Heizung im Auto
    e_auto_winter_aufschlag: float = (
        0.25  # +25% Verbrauch bei -10°C  [CALIBRATED: ADAC-2024 Wintertest E-Auto-Verbrauch]
    )

    # Industrie reduziert nicht, Sockel steigt leicht (mehr Licht)
    sockel_winter_faktor: float = (
        1.10  # [ASSUMPTION: 10% Sockel-Aufschlag durch Beleuchtung/HH-Geräte im Winter]
    )

    # Importe begrenzt: -- bei pan-europäischer Dunkelflaute schließen Nachbarn
    import_max_gw: float = 8.0  # 8 GW realistisches Import-Cap  [CALIBRATED: ENTSO-E ERAA-2023 — pan-europäische Dunkelflaute-Korrelation 70-80%]

    # Härtungs-Parameter (Default = neutral; die LOLE-P99-Variante
    # setzt diese Werte über `lole_p99_winter_stress_params()`).
    backup_availability: float = 1.0  # [ASSUMPTION: Verfügbarkeitsfaktor für Backup-Kraftwerke (Gas, H2, Kohle, KKW). Default 1.0 = ungestört. Worst-Case: 0.95.]
    multi_event_factor: float = 1.0  # [ASSUMPTION: Skaliert energy_deficit_twh/storage_drain_twh, um sequenzielle Mehrfach-Dunkelflauten in einem Winter abzubilden. Default 1.0 = Single-Event. Worst-Case: 3.0 für drei separate Phasen.]

    def winter_demand_gw(
        self,
        base_demand_twh: float,
        demand: Demand,
        *,
        electrification_scaling: float = 1.0,
    ) -> float:
        """Spitzenlast während Dunkelflaute in GW.

        Kalibrierung: Realer DE-Peak heute ~80 GW. Mit voller Elektrifizierung
        (E-Mob 80%, WP 60%, Industrie-H2) erwarten ÜNB 130-160 GW.
        Worst-Case Dunkelflaute kalt: 150-180 GW.

        Wir rechnen mit Lastfaktoren:
            - Sockel HH+Gewerbe: 1.3x Mittelwert (Winter-Abendspitze)
            - Heizung: 2.0x Jahresmittel (kalter Tag) × COP-Verschlechterung
            - E-Mobilität: 1.4x Mittel (60% laden in Spitzenstunde, +25% Winter)
            - Industrie: 1.0x (kontinuierlich)

        ``electrification_scaling`` skaliert die
        elektrifizierten Komponenten (Heizung, E-Mobilität, Industrie-Neu)
        zwischen 0.0 (heute, keine Sektorkopplung im Stress) und 1.0
        (Steady-State 2045+, voll elektrifiziert). Sockel HH+Gewerbe und
        klassische Industrie bleiben unverändert.
        """
        # Sockel HH+Gewerbe (klassischer Bestand, läuft heute wie morgen)
        sockel_avg_gw = demand.base_household_commercial_twh * 1000 / 8760
        sockel_peak_gw = sockel_avg_gw * self.sockel_winter_faktor * 1.3

        # Heizung: elektrifizierte Komponente, skaliert mit Hochlauf
        heizung_avg_gw = (
            demand.heating.electricity_consumption_twh() * 1000 / 8760 * electrification_scaling
        )
        cop_loss = demand.heating.cop_jahres / self.cop_winter
        # Realistic peak: 1.8x Jahresmittel an extrem kalten Tagen
        heizung_peak_gw = heizung_avg_gw * self.heizbedarf_anstieg_faktor * cop_loss

        # E-Auto: elektrifizierte Komponente, skaliert mit Hochlauf
        emob_avg_gw = (
            demand.mobility.electricity_consumption_twh() * 1000 / 8760 * electrification_scaling
        )
        emob_peak_gw = emob_avg_gw * 1.4 * (1 + self.e_auto_winter_aufschlag)

        # Industrie: Sockel klassisch unskaliert + Industrie-Neu skaliert
        industrie_total_avg_gw = demand.industry.electricity_consumption_twh() * 1000 / 8760
        industrie_klassisch_avg_gw = demand.industry.classic_electricity_twh * 1000 / 8760
        industrie_neu_avg_gw = (
            industrie_total_avg_gw - industrie_klassisch_avg_gw
        ) * electrification_scaling
        industrie_gw = industrie_klassisch_avg_gw + industrie_neu_avg_gw

        return sockel_peak_gw + heizung_peak_gw + emob_peak_gw + industrie_gw

    def winter_supply_ee_gw(self, ee_caps: dict[str, float]) -> float:
        """EE-Erzeugung während Dunkelflaute in GW."""
        pv_gw = ee_caps.get("pv", 0) * self.pv_capacity_factor
        won_gw = ee_caps.get("wind_onshore", 0) * self.wind_capacity_factor
        woff_gw = (
            ee_caps.get("wind_offshore", 0) * self.wind_capacity_factor * 1.5
        )  # offshore besser
        # Biomasse + Wasserkraft + Müll: ~ 8 GW kontinuierlich
        firm_gw = 8.0  # [ASSUMPTION: Biomasse + Wasserkraft + Müll-KWK kontinuierlich verfügbar — Größenordnung BNetzA-Kraftwerksliste 2024]
        return pv_gw + won_gw + woff_gw + firm_gw


def lole_p95_winter_stress_params() -> WinterStressParams:
    """LOLE-konforme Stresstest-Parameter (P95-Wetterjahr).

    Methodischer Anker: deutsche Reliability-Norm 2,77 h/a Loss-of-Load-
    Expectation, festgelegt 2021 vom BMWK gemäß VO (EU) 2019/943
    Art. 25 Abs. 1 (deutsch-luxemburgische Gebotszone). Dieser Stresstest
    bildet ein P95-Wetterjahr ab — die schlechtesten 5 % der Wetter-
    Realisationen, wie sie ENTSO-E ERAA-Methodologie über Monte-Carlo-
    Wetterjahre durchspielt.

    Eintritts-Wahrscheinlichkeit grob: ~5 % pro Winter, Wiederkehr
    alle ~20 Jahre. Damit deckt dieser Stresstest die offizielle
    Auslegungs-Norm ab — nicht ein willkürlich gewähltes Extremum.

    Parameter-Set für den gehärteten P95-Stresstest gegen den
    BMWK-Reliability-Standard.

    Vier Härtungen gegenüber dem Default (gegenüber dem in
    `WinterStressParams()` kalibrierten realen DKF Dezember 2024):

    1. **Dauer 10 statt 7 Tage.** KIT 2024: 10-Tage-DKF alle ~5 Jahre
       dokumentiert. Real eingetreten Nov 2024 (3 Tage), Dez 2024
       (4 Tage), Jan 2025 (3 Tage). 10-Tage-Niveau entspricht 2010er
       Dezember.

    2. **EE-Erzeugung im P95-Wetter.** PV 3 % CF (P95 für Winter-
       Wetter, DWD), Wind 8 % (ENTSO-E ERAA-Methodologie P95).
       Beide signifikant unter Jahresmittel, aber im realistischen
       Schlechtwetter-Bereich.

    3. **Backup-Verfügbarkeit 97 %.** BNetzA-VS-2025 mittlere
       Bandbreite; bei Kälte einzelne Wartungs- und Brennstoff-
       Engpässe. 97 % heißt: 3 % der nominalen Backup-GW stehen
       nicht zur Verfügung — moderater P95-Fall.

    4. **Zwei sequenzielle Phasen.** 2024 dokumentiert: 2 grosse
       DKF im Jahr (Nov, Dez). Realistische Annahme für Stress-
       winter.
    """
    return WinterStressParams(
        duration_hours=240,  # 10 Tage (KIT 2024 alle ~5 Jahre)
        pv_capacity_factor=0.03,  # 3 % CF (DWD P95-Winter)
        wind_capacity_factor=0.08,  # 8 % CF (ENTSO-E ERAA P95)
        backup_availability=0.97,  # 97 % (BNetzA-VS-2025 mittlere Bandbreite)
        multi_event_factor=2.0,  # Zwei DKF pro Winter (real 2024)
    )


def lole_p99_winter_stress_params() -> WinterStressParams:
    """100-Jahre-Wiederkehr Stresstest-Parameter (P99-Wetterjahr).

    Methodischer Anker: P99-Quantil der ENTSO-E ERAA-Wetter-Monte-Carlo,
    entspricht grob einem 100-Jahre-Wiederkehrintervall — also dem
    Schlechtwetter-Szenario, das einmal im Jahrhundert auftritt.

    Eintritts-Wahrscheinlichkeit grob: ~1 % pro Winter, Wiederkehr
    alle ~100 Jahre. Worst-Case-Parameter-Set für Robustheits-Tests:
    bleibt die Pfad-Reihenfolge auch unter diesen Annahmen stabil?

    Vier Härtungen gegenüber LOLE-P95:

    1. **Dauer 14 statt 10 Tage.** KIT 2024: 14-Tage-DKF alle ~10
       Jahre dokumentiert. Mit den anderen P99-Werten kombiniert
       ergibt sich grob ein 100-Jahre-Ereignis.

    2. **EE-Erzeugung im P99-Wetter.** PV 1 % CF, Wind 5 %
       (ERAA P99-Quantil — pan-europäische Hochdrucklage,
       Nebel über mehreren Tagen).

    3. **Backup-Verfügbarkeit 95 %.** BNetzA-VS-2025 untere
       Bandbreite (92–98 %).

    4. **Zwei sequenzielle Phasen.** Wie P95 — Mehrfach-DKF
       sind eher Wetter-Trend als P99-Eigenschaft. Der Winter
       2009/2010 hatte 7 DKF, aber die meisten kürzer.
    """
    return WinterStressParams(
        duration_hours=336,  # 14 Tage (KIT 2024 alle ~10 Jahre)
        pv_capacity_factor=0.01,  # 1 % CF (ERAA P99)
        wind_capacity_factor=0.05,  # 5 % CF (ERAA P99 pan-europ. Hochdruck)
        backup_availability=0.95,  # 95 % (BNetzA-VS-2025 untere Bandbreite)
        multi_event_factor=2.0,  # Zwei DKF (Mehrfach-DKF wie P95)
    )


@dataclass
class WinterStressResult:
    model: str  # Pfadname: "WEITER-SO", "EE-GAS", "EE-H2", "KKW-GAS", "KKW-H2"
    peak_demand_gw: float
    ee_supply_gw: float
    residual_gw: float  # Lücke = Demand - EE
    coverage_by: dict[str, float]  # GW pro Backup-Quelle
    coverage_total_gw: float
    deficit_gw: float  # ungedeckte Lücke (>0 = Blackout-Risiko)
    energy_deficit_twh: float  # Energie-Lücke über Dauer
    cost_premium_eur_mwh: float  # Preisaufschlag in dieser Phase
    storage_drain_twh: float  # Speicher-Entladung


def sokal_gw_safe(x: float) -> float:
    """Workaround für negative Werte in der Modellierung."""
    return max(0, x)


def winter_stress_test(
    year: int,
    demand: Demand,
    tp: TimePathParams | None = None,
    *,
    ws: WinterStressParams | None = None,
    # Batterien — symmetrisch 60 GW für alle vier Nicht-WEITER-SO-Pfade.
    # Pfad-Definition statt pfad-spezifischer Investitions-Setzung: was
    # die Pfade unterscheidet, ist Brennstoff (H2 vs. Erdgas) und KKW
    # ja/nein, nicht der Batterie-Ausbau. Symmetrie ist methodisch
    # geboten, weil eine asymmetrische Batterie-Setzung ohne externe
    # Begründung Pfad-Vergleiche verfälschen würde.
    # Endwert 60 GW = ~56 % des System-Hochlaufs (108 GW System-Wert
    # in 2050 aus tp.battery_capacity).
    battery_gw_ee_h2: float = 60.0,
    battery_gw_ee_gas: float = 60.0,
    battery_gw_kkw_gas: float = 60.0,
    battery_gw_kkw_h2: float = 60.0,
    battery_gw_weiterso: float = 12.0,  # WEITER-SO bleibt gebremst (Pfad-Definition)
    battery_gw_bestand: float = 30.0,  # BESTAND-Lager-Programm-Annahme
    # Backup-Kraftwerke: Default = -1 ist Signal-Wert "nutze Time-Path"
    # (Time-Paths aus tp). Alle vier
    # Nicht-WEITER-SO-Pfade haben dieselbe Bridge-Phase-Backup-Architektur
    # (Erdgas-Bestand + H2-ready); Differenzen entstehen nur durch H2-
    # Brennstoff-Verfügbarkeit und KKW. Aufrufer können explizite Werte
    # setzen.
    gas_backup_gw_ee_gas: float = -1.0,  # -1 = Time-Path
    gas_backup_gw_kkw_gas: float = -1.0,  # -1 = Time-Path
    h2_backup_gw_ee_h2: float = -1.0,  # -1 = Time-Path
    h2_backup_gw_kkw_h2: float = -1.0,  # -1 = Time-Path
    weiterso_coal_gas_gw: float = -1.0,  # -1 = Time-Path (Kohle + Gas-Bestand)
    # BESTAND nutzt die bestand_gas_capacity-Trajektorie (36 → 50 GW)
    # aus tp. Bestands-Lager-Programm: aktiver Erdgas-Neubau ohne H2-ready.
    gas_backup_gw_bestand: float = -1.0,  # -1 = Time-Path tp.bestand_gas_capacity
    # Bedarfshochlauf-Skalierung. Default 1.0 = Steady-State-Bedarf.
    # Im Hochlauf-Plot wird mit 0.0→1.0 zwischen 2026 und 2045 skaliert,
    # analog zu _ee_skalierung im Mix-Hochlauf-Chart. Pfad-Differenzierung:
    # WEITER-SO nutzt 0.6 × demand_scaling (gebremste Sektorkopplung,
    # konsistent zu _compute_demand_year), die anderen fünf Pfade
    # nutzen demand_scaling direkt.
    coal_bridge_gw_active: float = -1.0,
    demand_scaling: float = 1.0,
    # Sensitivierbare Pfad-Bremsen für die Sektorkopplung.
    # WEITER-SO und BESTAND koppeln strukturell langsamer als die aktiven
    # Programme. Defaults sind quellenbasiert kalibriert; für Sensitivitäts-
    # Studien können beide Werte überschrieben werden.
    #
    # WEITER-SO 0.60: Konsistent zur weiterso_skalierung in
    #   `_compute_demand_year` (path_model.py). Methodische Setzung des
    #   path_model: WEITER-SO koppelt 60 % des aktiven Sektorkopplungs-
    #   Hochlaufs.
    #
    # BESTAND 0.70: Bestands-Lager-Programm fährt aktive Erdgas-Erweiterung,
    #   aber kein aktives Wärmepumpen-/E-Mob-Programm. Quellen-Triangulation:
    #   - BEE-Wärmeszenario 2045 (Klimaneutral-Pfad): 14-18 Mio Wärmepumpen
    #     2045. BESTAND-Schätzung bei realistisch verlangsamter Roll-Out-
    #     Trajektorie: ~10-12 Mio (60-65 % der aktiven Trajektorie).
    #   - Realer Trend 2024 (Zukunft Altbau): 70 % der Heizungs-Neuinstal-
    #     lationen 2024 sind fossil. Trend ohne aktives Förderprogramm.
    #   - BDI/BCG Klimapfade 2.0: 993 TWh Strombedarf 2045 (aktiv).
    #     Ariadne 2025 Existierende Politiken: 1.037 TWh — überlappt mit
    #     dem aktiven Bereich, weil E-Mob aus Wirtschaftlichkeit auch ohne
    #     aktives Programm hochläuft.
    #   - PwC-Studie 2023 zum Wärmepumpen-Hochlauf: Hemmnisse und
    #     Schub-Hochlauf-Differenz nach der Heizungsdebatte 2023.
    #   Gewichteter Mittelwert über die elektrifizierten Komponenten
    #   (Wärmepumpen ~60-65 %, E-Mob ~75-80 %, Industrie-Neu ~70 %)
    #   ergibt ~70 %.
    weiterso_brake_factor: float = 0.60,
    bestand_brake_factor: float = 0.70,
) -> dict[str, WinterStressResult]:
    """Winter-Stress-Test für alle 6 Pfade.

    Prüft, ob die Spitzenlast während einer 10-tägigen Dunkelflaute
    gedeckt werden kann.

    Pfade:
        WEITER-SO: Status quo, fossile Bestandsflotte als Backup
        EE-GAS:    EE-Hochlauf + Gas-Backup
        EE-H2:     EE-Hochlauf + Wasserstoff-Saisonspeicher
        KKW-GAS:   EE+KKW + Gas-Backup
        KKW-H2:    EE+KKW + Wasserstoff-Backup
        BESTAND:   gedämpfter EE + aktiver Erdgas-Neubau (ohne H2-ready)
    """
    if ws is None:
        ws = WinterStressParams()
    if tp is None:
        # tp ist optional; Default-Instanz wird lazy importiert, um den
        # Top-Level-Import von path_inputs zu vermeiden.
        from enesys.core.path_inputs import TimePathParams

        tp = TimePathParams()

    # Time-Path-Resolution: Wenn die Backup-Parameter auf -1 gesetzt sind
    # (Default-Signal), nutze die Time-Path-Werte aus tp.
    # fossil_total = Erdgas-Bestand + H2-ready (=Bridge-Phase-Gesamtkapazität).
    # Die vier Nicht-WEITER-SO-Pfade nutzen diese Architektur symmetrisch.
    gas_existing_gw = tp.gas_existing_capacity(year)
    h2ready_gw = tp.h2ready_capacity(year)
    fossil_bridge_total = gas_existing_gw + h2ready_gw

    if gas_backup_gw_ee_gas < 0:
        gas_backup_gw_ee_gas = fossil_bridge_total
    if gas_backup_gw_kkw_gas < 0:
        gas_backup_gw_kkw_gas = fossil_bridge_total
    if h2_backup_gw_ee_h2 < 0:
        h2_backup_gw_ee_h2 = fossil_bridge_total
    if h2_backup_gw_kkw_h2 < 0:
        h2_backup_gw_kkw_h2 = fossil_bridge_total
    if weiterso_coal_gas_gw < 0:
        # WEITER-SO bleibt mit der Kohle+Gas-Bestandsflotte, sinkend bis
        # zum Kohleausstieg 2038. Default-Trajektorie 65→45→30 GW.
        # Hier: nutze tp.gas_existing_capacity + Kohle-Flotte (sinkend).
        coal_ws = tp.coal_existing_capacity(year, scenario="weiterso")
        weiterso_coal_gas_gw = coal_ws + gas_existing_gw
    if gas_backup_gw_bestand < 0:
        # BESTAND nutzt aktiv-erweitertes Erdgas (Bestand + Neubau) über
        # die bestand_gas_capacity-Trajektorie 36 → 50 GW, plus Kohle-Flotte
        # bis KVBG-Phaseout 2038 (Bestands-Lager kann KVBG nicht
        # parlamentarisch rückrollen). Kein H2-ready (Bestands-Lager-
        # Programm-Definition).
        coal_bestand = tp.coal_existing_capacity(year, scenario="bestand")
        gas_backup_gw_bestand = tp.bestand_gas_capacity(year) + coal_bestand
    if coal_bridge_gw_active < 0:
        # Aktive Pfade nutzen die KVBG-Bridge-Phase-Kohle über
        # tp.coal_bestand_capacity(year, scenario="active") — 33 GW in 2026,
        # gewichteter Mittelwert-Auslauf bis 2034 (BRIDGE_PHASE-Spec).
        # Ab 2034 = 0 GW.
        coal_bridge_gw_active = tp.coal_existing_capacity(year, scenario="active")

    # Batterien zeitabhängig über tp.battery_capacity(): System-Wert ×
    # Pfad-Anteil. Symmetrisch 55,6 % für alle Nicht-WEITER-SO-Pfade,
    # 11,1 % für WEITER-SO. Greift nur, wenn der Aufrufer den Default
    # (60 GW bzw. 12 GW) verwendet — explizite Werte werden respektiert.
    # BESTAND-Anteil 27,8 % (30 GW / 108 GW): moderater Ausbau, mehr
    # als WEITER-SO aber weniger als die aktiven EE-Pfade.
    battery_share_non_ws = 0.556  # 60 GW / 108 GW
    battery_share_ws = 0.111  # 12 GW / 108 GW
    battery_share_bestand = 0.278  # 30 GW / 108 GW
    bat_system = tp.battery_capacity(year)
    if abs(battery_gw_ee_h2 - 60.0) < 0.01:
        battery_gw_ee_h2 = bat_system * battery_share_non_ws
    if abs(battery_gw_ee_gas - 60.0) < 0.01:
        battery_gw_ee_gas = bat_system * battery_share_non_ws
    if abs(battery_gw_kkw_gas - 60.0) < 0.01:
        battery_gw_kkw_gas = bat_system * battery_share_non_ws
    if abs(battery_gw_kkw_h2 - 60.0) < 0.01:
        battery_gw_kkw_h2 = bat_system * battery_share_non_ws
    if abs(battery_gw_weiterso - 12.0) < 0.01:
        battery_gw_weiterso = bat_system * battery_share_ws
    if abs(battery_gw_bestand - 30.0) < 0.01:
        battery_gw_bestand = bat_system * battery_share_bestand

    # backup_availability < 1.0 reduziert die nominalen Backup-Kapazitäten
    # (Wartung, Brennstoff-Logistik, Lieferketten). Default 1.0 = ungestört;
    # Worst-Case 0.95 (BNetzA-VS-2025).
    avail = ws.backup_availability
    battery_gw_ee_h2 *= avail
    battery_gw_ee_gas *= avail
    battery_gw_kkw_gas *= avail
    battery_gw_kkw_h2 *= avail
    battery_gw_weiterso *= avail
    battery_gw_bestand *= avail
    gas_backup_gw_ee_gas *= avail
    gas_backup_gw_kkw_gas *= avail
    h2_backup_gw_ee_h2 *= avail
    h2_backup_gw_kkw_h2 *= avail
    weiterso_coal_gas_gw *= avail
    gas_backup_gw_bestand *= avail
    gas_existing_gw *= avail
    h2ready_gw *= avail
    coal_bridge_gw_active *= avail

    base_demand_twh = demand.total_twh()
    ee_caps = tp.ee_capacity(year)
    # KKW liefert bei reduzierter Backup-Verfügbarkeit ebenfalls weniger
    # (Brennstab-Logistik, Wartung, ungeplante Abschaltungen).
    nuc_gw = tp.nuclear_capacity(year) * avail

    # Pfad-spezifische Spitzenlast für den Hochlauf.
    # WEITER-SO koppelt die Sektoren strukturell langsamer (60%-Bremse,
    # konsistent zu _compute_demand_year-Modellannahme). Diese 60%-Bremse
    # gilt durchgehend — auch im Steady-State 2045+ erreicht WEITER-SO
    # nicht den vollen Peak, weil das Programm keine aktive Sektorkopplung
    # treibt. Damit ist Konsistenz zur LCOE/Mix-Berechnung gewährleistet:
    # WEITER-SO Strombedarf bleibt strukturell unter dem aktiver Pfade.
    # BESTAND koppelt zwischen WEITER-SO und aktiv: aktive Wirtschaft, aber
    # langsamere Wärmepumpen-/E-Mob-Adaption als die EE-/KKW-Programme.
    # Default 0.85 (Bestand_lag-Faktor); kalibriert als plausibler Wert
    # zwischen WEITER-SO 0.60 und aktiv 1.00.
    weiterso_peak_scaling = demand_scaling * weiterso_brake_factor
    bestand_peak_scaling = demand_scaling * bestand_brake_factor
    peak_demand_gw_active = ws.winter_demand_gw(
        base_demand_twh, demand, electrification_scaling=demand_scaling
    )
    peak_demand_gw_weiterso = ws.winter_demand_gw(
        base_demand_twh, demand, electrification_scaling=weiterso_peak_scaling
    )
    peak_demand_gw_bestand = ws.winter_demand_gw(
        base_demand_twh, demand, electrification_scaling=bestand_peak_scaling
    )

    ee_supply_gw = ws.winter_supply_ee_gw(ee_caps)
    residual_gw = peak_demand_gw_active - ee_supply_gw

    # WEITER-SO hat reduzierten EE-Ausbau — wir simulieren das durch eine
    # 60%-Reduktion der ee_supply_gw. Real wird das im path_model durch
    # WeiterSoParams gesteuert, aber für den Stresstest reicht die
    # Skalierung hier.
    weiterso_ee_supply_gw = ee_supply_gw * WEITERSO_EE_BRAKE  # gebremster EE-Ausbau
    weiterso_residual_gw = peak_demand_gw_weiterso - weiterso_ee_supply_gw

    # BESTAND nutzt den Modul-Faktor BESTAND_EE_FACTOR (Begründung siehe
    # Definition oben) und einen eigenen Peak (0.85-Bremse), nicht den
    # vollen aktiven Peak.
    bestand_ee_supply_gw = ee_supply_gw * BESTAND_EE_FACTOR
    bestand_residual_gw = peak_demand_gw_bestand - bestand_ee_supply_gw

    # peak_demand_gw: Alias auf den aktiven Peak.
    peak_demand_gw = peak_demand_gw_active

    results = {}

    # === EE-H2: EE + Batterie + Kohle-Bridge + H2-Backup + Importe + DSM ===
    battery_avg_ee_h2 = battery_gw_ee_h2 * BATTERY_DURATION_HOURS / 24
    ee_h2_coverage = {
        "Batterien (gemittelt)": battery_avg_ee_h2,
        "Kohle-Bridge": min(coal_bridge_gw_active, max(0, residual_gw - battery_avg_ee_h2)),
        "H2-Backup": min(
            h2_backup_gw_ee_h2,
            max(0, residual_gw - battery_avg_ee_h2 - coal_bridge_gw_active),
        ),
        "Importe": min(
            ws.import_max_gw,
            max(
                0,
                residual_gw - battery_avg_ee_h2 - coal_bridge_gw_active - h2_backup_gw_ee_h2,
            ),
        ),
        "Biomasse-Flex": BIOMASS_FLEX_GW,
        "DSM": min(15.0, residual_gw * 0.10),
    }
    ee_h2_total = sum(ee_h2_coverage.values())
    ee_h2_deficit = max(0, residual_gw - ee_h2_total)

    results["EE-H2"] = WinterStressResult(
        model="EE-H2",
        peak_demand_gw=peak_demand_gw,
        ee_supply_gw=ee_supply_gw,
        residual_gw=residual_gw,
        coverage_by=ee_h2_coverage,
        coverage_total_gw=ee_h2_total,
        deficit_gw=ee_h2_deficit,
        energy_deficit_twh=ee_h2_deficit * ws.duration_hours / 1000,
        cost_premium_eur_mwh=250 if ee_h2_deficit < 5 else 600,
        storage_drain_twh=battery_avg_ee_h2 * ws.duration_hours / 1000,
    )

    # === KKW-GAS: EE + KKW + Batterie + Kohle-Bridge + Gas-Backup + Importe ===
    battery_avg_kkw_gas = battery_gw_kkw_gas * BATTERY_DURATION_HOURS / 24
    kkw_gas_coverage = {
        "Kernkraft (Grundlast)": nuc_gw,
        "Batterien (gemittelt)": battery_avg_kkw_gas,
        "Kohle-Bridge": min(
            coal_bridge_gw_active,
            max(0, residual_gw - nuc_gw - battery_avg_kkw_gas),
        ),
        "Gas-Backup": min(
            gas_backup_gw_kkw_gas,
            max(
                0,
                residual_gw - nuc_gw - battery_avg_kkw_gas - coal_bridge_gw_active,
            ),
        ),
        "Importe": min(
            ws.import_max_gw,
            max(
                0,
                residual_gw
                - nuc_gw
                - battery_avg_kkw_gas
                - coal_bridge_gw_active
                - gas_backup_gw_kkw_gas,
            ),
        ),
        "Biomasse-Flex": BIOMASS_FLEX_GW,
        "DSM": min(8.0, residual_gw * 0.05),
    }
    kkw_gas_total = sum(kkw_gas_coverage.values())
    kkw_gas_deficit = max(0, residual_gw - kkw_gas_total)

    results["KKW-GAS"] = WinterStressResult(
        model="KKW-GAS",
        peak_demand_gw=peak_demand_gw,
        ee_supply_gw=ee_supply_gw,
        residual_gw=residual_gw,
        coverage_by=kkw_gas_coverage,
        coverage_total_gw=kkw_gas_total,
        deficit_gw=kkw_gas_deficit,
        energy_deficit_twh=kkw_gas_deficit * ws.duration_hours / 1000,
        cost_premium_eur_mwh=200 if kkw_gas_deficit < 5 else 600,
        storage_drain_twh=battery_avg_kkw_gas * ws.duration_hours / 1000,
    )

    # === EE-GAS: EE + Batterie + Kohle-Bridge + Gas-Backup + Importe + DSM ===
    battery_avg_ee_gas = battery_gw_ee_gas * BATTERY_DURATION_HOURS / 24
    ee_gas_coverage = {
        "Batterien (gemittelt)": battery_avg_ee_gas,
        "Kohle-Bridge": min(coal_bridge_gw_active, max(0, residual_gw - battery_avg_ee_gas)),
        "Gas-Backup": min(
            gas_backup_gw_ee_gas,
            max(0, residual_gw - battery_avg_ee_gas - coal_bridge_gw_active),
        ),
        "Importe": min(
            ws.import_max_gw,
            max(
                0,
                residual_gw - battery_avg_ee_gas - coal_bridge_gw_active - gas_backup_gw_ee_gas,
            ),
        ),
        "Biomasse-Flex": BIOMASS_FLEX_GW,
        "DSM": min(15.0, residual_gw * 0.10),
    }
    ee_gas_total = sum(ee_gas_coverage.values())
    ee_gas_deficit = max(0, residual_gw - ee_gas_total)

    results["EE-GAS"] = WinterStressResult(
        model="EE-GAS",
        peak_demand_gw=peak_demand_gw,
        ee_supply_gw=ee_supply_gw,
        residual_gw=residual_gw,
        coverage_by=ee_gas_coverage,
        coverage_total_gw=ee_gas_total,
        deficit_gw=ee_gas_deficit,
        energy_deficit_twh=ee_gas_deficit * ws.duration_hours / 1000,
        cost_premium_eur_mwh=200 if ee_gas_deficit < 5 else 500,
        storage_drain_twh=battery_avg_ee_gas * ws.duration_hours / 1000,
    )

    # === KKW-H2: EE + KKW + Batterie + Kohle-Bridge + H2-Backup + Importe ===
    battery_avg_kkw_h2 = battery_gw_kkw_h2 * BATTERY_DURATION_HOURS / 24
    kkw_h2_coverage = {
        "Kernkraft (Grundlast)": nuc_gw,
        "Batterien (gemittelt)": battery_avg_kkw_h2,
        "Kohle-Bridge": min(
            coal_bridge_gw_active,
            max(0, residual_gw - nuc_gw - battery_avg_kkw_h2),
        ),
        "H2-Backup": min(
            h2_backup_gw_kkw_h2,
            max(
                0,
                residual_gw - nuc_gw - battery_avg_kkw_h2 - coal_bridge_gw_active,
            ),
        ),
        "Importe": min(
            ws.import_max_gw,
            max(
                0,
                residual_gw
                - nuc_gw
                - battery_avg_kkw_h2
                - coal_bridge_gw_active
                - h2_backup_gw_kkw_h2,
            ),
        ),
        "Biomasse-Flex": BIOMASS_FLEX_GW,
        "DSM": min(8.0, residual_gw * 0.05),
    }
    kkw_h2_total = sum(kkw_h2_coverage.values())
    kkw_h2_deficit = max(0, residual_gw - kkw_h2_total)

    results["KKW-H2"] = WinterStressResult(
        model="KKW-H2",
        peak_demand_gw=peak_demand_gw,
        ee_supply_gw=ee_supply_gw,
        residual_gw=residual_gw,
        coverage_by=kkw_h2_coverage,
        coverage_total_gw=kkw_h2_total,
        deficit_gw=kkw_h2_deficit,
        energy_deficit_twh=kkw_h2_deficit * ws.duration_hours / 1000,
        cost_premium_eur_mwh=300 if kkw_h2_deficit < 5 else 600,  # H2 teurer als Gas
        storage_drain_twh=battery_avg_kkw_h2 * ws.duration_hours / 1000,
    )

    # === BESTAND: gedämpfter EE-Ausbau + Erdgas-Programm-Flotte + Importe + DSM ===
    # Bestands-Lager-Pure-Play (aktive fossile Kontinuität).
    # Anders als WEITER-SO: aktiver Erdgas-Neubau (35 → 50 GW), plus
    # KVBG-Kohle-Flotte bis 2038 (Bestands-Lager kann das KVBG-
    # Bundesgesetz nicht parlamentarisch rückrollen), 30 GW Batterien
    # (mehr als WEITER-SO 12 GW, weniger als aktive Pfade 60 GW), 5 % DSM.
    # Methodische Robustheit: BESTAND ist im Stresstest robuster als die
    # KKW-Pfade (Erdgas-Brennstoff-Logistik einfacher als KKW-Brennstab),
    # was aus methodischen Gründen offen ausgewiesen wird — die Empfehlung
    # gegen BESTAND folgt nicht aus Versorgungssicherheit, sondern aus
    # Stranded-Assets, politischer Durchsetzbarkeit und LCOE-Vergleich.
    battery_avg_bestand = battery_gw_bestand * BATTERY_DURATION_HOURS / 24
    bestand_coverage = {
        "Batterien (gemittelt)": battery_avg_bestand,
        "Erdgas-Flotte": min(
            gas_backup_gw_bestand, max(0, bestand_residual_gw - battery_avg_bestand)
        ),
        "Importe": min(
            ws.import_max_gw,
            max(0, bestand_residual_gw - battery_avg_bestand - gas_backup_gw_bestand),
        ),
        "Biomasse-Flex": BIOMASS_FLEX_GW,
        "DSM": min(8.0, bestand_residual_gw * 0.05),  # 5 % DSM
    }
    bestand_total = sum(bestand_coverage.values())
    bestand_deficit = max(0, bestand_residual_gw - bestand_total)

    results["BESTAND"] = WinterStressResult(
        model="BESTAND",
        peak_demand_gw=peak_demand_gw_bestand,
        ee_supply_gw=bestand_ee_supply_gw,
        residual_gw=bestand_residual_gw,
        coverage_by=bestand_coverage,
        coverage_total_gw=bestand_total,
        deficit_gw=bestand_deficit,
        energy_deficit_twh=bestand_deficit * ws.duration_hours / 1000,
        # Erdgas-Spitzenpreise + CO2-Pönale (BestandParams.co2_price_eur_t_2030 = 120 €/t)
        cost_premium_eur_mwh=280 if bestand_deficit < 5 else 700,
        storage_drain_twh=battery_avg_bestand * ws.duration_hours / 1000,
    )

    # === WEITER-SO: gebremster EE-Ausbau + fossile Bestandsflotte + Importe ===
    # Backup besteht aus der bestehenden Kohle-/Gas-Flotte (sinkend bis 2038
    # Kohleausstieg, danach nur noch Gas). Wir rechnen konservativ mit
    # 65 GW Bestandsflotte 2030, 45 GW 2040, 30 GW 2050.
    if year < 2038:
        weiterso_fossil_gw = weiterso_coal_gas_gw
    elif year < 2045:
        weiterso_fossil_gw = weiterso_coal_gas_gw * 0.7  # nach Kohleausstieg
    else:
        weiterso_fossil_gw = weiterso_coal_gas_gw * 0.45  # zunehmende Stilllegung

    battery_avg_weiterso = battery_gw_weiterso * BATTERY_DURATION_HOURS / 24
    weiterso_coverage = {
        "Batterien (gemittelt)": battery_avg_weiterso,
        "Fossile Bestandsflotte": min(
            weiterso_fossil_gw, max(0, weiterso_residual_gw - battery_avg_weiterso)
        ),
        "Importe": min(
            ws.import_max_gw,
            max(0, weiterso_residual_gw - battery_avg_weiterso - weiterso_fossil_gw),
        ),
        "Biomasse-Flex": BIOMASS_FLEX_GW,
        "DSM": min(5.0, weiterso_residual_gw * 0.03),  # WEITER-SO hat wenig DSM-Investition
    }
    weiterso_total = sum(weiterso_coverage.values())
    weiterso_deficit = max(0, weiterso_residual_gw - weiterso_total)

    results["WEITER-SO"] = WinterStressResult(
        model="WEITER-SO",
        peak_demand_gw=peak_demand_gw_weiterso,
        ee_supply_gw=weiterso_ee_supply_gw,
        residual_gw=weiterso_residual_gw,
        coverage_by=weiterso_coverage,
        coverage_total_gw=weiterso_total,
        deficit_gw=weiterso_deficit,
        energy_deficit_twh=weiterso_deficit * ws.duration_hours / 1000,
        cost_premium_eur_mwh=350 if weiterso_deficit < 5 else 800,  # fossile Spitzenpreise + CO2
        storage_drain_twh=battery_avg_weiterso * ws.duration_hours / 1000,
    )

    # multi_event_factor skaliert Energie-Größen für sequenzielle
    # Mehrfach-Dunkelflauten. Default 1.0 = Single-Event; Worst-Case 3.0.
    # Stunden-bezogene Größen (peak_demand_gw, deficit_gw,
    # cost_premium_eur_mwh) bleiben unberührt — eine zweite Dunkelflaute
    # in derselben Saison hat dieselbe Spitzenlast wie die erste.
    if ws.multi_event_factor != 1.0:
        for r in results.values():
            r.energy_deficit_twh *= ws.multi_event_factor
            r.storage_drain_twh *= ws.multi_event_factor

    return results


# =============================================================================
# Schatten-Andockung
# =============================================================================
#
# `winter_stress_balance` ist die Konsumenten-Schnittstelle für die
# Schatten-Pipeline. Statt eigener Kapazitäts- und Backup-Setzungen liest
# sie aus `compute_path(system_state=DUNKELFLAUTE)`:
#
# - Kapazitäten pro Tech (PathResult.capacity_buildup) — die EE-Schicht
#   und KKW-Schicht der Dunkelflaute kommen direkt aus dem Schatten.
# - Boost-Brennstoff-Verfügbarkeit pro Brennstoff (PathResult.fuel_used
#   im DUNKELFLAUTE-State liefert die Mengen unter Boost-Bedingungen). Diese
#   TWh-Mengen werden über die Dunkelflauten-Dauer auf GW umgerechnet.
#
# `winter_stress_test` (Default-Konfiguration, GW-basiert) bleibt für
# den Standard-Aufruf erhalten; `winter_stress_balance` rechnet
# Mengen-basiert und stellt damit die Konsistenz zur LCOE/Mix-Berechnung
# explizit her.

# EE-Techs in der Stress-Bilanz. Wasser/Bio/Müll-KWK kommen über
# `WinterStressParams.winter_supply_ee_gw` als 8 GW Sockel rein —
# `winter_stress_balance` zieht die EE-Kapazitäten direkt aus dem Schatten
# und multipliziert mit ws.pv/wind_capacity_factor.
_EE_TECHS: tuple[str, ...] = ("pv", "wind_onshore", "wind_offshore")

# Backup-Techs mit Brennstoff-Begrenzung. Sortierung gibt Merit-Order in
# der Dunkelflaute vor (KKW Grundlast vor Bridge-Gas vor Bestand-Gas vor
# Kohle-Auslauf vor Bio). Pro Tech wird die GW-Verfügbarkeit über die
# Stress-Dauer aus der Boost-Mengen-Bilanz des Pfad-Modells abgeleitet.
_BACKUP_TECHS: tuple[str, ...] = (
    "kkw_bestand",
    "kkw_neubau_epr",
    "kkw_neubau_smr",
    "gas_h2ready",
    "erdgas_bestand",
    "kohle",
    "bio",
)


@dataclass
class WinterStressResultBalance:
    """Mengen-Bilanz-Andockungs-Resultat pro Pfad. Konsistent mit der
    Schatten-Pipeline aus `core/path_model.py` (system_state=DUNKELFLAUTE).

    Felder ähneln `WinterStressResult`, aber jede GW-Zahl ist aus dem
    Schatten abgeleitet (entweder direkt aus
    `PathResult.capacity_buildup` oder aus Brennstoff-Verfügbarkeit
    umgerechnet über `WinterStressParams.duration_hours`).
    """

    path_id: str
    year: int
    camp: str
    peak_demand_gw: float
    ee_supply_gw: float
    residual_gw: float
    backup_by_tech_gw: dict[str, float]
    backup_total_gw: float
    deficit_gw: float
    energy_deficit_twh: float
    storage_drain_twh: float
    path_result: PathResult
    """Die zugrundeliegende Schatten-Mengen-Bilanz im DUNKELFLAUTE-State.
    Macht die Rückführbarkeit der Stress-Werte auf die Inventar-Source-
    Tags explizit (PathResult.provenance)."""


def winter_stress_balance(
    year: int,
    demand: Demand,
    camp: str = "neutral_default",
    *,
    paths: tuple[str, ...] = PATH_IDS,
    ws: WinterStressParams | None = None,
    electrification_scaling: float = 1.0,
    battery_share: dict[str, float] | None = None,
    bat_system_gw: float = 108.0,
    param_set: str | None = None,
) -> dict[str, WinterStressResultBalance]:
    """Stresstest auf Basis der Schatten-Pipeline.

    Pro Pfad:

    1. `compute_path(path, [year], lager, system_state=DUNKELFLAUTE)` liefert
       Kapazitäten und Boost-Brennstoff-Bilanz.
    2. `peak_demand_gw` aus `ws.winter_demand_gw(...)` — dieselbe Logik
       wie heute, aber konsistent zur Demand-Kurve des Pfad-Modells.
    3. `ee_supply_gw` aus den Pfad-Modell-Kapazitäten (pv/wind_onshore/wind_offshore)
       mit `ws.pv_capacity_factor` / `ws.wind_capacity_factor`. Plus
       8 GW Sockel (Wasser/Bio/Müll, identisch zu `winter_supply_ee_gw`).
    4. `backup_by_tech_gw` aus den Boost-Mengen pro Brennstoff,
       umgerechnet als `fuel_used_twh × 1000 / duration_hours = GW
       gemittelt über Dunkelflaute`. KKW ist Mengen-unbegrenzt (Uran-
       Verfügbarkeit 500 TWh > KKW-Bedarf), läuft mit
       installierter Kapazität × backup_availability.
    5. `deficit_gw = max(0, peak - ee - backup - import - battery)`.

    `battery_share` (default: Pfad-Anteile aus heutigem
    `winter_stress_test`, 55,6 % aktive Pfade / 11,1 % WEITER-SO /
    27,8 % BESTAND) skaliert das System-Batterie-Total `bat_system_gw`
    pro Pfad.
    """
    # Lokal-Import vermeidet Zyklus auf Modul-Lade-Ebene.
    from enesys.core.inventories import (
        FUEL_INVENTORY,
        PATH_POLICY,
        TECH_INVENTORY,
    )
    from enesys.core.path_model import compute_path

    if ws is None:
        ws = WinterStressParams()

    if battery_share is None:
        battery_share = {
            "ee_gas": 0.556,
            "ee_h2": 0.556,
            "kkw_gas": 0.556,
            "kkw_h2": 0.556,
            "weiterso": 0.111,
            "bestand": 0.278,
        }

    avail = ws.backup_availability
    base_demand_twh = demand.total_twh()

    results: dict[str, WinterStressResultBalance] = {}

    for path_id in paths:
        path_results = compute_path(
            path_id,
            [year],
            camp,
            system_state=SystemState.DUNKELFLAUTE,
            param_set=param_set,
        )
        if not path_results:
            continue
        path = path_results[0]

        # 2. Spitzenlast — Pfad-spezifische Sektorkopplungs-Bremse.
        # WEITER-SO 0,60, BESTAND 0,70 (siehe `_compute_demand_year`).
        if path_id == "weiterso":
            peak_scaling = electrification_scaling * 0.60
        elif path_id == "bestand":
            peak_scaling = electrification_scaling * 0.70
        else:
            peak_scaling = electrification_scaling
        peak_demand_gw = ws.winter_demand_gw(
            base_demand_twh,
            demand,
            electrification_scaling=peak_scaling,
        )

        # 3. EE-Supply aus Pfad-Modell-Kapazitäten in der Dunkelflaute.
        # Wasser und Bio sind jeweils eigene Schicht in backup_by_tech_gw
        # (Wasser mit Pumpspeicher-Boost via vlh_max_boost).
        ee_caps_gw = {t: path.capacity_buildup.get(t, 0.0) for t in _EE_TECHS}
        pv_gw = ee_caps_gw["pv"] * ws.pv_capacity_factor
        won_gw = ee_caps_gw["wind_onshore"] * ws.wind_capacity_factor
        woff_gw = ee_caps_gw["wind_offshore"] * ws.wind_capacity_factor * 1.5
        ee_supply_gw = (pv_gw + won_gw + woff_gw) * avail
        residual_gw = max(0.0, peak_demand_gw - ee_supply_gw)

        # 4. Backup-GW pro Tech aus der Boost-Mengen-Bilanz des Pfad-Modells.
        # Brennstoff-begrenzte Techs: TWh × 1000 / Stunden = GW-Mittel.
        # KKW (uran ist 500 TWh-Plausi-Limit, faktisch unlimitiert für DE):
        # Verwende installierte Kapazität × Verfügbarkeit.
        backup_by_tech_gw: dict[str, float] = {}
        # uran-getriebene Techs nutzen Kapazität direkt
        for tech_id in ("kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"):
            backup_by_tech_gw[tech_id] = path.capacity_buildup.get(tech_id, 0.0) * avail

        # DSM: Lastflex ohne Brennstoff,
        # in der Dunkelflaute mit installierter GW × Verfügbarkeit abrufbar.
        # vlh_max_boost = 1.500 h reicht für mehrere Dunkelflauten pro Jahr.
        backup_by_tech_gw["dsm"] = path.capacity_buildup.get("dsm", 0.0) * avail

        # Wasser (»Pumpspeicher-
        # Boost im Stress berücksichtigt?«): vlh_max_boost / vlh_normal
        # aktiviert den Pumpspeicher-Anteil im Bestand als zusätzliche
        # Dunkelflauten-Reserve. 5 GW × (4500/3500) × 0,95 ≈ 6,1 GW
        # (vorher 4,75 GW reine Nameplate). Kommentar im TechEntry
        # für Wasser dokumentiert diese Logik.
        wasser_tech = TECH_INVENTORY["wasser"]
        wasser_boost_faktor = (
            wasser_tech.vlh_max_boost / wasser_tech.vlh_normal
            if wasser_tech.vlh_max_boost and wasser_tech.vlh_normal > 0
            else 1.0
        )
        backup_by_tech_gw["wasser"] = (
            path.capacity_buildup.get("wasser", 0.0) * wasser_boost_faktor * avail
        )

        # Importe: jetzt eigene Tech im Pfad-Modell, nicht mehr Modul-Konstante.
        # installed × avail.
        backup_by_tech_gw["importe"] = path.capacity_buildup.get("importe", 0.0) * avail

        # Brennstoff-begrenzte Techs: Boost-Verfügbarkeit direkt aus
        # FUEL_INVENTORY[fuel].boost_max_twh_per_year, gefiltert über
        # PATH_POLICY[path].fuel_constraints (forbidden/stop/phaseout).
        #
        # Stress-Dauer-basierte Logik: In der Dunkelflauten-Periode (ws.duration_hours,
        # typisch 240 h) kann brennstoff-getragene Tech mit installierter
        # GW × Verfügbarkeit laufen, solange das Brennstoff-Jahresbudget
        # für die Stress-Periode reicht. Brennstoff-Bedarf für volle Last:
        #   installed_gw × duration_h / 1000 / efficiency_el  (TWh thermisch)
        # Wenn fuel_avail ≥ Bedarf: GW = installed_gw × avail.
        # Sonst: GW = fuel_avail × efficiency_el × 1000 / duration_h.
        policy = PATH_POLICY[path_id]
        # Guard gegen duration_hours=0 in
        # Sensi-Konfigurationen (extreme Dunkelflauten-Setups).
        duration_h = max(1.0, ws.duration_hours)
        for tech_id in ("gas_h2ready", "erdgas_bestand", "kohle", "bio", "strategische_reserve"):
            installed_gw = path.capacity_buildup.get(tech_id, 0.0)
            tech = TECH_INVENTORY[tech_id]
            eta_el = tech.efficiency_el
            tech_fuel_avail_twh_th = 0.0
            for fuel_id in tech.fuel_set:
                fuel_constraint = policy.fuel_constraints.get(fuel_id, "")
                if fuel_constraint in ("stop", "forbidden"):
                    continue
                if fuel_constraint.startswith("phaseout_"):
                    phaseout_year = int(fuel_constraint.split("_", 1)[1])
                    if year >= phaseout_year:
                        # boost_policy weicht phaseout im
                        # Stress auf (Erdgas-Notfall-Rückfall für
                        # EE-H2/KKW-H2 in der Dunkelflaute).
                        if not policy.boost_policy.get(fuel_id, False):
                            continue
                tech_fuel_avail_twh_th += FUEL_INVENTORY[fuel_id].boost_max_twh_per_year(year, camp)
            # Maximal-Strom-Output während Stress-Periode (TWh):
            #   installed_gw × duration_h / 1000
            # Brennstoff-Bedarf dazu (thermisch, TWh):
            #   strom_max / eta_el
            strom_max_twh = installed_gw * duration_h / 1000.0
            fuel_demand_twh_th = strom_max_twh / eta_el if eta_el > 0 else 0.0
            if fuel_demand_twh_th <= tech_fuel_avail_twh_th:
                # Brennstoff reicht, Hardware-Limit greift
                stress_gw = installed_gw
            else:
                # Brennstoff-limitiert: maximaler Strom über Dauer
                stress_gw = tech_fuel_avail_twh_th * eta_el * 1000.0 / duration_h
            backup_by_tech_gw[tech_id] = stress_gw * avail

        # Batterien: Pfad-Anteil × System × Mittel über Dauer.
        bat_pfad = bat_system_gw * battery_share.get(path_id, 0.0) * avail
        battery_avg_gw = bat_pfad * BATTERY_DURATION_HOURS / 24

        # Importe + DSM + Biomasse-Flex (Modul-Konstante, getrennt von
        # bio-Tech-Boost) als zusätzliche Beiträge.
        backup_total_gw = (
            sum(backup_by_tech_gw.values()) + battery_avg_gw + ws.import_max_gw + BIOMASS_FLEX_GW
        )

        deficit_gw = max(0.0, residual_gw - backup_total_gw)
        energy_deficit_twh = deficit_gw * ws.duration_hours / 1000.0 * ws.multi_event_factor
        storage_drain_twh = battery_avg_gw * ws.duration_hours / 1000.0 * ws.multi_event_factor

        results[path_id] = WinterStressResultBalance(
            path_id=path_id,
            year=year,
            camp=camp,
            peak_demand_gw=peak_demand_gw,
            ee_supply_gw=ee_supply_gw,
            residual_gw=residual_gw,
            backup_by_tech_gw=backup_by_tech_gw,
            backup_total_gw=backup_total_gw,
            deficit_gw=deficit_gw,
            energy_deficit_twh=energy_deficit_twh,
            storage_drain_twh=storage_drain_twh,
            path_result=path,
        )

    return results
