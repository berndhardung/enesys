"""Flächen-Modell für die sechs Pfade — Flächen-Bilanz pro Pfad.

Zweck:
    Quantifiziert den Flächenbedarf der sechs Pfade (WEITER-SO, BESTAND,
    EE-GAS, EE-H2, KKW-GAS, KKW-H2) auf Basis der PATH_MIXES und externer
    Kennzahlen (PV-Belegung, Wind-Leistungsdichte, KKW-Site-Größe,
    Tagebau-Bestand).

    Das Modell ist kein Substitute für Detail-Planung, sondern für den
    quantitativen Vergleich zwischen den Pfaden auf Aggregat-Niveau.

Konsistenz-Prinzip:
    - Erzeugungsanteile kommen direkt aus path_sensitivity.PATH_MIXES
    - Strombedarf 2045 ist die zentrale Skalierungs-Konstante
    - PV-Belegungsdichte, Wind-Leistungsdichte, KKW-Site-Größe sind
      mit Quellen-Tag dokumentiert
    - Die Ausgabe von compute_path_flaeche() materialisiert die
      Flächenbilanz pro Pfad (Tiefen-Box: Flächenbedarf)
    - Tests in tests/extensions/test_landuse_consistency.py verifizieren,
      dass die Ziel-Werte mit der Modell-Ausgabe übereinstimmen

Quellen-Tag-Konvention (wie im Hauptmodell, siehe core/source_trace.py):
    [SRC: TAG]      = belegt durch externe Quelle
    [CALIBRATED: ]  = aus Quellen hergeleitet, mit Begründung
    [ASSUMPTION: ]  = Schätzung ohne harte Quelle, mit Begründung
    [MODEL: ]       = Modell-interne Konstante, z. B. aus PATH_MIXES
"""

from __future__ import annotations

from dataclasses import dataclass

from enesys.core.path_sensitivity import PATH_MIXES, PATH_NAMES

# =============================================================================
# Flächen-Kennzahlen pro Technologie
# =============================================================================


