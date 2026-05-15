#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Hollingsworth_2005"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-11"
source_dataset = '''
Hollingsworth, Teresa Nettleton. 2005. Active layer depths: 150 mature black
spruce sites in interior Alaska (2000-2003). Bonanza Creek LTER -
University of Alaska Fairbanks. BNZ:140.
http://www.lter.uaf.edu/data/data-detail/id/140
doi:10.6073/pasta/2fbece708e6552adb8ba6dcbc817ebb1
'''
processing_assumptions = [
  "Depth strings are cleaned to numeric values by removing non-numeric characters before aggregation.",
  "Each site-date group is summarized using probe-code counts: I indicates valid permafrost hits, while R and O affect pf_observed and thaw-depth handling.",
  "pf_observed is set to 1 only when I-coded hits outnumber the combined R and O counts.",
  "obs_limit is set to the maximum O-coded depth when present; otherwise it defaults to 130 cm.",
  "method is set to tp for all processed rows.",
]
temporal_handling = [
  "Per-date records are preserved and summarized within each site-date group rather than aggregated across years.",
]
spatial_handling = [
  "Coordinates are joined from the separate TKN_SiteCords.csv table without reprojection.",
]
manual_steps = []
known_limitations = [
  "The interpretation of probe codes is encoded in CUSP-specific aggregation logic and should be revisited if the source code definitions change.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np

import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Hollingsworth_2005"

# Load data
coords_df = pd.read_csv(_ROOT_DIR / "data" / source /"TKN_SiteCords.csv")
depth_df = pd.read_csv(_ROOT_DIR / "data" / source /"140_activelayerdpth.txt", sep="\t")

# Standardize column names
coords_df.rename(columns={"site_id": "Site", "n_dd": "lat", "w_dd": "lon"}, inplace=True)
depth_df.rename(columns={
    "Site": "site_id",
    "thaw": "depth_cm",
    "probe code": "code"
}, inplace=True)

# Clean numeric fields
depth_df["depth_cm"] = pd.to_numeric(
    depth_df["depth_cm"].astype(str).str.replace(r"[^\d.]+", "", regex=True),
    errors='coerce'
)

# Define logic function
def process_group(group):
    codes = group["code"].value_counts()
    I = codes.get("I", 0)
    R = codes.get("R", 0)
    O = codes.get("O", 0)

    if R > 0 or O > 0:
        if I == 0 or I <= (R + O):
            thaw_depth = np.nan
        else:
            thaw_depth = group.loc[group["code"] == "I", "depth_cm"].mean()
    else:
        thaw_depth = group["depth_cm"].mean()

    pf_observed = 1 if I > (R + O) else 0
    pf_depth = thaw_depth if pf_observed == 1 else np.nan

    if O > 0:
        obs_limit = group.loc[group["code"] == "O", "depth_cm"].max()
    else:
        obs_limit = 130

    return pd.Series({
        "thaw_depth": thaw_depth,
        "pf_observed": pf_observed,
        "pf_depth": pf_depth,
        "obs_limit": obs_limit
    })



# Merge coordinates
agg = (
    depth_df
    .groupby(["site_id", "date"], group_keys=False)
    .apply(lambda g: process_group(g.drop(columns=["site_id", "date"], errors="ignore")))
    .reset_index()
)
final_df = pd.merge(agg, coords_df[['Site', 'lat', 'lon']], left_on="site_id", right_on="Site", how="left")
final_df.drop(columns=["Site"], inplace=True)

# Add method field
final_df["pf_observed"] = final_df["pf_observed"].astype(int)
final_df["method"] = "tp"
final_df["source"] = source

# Reorder and save
final_df = final_df[[
    "site_id", "date", "lat", "lon",
    "thaw_depth", "pf_observed", "pf_depth",
    "obs_limit", "method", "source"
]]

# Save to CSV
data_utils.check_columns(final_df)

final_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

