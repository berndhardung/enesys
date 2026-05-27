"""Coverage-Matrix-Tests: Mengen-Bilanz schließt sich, Tornado-Hebel sind self-konsistent.

Zwei Klassen struktureller Sicherungen:

1. **No-Unserved-Demand-Matrix** für aktive Pfade × alle Lager × Stützjahre.
   Aktive Pfade (EE-GAS/EE-H2/KKW-GAS/KKW-H2/BESTAND) müssen unter
   beliebigem Lager-Belief eine geschlossene Mengen-Bilanz haben — die
   Pfad-Politik (`fuel_cap_multipliers`, `boost_policy`) muss die
   physische Infrastruktur so hinterlegen, dass keine VOLL-Pönale auf
   `unserved_twh` getriggert wird. WEITER-SO ist ausgenommen: sein
   Pfad-Charakter beinhaltet, dass die Sektor-Kopplung nicht
   durchgeführt wird; Defizit darf hier strukturell entstehen.

2. **Tornado-Baseline-Bracket-Invariante:** jeder signifikante
   Tornado-Hebel klammert die Baseline ein. Verletzung mit großer
   Diskrepanz weist auf Override-vs-Lager-Default-Drift in der
   Sensi-Mechanik hin (z.B. Skalar-Override gegen jahres-gerampten
   Lager-Default). Konvexe Hebel-Verläufe (Modell-Mengen-Bilanz mit
   Optimum im Inneren) sind methodisch erlaubt und werden über die
   Toleranz abgedeckt.
"""

from __future__ import annotations

import pytest

from enesys.core.path_model import PATH_LABEL, compute_path
from enesys.core.sensitivity import baseline_all_paths, tornado_path_analysis

# -----------------------------------------------------------------------------
# 1) No-Unserved-Demand-Matrix
# -----------------------------------------------------------------------------

ACTIVE_PATHS: tuple[str, ...] = ("ee_gas", "ee_h2", "kkw_gas", "kkw_h2", "bestand")
CAMPS: tuple[str, ...] = (
    "neutral_default",
    "ee_optimistic",
    "atom_optimistic",
    "bestand_optimistic",
)
COVERAGE_YEARS: tuple[int, ...] = (2030, 2040, 2045, 2050, 2055)
UNSERVED_TOLERANCE_TWH: float = 0.5


@pytest.mark.parametrize("path_id", ACTIVE_PATHS)
@pytest.mark.parametrize("camp", CAMPS)
def test_active_paths_close_demand_balance(path_id: str, camp: str) -> None:
    """Aktive Pfade decken die Demand unter jedem Lager-Belief.

    Verletzung deutet darauf hin, dass `fuel_cap_multipliers` oder
    `boost_policy` der Pfad-Politik nicht für die Welt-Belief-
    Kombination ausreicht.
    """
    results = compute_path(path_id, list(COVERAGE_YEARS), camp=camp)
    for r in results:
        assert r.unserved_twh < UNSERVED_TOLERANCE_TWH, (
            f"{path_id} {camp} {r.year}: unserved {r.unserved_twh:.2f} TWh "
            f"> {UNSERVED_TOLERANCE_TWH} TWh — Pfad-Brennstoff-Infrastruktur "
            f"reicht in diesem Lager nicht."
        )


def test_weiterso_bridge_phase_no_unserved() -> None:
    """WEITER-SO darf in Spätjahren Defizit haben (Sektor-Kopplung wird
    nicht durchgeführt), aber in der Bridge-Phase 2026-2030 muss die
    Bilanz schließen.
    """
    for camp in CAMPS:
        results = compute_path("weiterso", [2030], camp=camp)
        assert results[0].unserved_twh < UNSERVED_TOLERANCE_TWH, (
            f"weiterso {camp} 2030: unserved {results[0].unserved_twh:.2f} TWh "
            f"in der Bridge-Phase nicht akzeptabel."
        )


# -----------------------------------------------------------------------------
# 2) Tornado-Baseline-Bracket-Invariante
# -----------------------------------------------------------------------------

BRACKET_TOLERANCE_CT: float = 0.50
SIGNIFICANT_SWING_CT: float = 0.20
TORNADO_PATHS: tuple[str, ...] = ("ee_gas", "kkw_gas")


@pytest.mark.parametrize("camp", CAMPS)
@pytest.mark.parametrize("path_id", TORNADO_PATHS)
def test_tornado_hebel_bracketet_baseline(camp: str, path_id: str) -> None:
    """Signifikante Tornado-Hebel klammern die Baseline ein (mit Toleranz).

    Verletzung jenseits der Toleranz weist auf Override-vs-Lager-Default-
    Drift hin. Konvexe Hebel-Verläufe mit Minimum/Maximum im Inneren
    sind methodisch erlaubt — die Toleranz deckt sie ab.
    """
    base = baseline_all_paths(year=2045, camp=camp)
    baseline = base[PATH_LABEL[path_id]]
    hebel = tornado_path_analysis(path_id, year=2045, baseline_camp=camp)
    for h in hebel:
        mn = min(h["price_low"], h["price_high"])
        mx = max(h["price_low"], h["price_high"])
        swing = mx - mn
        if swing < SIGNIFICANT_SWING_CT:
            continue
        lower = mn - BRACKET_TOLERANCE_CT
        upper = mx + BRACKET_TOLERANCE_CT
        assert lower <= baseline <= upper, (
            f"{camp} {path_id} »{h['label']}«: Baseline {baseline:.2f} ct "
            f"nicht in [{mn:.2f}, {mx:.2f}] ±{BRACKET_TOLERANCE_CT} ct "
            f"(Swing {swing:.2f} ct)."
        )
