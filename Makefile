.DEFAULT_GOAL := help
.PHONY: help venv install test test-model lint lint-fix check build charts clean

# Parameter set ("camp") used by the chart wrappers. Default: neutral_default.
# Override with: make charts CAMP=ee_optimistic
CAMP ?= neutral_default

# Use the project's venv-Python when available, otherwise fall back to
# system python3. The venv is created by `make venv` or by the devcontainer's
# `uv sync --all-extras` step.
ifneq ($(wildcard .venv/bin/python),)
    PYTHON := $(CURDIR)/.venv/bin/python
    export PATH := $(CURDIR)/.venv/bin:$(PATH)
else
    PYTHON := python3
endif

help:
	@echo "Targets:"
	@echo "  venv        create .venv and install all extras (uv if available, pip fallback)"
	@echo "              ↳ in the devcontainer this runs automatically during build —"
	@echo "                only needed for bare-metal setups (no Docker / no Devcontainer)"
	@echo "  install     pip install -e .[dev]  (legacy, prefer 'venv')"
	@echo "  test        pytest (full suite)"
	@echo "  test-model  pytest -q (compact output)"
	@echo "  lint        ruff check + ruff format --check"
	@echo "  lint-fix    ruff check --fix + ruff format (apply auto-fixes)"
	@echo "  check       test + lint (CI-equivalent)"
	@echo "  build       python -m build  (-> dist/*.whl, *.tar.gz)"
	@echo "  charts      generate all standalone charts in examples/ (CAMP=$(CAMP))"
	@echo "              available camps: neutral_default, ee_optimistic, atom_optimistic, bestand_optimistic"
	@echo "  clean       remove caches and build artifacts"

venv:
	@# Abort if running on host while a devcontainer config exists — a venv
	@# created with host-Python won't match the container's Python version.
	@# Override with `make venv FORCE=1` for intentional bare-metal setups.
	@if [ -f .devcontainer/devcontainer.json ] && [ ! -f /.dockerenv ] && [ -z "$$REMOTE_CONTAINERS" ] && [ -z "$(FORCE)" ]; then \
	  echo "⚠  Devcontainer-Setup detected, but you appear to be on the host."; \
	  echo "   The container builds .venv automatically (uv sync via onCreateCommand)."; \
	  echo "   Running 'make venv' here creates a venv with host-Python that"; \
	  echo "   the container may reject due to Python-version mismatch."; \
	  echo ""; \
	  echo "   Recommended:  code .       # devcontainer handles setup"; \
	  echo "   Bare-metal:   make venv FORCE=1"; \
	  exit 1; \
	fi
	@echo "-> Create .venv and install model + ui/charts/dev extras"
	@if command -v uv >/dev/null 2>&1; then \
	  echo "  (using uv sync with uv.lock - fast + deterministic)"; \
	  uv sync --all-extras; \
	else \
	  echo "  (uv not found, falling back to pip - slower, no lock)"; \
	  echo "  Tip: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
	  python3 -m venv .venv; \
	  .venv/bin/python -m pip install --quiet --upgrade pip wheel; \
	  .venv/bin/python -m pip install --quiet -e '.[charts,dev]'; \
	fi
	@echo "OK venv ready. Activate with: source .venv/bin/activate"

install:
	$(PYTHON) -m pip install -e .[dev]

# Precondition: pytest / ruff müssen verfügbar sein. Fresh-Clone-Nutzer
# laufen sonst in »No module named pytest« mit unklarer Diagnose.
.PHONY: _check-deps
_check-deps:
	@$(PYTHON) -c "import pytest" 2>/dev/null || { \
	  echo ""; \
	  echo "FEHLER: pytest nicht gefunden. Setup nachholen:"; \
	  echo ""; \
	  echo "    make venv            # uv sync oder pip install der dev-Extras"; \
	  echo ""; \
	  echo "Wenn Du eine eigene venv pflegst, dort installieren:"; \
	  echo ""; \
	  echo "    pip install -e '.[charts,dev]'"; \
	  echo ""; \
	  exit 1; \
	}

test: _check-deps
	$(PYTHON) -m pytest

test-model: _check-deps
	$(PYTHON) -m pytest -q

lint: _check-deps
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

lint-fix: _check-deps
	$(PYTHON) -m ruff check --fix src/ tests/
	$(PYTHON) -m ruff format src/ tests/

check: test lint
	@echo ""
	@echo "OK all checks passed."

build:
	$(PYTHON) -m build

charts:
	@echo "-> Generate standalone charts in examples/ (camp: $(CAMP))"
	@for script in examples/generate_chart_*.py; do \
	  echo "  - $$script --camp $(CAMP)"; \
	  $(PYTHON) "$$script" --camp $(CAMP) || { echo "  ! ERROR in $$script"; exit 1; }; \
	done
	@echo "OK all charts built (camp: $(CAMP))"

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/ .coverage
	rm -f examples/*.png
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
