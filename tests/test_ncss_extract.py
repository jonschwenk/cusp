from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "NCSS_Lab_Data_Mart"
    / "extract_ncss_lab_data_mart_raw.py"
)
SPEC = importlib.util.spec_from_file_location("extract_ncss_lab_data_mart_raw", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NcssFrozenHorizonParserTests(unittest.TestCase):
    def test_accepts_frozen_horizon_suffixes(self) -> None:
        valid = [
            "Cf",
            "Cff",
            "Bgf",
            "Cfg",
            "Oaf",
            "2Cf",
            "Cf/Ojjf",
            "wf/Cf1",
            "1C2f",
            "OajjF1/Cjjg",
            "CjjgF2/Oajj",
            "CF",
            "wCf",
            "A/Of",
            "BCg/Ajjf",
        ]

        for designation in valid:
            with self.subTest(designation=designation):
                self.assertEqual(MODULE.is_frozen_horizon_designation(designation), 1)

    def test_rejects_incidental_f_characters_and_prose(self) -> None:
        invalid = [
            None,
            "",
            "Bkm",
            "Ap",
            "Clay Films",
            "clayfilm cup",
            "Bt of B/E",
            "C1(lfs)",
            "Fe",
            "tILEF",
            "2Bt3",
        ]

        for designation in invalid:
            with self.subTest(designation=designation):
                self.assertEqual(MODULE.is_frozen_horizon_designation(designation), 0)


if __name__ == "__main__":
    unittest.main()
