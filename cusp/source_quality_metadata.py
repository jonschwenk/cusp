"""Build source-level quality flag metadata for CUSP sources."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cusp.data_utils import _ROOT_DIR


DATA_DIR = _ROOT_DIR / "data"
DEFAULT_QUALITY_FLAG_DEFINITIONS = DATA_DIR / "quality_flag_definitions.csv"
DEFAULT_SOURCE_QUALITY_FLAGS = DATA_DIR / "source_quality_flags.csv"
DEFAULT_SOURCE_DUPLICATION_NOTES = DATA_DIR / "source_duplication_notes.csv"
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


def _load_source_duplication_notes(path: Path = DEFAULT_SOURCE_DUPLICATION_NOTES) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["source", "duplication_notes"])
    notes = pd.read_csv(path)
    required = ["source", "duplication_notes"]
    missing = [column for column in required if column not in notes.columns]
    if missing:
        raise RuntimeError(f"Source duplication notes table is missing required columns: {missing}")
    return notes.loc[:, required].dropna(subset=["source"]).drop_duplicates(subset=["source"], keep="first").copy()


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


def build_source_metadata(
    observations: pd.DataFrame,
    source_quality_metadata: pd.DataFrame,
    source_reference_crosswalk: pd.DataFrame | None = None,
    duplication_notes_path: Path = DEFAULT_SOURCE_DUPLICATION_NOTES,
) -> pd.DataFrame:
    """Build the user-facing one-row-per-source catalog."""

    records: list[dict[str, object]] = []
    for source, source_df in observations.groupby("source", dropna=False, sort=True):
        methods = sorted(value for value in source_df["method"].dropna().astype(str).unique() if value)
        records.append(
            {
                "source": source,
                "n_observations": int(len(source_df)),
                "n_pf_observed_yes": int(source_df["pf_observed"].eq(1).sum()),
                "n_pf_observed_no": int(source_df["pf_observed"].eq(0).sum()),
                "n_alt_observations": int(source_df["thaw_depth"].notna().sum()),
                "n_pf_depth_observations": int(source_df["pf_depth"].notna().sum()),
                "methods": ";".join(methods),
            }
        )

    metadata = pd.DataFrame.from_records(records)
    if metadata.empty:
        metadata = pd.DataFrame(
            columns=[
                "source",
                "n_observations",
                "n_pf_observed_yes",
                "n_pf_observed_no",
                "n_alt_observations",
                "n_pf_depth_observations",
                "methods",
            ]
        )

    metadata = metadata.merge(
        source_quality_metadata,
        on="source",
        how="left",
        validate="one_to_one",
    )

    for column in [
        "source_quality_flags",
        "source_quality_flag_names",
        "source_quality_flag_categories",
    ]:
        if column not in metadata.columns:
            metadata[column] = ""
        metadata[column] = metadata[column].fillna("")

    flag_names = metadata["source_quality_flag_names"].astype("string")
    metadata["has_duplication_caveat"] = flag_names.str.split(";").map(
        lambda values: "possible_duplicate_or_overlap" in values if isinstance(values, list) else False
    )
    duplication_notes = _load_source_duplication_notes(duplication_notes_path)
    metadata = metadata.merge(duplication_notes, on="source", how="left", validate="one_to_one")
    metadata["duplication_notes"] = metadata["duplication_notes"].fillna("")

    if source_reference_crosswalk is not None and not source_reference_crosswalk.empty:
        citation_columns = [
            column
            for column in ["title", "author", "year", "doi", "url"]
            if column in source_reference_crosswalk.columns
        ]
        if citation_columns:
            metadata = metadata.merge(
                source_reference_crosswalk[["source"] + citation_columns],
                on="source",
                how="left",
                validate="one_to_one",
            )

    preferred_columns = [
        "source",
        "n_observations",
        "n_pf_observed_yes",
        "n_pf_observed_no",
        "n_alt_observations",
        "n_pf_depth_observations",
        "methods",
        "source_quality_flags",
        "source_quality_flag_names",
        "source_quality_flag_categories",
        "has_duplication_caveat",
        "duplication_notes",
    ]
    remaining_columns = [column for column in metadata.columns if column not in preferred_columns]
    return metadata.loc[:, preferred_columns + remaining_columns].sort_values("source", kind="mergesort").reset_index(drop=True)
