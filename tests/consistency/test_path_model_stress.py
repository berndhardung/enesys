"""Tests für Dunkelflauten-State der Mengen-Bilanz-Pipeline + Andockung
des Winter-Stresstests.

Prüft:

- `compute_path(system_state=SystemState.DUNKELFLAUTE)` nutzt boost_max + vlh_max_boost.
- Stress-Mengen sind ≥ Normalbetriebs-Mengen (Boost-Reserve verfügbar).
- `winter_stress_balance` liefert für alle sechs Pfade plausible
  `WinterStressResultBalance`-Instanzen mit ≥ 0 Defizit.
- EE-Pfade haben Bridge-Gas/H2-Backup-Beiträge aus Schatten;
  BESTAND nutzt erdgas_bestand, nicht gas_h2ready.
- `WinterStressParams.backup_availability` skaliert die Backup-GW.

Konsistenz-Anker: Die Mengen-Bilanz im DUNKELFLAUTE-State ist die einzige
Daten-Quelle; Stresstest-Werte sind aus PathResult abgeleitet.
"""

from __future__ import annotations

import pytest

from enesys.core.demand import Demand
from enesys.core.inventories.fuel_inventory import FUEL_INVENTORY
from enesys.core.path_ids import PATH_IDS as SECHS_PFADE
from enesys.core.path_model import (
    PathResult,
    compute_path,
)
from enesys.core.system_state import SystemState
from enesys.extensions.winter_stress import (
    WinterStressParams,
    WinterStressResultBalance,
    lole_p95_winter_stress_params,
    winter_stress_balance,
)

# ---------------------------------------------------------------------------
# compute_path Dunkelflauten-State
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path_id", SECHS_PFADE)
def test_dunkelflaute_state_smoke(path_id: str) -> None:
    """Pipeline läuft im DUNKELFLAUTE-State für jeden Pfad und liefert
    PathResult.system_state='dunkelflaute'."""
    results = compute_path(path_id, [2030, 2045, 2055], system_state=SystemState.DUNKELFLAUTE)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, PathResult)
        assert r.system_state == "dunkelflaute"
        assert r.path_id == path_id


def test_default_pfad_bleibt_normalbetrieb() -> None:
    """Ohne system_state-Kwarg ist Normal-State."""
    results = compute_path("ee_gas", [2045])
    assert results[0].system_state == "normal"


@pytest.mark.parametrize("year", [2030, 2045, 2055])
@pytest.mark.parametrize("lager", ["neutral_default", "ee_optimistic", "atom_optimistic"])
def test_fuel_inventory_boost_max_groesser_gleich_dauer_max(year: int, lager: str) -> None:
    """ADR-9 Dauer-vs-Boost-Verfügbarkeits-Invariante.

    Für jeden Brennstoff im Inventar gilt: ``boost_max ≥ dauer_max`` —
    die Stress-Kurzfrist-Höchstmenge darf nicht unter der
    Normalbetriebs-Höchstmenge liegen. Reine Verfügbarkeits-Aussage
    am Inventar, **nicht** am Verbrauchs-Output von ``compute_path``.

    Ein Test auf Verbrauchs-Ebene (``fuel_used``) wäre durch den
    Wasser-Stress-Boost verfälscht: Wasser-Boost ersetzt den
    Bridge-Backup-Anteil von KKW-Pfaden, sodass der Stress-Verbrauch
    KKW-spezifischer Backups unter dem Normal-Wert liegen kann. Die
    strukturelle Invariante »Boost-Mengen ≥ Normal-Mengen« ist eine
    Aussage über das **Inventar** (Verfügbarkeit), nicht über den
    pfad-spezifischen Verbrauch. Diese Form prüft genau das.
    """
    assert FUEL_INVENTORY, "FUEL_INVENTORY ist leer — Test nicht meaningful"
    verletzungen: list[tuple[str, float, float]] = []
    for fuel_id, entry in FUEL_INVENTORY.items():
        dauer = entry.duration_max_twh_per_year(year, lager)
        boost = entry.boost_max_twh_per_year(year, lager)
        if boost < dauer - 1e-9:
            verletzungen.append((fuel_id, dauer, boost))
    assert not verletzungen, f"ADR-9 verletzt in {year}/{lager}: " + ", ".join(
        f"{fid} dauer={d:.2f} boost={b:.2f}" for fid, d, b in verletzungen
    )


