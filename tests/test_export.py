from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cusp.export import export_release_bundle, normalize_dataset_version


class ExportTests(unittest.TestCase):
    def test_normalize_dataset_version(self) -> None:
        self.assertEqual(normalize_dataset_version("1.0"), "v1.0")
        self.assertEqual(normalize_dataset_version("v2.3"), "v2.3")
        with self.assertRaises(ValueError):
            normalize_dataset_version("1.0.0")

    def test_export_release_bundle_writes_flat_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical_path = tmp / "cusp_observations.csv"
            features_path = tmp / "cusp_observations_features.csv"
            bib_path = tmp / "sources.bib"
            export_root = tmp / "exports"

            canonical = pd.DataFrame(
                {
                    "cusp_obs_id": ["obs_a", "obs_b"],
                    "source": ["A", "B"],
                    "site_id": ["s1", "s2"],
                    "lat": [10.0, 11.0],
                    "lon": [20.0, 21.0],
                    "date": ["2020-08-01", "2020-08-02"],
                    "pf_observed": [1, 0],
                    "thaw_depth": [30.0, 40.0],
                    "pf_depth": [30.0, 40.0],
                    "obs_limit": [None, None],
                    "method": ["tp", "pit"],
                    "quality_flags": ["", "LB"],
                }
            )
            canonical.to_csv(canonical_path, index=False)

            features = pd.DataFrame(
                {
                    "cusp_obs_id": ["obs_a", "obs_b"],
                    "sand": [0.1, 0.2],
                    "soil_oc": [10.0, 20.0],
                }
            )
            features.to_csv(features_path, index=False)

            bib_path.write_text(
                "@misc{A,\n  title = {Title A},\n}\n\n@article{B,\n  title = {Title B},\n}\n",
                encoding="utf-8",
            )

            archived_dir, latest_dir = export_release_bundle(
                dataset_version="1.0",
                canonical_input=canonical_path,
                features_input=features_path,
                master_bib_input=bib_path,
                export_root=export_root,
                changes_markdown="- Initial release.\n",
            )

            self.assertTrue((archived_dir / "cusp_v1.0.csv").exists())
            self.assertTrue((archived_dir / "cusp_features_v1.0.csv").exists())
            self.assertTrue((archived_dir / "cusp_sources_v1.0.bib").exists())
            self.assertTrue((archived_dir / "RELEASE_INFO.md").exists())
            self.assertTrue((latest_dir / "cusp_v1.0.csv").exists())
            self.assertTrue((latest_dir / "cusp_features_v1.0.csv").exists())

            release_info = (archived_dir / "RELEASE_INFO.md").read_text(encoding="utf-8")
            self.assertIn("CUSP Release v1.0", release_info)
            self.assertIn("cusp_v1.0.csv", release_info)

    def test_export_rejects_non_observation_feature_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical_path = tmp / "cusp_observations.csv"
            features_path = tmp / "agg_features.csv"
            bib_path = tmp / "sources.bib"

            canonical = pd.DataFrame(
                {
                    "cusp_obs_id": ["obs_a"],
                    "source": ["A"],
                    "site_id": ["s1"],
                    "lat": [10.0],
                    "lon": [20.0],
                    "date": ["2020-08-01"],
                    "pf_observed": [1],
                    "thaw_depth": [30.0],
                    "pf_depth": [30.0],
                    "obs_limit": [None],
                    "method": ["tp"],
                    "quality_flags": [""],
                }
            )
            canonical.to_csv(canonical_path, index=False)
            pd.DataFrame({"cusp_30m_id": ["agg_a"], "soil_oc": [1.0]}).to_csv(features_path, index=False)
            bib_path.write_text("@misc{A,\n  title = {Title A},\n}\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                export_release_bundle(
                    dataset_version="1.0",
                    canonical_input=canonical_path,
                    features_input=features_path,
                    master_bib_input=bib_path,
                    export_root=tmp / "exports",
                )


if __name__ == "__main__":
    unittest.main()