@dataclass(frozen=True)
class LanduseParams:
    """Flächen-Kennzahlen pro Technologie und Pfad-Bestand.

    Alle Werte mit Quelle. Werden für die compute_path_flaeche()-Funktion
    genutzt. Frozen, damit sie versehentlich nicht modifiziert werden —
    Tests können bei Änderungen gezielt nachziehen.
    """

    # ---- Strombedarf 2045 (TWh/Jahr) ----------------------------------------

    strombedarf_twh_2045: float = 703.0
    """Jahresstrombedarf Deutschland 2045.
    [SRC: MODEL-DEFAULT] Konsistent zum Modell-Default, basiert auf
    Sektorkopplungs-Annahmen (Mobilität, Wärme, Industrie, Sockel)."""

    # ---- Photovoltaik (Freifläche) ------------------------------------------

    pv_belegung_mw_pro_ha: float = 1.0
    """Belegungsdichte PV-Freifläche: 1,0 MWp/Hektar.
    [SRC: ISE] Mittlerer Wert aus Fraunhofer-ISE-Bandbreite 1,0-1,25 MWp/ha.
    Konservativ nach unten gerundet (kleinere Anlagen, größere Modulabstände
    für Wartung/Reinigung)."""

    pv_vlh_h_pro_jahr: float = 1000.0
    """Volllaststunden Freiflächen-PV.
    [SRC: ISE] Typischer Süddeutschland-Standort 1000-1100 h/a, hier konservativ
    1000 h/a (ergibt 1.000 MWh/ha/Jahr)."""

    pv_dach_anteil: float = 0.66
    """Anteil PV auf Dächern (Gebäude/Fassaden, nicht flächenwirksam).
    [SRC: ISE] Fraunhofer-ISE-Annahme: ca. 2/3 der PV-Leistung auf Dächern,
    1/3 auf Freiflächen — bei den nötigen Zubau-Mengen."""

    # ---- Wind onshore -------------------------------------------------------

    wind_onshore_leistungsdichte_mw_pro_km2: float = 26.0
    """Leistungsdichte Wind onshore: 26 MW/km² Vorrangfläche.
    [SRC: FfE] Mittelwert aus FfE-Discussion-Paper 23-29 MW/km². Wert gilt
    für ausgewiesene Vorrangflächen, NICHT für versiegelte Anlagenfläche
    (die ist 1-2 Prozent davon)."""

    wind_onshore_vlh_h_pro_jahr: float = 2200.0
    """Volllaststunden Wind onshore (Mittel über alle Standorte).
    [SRC: ISE-2024] DE-Mittelwert; KernD-Bewertung 2024 sieht historisches Mittel bei ~1.850 VLh, neue Anlagen mit größeren Rotoren erreichen 2.200-2.500."""

    # ---- Wind offshore ------------------------------------------------------

    wind_offshore_leistungsdichte_mw_pro_km2: float = 8.0
    """Leistungsdichte Wind offshore: 8 MW/km² (Park-Mittelwert inkl. Abstände).
    [SRC: BSH] Bundesamt für Seeschifffahrt und Hydrographie, mittlere Belegung
    deutscher Offshore-Parks. Größere Abstände als onshore wegen Anströmung
    und Wartungs-Korridore."""

    wind_offshore_vlh_h_pro_jahr: float = 4200.0
    """Volllaststunden Wind offshore.
    [SRC: ISE-2024] DE-Bandbreite 3.500-4.500 VLh, Modell wählt oberen Rand für moderne Großanlagen Nordsee/Ostsee."""

    # ---- Kernkraft ----------------------------------------------------------

    kkw_site_km2_pro_block: float = 1.5
    """Flächenbedarf pro KKW-Site (1500-MW-Block) inklusive Sicherheitsabstand.
    [ASSUMPTION: 1,0-2,0 km²] Mittelwert. Reine Anlagenfläche ist ca. 0,3 km²,
    plus Sicherheitsabstand, Schaltanlagen, Kühlturm, Notfallzufahrt. Der
    Uran-Bergbau (außerhalb DE) wird hier NICHT mitgerechnet — das wäre
    zusätzlich 0,5-5 km² pro GW-Lebenszyklus, je nach Lagerstätte."""

    kkw_block_gw: float = 1.5
    """Bruttoleistung eines Standard-KKW-Blocks (EPR2-Klasse).
    [SRC: EDF-EPR-Specifications, EPR2 1.500-1.670 MWe netto je Block]"""

    # ---- Tagebau-Bestand (Status quo) ---------------------------------------

    tagebau_bestand_km2: float = 1794.0
    """Kumulierter Flächenverbrauch Braunkohletagebau Deutschland.
    [SRC: STATISTIK-KOHLENWIRTSCHAFT] 179.402 Hektar = 1.794 km² seit Beginn
    der Abbautätigkeit. Davon ca. 1.240 km² rekultiviert, der Rest aktiv,
    in Stilllegung oder als Restloch/See."""

    tagebau_zuwachs_ha_pro_tag: float = 1.2
    """Aktueller Zuwachs Braunkohle-Tagebauflächen.
    [SRC: UBA-2024] Der Wert sinkt mit dem Kohleausstieg (war 2017 noch
    2,1 ha/Tag, 2024 1,2 ha/Tag)."""

    # ---- Pfad-Trajektorien-Annahmen -----------------------------------------

    weiter_so_tagebau_zuwachs_jahre: int = 13
    """WEITER-SO: Tagebauzuwachs läuft bis 2038 (Kohleausstieg-Gesetz).
    [SRC: KohleAusG §2 (Kohleausstieg 2038); 2025-2038 = 13 Jahre × 1,2 ha/Tag × 365 Tage]"""

    kkw_pfad_anzahl_bloecke: int = 10
    """Anzahl neuer KKW-Blöcke in den KKW-Pfaden bis 2045.
    [ASSUMPTION: Realismus-Check Landnutzung — 5-10 baubare Blöcke bis 2045/2050; oberer Rand der Bandbreite]"""


DEFAULT_LANDUSE_PARAMS = LanduseParams()


# =============================================================================
# Hauptfunktion: Flächenbedarf pro Pfad
# =============================================================================


@dataclass(frozen=True)
class PathLanduseResult:
    """Strukturiertes Ergebnis für einen Pfad.

    Alle Felder in km².
    """

    path: str
    pv_freiflaeche_km2: float
    wind_onshore_km2: float
    wind_offshore_km2: float
    ee_summe_km2: float
    kkw_sites_km2: float
    tagebau_km2: float
    gesamt_km2: float

    def to_dict(self) -> dict:
        """Für Tests, Tabellen-Generierung und Dashboard-Export."""
        return {
            "path": self.path,
            "pv_freiflaeche_km2": self.pv_freiflaeche_km2,
            "wind_onshore_km2": self.wind_onshore_km2,
            "wind_offshore_km2": self.wind_offshore_km2,
            "ee_summe_km2": self.ee_summe_km2,
            "kkw_sites_km2": self.kkw_sites_km2,
            "tagebau_km2": self.tagebau_km2,
            "gesamt_km2": self.gesamt_km2,
        }


