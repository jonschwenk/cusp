"""CLI entry point for the supported CUSP GEE feature sampler."""

from __future__ import annotations

import argparse

from .models import FeatureSamplingConfig
from .sampler import sample_features_from_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample supported GEE features for a CUSP table.")
    parser.add_argument("--input", required=True, help="Path to combined.csv, aggregated_30m.csv, or another point-like CUSP table.")
    parser.add_argument("--output", help="Output CSV for sampled features. Defaults next to the input.")
    parser.add_argument("--manifest", help="Optional JSON manifest path. Defaults next to the output.")
    parser.add_argument("--id-column", help="Override the canonical join column.")
    parser.add_argument(
        "--feature-set",
        default="base_v1",
        help="Named feature set to sample. Use 'none' to disable the default set. Default: base_v1",
    )
    parser.add_argument(
        "--features",
        help="Comma-separated additional feature keys. Example: slope,aspect",
    )
    parser.add_argument(
        "--sample-buffer-m",
        type=float,
        default=None,
        help="Optional sampling buffer in meters. Default is point sampling.",
    )
    parser.add_argument("--chunk-size", type=int, default=5000, help="Points per sampling chunk.")
    parser.add_argument("--climate-avg-years", type=int, default=20, help="Antecedent climate averaging window in years.")
    parser.add_argument("--curvature-window-sizes", default="3,5,7,9", help="Comma-separated odd window sizes for curvature.")
    parser.add_argument("--curvature-method", default="LoG", help="Curvature method. Supported: LoG, basic.")
    parser.add_argument("--curvature-sigma", type=float, default=1.0, help="Sigma for LoG curvature.")
    parser.add_argument("--gee-project", help="Optional Earth Engine project to initialize with.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed feature columns from an existing output CSV and continue sampling missing features.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    feature_keys = None
    if args.features:
        feature_keys = [key.strip() for key in args.features.split(",") if key.strip()]

    curvature_window_sizes = tuple(
        int(value.strip()) for value in args.curvature_window_sizes.split(",") if value.strip()
    )
    config = FeatureSamplingConfig(
        sample_buffer_m=args.sample_buffer_m,
        chunk_size=args.chunk_size,
        climate_avg_years=args.climate_avg_years,
        curvature_window_sizes=curvature_window_sizes,
        curvature_method=args.curvature_method,
        curvature_sigma=args.curvature_sigma,
    )

    sample_features_from_path(
        args.input,
        output_path=args.output,
        manifest_path=args.manifest,
        id_column=args.id_column,
        feature_keys=feature_keys,
        feature_set=args.feature_set,
        config=config,
        gee_project=args.gee_project,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
