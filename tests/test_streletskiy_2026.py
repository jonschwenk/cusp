from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "data/Streletskiy_2026"
SPEC = importlib.util.spec_from_file_location("process_streletskiy_2026", HERE / "process_streletskiy_2026.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def candidate(code="NEW1", year=2020, depth="45", **overrides):
    return {
        "ID": 1, "Site_Name": "Example", "SiteCode": code,
        "Lat": 65.0, "Lon": -147.0, "year": year, "ALT": depth,
        "METHOD_PLAIN": "Borehole", "METHOD": "T/B", "Country": "USA",
        "Region": "North America", "Elevation": 10,
        **overrides,
    }


def provider(rows):
    return pd.DataFrame(rows, columns=["calm_site_code", "calm_year", "thaw_depth", "method", "pf_observed", "obs_limit"])


class StreletskiyTests(unittest.TestCase):
    def setUp(self):
        self.calm = provider([("U1", 2020, 45, "tp", 1, np.nan), ("CH2", 2020, np.nan, "temp", 0, 1300)])
        self.south = provider([("A1", 2020, 50, "temp", 1, np.nan)])
        self.permos = pd.DataFrame({"permos_calm_id": ["CH3"], "permos_year": [2020]})
        self.exclusions = {"CH1:2022": {"reason": "unresolved_permos_quality_conflict", "reference": "PERMOS"}}

    def process(self, raw):
        with contextlib.redirect_stdout(io.StringIO()):
            return MODULE.build_processed_table(raw, self.calm, self.south, self.permos, self.exclusions)

    def test_original_sources_win_but_independent_years_remain(self):
        raw = pd.DataFrame([
            candidate("u 1"), candidate("U1", 2021), candidate("U1", 2022),
            candidate("CH2", depth="1300"), candidate("CH3"),
            candidate("A1", depth="50", Lat=-77), candidate("CH1", 2022, "724"),
            candidate("ZERO", depth="0"), candidate("MISSING", depth="-"),
        ], index=[7] * 9)
        before = raw.copy(deep=True)
        result, audit = self.process(raw)
        pd.testing.assert_frame_equal(raw, before)
        self.assertEqual(result.calm_year.tolist(), [2021, 2022])
        self.assertEqual(result.date.tolist(), ["2021-09-01", "2022-09-01"])
        self.assertEqual(audit.decision.tolist(), [
            "calm_republication_retained", "retained", "retained",
            "calm_bound_or_nonexact_retained", "original_permos_retained",
            "original_calm_south_retained", "unresolved_permos_quality_conflict",
            "zero_unresolved", "missing_alt",
        ])
        self.assertEqual(audit.iloc[3].retained_provider_pf_observed, 0)
        self.assertEqual(audit.iloc[3].retained_provider_obs_limit_cm, 1300)
        self.assertTrue(pd.isna(audit.iloc[3].retained_provider_depth_cm))

    def test_depth_and_method_conflicts_are_preserved_in_audit(self):
        _, audit = self.process(pd.DataFrame([candidate("U1", depth="70")]))
        self.assertEqual(audit.iloc[0].decision, "calm_conflict_deferred")
        self.assertEqual(audit.iloc[0].alt_cm, 70)
        self.assertEqual(audit.iloc[0].retained_provider_depth_cm, 45)
        self.assertEqual(audit.iloc[0].retained_provider_method, "tp")

    def test_unrepresented_or_conflicting_southern_row_fails(self):
        for row in [candidate("A999", Lat=-77), candidate("A1", depth="80", Lat=-77)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.process(pd.DataFrame([row]))

    def test_unknown_methods_bounds_and_invalid_coordinates_fail(self):
        for row in [candidate(METHOD_PLAIN="Mystery"), candidate(depth=">90"), candidate(depth="-5"), candidate(Lat=95)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.process(pd.DataFrame([row]))

    def test_duplicate_site_year_or_provider_key_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError, "Duplicate synthesis"):
            self.process(pd.DataFrame([candidate(), candidate()]))
        self.calm = pd.concat([self.calm, self.calm], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Ambiguous provider"):
            self.process(pd.DataFrame([candidate()]))

    def test_full_snapshot_accounting_and_reproducibility(self):
        path = HERE / "CALM_Sites_Data.csv"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), MODULE.RAW_SHA256)
        calm = pd.read_csv(ROOT / "data/CALM/processed_calm.csv", low_memory=False)
        south = pd.read_csv(ROOT / "data/CALM_South/processed_calm_south.csv")
        permos = pd.read_csv(ROOT / "data/PERMOS_2024/processed_permos_2024.csv", low_memory=False)
        exclusions = json.loads((HERE / "review_exclusions.json").read_text())
        with contextlib.redirect_stdout(io.StringIO()):
            result, audit = MODULE.build_processed_table(pd.read_csv(path), calm, south, permos, exclusions)
        self.assertEqual(len(audit), 3500)
        self.assertEqual(audit.decision.value_counts().to_dict(), {
            "calm_republication_retained": 2152, "missing_alt": 801,
            "original_calm_south_retained": 270, "retained": 214,
            "calm_conflict_deferred": 57, "calm_bound_or_nonexact_retained": 3,
            "zero_unresolved": 2, "unresolved_permos_quality_conflict": 1,
        })
        self.assertEqual(result.method.value_counts().to_dict(), {"temp": 210, "tp": 4})
        self.assertEqual(result.site_id.nunique(), 24)
        self.assertTrue(result.lat.gt(0).all())
        self.assertTrue(result.thaw_depth.gt(0).all())
        self.assertFalse(result.duplicated(["site_id", "date"]).any())
        expected = pd.read_csv(HERE / "processed_streletskiy_2026.csv")
        roundtrip = pd.read_csv(io.StringIO(result.to_csv(index=False)))
        pd.testing.assert_frame_equal(roundtrip, expected, check_dtype=False)

    def test_duplicate_permos_keys_require_review(self):
        self.permos = pd.concat([self.permos, self.permos], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Ambiguous PERMOS"):
            self.process(pd.DataFrame([candidate()]))


if __name__ == "__main__":
    unittest.main()