def compute_path_landuse(
    path: str,
    params: LanduseParams | None = None,
) -> PathLanduseResult:
    """Berechnet den Flächenbedarf für einen der sechs Pfade.

    Args:
        path: Pfadname (eines aus PATH_NAMES).
        params: LanduseParams. Default: DEFAULT_LANDUSE_PARAMS.

    Returns:
        PathLanduseResult mit aufgeschlüsselten und summierten km²-Werten.

    Raises:
        ValueError: Wenn path kein gültiger Pfadname ist.

    Methode:
        1. Erzeugung pro Technologie ableiten:
           erzeugung_twh = strombedarf × mix_anteil
        2. Installierte Leistung ableiten (über VLH):
           leistung_gw = erzeugung_twh × 1000 / vlh
        3. Fläche aus Leistung × Belegungsdichte
        4. PV: nur Freiflächen-Anteil ist flächenwirksam (Dächer = 0)
        5. KKW-Sites: feste Anzahl (10) × Site-Größe für KKW-Pfade
        6. Tagebau: Bestand 1.794 km², bei WEITER-SO + Zuwachs bis 2038
    """
    if params is None:
        params = DEFAULT_LANDUSE_PARAMS

    if path not in PATH_NAMES:
        raise ValueError(f"Unbekannter Pfad '{path}'. Gültige Pfade: {PATH_NAMES}")

    mix = PATH_MIXES[path]

    # --- PV-Freifläche ----------------------------------------------------
    pv_anteil_gesamt = mix.get("pv", 0.0)
    pv_erzeugung_twh = params.strombedarf_twh_2045 * pv_anteil_gesamt
    pv_leistung_gw = (pv_erzeugung_twh * 1000) / params.pv_vlh_h_pro_jahr
    # Nur ein Anteil davon ist flächenwirksam (Rest ist auf Dächern)
    pv_frei_leistung_gw = pv_leistung_gw * (1.0 - params.pv_dach_anteil)
    # Belegung: 1 MW/ha = 1.000 MW/km² → GW × 1.000 / (MW/km²) → km²
    pv_freiflaeche_km2 = pv_frei_leistung_gw * 1000 / (params.pv_belegung_mw_pro_ha * 100)
    # Erklärung Faktor 100: 1 MW/ha = 100 MW/km²
    # Also: leistung_mw / (mw_pro_ha × 100) = km²

    # --- Wind onshore -----------------------------------------------------
    wind_on_anteil = mix.get("wind_onshore", 0.0)
    wind_on_erzeugung_twh = params.strombedarf_twh_2045 * wind_on_anteil
    wind_on_leistung_gw = wind_on_erzeugung_twh * 1000 / params.wind_onshore_vlh_h_pro_jahr
    wind_onshore_km2 = wind_on_leistung_gw * 1000 / params.wind_onshore_leistungsdichte_mw_pro_km2

    # --- Wind offshore (zur Vollständigkeit, in Tabelle nicht ausgewiesen) ---
    wind_off_anteil = mix.get("wind_offshore", 0.0)
    wind_off_erzeugung_twh = params.strombedarf_twh_2045 * wind_off_anteil
    wind_off_leistung_gw = wind_off_erzeugung_twh * 1000 / params.wind_offshore_vlh_h_pro_jahr
    wind_offshore_km2 = (
        wind_off_leistung_gw * 1000 / params.wind_offshore_leistungsdichte_mw_pro_km2
    )
    # Hinweis: Offshore-Flächen liegen in der AWZ, nicht auf Land — sie
    # werden daher nicht zur Land-Flächen-Summe gezählt.

    ee_summe_km2 = pv_freiflaeche_km2 + wind_onshore_km2

    # --- KKW-Sites --------------------------------------------------------
    nuclear_anteil = mix.get("nuclear", 0.0)
    if nuclear_anteil > 0:
        # Anzahl Blöcke aus dem Pfad-Mix ableiten
        kkw_erzeugung_twh = params.strombedarf_twh_2045 * nuclear_anteil
        # KKW: 8000 VLH typisch, 1,5 GW Block
        kkw_leistung_gw = kkw_erzeugung_twh * 1000 / 8000
        n_bloecke = round(kkw_leistung_gw / params.kkw_block_gw)
        kkw_sites_km2 = n_bloecke * params.kkw_site_km2_pro_block
    else:
        kkw_sites_km2 = 0.0

    # --- Tagebau ----------------------------------------------------------
    tagebau_km2 = params.tagebau_bestand_km2
    if path == "WEITER-SO":
        # Zuwachs bis Kohleausstieg
        zuwachs_ha = (
            params.tagebau_zuwachs_ha_pro_tag * 365 * params.weiter_so_tagebau_zuwachs_jahre
        )
        zuwachs_km2 = zuwachs_ha / 100  # 1 km² = 100 ha
        tagebau_km2 += zuwachs_km2

    # --- Gesamt -----------------------------------------------------------
    gesamt_km2 = ee_summe_km2 + kkw_sites_km2 + tagebau_km2

    return PathLanduseResult(
        path=path,
        pv_freiflaeche_km2=pv_freiflaeche_km2,
        wind_onshore_km2=wind_onshore_km2,
        wind_offshore_km2=wind_offshore_km2,
        ee_summe_km2=ee_summe_km2,
        kkw_sites_km2=kkw_sites_km2,
        tagebau_km2=tagebau_km2,
        gesamt_km2=gesamt_km2,
    )


def compute_all_paths(
    params: LanduseParams | None = None,
) -> dict[str, PathLanduseResult]:
    """Convenience: Flächenbedarf für alle sechs Pfade als Dict."""
    return {p: compute_path_landuse(p, params) for p in PATH_NAMES}
