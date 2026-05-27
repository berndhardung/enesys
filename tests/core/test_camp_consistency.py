"""Konsistenztest: PathSnapshotParams-Defaults gegen CAMP_RANGES.

Sichert, dass die zentrale Lager-Tabelle (`core/lager_ranges.py:
CAMP_RANGES`) und die Default-Werte der Snapshot-Parameter in
`core/path_sensitivity.py:PathSnapshotParams` synchron bleiben.

**Methodischer Hintergrund:** `CAMP_RANGES` ist die zentrale Tabelle
für alle Tornado-Hebel mit ihrer Spannweite (ee_optimistic / neutral /
atom_optimistic). `PathSnapshotParams` definiert die Default-Werte für
die 5-Pfad-Snapshot-Bewertung 2045. Beide enthalten denselben
Parameter-Set; eine Drift zwischen `CAMP_RANGES["x"]["neutral_default"]`
und `PathSnapshotParams.x` würde bedeuten, dass die Snapshot-Berechnung
mit anderen Werten arbeitet als die Tornado-Sensitivität — methodisch
inkonsistent.

**Bewusste Ausnahme:** `grid_surcharge` ist absichtlich unterschiedlich:
- `CAMP_RANGES["grid_surcharge"]["neutral_default"] = 7.0` (Mittelwert
  der Tornado-Spannweite)
- `PathSnapshotParams.grid_surcharge = 5.5` (EE-optimistisches
  Snapshot-Ende — die Snapshot-Berechnung rechnet bewusst mit dem
  unteren Ende der Bandbreite, weil sie ein 2045-EE-System modelliert,
  in dem die Netzkosten durch Trassenausbau-Lernkurven gedrückt sind).

Diese Ausnahme ist im Test explizit dokumentiert. Wer den
`grid_surcharge`-Snapshot-Default ändern will, muss diese Ausnahme im
Test mit ändern UND die Begründung in der Box-Tiefenanalyse zu
Netzkosten anpassen.

**Folgewirkung im Workflow:** Wer einen Wert in `CAMP_RANGES` oder
`PathSnapshotParams` ändert, MUSS beide Stellen mitziehen — sonst
schlägt dieser Test fehl. Das ist genau das Drift-Präventions-Pattern,
das WACC schon hat (siehe `test_wacc_consistency.py`).
"""

from __future__ import annotations

import pytest

from enesys.core.camp_ranges import CAMP_RANGES
from enesys.core.path_sensitivity import PathSnapshotParams

# Bewusste Sonderfälle: Parameter, deren PSP-Default bewusst vom
# LAGER neutral_default abweicht. Schlüssel = Parameter-Name, Wert =
# Begründung (sichtbar in der Test-Fehlermeldung).
BEWUSSTE_AUSNAHMEN: dict[str, str] = {
    "grid_surcharge": (
        "Snapshot-Default 5.5 = EE-optimistisches Bandende; "
        "LAGER neutral_default 7.0 = Tornado-Mitte. "
        "Bewusste methodische Wahl: Snapshot rechnet 2045-EE-System "
        "mit gedrückten Netzkosten durch Trassenausbau-Lernkurve."
    ),
    # nep_realisierung_grad steht hier bewusst nicht: PSP-Default und
    # LAGER-neutral_default sind beide auf 0,65 gesetzt (kurzfristige
    # WEITERSO-Wettbewerbsfähigkeit im Modell verankert), also keine
    # echte Sonder-Fall-Diskrepanz.
}


def test_lager_neutral_default_synchron_mit_path_snapshot_params() -> None:
    """Default-Werte in PathSnapshotParams müssen mit CAMP_RANGES übereinstimmen.

    Mit Ausnahme der explizit dokumentierten Sonderfälle (siehe
    BEWUSSTE_AUSNAHMEN-Dict im Modul).
    """
    p = PathSnapshotParams()
    drifts: list[str] = []

    for param, spec in CAMP_RANGES.items():
        if not hasattr(p, param):
            # Parameter, der in CAMP_RANGES, aber nicht in PSP definiert ist
            # (z.B. CAPEX-Parameter, die nur in ForwardCostParams leben)
            continue
        psp_val = getattr(p, param)
        lager_val = spec["neutral_default"]
        if abs(psp_val - lager_val) > 1e-9:
            if param in BEWUSSTE_AUSNAHMEN:
                # Bewusster Sonderfall — kein Drift-Fehler
                continue
            drifts.append(
                f"  - {param}: LAGER={lager_val}, PSP={psp_val} "
                f"(Differenz {psp_val - lager_val:+.3f})"
            )

    assert not drifts, (
        "Drift zwischen CAMP_RANGES.neutral_default und "
        "PathSnapshotParams-Defaults:\n"
        + "\n".join(drifts)
        + "\n\nBewusste Ausnahmen (kein Drift): "
        + ", ".join(BEWUSSTE_AUSNAHMEN.keys())
    )


def test_bewusste_ausnahmen_sind_tatsaechlich_inkonsistent() -> None:
    """Die als Sonderfall markierten Parameter müssen tatsächlich abweichen.

    Wenn jemand z.B. `grid_surcharge` in `PathSnapshotParams` auf 7.0
    angleicht (was den Sonderfall obsolet macht), sollte der Eintrag
    aus BEWUSSTE_AUSNAHMEN entfernt werden — sonst dokumentiert
    BEWUSSTE_AUSNAHMEN eine nicht mehr existierende Diskrepanz.

    Dieser Test fängt den umgekehrten Fall: BEWUSSTE_AUSNAHMEN dürfen
    keine Geister-Einträge enthalten.
    """
    p = PathSnapshotParams()
    geister: list[str] = []

    for param in BEWUSSTE_AUSNAHMEN:
        spec = CAMP_RANGES.get(param)
        if not spec:
            geister.append(f"  - {param}: nicht in CAMP_RANGES")
            continue
        psp_val = getattr(p, param)
        lager_val = spec["neutral_default"]
        if abs(psp_val - lager_val) <= 1e-9:
            geister.append(
                f"  - {param}: PSP={psp_val} == LAGER={lager_val}, "
                f"BEWUSSTE_AUSNAHMEN-Eintrag ist veraltet"
            )

    assert not geister, "BEWUSSTE_AUSNAHMEN enthält Geister-Einträge:\n" + "\n".join(geister)


@pytest.mark.parametrize("param", sorted(CAMP_RANGES.keys()))
def test_camp_range_has_consistent_structure(param: str) -> None:
    """Jeder CAMP_RANGES-Eintrag hat die erwarteten Schlüssel.

    Damit ist sichergestellt, dass Tornado- und Lager-Code in der
    Lage sind, jeden Eintrag zu verarbeiten — ein Tippfehler beim
    Hinzufügen eines neuen Parameters fällt sofort auf.
    """
    spec = CAMP_RANGES[param]
    erwartet = {
        "neutral_default",
        "ee_optimistic",
        "atom_optimistic",
        "source_tag",
        "verteilung",
        "label",
    }
    fehlend = erwartet - set(spec.keys())
    assert not fehlend, f"CAMP_RANGES['{param}']: Schlüssel fehlen: {fehlend}"
