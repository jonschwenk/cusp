"""Build the release-facing CUSP observation-level artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_integer_dtype

from cusp.data_utils import _ROOT_DIR


DATA_DIR = _ROOT_DIR / "data"
DEFAULT_SKIPPED_SOURCES = [
    "CALM",
    "Brown_etal_2000_calm",
    "Wilcox_2015",
    "Yi_etal_2020_ABoVE",
    "Beer_etal_2013",
    "Sadeghi_etal_2023",
]
REQUIRED_SOURCE_COLUMNS = [
    "lon",
    "lat",
    "date",
    "source",
    "site_id",
    "pf_observed",
    "pf_depth",
    "thaw_depth",
    "obs_limit",
]
OPTIONAL_RELEASE_COLUMNS = ["method"]


CANONICAL_COLUMNS = [
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
]
OBS_ID_COMPONENT_COLUMNS = [column for column in CANONICAL_COLUMNS if column != "cusp_obs_id"]
INTERNAL_BUILD_COLUMNS = {"_build_row_number", "build_action", "build_reason"}
ALLOWED_METHODS = {"gp", "tp", "pit", "aug", "pit_aug", "tp_pit", "tt", "temp", "unknown"}
METHOD_NORMALIZATION_MAP = {
    "Frost Probe Transect or Grid": "tp",
    "Frost Probe Transect or Grid & Borehole": "tp_pit",
    "Thaw Tube": "tt",
    "tp/pit": "tp_pit",
    "aug_pit": "pit_aug",
}

DEFAULT_CANONICAL_OUTPUT = DATA_DIR / "cusp_observations.csv"
DEFAULT_ALLFIELDS_OUTPUT = DATA_DIR / "cusp_observations_allfields.csv"
DEFAULT_METADATA_OUTPUT = DATA_DIR / "cusp_observations_metadata.csv"
DEFAULT_DELETED_OUTPUT = DATA_DIR / "cusp_observations_deleted_rows.csv"
DEFAULT_FLAGS_OUTPUT = DATA_DIR / "cusp_observations_qc_flags.csv"
DEFAULT_SOURCE_REFERENCE_OUTPUT = DATA_DIR / "source_reference_crosswalk.csv"
DEFAULT_BIBTEX_OUTPUT = DATA_DIR / "cusp_sources_bibtex.csv"
DEFAULT_MANIFEST_OUTPUT = DATA_DIR / "observation_release_manifest.json"


@dataclass(frozen=True)
class BuildOutputs:
    observations: pd.DataFrame
    observations_allfields: pd.DataFrame
    observations_metadata: pd.DataFrame
    deleted_rows: pd.DataFrame
    qc_flags: pd.DataFrame
    source_reference_crosswalk: pd.DataFrame

    @property
    def combined(self) -> pd.DataFrame:
        """Compatibility alias for the canonical observation table."""

        return self.observations

    @property
    def combined_allfields(self) -> pd.DataFrame:
        """Compatibility alias for the all-fields observation table."""

        return self.observations_allfields

    @property
    def combined_md(self) -> pd.DataFrame:
        """Compatibility alias for the observation source metadata table."""

        return self.observations_metadata


def display_path(path: Path) -> str:
    """Return a stable human-readable path for manifests."""

    try:
        return str(path.relative_to(_ROOT_DIR))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file on disk."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_scalar_string(value: object) -> str:
    """Serialize a scalar into a deterministic string for ID generation."""

    if pd.isna(value):
        return ""
    if isinstance(value, (float, np.floating)):
        return format(float(value), ".12g")
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def build_cusp_obs_id(df: pd.DataFrame) -> pd.Series:
    """Build deterministic observation IDs from the canonical non-ID fields."""

    serialized = df.loc[:, OBS_ID_COMPONENT_COLUMNS].apply(
        lambda row: "|".join(stable_scalar_string(row[column]) for column in OBS_ID_COMPONENT_COLUMNS),
        axis=1,
    )
    return serialized.map(lambda value: f"obs_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}")


def list_available_sources(data_dir: Path = DATA_DIR) -> list[str]:
    """Return source directories in a deterministic order."""

    return sorted(path.name for path in data_dir.iterdir() if path.is_dir())


def list_included_sources(
    data_dir: Path = DATA_DIR,
    skipped_sources: list[str] | None = None,
) -> list[str]:
    """Return source directories that are currently part of the observation release."""

    skipped = set(skipped_sources or DEFAULT_SKIPPED_SOURCES)
    return [source for source in list_available_sources(data_dir) if source not in skipped]


def ensure_release_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add any expected-but-optional release columns that are missing."""

    for column in OPTIONAL_RELEASE_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    return df


