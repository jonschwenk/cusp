from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cusp.build import (
    CANONICAL_COLUMNS,
    build_release_tables,
    build_source_reference_crosswalk,
    normalize_method,
    write_build_outputs,
)


class BuildTests(unittest.TestCase):
    def test_normalize_method_maps_known_values(self) -> None:
        self.assertEqual(normalize_method("Frost Probe Transect or Grid"), "tp")
        self.assertEqual(normalize_method("Frost Probe Transect or Grid & Borehole"), "tp_pit")
        self.assertEqual(normalize_method("Thaw Tube"), "tt")
        self.assertEqual(normalize_method("tp/pit"), "tp_pit")
        self.assertEqual(normalize_method("aug_pit"), "pit_aug")
        self.assertEqual(normalize_method("unknown"), "unknown")

    def test_build_release_tables_trims_columns_and_logs_deletions(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "source": "Example_A",
                    "site_id": "A1",
                    "lat": 65.0,
                    "lon": -147.0,
                    "date": "2020-08-01",
                    "pf_observed": 1,
                    "thaw_depth": 40.0,
                    "pf_depth": 40.0,
                    "obs_limit": 120.0,
                    "method": "Frost Probe Transect or Grid",
                    "extra_col": "keep",
                },
                {
                    "source": "Example_A",
                    "site_id": "A1",
                    "lat": 65.0,
                    "lon": -147.0,
                    "date": "2020-08-01",
                    "pf_observed": 1,
                    "thaw_depth": 40.0,
                    "pf_depth": 40.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                    "extra_col": "duplicate",
                },
                {
                    "source": "Example_B",
                    "site_id": None,
                    "lat": 0.0,
                    "lon": 0.0,
                    "date": "2020-08-02",
                    "pf_observed": 0,
                    "thaw_depth": None,
                    "pf_depth": None,
                    "obs_limit": 0.0,
                    "method": None,
                    "extra_col": "drop",
                },
                {
                    "source": "Example_C",
                    "site_id": None,
                    "lat": 66.0,
                    "lon": -150.0,
                    "date": "2020-08-03",
                    "pf_observed": 1,
                    "thaw_depth": 25.0,
                    "pf_depth": 25.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                    "extra_col": "warnless",
                },
            ]
        )

        outputs = build_release_tables(raw)

        self.assertEqual(outputs.combined.columns.tolist(), CANONICAL_COLUMNS)
        self.assertEqual(len(outputs.combined), 2)
        self.assertTrue(outputs.combined.iloc[0]["cusp_obs_id"].startswith("obs_"))
        self.assertEqual(outputs.combined.iloc[0]["method"], "tp")
        self.assertIn("cusp_obs_id", outputs.combined_allfields.columns)
        self.assertIn("extra_col", outputs.combined_allfields.columns)
        self.assertEqual(outputs.deleted_rows["build_reason"].tolist(), ["zero_zero_coordinates", "duplicate_required_fields"])
        self.assertEqual(outputs.qc_flags["build_reason"].tolist(), [])

    def test_build_source_reference_crosswalk_filters_to_included_sources(self) -> None:
        combined_md = pd.DataFrame({"source": ["A", "B"]})
        bib = pd.DataFrame(
            {
                "source": ["A", "B", "C"],
                "title": ["Title A", "Title B", "Title C"],
                "doi": ["doi-a", "doi-b", "doi-c"],
            }
        )

        crosswalk = build_source_reference_crosswalk(combined_md, bib)

        self.assertEqual(crosswalk["source"].tolist(), ["A", "B"])
        self.assertEqual(crosswalk["title"].tolist(), ["Title A", "Title B"])

    def test_write_build_outputs_generates_manifest(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "source": "Example_A",
                    "site_id": "A1",
                    "lat": 65.0,
                    "lon": -147.0,
                    "date": "2020-08-01",
                    "pf_observed": 1,
                    "thaw_depth": 40.0,
                    "pf_depth": 45.0,
                    "obs_limit": 120.0,
                    "method": "tp",
                }
            ]
        )
        outputs = build_release_tables(raw)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical = tmp / "combined.csv"
            allfields = tmp / "combined_allfields.csv"
            metadata = tmp / "combined_md.csv"
            deleted = tmp / "combined_deleted_rows.csv"
            flags = tmp / "combined_qc_flags.csv"
            gpkg = tmp / "all_sites.gpkg"
            crosswalk = tmp / "source_reference_crosswalk.csv"
            manifest = tmp / "observation_release_manifest.json"

            write_build_outputs(
                outputs,
                canonical_path=canonical,
                allfields_path=allfields,
                metadata_path=metadata,
                deleted_path=deleted,
                flags_path=flags,
                gpkg_path=gpkg,
                source_reference_path=crosswalk,
                manifest_path=manifest,
            )

            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest_data["build_scope"], "observation_release")
            self.assertEqual(manifest_data["summary"]["combined_rows"], 1)
            self.assertEqual(manifest_data["summary"]["combined_sources"], 1)
            self.assertIn("combined.csv", manifest_data["artifacts"])
            self.assertEqual(manifest_data["artifacts"]["all_sites.gpkg"]["rows"], 1)
            self.assertEqual(manifest_data["artifacts"]["source_reference_crosswalk.csv"]["rows"], 1)


if __name__ == "__main__":
    unittest.main()
