"""Versions-Single-Source-Gate: alle Version-Strings stimmen überein.

``VERSION``-Datei ist die Single Source of Truth (siehe
``src/enesys/version.py`` Docstring). Alle abgeleiteten Quellen müssen
identisch sein, damit kein Drift entsteht (PDFs / Briefings / Badges /
``pyproject.toml`` vs. ``VERSION``-Datei).

Geprüfte Quellen
----------------
- ``VERSION`` (Repo-Root)
- ``pyproject.toml`` ``version``-Feld (statisch oder dynamic-via-VERSION)
- ``CITATION.cff`` ``version:``-Eintrag
- ``CHANGELOG.md`` letzter ``## [X.Y.Z]``-Headline
- ``public/VERSION`` (falls vorhanden — Privat-Repo)
- ``public/pyproject.toml`` (falls vorhanden)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def _read_version_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _read_pyproject_version(path: Path) -> str:
    """Liest die Version aus pyproject.toml.

    Unterstützt beide Formen:
    - statisch: ``[project] version = "..."``
    - dynamisch: ``[project] dynamic = ["version"]`` mit
      ``[tool.setuptools.dynamic] version = { file = "VERSION" }``
      — in dem Fall wird die referenzierte Datei gelesen.
    """
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    project = data["project"]
    if "version" in project:
        return project["version"]
    if "version" in project.get("dynamic", []):
        dyn = data.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("version", {})
        version_file = dyn.get("file")
        if version_file:
            return _read_version_file(path.parent / version_file)
    raise KeyError(f"{path} hat weder project.version noch dynamic[version] mit file-Quelle")


_CITATION_VERSION_RE = re.compile(r'^version:\s*"?([^"\s]+)"?\s*$', re.MULTILINE)
_CHANGELOG_VERSION_RE = re.compile(r"^##\s+\[([^\]]+)\]", re.MULTILINE)


def _read_citation_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = _CITATION_VERSION_RE.search(text)
    if not m:
        raise ValueError(f"{path}: kein `version:`-Eintrag gefunden")
    return m.group(1).strip()


def _read_changelog_version(path: Path) -> str:
    """Liest die jüngste freigegebene Version aus CHANGELOG.md.

    Skippt den ``[Unreleased]``-Headline (Keep-a-Changelog-Konvention)
    und gibt den ersten konkreten Versions-Eintrag zurück.
    """
    text = path.read_text(encoding="utf-8")
    for match in _CHANGELOG_VERSION_RE.finditer(text):
        candidate = match.group(1).strip()
        if candidate.lower() == "unreleased":
            continue
        return candidate
    raise ValueError(f"{path}: keine freigegebene Versions-Headline gefunden")


def _gather_versions() -> dict[str, str]:
    """Sammelt alle Versions-Quellen, die im aktuellen Tree existieren."""
    versions: dict[str, str] = {}

    versions["VERSION"] = _read_version_file(REPO_ROOT / "VERSION")
    versions["pyproject.toml"] = _read_pyproject_version(REPO_ROOT / "pyproject.toml")
    versions["CITATION.cff"] = _read_citation_version(REPO_ROOT / "CITATION.cff")
    versions["CHANGELOG.md"] = _read_changelog_version(REPO_ROOT / "CHANGELOG.md")

    public_version = REPO_ROOT / "public" / "VERSION"
    public_pyproject = REPO_ROOT / "public" / "pyproject.toml"
    if public_version.exists():
        versions["public/VERSION"] = _read_version_file(public_version)
    if public_pyproject.exists():
        versions["public/pyproject.toml"] = _read_pyproject_version(public_pyproject)

    return versions


_PRERELEASE_SUFFIX_RE = re.compile(
    r"[-.]?(pre|dev|rc|a|b|alpha|beta)\d*$",
    re.IGNORECASE,
)
# PEP-440-local-Version (z.B. ``+2026-05-23.gb90cc91``) — wird vom
# Public-ZIP-Build an public/VERSION angehängt, damit der Snapshot-Stand
# auch ohne ``.git/`` nachvollziehbar bleibt. Siehe docs/VERSIONING.md.
_LOCAL_VERSION_RE = re.compile(r"\+[A-Za-z0-9._-]+$")


def _strip_local(v: str) -> str:
    return _LOCAL_VERSION_RE.sub("", v)


def _strip_prerelease(v: str) -> str:
    return _PRERELEASE_SUFFIX_RE.sub("", v)


def _normalize(v: str) -> str:
    """Strippt Local-Version (`+…`) und Pre-Release-Suffix (`-pre` etc.)."""
    return _strip_prerelease(_strip_local(v))


def test_all_version_strings_match() -> None:
    """Alle Versions-Quellen tragen dieselbe Basis-Version.

    Privat- und Public-Quellen dürfen einen Pre-Release-Suffix tragen
    (``-pre``, ``.dev0``, …); public/VERSION trägt zusätzlich einen
    PEP-440-Local-Build-Stamp (``+<date>.g<hash>``). Die Basis
    (Major.Minor.Patch) muss aber überall identisch sein.
    """
    versions = _gather_versions()
    bases = {src: _normalize(ver) for src, ver in versions.items()}
    unique = set(bases.values())
    assert len(unique) == 1, (
        f"Basis-Versions-Drift zwischen {len(versions)} Quellen — "
        f"erwartet identische Basis, gefunden:\n"
        + "\n".join(
            f"  {src:<28} = {ver!r} (Basis: {bases[src]!r})" for src, ver in versions.items()
        )
    )


def test_get_base_version_matches_file() -> None:
    """``enesys.version.get_base_version()`` liest die VERSION-Datei korrekt.

    Im Public-ZIP-Build trägt VERSION einen PEP-440-Local-Build-Stamp
    (``+<date>.g<hash>``), den ``get_base_version()`` strippt; der
    Vergleich läuft auf der Basis-Version ohne Local-Suffix.
    """
    from enesys.version import get_base_version

    expected = _strip_local(_read_version_file(REPO_ROOT / "VERSION"))
    actual = get_base_version()
    assert actual == expected, f"get_base_version() != VERSION-Datei: {actual!r} vs {expected!r}"