def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce the standard numeric columns where possible."""

    for column in ["lon", "lat", "pf_depth", "thaw_depth", "obs_limit"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def normalize_dates(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Normalize mixed-format date columns to `YYYY-MM-DD`."""

    dates = pd.to_datetime(
        df["date"],
        format="mixed",
        dayfirst=False,
        errors="coerce",
        cache=False,
    )
    if dates.isna().any():
        bad_examples = df.loc[dates.isna(), "date"].head(10).tolist()
        raise ValueError(
            f"{source}: couldn't parse some dates in 'date' column. "
            f"First examples: {bad_examples}"
        )

    df["date"] = dates.dt.strftime("%Y-%m-%d")
    return df


def validate_data_df(df: pd.DataFrame, source: str) -> None:
    """Perform basic checks before a source is assimilated."""

    missing = [column for column in REQUIRED_SOURCE_COLUMNS if column not in df.columns]
    if missing:
        raise RuntimeError(f"{source} csv is missing the following required columns: {missing}")

    if not is_integer_dtype(df["pf_observed"]):
        raise RuntimeError(f"{source} csv pf_observed column is not integer type.")

    lon = df["lon"].dropna()
    lat = df["lat"].dropna()
    if not lon.empty and (lon.max() > 180 or lon.min() < -180):
        raise RuntimeError(f"{source} has longitude problems.")
    if not lat.empty and (lat.max() > 90 or lat.min() < -90):
        raise RuntimeError(f"{source} has latitude problems.")


def haversine(lats: list[float] | np.ndarray, lons: list[float] | np.ndarray) -> np.ndarray:
    """Compute distances in meters between coordinate pairs."""

    radius = 6372.8 * 1000
    dlat = np.radians(np.diff(lats))
    dlon = np.radians(np.diff(lons))
    lat1 = np.radians(lats[:-1])
    lat2 = np.radians(lats[1:])

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return radius * c


def boundbox_area(df: pd.DataFrame) -> float:
    """Approximate the area in square km of the minimum bounding box around the points."""

    working = df.dropna(subset=["lat", "lon"])
    if working.empty:
        return np.nan

    lat_max = working["lat"].max()
    lat_min = working["lat"].min()
    lon_max = working["lon"].max()
    lon_min = working["lon"].min()

    lat_dist = haversine([lat_min, lat_max], [lon_min, lon_min])[0] / 1000
    lon_dist = haversine([lat_min, lat_min], [lon_min, lon_max])[0] / 1000
    return lat_dist * lon_dist


def build_metastats(df: pd.DataFrame, source: str) -> dict[str, object]:
    """Build the current compact per-source summary table."""

    return {
        "source": source,
        "N_pf_Y": int(np.sum(df["pf_observed"] == 1)),
        "N_pf_N": int(np.sum(df["pf_observed"] == 0)),
        "N_pf": int(np.sum(df["pf_observed"] == 1) + np.sum(df["pf_observed"] == 0)),
        "bb_area_km2": boundbox_area(df),
        "N_alt": int(np.sum(df["pf_depth"] > 0)),
    }


def load_processed_source(
    source: str,
    data_dir: Path = DATA_DIR,
) -> pd.DataFrame:
    """Load a processed source table and coerce its core fields."""

    datapath = data_dir / source / f"processed_{source.lower()}.csv"
    this_df = pd.read_csv(datapath, low_memory=False)
    this_df = ensure_release_columns(this_df)
    this_df = coerce_numeric_columns(this_df)
    this_df["source"] = source
    this_df["pf_observed"] = pd.to_numeric(this_df["pf_observed"], errors="raise").astype("Int64")
    this_df = normalize_dates(this_df, source)
    validate_data_df(this_df, source)
    return this_df


