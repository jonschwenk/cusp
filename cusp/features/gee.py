"""Earth Engine helpers for the supported CUSP feature sampler."""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import ndimage

from .models import FeatureSamplingConfig, SamplingTable


@dataclass(frozen=True)
class EarthEngineContext:
    """Thin wrapper around lazily imported EE modules."""

    ee: Any
    geemap: Any


def create_earth_engine_context(project: str | None = None) -> EarthEngineContext:
    """Import and initialize the Earth Engine stack on demand."""

    started = perf_counter()
    project_label = project if project is not None else "default project"
    print(f"[cusp.features] Importing Earth Engine stack for {project_label}", flush=True)
    import ee  # type: ignore
    import geemap  # type: ignore

    print(f"[cusp.features] Initializing Earth Engine for {project_label}", flush=True)
    try:
        if project is None:
            ee.Initialize()
        else:
            ee.Initialize(project=project)
    except Exception:
        # Some environments are already initialized; retrying Initialize can fail noisily.
        # Fall through when the runtime is already usable.
        if project is not None:
            ee.Initialize(project=project)
    elapsed = perf_counter() - started
    print(f"[cusp.features] Earth Engine ready in {elapsed:.1f}s", flush=True)
    return EarthEngineContext(ee=ee, geemap=geemap)


def buffer_points(points: gpd.GeoDataFrame, sample_buffer_m: float, buffer_crs: str) -> gpd.GeoDataFrame:
    """Buffer sampling points in a projected CRS and return EPSG:4326 polygons."""

    projected = points.to_crs(buffer_crs)
    buffered = projected.copy()
    buffered["geometry"] = projected.geometry.buffer(sample_buffer_m)
    return buffered.to_crs("EPSG:4326")


def _chunk_frame(df: gpd.GeoDataFrame, chunk_size: int) -> Iterable[gpd.GeoDataFrame]:
    for start in range(0, len(df), chunk_size):
        yield df.iloc[start : start + chunk_size].copy()


def _sampling_properties(chunk: gpd.GeoDataFrame, id_column: str) -> list[str]:
    properties = [id_column, "_sample_index"]
    for column in ["date", "year", "lat", "lon"]:
        if column in chunk.columns:
            properties.append(column)
    return properties


def _sample_image_chunk(
    *,
    context: EarthEngineContext,
    image: Any,
    chunk: gpd.GeoDataFrame,
    id_column: str,
    output_names: list[str],
    sample_buffer_m: float | None,
    buffer_crs: str,
    reducer_name: str,
    scale_m: float | None = None,
) -> pd.DataFrame:
    ee = context.ee
    geemap = context.geemap

    properties = _sampling_properties(chunk, id_column=id_column)
    working = chunk.loc[:, properties + ["geometry"]].copy()

    if scale_m is None:
        scale_m = float(image.select(0).projection().nominalScale().getInfo())

    renamed = image.rename(output_names)

    if sample_buffer_m is None:
        feature_collection = geemap.geopandas_to_ee(working)
        sampled = renamed.sampleRegions(
            collection=feature_collection,
            properties=properties,
            scale=scale_m,
            geometries=False,
        ).getInfo()
        value_keys = output_names
    else:
        buffered = buffer_points(working, sample_buffer_m=sample_buffer_m, buffer_crs=buffer_crs)
        feature_collection = geemap.geopandas_to_ee(buffered)
        reducer = getattr(ee.Reducer, reducer_name)()
        sampled = renamed.reduceRegions(
            collection=feature_collection,
            reducer=reducer,
            scale=scale_m,
        ).getInfo()
        value_keys = output_names

    rows: list[dict[str, object]] = []
    for feature in sampled["features"]:
        props = feature["properties"]
        row = {
            id_column: props.get(id_column),
            "_sample_index": props.get("_sample_index"),
        }
        for output_name, value_key in zip(output_names, value_keys):
            row[output_name] = props.get(value_key, props.get(output_name))
        rows.append(row)

    sampled_df = pd.DataFrame.from_records(rows)
    if sampled_df.empty:
        return chunk.loc[:, [id_column, "_sample_index"]].assign(
            **{output_name: np.nan for output_name in output_names}
        )

    full_index = chunk.loc[:, [id_column, "_sample_index"]]
    sampled_df = full_index.merge(sampled_df, on=[id_column, "_sample_index"], how="left")
    return sampled_df


