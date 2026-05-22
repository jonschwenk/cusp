#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Utqiagvik_ERT_GPR"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk"
last_substantive_update = "2026-05-22"
source_dataset = '''
Ekimova, Valentina; Sullivan, Taylor; Nelson, MacKenzie; Epstein,
Howard; Douglas, Thomas; Jull, Matthew (2025): Utqiagvik permafrost
geophysics datasets (2021-2023) [dataset]. Zenodo.
https://doi.org/10.5281/zenodo.17096203
'''
processing_assumptions = [
  "Only thaw-probe observations are emitted as CUSP rows; raw ERT and GPR files are retained as source context but are not converted into observations because they are geophysical measurement files rather than interpreted point thaw-depth picks.",
  "The source thaw_depth column is reported in meters and is converted to centimeters.",
  "Numeric thaw_depth rows are treated as permafrost-present point observations, with pf_depth set equal to thaw_depth.",
  "Rows whose field comment indicates that the frost probe bottomed out are retained as permafrost-absence observations to the 1 m probe limit stated in Ekimova et al. 2026.",
  "Rows without numeric thaw_depth and without a frost-probe-bottomed-out comment are dropped because they document locations where no usable thaw-depth observation was recorded.",
  "Source comment values consisting only of a ditto mark are forward-filled from the previous non-empty comment before processing.",
  "Method is set to tp for all emitted observations.",
]
temporal_handling = [
  "The source table reports year only.",
  "The publication describes field work as occurring in late August to early September near peak thaw, so year-only dates are encoded as September 1 of the reported year.",
]
spatial_handling = [
  "Source coordinates are UTM easting/northing in EPSG:32604 and are transformed to WGS84 latitude/longitude.",
  "The source elevation and detected CRS columns are retained as provenance fields.",
]
manual_steps = [
  "Download Geophysics_for_publication.zip from Zenodo DOI 10.5281/zenodo.17096203 and extract it in this source directory."
]
known_limitations = [
  "The raw ERT and GPR files may support interpreted thaw-depth profiles in the paper, but CUSP currently ingests only the direct thaw-probe table from this release.",
  "Future GPR ingestion would need interpreted thaw-depth picks or a documented picking workflow; ingesting every raw trace would overstate independent observations and mostly duplicate the same probe transect footprints.",
  "Future ERT ingestion would require explicit inversion and interpretation decisions because the archive contains raw quadripole measurements and topography rather than point thaw-depth observations; resistivity-derived thaw depth is more interpretive than the probe table.",
  "Several field notes indicate gravel, road, standing water, or possible refusal ambiguity; these notes are preserved but not used to filter numeric thaw-depth observations.",
  "The BEO rows are spatially near existing Barrow/CALM observations, but this source provides individual 2021-2023 transect point observations rather than CALM annual site means.",
]
external_dependencies = [
  "Zenodo DOI: 10.5281/zenodo.17096203",
  "Article DOI: 10.5194/tc-20-265-2026",
]
notes = ""
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "Utqiagvik_ERT_GPR"
source_dir = _ROOT_DIR / "data" / source
raw_path = source_dir / "Geophysics_for_publication" / "thaw_probe_depth_joined.csv"
output_path = source_dir / f"processed_{source.lower()}.csv"

PROBE_LIMIT_CM = 100.0


def clean_comment(series: pd.Series) -> pd.Series:
    """Normalize blank and ditto-mark source comments."""

    comment = series.astype("string").str.strip()
    comment = comment.mask(comment == "")
    comment = comment.mask(comment == '"').ffill()
    return comment


def site_id_from_name(name: object) -> object:
    """Return the source transect identifier by dropping the point index."""

    if pd.isna(name):
        return pd.NA

    value = str(name).strip()
    parts = value.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return value


raw = pd.read_csv(raw_path)
raw["source_comment"] = clean_comment(raw["comment"])
raw["source_thaw_depth_m"] = pd.to_numeric(raw["thaw_depth"], errors="coerce")

numeric_depth = raw["source_thaw_depth_m"].notna()
bottomed_out = (
    raw["source_comment"].str.contains("frost probe bottomed out", case=False, na=False)
    & ~numeric_depth
)
retain = numeric_depth | bottomed_out

df = raw.loc[retain].copy()

transformer = Transformer.from_crs("EPSG:32604", "EPSG:4326", always_xy=True)
df["lon"], df["lat"] = transformer.transform(
    df["Easting"].astype(float).to_numpy(),
    df["Northing"].astype(float).to_numpy(),
)

df["site_id"] = df["name"].map(site_id_from_name)
df["date"] = pd.to_datetime(df["year"].astype(int).astype(str) + "-09-01").dt.strftime("%Y-%m-%d")
df["method"] = "tp"
df["source"] = source

df["thaw_depth"] = df["source_thaw_depth_m"] * 100.0
df["pf_depth"] = df["thaw_depth"]
df["pf_observed"] = 1
df["obs_limit"] = np.nan

df.loc[bottomed_out.loc[df.index], ["thaw_depth", "pf_depth"]] = np.nan
df.loc[bottomed_out.loc[df.index], "pf_observed"] = 0
df.loc[bottomed_out.loc[df.index], "obs_limit"] = PROBE_LIMIT_CM

df["pf_observed"] = df["pf_observed"].astype(int)

df = df.rename(
    columns={
        "name": "source_point_id",
        "Easting": "source_easting",
        "Northing": "source_northing",
        "Elevation (m)": "source_elevation_m",
        "Detected_CRS": "source_detected_crs",
    }
)

ordered_columns = [
    "lon",
    "lat",
    "date",
    "source",
    "site_id",
    "pf_observed",
    "pf_depth",
    "thaw_depth",
    "obs_limit",
    "method",
    "source_point_id",
    "source_thaw_depth_m",
    "source_comment",
    "source_easting",
    "source_northing",
    "source_elevation_m",
    "source_detected_crs",
]

df_out = df[ordered_columns].copy()

data_utils.check_columns(df_out)

df_out.to_csv(output_path, index=False)
