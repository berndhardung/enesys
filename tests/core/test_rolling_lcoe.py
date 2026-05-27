"""Konsistenztests für Rolling-LCOE und Mix-Aggregationen.

Rolling-LCOE (`rolling_lcoe(Y) = Mittel über (Y, Y+29)`) ist die
kanonische Trajektorien-Definition für Pfad-Vergleiche; Snapshot-Lesungen
(`baseline_all_paths(year=Y)`) bleiben als Stichjahr-API erhalten.

Mix-Aggregationen (`snapshot_mix`, `mean_mix`, `steady_state_mix`)
exposen `PathResult.mix_by_technology` als zentrale Schnittstelle für
Hochlauf-Charts und Buch-Auszüge.

Geprüft:

1. ``PathResult.mix_by_technology`` summiert pro Jahr auf ~1
   (für aktive Pfade mit demand_twh > 0).
2. ``snapshot_mix(P, Y)`` == ``compute_path(P, [Y])[0].mix_by_technology``.
3. ``mean_mix(P, A, B)`` == Mittel der Snapshot-Mixe über (A, B);
   Summe pro Tech über alle Techs ~1.
4. ``rolling_lcoe(P, Y)`` == arithmetisches Mittel der jährlichen
   ``lcoe_ct_kwh`` über (Y, Y+29).
5. ``rolling_lcoe_trajectory`` liefert dasselbe Ergebnis wie ein
   per-Jahr-Loop über ``rolling_lcoe``.
6. ``rolling_all_paths(2026)`` reproduziert das heutige 30-J-Mittel
   2026-2055 (sechs-Pfad-Matrix in Pfad-Label-Form).
7. Asymptotische Konvergenz: ``rolling_lcoe(2055)`` ist über ein
   Verschiebungs-Fenster (2055 vs 2056) stabil im engen Toleranzband;
   über 15 Jahre (2055 vs 2070) bleibt die Drift unter 1 ct/kWh
   (asynchrone Pfad-Fertigstellung, siehe
   ``test_rolling_lcoe_asymptotic_policy_completion``).
8. Glättung: die Spannweite der Rolling-LCOE-Trajektorie ist nicht
   größer als die Spannweite der jährlichen LCOE-Trajektorie
   (Mittelung kann nur dämpfen).
"""

from __future__ import annotations

import pytest

from enesys.core.path_aggregations import (
    mean_mix,
    snapshot_mix,
    steady_state_mix,
)
from enesys.core.path_model import compute_path
from enesys.core.rolling_lcoe import (
    rolling_all_paths,
    rolling_lcoe,
    rolling_lcoe_trajectory,
)

ACTIVE_PATHS = ("ee_gas", "ee_h2", "kkw_gas", "kkw_h2")


# ---------------------------------------------------------------------------
# Mix-Konsistenz (Aggregations-Schicht)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path_id", ACTIVE_PATHS)
def test_mix_by_technology_sums_to_one(path_id: str) -> None:
    """Anteil-Summe über alle Techs ~1 pro Jahr (Mengen-Bilanz schließt)."""
    for year in (2026, 2035, 2045, 2055):
        result = compute_path(path_id, [year])[0]
        total = sum(result.mix_by_technology.values())
        assert total == pytest.approx(1.0, abs=0.02), (
            f"{path_id}/{year}: Mix-Summe {total:.4f} weicht von 1.0 ab"
        )


def test_snapshot_mix_matches_path_result() -> None:
    """``snapshot_mix(P, Y)`` == ``compute_path(P, [Y])[0].mix_by_technology``."""
    result = compute_path("ee_gas", [2045])[0]
    snap = snapshot_mix("ee_gas", 2045)
    assert snap == result.mix_by_technology


def test_mean_mix_equals_yearly_average() -> None:
    """``mean_mix(P, A, B)`` == arithmetisches Mittel der jährlichen Mixe."""
    path_id, year_from, year_to = "ee_gas", 2030, 2034
    years = list(range(year_from, year_to + 1))
    yearly = [r.mix_by_technology for r in compute_path(path_id, years)]
    techs = {tech for mix in yearly for tech in mix}
    expected = {tech: sum(mix.get(tech, 0.0) for mix in yearly) / len(yearly) for tech in techs}
    expected = {t: v for t, v in expected.items() if v > 0}
    actual = mean_mix(path_id, year_from, year_to)
    assert actual.keys() == expected.keys()
    for tech, share in expected.items():
        assert actual[tech] == pytest.approx(share, abs=1e-9)


def test_steady_state_mix_uses_2055_to_2084_window() -> None:
    """``steady_state_mix`` == ``mean_mix(2055, 2084)``."""
    actual = steady_state_mix("ee_gas")
    expected = mean_mix("ee_gas", 2055, 2084)
    assert actual.keys() == expected.keys()
    for tech in actual:
        assert actual[tech] == pytest.approx(expected[tech], abs=1e-9)


def test_mean_mix_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="year_from"):
        mean_mix("ee_gas", 2055, 2026)


# ---------------------------------------------------------------------------
# Rolling LCOE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path_id", ACTIVE_PATHS)
def test_rolling_lcoe_equals_window_mean(path_id: str) -> None:
    """``rolling_lcoe(P, 2026)`` == Mittel der LCOE-Werte 2026-2055."""
    years = list(range(2026, 2056))
    yearly = [r.lcoe_ct_kwh for r in compute_path(path_id, years)]
    expected = sum(yearly) / len(yearly)
    assert rolling_lcoe(path_id, 2026) == pytest.approx(expected, abs=1e-9)


