"""Konsistenztest: WACC-Defaults in ForwardCostParams gegen WACC_TABLE.

Sichert, dass die zentrale WACC-Quelle (`core/wacc.py`) und die
Default-Werte in `ForwardCostParams.wacc_*` synchron bleiben.
Wer einen WACC-Default ändert, MUSS beide Stellen mitziehen.

Dieser Test ist absichtlich knapp und maschinell: er ersetzt nicht
die methodische WACC-Begründung in `docs/SOURCES.md`
Abschnitt C — er stellt nur sicher, dass die Begründung dort und der
Wert im Code nicht auseinanderlaufen.
"""

from __future__ import annotations

import pytest

from enesys.core import wacc
from enesys.core.path_inputs import ForwardCostParams


def test_all_expected_wacc_names_defined() -> None:
    """Vier Asset-Klassen mit eigenem WACC: pv, wind, nuclear, battery."""
    expected = {"pv", "wind", "nuclear", "battery"}
    assert set(wacc.all_names()) == expected


@pytest.mark.parametrize("name", ["pv", "wind", "nuclear", "battery"])
def test_provenance_has_source_tag_and_justification(name: str) -> None:
    """Jede Provenance-Eintrag muss Quelle und Begründung dokumentieren."""
    prov = wacc.get(name)
    assert prov.source_tag, f"WACC '{name}': source_tag fehlt"
    assert prov.rationale, f"WACC '{name}': rationale fehlt"
    assert prov.lower_bound < prov.default < prov.upper_bound, (
        f"WACC '{name}': Default {prov.default} liegt nicht im Bereich "
        f"[{prov.lower_bound}, {prov.upper_bound}]"
    )


@pytest.mark.parametrize("name", ["pv", "wind", "nuclear", "battery"])
def test_forward_cost_params_default_synchron_mit_wacc_table(name: str) -> None:
    """``ForwardCostParams.wacc_<name>`` muss exakt ``wacc.get(name).default`` sein.

    Erzwingt das im Modul-Docstring von ``core/wacc.py`` zugesicherte
    Single-Source-of-Truth-Pattern: wer einen WACC-Default ändert, MUSS
    beide Stellen mitziehen. Ohne diesen Test driften die beiden Werte
    schleichend auseinander.
    """
    default_from_params = getattr(ForwardCostParams(), f"wacc_{name}")
    default_from_table = wacc.get(name).default
    assert default_from_params == pytest.approx(default_from_table), (
        f"ForwardCostParams.wacc_{name}={default_from_params} weicht von "
        f"wacc.get('{name}').default={default_from_table} ab — eine der "
        f"beiden Stellen wurde geändert ohne die andere nachzuziehen."
    )


def test_nuclear_hoeher_als_pv() -> None:
    """Risikoprämie KKW > PV ist eine fundamentale Modell-Aussage.

    Wenn dieser Test fehlschlägt, ist die WACC-Tabelle inkonsistent
    mit der ökonomischen Logik des Modells (Bauzeit-Risiko, Asset-
    Lebensdauer, Kapital-Bindung).
    """
    assert wacc.get("nuclear").default > wacc.get("pv").default
