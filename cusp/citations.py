"""Extract BibTeX entries for sources used in a CUSP table."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from cusp.data_utils import _ROOT_DIR


DATA_DIR = _ROOT_DIR / "data"
DEFAULT_MASTER_BIB_PATH = DATA_DIR / "cusp_sources.bib"


def load_cusp_table(path: Path) -> pd.DataFrame:
    """Load a CUSP-style table from CSV or GeoPackage."""

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix == ".gpkg":
        return gpd.read_file(path)
    raise ValueError(f"Unsupported input format for citation extraction: {path.suffix}")


def extract_source_keys(df: pd.DataFrame) -> list[str]:
    """Return sorted unique source keys from observation or aggregation tables."""

    sources: set[str] = set()

    if "source" in df.columns:
        values = df["source"].dropna().astype(str).str.strip()
        sources.update(value for value in values if value)

    if "aggregated_sources" in df.columns:
        values = df["aggregated_sources"].dropna().astype(str)
        for raw_value in values:
            for piece in re.split(r"[;,]", raw_value):
                source = piece.strip()
                if source:
                    sources.add(source)

    if not sources:
        raise ValueError(
            "Input table does not contain a usable 'source' or 'aggregated_sources' column."
        )

    return sorted(sources)


def parse_bibtex_entries(path: Path) -> dict[str, str]:
    """Parse a BibTeX file into a mapping from entry key to full entry text."""

    text = path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}

    current_lines: list[str] = []
    current_key: str | None = None
    brace_balance = 0

    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if current_key is None:
            if not stripped.startswith("@"):
                continue
            current_lines = [line]
            brace_balance = line.count("{") - line.count("}")
            header = stripped.split("{", 1)
            if len(header) != 2 or "," not in header[1]:
                raise ValueError(f"Could not parse BibTeX entry header: {line.strip()}")
            current_key = header[1].split(",", 1)[0].strip()
            if brace_balance == 0:
                entries[current_key] = "".join(current_lines).strip() + "\n"
                current_lines = []
                current_key = None
        else:
            current_lines.append(line)
            brace_balance += line.count("{") - line.count("}")
            if brace_balance == 0:
                entries[current_key] = "".join(current_lines).strip() + "\n"
                current_lines = []
                current_key = None

    if current_key is not None:
        raise ValueError(f"Unterminated BibTeX entry for key: {current_key}")

    return entries


def build_bibtex_subset(
    source_keys: list[str],
    master_bib_path: Path = DEFAULT_MASTER_BIB_PATH,
) -> tuple[str, list[str]]:
    """Return BibTeX text for the requested sources and any missing keys."""

    entries = parse_bibtex_entries(master_bib_path)
    missing = [source for source in source_keys if source not in entries]
    included = [entries[source].rstrip() for source in source_keys if source in entries]
    bib_text = "\n\n".join(included).strip()
    if bib_text:
        bib_text += "\n"
    return bib_text, missing


def extract_bibtex_for_table(
    table_path: Path,
    master_bib_path: Path = DEFAULT_MASTER_BIB_PATH,
) -> tuple[str, list[str], list[str]]:
    """Return BibTeX text, used source keys, and any missing BibTeX keys."""

    table = load_cusp_table(table_path)
    source_keys = extract_source_keys(table)
    bib_text, missing = build_bibtex_subset(source_keys, master_bib_path=master_bib_path)
    return bib_text, source_keys, missing


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for citation extraction."""

    parser = argparse.ArgumentParser(
        description="Extract copy/pastable BibTeX entries for the sources used in a CUSP table."
    )
    parser.add_argument("--input", type=Path, required=True, help="CUSP CSV or GPKG to inspect.")
    parser.add_argument(
        "--master-bib",
        type=Path,
        default=DEFAULT_MASTER_BIB_PATH,
        help="Master BibTeX file containing all CUSP source entries.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output .bib file. If omitted, BibTeX is printed to stdout.",
    )
    parser.add_argument(
        "--sources-output",
        type=Path,
        help="Optional text file listing the source keys found in the input table.",
    )
    return parser.parse_args()


def main() -> None:
    """Extract BibTeX entries for the sources referenced by a CUSP table."""

    args = parse_args()
    bib_text, source_keys, missing = extract_bibtex_for_table(
        args.input,
        master_bib_path=args.master_bib,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(bib_text, encoding="utf-8")
    else:
        print(bib_text, end="")

    if args.sources_output is not None:
        args.sources_output.parent.mkdir(parents=True, exist_ok=True)
        args.sources_output.write_text("\n".join(source_keys) + "\n", encoding="utf-8")

    if missing:
        missing_text = ", ".join(missing)
        raise SystemExit(f"Missing BibTeX entries for source keys: {missing_text}")


if __name__ == "__main__":
    main()
