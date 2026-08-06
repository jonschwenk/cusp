#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jorgenson_Kanevskiy_2022_Gosling"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
source_dataset = '''
Mark Jorgenson and Mikhail Kanevskiy. (2022). Gosling Lake, Alaska,
Topography, Vegetation, Soils, Soil temperatures, and Site-Environmental Data,
2005-2021. Arctic Data Center. doi:10.18739/A22F7JS4S.
'''
processing_assumptions = [
  "SoilPFrost codes p and y are treated as permafrost present, a and n as absent, and u as unresolved.",
  "pf_depth is set equal to thaw_depth only when pf_observed is definitively present.",
  "For permafrost-absent rows, SoilThawDep_cm is the source's recorded maximum probing depth in totally unfrozen soil; CUSP moves that value to obs_limit and clears thaw_depth.",
  "SoilObsDep_cm is retained as a provenance field but is not used as the permafrost observation limit because it records the separately described soil-profile depth and is shallower than the frost-probe reach for all absence rows.",
  "method is tp because the metadata explicitly describes thaw-depth and maximum-unfrozen-depth measurements with a metal probe.",
  "Rows with missing thaw_depth are dropped from the processed output.",
]
temporal_handling = [
  "Dates are parsed from the source Date column and reformatted to calendar dates.",
]
spatial_handling = [
  "LatWGS84 and LonWGS84 are used directly from the source archive.",
]
manual_steps = []
known_limitations = [
  "Rows with unresolved SoilPFrost codes are dropped rather than exported with missing pf_observed.",
  "This dedicated release is primary for 15 matching site-years also compiled in Jorgenson_Kanevskiy_2025; the copies are removed in the 2025 inventory processor.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np
from pandas import NA
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Jorgenson_Kanevskiy_2022_Gosling"

# Load the CSV, treating 999 as NaN
df = pd.read_csv(_ROOT_DIR / "data" / source /"Gosling_Lake_Alaska_Site_Environmental_Data_Archive_2022.csv", na_values=999)

processed = []

for _, row in df.iterrows():
    thaw_depth = row['SoilThawDep_cm']

    # Safely get a lowercase string code or None
    raw = row['SoilPFrost']
    code = str(raw).strip().lower() if pd.notna(raw) else None

    # Map codes to 1/0/NaN (use NaN to keep numeric dtype)
    code_map = {'p': 1, 'y': 1, 'a': 0, 'n': 0, 'u': pd.NA}
    pf_observed = code_map.get(code, pd.NA)

    # Only set pf_depth when pf_observed is exactly 1
    pf_depth = thaw_depth if (pf_observed is not pd.NA and pf_observed == 1) else np.nan

    processed.append({
        'site_id': row['SiteID'],
        'date': pd.to_datetime(row['Date'], errors='coerce').strftime('%m/%d/%Y') if pd.notna(row['Date']) else np.nan,
        'lat': row['LatWGS84'],
        'lon': row['LonWGS84'],
        'thaw_depth': thaw_depth,
        'pf_observed': pf_observed,
        'pf_depth': pf_depth,
        'method': 'tp',
        'obs_limit': row['SoilObsDep_cm'],
        'gosling_soil_profile_obs_depth_cm': row['SoilObsDep_cm'],
        'org_thick': row['SoilOrgSurfThk_cm'],
        'source' : source
    })

# Create and export DataFrame
out_df = pd.DataFrame(processed)
out_df = out_df.dropna(subset=["thaw_depth"])
out_df = out_df.dropna(subset=["pf_observed"]).copy()
out_df['pf_observed'] = out_df['pf_observed'].astype("Int64")
out_df['pf_depth'] = pd.to_numeric(out_df['pf_depth'], errors='coerce')
absence = out_df['pf_observed'].eq(0)
out_df.loc[absence, 'obs_limit'] = out_df.loc[absence, 'thaw_depth']
out_df.loc[absence, 'thaw_depth'] = np.nan
out_df.loc[~absence, 'obs_limit'] = np.nan

if int(absence.sum()) != 6 or out_df.loc[absence, 'obs_limit'].isna().any():
    raise ValueError("Unexpected Gosling absence count or missing maximum probing depth.")

# Save to CSV
data_utils.check_columns(out_df)

out_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
