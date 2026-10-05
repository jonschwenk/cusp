from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "data/CALM_South"
SPEC = importlib.util.spec_from_file_location("process_calm_south", HERE / "process_calm_south.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(code="A1", year=2020, depth="45", **overrides):
    return {
        "calm_site_code": code, "calm_site_name": "Example site",
        "calm_lat_raw": "77 51'S", "calm_lon_raw": "166 46'E",
        "calm_elevation_m": 38, "calm_method_raw": "T/B",
        "calm_year": year, "calm_ald_raw": depth, "calm_workbook_row": 34,
        **overrides,
    }


class CalmSouthTests(unittest.TestCase):
    def test_coordinate_formats_and_hemisphere_signs(self):
        cases = [
            ("-74.745489", "lat", -74.745489),
            ("62.98S", "lat", -62.98),
            ("77 51'S", "lat", -77.85),
            ('62 11\'54"S', "lat", -62.19833333333333),
            ("69.24.14S", "lat", -69.4038888888889),
            ('62\ufffd38\ufffd59.1"S', "lat", -(62 + 38 / 60 + 59.1 / 3600)),
            ("166 46'E", "lon", 166 + 46 / 60),
        ]
        for value, axis, expected in cases:
            with self.subTest(value=value):
                self.assertAlmostEqual(MODULE.parse_coordinate(value, axis), expected)

    def test_invalid_coordinates_do_not_receive_guessed_repairs(self):
        for value, axis in [("62 98 S", "lat"), ("11.47.76E", "lon"), ("91", "lat"), ("181", "lon"), ("", "lon"), ("nan", "lat"), ("-62W", "lat"), ("-62S", "lat"), ("-62N", "lat"), ("+62S", "lat")]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MODULE.parse_coordinate(value, axis)

    def test_bounds_and_zeros_are_not_flattened(self):
        self.assertEqual(MODULE.parse_depth("90+"), ("lower", 90.0))
        self.assertEqual(MODULE.parse_depth(">130"), ("lower", 130.0))
        self.assertEqual(MODULE.parse_depth("0"), ("zero_unresolved", 0.0))
        self.assertEqual(MODULE.parse_depth("12.5"), ("exact", 12.5))
        self.assertEqual(MODULE.parse_depth("-")[0], "missing")
        with self.assertRaises(ValueError):
            MODULE.parse_depth("about 90")

    def test_native_method_codes(self):
        for code, expected in [("T/B", "temp"), ("T/B3.6", "temp"), ("TT", "tt"), ("100.0", "tp"), ("100/P/B1.3", "tp"), ("70/T/G/B2.0", "unknown"), ("T/100", "unknown")]:
            with self.subTest(code=code):
                self.assertEqual(MODULE.method_from_code(code), expected)

    def test_annual_records_bounds_and_flags_with_duplicate_indices(self):
        raw = pd.DataFrame([
            row(year=2019), row(year=2020, depth="90+"),
            row(code="A7", depth="0"), row(code="A8", depth="-"),
            row(code="A29", calm_lon_raw="45.86W", calm_method_raw="100"),
        ], index=[3] * 5)
        before = raw.copy(deep=True)
        overrides = {"A29": {"lat": -67.665556, "lon": 45.841944, "coordinate_reference": "verified site metadata", "coordinate_note": "Sign error"}}
        with contextlib.redirect_stdout(io.StringIO()):
            result, audit = MODULE.build_processed_table(raw, overrides)
        pd.testing.assert_frame_equal(raw, before)
        self.assertEqual(len(result), 3)
        self.assertEqual(audit.decision.tolist(), ["retained", "retained", "zero_unresolved", "missing", "retained"])
        bound = result.loc[result.obs_limit.notna()].iloc[0]
        self.assertEqual(bound.pf_observed, 0)
        self.assertEqual(bound.obs_limit, 90)
        self.assertTrue(pd.isna(bound.thaw_depth))
        self.assertTrue(pd.isna(bound.pf_depth))
        self.assertEqual(bound.date, "2020-02-01")
        corrected = result.loc[result.site_id.eq("CALM_A29")].iloc[0]
        self.assertGreater(corrected.lon, 0)
        self.assertTrue(corrected.quality_flag_coord_lookup_or_interpolated)
        self.assertTrue(corrected.quality_flag_coord_source_flagged)
        self.assertEqual(corrected.calm_lon_raw, "45.86W")

    @unittest.skipUnless(importlib.util.find_spec("xlrd"), "Raw XLS integration needs the optional source-processing extra")
    def test_original_workbook_accounting_and_reproducibility(self):
        path = HERE / "CALM_S_Summary.xls"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), MODULE.RAW_SHA256)
        overrides = json.loads((HERE / "site_overrides.json").read_text())["sites"]
        with contextlib.redirect_stdout(io.StringIO()):
            result, audit = MODULE.build_processed_table(MODULE.read_workbook(path), overrides)
        self.assertEqual(len(audit), 1332)
        self.assertEqual(audit.decision.value_counts().to_dict(), {"missing": 893, "retained": 437, "zero_unresolved": 2})
        self.assertEqual(result.pf_observed.value_counts().to_dict(), {1: 426, 0: 11})
        self.assertEqual(result.site_id.nunique(), 31)
        self.assertFalse(result.duplicated(["site_id", "date"]).any())
        self.assertEqual(result.method.value_counts().to_dict(), {"temp": 323, "tp": 107, "unknown": 7})
        expected = pd.read_csv(HERE / "processed_calm_south.csv", keep_default_na=True)
        roundtrip = pd.read_csv(io.StringIO(result.to_csv(index=False)))
        pd.testing.assert_frame_equal(roundtrip, expected, check_dtype=False)


if __name__ == "__main__":
    unittest.main()
