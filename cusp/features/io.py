"""Input/output helpers for the supported GEE feature sampler."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .models import SamplingTable


TABULAR_SUFFIXES = {".csv", ".tsv"}
GEOSPATIAL_SUFFIXES = {".gpkg", ".geojson", ".json", ".shp"}
DEFAULT_ID_CANDIDATES = ("cusp_obs_id", "cusp_30m_id")


def detect_id_column(df: pd.DataFrame, id_column: str | None = None) -> str:
    """Detect the canonical join key for a CUSP observation or aggregation table."""

    if id_column is not None:
        if id_column not in df.columns:
            raise KeyError(f"Requested id_column '{id_column}' was not found in the input table.")
        return id_column

    present = [candidate for candidate in DEFAULT_ID_CANDIDATES if candidate in df.columns]
    if len(present) == 1:
        return present[0]
    if len(present) > 1:
        raise ValueError(
            "The input table contains multiple canonical ID columns. "
            "Pass id_column explicitly to disambiguate."
        )
    raise ValueError(
        "Could not detect a canonical ID column. Expected one of "
        f"{list(DEFAULT_ID_CANDIDATES)} or an explicit id_column."
    )


def _normalize_date_and_year(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize supported temporal columns for feature sampling."""

    working = df.copy()
    if "date" in working.columns:
        dates = pd.to_datetime(working["date"], format="mixed", errors="raise")
        working["date"] = dates.dt.strftime("%Y-%m-%d")
        if "year" not in working.columns:
            working["year"] = dates.dt.year.astype("Int64")
    elif "year" in working.columns:
        working["year"] = pd.to_numeric(working["year"], errors="coerce").astype("Int64")
    return working


def normalize_sampling_frame(df: pd.DataFrame, id_column: str | None = None) -> SamplingTable:
    """Normalize a point-like CUSP table for feature sampling."""

    detected_id = detect_id_column(df, id_column=id_column)

    if isinstance(df, gpd.GeoDataFrame):
        gdf = df.copy()
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        else:
            gdf = gdf.to_crs("EPSG:4326")
        if "lat" not in gdf.columns:
            gdf["lat"] = gdf.geometry.y
        if "lon" not in gdf.columns:
            gdf["lon"] = gdf.geometry.x
    else:
        working = df.copy()
        for column in ["lat", "lon"]:
            if column not in working.columns:
                raise KeyError(f"Input table is missing required '{column}' column for feature sampling.")
            working[column] = pd.to_numeric(working[column], errors="coerce")
        if working["lat"].isna().any() or working["lon"].isna().any():
            raise ValueError("Input table contains missing or non-numeric coordinates.")
        gdf = gpd.GeoDataFrame(
            working,
            geometry=gpd.points_from_xy(working["lon"], working["lat"]),
            crs="EPSG:4326",
        )

    gdf = _normalize_date_and_year(gdf)
    gdf[detected_id] = gdf[detected_id].astype("string")
    gdf = gdf.reset_index(drop=True)
    return SamplingTable(frame=gdf, id_column=detected_id)


def load_sampling_table(path: str | Path, id_column: str | None = None) -> SamplingTable:
    """Load a CSV or geospatial point table for GEE feature sampling."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TABULAR_SUFFIXES:
        sep = "\t" if suffix == ".tsv" else ","
        frame = pd.read_csv(path, sep=sep, low_memory=False)
    elif suffix in GEOSPATIAL_SUFFIXES:
        frame = gpd.read_file(path)
    else:
        raise ValueError(
            f"Unsupported input suffix '{suffix}'. Supported tabular: {sorted(TABULAR_SUFFIXES)}; "
            f"supported geospatial: {sorted(GEOSPATIAL_SUFFIXES)}."
        )

    table = normalize_sampling_frame(frame, id_column=id_column)
    return SamplingTable(frame=table.frame, id_column=table.id_column, source_path=path)


def default_feature_output_path(input_path: str | Path) -> Path:
    """Derive a default feature-table output path next to the input table."""

    input_path = Path(input_path)
    return input_path.with_name(f"{input_path.stem}_features.csv")


def default_feature_manifest_path(output_path: str | Path) -> Path:
    """Derive the companion manifest path for a feature table."""

    output_path = Path(output_path)
    return output_path.with_name(f"{output_path.stem}_manifest.json")
