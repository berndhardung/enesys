"""Generator wrapper: mix ramp-up grid from viz.charts.rampup.

Writes the chart as PNG (or SVG when ``--variant web``). The rendering
logic itself lives in src/enesys/viz/charts/rampup.py.

Usage:
    python examples/generate_chart_mix_rampup.py
    python examples/generate_chart_mix_rampup.py --variant standalone --camp ee_optimistic
    python examples/generate_chart_mix_rampup.py --out /tmp/charts
"""

import argparse
from pathlib import Path

from enesys.viz.charts.rampup import compute_mix_rampup_data, render_mix_rampup_grid

DEFAULT_OUT_DIR = Path(__file__).parent
OUT_NAME = "mix_rampup_grid"
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
        help="Camp / assumption preset for the data path (default: neutral_default)",
    )
    parser.add_argument(
        "--param-set",
        default=None,
        help=(
            "External assumption substrate (e.g. ariadne_pypsa). When set, "
            "overrides camp defaults per year."
        ),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = compute_mix_rampup_data(camp=args.camp, param_set=args.param_set)
    suffix = ".svg" if args.variant == "web" else ".png"
    key = args.param_set if args.param_set else data.camp
    out = args.out / f"{OUT_NAME}_{key}{suffix}"
    subtitle_set = f"Parameter set: {args.param_set}" if args.param_set else f"Camp: {data.camp}"
    render_mix_rampup_grid(
        data,
        out,
        variant=args.variant,
        title="Energy mix ramp-up 2026–2055",
        subtitle=f"Path grid · {subtitle_set}",
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
