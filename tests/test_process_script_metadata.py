from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cusp.generate_process_script_metadata as metadata_cli
from cusp.process_script_metadata import (
    CSV_COLUMNS,
    REPO_ROOT,
    build_metadata_record,
    metadata_csv_matches,
    parse_structured_metadata,
    path_display,
    write_metadata_csv,
)


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
    def test_path_display_uses_portable_separators(self) -> None:
        path = REPO_ROOT / "data" / "Example_Source" / "process_example_source.py"
        self.assertEqual(
            path_display(path),
            "data/Example_Source/process_example_source.py",
        )

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

    def test_metadata_csv_match_requires_exact_columns_and_records(self) -> None:
        record = {column: "" for column in CSV_COLUMNS}
        record["source_directory"] = "Example_Source"
        record["validation_error_count"] = "0"

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "metadata.csv"
            write_metadata_csv([record], output)
            self.assertTrue(metadata_csv_matches([record], output))

            changed = dict(record)
            changed["notes"] = "changed"
            self.assertFalse(metadata_csv_matches([changed], output))

    def test_check_mode_detects_stale_csv_without_writing(self) -> None:
        record = {column: "" for column in CSV_COLUMNS}
        record["source_directory"] = "Example_Source"
        record["validation_error_count"] = "0"

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "metadata.csv"
            output.write_text("stale\n", encoding="utf-8")
            args = SimpleNamespace(
                paths=[],
                output=str(output),
                check=True,
                strict=True,
            )
            with (
                patch.object(metadata_cli, "parse_args", return_value=args),
                patch.object(metadata_cli, "resolve_script_paths", return_value=[]),
                patch.object(metadata_cli, "build_metadata_records", return_value=[record]),
                patch.object(metadata_cli, "write_metadata_csv") as write_mock,
            ):
                exit_code = metadata_cli.main()

            self.assertEqual(exit_code, 1)
            write_mock.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "stale\n")


if __name__ == "__main__":
    unittest.main()
