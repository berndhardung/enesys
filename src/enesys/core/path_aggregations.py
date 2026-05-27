"""Aggregations-Funktionen für die Pfad-Mix-Trajektorie.

Zentrale Schnittstelle für Chart-Generatoren und Analyse-Skripte, die
Mix-Aussagen über Jahresscheiben formulieren. Single Source für drei
Lesungen:

- :func:`snapshot_mix` — ein Stichjahr.
- :func:`mean_mix` — arithmetisches Mittel der Tech-Anteile über einen
  Jahres-Bereich (inklusive Endpunkte).
- :func:`steady_state_mix` — Mittel über 2055-2084 (30-J-Steady-State).

Alle Funktionen ziehen ihren Mix aus :attr:`PathResult.mix_by_technology`.
Aggregation: arithmetisches Mittel der Anteile pro Tech über die Jahre
des Bereichs, nicht gewichtet nach Dispatch-Volumen — entspricht der
methodischen Lesung »wie sieht der Mix im Schnitt der Periode aus«.
"""

from __future__ import annotations

from enesys.core.path_model import compute_path

DEFAULT_STEADY_START = 2055
DEFAULT_STEADY_END = 2084


def snapshot_mix(
    path_id: str,
    year: int,
    camp: str = "neutral_default",
    *,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Pro-Tech-Anteil an der Strom-Erzeugung in einem Stichjahr.

    Wrapper um :func:`compute_path`; liefert den ``mix_by_technology``-
    Eintrag des Jahres direkt zurück. Summe ~1 (Mengen-Bilanz schließt).
    """
    result = compute_path(
        path_id,
        [year],
        camp=camp,
        param_set=param_set,
        param_overrides=param_overrides,
    )[0]
    return dict(result.mix_by_technology)


def mean_mix(
    path_id: str,
    year_from: int,
    year_to: int,
    camp: str = "neutral_default",
    *,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Arithmetisches Mittel der Tech-Anteile über (``year_from``, ``year_to``).

    Beide Endpunkte inklusive. Aggregations-Regel: Anteil pro Tech pro
    Jahr aufsummieren, durch Anzahl der Jahre teilen. Techs, die in
    keinem Jahr dispatch tragen, fehlen im Ergebnis. Summe ~1.
    """
    if year_from > year_to:
        raise ValueError(f"year_from ({year_from}) muss <= year_to ({year_to}) sein")
    years = list(range(year_from, year_to + 1))
    results = compute_path(
        path_id,
        years,
        camp=camp,
        param_set=param_set,
        param_overrides=param_overrides,
    )
    accumulator: dict[str, float] = {}
    for result in results:
        for tech_id, share in result.mix_by_technology.items():
            accumulator[tech_id] = accumulator.get(tech_id, 0.0) + share
    n = len(results)
    return {tech_id: total / n for tech_id, total in accumulator.items()}


def steady_state_mix(
    path_id: str,
    camp: str = "neutral_default",
    *,
    start: int = DEFAULT_STEADY_START,
    end: int = DEFAULT_STEADY_END,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Mix-Mittel über den Steady-State-Bereich (Default 2055-2084).

    Dünner Alias für :func:`mean_mix` mit den kanonischen Steady-State-
    Endpunkten. ``start``/``end`` sind Sensi-Hebel für Analyse-Skripte.
    """
    return mean_mix(
        path_id,
        start,
        end,
        camp=camp,
        param_set=param_set,
        param_overrides=param_overrides,
    )
