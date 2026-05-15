"""Supported GEE feature-sampling orchestration for CUSP."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pandas as pd

from .gee import build_feature_manifest, create_earth_engine_context
from .io import (
    default_feature_manifest_path,
    default_feature_output_path,
    load_sampling_table,
)
from .models import FeatureSamplingConfig, FeatureSamplingResult, SamplingTable
from .registry import FEATURE_REGISTRY, resolve_feature_keys


def _feature_output_columns(key: str) -> list[str]:
    """Return the declared non-ID output columns for one feature key."""

    return list(FEATURE_REGISTRY[key].output_columns)


def sample_features_for_table(
    table: SamplingTable,
    *,
    feature_keys: list[str] | None = None,
    feature_set: str | None = "base_v1",
    config: FeatureSamplingConfig | None = None,
    context: object | None = None,
) -> FeatureSamplingResult:
    """Sample one supported GEE feature set for a normalized CUSP table."""

    config = config or FeatureSamplingConfig()
    selected_keys = resolve_feature_keys(feature_keys, feature_set=feature_set)
    if context is None:
        context = create_earth_engine_context()

    result = table.identity_frame()
    feature_metadata: dict[str, dict[str, object]] = {}
    total_features = len(selected_keys)

    for index, key in enumerate(selected_keys, start=1):
        definition = FEATURE_REGISTRY[key]
        started = perf_counter()
        print(
            f"[cusp.features] Sampling feature {index}/{total_features}: {key} "
            f"({len(table.frame)} rows)",
            flush=True,
        )
        sampled = definition.sample_fn(table, config, context)
        elapsed = perf_counter() - started
        print(
            f"[cusp.features] Completed feature {index}/{total_features}: {key} "
            f"in {elapsed:.1f}s",
            flush=True,
        )
        result = result.merge(sampled, on=table.id_column, how="left")
        metadata = definition.metadata()
        metadata["output_columns"] = [column for column in sampled.columns if column != table.id_column]
        feature_metadata[key] = metadata

    return FeatureSamplingResult(
        features=result,
        selected_features=tuple(selected_keys),
        input_table=table,
        feature_metadata=feature_metadata,
    )


def sample_features_from_path(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
    id_column: str | None = None,
    feature_keys: list[str] | None = None,
    feature_set: str | None = "base_v1",
    config: FeatureSamplingConfig | None = None,
    gee_project: str | None = None,
    resume: bool = False,
) -> FeatureSamplingResult:
    """Load a CUSP point table, sample supported GEE features, and write outputs."""

    input_path = Path(input_path)
    output_path = Path(output_path) if output_path is not None else default_feature_output_path(input_path)
    manifest_path = (
        Path(manifest_path) if manifest_path is not None else default_feature_manifest_path(output_path)
    )

    config = config or FeatureSamplingConfig()
    total_started = perf_counter()
    print(f"[cusp.features] Input: {input_path}", flush=True)
    print(f"[cusp.features] Output: {output_path}", flush=True)
    print(f"[cusp.features] Manifest: {manifest_path}", flush=True)
    print(
        "[cusp.features] Config: "
        f"chunk_size={config.chunk_size}, "
        f"sample_buffer_m={config.sample_buffer_m}, "
        f"climate_avg_years={config.climate_avg_years}, "
        f"curvature_method={config.curvature_method}, "
        f"curvature_window_sizes={config.curvature_window_sizes}",
        flush=True,
    )
    print("[cusp.features] Loading sampling table", flush=True)
    load_started = perf_counter()
    table = load_sampling_table(input_path, id_column=id_column)
    load_elapsed = perf_counter() - load_started
    print(
        f"[cusp.features] Loaded {table.row_count} row(s) with ID column "
        f"'{table.id_column}' in {load_elapsed:.1f}s",
        flush=True,
    )
    context = create_earth_engine_context(project=gee_project)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    selected_keys = resolve_feature_keys(feature_keys, feature_set=feature_set)
    print(
        f"[cusp.features] Selected feature families ({len(selected_keys)}): "
        + ", ".join(selected_keys),
        flush=True,
    )
    result_frame = table.identity_frame()
    completed_features: list[str] = []
    feature_metadata: dict[str, dict[str, object]] = {}

    if resume and output_path.exists():
        print(f"[cusp.features] Resume requested; reading existing output {output_path}", flush=True)
        existing = pd.read_csv(output_path, low_memory=False)
        if table.id_column not in existing.columns:
            raise KeyError(f"Cannot resume because existing output is missing '{table.id_column}'.")
        expected_ids = table.frame[table.id_column].astype("string").reset_index(drop=True)
        existing_ids = existing[table.id_column].astype("string").reset_index(drop=True)
        if len(existing_ids) != len(expected_ids) or not existing_ids.equals(expected_ids):
            raise ValueError("Cannot resume because existing output IDs do not match the input table order.")
        result_frame = existing
        print(
            f"[cusp.features] Resume output has {len(result_frame)} row(s) and "
            f"{len(result_frame.columns)} column(s)",
            flush=True,
        )

    total_features = len(selected_keys)
    for index, key in enumerate(selected_keys, start=1):
        definition = FEATURE_REGISTRY[key]
        declared_outputs = _feature_output_columns(key)
        if declared_outputs and all(column in result_frame.columns for column in declared_outputs):
            print(
                f"[cusp.features] Skipping feature {index}/{total_features}: {key} "
                "already present in output "
                f"({', '.join(declared_outputs)})",
                flush=True,
            )
            metadata = definition.metadata()
            metadata["output_columns"] = declared_outputs
            feature_metadata[key] = metadata
            completed_features.append(key)
            continue

        started = perf_counter()
        print(
            f"[cusp.features] Sampling feature {index}/{total_features}: {key} "
            f"({len(table.frame)} rows)",
            flush=True,
        )
        sampled = definition.sample_fn(table, config, context)
        elapsed = perf_counter() - started
        print(
            f"[cusp.features] Completed feature {index}/{total_features}: {key} "
            f"in {elapsed:.1f}s",
            flush=True,
        )

        duplicate_columns = [column for column in sampled.columns if column != table.id_column and column in result_frame.columns]
        if duplicate_columns:
            print(
                f"[cusp.features] Replacing existing column(s) for {key}: "
                + ", ".join(duplicate_columns),
                flush=True,
            )
            result_frame = result_frame.drop(columns=duplicate_columns)
        result_frame = result_frame.merge(sampled, on=table.id_column, how="left")

        metadata = definition.metadata()
        metadata["output_columns"] = [column for column in sampled.columns if column != table.id_column]
        feature_metadata[key] = metadata
        completed_features.append(key)

        checkpoint_started = perf_counter()
        print(
            f"[cusp.features] Writing checkpoint after {key}: "
            f"{len(result_frame)} row(s), {len(result_frame.columns)} column(s)",
            flush=True,
        )
        result_frame.to_csv(output_path, index=False)
        build_feature_manifest(
            output_path=output_path,
            manifest_path=manifest_path,
            result_features=result_frame,
            selected_features=completed_features,
            feature_metadata=feature_metadata,
            input_table=table,
            config=config,
        )
        checkpoint_elapsed = perf_counter() - checkpoint_started
        print(
            f"[cusp.features] Checkpoint complete after {key} in {checkpoint_elapsed:.1f}s "
            f"({len(completed_features)}/{total_features} feature families)",
            flush=True,
        )

    result = FeatureSamplingResult(
        features=result_frame,
        selected_features=tuple(completed_features),
        input_table=table,
        feature_metadata=feature_metadata,
    )

    print(
        f"[cusp.features] Writing final output: {len(result.features)} row(s), "
        f"{len(result.features.columns)} column(s)",
        flush=True,
    )
    result.features.to_csv(output_path, index=False)
    build_feature_manifest(
        output_path=output_path,
        manifest_path=manifest_path,
        result_features=result.features,
        selected_features=list(result.selected_features),
        feature_metadata=result.feature_metadata,
        input_table=result.input_table,
        config=config,
    )
    total_elapsed = perf_counter() - total_started
    print(
        f"[cusp.features] Feature sampling complete in {total_elapsed:.1f}s: "
        f"{output_path}",
        flush=True,
    )
    return result
