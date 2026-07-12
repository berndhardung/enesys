"""Generator wrapper: path×camp cost matrix from viz.charts.regret_matrix.

A condensed decision view: six policy paths (rows) against the four camp
worlds (columns). The cell shows full-system LCOE, the cell colour encodes
regret (green = robust, yellow-red = expensive-if-wrong), and the bars on the
right show the maximum regret per path. Rendering logic lives in
src/enesys/viz/charts/regret_matrix.py.

A comparable horizon pair (--horizon), identical methodology, only the horizon
differs — so the two images can be read side by side:
  today    — 2026-2055.
  children — 2055-2084 steady state, the bill the next generation inherits
             (the full nuclear fleet's capex finally loads per kWh).
Both use full-system LCOE (electricity + the cost of the fossil heat/mobility a
path does not electrify), benchmark = cheapest of all six, all six full members.

Unlike the other gallery charts this one is a *cross-camp synthesis*: it
shows all four camps at once, so there is one image per horizon and language
(no per-camp fan-out, hence --camp/--param-set are accepted but ignored).

Usage:
    python examples/generate_chart_regret_matrix.py            # both horizons
    python examples/generate_chart_regret_matrix.py --horizon children --lang de
    python examples/generate_chart_regret_matrix.py --variant web
"""

import argparse
from pathlib import Path

from enesys.viz.charts.regret_matrix import (
    compute_fullsystem_matrix_data,
    render_regret_matrix,
)

DEFAULT_OUT_DIR = Path(__file__).parent
VARIANTS = ("embedded", "epub", "standalone", "web")

# horizon -> (start_year, output basename)
_HORIZONS = {
    "today": (2026, "regret_matrix"),
    "children": (2055, "regret_matrix_intergenerational"),
}

_TITLE = {
    "today": {
        "en": "Cost and cost of being wrong, by path",
        "de": "Kosten und Kosten des Irrtums je Pfad",
    },
    "children": {
        "en": "Cost of being wrong — the bill we hand our children",
        "de": "Kosten des Irrtums — die Rechnung, die unsere Kinder erben",
    },
}
_SUBTITLE = {
    "today": {
        "en": "Full energy system, 2026-2055 · benchmark = cheapest of all six paths",
        "de": "Voll-System, 2026-2055 · Benchmark = günstigster von allen sechs Pfaden",
    },
    "children": {
        "en": (
            "Full energy system, steady state 2055-2084, full nuclear fleet · "
            "benchmark = cheapest of all six paths"
        ),
        "de": (
            "Voll-System, Steady-State 2055-2084, KKW-Flotte voll am Netz · "
            "Benchmark = günstigster von allen sechs Pfaden"
        ),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--horizon",
        choices=("today", "children", "both"),
        default="both",
        help="both (default, comparable pair, shared bar scale), today, or children",
    )
    parser.add_argument(
        "--variant",
        choices=VARIANTS,
        default="standalone",
        help="Rendering variant (default: standalone — standalone image with title)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--lang",
        choices=("de", "en"),
        default="en",
        help="Chart language for title, subtitle and in-figure labels (default: en)",
    )
    parser.add_argument(
        "--cell-value",
        choices=("lcoe", "regret"),
        default="lcoe",
        help="Number shown in each cell (default: lcoe); colour always encodes regret.",
    )
    # --camp / --param-set are accepted but ignored: this chart is a cross-camp
    # synthesis (all four camps are the columns), so it has no per-camp variant.
    # The flags exist only for consistency with the Makefile chart loop.
    parser.add_argument("--camp", default="neutral_default", help=argparse.SUPPRESS)
    parser.add_argument("--param-set", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    horizons = ("today", "children") if args.horizon == "both" else (args.horizon,)
    data = {h: compute_fullsystem_matrix_data(_HORIZONS[h][0]) for h in horizons}
    # Shared bar axis across the pair so bar lengths are directly comparable.
    bar_xmax = (
        max(v for d in data.values() for v in d.maxreg_eur_yr.values())
        if args.horizon == "both"
        else None
    )

    suffix = ".svg" if args.variant == "web" else ".png"
    for h in horizons:
        out = args.out / f"{_HORIZONS[h][1]}_{args.lang}{suffix}"
        render_regret_matrix(
            data[h],
            out,
            variant=args.variant,
            title=_TITLE[h][args.lang],
            subtitle=_SUBTITLE[h][args.lang],
            lang=args.lang,
            cell_value=args.cell_value,
            bar_xmax=bar_xmax,
        )
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
