"""
enesys — Open Source Cost-Robustness Analysis

Ein transparentes, reproduzierbares Modell der deutschen Energiewende
mit Vergleich von sechs Übergangspfaden für die Stromversorgung
2026-2055:

    WEITER-SO  Verlängerung des Status quo (Kohle-Restanteil + Erdgas)
    BESTAND    Bestandsflotten-Schwerpunkt, gedämpfter EE-Zubau
    EE-GAS     Erneuerbare + fossiles Gas-Backup
    EE-H2      Erneuerbare + Wasserstoff-Saisonspeicher (CO₂-frei)
    KKW-GAS    Atom-Wiedereinstieg + Bridge-Gas + fossiles Gas-Backup
    KKW-H2     Atom-Wiedereinstieg + Bridge-Gas + H2-Backup (CO₂-frei)

Public API
----------

Pfadmodell (2026-2055-Trajektorie, das Hauptarbeitspferd)::

    from enesys import (
        Demand, ForwardCostParams, TimePathParams, FlexibilityParams,
        GridStabilityParams, WeiterSoParams, WinterStressParams,
        compute_path, winter_stress_test, lole_p99_winter_stress_params,
    )

Sensitivitäts-Datenstrukturen (Slider-Bridge-Schicht)::

    from enesys import (
        PathSnapshotParams, PATH_NAMES, PATH_COLORS, PATH_MIXES,
        camp_preset_params, camp_range_2045, camp_value_2045,
    )

Sensitivitäts-Berechnung (Mengen-Bilanz-Schicht)::

    from enesys import (
        baseline_all_paths, compute_path,
        tornado_path_analysis, monte_carlo_all_paths,
    )

CO₂-Lock-in und Winter-Stresstest::

    from enesys import (
        co2_lockin_metric, co2_lockin_report,
        winter_stress_balance,
    )

Externe Parameter-Sets als Cross-Validation::

    from enesys import PARAM_SETS, ParamSet, baseline_all_paths
    prices = baseline_all_paths(year=2045, param_set="ariadne_pypsa")

Camp-Bandbreiten::

    from enesys import CAMP_RANGES, camp_range

Dokumentation
-------------

    - README.md           : Quickstart
    - docs/FORMULAS.md    : alle Modellgleichungen
    - docs/SOURCES.md     : Quellen-Traceability je Parameter
    - docs/HOWTO_RUN.md   : Detailliertes How-to
"""

# Datenstrukturen und Camp-Bandbreiten
# Die Param-Dataclasses (Demand, ForwardCostParams etc.) liegen in
# `path_inputs.py` (Konsumenten: Tests, Examples).
# Die Mengen-Bilanz-Schicht (compute_path, baseline_all_paths, PathResult)
# ist in `path_model.py` kanonisch.
from enesys.core.camp_ranges import (
    CAMP_RANGES,
    camp_range,
)
from enesys.core.param_sets import PARAM_SETS, ParamSet
from enesys.core.path_aggregations import (
    mean_mix,
    snapshot_mix,
    steady_state_mix,
)
from enesys.core.path_inputs import (
    Demand,
    FlexibilityParams,
    ForwardCostParams,
    GridStabilityParams,
    TimePathParams,
    WeiterSoParams,
)
from enesys.core.path_model import (
    PATH_LABEL,
    PathResult,
    co2_lockin_metric,
    co2_lockin_report,
    compute_path,
)

# 6-Pfad-Sensitivitätsanalyse
from enesys.core.path_sensitivity import (
    CAMP_RANGES_2045,
    PATH_COLORS,
    PATH_MIXES,
    PATH_NAMES,
    PathSnapshotParams,
    camp_preset_params,
    camp_range_2045,
    camp_value_2045,
)
from enesys.core.rolling_lcoe import (
    rolling_all_paths,
    rolling_lcoe,
    rolling_lcoe_trajectory,
)
from enesys.core.sensitivity import (
    baseline_all_paths,
    monte_carlo_all_paths,
    tornado_path_analysis,
)
from enesys.extensions.landuse import (
    DEFAULT_LANDUSE_PARAMS,
    LanduseParams,
    PathLanduseResult,
    compute_path_landuse,
)
from enesys.extensions.landuse import (
    compute_all_paths as compute_all_paths_landuse,
)
from enesys.extensions.winter_stress import (
    WinterStressParams,
    lole_p99_winter_stress_params,
    winter_stress_balance,
    winter_stress_test,
)
from enesys.version import __version__, get_version

__all__ = [
    "__version__",
    "get_version",
    # Camp-Bandbreiten
    "CAMP_RANGES",
    "camp_range",
    # Pfadmodell
    "Demand",
    "ForwardCostParams",
    "TimePathParams",
    "FlexibilityParams",
    "GridStabilityParams",
    "WinterStressParams",
    "WeiterSoParams",
    "PathResult",
    "compute_path",
    "winter_stress_test",
    "lole_p99_winter_stress_params",
    # 6-Pfad-Sensitivitätsanalyse — Datenstrukturen (Slider-Bridge)
    "PATH_NAMES",
    "PATH_COLORS",
    "PATH_MIXES",
    "PathSnapshotParams",
    "camp_preset_params",
    "camp_range_2045",
    "camp_value_2045",
    "CAMP_RANGES_2045",
    # Mengen-Bilanz-Modell
    "baseline_all_paths",
    "PATH_LABEL",
    # Mix-Aggregationen (Trajektorien-Lesung pro Pfad)
    "snapshot_mix",
    "mean_mix",
    "steady_state_mix",
    # Rolling LCOE (30-Jahres-Mittel als kanonische Trajektorien-Definition)
    "rolling_lcoe",
    "rolling_lcoe_trajectory",
    "rolling_all_paths",
    # Sensitivitäts-Analysen
    "tornado_path_analysis",
    "monte_carlo_all_paths",
    # CO₂-Lock-in
    "co2_lockin_metric",
    "co2_lockin_report",
    # Winter-Stresstest
    "winter_stress_balance",
    # Externe Parameter-Sets
    "PARAM_SETS",
    "ParamSet",
    # Flächen-Modell
    "LanduseParams",
    "DEFAULT_LANDUSE_PARAMS",
    "PathLanduseResult",
    "compute_path_landuse",
    "compute_all_paths_landuse",
]
