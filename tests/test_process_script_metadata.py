from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cusp.process_script_metadata import build_metadata_record, parse_structured_metadata


STRUCTURED_DOCSTRING = """
metadata_schema_version = 1
source_key = "Example_Source"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jschwenk"
last_substantive_update = "2026-04-10"
source_dataset = '''
Example dataset citation.
'''
processing_assumptions = ["Assumption one."]
temporal_handling = ["Per-record dates are preserved."]
spatial_handling = ["Coordinates are already in WGS84."]
manual_steps = []
known_limitations = ["Still a synthetic example."]
external_dependencies = []
notes = ""
"""


class ProcessScriptMetadataTests(unittest.TestCase):
    def test_parse_structured_docstring(self) -> None:
        status, metadata, errors = parse_structured_metadata(
            STRUCTURED_DOCSTRING,
            Path("/tmp/data/Example_Source/process_example_source.py"),
        )
        self.assertEqual(status, "structured_toml")
        self.assertEqual(metadata["source_key"], "Example_Source")
        self.assertEqual(errors, [])

    def test_parse_legacy_docstring(self) -> None:
        status, metadata, errors = parse_structured_metadata(
            "Legacy free-form docstring",
            Path("/tmp/data/Example_Source/process_example_source.py"),
        )
        self.assertEqual(status, "legacy_unstructured")
        self.assertEqual(metadata, {})
        self.assertEqual(errors, [])

    def test_build_record_flags_validation_error_for_source_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            script_path = repo_root / "data" / "Example_Source" / "process_example_source.py"
            script_path.parent.mkdir(parents=True)
            script_path.write_text(
                '"""\n'
                + STRUCTURED_DOCSTRING.replace('source_key = "Example_Source"', 'source_key = "Wrong_Source"')
                + '"""\n'
                "source = 'Example_Source'\n",
                encoding="utf-8",
            )

            processed_path = script_path.parent / "processed_example_source.csv"
            processed_path.write_text("site_id\nexample\n", encoding="utf-8")

            record = build_metadata_record(script_path)
            self.assertEqual(record["metadata_status"], "structured_toml")
            self.assertEqual(record["structured_metadata_present"], "yes")
            self.assertGreater(int(record["validation_error_count"]), 0)
            self.assertIn("does not match source directory", record["validation_errors"])


if __name__ == "__main__":
    unittest.main()
