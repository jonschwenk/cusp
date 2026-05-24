"""CLI for building source-level quality flag metadata."""

from __future__ import annotations

import argparse
from pathlib import Path

from cusp.source_quality_metadata import DEFAULT_OUTPUT, write_source_quality_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build source-level CUSP quality flag metadata.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = write_source_quality_metadata(output_path=args.output)
    print(f"Wrote {args.output} with {len(metadata)} source rows.")


if __name__ == "__main__":
    main()
