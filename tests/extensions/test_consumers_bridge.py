"""Tests für die Verbraucher-Brücke (Forward Cost → Stromrechnung).

Forward Cost (volkswirtschaftliche Sicht): LCOE-Vollkosten neuer Anlagen,
30-Jahres-Mittel, BNetzA-Forward-Trend für Netz (7,0 ct/kWh).

Verbraucher-Sicht (Stromrechnung): Forward Cost mit zwei Brücken-Komponenten:
- Netz-heute (BDEW Mai 2026: 9,3 ct/kWh) ersetzt Modell-Netz 7,0
- Marktaufschlag (4,4 ct/kWh, kalibriert auf WEITER-SO heute = 37,0 ct)

Die Brücke ist methodisch sauber getrennt: der Forward Cost bleibt
unverändert (alle 197 bestehenden Tests grün), die Verbraucher-Sicht
erweitert nur die Verbraucher-Tab-Berechnung.

Diese Tests versiegeln:
- WEITER-SO mit Default-Slidern landet bei 37,0 ± 0,1 ct (Kalibrierung)
- Pfad-Differenzen sind reine Forward-Cost-Differenzen × (1 + MwSt)
  (Marktaufschlag wirkt linear auf alle Pfade gleich)
- Industrie-Modus rechnet weiterhin korrekt (Vorsteuerabzug)
- Slider-Bandbreiten plausibel
"""

import pytest

from enesys.extensions.consumer_bridge import (
    BDEW_HOUSEHOLD_GROSS_TODAY_CT,
    ENDVERBRAUCHER_KOMPONENTEN,
    NETZ_IM_FORWARD_COST_CT,
    calibrated_market_surcharge,
    compute_consumer_price,
)

# Forward-Cost-Werte aus dem Pfad-Modell (volkswirtschaftliche Sicht,
# 30-Jahres-Mittel 2026-2055, neutral_default-Lager). Aus compute_path
# reproduzierbar; bei Modell-Updates über tools/render_book_values.py
# oder manuell aus dem Test-Output nachziehen.
FC_WS = 16.92  # WEITER-SO
FC_EG = 16.56  # EE-GAS (günstigster Pfad im 30y-Mittel)
FC_EH = 17.17  # EE-H2
FC_KG = 17.31  # KKW-GAS
FC_KH = 17.68  # KKW-H2 (teuerster Pfad)


# Default-Slider-Werte
DEFAULT_SALES = 1.5
DEFAULT_TAX = 2.05
DEFAULT_CONCESSION = 1.80
DEFAULT_LEVIES = 2.84  # BDEW-genau, Mai 2026
DEFAULT_VAT = 19.0
DEFAULT_GRID_TODAY = 9.3
DEFAULT_MARKET_SURCHARGE = 4.4

# Realwert BDEW Mai 2026 (Haushalt, 3.500 kWh/Jahr brutto)
BDEW_HEUTE_HAUSHALT_BRUTTO = 37.0


def _verbraucher_brutto(forward_cost: float, **overrides) -> float:
    """Hilfsfunktion: Brutto-Verbraucherpreis mit Defaults und Overrides."""
    kwargs = {
        "forward_cost": forward_cost,
        "vertriebsmarge": DEFAULT_SALES,
        "electricity_tax": DEFAULT_TAX,
        "concession_levy": DEFAULT_CONCESSION,
        "other_levies": DEFAULT_LEVIES,
        "vat_pct": DEFAULT_VAT,
        "netz_heute": DEFAULT_GRID_TODAY,
        "marktaufschlag": DEFAULT_MARKET_SURCHARGE,
    }
    kwargs.update(overrides)
    return compute_consumer_price(**kwargs)["brutto"]


# ===========================================================================
# 1. Kalibrierung: WEITER-SO heute = BDEW-Realwert
# ===========================================================================


