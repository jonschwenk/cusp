from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cusp.features import (
    BASE_FEATURE_SET,
    FeatureDefinition,
    FeatureSamplingConfig,
    detect_id_column,
    load_sampling_table,
    normalize_sampling_frame,
    resolve_feature_keys,
    sample_features_for_table,
    sample_features_from_path,
)


class FeatureTests(unittest.TestCase):
    def test_detect_id_column_for_observation_and_aggregated_tables(self) -> None:
        observations = pd.DataFrame({"cusp_obs_id": ["obs_1"], "lat": [65.0], "lon": [-147.0]})
        aggregated = pd.DataFrame({"cusp_30m_id": ["agg_1"], "lat": [65.0], "lon": [-147.0]})

        self.assertEqual(detect_id_column(observations), "cusp_obs_id")
        self.assertEqual(detect_id_column(aggregated), "cusp_30m_id")

    def test_normalize_sampling_frame_derives_year_from_date(self) -> None:
        raw = pd.DataFrame(
            {
                "cusp_obs_id": ["obs_1"],
                "lat": [65.0],
                "lon": [-147.0],
                "date": ["2020-08-15"],
            }
        )
        table = normalize_sampling_frame(raw)
        self.assertEqual(table.id_column, "cusp_obs_id")
        self.assertEqual(table.frame.loc[0, "year"], 2020)
        self.assertEqual(table.frame.loc[0, "date"], "2020-08-15")

    def test_load_sampling_table_supports_csv(self) -> None:
        raw = pd.DataFrame(
            {
                "cusp_30m_id": ["agg_1"],
                "lat": [66.0],
                "lon": [-150.0],
                "date": ["2021-08-20"],
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "aggregated_30m.csv"
            raw.to_csv(path, index=False)
            table = load_sampling_table(path)

        self.assertEqual(table.id_column, "cusp_30m_id")
        self.assertEqual(table.frame.loc[0, "year"], 2021)

    def test_resolve_feature_keys_base_v1(self) -> None:
        resolved = resolve_feature_keys()
        self.assertEqual(tuple(resolved), BASE_FEATURE_SET)

    def test_resolve_feature_keys_supports_feature_set_none(self) -> None:
        resolved = resolve_feature_keys(feature_keys=["slope"], feature_set="none")
        self.assertEqual(resolved, ["slope"])

    def test_sample_features_for_table_merges_feature_outputs_by_id(self) -> None:
        raw = pd.DataFrame(
            {
                "cusp_obs_id": ["obs_1", "obs_2"],
                "lat": [65.0, 65.1],
                "lon": [-147.0, -147.1],
                "date": ["2020-08-01", "2020-08-02"],
            }
        )
        table = normalize_sampling_frame(raw)

        def _sample_a(table, config, context):
            return pd.DataFrame({table.id_column: table.frame[table.id_column], "feat_a": [1.0, 2.0]})

        def _sample_b(table, config, context):
            return pd.DataFrame({table.id_column: table.frame[table.id_column], "feat_b": [3.0, 4.0]})

        fake_registry = {
            "feat_a": FeatureDefinition(
                key="feat_a",
                output_columns=("feat_a",),
                description="A",
                source_label="test",
                temporal_mode="static",
                sample_fn=_sample_a,
            ),
            "feat_b": FeatureDefinition(
                key="feat_b",
                output_columns=("feat_b",),
                description="B",
                source_label="test",
                temporal_mode="static",
                sample_fn=_sample_b,
            ),
        }

        from cusp.features import sampler as sampler_module
        from cusp.features import registry as registry_module

        original_feature_registry = registry_module.FEATURE_REGISTRY.copy()
        original_resolver = registry_module.resolve_feature_keys
        try:
            registry_module.FEATURE_REGISTRY.clear()
            registry_module.FEATURE_REGISTRY.update(fake_registry)
            sampler_module.FEATURE_REGISTRY.clear()
            sampler_module.FEATURE_REGISTRY.update(fake_registry)

            def _resolve(feature_keys=None, feature_set="base_v1"):
                return ["feat_a", "feat_b"]

            registry_module.resolve_feature_keys = _resolve
            sampler_module.resolve_feature_keys = _resolve

            result = sample_features_for_table(
                table,
                feature_set=None,
                feature_keys=["feat_a", "feat_b"],
                config=FeatureSamplingConfig(),
                context=object(),
            )
        finally:
            registry_module.FEATURE_REGISTRY.clear()
            registry_module.FEATURE_REGISTRY.update(original_feature_registry)
            sampler_module.FEATURE_REGISTRY.clear()
            sampler_module.FEATURE_REGISTRY.update(original_feature_registry)
            registry_module.resolve_feature_keys = original_resolver
            sampler_module.resolve_feature_keys = original_resolver

        self.assertEqual(
            result.features.columns.tolist(),
            ["cusp_obs_id", "date", "year", "lat", "lon", "feat_a", "feat_b"],
        )
        self.assertEqual(result.features["feat_a"].tolist(), [1.0, 2.0])
        self.assertEqual(result.features["feat_b"].tolist(), [3.0, 4.0])

    def test_sample_features_from_path_can_resume_completed_outputs(self) -> None:
        raw = pd.DataFrame(
            {
                "cusp_obs_id": ["obs_1", "obs_2"],
                "lat": [65.0, 65.1],
                "lon": [-147.0, -147.1],
                "date": ["2020-08-01", "2020-08-02"],
            }
        )

        calls: list[str] = []

        def _sample_a(table, config, context):
            calls.append("feat_a")
            return pd.DataFrame({table.id_column: table.frame[table.id_column], "feat_a": [1.0, 2.0]})

        def _sample_b(table, config, context):
            calls.append("feat_b")
            return pd.DataFrame({table.id_column: table.frame[table.id_column], "feat_b": [3.0, 4.0]})

        fake_registry = {
            "feat_a": FeatureDefinition(
                key="feat_a",
                output_columns=("feat_a",),
                description="A",
                source_label="test",
                temporal_mode="static",
                sample_fn=_sample_a,
            ),
            "feat_b": FeatureDefinition(
                key="feat_b",
                output_columns=("feat_b",),
                description="B",
                source_label="test",
                temporal_mode="static",
                sample_fn=_sample_b,
            ),
        }

        from cusp.features import sampler as sampler_module
        from cusp.features import registry as registry_module

        original_feature_registry = registry_module.FEATURE_REGISTRY.copy()
        original_resolver = registry_module.resolve_feature_keys
        original_context_factory = sampler_module.create_earth_engine_context
        try:
            registry_module.FEATURE_REGISTRY.clear()
            registry_module.FEATURE_REGISTRY.update(fake_registry)
            sampler_module.FEATURE_REGISTRY.clear()
            sampler_module.FEATURE_REGISTRY.update(fake_registry)

            def _resolve(feature_keys=None, feature_set="base_v1"):
                return ["feat_a", "feat_b"]

            registry_module.resolve_feature_keys = _resolve
            sampler_module.resolve_feature_keys = _resolve
            sampler_module.create_earth_engine_context = lambda project=None: object()

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                input_path = tmp / "cusp_observations.csv"
                output_path = tmp / "cusp_observations_features.csv"
                manifest_path = tmp / "cusp_observations_features_manifest.json"
                raw.to_csv(input_path, index=False)
                raw.assign(feat_a=[1.0, 2.0]).loc[:, ["cusp_obs_id", "date", "lat", "lon", "feat_a"]].to_csv(
                    output_path,
                    index=False,
                )

                result = sample_features_from_path(
                    input_path,
                    output_path=output_path,
                    manifest_path=manifest_path,
                    feature_set=None,
                    feature_keys=["feat_a", "feat_b"],
                    resume=True,
                )
        finally:
            registry_module.FEATURE_REGISTRY.clear()
            registry_module.FEATURE_REGISTRY.update(original_feature_registry)
            sampler_module.FEATURE_REGISTRY.clear()
            sampler_module.FEATURE_REGISTRY.update(original_feature_registry)
            registry_module.resolve_feature_keys = original_resolver
            sampler_module.resolve_feature_keys = original_resolver
            sampler_module.create_earth_engine_context = original_context_factory

        self.assertEqual(calls, ["feat_b"])
        self.assertEqual(result.features["feat_a"].tolist(), [1.0, 2.0])
        self.assertEqual(result.features["feat_b"].tolist(), [3.0, 4.0])
