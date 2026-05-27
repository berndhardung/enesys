"""Sensitivitäts-Analysen auf der Mengen-Bilanz: Tornado, Monte-Carlo,
Schadens-Asymmetrie.

Alle Funktionen sind dünne Wrapper um ``compute_path`` — sie variieren
``param_overrides`` und/oder ``camp`` und aggregieren das LCOE-Ergebnis.
Keine eigene Modell-Logik; bei Drift im Mengen-Bilanz-Kern fließen
neue Werte automatisch durch. Damit bleibt die Sensi-Schicht isoliert
testbar und der Orchestrator in ``path_model`` schlank.

Die 6-Pfad-LCOE-Matrix selbst (Pfad-Label → ct/kWh) liefert
:func:`enesys.core.rolling_lcoe.rolling_all_paths`. Der hier exportierte
Alias :func:`baseline_all_paths` ruft den Rolling-30-J-Mittelwert ab
``year``-Start auf — kanonische Trajektorien-Lesung statt Stichjahr.
"""

from __future__ import annotations

from enesys.core.path_model import _PATH_ORDER, PATH_LABEL, compute_path
from enesys.core.rolling_lcoe import rolling_all_paths

# ---------------------------------------------------------------------------
# 6-Pfad-LCOE-Matrix (Pfad-Label-Form)
# ---------------------------------------------------------------------------


