# How to Run

A practical guide to running the model. For a deeper understanding, see
the README and METHODOLOGY documents.

## Prerequisites

- Python 3.10 or newer
- Git
- Optional: a virtual environment tool (`venv`, `conda`, `uv`, etc.)

## Installation

### Standard install (recommended)

```bash
git clone https://github.com/berndhardung/enesys.git
cd enesys

# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Install package in editable mode with all extras (UI, charts, dev)
pip install -e ".[all]"
```

For development without the Streamlit UI:

```bash
pip install -e ".[charts,dev]"
```

For the minimal model-only install (no charts, no UI):

```bash
pip install -e .
```

## What you can do

### 1. Run the test suite

```bash
pytest tests/ -v
```

Covers:
- path-model tests (Demand, Forward LCOE, 30-year integration, six-path invariants)
- sensitivity tests (tornado, Monte-Carlo, camp presets)
- winter-stress test, sector coupling
- source-traceability tests
- convergence tests against the external parameter substrate (PyPSA-Technology-Data)

### 2. Run the source-traceability validator standalone

```bash
python -m enesys.core.source_trace check
python -m enesys.core.source_trace list-tags
python -m enesys.core.source_trace orphans
```

The `check` command is what runs in CI. `list-tags` shows all defined sources.
`orphans` shows tags defined in SOURCES.md but unused in code.

### 3. Render the standalone charts

```bash
python examples/generate_chart_nuclear_build_time_empirics.py
python examples/generate_chart_mix_rampup.py --camp neutral_default
python examples/generate_chart_tornado_sensitivity.py
python examples/generate_chart_monte_carlo.py
python examples/generate_chart_stress_rampup.py
```

PNGs land in `examples/`. Each script is a thin wrapper around the
`render_*` functions in `enesys.viz.charts`. Override the camp with
`--camp ee_optimistic` etc.; produce SVG for the web with
`--variant web`.

### 4. Use the model programmatically

Open a Python REPL or notebook:

```python
from enesys import compute_path, rolling_all_paths

# Forward-cost trajectory for the EE-GAS path, 2030-2055, in the
# neutral_default camp:
results = compute_path("ee_gas", years=[2030, 2040, 2050, 2055], camp="neutral_default")
for r in results:
    print(f"{r.year}: LCOE = {r.lcoe_ct_kwh:.2f} ct/kWh, CO2 = {r.co2_mt:.1f} Mt")

# Compare all six paths via rolling 30-year LCOE 2026-2055 (canonical):
prices = rolling_all_paths(year=2026, camp="neutral_default")
for path, lcoe in sorted(prices.items(), key=lambda x: x[1]):
    print(f"  {path:<10} {lcoe:6.2f} ct/kWh")
```

For all available parameters and functions:

```python
import enesys
help(enesys)
```

## Customizing assumptions

Want to test how the conclusions change with different assumptions?
You have three options:

### Option 1: Use a built-in camp preset

```python
from enesys import rolling_all_paths

# Compute rolling 30-year LCOE 2026-2055 for each of the five canonical camps:
for camp in (
    "neutral_default",
    "ee_optimistic",
    "atom_optimistic",
    "bestand_optimistic",
    "weiterso_optimistic",
):
    prices = rolling_all_paths(year=2026, camp=camp)
    print(camp, prices)
```

Available camps: `neutral_default`, `ee_optimistic`, `atom_optimistic`,
`bestand_optimistic`, `weiterso_optimistic`.

### Option 2: Override individual parameters

```python
from enesys import compute_path

# Test what happens if PV CAPEX falls faster than expected
results = compute_path(
    "ee_gas",
    years=[2030, 2040, 2050],
    camp="neutral_default",
    param_overrides={"pv.capex_eur_kw": 400},  # override default
)
```

Override keys follow the pattern `<tech_id>.<field>`. The most common
`tech_id` values:

| Technology | `tech_id` | Example field |
|---|---|---|
| Solar PV | `pv` | `capex_eur_kw`, `wacc_pct` |
| Wind onshore | `wind_onshore` | `capex_eur_kw`, `vlh_normal` |
| Wind offshore | `wind_offshore` | `capex_eur_kw`, `vlh_normal` |
| Battery storage | `battery` | `capex_eur_kw`, `lifetime_years` |
| Existing nuclear | `kkw_bestand` | `capex_eur_kw`, `opex_eur_kw_year` |
| New nuclear (EPR) | `kkw_neubau_epr` | `capex_eur_kw`, `wacc_pct` |
| New nuclear (SMR) | `kkw_neubau_smr` | `capex_eur_kw`, `vlh_normal` |
| Existing gas | `gas_existing` | `opex_eur_kw_year` |
| H₂-ready gas | `gas_h2ready` | `capex_eur_kw` |

The full list of `tech_id` values is in
`src/enesys/core/inventories/tech_inventory.py`.

### Option 3: Run Monte Carlo with custom uncertainty bands

```python
from enesys import monte_carlo_all_paths

# Default uses CAMP_RANGES (rolling 2026-2055 with n_year_samples=6
# trapezoidal approximation); result includes per-path price arrays.
# Pass n_year_samples=30 for full resolution, n_runs=3000 for the
# headline book reproduction.
results = monte_carlo_all_paths(year=2026, n_runs=10_000, seed=42)
```

The full sensitivity API is exposed at the top level of `enesys`:
`rolling_all_paths`, `baseline_all_paths`, `tornado_path_analysis`,
`monte_carlo_all_paths`.
Use these — `enesys.core.*` submodules are internal and not part of the
stable API.

## Reporting issues

If something doesn't work as expected:

1. Check that the test suite passes: `pytest tests/ -v`
2. Verify your numpy version: `pip show numpy`
3. Re-read the relevant chapter in `docs/FORMULAS.md`
4. Open an issue on GitHub with the bug-report template

## Reproducibility commitment

If you can run the full test suite (`pytest tests/`) and it passes on a
fresh install, your environment is correctly set up. Any analytical
results from the model are then **bit-exact reproducible** because
Monte Carlo uses fixed seeds.

If a result is not reproducible, **that is a bug** — please report it.
