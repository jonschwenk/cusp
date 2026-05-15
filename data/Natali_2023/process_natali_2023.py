#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Natali_2023"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "annalisekhandelwal"
last_substantive_update = "2026-04-10"
source_dataset = '''
Natali, S.; Ludwig, S.; Minions, C.; Watts, J. D. 2023. ABoVE: Thaw Depth at
Selected Unburned and Burned Sites Across Alaska (Version 1.0). ORNL
Distributed Active Archive Center. https://doi.org/10.3334/ORNLDAAC/1579
'''
processing_assumptions = [
  "pf_observed is inferred from thaw_depth using a fixed 115 cm cutoff.",
  "pf_depth is set equal to thaw_depth where pf_observed = 1.",
  "sample_location is retained as transect_point when present.",
  "method is set to tp for all rows.",
  "Rows with missing thaw_depth or missing coordinates are dropped before export.",
]
temporal_handling = [
  "Per-record dates are preserved directly from the source CSV.",
]
spatial_handling = [
  "Coordinates are read directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "The 115 cm permafrost threshold is a CUSP processing assumption rather than a source-provided permafrost label.",
]
external_dependencies = []
notes = ""
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Natali_2023'

# Import data 
df = pd.read_csv(_ROOT_DIR / "data" / source /"thaw_depth.csv")




# Rename columns
column_mapping = {
    "date": "date",
    "latitude ": "lat",
    "longitude ": "lon",
    "site_code": "site_id",
    "transect": "transect_name",
}
df.rename(columns=column_mapping, inplace=True)

df.replace(-9999, np.nan, inplace=True)


# Create new required columns

df["pf_observed"] = df["thaw_depth"].apply(lambda x: 1 if x < 115 else 0)
df["obs_limit"] = 115
df["source"] = "Natali_2023"
df["transect_point"] = df["sample_location"] if "sample_location" in df.columns else pd.NA
df['pf_depth'] = np.where(df['pf_observed'] == 1, df['thaw_depth'], np.nan)
df.loc[df['thaw_depth'].isna(), 'pf_observed'] = np.nan
df['method'] = 'tp'
df = df.dropna(subset=['thaw_depth', 'lat', 'lon', 'pf_observed']).copy()
df['pf_observed'] = df['pf_observed'].astype(int)


# Drop columns if they exist
# columns_to_drop = ["site_name", "notes"]
# df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

# # Select and reorder columns
# final_columns = ["date", "thaw_depth", "pf_depth", "obs_limit", "pf_observed",
#                  "transect_name", "transect_point", "lon", "lat", "source", "site_id"]
# existing_columns = [col for col in final_columns if col in df.columns]
data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
