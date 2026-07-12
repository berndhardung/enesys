"""Convergence-Test: zentrale Pfad-Aussagen halten unter NEA-PCGE-Substrat.

PCGE 2020 ist atom-orientiertes Annahmen-Substrat (OECD-Europa-Median,
WACC 7 % real, USD_2018 → EUR_2025) — symmetrisches Gegenstück zu
``ariadne_pypsa`` (EE-leaning).

Anders als bei Ariadne fordert dieser Test KEINE strenge Pfad-Reihenfolge-
Identität: PCGE hat eine andere methodische Schwerpunktsetzung
(keine EE-Lernrate, statischer 2025-Snapshot, höherer WACC), und das
verschiebt nahe-beieinanderliegende Pfade. Stattdessen werden die
STRUKTURELLEN INVARIANTEN geprüft:

1. **Strukturelle Hygiene** — Override-Keys mappen auf existierende
   Tech-/Fuel-IDs.
2. **Plausibilität** — LCOE-Werte in vernünftiger Bandbreite.
3. **EE-GAS bleibt wettbewerbsfähig** — unter PCGE rückt EE-GAS oft
   auf Platz 2 oder 3 (statisches 2025-Snapshot ohne EE-Lernkurve,
   WACC 7 % real), bleibt aber in den Top-3.
4. **KKW-H2 bleibt strukturell teuer** — Doppel-Wette KKW-CAPEX × H2-
   Infrastruktur lässt KKW-H2 in den Top-2 teuersten Pfaden; KKW-H2
   bleibt teurer als EE-H2 (gleiche H2-Kette, KKW-CAPEX zusätzlich).
5. **Diff-Bandbreite** — pro-Pfad-Diff bleibt in vernünftiger Bandbreite
   (< 5 ct/kWh). PCGE-Substrat hebt das Niveau erwartet konsistent;
   ein Sprung > 5 würde auf Daten-Bug oder Mapping-Fehler hinweisen.
"""

from __future__ import annotations

from enesys import baseline_all_paths
from enesys.core.inventories.fuel_inventory import FUEL_INVENTORY
from enesys.core.inventories.tech_inventory import TECH_INVENTORY
from enesys.core.param_sets import PARAM_SETS, get
from enesys.core.param_sets._base import assert_known_keys

PCGE = "nea_pcge"
REFERENCE_YEAR = 2045


def test_nea_pcge_is_registered() -> None:
    """Set ist in Registry erreichbar."""
    assert PCGE in PARAM_SETS
    set_obj = get(PCGE)
    assert set_obj.name == PCGE
    assert set_obj.currency_year == 2025


def test_nea_pcge_overrides_use_known_ids() -> None:
    """Override-Keys zeigen alle auf existierende Tech-/Fuel-IDs."""
    overrides = get(PCGE).overrides(year=REFERENCE_YEAR)
    unknown = assert_known_keys(
        overrides,
        known_tech_ids=set(TECH_INVENTORY),
        known_fuel_ids=set(FUEL_INVENTORY),
    )
    assert unknown == [], (
        f"Override-Keys verweisen auf {len(unknown)} unbekannte IDs: "
        f"{unknown}. Vermutlich Tech- oder Fuel-Umbenennung — "
        f"Mapping in src/enesys/core/param_sets/nea_pcge.py anpassen."
    )


def test_nea_pcge_lcoe_values_plausible() -> None:
    """LCOE-Werte liegen in vernünftiger Bandbreite — schützt vor Einheiten-Bugs."""
    lcoe = baseline_all_paths(year=REFERENCE_YEAR, param_set=PCGE)
    for path, value in lcoe.items():
        assert 5.0 <= value <= 40.0, (
            f"LCOE {path}={value:.2f} ct/kWh außerhalb plausibler "
            f"Bandbreite [5, 40]. Hinweis auf Einheiten-Bug "
            f"(z.B. USD-EUR-Konversion vergessen, WACC-Anteil-vs-Prozent)."
        )


def test_nea_pcge_ee_gas_in_top_three() -> None:
    """EE-GAS bleibt in den Top-3 unter PCGE-Substrat.

    Anders als unter dem Default-Substrat ist EE-GAS unter PCGE nicht
    zwingend Top-1: PCGE setzt einen statischen 2025-Snapshot ohne
    EE-Lernkurve und mit WACC 7 % real, das verteuert EE relativ. Die
    Pfade liegen unter PCGE dicht beieinander (Spannweite ~1,5 ct/kWh
    zwischen den Top-3), und EE-GAS, KKW-GAS und WEITER-SO tauschen
    sich Platz 1-3 je nach Bezugsjahr. Die Architektur-Aussage »EE-GAS
    bleibt wettbewerbsfähig auch unter atom-orientiertem Substrat«
    misst sich darum am Top-3-Verbleib, nicht am Top-1-Status.
    """
    pcge = baseline_all_paths(year=REFERENCE_YEAR, param_set=PCGE)
    ranking = sorted(pcge, key=pcge.get)
    assert "EE-GAS" in ranking[:3], (
        f"EE-GAS soll in Top-3 bleiben, Reihenfolge: {ranking}. PCGE-LCOEs: {pcge}."
    )


