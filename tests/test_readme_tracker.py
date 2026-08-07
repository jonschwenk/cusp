from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cusp.readme_tracker import (
    TRACKER_END,
    TRACKER_START,
    find_latest_release_csv,
    summarize_release,
    synchronize_readme,
)


class ReadmeTrackerTests(unittest.TestCase):
    def _write_release(self, path: Path) -> None:
        pd.DataFrame(
            {
                "source": ["A", "A", "B", "C"],
                "pf_observed": [1, 0, 1, 0],
                "thaw_depth": [25.0, None, 40.0, None],
            }
        ).to_csv(path, index=False)

    def test_summarize_release_uses_canonical_observation_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            release_csv = Path(tmpdir) / "cusp_v2.3.csv"
            self._write_release(release_csv)

            tracker = summarize_release(release_csv)

            self.assertEqual(tracker.version, "v2.3")
            self.assertEqual(tracker.total_observations, 4)
            self.assertEqual(tracker.presence_observations, 2)
            self.assertEqual(tracker.absence_observations, 2)
            self.assertEqual(tracker.alt_observations, 2)
            self.assertEqual(tracker.source_count, 3)

    def test_synchronize_readme_updates_only_generated_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            release_csv = tmp / "cusp_v2.3.csv"
            readme = tmp / "README.md"
            self._write_release(release_csv)
            readme.write_text(
                f"# Before\n\n{TRACKER_START}\nstale\n{TRACKER_END}\n\nAfter\n",
                encoding="utf-8",
            )

            self.assertTrue(synchronize_readme(readme_path=readme, release_csv=release_csv))
            updated = readme.read_text(encoding="utf-8")
            self.assertIn("# Before", updated)
            self.assertIn("After", updated)
            self.assertIn(">v2.3</a>", updated)
            self.assertIn("<strong>4</strong><br><sub>Total observations</sub>", updated)
            self.assertIn("<strong>3</strong><br><sub>Included sources</sub>", updated)
            self.assertTrue(synchronize_readme(readme_path=readme, release_csv=release_csv, check=True))

    def test_check_detects_stale_tracker_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            release_csv = tmp / "cusp_v2.3.csv"
            readme = tmp / "README.md"
            self._write_release(release_csv)
            stale = f"{TRACKER_START}\nstale\n{TRACKER_END}\n"
            readme.write_text(stale, encoding="utf-8")

            self.assertFalse(synchronize_readme(readme_path=readme, release_csv=release_csv, check=True))
            self.assertEqual(readme.read_text(encoding="utf-8"), stale)

    def test_find_latest_release_requires_one_versioned_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            latest = Path(tmpdir)
            release_csv = latest / "cusp_v2.3.csv"
            self._write_release(release_csv)
            (latest / "cusp_features_v2.3.csv").write_text("ignored\n", encoding="utf-8")

            self.assertEqual(find_latest_release_csv(latest), release_csv)


if __name__ == "__main__":
    unittest.main()
