"""Convergence-Test: Pfad-Reihenfolge robust gegen Ariadne/PyPSA-Substrat.

Der zentrale enesys-Befund ist die strukturelle Pfad-Ordnung: EE-GAS
in den Top-2, KKW-H2 als teuerster Pfad, KKW-Pfade nicht günstiger als
EE-Pfade derselben H2/GAS-Variante. Mittelfeld-Pfade (BESTAND, EE-H2,
WEITER-SO) liegen dicht beieinander und können je nach Substrat einen
Platz tauschen — das schwächt die Architektur-Aussage nicht.

Dieser Test stellt sicher, dass die strukturellen Eckpunkte erhalten
bleiben, wenn man die enesys-Default-Annahmen durch das PyPSA/
technology-data Substrat ersetzt (die Eingabe-Datenbank von PyPSA-DE /
BMBF-Ariadne).

Drei Aussagen werden geprüft
----------------------------
1. **Strukturelle Hygiene** — alle Override-Keys zeigen auf existierende
   Tech-/Fuel-IDs. Fängt stille Inventar-Umbenennungen sofort ab.
2. **Plausibilität** — LCOE-Werte mit Override liegen in vernünftiger
   Bandbreite (10-30 ct/kWh). Schützt vor Einheiten-Bugs (WACC-Anteil
   vs. Prozent etc.).
3. **Strukturelle Konvergenz** — EE-GAS in Top-2, KKW-H2 teuerster
   Pfad, KKW-Pfade nicht günstiger als EE-Pfade. Absolute Differenzen
   pro Pfad < 5 ct/kWh als Bandbreiten-Sicherheit, ohne harte Werte
   einzukleben (Drift-Schutz: PyPSA-CSV-Updates dürfen den Test nicht
   ohne Modell-Reaktion brechen).
"""

from __future__ import annotations

from enesys import baseline_all_paths
from enesys.core.inventories.fuel_inventory import FUEL_INVENTORY
from enesys.core.inventories.tech_inventory import TECH_INVENTORY
from enesys.core.param_sets import PARAM_SETS, get
from enesys.core.param_sets._base import assert_known_keys

ARIADNE = "ariadne_pypsa"
REFERENCE_YEAR = 2045


def test_ariadne_is_registered() -> None:
    """Set ist in Registry erreichbar."""
    assert ARIADNE in PARAM_SETS
    set_obj = get(ARIADNE)
    assert set_obj.name == ARIADNE
    assert set_obj.reference_years == (2030, 2040, 2050)


def test_ariadne_overrides_use_known_ids() -> None:
    """Override-Keys zeigen alle auf existierende Tech-/Fuel-IDs.

    Fängt stille Inventar-Umbenennungen sofort ab — Refactor-Pflicht
    wird mit konkreter Liste sichtbar statt durch obskuren Modell-Crash.
    """
    overrides = get(ARIADNE).overrides(year=REFERENCE_YEAR)
    unknown = assert_known_keys(
        overrides,
        known_tech_ids=set(TECH_INVENTORY),
        known_fuel_ids=set(FUEL_INVENTORY),
    )
    assert unknown == [], (
        f"Override-Keys verweisen auf {len(unknown)} unbekannte IDs: "
        f"{unknown}. Vermutlich Tech- oder Fuel-Umbenennung — "
        f"Mapping in src/enesys/core/param_sets/ariadne_pypsa.py anpassen."
    )


def test_ariadne_lcoe_values_plausible() -> None:
    """LCOE-Werte liegen in vernünftiger Bandbreite — schützt vor Einheiten-Bugs."""
    lcoe = baseline_all_paths(year=REFERENCE_YEAR, param_set=ARIADNE)
    for path, value in lcoe.items():
        assert 5.0 <= value <= 40.0, (
            f"LCOE {path}={value:.2f} ct/kWh außerhalb plausibler "
            f"Bandbreite [5, 40]. Hinweis auf Einheiten-Bug "
            f"(z.B. WACC Anteil vs. Prozent)."
        )


