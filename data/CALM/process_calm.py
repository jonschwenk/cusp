#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "CALM"
release_clearance = "needs_review"
permission_basis = "CC-BY-4.0"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-19"
source_dataset = '''
Streletskiy, Dmitry A; CALM; GTN-P; Wieczorek, Mareike; Heim,
Birgit; Bartsch, Annett (2025): GTN-P CALM: 35 years of Active Layer
Thickness (ALT) across latitudinal and elevational gradients in the
Northern Hemisphere [dataset]. PANGAEA.
https://doi.org/10.1594/PANGAEA.972777
'''
processing_assumptions = [
  "The PANGAEA tab export is parsed directly; the event-level metadata block is used to recover site method details, URIs, location, and elevation.",
  "Rows without a numeric active-layer-depth value are dropped rather than converted to permafrost absence.",
  "Numeric ALD values are treated as direct active-layer-thickness observations with pf_observed = 1 and pf_depth equal to thaw_depth.",
  "ALD values reported with a leading > are treated as lower-bound observations where permafrost was not confirmed within the reported limit; pf_observed is set to 0, obs_limit is set to the reported depth, and thaw_depth/pf_depth are left missing.",
  "ALD values reported with a leading < are treated as upper-bound observations where permafrost was confirmed but the exact thaw depth is not recoverable; pf_observed is set to 1 and the exact thaw_depth/pf_depth are left missing.",
  "ESA CCI validation comments are preserved as provenance and are not used to filter observations.",
  "The CALM Event label is used as site_id because it is stable and unique across the file.",
]
temporal_handling = [
  "The source reports year-only annual end-of-thaw-season ALT values.",
  "Year-only dates are encoded as September 1 of that year, following the project convention for Northern Hemisphere thaw-season observations without a reported month or day.",
]
spatial_handling = [
  "Latitude and longitude are read from the data table, which repeats the event coordinates for every annual observation.",
]
manual_steps = []
known_limitations = [
  "This PANGAEA file is an annual site-level time-series export, not the individual CALM grid-node raw measurements.",
  "A small number of event metadata records lack a recoverable method detail and are assigned method = unknown.",
  "The processed output is marked needs_review and is not included in the default release build until duplicate/subsumption review is complete.",
]
external_dependencies = []
notes = ""
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from cusp.data_utils import _ROOT_DIR
from cusp import data_utils


source = "CALM"
source_dir = _ROOT_DIR / "data" / source
raw_path = source_dir / "GTN-P_CALM_1990-2024.tab"


def clean_text(series: pd.Series) -> pd.Series:
    """Strip string columns and convert empty strings to missing values."""

    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def first_match(pattern: str, text: str) -> object:
    match = re.search(pattern, text)
    if not match:
        return pd.NA
    return match.group(1).strip()


