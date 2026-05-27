"""Mypy-Clean-Gate: pytest failt, wenn mypy auf ``src/enesys/`` Errors findet.

Lokaler pytest-Lauf fängt Type-Errors sofort, nicht erst in CI. Konsistent
mit dem ``test_ruff_clean.py``-Pattern.

Skipt mit Hinweis, falls mypy nicht im Pfad ist — etwa wenn der Test-
Lauf ohne ``pip install -e ".[dev]"`` erfolgt.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mypy_clean_src() -> None:
    """``mypy src/enesys/`` muss ohne Errors durchlaufen.

    Spiegelt den CI-Schritt aus ``.github/workflows/tests.yml`` — wenn
    dieser Test grün ist, ist auch der CI-Type-Check-Step grün.
    """
    mypy = shutil.which("mypy")
    if mypy is None:
        pytest.skip('mypy nicht installiert; dev-deps via `pip install -e ".[dev]"` ergänzen.')

    result = subprocess.run(
        [mypy, "src/enesys/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Mypy hat Type-Errors gefunden:\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
