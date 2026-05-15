#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Myers-Smith_2005"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-11"
source_dataset = '''
Myers-Smith, Isla. 2005. Active Layer Depth Data for the BBC collapse scar
for 2003 and 2004, Bonanza Creek LTER - University of Alaska Fairbanks.
BNZ:206. http://www.lter.uaf.edu/data/data-detail/id/206
doi:10.6073/pasta/28920b92a1ca20a1a7e90fff842f3e45
'''
processing_assumptions = [
  "Measurement coordinates are assigned by merging collapse-scar transect distances with a separate coordinate table for east and west offsets.",
  "Rows containing > in the active-layer-depth field or missing depth are treated as invalid/non-permafrost observations for the site-year grouping logic.",
  "pf_depth is assigned as the maximum numeric thaw depth observed at each location-year where pf_observed = 1.",
  "obs_limit is set to 120 cm for 2003 and 205.5 cm for 2004.",
  "method is fixed to tp.",
]
temporal_handling = [
  "Dates are reconstructed from Year and DOY in the source table.",
]
spatial_handling = [
  "Point coordinates are based on an auxiliary Transect_Points_Coordinates.csv file derived from dataset-provided transect endpoints and Google Earth interpretation.",
]
manual_steps = [
  "Transect point coordinates were derived outside this script and stored in Transect_Points_Coordinates.csv.",
]
known_limitations = [
  "Coordinate placement depends on the manual boardwalk-based reconstruction described in the script header.",
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

source = "Myers-Smith_2005"

# Load data
data_df = pd.read_csv(_ROOT_DIR / "data" / source /"206_active_layer_depth_bbc.csv", na_values=['-9999'])
coord_df = pd.read_csv(_ROOT_DIR / "data" / source /"Transect_Points_Coordinates.csv")

# Map Offset_Left = East, Offset_Right = West using Type field
coord_east = coord_df[coord_df['Type'] == 'Offset_Left'][['Distance_m', 'Latitude', 'Longitude']].rename(
    columns={'Distance_m': 'Distance (m)', 'Latitude': 'lat', 'Longitude': 'lon'}).assign(Side='East')

coord_west = coord_df[coord_df['Type'] == 'Offset_Right'][['Distance_m', 'Latitude', 'Longitude']].rename(
    columns={'Distance_m': 'Distance (m)', 'Latitude': 'lat', 'Longitude': 'lon'}).assign(Side='West')

coord_combined = pd.concat([coord_east, coord_west], ignore_index=True)

# Date and ID construction
data_df['date'] = pd.to_datetime(data_df['Year'].astype(str) + data_df['DOY'].astype(str), format='%Y%j').dt.strftime('%m/%d/%Y')
data_df['site_key'] = data_df['Side of Transect'] + "_" + data_df['Distance (m)'].astype(str)
data_df['site_id'] = 'bbc_' + data_df['Side of Transect'] + '_' + data_df['Distance (m)'].astype(str)

# Preserve thaw depth string and numeric forms
data_df['thaw_depth'] = data_df['Mean Active Layer Depth (cm)'].astype(str).replace('nan', np.nan)
data_df['thaw_depth_num'] = pd.to_numeric(data_df['Mean Active Layer Depth (cm)'], errors='coerce')

# Mark invalid and determine pf_observed
data_df['invalid'] = data_df['thaw_depth'].str.contains('>') | data_df['thaw_depth'].isna()
data_df['invalid_group'] = data_df.groupby(['Year', 'site_key'])['invalid'].transform('max')
data_df['pf_observed'] = np.where(data_df['invalid_group'], 0, 1)

# Determine max pf_depth per location/year
max_depths = (
    data_df[data_df['pf_observed'] == 1]
    .groupby(['Year', 'site_key'])['thaw_depth_num']
    .max()
    .reset_index()
    .rename(columns={'thaw_depth_num': 'max_pf_depth'})
)
data_df = data_df.merge(max_depths, on=['Year', 'site_key'], how='left')
data_df['pf_depth'] = np.where(data_df['pf_observed'] == 1, data_df['max_pf_depth'], np.nan)

# Add static fields
data_df['obs_limit'] = np.where(data_df['Year'] == 2003, 120, 205.5)
data_df['method'] = 'tp'

# Merge coordinates by Distance and Side
merged_df = pd.merge(
    data_df,
    coord_combined[['Distance (m)', 'Side', 'lat', 'lon']],
    left_on=['Distance (m)', 'Side of Transect'],
    right_on=['Distance (m)', 'Side'],
    how='left'
)

merged_df['source'] = source

# Final export
final_output = merged_df[['site_id', 'date', 'lat', 'lon', 'thaw_depth', 'pf_observed', 'pf_depth', 'obs_limit', 'method', 'source']]



data_utils.check_columns(final_output)
final_output.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False, float_format='%.15g')
