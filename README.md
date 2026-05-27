# enesys — Forward-cost analysis of Germany's energy transition

> **⚠️ Pre-1.0 development release.** API surface may still change
> before 1.0. Code and analyses are functional and tested. Pin to a
> specific Git tag if you rely on reproducible results. See
> [`CHANGELOG.md`](CHANGELOG.md) for the current cut. Issues and PRs
> welcome.

> Six paths, three decades, one open model. Every assumption
> documented, every source cited, every claim reproducible in five
> minutes.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berndhardung/enesys/blob/main/notebooks/01_quickstart.ipynb)

**The German energy debate argues about the wrong axis.** Most
discussions ask: renewable or nuclear? But the actual decision is
two-dimensional — base-load × backup. This repository contains the
quantitative model that walks through both axes for six realistic
paths from 2026 to 2055, then asks: which path wins under *any*
plausible set of assumptions?

| Want to … | Then look at … |
|-----------|----------------|
| **Try it without installing anything** | [Open the Quickstart notebook in Colab](https://colab.research.google.com/github/berndhardung/enesys/blob/main/notebooks/01_quickstart.ipynb) — 5 minutes, no setup |
| **Use the model programmatically** | [Quickstart §](#use-the-model-programmatically) — six lines of Python |
| **Audit the assumptions** | [`docs/SOURCES.md`](docs/SOURCES.md) — every default with primary-source tag |
| **See the formulas** | [`docs/FORMULAS.md`](docs/FORMULAS.md) — derivation and worked examples |
| **Challenge a finding** | Open an issue with model parameters and your counter-evidence |

## What this is

A Python model that compares **six pathways** for the German energy transition,
arranged along two independent axes (base-load × backup):

|              | **Backup: Gas**  | **Backup: H₂** |
|--------------|------------------|----------------|
| **Status quo / inaction**   | WEITER-SO    | (n/a)          |
| **Existing-fleet emphasis** | BESTAND      | (n/a)          |
| **EE-only**      | EE-GAS       | EE-H2          |
| **EE + KKW**     | KKW-GAS      | KKW-H2         |

The model has explicit treatment of:

- **Forward costs** (no sunk costs in investment decisions)
- **Time-path dynamics** (2026 → 2055, with realistic build-times)
- **Asymmetric uncertainty** (different assumption-sets for renewables vs.
  nuclear advocates)
- **Sector coupling efficiency** (heat pumps and EVs as 2:1 primary energy
  multipliers)
- **Grid stability requirements** (inertia, black-start, frequency control)
- **Winter dunkelflaute stress test** (10-day cold dark calm periods)

The model traces every default parameter to a primary source (see
[`docs/SOURCES.md`](docs/SOURCES.md)) and exposes every
formula transparently (see [`docs/FORMULAS.md`](docs/FORMULAS.md)).

## Why another OSS energy model?

The German energy-modelling landscape is rich — PyPSA-Eur, REMIND,
MESSAGE, oemof, AnyMOD, calliope, Agora and Fraunhofer studies, IEA
scenarios. This model is *not* a replacement for any of them; it has a
much narrower lens, focused on one question: **which path is robustly
cheapest as a forward decision, across the assumption substrates the
opposing camps would actually defend?**

### What this is not

- **Not a high-resolution dispatch model.** No hourly grid simulation,
  no unit-commitment, no network flows. For that:
  [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur),
  [oemof](https://oemof.org/), [calliope](https://www.callio.pe/).
- **Not an integrated assessment / macro-economy model.** No CGE
  feedback loops, no inter-sectoral capital allocation, no global
  emissions pathways. For that:
  [REMIND](https://www.pik-potsdam.de/en/institute/departments/transformation-pathways/models/remind),
  [MESSAGE](https://iiasa.ac.at/models-tools-data/message),
  [IEA ETP](https://www.iea.org/reports/energy-technology-perspectives-2024).
- **Not a policy roadmap or a strategy paper.** For sector-coupling
  pathways with policy detail:
  [Agora Energiewende](https://www.agora-energiewende.org/),
  [Fraunhofer ISE studies](https://www.ise.fraunhofer.de/en/publications/studies.html),
  [BMBF-Ariadne project](https://ariadneprojekt.de/).
- **Not a forecast.** The model answers "given these assumptions, what
  follows?" — not "what will Germany do?".

If your question fits one of the categories above, those tools are the
right starting point. The four properties below describe what this
model is doing inside its narrower lens.

## What makes this distinctive

Four properties — each verifiable in the code, not just claims.

1. **Forward-cost framing as a structural choice.** Sunk costs (KKW
   decommissioning fund, EEG-Altlast, Endlager — nuclear-waste —
   fund) sit in dedicated context fields and are *deliberately
   excluded* from the LCOE arithmetic. Most policy discussions
   silently mix the two; this model makes the distinction visible in
   the code itself
   ([`src/enesys/core/path_model.py`](src/enesys/core/path_model.py)
   `compute_path` plus
   [`src/enesys/core/path_inputs.py`](src/enesys/core/path_inputs.py)).

2. **Two-dimensional path space (base-load × backup, six paths).**
   Much of the public debate compresses the decision into one axis
   (renewables vs. nuclear). The model treats base-load source and
   backup vector as *independent* axes — that's why KKW-GAS and KKW-H₂
   exist as separate paths, and why the symmetric EE pair makes sense.
   The "renewable or nuclear?" framing turns out to be the wrong
   question once both axes are explicit.

3. **Camp-symmetric methodology — no built-in bias in the point estimate.**
   Every contested parameter (nuclear CAPEX, electrolysis cost, gas
   price, WACC, …) carries an EE-optimistic and an atom-optimistic
   alternative alongside the neutral default, plus a bestand-optimistic
   variant. In the point estimate **each camp gets its preferred path**:
   atom_optimistic → KKW-GAS as cheapest, the three other camps → EE-GAS.
   The recommendation (EE-GAS) does *not* follow from "EE wins everywhere"
   — it follows from **min-max-regret across the four camps**: picking
   KKW-policy in an EE-friendly world loses roughly twice as much as
   picking EE-policy in a KKW-friendly world (the asymmetry comes from
   nuclear's IBN landing after 2045 in three of four camps). See
   `CAMP_RANGES` in [`src/enesys/core/camp_ranges.py`](src/enesys/core/camp_ranges.py).

4. **Cross-validation against an external assumption substrate.** The
   `param_sets/` module hosts independent assumption sets from outside
   institutions — currently the PyPSA-Technology-Data defaults (the
   input data feeding PyPSA-DE / BMBF-Ariadne). The convergence test
   [`tests/consistency/test_ariadne_convergence.py`](tests/consistency/test_ariadne_convergence.py)
   asserts that the structural eckpunkte of the path ranking hold
   under that substrate swap. See
   [`docs/PARAM_SETS.md`](docs/PARAM_SETS.md) for the mechanism and
   contribution guide for further sets.

## The six paths

| Model | Strategy | Key feature |
|---|---|---|
| **WEITER-SO** | Status quo continuation | Baseline: political inaction, Kohle until 2038, Erdgas wachsend |
| **BESTAND** | Existing-fleet emphasis, dampened EE-Zubau | Shows what »keep what we have« actually costs |
| **EE-GAS** | Renewables + Storage + Gas-Backup with green ramp-up | Pragmatic optimum, robust to H₂ uncertainty |
| **EE-H2** | Renewables + Storage + H₂-Backup | Pure energy transition, H₂ wager |
| **KKW-GAS** | Renewables + Nuclear (post-2042) + Bridge-Gas | Nuclear renaissance with realistic build-times |
| **KKW-H2** | Renewables + Nuclear + H₂-Backup | Reveals structural independence of backup choice |

Headline finding under default assumptions (30-year average 2026-2055,
`neutral_default` camp):

| Path | Cost (LCOE) | Cumulative CO₂ | vs WEITER-SO |
|---|---|---|---|
| **EE-GAS** | **16.56 ct/kWh** | 1,825 Mt | saves 95 Mt |
| WEITER-SO | 16.92 ct/kWh | 1,920 Mt | (baseline) |
| EE-H2 | 17.17 ct/kWh | **1,610 Mt** | saves 310 Mt |
| BESTAND | 17.30 ct/kWh | 2,272 Mt | adds 352 Mt |
| KKW-GAS | 17.31 ct/kWh | 2,194 Mt | adds 274 Mt |
| KKW-H2 | 17.63 ct/kWh | 1,952 Mt | adds 32 Mt |

**EE-GAS is the cost optimum in the neutral camp; EE-H2 has the lowest
cumulative CO₂.** The gap from EE-GAS to WEITER-SO is just 0.36 ct/kWh
— supporting the "humility thesis" that **political inaction is
economically nearly as expensive as the most pragmatic active path**,
only with higher emissions. KKW-paths cost more without a clear CO₂
payoff in return. BESTAND — an "existing-fleet" emphasis with dampened
EE expansion — is the worst on the CO₂ axis. **Other camps yield other
top paths** (see distinctive property 3 above); the recommendation
comes from min-max-regret across camps, not from this single table.

Numbers reproducible with `python -c "from enesys import compute_path; ..."`
(see Quickstart below).

## Quickstart

**Zero-setup path — Google Colab.** Open
[`notebooks/01_quickstart.ipynb`](notebooks/01_quickstart.ipynb) in
[Colab](https://colab.research.google.com/github/berndhardung/enesys/blob/main/notebooks/01_quickstart.ipynb)
and run all cells. The first cell `%pip install`s enesys from this repo;
the rest walks through the forward-cost snapshot, the four-camp lager-
symmetry, the 30-year trajectory, the tornado sensitivity, and a small
Monte-Carlo — five minutes end-to-end.

**Local install:**

```bash
git clone https://github.com/berndhardung/enesys.git
cd enesys
pip install -e ".[charts]"
```

**Easiest setup — VS Code + Docker (no Python on the host needed):** after `git clone` open the folder in VS Code (`code .`) and accept the "Reopen in Container" prompt. The included `.devcontainer/` provisions Python 3.12, uv, all dependencies and editor extensions; the venv is built during the container build so the environment is ready as soon as VS Code attaches.

**Bare-metal setup with uv:** install [uv](https://github.com/astral-sh/uv) once, then `make venv` builds the full dev environment deterministically from `uv.lock` in a few seconds.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # one-time, ~5 s
make venv                                          # ~5 s, uses uv.lock
```

**Or in GitHub Codespaces:** click *Code → Codespaces → Create codespace*. Same `.devcontainer/` setup, runs in the cloud.

### Use the model programmatically

```python
from enesys import compute_path, baseline_all_paths

# Forward-cost trajectory for the EE-GAS path, 2030-2055, in the
# neutral_default camp:
results = compute_path("ee_gas", years=[2030, 2040, 2050, 2055], camp="neutral_default")
for r in results:
    print(f"{r.year}: LCOE = {r.lcoe_ct_kwh:.2f} ct/kWh, CO2 = {r.co2_mt:.1f} Mt")

# Compare all six paths at one year:
prices = baseline_all_paths(year=2045, camp="neutral_default")
for path, lcoe in sorted(prices.items(), key=lambda x: x[1]):
    print(f"  {path:<10} {lcoe:6.2f} ct/kWh")
```

### Run the test suite

```bash
pytest tests/ -v
```

Covers path-model tests (Demand, Forward LCOE, 30-year integration,
six-path invariants, winter-stress test), sensitivity tests (tornado,
Monte-Carlo, camp presets), source-traceability tests, and convergence
tests against the external parameter substrate
(PyPSA-Technology-Data).

## Package layout

```
enesys/
├── README.md, LICENSE, CHANGELOG.md, AUTHORS.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md
├── pyproject.toml, uv.lock, Makefile, VERSION
│
├── src/enesys/         Model library
│   ├── core/                         Data structures, path model, sensitivity, WACC
│   ├── extensions/                   Anhang-C, land use, consumer, winter stress
│   └── viz/                          Chart building blocks (matplotlib + plotly theme)
│
├── tests/                            pytest suite
└── docs/                             Methodology, formulas, sources, architecture
```

## Documentation map

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — five-minute orientation
- [`docs/HOWTO_RUN.md`](docs/HOWTO_RUN.md) — running locally and in Docker
- [`docs/FORMULAS.md`](docs/FORMULAS.md) — every formula with derivation and
  worked examples
- [`docs/SOURCES.md`](docs/SOURCES.md) — every default parameter with source,
  range, and camp-specific assumptions
- [`docs/VERSIONING.md`](docs/VERSIONING.md) — version scheme and how the
  version is pinned across model packages
- [`docs/methodik/modell_architektur.md`](docs/methodik/modell_architektur.md) —
  high-level architecture overview
- [`docs/methodik/`](docs/methodik/) — further methodology deep dives
  (Anhang-C bottom-up cross-check, bridge phase parameters, English
  methodology overview)

## Sources

The model is calibrated against:

- **Fraunhofer ISE** — *Stromgestehungskosten erneuerbarer Energien 2024*
  ([PDF](https://www.ise.fraunhofer.de/content/dam/ise/de/documents/publications/studies/DE2024_ISE_Studie_Stromgestehungskosten_Erneuerbare_Energien.pdf))
- **BloombergNEF** — *Energy Storage Cost Survey 2025* (10 Dec 2025);
  *LCOE Report 2026* (18 Feb 2026)
- **EWI Köln** — Hydrogen storage requirements
- **Cour des Comptes (FR)** — Flamanville EPR audit (17 years, €23.7 bn)
- **EDF** — Hinkley Point C status reports
- **KENFO** — *Geschäftsbericht 2024*
- **KernD** — *Bewertung der Fraunhofer ISE Studie* (pro-nuclear critique)
- **Modo Energy** — *Inertia in Europe* (Nov 2025)
- **DE-TSOs** — Joint inertia procurement (22 Jan 2026)

Full traceability is in [`docs/SOURCES.md`](docs/SOURCES.md).

## Reproducibility commitments

- **Pinned dependencies** in `uv.lock` (76 packages with hashes)
- **Deterministic Monte-Carlo** with fixed seeds in tests
- **Python 3.10+** with explicit version constraints
- **CI on every commit** via GitHub Actions
- **All defaults annotated** with `[SRC: ...]` tags pointing to
  `docs/SOURCES.md`

If you can't reproduce a result, please open an issue with the parameter
set you used and the command you ran.

## Citation

If you use this model in academic or policy work, please cite:

```bibtex
@software{enesys_2026,
  author       = {Hardung, Bernd},
  title        = {enesys: A transparent cost-robustness analysis
                  for the German energy transition},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/berndhardung/enesys},
  note         = {See CITATION.cff for current version}
}
```

## Contributing

This project welcomes:

- **Bug reports** for incorrect formulas, source mismatches, or test failures
- **Source updates** when newer studies (BNEF, ISE, BNetzA) are published
- **Translations** of the model into other regulatory contexts (FR, PL, etc.)
- **Critical reviews** of methodology — issues that say "your assumption X
  is wrong because Y" are especially welcome

What this project does **not** want:

- Pull requests that hardcode advocacy positions (pro/anti renewables, pro/anti
  nuclear) — the model must remain neutral and parameter-driven
- Deletion of "inconvenient" parameters or sources

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Source code (`src/`, `tests/`, top-level configuration) is licensed
under the **MIT License** — see [`LICENSE`](LICENSE).

Methodology documentation under `docs/` is distributed under MIT alongside
the source code; a separate license tier (CC0 or CC-BY-4.0) may be applied
at a later date.

