"""Sources page — every default in the model backed by a primary citation.

Parses ``docs/SOURCES.md`` for the top-level tag list, builds a reverse
index from each tag to the sliders that use it, and renders one
expander per tag. When ``?tag=XYZ`` is set the matching expander is
opened automatically so deep-links from slider tooltips land on the
right citation.

Each expander shows:

- the full bibliographic description from ``docs/SOURCES.md``,
- the list of sliders that pull their default from this source
  (reverse index built from :data:`enesys.ui.slider_bridge.SLIDER_SPEC`),
- any external URLs detected in the description, rendered as clickable
  links.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import streamlit as st

from enesys.ui.i18n import render_sidebar_lang_toggle
from enesys.ui.slider_bridge import SLIDER_SPEC
from enesys.version import get_base_version

QP_LANG = "lang"
QP_TAG = "tag"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SOURCES_PATH = _REPO_ROOT / "docs" / "SOURCES.md"
_TAG_LINE_RE = re.compile(r"^-\s+`([A-Z0-9][A-Z0-9_\-\.+:]*)`\s+(.+)$")
_TAG_TABLE_RE = re.compile(
    r"^\|\s*`([A-Z0-9][A-Z0-9_\-\.+:]*)`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$"
)
_URL_RE = re.compile(r"https?://[^\s)\]]+")


@lru_cache(maxsize=1)
def _load_tag_entries() -> tuple[tuple[str, str], ...]:
    """Parse the tag list from ``docs/SOURCES.md``.

    Recognises two formats: bullet entries (``- `TAG` description``) at
    the top of the file and the markdown source table further down
    (``| `TAG` | description | url | date |``). Returns an ordered
    tuple of ``(tag, description)`` pairs, the first occurrence wins.
    """
    if not _SOURCES_PATH.exists():
        return ()
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in _SOURCES_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        bullet = _TAG_LINE_RE.match(stripped)
        if bullet:
            tag, desc = bullet.group(1), bullet.group(2).strip()
        else:
            table = _TAG_TABLE_RE.match(stripped)
            if not table:
                continue
            tag = table.group(1)
            desc_text = table.group(2).strip()
            url = table.group(3).strip()
            date = table.group(4).strip()
            parts = [desc_text]
            if url and url != "—":
                parts.append(url)
            if date and date != "—":
                parts.append(f"({date})")
            desc = " · ".join(parts)
        if tag in seen:
            continue
        seen.add(tag)
        entries.append((tag, desc))
    return tuple(entries)


@lru_cache(maxsize=1)
def _reverse_index() -> dict[str, list[tuple[str, str, str]]]:
    """Return ``{source_tag: [(slider_key, label_de, label_en), ...]}``.

    A slider's ``source_tag`` may contain multiple tags separated by
    commas (e.g. ``"EDF-HPC, COURDESCOMPTES-FLAM"``); each is registered
    against its respective key.
    """
    index: dict[str, list[tuple[str, str, str]]] = {}
    for key, spec in SLIDER_SPEC.items():
        for raw in spec.source_tag.split(","):
            tag = raw.strip()
            if not tag:
                continue
            index.setdefault(tag, []).append((key, spec.label_de, spec.label_en))
    return index


def _summary_for_tag(tag: str, desc: str) -> str:
    """Trim the long bibliographic description down to a header summary."""
    head = desc.split(". ")[0].split(" — ")[0].split(";")[0]
    if len(head) > 110:
        head = head[:107].rstrip() + "…"
    return head


def _render_tag_block(
    tag: str,
    desc: str,
    expanded: bool,
    reverse_index: dict[str, list[tuple[str, str, str]]],
    lang: str,
) -> None:
    summary = _summary_for_tag(tag, desc)
    with st.expander(f"**`{tag}`** — {summary}", expanded=expanded):
        st.markdown(desc)

        # External links extracted from the description.
        urls = _URL_RE.findall(desc)
        if urls:
            label = "🔗 Links" if lang == "en" else "🔗 Links"
            st.markdown(f"**{label}**")
            for url in urls:
                st.markdown(f"- <{url}>")

        # Reverse index: which sliders pull from this tag.
        consumers = reverse_index.get(tag, [])
        if consumers:
            heading = "🎛️ Used by sliders" if lang == "en" else "🎛️ Verwendet von Slidern"
            st.markdown(f"**{heading}**")
            for _key, label_de, label_en in consumers:
                label = label_en if lang == "en" else label_de
                st.markdown(f"- {label}")
        else:
            note = (
                "_Not currently bound to a UI slider — referenced in the model defaults._"
                if lang == "en"
                else "_Aktuell an keinen UI-Slider gebunden — wird nur in den Modell-Defaults referenziert._"
            )
            st.markdown(note)


def render_sources_page() -> None:
    """Render the sources page (entry symbol consumed by st.navigation)."""
    lang = render_sidebar_lang_toggle()

    title = "📚 Sources" if lang == "en" else "📚 Quellen"
    st.title(title)

    intro = (
        "Every default value in the model is backed by a primary source. "
        "Slider tooltips link here; the focused tag opens automatically. "
        "Each entry lists the sliders that pull their default from this "
        "source and any external links to the original publication."
        if lang == "en"
        else "Jeder Default-Wert im Modell ist mit einer Primärquelle "
        "belegt. Slider-Tooltips verlinken hierher; der fokussierte "
        "Tag öffnet sich automatisch. Jeder Eintrag zeigt die Slider, "
        "die ihre Vorbelegung aus dieser Quelle ziehen, plus externe "
        "Links zur Originalpublikation."
    )
    st.markdown(intro)

    entries = _load_tag_entries()
    if not entries:
        st.warning(
            "docs/SOURCES.md not found in this deployment."
            if lang == "en"
            else "docs/SOURCES.md ist in diesem Deployment nicht verfügbar."
        )
        return

    reverse = _reverse_index()
    bound_count = sum(1 for tag, _ in entries if reverse.get(tag))
    caption = (
        f"{len(entries)} source tags · {bound_count} bound to UI sliders."
        if lang == "en"
        else f"{len(entries)} Quellen-Tags · {bound_count} an UI-Slider gebunden."
    )
    st.caption(caption)

    focus_tag = st.query_params.get(QP_TAG)
    search_label = "🔍 Filter tags" if lang == "en" else "🔍 Tag-Filter"
    query = st.text_input(search_label, value="", key="sources_filter")

    show_only_bound = st.checkbox(
        "Show only sources used in the UI"
        if lang == "en"
        else "Nur Quellen mit Slider-Bindung anzeigen",
        value=False,
        key="sources_only_bound",
    )

    for tag, desc in entries:
        if show_only_bound and not reverse.get(tag):
            continue
        if query and query.upper() not in tag.upper() and query.lower() not in desc.lower():
            continue
        expanded = bool(focus_tag) and focus_tag.upper() == tag.upper()
        _render_tag_block(tag, desc, expanded, reverse, lang)

    st.divider()
    full_label = (
        "Open the full SOURCES.md (per-parameter documentation)"
        if lang == "en"
        else "Vollständige SOURCES.md öffnen (pro-Parameter-Dokumentation)"
    )
    with st.expander(full_label):
        if _SOURCES_PATH.exists():
            st.markdown(_SOURCES_PATH.read_text(encoding="utf-8"))

    license_label = "MIT License" if lang == "en" else "MIT-Lizenz"
    st.caption(
        f"enesys · {get_base_version()} · {license_label} · "
        f"[GitHub](https://github.com/berndhardung/enesys)"
    )


__all__ = ["render_sources_page"]