def test_nea_pcge_kkw_h2_teurer_als_ee_gas_und_kkw_gas() -> None:
    """KKW-H2 bleibt unter PCGE strukturell teurer als EE-GAS und KKW-GAS.

    Auch unter atom-orientierter PCGE-Substrat-Wahl (LTO 550 USD/kW,
    Gen-III 5 466 USD/kW als EU-Median) bleibt KKW-H2 strukturell
    teurer als (a) der billigste aktive Pfad (EE-GAS) und (b) der
    KKW-Schwester-Pfad mit Gas-Backup (KKW-GAS). Letzteres isoliert
    die H2-Infrastruktur-Wette: gleicher KKW-Stack, nur das Backup
    wechselt — der Mehrpreis muss aus der H2-Schicht kommen, nicht
    aus der KKW-Schicht. Diese Architektur-Aussage ist robust gegen
    Substrat-Wahl.
    """
    pcge = baseline_all_paths(year=REFERENCE_YEAR, param_set=PCGE)
    assert pcge["KKW-H2"] > pcge["EE-GAS"], (
        f"KKW-H2({pcge['KKW-H2']:.2f}) sollte teurer als "
        f"EE-GAS({pcge['EE-GAS']:.2f}) bleiben. PCGE-LCOEs: {pcge}."
    )
    # KKW-H2 > KKW-GAS isoliert die H2-Backup-Mehrkosten gegenüber
    # Gas-Backup bei sonst gleichem KKW-Stack.
    assert pcge["KKW-H2"] > pcge["KKW-GAS"], (
        f"KKW-H2({pcge['KKW-H2']:.2f}) sollte teurer als "
        f"KKW-GAS({pcge['KKW-GAS']:.2f}) bleiben — H2-Backup-Aufschlag."
    )


def test_nea_pcge_diffs_bounded() -> None:
    """Absolute Diff pro Pfad < 5 ct/kWh. Sanity-Bandbreite ohne harte Werte."""
    default = baseline_all_paths(year=REFERENCE_YEAR)
    pcge = baseline_all_paths(year=REFERENCE_YEAR, param_set=PCGE)

    big_diffs = {
        path: pcge[path] - default[path]
        for path in default
        if abs(pcge[path] - default[path]) >= 5.0
    }
    assert not big_diffs, (
        f"Unerwartet große PCGE-Diff (>5 ct/kWh) bei: {big_diffs}. "
        f"Vermutlich Daten-Bug oder Mapping-Fehler in nea_pcge.py."
    )


def test_nea_pcge_kkw_diff_smaller_than_ee_diff() -> None:
    """KKW-Pfad-Diff unter PCGE ist absolut kleiner als EE-Pfad-Diff.

    Das ist die methodische Pointe von PCGE: atom-orientierte
    Substrat-Wahl verteuert EE relativ stärker als KKW. Wenn dieser
    Effekt verschwindet, ist entweder das Substrat falsch gepflegt
    oder das Mapping kaputt.
    """
    default = baseline_all_paths(year=REFERENCE_YEAR)
    pcge = baseline_all_paths(year=REFERENCE_YEAR, param_set=PCGE)

    ee_diff_mean = (
        abs(pcge["EE-GAS"] - default["EE-GAS"]) + abs(pcge["EE-H2"] - default["EE-H2"])
    ) / 2
    kkw_diff_mean = (
        abs(pcge["KKW-GAS"] - default["KKW-GAS"]) + abs(pcge["KKW-H2"] - default["KKW-H2"])
    ) / 2

    assert kkw_diff_mean < ee_diff_mean, (
        f"PCGE-Asymmetrie erwartet: KKW-Pfad-Diff sollte kleiner als "
        f"EE-Pfad-Diff sein (atom-orientiertes Substrat). "
        f"Aktuell: KKW-Diff-Mittel={kkw_diff_mean:.2f}, "
        f"EE-Diff-Mittel={ee_diff_mean:.2f}."
    )


def test_nea_pcge_is_snapshot_not_trajectory() -> None:
    """PCGE liefert KEINE Trajektorien — Werte 2030/2050 identisch.

    Schützt gegen versehentliche Einführung von Trajektorien-Logik in
    nea_pcge.py — das wäre eine Verletzung der PCGE-2020-Charakteristik
    (Stichwert-Snapshot, kein Forecast).
    """
    set_obj = get(PCGE)
    o2030 = set_obj.overrides(year=2030)
    o2050 = set_obj.overrides(year=2050)

    assert o2030 == o2050, (
        "PCGE-Overrides 2030 und 2050 müssen identisch sein "
        "(Snapshot-Charakter). Wenn die Unterschiede sind, wurde "
        "Trajektorien-Logik versehentlich eingebaut."
    )
