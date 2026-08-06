#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Myers-Smith_2005"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Myers-Smith, Isla. 2005. Active Layer Depth Data for the BBC collapse scar
for 2003 and 2004, Bonanza Creek LTER - University of Alaska Fairbanks.
BNZ:206. http://www.lter.uaf.edu/data/data-detail/id/206
doi:10.6073/pasta/28920b92a1ca20a1a7e90fff842f3e45
'''
processing_assumptions = [
  "Measurement coordinates are assigned by merging collapse-scar transect distances with a separate coordinate table for east and west offsets.",
  "Each dated row is interpreted independently rather than assigning one annual state to every observation at a location.",
  "Ordinary numeric thaw depths are permafrost detections and are copied to pf_depth.",
  "Explicit >120 and >205.5 values are lower-bound absence observations with the reported value used as obs_limit; missing-depth rows are excluded.",
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
  "Coordinate placement depends on the manual boardwalk-based reconstruction described in the script header and is flagged as interpolated.",
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

# Interpret every dated measurement directly.
data_df['myers_smith_thaw_depth_raw'] = data_df['Mean Active Layer Depth (cm)'].astype('string').str.strip()
lower_bound = data_df['myers_smith_thaw_depth_raw'].str.startswith('>', na=False)
depth = pd.to_numeric(
    data_df['myers_smith_thaw_depth_raw'].str.replace('>', '', regex=False),
    errors='coerce',
)
valid = depth.notna() & depth.gt(0)
data_df = data_df.loc[valid].copy()
lower_bound = lower_bound.loc[data_df.index]
depth = depth.loc[data_df.index]
if int(lower_bound.sum()) != 120:
    raise ValueError(f"Expected 120 Myers-Smith lower-bound rows; found {int(lower_bound.sum())}.")

data_df['pf_observed'] = np.where(lower_bound, 0, 1)
data_df['thaw_depth'] = depth.mask(lower_bound)
data_df['pf_depth'] = data_df['thaw_depth']
data_df['obs_limit'] = depth.where(lower_bound)
data_df['method'] = 'tp'
data_df['quality_flag_coord_lookup_or_interpolated'] = True

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
final_output = merged_df[['site_id', 'date', 'lat', 'lon', 'thaw_depth', 'pf_observed', 'pf_depth', 'obs_limit', 'method', 'source', 'myers_smith_thaw_depth_raw', 'quality_flag_coord_lookup_or_interpolated']]



data_utils.check_columns(final_output)
final_output.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False, float_format='%.15g')
