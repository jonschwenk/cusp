"""Shared models for the supported GEE feature sampler."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import geopandas as gpd
import pandas as pd


@dataclass(frozen=True)
class SamplingTable:
    """Normalized point-like CUSP table used for feature sampling."""

    frame: gpd.GeoDataFrame
    id_column: str
    source_path: Path | None = None

    @property
    def row_count(self) -> int:
        return int(len(self.frame))

    def identity_frame(self) -> pd.DataFrame:
        """Return the standard join columns that should accompany sampled features."""

        cols = [self.id_column]
        for column in ["date", "year", "lat", "lon"]:
            if column in self.frame.columns:
                cols.append(column)
        return self.frame.loc[:, cols].copy()


@dataclass(frozen=True)
class FeatureSamplingConfig:
    """Runtime options for supported GEE feature sampling."""

    sample_buffer_m: float | None = None
    buffer_crs: str = "EPSG:3413"
    chunk_size: int = 5000
    climate_avg_years: int = 20
    curvature_window_sizes: tuple[int, ...] = (3, 5, 7, 9)
    curvature_method: str = "LoG"
    curvature_sigma: float = 1.0
    gsw_start_year: int = 1999
    gsw_end_year: int = 2021


@dataclass(frozen=True)
class FeatureDefinition:
    """One supported feature or feature family in the registry."""

    key: str
    output_columns: tuple[str, ...]
    description: str
    source_label: str
    temporal_mode: str
    sample_fn: Callable[[SamplingTable, FeatureSamplingConfig, Any], pd.DataFrame]
    notes: str | None = None

    def metadata(self) -> dict[str, object]:
        """Return JSON-friendly metadata for manifests/docs."""

        return {
            "key": self.key,
            "output_columns": list(self.output_columns),
            "description": self.description,
            "source_label": self.source_label,
            "temporal_mode": self.temporal_mode,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FeatureSamplingResult:
    """Result bundle returned by the feature sampler."""

    features: pd.DataFrame
    selected_features: tuple[str, ...]
    input_table: SamplingTable
    feature_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
