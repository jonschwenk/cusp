"""
Generate and validate parseable metadata extracted from source-processing script
module docstrings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cusp.process_script_metadata import (
    DEFAULT_OUTPUT,
    REPO_ROOT,
    build_metadata_records,
    discover_process_scripts,
    is_process_script,
    metadata_csv_matches,
    path_display,
    summarize_records,
    write_metadata_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate PROCESS_SCRIPT_METADATA.csv from structured process-script docstrings."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional specific process scripts to validate/generate. Defaults to all scripts under data/.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output CSV path. Default: PROCESS_SCRIPT_METADATA.csv in the repo root.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate metadata and print a summary without treating CSV generation as the primary goal.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require structured metadata for every targeted script.",
    )
    return parser.parse_args()


def resolve_script_paths(raw_paths: list[str]) -> list[Path]:
    if not raw_paths:
        return discover_process_scripts(REPO_ROOT)

    paths: list[Path] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (REPO_ROOT / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"{raw_path} does not exist")
        if not is_process_script(path):
            raise ValueError(f"{raw_path} is not a recognized process script")
        paths.append(path)
    return sorted(paths)


def main() -> int:
    args = parse_args()
    script_paths = resolve_script_paths(args.paths)
    records = build_metadata_records(script_paths, strict=args.strict)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path

    has_errors = any(int(record["validation_error_count"]) > 0 for record in records)
    if args.check:
        is_stale = not args.paths and not metadata_csv_matches(records, output_path)
        if is_stale:
            print(
                f"{path_display(output_path)} is missing or stale; regenerate it without --check.",
                file=sys.stderr,
            )
        else:
            scope = "targeted scripts" if args.paths else path_display(output_path)
            print(f"Validated {len(records)} records against {scope} without writing files")
        print(summarize_records(records))
        return 1 if has_errors or is_stale else 0

    write_metadata_csv(records, output_path)
    print(f"Wrote {len(records)} records to {path_display(output_path)}")
    print(summarize_records(records))

    if args.strict:
        return 1 if has_errors else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