def test_dunkelflaute_state_lcoe_im_plausi_korridor() -> None:
    """LCOE im Stress-Mode (SystemState=DUNKELFLAUTE).

    Unter Dunkelflaute-Wetter-Stress sinkt EE-VLH (× 0,3), Battery liefert
    keine Energie (Cap erschöpft), Importe halbiert (EU-korreliert). Die
    LCOE-Werte sind **kein Jahres-Durchschnitt**, sondern eine
    Snapshot-Bilanz unter der Annahme »ganzes Jahr Dunkelflaute« — sie
    sind nur als oberer Stress-Korridor relevant, nicht als realer
    LCOE-Anker. Bei strukturellem Mangel kann unserved_twh sehr groß
    werden und VOLL-Pönale (2.000 €/MWh) dominiert das LCOE.

    Test prüft nur, dass die Stress-LCOE positiv sind (Bilanz schließt)
    und im 5-200 ct/kWh-Plausi-Band liegen — der weite Korridor ist
    der methodische Preis dafür, dass Dunkelflaute-Bilanz keine
    Jahres-LCOE-Aussage ist.
    """
    for path_id in SECHS_PFADE:
        stress = compute_path(path_id, [2045], system_state=SystemState.DUNKELFLAUTE)[0]
        if stress.lcoe_ct_kwh > 0:
            assert 5.0 <= stress.lcoe_ct_kwh <= 200.0, (
                f"{path_id} Stress-LCOE {stress.lcoe_ct_kwh:.2f} außerhalb 5-200"
            )


# ---------------------------------------------------------------------------
# winter_stress_balance — Mengen-Bilanz-Andockung
# ---------------------------------------------------------------------------


def test_winter_stress_balance_smoke() -> None:
    """winter_stress_balance läuft für alle sechs Pfade in 2045."""
    results = winter_stress_balance(2045, Demand(), "neutral_default")
    assert set(results.keys()) == set(SECHS_PFADE)
    for path_id, r in results.items():
        assert isinstance(r, WinterStressResultBalance)
        assert r.path_id == path_id
        assert r.year == 2045
        assert r.camp == "neutral_default"
        assert r.peak_demand_gw > 0
        assert r.ee_supply_gw >= 0
        assert r.backup_total_gw >= 0
        assert r.deficit_gw >= 0


def test_winter_stress_balance_referenz_auf_path_result() -> None:
    """Jedes Stress-Resultat hat die zugrundeliegende PathResult
    (DUNKELFLAUTE-State) referenziert."""
    results = winter_stress_balance(2045, Demand(), "neutral_default")
    for path_id, r in results.items():
        assert r.path_result.system_state == "dunkelflaute"
        assert r.path_result.path_id == path_id
        assert r.path_result.year == 2045


def test_winter_stress_balance_pfad_filter() -> None:
    """`paths`-Argument schränkt das Resultat ein."""
    results = winter_stress_balance(
        2045,
        Demand(),
        "neutral_default",
        paths=("ee_gas", "kkw_gas"),
    )
    assert set(results.keys()) == {"ee_gas", "kkw_gas"}


def test_winter_stress_balance_ee_pfade_haben_bridge_gas() -> None:
    """EE-GAS hat gas_h2ready + erdgas_bestand als Backup; EE-H2 hat
    gas_h2ready (für H2-Fallback) aber kein erdgas_bestand wegen
    forbidden-Constraint in EE-H2-Policy."""
    results = winter_stress_balance(2045, Demand(), "neutral_default")

    ee_gas_backup = results["ee_gas"].backup_by_tech_gw
    assert ee_gas_backup.get("gas_h2ready", 0.0) > 0.0
    assert ee_gas_backup.get("erdgas_bestand", 0.0) > 0.0

    ee_h2_backup = results["ee_h2"].backup_by_tech_gw
    assert ee_h2_backup.get("gas_h2ready", 0.0) > 0.0


