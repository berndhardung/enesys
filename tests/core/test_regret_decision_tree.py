"""Strukturelle Mechanik-Tests für die Reue-Matrix.

Sichert ab, dass die Voll-Matrix 6 Pfade × 4 Welten = 24 Zellen
strukturell stimmt (alle Zellen rechnen, LCOE im plausiblen Korridor,
Savage-Reue-Eigenschaft, ein Minimum pro Welt, Schaden-Skalierung).
"""

from __future__ import annotations

import pytest

from enesys.core.regret_decision_tree import (
    CAMP_WORLDS,
    PolicyChoice,
    RegretMatrixCell,
    compute_regret_matrix,
    damage_bn_eur,
)


@pytest.fixture(scope="module")
def matrix() -> list[RegretMatrixCell]:
    return compute_regret_matrix()


def test_all_24_cells_compute(matrix):
    """6 Pfade × 4 Welten = 24 Zellen (ζ.3b Voll-Matrix)."""
    assert len(matrix) == 24
    worlds = {c.world for c in matrix}
    policies = {c.policy for c in matrix}
    assert worlds == set(CAMP_WORLDS)
    assert policies == set(PolicyChoice)
    assert len(PolicyChoice) == 6  # 6 Pfade nach ζ.3b


def test_lcoe_in_plausibility_band(matrix):
    """LCOE-Werte im 10-60 ct/kWh-Korridor (30-Jahres-Mittel).

    H2-Pfade in NEP-skeptischen Welten erreichen bis ~50 ct (EE_H2 / KKW_H2
    in bestand_optimistic). Korridor entsprechend großzügig.
    """
    for c in matrix:
        assert 10.0 <= c.lcoe_30y_mean_ct_kwh <= 60.0, (
            f"{c.policy.name} in {c.world}: LCOE {c.lcoe_30y_mean_ct_kwh:.2f} außerhalb 10-60 ct"
        )


def test_regret_non_negative_by_construction(matrix):
    """Savage-Eigenschaft: Reue ≥ 0 für jede Zelle."""
    for c in matrix:
        assert c.regret_ct_kwh >= -1e-9, (
            f"{c.policy.name} in {c.world}: Reue {c.regret_ct_kwh:.4f} < 0 "
            f"(verletzt Savage-Konstruktion)"
        )


def test_exactly_one_minimum_per_world(matrix):
    """In jeder Welt-Sicht hat genau eine Politik Reue = 0 (Min-LCOE)."""
    for world in CAMP_WORLDS:
        world_cells = [c for c in matrix if c.world == world]
        minima = [c for c in world_cells if c.is_minimum]
        assert len(minima) == 1, f"{world}: erwartet 1 Min-Politik, gefunden {len(minima)}"
        assert minima[0].regret_ct_kwh == pytest.approx(0.0, abs=1e-9)


def test_damage_scaling_correct():
    """Schaden = Reue × 30 J × 858 TWh / 100 (Mrd EUR)."""
    assert damage_bn_eur(1.0) == pytest.approx(257.4, abs=0.1)
    assert damage_bn_eur(0.5) == pytest.approx(128.7, abs=0.1)
    assert damage_bn_eur(0.0) == 0.0