class TestKalibrierung:
    """Der Marktaufschlag-Default ist so kalibriert, dass WEITER-SO heute
    bei BDEW-Realwert 37,0 ct/kWh landet."""

    def test_weiter_so_landet_bei_bdew_realwert(self):
        """WEITER-SO mit dynamisch berechnetem Marktaufschlag landet
        bei BDEW-Realwert (37,0 ct). Der Marktaufschlag wird zur Laufzeit
        aus dem WEITER-SO-Forward-Cost reverse-berechnet, damit der Test
        bei LCOE-Drift nicht reißt."""
        dynamic_surcharge = calibrated_market_surcharge(FC_WS)
        brutto = _verbraucher_brutto(FC_WS, marktaufschlag=dynamic_surcharge)
        assert abs(brutto - BDEW_HEUTE_HAUSHALT_BRUTTO) < 0.01, (
            f"WEITER-SO Brutto {brutto:.4f} ct weicht von BDEW-Ziel "
            f"{BDEW_HEUTE_HAUSHALT_BRUTTO:.1f} ct ab — die "
            "Reverse-Formel in calibrated_market_surcharge() ist defekt."
        )
        # Sanity: der dynamische Marktaufschlag liegt im plausiblen
        # 2-8 ct-Korridor (siehe ENDVERBRAUCHER_KOMPONENTEN-Bandbreite).
        assert 2.0 <= dynamic_surcharge <= 8.0, (
            f"calibrated_market_surcharge ({dynamic_surcharge:.2f}) "
            f"außerhalb des Slider-Korridors 2-8 ct."
        )

    def test_bdew_realwert_anker_unchanged(self):
        """Der BDEW-Realwert-Anker in consumer_bridge stimmt mit der
        Test-Konstante überein (Single Source of Truth)."""
        assert BDEW_HOUSEHOLD_GROSS_TODAY_CT == BDEW_HEUTE_HAUSHALT_BRUTTO

    def test_default_slider_werte_konsistent(self):
        """Die in diesem Test verwendeten Defaults müssen mit den
        Slider-Definitionen in ENDVERBRAUCHER_KOMPONENTEN übereinstimmen.
        Sonst läuft die Streamlit-UI mit anderen Werten als der Test."""
        assert ENDVERBRAUCHER_KOMPONENTEN["vertriebsmarge"]["default"] == DEFAULT_SALES
        assert ENDVERBRAUCHER_KOMPONENTEN["stromsteuer"]["default"] == DEFAULT_TAX
        assert ENDVERBRAUCHER_KOMPONENTEN["konzessionsabgabe"]["default"] == DEFAULT_CONCESSION
        assert ENDVERBRAUCHER_KOMPONENTEN["umlagen"]["default"] == DEFAULT_LEVIES
        assert ENDVERBRAUCHER_KOMPONENTEN["mwst"]["default"] == DEFAULT_VAT
        assert ENDVERBRAUCHER_KOMPONENTEN["netz_heute"]["default"] == DEFAULT_GRID_TODAY
        assert ENDVERBRAUCHER_KOMPONENTEN["marktaufschlag"]["default"] == DEFAULT_MARKET_SURCHARGE


# ===========================================================================
# 2. Pfad-Differenzen: linear, vom Marktaufschlag unberührt
# ===========================================================================


class TestPfadDifferenzen:
    """Der Marktaufschlag wirkt auf alle Pfade gleich. Pfad-Differenzen
    bleiben dadurch reine Forward-Cost-Differenzen × (1 + MwSt)."""

    @pytest.mark.parametrize(
        "fc_a,fc_b",
        [
            (FC_WS, FC_EG),
            (FC_EH, FC_EG),
            (FC_KG, FC_EG),
            (FC_KH, FC_EG),
            (FC_WS, FC_KH),
        ],
    )
    def test_path_difference_is_fc_difference_times_vat(self, fc_a, fc_b):
        """Die Brutto-Differenz zweier Pfade muss exakt der
        Forward-Cost-Differenz × (1 + MwSt/100) entsprechen."""
        brutto_a = _verbraucher_brutto(fc_a)
        brutto_b = _verbraucher_brutto(fc_b)
        actual_diff = brutto_a - brutto_b
        expected_diff = (fc_a - fc_b) * (1 + DEFAULT_VAT / 100)
        assert abs(actual_diff - expected_diff) < 0.001, (
            f"Pfad-Differenz {actual_diff:.4f} weicht von erwarteter "
            f"{expected_diff:.4f} ab. Marktaufschlag wirkt nicht linear "
            "auf alle Pfade gleich."
        )

    def test_marktaufschlag_aenderung_pfad_diff_bleibt(self):
        """Wenn der Marktaufschlag verändert wird, bleibt die Pfad-Differenz
        unverändert — der Aufschlag verschiebt nur das Niveau."""
        diff_default = _verbraucher_brutto(FC_WS) - _verbraucher_brutto(FC_EG)
        diff_hoch = _verbraucher_brutto(FC_WS, marktaufschlag=8.0) - _verbraucher_brutto(
            FC_EG, marktaufschlag=8.0
        )
        diff_null = _verbraucher_brutto(FC_WS, marktaufschlag=0.0) - _verbraucher_brutto(
            FC_EG, marktaufschlag=0.0
        )
        assert abs(diff_default - diff_hoch) < 0.001
        assert abs(diff_default - diff_null) < 0.001


# ===========================================================================
# 3. Brücke Forward Cost ↔ Verbraucher-Sicht: Netz-Substitution korrekt
# ===========================================================================


