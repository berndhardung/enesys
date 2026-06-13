"""Generator wrapper: LCOE trajectory chart from viz.charts.trajectory.

Writes the chart as PNG (or SVG when ``--variant web``). The rendering
logic itself lives in src/enesys/viz/charts/trajectory.py.

Usage:
    python examples/generate_chart_lcoe_trajectory.py
    python examples/generate_chart_lcoe_trajectory.py --variant standalone --camp ee_optimistic
    python examples/generate_chart_lcoe_trajectory.py --out /tmp/charts

Available camps (parameter sets):
    neutral_default, ee_optimistic, atom_optimistic, bestand_optimistic
"""

import argparse
from pathlib import Path

from enesys.viz.charts.trajectory import compute_trajectory_data, render_lcoe_trajectory

DEFAULT_OUT_DIR = Path(__file__).parent
OUT_NAME = "lcoe_trajectory"
VARIANTS = ("embedded", "epub", "standalone", "web")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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
        "--camp",
        default="neutral_default",
        help=(
            "Camp / assumption preset (default: neutral_default). "
            "Available: neutral_default, ee_optimistic, atom_optimistic, bestand_optimistic"
        ),
    )
    parser.add_argument(
        "--param-set",
        default=None,
        help=(
            "External assumption substrate from enesys.core.param_sets "
            "(e.g. ariadne_pypsa). When set, overrides camp defaults per year."
        ),
    )
    parser.add_argument(
        "--lang",
        choices=("de", "en"),
        default="en",
        help="Chart language for title, subtitle and in-figure labels (default: en)",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = compute_trajectory_data(camp=args.camp, param_set=args.param_set)
    suffix = ".svg" if args.variant == "web" else ".png"
    key = args.param_set if args.param_set else args.camp
    out = args.out / f"{OUT_NAME}_{key}_{args.lang}{suffix}"
    if args.param_set:
        set_label = (
            "Parameter set" if args.lang == "en" else "Parametersatz"
        ) + f": {args.param_set}"
    else:
        set_label = ("Camp" if args.lang == "en" else "Lager") + f": {args.camp}"
    title = {
        "en": f"Rolling 30-year LCOE per investment start year (2026–{2026 + 29})",
        "de": f"Rollierende 30-Jahres-LCOE je Investitions-Startjahr (2026–{2026 + 29})",
    }[args.lang]
    subtitle = {
        "en": f"Six paths · lifecycle LCOE + path spread · {set_label}",
        "de": f"Sechs Pfade · Lebenszyklus-LCOE + Pfad-Spannweite · {set_label}",
    }[args.lang]
    render_lcoe_trajectory(
        data,
        out,
        variant=args.variant,
        title=title,
        subtitle=subtitle,
        lang=args.lang,
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
