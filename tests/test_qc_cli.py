from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cusp.qc.cli import run_aggregated_validation, run_observations_audit, run_observations_validation


REPO_ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS_PATH = REPO_ROOT / "data" / "cusp_observations.csv"
AGGREGATED_PATH = REPO_ROOT / "data" / "aggregated_30m.csv"
MEMBERSHIP_PATH = REPO_ROOT / "data" / "aggregated_30m_membership.csv"


class QcCliTests(unittest.TestCase):
    def test_run_observations_validation_on_current_release_outputs(self) -> None:
        result = run_observations_validation(OBSERVATIONS_PATH)
        self.assertTrue(result.ok)
        self.assertEqual(result.summary["counts"]["schema_mismatch"], 0)

    def test_run_aggregated_validation_on_current_release_outputs(self) -> None:
        result = run_aggregated_validation(AGGREGATED_PATH, membership_path=MEMBERSHIP_PATH)
        self.assertTrue(result.ok)
        self.assertEqual(result.summary["counts"]["schema_mismatch"], 0)

    def test_run_observations_audit_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "qc_audit"
            payload = run_observations_audit(OBSERVATIONS_PATH, out_dir=out_dir)

            self.assertEqual(payload["input_path"], str(OBSERVATIONS_PATH))
            self.assertTrue((out_dir / "qc_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
