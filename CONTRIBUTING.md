# Contributing

Thank you for your interest. This project takes contributions, but with a
clear **scope discipline** because the model is meant to be a *neutral
analytical tool*, not an advocacy platform.

## What we welcome

### 1. Bug reports

Found a formula error, broken test, or non-reproducible result? Please open
an issue with:

- The exact command or code that fails
- Expected vs. actual output
- Your Python version and OS

### 2. Source updates

When a primary source publishes new data (e.g., next BNEF survey, new ISE
study), we welcome PRs that:

- Update the parameter default to the new value
- Update the corresponding entry in `docs/SOURCES.md` with the new
  citation, date, and URL
- Update or add a test that anchors the new value
- Note in the PR description: *what changed and why it matters*

### 3. New regulatory contexts

The model is calibrated for Germany. We welcome forks that adapt it to
other countries (France, Poland, UK, etc.). PRs that make the model
*regionally configurable* (rather than country-specific) are especially
welcome.

### 4. Methodological critique

Open an issue with:

- Which assumption you think is wrong
- Which source supports your alternative
- What the impact would be on the conclusion

The model is built on the principle that *robust conclusions survive
adversarial assumptions*. Critique that points to weaknesses in this
robustness is the most valuable contribution.

## What we don't want

### 1. Advocacy commits

Do not submit PRs that:

- Hardcode pro-renewable or pro-nuclear assumptions
- Remove "inconvenient" parameters or sources
- Bias the default presets toward one lager
- Add prose to the documentation arguing for one specific policy

The model must remain a tool that both renewables advocates and nuclear
advocates can use to test their assumptions.

### 2. Off-topic features

Examples of out-of-scope contributions:

- Adding completely different energy technologies (e.g., space-based solar)
  without primary-source backing
- Politically motivated reframing of variable names
- Marketing or promotional content

## How to contribute

### Setup

See the [Quickstart in the README](README.md#quickstart). For development
work, add the `dev` extras: `make venv` (uv-based) is the fast and
deterministic path; `pip install -e ".[dev]"` works as a fallback.

### Run tests before submitting

```bash
make test
```

The full suite must stay green. New parameters need new tests.

### Commit conventions

We use semantic commits:

- `fix:` bug fixes (formula errors, test failures)
- `feat:` new features (new model components, new analyses)
- `docs:` documentation only
- `data:` parameter or source updates
- `test:` test additions or fixes
- `refactor:` non-functional changes

Example:

```
data: update battery CAPEX to BNEF Dec 2025 value

BNEF Energy Storage Cost Survey 2025 published 10 Dec 2025
reports turnkey BESS at $117/kWh global average, down from $169/kWh
in 2024. Update battery_capex_eur_kwh default from 165 to 110.

Sources: SOURCES.md updated with new citation.
Tests: test_path_model.py:test_battery_realistic anchored at new value.
```

### Pull request checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] New parameters have new tests
- [ ] `docs/SOURCES.md` updated if defaults changed
- [ ] `docs/FORMULAS.md` updated if formulas changed
- [ ] `[SRC: ...]` tags in code point to existing entries in SOURCES.md
- [ ] PR description explains *what* and *why*

## Code style

- Python 3.10+ idioms (use `dict[str, float]`, not `Dict[str, float]`)
- Type hints encouraged, especially for public API
- Docstrings in module and function level
- No comments that just restate the code
- Comments that justify *why* a value is chosen are welcome, especially
  with `[SRC: tag]` references

## Communication

- **Issues**: technical questions and bug reports
- **Discussions**: methodological debate, alternative interpretations
- **Email**: for sensitive matters (e.g., suspected source manipulation)

## Code of conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
The energy transition is a contested topic; debate is welcome but personal
attacks are not.

## Recognition

Contributors will be recognized in:

- `AUTHORS.md` (significant contributions)
- Release notes (per-release contributions)
