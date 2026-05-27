"""Konsistenz-Tests für das Flächen-Modell.

Diese Tests versiegeln drei Dinge:
    1. Die Soll-Werte in `LANDUSE_TARGETS_KM2` stimmen mit der
       Modell-Funktion überein.
    2. Plausibilitäts-Eigenschaften (Summen positiv, Reihenfolgen).
    3. Bei Änderungen der PATH_MIXES oder des Strombedarfs ziehen
       die Tests automatisch nach (Hauptmodell-Drift wird verhindert).

Wenn neue Quellen oder Belegungsdichten eingearbeitet werden müssen,
sind die Toleranzen hier die maßgebliche Stelle, an der die Ziel-Werte
festgeschrieben sind.
"""

from __future__ import annotations

import pytest

from enesys.core.path_sensitivity import PATH_NAMES
from enesys.extensions.landuse import (
    DEFAULT_LANDUSE_PARAMS,
    LanduseParams,
    compute_all_paths,
    compute_path_landuse,
)

# =============================================================================
# Modell-Soll-Tabelle
# =============================================================================
# Diese Tabelle ist die Modell-Soll-Schnittstelle für ``compute_path_landuse()``.
# ``TestModelMatchesTargets`` und ``TestPlausibility`` versiegeln den
# Modell-Output gegen sie.
#
# Toleranz: ±50 km² (auf 50er gerundet, ausreichend für die Modell-
# Plausibilitätsprüfung).

LANDUSE_TARGETS_KM2 = {
    # Pfad → {Spalte → Soll-Wert in km²}
    "WEITER-SO": {"ee_summe": 2300, "kkw_sites": 0, "tagebau": 1850, "gesamt": 4170},
    "EE-GAS": {"ee_summe": 4650, "kkw_sites": 0, "tagebau": 1800, "gesamt": 6450},
    "EE-H2": {"ee_summe": 4650, "kkw_sites": 0, "tagebau": 1800, "gesamt": 6450},
    "KKW-GAS": {"ee_summe": 2800, "kkw_sites": 30, "tagebau": 1800, "gesamt": 4630},
    "KKW-H2": {"ee_summe": 2800, "kkw_sites": 30, "tagebau": 1800, "gesamt": 4630},
    # BESTAND als sechster Pfad. Kleinster EE-Mix (~32 % statt 86 % bei
    # EE-Pfaden) → kleinste EE-Fläche (~1660 km² PV+Wind onshore). Kein
    # Atom (0 km² KKW-Sites). Tagebau wie bei aktiven Pfaden 1800
    # (BESTAND ohne Kohle, gleicher Tagebau wie EE-Pfade aus Restbergbau-
    # Sanierung). Gesamt ~3450 km².
    "BESTAND": {"ee_summe": 1660, "kkw_sites": 0, "tagebau": 1800, "gesamt": 3450},
}
TOLERANCE_KM2 = 60


# =============================================================================
# Tests Modell-Soll-Konsistenz
# =============================================================================


class TestModelMatchesTargets:
    """Versiegelt die Soll-Tabelle gegen die Modell-Berechnung."""

    @pytest.mark.parametrize("path", PATH_NAMES)
    def test_ee_summe_matches_target(self, path):
        """EE-Flächen-Summe (PV-Frei + Wind onshore) stimmt mit Soll."""
        result = compute_path_landuse(path)
        soll = LANDUSE_TARGETS_KM2[path]["ee_summe"]
        assert abs(result.ee_summe_km2 - soll) <= TOLERANCE_KM2, (
            f"{path}: EE-Summe {result.ee_summe_km2:.0f} km² weicht vom "
            f"Soll-Wert {soll} km² um mehr als {TOLERANCE_KM2} km² ab."
        )

    @pytest.mark.parametrize("path", PATH_NAMES)
    def test_kkw_sites_matches_target(self, path):
        """KKW-Flächen stimmen mit Soll."""
        result = compute_path_landuse(path)
        soll = LANDUSE_TARGETS_KM2[path]["kkw_sites"]
        # KKW-Sites sind kleine Werte — engere absolute Toleranz
        assert abs(result.kkw_sites_km2 - soll) <= 5, (
            f"{path}: KKW-Sites {result.kkw_sites_km2:.0f} km² weicht vom "
            f"Soll-Wert {soll} km² um mehr als 5 km² ab."
        )

    @pytest.mark.parametrize("path", PATH_NAMES)
    def test_tagebau_matches_target(self, path):
        """Tagebau-Flächen stimmen mit Soll."""
        result = compute_path_landuse(path)
        soll = LANDUSE_TARGETS_KM2[path]["tagebau"]
        assert abs(result.tagebau_km2 - soll) <= TOLERANCE_KM2, (
            f"{path}: Tagebau {result.tagebau_km2:.0f} km² weicht vom "
            f"Soll-Wert {soll} km² um mehr als {TOLERANCE_KM2} km² ab."
        )

    @pytest.mark.parametrize("path", PATH_NAMES)
    def test_gesamt_matches_target(self, path):
        """Gesamtsumme stimmt mit Soll."""
        result = compute_path_landuse(path)
        soll = LANDUSE_TARGETS_KM2[path]["gesamt"]
        assert abs(result.gesamt_km2 - soll) <= TOLERANCE_KM2, (
            f"{path}: Gesamt {result.gesamt_km2:.0f} km² weicht vom "
            f"Soll-Wert {soll} km² um mehr als {TOLERANCE_KM2} km² ab."
        )


# =============================================================================
# Tests Plausibilität
# =============================================================================


