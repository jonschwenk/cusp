from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "Pastick" / "process_pastick.py"
)
SPEC = importlib.util.spec_from_file_location("process_pastick", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PastickNcssOverlapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.ncss_path = (
            self.root / "data" / "NCSS_Lab_Data_Mart" / "processed_ncss_lab_data_mart.csv"
        )
        self.ncss_path.parent.mkdir(parents=True)
        pd.DataFrame(
            [{"lat": 65.0, "lon": -147.0, "pf_observed": 1}]
        ).to_csv(self.ncss_path, index=False)
        root_patch = patch.object(MODULE, "_ROOT_DIR", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    @staticmethod
    def row(**overrides) -> dict:
        return {
            "site_id": "123",
            "lat": 65.0,
            "lon": -147.0,
            "pf_observed": 1,
            "method": "pit",
            **overrides,
        }

    def test_shared_index_does_not_remove_unmatched_rows(self) -> None:
        data = pd.DataFrame(
            [
                self.row(),
                self.row(site_id="456", lat=66.0),
                self.row(method="tp"),
                self.row(method="pit_aug"),
                self.row(method="unknown"),
                self.row(site_id="field-site"),
                self.row(pf_observed=0),
            ],
            index=[7] * 7,
        )
        before = data.copy(deep=True)
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            result = MODULE.remove_ncss_overlaps(data)

        pd.testing.assert_frame_equal(result, data.iloc[1:])
        pd.testing.assert_frame_equal(data, before)
        self.assertIn("Removed 1 Pastick rows", log.getvalue())

    def test_counts_matching_rows_not_distinct_index_labels(self) -> None:
        data = pd.DataFrame(
            [self.row(), self.row(site_id="456"), self.row(method="tp")],
            index=["shared"] * 3,
        )
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            result = MODULE.remove_ncss_overlaps(data)

        pd.testing.assert_frame_equal(result, data.iloc[2:])
        self.assertIn("Removed 2 Pastick rows", log.getvalue())

    def test_distance_threshold_and_missing_values(self) -> None:
        data = pd.DataFrame(
            [
                self.row(lat=65.000005),  # Approximately 0.56 m from NCSS.
                self.row(lat=65.000020),  # Approximately 2.22 m from NCSS.
                self.row(lat=None),
                self.row(lon=None),
                self.row(pf_observed=None),
                self.row(site_id=None),
            ],
            index=[8, 2, 8, 2, 8, 2],
        )
        with contextlib.redirect_stdout(io.StringIO()):
            result = MODULE.remove_ncss_overlaps(data)
            wider_result = MODULE.remove_ncss_overlaps(data, threshold_m=3.0)

        pd.testing.assert_frame_equal(result, data.iloc[1:])
        pd.testing.assert_frame_equal(wider_result, data.iloc[2:])

    def test_no_matches_preserves_rows_and_index(self) -> None:
        data = pd.DataFrame(
            [self.row(lat=66.0), self.row(pf_observed=0)], index=[4, 4]
        )
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            result = MODULE.remove_ncss_overlaps(data)

        pd.testing.assert_frame_equal(result, data)
        self.assertIsNot(result, data)
        self.assertEqual(log.getvalue(), "")

    def test_empty_input_is_preserved(self) -> None:
        data = pd.DataFrame([self.row()]).iloc[:0]
        result = MODULE.remove_ncss_overlaps(data)
        pd.testing.assert_frame_equal(result, data)

    def test_missing_ncss_file_fails_explicitly(self) -> None:
        self.ncss_path.unlink()
        with self.assertRaisesRegex(FileNotFoundError, "required for Pastick"):
            MODULE.remove_ncss_overlaps(pd.DataFrame([self.row()]))


if __name__ == "__main__":
    unittest.main()
