from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from cusp.build import ALLOWED_METHODS, CANONICAL_COLUMNS
from cusp.qc import (
    check_coordinates,
    check_cusp_obs_id,
    check_dates,
    check_method_values,
    check_negative_depths,
    check_pf_observed_values,
    check_zero_obs_limit,
    ensure_out_dir,
    load_observations_csv,
    write_csv,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "cusp_observations.csv"
OUT_DIR = REPO_ROOT / "outputs" / "qc_tests"
EXPECTED_COLUMNS = ["row_index"] + CANONICAL_COLUMNS


def _write_report_on_failure(df: pd.DataFrame, name: str) -> Path:
    """Write a QC report only when there is something to inspect."""

    path = OUT_DIR / name
    if df.empty:
        return path
    ensure_out_dir(OUT_DIR)
    write_csv(df, path)
    return path


class ObservationQATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not DATA_PATH.exists():
            raise FileNotFoundError(f"Missing dataset CSV: {DATA_PATH}")
        cls.observations_df = load_observations_csv(DATA_PATH)

    def test_canonical_columns(self) -> None:
        self.assertEqual(
            self.observations_df.columns.tolist(),
            EXPECTED_COLUMNS,
            "cusp_observations.csv should contain only the canonical release columns.",
        )

    def test_cusp_obs_id_present_and_unique(self) -> None:
        result = check_cusp_obs_id(self.observations_df)
        _write_report_on_failure(result.details, "invalid_cusp_obs_id.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows with missing or duplicate cusp_obs_id. "
            f"See {OUT_DIR / 'invalid_cusp_obs_id.csv'}.",
        )

    def test_pf_observed_values(self) -> None:
        result = check_pf_observed_values(self.observations_df)
        _write_report_on_failure(result.details, "invalid_pf_observed.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows where pf_observed is not 0/1. "
            f"See {OUT_DIR / 'invalid_pf_observed.csv'}.",
        )

    def test_method_values(self) -> None:
        result = check_method_values(self.observations_df, ALLOWED_METHODS)
        _write_report_on_failure(result.details, "invalid_method.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows with missing or unsupported method values. "
            f"See {OUT_DIR / 'invalid_method.csv'}.",
        )

    def test_coordinates_missing_or_invalid(self) -> None:
        result = check_coordinates(self.observations_df)
        _write_report_on_failure(result.details, "invalid_coordinates.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows with missing/invalid coordinates. "
            f"See {OUT_DIR / 'invalid_coordinates.csv'}.",
        )

    def test_dates_parseable_and_in_range(self) -> None:
        result = check_dates(self.observations_df)
        _write_report_on_failure(result.details, "bad_dates.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows with invalid dates. "
            f"See {OUT_DIR / 'bad_dates.csv'}.",
        )

    def test_depths_non_negative(self) -> None:
        result = check_negative_depths(self.observations_df)
        _write_report_on_failure(result.details, "bad_depths.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows with negative depths. "
            f"See {OUT_DIR / 'bad_depths.csv'}.",
        )

    def test_obs_limit_not_zero(self) -> None:
        result = check_zero_obs_limit(self.observations_df)
        _write_report_on_failure(result.details, "zero_obs_limit.csv")
        self.assertEqual(
            result.count(),
            0,
            f"Found {result.count()} rows with obs_limit == 0. "
            f"See {OUT_DIR / 'zero_obs_limit.csv'}.",
        )


if __name__ == "__main__":
    unittest.main()