def method_from_detail(method_detail: object) -> str:
    if pd.isna(method_detail):
        return "unknown"

    detail = str(method_detail).lower()
    if "thaw tube" in detail:
        return "tt"
    if "mechanical probing" in detail or "probe" in detail or "probing" in detail:
        return "tp"
    if "ground temperature" in detail or "borehole" in detail:
        return "temp"
    return "unknown"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def find_table_header(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.startswith("Event\tSite\tName\tID\tCountry"):
            return index
    raise ValueError(f"Could not find table header in {raw_path}.")


def parse_event_metadata(lines: list[str]) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for line in lines:
        event_match = re.search(r"(?:Event\(s\):\s*)?(CALM_[A-Z0-9]+)\b", line)
        if not event_match:
            continue

        event = event_match.group(1)
        comment = first_match(r"\* COMMENT:\s*(.*)$", line)
        method_detail = pd.NA
        pi = pd.NA
        if not pd.isna(comment):
            method_detail = first_match(r"Method:\s*([^,;]+(?:[,;][^,;]+)*)", str(comment))
            pi = first_match(r"PI:\s*([^,]+(?:,\s*[^,]+)*?)(?:,\s*Method:|\s*Method:|$)", str(comment))

        records.append(
            {
                "calm_event": event,
                "calm_uri": first_match(r"\(URI:\s*([^)]+)\)", line),
                "calm_event_latitude": first_match(r"\* LATITUDE:\s*([\-0-9.]+)", line),
                "calm_event_longitude": first_match(r"\* LONGITUDE:\s*([\-0-9.]+)", line),
                "calm_elevation_m": first_match(r"\* ELEVATION:\s*([\-0-9.]+)", line),
                "calm_location": first_match(r"\* LOCATION:\s*([^*]+)", line),
                "calm_method_device": first_match(r"\* METHOD/DEVICE:\s*([^*]+)", line),
                "calm_event_comment": comment,
                "calm_pi": pi,
                "calm_event_method_detail": method_detail,
            }
        )

    return pd.DataFrame.from_records(records).drop_duplicates("calm_event")


lines = read_lines(raw_path)
header_index = find_table_header(lines)
event_metadata = parse_event_metadata(lines[:header_index])

raw = pd.read_csv(raw_path, sep="\t", skiprows=header_index, dtype=str)

df = raw.merge(event_metadata, left_on="Event", right_on="calm_event", how="left")

ald_raw = clean_text(df["ALD [cm]"])
ald_is_lower_bound = ald_raw.str.startswith(">", na=False)
ald_is_upper_bound = ald_raw.str.startswith("<", na=False)
ald_is_bounded = ald_is_lower_bound | ald_is_upper_bound
ald_numeric = pd.to_numeric(ald_raw.str.replace(r"^[><]\s*", "", regex=True), errors="coerce")

df["calm_ald_raw"] = ald_raw
df["calm_ald_bound_type"] = np.select(
    [ald_is_lower_bound, ald_is_upper_bound],
    ["lower", "upper"],
    default="exact",
)
df["calm_ald_bound_cm"] = np.where(ald_is_bounded, ald_numeric, np.nan)
df["calm_year"] = pd.to_numeric(df["Date/Time"], errors="coerce").astype("Int64")

df = df.loc[ald_numeric.notna() & df["calm_year"].notna()].copy()
ald_numeric = ald_numeric.loc[df.index]
ald_is_lower_bound = ald_is_lower_bound.loc[df.index]
ald_is_upper_bound = ald_is_upper_bound.loc[df.index]
ald_is_bounded = ald_is_bounded.loc[df.index]

df["site_id"] = clean_text(df["Event"])
df["source"] = source
df["lat"] = pd.to_numeric(df["Latitude"], errors="coerce")
df["lon"] = pd.to_numeric(df["Longitude"], errors="coerce")
df["date"] = df["calm_year"].astype(str) + "-09-01"
df["method"] = df["calm_event_method_detail"].map(method_from_detail)

df["pf_observed"] = np.where(ald_is_lower_bound, 0, 1).astype(int)
df["thaw_depth"] = np.where(ald_is_bounded, np.nan, ald_numeric)
df["pf_depth"] = np.where(ald_is_bounded, np.nan, ald_numeric)
df["obs_limit"] = np.where(ald_is_lower_bound, ald_numeric, np.nan)

df["calm_site_code"] = clean_text(df["Site"])
df["calm_site_name"] = clean_text(df["Name"])
df["calm_gtnp_id"] = clean_text(df["ID"])
df["calm_country"] = clean_text(df["Country"])
df["calm_area"] = clean_text(df["Area"])
df["calm_sample_comment"] = clean_text(df["Sample comment"])
df["calm_validation_comment"] = clean_text(df["Comment"])

df["calm_event_latitude"] = pd.to_numeric(df["calm_event_latitude"], errors="coerce")
df["calm_event_longitude"] = pd.to_numeric(df["calm_event_longitude"], errors="coerce")
df["calm_elevation_m"] = pd.to_numeric(df["calm_elevation_m"], errors="coerce")

output_columns = [
    "site_id",
    "source",
    "date",
    "lat",
    "lon",
    "pf_observed",
    "pf_depth",
    "thaw_depth",
    "obs_limit",
    "method",
    "calm_site_code",
    "calm_site_name",
    "calm_gtnp_id",
    "calm_country",
    "calm_area",
    "calm_ald_raw",
    "calm_ald_bound_type",
    "calm_ald_bound_cm",
    "calm_year",
    "calm_sample_comment",
    "calm_validation_comment",
    "calm_uri",
    "calm_pi",
    "calm_event_method_detail",
    "calm_method_device",
    "calm_event_comment",
    "calm_event_latitude",
    "calm_event_longitude",
    "calm_elevation_m",
    "calm_location",
]

df = df.loc[:, output_columns].sort_values(["site_id", "date"], kind="mergesort").reset_index(drop=True)

data_utils.check_columns(df)

df.to_csv(source_dir / f"processed_{source.lower()}.csv", index=False)

print(f"Processed {len(df)} CALM observations from {raw_path.name}.")
print(f"Dropped {len(raw) - len(df)} rows without usable ALD/year values.")
print("Method counts:")
print(df["method"].value_counts(dropna=False).sort_index().to_string())
print("pf_observed counts:")
print(df["pf_observed"].value_counts(dropna=False).sort_index().to_string())
