#!/usr/bin/env python3
"""
metadata_schema_version = 1
source_key = "Kling_2016"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
source_dataset = '''
Kling, G. 2016. Tussock Watershed Thaw Depth Survey Summary for 1990 to
present, Arctic LTER, Toolik Research Station, Alaska, ver. 9.
Environmental Data Initiative.
https://doi.org/10.6073/pasta/fc25feb51864f13223b8573cffb7ed87
'''
processing_assumptions = [
  "Each source row is a date-specific mean of many thaw-probe measurements and is retained as one summary observation.",
  "thaw_depth and pf_depth are both set to the reported date-specific mean thaw depth; the associated count, spread, minimum, and maximum are preserved as provenance.",
  "Every retained mean represents probe contact with frozen ground, so pf_observed is set to 1 without an arbitrary depth threshold.",
  "site_id is fixed to LTER_TussockWS and method defaults to tp unless the metadata text says otherwise.",
  "lat/lon are inferred from the center of the metadata bounding box rather than from observation-specific coordinates.",
]
temporal_handling = [
  "Per-record dates are preserved from the source CSV after parsing.",
]
spatial_handling = [
  "The script derives one representative site coordinate from metadata text rather than using point locations.",
]
manual_steps = []
known_limitations = [
  "All records share one site-level coordinate instead of observation-specific positions.",
  "The output represents source summary means rather than the individual probe measurements.",
]
external_dependencies = []
notes = ""
"""
import re
import sys
from pathlib import Path


import pandas as pd
import numpy as np
import os
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Kling_2016'

# ---------- Config ----------
CSV_NAME = "1990_present_TW_thaw_Kling.csv"
TXT_NAME = "knb-lter-arc.1019.10.txt"
#OUT_NAME = "LTER_TussockWS_processed.csv"

SITE_ID = "LTER_TussockWS"
DEFAULT_METHOD = "tp"  # thaw probe
DEFAULT_OBS_LIMIT = np.nan
def parse_bbox_and_probe(txt_path: Path):
    """
    Parse latitude/longitude (bounding coordinates) and, if present,
    a probe method and length from the metadata .txt file.

    Returns (lat, lon, method, obs_limit_cm)
    """
    text = txt_path.read_text(encoding="utf-8", errors="ignore")

    # Helper to extract a labeled float
    def find_first_float(label):
        m = re.search(rf"{label}\s*[: ]\s*([+-]?\d+(?:\.\d+)?)", text, re.IGNORECASE)
        return float(m.group(1)) if m else None

    west  = find_first_float(r"West bounding coordinate")
    east  = find_first_float(r"East bounding coordinate")
    north = find_first_float(r"North bounding coordinate")
    south = find_first_float(r"South bounding coordinate")

    # Compute center if possible
    if west is not None and east is not None:
        lon = (west + east) / 2.0
    elif west is not None:
        lon = west
    elif east is not None:
        lon = east
    else:
        lon = np.nan

    if south is not None and north is not None:
        lat = (south + north) / 2.0
    elif south is not None:
        lat = south
    elif north is not None:
        lat = north
    else:
        lat = np.nan

    # Method: default to "tp" unless something else explicitly appears
    method = DEFAULT_METHOD
    method_match = re.search(r"\bmethod(?:s)?:\s*([A-Za-z0-9_ \-]+)", text, flags=re.IGNORECASE)
    if method_match:
        cand = method_match.group(1).strip()
        if re.search(r"\bthaw\s*probe\b", cand, re.IGNORECASE) or cand.lower().startswith("tp"):
            method = "tp"
        else:
            short = re.findall(r"[A-Za-z0-9]+", cand)
            if short:
                method = short[0].lower()

    # Probe length -> obs_limit in cm
    obs_limit = np.nan
    length_match = re.search(r"(?:probe\s*length|length\s*of\s*probe)\s*[:=]?\s*([\d.]+)\s*(cm|mm|m)\b", text, flags=re.IGNORECASE)
    if length_match:
        val = float(length_match.group(1))
        unit = length_match.group(2).lower()
        if unit == "mm":
            obs_limit = val / 10.0
        elif unit == "m":
            obs_limit = val * 100.0
        else:  # cm
            obs_limit = val

    return lat, lon, method, obs_limit


def main(workdir: Path):
    csv_path = _ROOT_DIR / "data" / source / CSV_NAME
    txt_path = _ROOT_DIR / "data" / source / TXT_NAME
    # out_path = workdir / OUT_NAME

    # if not csv_path.exists():
    #     print(f"ERROR: Cannot find {CSV_NAME} next to this script.", file=sys.stderr)
    #     sys.exit(1)

    # Defaults for spatial/probe info
    lat = np.nan
    lon = np.nan
    method = DEFAULT_METHOD
    obs_limit = DEFAULT_OBS_LIMIT

    # Parse TXT if present
    if txt_path.exists():
        lat, lon, method, obs_limit = parse_bbox_and_probe(txt_path)

    # Read CSV: skip first 4 metadata lines; infer first two columns
    df = pd.read_csv(csv_path, skiprows=4)
    if df.shape[1] < 2:
        raise ValueError("CSV does not have the expected columns (at least 2).")

    df = df.rename(columns={
        df.columns[0]: "date",
        df.columns[1]: "thaw_depth",
        df.columns[2]: "kling_source_sd_cm",
        df.columns[3]: "kling_source_se_cm",
        df.columns[4]: "kling_source_n",
        df.columns[5]: "kling_source_min_cm",
        df.columns[6]: "kling_source_max_cm",
        df.columns[7]: "kling_source_cv_percent",
    })
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    numeric_columns = [
        "thaw_depth", "kling_source_sd_cm", "kling_source_se_cm",
        "kling_source_n", "kling_source_min_cm", "kling_source_max_cm",
        "kling_source_cv_percent",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["date", "thaw_depth"]).copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["kling_source_n"] = df["kling_source_n"].astype("Int64")
    df["pf_depth"] = df["thaw_depth"]
    df["pf_observed"] = pd.Series(1, index=df.index, dtype="Int64")

    # Static fields
    df["site_id"] = SITE_ID
    df["lat"] = lat
    df["lon"] = lon
    df["obs_limit"] = obs_limit
    df["method"] = method
    df["source"] = source

    # Final ordering
    out_cols = [
        "site_id", "date", "lat", "lon", "thaw_depth", "pf_observed",
        "pf_depth", "obs_limit", "method", "source",
        "kling_source_sd_cm", "kling_source_se_cm", "kling_source_n",
        "kling_source_min_cm", "kling_source_max_cm",
        "kling_source_cv_percent",
    ]
    out_df = df[out_cols].sort_values("date").reset_index(drop=True)

    data_utils.check_columns(out_df)

    out_df.to_csv(_ROOT_DIR / "data" / source / "processed_kling_2016.csv", index=False)

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    if len(sys.argv) > 1:
        main(Path(sys.argv[1]))
    else:
        main(here)
