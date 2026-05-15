#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Whitley_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Annalise Khandelwal"
last_substantive_update = "2026-04-10"
source_dataset = '''
Whitley, M.; Frost, G.; Jorgenson, M. T.; Macander, M.; Maio, C. V.; Winder,
S. G. 2018. ABoVE: Permafrost Measurements and Distribution Across the Y-K
Delta, Alaska, 2016. ORNL DAAC. https://doi.org/10.3334/ORNLDAAC/1598
'''
processing_assumptions = [
  "Source UTM coordinates are transformed from EPSG:26903 to WGS84 before export.",
  "A single campaign-midpoint date of 2016-07-13 is assigned to all rows.",
  "Where pf_observed = 1, thaw_depth is taken from frost_bottom when available, otherwise from frost_top.",
  "pf_depth is set equal to thaw_depth for permafrost-present records, and obs_limit is fixed at 125 cm.",
  "method is set to tp for all processed rows.",
]
temporal_handling = [
  "All observations share one representative campaign date because the script uses the midpoint of the 2016 measurement window.",
]
spatial_handling = [
  "Coordinates are transformed from NAD83 / UTM zone 3N (EPSG:26903) to WGS84.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all records share one campaign-average date.",
]
external_dependencies = []
notes = ""
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os
from pyproj import Transformer
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Whitley_2018'


df = pd.read_csv(_ROOT_DIR / "data" / source /"PermafrostDepth_Fielddata_2016.csv")

# -----------------------------------------------------
# COORDINATE TRANSFORMATION (UTM to WGS84)
# -----------------------------------------------------
transformer = Transformer.from_crs("EPSG:26903", "EPSG:4326", always_xy=True)
df["lon"], df["lat"] = zip(*df.apply(lambda row: transformer.transform(row["easting"], row["northing"]), axis=1))

# -----------------------------------------------------
# RENAME COLUMNS
# -----------------------------------------------------
column_mapping = {
    "latitude ": "lat",
    "longitude ": "lon",
    "permafrost": "pf_observed",
    "FID": "site_id",
    "transect": "transect_name",
}
df.rename(columns=column_mapping, inplace=True)

# -----------------------------------------------------
# ADD REQUIRED COLUMNS
# -----------------------------------------------------
df['date'] = '07/13/2016' # midpoint of measurements 7/8 - 7/17 2016
df.loc[df['pf_observed'] == 0, ['pf_depth', 'thaw_depth']] = np.nan
mask = df['pf_observed'] == 1
df.loc[mask & (df['frost_bottom'] != -9999), 'thaw_depth'] = df.loc[mask & (df['frost_bottom'] != -9999), 'frost_bottom']
df.loc[mask & (df['frost_bottom'] == -9999), 'thaw_depth'] = df.loc[mask & (df['frost_bottom'] == -9999), 'frost_top']
df['pf_depth'] = df['thaw_depth'] # using the observed thaw depth where dataset indicates presence of PF
df["obs_limit"] = 125
df["source"] = "Whitley_2018"
df["method"] = "tp"


# -----------------------------------------------------
# CLEAN DATA
# -----------------------------------------------------
df.replace(-9999, pd.NA, inplace=True)
columns_to_drop = [
    "distance", "trans_distance", "easting", "northing", 'frost_top', 'frost_bottom',
    "frost_top_depth_flag", "frost_bottom_depth_flag", "frost_thickness",
    "frost_thickness_flag", "water_depth", "photos", "notes"
]
df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
