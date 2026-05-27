"""Template für neue ParamSets — als Vorlage kopieren, nicht direkt nutzen.

Anleitung
---------
1. Diese Datei nach ``{name}.py`` kopieren (z.B. ``nea_pcge.py``).
2. Trajektorien-Werte aus der externen Quelle übertragen (hard-coded,
   nicht aus CSV laden — explizite Werte im Code sind das ganze Ziel
   für Reproduzierbarkeit).
3. Mapping externer Tech-Namen → enesys-Tech-IDs in ``_TECH_MAPPING``
   anpassen. Vorsicht bei 1:n-Mappings (eine externe Quelle hat oft eine
   pauschale ``"nuclear"``-Kategorie, enesys unterscheidet
   ``kkw_bestand`` / ``kkw_neubau_epr`` / ``kkw_neubau_smr``).
4. Caveats vollständig dokumentieren — was differiert methodisch zwischen
   der Quelle und enesys? Lerneffekte, WACC-Behandlung, Bauzeit-
   Modellierung, Fuel-Preise.
5. Set in ``__init__.py`` Registry eintragen.
6. Convergence-Test ``tests/consistency/test_{name}_convergence.py``
   analog zu ``test_ariadne_convergence.py`` anlegen.

Die enesys-Tech-IDs siehe ``src/enesys/core/inventories/tech_inventory.py``,
die Fuel-IDs siehe ``src/enesys/core/inventories/fuel_inventory.py``.
"""

from __future__ import annotations

from enesys.core.param_sets._base import ParamSet, TrajectoryValue

# =============================================================================
# 1. ROHWERTE der externen Quelle
# =============================================================================
# Konvention: Werte in nativer Einheit der Quelle, möglichst nahe am Original.
# Umrechnung auf enesys-Einheiten erst in ``_TECH_MAPPING`` bzw.
# ``build_trajectories``.

# Beispiel: CAPEX-Trajektorien in EUR/kW
_CAPEX_TRAJECTORY: dict[str, TrajectoryValue] = {
    # "pv":           {2030: 482.48, 2040: 403.38, 2050: 367.87},
    # "onwind":       {2030: 1383.31, 2040: 1305.83, 2050: 1286.47},
    # "nuclear":      10805.70,  # zeitkonstant
}

# Brennstoffpreise in EUR/MWh_th
_FUEL_TRAJECTORY: dict[str, TrajectoryValue] = {
    # "gas":     {2030: 28.42, 2040: 25.59, 2050: 22.76},
    # "nuclear": 7.45,
}


# =============================================================================
# 2. MAPPING — externe Tech-Namen auf enesys-Tech-IDs
# =============================================================================
# Hier ist Vorsicht geboten: externe Quellen haben oft pauschale
# Kategorien (»nuclear«, »gas«); enesys differenziert feiner.

_TECH_MAPPING: dict[str, tuple[str, ...]] = {
    # "pv":        ("pv",),
    # "onwind":    ("wind_onshore",),
    # "nuclear":   ("kkw_bestand", "kkw_neubau_epr", "kkw_neubau_smr"),
}

# enesys-Fuel-IDs siehe inventories/fuel_inventory.py:
#   erdgas_inland, erdgas_import, lng, h2_inland, h2_import,
#   bio_strom, uran, steinkohle, braunkohle
_FUEL_MAPPING: dict[str, str] = {
    # "gas":     "erdgas_import",   # heute dominante Quelle
    # "nuclear": "uran",
    # "coal":    "steinkohle",      # Lazard-Standard, nicht Braunkohle
}


# =============================================================================
# 3. BUILD-FUNKTION
# =============================================================================


def build_trajectories() -> dict[str, TrajectoryValue]:
    """Konstruiert das Trajektorien-Dict für ``ParamSet.trajectories_factory``.

    Returns
    -------
    Dict mit Keys ``"<tech_id>.<field>"`` oder ``"<fuel_id>.preis_eur_mwh"``.
    Werte sind float (zeitkonstant) oder dict[int, float] (Stützstellen).
    """
    t: dict[str, TrajectoryValue] = {}

    # CAPEX-Trajektorien
    for ext_name, enesys_ids in _TECH_MAPPING.items():
        capex = _CAPEX_TRAJECTORY[ext_name]
        for enesys_id in enesys_ids:
            t[f"{enesys_id}.capex_eur_kw"] = capex

    # Fuel-Preis-Trajektorien
    for ext_fuel, enesys_fuel in _FUEL_MAPPING.items():
        t[f"{enesys_fuel}.preis_eur_mwh"] = _FUEL_TRAJECTORY[ext_fuel]

    return t


# =============================================================================
# 4. PARAMSET-INSTANZ
# =============================================================================

# Diese Konstante ist der Export. Name in der Registry (__init__.py)
# muss identisch sein.
TEMPLATE_SET = ParamSet(
    name="template",
    description="Template — als Vorlage kopieren, nicht direkt registrieren",
    source="N/A",
    reference_years=(2030, 2040, 2050),
    currency_year=2025,
    trajectories_factory=build_trajectories,
    caveats=("Dies ist nur eine Vorlage — Werte und Mapping müssen pro Quelle befüllt werden.",),
)


# =============================================================================
# 5. INSPEKTIONS-CLI
# =============================================================================
#
# Aufruf:    python -m enesys.core.param_sets.<name>
# Zweck:     schnelle Sichtprüfung der erzeugten Overrides ohne Modell-Lauf.


def _main() -> None:
    print(TEMPLATE_SET.summary())
    print()
    print("Generierte Overrides für 2045 (interpoliert):")
    for key, value in sorted(TEMPLATE_SET.overrides(year=2045).items()):
        print(f"  {key:<40} = {value:>10.2f}")


if __name__ == "__main__":
    _main()
