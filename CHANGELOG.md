# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-07-12 — New cost substrate, regret-matrix chart, path-measures API

Minor release — first genuine new model-API capability since 0.2.x.

### Added

- **Cost-substrate family now spans three camp-aligned positions.**
  New renewables-leaning substrate `ise_lcoe` (Fraunhofer ISE
  "Stromgestehungskosten Erneuerbare Energien" 2024) — a German cost
  substrate that also covers nuclear, verified against the primary
  source (Tab. 1/2/5) with a new convergence test (7 slots). Alongside
  it, the nuclear-leaning substrate `nea_pcge` (IEA/NEA, *Projected
  Costs of Generating Electricity*, 2020, 9th ed. — OECD-Europe median,
  WACC 7% real) is now documented in `docs/PARAM_SETS.md` for the first
  time, next to the existing neutral `ariadne_pypsa` substrate.
  Methodological notes cover the "source, not camp" framing and the
  nuclear-leaning asymmetry.
- **`enesys.viz.charts.regret_matrix`** — a new chart type: a path×camp
  full-system cost matrix (six policy paths × four camp worlds), cell colour
  encodes regret, bars show maximum regret per path. Ships as a comparable
  horizon pair (today 2026-2055 vs. children 2055-2084 steady state, full
  nuclear fleet online) with a shared bar scale. New standalone generator:
  `examples/generate_chart_regret_matrix.py`.
- **`enesys.core.path_measures`** — a new module computing, per policy path,
  a neutral list of preconditions/measures (deadline, realization rate,
  build-time provenance) framed as "what would have to happen, by when, for
  this path to work out." Library-only so far — not yet wired into the
  Streamlit UI.

### Changed

- Nothing breaking — all additions are purely additive to the `enesys`
  model API.

## [0.2.1] — 2026-06-13 — Streamlit performance, bilingual chart export, fixes

Patch release — visualisation performance and bug fixes; no model-API change.

### Added

- **`--lang {de,en}` on the standalone chart generators** — each chart
  renders in a single language and the output filename gets a `_de` /
  `_en` suffix. Default `en`; both via `make build-charts LANGS="de en"`.

### Changed

- **Streamlit compare view substantially faster** — renders one chart at
  a time (chart switcher; "All charts" restores the full view), reuses
  cached model data on language/layout switches, and caches rendered
  charts to disk. First paint now costs one chart instead of six.
- Internal test-suite speedups.

### Fixed

- **Mixed-language chart images** — generators emitted an English title
  over a German body; charts are now consistently one language.
- **Monte-Carlo win-probability axis** labelled the wrong way round — now
  "EE-GAS win probability vs. each path".
- **Dead "sources" deep-link** in the Streamlit app under Streamlit ≥1.36
  path-based routing.
- **Crash when selecting the `weiterso_optimistic` camp** — slider ranges
  now always cover every camp default.

## [0.2.0] — 2026-06-07 — Streamlit UI, English documentation, regret-robustness API

This release adds:

- a Streamlit-based compare-view UI as the primary visible surface,
- English documentation across the README front-path and methodology depth,
- a new public API for nuclear-start-year regret robustness analysis,
- a reframed README headline that leads with Monte-Carlo pair
  probabilities instead of point-estimate rankings,
- an external-output comparison against PyPSA-DE / Ariadne and
  Fraunhofer ISE per-technology LCOEs.

System-boundary CO₂ accounting (forward 2026–2055) replaces the prior
electricity-sector-only reporting so the CO₂ axis matches the cost axis.

### Added

- **Streamlit compare-view UI** (`app/streamlit_app.py`, `src/enesys/ui/`) —
  Side-by-side comparison of two parameter camps across the core charts
  (mix ramp-up, winter stress, LCOE trajectory, tornado, Monte-Carlo).
  Runs locally via `streamlit run app/streamlit_app.py` or on Streamlit
  Community Cloud.
- **Bilingual UI** — chart titles, axes, legends, and tornado-lever labels
  available in DE/EN via `src/enesys/viz/charts/labels.py`; language
  selection persists across pages.
- **Regret-robustness public API** (`src/enesys/core/regret_decision_tree.py`):
  `compute_regret_matrix`, `minimax_regret_per_policy`,
  `nuclear_start_year_regret_analysis`, `kkw_regret_crossover_year`, plus
  the data classes `RegretMatrixCell`, `PolicyChoice`,
  `NuclearStartYearRegretPoint`. Operationalises the question "at which
  KKW start year does a nuclear policy become regret-optimal?". At
  current model defaults the crossover is `None` for 2020–2055 — the
  recommendation is not a timing artifact.
- **`override_kkw_epr_startjahr` context manager**
  (`src/enesys/core/inventories/tech_inventory.py`) — temporarily sets a
  uniform nuclear start year across all camps for sensitivity sweeps.
  Function previously named `_kkw_epr_startjahr` is now public as
  `kkw_epr_startjahr`.
