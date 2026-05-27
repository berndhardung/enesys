"""Demand-Schicht von enesys.

Aggregierte Stromnachfrage Deutschlands für die Trajektorie 2026-2055,
zerlegt in vier Sektoren mit Sektorkopplungs-Logik:

    - Sockel Haushalt + Gewerbe (Basisnachfrage, heute ~220 TWh)
    - Mobilität (PKW + Nutzfahrzeuge, e_anteil-skaliert)
    - Wärme (Wärmepumpen, COP-abhängig)
    - Industrie (klassisch + H2-Stromäquivalent + Direktelektrifizierung)

GHD ist im Modell im Sockel enthalten (Pauschal-Sockel-Ansatz).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ===========================================================================
# DSM-KONSTANTEN
# ===========================================================================

PKW_DSM_TAGES_VERSCHIEBBAR_ANTEIL: float = 0.5
"""Anteil des PKW-Tages-Stroms, der per DSM verschiebbar ist.

Heute typische Annahme: ~50 % des Lade-Volumens kann innerhalb eines
Tages zeitlich verschoben werden (z.B. Nacht-Laden statt Abend-Spitze,
oder Solar-Mittag statt Morgen).

[ASSUMPTION: konservativ; aktuelle Smart-Charging-Studien (BNEF 2025,
ISE-Wärmesektor-Kopplung) zeigen Bandbreiten 30-70 % je nach Anreiz-
Struktur. Bei höheren CO₂-Preisen und dynamischen Tarifen wird der
Wert tendenziell steigen.]

