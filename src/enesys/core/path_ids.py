"""Zentrale Pfad- und Camp-Konstanten — Single Source of Truth.

Diese Konstanten ersetzen verstreute Magic-Strings im Code. Alle
Konsumenten — Pipeline, Sensi, Charts, Tests — importieren von hier.

Verwendung
----------
.. code-block:: python

    from enesys.core.path_ids import (
        PATH_IDS,
        ACTIVE_PATH_IDS,
        CAMP_IDS,
        PathId,
        CampId,
    )

    for path_id in PATH_IDS:
        result = compute_path(path_id, years=[2045])
"""

from __future__ import annotations

from typing import Literal

#: Alle sechs Pfade in kanonischer Reihenfolge: WEITER-SO, BESTAND, EE-GAS,
#: EE-H2, KKW-GAS, KKW-H2. Übergreifend in Code, Tests und Charts genutzt.
PATH_IDS: tuple[str, ...] = (
    "weiterso",
    "bestand",
    "ee_gas",
    "ee_h2",
    "kkw_gas",
    "kkw_h2",
)

#: Die fünf programmatisch-aktiven Pfade ohne WEITER-SO (passive Drift).
#: Werden für Mengen-Bilanz-Konsistenzprüfungen und Reue-Vergleiche
#: konsumiert, in denen WEITER-SO als Referenz-Pfad ausgeklammert ist.
ACTIVE_PATH_IDS: tuple[str, ...] = (
    "bestand",
    "ee_gas",
    "ee_h2",
    "kkw_gas",
    "kkw_h2",
)

#: Die vier kanonischen Welt-Lager plus die WEITER-SO-Position als fünfter
#: Eintrag. Konvention aus `core/camp_ranges.py` — neutral als Anker, plus
#: vier adversarielle Lager-Welten (EE/Atom/Bestand/WEITER-SO).
CAMP_IDS: tuple[str, ...] = (
    "neutral_default",
    "ee_optimistic",
    "atom_optimistic",
    "bestand_optimistic",
    "weiterso_optimistic",
)

#: Pfad-ID als Literal-Type für statische Type-Checks.
PathId = Literal[
    "weiterso",
    "bestand",
    "ee_gas",
    "ee_h2",
    "kkw_gas",
    "kkw_h2",
]

#: Lager-ID als Literal-Type für statische Type-Checks.
CampId = Literal[
    "neutral_default",
    "ee_optimistic",
    "atom_optimistic",
    "bestand_optimistic",
    "weiterso_optimistic",
]

__all__ = [
    "PATH_IDS",
    "ACTIVE_PATH_IDS",
    "CAMP_IDS",
    "PathId",
    "CampId",
]
