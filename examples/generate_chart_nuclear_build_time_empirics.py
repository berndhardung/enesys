"""Generator wrapper: nuclear build-time empirics chart from viz.charts.build_time.

Writes the chart as PNG (or SVG when ``--variant web``). The rendering
logic itself lives in src/enesys/viz/charts/build_time.py.

Usage:
    python examples/generate_chart_nuclear_build_time_empirics.py
    python examples/generate_chart_nuclear_build_time_empirics.py --variant standalone
    python examples/generate_chart_nuclear_build_time_empirics.py --out /tmp/charts

Note: the build-time chart shows historical FOAK empirics (2005–2030) and is
not camp dependent. ``--camp`` is accepted for a consistent CLI surface
across all chart wrappers, but ignored.
"""

import argparse
from pathlib import Path

from enesys.viz.charts.build_time import compute_build_time_data, render_build_time_empirics

DEFAULT_OUT_DIR = Path(__file__).parent
OUT_NAME = "nuclear_build_time_empirics"
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
        help="Accepted for CLI consistency, but ignored (build time is historical).",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = compute_build_time_data()
    suffix = ".svg" if args.variant == "web" else ".png"
    out = args.out / (OUT_NAME + suffix)
    render_build_time_empirics(
        data,
        out,
        variant=args.variant,
        title="Western nuclear build-time empirics — FID lead time + construction",
        subtitle="FOAK reactors 2002–2030 · stacked: political decision → groundbreaking + groundbreaking → IBN",
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