Wird in `MobilityParams.flex_potential_gwh()` verwendet.
"""


@dataclass
class MobilityParams:
    """PKW-Elektrifizierung als Treiber des Strombedarfs

    Wirkungsgrad-Vergleich (Diskussions-Anker):
        Verbrenner-PKW: ~7 L/100km × 9.7 kWh/L = 68 kWh/100km Endenergie
        E-Auto:         18 kWh/100km Endenergie
        Effizienz-Faktor: ~3.8 (E-Auto braucht ~26% des Verbrenner-Inputs)

    Diese Asymmetrie wird über `verbrauch_kwh_pro_100km` direkt eingerechnet.

    QUELLEN (siehe SOURCES.md für Details):
    - PKW-Bestand: KBA 2024 (Kraftfahrt-Bundesamt)
    - Jahresfahrleistung: KBA 2024
    - kWh/100km: ADAC E-Auto-Tests, BNEF EV-Survey 2025
    - Heizwert Benzin: physikalische Konstante
    """

    pkw_bestand_mio: float = 49.0  # [SRC: KBA-2024]
    jahresfahrleistung_km: float = 13_500  # [SRC: KBA-2024]
    verbrauch_kwh_pro_100km: float = 18.0  # [SRC: ADAC-2024, Mix]
    electric_share: float = 0.80  # [ASSUMPTION: 80% E-PKW-Anteil im Bestand 2045 — entspricht 100% Neuzulassung ab 2035 plus Bestandsumlauf]
    ladeverlust_pct: float = 0.10  # Lade- und Netzverluste  [CALIBRATED: VDE-Standard]
    nutzfahrzeuge_zusatz_twh: float = 25.0  # [SRC: NPM-2023]
    commercial_vehicles_electric_share: float = 0.60  # [ASSUMPTION: 60% E-LKW-Anteil 2045 — konservativer als PKW wegen längerer Nutzungsdauer]

    # Wirkungsgrad-Vergleichswerte (Diskussions-Anker, nicht für die Demand-Rechnung)
    verbrenner_l_pro_100km: float = 7.0  # Verbrenner-Bestandsmittel  [SRC: KBA-2024]
    benzin_kwh_pro_liter: float = 9.7  # Heizwert Benzin  [CALIBRATED: physikalische Konstante]

    def electricity_consumption_twh(self) -> float:
        """Jahresstrombedarf Mobilität in TWh"""
        pkw_kwh_pro_jahr = self.jahresfahrleistung_km / 100 * self.verbrauch_kwh_pro_100km
        pkw_twh = (
            self.pkw_bestand_mio
            * 1e6
            * pkw_kwh_pro_jahr
            * self.electric_share
            * (1 + self.ladeverlust_pct)
        ) / 1e9
        nfz_twh = self.nutzfahrzeuge_zusatz_twh * self.commercial_vehicles_electric_share
        return pkw_twh + nfz_twh

    def flex_potential_gwh(self) -> float:
        """Verschiebbares Lade-Volumen pro Tag (GWh)

        Verwendet `PKW_DSM_TAGES_VERSCHIEBBAR_ANTEIL` (Default 50 %)
        als Modul-Konstante; Begründung dort.
        """
        return self.electricity_consumption_twh() * 1000 / 365 * PKW_DSM_TAGES_VERSCHIEBBAR_ANTEIL

    def wirkungsgrad_faktor(self) -> float:
        """Faktor um den E-Auto effizienter ist als Verbrenner.

        > 1 bedeutet E-Auto ist effizienter.
        """
        verbrenner_kwh_100km = self.verbrenner_l_pro_100km * self.benzin_kwh_pro_liter
        return verbrenner_kwh_100km / max(1e-9, self.verbrauch_kwh_pro_100km)

    def primary_energy_savings_twh(self) -> float:
        """Primärenergie-Einsparung gegenüber Verbrenner-Welt in TWh.

        Wenn alle 49 Mio. PKW elektrisch fahren würden mit gleicher Fahrleistung,
        wieviel Primärenergie spart das gegenüber Verbrenner-Welt?
        """
        verbrenner_kwh_100km = self.verbrenner_l_pro_100km * self.benzin_kwh_pro_liter
        verbrenner_total = (
            self.pkw_bestand_mio
            * 1e6
            * self.jahresfahrleistung_km
            / 100
            * verbrenner_kwh_100km
            * self.electric_share
        ) / 1e9  # was Verbrenner gebraucht hätten
        return verbrenner_total - self.electricity_consumption_twh()


@dataclass
class HeatingParams:
    """Wärmepumpen-Elektrifizierung

    Wirkungsgrad-Vergleich (Diskussions-Anker):
        Gas-Brennwertkessel: ~95% Wirkungsgrad → braucht 1.05 kWh Gas pro kWh Wärme
        Wärmepumpe COP 3.2:  → braucht 0.31 kWh Strom pro kWh Wärme
        Effizienz-Faktor:    ~3.4 (WP braucht ~30% der Endenergie der Gasheizung)

    Über `cop_jahres` direkt eingerechnet.

    QUELLEN (siehe SOURCES.md):
    - Heizungsbestand: BDEW Heizungs-Statistik 2024
    - Heizbedarf: BMWi Energiebilanz, dena-Gebäudereport
    - COP: BWP-Branchenstudien, Fraunhofer ISE WP-Monitoring
    """

    heizungen_bestand_mio: float = 21.5  # [SRC: BDEW-2024]
    heizbedarf_kwh_pro_jahr: float = 18_000  # Durchschnittswohnung  [SRC: AGEB-2024]
    heatpump_share: float = 0.60  # [ASSUMPTION: 60% WP-Anteil 2045 — Pfad nach GEG-Heizungsgesetz mit langsamerem Hochlauf als Flächenziel]
    cop_jahres: float = 3.2  # [SRC: BWP-2024, ISE-Monitoring]
    direct_electric_share: float = 0.05  # Heizstab/Spitzenlast  [CALIBRATED: BWP-Schätzung Heizstab-Anteil bei WP-Hybridsystemen]
    district_heat_share: float = 0.15  # [SRC: AGEB-2024]

    # Wirkungsgrad-Vergleichswerte
    gas_heating_efficiency: float = 0.95  # Brennwert-Wirkungsgrad  [CALIBRATED: BDH-Standard]

    def electricity_consumption_twh(self) -> float:
        """Jahresstrombedarf Wärme in TWh

        Die WP-Häuser brauchen nur (Bedarf / COP), Direktheizung 1:1.
        """
        relevant = 1 - self.district_heat_share
        wp_twh = (
            self.heizungen_bestand_mio
            * 1e6
            * self.heizbedarf_kwh_pro_jahr
            * relevant
            * self.heatpump_share
            / self.cop_jahres
        ) / 1e9
        # Direktheizungs-Anteil bleibt bestehen (Restmenge)
        rest_anteil = (1 - self.heatpump_share) * self.direct_electric_share
        direkt_twh = (
            self.heizungen_bestand_mio * 1e6 * self.heizbedarf_kwh_pro_jahr * relevant * rest_anteil
        ) / 1e9
        return wp_twh + direkt_twh

    def flex_potential_gwh(self) -> float:
        """Verschiebbares Heiz-Volumen (Pufferspeicher)

        Wärmepumpen mit Pufferspeicher: 6-12h Verschiebbarkeit
        """
        return self.electricity_consumption_twh() * 1000 / 365 * 0.30

    def wirkungsgrad_faktor(self) -> float:
        """Faktor um den Wärmepumpe effizienter ist als Gasheizung.

        Faktor = COP × Gasheizung-Wirkungsgrad
        """
        return self.cop_jahres * self.gas_heating_efficiency

    def primary_energy_savings_twh(self) -> float:
        """Primärenergie-Einsparung WP vs Gasheizung in TWh.

        Bei aktuellem WP-Anteil: wieviel Endenergie spart das gegenüber
        einer Welt mit nur Gasheizungen?
        """
        relevant = 1 - self.district_heat_share
        gas_endenergie = (
            self.heizungen_bestand_mio
            * 1e6
            * self.heizbedarf_kwh_pro_jahr
            * relevant
            * self.heatpump_share
            / self.gas_heating_efficiency
        ) / 1e9
        return gas_endenergie - self.electricity_consumption_twh()


@dataclass
class IndustryParams:
    """Industrie-Elektrifizierung und Wasserstoff-Bedarf

    Wirkungsgrad-Vergleich (analog zu Mobilität und Wärme):
        Industrieofen Erdgas:    ~85% Wirkungsgrad
        Elektrokessel:           ~99%
        Wärmepumpe Niedertemp:   COP ~3.5 (Prozesswärme bis 150°C)
        Mittlerer E-Faktor (Mix Niedertemp/Mitteltemp/Hochtemp): ~1.5

    Konstruktion analog zu mobility.e_anteil und heating.wp_anteil:
        Sockel (heutige klassische Stromnachfrage)
        + Direkte Elektrifizierung (Hebel direkt_elek_anteil auf
          fossile Endenergie, mittlerer Effizienz-Faktor)
        + Wasserstoff-Strom-Input (Stahl, Chemie, sonstige)

    QUELLEN (siehe SOURCES.md):
    - Klassische Industriestromnachfrage: AGEB-2024
    - Fossile Endenergie Industrie: AGEB-Energiebilanz 2024
    - Direktelektrifizierungs-Anteil: Ariadne 2025 H2-/Elektrifizierungs-Szenarien
    - Mittlerer E-Faktor: Agora Industrie 2019, BCG/Roland-Berger 2023
    - H2-Industrie-Bedarf: BMWK-H2-Strategie 2023
    """

    # Heutiger klassischer Sockel
    classic_electricity_twh: float = (
        230  # klass. Industrie heutige Stromnachfrage  [SRC: AGEB-2024]
    )

    # Heutige fossile Endenergie der Industrie (Erdgas, Öl, Kohle für Prozesswärme)
    industrie_endenergie_fossil_twh: float = (
        600  # heute fossile Endenergie Industrie  [SRC: AGEB-2024]
    )

    # Hebel: Anteil der heutigen fossilen Endenergie, der bis 2045 elektrifiziert wird
    direct_electric_share_industry: float = (
        0.35  # [ASSUMPTION: Mittelwert Ariadne H2- und Elektrifizierungs-Szenarien 2025]
    )

    # Mittlerer Effizienz-Faktor: 1 kWh fossile Endenergie ersetzt durch X kWh Strom
    elektrifizierungs_faktor: float = 1.5  # [CALIBRATED: Mix Niedertemp WP COP~3.5 + Mitteltemp E-Kessel ~1.0 + Hochtemp E-Ofen ~1.0]

    # H2-Komponenten (Strom-Input für Elektrolyse für nicht-elektrifizierbare Prozesse)
    h2_stahl_twh_strom: float = 30  # Strom für Stahl-DRI via H2  [SRC: BMWK-H2-STRATEGIE-2023]
    h2_chemie_twh_strom: float = 25  # Strom für Ammoniak/Methanol  [SRC: BMWK-H2-STRATEGIE-2023]
    h2_sonstige_twh_strom: float = 25  # Restposten Industrie-H2  [ASSUMPTION: Differenz zur 95-130 TWh Gesamtspanne BMWK-Strategie]

    def electricity_consumption_twh(self) -> float:
        """Gesamtstrombedarf Industrie 2045 (klassisch + Direktelektrifizierung + H2-Strom)."""
        elek_zusatz = (
            self.industrie_endenergie_fossil_twh
            * self.direct_electric_share_industry
            / self.elektrifizierungs_faktor
        )
        return (
            self.classic_electricity_twh
            + elek_zusatz
            + self.h2_stahl_twh_strom
            + self.h2_chemie_twh_strom
            + self.h2_sonstige_twh_strom
        )

    def direct_electrification_twh(self) -> float:
        """Strom-Bedarf aus Direktelektrifizierung (Tornado-Analyse)."""
        return (
            self.industrie_endenergie_fossil_twh
            * self.direct_electric_share_industry
            / self.elektrifizierungs_faktor
        )


@dataclass
class Demand:
    """Aggregierte Nachfrage 2045 mit expliziter Sektorkopplung.

    Setzt sich zusammen aus:
        - Sockel Haushalt + Gewerbe (heute ca. 220 TWh)
        - Mobilität (E-Pkw, Lkw)
        - Wärme (Wärmepumpen, COP-abhängig)
        - Industrie (klassische Stromnachfrage + H2-Stromäquivalent +
          Direktelektrifizierung)
    """

    base_household_commercial_twh: float = 220  # HH+Gewerbe heute  [SRC: AGEB-2024]
    mobility: MobilityParams = field(default_factory=MobilityParams)
    heating: HeatingParams = field(default_factory=HeatingParams)
    industry: IndustryParams = field(default_factory=IndustryParams)

    def total_twh(self) -> float:
        return (
            self.base_household_commercial_twh
            + self.mobility.electricity_consumption_twh()
            + self.heating.electricity_consumption_twh()
            + self.industry.electricity_consumption_twh()
        )

    def breakdown(self) -> dict[str, float]:
        return {
            "Sockel HH+Gew": self.base_household_commercial_twh,
            "Mobilität": self.mobility.electricity_consumption_twh(),
            "Wärme": self.heating.electricity_consumption_twh(),
            "Industrie": self.industry.electricity_consumption_twh(),
        }

    def total_flex_gwh_per_day(self) -> float:
        """Gesamtes verschiebbares Tagesvolumen"""
        return self.mobility.flex_potential_gwh() + self.heating.flex_potential_gwh()

    def primary_energy_savings_summary(self) -> dict[str, float]:
        """Primärenergie-Einsparung durch Sektorkopplung gegenüber fossiler Welt.

        Zentrale Modell-Erkenntnis: Sektorkopplung spart MEHR Primärenergie
        als die Stromproduktion selbst, weil Verbrenner und Gasheizungen
        Faktor 3-4 ineffizienter sind.
        """
        mob_save = self.mobility.primary_energy_savings_twh()
        heat_save = self.heating.primary_energy_savings_twh()
        return {
            "mobility_einsparung_twh": mob_save,
            "heating_einsparung_twh": heat_save,
            "total_einsparung_twh": mob_save + heat_save,
            "mobility_faktor": self.mobility.wirkungsgrad_faktor(),
            "heating_faktor": self.heating.wirkungsgrad_faktor(),
            "stromverbrauch_durch_sektorkopplung_twh": (
                self.mobility.electricity_consumption_twh()
                + self.heating.electricity_consumption_twh()
            ),
        }
