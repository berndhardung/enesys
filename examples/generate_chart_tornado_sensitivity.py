"""Generator wrapper: tornado sensitivity from viz.charts.tornado.

Default paths: EE-GAS (robustness anchor) and KKW-GAS (camp challenger),
side by side. Rendering logic lives in src/enesys/viz/charts/tornado.py.

Usage:
    python examples/generate_chart_tornado_sensitivity.py
    python examples/generate_chart_tornado_sensitivity.py --variant standalone --camp ee_optimistic

Available camps (parameter sets):
    neutral_default, ee_optimistic, atom_optimistic, bestand_optimistic
"""

import argparse
from pathlib import Path

from enesys.viz.charts.tornado import compute_tornado_data, render_tornado_sensitivity

DEFAULT_OUT_DIR = Path(__file__).parent
OUT_NAME = "tornado_sensitivity"
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
        help="External assumption substrate (e.g. ariadne_pypsa).",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = compute_tornado_data(camp=args.camp, param_set=args.param_set)
    suffix = ".svg" if args.variant == "web" else ".png"
    key = args.param_set if args.param_set else data.camp
    out = args.out / f"{OUT_NAME}_{key}{suffix}"
    subtitle_set = f"Parameter set: {args.param_set}" if args.param_set else f"Camp: {data.camp}"
    render_tornado_sensitivity(
        data,
        out,
        variant=args.variant,
        title="Tornado sensitivity: which parameters move the result?",
        subtitle=f"EE-GAS vs. KKW-GAS · {subtitle_set}",
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
