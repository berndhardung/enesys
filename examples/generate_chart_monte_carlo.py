"""Generator wrapper: Monte-Carlo robustness from viz.charts.montecarlo.

Default: 3,000 samples, seed 42, all six paths. Rendering logic lives in
src/enesys/viz/charts/montecarlo.py.

Usage:
    python examples/generate_chart_monte_carlo.py
    python examples/generate_chart_monte_carlo.py --variant standalone --n-runs 5000

Available camps (parameter sets):
    neutral_default, ee_optimistic, atom_optimistic, bestand_optimistic
"""

import argparse
from pathlib import Path

from enesys.viz.charts.montecarlo import compute_monte_carlo_data, render_monte_carlo

DEFAULT_OUT_DIR = Path(__file__).parent
OUT_NAME = "monte_carlo"
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
    parser.add_argument(
        "--n-runs",
        type=int,
        default=500,
        help=(
            "Number of Monte-Carlo samples (default: 500 with 6-year-sample "
            "trapezoidal approximation; use 3000 for full resolution)."
        ),
    )
    parser.add_argument(
        "--n-year-samples",
        type=int,
        default=6,
        help=(
            "Year samples for the rolling-LCOE trapezoidal approximation per MC "
            "draw (default: 6; use 30 for exact rolling)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = compute_monte_carlo_data(
        n_runs=args.n_runs,
        n_year_samples=args.n_year_samples,
        seed=args.seed,
        camp=args.camp,
        param_set=args.param_set,
    )
    suffix = ".svg" if args.variant == "web" else ".png"
    key = args.param_set if args.param_set else args.camp
    out = args.out / f"{OUT_NAME}_{key}{suffix}"
    subtitle_set = f"Parameter set: {args.param_set}" if args.param_set else f"Camp: {args.camp}"
    render_monte_carlo(
        data,
        out,
        variant=args.variant,
        title="Monte-Carlo robustness: distribution across all paths",
        subtitle=(f"{data.n_runs} assumption draws · seed {data.seed} · {subtitle_set}"),
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
