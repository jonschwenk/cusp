from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cusp.aggregate import (
    build_aggregation_tables,
    write_aggregation_outputs,
)


class AggregateTests(unittest.TestCase):
    def test_aggregation_splits_by_temporal_linkage_and_builds_membership(self) -> None:
        canonical = pd.DataFrame(
            [
                {
                    "cusp_obs_id": "obs_a",
                    "source": "A",
                    "site_id": "S1",
                    "lat": 65.0,
                    "lon": -147.0,
                    "date": "2020-06-01",
                    "pf_observed": 0,
                    "thaw_depth": 20.0,
                    "pf_depth": 20.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                },
                {
                    "cusp_obs_id": "obs_b",
                    "source": "A",
                    "site_id": "S1",
                    "lat": 65.00001,
                    "lon": -147.00001,
                    "date": "2020-08-15",
                    "pf_observed": 1,
                    "thaw_depth": 60.0,
                    "pf_depth": 60.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                },
                {
                    "cusp_obs_id": "obs_c",
                    "source": "B",
                    "site_id": "S2",
                    "lat": 65.00002,
                    "lon": -147.00002,
                    "date": "2020-08-20",
                    "pf_observed": 1,
                    "thaw_depth": 80.0,
                    "pf_depth": 80.0,
                    "obs_limit": 150.0,
                    "method": "pit",
                },
            ]
        )

        outputs = build_aggregation_tables(canonical, distance_m=30.0, temporal_link_days=31)

        self.assertEqual(len(outputs.aggregated), 2)
        row = outputs.aggregated.loc[outputs.aggregated["n_grouped"] == 2].iloc[0]
        self.assertTrue(row["cusp_30m_id"].startswith("agg30m_"))
        self.assertEqual(row["year"], 2020)
        self.assertEqual(row["date"], "2020-08-20")
        self.assertEqual(row["n_grouped"], 2)
        self.assertEqual(row["pf_observed"], 1.0)
        self.assertEqual(row["method"], "mixed")
        self.assertEqual(row["aggregated_sources"], "A,B")

        self.assertCountEqual(outputs.membership["cusp_obs_id"].tolist(), ["obs_a", "obs_b", "obs_c"])
        self.assertEqual(len(outputs.excluded_rows), 0)
        self.assertCountEqual(outputs.qc_flags["flag"].tolist(), ["mixed_method", "mixed_source", "multi_date_window"])

    def test_aggregation_pf_observed_is_fraction_when_mixed(self) -> None:
        canonical = pd.DataFrame(
            [
                {
                    "cusp_obs_id": "obs_1",
                    "source": "A",
                    "site_id": "S1",
                    "lat": 66.0,
                    "lon": -150.0,
                    "date": "2021-08-01",
                    "pf_observed": 0,
                    "thaw_depth": 20.0,
                    "pf_depth": 20.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                },
                {
                    "cusp_obs_id": "obs_2",
                    "source": "B",
                    "site_id": "S2",
                    "lat": 66.00001,
                    "lon": -150.00001,
                    "date": "2021-08-05",
                    "pf_observed": 1,
                    "thaw_depth": 50.0,
                    "pf_depth": 50.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                },
            ]
        )

        outputs = build_aggregation_tables(canonical, distance_m=30.0, temporal_link_days=31)

        self.assertEqual(len(outputs.aggregated), 1)
        self.assertEqual(outputs.aggregated.iloc[0]["pf_observed"], 0.5)
        self.assertEqual(outputs.aggregated.iloc[0]["method"], "tp")
        self.assertIn("mixed_pf_observed", outputs.qc_flags["flag"].tolist())

    def test_write_aggregation_outputs_generates_manifest(self) -> None:
        canonical = pd.DataFrame(
            [
                {
                    "cusp_obs_id": "obs_1",
                    "source": "A",
                    "site_id": "S1",
                    "lat": 65.0,
                    "lon": -147.0,
                    "date": "2020-08-01",
                    "pf_observed": 1,
                    "thaw_depth": 40.0,
                    "pf_depth": 40.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                }
            ]
        )
        outputs = build_aggregation_tables(canonical, distance_m=30.0, temporal_link_days=31)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            aggregated = tmp / "aggregated_30m.csv"
            membership = tmp / "aggregated_30m_membership.csv"
            flags = tmp / "aggregated_30m_qc_flags.csv"
            excluded = tmp / "aggregated_30m_excluded_rows.csv"
            gpkg = tmp / "aggregated_30m.gpkg"
            manifest = tmp / "aggregated_30m_manifest.json"

            write_aggregation_outputs(
                outputs,
                aggregated_path=aggregated,
                membership_path=membership,
                flags_path=flags,
                excluded_path=excluded,
                gpkg_path=gpkg,
                manifest_path=manifest,
                distance_m=30.0,
                temporal_link_days=31,
            )

            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest_data["build_scope"], "aggregated_30m_release")
            self.assertEqual(manifest_data["summary"]["aggregated_rows"], 1)
            self.assertEqual(manifest_data["summary"]["membership_rows"], 1)
            self.assertEqual(manifest_data["summary"]["excluded_rows"], 0)
            self.assertIn("aggregated_30m.csv", manifest_data["artifacts"])


if __name__ == "__main__":
    unittest.main()