class TestPlausibility:
    """Plausibilitäts-Checks der Modell-Logik."""

    def test_all_results_positive(self):
        """Keine negativen Flächen."""
        for path in PATH_NAMES:
            r = compute_path_landuse(path)
            assert r.pv_freiflaeche_km2 >= 0
            assert r.wind_onshore_km2 >= 0
            assert r.wind_offshore_km2 >= 0
            assert r.ee_summe_km2 >= 0
            assert r.kkw_sites_km2 >= 0
            assert r.tagebau_km2 > 0  # Bestand immer > 0
            assert r.gesamt_km2 > 0

    def test_ee_summe_is_sum_of_components(self):
        """ee_summe = pv_freiflaeche + wind_onshore (offshore zählt nicht zu Land)."""
        for path in PATH_NAMES:
            r = compute_path_landuse(path)
            assert abs(r.ee_summe_km2 - (r.pv_freiflaeche_km2 + r.wind_onshore_km2)) < 0.5

    def test_gesamt_is_sum_of_parts(self):
        """gesamt = ee_summe + kkw_sites + tagebau."""
        for path in PATH_NAMES:
            r = compute_path_landuse(path)
            soll = r.ee_summe_km2 + r.kkw_sites_km2 + r.tagebau_km2
            assert abs(r.gesamt_km2 - soll) < 0.5

    def test_ee_pfade_brauchen_mehr_ee_flaechen_als_kkw(self):
        """EE-Pfade haben mehr EE-Anteil → mehr Fläche als KKW-Pfade."""
        ee_gas = compute_path_landuse("EE-GAS")
        kkw_gas = compute_path_landuse("KKW-GAS")
        assert ee_gas.ee_summe_km2 > kkw_gas.ee_summe_km2, (
            "EE-GAS sollte mehr EE-Fläche brauchen als KKW-GAS — "
            "sonst stimmen die PATH_MIXES nicht."
        )

    def test_weiter_so_hat_wachsenden_tagebau(self):
        """WEITER-SO ist der einzige Pfad mit weiter wachsendem Tagebau."""
        weiter_so = compute_path_landuse("WEITER-SO")
        ee_gas = compute_path_landuse("EE-GAS")
        assert weiter_so.tagebau_km2 > ee_gas.tagebau_km2

    def test_kkw_pfade_haben_kkw_sites(self):
        """KKW-Pfade haben Site-Flächen, EE-/WEITER-SO-Pfade nicht."""
        for path in ["KKW-GAS", "KKW-H2"]:
            r = compute_path_landuse(path)
            assert r.kkw_sites_km2 > 0
        for path in ["WEITER-SO", "EE-GAS", "EE-H2"]:
            r = compute_path_landuse(path)
            assert r.kkw_sites_km2 == 0

    def test_ee_gas_und_ee_h2_haben_identische_ee_flaechen(self):
        """Da PATH_MIXES für EE-GAS und EE-H2 identische EE-Anteile hat,
        müssen die EE-Flächen gleich sein."""
        ee_gas = compute_path_landuse("EE-GAS")
        ee_h2 = compute_path_landuse("EE-H2")
        assert abs(ee_gas.ee_summe_km2 - ee_h2.ee_summe_km2) < 0.5

    def test_kkw_gas_und_kkw_h2_haben_identische_ee_flaechen(self):
        """Analog für KKW-Pfade."""
        kkw_gas = compute_path_landuse("KKW-GAS")
        kkw_h2 = compute_path_landuse("KKW-H2")
        assert abs(kkw_gas.ee_summe_km2 - kkw_h2.ee_summe_km2) < 0.5

    def test_invalid_path_raises(self):
        with pytest.raises(ValueError, match="Unbekannter Pfad"):
            compute_path_landuse("NICHT-EXISTENT")

    def test_compute_all_paths_returns_one_per_path(self):
        """Liefert genau einen Eintrag pro Pfadnamen — dynamisch gegen PATH_NAMES."""
        results = compute_all_paths()
        assert set(results.keys()) == set(PATH_NAMES)
        assert len(results) == len(PATH_NAMES)


# =============================================================================
# Tests Sensitivität auf Parameter-Änderungen
# =============================================================================


class TestParameterSensitivity:
    """Stellt sicher, dass die Funktion auf Parameter-Änderungen reagiert
    — relevant, wenn Nutzer eigene Annahmen einsetzen wollen."""

    def test_doppelter_strombedarf_verdoppelt_ee_flaechen(self):
        """Linearität: doppelter Strombedarf → doppelte EE-Fläche."""
        base = compute_path_landuse("EE-GAS")
        doppelt = LanduseParams(
            strombedarf_twh_2045=DEFAULT_LANDUSE_PARAMS.strombedarf_twh_2045 * 2
        )
        result = compute_path_landuse("EE-GAS", doppelt)
        assert abs(result.ee_summe_km2 / base.ee_summe_km2 - 2.0) < 0.01

    def test_dichtere_pv_belegung_reduziert_pv_flaeche(self):
        """Höhere Belegungsdichte → weniger Fläche."""
        base = compute_path_landuse("EE-GAS")
        dichter = LanduseParams(pv_belegung_mw_pro_ha=2.0)  # statt 1.0
        result = compute_path_landuse("EE-GAS", dichter)
        assert result.pv_freiflaeche_km2 < base.pv_freiflaeche_km2 * 0.6

    def test_höherer_dach_anteil_reduziert_pv_freiflaeche(self):
        """Mehr PV auf Dächern → weniger Freifläche."""
        base = compute_path_landuse("EE-GAS")
        mehr_dach = LanduseParams(pv_dach_anteil=0.9)  # statt 0.66
        result = compute_path_landuse("EE-GAS", mehr_dach)
        assert result.pv_freiflaeche_km2 < base.pv_freiflaeche_km2 * 0.5
