"""Streamlit compare view: anchor camp vs. variant camp, full chart stack.

Layout
------
- Sidebar: language toggle, anchor-camp selectbox, variant-camp radio
  (with ``individuell``), slider panel.
- Main: title + sub-caption, then a 2-column layout that iterates the
  :data:`enesys.viz.charts.CHARTS` registry — left column renders the
  anchor camp, right column renders the variant camp (with overrides).
  Charts flagged ``varies_with_camp=False`` are rendered once full-width
  beneath the columns.

State
-----
Slider values live in ``st.session_state``. On every rerun the variant
sliders are diffed against the variant camp's defaults; non-empty diff
auto-switches the variant radio to ``individuell`` and the caption shows
the override list. Switching the variant radio explicitly back to a camp
resets the slider values to that camp's defaults.

Deep linking
------------
``?lang=``, ``?anchor=``, ``?variant=`` are read on first render and
written back when the sidebar state changes.
"""

from __future__ import annotations

import io
from typing import Any

import matplotlib.pyplot as plt
import streamlit as st

from enesys.ui.i18n import load_texts, render_sidebar_lang_toggle
from enesys.ui.slider_bridge import (
    GROUP_LABELS_DE,
    GROUP_LABELS_EN,
    LAGER_OPTIONS,
    SLIDER_SPEC,
    SliderSpec,
    build_overrides_from_sliders,
    get_camp_defaults,
    slider_groups,
)
from enesys.version import get_base_version
from enesys.viz.charts import CHARTS, CHARTS_BY_ID, ChartSpec

DEFAULT_ANCHOR_CAMP = "neutral_default"
DEFAULT_VARIANT_CAMP = "atom_optimistic"
INDIVIDUELL_KEY = "individuell"
MAX_OVERRIDES_INLINE = 3
QP_LANG = "lang"
QP_ANCHOR = "anchor"
QP_VARIANT = "variant"
QP_MOBILE = "mobile"
QP_CHART = "chart"
ALL_CHARTS_KEY = "__all__"  # sentinel: render the full chart stack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _camp_label(camp_id: str, lang: str) -> str:
    """Return the human-readable label for a camp id."""
    if camp_id == INDIVIDUELL_KEY:
        return "Individuell" if lang == "de" else "Custom"
    for cid, label_de, label_en, _desc in LAGER_OPTIONS:
        if cid == camp_id:
            return label_en if lang == "en" else label_de
    return camp_id


def _format_override_value(key: str, value: float, lang: str) -> str:
    spec = SLIDER_SPEC.get(key)
    fmt = spec.fmt if spec else "%.3f"
    label = (spec.label_en if lang == "en" else spec.label_de) if spec else key
    return f"{label} = {fmt % value}"


def _caption_for_variant(camp_id: str, overrides: dict[str, float], lang: str) -> str:
    """Build the caption that sits above the variant-side charts.

    Resolves ``individuell`` to ``"Individuell: <base camp>"`` using
    :data:`st.session_state.last_real_variant` so the reader still sees
    which camp the overrides were applied to.
    """
    if camp_id == INDIVIDUELL_KEY:
        base_camp = st.session_state.get("last_real_variant", camp_id)
        base_label = _camp_label(base_camp, lang)
        individuell_label = "Custom" if lang == "en" else "Individuell"
        base = f"{individuell_label}: {base_label}"
    else:
        base = _camp_label(camp_id, lang)

    if not overrides:
        return base
    if len(overrides) <= MAX_OVERRIDES_INLINE:
        parts = [_format_override_value(k, v, lang) for k, v in overrides.items()]
        return f"{base} + {', '.join(parts)}"
    n = len(overrides)
    suffix = f"{n} adjustments" if lang == "en" else f"{n} Anpassungen"
    return f"{base} + {suffix}"


# ---------------------------------------------------------------------------
# Caching layer
# ---------------------------------------------------------------------------


SCREEN_DPI = 110  # render once at screen DPI; book-quality stays in viz/charts

# Per-chart compute overrides for the on-screen render path. The Monte-Carlo
# chart is the single most expensive compute (~3.5 s at the 500-draw default);
# 300 draws keep the violins/win-probabilities visually stable while cutting
# ~40 % off the wall-clock. Book/export/test paths keep the full default —
# this only affects the Streamlit screen render.
_SCREEN_COMPUTE_KWARGS: dict[str, dict[str, int]] = {
    "montecarlo": {"n_runs": 300},
}


