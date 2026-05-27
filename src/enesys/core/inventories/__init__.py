"""Daten-Inventare für das Kapazitäts-/Dispatch-Modell.

Vier Inventare:

- `TECH_INVENTORY` — Erzeugungs-Technologien (Bestand, Zubau, CAPEX, WACC, …)
- `FUEL_INVENTORY` — mengenbegrenzte Brennstoffe (Dauer-/Boost-Mengen, Preis, CO₂)
- `PATH_POLICY` — Pfad-Politik (Dispatch-Reihenfolge, Constraints, Politik-Default)
- `DEMAND_CURVES` — Demand-Trajektorie pro Pfad

Plus Schema-Klassen `TechEntry`, `FuelEntry`, `PathPolicyEntry`,
`PolicySetting`, `DemandCurve`. Befüllung aus heutigen Modell-Konstanten
und Source-Tags.
"""

from __future__ import annotations

from .demand_curves import DEMAND_CURVES, DemandCurve
from .fuel_inventory import FUEL_INVENTORY, FuelEntry
from .path_policy import PATH_POLICY, PathPolicyEntry, PolicySetting
from .tech_inventory import TECH_INVENTORY, TechEntry

__all__ = [
    "DEMAND_CURVES",
    "DemandCurve",
    "FUEL_INVENTORY",
    "FuelEntry",
    "PATH_POLICY",
    "PathPolicyEntry",
    "PolicySetting",
    "TECH_INVENTORY",
    "TechEntry",
]
