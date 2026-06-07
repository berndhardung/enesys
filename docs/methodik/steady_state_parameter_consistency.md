# Steady-state model — parameter consistency with the main model

This table documents each parameter in the steady-state model (covers
the period 2055–2085) against the corresponding main-model value
(`path_model.py ForwardCostParams`). It is the foundation for the
claim "the steady-state model is methodologically consistent with the
main model".

## Convention for source tags

- `[SRC: TAG]` — external source from `docs/SOURCES.md`
- `[CALIBRATED: ]` — derived from sources, with rationale
- `[ASSUMPTION: ]` — estimate without a hard source, with rationale
- `[MODEL: ]` — model-internal constant, e.g. from `ForwardCostParams`

## CAPEX (€/kW)

CAPEX values fall markedly from 2026 to 2050 — that is the central
learning-curve assumption from C.2.

| Parameter | Main model 2026 | Steady state 2055 | Factor | Source |
|---|---|---|---|---|
| PV | 700 | **350** | ÷2 | BNEF-NEO-2024 Net-Zero median |
| Wind onshore | 1,400 | **1,100** | ÷1.3 | IEA-WEO-2024 |
| Wind offshore | 3,000 | **1,800** | ÷1.7 | IEA-WEO-2024 |
| Nuclear | 11,000 | **6,000** | ÷1.8 | C.2 mid-value SMR-optim/EPR-pessim |
| Battery €/kWh | 110 | **50** | ÷2.2 | BNEF-2025-LIB learning rate |
| Biomass | — | 3,000 | — | mature, similar to today |

## OPEX (€/kW/yr) — absolute, not percentage

OPEX values are structural to the technology and only decline mildly
relative to 2026 (maintenance learning curves). No drastic reduction.

| Parameter | Main model 2026 | Steady state 2055 | Diff | Rationale |
|---|---|---|---|---|
| PV | 12 | **10** | -17 % | standardized maintenance |
| Wind onshore | 35 | **28** | -20 % | predictive maintenance |
| Wind offshore | 90 | **70** | -22 % | standardized offshore logistics |
| Nuclear | 130 | **150** | +15 % | conservative fuel-element assumption |
| Biomass | — | 180 | — | fuel costs dominate |

**Methodological convention:** OPEX is modeled as absolute €/kW/yr,
not as a percentage of CAPEX. This is the main-model convention and
matches reality: maintenance, insurance, and fuel costs do not scale
1:1 with CAPEX but are largely stable by plant size and technology.

## Lifetime (years) — structural, identical to the main model

| Parameter | Main model | Steady state | Source |
|---|---|---|---|
| PV | 30 | **30** | ISE-2024 |
| Wind | 25 | **25** | ISE-2024 |
| Nuclear | 60 | **60** | EPR design spec |
| Battery | 6,000 cycles | 15 years | equivalent at 365/yr |
| Biomass | — | 25 | assumption analogous to wind |

## Full-load hours (h/yr) — identical to the main model

| Parameter | Main model | Steady state | Source |
|---|---|---|---|
| PV | 1,050 | **1,050** | ISE-2024 DE mean |
| Wind onshore | 2,200 | **2,200** | ISE-2024 DE mean |
| Wind offshore | 4,200 | **4,200** | ISE-2024 |
| Nuclear | 6,500 | **6,500** | ISE-2024, EE-mix reality |
| Biomass | — | 4,500 | baseload assumption |

**Note on nuclear VLH:** KernD historically argues for
7,500-8,000 hours. The lower 6,500 reflect that in an 80 % EE system
in 2055, nuclear utilization is depressed by EE priority and load-
following limits — see TAB-2017 on load-following capability and
OECD-NEA-2019 on system costs.

## WACC per technology

WACC is the central control variable. The main model sets values for
2026 with risk premia. For 2055 the values are moderately reduced for
mature technologies — consistent with the learning-curve logic.

| Technology | Main model 2026 | Steady state 2055 | Diff | Rationale |
|---|---|---|---|---|
| PV | 5.0 % | **4.0 %** | -1 pp | 30 years of established industry |
| Wind | 6.0 % | **5.0 %** | -1 pp | mature permitting processes |
| Nuclear | **8.5 %** | **8.5 %** | 0 pp | build-time risk remains structural |
| Battery | 7.0 % | **5.0 %** | -2 pp | mature asset class in 2055 |

**Nuclear WACC unchanged.** A "learning-curve reduction" for nuclear
would presuppose that the industry empirically demonstrates schedule
and budget discipline; the EU references Hinkley Point C, Flamanville,
and Olkiluoto do not yet support that. The sensitivity table covers an
implicit WACC reduction via the scenario "nuclear CAPEX 4,500 €/kW" —
nuclear at 4,500 €/kW with 5 % WACC corresponds to roughly the same
LCOE as nuclear at 6,000 €/kW with 8.5 % WACC.

