"""Generator wrapper: stress-test ramp-up grid from viz.charts.stress.

Writes the chart as PNG (or SVG when ``--variant web``). The rendering
logic itself lives in src/enesys/viz/charts/stress.py.

Usage:
    python examples/generate_chart_stress_rampup.py
    python examples/generate_chart_stress_rampup.py --variant standalone --camp ee_optimistic
    python examples/generate_chart_stress_rampup.py --out /tmp/charts
"""

import argparse
from pathlib import Path

from enesys.viz.charts.stress import compute_stress_rampup_data, render_stress_rampup_grid

DEFAULT_OUT_DIR = Path(__file__).parent
OUT_NAME = "stress_rampup_grid"
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
        help="External assumption substrate (e.g. ariadne_pypsa).",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = compute_stress_rampup_data(camp=args.camp, param_set=args.param_set)
    suffix = ".svg" if args.variant == "web" else ".png"
    key = args.param_set if args.param_set else data.camp
    out = args.out / f"{OUT_NAME}_{key}{suffix}"
    subtitle_set = f"Parameter set: {args.param_set}" if args.param_set else f"Camp: {data.camp}"
    render_stress_rampup_grid(
        data,
        out,
        variant=args.variant,
        title="Stress-test ramp-up 2026–2055 — LOLE-P95 design standard",
        subtitle=f"LOLE-P95 dark-doldrum reserve per path (BMWK reliability 2.77 h/a) · {subtitle_set}",
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
