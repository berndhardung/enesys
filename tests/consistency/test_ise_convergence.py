"""Parameter-Substrat-Robustheit: Pfad-Reihenfolge robust gegen das
Fraunhofer-ISE-2024-Kosten-Substrat.

Drittes Substrat im Quervergleich neben Ariadne/PyPSA (EE-leaning) und
NEA/PCGE (atom-orientiert). ISE ist eine *deutsche* Quelle mit eigener
Methodik; auf Parameter-Ebene ist sie nicht atom-feindlich (Kernkraft-
CAPEX-Mitte ~11 000 EUR/kW ≈ enesys-neutral). Importiert wird allein das
Kosten-Substrat, nicht die ISE-VLH-System-Annahme.

Geprüft werden dieselben strukturellen Eckpunkte wie beim Ariadne-Test,
mit einer bewusst schwächeren »teuerster Pfad«-Aussage: Unter dem ISE-
Substrat überholt BESTAND knapp KKW-H2 als teuersten Pfad (beide liegen
im teuren Cluster innerhalb ~0,2 ct/kWh). Die Architektur-Aussage — EE-
GAS in Top-2, KKW-Pfade nicht günstiger als EE-Pfade derselben H2/GAS-
Variante, KKW-H2 in den teuersten beiden — bleibt erhalten.
"""

from __future__ import annotations

from enesys import baseline_all_paths
from enesys.core.inventories.fuel_inventory import FUEL_INVENTORY
from enesys.core.inventories.tech_inventory import TECH_INVENTORY
from enesys.core.param_sets import PARAM_SETS, get
from enesys.core.param_sets._base import assert_known_keys

ISE = "ise_lcoe"
REFERENCE_YEAR = 2045


def test_ise_is_registered() -> None:
    """Set ist in Registry erreichbar."""
    assert ISE in PARAM_SETS
    set_obj = get(ISE)
    assert set_obj.name == ISE
    assert set_obj.reference_years == (2024, 2035, 2045)
    assert set_obj.currency_year == 2025


def test_ise_overrides_use_known_ids() -> None:
    """Override-Keys zeigen alle auf existierende Tech-/Fuel-IDs.

    Fängt stille Inventar-Umbenennungen sofort ab — Refactor-Pflicht
    wird mit konkreter Liste sichtbar statt durch obskuren Modell-Crash.
    """
    overrides = get(ISE).overrides(year=REFERENCE_YEAR)
    unknown = assert_known_keys(
        overrides,
        known_tech_ids=set(TECH_INVENTORY),
        known_fuel_ids=set(FUEL_INVENTORY),
    )
    assert unknown == [], (
        f"Override-Keys verweisen auf {len(unknown)} unbekannte IDs: "
        f"{unknown}. Vermutlich Tech- oder Fuel-Umbenennung — "
        f"Mapping in src/enesys/core/param_sets/ise_lcoe.py anpassen."
    )


def test_ise_lcoe_values_plausible() -> None:
    """LCOE-Werte liegen in vernünftiger Bandbreite — schützt vor Einheiten-Bugs."""
    lcoe = baseline_all_paths(year=REFERENCE_YEAR, param_set=ISE)
    for path, value in lcoe.items():
        assert 5.0 <= value <= 40.0, (
            f"LCOE {path}={value:.2f} ct/kWh außerhalb plausibler "
            f"Bandbreite [5, 40]. Hinweis auf Einheiten-Bug "
            f"(z.B. WACC Anteil vs. Prozent, EUR/kWh vs. EUR/MWh)."
        )


