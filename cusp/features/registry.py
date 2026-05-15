"""Feature registry for the supported GEE sampler."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .gee import (
    build_curvature_image,
    image_collection_date_bounds,
    build_soil_carbon_image,
    build_soil_texture_images,
    build_surface_water_occurrence_image,
    reduce_image_collection_mean,
    sample_image_bands,
    sample_single_band_image,
)
from .models import FeatureDefinition, FeatureSamplingConfig, SamplingTable


def _sample_static_image(
    *,
    table: SamplingTable,
    config: FeatureSamplingConfig,
    context: object,
    output_name: str,
    image: object,
    reducer_name: str = "mean",
) -> pd.DataFrame:
    return sample_single_band_image(
        table=table,
        context=context,  # type: ignore[arg-type]
        image=image,
        output_name=output_name,
        config=config,
        reducer_name=reducer_name,
    )


def sample_slope(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    arctic_dem = context.ee.Image("UMN/PGC/ArcticDEM/V4/2m_mosaic").select("elevation")
    arctic_slope = context.ee.Terrain.slope(arctic_dem)
    return _sample_static_image(
        table=table,
        config=config,
        context=context,
        output_name="slope",
        image=arctic_slope,
    )


def sample_aspect(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    arctic_dem = context.ee.Image("UMN/PGC/ArcticDEM/V4/2m_mosaic").select("elevation")
    arctic_aspect = context.ee.Terrain.aspect(arctic_dem)
    return _sample_static_image(
        table=table,
        config=config,
        context=context,
        output_name="aspect",
        image=arctic_aspect,
    )


def sample_curvature(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    ee = context.ee
    arctic_dem = ee.Image("UMN/PGC/ArcticDEM/V4/2m_mosaic").select("elevation")
    images = []
    output_names = []
    for window_size in config.curvature_window_sizes:
        image = build_curvature_image(
            context=context,  # type: ignore[arg-type]
            dem=arctic_dem,
            window_size=window_size,
            method=config.curvature_method,
            sigma=config.curvature_sigma,
        )
        output_name = f"curvature_{window_size * 2}m"
        images.append(image.rename(output_name))
        output_names.append(output_name)
    return sample_image_bands(
        table=table,
        context=context,  # type: ignore[arg-type]
        image=ee.Image.cat(images),
        output_names=output_names,
        config=config,
    )


def sample_terrain(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    ee = context.ee
    arctic_dem = ee.Image("UMN/PGC/ArcticDEM/V4/2m_mosaic").select("elevation")
    images = [
        ee.Terrain.slope(arctic_dem).rename("slope"),
        ee.Terrain.aspect(arctic_dem).rename("aspect"),
    ]
    output_names = ["slope", "aspect"]
    for window_size in config.curvature_window_sizes:
        output_name = f"curvature_{window_size * 2}m"
        images.append(
            build_curvature_image(
                context=context,  # type: ignore[arg-type]
                dem=arctic_dem,
                window_size=window_size,
                method=config.curvature_method,
                sigma=config.curvature_sigma,
            ).rename(output_name)
        )
        output_names.append(output_name)
    return sample_image_bands(
        table=table,
        context=context,  # type: ignore[arg-type]
        image=ee.Image.cat(images),
        output_names=output_names,
        config=config,
    )


def sample_soil_texture(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    ee = context.ee
    images = build_soil_texture_images(context=context)  # type: ignore[arg-type]
    output_names = ["sand", "silt", "clay"]
    return sample_image_bands(
        table=table,
        context=context,  # type: ignore[arg-type]
        image=ee.Image.cat([images[output_name].rename(output_name) for output_name in output_names]),
        output_names=output_names,
        config=config,
    )


def sample_soil_oc(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    image = build_soil_carbon_image(context=context)  # type: ignore[arg-type]
    return _sample_static_image(
        table=table,
        config=config,
        context=context,
        output_name="soil_oc",
        image=image,
    )


def _sample_climate_feature(
    *,
    table: SamplingTable,
    config: FeatureSamplingConfig,
    context: object,
    output_name: str,
    band_name: str,
    annual_multiplier: float = 1.0,
) -> pd.DataFrame:
    if "year" not in table.frame.columns:
        raise KeyError(f"Sampling '{output_name}' requires a 'year' column or a parseable 'date' column.")

    era5 = context.ee.ImageCollection("ECMWF/ERA5/MONTHLY")
    available_start, available_end = image_collection_date_bounds(era5)
    outputs: list[pd.DataFrame] = []
    years = sorted(table.frame["year"].dropna().astype(int).unique())
    total_years = len(years)
    for index, year in enumerate(years, start=1):
        subset = table.frame.loc[table.frame["year"].astype("Int64") == year].copy()
        if subset.empty:
            continue
        print(
            f"[cusp.features]   {output_name}: year {index}/{total_years} ({year}) "
            f"with {len(subset)} rows",
            flush=True,
        )
        requested_start = pd.Timestamp(f"{year - config.climate_avg_years}-01-01")
        requested_end = pd.Timestamp(f"{year}-12-31")

        if available_start is None or available_end is None:
            outputs.append(subset.loc[:, [table.id_column]].assign(**{output_name: float("nan")}))
            continue

        start = max(requested_start, available_start)
        end = min(requested_end, available_end)
        if start > end:
            print(
                f"[cusp.features]   {output_name}: no ERA5 overlap for year {year}; writing NaN",
                flush=True,
            )
            outputs.append(subset.loc[:, [table.id_column]].assign(**{output_name: float("nan")}))
            continue

        filter_start = start.strftime("%Y-%m-%d")
        filter_end = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        annual_image = reduce_image_collection_mean(
            context=context,  # type: ignore[arg-type]
            image_collection=era5.filterDate(filter_start, filter_end),
            band_name=band_name,
        )
        subset_table = SamplingTable(frame=subset.reset_index(drop=True), id_column=table.id_column)
        sampled = _sample_static_image(
            table=subset_table,
            config=config,
            context=context,
            output_name=output_name,
            image=annual_image,
        )
        if annual_multiplier != 1.0:
            sampled[output_name] = pd.to_numeric(sampled[output_name], errors="coerce") * annual_multiplier
        outputs.append(sampled)

    combined = pd.concat(outputs, ignore_index=True)
    combined = combined.sort_values(table.id_column, kind="mergesort").reset_index(drop=True)
    return combined


def _sample_climate_features(
    *,
    table: SamplingTable,
    config: FeatureSamplingConfig,
    context: object,
    specs: list[tuple[str, str, float]],
) -> pd.DataFrame:
    if "year" not in table.frame.columns:
        outputs = ", ".join(output_name for output_name, _, _ in specs)
        raise KeyError(f"Sampling '{outputs}' requires a 'year' column or a parseable 'date' column.")

    ee = context.ee
    era5 = ee.ImageCollection("ECMWF/ERA5/MONTHLY")
    available_start, available_end = image_collection_date_bounds(era5)
    outputs: list[pd.DataFrame] = []
    years = sorted(table.frame["year"].dropna().astype(int).unique())
    total_years = len(years)
    output_names = [output_name for output_name, _, _ in specs]
    band_names = [band_name for _, band_name, _ in specs]
    for index, year in enumerate(years, start=1):
        subset = table.frame.loc[table.frame["year"].astype("Int64") == year].copy()
        if subset.empty:
            continue
        print(
            f"[cusp.features]   climate: year {index}/{total_years} ({year}) "
            f"with {len(subset)} rows",
            flush=True,
        )
        requested_start = pd.Timestamp(f"{year - config.climate_avg_years}-01-01")
        requested_end = pd.Timestamp(f"{year}-12-31")

        if available_start is None or available_end is None:
            outputs.append(subset.loc[:, [table.id_column]].assign(**{name: float("nan") for name in output_names}))
            continue

        start = max(requested_start, available_start)
        end = min(requested_end, available_end)
        if start > end:
            print(
                f"[cusp.features]   climate: no ERA5 overlap for year {year}; writing NaN",
                flush=True,
            )
            outputs.append(subset.loc[:, [table.id_column]].assign(**{name: float("nan") for name in output_names}))
            continue

        filter_start = start.strftime("%Y-%m-%d")
        filter_end = (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        annual_image = (
            era5.filterDate(filter_start, filter_end)
            .select(band_names)
            .reduce(ee.Reducer.mean())
            .rename(output_names)
        )
        subset_table = SamplingTable(frame=subset.reset_index(drop=True), id_column=table.id_column)
        sampled = sample_image_bands(
            table=subset_table,
            context=context,  # type: ignore[arg-type]
            image=annual_image,
            output_names=output_names,
            config=config,
        )
        for output_name, _, annual_multiplier in specs:
            if annual_multiplier != 1.0:
                sampled[output_name] = pd.to_numeric(sampled[output_name], errors="coerce") * annual_multiplier
        outputs.append(sampled)

    combined = pd.concat(outputs, ignore_index=True)
    combined = combined.sort_values(table.id_column, kind="mergesort").reset_index(drop=True)
    return combined


def sample_temperature(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    return _sample_climate_feature(
        table=table,
        config=config,
        context=context,
        output_name="temperature",
        band_name="mean_2m_air_temperature",
    )


def sample_precip(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    return _sample_climate_feature(
        table=table,
        config=config,
        context=context,
        output_name="precip",
        band_name="total_precipitation",
        annual_multiplier=12.0,
    )


def sample_climate(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    return _sample_climate_features(
        table=table,
        config=config,
        context=context,
        specs=[
            ("temperature", "mean_2m_air_temperature", 1.0),
            ("precip", "total_precipitation", 12.0),
        ],
    )


def sample_surface_water_occurrence(
    table: SamplingTable, config: FeatureSamplingConfig, context: object
) -> pd.DataFrame:
    image = build_surface_water_occurrence_image(
        context=context,  # type: ignore[arg-type]
        start_year=config.gsw_start_year,
        end_year=config.gsw_end_year,
    )
    return _sample_static_image(
        table=table,
        config=config,
        context=context,
        output_name="swo_landsat",
        image=image,
    )


def sample_merit_hand(table: SamplingTable, config: FeatureSamplingConfig, context: object) -> pd.DataFrame:
    merit = context.ee.Image("MERIT/Hydro/v1_0_1").select("hnd")
    return _sample_static_image(
        table=table,
        config=config,
        context=context,
        output_name="merit90_hand",
        image=merit,
    )


FEATURE_REGISTRY: dict[str, FeatureDefinition] = {
    "slope": FeatureDefinition(
        key="slope",
        output_columns=("slope",),
        description="Terrain slope from ArcticDEM.",
        source_label="UMN/PGC/ArcticDEM/V4/2m_mosaic",
        temporal_mode="static",
        sample_fn=sample_slope,
    ),
    "aspect": FeatureDefinition(
        key="aspect",
        output_columns=("aspect",),
        description="Terrain aspect from ArcticDEM.",
        source_label="UMN/PGC/ArcticDEM/V4/2m_mosaic",
        temporal_mode="static",
        sample_fn=sample_aspect,
    ),
    "curvature": FeatureDefinition(
        key="curvature",
        output_columns=("curvature_6m", "curvature_10m", "curvature_14m", "curvature_18m"),
        description="Multiscale curvature derived from ArcticDEM.",
        source_label="UMN/PGC/ArcticDEM/V4/2m_mosaic",
        temporal_mode="static",
        sample_fn=sample_curvature,
        notes="Current defaults use LoG curvature with window sizes 3, 5, 7, and 9.",
    ),
    "terrain": FeatureDefinition(
        key="terrain",
        output_columns=("slope", "aspect", "curvature_6m", "curvature_10m", "curvature_14m", "curvature_18m"),
        description="Terrain slope, aspect, and multiscale curvature from ArcticDEM.",
        source_label="UMN/PGC/ArcticDEM/V4/2m_mosaic",
        temporal_mode="static",
        sample_fn=sample_terrain,
        notes="Composite base_v1 feature that samples all terrain outputs in one Earth Engine request per chunk.",
    ),
    "soil_texture": FeatureDefinition(
        key="soil_texture",
        output_columns=("sand", "silt", "clay"),
        description="Depth-weighted SoilGrids sand, silt, and clay fractions.",
        source_label="projects/soilgrids-isric",
        temporal_mode="static",
        sample_fn=sample_soil_texture,
    ),
    "soil_oc": FeatureDefinition(
        key="soil_oc",
        output_columns=("soil_oc",),
        description="Depth-weighted SoilGrids soil organic carbon.",
        source_label="projects/soilgrids-isric/soc_mean",
        temporal_mode="static",
        sample_fn=sample_soil_oc,
    ),
    "temperature": FeatureDefinition(
        key="temperature",
        output_columns=("temperature",),
        description="Antecedent mean 2 m air temperature from ERA5 monthly data.",
        source_label="ECMWF/ERA5/MONTHLY",
        temporal_mode="antecedent_year_mean",
        sample_fn=sample_temperature,
        notes="Default climate window is the previous 20 years through the observation year.",
    ),
    "precip": FeatureDefinition(
        key="precip",
        output_columns=("precip",),
        description="Antecedent annualized total precipitation from ERA5 monthly data.",
        source_label="ECMWF/ERA5/MONTHLY",
        temporal_mode="antecedent_year_mean",
        sample_fn=sample_precip,
        notes="Default climate window is the previous 20 years through the observation year.",
    ),
    "climate": FeatureDefinition(
        key="climate",
        output_columns=("temperature", "precip"),
        description="Antecedent mean temperature and annualized precipitation from ERA5 monthly data.",
        source_label="ECMWF/ERA5/MONTHLY",
        temporal_mode="antecedent_year_mean",
        sample_fn=sample_climate,
        notes="Composite base_v1 feature that samples temperature and precipitation together by year.",
    ),
    "swo_landsat": FeatureDefinition(
        key="swo_landsat",
        output_columns=("swo_landsat",),
        description="Long-term surface-water occurrence from JRC Global Surface Water monthly history.",
        source_label="JRC/GSW1_4/MonthlyHistory",
        temporal_mode="static_window",
        sample_fn=sample_surface_water_occurrence,
        notes="Default occurrence window is 1999-2021.",
    ),
    "merit_hand": FeatureDefinition(
        key="merit_hand",
        output_columns=("merit90_hand",),
        description="Height above nearest drainage from MERIT Hydro.",
        source_label="MERIT/Hydro/v1_0_1",
        temporal_mode="static",
        sample_fn=sample_merit_hand,
    ),
}


BASE_FEATURE_SET = (
    "soil_texture",
    "soil_oc",
    "climate",
    "swo_landsat",
    "merit_hand",
    "terrain",
)


def resolve_feature_keys(
    feature_keys: Iterable[str] | None = None,
    *,
    feature_set: str | None = "base_v1",
) -> list[str]:
    """Resolve a feature-set request into concrete feature keys."""

    resolved: list[str] = []
    if feature_set is not None:
        if feature_set == "none":
            feature_set = None
        elif feature_set != "base_v1":
            raise ValueError(f"Unsupported feature_set '{feature_set}'.")
    if feature_set is not None:
        resolved.extend(BASE_FEATURE_SET)

    if feature_keys is not None:
        resolved.extend(feature_keys)

    deduped: list[str] = []
    for key in resolved:
        if key not in FEATURE_REGISTRY:
            raise KeyError(f"Unsupported feature key '{key}'.")
        if key not in deduped:
            deduped.append(key)
    return deduped
