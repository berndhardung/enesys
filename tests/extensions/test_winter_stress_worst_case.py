"""Mechanik-Tests für den Worst-Case-Winter-Stresstest.

Sichert ab, dass die Verschärfungen ``lole_p99_winter_stress_params``
strukturell greifen (Felder gesetzt, Defizite strikt höher als der
Default-Test, Energy-Deficit skaliert mit ``multi_event_factor``) und
dass der Default-Test durch die zusätzlichen WS-Felder nicht
mitgezogen wird.
"""

from __future__ import annotations

from enesys import (
    Demand,
    TimePathParams,
    lole_p99_winter_stress_params,
    winter_stress_test,
)


def _setup():
    return Demand(), TimePathParams()


# =============================================================================
# Strukturelle Tests: Worst-Case ist strikt schärfer als Default
# =============================================================================


def test_worst_case_factory_sets_all_hardenings():
    """lole_p99_winter_stress_params() muss alle vier Worst-Case-Härtungen setzen.

    Wenn jemand einen Default-Wert verschiebt, sollte dieser Test die
    Drift fangen.
    """
    ws = lole_p99_winter_stress_params()
    assert ws.duration_hours == 336, "Worst-Case muss 14 Tage (336h) Dauer haben"
    assert ws.pv_capacity_factor < 0.03, "Worst-Case muss PV-CF strikt unter Default 3% setzen"
    assert ws.wind_capacity_factor < 0.10, "Worst-Case muss Wind-CF strikt unter Default 10% setzen"
    assert ws.backup_availability < 1.0, "Worst-Case muss Backup-Verfügbarkeit unter 100% setzen"
    assert ws.multi_event_factor > 1.0, "Worst-Case muss Mehrfach-Event-Faktor über 1 setzen"


def test_worst_case_defizite_strikt_hoeher_als_default_2045():
    """Im Jahr 2045 muss der Worst-Case-Test bei jedem Pfad ein höheres
    Defizit zeigen als der Default-Test.

    2045 ist gewählt, weil dort alle Pfade ihre Backup-Kapazitäten
    aufgebaut haben — wenn der Default-Test kein Defizit zeigt (was bei
    EE-GAS, EE-H2 und KKW-GAS der Fall ist), kann nur der Worst-Case
    Verschärfung sichtbar machen.
    """
    d, tp = _setup()
    res_default = winter_stress_test(2045, d, tp)
    res_worst = winter_stress_test(2045, d, tp, ws=lole_p99_winter_stress_params())

    for path in ["WEITER-SO", "EE-GAS", "EE-H2", "KKW-GAS", "KKW-H2"]:
        d_def = res_default[path].deficit_gw
        d_worst = res_worst[path].deficit_gw
        assert d_worst > d_def, (
            f"{path}: Worst-Case-Defizit ({d_worst:.2f} GW) muss > "
            f"Default ({d_def:.2f} GW) sein. Sonst wirkt die Verschärfung nicht."
        )


def test_worst_case_energy_deficit_skaliert_mit_multi_event():
    """multi_event_factor=3 muss energy_deficit_twh dreifach skalieren
    gegenüber sonst gleicher Konfiguration.

    Bestätigt, dass der Multiplikator nur Energie-Größen trifft, nicht
    Spitzenlast-Größen. Eine zweite Dunkelflaute hat dieselbe Spitze,
    aber verdoppelte Energiebilanz.
    """
    from enesys import WinterStressParams

    d, tp = _setup()

    ws_single = WinterStressParams(
        duration_hours=336,
        pv_capacity_factor=0.01,
        wind_capacity_factor=0.05,
        backup_availability=0.95,
        multi_event_factor=1.0,
    )
    ws_triple = WinterStressParams(
        duration_hours=336,
        pv_capacity_factor=0.01,
        wind_capacity_factor=0.05,
        backup_availability=0.95,
        multi_event_factor=3.0,
    )

    r_single = winter_stress_test(2045, d, tp, ws=ws_single)
    r_triple = winter_stress_test(2045, d, tp, ws=ws_triple)

    for path in ["WEITER-SO", "EE-GAS", "KKW-H2"]:
        assert r_triple[path].peak_demand_gw == r_single[path].peak_demand_gw, (
            f"{path}: Spitzenlast darf nicht durch multi_event_factor verändert werden"
        )
        assert r_triple[path].deficit_gw == r_single[path].deficit_gw, (
            f"{path}: Stunden-Defizit darf nicht durch multi_event_factor verändert werden"
        )
        # Energie-Defizit: 3x bei multi=3.0 (mit kleiner Toleranz für Rundung)
        if r_single[path].energy_deficit_twh > 0:
            ratio = r_triple[path].energy_deficit_twh / r_single[path].energy_deficit_twh
            assert 2.99 <= ratio <= 3.01, (
                f"{path}: energy_deficit-Skalierung ist {ratio:.2f}x, erwartet 3.0x"
            )