def test_ise_preserves_path_ranking() -> None:
    """Pfad-Reihenfolge bleibt strukturell stabil unter dem ISE-Substrat.

    Geprüft werden die strukturellen Eckpunkte: EE-GAS bleibt Top-Pfad
    (oder Top-2), KKW-Pfade bleiben nicht günstiger als EE-Pfade derselben
    H2/GAS-Variante. Die »teuerster Pfad«-Aussage ist bewusst als »KKW-H2
    in den teuersten beiden« formuliert: unter ISE überholt BESTAND knapp
    KKW-H2 (beide im teuren Cluster), ohne die Architektur-Aussage zu
    schwächen.
    """
    default = baseline_all_paths(year=REFERENCE_YEAR)
    ise = baseline_all_paths(year=REFERENCE_YEAR, param_set=ISE)

    ranking_default = sorted(default, key=default.get)
    ranking_ise = sorted(ise, key=ise.get)

    # (1) EE-GAS bleibt in Top-2 unter beiden Substraten.
    for label, rank in (("Default", ranking_default), ("ISE", ranking_ise)):
        assert "EE-GAS" in rank[:2], (
            f"EE-GAS nicht in Top-2 unter {label}: {rank}. Default-LCOE: {default}, ISE-LCOE: {ise}"
        )

    # (2) KKW-GAS nicht günstiger als EE-GAS, KKW-H2 nicht günstiger als
    # EE-H2 — strukturelle Architektur-Aussage des Modells.
    for label, lcoe in (("Default", default), ("ISE", ise)):
        assert lcoe["KKW-GAS"] >= lcoe["EE-GAS"], (
            f"KKW-GAS({lcoe['KKW-GAS']:.2f}) < EE-GAS({lcoe['EE-GAS']:.2f}) "
            f"unter {label} — strukturelle Aussage gebrochen"
        )
        assert lcoe["KKW-H2"] >= lcoe["EE-H2"], (
            f"KKW-H2({lcoe['KKW-H2']:.2f}) < EE-H2({lcoe['EE-H2']:.2f}) unter {label}"
        )

    # (3) KKW-H2 bleibt in den teuersten beiden Pfaden. Unter ISE überholt
    # BESTAND knapp KKW-H2 als Maximum — bewusst tolerierte Mittelfeld-/
    # Spitzen-Rotation, kein Bruch der Architektur-Aussage.
    assert "KKW-H2" in ranking_ise[-2:], (
        f"KKW-H2 nicht in den teuersten beiden unter ISE: {ranking_ise}. ISE-LCOE: {ise}"
    )


def test_ise_diffs_bounded() -> None:
    """Absolute Diff pro Pfad < 5 ct/kWh.

    Sanity-Bandbreite ohne harte Werte: ISE-Edition-Updates können
    Trajektorien leicht verschieben, ohne den Test zu brechen. Eine
    sprunghafte Verschiebung > 5 ct/kWh wiese auf einen Daten- oder
    Mapping-Fehler hin.
    """
    default = baseline_all_paths(year=REFERENCE_YEAR)
    ise = baseline_all_paths(year=REFERENCE_YEAR, param_set=ISE)

    big_diffs = {
        path: ise[path] - default[path] for path in default if abs(ise[path] - default[path]) >= 5.0
    }
    assert not big_diffs, (
        f"Unerwartet große ISE-Diff (>5 ct/kWh) bei: {big_diffs}. "
        f"Vermutlich Daten-Bug oder Mapping-Fehler in ise_lcoe.py."
    )


def test_ise_pv_learning_trajectory() -> None:
    """PV-Freifläche trägt eine Lernkurve: 2024 > 2045 (sinkende CAPEX)."""
    set_obj = get(ISE)
    pv_2024 = set_obj.overrides(year=2024)["pv.capex_eur_kw"]
    pv_2045 = set_obj.overrides(year=2045)["pv.capex_eur_kw"]
    assert pv_2024 > pv_2045, f"PV-Lernkurve kaputt: 2024={pv_2024:.1f} nicht > 2045={pv_2045:.1f}"

    # Kernkraft-CAPEX ist zeitkonstant (kein Lerneffekt in der Studie).
    o2024 = set_obj.overrides(year=2024)
    o2045 = set_obj.overrides(year=2045)
    assert o2024["kkw_neubau_epr.capex_eur_kw"] == o2045["kkw_neubau_epr.capex_eur_kw"]


def test_ise_nuclear_capex_matches_neutral_on_parameter_level() -> None:
    """ISE-Kernkraft-CAPEX-Mitte liegt nahe der neutralen Setzung.

    Sichert die Kern-Aussage des Substrats ab: ISE ist auf Parameter-Ebene
    nicht atom-feindlich; das EE-freundliche Studien-Ergebnis stammt aus der
    (hier bewusst nicht importierten) VLH-System-Annahme, nicht aus den
    Kosten-Inputs. EUR_2024→EUR_2025-Uplift (×1,02) auf die Bandmitte 11 000.
    """
    capex = get(ISE).overrides(year=REFERENCE_YEAR)["kkw_neubau_epr.capex_eur_kw"]
    assert 10_000 <= capex <= 12_000, (
        f"ISE-Kernkraft-CAPEX {capex:.0f} EUR/kW unerwartet weit von der "
        f"neutralen ~11 000-Setzung entfernt — Mapping/Konversion prüfen."
    )
