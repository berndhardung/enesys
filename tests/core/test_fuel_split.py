"""Unit-Tests für ``split_gas_h2ready_by_fuel``.

Sichert die Single-Source-of-Truth-Funktion, die in den Chart-Helfern
(``viz/charts/rampup.py``, ``viz/charts/stress.py``) verwendet wird,
gegen Drift ab.
"""

from __future__ import annotations

import pytest

from enesys.core.fuel import split_gas_h2ready_by_fuel


def test_split_proportional_pure_erdgas() -> None:
    """Wenn nur Erdgas verbraucht wird, fällt alles auf den Erdgas-Anteil."""
    erdgas, h2 = split_gas_h2ready_by_fuel(
        100.0, {"erdgas_inland": 50.0, "erdgas_import": 30.0, "lng": 20.0}
    )
    assert erdgas == pytest.approx(100.0)
    assert h2 == pytest.approx(0.0)


def test_split_proportional_pure_h2() -> None:
    """Wenn nur H₂ verbraucht wird, fällt alles auf den H₂-Anteil."""
    erdgas, h2 = split_gas_h2ready_by_fuel(100.0, {"h2_inland": 80.0, "h2_import": 20.0})
    assert erdgas == pytest.approx(0.0)
    assert h2 == pytest.approx(100.0)


def test_split_proportional_mixed() -> None:
    """Mischung aus Erdgas und H₂: Aufteilung folgt dem thermischen Anteil."""
    erdgas, h2 = split_gas_h2ready_by_fuel(100.0, {"erdgas_inland": 30.0, "h2_inland": 70.0})
    assert erdgas == pytest.approx(30.0)
    assert h2 == pytest.approx(70.0)
    assert erdgas + h2 == pytest.approx(100.0)


def test_split_zero_total() -> None:
    """Aggregat 0 liefert (0, 0) ohne Division durch 0."""
    erdgas, h2 = split_gas_h2ready_by_fuel(0.0, {"erdgas_inland": 50.0})
    assert erdgas == 0.0
    assert h2 == 0.0


def test_split_no_fuel_default_erdgas() -> None:
    """Ohne Brennstoff-Verbrauch fällt der Aggregat-Wert per Default auf Erdgas."""
    erdgas, h2 = split_gas_h2ready_by_fuel(50.0, {})
    assert erdgas == 50.0
    assert h2 == 0.0


def test_split_no_fuel_h2_fallback() -> None:
    """Ohne Brennstoff-Verbrauch + h2_default_fallback=True → alles auf H₂."""
    erdgas, h2 = split_gas_h2ready_by_fuel(50.0, {}, h2_default_fallback=True)
    assert erdgas == 0.0
    assert h2 == 50.0


def test_split_ignores_irrelevant_fuels() -> None:
    """Brennstoffe außerhalb der Erdgas/H₂-Familien werden ignoriert."""
    erdgas, h2 = split_gas_h2ready_by_fuel(
        100.0,
        {"erdgas_inland": 40.0, "h2_inland": 60.0, "kohle": 999.0, "uran": 500.0},
    )
    assert erdgas == pytest.approx(40.0)
    assert h2 == pytest.approx(60.0)
