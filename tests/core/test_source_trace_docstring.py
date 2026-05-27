"""Unit-Tests für die Docstring-Form von ``[SRC: TAG]``-Annotationen.

Stellt sicher, dass ``find_dataclass_defaults`` beide Annotation-Formen
akzeptiert:
1. Inline-Trailing-Kommentar: ``field: float = 1.0  # [SRC: TAG]``
2. Attribute-Docstring direkt unter dem Feld: ``field: float = 1.0\\n    \"\"\"... [SRC: TAG] ...\"\"\"``

Die Docstring-Form vermeidet monströse >150-Zeichen-Zeilen für Felder
mit langem Quellen-Tag oder mehrteiliger Begründung.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from enesys.core.source_trace import find_dataclass_defaults


@pytest.fixture
def synthetic_dataclass(tmp_path: Path) -> Path:
    """Schreibt eine synthetische Modell-Datei mit beiden Annotation-Formen."""
    path = tmp_path / "synthetic.py"
    path.write_text(
        '''"""Synthetic test module."""

from dataclasses import dataclass


@dataclass
class TestParams:
    inline_field: float = 1.0  # [SRC: TAG-INLINE]

    docstring_field: float = 2.0
    """Detaillierte Begründung in einem PEP-257-Attribute-Docstring,
    die ohne >150-Zeichen-Inline-Kommentar auskommt. [SRC: TAG-DOCSTRING]"""

    calibrated_docstring: float = 3.0
    """Modell-Setzung ohne externe Einzelquelle. [CALIBRATED: empirisch
    gemittelt aus mehreren Lit-Quellen]"""

    assumption_docstring: float = 4.0
    """[ASSUMPTION: Plausi-Setzung]"""

    no_annotation: float = 5.0
'''
    )
    return path


def test_inline_tag_recognized(synthetic_dataclass: Path) -> None:
    tags = find_dataclass_defaults(synthetic_dataclass)
    inline = next(t for t in tags if t.field == "inline_field")
    assert inline.tag == "TAG-INLINE"


def test_docstring_tag_recognized(synthetic_dataclass: Path) -> None:
    """SRC-Tag in einem Attribute-Docstring wird erkannt."""
    tags = find_dataclass_defaults(synthetic_dataclass)
    doc = next(t for t in tags if t.field == "docstring_field")
    assert doc.tag == "TAG-DOCSTRING"


def test_docstring_calibrated_recognized(synthetic_dataclass: Path) -> None:
    tags = find_dataclass_defaults(synthetic_dataclass)
    cal = next(t for t in tags if t.field == "calibrated_docstring")
    assert cal.is_calibrated is True
    assert cal.tag is None


def test_docstring_assumption_recognized(synthetic_dataclass: Path) -> None:
    tags = find_dataclass_defaults(synthetic_dataclass)
    ass = next(t for t in tags if t.field == "assumption_docstring")
    assert ass.is_assumption is True


def test_no_annotation_still_caught(synthetic_dataclass: Path) -> None:
    """Felder ohne Inline- *oder* Docstring-Annotation bleiben unerkannt."""
    tags = find_dataclass_defaults(synthetic_dataclass)
    none = next(t for t in tags if t.field == "no_annotation")
    assert none.tag is None
    assert not none.is_calibrated
    assert not none.is_assumption
    assert not none.is_model
