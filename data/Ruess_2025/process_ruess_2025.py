#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Ruess_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Ruess, Roger; Hollingsworth, Teresa Nettleton; Bonanza Creek LTER. 2025.
Bonanza Creek LTER: Active Layer Depth or Permafrost Presence for the Regional
Site Network. LTER Network Member Node.
https://pasta.lternet.edu/package/metadata/eml/knb-lter-bnz/605/6
doi:10.6073/pasta/10324bd31b26ef97fe2cfe6a8537d941
'''
processing_assumptions = [
  "Records are grouped by site and calendar year before summary statistics are computed.",
  "thaw_depth is the mean of non-rock, non--9999 depth observations within each site-year group.",
  "pf_observed is set to 0 when all depths are invalid or all hit types are Rock/None; otherwise it is set to 1 and pf_depth is set equal to thaw_depth.",
  "method is set to tp and obs_limit is left missing.",
]
temporal_handling = [
  "Each site-year summary record is assigned the representative date YYYY-01-01 because the script aggregates observations to annual groups.",
]
spatial_handling = [
  "Latitude and longitude are taken directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "Annual aggregation discards within-year measurement timing and variation.",
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

source = "Ruess_2025"

# Load the CSV
df = pd.read_csv(_ROOT_DIR / "data" / source /"605_RSN_ActiveLayerDepths_2024_with_coords.csv")

df.columns = df.columns.str.strip()
df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

results = []
grouped = df.groupby(['site', 'Year'])

for (site, year), group in grouped:
    valid_depths = group[~group['depth'].isin([-9999])]
    not_rock = valid_depths[~valid_depths['Hit Type'].str.strip().str.lower().eq('rock')]

    thaw_depth = not_rock['depth'].mean() if not not_rock.empty else np.nan

    lat = group['latitude'].dropna().iloc[0] if not group['latitude'].dropna().empty else np.nan
    lon = group['longitude'].dropna().iloc[0] if not group['longitude'].dropna().empty else np.nan

    all_invalid = group['depth'].eq(-9999).all()
    all_rock_or_none = group['Hit Type'].str.strip().isin(['Rock', 'None']).all()

    if np.isnan(thaw_depth) or all_invalid or all_rock_or_none:
        pf_observed = 0
        pf_depth = np.nan
    else:
        pf_observed = 1
        pf_depth = thaw_depth

    results.append({
        'site_id': site,
        'date': f"{int(year)}-01-01",
        'lat': float(lat) if not np.isnan(lat) else np.nan,
        'lon': float(lon) if not np.isnan(lon) else np.nan,
        'thaw_depth': float(thaw_depth) if not np.isnan(thaw_depth) else np.nan,
        'pf_observed': pf_observed,
        'pf_depth': float(pf_depth) if not np.isnan(pf_depth) else np.nan,
        'method': 'tp',
        'obs_limit': np.nan,
        'source': source
    })

final_df = pd.DataFrame(results)

data_utils.check_columns(final_df)
final_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False, float_format='%.15g')