def baseline_all_paths(
    year: int = 2026,
    camp: str = "neutral_default",
    *,
    window: int = 30,
    param_set: str | None = None,
    param_overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Rolling-LCOE-Matrix je Pfad ab Start-Jahr ``year`` × Lager.

    Liefert ``{Pfad-Label: ct/kWh}`` als Rolling-Mittel über
    (``year``, ``year + window - 1``). Default ``year=2026`` /
    ``window=30`` reproduziert den kanonischen Trajektorien-LCOE
    2026-2055. Stichjahr-Lesung über ``window=1``.

    Dünner Alias auf :func:`enesys.core.rolling_lcoe.rolling_all_paths`;
    Konsumenten der älteren Snapshot-API werden über den ``window``-
    Parameter mit der Rolling-Definition synchronisiert.

    `param_set` lädt ein externes Annahmen-Substrat aus der
    ``param_sets``-Registry (z.B. ``"ariadne_pypsa"``) und legt es als
    Override-Basis pro Pfad an. Für Quervalidierungen.
    """
    return rolling_all_paths(
        year,
        camp=camp,
        window=window,
        param_set=param_set,
        param_overrides=param_overrides,
    )


# ---------------------------------------------------------------------------
# Schadens-Asymmetrie auf Mengen-Bilanz (Anker 2)
# ---------------------------------------------------------------------------


_CAMP_LABEL: tuple[tuple[str, str], ...] = (
    ("ee_optimistic", "EE-Lager"),
    ("neutral_default", "Empirisch-Mittel"),
    ("atom_optimistic", "KKW-Lager"),
    ("bestand_optimistic", "Bestand-Lager"),
)
"""Vier kanonische Lager × Pfad-Label (EE / Empirisch-Mittel / KKW / Bestand).
NEP-Realgrad ist nicht als orthogonaler Parameter modelliert, sondern
integriert in der Lager-Definition."""


# ---------------------------------------------------------------------------
# Tornado + Monte-Carlo auf Mengen-Bilanz (strukturelle Hebel)
# ---------------------------------------------------------------------------


TORNADO_LEVERS: dict[str, tuple[float, float, str]] = {
    # Format: param_key -> (low_value, high_value, label)
    # Bandbreiten überwiegend aus Lager-Spreizung in TECH/FUEL_INVENTORY,
    # für Techs ohne Lager-Spreizung (Wind, Battery, Elektrolyse) ±25 % um
    # den neutralen Default als plausible Bandbreite (entspricht der
    # Spreizungs-Heuristik aus der Anchor-Tabelle).
    # --- CAPEX-Hebel (€/kW) -------------------------------------------------
    "pv.capex_eur_kw": (423.0, 700.0, "PV-CAPEX"),
    "wind_onshore.capex_eur_kw": (1050.0, 1750.0, "Wind-Onshore-CAPEX (±25 %)"),
    "wind_offshore.capex_eur_kw": (2250.0, 3750.0, "Wind-Offshore-CAPEX (±25 %)"),
    "kkw_neubau_epr.capex_eur_kw": (9000.0, 16000.0, "KKW-EPR-CAPEX"),
    "kkw_neubau_smr.capex_eur_kw": (6000.0, 14000.0, "KKW-SMR-CAPEX"),
    "gas_h2ready.capex_eur_kw": (825.0, 1375.0, "Gas-H2-Ready-CAPEX (±25 %)"),
    "battery.capex_eur_kw": (125.0, 207.0, "Batterie-CAPEX (±25 %)"),
    # --- WACC-Hebel (%) -----------------------------------------------------
    "pv.wacc_pct": (0.038, 0.065, "PV-WACC"),
    "wind_onshore.wacc_pct": (0.045, 0.075, "Wind-Onshore-WACC"),
    "kkw_neubau_epr.wacc_pct": (0.070, 0.100, "KKW-EPR-WACC"),
    "kkw_neubau_smr.wacc_pct": (0.070, 0.100, "KKW-SMR-WACC"),
    "gas_h2ready.wacc_pct": (0.065, 0.085, "Gas-H2-Ready-WACC"),
    "battery.wacc_pct": (0.060, 0.085, "Batterie-WACC"),
    # --- Globale Hebel ------------------------------------------------------
    "co2_price_eur_t": (80.0, 180.0, "CO₂-Preis €/t"),
    "erdgas_inland.preis_eur_mwh": (25.0, 50.0, "Erdgas-Preis €/MWh"),
    "h2_inland.preis_eur_mwh": (80.0, 130.0, "H₂-Inland-Preis €/MWh"),
    "h2_import.preis_eur_mwh": (90.0, 150.0, "H₂-Import-Preis €/MWh"),
    # --- Realgrad-Hebel (Mengen-Bilanz-Schicht) -----------------------------
    # nep_realisierung_grad: 0.40 (Status-quo) - 0.90 (NEP-Soll erfüllt),
    # Default 1.0 (kein Override). Bandbreite aus LAGER_RANGES.
    # kkw_realisierung_grad: 0.20 (EE-Lager pessimistisch) - 1.00 (Plan).
    "nep_realization_rate": (0.40, 0.90, "NEP-Realisierungsgrad"),
    "nuclear_realization_rate": (0.20, 1.00, "KKW-Realisierungsgrad"),
    # --- Battery-Tagesarbitrage-VLH (RTE-Verlust-Hebel) ---------------------
    # battery_discharge_vlh: 300 h/a (KKW-Bandlast-Welt) - 800 h/a (EE-PV-Welt).
    # Steuert den RTE-Verlust-Bedarf der Generatoren über
    # discharge_twh × (1/RTE − 1). Bandbreite aus CAMP_RANGES.
    "battery_discharge_vlh": (300.0, 800.0, "Battery-Discharge-VLH"),
}


def _rolling_lcoe_with_overrides(
    path_id: str,
    year: int,
    camp: str,
    window: int,
    overrides: dict[str, float],
) -> float:
    """Rolling-30-J-Mittel-LCOE mit Param-Overrides (ein compute_path-Aufruf)."""
    results = compute_path(
        path_id,
        list(range(year, year + window)),
        camp=camp,
        param_overrides=overrides,
    )
    return sum(r.lcoe_ct_kwh for r in results) / len(results)


def tornado_path_analysis(
    path_id: str,
    *,
    year: int = 2026,
    window: int = 30,
    baseline_camp: str = "neutral_default",
    baseline_overrides: dict[str, float] | None = None,
) -> list[dict]:
    """Tornado-Analyse pro Pfad: welcher Hebel bewegt Rolling-LCOE am stärksten?

    Für jeden Hebel aus ``TORNADO_LEVERS``: variiert zwischen low- und
    high-Wert (alle anderen Parameter auf ``baseline_camp``-Default,
    überschrieben durch ``baseline_overrides``), berechnet
    Rolling-30-Jahres-LCOE pro Variation, misst den Swing.

    ``year``/``window`` steuern den Rolling-Bereich (Default 2026-2055,
    der kanonische Trajektorien-LCOE). Stichjahr-Sensitivität über
    ``window=1``.

    ``baseline_overrides``: Override-Dict, das den Baseline-Punkt
    verschiebt — alle Tornado-Achsen variieren dann um diesen verschobenen
    Punkt. Streamlit-UIs nutzen das, um Slider-State (z.B.
    nep_realisierung_grad aus Top-Hebel-Slider) als Tornado-Baseline zu
    setzen statt nur Lager-Default.

    Output-Struktur::

        [
            {
                "parameter": "pv.capex_eur_kw",
                "label": "PV-CAPEX",
                "low_value": 423.0,
                "high_value": 700.0,
                "price_low": 16.20,    # Rolling-LCOE bei Low-Setzung
                "price_high": 16.85,   # Rolling-LCOE bei High-Setzung
                "swing": 0.65,         # |price_high - price_low|
                "baseline": 16.70,     # Rolling-LCOE bei baseline_camp-Default
            },
            ...
        ]

    Sortiert nach ``swing`` absteigend (größter Hebel oben).

    Strukturelle Hebel: nutzt CAPEX/WACC/Brennstoff/CO2-Hebel statt
    aggregierter LCOE-Komponenten — methodisch klarer, mit mehr
    Auflösung.
    """
    base_overrides = baseline_overrides or {}
    baseline_lcoe = _rolling_lcoe_with_overrides(
        path_id, year, baseline_camp, window, base_overrides
    )

    results: list[dict] = []
    for param_key, (lo, hi, label) in TORNADO_LEVERS.items():
        overrides_lo = {**base_overrides, param_key: lo}
        overrides_hi = {**base_overrides, param_key: hi}
        price_lo = _rolling_lcoe_with_overrides(path_id, year, baseline_camp, window, overrides_lo)
        price_hi = _rolling_lcoe_with_overrides(path_id, year, baseline_camp, window, overrides_hi)
        swing = abs(price_hi - price_lo)
        results.append(
            {
                "parameter": param_key,
                "label": label,
                "low_value": lo,
                "high_value": hi,
                "price_low": price_lo,
                "price_high": price_hi,
                "swing": swing,
                "baseline": baseline_lcoe,
            }
        )
    return sorted(results, key=lambda r: -r["swing"])


def monte_carlo_all_paths(
    *,
    year: int = 2026,
    window: int = 30,
    n_year_samples: int = 6,
    baseline_camp: str = "neutral_default",
    n_runs: int = 500,
    seed: int = 42,
    baseline_overrides: dict[str, float] | None = None,
) -> dict:
    """Monte-Carlo Rolling-LCOE über alle sechs Pfade.

    Für jeden der ``n_runs`` Samples wird pro Tornado-Hebel ein Wert aus
    der Uniform-Verteilung [low, high] gezogen, die Overrides werden zu
    einem ``param_overrides``-Dict kombiniert, und für alle sechs Pfade
    wird der Rolling-Mittel-LCOE über (``year``, ``year + window - 1``)
    berechnet. Default 2026-2055 = Pfad-Lebenszyklus-MC; Stichjahr-MC
    über ``window=1``.

    ``n_year_samples`` steuert die Trajektorien-Auflösung pro Sample:
    statt jedes Jahr im Fenster wird nur an ``n_year_samples`` gleich-
    verteilten Stützjahren gerechnet (Trapez-Approximation des Mittels).
    LCOE-Trajektorien sind glatt (Lernkurven, smooth Brennstoff-/CO₂-
    Pfade); 6 Stützjahre reichen für <0,05 ct/kWh Abweichung gegenüber
    voller Auflösung. Setzt ``n_year_samples=window`` für exakten
    Rolling-Mittel pro Sample.

    Zentrale Frage: P(EE-GAS < anderer Pfad) für jeden anderen Pfad.

    Mengen-Bilanz-Variante:

    - **uniform** statt normal/lognormal — konservativer (breitere
      Spannweite, weniger Häufung am Mittel)
    - **keine Korrelationen** — Default-Parameter sind unabhängig.

    Rückgabe-Struktur::

        {
            "n_runs": int,
            "prices_per_path": dict[str, np.ndarray],
            "p_ee_gas_wins_vs": dict[str, float],
            "p_ee_gas_top2": float,
            "ranking_distribution": dict[str, np.ndarray],
            "mean_per_path": dict[str, float],
            "std_per_path": dict[str, float],
            "p5_per_path": dict[str, float],
            "p95_per_path": dict[str, float],
            "use_correlations": bool,  # immer False in Mengen-Bilanz-Variante
        }
    """
    import numpy as np  # noqa: PLC0415

    rng = np.random.default_rng(seed)

    # Sample alle Tornado-Hebel uniform aus [lo, hi]
    sample_keys = list(TORNADO_LEVERS.keys())
    n_keys = len(sample_keys)
    # 2D-Array: shape (n_runs, n_keys) — vermeidet n_runs dict-Lookups in Schleife
    samples_2d = np.empty((n_runs, n_keys))
    for k_idx, param_key in enumerate(sample_keys):
        lo, hi, _label = TORNADO_LEVERS[param_key]
        samples_2d[:, k_idx] = rng.uniform(lo, hi, n_runs)

    # Pfad-Reihenfolge fest. EE-GAS-Index für Win-Prob + Top-2.
    path_labels = [PATH_LABEL[pid] for pid in _PATH_ORDER]
    ee_gas_idx = path_labels.index("EE-GAS")
    n_paths = len(_PATH_ORDER)
    # 2D-Preise-Array: shape (n_runs, n_paths) — eine Allokation, schneller Index-Zugriff
    prices_arr = np.empty((n_runs, n_paths))

    # Stützjahre für die Trapez-Approximation des Rolling-Mittels.
    # Gleichverteilt zwischen year und year + window - 1, dedupliziert.
    # window=1 ergibt ein Stichjahr; n_year_samples >= window nutzt alle Jahre.
    if n_year_samples < 1:
        raise ValueError(f"n_year_samples muss >= 1 sein, war {n_year_samples}")
    if n_year_samples >= window:
        sample_years = list(range(year, year + window))
    else:
        sample_years = (
            sorted(
                {
                    int(round(year + i * (window - 1) / (n_year_samples - 1)))
                    for i in range(n_year_samples)
                }
            )
            if n_year_samples > 1
            else [year]
        )
    n_sample_years = len(sample_years)

    # baseline_overrides als Basis-Dict; pro Run wird daraus eine in-place
    # geupdatete Kopie genutzt (vermeidet Dict-Allokation in der Schleife).
    bo = baseline_overrides or {}
    overrides: dict[str, float] = dict(bo)
    for i in range(n_runs):
        # Sample-Werte in das Overrides-Dict mergen (kollidierende Keys → Sample gewinnt).
        for k_idx, key in enumerate(sample_keys):
            overrides[key] = float(samples_2d[i, k_idx])
        for p_idx, pid in enumerate(_PATH_ORDER):
            rs = compute_path(pid, sample_years, camp=baseline_camp, param_overrides=overrides)
            prices_arr[i, p_idx] = sum(r.lcoe_ct_kwh for r in rs) / n_sample_years

    # P(EE-GAS < anderer Pfad) — vektorisiert über alle Runs auf einmal.
    ee_gas_col = prices_arr[:, ee_gas_idx]
    p_ee_gas_wins_vs: dict[str, float] = {}
    for p_idx, label in enumerate(path_labels):
        if p_idx == ee_gas_idx:
            continue
        p_ee_gas_wins_vs[label] = float(np.mean(ee_gas_col < prices_arr[:, p_idx]))

    # Ranking-Verteilung via argsort: eine NumPy-Operation statt n_runs Python-Sorts.
    # argsort(axis=1) liefert pro Run die Pfad-Indizes in aufsteigender Preis-Reihenfolge.
    ranked_indices = np.argsort(prices_arr, axis=1)
    # rankings[label] = Histogramm "wie oft landete dieser Pfad auf Rang 0,1,2,3,4,5"
    rankings: dict[str, np.ndarray] = {}
    for p_idx, label in enumerate(path_labels):
        # Position dieses Pfads pro Run = wo p_idx in ranked_indices[i] auftaucht.
        positions = np.argmax(ranked_indices == p_idx, axis=1)
        rankings[label] = np.bincount(positions, minlength=n_paths).astype(int)
    # EE-GAS-Top-2: in wie vielen Runs sitzt ee_gas_idx auf Rang 0 oder 1?
    n_top2 = int(
        np.sum((ranked_indices[:, 0] == ee_gas_idx) | (ranked_indices[:, 1] == ee_gas_idx))
    )

    # Output: prices_per_path als dict[label, ndarray] für Backwards-Compat
    # (Konsumenten greifen typisch über Label zu).
    prices: dict[str, np.ndarray] = {
        label: prices_arr[:, p_idx].copy() for p_idx, label in enumerate(path_labels)
    }

    return {
        "n_runs": n_runs,
        "prices_per_path": prices,
        "p_ee_gas_wins_vs": p_ee_gas_wins_vs,
        "p_ee_gas_top2": n_top2 / n_runs,
        "ranking_distribution": rankings,
        "mean_per_path": {label: float(np.mean(prices[label])) for label in path_labels},
        "std_per_path": {label: float(np.std(prices[label])) for label in path_labels},
        "p5_per_path": {label: float(np.percentile(prices[label], 5)) for label in path_labels},
        "p95_per_path": {label: float(np.percentile(prices[label], 95)) for label in path_labels},
        "use_correlations": False,
    }


def damage_asymmetry_settings(
    year: int = 2026,
    demand_twh_per_year: float = 858.0,
    jahre: int = 30,
    window: int = 30,
) -> list[dict]:
    """Pfad-Differenz und Geld-Schaden über die vier Lager.

    - Vier Lager: EE / Empirisch-Mittel / KKW / Bestand.
    - LCOE-Differenz kommt aus dem Rolling-Mittel über
      ``(year, year + window - 1)`` (Default 2026-2055 = kanonischer
      Lebenszyklus-LCOE).
    - Schadens-Größenordnung: ``|diff_ct_kwh| × demand_twh × jahre``.
      Strukturell von der Mengen-Bilanz-Architektur getragen.

    Rückgabe: Liste von Dicts mit Schlüsseln ``label``, ``lager``,
    ``wacc_nuclear``, ``nep_realisierung_grad`` (Welt-Belief-Werte aus
    LAGER_RANGES, narrativ für Buch- und Streamlit-Display),
    ``ee_gas_ct_kwh``, ``kkw_gas_ct_kwh``, ``diff_ct_kwh``,
    ``schaden_mrd_eur``, ``guenstigerer_pfad``.
    """
    from enesys.core.camp_ranges import CAMP_RANGES

    results = []
    for lager_id, label in _CAMP_LABEL:
        ee = _rolling_lcoe_with_overrides("ee_gas", year, lager_id, window, {})
        kkw = _rolling_lcoe_with_overrides("kkw_gas", year, lager_id, window, {})
        diff = kkw - ee
        schaden_mrd = abs(diff) / 100.0 * demand_twh_per_year * jahre
        results.append(
            {
                "label": label,
                "lager": lager_id,
                "wacc_nuclear": CAMP_RANGES["wacc_nuclear"][lager_id],
                "nep_realization_rate": CAMP_RANGES["nep_realization_rate"][lager_id],
                "ee_gas_ct_kwh": round(ee, 2),
                "kkw_gas_ct_kwh": round(kkw, 2),
                "diff_ct_kwh": round(diff, 2),
                "schaden_mrd_eur": round(schaden_mrd, 0),
                "guenstigerer_pfad": "EE-GAS" if diff > 0 else "KKW-GAS",
            }
        )
    return results
