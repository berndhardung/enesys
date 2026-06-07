"""Streamlit Community Cloud entry point.

Streamlit Community Cloud expects a designated app file at
``app/streamlit_app.py``. This file configures the page and wires the
multi-page navigation (Landing / Compare / Sources). The page modules
themselves live in :mod:`enesys.ui.pages`.

Local development::

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="enesys — Architecture of Germany's power system",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from enesys.ui.pages.charts import render_charts_page  # noqa: E402
from enesys.ui.pages.landing import render_landing_page  # noqa: E402
from enesys.ui.pages.sources import render_sources_page  # noqa: E402

# Streamlit's navigation accepts a list of ``st.Page`` objects; the
# ``url_path`` keys are reflected in the ``?page=`` query parameter.
navigation = st.navigation(
    [
        st.Page(
            render_landing_page, title="Overview", icon="🏠", default=True, url_path="overview"
        ),
        st.Page(render_charts_page, title="Charts", icon="📊", url_path="charts"),
        st.Page(render_sources_page, title="Sources", icon="📚", url_path="sources"),
    ]
)
navigation.run()