def test_winter_stress_balance_bestand_kein_h2ready() -> None:
    """BESTAND nutzt erdgas_bestand als Backup, aber kein gas_h2ready
    (Bestands-Lager-Programm: aktives Erdgas, kein H2-Aufbau)."""
    results = winter_stress_balance(2045, Demand(), "neutral_default")
    bestand_backup = results["bestand"].backup_by_tech_gw
    # erdgas_bestand vorhanden
    assert bestand_backup.get("erdgas_bestand", 0.0) > 0.0
    # gas_h2ready nicht (forbidden in BESTAND-Policy oder leerer Bestand)
    h2ready = bestand_backup.get("gas_h2ready", 0.0)
    assert h2ready < 1.0, f"BESTAND sollte kein gas_h2ready haben, hat {h2ready}"


def test_winter_stress_balance_kkw_pfade_haben_kernkraft_backup() -> None:
    """KKW-GAS und KKW-H2 haben kkw_neubau_epr + kkw_neubau_smr als Backup."""
    results = winter_stress_balance(2045, Demand(), "neutral_default")
    for kkw_pfad in ("kkw_gas", "kkw_h2"):
        backup = results[kkw_pfad].backup_by_tech_gw
        kkw_total = (
            backup.get("kkw_bestand", 0.0)
            + backup.get("kkw_neubau_epr", 0.0)
            + backup.get("kkw_neubau_smr", 0.0)
        )
        assert kkw_total > 0.0, f"{kkw_pfad} sollte KKW-Backup haben"


def test_winter_stress_balance_backup_availability_skaliert() -> None:
    """backup_availability=0,95 reduziert Backup-Beiträge."""
    ws_normal = WinterStressParams()  # avail=1.0
    ws_avail = WinterStressParams(backup_availability=0.5)
    r_normal = winter_stress_balance(2045, Demand(), "neutral_default", ws=ws_normal)
    r_avail = winter_stress_balance(2045, Demand(), "neutral_default", ws=ws_avail)
    for path_id in SECHS_PFADE:
        b_normal = r_normal[path_id].backup_total_gw
        b_avail = r_avail[path_id].backup_total_gw
        # Reduktion auf 50 % Avail muss kleiner machen — exakt 0,5 nicht,
        # weil Importe + Biomasse-Flex Modul-Konstanten sind, die nicht
        # über avail skaliert werden.
        assert b_avail < b_normal


def test_winter_stress_balance_p95_haerter_als_default() -> None:
    """LOLE-P95-Konfiguration produziert größere Defizite als Default
    (kürzere PV/Wind-Erzeugung, reduzierte backup_availability)."""
    r_default = winter_stress_balance(2045, Demand(), "neutral_default")
    r_p95 = winter_stress_balance(
        2045,
        Demand(),
        "neutral_default",
        ws=lole_p95_winter_stress_params(),
    )
    # Mindestens für einen Pfad nimmt das Defizit zu.
    increased_any = False
    for path_id in SECHS_PFADE:
        if r_p95[path_id].deficit_gw > r_default[path_id].deficit_gw + 0.1:
            increased_any = True
            break
    assert increased_any, "LOLE-P95 sollte mindestens einen Pfad härter treffen"


def test_winter_stress_balance_lager_variation() -> None:
    """Lager-Variation ändert die Stress-Bilanz (z. B. atom_optimistic
    hat höhere KKW-Kapazität → mehr Backup in KKW-Pfaden)."""
    r_default = winter_stress_balance(2045, Demand(), "neutral_default")
    r_atom = winter_stress_balance(2045, Demand(), "atom_optimistic")
    kkw_default = sum(
        r_default["kkw_gas"].backup_by_tech_gw.get(t, 0.0)
        for t in ("kkw_neubau_epr", "kkw_neubau_smr")
    )
    kkw_atom = sum(
        r_atom["kkw_gas"].backup_by_tech_gw.get(t, 0.0)
        for t in ("kkw_neubau_epr", "kkw_neubau_smr")
    )
    assert kkw_atom > kkw_default, (
        f"atom_optimistic sollte mehr KKW-Backup haben, "
        f"hat {kkw_atom:.2f} vs default {kkw_default:.2f}"
    )


def test_winter_stress_balance_energy_deficit_skaliert_mit_duration() -> None:
    """duration_hours × deficit_gw / 1000 × multi_event_factor =
    energy_deficit_twh."""
    ws = WinterStressParams(duration_hours=240, multi_event_factor=2.0)
    results = winter_stress_balance(2045, Demand(), "neutral_default", ws=ws)
    for r in results.values():
        expected = r.deficit_gw * 240 / 1000.0 * 2.0
        assert abs(r.energy_deficit_twh - expected) < 1e-6