@st.cache_data(show_spinner=False)
def _cached_chart_data(
    chart_id: str,
    camp: str,
    overrides_items: tuple[tuple[str, float], ...],
) -> Any:
    """Memoised ``compute`` step — language- and variant-independent.

    Split out from the PNG cache so that switching language or toggling
    the mobile layout (both change only the render, not the model data)
    re-renders without re-running the expensive model computation. The
    cache key is ``(chart_id, camp, overrides)`` only.
    """
    spec = next(s for s in CHARTS if s.chart_id == chart_id)
    overrides = dict(overrides_items) if overrides_items else None
    return spec.compute(
        camp=camp, param_overrides=overrides, **_SCREEN_COMPUTE_KWARGS.get(chart_id, {})
    )


@st.cache_data(show_spinner=False, persist="disk")
def _cached_chart_png(
    chart_id: str,
    camp: str,
    overrides_items: tuple[tuple[str, float], ...],
    render_variant: str = "embedded",
    lang: str = "de",
) -> bytes:
    """Memoised pipeline ``compute -> render -> PNG bytes``.

    Caching the rendered PNG (not just the chart data) collapses the
    second visit to a chart into a dict lookup and an ``st.image`` call,
    skipping matplotlib entirely. The cache key is the chart id plus the
    camp/overrides/variant/lang tuple; ``st.cache_data`` invalidates on
    input change. The compute step is delegated to :func:`_cached_chart_data`
    so a language/variant switch reuses the already-computed model data.

    ``persist="disk"`` writes the rendered PNG to the deployment's cache
    directory, so a state computed once stays fast across reruns and
    process restarts within a deployment (recomputed only after a code
    redeploy or an explicit cache clear) — no prebuilt binaries in git.
    """
    spec = next(s for s in CHARTS if s.chart_id == chart_id)
    data = _cached_chart_data(chart_id, camp, overrides_items)
    fig = spec.render(data, return_fig=True, variant=render_variant, lang=lang)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=SCREEN_DPI, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _hashable_overrides(overrides: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted(overrides.items()))


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------


def _slider_key(param_key: str) -> str:
    return f"slider_{param_key}"


def _init_session_state(default_anchor: str, default_variant: str) -> None:
    """Seed the widget-backing session state on the very first render.

    Single source of truth per widget: ``anchor_select``, ``variant_radio``
    and ``slider_<param>``. All later mutations go through these keys
    directly so the widgets and the model agree on what is displayed.
    Existing slider values are clamped into the slider's range so a
    stale session value cannot raise ``StreamlitValueAboveMaxError``
    after a range tweak in :data:`SLIDER_SPEC`.
    """
    st.session_state.setdefault("anchor_select", default_anchor)
    st.session_state.setdefault("variant_radio", default_variant)
    st.session_state.setdefault("last_real_variant", default_variant)
    defaults = get_camp_defaults(default_variant)
    for key, spec in SLIDER_SPEC.items():
        widget_key = _slider_key(key)
        if widget_key not in st.session_state:
            st.session_state[widget_key] = _clamp(defaults.get(key, spec.lo), spec)
        else:
            st.session_state[widget_key] = _clamp(st.session_state[widget_key], spec)


def _clamp(value: float, spec: SliderSpec) -> float:
    return max(float(spec.lo), min(float(spec.hi), float(value)))


def _reset_sliders_to_camp(camp: str) -> None:
    """Snap all slider session-state values to the given camp's defaults.

    Values are clamped into each slider's range as a safety net. The
    range is auto-widened to cover all camp defaults (see
    :func:`slider_bridge._widen_specs_to_cover_camps`), so this is a
    no-op for camps — but it keeps a stale or hand-crafted session value
    from pushing the bound widget out of range.
    """
    defaults = get_camp_defaults(camp)
    for key, value in defaults.items():
        spec = SLIDER_SPEC.get(key)
        st.session_state[_slider_key(key)] = _clamp(value, spec) if spec else value


def _current_slider_values() -> dict[str, float]:
    return {key: float(st.session_state.get(_slider_key(key), 0.0)) for key in SLIDER_SPEC}