def combine_sources(
    sources: list[str] | None = None,
    data_dir: Path = DATA_DIR,
) -> pd.DataFrame:
    """Combine all included processed sources into a single all-fields table."""

    selected_sources = sources or list_included_sources(data_dir)
    observation_frames: list[pd.DataFrame] = []

    for source in selected_sources:
        observation_frames.append(load_processed_source(source, data_dir=data_dir))

    observations = pd.concat(observation_frames, ignore_index=True) if observation_frames else pd.DataFrame()
    sort_cols = [column for column in ["source", "site_id", "date", "lat", "lon", "method"] if column in observations.columns]
    if sort_cols:
        observations = observations.sort_values(sort_cols, kind="mergesort", na_position="last").reset_index(drop=True)
    return observations


def normalize_method(value: object) -> object:
    """Normalize method values to the controlled release vocabulary where possible."""

    if pd.isna(value):
        return pd.NA

    method = str(value).strip()
    if not method:
        return pd.NA

    if method in METHOD_NORMALIZATION_MAP:
        return METHOD_NORMALIZATION_MAP[method]

    method = method.lower().replace("/", "_").replace(" ", "_")
    if method in {"aug_pit", "pit_aug"}:
        return "pit_aug"
    if method in {"tp_pit", "pit_tp"}:
        return "tp_pit"
    if method == "thaw_tube":
        return "tt"
    if method == "frost_probe_transect_or_grid":
        return "tp"
    if method == "frost_probe_transect_or_grid_&_borehole":
        return "tp_pit"
    return method


