"""Rolling LCOE als kanonische Trajektorien-Definition.

Definition::

    LCOE(Y) = arithmetisches Mittel von compute_path-LCOE über (Y, Y+W-1)

mit Default-Fenster ``W = 30`` Jahren. Damit ist:

- ``rolling_lcoe(2026)`` = Mittel 2026-2055 (heutiges »30-J-Mittel«).
- ``rolling_lcoe(2045)`` = Mittel 2045-2074 (Trajektorien-Lesung 2045).
- ``rolling_lcoe(2055)`` = Mittel 2055-2084 (Steady-State).

Ein fließender Übergang vom Bridge-Pfad in den Steady-State, ohne
Stützstellen-Diskussion. Aggregation ist unbewichtet (Jahres-Mittel
der jährlichen ``lcoe_ct_kwh``-Werte) — entspricht der Lesung
»durchschnittliche Stromgestehungskosten im 30-Jahres-Lebenszyklus
ab Jahr Y«.

**Fenster ≠ Asset-Lifetime.** Das 30-J-Fenster ist die Investitions-
Lebenszyklus-Konvention für den *Pfad-Vergleich*, nicht die technische
Anlagen-Lebensdauer. Die Annuität (WACC-Diskontierung der CAPEX) bleibt
tech-spezifisch in ``compute_path`` über ``TechEntry.lifetime_years``
(PV 30, Wind 25, KKW-Neubau 60, etc.). Das Rolling-Mittel ist eine
zeitliche Aggregation der bereits annuitäts-bereinigten Jahres-LCOE,
keine weitere Diskontierung der Jahresscheiben.

**Arithmetisch statt DCF-gewichtet.** Bewusst unbewichtet — die
jährlichen ``lcoe_ct_kwh`` enthalten bereits die Annuität (= WACC-
Diskontierung der CAPEX). Eine zusätzliche DCF-Gewichtung der Jahres-
scheiben wäre Doppeldiskontierung und würde Bridge-Pfade systematisch
billiger erscheinen lassen (Frühjahre stärker gewichtet) und KKW mit
spätem IBN-Jahr teurer. Arithmetisch entspricht der Lesart der Buch-
Anker (»Durchschnittspreis im Investment-Lebenszyklus«).

Schnellzugriff für 6-Pfade-Tabellen: :func:`rolling_all_paths` liefert
die Pfad-Label-Matrix (»EE-GAS« etc.) analog zu
:func:`enesys.core.sensitivity.baseline_all_paths`, aber als Rolling-
Mittel statt Stichjahr-Snapshot.
"""

from __future__ import annotations

from enesys.core.path_model import _PATH_ORDER, PATH_LABEL, compute_path

DEFAULT_WINDOW_YEARS = 30


def rolling_lcoe(
    path_id: str,
    year: int,
    camp: str = "neutral_default",
    *,
    window: int = DEFAULT_WINDOW_YEARS,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> float:
    """Rolling 30-Jahres-LCOE ab Jahr ``year`` (ct/kWh).

    Berechnet ``compute_path`` für (``year``, ``year + window - 1``)
    und mittelt die jährlichen ``lcoe_ct_kwh``-Werte arithmetisch.
    """
    if window < 1:
        raise ValueError(f"window muss >= 1 sein, war {window}")
    years = list(range(year, year + window))
    results = compute_path(
        path_id,
        years,
        camp=camp,
        param_set=param_set,
        param_overrides=param_overrides,
    )
    return sum(r.lcoe_ct_kwh for r in results) / len(results)


def rolling_lcoe_trajectory(
    path_id: str,
    years: list[int],
    camp: str = "neutral_default",
    *,
    window: int = DEFAULT_WINDOW_YEARS,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> dict[int, float]:
    """Rolling-LCOE für eine Liste von Start-Jahren.

    Effizienzpfad gegenüber wiederholten ``rolling_lcoe``-Aufrufen:
    Berechnet ``compute_path`` einmal über den Gesamt-Bereich
    (min(years) bis max(years) + window - 1) und mittelt pro
    Start-Jahr über das Fenster.
    """
    if not years:
        return {}
    if window < 1:
        raise ValueError(f"window muss >= 1 sein, war {window}")
    start = min(years)
    end = max(years) + window - 1
    all_years = list(range(start, end + 1))
    results = compute_path(
        path_id,
        all_years,
        camp=camp,
        param_set=param_set,
        param_overrides=param_overrides,
    )
    by_year = {r.year: r.lcoe_ct_kwh for r in results}
    return {y: sum(by_year[yy] for yy in range(y, y + window)) / window for y in years}


def rolling_all_paths(
    year: int = 2026,
    camp: str = "neutral_default",
    *,
    window: int = DEFAULT_WINDOW_YEARS,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Rolling-LCOE je Pfad für ein Start-Jahr (Pfad-Label-Matrix).

    Parallel zu :func:`enesys.core.sensitivity.baseline_all_paths`, aber
    Rolling-30-Jahres-Mittel statt Stichjahr-Snapshot. Default
    ``year=2026`` liefert das heutige »30-J-Mittel 2026-2055« —
    den kanonischen Vergleichswert der Pfad-Mengen-Bilanz.
    """
    return {
        PATH_LABEL[pid]: rolling_lcoe(
            pid,
            year,
            camp=camp,
            window=window,
            param_set=param_set,
            param_overrides=param_overrides,
        )
        for pid in _PATH_ORDER
    }
