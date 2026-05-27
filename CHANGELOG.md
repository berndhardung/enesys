# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-27 — Initial public mirror

First public mirror of the model. Pre-1.0 — interfaces may still change
before 1.0.

### What the model can do

- **Six-path forward-cost comparison** (WEITER-SO, BESTAND, EE-GAS, EE-H2,
  KKW-GAS, KKW-H2) over a 30-year horizon (2026–2055), with explicit
  treatment of build-times, sector coupling, and grid-stability requirements.
- **Lager-symmetric sensitivity analysis** — five parameter camps
  (`neutral_default`, `ee_optimistic`, `atom_optimistic`,
  `bestand_optimistic`, `weiterso_optimistic`) plus arbitrary parameter
  overrides at the API level.
- **Tornado + Monte-Carlo robustness** — every default parameter has a
  documented camp range; Monte-Carlo over the joint ranges reports
  P(path wins) percentages.
- **Forward-cost framing** — sunk costs (existing nuclear decommissioning,
  endlager fund, EEG legacy) are tracked as informative variables but
  explicitly excluded from investment decisions.
- **Winter dunkelflaute stress test** — 10-day cold-dark-calm period
  with cost and reliability impact.
- **Steady-state 2055 cross-check** — `compute_path` runs forward to a
  2055–2085 steady-state window as an independent triangulation against
  the 30-year trajectory.
- **Five standalone chart wrappers** (`examples/generate_chart_*.py`) for
  the central visuals: build-time empirics, mix ramp-up, winter stress,
  tornado sensitivity, Monte-Carlo robustness.

### What the model does not do

- **No optimization.** The model evaluates pathways under chosen parameters;
  it does not search for an optimal pathway.
- **No hourly dispatch.** Backup needs are derived from a structural winter
  stress test, not from a full chronological hourly simulation.
- **No grid topology.** Network costs enter as a per-kWh markup calibrated
  to BNetzA scenarios, not from explicit line-by-line modelling.
- **No multi-country coupling.** Germany is modelled as a single price zone;
  cross-border exchange is implicit in the residual mix.

### Quality gates

- Full test suite passes (pytest); deterministic Monte-Carlo with fixed
  seeds.
- Every default parameter has a `[SRC: ...]` tag pointing to a primary
  source in [`docs/SOURCES.md`](docs/SOURCES.md).
- Python 3.10+ required; pinned dependencies in `uv.lock`.
- CI runs on every commit (GitHub Actions).

### Known limitations of this release

- API surface (function signatures, dataclass fields) may still change
  before 1.0.
- Documentation is bilingual: methodology is mostly German, source
  comments and tests are bilingual.
