"""Build source-level quality flag metadata for CUSP sources."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cusp.data_utils import _ROOT_DIR


DATA_DIR = _ROOT_DIR / "data"
DEFAULT_QUALITY_FLAG_DEFINITIONS = DATA_DIR / "quality_flag_definitions.csv"
DEFAULT_SOURCE_QUALITY_FLAGS = DATA_DIR / "source_quality_flags.csv"
DEFAULT_OUTPUT = DATA_DIR / "source_quality_metadata.csv"


def _load_quality_flag_definitions(path: Path) -> pd.DataFrame:
    definitions = pd.read_csv(path)
    required = ["flag", "flag_code", "flag_category", "flag_description"]
    missing = [column for column in required if column not in definitions.columns]
    if missing:
        raise RuntimeError(f"Quality flag definitions are missing required columns: {missing}")
    if definitions["flag"].duplicated().any():
        duplicates = definitions.loc[definitions["flag"].duplicated(), "flag"].tolist()
        raise RuntimeError(f"Duplicate quality flag definitions found: {duplicates}")
    if definitions["flag_code"].duplicated().any():
        duplicates = definitions.loc[definitions["flag_code"].duplicated(), "flag_code"].tolist()
        raise RuntimeError(f"Duplicate quality flag codes found: {duplicates}")
    return definitions.loc[:, required].copy()


def _load_source_quality_flags(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["source", "flag"])
    source_flags = pd.read_csv(path)
    required = ["source", "flag"]
    missing = [column for column in required if column not in source_flags.columns]
    if missing:
        raise RuntimeError(f"Source quality flag table is missing required columns: {missing}")
    return source_flags.loc[:, required].dropna().drop_duplicates().copy()


def _list_available_sources(data_dir: Path) -> list[str]:
    return sorted(path.name for path in data_dir.iterdir() if path.is_dir())


def build_source_quality_metadata(
    data_dir: Path = DATA_DIR,
    definitions_path: Path = DEFAULT_QUALITY_FLAG_DEFINITIONS,
    source_flags_path: Path = DEFAULT_SOURCE_QUALITY_FLAGS,
) -> pd.DataFrame:
    """Build one source-level quality flag summary row per source directory."""

    definitions = _load_quality_flag_definitions(definitions_path)
    source_flags = _load_source_quality_flags(source_flags_path)
    definitions_by_flag = definitions.set_index("flag")

    rows: list[dict[str, object]] = []
    source_flag_map = (
        source_flags.groupby("source")["flag"].apply(lambda values: sorted(set(values.astype(str)))).to_dict()
        if not source_flags.empty
        else {}
    )

    for source in _list_available_sources(data_dir):
        flags = source_flag_map.get(source, [])
        codes = [definitions_by_flag.loc[flag, "flag_code"] for flag in flags]
        categories = sorted({definitions_by_flag.loc[flag, "flag_category"] for flag in flags})
        rows.append(
            {
                "source": source,
                "source_quality_flags": ";".join(codes),
                "source_quality_flag_names": ";".join(flags),
                "source_quality_flag_categories": ";".join(categories),
            }
        )

    return pd.DataFrame.from_records(rows).sort_values("source", kind="mergesort").reset_index(drop=True)


def write_source_quality_metadata(
    output_path: Path = DEFAULT_OUTPUT,
    data_dir: Path = DATA_DIR,
    definitions_path: Path = DEFAULT_QUALITY_FLAG_DEFINITIONS,
    source_flags_path: Path = DEFAULT_SOURCE_QUALITY_FLAGS,
) -> pd.DataFrame:
    """Write source-level quality metadata and return the generated frame."""

    metadata = build_source_quality_metadata(
        data_dir=data_dir,
        definitions_path=definitions_path,
        source_flags_path=source_flags_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_csv(output_path, index=False)
    return metadata
