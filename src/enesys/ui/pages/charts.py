"""Charts page wrapper — delegates to ``streamlit_path.render_path_page``."""

from __future__ import annotations

from enesys.ui.streamlit_path import render_path_page


def render_charts_page() -> None:
    render_path_page()


__all__ = ["render_charts_page"]