## Mix shares

Mix shares reflect the steady state in 2055. They are not directly
taken from the main model (which models the trajectory) but derived
from its 2050+ steady state.

| Path | PV | Wind on | Wind off | Bio | Hydro | Nuclear | Backup |
|---|---|---|---|---|---|---|---|
| EE-GAS | 43 % | 32 % | 15 % | 4 % | 3 % | — | 8 % |
| EE-H2 | 43 % | 32 % | 15 % | 4 % | 3 % | — | 8 % H₂ |
| KKW-GAS | 28 % | 21 % | 10 % | 3 % | 2 % | 30 % | 6 % |
| KKW-H2 | 28 % | 21 % | 10 % | 3 % | 2 % | 30 % | 6 % H₂ |
| WEITER-SO | 30 % | 20 % | 8 % | 5 % | 3 % | — | 30 % gas |

## Storage shares (electricity throughput via daily storage)

Methodological logic: storage demand scales with the **variable
component** in the path, not with the path family wholesale. Seasonal
storage (H₂) is not in this layer — it flows into the generation
layer via backup generation.

| Path | Share | Rationale |
|---|---|---|
| EE-GAS | 10 % | Schill-DIW-2024 for 100 % EE systems |
| EE-H2 | 12 % | daily balancing + H₂ seasonal combined |
| KKW-GAS | 7 % | 70 % variable component × scaling + nuclear-surplus buffering |
| KKW-H2 | 10 % | nuclear + H₂ seasonal |
| WEITER-SO | 3 % | little storage build-out, gas as flexibility |

The scaling 10 % × 70/92 ≈ 7.5 % reflects that in the KKW path there
is less variable EE generation (70 % instead of 92 %), but the
nuclear baseload in low-load hours (summer nights) must additionally
be buffered.

## Grid and stability

| Layer | Value | Source |
|---|---|---|
| Grid, active | 7.0 ct/kWh | BNETZA-VS-2025 (mid-range 5-8) |
| Grid, WEITER-SO | 7.5 ct/kWh | + 0.5 for less modernization |
| Stability, EE | 1.1 ct/kWh | MODO-2025 + ENTSO-E models |
| Stability, KKW | 0.4 ct/kWh | rotating masses provide inertia passively |
| Stability, WEITER-SO | 0.6 ct/kWh | between EE and KKW |

## CO₂ penalty

Calculated via `co2_pricing_ct_kwh()` from `path_model.py` —
**the same function** as the main model. CO₂ intensities of the mix
components are lifecycle values (IPCC AR6 median):

| Technology | CO₂ intensity |
|---|---|
| PV | 30 g/kWh |
| Wind | 10 g/kWh |
| Biomass | 50 g/kWh |
| Hydro | 5 g/kWh |
| Nuclear | 12 g/kWh |
| Natural gas (combustion) | 350 g/kWh |
| H₂ (green) | 0 g/kWh |

| Path | World CO₂ price | Rationale |
|---|---|---|
| Active paths (neutral) | 130 €/t | main-model default 2030+, camp-specific 100-160 (ee_opt 160 / atom_opt 150 / bestand_opt 100) |
| WEITER-SO | 100 €/t | main-model WEITER-SO-specific (ETS softening assumption) |

## Results (steady state 2055-2085, `neutral_default` camp)

30-year mean from `compute_path()`:

| Path      | LCOE 2055-2085 |
|---|---:|
| EE-GAS    | 15.54 ct |
| WEITER-SO | 15.77 ct |
| EE-H2     | 16.32 ct |
| BESTAND   | 16.92 ct |
| KKW-GAS   | 17.37 ct |
| KKW-H2    | 18.15 ct |

**EE-GAS remains the cheapest path in the default scenario**, with a
slim lead over WEITER-SO (~0.23 ct) and a clear gap to KKW-GAS
(+1.83 ct) and KKW-H2 (+2.61 ct). The steady state differs from the
2045 snapshot ordering: KKW-GAS and KKW-H2 drop to the back ranks in
the 30-year mean 2055-2085, because the heavy bridge-phase CO₂ loads
and build-time delays from the 2040s are out of the window and pure
steady-state operation amortizes.

## Camp symmetry

The EE-GAS recommendation in steady state 2055-2085 holds in the
`neutral_default`, `ee_optimistic`, and `bestand_optimistic` camps;
in the `atom_optimistic` camp it tips in favor of KKW-GAS (higher
nuclear realization rate, planned build time used in full). That is
the structural camp asymmetry: every camp delivers its preferred path
in the point estimate. The model's recommendation follows from
min-max regret across the four camps, not from a cross-camp point
estimate (see README, methodology.md).

## Drift safeguard

Consistency between the main model and the steady-state model is
secured by tests in `tests/consistency/`; on parameter changes in the
main model these tests fire and force an explicit update of the
steady-state model.
