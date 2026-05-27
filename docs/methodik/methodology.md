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

This is the substantive content of the recommendation. The min-max-regret
implementation lives in
[`core/regret_decision_tree.py`](../../src/enesys/core/regret_decision_tree.py).

## 4. Cross-validation against external assumption sets

Adversarial assumption substrates from outside this project sit in
[`core/param_sets/`](../../src/enesys/core/param_sets/):

- `ariadne_pypsa` — PyPSA-Technology-Data defaults (the substrate feeding
  PyPSA-DE / BMBF-Ariadne; EE-leaning).

The convergence test in
[`tests/consistency/test_ariadne_convergence.py`](../../tests/consistency/test_ariadne_convergence.py)
asserts that the structural eckpunkte of the result (EE-GAS in Top-2,
KKW-H2 most expensive) hold under the substrate swap. It does *not*
assert identical rankings — dense mid-field paths (BESTAND, EE-H2,
WEITER-SO) sit within 0.4 ct/kWh of each other and trade places
depending on substrate.

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
