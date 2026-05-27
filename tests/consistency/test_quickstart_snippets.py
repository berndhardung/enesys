"""Smoke-Test: alle Python-Code-Snippets aus ``docs/QUICKSTART.md`` laufen.

Verhindert, dass die Quickstart-Beispiele still aus dem Modell driften.
Wenn `compute_path` / `baseline_all_paths` / `Demand` ihre Signatur
ändern und der Quickstart nicht nachgezogen wird, schlägt dieser Test
fehl, bevor ein Nutzer auf eine tote Stelle in der Doku trifft.

Mechanik: Markdown-File parsen, jeden ``python``-Codeblock einzeln in
einem frischen Namespace ausführen. CLI-Beispiele (``bash``-Blöcke)
werden ignoriert.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
QUICKSTART_MD = REPO_ROOT / "docs" / "QUICKSTART.md"

_CODE_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _python_blocks() -> list[str]:
    text = QUICKSTART_MD.read_text(encoding="utf-8")
    return [m.group(1) for m in _CODE_BLOCK_RE.finditer(text)]


def test_quickstart_has_python_blocks() -> None:
    """Sanity: QUICKSTART enthält überhaupt Python-Snippets."""
    assert _python_blocks(), (
        f"{QUICKSTART_MD} enthält keine ```python`-Blöcke — der "
        f"Smoke-Test wäre dann sinnlos. Quickstart-Snippets prüfen."
    )


@pytest.mark.parametrize("block", _python_blocks())
def test_quickstart_snippet_runs(block: str) -> None:
    """Jeder Python-Block läuft ohne Exception."""
    exec(compile(block, str(QUICKSTART_MD), "exec"), {})