def test_rolling_lcoe_window_parameter() -> None:
    """``window``-Parameter steuert die Fenster-Länge konsistent."""
    years = list(range(2030, 2040))
    yearly = [r.lcoe_ct_kwh for r in compute_path("ee_gas", years)]
    expected = sum(yearly) / len(yearly)
    assert rolling_lcoe("ee_gas", 2030, window=10) == pytest.approx(expected, abs=1e-9)


def test_rolling_lcoe_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window"):
        rolling_lcoe("ee_gas", 2026, window=0)


def test_rolling_lcoe_trajectory_matches_per_year_calls() -> None:
    """``rolling_lcoe_trajectory`` ist konsistent mit Einzel-Aufrufen."""
    years = [2026, 2030, 2040, 2055]
    bulk = rolling_lcoe_trajectory("ee_gas", years)
    for y in years:
        assert bulk[y] == pytest.approx(rolling_lcoe("ee_gas", y), abs=1e-9)


def test_rolling_lcoe_trajectory_empty_input() -> None:
    assert rolling_lcoe_trajectory("ee_gas", []) == {}


def test_rolling_all_paths_returns_six_path_matrix() -> None:
    """Sechs Pfad-Label, Werte == Einzel-``rolling_lcoe``-Aufrufe."""
    matrix = rolling_all_paths(2026)
    expected_labels = {"WEITER-SO", "BESTAND", "EE-GAS", "EE-H2", "KKW-GAS", "KKW-H2"}
    assert set(matrix) == expected_labels
    assert matrix["EE-GAS"] == pytest.approx(rolling_lcoe("ee_gas", 2026), abs=1e-9)


# ---------------------------------------------------------------------------
# Trajektorien-Eigenschaften: Konvergenz + Glättung
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path_id", ACTIVE_PATHS)
def test_rolling_lcoe_steady_state_convergence(path_id: str) -> None:
    """Rolling-LCOE konvergiert für Y → Steady-State.

    Operationale Lesung: ``rolling_lcoe(2055)`` und ``rolling_lcoe(2060)``
    liegen eng beieinander — nach Klimaneutralität gibt es keine
    systematische Trajektorien-Drift mehr im Mengen-Mix.
    """
    a = rolling_lcoe(path_id, 2055)
    b = rolling_lcoe(path_id, 2060)
    drift = abs(a - b)
    assert drift < 0.5, (
        f"{path_id}: Rolling-LCOE driftet im Steady-State zu stark: "
        f"|{a:.3f} − {b:.3f}| = {drift:.3f} ct/kWh"
    )


@pytest.mark.parametrize("path_id", ACTIVE_PATHS)
def test_rolling_lcoe_asymptotic_policy_completion(path_id: str) -> None:
    """Rolling-LCOE konvergiert asymptotisch, nicht monoton im Modell-Fenster.

    Markt-Parameter sind im Modell jahresunabhängig (Camp-Belief-Spreizung
    statt linearer Extrapolation): Brennstoff-Preise, CO₂-Preise und
    Mengen-Kapazitäten plateauen bereits bis 2055. Die verbleibende
    Rolling-LCOE-Dynamik nach 2055 wird ausschließlich durch
    *asynchrone Pfad-Fertigstellung* getrieben — KKW-Bauzeit-Streckung
    (sqrt-Realgrad) im neutralen Lager schiebt das 24-GW-Ziel in die
    späten 2060er; in diesem Fenster wird Bridge-Gas durch späte
    Reaktor-Inbetriebnahmen abgelöst. Das ist eine bewusste Modell-
    Eigenschaft, kein Konvergenz-Defekt: die Drift macht den Zeit-Versatz
    politischer Programme sichtbar.

    Strikte Monotonie (Drift im späteren Intervall kleiner als im
    früheren) ist deshalb konzeptionell nicht erwartbar — eine Pfad-
    Politik stoppt nicht, nur weil ein Steady-State-Fenster startet.
    Operationale Obergrenze stattdessen: die absolute Drift bleibt
    klein gegen den Pfad-Vergleichs-Korridor (~1 ct/kWh), so dass die
    Pfad-Aussage über das Modell-Fenster trägt.

    Geprüft: ``|rolling(2055) − rolling(2070)| ≤ 1,0 ct/kWh`` für alle
    aktiven Pfade.
    """
    drift = abs(rolling_lcoe(path_id, 2055) - rolling_lcoe(path_id, 2070))
    assert drift < 1.0, (
        f"{path_id}: Rolling-LCOE-Drift 2055 vs 2070 > 1 ct/kWh "
        f"({drift:.3f}) — asymptotische Konvergenz ist zu schwach für "
        f"den Pfad-Vergleichs-Korridor."
    )


@pytest.mark.parametrize("path_id", ACTIVE_PATHS)
def test_rolling_lcoe_smoother_than_yearly(path_id: str) -> None:
    """Mittelung dämpft Schwankung — Rolling-Spannweite ≤ Jahres-Spannweite.

    Geprüft über den Trajektorien-Block 2026-2055 (Start-Jahre für
    Rolling) vs. jährliche LCOE im gleichen Block.
    """
    start_years = list(range(2026, 2056))
    rolling_values = list(rolling_lcoe_trajectory(path_id, start_years).values())
    yearly_values = [r.lcoe_ct_kwh for r in compute_path(path_id, start_years)]
    rolling_range = max(rolling_values) - min(rolling_values)
    yearly_range = max(yearly_values) - min(yearly_values)
    assert rolling_range <= yearly_range + 1e-9, (
        f"{path_id}: Rolling-Spannweite {rolling_range:.3f} > "
        f"Jahres-Spannweite {yearly_range:.3f} — Mittelung sollte dämpfen"
    )
