"""Supported Google Earth Engine feature sampling for CUSP."""

from .io import (
    default_feature_manifest_path,
    default_feature_output_path,
    detect_id_column,
    load_sampling_table,
    normalize_sampling_frame,
)
from .models import FeatureDefinition, FeatureSamplingConfig, FeatureSamplingResult, SamplingTable
from .registry import BASE_FEATURE_SET, FEATURE_REGISTRY, resolve_feature_keys
from .sampler import sample_features_for_table, sample_features_from_path

__all__ = [
    "BASE_FEATURE_SET",
    "FEATURE_REGISTRY",
    "FeatureDefinition",
    "FeatureSamplingConfig",
    "FeatureSamplingResult",
    "SamplingTable",
    "default_feature_manifest_path",
    "default_feature_output_path",
    "detect_id_column",
    "load_sampling_table",
    "normalize_sampling_frame",
    "resolve_feature_keys",
    "sample_features_for_table",
    "sample_features_from_path",
]
