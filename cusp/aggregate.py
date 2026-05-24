"""Build the release-facing 30 m aggregated CUSP artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from cusp.build import DATA_DIR, display_path, sha256_file


DEFAULT_CANONICAL_INPUT = DATA_DIR / "cusp_observations.csv"
DEFAULT_AGGREGATED_OUTPUT = DATA_DIR / "aggregated_30m.csv"
DEFAULT_MEMBERSHIP_OUTPUT = DATA_DIR / "aggregated_30m_membership.csv"
DEFAULT_FLAGS_OUTPUT = DATA_DIR / "aggregated_30m_qc_flags.csv"
DEFAULT_EXCLUDED_OUTPUT = DATA_DIR / "aggregated_30m_excluded_rows.csv"
DEFAULT_GPKG_OUTPUT = DATA_DIR / "aggregated_30m.gpkg"
DEFAULT_GPKG_LAYER = "aggregated_30m"
DEFAULT_MANIFEST_OUTPUT = DATA_DIR / "aggregated_30m_manifest.json"

DEFAULT_DISTANCE_M = 30.0
DEFAULT_TEMPORAL_LINK_DAYS = 31
DEFAULT_PROJECTED_CRS = "EPSG:3413"

REQUIRED_INPUT_COLUMNS = [
    "cusp_obs_id",
    "source",
    "site_id",
    "lat",
    "lon",
    "date",
    "pf_observed",
    "thaw_depth",
    "pf_depth",
    "obs_limit",
    "method",
    "quality_flags",
]

AGGREGATED_COLUMNS = [
    "cusp_30m_id",
    "year",
    "date",
    "lat",
    "lon",
    "pf_observed",
    "thaw_depth",
    "pf_depth",
    "obs_limit",
    "method",
    "quality_flags",
    "aggregated_sources",
    "n_grouped",
]


@dataclass(frozen=True)
class AggregationOutputs:
    aggregated: pd.DataFrame
    membership: pd.DataFrame
    qc_flags: pd.DataFrame
    excluded_rows: pd.DataFrame
    aggregated_gdf: gpd.GeoDataFrame


def stable_scalar_string(value: object) -> str:
    """Serialize a scalar into a deterministic string for IDs/details."""

    if pd.isna(value):
        return ""
    if isinstance(value, (float, np.floating)):
        return format(float(value), ".12g")
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def load_canonical_observations(path: Path = DEFAULT_CANONICAL_INPUT) -> pd.DataFrame:
    """Load the canonical observation-level table used for supported aggregation."""

    df = pd.read_csv(path, low_memory=False)
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise RuntimeError(
            "The canonical observation table is missing required aggregation columns: "
            f"{missing}. Re-run `python -m cusp.build` first."
        )

    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="raise")
    return df


def assign_spatial_cells(
    df: pd.DataFrame,
    distance_m: float = DEFAULT_DISTANCE_M,
    projected_crs: str = DEFAULT_PROJECTED_CRS,
) -> pd.DataFrame:
    """Assign deterministic 30 m grid cells in projected coordinates."""

    working = df.copy()
    working["date"] = pd.to_datetime(working["date"], format="mixed", errors="raise")

    gdf = gpd.GeoDataFrame(
        working,
        geometry=gpd.points_from_xy(working["lon"], working["lat"]),
        crs="EPSG:4326",
    ).to_crs(projected_crs)
    gdf["_x_m"] = gdf.geometry.x
    gdf["_y_m"] = gdf.geometry.y
    gdf["_cell_x"] = np.floor(gdf["_x_m"] / distance_m).astype("int64")
    gdf["_cell_y"] = np.floor(gdf["_y_m"] / distance_m).astype("int64")
    gdf["year"] = gdf["date"].dt.year.astype("int64")
    return pd.DataFrame(gdf.drop(columns="geometry"))


def assign_temporal_groups(
    df: pd.DataFrame,
    temporal_link_days: int = DEFAULT_TEMPORAL_LINK_DAYS,
) -> pd.DataFrame:
    """Split each spatial cell-year group into temporal linkage groups."""

    group_cols = ["_cell_x", "_cell_y", "year"]
    working = df.copy().sort_values(group_cols + ["date", "cusp_obs_id"], kind="mergesort").reset_index(drop=True)
    working["_date_gap_days"] = (
        working.groupby(group_cols, sort=True)["date"].diff().dt.total_seconds().div(86400.0)
    )
    working["_temporal_break"] = working["_date_gap_days"].gt(temporal_link_days).fillna(False)
    working["_time_group"] = working.groupby(group_cols, sort=True)["_temporal_break"].cumsum().astype("int64")
    return working


def build_cusp_30m_id(member_obs_ids: list[str]) -> str:
    """Build a deterministic aggregation ID from the sorted member observation IDs."""

    payload = "|".join(sorted(member_obs_ids))
    return f"agg30m_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def median_or_nan(values: pd.Series) -> float:
    """Return a median while preserving NaN for fully missing groups."""

    non_null = values.dropna()
    if non_null.empty:
        return np.nan
    return float(non_null.median())


def max_or_nan(values: pd.Series) -> float:
    """Return a max while preserving NaN for fully missing groups."""

    non_null = values.dropna()
    if non_null.empty:
        return np.nan
    return float(non_null.max())


def build_qc_flag_rows(group: pd.DataFrame, cusp_30m_id: str, pf_mean: float) -> list[dict[str, object]]:
    """Build long-form QC flags for one aggregated group."""

    flags: list[dict[str, object]] = []
    methods = sorted(stable_scalar_string(value) for value in group["method"].dropna().unique())
    sources = sorted(stable_scalar_string(value) for value in group["source"].dropna().unique())
    pf_unique = sorted(stable_scalar_string(value) for value in group["pf_observed"].dropna().unique())
    if len(pf_unique) > 1:
        flags.append(
            {
                "cusp_30m_id": cusp_30m_id,
                "flag": "mixed_pf_observed",
                "detail": stable_scalar_string(pf_mean),
            }
        )
    if len(methods) > 1:
        flags.append(
            {
                "cusp_30m_id": cusp_30m_id,
                "flag": "mixed_method",
                "detail": ",".join(methods),
            }
        )
    if len(sources) > 1:
        flags.append(
            {
                "cusp_30m_id": cusp_30m_id,
                "flag": "mixed_source",
                "detail": ",".join(sources),
            }
        )
    unique_dates = sorted(group["date"].dropna().astype(str).unique())
    if len(unique_dates) > 1:
        flags.append(
            {
                "cusp_30m_id": cusp_30m_id,
                "flag": "multi_date_window",
                "detail": f"{unique_dates[0]}..{unique_dates[-1]}",
            }
        )

    return flags


def aggregate_groups(retained: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aggregate temporally linked 30 m groups into canonical rows."""

    group_cols = ["_cell_x", "_cell_y", "year", "_time_group"]
    aggregated_rows: list[dict[str, object]] = []
    membership_rows: list[dict[str, object]] = []
    qc_flag_rows: list[dict[str, object]] = []

    for _, group in retained.groupby(group_cols, sort=True, dropna=False):
        member_obs_ids = group["cusp_obs_id"].astype(str).tolist()
        cusp_30m_id = build_cusp_30m_id(member_obs_ids)

        pf_mean = float(group["pf_observed"].astype(float).mean())
        method_values = sorted(stable_scalar_string(value) for value in group["method"].dropna().unique())
        method = method_values[0] if len(method_values) == 1 else "mixed"
        quality_flags = sorted(
            {
                flag
                for value in group["quality_flags"].dropna().astype(str)
                for flag in value.split(";")
                if flag
            }
        )
        aggregated_sources = ",".join(sorted(stable_scalar_string(value) for value in group["source"].dropna().unique()))

        aggregated_rows.append(
            {
                "cusp_30m_id": cusp_30m_id,
                "year": int(group["year"].iloc[0]),
                "date": max(group["date"].astype(str)),
                "lat": float(group["lat"].mean()),
                "lon": float(group["lon"].mean()),
                "pf_observed": pf_mean,
                "thaw_depth": median_or_nan(group["thaw_depth"]),
                "pf_depth": median_or_nan(group["pf_depth"]),
                "obs_limit": max_or_nan(group["obs_limit"]),
                "method": method,
                "quality_flags": ";".join(quality_flags),
                "aggregated_sources": aggregated_sources,
                "n_grouped": int(len(group)),
            }
        )

        membership_rows.extend(
            {
                "cusp_30m_id": cusp_30m_id,
                "cusp_obs_id": obs_id,
            }
            for obs_id in sorted(member_obs_ids)
        )
        qc_flag_rows.extend(build_qc_flag_rows(group, cusp_30m_id=cusp_30m_id, pf_mean=pf_mean))

    aggregated = pd.DataFrame.from_records(aggregated_rows, columns=AGGREGATED_COLUMNS)
    if not aggregated.empty:
        aggregated = aggregated.sort_values(
            ["year", "date", "lat", "lon", "cusp_30m_id"],
            kind="mergesort",
            na_position="last",
        ).reset_index(drop=True)

    membership = pd.DataFrame.from_records(membership_rows, columns=["cusp_30m_id", "cusp_obs_id"])
    if not membership.empty:
        membership = membership.sort_values(["cusp_30m_id", "cusp_obs_id"], kind="mergesort").reset_index(drop=True)

    qc_flags = pd.DataFrame.from_records(qc_flag_rows, columns=["cusp_30m_id", "flag", "detail"])
    if not qc_flags.empty:
        qc_flags = qc_flags.sort_values(["flag", "cusp_30m_id", "detail"], kind="mergesort").reset_index(drop=True)

    return aggregated, membership, qc_flags