def sample_single_band_image(
    *,
    table: SamplingTable,
    context: EarthEngineContext,
    image: Any,
    output_name: str,
    config: FeatureSamplingConfig,
    reducer_name: str = "mean",
    scale_m: float | None = None,
) -> pd.DataFrame:
    """Sample a single-band image for all rows in a normalized CUSP table."""

    return sample_image_bands(
        table=table,
        context=context,
        image=image,
        output_names=[output_name],
        config=config,
        reducer_name=reducer_name,
        scale_m=scale_m,
    )


def sample_image_bands(
    *,
    table: SamplingTable,
    context: EarthEngineContext,
    image: Any,
    output_names: list[str],
    config: FeatureSamplingConfig,
    reducer_name: str = "mean",
    scale_m: float | None = None,
) -> pd.DataFrame:
    """Sample one image with one or more bands for all rows in a CUSP table."""

    working = table.frame.copy()
    working["_sample_index"] = np.arange(len(working), dtype="int64")
    chunk_results: list[pd.DataFrame] = []
    if scale_m is None:
        scale_m = float(image.select(0).projection().nominalScale().getInfo())

    total_chunks = ceil(len(working) / config.chunk_size) if len(working) else 0
    output_label = ",".join(output_names)
    print(
        f"[cusp.features]   sampling {len(working)} rows for {output_label} "
        f"in {total_chunks} chunk(s) of up to {config.chunk_size}",
        flush=True,
    )
    for chunk_index, chunk in enumerate(_chunk_frame(working, chunk_size=config.chunk_size), start=1):
        chunk_started = perf_counter()
        print(
            f"[cusp.features]   chunk {chunk_index}/{total_chunks} start -> {output_label} "
            f"({len(chunk)} rows)",
            flush=True,
        )
        chunk_results.append(
            _sample_image_chunk(
                context=context,
                image=image,
                chunk=chunk,
                id_column=table.id_column,
                output_names=output_names,
                sample_buffer_m=config.sample_buffer_m,
                buffer_crs=config.buffer_crs,
                reducer_name=reducer_name,
                scale_m=scale_m,
            )
        )
        chunk_elapsed = perf_counter() - chunk_started
        print(
            f"[cusp.features]   chunk {chunk_index}/{total_chunks} done -> {output_label} "
            f"in {chunk_elapsed:.1f}s",
            flush=True,
        )

    if not chunk_results:
        return table.identity_frame().assign(
            **{output_name: pd.Series(dtype="float64") for output_name in output_names}
        )

    merged = pd.concat(chunk_results, ignore_index=True)
    merged = merged.sort_values("_sample_index", kind="mergesort").reset_index(drop=True)
    return merged.loc[:, [table.id_column] + output_names]


def reduce_image_collection_mean(context: EarthEngineContext, image_collection: Any, band_name: str) -> Any:
    """Reduce one image-collection band to its mean image."""

    ee = context.ee
    projection = image_collection.first().projection().getInfo()["crs"]
    scale = image_collection.first().projection().nominalScale().getInfo()
    return (
        image_collection.select(band_name)
        .reduce(ee.Reducer.mean())
        .reproject(projection, scale=scale)
    )


