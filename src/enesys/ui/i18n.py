"""i18n loader — selects the active text module from a language code.

The Streamlit UI reads ``?lang=`` from the URL query string and passes
the value here. ``load_texts(lang)`` returns the matching text module
(:mod:`texts_de` or :mod:`texts_en`); unknown codes fall back to German.
"""

from __future__ import annotations

from types import ModuleType
from typing import Literal

from enesys.ui import texts_de, texts_en

Lang = Literal["de", "en"]
DEFAULT_LANG: Lang = "de"
SUPPORTED_LANGS: tuple[Lang, ...] = ("de", "en")


def load_texts(lang: str | None) -> ModuleType:
    """Return the text module for ``lang``.

    Unknown or missing codes fall back to :data:`DEFAULT_LANG`. The
    returned module exposes the same public attributes as
    :mod:`texts_de` — switching languages is a single rebind.
    """
    if lang == "en":
        return texts_en
    return texts_de


def normalise_lang(lang: str | None) -> Lang:
    """Return ``lang`` if supported, otherwise :data:`DEFAULT_LANG`."""
    if lang in SUPPORTED_LANGS:
        return lang  # type: ignore[return-value]
    return DEFAULT_LANG


_APP_LANG_KEY = "app_lang"  # application-controlled, persists across page nav
_LANG_WIDGET_KEY = "sidebar_lang_widget"  # widget-controlled, may be cleared


def resolve_active_lang() -> Lang:
    """Return the active language for the current Streamlit session.

    Priority: :data:`_APP_LANG_KEY` in session_state (persists across
    page navigation — set explicitly by :func:`render_sidebar_lang_toggle`)
    → ``?lang=`` query parameter (deep-link / first visit) →
    :data:`DEFAULT_LANG`.
    """
    import streamlit as st  # noqa: PLC0415 — Streamlit is optional at import time

    cached = st.session_state.get(_APP_LANG_KEY)
    if cached in SUPPORTED_LANGS:
        return cached
    return normalise_lang(st.query_params.get("lang"))


def render_sidebar_lang_toggle() -> Lang:
    """Render the sidebar language toggle and return the active language.

    Two state slots are used:

    - ``app_lang`` is set explicitly and survives Streamlit's
      page-navigation reset (widget keys get garbage-collected when a
      widget is not rendered on the new page; explicit keys do not).
    - ``sidebar_lang_widget`` is the radio widget's own key. The
      ``on_change`` callback mirrors the widget's value back to
      ``app_lang`` and the ``?lang=`` URL parameter, so a user pick
      persists across navigation, browser reload (via URL), and refresh.

    The widget itself reads its initial value from ``app_lang`` via
    ``index=`` on each render, so even if Streamlit clears the widget
    state between pages the UI never snaps back to the default.
    """
    import streamlit as st  # noqa: PLC0415

    # First-visit seed: take the lang from URL or default.
    if _APP_LANG_KEY not in st.session_state:
        st.session_state[_APP_LANG_KEY] = normalise_lang(st.query_params.get("lang"))

    current = st.session_state[_APP_LANG_KEY]
    if current not in SUPPORTED_LANGS:
        current = DEFAULT_LANG
        st.session_state[_APP_LANG_KEY] = current

    def _on_change() -> None:
        chosen = st.session_state[_LANG_WIDGET_KEY]
        if chosen in SUPPORTED_LANGS:
            st.session_state[_APP_LANG_KEY] = chosen
            st.query_params["lang"] = chosen

    label = "🌐 Language" if current == "en" else "🌐 Sprache"
    st.sidebar.title("⚡ enesys")
    st.sidebar.radio(
        label,
        options=list(SUPPORTED_LANGS),
        index=SUPPORTED_LANGS.index(current),
        format_func=lambda code: "Deutsch" if code == "de" else "English",
        horizontal=True,
        key=_LANG_WIDGET_KEY,
        on_change=_on_change,
    )
    # Keep the URL in sync on first paint (e.g. fresh session loaded
    # via /charts with no ?lang= yet).
    if st.query_params.get("lang") != current:
        st.query_params["lang"] = current
    return current


__all__ = [
    "DEFAULT_LANG",
    "Lang",
    "SUPPORTED_LANGS",
    "load_texts",
    "normalise_lang",
    "resolve_active_lang",
]
