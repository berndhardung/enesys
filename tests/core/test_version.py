"""Tests für die Versionsverwaltung.

Testet:
- get_base_version() liest die VERSION-Datei korrekt
- get_version() rendert das gewünschte Format-Schema:
  * sauberer Build (stable-Branch + clean) → nur Basis
  * Branch + clean → Basis + hash
  * dirty → Basis + (hash) + dirty
- Verhalten ohne Git (Container, Wheel-Install)

Die Tests setzen ein temporäres Git-Repo auf, um die vier Hauptfälle
deterministisch zu erzeugen.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from enesys.version import (
    get_base_version,
    get_git_metadata,
    get_version,
)

# ---------------------------------------------------------------------------
# Basis-Version aus VERSION-Datei
# ---------------------------------------------------------------------------


def test_base_version_is_semver_format():
    """VERSION-Datei enthält MAJOR.MINOR.PATCH, optional mit Pre-Release-Suffix.

    Privat trägt einen Pre-Release-Tag (z.B. ``0.0.1-pre``, ``0.1.0.dev0``);
    Public-Build strippt ihn beim Mirror-Build (siehe build_public.py).
    """
    base = get_base_version()
    assert re.match(
        r"^\d+\.\d+\.\d+([-.]?(pre|dev|rc|a|b|alpha|beta)\d*)?$",
        base,
        re.IGNORECASE,
    ), f"VERSION-Inhalt '{base}' entspricht nicht MAJOR.MINOR.PATCH[-pre|.dev|...]"


def test_base_version_is_not_empty():
    """VERSION-Datei ist nicht leer."""
    base = get_base_version()
    assert base
    assert base != "0.0.0", (
        "Default-Fallback '0.0.0' aktiv — VERSION-Datei wahrscheinlich nicht "
        "gefunden. Liegt sie im Repo-Root?"
    )


# ---------------------------------------------------------------------------
# Git-Metadaten
# ---------------------------------------------------------------------------


def test_git_metadata_returns_expected_keys():
    """get_git_metadata liefert immer dieselben Keys, auch ohne Git."""
    meta = get_git_metadata()
    assert set(meta.keys()) == {"branch", "hash", "hash_short", "dirty"}


def test_git_metadata_dirty_is_bool():
    """dirty ist immer ein bool, niemals None."""
    meta = get_git_metadata()
    assert isinstance(meta["dirty"], bool)


# ---------------------------------------------------------------------------
# get_version() — vier Format-Cases
# ---------------------------------------------------------------------------


def test_version_string_starts_with_base_version():
    """get_version() beginnt immer mit der Basis-Version aus VERSION-Datei."""
    base = get_base_version()
    version = get_version()
    assert version.startswith(base), f"Version '{version}' beginnt nicht mit Basis '{base}'"


def test_version_string_format_overall():
    """Validiert das Format: BASE oder BASE-gHASH-DATE oder
    BASE-gHASH-dirty-DATE oder BASE-dirty-DATE (wenn keine git-
    Metadaten verfügbar). Im Public-ZIP-Build (kein Git) hängt
    zusätzlich ein PEP-440-Local-Stamp ``+<date>.g<hash>`` aus
    der VERSION-Datei dran."""
    version = get_version()
    pattern = (
        r"^"
        r"\d+\.\d+\.\d+"  # Basis-Version
        r"([-.]?(pre|dev|rc|a|b|alpha|beta)\d*)?"  # optionales Pre-Release-Suffix
        r"(-g[0-9a-f]{7,})?"  # optionaler Hash-Teil
        r"(-dirty)?"  # optionales dirty-Suffix
        r"(-\d{4}-\d{2}-\d{2})?"  # optionales ISO-Datum
        r"(\+[A-Za-z0-9._-]+)?"  # optionaler PEP-440-Local-Stamp (Public-ZIP)
        r"$"
    )
    assert re.match(pattern, version, re.IGNORECASE), (
        f"Version '{version}' entspricht nicht dem erlaubten Schema"
    )


# ---------------------------------------------------------------------------
# Vier-Case-Test in temporärem Git-Repo
# ---------------------------------------------------------------------------


def _make_temp_repo(tmp_path: Path) -> Path:
    """Setzt ein minimales Git-Repo mit VERSION + version.py auf.

    Returns: Pfad zum Repo-Root.
    """
    # Layout nachbauen: tmp/src/enesys/{__init__,version}.py
    pkg_dir = tmp_path / "src" / "enesys"
    pkg_dir.mkdir(parents=True)

    # version.py + __main__.py ins temporäre Repo kopieren
    real_pkg = Path(__file__).resolve().parent.parent.parent / "src" / "enesys"
    (pkg_dir / "version.py").write_text(
        (real_pkg / "version.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (pkg_dir / "__main__.py").write_text(
        (real_pkg / "__main__.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    # VERSION-Datei mit Test-Wert
    (tmp_path / "VERSION").write_text("0.5.0\n", encoding="utf-8")

    # Git initialisieren
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q")
    git("config", "user.email", "test@test.local")
    git("config", "user.name", "Test")
    # gitignore setzen, damit pycache nicht die dirty-Erkennung stört
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    git("add", "VERSION", "src", ".gitignore")
    git("commit", "-q", "-m", "init")

    return tmp_path


def _run_version_in(repo: Path) -> str:
    """Ruft das version.py-Modul im temporären Repo auf und gibt das
    gerenderte get_version()-Ergebnis zurück."""
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-m", "enesys"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def test_case_main_clean(tmp_path):
    """Auf main-ähnlichem Branch + clean → Basis-Version + Hash + Datum."""
    repo = _make_temp_repo(tmp_path)
    version = _run_version_in(repo)
    assert re.match(r"^0\.5\.0-g[0-9a-f]{7,}-\d{4}-\d{2}-\d{2}$", version), (
        f"Erwartet '0.5.0-gXXXXXXX-YYYY-MM-DD', bekommen '{version}'"
    )


def test_case_main_dirty(tmp_path):
    """Auf main + uncommittete Änderung → Basis-Hash-dirty-Datum."""
    repo = _make_temp_repo(tmp_path)
    # tracked file modifizieren
    (repo / "VERSION").write_text("0.5.0\n# extra\n", encoding="utf-8")
    version = _run_version_in(repo)
    assert re.search(r"-dirty-\d{4}-\d{2}-\d{2}$", version), (
        f"Erwartet '...-dirty-YYYY-MM-DD', bekommen '{version}'"
    )
    assert "-g" in version, f"Erwartet Hash-Suffix in '{version}'"


def test_case_stable_branch_clean(tmp_path):
    """Auf stable/X.Y-Branch + clean → nur Basis-Version, kein Suffix, kein Datum."""
    repo = _make_temp_repo(tmp_path)
    subprocess.run(
        ["git", "checkout", "-q", "-b", "stable/0.5"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    version = _run_version_in(repo)
    assert version == "0.5.0", f"Erwartet sauberes '0.5.0' auf stable-Branch, bekommen '{version}'"


def test_case_stable_branch_dirty(tmp_path):
    """Auf stable/X.Y-Branch + dirty → trotzdem Hash-dirty-Datum-Suffix."""
    repo = _make_temp_repo(tmp_path)
    subprocess.run(
        ["git", "checkout", "-q", "-b", "stable/0.5"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # tracked file modifizieren
    (repo / "VERSION").write_text("0.5.0\n# extra\n", encoding="utf-8")
    version = _run_version_in(repo)
    assert re.search(r"-dirty-\d{4}-\d{2}-\d{2}$", version), (
        f"Erwartet '...-dirty-YYYY-MM-DD' auch auf stable-Branch bei dirty, bekommen '{version}'"
    )


def test_untracked_files_do_not_make_dirty(tmp_path):
    """Untracked files (z.B. __pycache__) dürfen NICHT als dirty zählen."""
    repo = _make_temp_repo(tmp_path)
    # Untracked file anlegen
    (repo / "untracked_dummy.txt").write_text("nothing tracked\n")
    version = _run_version_in(repo)
    assert "-dirty" not in version, f"Untracked file hat fälschlich dirty ausgelöst: '{version}'"