def image_collection_date_bounds(image_collection: Any) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Return inclusive UTC date bounds for an Earth Engine image collection."""

    min_ms = image_collection.aggregate_min("system:time_start").getInfo()
    max_ms = image_collection.aggregate_max("system:time_start").getInfo()
    if min_ms is None or max_ms is None:
        return None, None

    start = pd.to_datetime(min_ms, unit="ms", utc=True).tz_convert(None).normalize()
    end = pd.to_datetime(max_ms, unit="ms", utc=True).tz_convert(None).normalize()
    return start, end


def build_surface_water_occurrence_image(context: EarthEngineContext, start_year: int, end_year: int) -> Any:
    """Build a GSW occurrence image for a target year span."""

    ee = context.ee
    monthly_history = ee.ImageCollection("JRC/GSW1_4/MonthlyHistory")
    projection = monthly_history.first().projection().getInfo()["crs"]
    scale = monthly_history.first().projection().nominalScale().getInfo()
    cut = monthly_history.filter(
        ee.Filter.And(ee.Filter.gte("year", start_year), ee.Filter.lte("year", end_year))
    )

    def _relab(image: Any) -> Any:
        return image.remap([2, 1], [1, 0], None, "water")

    return (
        cut.map(_relab)
        .reduce(ee.Reducer.mean())
        .reproject(projection, scale=scale)
        .multiply(100)
        .round()
        .toUint8()
        .reproject(projection, scale=scale)
    )


def build_soil_texture_images(context: EarthEngineContext) -> dict[str, Any]:
    """Return depth-weighted SoilGrids sand/silt/clay images."""

    ee = context.ee
    weights = np.array([5, 10, 15, 30, 40, 100], dtype="float64")
    weights = (weights / weights.sum()).tolist()

    sand_grid = ee.Image("projects/soilgrids-isric/sand_mean")
    silt_grid = ee.Image("projects/soilgrids-isric/silt_mean")
    clay_grid = ee.Image("projects/soilgrids-isric/clay_mean")
    soil_mass_grid = sand_grid.add(silt_grid.add(clay_grid))

    sand = sand_grid.divide(soil_mass_grid).multiply(ee.Image.constant(weights)).reduce(ee.Reducer.sum())
    silt = silt_grid.divide(soil_mass_grid).multiply(ee.Image.constant(weights)).reduce(ee.Reducer.sum())
    clay = clay_grid.divide(soil_mass_grid).multiply(ee.Image.constant(weights)).reduce(ee.Reducer.sum())
    return {"sand": sand, "silt": silt, "clay": clay}


def build_soil_carbon_image(context: EarthEngineContext) -> Any:
    """Return depth-weighted SoilGrids soil organic carbon."""

    ee = context.ee
    weights = np.array([5, 10, 15, 30, 40, 100], dtype="float64")
    weights = (weights / weights.sum()).tolist()
    soc_grid = ee.Image("projects/soilgrids-isric/soc_mean")
    return soc_grid.multiply(ee.Image.constant(weights)).reduce(ee.Reducer.sum())


def fspecial_gauss(win_size: int, sigma: float) -> np.ndarray:
    """Generate a MATLAB-style 2-D Gaussian kernel."""

    x, y = np.mgrid[-win_size // 2 + 1 : win_size // 2 + 1, -win_size // 2 + 1 : win_size // 2 + 1]
    gaussian = np.exp(-((x**2 + y**2) / (2.0 * sigma**2)))
    return gaussian / gaussian.sum()


def laplacian_gaussian_kernel(window_size: int, sigma: float, scale_m: float) -> np.ndarray:
    """Generate a Laplacian-of-Gaussian kernel for curvature sampling."""

    gaussian = fspecial_gauss(win_size=window_size, sigma=sigma)
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype="float64") * (scale_m ** -2)
    return ndimage.convolve(gaussian, laplacian) * 100


def smoothed_curvature_kernel(window_size: int, scale_m: float) -> np.ndarray:
    """Generate a smoothed Laplacian kernel for terrain curvature."""

    smooth = np.ones((window_size, window_size), dtype="float64")
    smooth = smooth / smooth.sum()
    padded = np.pad(smooth, pad_width=((1, 1), (1, 1)), mode="constant")
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype="float64") * (scale_m ** -2)
    return ndimage.convolve(padded, laplacian) * 100


def build_curvature_image(
    context: EarthEngineContext,
    dem: Any,
    *,
    window_size: int,
    method: str,
    sigma: float,
) -> Any:
    """Compute a single-band curvature image from a DEM."""

    ee = context.ee
    scale_m = float(dem.projection().nominalScale().getInfo())
    if method == "basic":
        kernel = smoothed_curvature_kernel(window_size=window_size, scale_m=scale_m)
    elif method == "LoG":
        kernel = laplacian_gaussian_kernel(window_size=window_size, sigma=sigma, scale_m=scale_m)
    else:
        raise ValueError(f"Unsupported curvature method '{method}'.")
    return dem.convolve(ee.Kernel.fixed(weights=kernel.tolist())).rename(["curvature"])


def build_feature_manifest(
    *,
    output_path: Path,
    manifest_path: Path,
    result_features: pd.DataFrame,
    selected_features: list[str],
    feature_metadata: dict[str, dict[str, object]],
    input_table: SamplingTable,
    config: FeatureSamplingConfig,
) -> None:
    """Write a compact JSON manifest describing one feature-sampling run."""

    payload = {
        "build_scope": "gee_feature_sampling",
        "input_path": str(input_table.source_path) if input_table.source_path is not None else None,
        "input_id_column": input_table.id_column,
        "input_rows": input_table.row_count,
        "selected_features": selected_features,
        "sampling_config": {
            "sample_buffer_m": config.sample_buffer_m,
            "buffer_crs": config.buffer_crs,
            "chunk_size": config.chunk_size,
            "climate_avg_years": config.climate_avg_years,
            "curvature_window_sizes": list(config.curvature_window_sizes),
            "curvature_method": config.curvature_method,
            "curvature_sigma": config.curvature_sigma,
            "gsw_start_year": config.gsw_start_year,
            "gsw_end_year": config.gsw_end_year,
        },
        "output": {
            "path": str(output_path),
            "rows": int(len(result_features)),
            "columns": list(result_features.columns),
        },
        "features": feature_metadata,
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
