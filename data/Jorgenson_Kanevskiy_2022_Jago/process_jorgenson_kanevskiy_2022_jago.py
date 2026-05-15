#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jorgenson_Kanevskiy_2022_Jago"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2025-07-25"
source_dataset = '''
Mark Jorgenson and Mikhail Kanevskiy. (2022). Jago Alaska Topography,
Vegetation, Soils, and Site-Environmental Data 2009-2018.
Arctic Data Center. doi:10.18739/A2XP6V496.
'''
processing_assumptions = [
  "SoilPFrost code p is treated as permafrost present, a as absent, and u as unresolved.",
  "pf_depth is set equal to thaw_depth only when pf_observed is present.",
  "The source SoilObsDep_cm field is retained as obs_limit.",
]
temporal_handling = [
  "Dates are parsed from the source Date column and reformatted to calendar dates.",
]
spatial_handling = [
  "LatWGS84 and LonWGS84 are used directly from the source archive.",
]
manual_steps = []
known_limitations = [
  "method is exported as unknown because the source archive does not specify a clean controlled-vocabulary method.",
  "Rows with unresolved SoilPFrost codes are dropped rather than exported with missing pf_observed.",
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

source = "Jorgenson_Kanevskiy_2022_Jago"

# Load the CSV, treating 999 as NaN
df = pd.read_csv(_ROOT_DIR / "data" / source /"Jago_Site_Environmental_Data_Archive_2022.csv", na_values=999)

processed = []

for _, row in df.iterrows():
    thaw_depth = row['SoilThawDep_cm']
    pfrost_code = str(row['SoilPFrost']).lower() if pd.notna(row['SoilPFrost']) else None

    if pfrost_code == 'p':
        pf_observed = 1
    elif pfrost_code == 'a':
        pf_observed = 0
    elif pfrost_code == 'u':
        pf_observed = None
    else:
        pf_observed = None

    pf_depth = thaw_depth if pf_observed == 1 else None

    processed.append({
        'site_id': row['SiteID'],
        'date': pd.to_datetime(row['Date'], errors='coerce').strftime('%m/%d/%Y') if pd.notna(row['Date']) else None,
        'lat': row['LatWGS84'],
        'lon': row['LonWGS84'],
        'thaw_depth': thaw_depth,
        'pf_observed': pf_observed,
        'pf_depth': pf_depth,
        'method': 'unknown',
        'obs_limit': row['SoilObsDep_cm'],
        'org_thick': row['SoilOrgSurfThk_cm'],
        'source' : source
    })

# Create and export DataFrame
out_df = pd.DataFrame(processed)
out_df = out_df.dropna(subset=["pf_observed"]).copy()
out_df['pf_observed'] = out_df['pf_observed'].astype(int)

# Save to CSV
data_utils.check_columns(out_df)

out_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
