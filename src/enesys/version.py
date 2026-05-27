"""Versionsverwaltung für enesys.

Single-Source-Pattern: die Versionsnummer liegt in einer einzigen
Datei (`VERSION` im Repo-Root). Alle Konsumenten (Python-Paket,
Dashboard-Builds, Begleitdokumente) lesen aus dieser Quelle.

Versionsschema (Pre-1.0-Modus):
    MAJOR.MINOR.PATCH

    - MAJOR: Hauptlinie, an einen Stable-Branch gekoppelt
      (z.B. `stable/0.1`, später `stable/1.0`).
    - MINOR: darf in <1.0 *breaking* sein (kein Kompatibilitäts-Versprechen
      vor Version 1.0).
    - PATCH: Bugfixes innerhalb einer MINOR-Linie.

Anzeige-Format
--------------
Auf einem Stable-Branch und ohne lokale Änderungen wird nur die
Basis-Version gezeigt — das ist der saubere "GitHub-Release"-Stil:

    "0.1.0"

Bei Dev-Builds (kein Stable-Branch oder dirty) hängt sich Hash und
Build-Datum dran, damit der konkrete Stand eindeutig identifizierbar
bleibt:

    "0.1.0-gabc1234-2026-05-02"            sauber, aber kein Stable-Branch
    "0.1.0-dirty-2026-05-02"               lokale Änderungen
    "0.1.0-gabc1234-dirty-2026-05-02"      beides

Echte Releases werden mit annotierten Git-Tags `vX.Y.Z` markiert.
`get_version()` selbst wertet die Tags aber nicht aus — der Stand
wird ausschließlich über die VERSION-Datei und den Git-Status (Hash,
Dirty-Flag, Build-Datum) gerendert. Tags sind reine Bezugsadresse
für GitHub-Releases, DOIs und Bug-Reports.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
from importlib import metadata as _metadata
from pathlib import Path

# Pfad zur Repo-Root — von src/enesys/version.py aus
# zwei Ebenen hoch. Funktioniert im Editable-Install/Source-Checkout;
# bei einem regulären pip-Install liegt VERSION nicht mehr in diesem
# Pfad — dort übernimmt der importlib.metadata-Fallback.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_VERSION_FILE = _REPO_ROOT / "VERSION"

# PEP-440-Local-Version-Suffix (``+<date>.g<hash>``). Wird von
# ``tools/build_public.py`` an die VERSION-Datei im Public-ZIP-Snapshot
# angehängt, damit der entpackte Stand auch ohne ``.git/`` nachvollziehbar
# bleibt. Im Code wird der Stamp gestrippt — die "Basis"-Version ist die
# saubere Semver-Form ohne Build-Metadaten.
_LOCAL_VERSION_RE = re.compile(r"\+[A-Za-z0-9._-]+$")


def _read_version_file_raw() -> str:
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError):
        try:
            return _metadata.version("enesys")
        except _metadata.PackageNotFoundError:
            return "0.0.0"


def get_base_version() -> str:
    """Liest die Basis-Version aus der VERSION-Datei.

    Strippt einen etwaigen PEP-440-Local-Version-Stamp (``+...``), den
    der Public-ZIP-Build anhängt — die zurückgegebene Basis ist immer
    in MAJOR.MINOR.PATCH-Form (mit optionalem Pre-Release-Suffix).

    Fällt zurück auf "0.0.0", wenn die Datei nicht gefunden wird.
    """
    return _LOCAL_VERSION_RE.sub("", _read_version_file_raw())


def get_local_version_stamp() -> str:
    """Liefert den PEP-440-Local-Version-Stamp (``+<date>.g<hash>``) oder ``""``.

    Im Privat-Repo ist der Stamp leer; im Public-ZIP wird er von
    ``tools/build_public.py`` an VERSION angehängt, damit der
    Snapshot-Stand auch ohne ``.git/`` identifizierbar bleibt.
    """
    raw = _read_version_file_raw()
    m = _LOCAL_VERSION_RE.search(raw)
    return m.group(0) if m else ""


def _git(*args: str) -> str | None:
    """Führt einen git-Befehl im Repo-Root aus.

    Returns:
        Stdout (gestrippt) oder None bei Fehler / kein Git verfügbar.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def get_git_metadata() -> dict:
    """Sammelt Git-Status: Branch, Commit-Hash, Dirty-Flag, Distance.

    Returns:
        Dict mit Keys 'branch', 'hash', 'hash_short', 'dirty'.
        Wenn kein Git-Repo: alle None.
    """
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    hash_full = _git("rev-parse", "HEAD")
    hash_short = _git("rev-parse", "--short=7", "HEAD")
    # Dirty-Flag: Modifikationen an *tracked* files (uncommitted oder
    # staged). `--untracked-files=no` blendet untracked files aus
    # (z.B. __pycache__, .pytest_cache, lokale Output-Verzeichnisse).
    status = _git("status", "--porcelain", "--untracked-files=no")
    dirty = (status is not None) and (status != "")
    return {
        "branch": branch,
        "hash": hash_full,
        "hash_short": hash_short,
        "dirty": dirty,
    }


def _build_date() -> str:
    """Aktuelles Datum im ISO-Format YYYY-MM-DD."""
    return _dt.date.today().isoformat()


def get_version() -> str:
    """Liefert die vollständige Build-Versionsnummer.

    Format-Regeln:
        - Kein Git verfügbar:                        nur Basis-Version
        - Auf stable/X.Y-Branch UND clean:          nur Basis-Version
        - Sonst (Dev-Build oder dirty):              Basis + Hash + ggf. dirty + Build-Datum

    Beispiele:
        "0.1.0"                              Stable-Branch, sauber
        "0.0.1-gabc1234-2026-05-02"          Dev-Branch, sauber
        "0.0.1-dirty-2026-05-02"             lokale Änderungen ohne Hash
        "0.1.0-gabc1234-dirty-2026-05-02"    beides
    """
    base = get_base_version()
    meta = get_git_metadata()

    # Kein Git verfügbar → Basis + ggf. Public-ZIP-Build-Stamp aus VERSION
    if meta["hash"] is None:
        return base + get_local_version_stamp()

    branch = meta["branch"] or ""
    hash_short = meta["hash_short"] or ""
    dirty = meta["dirty"]

    # Auf einem Stable-Branch und nicht dirty → saubere Versionsnummer
    # ohne Suffix. Konvention: stable/0.1 = saubere 0.1.x-Linie.
    is_stable_branch = branch.startswith("stable/")
    if is_stable_branch and not dirty:
        return base

    # Sonst: Basis-Version + Hash + ggf. -dirty + Build-Datum
    parts = [base]
    if hash_short:
        parts.append(f"g{hash_short}")
    if dirty:
        parts.append("dirty")
    parts.append(_build_date())
    return "-".join(parts)


# Modul-Level-Konstante für einfachen Import
__version__ = get_version()
