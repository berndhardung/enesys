"""Konsistenz-Tests für externe Quellen (BDEW, Destatis).

Diese Tests stellen sicher, dass die zentrale Quellen-Datei
``external_sources.py`` die *einzige* Wahrheit für externe Werte ist und
beim Update einer Quelle die Konsistenz im gesamten Repo gewahrt bleibt.

**Kontext.** Werte wie der heutige BDEW-Haushaltsstrompreis (37,0 ct/kWh)
oder die Anzahl der Privathaushalte (41 Mio.) erscheinen an vielen Stellen:
Slider-Defaults, Tooltips, Heute-Tabelle, Buch-Tiefen-Boxen, Web-Dashboard.
Diese Tests prüfen, dass:

1. Die zentrale Quelle ist die Wahrheit (Schema, Plausibilität).
2. Slider-Defaults beziehen ihre Werte aus der Quelle, nicht hardcoded.
3. Die exportierte JSON ist mit der Python-Quelle konsistent.
4. Kalibrierung der Verbraucher-Brücke stimmt zur zentralen Quelle.

Die Buch-Konsistenz-Tests für dieselben Werte (BDEW-Brutto, Haushalts-Anzahl
im Manuskript) liegen in ``tests/consistency/test_buch_endverbraucher_konsistenz.py``
— Privat-only, nicht im OSS-Mirror.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from enesys.extensions.consumer_bridge import (
    ENDVERBRAUCHER_KOMPONENTEN,
    VERBRAUCHERGRUPPEN,
    compute_consumer_price,
)
from enesys.extensions.consumers import (
    BDEW_2026_HOUSEHOLD,
    BDEW_2026_INDUSTRY,
    BDEW_2026_SOURCE,
    DESTATIS_2024,
    DESTATIS_2024_SOURCE,
    MARKET_SURCHARGE_CALIBRATED,
    TCL_2026,
    to_dict,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ===========================================================================
# 1. Plausibilität der zentralen Quelle
# ===========================================================================


class TestZentraleQuellePlausibel:
    """Die Werte in external_sources.py sind in sich plausibel."""

    def test_bdew_gross_is_sum_of_components(self):
        """Brutto-Haushaltspreis = Summe der drei Blöcke
        (mit ±0,2 ct Toleranz für BDEW-Rundung)."""
        h = BDEW_2026_HOUSEHOLD
        summe = h.procurement_sales + h.grid_fees + h.taxes_charges_levies
        assert abs(summe - h.gross) < 0.2, (
            f"BDEW-Komponenten {summe:.1f} vs. Brutto {h.gross:.1f} weichen ab — "
            "BDEW-Daten unstimmig oder Werte falsch eingetragen."
        )

    def test_vat_share_from_gross_correct(self):
        """MwSt-Anteil = Brutto × (MwSt% / (100 + MwSt%))."""
        h = BDEW_2026_HOUSEHOLD
        expected = h.gross * TCL_2026.mwst_pct / (100 + TCL_2026.mwst_pct)
        assert abs(h.vat_share - expected) < 0.01

    def test_sau_summe_passt_zu_bdew_block(self):
        """Stromsteuer + Konzession + sonstige Umlagen + MwSt-Anteil
        = BDEW-Block 'Steuern/Abgaben/Umlagen' (mit Toleranz)."""
        sau_total = (
            TCL_2026.stromsteuer
            + TCL_2026.konzessionsabgabe
            + TCL_2026.sonstige_umlagen
            + BDEW_2026_HOUSEHOLD.vat_share
        )
        assert abs(sau_total - BDEW_2026_HOUSEHOLD.taxes_charges_levies) < 0.1

    def test_destatis_haushalte_plausibel(self):
        """Anzahl Haushalte plausibel (zwischen 35 und 50 Millionen)."""
        n = DESTATIS_2024.anzahl_privathaushalte
        assert 35_000_000 < n < 50_000_000

    def test_konzessionsabgabe_in_bandbreite(self):
        """Mittelwert liegt zwischen Min und Max."""
        assert (
            TCL_2026.konzessionsabgabe_min
            <= TCL_2026.konzessionsabgabe
            <= TCL_2026.konzessionsabgabe_max
        )


# ===========================================================================
# 2. Marktaufschlag-Kalibrierung
# ===========================================================================


class TestMarktaufschlagKalibrierung:
    """Der Default-Marktaufschlag ist exakt so kalibriert, dass WEITER-SO
    Brutto = BDEW-Realwert. Wenn die BDEW-Werte ändern, muss
    MARKET_SURCHARGE_CALIBRATED in external_sources.py angepasst werden."""

    def test_weiter_so_landet_bei_bdew_brutto(self):
        """WEITER-SO mit allen Default-Slidern aus zentraler Quelle =
        BDEW-Realwert (±0,1 ct Toleranz für Rundung)."""
        result = compute_consumer_price(
            forward_cost=16.25,  # WEITER-SO Forward Cost (volkswirtschaftliche Sicht, unverändert)
            vertriebsmarge=ENDVERBRAUCHER_KOMPONENTEN["vertriebsmarge"]["default"],
            electricity_tax=ENDVERBRAUCHER_KOMPONENTEN["stromsteuer"]["default"],
            concession_levy=ENDVERBRAUCHER_KOMPONENTEN["konzessionsabgabe"]["default"],
            other_levies=ENDVERBRAUCHER_KOMPONENTEN["umlagen"]["default"],
            vat_pct=ENDVERBRAUCHER_KOMPONENTEN["mwst"]["default"],
            netz_heute=ENDVERBRAUCHER_KOMPONENTEN["netz_heute"]["default"],
            marktaufschlag=ENDVERBRAUCHER_KOMPONENTEN["marktaufschlag"]["default"],
        )
        assert abs(result["brutto"] - BDEW_2026_HOUSEHOLD.gross) < 0.1, (
            f"WEITER-SO Brutto {result['brutto']:.2f} ≠ BDEW {BDEW_2026_HOUSEHOLD.gross}. "
            "Marktaufschlag-Kalibrierung muss in external_sources.py "
            "neu berechnet werden."
        )


# ===========================================================================
# 3. Slider-Defaults stammen aus der zentralen Quelle (kein Hardcoding)
# ===========================================================================


class TestSliderAusZentraleQuelle:
    """Die Streamlit-Slider-Defaults müssen aus external_sources.py kommen.
    Wenn jemand einen Slider hardcoded, fällt das hier auf."""

    def test_stromsteuer_aus_sau(self):
        assert ENDVERBRAUCHER_KOMPONENTEN["stromsteuer"]["default"] == TCL_2026.stromsteuer
        assert ENDVERBRAUCHER_KOMPONENTEN["stromsteuer"]["max"] == TCL_2026.stromsteuer

    def test_konzession_aus_sau(self):
        assert (
            ENDVERBRAUCHER_KOMPONENTEN["konzessionsabgabe"]["default"] == TCL_2026.konzessionsabgabe
        )
        assert (
            ENDVERBRAUCHER_KOMPONENTEN["konzessionsabgabe"]["min"] == TCL_2026.konzessionsabgabe_min
        )
        assert (
            ENDVERBRAUCHER_KOMPONENTEN["konzessionsabgabe"]["max"] == TCL_2026.konzessionsabgabe_max
        )

    def test_umlagen_aus_sau(self):
        assert ENDVERBRAUCHER_KOMPONENTEN["umlagen"]["default"] == TCL_2026.sonstige_umlagen

    def test_mwst_aus_sau(self):
        assert ENDVERBRAUCHER_KOMPONENTEN["mwst"]["default"] == TCL_2026.mwst_pct

    def test_netz_heute_aus_bdew(self):
        assert ENDVERBRAUCHER_KOMPONENTEN["netz_heute"]["default"] == BDEW_2026_HOUSEHOLD.grid_fees

    def test_marktaufschlag_aus_quelle(self):
        assert (
            ENDVERBRAUCHER_KOMPONENTEN["marktaufschlag"]["default"] == MARKET_SURCHARGE_CALIBRATED
        )

    def test_haushalt_kwh_aus_bdew(self):
        assert (
            VERBRAUCHERGRUPPEN["haushalt"]["kwh_pro_jahr"]
            == BDEW_2026_HOUSEHOLD.annual_consumption_kwh
        )

    def test_brutto_in_expected_today_string(self):
        """Der angezeigte 'expected_today'-String enthält den BDEW-Brutto-Wert."""
        s = VERBRAUCHERGRUPPEN["haushalt"]["expected_today"]
        # 37.0 → "37,0" für deutsches Komma
        expected_str = f"{BDEW_2026_HOUSEHOLD.gross:.1f}".replace(".", ",")
        assert expected_str in s, (
            f"BDEW-Brutto {expected_str} nicht im expected_today-String '{s}' gefunden — "
            "VERBRAUCHERGRUPPEN noch hardcoded?"
        )


# ===========================================================================
# 4. JSON-Export ist mit Python-Quelle konsistent
# ===========================================================================


class TestJsonExport:
    """to_dict() liefert die gleichen Werte wie die Python-Konstanten."""

    def test_to_dict_enthaelt_bdew(self):
        d = to_dict()
        assert d["bdew_2026"]["haushalt"]["gross"] == BDEW_2026_HOUSEHOLD.gross
        assert d["bdew_2026"]["haushalt"]["grid_fees"] == BDEW_2026_HOUSEHOLD.grid_fees
        assert d["bdew_2026"]["industrie"]["kleine_mittlere"] == BDEW_2026_INDUSTRY.kleine_mittlere

    def test_to_dict_enthaelt_destatis(self):
        d = to_dict()
        assert (
            d["destatis_2024"]["haushalte"]["anzahl_privathaushalte"]
            == DESTATIS_2024.anzahl_privathaushalte
        )

    def test_to_dict_enthaelt_marktaufschlag(self):
        d = to_dict()
        assert d["marktaufschlag_kalibriert"] == MARKET_SURCHARGE_CALIBRATED

    def test_quellen_metadaten_komplett(self):
        d = to_dict()
        bdew = d["bdew_2026"]["quelle"]
        assert bdew["source_tag"] == BDEW_2026_SOURCE.source_tag
        assert bdew["url"].startswith("https://")
        destatis = d["destatis_2024"]["quelle"]
        assert destatis["source_tag"] == DESTATIS_2024_SOURCE.source_tag


# ===========================================================================
# 5. SOURCES.md hat alle Tags, die external_sources verwendet
# ===========================================================================


class TestSourceTagsInSourcesMd:
    """Jeder source_tag aus external_sources.py muss in SOURCES.md vorkommen."""

    @pytest.fixture
    def sources_md_content(self):
        path = REPO_ROOT / "docs" / "SOURCES.md"
        return path.read_text(encoding="utf-8")

    def test_bdew_tag_in_sources(self, sources_md_content):
        assert f"`{BDEW_2026_SOURCE.source_tag}`" in sources_md_content, (
            f"Tag {BDEW_2026_SOURCE.source_tag} fehlt in docs/SOURCES.md — "
            "neuen Tag dort eintragen wenn BDEW-Quelle aktualisiert wird."
        )

    def test_destatis_tag_in_sources(self, sources_md_content):
        assert f"`{DESTATIS_2024_SOURCE.source_tag}`" in sources_md_content


# ===========================================================================
# 6. JSON-Datei ist aktuell (write/read-Roundtrip)
# ===========================================================================
# Buch-Manuskript-Konsistenz für Endverbraucher-Werte ist nach
# tests/consistency/test_buch_endverbraucher_konsistenz.py ausgelagert
# (Privat-only, im OSS-Mirror nicht enthalten).


class TestJsonAktuell:
    """JSON-Export erzeugt eine schreibbare, valide Datei mit den
    erwarteten Top-Level-Schlüsseln."""

    def test_json_can_be_written(self, tmp_path):
        target = tmp_path / "external_sources.json"
        write_json(target)
        assert target.exists()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        # Haushalts-Brutto stimmt überein
        assert loaded["bdew_2026"]["haushalt"]["gross"] == BDEW_2026_HOUSEHOLD.gross
