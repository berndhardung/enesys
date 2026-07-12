"""Tests für das Maßnahmen-Inventar (``path_measures``).

Nagelt die *gerechneten* Größen (LNG-Menge, ETS-Budget, Winter-Defizit-Zeile)
gegen Golden-Werte fest — sonst gingen ungetestete abgeleitete Zahlen live —
und prüft die Struktur (Tags gültig, welcher Pfad welche Bausteine bekommt).
"""

from __future__ import annotations

import pytest

from enesys.core.path_measures import (
    Measure,
    ets_budget_mrd_eur,
    lng_mrd_m3_per_year,
    path_measures,
)

_ALL_PIDS = ("weiterso", "bestand", "ee_gas", "ee_h2", "kkw_gas", "kkw_h2")
_VALID_ADRESSAT = {"V", "P"}
_VALID_HEBEL = {"H", "K"}
_VALID_TYP = {"rate", "binaer", "folge", "voraussetzung"}


# --- gerechnete Größen (Golden) ------------------------------------------


def test_lng_magnitude_golden():
    """Gas-Importmenge @2045 → Mrd m³/a, gegen Golden-Wert."""
    assert lng_mrd_m3_per_year("weiterso") == pytest.approx(26.1, abs=0.6)
    assert lng_mrd_m3_per_year("bestand") == pytest.approx(33.6, abs=0.6)


def test_ets_budget_golden():
    """Kumuliertes ETS-Budget 2026–2055 → Mrd €, gegen Golden-Wert."""
    assert ets_budget_mrd_eur("weiterso") == pytest.approx(256, abs=6)
    assert ets_budget_mrd_eur("bestand") == pytest.approx(298, abs=6)


def test_ets_consistent_with_co2_system_integral():
    """Das ETS-Budget ist Σ(co2_mt × co2_price) — exakt das CO₂-System-Integral
    der LCOE, unabhängig nachgerechnet (keine Pauschal-Konstante)."""
    from enesys.core.fuel import co2_price_year
    from enesys.core.path_model import compute_path

    years = list(range(2026, 2056))
    rs = compute_path("weiterso", years, camp="neutral_default")
    expected = (
        sum(r.co2_mt * co2_price_year(y, "neutral_default") for r, y in zip(rs, years, strict=True))
        / 1000.0
    )
    assert ets_budget_mrd_eur("weiterso") == pytest.approx(expected, abs=1e-6)


def test_displayed_values_rounded():
    """Die gezeigten Größen sind gerundet (griffig), nicht scheinpräzise."""
    ws = {m.text: m.wert for m in path_measures("weiterso", max_deficit_gw=41.4)}
    fossil = next(v for t, v in ws.items() if "Fossil weiterbetreiben" in t)
    assert "~26 Mrd m³/a" in fossil
    assert "~260 Mrd €" in fossil
    deficit = next(v for t, v in ws.items() if "Abschaltlast" in t)
    assert deficit == "~41 GW"


# --- Struktur ------------------------------------------------------------


def test_all_tags_valid():
    for pid in _ALL_PIDS:
        for m in path_measures(pid, max_deficit_gw=41.0):
            assert isinstance(m, Measure)
            assert m.adressat in _VALID_ADRESSAT
            assert m.hebel in _VALID_HEBEL
            assert m.typ in _VALID_TYP
            assert m.text and m.quelle


def test_block_composition():
    """Aktive Pfade = EE-Sockel; KKW erbt + Zusatz; Referenzpfade eigener Block."""
    assert len(path_measures("ee_gas")) == 3  # EE-Sockel
    assert len(path_measures("ee_h2")) == 3
    assert len(path_measures("kkw_gas")) == 5  # + KKW-Zusatz
    assert len(path_measures("kkw_h2")) == 5
    assert len(path_measures("weiterso", max_deficit_gw=41)) == 4  # + Abschaltlast
    assert len(path_measures("bestand")) == 4  # + Klima/Recht-Folge


def test_abschaltlast_only_weiterso():
    """Die GW-Abschaltlast-Zeile gilt nur für WEITER-SO (BESTAND: 0 GW)."""
    ws = [m.text for m in path_measures("weiterso", max_deficit_gw=41)]
    be = [m.text for m in path_measures("bestand")]
    assert any("Abschaltlast" in t for t in ws)
    assert not any("Abschaltlast" in t for t in be)


def test_kkw_inherits_ee_sockel():
    """KKW-Pfade enthalten den vollen EE-Sockel plus KKW-Zusatz."""
    ee_texts = {m.text for m in path_measures("ee_gas")}
    kkw_texts = {m.text for m in path_measures("kkw_gas")}
    assert ee_texts <= kkw_texts


def test_unknown_path_raises():
    with pytest.raises(ValueError):
        path_measures("nonsense")
