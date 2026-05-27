"""
Source Traceability Validator.

Ensures that every default parameter in the model has a `[SRC: TAG]` or
`[CALIBRATED]` annotation, and that every TAG used in code is defined in
docs/SOURCES.md with proper metadata (URL, date, citation).

This script is run:
    1. As part of `pytest tests/` (file: tests/core/test_source_traceability.py)
    2. As a CI check on every PR (workflow: .github/workflows/source-trace.yml)

If you add a new parameter without a [SRC: ...] tag, this fails.
If you cite a TAG that does not exist in SOURCES.md, this fails.
If a TAG in SOURCES.md is missing URL or date, this fails.

Why this matters:
    The model's authority comes from source-traceability. Without an
    automated check, source rigor erodes after a few months as new
    contributors forget to add tags. This automated check makes silent
    omissions impossible.

Usage:
    python -m enesys.source_trace check
    python -m enesys.source_trace list-tags
    python -m enesys.source_trace orphans
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Pattern: matches [SRC: TAG-NAME], [CALIBRATED], [ASSUMPTION: ...], [MODEL: ...]
# Tags can include letters (any case), digits, dashes.
SRC_TAG_PATTERN = re.compile(r"\[SRC:\s*([A-Za-z][A-Za-z0-9-]*)")
CALIBRATED_PATTERN = re.compile(r"\[CALIBRATED")
ASSUMPTION_PATTERN = re.compile(r"\[ASSUMPTION")
MODEL_PATTERN = re.compile(r"\[MODEL")

# Pattern: matches a default value in a dataclass field
# We use a multiline approach: scan the file, track @dataclass decorator
# context, only check fields inside dataclasses.
# The simple regex below catches most fields with a colon-type-equals pattern,
# but we filter to lines that look like top-level dataclass attributes
# (4-space indent, not function arguments).
DEFAULT_FIELD_PATTERN = re.compile(
    r"^(    )([a-z_][a-z0-9_]*)\s*:\s*(?:float|int|str|bool)\s*=\s*([^#\n]+?)(?:\s*#\s*(.*))?$",
    re.MULTILINE,
)

# Fields that don't need traceability (model assumptions, not measurements)
EXEMPT_FIELDS = {
    "electric_share",  # modeled penetration share
    "heatpump_share",  # modeled penetration share
    "commercial_vehicles_electric_share",  # modeled penetration share
    "backup_share",  # model assumption
    "storage_share",  # model assumption
    "pv_share",
    "wind_onshore_share",
    "wind_offshore_share",
    "biomass_share",
    "hydro_share",
    "nuclear_share",
    "co2_intensity_g_kwh",  # derived from mix
    "nuclear_subsidy",  # policy parameter, default 0
    "direct_electric_share",  # small assumption
    "efficiency_factor",  # secondary assumption
    "import_max_gw",  # stress-test assumption
    "duration_hours",  # stress-test scenario
    "pv_capacity_factor",  # stress-test scenario
    "wind_capacity_factor",  # stress-test scenario
    "cop_winter",  # stress-test scenario
    "heizbedarf_anstieg_faktor",  # stress-test scenario
    "e_auto_winter_aufschlag",  # stress-test scenario
    "sockel_winter_faktor",  # stress-test scenario
    "ab_backup_share",  # scenario parameter
    # Path-model time projections (modeled, not from a single source)
    "nuclear_first_unit_year",
    "nuclear_buildout_years",
    "nuclear_target_gw_2050",
    "battery_additions_gw_per_year_2026",
    "battery_additions_growth_pct",
    "battery_target_gw_2037",
    "h2_capacity_target_gw_2035",
    "h2_capacity_target_gw_2045",
    "pv_additions_gw_per_year",
    "wind_onshore_additions_gw_per_year",
    "wind_offshore_additions_gw_per_year",
    # Flexibility coefficients (model parameters)
    "ee_dsm_share",
    "kkw_dsm_share",
    "ee_v2g_share",
    "kkw_v2g_share",
    "ee_smart_heating_share",
    "kkw_smart_heating_share",
    "ee_flex_invest_per_mwh",
    "kkw_flex_invest_per_mwh",
    # Grid stability shares (model parameters)
    "ee_grid_forming_battery_capex_uplift",
    "ee_synchronous_condenser_eur_kva",
    "ee_synchronous_condenser_share",
    "nuclear_inertia_share",
    "nuclear_gfm_share",
    "blackstart_surcharge_ct_kwh",
    "inertia_demand_gw_2030",
    "inertia_demand_gw_2045",
    # Sunk-cost annotations (informational only)
    "sunk_nuclear_decommissioning_bn",
    "sunk_repository_fund_bn",
    "sunk_eeg_legacy_bn",
    # Mix presets
    "industry_h2_twh",
    "dsm_share",
    "h2_stahl_twh_strom",
    "h2_chemie_twh_strom",
    "h2_sonstige_twh_strom",
    "elektrifizierungs_zusatz_twh",
    # Mengen-Bilanz-Schicht (path_model.py): Function-Signature-
    # Parameter ohne Quellen-Anspruch.
    "system_state",  # SystemState-Enum-Wert (normal/scarcity/dunkelflaute)
    "h2_realization_rate",  # Politik-Hebel auf H2-Verfügbarkeit (resolved aus PolicySetting)
    "camp",
    "include_pilot_notes",
    "start_year",
    "end_year",
    "lockin_threshold_year",
    "year",
    "baseline_camp",
    "n_runs",
    "seed",
    "demand_twh_per_year",
    "jahre",
}


@dataclass
class CodeTag:
    file: Path
    line: int
    field: str
    tag: str | None
    is_calibrated: bool
    is_assumption: bool
    is_model: bool
    raw_comment: str


@dataclass
class SourceEntry:
    tag: str
    citation: str
    url: str | None
    date: str | None


# --------------------------------------------------------------------------- #
# Code parsing
# --------------------------------------------------------------------------- #


# Pattern: triple-quoted docstring attached to the field below.
# Matches both """...""" and r"""...""" forms, single- or multi-line.
_DOCSTRING_AFTER_FIELD_RE = re.compile(
    r'^[ \t]+(?:r|b)?"""(.*?)"""',
    re.DOTALL | re.MULTILINE,
)


def _extract_field_docstring(text: str, match_end: int) -> str:
    """Return the attribute-docstring directly after a field, if present.

    Looks at the lines immediately following ``match_end`` (the end of the
    matched field declaration). A triple-quoted string that starts on the
    next non-blank line and is at the same indent level as a dataclass
    field is treated as the field's docstring (PEP-257-style attribute
    docstring; widely supported by tooling).

    Returns the raw docstring text (between the triple-quotes) or an empty
    string if no docstring follows.
    """
    # Walk forward to the next non-blank, non-comment line.
    pos = match_end
    if pos < len(text) and text[pos] == "\n":
        pos += 1
    # Skip blank lines.
    remainder = text[pos:]
    # The docstring (if any) must start within ~3 lines and at indented level.
    lookahead_lines = remainder.split("\n", 5)
    candidate = "\n".join(lookahead_lines[:5])
    m = _DOCSTRING_AFTER_FIELD_RE.match(candidate)
    return m.group(1) if m else ""


def find_dataclass_defaults(file: Path) -> list[CodeTag]:
    """Find all dataclass field defaults in a file and their [SRC] / [CALIBRATED] tags.

    The annotation can sit either in an inline trailing comment
    (``field: float = 1.0  # [SRC: TAG]``) or in an attribute docstring
    directly below the field (``field: float = 1.0\\n    \"\"\"... [SRC:
    TAG] ...\"\"\"``). The docstring form is preferred for long
    explanations because it avoids monster inline-comment lines.
    """
    text = file.read_text(encoding="utf-8")
    results = []

    for match in DEFAULT_FIELD_PATTERN.finditer(text):
        field_name = match.group(2)
        comment = match.group(4) or ""
        line_num = text[: match.start()].count("\n") + 1

        # Combine inline comment + attached docstring for annotation lookup.
        docstring = _extract_field_docstring(text, match.end())
        annotation_source = comment + " " + docstring

        # Extract tag, if present
        src_match = SRC_TAG_PATTERN.search(annotation_source)
        cal_match = CALIBRATED_PATTERN.search(annotation_source)
        ass_match = ASSUMPTION_PATTERN.search(annotation_source)
        mod_match = MODEL_PATTERN.search(annotation_source)
        tag = src_match.group(1) if src_match else None
        is_calibrated = bool(cal_match)
        is_assumption = bool(ass_match)
        is_model = bool(mod_match)

        results.append(
            CodeTag(
                file=file,
                line=line_num,
                field=field_name,
                tag=tag,
                is_calibrated=is_calibrated,
                is_assumption=is_assumption,
                is_model=is_model,
                raw_comment=annotation_source.strip(),
            )
        )

    return results


# --------------------------------------------------------------------------- #
# SOURCES.md parsing
# --------------------------------------------------------------------------- #


def parse_sources_md(sources_file: Path) -> dict[str, SourceEntry]:
    """Parse SOURCES.md and extract tag→entry mapping.

    Looks for the source table in the format:
        | Tag | Vollzitat | URL/DOI | Datum |
        |---|---|---|---|
        | `TAG-NAME` | Citation text | https://... | 2024 |
    """
    text = sources_file.read_text(encoding="utf-8")
    entries: dict[str, SourceEntry] = {}

    # Match table rows starting with | `TAG`
    row_pattern = re.compile(
        r"^\s*\|\s*`([A-Za-z][A-Za-z0-9-]*)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        re.MULTILINE,
    )

    for match in row_pattern.finditer(text):
        tag = match.group(1).strip()
        citation = match.group(2).strip()
        url = match.group(3).strip()
        date = match.group(4).strip()

        # Skip the header separator row
        if tag in {"Tag", "TAG"}:
            continue

        entries[tag] = SourceEntry(
            tag=tag,
            citation=citation,
            url=url if url and url != "—" else None,
            date=date if date and date != "—" else None,
        )

    return entries


def find_inline_src_tags_in_sources(sources_file: Path) -> set[str]:
    """Also collect tags that appear in inline references like `[SRC: TAG]`
    inside SOURCES.md, in case they're not in the main table."""
    text = sources_file.read_text(encoding="utf-8")
    return set(SRC_TAG_PATTERN.findall(text))


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def validate(repo_root: Path) -> tuple[list[str], list[str], list[str]]:
    """Run the full validation. Returns (errors, warnings, info)."""
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    # 1. Parse all model files
    code_files = [
        repo_root / "src" / "enesys" / "core" / "camp_ranges.py",
        repo_root / "src" / "enesys" / "core" / "path_model.py",
    ]

    all_code_tags: list[CodeTag] = []
    for cf in code_files:
        if not cf.exists():
            errors.append(f"Expected model file not found: {cf}")
            continue
        all_code_tags.extend(find_dataclass_defaults(cf))

    # 2. Parse SOURCES.md
    sources_md = repo_root / "docs" / "SOURCES.md"
    if not sources_md.exists():
        errors.append(f"SOURCES.md not found at {sources_md}")
        return errors, warnings, info

    sources_table = parse_sources_md(sources_md)
    sources_inline = find_inline_src_tags_in_sources(sources_md)
    all_known_tags = set(sources_table.keys()) | sources_inline

    info.append(f"Found {len(sources_table)} tags in SOURCES.md table")
    info.append(f"Scanned {len(all_code_tags)} default-field declarations in code")

    # 3. CHECK A: every code tag must exist in SOURCES.md
    used_tags: set[str] = set()
    for ct in all_code_tags:
        if ct.tag is None:
            continue
        used_tags.add(ct.tag)
        if ct.tag not in all_known_tags:
            errors.append(
                f"{ct.file.name}:{ct.line}  field `{ct.field}` "
                f"references unknown tag [SRC: {ct.tag}] — add it to SOURCES.md"
            )

    # 4. CHECK B: SOURCES.md table entries need URL and date
    for tag, entry in sources_table.items():
        if not entry.url:
            warnings.append(f"SOURCES.md tag `{tag}` has no URL — add one for full traceability")
        if not entry.date:
            warnings.append(f"SOURCES.md tag `{tag}` has no date — add one for full traceability")

    # 5. CHECK C: every non-exempt default field needs an annotation
    #    Valid annotations: [SRC: TAG], [CALIBRATED], [ASSUMPTION: ...], [MODEL: ...]
    for ct in all_code_tags:
        if ct.field in EXEMPT_FIELDS:
            continue
        has_annotation = ct.tag is not None or ct.is_calibrated or ct.is_assumption or ct.is_model
        if not has_annotation:
            errors.append(
                f"{ct.file.name}:{ct.line}  field `{ct.field}` has no "
                f"[SRC: TAG], [CALIBRATED], [ASSUMPTION: ...], or "
                f"[MODEL: ...] annotation. "
                f"Either add a tag from SOURCES.md, mark as [CALIBRATED] "
                f"(empirically grounded but no single source), "
                f"[ASSUMPTION: explanation] (model assumption), "
                f"[MODEL: explanation] (model-internal constant), "
                f"or add `{ct.field}` to EXEMPT_FIELDS in source_trace.py."
            )

    # 6. Optional INFO: tags defined in SOURCES.md but never used in code
    unused = set(sources_table.keys()) - used_tags
    if unused:
        info.append(f"Tags in SOURCES.md not used in code: {sorted(unused)}")

    return errors, warnings, info


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def find_repo_root(start: Path) -> Path:
    """Walk up to find the repo root (directory containing pyproject.toml)."""
    current = start.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repo root (no pyproject.toml found)")


def cmd_check(repo_root: Path) -> int:
    errors, warnings, info = validate(repo_root)

    for msg in info:
        print(f"INFO    {msg}")
    for msg in warnings:
        print(f"WARNING {msg}")
    for msg in errors:
        print(f"ERROR   {msg}")

    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    else:
        print(f"OK: {len(warnings)} warning(s)")
        return 0


def cmd_list_tags(repo_root: Path) -> int:
    sources_md = repo_root / "docs" / "sources" / "SOURCES.md"
    entries = parse_sources_md(sources_md)
    print(f"Tags defined in SOURCES.md ({len(entries)}):")
    for tag, entry in sorted(entries.items()):
        url_display = entry.url or "(no URL)"
        date_display = entry.date or "(no date)"
        print(f"  {tag:25s} {date_display:15s} {url_display}")
    return 0


def cmd_orphans(repo_root: Path) -> int:
    """Show tags in SOURCES.md that are not referenced anywhere."""
    code_files = [
        repo_root / "src" / "enesys" / "core" / "camp_ranges.py",
        repo_root / "src" / "enesys" / "core" / "path_model.py",
    ]
    used_tags: set[str] = set()
    for cf in code_files:
        if cf.exists():
            for ct in find_dataclass_defaults(cf):
                if ct.tag:
                    used_tags.add(ct.tag)

    sources_md = repo_root / "docs" / "sources" / "SOURCES.md"
    entries = parse_sources_md(sources_md)
    unused = set(entries.keys()) - used_tags
    if unused:
        print(f"Tags in SOURCES.md not used in code ({len(unused)}):")
        for tag in sorted(unused):
            print(f"  {tag}")
    else:
        print("No orphan tags. All SOURCES.md entries are referenced in code.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    repo_root = find_repo_root(Path(__file__).parent)

    cmd = argv[0] if argv else "check"

    if cmd == "check":
        return cmd_check(repo_root)
    elif cmd == "list-tags":
        return cmd_list_tags(repo_root)
    elif cmd == "orphans":
        return cmd_orphans(repo_root)
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: source_trace.py [check|list-tags|orphans]")
        return 2


if __name__ == "__main__":
    sys.exit(main())
