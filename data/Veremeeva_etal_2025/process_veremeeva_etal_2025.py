#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Veremeeva_etal_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-21"

source_dataset = '''
Veremeeva, Alexandra; Morgenstern, Anne; Gottschalk, Milena; Junger,
Julia; Laboor, Sebastian; Abakumov, Evgeny; Grosse, Guido; et al. (2025):
ALLena: Thaw depth measurements of the active layer in the Lena River
Delta region from 1998 to 2022, Northeastern Siberia [dataset].
PANGAEA. https://doi.org/10.1594/PANGAEA.973813
'''

processing_assumptions = [
  "The PANGAEA tab export is parsed directly from its embedded table header.",
  "Each ALLena Data ID is emitted as one CUSP observation row.",
  "The canonical thaw_depth and pf_depth fields use Thaw depth mean [cm], which is the source-provided mean for the measurement site.",
  "The three discrete thaw-depth columns, thaw-depth minimum/maximum, source NOBS, and source quality flags are preserved as provenance columns.",
  "Rows with QF TD = 2 are treated as lower-bound observations because the source says the actual thaw depth was larger than the reported value; pf_observed is set to 0, obs_limit is set to the reported mean depth, and thaw_depth/pf_depth are left missing.",
  "Rows with QF TD = 1, where values were extracted from published figures, are retained as thaw-depth observations and flagged in the provenance columns.",
  "Method is mapped from Device: metal probe to tp, measurement tape in soil pit or at outcrop to pit, measurement tape on core to aug, and mixed soil pit / metal probe to tp_pit.",
  "Zero thaw-depth values are retained as reported rather than recoded.",
]

temporal_handling = [
  "The source Date/Time field is parsed as the observation date and written as YYYY-MM-DD.",
  "Rows with QF date = 1 are retained; the flag indicates cases where only a measurement date range was available to the source compilers.",
]

spatial_handling = [
  "Latitude and longitude are read directly from the source table in EPSG:4326.",
  "Rows with QF coord = 1 or 2 are retained and flagged in provenance columns; QF coord = 1 indicates coordinates georeferenced from figures, and QF coord = 2 indicates likely coordinate problems in the source.",
]

manual_steps = [
  "Download Veremeeva_main_table.tab from the PANGAEA dataset landing page."
]

known_limitations = [
  "The local raw file is the main ALLena table. It does not include the separate detailed tables for sites with more than three thaw-depth measurements.",
  "For source rows with more than three measurements, CUSP retains only the source-provided mean/min/max/NOBS summary available in the main table.",
  "The method mapping for measurement tape on core uses aug as the closest current CUSP method vocabulary term.",
  "One 30 m/year aggregate cell overlaps with CALM near Samoylov in 2002, but exact observation-level duplicate checks found no CALM matches on coordinates, date, and thaw/permafrost depth.",
]

external_dependencies = [
  "PANGAEA DOI: 10.1594/PANGAEA.973813"
]

notes = ""
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "Veremeeva_etal_2025"
source_dir = _ROOT_DIR / "data" / source
raw_path = source_dir / "Veremeeva_main_table.tab"
output_path = source_dir / f"processed_{source.lower()}.csv"


RAW_COLUMNS = [
    "event",
    "data_id",
    "field_id",
    "date_time",
    "qf_date",
    "location",
    "position_type",
    "latitude",
    "longitude",
    "qf_coord",
    "elevation_m",
    "device",
    "thaw_depth_1_cm",
    "thaw_depth_2_cm",
    "thaw_depth_3_cm",
    "thaw_depth_mean_cm",
    "qf_td",
    "thaw_depth_min_cm",
    "thaw_depth_max_cm",
    "method_comment",
    "nobs",
    "sample_comment",
    "detail_table_name",
    "microtopography",
    "ground_wetness_description",
    "vegetation_type",
    "geomorphology",
    "geologic_unit",
    "area",
    "publication_status",
    "data_source",
    "field_report_reference",
    "data_publication_reference",
    "related_publication_reference",
    "campaign",
    "data_authors",
    "institution",
    "measured_by",
    "contact",
    "comment",
    "measurement_comment",
    "measurement_type",
    "repeated_measurement",
    "repeat_timing",
    "repeat_years",
    "repeat_events",
]


def clean_text(series: pd.Series) -> pd.Series:
    """Strip text values and convert empty strings to missing values."""

    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def find_table_header(path: Path) -> int:
    """Return the zero-based line index of the PANGAEA data table header."""

    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if line.startswith("Event ("):
                return index
    raise ValueError(f"Could not find PANGAEA table header in {path}.")


def read_raw_table(path: Path) -> pd.DataFrame:
    """Read the PANGAEA tab export and replace verbose headings."""

    header_index = find_table_header(path)
    raw = pd.read_csv(path, sep="\t", skiprows=header_index, dtype=str, low_memory=False)
    if len(raw.columns) != len(RAW_COLUMNS):
        raise ValueError(
            f"Expected {len(RAW_COLUMNS)} columns in {path.name}, found {len(raw.columns)}."
        )

    raw.columns = RAW_COLUMNS
    return raw


def method_from_device(device: object) -> str:
    """Map ALLena Device values into the current CUSP method vocabulary."""

    if pd.isna(device):
        return "unknown"

    value = str(device).lower().strip()
    has_probe = "metal probe" in value
    has_soil_pit = "soil pit" in value
    has_outcrop = "outcrop" in value
    has_core = "core" in value

    if has_probe and (has_soil_pit or has_outcrop):
        return "tp_pit"
    if has_probe:
        return "tp"
    if has_soil_pit or has_outcrop:
        return "pit"
    if has_core:
        return "aug"
    return "unknown"