def build_aggregated_gdf(aggregated: pd.DataFrame) -> gpd.GeoDataFrame:
    """Build the geospatial export for the 30 m aggregation."""

    return gpd.GeoDataFrame(
        aggregated.copy(),
        geometry=gpd.points_from_xy(aggregated["lon"], aggregated["lat"]),
        crs="EPSG:4326",
    )


def build_aggregation_tables(
    canonical: pd.DataFrame,
    distance_m: float = DEFAULT_DISTANCE_M,
    temporal_link_days: int = DEFAULT_TEMPORAL_LINK_DAYS,
) -> AggregationOutputs:
    """Build the canonical 30 m aggregation tables from the observation release."""

    with_cells = assign_spatial_cells(canonical, distance_m=distance_m)
    retained = assign_temporal_groups(with_cells, temporal_link_days=temporal_link_days)
    aggregated, membership, qc_flags = aggregate_groups(retained)
    aggregated_gdf = build_aggregated_gdf(aggregated)

    excluded = pd.DataFrame(
        columns=[
            "cusp_obs_id",
            "source",
            "site_id",
            "lat",
            "lon",
            "date",
            "year",
            "exclusion_reason",
            "window_start_date",
            "latest_group_date",
        ]
    )

    return AggregationOutputs(
        aggregated=aggregated,
        membership=membership,
        qc_flags=qc_flags,
        excluded_rows=excluded,
        aggregated_gdf=aggregated_gdf,
    )


