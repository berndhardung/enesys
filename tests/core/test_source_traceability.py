"""
Source Traceability Test.

Runs the source-trace validator as part of the standard pytest suite.
Fails if any default parameter is missing a [SRC: TAG] or [CALIBRATED]
annotation, or if any TAG is referenced that is not in SOURCES.md.

This is the same validator that runs in CI on every PR.
"""

from pathlib import Path

import pytest

from enesys.core.source_trace import find_repo_root, validate


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return find_repo_root(Path(__file__).parent)


def test_no_unannotated_defaults(repo_root: Path) -> None:
    """Every default parameter must have [SRC: TAG] or [CALIBRATED] annotation."""
    errors, _, _ = validate(repo_root)

    annotation_errors = [e for e in errors if "no [SRC: TAG]" in e]
    assert not annotation_errors, (
        "Found default parameters without source annotation:\n"
        + "\n".join(annotation_errors)
        + "\n\nFix: Add [SRC: TAG] (referencing a tag in SOURCES.md) "
        "or [CALIBRATED] (for pure model assumptions) as inline comment."
    )


def test_all_tags_resolve(repo_root: Path) -> None:
    """Every [SRC: TAG] used in code must be defined in SOURCES.md."""
    errors, _, _ = validate(repo_root)

    unknown_tag_errors = [e for e in errors if "unknown tag" in e]
    assert not unknown_tag_errors, (
        "Found [SRC: TAG] references that are not in SOURCES.md:\n"
        + "\n".join(unknown_tag_errors)
        + "\n\nFix: Add the missing tag to docs/SOURCES.md with full "
        "citation, URL, and date. This failure is expected when a "
        "parameter update introduces a new source — adding the tag "
        "alongside the value change is the normal flow, not a bug."
    )


def test_validator_runs_clean(repo_root: Path) -> None:
    """Full validator run with zero errors. (Warnings are OK but logged.)"""
    errors, warnings, info = validate(repo_root)

    if warnings:
        print("\nWarnings (non-fatal):")
        for w in warnings:
            print(f"  {w}")

    assert not errors, (
        f"Source-traceability validation failed with {len(errors)} error(s):\n" + "\n".join(errors)
    )
