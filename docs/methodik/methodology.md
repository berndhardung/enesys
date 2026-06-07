# Methodology

This document explains the three structural choices that distinguish this
model from a generic LCOE calculator. It does not repeat the formulas
(see [FORMULAS.md](../FORMULAS.md)) or the parameter sources (see
[SOURCES.md](../SOURCES.md)). It explains *why* those formulas are framed
the way they are.

## 1. Forward costs only

Past investments are sunk. EEG payments already disbursed, KKW
decommissioning funds set aside, transmission lines already built — none
of these enter the LCOE arithmetic of new investment decisions. The
distinction is implemented in
[`core/path_model.py`](../../src/enesys/core/path_model.py) (`compute_path`)
and
[`core/path_inputs.py`](../../src/enesys/core/path_inputs.py): sunk-cost
context fields are addressed separately and excluded from the path
comparison by construction.

Why this matters: the public debate routinely mixes the two ("renewables
cost us 270 bn €, so they're expensive"). Mixing sunk and forward costs
turns any path comparison into an accounting choice rather than a physical
one.

## 2. Time-paths, not steady states

The build time of a new dispatchable plant is not a footnote — it
determines which paths can deliver climate neutrality by 2045. The
empirical FOAK build time for Western nuclear (Olkiluoto-3, Flamanville-3,
Hinkley Point C, Vogtle-3/4) is 13–17 years from groundbreaking, plus
3–8 years from political decision to groundbreaking (the *FID* lead
time — Final Investment Decision: the moment the developer commits
capital and construction begins). A 2026 political commitment therefore
yields nuclear *IBN* (Inbetriebnahme — commissioning, the moment the
plant first delivers power to the grid) somewhere in 2036–2050,
depending on realization rate.

Consequence: any comparison of "steady-state EE-GAS vs. steady-state
KKW-GAS" hides the bridge phase. The model integrates over 2026–2055 and
reports the 30-year average — that is the honest comparison.

See [`viz/charts/build_time.py`](../../src/enesys/viz/charts/build_time.py)
for the empirical data underlying this claim.

## 3. Camp-symmetric assumption substrates

Every contested parameter (nuclear CAPEX, electrolysis cost, gas price,
WACC, NEP grid-realization rate — NEP = *Netzentwicklungsplan*,
Germany's official grid expansion plan) carries four alternative
defaults — one per camp:

| Camp | Parameter tilt |
|---|---|
| `neutral_default` | mid-range empirical defaults |
| `ee_optimistic` | renewable-friendly (low PV/wind CAPEX, fast learning, high NEP-realization) |
| `atom_optimistic` | nuclear-friendly (low nuclear CAPEX, 100% realization, low CO₂ price) |
| `bestand_optimistic` | existing-fleet-friendly (slow EE expansion, high carbon price exemption) |

See [`core/camp_ranges.py`](../../src/enesys/core/camp_ranges.py) for the
parameter table.

**The methodological pointe.** Under the four camp-defaults the point-
estimate winner across the full six-path set shifts substantially —
Rolling-LCOE 2026-2055: `neutral_default` → EE-GAS (16,79 ct/kWh),
`ee_optimistic` → EE-GAS (15,55), `atom_optimistic` → KKW-GAS (17,93),
`bestand_optimistic` → WEITER-SO (17,46). The active four-path
competition (EE-GAS, EE-H2, KKW-GAS, KKW-H2) reorders across camps such
that no path holds the point-estimate slot across all four. The model
has no built-in camp preference. That is exactly why the point estimate
cannot decide the question.

The recommendation (EE-GAS) follows from **min-max-regret across the
four camps**, not from a point-estimate dominance: picking KKW-policy
in an EE-optimistic world incurs roughly twice the cost penalty as
picking EE-policy in a nuclear-optimistic world (EE-Lager-Reue ~775 Mrd
> KKW-Lager-Reue ~368 Mrd → EE-GAS minimax-regret-optimal). The
asymmetry comes from two structural facts, not from biased parameters:

1. **Spread asymmetry.** EE-optimistic camps widen the EE↔KKW cost gap
   more than nuclear-optimistic camps do — because nuclear CAPEX has a
   smaller plausible range than EE learning rates compounded over 20
   years.
2. **Timing asymmetry.** Nuclear IBN falls after 2045 in three of four
   camps. Only the `atom_optimistic` camp delivers KKW by 2036 — in the
   other three worlds, nuclear policy is structurally too late for the
   2045 climate target, while EE-policy delivers in all four worlds.
   Note that *for the regret outcome* timing is not the binding factor
   — section 4b quantifies how the regret picture moves when the
   nuclear start year is varied independently of the camp realization
   rate; the dominant lever is spread asymmetry (reason 1), not
   timing.

This is the substantive content of the recommendation. The min-max-regret
implementation lives in
[`core/regret_decision_tree.py`](../../src/enesys/core/regret_decision_tree.py).

## 4. Parameter-substrate robustness check

The model's defaults sit inside the enesys-curated `CAMP_RANGES` substrate
(four camps, neutral mid-point). A separate question — does the
conclusion survive if you swap the *entire substrate* for one curated
elsewhere? — is answered by an external parameter substrate plugged
through the same `compute_path` pipeline.

Adversarial substrates from outside this project sit in
[`core/param_sets/`](../../src/enesys/core/param_sets/):

- `ariadne_pypsa` — PyPSA-Technology-Data defaults (the substrate feeding
  PyPSA-DE / BMBF-Ariadne; EE-leaning).

The robustness-check test in
[`tests/consistency/test_ariadne_convergence.py`](../../tests/consistency/test_ariadne_convergence.py)
asserts that the *structural cornerstones* of the result (EE-GAS in
Top-2, KKW-H2 most expensive) hold under the substrate swap. It does *not*
assert identical rankings — dense mid-field paths (BESTAND, EE-H2,
WEITER-SO) sit within 0.4 ct/kWh of each other and trade places
depending on substrate. The naming convention "parameter-substrate
robustness check" rather than "cross-validation" is deliberate:
cross-validation in statistics has a specific train/test meaning that
does not apply here — this test substitutes the entire assumption
substrate, not held-out data.

## 4a. What is structural and what is within parameter noise

Not every claim the model produces has the same epistemic weight. The
Monte-Carlo machinery (`monte_carlo_all_paths`, n = 2,000 over the
camp ranges) makes the distinction explicit:

**Structural — survives parameter noise:**

- **CO₂ separation between active and inactive paths.** Active paths
  (EE-GAS, EE-H2, KKW-GAS, KKW-H2) save ~1,500-2,200 Mt cumulative CO₂
  vs. WEITER-SO/BESTAND over 2026-2055. The separation does not depend
  on cost parameters — it follows from whether heating and mobility
  are electrified or stay fossil.
- **Cost ordering inside the active-path set.** EE-GAS beats EE-H2 in
  ≥ 97 % of MC runs, and both KKW paths in 100 %. Nuclear paths sit at
  the bottom of the cost distribution with certainty.
- **Regret asymmetry.** Picking nuclear policy in an EE-friendly world
  loses roughly twice as much as the inverse — the structural
  asymmetry of section 3.

**Within parameter noise — read as a tied cluster, not a ranking:**

- **Cost ordering between WEITER-SO, EE-GAS, BESTAND and EE-H2.** The
  deterministic 6-path cost spread is 1.0 ct/kWh; the MC P5-P95 spread
  inside one path is 1.7-3.6 ct/kWh. The deterministic point estimate
  for the cheapest path is unstable across reasonable parameter draws.

This separation is honored throughout the documentation: structural
claims are stated as findings; cost-rank claims inside the noise
cluster are stated as deterministic baselines with the MC distribution
visible alongside.

## 4b. Robustness check: nuclear start year independent of camp realization rate

The camp-specific nuclear start years (`atom_optimistic` 2036,
`neutral_default` 2046, `bestand_optimistic` 2047,
`ee_optimistic` 2050) are derived from `KKW_EPR_APPROVAL_YEAR = 2029`
plus sqrt-stretching of the build time by the camp's nuclear
realization rate. Because the realization rate is camp-dependent, the
start year is too — a natural follow-up question is therefore: how
does the minimax-regret outcome shift if the start year is varied
*independently* of the realization rate?

`nuclear_start_year_regret_analysis` answers that question. It calls
`override_kkw_epr_startjahr(X)` so that *every* camp returns the same
candidate start year X, then computes the full Savage regret matrix
for each X. Result for X ∈ {2028, …, 2055}:

| Start year X (all camps) | EE-GAS max-regret | KKW-GAS max-regret | Minimax winner |
|---:|---:|---:|---|
| 2028 | 1.71 ct/kWh | 3.01 ct/kWh | EE-GAS |
| 2036 | 1.71 ct/kWh | 2.98 ct/kWh | EE-GAS |
| 2044 | 1.71 ct/kWh | 2.99 ct/kWh | EE-GAS |
| 2052 | 1.71 ct/kWh | 3.02 ct/kWh | EE-GAS |

The minimax winner is EE-GAS at every candidate year in the search
range 2020-2055; `kkw_regret_crossover_year()` returns `None`. The
binding term for KKW-policy max-regret is the cost gap in the
`ee_optimistic` world, where KKW-GAS sits ~3 ct/kWh above EE-GAS
regardless of when KKW first delivers. The KKW start year matters by
~0.05 ct/kWh across the 24-year window — two orders of magnitude
smaller than the structural cost gap it would need to close.

**What this means.** The recommendation does not rest on a hardcoded
"KKW arrives late" assumption. Even with KKW arriving in 2028
(physically infeasible under the build-time evidence — see
[`viz/charts/build_time.py`](../../src/enesys/viz/charts/build_time.py)),
KKW-policy stays at ~1.3 ct/kWh higher minimax-regret than EE-GAS.
The binding lever for shifting the regret outcome is KKW LCOE in the
`ee_optimistic` world, not KKW timing.

Reproduce in code:

```python
from enesys import nuclear_start_year_regret_analysis, kkw_regret_crossover_year

points = nuclear_start_year_regret_analysis(range(2028, 2056, 4))
for p in points:
    print(p.nuclear_start_year, p.minimax_winner.value,
          p.max_regret_per_policy)

crossover = kkw_regret_crossover_year((2020, 2055))
print("First start year where KKW-policy becomes regret-optimal:", crossover)
```

## 4c. External-output comparison: enesys vs Ariadne / Fraunhofer ISE

The previous section answers the *substrate* question (does the
result survive Ariadne's input parameters?). A separate question is
the *output* question: how do enesys's per-tech and system numbers
compare to published numbers from the same model family?

**Apples-to-oranges caveat first.** Ariadne and Fraunhofer ISE
publish two kinds of numbers that look comparable but are not:

- *Per-technology LCOE* (e.g. PV 53 EUR/MWh in 2045). Comparable to
  enesys per-tech LCOE.
- *Wholesale equilibrium price* (e.g. "stabilises long-term at
  70–80 EUR/MWh"). This is the merit-order clearing price averaged
  over all hours; it is *not* the cost of supply. enesys does not
  natively produce this number — `compute_path` returns a cost-of-
  supply LCOE that includes grid, stability and CO₂ penalty on top of
  generation. Comparing the 16.80 ct/kWh enesys-LCOE to Ariadne's
  7–8 ct/kWh wholesale would mix two different objects.

What can be compared honestly:

### Per-technology LCOE 2045

| Technology | enesys default 2045 | Ariadne / ISE 2045 |
|---|---:|---:|
| PV utility | 6.0 ct/kWh | 5.3 ct/kWh |
| Wind onshore | 6.5 ct/kWh | 5.8 ct/kWh |
| Wind offshore | 9.0 ct/kWh | 5.9–6.6 ct/kWh |
| H₂ backup (peaker) | 32 ct/kWh | ~35 ct/kWh |
| Gas CCGT (generation only) | 6.8 ct/kWh | n/a |

enesys per-tech LCOEs sit within ~1 ct/kWh of the Ariadne / ISE 2024
values for PV, onshore wind, and H₂ backup. enesys is conservatively
higher on offshore wind (~2–3 ct above the lower end of Ariadne's
range) — a deliberate choice in `neutral_default` to absorb
North-Sea grid-connection-cost uncertainty.

Ariadne 2025 wholesale-price source: "Großhandel stabilisiert sich
langfristig bei 70–80 EUR/MWh" — Ariadne Szenarienreport 2025
([`ariadneprojekt.de/publikation/report-szenarien-zur-klimaneutralitat-2045/`](https://ariadneprojekt.de/publikation/report-szenarien-zur-klimaneutralitat-2045/)).
Fraunhofer ISE per-tech LCOE source: *Stromgestehungskosten
erneuerbare Energien* 2024 update.

### System-level cross-check via substrate swap

Substituting the Ariadne/PyPSA-Tech-Data substrate into enesys's
architecture (`param_set="ariadne_pypsa"`) yields:

| Path | enesys-native 2045 | enesys + ariadne_pypsa 2045 | Δ |
|---|---:|---:|---:|
| EE-GAS | 16.80 ct/kWh | 15.58 ct/kWh | −1.22 |
| EE-H2 | 17.51 ct/kWh | 16.29 ct/kWh | −1.22 |
| KKW-GAS | 17.36 ct/kWh | 16.15 ct/kWh | −1.21 |
| KKW-H2 | 18.19 ct/kWh | 16.98 ct/kWh | −1.21 |
| WEITER-SO | 16.70 ct/kWh | 15.41 ct/kWh | −1.29 |
| BESTAND | 17.21 ct/kWh | 16.10 ct/kWh | −1.11 |

The substrate swap shifts every path's LCOE down by ~1.1–1.3 ct/kWh
*uniformly*; path ordering is preserved. The Ariadne substrate is
quietly more EE-friendly on PV / onshore wind learning curves, and
its single 5.36 % real WACC (vs enesys's tech-differentiated WACCs)
also nudges nuclear and EE in the same direction. The shift is in
the expected direction and of the expected magnitude.

### What this does and does not establish

- ✓ enesys's per-tech defaults agree with Ariadne / ISE within ~1
  ct/kWh on the four main RE/H₂ technologies.
- ✓ The structural cost ordering (EE-GAS cheapest, KKW-H2 most
  expensive among active paths) survives a full substrate swap to
  Ariadne inputs.
- ✗ A direct enesys-LCOE-to-Ariadne-system-LCOE comparison is *not*
  possible: Ariadne publishes wholesale equilibrium prices, per-tech
  LCOEs, and system investment totals — none of which is the same
  object as enesys's cost-of-supply LCOE.

Reproduce:

```python
from enesys import compute_path
native = compute_path("ee_gas", [2045], camp="neutral_default")[0]
ariadne = compute_path("ee_gas", [2045], camp="neutral_default",
                       param_set="ariadne_pypsa")[0]
print(f"native   {native.lcoe_ct_kwh:.2f} ct/kWh")
print(f"ariadne  {ariadne.lcoe_ct_kwh:.2f} ct/kWh")
print(f"Δ        {ariadne.lcoe_ct_kwh - native.lcoe_ct_kwh:+.2f} ct/kWh")
```

## 5. What the model deliberately does not include

The model is a Forward-LCOE comparison of six explicit paths under
documented assumption substrates. It is **not**:

- a high-resolution dispatch model (no hourly grid simulation, no
  network flows),
- an integrated assessment model (no CGE feedback, no inter-sectoral
  capital allocation),
- a sector-coupling pathway planner (it uses aggregate efficiency
  multipliers, not sectoral demand modeling),
- a policy roadmap.

Decisions deliberately out of scope: geopolitical disruption risks,
unproven technologies (commercial-deployment threshold), behavioral
demand reduction, regime-change political risk. These belong in
adjacent analyses, not in this model's parameters.

For tools that cover these gaps, see the "What this is not" section in
the [README](../../README.md).

## 6. References for the methodology

The approach combines several established techniques:

- **Forward-LCOE arithmetic** — standard in BNEF and IEA reports.
- **Annuity factor for capital recovery** — textbook engineering
  economics.
- **Monte-Carlo robustness with documented distributions** — standard in
  finance, less common in energy policy.
- **Tornado sensitivity analysis** — standard in decision analysis
  (Howard, Raiffa).
- **Camp-symmetric assumption substrates** — adapted from adversarial
  robustness principles: conclusions survive only if they hold under the
  most aggressive parameter substrate the opposing position would accept.
- **Source traceability via `[SRC: TAG]` annotations** — every default
  parameter carries a tag that resolves to a primary source in
  [SOURCES.md](../SOURCES.md); enforced by
  [`test_source_traceability.py`](../../tests/core/test_source_traceability.py).