def normalize_methods(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize the observation method column in-place-friendly form."""

    df = df.copy()
    if "method" not in df.columns:
        df["method"] = pd.NA
    df["method"] = df["method"].map(normalize_method)
    return df


def stable_allfields_column_order(df: pd.DataFrame) -> list[str]:
    """Return a deterministic column order with canonical fields first."""

    extras = sorted(
        column
        for column in df.columns
        if column not in CANONICAL_COLUMNS and column not in INTERNAL_BUILD_COLUMNS
    )
    return [column for column in CANONICAL_COLUMNS if column in df.columns] + extras


def _make_action_frame(df: pd.DataFrame, mask: pd.Series, action: str, reason: str) -> pd.DataFrame:
    if not mask.any():
        return pd.DataFrame(columns=list(df.columns) + ["build_action", "build_reason"])
    action_df = df.loc[mask].copy()
    action_df["build_action"] = action
    action_df["build_reason"] = reason
    return action_df


def apply_hard_deletions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Delete rows that are clearly invalid for the release-facing observation table."""

    working = df.copy()
    deleted_frames: list[pd.DataFrame] = []

    def drop_mask(mask: pd.Series, reason: str) -> None:
        nonlocal working
        deleted = _make_action_frame(working, mask, "deleted", reason)
        if not deleted.empty:
            deleted_frames.append(deleted)
            working = working.loc[~mask].copy()

    drop_mask(working["source"].isna(), "missing_source")
    drop_mask(working["date"].isna(), "missing_date")
    drop_mask(working["pf_observed"].isna(), "missing_pf_observed")
    drop_mask(working["lat"].isna() | working["lon"].isna(), "missing_coordinates")
    drop_mask((working["lat"] == 0) & (working["lon"] == 0), "zero_zero_coordinates")
    drop_mask((working["lat"] > 90) | (working["lat"] < -90) | (working["lon"] > 180) | (working["lon"] < -180), "coordinate_out_of_range")

    duplicate_mask = working.duplicated(subset=OBS_ID_COMPONENT_COLUMNS, keep="first")
    drop_mask(duplicate_mask, "duplicate_required_fields")

    deleted_rows = (
        pd.concat(deleted_frames, ignore_index=True)
        if deleted_frames
        else pd.DataFrame(columns=list(df.columns) + ["build_action", "build_reason"])
    )
    return working, deleted_rows


def build_qc_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Collect non-deletion QC flags for the cleaned observation table."""

    flag_frames = [
        _make_action_frame(df, df["method"].isna(), "flagged", "missing_method"),
        _make_action_frame(df, df["obs_limit"] == 0, "flagged", "zero_obs_limit"),
    ]

    noncanonical_method_mask = df["method"].notna() & ~df["method"].isin(ALLOWED_METHODS)
    flag_frames.append(_make_action_frame(df, noncanonical_method_mask, "flagged", "noncanonical_method"))

    qc_flags = pd.concat(flag_frames, ignore_index=True)
    if qc_flags.empty:
        return qc_flags

    qc_flags = qc_flags.sort_values(
        ["build_reason", "source", "site_id", "date", "lat", "lon"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)
    return qc_flags


def build_release_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Build the compact source summary from the cleaned all-fields table."""

    records = [build_metastats(source_df, source) for source, source_df in df.groupby("source", dropna=False, sort=True)]
    if not records:
        return pd.DataFrame(columns=["source", "N_pf_Y", "N_pf_N", "N_pf", "bb_area_km2", "N_alt"])
    return pd.DataFrame.from_records(records).sort_values("source", kind="mergesort").reset_index(drop=True)


def build_source_reference_crosswalk(
    observations_metadata: pd.DataFrame,
    bibtex_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build a one-row-per-source crosswalk between included sources and citation metadata."""

    observation_sources = observations_metadata[["source"]].drop_duplicates().copy()
    bib_subset = bibtex_df.copy()
    bib_subset = bib_subset[bib_subset["source"].isin(observation_sources["source"])].copy()
    bib_subset = bib_subset.sort_values("source", kind="mergesort").drop_duplicates(subset=["source"], keep="first")

    crosswalk = observation_sources.merge(bib_subset, on="source", how="left", validate="one_to_one")
    citation_columns = [column for column in bib_subset.columns if column != "source"]
    crosswalk = crosswalk[["source"] + citation_columns]
    return crosswalk.sort_values("source", kind="mergesort").reset_index(drop=True)


def build_release_manifest(
    outputs: BuildOutputs,
    canonical_path: Path,
    allfields_path: Path,
    metadata_path: Path,
    deleted_path: Path,
    flags_path: Path,
    source_reference_path: Path,
) -> dict[str, object]:
    """Build a JSON-serializable release manifest for the observation artifacts."""

    generation_time = datetime.now(timezone.utc).isoformat()
    observations = outputs.observations

    artifact_specs = [
        ("cusp_observations.csv", canonical_path, outputs.observations),
        ("cusp_observations_allfields.csv", allfields_path, outputs.observations_allfields),
        ("cusp_observations_metadata.csv", metadata_path, outputs.observations_metadata),
        ("cusp_observations_deleted_rows.csv", deleted_path, outputs.deleted_rows),
        ("cusp_observations_qc_flags.csv", flags_path, outputs.qc_flags),
        ("source_reference_crosswalk.csv", source_reference_path, outputs.source_reference_crosswalk),
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

    manifest = {
        "generated_at_utc": generation_time,
        "build_scope": "observation_release",
        "artifacts": artifacts,
        "summary": {
            "observation_rows": int(len(observations)),
            "observation_sources": int(observations["source"].nunique()),
            "date_min": str(observations["date"].min()),
            "date_max": str(observations["date"].max()),
        },
    }
    return manifest


def build_release_tables(raw_allfields: pd.DataFrame) -> BuildOutputs:
    """Convert the raw all-fields observation output into release-facing tables."""

    working = raw_allfields.copy()
    working = normalize_methods(working)
    working["_build_row_number"] = range(len(working))

    working, deleted_rows = apply_hard_deletions(working)

    sort_cols = [column for column in OBS_ID_COMPONENT_COLUMNS if column in working.columns]
    working = working.sort_values(sort_cols, kind="mergesort", na_position="last").reset_index(drop=True)
    working["cusp_obs_id"] = build_cusp_obs_id(working)
    qc_flags = build_qc_flags(working)
    canonical = working.loc[:, CANONICAL_COLUMNS].copy()

    allfields_columns = stable_allfields_column_order(working)
    observations_allfields = working.loc[:, allfields_columns].copy()
    observations_metadata = build_release_metadata(observations_allfields)
    bibtex_df = pd.read_csv(DEFAULT_BIBTEX_OUTPUT, low_memory=False)
    source_reference_crosswalk = build_source_reference_crosswalk(observations_metadata, bibtex_df)

    if not deleted_rows.empty:
        deleted_rows = deleted_rows.loc[
            :,
            ["_build_row_number"] + stable_allfields_column_order(deleted_rows) + ["build_action", "build_reason"],
        ]
    if not qc_flags.empty:
        qc_flags = qc_flags.loc[
            :,
            ["_build_row_number"] + stable_allfields_column_order(qc_flags) + ["build_action", "build_reason"],
        ]

    return BuildOutputs(
        observations=canonical,
        observations_allfields=observations_allfields,
        observations_metadata=observations_metadata,
        deleted_rows=deleted_rows,
        qc_flags=qc_flags,
        source_reference_crosswalk=source_reference_crosswalk,
    )


def write_build_outputs(
    outputs: BuildOutputs,
    canonical_path: Path = DEFAULT_CANONICAL_OUTPUT,
    allfields_path: Path = DEFAULT_ALLFIELDS_OUTPUT,
    metadata_path: Path = DEFAULT_METADATA_OUTPUT,
    deleted_path: Path = DEFAULT_DELETED_OUTPUT,
    flags_path: Path = DEFAULT_FLAGS_OUTPUT,
    source_reference_path: Path = DEFAULT_SOURCE_REFERENCE_OUTPUT,
    manifest_path: Path = DEFAULT_MANIFEST_OUTPUT,
) -> None:
    """Write the release-facing build outputs to disk."""

    for path in [
        canonical_path,
        allfields_path,
        metadata_path,
        deleted_path,
        flags_path,
        source_reference_path,
        manifest_path,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)

    outputs.observations.to_csv(canonical_path, index=False)
    outputs.observations_allfields.to_csv(allfields_path, index=False)
    outputs.observations_metadata.to_csv(metadata_path, index=False)
    outputs.deleted_rows.to_csv(deleted_path, index=False)
    outputs.qc_flags.to_csv(flags_path, index=False)
    outputs.source_reference_crosswalk.to_csv(source_reference_path, index=False)
    manifest = build_release_manifest(
        outputs,
        canonical_path=canonical_path,
        allfields_path=allfields_path,
        metadata_path=metadata_path,
        deleted_path=deleted_path,
        flags_path=flags_path,
        source_reference_path=source_reference_path,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the supported observation build."""

    parser = argparse.ArgumentParser(description="Build the release-facing CUSP observation bundle.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Directory containing per-source processed tables.")
    parser.add_argument(
        "--skip-source",
        action="append",
        default=[],
        help="Source key to exclude from the build. May be passed multiple times.",
    )
    parser.add_argument("--canonical-output", type=Path, default=DEFAULT_CANONICAL_OUTPUT)
    parser.add_argument("--allfields-output", type=Path, default=DEFAULT_ALLFIELDS_OUTPUT)
    parser.add_argument("--metadata-output", type=Path, default=DEFAULT_METADATA_OUTPUT)
    parser.add_argument("--deleted-output", type=Path, default=DEFAULT_DELETED_OUTPUT)
    parser.add_argument("--flags-output", type=Path, default=DEFAULT_FLAGS_OUTPUT)
    parser.add_argument("--source-reference-output", type=Path, default=DEFAULT_SOURCE_REFERENCE_OUTPUT)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    return parser.parse_args()


def main() -> None:
    """Build the release-facing observation-level CUSP tables."""

    args = parse_args()
    skipped_sources = sorted(set(DEFAULT_SKIPPED_SOURCES).union(args.skip_source))
    selected_sources = list_included_sources(args.data_dir, skipped_sources=skipped_sources)
    raw_allfields = combine_sources(sources=selected_sources, data_dir=args.data_dir)
    build_outputs = build_release_tables(raw_allfields)
    write_build_outputs(
        build_outputs,
        canonical_path=args.canonical_output,
        allfields_path=args.allfields_output,
        metadata_path=args.metadata_output,
        deleted_path=args.deleted_output,
        flags_path=args.flags_output,
        source_reference_path=args.source_reference_output,
        manifest_path=args.manifest_output,
    )


if __name__ == "__main__":
    main()
