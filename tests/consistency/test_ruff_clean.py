"""Ruff-Clean-Gate: pytest failt, wenn Ruff Verstöße findet.

Lokaler pytest-Lauf soll Ruff-Errors sofort fangen, nicht erst in CI.
Verhindert, dass jemand mit grünem Test-Suite-Lauf nach CI-Failure
zurückfindet (»aber lokal lief doch alles«).

Mit pytest.skip, falls ruff nicht im Pfad ist — typisch für Test-
Läufe ohne ``pip install -e ".[dev]"``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ruff_check_src_and_tests_clean() -> None:
    """``ruff check src/ tests/`` muss ohne Fehler durchlaufen.

    Spiegelt den CI-Schritt aus ``.github/workflows/tests.yml`` — wenn
    dieser Test grün ist, ist auch der CI-Lint-Step grün.
    """
    ruff = shutil.which("ruff")
    if ruff is None:
        pytest.skip('ruff nicht installiert; dev-deps via `pip install -e ".[dev]"` ergänzen.')

    result = subprocess.run(
        [ruff, "check", "src/", "tests/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Ruff hat Verstöße gefunden:\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )


def test_ruff_format_check_src_and_tests_clean() -> None:
    """``ruff format --check src/ tests/`` muss ohne Diff durchlaufen.

    Formatierungs-Gate. Pre-Commit-Hook hat dieselbe Regel, aber dieser
    Test fängt sie auch ohne installierten Pre-Commit.
    """
    ruff = shutil.which("ruff")
    if ruff is None:
        pytest.skip('ruff nicht installiert; dev-deps via `pip install -e ".[dev]"` ergänzen.')

    result = subprocess.run(
        [ruff, "format", "--check", "src/", "tests/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Ruff-Format-Check failt (nicht formatierte Files):\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}\n"
            f"Fix: `ruff format src/ tests/` lokal ausführen."
        )
