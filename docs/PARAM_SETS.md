# PARAM_SETS.md — External assumption substrates as a first-class construct

## What is a ParamSet?

A **ParamSet** bundles the default assumption substrate of an external
model family (PyPSA-DE/Ariadne, NEA-IEA PCGE, BNEF, Fraunhofer ISE, …)
as a reproducible override dict for `compute_path`. It translates the
tech names of the external source to enesys tech IDs and supplies
trajectory values for CAPEX, FOM, VOM, WACC, and fuel prices over
knot years 2030 / 2040 / 2050.

## Distinction from CAMP_RANGES

| Aspect | CAMP_RANGES | ParamSet |
|---|---|---|
| Argument | political | methodological |
| Question | "What range would this camp accept?" | "Does our finding survive under the assumption substrate of another model?" |
| Content | EE/atom/existing-fleet-optimistic, neutral default | concrete default values of an external source |
| Representation | range per tech | knot-point trajectory per tech |
| Override mechanism | shared: `param_overrides` in `compute_path` | shared: `param_overrides` in `compute_path` |

Both structures are compatible with the tornado / Monte-Carlo
infrastructure.

## Usage

```python
from enesys import rolling_all_paths

# Standard enesys assumptions (rolling 30-yr from 2026, canonical):
default = rolling_all_paths(year=2026)

# With external substrate (Ariadne/PyPSA):
ariadne = rolling_all_paths(year=2026, param_set="ariadne_pypsa")

# Available sets:
from enesys import PARAM_SETS
print(list(PARAM_SETS))
```

Path-by-path call:

```python
from enesys import compute_path

result = compute_path(
    "ee_gas",
    years=[2030, 2040, 2050],
    param_set="ariadne_pypsa",  # trajectory takes effect year by year
)
```

Combination with constant overrides (e.g. for a Monte-Carlo sample):

```python
# Trajectory as the base, constant override takes precedence:
compute_path(
    "ee_gas",
    [2045],
    param_set="ariadne_pypsa",
    param_overrides={"co2_price_eur_t": 200.0},
)
```

CLI inspection (display override values for one year):

```bash
python -m enesys.core.param_sets.ariadne_pypsa
```

## Available sets

### ariadne_pypsa

PyPSA-Tech-Data default assumptions 2030 / 2040 / 2050 — the
assumption substrate of the BMBF-Ariadne model family.

- **Source:** [PyPSA/technology-data](https://github.com/PyPSA/technology-data)
- **Primary citations:** Lazard 16.0 (nuclear, coal), Danish Energy
  Agency (renewables, gas, electrolysis), ENTSO-E/ENTSOG TYNDP 2024
  (fuel prices)
- **Knot years:** 2030 / 2040 / 2050
- **Price basis:** EUR_2025

**Methodological classification.** PyPSA-DE is EE-leaning as a model
framework (default scenarios without nuclear); the individual
parameter values, however, are cleanly grounded in primary sources
and not anti-nuclear. Nuclear CAPEX (10,806 EUR/kW, Lazard 16.0) is
almost identical to enesys-neutral (11,000 EUR/kW).


## How do I add a new set?

1. **Copy the template:**
   ```bash
   cp src/enesys/core/param_sets/_template.py src/enesys/core/param_sets/{name}.py
   ```
2. **Hard-code the values** from the primary source. Do *not* load
   them at runtime from CSVs — explicit values in code are the goal
   for reproducibility.
3. **Adjust the mapping:**
   - External tech names → enesys tech IDs in `_TECH_MAPPING`
   - External fuel names → enesys fuel IDs in `_FUEL_MAPPING`
   - Watch for 1:n mappings (e.g. external "nuclear" → enesys
     `kkw_bestand` + `kkw_neubau_epr` + `kkw_neubau_smr`)
4. **Document the caveats fully** — what differs methodologically
   between the source and enesys? Learning effects, WACC handling,
   build-time modeling, fuel prices.
5. **Registry entry** in `src/enesys/core/param_sets/__init__.py`:
   ```python
   from enesys.core.param_sets.{name} import {NAME}_SET
   PARAM_SETS[{NAME}_SET.name] = {NAME}_SET
   ```
6. **Convergence test** `tests/consistency/test_{name}_convergence.py`
   modeled on `test_ariadne_convergence.py`. Six test slots:
   registry entry, override-keys hygiene, LCOE plausibility, path-
   order convergence, diff range, trajectory interpolation.

## Data conventions

### Trajectory value format

```python
{
    # time-constant:
    "kkw_neubau_epr.capex_eur_kw": 10805.70,

    # knot points (≥ 1, arbitrary years):
    "pv.capex_eur_kw": {2030: 482.48, 2040: 403.38, 2050: 367.87},

    # only 2 knot points — interpolation between them, constant outside:
    "steinkohle.preis_eur_mwh": {2030: 7.82, 2050: 6.72},
}
```

`ParamSet.overrides(year)` resolves knot points via linear
interpolation. Outside the range the nearest edge value is held
constant — no trend extrapolation, because learning effects beyond
the source horizons are speculative.

### Allowed override fields

`compute_path` accepts only the following override keys:

| Key pattern | Meaning |
|---|---|
| `<tech_id>.capex_eur_kw` | TechEntry CAPEX in EUR/kW |
| `<tech_id>.wacc_pct` | WACC as a **share** (0.0536 = 5.36 %) — *name is misleading* |
| `<tech_id>.opex_fix_eur_kw_a` | fixed operating cost in EUR/kW/yr |
| `<tech_id>.opex_var_eur_mwh` | variable operating cost in EUR/MWh |
| `<tech_id>.vlh_normal` | full-load hours in normal operation |
| `<fuel_id>.preis_eur_mwh` | fuel price in EUR/MWh_th |
| `co2_price_eur_t` | global CO₂ price |

Other fields (lifetime, efficiency, etc.) are not overridable via
`param_overrides` and must be changed on the tech-inventory side if
needed.

### Hard-code values instead of loading CSV

External sources are deliberately hard-coded into `*.py` files and not
read at runtime from CSV. Reasons:

- **Reproducibility** without external file dependency
- **Explicit values in code** — readable, diffable
- **Deliberate re-curation** on source updates instead of silent drift
- **No pandas dependency** for the override path

Each set file documents the source commit / state in the module
docstring, so the value transfer remains traceable.

## Architectural robustness

Adding a new set changes existing code as follows:

- **A new file** `src/enesys/core/param_sets/{name}.py`
- **A registry line** in `__init__.py`
- **Optionally** a dedicated convergence test

**What does not need to be touched:** `compute_path()`,
`baseline_all_paths()`, `path_model.py`, CAMP_RANGES, existing tests,
tech / fuel inventories.

**Known risk spot:** renaming an enesys tech ID would break all sets
at once. Mitigation: `assert_known_keys()` in the convergence test
fails with a clear list of unknown keys — refactor obligations
become visible instead of an obscure model crash.

## Multi-year overrides

`compute_path` supports three override sources with clear priority:

1. `param_set` (trajectory, lowest priority)
2. `param_overrides` (constant across all years)
3. `param_overrides_yearly` (per year, highest priority)

For multi-year runs the ParamSet trajectory is resolved year by year
— so learning effects are real, not averaged to a reference year.
