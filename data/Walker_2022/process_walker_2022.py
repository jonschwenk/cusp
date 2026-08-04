#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Walker_2022"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Walker, D. A., M. Kanevskiy, A. L. Breen, A. Kade, R. P. Daanen, B. M. Jones,
D. J. Nicolsky, H. Bergstedt, E. Watson-Cook, and J. L. Peirce. 2022.
Observations in ice-rich permafrost systems, Prudhoe Bay Alaska, 2020-21.
AGC Data Report 22-01, Alaska Geobotany Center, Fairbanks, Alaska, USA.
'''
processing_assumptions = [
  "Rows with numeric thaw depths are direct permafrost-presence observations with pf_depth equal to thaw_depth.",
  "Rows reported as >x are lower-bound absence observations: pf_observed = 0, obs_limit = x, and thaw_depth/pf_depth are left empty.",
  "Rows with other nonnumeric thaw-depth text are excluded because they do not support a state/depth observation.",
  "Transect sample points are assumed to already have individual lat/lon coordinates in the input table.",
]
temporal_handling = [
  "Source dates are normalized to ISO calendar dates.",
]
spatial_handling = [
  "The script uses the per-point latitude and longitude values present in the input CSV.",
]
manual_steps = []
known_limitations = [
  "Greater-than measurements are censored at their reported probing limit and do not provide exact active-layer thickness.",
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
df['walker_thaw_depth_raw'] = df['thaw_depth'].astype('string').str.strip()
numeric_depth = pd.to_numeric(df['walker_thaw_depth_raw'], errors='coerce')
lower_bound = df['walker_thaw_depth_raw'].str.match(r'^>\s*\d+(?:\.\d+)?$', na=False)
valid_rows = numeric_depth.notna() | lower_bound
df_filtered = df[valid_rows].copy()
numeric_depth = numeric_depth.loc[df_filtered.index]
lower_bound = lower_bound.loc[df_filtered.index]
limit_depth = pd.to_numeric(
    df_filtered['walker_thaw_depth_raw'].str.replace('>', '', regex=False).str.strip(),
    errors='coerce',
)

if int(lower_bound.sum()) != 22:
    raise ValueError(f"Expected 22 Walker greater-than observations; found {int(lower_bound.sum())}.")

# Generate required columns
df_filtered['source'] = source
df_filtered['thaw_depth'] = numeric_depth.where(~lower_bound)
df_filtered['pf_depth'] = df_filtered['thaw_depth']
df_filtered['pf_observed'] = np.where(lower_bound, 0, 1)
df_filtered['obs_limit'] = limit_depth.where(lower_bound)
df_filtered['method'] = 'tp'
df_filtered['date'] = pd.to_datetime(df_filtered['date'], format='%m/%d/%y').dt.strftime('%Y-%m-%d')
df_filtered['site_id_full'] = df_filtered['site_id'].astype(str) + "_" + df_filtered['distance_m'].astype(int).astype(str)

# Select required columns
output_df = df_filtered[
    [
        'lat', 'lon', 'date', 'source', 'site_id_full', 'pf_observed',
        'pf_depth', 'obs_limit', 'thaw_depth', 'method',
        'walker_thaw_depth_raw', 'distance_m',
    ]
].rename(columns={'site_id_full': 'site_id'}).copy()

# Save to CSV
data_utils.check_columns(output_df)

output_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
