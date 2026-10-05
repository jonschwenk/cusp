from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "data/Crater_Lake_AERT_2024"
SPEC = importlib.util.spec_from_file_location("process_crater_lake_aert_2024", HERE / "process_crater_lake_aert_2024.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CraterLakeProbeTests(unittest.TestCase):
    def build(self, raw):
        with contextlib.redirect_stdout(io.StringIO()):
            return MODULE.build_processed_table(raw)

    def test_pinned_input_accounting_and_offline_reproduction(self):
        path = HERE / "probing_data.txt"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), MODULE.RAW_SHA256)
        raw = pd.read_csv(path, sep="\t")
        before = raw.copy(deep=True)
        result, audit = self.build(raw)
        pd.testing.assert_frame_equal(raw, before)
        self.assertEqual(len(result), 10)
        self.assertEqual(audit.decision.value_counts().to_dict(),
                         {"retained_direct_probe": 10, "excluded_derived_mean": 5})
        self.assertEqual(result.site_id.nunique(), 2)
        self.assertEqual(result.date.nunique(), 5)
        self.assertFalse(result.duplicated(["site_id", "date"]).any())
        self.assertEqual(result.thaw_depth.tolist(), [34, 33, 33, 30, 29.5, 26, 29.5, 29.5, 34, 35])
        self.assertTrue(result.pf_observed.eq(1).all())
        self.assertTrue(result.method.eq("tp").all())
        self.assertTrue(result.obs_limit.isna().all())
        self.assertTrue(result.pf_depth.eq(result.thaw_depth).all())
        self.assertTrue(result.quality_flag_coord_site_level.all())
        self.assertTrue(result.quality_flag_possible_duplicate_or_overlap.all())
        self.assertEqual(result.lat.nunique(), 1)
        self.assertAlmostEqual(result.lat.iloc[0], -(62 + 59 / 60 + 6.7 / 3600))
        self.assertAlmostEqual(result.lon.iloc[0], -(60 + 40 / 60 + 44.8 / 3600))
        expected = pd.read_csv(HERE / "processed_crater_lake_aert_2024.csv")
        roundtrip = pd.read_csv(io.StringIO(result.to_csv(index=False)))
        pd.testing.assert_frame_equal(roundtrip, expected, check_dtype=False)

    def test_ambiguous_values_or_repeated_dates_require_review(self):
        raw = pd.DataFrame({"date": ["2020-02-15"], "[3,2]": [34], "[3,3]": [35], "mean": [34.5]})
        for value in [0, -1, None, float("inf"), "refusal"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.build(raw.assign(**{"[3,2]": value}))
        with self.assertRaises(ValueError):
            self.build(pd.concat([raw, raw]))
        with self.assertRaises(ValueError):
            self.build(raw.assign(date="2020-02"))
        with self.assertRaises(ValueError):
            self.build(raw.rename(columns={"[3,2]": "unknown node"}))


if __name__ == "__main__":
    unittest.main()
