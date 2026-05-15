
"""
metadata_schema_version = 1
source_key = "Kling_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
last_substantive_update = "2026-04-11"
source_dataset = '''
Kling, G. 2025. Imnavait Watershed Thaw Depth Survey Summary for 2003 to 2024,
Arctic LTER, Toolik Research Station, Alaska, ver. 13. Environmental Data
Initiative. https://doi.org/10.6073/pasta/6ed482c5c7dd3fd5871b2e463734ce75
'''
processing_assumptions = [
  "thaw_depth is taken from the annual mean thaw-depth column in the source CSV.",
  "pf_depth is assigned as the annual maximum thaw_depth for all rows within the same year.",
  "pf_observed is set to 1 when the annual maximum thaw_depth is less than 130 cm and 0 otherwise.",
  "site_id is fixed to LTER_Imnavait and method is fixed to tp.",
  "lat/lon are inferred from the center of a bounding box extracted from the metadata text file rather than point coordinates in the source CSV.",
]
temporal_handling = [
  "Per-record dates are preserved from the source CSV after parsing.",
]
spatial_handling = [
  "The script derives one representative site coordinate from metadata text rather than observation-specific coordinates.",
]
manual_steps = []
known_limitations = [
  "The output uses one site-level coordinate for all records instead of per-observation positions.",
  "The 130 cm permafrost threshold is a CUSP processing assumption.",
]
external_dependencies = []
notes = ""
"""


#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Tuple, Optional

import numpy as np
import pandas as pd

# Prefer repository _ROOT_DIR; fallback to script dir if not importable
try:
    from cusp.data_utils import _ROOT_DIR  # type: ignore
except Exception:
    _ROOT_DIR = Path(__file__).resolve().parent

SOURCE = "Kling_2025"
DEFAULT_CSV_NAME = "2003_present_Imnavait_Thaw_Kling.13.csv"
DEFAULT_META_NAME = "knb-lter-arc.1626.13.txt"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Process Imnavait thaw-depth dataset (Kling 2025).")
    p.add_argument("--csv", type=Path, default=None, help="Override CSV path (default uses _ROOT_DIR/data/SOURCE).")
    p.add_argument("--meta", type=Path, default=None, help="Override metadata TXT path (default uses _ROOT_DIR/data/SOURCE).")
    p.add_argument("--out", type=Path, default=None, help="Override output CSV path (default uses _ROOT_DIR/data/SOURCE).")
    return p.parse_args()


def resolve_paths(csv_override: Optional[Path], meta_override: Optional[Path], out_override: Optional[Path]) -> Tuple[Path, Path, Path]:
    repo_base = Path(_ROOT_DIR)
    data_base = repo_base / "data" / SOURCE
    base = data_base if data_base.exists() else Path(__file__).resolve().parent
    csv_path = csv_override if csv_override is not None else base / DEFAULT_CSV_NAME
    meta_path = meta_override if meta_override is not None else base / DEFAULT_META_NAME
    out_path = out_override if out_override is not None else base / "processed_kling_2025.csv"
    return csv_path, meta_path, out_path


def load_csv(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    rename_map = {
        "Date": "date",
        "Mean_thaw_cm": "mean_thaw_cm",
        "Standard_Devation_cm": "sd_cm",
        "Standard_Error_cm": "se_cm",
        "N": "n",
        "Minimum_cm": "min_cm",
        "Maximum_cm": "max_cm",
        "CV_%": "cv_percent",
    }
    df = df.rename(columns=rename_map)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["date"].dt.year
    for c in ["mean_thaw_cm", "sd_cm", "se_cm", "n", "min_cm", "max_cm", "cv_percent"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def _extract_bounds_from_numeric_lines(text: str) -> Tuple[Optional[float], Optional[float]]:
    line_nums = re.findall(r"^[ \t]*([+-]?\d+(?:\.\d+)?)[ \t]*$", text, re.MULTILINE)
    vals = [float(x) for x in line_nums]
    lons = [v for v in vals if -180.0 <= v <= -100.0]
    lats = [v for v in vals if 60.0 <= v <= 75.0]
    if len(lons) >= 2 and len(lats) >= 2:
        lon = (min(lons) + max(lons)) / 2.0
        lat = (min(lats) + max(lats)) / 2.0
        return lat, lon
    return None, None


def _extract_bounds_from_dms(text: str) -> Tuple[Optional[float], Optional[float]]:
    m = re.search(r"(\d{1,2})[°º](\d{1,2}).{0,6}N.*?(\d{1,3})[°º](\d{1,2}).{0,6}W", text, re.IGNORECASE | re.DOTALL)
    if m:
        lat_deg, lat_min, lon_deg, lon_min = map(int, m.groups())
        lat = float(lat_deg) + float(lat_min)/60.0
        lon = - (float(lon_deg) + float(lon_min)/60.0)
        return lat, lon
    return None, None


def extract_lat_lon(meta_text: str) -> Tuple[Optional[float], Optional[float]]:
    lat, lon = _extract_bounds_from_numeric_lines(meta_text)
    if lat is not None and lon is not None:
        return lat, lon
    lat, lon = _extract_bounds_from_dms(meta_text)
    return lat, lon


def build_output(df: pd.DataFrame, meta_path: Path) -> pd.DataFrame:
    meta_text = meta_path.read_text(errors="ignore")
    lat, lon = extract_lat_lon(meta_text)

    annual_max = df.groupby("year", as_index=True)["mean_thaw_cm"].max().rename("pf_depth")
    merged = df.merge(annual_max, left_on="year", right_index=True, how="left")
    merged["pf_observed"] = (merged["pf_depth"] < 130).astype("Int64")

    out = pd.DataFrame({
        "site_id": "LTER_Imnavait",
        "date": pd.to_datetime(merged["date"]).dt.date.astype(str),
        "lat": lat,
        "lon": lon,
        "thaw_depth": merged["mean_thaw_cm"],
        "pf_observed": merged["pf_observed"],
        "pf_depth": merged["pf_depth"],
        "obs_limit": pd.Series([np.nan] * len(merged)),
        "method": "tp",
        "source": SOURCE,
    })
    cols = ["site_id", "date", "lat", "lon", "thaw_depth", "pf_observed", "pf_depth", "obs_limit", "method", "source"]
    return out[cols]


def main():
    args = parse_args()
    csv_path, meta_path, out_path = resolve_paths(args.csv, args.meta, args.out)

    df = load_csv(csv_path)
    out = build_output(df, meta_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