def build_aggregation_manifest(
    outputs: AggregationOutputs,
    aggregated_path: Path,
    membership_path: Path,
    flags_path: Path,
    excluded_path: Path,
    gpkg_path: Path,
    distance_m: float,
    temporal_link_days: int,
) -> dict[str, object]:
    """Build a JSON-serializable manifest for the 30 m aggregation artifacts."""

    artifact_specs = [
        ("aggregated_30m.csv", aggregated_path, outputs.aggregated),
        ("aggregated_30m_membership.csv", membership_path, outputs.membership),
        ("aggregated_30m_qc_flags.csv", flags_path, outputs.qc_flags),
        ("aggregated_30m_excluded_rows.csv", excluded_path, outputs.excluded_rows),
        ("aggregated_30m.gpkg", gpkg_path, outputs.aggregated_gdf),
    ]

    artifacts: dict[str, dict[str, object]] = {}
    for artifact_name, path, frame in artifact_specs:
        artifacts[artifact_name] = {
            "path": display_path(path),
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "size_bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        }

    summary = {
        "aggregated_rows": int(len(outputs.aggregated)),
        "membership_rows": int(len(outputs.membership)),
        "excluded_rows": int(len(outputs.excluded_rows)),
        "qc_flag_rows": int(len(outputs.qc_flags)),
        "year_min": int(outputs.aggregated["year"].min()) if not outputs.aggregated.empty else None,
        "year_max": int(outputs.aggregated["year"].max()) if not outputs.aggregated.empty else None,
        "pf_observed_min": float(outputs.aggregated["pf_observed"].min()) if not outputs.aggregated.empty else None,
        "pf_observed_max": float(outputs.aggregated["pf_observed"].max()) if not outputs.aggregated.empty else None,
    }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_scope": "aggregated_30m_release",
        "aggregation_parameters": {
            "distance_m": distance_m,
            "temporal_link_days": temporal_link_days,
            "temporal_window_total_days": temporal_link_days * 2,
            "projected_crs": DEFAULT_PROJECTED_CRS,
        },
        "summary": summary,
        "artifacts": artifacts,
    }


