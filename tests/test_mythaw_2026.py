"""Regression checks for the source's caps, copy protocols and dated field notes."""

import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "data/MyThaw_2026/process_mythaw_2026.py"
SPEC = importlib.util.spec_from_file_location("mythaw", SOURCE)
mythaw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mythaw)


class MyThawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = mythaw.rows_from_archive()

    def find(self, year, site, day, point):
        return next(row for row in self.rows if row["_year"] == year and row["Site"] == site
                    and row["Date/Time"][:10] == day and row[mythaw.POINT] and row[mythaw.DEPTH]
                    and int(float(row[mythaw.POINT])) == point)

    def test_limit_and_stone_stops_are_distinct(self):
        capped = self.find(2022, "Bayelva", "2022-09-06", 0)
        stone = self.find(2022, "Bayelva", "2022-09-06", 2)
        self.assertEqual(mythaw.decision(capped, 2022), "retained_lower_bound")
        self.assertEqual(mythaw.decision(stone, 2022), "excluded_source_stone_stop")

    def test_whole_degree_coordinates_use_precise_site_location(self):
        row = next(row for row in self.rows if row["_year"] == 2022
                   and row["Site"] == "Toolik Field Station" and row[mythaw.DEPTH])
        result = mythaw.transformed(row)
        self.assertEqual(result["lat"], row["Latitude descr (latitude of site in deg)"])
        self.assertNotEqual(float(result["lat"]), float(result["upstream_transect_lat"]))

    def test_source_date_correction_is_point_specific(self):
        early = mythaw.transformed(self.find(2023, "Bayelva", "2023-07-31", 2))
        late = mythaw.transformed(self.find(2023, "Bayelva", "2023-07-31", 4))
        self.assertEqual(early["date"], "2023-07-28")
        self.assertEqual(late["date"], "2023-07-31")

    def test_duplicate_protocols_require_raw_agreement(self):
        mythaw.verify_protocol_copies(self.rows)
        changed = [dict(row) for row in self.rows]
        next(row for row in changed if row["Protocol ID"] == "4846957")[mythaw.DEPTH] = "999"
        with self.assertRaises(ValueError):
            mythaw.verify_protocol_copies(changed)

    def test_rock_comment_applies_to_named_point(self):
        rock = self.find(2022, "Northern Border of Russel Glacier", "2022-08-23", 0)
        other = self.find(2022, "Northern Border of Russel Glacier", "2022-08-23", 1)
        self.assertEqual(mythaw.decision(rock, 2022), "excluded_source_stone_stop")
        self.assertEqual(mythaw.decision(other, 2022), "retained_seasonal_thaw")

    def test_undocumented_long_rod_is_deferred(self):
        row = self.find(2024, "Bayelva", "2024-09-10", 1)
        self.assertEqual(mythaw.decision(row, 2024), "excluded_protocol_length_conflict")


if __name__ == "__main__":
    unittest.main()
