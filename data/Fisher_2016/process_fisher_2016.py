#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Fisher_2016"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-22"

source_dataset = '''
Williams, M.; Estop-Aragones, C.; Fisher, J.P.; Murton, J.B.; Phoenix,
G.K.; Hartley, I.P. (2020): Extensive vegetation and soil surveys from
multiple sites in boreal forests of subarctic Canada, 2013-2014.
NERC Environmental Information Data Centre.
https://doi.org/10.5285/36f4e380-d01d-44a7-8321-7a677e6996b2
'''

processing_assumptions = [
  "Each plot row in Extensive_Vegetation_and_Soil_Data.csv is emitted as one CUSP observation.",
  "The source ALD field is reported in centimeters and is retained in centimeters.",
  "Numeric ALD rows are treated as permafrost-present late-August active-layer/thaw-depth observations, with pf_depth set equal to thaw_depth.",
  "Rows reported as > 150 are treated as lower-bound/no-refusal observations: pf_observed is set to 0, obs_limit is set to 150 cm, and thaw_depth/pf_depth are left missing.",
  "Rows missing plot GPS coordinates are dropped because they cannot be represented as CUSP point observations.",
  "The source documentation states ALD was taken from the bottom of the moss layer; CUSP preserves the reported ALD value rather than adding moss thickness to reinterpret the datum.",
  "Method is set to tp because the documentation describes a graduated stainless-steel rod inserted to refusal, with temperature confirmation of frozen soil.",
]

temporal_handling = [
  "The source gives campaign years by region/site group rather than plot-level dates.",
  "Whitehorse/Yukon plots (Region = WH) are assigned 2013-08-31.",
  "Yellowknife/Northwest Territories plots (Region = YK) are assigned 2014-08-31.",
]

spatial_handling = [
  "Plot-level GPS.N and GPS.W coordinates are read directly from the source CSV.",
  "GPS.W is stored as positive west longitude in the source and is converted to negative decimal degrees for CUSP.",
]

manual_steps = [
  "Download fisher_2016_data.zip from https://data-package.ceh.ac.uk/data/36f4e380-d01d-44a7-8321-7a677e6996b2.zip and extract the data package under raw/."
]

known_limitations = [
  "The exact plot measurement day is not reported; late-August representative dates are used.",
  "The source ALD datum is bottom of moss layer rather than moss/vegetation surface, so values may not be directly comparable to thaw depths measured from the ground or moss surface.",
  "No coordinate/year/depth duplicates were found against the current CUSP release within 50 m, but this source is geographically near other Yukon/Northwest Territories datasets.",
]

external_dependencies = [
  "Dataset DOI: 10.5285/36f4e380-d01d-44a7-8321-7a677e6996b2",
  "Article DOI: 10.1111/gcb.13248",
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


source = "Fisher_2016"
source_dir = _ROOT_DIR / "data" / source
raw_path = source_dir / "raw" / "data" / "Extensive_Vegetation_and_Soil_Data.csv"
output_path = source_dir / f"processed_{source.lower()}.csv"

REGION_DATES = {
    "WH": "2013-08-31",
    "YK": "2014-08-31",
}


raw = pd.read_csv(raw_path)
raw["source_ald_raw"] = raw["ALD"].astype("string").str.strip()
lower_bound = raw["source_ald_raw"].str.startswith(">", na=False)
raw["source_ald_cm"] = pd.to_numeric(
    raw["source_ald_raw"].str.replace(">", "", regex=False).str.strip(),
    errors="coerce",
)

df = raw.copy()
df["lon"] = -pd.to_numeric(df["GPS.W"], errors="coerce")
df["lat"] = pd.to_numeric(df["GPS.N"], errors="coerce")
df = df.dropna(subset=["lat", "lon"]).copy()
df["date"] = df["Region"].map(REGION_DATES)
df["source"] = source
df["site_id"] = df["Plot"]
df["method"] = "tp"

df["thaw_depth"] = df["source_ald_cm"]
df["pf_depth"] = df["source_ald_cm"]
df["pf_observed"] = 1
df["obs_limit"] = np.nan

df.loc[lower_bound, ["thaw_depth", "pf_depth"]] = np.nan
df.loc[lower_bound, "pf_observed"] = 0
df.loc[lower_bound, "obs_limit"] = df.loc[lower_bound, "source_ald_cm"]

df["pf_observed"] = df["pf_observed"].astype(int)

df = df.rename(
    columns={
        "Region": "source_region",
        "Site": "source_site",
        "Plot": "source_plot",
        "GPS.N": "source_gps_n",
        "GPS.W": "source_gps_w",
        "slope": "source_slope_degrees",
        "Tree_LAI": "source_tree_lai",
        "Understorey_LAI": "source_understorey_lai",
        "OM_thick": "source_organic_matter_thickness_cm",
        "Moss_thickness": "source_moss_thickness_cm",
        "Moss_thickness.1": "source_om_and_moss_thickness_cm",
        "DeepMoist": "source_deep_moisture",
        "SurfMoist": "source_surface_moisture",
        "Height": "source_vegetation_height_cm",
        "LAI": "source_total_lai",
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
    "source_ald_raw",
    "source_ald_cm",
    "source_region",
    "source_site",
    "source_plot",
        "source_gps_n",
        "source_gps_w",
        "source_organic_matter_thickness_cm",
        "source_moss_thickness_cm",
        "source_om_and_moss_thickness_cm",
    ]

df_out = df[ordered_columns].copy()

data_utils.check_columns(df_out)

df_out.to_csv(output_path, index=False)
