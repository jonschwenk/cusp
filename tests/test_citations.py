from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from cusp.citations import (
    build_bibtex_subset,
    extract_bibtex_for_table,
    extract_source_keys,
    parse_bibtex_entries,
)


class CitationsTests(unittest.TestCase):
    def test_extract_source_keys_from_observation_table(self) -> None:
        df = pd.DataFrame({"source": ["A", "B", "A", None]})
        self.assertEqual(extract_source_keys(df), ["A", "B"])

    def test_extract_source_keys_from_aggregation_table(self) -> None:
        df = pd.DataFrame({"aggregated_sources": ["A;B", "B; C", "C,D", None]})
        self.assertEqual(extract_source_keys(df), ["A", "B", "C", "D"])

    def test_extract_source_keys_from_aggregation_table_with_commas(self) -> None:
        df = pd.DataFrame({"aggregated_sources": ["A,B", "B, C", None]})
        self.assertEqual(extract_source_keys(df), ["A", "B", "C"])

    def test_parse_bibtex_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "sources.bib"
            bib_path.write_text(
                "@misc{A,\n  title = {Title A},\n}\n\n@article{B,\n  title = {Title B},\n}\n",
                encoding="utf-8",
            )
            entries = parse_bibtex_entries(bib_path)
            self.assertEqual(sorted(entries), ["A", "B"])
            self.assertIn("Title A", entries["A"])

    def test_build_bibtex_subset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir) / "sources.bib"
            bib_path.write_text(
                "@misc{A,\n  title = {Title A},\n}\n\n@article{B,\n  title = {Title B},\n}\n",
                encoding="utf-8",
            )
            bib_text, missing = build_bibtex_subset(["B", "A", "C"], master_bib_path=bib_path)
            self.assertIn("@article{B", bib_text)
            self.assertIn("@misc{A", bib_text)
            self.assertEqual(missing, ["C"])

    def test_extract_bibtex_for_table_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            table_path = tmp / "subset.csv"
            bib_path = tmp / "sources.bib"

            pd.DataFrame({"source": ["A", "B"]}).to_csv(table_path, index=False)
            bib_path.write_text(
                "@misc{A,\n  title = {Title A},\n}\n\n@article{B,\n  title = {Title B},\n}\n",
                encoding="utf-8",
            )

            bib_text, source_keys, missing = extract_bibtex_for_table(table_path, master_bib_path=bib_path)
            self.assertEqual(source_keys, ["A", "B"])
            self.assertEqual(missing, [])
            self.assertIn("Title A", bib_text)
            self.assertIn("Title B", bib_text)


if __name__ == "__main__":
    unittest.main()
