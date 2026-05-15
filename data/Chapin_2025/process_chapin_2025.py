#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Chapin_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-11"
source_dataset = '''
Chapin, F.S.; Ruess, R.; Bonanza Creek LTER. 2025. Bonanza Creek LTER:
Annual Active Layer Depths from 2002 to Present in the Survey Line Fire near
Fairbanks, Alaska, ver. 26. Environmental Data Initiative.
https://doi.org/10.6073/pasta/b3318a9042025ce80e04ce13abf35898

Chapin, F.S.; Ruess, R.; Bonanza Creek LTER. 2025. Bonanza Creek LTER:
Annual Active Layer Depths from 2004 to Present in the Boundary Fire Fireline
near Fairbanks, Alaska, ver. 27. Environmental Data Initiative.
https://doi.org/10.6073/pasta/39a508640acba64933f5ad5613b744d0
'''
processing_assumptions = [
  "Boundary Fire and Survey Line Fire annual thaw-depth tables are concatenated into one source product.",
  "thaw_depth is averaged by site and calendar year.",
  "pf_observed is set to 0 only when all flags in a site-year group are N; otherwise it is set to 1.",
  "pf_depth is set equal to the annual mean thaw_depth where pf_observed = 1.",
  "Site coordinates are assigned from a hardcoded lookup table in the script.",
]
temporal_handling = [
  "The first measurement date within each site-year group is retained as the representative output date.",
]
spatial_handling = [
  "Coordinates are not read from the source tables; they are assigned from the script's site_coords lookup.",
]
manual_steps = []
known_limitations = [
  "Annual averaging removes within-year variation in thaw depth.",
  "The hardcoded coordinate lookup should be checked whenever site lists or identifiers change.",
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

source = "Chapin_2025"

# Load the input CSV files
file1 = "239_boundaryfire_active_layer_2024.csv"
file2 = "240_surveylinefire_active_layer_2024.csv"

# Read data
df1 = pd.read_csv(_ROOT_DIR / "data" / source /file1)
df2 = pd.read_csv(_ROOT_DIR / "data" / source /file2)

# Combine datasets
df = pd.concat([df1, df2], ignore_index=True)

# Replace -9999 with NaN and ensure 'depth' is numeric
df.replace(-9999, np.nan, inplace=True)
df['depth'] = pd.to_numeric(df['depth'], errors='coerce')

# Remove rows with flag = 'R'
df = df[df['flag'] != 'R']

# Convert 'date' to datetime and extract year
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df['year'] = df['date'].dt.year

# Mean depth by site and year
mean_depths = df.groupby(['site', 'year'], as_index=False)['depth'].mean()
mean_depths.rename(columns={'depth': 'thaw_depth'}, inplace=True)

# Get first measurement date per group
date_lookup = df.groupby(['site', 'year'], as_index=False)['date'].first()

# Merge thaw depth and date
summary = pd.merge(mean_depths, date_lookup, on=['site', 'year'], how='left')

# Calculate pf_observed and pf_depth
summary['pf_observed'] = 1
summary['pf_observed'] = np.where(
    df.groupby(['site', 'year'])['flag'].apply(lambda flags: all(f == 'N' for f in flags)).values,
    0,
    1
)
summary['pf_depth'] = np.where(summary['pf_observed'] == 1, summary['thaw_depth'], np.nan)

# Add site coordinates
site_coords = {
    'SL1A': (64.65421365, -148.2812152),
    'SL1B': (64.64826898, 64.64826898),
    'BFBURN': (65.15142, -147.47664),
    'BFCONTROL': (65.15472, -147.49046),
    'BFFIRELINEBURNED': (65.15288, -147.48022),
    'BFFIRELINEUNBURNED': (65.15478, -147.48973),
    'BFSAFETYZONE': (65.15254, -147.48017)
}

summary['lat'] = summary['site'].map(lambda x: site_coords.get(x, (np.nan, np.nan))[0])
summary['lon'] = summary['site'].map(lambda x: site_coords.get(x, (np.nan, np.nan))[1])
summary['source'] = source
summary['method'] = 'tp'
summary['obs_limit'] = np.nan
summary.rename(columns={'site':'site_id'}, inplace=True)
summary = summary.drop(columns=['year'])

# Save to CSV
data_utils.check_columns(summary)

summary.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
