"""WACC-Provenance: zentrale Quelle für WACC-Werte und ihre Herleitung.

Die WACC-Werte selbst leben in `ForwardCostParams.wacc_*` als
Default-Felder — das schützt die öffentliche API der importierenden
Module. Dieses Modul liefert zusätzlich:

- die **Bandbreiten** der jeweiligen Quellenliteratur (für
  Sensitivitäts-Analysen und Lager-Modelle),
- die **Quellen-Tags** zur Herleitung,
- eine **Konsistenz-Prüfung**, die in den Tests einfordert, dass die
  Default-Werte in `ForwardCostParams` mit dieser zentralen Quelle
  synchron bleiben.

Bei Wertänderung an einer der beiden Stellen muss die andere mit-
gezogen werden — der Konsistenztest schlägt sonst fehl und macht den
Drift sichtbar.

Konservative Setzung: innerhalb der Quellen-Bandbreite wählen die
Defaults für jeden WACC den Punkt, der den jeweiligen Pfad eher
ungünstiger erscheinen lässt (z. B. ``wacc_pv`` 5,0 % statt 4,8 %,
``wacc_nuclear`` 9,0 % statt 9,5 %). Damit ist das Ergebnis robust
gegen WACC-Sensitivitätsläufe innerhalb der Quellenbandbreite. Details
in ``docs/SOURCES.md`` Abschnitt C.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WaccProvenance:
    """Herleitung und Bandbreite eines WACC-Wertes.

    Felder:
        name: Bezeichner (entspricht ForwardCostParams.wacc_<name>)
        default: tatsächlich verwendeter Default-Wert (Anteil, nicht Prozent)
        lower_bound: untere Plausibilitätsgrenze laut Quellenliteratur
        upper_bound: obere Plausibilitätsgrenze laut Quellenliteratur
        source_tag: SRC- oder CALIBRATED-Tag aus SOURCES.md
        rationale: kurze Begründung (1-2 Sätze)
    """

    name: str
    default: float
    lower_bound: float
    upper_bound: float
    source_tag: str
    rationale: str


# Zentrale Tabelle. Bei Änderung an einem Default hier MUSS die
# entsprechende Default-Zuweisung in ForwardCostParams.wacc_<name>
# mitgezogen werden — der Konsistenztest in tests/core/ schlägt sonst fehl.
WACC_TABLE: dict[str, WaccProvenance] = {
    "pv": WaccProvenance(
        name="pv",
        default=0.05,
        lower_bound=0.038,
        upper_bound=0.065,
        source_tag="CALIBRATED:IRENA-2024-WACC",
        rationale=(
            "EU-Mittel 3,8% + DE-Premium-Aufschlag → oberes Drittel der "
            "EU-Spanne bei 5,0% (konservative Setzung am oberen Ende der "
            "Quellen-Bandbreite, EE-Pfade werden dadurch eher teurer "
            "gerechnet)."
        ),
    ),
    "wind": WaccProvenance(
        name="wind",
        default=0.06,
        lower_bound=0.045,
        upper_bound=0.075,
        source_tag="CALIBRATED:IRENA-2024",
        rationale=(
            "WEU 3,3% + DE-NIMBY/Genehmigungs-Aufschlag → 6,0%. "
            "Spannweite reflektiert Onshore- vs. Offshore-Risikoprämie "
            "und politische Genehmigungsunsicherheit."
        ),
    ),
    "nuclear": WaccProvenance(
        name="nuclear",
        default=0.090,
        lower_bound=0.07,
        upper_bound=0.10,
        source_tag="CALIBRATED:HPC-Helm-Oxford+Sizewell-RAB",
        rationale=(
            "Alle drei Werte sind real (nicht nominal). HPC realisierter "
            "WACC 9,0% ist real terms equity return über CPI-indexiertes "
            "CfD (Helm-Oxford; UK Parliament HPC0003 Evidence: NNBG erhält "
            "£79,7 Mrd 'in real terms, 2016 prices'). Sizewell-C-RAB 6,7% "
            "real CPIH (UK GOV) als untere Grenze, Privat-Investor 10% als "
            "obere."
        ),
    ),
    "battery": WaccProvenance(
        name="battery",
        default=0.07,
        lower_bound=0.06,
        upper_bound=0.085,
        source_tag="CALIBRATED:BNEF-2025-ESS-implizit",
        rationale=(
            "Oberhalb von Solar (5%) wegen Asset-Klasse-Neuheit, "
            "unterhalb von KKW (9,0%) wegen kürzerer Bauzeit und "
            "etablierter Lieferkette."
        ),
    ),
}


def get(name: str) -> WaccProvenance:
    """Provenance eines WACC-Wertes.

    >>> get("nuclear").default
    0.09
    """
    return WACC_TABLE[name]


def all_names() -> tuple[str, ...]:
    """Alle in der Tabelle definierten WACC-Namen."""
    return tuple(WACC_TABLE.keys())