- **README headline image** (`docs/_static/headline_stress_rampup.png`)
  showing the six-panel stress-test ramp-up across all paths, built via
  a new release-asset pipeline (`tools/build_readme_assets.py`) that is
  intentionally decoupled from the per-chart generators in `examples/`.
- **Methodology Section 4b** — *Robustness check: nuclear start year
  independent of camp realization rate*. Documents the regret-robustness
  finding with a reproducible code snippet.
- **Methodology Section 4c** — *External-output comparison: enesys vs
  Ariadne / Fraunhofer ISE*. Per-technology LCOE side-by-side comparison
  and substrate-swap cross-check; flags the apples-to-oranges between
  enesys cost-of-supply LCOE and Ariadne wholesale-equilibrium prices.
- **Pull-request template** for OSS contributions
  (`.github/PULL_REQUEST_TEMPLATE.md`).

### Changed

- **Documentation surface fully English.** Translated `docs/FORMULAS.md`,
  `docs/PARAM_SETS.md`, `docs/VERSIONING.md`,
  `docs/methodik/modell_architektur.md`, and
  `docs/methodik/bridge_phase_parameters.md`. The steady-state
  parameter-consistency document is now
  [`docs/methodik/steady_state_parameter_consistency.md`](docs/methodik/steady_state_parameter_consistency.md)
  (renamed from a German-suffix filename; all link sites and the
  build whitelist updated). `docs/SOURCES.md` gets an English header and English
  section labels; source citations stay in their primary language
  because most primary sources are German (BNetzA, BMWE, ISE, EWI,
  KVBG, NWS, …).
- **README headline framing — Monte-Carlo pair probabilities.** The
  deterministic 6-path cost spread is 1.0 ct/kWh — smaller than the
  P5–P95 spread within any single path (1.7–3.6 ct/kWh across 2,000 MC
  runs). The README now leads with `P(EE-GAS < other path)` from
  `monte_carlo_all_paths` and flags the point-estimate ordering as a
  tied cluster within MC noise rather than as a ranking.
- **Robust vs noise separation made explicit** (README + methodology
  Section 4a). Structural claims — CO₂ separation between active and
  inactive paths, EE-GAS dominance among active paths, regret
  asymmetry — stated as findings. Cost ordering between WEITER-SO,
  EE-GAS, BESTAND, EE-H2 stated as a deterministic baseline cluster.
- **Naming: `cross-validation` → `parameter-substrate robustness check`**
  (methodology Section 4, `test_ariadne_convergence.py`, CITATION.cff,
  internal comments). `cross-validation` has a specific train/test
  meaning in statistics that does not apply when swapping the entire
  assumption substrate.
- **`Streamlit + chart libraries are now base dependencies`** in
  `pyproject.toml` (`streamlit`, `plotly`, `matplotlib`, `pandas`).
  Previously gated behind optional extras; install `enesys` and the UI
  runs out of the box.
- **CO₂ accounting boundary** — `co2_lockin_metric` reports CO₂ over
  the forward 2026–2055 system boundary, aligning the CO₂ axis with
  the cost axis. `docs/FORMULAS.md` and public README values updated
  accordingly.
- **Stress-test default** — `stress_rampup` sizes backup capacity to
  LOLE-P95 (95th-percentile loss-of-load expectation) instead of the
  previous deterministic worst-case. API surface unchanged.
- **Rolling-LCOE methodology** — `docs/methodik/methodology.md` and
  `docs/QUICKSTART.md` reframed around Rolling-LCOE 2026–2055 as the
  primary cost metric; Snapshot-LCOE retained as a cross-check.
- **Streamlit Monte-Carlo expander text** points to `docs/SOURCES.md`
  and `docs/methodik/methodology.md` instead of the previous reference
  to a separate publication.
- **Stress-chart labels** — `cold-spell average` → `dark-doldrum
  average` and `Peak demand (cold spell)` → `Peak demand (dark
  doldrum)` for consistency with the ENTSO-E term and with the chart
  subtitle.
- **CI workflows** — bumped to `actions/checkout@v5` and
  `actions/setup-python@v6`.
- **README distinctive-properties section** condensed from five long
  blocks to five tight bullets with code-reference pointers; full
  discussion remains in `docs/methodik/methodology.md`.

### Fixed

- Ruff format pass on mobile-layout fix in `rampup` and `stress` charts.
- Notebook ruff format on `notebooks/01_quickstart.ipynb`.
- Line-end-hyphen hygiene across narrative files.
- Removed residual references to internal narrative sources from public
  code comments and tests (book/manuscript callouts, appendix-letter
  cross-references, dead test-file pointer).

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