# =============================================================================
# Default-Test bleibt unverändert (Regression-Schutz)
# =============================================================================


def test_default_test_unveraendert_durch_worst_case_haertungen():
    """Der Default-Test (ohne ws-Parameter) muss bit-genau dasselbe
    Verhalten zeigen wie ohne Worst-Case-Härtungen.

    Die zwei zusätzlichen WinterStressParams-Felder (backup_availability
    und multi_event_factor) haben neutrale Defaults (1,0 / 1,0), damit
    der bestehende Test unverändert bleibt — sonst hätten die fünf
    Defizit-Anker-Tests in tests/conclusions/ mitgezogen werden müssen.

    Backup-Architektur kommt aus den Time-Paths (gas_existing + h2ready),
    Batterien zeitabhängig. Default 2045: EE-Pfade haben beide 0,22 GW
    Restdefizit (Pfad-Symmetrie), KKW-Pfade Defizit, weil mit
    kkw_realisierung_grad=0,40 als Default der KKW-Hochlauf auf 2049-2057
    gestreckt ist und KKW in 2045 noch nicht am Netz steht. Dieser Test
    prüft die Plan-Trajektorie
    (kkw_realisierung_grad=1,0, KKW-Lager-Optimum) — gestreckte Trajektorie
    in test_kkw_realisierung_grad_streckt_hochlauf.
    """
    from enesys import WinterStressParams

    ws = WinterStressParams()
    assert ws.backup_availability == 1.0
    assert ws.multi_event_factor == 1.0

    # Default 2045: KKW-Pfade sind defizit-frei in Plan-Trajektorie.
    # EE-Pfade tragen eine kleine Rest-Lücke (~0–2 GW) aus dem
    # H2-Backup-Hochlauf. Explizit kkw_realisierung_grad=1.0 für
    # Plan-Trajektorie-Test.
    d, _ = _setup()
    tp = TimePathParams(nuclear_realization_rate=1.0)
    res = winter_stress_test(2045, d, tp)
    assert res["KKW-GAS"].deficit_gw == 0.0
    assert res["KKW-H2"].deficit_gw == 0.0
    # EE-Pfade: kleine Rest-Lücke ≤ 2 GW; absoluter Wert ist sensibel
    # gegenüber der Demand-Trajektorie, deshalb nur Korridor-Test.
    assert 0.0 <= res["EE-GAS"].deficit_gw <= 2.0, (
        f"EE-GAS-Defizit {res['EE-GAS'].deficit_gw:.2f} GW außerhalb 0–2 GW."
    )
    assert 0.0 <= res["EE-H2"].deficit_gw <= 2.0, (
        f"EE-H2-Defizit {res['EE-H2'].deficit_gw:.2f} GW außerhalb 0–2 GW."
    )
    # Pfad-Symmetrie EE-GAS ↔ EE-H2: Defizite liegen dicht zusammen.
    assert abs(res["EE-GAS"].deficit_gw - res["EE-H2"].deficit_gw) < 0.5, (
        f"EE-Pfad-Symmetrie verletzt: EE-GAS {res['EE-GAS'].deficit_gw:.2f} "
        f"vs EE-H2 {res['EE-H2'].deficit_gw:.2f} GW."
    )
