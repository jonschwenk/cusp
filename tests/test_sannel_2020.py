"""Guard the difference between a probe limit and measured permafrost depth."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sannel_processor", ROOT / "data/Sannel_2020/process_sannel_2020.py"
)
PROCESSOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROCESSOR)


class SannelSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.sites = {"B8": "68°27.720′N", "C8": "20°54.118′E", "D8": "Peat plateau"}

    def test_probe_limit_has_no_exact_depth(self):
        row = PROCESSOR.make_record(1, "2010-09-02", ">100 (>100, >100, >100)",
                                    self.sites, installation=False)
        self.assertEqual(row["pf_observed"], 0)
        self.assertEqual(row["obs_limit"], 100)
        self.assertIsNone(row["pf_depth"])
        self.assertIsNone(row["thaw_depth"])
        self.assertTrue(row["quality_flag_lower_bound_absence"])

    def test_unsampled_water_has_no_presence_claim(self):
        row = PROCESSOR.make_record(1, "2010-09-02", "No data (in water)",
                                    self.sites, installation=False)
        self.assertEqual(row["decision"], "excluded_in_water")
        self.assertIsNone(row["pf_observed"])
        self.assertIsNone(row["obs_limit"])

    def test_mean_preserves_source_rounding(self):
        row = PROCESSOR.make_record(1, "2010-09-02", "57 (57, 57, 58)",
                                    self.sites, installation=False)
        self.assertEqual(row["thaw_depth"], 57)
        self.assertTrue(row["quality_flag_summary_statistic"])
        self.assertEqual(row["upstream_measurement"], "57 (57, 57, 58)")


if __name__ == "__main__":
    unittest.main()
