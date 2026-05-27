"""Registry externer Parameter-Sets als first-class Annahmen-Vergleichspunkte.

Ein ``ParamSet`` (siehe ``_base.py``) bündelt das Default-Annahmen-Substrat
einer externen Modellfamilie als reproduzierbares Trajektorien-Dict, das
über ``compute_path(param_set="<name>")`` als Override eingespielt wird.

Verwendung
----------

.. code-block:: python

    from enesys import baseline_all_paths

    # Mit externem Annahmen-Substrat:
    baseline_all_paths(year=2045, param_set="ariadne_pypsa")

    # Verfügbare Sets auflisten:
    from enesys.core.param_sets import PARAM_SETS
    print(list(PARAM_SETS))

Beitrag eines neuen Sets
------------------------
1. ``_template.py`` nach ``{name}.py`` kopieren.
2. Trajektorien-Werte, Tech-/Fuel-Mapping, Caveats befüllen.
3. Import + Registry-Eintrag hier ergänzen.
4. Convergence-Test ``tests/consistency/test_{name}_convergence.py``
   nach Vorbild von ``test_ariadne_convergence.py``.

Verfügbare Substrate
--------------------
- ``ariadne_pypsa`` — PyPSA-DE / Ariadne-Substrat, EE-leaning.
"""

from __future__ import annotations

from enesys.core.param_sets._base import ParamSet
from enesys.core.param_sets.ariadne_pypsa import ARIADNE_PYPSA

PARAM_SETS: dict[str, ParamSet] = {
    ARIADNE_PYPSA.name: ARIADNE_PYPSA,
}

# Optionale Substrate werden dynamisch nachregistriert, wenn das jeweilige
# Modul importierbar ist — so bleibt die Registry tolerant gegenüber
# Installationen, die ein Substrat noch nicht enthalten.
try:
    from enesys.core.param_sets.nea_pcge import NEA_PCGE
except ImportError:
    pass
else:
    PARAM_SETS[NEA_PCGE.name] = NEA_PCGE


def get(name: str) -> ParamSet:
    """Liefert ein ParamSet aus der Registry, mit klarem Fehler bei Tippfehlern."""
    if name not in PARAM_SETS:
        available = ", ".join(sorted(PARAM_SETS)) or "(keine)"
        raise KeyError(f"ParamSet {name!r} nicht in Registry. Verfügbar: {available}")
    return PARAM_SETS[name]


__all__ = ["PARAM_SETS", "ParamSet", "get"]
