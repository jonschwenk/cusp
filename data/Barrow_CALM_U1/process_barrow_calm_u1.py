#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Barrow_CALM_U1"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Codex"
last_substantive_update = "2026-05-22"

source_dataset = '''
Brown, J. and Nelson, F. 1998. Active layer and permafrost properties,
including snow depth, soil temperature, and soil moisture, Barrow,
Alaska, Version 1. NSIDC GGD222. National Snow and Ice Data Center.
https://doi.org/10.7265/w3wq-st79
'''

processing_assumptions = [
  "Only the plot-level thaw-depth summary files named YYplN.dat are ingested into CUSP.",
  "Soil-temperature, soil-moisture, and snow-depth files are excluded because they are related environmental measurements rather than canonical CUSP thaw-depth/permafrost-depth observations.",
  "Each YYplN.dat file is a summary table for one plot; each non-empty date column is emitted as one CUSP observation.",
  "The source does not include individual probe measurements in these files, so CUSP uses the source-provided MEAN thaw depth as thaw_depth and pf_depth.",
  "The source-provided N OF CASES, minimum, maximum, and median are preserved as provenance columns.",
  "All retained thaw-depth summaries are treated as permafrost-present active-layer observations with method = tp.",
  "All rows use the dataset-level coordinate published on the NSIDC landing page because plot-specific coordinates are not present in the ASCII files.",
]

temporal_handling = [
  "Date columns are parsed from YYMMDD tokens in the source files.",
  "The 1962 files report 620800, which is interpreted as August 1962 with no known day; CUSP records this as 1962-08-01 and flags the date precision as month.",
]

spatial_handling = [
  "The dataset-level NSIDC spatial coverage coordinate is used for every plot/date summary: 71.29058, -156.78872.",
]

manual_steps = [
  "Downloaded all files from ftp://sidads.colorado.edu/pub/DATASETS/fgdc/ggd222_activlayer_barrow into raw/."
]

known_limitations = [
  "The original individual probe points are not available in the downloaded ASCII files; CUSP represents source summary means rather than raw probe observations.",
  "Plot-specific coordinates are not available in the source files.",
  "This source overlaps conceptually with CALM U1, but it provides pre-1990s and early-1990s plot/date thaw-depth summaries that are more detailed than the annual CALM export.",
]

external_dependencies = [
  "NSIDC DOI: 10.7265/w3wq-st79"
]

notes = ""
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "Barrow_CALM_U1"
source_dir = _ROOT_DIR / "data" / source
raw_dir = source_dir / "raw"
output_path = source_dir / f"processed_{source.lower()}.csv"

DATASET_LAT = 71.29058
DATASET_LON = -156.78872

STAT_ROWS = {
    "N OF CASES": "barrow_n_cases",
    "MINIMUM": "barrow_thaw_depth_min_cm",
    "MAXIMUM": "barrow_thaw_depth_max_cm",
    "MEAN": "barrow_thaw_depth_mean_cm",
    "MEDIAN": "barrow_thaw_depth_median_cm",
}


def parse_date_token(token: str) -> tuple[str, str]:
    """Return a YYYY-MM-DD date and precision flag from a YYMMDD token."""

    year = 1900 + int(token[0:2])
    month = int(token[2:4])
    day = int(token[4:6])
    if day == 0:
        return f"{year:04d}-{month:02d}-01", "month"
    return f"{year:04d}-{month:02d}-{day:02d}", "day"


def first_line_with_dates(lines: list[str]) -> str:
    for line in lines:
        if re.search(r"\b\d{6}\b", line):
            return line
    raise ValueError("Could not find a YYMMDD header row.")


def stat_lines(lines: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        for source_label in STAT_ROWS:
            if stripped.startswith(source_label):
                found[source_label] = line
    missing = sorted(set(STAT_ROWS) - set(found))
    if missing:
        raise ValueError(f"Missing expected statistic rows: {missing}")
    return found


def numeric_from_span(line: str, start: int, stop: int) -> float:
    values = re.findall(r"-?\d+(?:\.\d+)?", line[start:stop])
    if not values:
        return np.nan
    return float(values[0])


def parse_plot_file(path: Path) -> list[dict[str, object]]:
    match = re.fullmatch(r"(?P<year>\d{2})pl(?P<plot>\d+)\.dat", path.name, flags=re.IGNORECASE)
    if not match:
        return []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    date_line = first_line_with_dates(lines)
    stats = stat_lines(lines)
    date_matches = list(re.finditer(r"\b\d{6}\b", date_line))

    records: list[dict[str, object]] = []
    for index, date_match in enumerate(date_matches):
        start = date_match.start()
        stop = date_matches[index + 1].start() if index < len(date_matches) - 1 else len(date_line) + 20
        token = date_match.group()
        date, date_precision = parse_date_token(token)

        record: dict[str, object] = {
            "barrow_raw_file": path.name,
            "barrow_plot_id": f"P{int(match.group('plot'))}",
            "barrow_date_token": token,
            "barrow_date_precision": date_precision,
            "date": date,
        }
        for source_label, output_column in STAT_ROWS.items():
            record[output_column] = numeric_from_span(stats[source_label], start, stop)
        records.append(record)

    return records


records: list[dict[str, object]] = []
for raw_path in sorted(raw_dir.glob("[0-9][0-9]pl*.dat")):
    records.extend(parse_plot_file(raw_path))

df = pd.DataFrame.from_records(records)
df = df.loc[df["barrow_thaw_depth_mean_cm"].notna() & df["barrow_n_cases"].notna()].copy()

df["source"] = source
df["site_id"] = "U1_" + df["barrow_plot_id"].astype(str)
df["lat"] = DATASET_LAT
df["lon"] = DATASET_LON
df["method"] = "tp"
df["pf_observed"] = 1
df["thaw_depth"] = df["barrow_thaw_depth_mean_cm"]
df["pf_depth"] = df["barrow_thaw_depth_mean_cm"]
df["obs_limit"] = np.nan

df["barrow_n_cases"] = df["barrow_n_cases"].astype("Int64")

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
    "barrow_raw_file",
    "barrow_plot_id",
    "barrow_date_token",
    "barrow_date_precision",
    "barrow_n_cases",
    "barrow_thaw_depth_min_cm",
    "barrow_thaw_depth_max_cm",
    "barrow_thaw_depth_mean_cm",
    "barrow_thaw_depth_median_cm",
]

df = df.loc[:, output_columns].sort_values(["date", "site_id"], kind="mergesort").reset_index(drop=True)

data_utils.check_columns(df)
df.to_csv(output_path, index=False)
