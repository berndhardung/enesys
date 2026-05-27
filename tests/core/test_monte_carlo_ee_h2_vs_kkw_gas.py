def test_monte_carlo_ee_h2_vs_kkw_gas():
    """Monte-Carlo-Methodik zitiert P(EE-H2 < KKW-GAS) und
    P(min(EE-H2, EE-GAS) < KKW-GAS).

    ``monte_carlo_all_paths`` ist konservativ angelegt (Uniform-Sampling
    über strukturelle CAPEX/WACC/CO2/Brennstoff-Hebel inkl. NEP/KKW-
    Realgrad). Die Hebel-Variation macht den Paar-Vergleich
    EE-H2 vs. KKW-GAS instabil (Toss-up-Korridor 5-80 %); der
    methodisch belastbare »EE-Pfad-Vorsprung«-Befund ist
    ``min(EE-H2, EE-GAS) < KKW-GAS`` und liegt nahe 100 %.

    Geprüft:
    - P(EE-H2 günstiger als KKW-GAS) im Korridor 5-80 % (Toss-up)
    - P(min(EE-H2, EE-GAS) < KKW-GAS) ≥ 75 % (robust)
    """
    import numpy as np

    from enesys.core.sensitivity import monte_carlo_all_paths

    mc = monte_carlo_all_paths(n_runs=3000, seed=42)
    ee_h2 = np.array(mc["prices_per_path"]["EE-H2"])
    ee_gas = np.array(mc["prices_per_path"]["EE-GAS"])
    kkw_gas = np.array(mc["prices_per_path"]["KKW-GAS"])

    p_ee_h2_winning = float(np.mean(ee_h2 < kkw_gas))
    p_either_winning = float(np.mean(np.minimum(ee_h2, ee_gas) < kkw_gas))

    assert 0.05 <= p_ee_h2_winning <= 0.80, (
        f"P(EE-H2 < KKW-GAS) = {p_ee_h2_winning * 100:.1f}%, erwartet 5–80 % Korridor."
    )
    # h2_realisierung_grad operativ verteuert EE-H2 in h2-Skepsis-Welten
    # signifikant; das min-Argument bleibt dominant bei 75–100 %.
    assert 0.75 <= p_either_winning <= 1.00, (
        f"P(min(EE-H2, EE-GAS) < KKW-GAS) = {p_either_winning * 100:.1f}%, erwartet 75–100 %."
    )
