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
BIBTEX_TABLE_COLUMNS = [
    "source",
    "entrytype",
    "author",
    "year",
    "title",
    "journal",
    "booktitle",
    "publisher",
    "institution",
    "version",
    "volume",
    "number",
    "pages",
    "doi",
    "url",
    "howpublished",
    "note",
]


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


def _iter_bibtex_entries(path: Path) -> list[tuple[str, str]]:
    """Return BibTeX keys and full entry text in source-file order."""

    text = path.read_text(encoding="utf-8")
    entries: list[tuple[str, str]] = []

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
                entries.append((current_key, "".join(current_lines).strip() + "\n"))
                current_lines = []
                current_key = None
        else:
            current_lines.append(line)
            brace_balance += line.count("{") - line.count("}")
            if brace_balance == 0:
                entries.append((current_key, "".join(current_lines).strip() + "\n"))
                current_lines = []
                current_key = None

    if current_key is not None:
        raise ValueError(f"Unterminated BibTeX entry for key: {current_key}")

    return entries


def parse_bibtex_entries(path: Path) -> dict[str, str]:
    """Parse a BibTeX file into a mapping from entry key to full entry text."""

    return dict(_iter_bibtex_entries(path))


def _split_bibtex_fields(body: str) -> list[str]:
    """Split a BibTeX entry body at top-level commas."""

    fields: list[str] = []
    current: list[str] = []
    brace_depth = 0
    in_quotes = False
    escaped = False

    for char in body:
        if char == '"' and brace_depth == 0 and not escaped:
            in_quotes = not in_quotes
        elif not in_quotes and not escaped:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1

        if char == "," and brace_depth == 0 and not in_quotes:
            if "".join(current).strip():
                fields.append("".join(current).strip())
            current = []
        else:
            current.append(char)

        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False

    if "".join(current).strip():
        fields.append("".join(current).strip())
    return fields


def _unwrap_bibtex_value(value: str) -> str:
    """Remove one matching outer brace or quote pair from a field value."""

    value = value.strip()
    while len(value) >= 2 and (
        (value[0] == "{" and value[-1] == "}")
        or (value[0] == '"' and value[-1] == '"')
    ):
        value = value[1:-1].strip()
    return value


def parse_bibtex_table(path: Path) -> pd.DataFrame:
    """Parse the master BibTeX file into the generated source metadata table."""

    records: list[dict[str, str]] = []
    for source, entry_text in _iter_bibtex_entries(path):
        header = re.match(
            r"\s*@(?P<entrytype>[^\s{]+)\s*\{\s*[^,]+,",
            entry_text,
            flags=re.DOTALL,
        )
        if header is None:
            raise ValueError(f"Could not parse BibTeX entry header for key: {source}")

        body = entry_text[header.end() :].rstrip()
        if not body.endswith("}"):
            raise ValueError(f"Could not parse BibTeX entry body for key: {source}")
        body = body[:-1]

        record = {column: "" for column in BIBTEX_TABLE_COLUMNS}
        record["source"] = source
        record["entrytype"] = header.group("entrytype").lower()
        for field in _split_bibtex_fields(body):
            if "=" not in field:
                continue
            name, value = field.split("=", 1)
            name = name.strip().lower()
            if name in record:
                record[name] = _unwrap_bibtex_value(value)
        records.append(record)

    return pd.DataFrame.from_records(records, columns=BIBTEX_TABLE_COLUMNS)


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