def write_aggregation_outputs(
    outputs: AggregationOutputs,
    aggregated_path: Path = DEFAULT_AGGREGATED_OUTPUT,
    membership_path: Path = DEFAULT_MEMBERSHIP_OUTPUT,
    flags_path: Path = DEFAULT_FLAGS_OUTPUT,
    excluded_path: Path = DEFAULT_EXCLUDED_OUTPUT,
    gpkg_path: Path = DEFAULT_GPKG_OUTPUT,
    gpkg_layer: str = DEFAULT_GPKG_LAYER,
    manifest_path: Path = DEFAULT_MANIFEST_OUTPUT,
    distance_m: float = DEFAULT_DISTANCE_M,
    temporal_link_days: int = DEFAULT_TEMPORAL_LINK_DAYS,
) -> None:
    """Write the supported 30 m aggregation artifacts to disk."""

    for path in [
        aggregated_path,
        membership_path,
        flags_path,
        excluded_path,
        gpkg_path,
        manifest_path,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)

    outputs.aggregated.to_csv(aggregated_path, index=False)
    outputs.membership.to_csv(membership_path, index=False)
    outputs.qc_flags.to_csv(flags_path, index=False)
    outputs.excluded_rows.to_csv(excluded_path, index=False)
    outputs.aggregated_gdf.to_file(gpkg_path, layer=gpkg_layer, driver="GPKG")

    manifest = build_aggregation_manifest(
        outputs,
        aggregated_path=aggregated_path,
        membership_path=membership_path,
        flags_path=flags_path,
        excluded_path=excluded_path,
        gpkg_path=gpkg_path,
        distance_m=distance_m,
        temporal_link_days=temporal_link_days,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the supported aggregation build."""

    parser = argparse.ArgumentParser(description="Build the release-facing 30 m CUSP aggregation bundle.")
    parser.add_argument("--input", type=Path, default=DEFAULT_CANONICAL_INPUT, help="Canonical observation table to aggregate.")
    parser.add_argument("--output", type=Path, default=DEFAULT_AGGREGATED_OUTPUT)
    parser.add_argument("--membership-output", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    parser.add_argument("--flags-output", type=Path, default=DEFAULT_FLAGS_OUTPUT)
    parser.add_argument("--excluded-output", type=Path, default=DEFAULT_EXCLUDED_OUTPUT)
    parser.add_argument("--gpkg-output", type=Path, default=DEFAULT_GPKG_OUTPUT)
    parser.add_argument("--gpkg-layer", default=DEFAULT_GPKG_LAYER)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    parser.add_argument("--distance-m", type=float, default=DEFAULT_DISTANCE_M)
    parser.add_argument("--temporal-link-days", type=int, default=DEFAULT_TEMPORAL_LINK_DAYS)
    return parser.parse_args()


def main() -> None:
    """Build the supported 30 m aggregated release artifacts."""

    args = parse_args()
    canonical = load_canonical_observations(args.input)
    outputs = build_aggregation_tables(
        canonical,
        distance_m=args.distance_m,
        temporal_link_days=args.temporal_link_days,
    )
    write_aggregation_outputs(
        outputs,
        aggregated_path=args.output,
        membership_path=args.membership_output,
        flags_path=args.flags_output,
        excluded_path=args.excluded_output,
        gpkg_path=args.gpkg_output,
        gpkg_layer=args.gpkg_layer,
        manifest_path=args.manifest_output,
        distance_m=args.distance_m,
        temporal_link_days=args.temporal_link_days,
    )


if __name__ == "__main__":
    main()
