#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Walker_2022"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2025-07-03"
source_dataset = '''
Walker, D. A., M. Kanevskiy, A. L. Breen, A. Kade, R. P. Daanen, B. M. Jones,
D. J. Nicolsky, H. Bergstedt, E. Watson-Cook, and J. L. Peirce. 2022.
Observations in ice-rich permafrost systems, Prudhoe Bay Alaska, 2020-21.
AGC Data Report 22-01, Alaska Geobotany Center, Fairbanks, Alaska, USA.
'''
processing_assumptions = [
  "Rows with thaw-depth values that are neither numeric nor prefixed by '>' are dropped.",
  "pf_observed is set to 1 for every retained row and pf_depth is set equal to thaw_depth.",
  "Transect sample points are assumed to already have individual lat/lon coordinates in the input table.",
]
temporal_handling = [
  "Dates are preserved directly from the input CSV.",
]
spatial_handling = [
  "The script uses the per-point latitude and longitude values present in the input CSV.",
]
manual_steps = []
known_limitations = [
  "The script currently preserves non-ISO date strings from the source CSV instead of normalizing them to YYYY-MM-DD.",
  "Rows with '>' thaw-depth values are dropped rather than being retained explicitly as observation-limit records.",
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

source = "Walker_2022"


df = pd.read_csv(_ROOT_DIR / "data" / source /'Walker2002_TransectData.csv')

# Rename relevant columns for easier handling
df.rename(columns={
    'Latitude': 'lat',
    'Longitude': 'lon',
    'Date': 'date',
    'Thaw depth (cm)': 'thaw_depth',
    'site_id': 'site_id',
    'Distance_m': 'distance_m'
}, inplace=True)

# Drop rows where thaw_depth is not a number or does not contain '>'
df['thaw_depth'] = df['thaw_depth'].astype(str)
valid_rows = df['thaw_depth'].str.isnumeric() | df['thaw_depth'].str.contains('>')
df_filtered = df[valid_rows].copy()

# Convert numeric thaw_depths to float, otherwise NaN
def parse_thaw_depth(value):
    try:
        return float(value) if not '>' in value else np.nan
    except:
        return np.nan

df_filtered['thaw_depth_val'] = df_filtered['thaw_depth'].apply(parse_thaw_depth)

# Generate required columns
df_filtered['source'] = source
df_filtered['pf_depth'] = df_filtered['thaw_depth_val']
df_filtered['pf_observed'] = 1
df_filtered['obs_limit'] = np.nan
df_filtered['method'] = 'tp'
df_filtered['site_id_full'] = df_filtered['site_id'].astype(str) + "_" + df_filtered['distance_m'].astype(int).astype(str)

# Select required columns
output_df = df_filtered[['lat', 'lon', 'date', 'source', 'site_id_full', 'pf_observed', 
                         'pf_depth', 'obs_limit', 'thaw_depth', 'method']]
output_df.rename(columns={'site_id_full': 'site_id'}, inplace=True)

# Save to CSV
data_utils.check_columns(output_df)

output_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
