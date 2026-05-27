"""Invarianten-Test: `_SEKTOR_KOPPLUNG_REALGRAD` (demand_curves.py) und
`PATH_POLICY[*].default_policy.nep_realization_rate` (path_policy.py)
sind zwei konzeptionell GETRENNTE Größen, dürfen aber nicht beliebig
auseinanderlaufen.

Hintergrund:
- `nep_realisierung_grad` (path_policy) = Realisierungs-Grad der EE-Soll-
  Kapazität (NEP-Pfad). Bestimmt, wie viel der politisch geplanten EE-
  Erzeugung tatsächlich gebaut wird.
- `_SEKTOR_KOPPLUNG_REALGRAD` (demand_curves) = Hochlauf-Geschwindigkeit
  der zusätzlichen Strom-Nachfrage aus Sektor-Kopplung (WP, E-Mob,
  Industrie). Bestimmt, wann das Soll-Plateau (350/50/20 TWh) erreicht
  wird.

In KKW-Pfaden ist Sektor-Kopplungs-Realgrad höher als
`nep_realisierung_grad`, weil KKW-Backup die Sektor-Kopplung trägt.
In WSO/BESTAND identisch zu `nep_realisierung_grad` (politisch gedämpfter
Hochlauf gewollt).

Invariante: `_SEKTOR_KOPPLUNG_REALGRAD[pid] >= path_policy[pid].
nep_realisierung_grad`. Der Demand-Hochlauf darf nicht langsamer sein als
die EE-Erzeugung — sonst entstünde fossiler Backup-Bedarf trotz
vorhandenem EE-Strom.
"""

from enesys.core.inventories.demand_curves import (
    _PLATEAU_TWH_PRO_PFAD,
    _SEKTOR_KOPPLUNG_REALGRAD,
)
from enesys.core.inventories.path_policy import PATH_POLICY


def test_sektor_kopplung_realgrad_nicht_unter_nep_realisierung_grad() -> None:
    """`_SEKTOR_KOPPLUNG_REALGRAD[pid]` muss ≥ `path_policy.nep_realisierung_grad`
    sein. Andernfalls würde der Demand-Hochlauf langsamer als die EE-
    Erzeugung laufen — der EE-Strom hätte keine Abnehmer."""
    for path_id, entry in PATH_POLICY.items():
        nep_erzeugung = entry.default_policy.nep_realization_rate
        nep_demand = _SEKTOR_KOPPLUNG_REALGRAD[path_id]
        assert nep_demand >= nep_erzeugung, (
            f"Invariante verletzt für {path_id!r}: "
            f"_SEKTOR_KOPPLUNG_REALGRAD={nep_demand} < "
            f"path_policy.nep_realisierung_grad={nep_erzeugung}. "
            "Demand-Hochlauf darf nicht langsamer als EE-Erzeugung sein."
        )


def test_wso_bestand_synchron_zu_path_policy() -> None:
    """WSO/BESTAND tragen politisch gedämpften Hochlauf — hier muss
    `_SEKTOR_KOPPLUNG_REALGRAD` exakt dem `nep_realisierung_grad` folgen
    (politische Elektrifizierungs-Bremse wirkt direkt auf den Hochlauf)."""
    for path_id in ("weiterso", "bestand"):
        nep_erzeugung = PATH_POLICY[path_id].default_policy.nep_realization_rate
        nep_demand = _SEKTOR_KOPPLUNG_REALGRAD[path_id]
        assert nep_demand == nep_erzeugung, (
            f"{path_id}: WSO/BESTAND-Politik dämpft Demand und Erzeugung "
            f"gleichermaßen; _SEKTOR_KOPPLUNG_REALGRAD={nep_demand} "
            f"sollte = nep_realisierung_grad={nep_erzeugung} sein."
        )


def test_aktive_pfade_identischer_hochlauf() -> None:
    """Aktive Pfade (EE/KKW) müssen denselben Sektor-Kopplungs-Realgrad
    haben. EE-Pfade tragen mit EE-Hochlauf, KKW-Pfade mit EE+KKW — die
    Sektor-Kopplungs-Trajektorie ist trotzdem identisch (Politik-Vergleich
    ohne Demand-Asymmetrie-Verzerrung)."""
    aktive = {"ee_gas", "ee_h2", "kkw_gas", "kkw_h2"}
    werte = {_SEKTOR_KOPPLUNG_REALGRAD[p] for p in aktive}
    assert len(werte) == 1, (
        f"Aktive Pfade müssen identischen Sektor-Kopplungs-Hochlauf haben, "
        f"gefunden: {[(p, _SEKTOR_KOPPLUNG_REALGRAD[p]) for p in sorted(aktive)]}"
    )


def test_sector_coupling_realization_rate_covers_all_paths() -> None:
    """Alle 6 Pfade müssen in beiden Inventaren vorhanden sein."""
    assert set(_SEKTOR_KOPPLUNG_REALGRAD.keys()) == set(PATH_POLICY.keys())


def test_plateau_twh_per_path_covers_all_paths() -> None:
    """Plateau-Werte müssen für alle 6 Pfade gesetzt sein."""
    assert set(_PLATEAU_TWH_PRO_PFAD.keys()) == set(PATH_POLICY.keys())
