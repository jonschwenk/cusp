from __future__ import annotations

import unittest
from pathlib import Path

from cusp.qc.aggregate import (
    AGGREGATED_COLUMNS,
    check_cusp_30m_id,
    check_membership_integrity,
    check_n_grouped,
    check_pf_observed_fraction,
    load_aggregated_csv,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
AGGREGATED_PATH = REPO_ROOT / "data" / "aggregated_30m.csv"
MEMBERSHIP_PATH = REPO_ROOT / "data" / "aggregated_30m_membership.csv"


class AggregatedQATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aggregated_df = load_aggregated_csv(str(AGGREGATED_PATH))
        cls.membership_df = load_aggregated_csv(str(MEMBERSHIP_PATH))

    def test_aggregated_schema(self) -> None:
        self.assertEqual(self.aggregated_df.columns.tolist(), ["row_index"] + AGGREGATED_COLUMNS)

    def test_cusp_30m_id_present_and_unique(self) -> None:
        result = check_cusp_30m_id(self.aggregated_df)
        self.assertEqual(result.count(), 0)

    def test_pf_observed_fraction_in_range(self) -> None:
        result = check_pf_observed_fraction(self.aggregated_df)
        self.assertEqual(result.count(), 0)

    def test_n_grouped_positive(self) -> None:
        result = check_n_grouped(self.aggregated_df)
        self.assertEqual(result.count(), 0)

    def test_membership_integrity(self) -> None:
        result = check_membership_integrity(self.aggregated_df, self.membership_df)
        self.assertEqual(result.count(), 0)


if __name__ == "__main__":
    unittest.main()
