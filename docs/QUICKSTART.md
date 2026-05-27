# Quickstart

The model is a Python library. Five minutes from `git clone` to your first
path comparison.

## Prerequisites

- Python ≥ 3.10
- `pip` or `uv`

## Install

```bash
git clone https://github.com/berndhardung/enesys.git
cd enesys
pip install -e ".[all]"
```

With `uv` (faster, deterministic from `uv.lock`):

```bash
uv sync --all-extras
```

## Compare the six paths — rolling 30-year LCOE 2026–2055

The canonical view: a rolling 30-year mean LCOE across the full
transition, which absorbs the bridge phase and the timing of nuclear
commissioning rather than picking a single year. ``rolling_all_paths``
takes the investment-start year as input — the default ``year=2026``
produces the 30-year-lifecycle reading for an investment locked in
today.

```python
from enesys import rolling_all_paths

camp = "neutral_default"
print(f"Rolling 30-year LCOE 2026–2055 ({camp}, ct/kWh):")
for path, ct in sorted(rolling_all_paths(year=2026, camp=camp).items(), key=lambda kv: kv[1]):
    print(f"  {path:<10} {ct:6.2f}")
```

EE-GAS leads the field; KKW-H2 is structurally last. The three middle
paths (EE-GAS, EE-H2, KKW-GAS) sit within roughly 3 ct/kWh of each
other — close enough that the ranking is not stably determinable in
the point estimate. The recommendation rests on min-max-regret across
the four assumption camps, not on point dominance.

Try other camps — `ee_optimistic`, `atom_optimistic`,
`bestand_optimistic`, `weiterso_optimistic` — each yields its own
preferred path. See [methodology.md §3](methodik/methodology.md) for
the camp-symmetric methodology.

## Rolling-LCOE trajectory at a later start year

The rolling-LCOE API takes any investment-start year. ``year=2045``
gives the 30-year lifecycle (2045–2074) for an investment locked in
at the climate-neutrality deadline; ``year=2055`` reads the post-
investment steady state (2055–2084).

```python
from enesys import rolling_all_paths

# 30-year mean 2045–2074 (lifecycle starting at the KSG-2045 deadline)
lcoe_2045 = rolling_all_paths(year=2045, camp="neutral_default")
for path, ct in sorted(lcoe_2045.items(), key=lambda kv: kv[1]):
    print(f"  {path:<10} {ct:6.2f} ct/kWh")
```

Single-year readings are available via ``window=1`` for any path-pair
comparison anchored to a specific calendar year — but the canonical
view is always the 30-year rolling mean, because the snapshot at a
single year mixes amortised CAPEX with current OPEX in a way that
does not map onto end-customer prices.

## Trace a single path over time

```python
from enesys import compute_path

results = compute_path(
    "ee_gas",
    years=[2030, 2040, 2050, 2055],
    camp="neutral_default",
)
for r in results:
    print(f"{r.year}: LCOE = {r.lcoe_ct_kwh:.2f} ct/kWh, CO2 = {r.co2_mt:.1f} Mt")
```

## Cross-validate against an external assumption set

```python
from enesys import rolling_all_paths

prices_pypsa = rolling_all_paths(year=2026, param_set="ariadne_pypsa")
for path, ct in sorted(prices_pypsa.items(), key=lambda kv: kv[1]):
    print(f"  {path:<10} {ct:6.2f} ct/kWh")
```

See [PARAM_SETS.md](PARAM_SETS.md) for the mechanism and the available
substrate (PyPSA-Technology-Data).

## Run the test suite

```bash
pytest tests/
```

The suite covers model invariants, source-traceability, and convergence
under alternative parameter substrates. A green suite is the precondition
for trusting any computed result.

## Render the example charts

The standalone scripts in `examples/` wrap the chart-rendering
functions used internally by the dashboard (in `enesys.viz`). They are
the recommended entry point for reproducing the figures — the
`enesys.viz.*` submodules themselves are not part of the stable public
API and may be refactored without notice.

```bash
python examples/generate_chart_nuclear_build_time_empirics.py
python examples/generate_chart_mix_rampup.py --camp neutral_default
python examples/generate_chart_tornado_sensitivity.py
python examples/generate_chart_monte_carlo.py
python examples/generate_chart_stress_rampup.py
```

PNGs land in `examples/`. Override the camp with `--camp ee_optimistic`
etc.; render SVG instead of PNG with `--variant web`.

## Where to go next

- [docs/FORMULAS.md](FORMULAS.md) — every formula with derivation and worked examples.
- [docs/SOURCES.md](SOURCES.md) — every default parameter with its primary source.
- [docs/methodik/methodology.md](methodik/methodology.md) — the three structural choices.
- [docs/methodik/modell_architektur.md](methodik/modell_architektur.md) — module-level architecture overview.
- [docs/HOWTO_RUN.md](HOWTO_RUN.md) — detailed runner for the full analysis.
