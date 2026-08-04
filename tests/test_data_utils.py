from __future__ import annotations

import unittest

import pandas as pd

from cusp.data_utils import aggregate_gpr_points, process_pf_observations


class AggregateGprPointsTests(unittest.TestCase):
    def test_aggregates_within_site_and_date_only(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "site_id": "A",
                    "date": "2013-08-12",
                    "lat": 71.25,
                    "lon": -156.60,
                    "thaw_depth": 20.0,
                    "method": "gp",
                    "source": "Example",
                },
                {
                    "site_id": "A",
                    "date": "2013-08-12",
                    "lat": 71.25,
                    "lon": -156.60,
                    "thaw_depth": 40.0,
                    "method": "gp",
                    "source": "Example",
                },
                {
                    "site_id": "A",
                    "date": "2014-08-12",
                    "lat": 71.25,
                    "lon": -156.60,
                    "thaw_depth": 60.0,
                    "method": "gp",
                    "source": "Example",
                },
            ]
        )

        result = aggregate_gpr_points(raw)

        self.assertEqual(len(result), 2)
        first_year = result.loc[result["date"].eq("2013-08-12")].iloc[0]
        second_year = result.loc[result["date"].eq("2014-08-12")].iloc[0]
        self.assertEqual(first_year["thaw_depth"], 30.0)
        self.assertEqual(first_year["gpr_native_count"], 2)
        self.assertTrue(first_year["quality_flag_summary_statistic"])
        self.assertEqual(second_year["thaw_depth"], 60.0)
        self.assertEqual(second_year["gpr_native_count"], 1)
        self.assertFalse(second_year["quality_flag_summary_statistic"])

    def test_keeps_distant_cells_separate(self) -> None:
        raw = pd.DataFrame(
            {
                "site_id": ["A", "A"],
                "date": ["2013-08-12", "2013-08-12"],
                "lat": [71.25, 71.251],
                "lon": [-156.60, -156.60],
                "thaw_depth": [20.0, 40.0],
            }
        )

        result = aggregate_gpr_points(raw, spacing_m=5)

        self.assertEqual(len(result), 2)

    def test_rejects_nonpositive_spacing(self) -> None:
        raw = pd.DataFrame(
            {
                "site_id": ["A"],
                "date": ["2013-08-12"],
                "lat": [71.25],
                "lon": [-156.60],
                "thaw_depth": [20.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "positive finite"):
            aggregate_gpr_points(raw, spacing_m=0)


class ProcessPermafrostObservationsTests(unittest.TestCase):
    def test_numeric_depth_is_presence_regardless_of_depth(self) -> None:
        raw = pd.DataFrame(
            {
                "alt": [75.0, 185.0, 200.0],
                "is_lower_bound": [False, False, True],
                "limit": [None, None, 200.0],
                "date": ["2020-08-01"] * 3,
            }
        )

        result = process_pf_observations(
            raw,
            alt_name="alt",
            obs_limit_val=raw["limit"],
            obs_limit_mask=raw["is_lower_bound"],
        )

        self.assertEqual(result["pf_observed"].tolist(), [1, 1, 0])
        self.assertEqual(result.loc[1, "pf_depth"], 185.0)
        self.assertTrue(pd.isna(result.loc[2, "thaw_depth"]))
        self.assertEqual(result.loc[2, "obs_limit"], 200.0)


if __name__ == "__main__":
    unittest.main()