def _apply_pending_state_transitions() -> None:
    """Reconcile widget keys before any widget renders this run.

    Two transitions can happen between reruns:

    1. The radio was just toggled. If it landed on a real camp (not
       ``individuell``) we snap the sliders to that camp's defaults
       and remember the camp as the diff base.
    2. A slider was just moved. If the new slider state diverges from
       the diff-base camp's defaults we promote the radio to
       ``individuell`` (so the user sees the camp label catch up to
       their tweak).

    Doing this *before* rendering means the widgets read the post-
    transition values directly — no rerun ping-pong.
    """
    prev_camp = st.session_state.get("prev_variant_radio")
    current_camp = st.session_state.get("variant_radio")
    if current_camp != prev_camp:
        # Radio changed. If the user picked a camp, snap sliders.
        if current_camp != INDIVIDUELL_KEY:
            st.session_state.last_real_variant = current_camp
            _reset_sliders_to_camp(current_camp)
        st.session_state.prev_variant_radio = current_camp
        st.query_params[QP_VARIANT] = current_camp
        return

    # No camp change → check whether sliders drifted away from the
    # diff-base camp and the radio should catch up to ``individuell``.
    if current_camp == INDIVIDUELL_KEY:
        return
    diff_camp = st.session_state.get("last_real_variant", current_camp)
    overrides = build_overrides_from_sliders(_current_slider_values(), diff_camp)
    if overrides:
        st.session_state.variant_radio = INDIVIDUELL_KEY
        st.session_state.prev_variant_radio = INDIVIDUELL_KEY
        # Keep the language-keyed widget in sync with this programmatic
        # promotion (the widget key, once in session_state, takes precedence
        # over ``index=``, so the displayed marker would otherwise lag).
        wkey = st.session_state.get("_variant_widget_key")
        if wkey:
            st.session_state[wkey] = INDIVIDUELL_KEY
        st.query_params[QP_VARIANT] = INDIVIDUELL_KEY


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar(lang: str, texts: Any) -> tuple[str, str, dict[str, float], bool]:
    """Render the camp / slider sidebar and return the active state.

    The brand title and language toggle are rendered by
    :func:`render_sidebar_lang_toggle` before this function is called.
    """
    mobile_default = st.query_params.get(QP_MOBILE) == "1"
    mobile = st.sidebar.toggle(
        "📱 Mobile layout" if lang == "en" else "📱 Mobile-Layout",
        value=mobile_default,
        key="mobile_toggle",
        help=(
            "Render charts in a portrait, single-column layout with "
            "larger fonts (recommended on phones)."
            if lang == "en"
            else "Charts im einspaltigen Portrait-Layout mit größerer "
            "Schrift rendern (empfohlen auf dem Handy)."
        ),
    )
    new_qp = "1" if mobile else "0"
    if st.query_params.get(QP_MOBILE, "0") != new_qp:
        st.query_params[QP_MOBILE] = new_qp

    st.sidebar.divider()

    anchor_label = "Anker (links)" if lang == "de" else "Anchor (left)"
    variant_label = "Variante (rechts)" if lang == "de" else "Variant (right)"

    anchor_camps = [cid for cid, *_ in LAGER_OPTIONS]
    anchor_camp = st.sidebar.selectbox(
        anchor_label,
        options=anchor_camps,
        format_func=lambda cid: _camp_label(cid, lang),
        key="anchor_select",
    )
    st.query_params[QP_ANCHOR] = anchor_camp

    variant_options = anchor_camps + [INDIVIDUELL_KEY]
    # ``variant_radio`` stays the app-state slot the transition machine reads
    # and writes; the *widget* carries the language in its key so a language
    # switch remounts it fresh and honours ``index=`` (a fixed key would keep
    # the value but drop the visual marker after the option relabel). The
    # on-change callback mirrors the widget back into the app-state slot
    # before the next run's transition reconciliation reads it.
    vkey = f"variant_radio_widget_{lang}"
    st.session_state["_variant_widget_key"] = vkey

    def _sync_variant() -> None:
        st.session_state.variant_radio = st.session_state[vkey]

    # ``index=`` only on the fresh mount (key not yet in session_state) — on a
    # language switch that seeds the new widget from the app-state slot; on
    # steady-state reruns the widget value is authoritative, and omitting
    # ``index=`` avoids Streamlit's "default value with Session State" warning.
    variant_kwargs: dict[str, Any] = {}
    if vkey not in st.session_state:
        variant_kwargs["index"] = variant_options.index(st.session_state.variant_radio)
    variant_camp = st.sidebar.radio(
        variant_label,
        options=variant_options,
        format_func=lambda cid: _camp_label(cid, lang),
        key=vkey,
        on_change=_sync_variant,
        **variant_kwargs,
    )

    diff_camp = st.session_state.get("last_real_variant", variant_camp)
    _render_slider_panel(lang)
    overrides = build_overrides_from_sliders(_current_slider_values(), diff_camp)

    return anchor_camp, variant_camp, overrides, mobile