def build_processed_table(raw: pd.DataFrame) -> pd.DataFrame:
    """Transform the ALLena main table into CUSP processed-source rows."""

    df = raw.copy()

    text_columns = [
        "event",
        "data_id",
        "field_id",
        "qf_date",
        "location",
        "position_type",
        "qf_coord",
        "device",
        "qf_td",
        "method_comment",
        "sample_comment",
        "detail_table_name",
        "microtopography",
        "ground_wetness_description",
        "vegetation_type",
        "geomorphology",
        "geologic_unit",
        "area",
        "publication_status",
        "data_source",
        "field_report_reference",
        "data_publication_reference",
        "related_publication_reference",
        "campaign",
        "data_authors",
        "institution",
        "measured_by",
        "contact",
        "comment",
        "measurement_comment",
        "measurement_type",
        "repeated_measurement",
        "repeat_timing",
        "repeat_years",
        "repeat_events",
    ]
    for column in text_columns:
        df[column] = clean_text(df[column])

    numeric_columns = [
        "latitude",
        "longitude",
        "elevation_m",
        "thaw_depth_1_cm",
        "thaw_depth_2_cm",
        "thaw_depth_3_cm",
        "thaw_depth_mean_cm",
        "thaw_depth_min_cm",
        "thaw_depth_max_cm",
        "nobs",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    parsed_dates = pd.to_datetime(df["date_time"], errors="coerce")
    df["date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    df = df.dropna(subset=["latitude", "longitude", "date", "thaw_depth_mean_cm"]).copy()

    lower_bound = df["qf_td"].eq("2").fillna(False).to_numpy()

    processed = pd.DataFrame(
        {
            "site_id": "ALLena_" + df["data_id"].astype("string"),
            "source": source,
            "date": df["date"],
            "lat": df["latitude"],
            "lon": df["longitude"],
            "pf_observed": np.where(lower_bound, 0, 1).astype(int),
            "pf_depth": np.where(lower_bound, np.nan, df["thaw_depth_mean_cm"]),
            "thaw_depth": np.where(lower_bound, np.nan, df["thaw_depth_mean_cm"]),
            "obs_limit": np.where(lower_bound, df["thaw_depth_mean_cm"], np.nan),
            "method": df["device"].map(method_from_device),
            "n_measurements": df["nobs"],
            "veremeeva_event": df["event"],
            "veremeeva_data_id": df["data_id"],
            "veremeeva_field_id": df["field_id"],
            "veremeeva_qf_date": df["qf_date"],
            "veremeeva_location": df["location"],
            "veremeeva_position_type": df["position_type"],
            "veremeeva_qf_coord": df["qf_coord"],
            "veremeeva_elevation_m": df["elevation_m"],
            "veremeeva_device": df["device"],
            "veremeeva_thaw_depth_1_cm": df["thaw_depth_1_cm"],
            "veremeeva_thaw_depth_2_cm": df["thaw_depth_2_cm"],
            "veremeeva_thaw_depth_3_cm": df["thaw_depth_3_cm"],
            "veremeeva_thaw_depth_mean_cm": df["thaw_depth_mean_cm"],
            "veremeeva_qf_td": df["qf_td"],
            "veremeeva_thaw_depth_min_cm": df["thaw_depth_min_cm"],
            "veremeeva_thaw_depth_max_cm": df["thaw_depth_max_cm"],
            "veremeeva_method_comment": df["method_comment"],
            "veremeeva_sample_comment": df["sample_comment"],
            "veremeeva_detail_table_name": df["detail_table_name"],
            "veremeeva_microtopography": df["microtopography"],
            "veremeeva_ground_wetness_description": df["ground_wetness_description"],
            "veremeeva_vegetation_type": df["vegetation_type"],
            "veremeeva_geomorphology": df["geomorphology"],
            "veremeeva_geologic_unit": df["geologic_unit"],
            "veremeeva_area": df["area"],
            "veremeeva_publication_status": df["publication_status"],
            "veremeeva_data_source": df["data_source"],
            "veremeeva_field_report_reference": df["field_report_reference"],
            "veremeeva_data_publication_reference": df["data_publication_reference"],
            "veremeeva_related_publication_reference": df["related_publication_reference"],
            "veremeeva_campaign": df["campaign"],
            "veremeeva_data_authors": df["data_authors"],
            "veremeeva_institution": df["institution"],
            "veremeeva_measured_by": df["measured_by"],
            "veremeeva_contact": df["contact"],
            "veremeeva_comment": df["comment"],
            "veremeeva_measurement_comment": df["measurement_comment"],
            "veremeeva_measurement_type": df["measurement_type"],
            "veremeeva_repeated_measurement": df["repeated_measurement"],
            "veremeeva_repeat_timing": df["repeat_timing"],
            "veremeeva_repeat_years": df["repeat_years"],
            "veremeeva_repeat_events": df["repeat_events"],
        }
    )

    return processed.sort_values(["site_id", "date"], kind="mergesort").reset_index(drop=True)


def main() -> None:
    raw = read_raw_table(raw_path)
    processed = build_processed_table(raw)

    data_utils.check_columns(processed)
    processed.to_csv(output_path, index=False)

    print(f"Processed {len(processed)} Veremeeva_etal_2025 observations from {raw_path.name}.")
    print(f"Dropped {len(raw) - len(processed)} rows without usable date, coordinates, or mean thaw depth.")
    print("Method counts:")
    print(processed["method"].value_counts(dropna=False).sort_index().to_string())
    print("pf_observed counts:")
    print(processed["pf_observed"].value_counts(dropna=False).sort_index().to_string())


if __name__ == "__main__":
    main()