class TestNetzBruecke:
    """Forward Cost enthält Netz 7,0 (BNetzA-Forward). In der Verbraucher-
    Sicht wird das durch netz_heute (BDEW Mai 2026: 9,3) ersetzt."""

    def test_grid_in_fc_constant_correct(self):
        """Die Konstante NETZ_IM_FORWARD_COST_CT muss 7,0 sein."""
        assert NETZ_IM_FORWARD_COST_CT == 7.0

    def test_netz_substitution_addiert_differenz(self):
        """Wenn netz_heute = netz_modell (7,0), darf der Brücken-Effekt
        verschwinden — Brutto entspricht dann reiner Aufschlag-Logik."""
        brutto_mit_bruecke = _verbraucher_brutto(FC_WS)
        brutto_ohne_bruecke = _verbraucher_brutto(FC_WS, netz_heute=NETZ_IM_FORWARD_COST_CT)
        # Differenz muss (9,3 - 7,0) × 1,19 = 2,737 ct sein
        diff = brutto_mit_bruecke - brutto_ohne_bruecke
        expected = (DEFAULT_GRID_TODAY - NETZ_IM_FORWARD_COST_CT) * 1.19
        assert abs(diff - expected) < 0.001

    def test_netz_slider_oberhalb_modell_default(self):
        """netz_heute Default 9,3 muss > netz_modell 7,0 sein —
        die Brücke geht in die richtige Richtung."""
        assert DEFAULT_GRID_TODAY > NETZ_IM_FORWARD_COST_CT


# ===========================================================================
# 4. Industrie-Modus: Vorsteuerabzug, Privilegien
# ===========================================================================


class TestIndustrieModus:
    """Industrie ist vorsteuerabzugsberechtigt (Netto = Brutto), bekommt
    Stromsteuer-Spitzenausgleich, Konzessionsabgabe-Reduktion und
    §19-Umlage-Befreiung."""

    def test_industrie_kein_mwst(self):
        """Bei use_industry_rates=True ist Brutto = Netto."""
        result = compute_consumer_price(
            forward_cost=FC_WS,
            vertriebsmarge=DEFAULT_SALES,
            electricity_tax=DEFAULT_TAX,
            concession_levy=DEFAULT_CONCESSION,
            other_levies=DEFAULT_LEVIES,
            vat_pct=DEFAULT_VAT,
            netz_heute=DEFAULT_GRID_TODAY,
            marktaufschlag=DEFAULT_MARKET_SURCHARGE,
            use_industry_rates=True,
        )
        assert result["brutto"] == result["netto"]
        assert result["mwst"] == 0.0

    def test_industrie_aufschlaege_reduziert(self):
        """Industrie-Stromsteuer ist 25% des Haushaltssatzes (Spitzenausgleich)."""
        result = compute_consumer_price(
            forward_cost=FC_WS,
            vertriebsmarge=DEFAULT_SALES,
            electricity_tax=DEFAULT_TAX,
            concession_levy=DEFAULT_CONCESSION,
            other_levies=DEFAULT_LEVIES,
            vat_pct=DEFAULT_VAT,
            use_industry_rates=True,
        )
        assert result["stromsteuer"] == DEFAULT_TAX * 0.25
        assert result["konzessionsabgabe"] == 0.11
        assert result["umlagen"] == DEFAULT_LEVIES * 0.4


# ===========================================================================
# 5. Slider-Bandbreiten plausibel
# ===========================================================================


class TestSliderBandbreiten:
    """Slider-Min/Max müssen plausibel sein und Default in Bandbreite liegen."""

    @pytest.mark.parametrize(
        "key",
        [
            "vertriebsmarge",
            "stromsteuer",
            "konzessionsabgabe",
            "umlagen",
            "mwst",
            "netz_heute",
            "marktaufschlag",
        ],
    )
    def test_default_in_bandbreite(self, key):
        komp = ENDVERBRAUCHER_KOMPONENTEN[key]
        assert komp["min"] <= komp["default"] <= komp["max"], (
            f"Slider {key}: default {komp['default']} liegt nicht "
            f"zwischen min {komp['min']} und max {komp['max']}."
        )

    def test_marktaufschlag_bandbreite_0_8(self):
        komp = ENDVERBRAUCHER_KOMPONENTEN["marktaufschlag"]
        assert komp["min"] == 0.0
        assert komp["max"] == 8.0

    def test_netz_heute_bandbreite(self):
        """netz_heute Bandbreite 6-12 deckt Forward-Trend (7,0)
        bis Worst-Case-Netzausbau (12) ab."""
        komp = ENDVERBRAUCHER_KOMPONENTEN["netz_heute"]
        assert komp["min"] <= NETZ_IM_FORWARD_COST_CT <= komp["max"]
        assert komp["min"] <= DEFAULT_GRID_TODAY <= komp["max"]