def _render_slider_panel(lang: str) -> None:
    """Render the per-group slider expanders."""
    group_labels = GROUP_LABELS_EN if lang == "en" else GROUP_LABELS_DE
    groups = slider_groups()

    # Top levers are always-visible (no expander).
    for key in groups["top"]:
        _slider_widget(key, SLIDER_SPEC[key], lang)

    for group in ("capex", "wacc", "fuel"):
        with st.sidebar.expander(group_labels[group], expanded=False):
            for key in groups[group]:
                _slider_widget(key, SLIDER_SPEC[key], lang)


def _slider_widget(key: str, spec: SliderSpec, lang: str) -> None:
    """Render a single slider with tooltip + source reference.

    The widget is bound to ``st.session_state[slider_<key>]`` via
    ``key=`` only — no ``value=`` argument, so Streamlit picks up
    programmatic state updates (camp-snap, deep-link init) on the
    very next render.
    """
    label = spec.label_en if lang == "en" else spec.label_de
    tooltip_text = spec.tooltip_en if lang == "en" else spec.tooltip_de
    source_label = "Source" if lang == "en" else "Quelle"
    # Description + source tag live in the native ``help`` tooltip — the most
    # compact affordance. The tag is plain text, NOT a markdown link: Streamlit
    # renders links inside hover tooltips but they are not clickable (the popover
    # dismisses before the anchor receives the click). The Sources page is
    # reachable via the top navigation; it auto-opens a tag with ``?tag=…``.
    help_md = f"{tooltip_text}\n\n📖 *{source_label}:* `{spec.source_tag}`"
    container = st.sidebar if spec.group == "top" else st
    container.slider(
        label,
        min_value=float(spec.lo),
        max_value=float(spec.hi),
        step=float(spec.step),
        format=spec.fmt,
        help=help_md,
        key=_slider_key(key),
    )


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------


def _render_chart_pair(
    spec: ChartSpec,
    anchor_camp: str,
    variant_camp: str,
    overrides: dict[str, float],
    lang: str,
    render_variant: str,
) -> None:
    """Render a single chart as two side-by-side figures."""
    title = spec.title_en if lang == "en" else spec.title_de
    st.subheader(title)
    col_a, col_b = st.columns(2)

    diff_camp = (
        st.session_state.last_real_variant if variant_camp == INDIVIDUELL_KEY else variant_camp
    )

    with col_a:
        st.caption(_camp_label(anchor_camp, lang))
        st.image(
            _cached_chart_png(spec.chart_id, anchor_camp, (), render_variant, lang),
            width="stretch",
        )

    with col_b:
        st.caption(_caption_for_variant(variant_camp, overrides, lang))
        st.image(
            _cached_chart_png(
                spec.chart_id, diff_camp, _hashable_overrides(overrides), render_variant, lang
            ),
            width="stretch",
        )


def _render_single_chart(spec: ChartSpec, lang: str, render_variant: str) -> None:
    """Render a chart that does not vary with camp (single column, full width)."""
    title = spec.title_en if lang == "en" else spec.title_de
    st.subheader(title)
    st.image(
        _cached_chart_png(spec.chart_id, "neutral_default", (), render_variant, lang),
        width="stretch",
    )