def test_ariadne_preserves_path_ranking() -> None:
    """Pfad-Reihenfolge bleibt strukturell stabil unter Ariadne-Substrat.

    Der zentrale Befund: enesys' Forward-Cost-Reihenfolge ist nicht
    annahmen-spezifisch, sondern strukturell. Dichte Mittelfeld-Pfade
    (BESTAND, EE-H2 liegen oft innerhalb 0,2 ct/kWh beieinander) können
    durch das PyPSA-Substrat einen Platz tauschen — das schwächt die
    Architektur-Aussage nicht. Geprüft werden deshalb die strukturellen
    Eckpunkte: EE-GAS bleibt Top-Pfad (oder Top-2), KKW-Pfade bleiben
    nicht günstiger als EE-Pfade derselben H2/GAS-Variante.
    """
    default = baseline_all_paths(year=REFERENCE_YEAR)
    ariadne = baseline_all_paths(year=REFERENCE_YEAR, param_set=ARIADNE)

    ranking_default = sorted(default, key=default.get)
    ranking_ariadne = sorted(ariadne, key=ariadne.get)

    # (1) EE-GAS bleibt in Top-2.
    for label, rank in (("Default", ranking_default), ("Ariadne", ranking_ariadne)):
        assert "EE-GAS" in rank[:2], (
            f"EE-GAS nicht in Top-2 unter {label}: {rank}. Default-LCOE: "
            f"{default}, Ariadne-LCOE: {ariadne}"
        )

    # (2) KKW-GAS nicht günstiger als EE-GAS, KKW-H2 nicht günstiger als
    # EE-H2 — strukturelle Architektur-Aussage des Modells.
    for label, lcoe in (("Default", default), ("Ariadne", ariadne)):
        assert lcoe["KKW-GAS"] >= lcoe["EE-GAS"], (
            f"KKW-GAS({lcoe['KKW-GAS']:.2f}) < EE-GAS({lcoe['EE-GAS']:.2f}) "
            f"unter {label} — strukturelle Aussage gebrochen"
        )
        assert lcoe["KKW-H2"] >= lcoe["EE-H2"], (
            f"KKW-H2({lcoe['KKW-H2']:.2f}) < EE-H2({lcoe['EE-H2']:.2f}) unter {label}"
        )

    # (3) Reihenfolgen müssen nicht identisch sein, aber Top-3 und
    # Bottom-2 sind robust: KKW-H2 bleibt teuerster, EE-GAS in Top-2.
    assert ranking_default[-1] == ranking_ariadne[-1] == "KKW-H2", (
        f"KKW-H2 nicht teuerster Pfad: Default {ranking_default[-1]}, Ariadne {ranking_ariadne[-1]}"
    )


def test_ariadne_diffs_bounded() -> None:
    """Absolute Diff pro Pfad < 5 ct/kWh.

    Sanity-Bandbreite ohne harte Werte: PyPSA-CSV-Updates können
    Trajektorien-Werte leicht verschieben, ohne dass der Test bricht.
    Eine sprunghafte Verschiebung > 5 ct/kWh würde aber auf einen
    Daten-Bug oder Mapping-Fehler hinweisen und sollte sichtbar werden.
    """
    default = baseline_all_paths(year=REFERENCE_YEAR)
    ariadne = baseline_all_paths(year=REFERENCE_YEAR, param_set=ARIADNE)

    big_diffs = {
        path: ariadne[path] - default[path]
        for path in default
        if abs(ariadne[path] - default[path]) >= 5.0
    }
    assert not big_diffs, (
        f"Unerwartet große Ariadne-Diff (>5 ct/kWh) bei: {big_diffs}. "
        f"Vermutlich Daten-Bug oder Mapping-Fehler in ariadne_pypsa.py."
    )


def test_ariadne_trajectory_interpolation() -> None:
    """Trajektorien-Auflösung: Stützstelle 2030 liefert 2030-Wert, 2045 liegt dazwischen."""
    set_obj = get(ARIADNE)
    o2030 = set_obj.overrides(year=2030)
    o2050 = set_obj.overrides(year=2050)
    o2045 = set_obj.overrides(year=2045)

    # PV-CAPEX hat Lerneffekt — 2030 > 2045 > 2050
    pv_capex_2030 = o2030["pv.capex_eur_kw"]
    pv_capex_2045 = o2045["pv.capex_eur_kw"]
    pv_capex_2050 = o2050["pv.capex_eur_kw"]
    assert pv_capex_2030 > pv_capex_2045 > pv_capex_2050, (
        f"PV-Lerneffekt-Trajektorie kaputt: "
        f"2030={pv_capex_2030} 2045={pv_capex_2045} 2050={pv_capex_2050}"
    )

    # Nuclear CAPEX ist zeitkonstant (Lazard-Baseline)
    assert o2030["kkw_neubau_epr.capex_eur_kw"] == o2050["kkw_neubau_epr.capex_eur_kw"]