def _render_footer(lang: str, texts: Any) -> None:
    st.divider()
    legal_label = "Legal & disclaimer" if lang == "en" else "Rechtliches & Haftung"
    with st.expander(legal_label):
        st.markdown(texts.RECHTLICHES_HAFTUNG_EXPANDER)
    version = get_base_version()
    license_label = "MIT License" if lang == "en" else "MIT-Lizenz"
    st.caption(
        f"enesys · {version} · {license_label} · [GitHub](https://github.com/berndhardung/enesys)"
    )


def _render_chart_selector(lang: str) -> str:
    """Render the chart picker and return the selected ``chart_id``.

    Returns a single ``chart_id`` or :data:`ALL_CHARTS_KEY`. This is the
    core of the lazy-render path: only the selected chart is computed and
    drawn on a given rerun, so the first paint costs one chart instead of
    all six. The default lands on the first (cheapest) chart; ``Alle
    Charts`` restores the full stacked view on demand. The choice is
    mirrored to ``?chart=`` so it survives reload and is shareable.
    """
    options = [s.chart_id for s in CHARTS] + [ALL_CHARTS_KEY]
    all_label = "All charts" if lang == "en" else "Alle Charts"

    def _fmt(cid: str) -> str:
        if cid == ALL_CHARTS_KEY:
            return all_label
        spec = CHARTS_BY_ID[cid]
        return spec.title_en if lang == "en" else spec.title_de

    # The selection lives in an app-controlled slot (``active_chart``), not
    # the widget key. The widget key carries the language, so a language
    # switch remounts the radio as a fresh widget — Streamlit then honours
    # ``index=`` and re-marks the selection. Reusing a single fixed key would
    # keep the value but drop the visual marker after every option relabel.
    if "active_chart" not in st.session_state:
        qp = st.query_params.get(QP_CHART)
        st.session_state.active_chart = qp if qp in options else options[0]

    ckey = f"active_chart_widget_{lang}"
    chart_kwargs: dict[str, Any] = {}
    if ckey not in st.session_state:
        chart_kwargs["index"] = options.index(st.session_state.active_chart)
    selected = st.radio(
        "Chart",
        options=options,
        format_func=_fmt,
        horizontal=True,
        key=ckey,
        label_visibility="collapsed",
        **chart_kwargs,
    )
    st.session_state.active_chart = selected
    if st.query_params.get(QP_CHART) != selected:
        st.query_params[QP_CHART] = selected
    return selected


def render_path_page() -> None:
    """Render the compare view as a standalone Streamlit page.

    Entry symbol consumed by ``app/streamlit_app.py`` and by the
    multipage navigation. Calling this twice in one Streamlit run is
    safe — session state persists across reruns.
    """
    lang = render_sidebar_lang_toggle()
    texts = load_texts(lang)

    initial_anchor = st.query_params.get(QP_ANCHOR) or DEFAULT_ANCHOR_CAMP
    initial_variant = st.query_params.get(QP_VARIANT) or DEFAULT_VARIANT_CAMP
    if initial_anchor not in {c[0] for c in LAGER_OPTIONS}:
        initial_anchor = DEFAULT_ANCHOR_CAMP
    if initial_variant not in {c[0] for c in LAGER_OPTIONS} | {INDIVIDUELL_KEY}:
        initial_variant = DEFAULT_VARIANT_CAMP

    _init_session_state(initial_anchor, initial_variant)
    _apply_pending_state_transitions()

    anchor_camp, variant_camp, overrides, mobile = _render_sidebar(lang, texts)
    render_variant = "mobile" if mobile else "embedded"

    title = (
        "Architecture of Germany's power system — comparison"
        if lang == "en"
        else "Architektur des Energiesystems — Vergleich"
    )
    st.title(title)

    sub = (
        f"**Anchor** {_camp_label(anchor_camp, lang)}   ↔   "
        f"**Variant** {_caption_for_variant(variant_camp, overrides, lang)}"
    )
    st.markdown(sub)

    selected = _render_chart_selector(lang)
    specs = list(CHARTS) if selected == ALL_CHARTS_KEY else [CHARTS_BY_ID[selected]]
    for spec in specs:
        if spec.varies_with_camp:
            _render_chart_pair(spec, anchor_camp, variant_camp, overrides, lang, render_variant)
        else:
            _render_single_chart(spec, lang, render_variant)

    _render_footer(lang, texts)


__all__ = ["render_path_page"]
