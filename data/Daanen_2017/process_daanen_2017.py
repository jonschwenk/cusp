#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Daanen_2017"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2025-07-24"
source_dataset = '''
Ronald Daanen. (2017). Elevation and permafrost active layer observations near
two creeks in the foothills of the Brooks Range, Alaska, May 2017.
Arctic Data Center. doi:10.18739/A2H708100.
'''
processing_assumptions = [
  "Only rows with 'no rocks' in Rock_depth [cm] and non-'c.n.p' thaw-depth values are retained.",
  "If the parsed Time field is missing or does not land in 2016, the script assigns a default date of 2016-08-24.",
  "pf_observed is inferred with a 125 cm observation limit and pf_depth is only retained when thaw_depth is below that limit.",
]
temporal_handling = [
  "Dates are parsed from the Time field when possible and otherwise default to 2016-08-24.",
]
spatial_handling = [
  "Lat and Lon are used directly from each creek CSV.",
]
manual_steps = []
known_limitations = [
  "The script applies a fallback date rather than preserving unknown timing when the Time field is unusable.",
  "method is fixed to tp for all rows.",
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

source = "Daanen_2017"


files = [
    "Nice_Lose_Dis.csv",
    "NiceGainDis.csv",
    "OksGainDis.csv",
    "OksLoseDis.csv"
]

final_dfs = []

for file in files:
    df = pd.read_csv(_ROOT_DIR / "data" / source /file)
    df = df[df['Rock_depth [cm]'].astype(str).str.lower().str.contains("no rocks", na=False)]
    df = df[df['Thaw depth [cm]'].astype(str).str.lower() != "c.n.p"]

    def parse_or_default_date(time_str):
        try:
            date = pd.to_datetime(time_str, errors='coerce')
            if pd.isnull(date) or date.year != 2016:
                return "8/24/2016"
            return date.strftime("%-m/%-d/%Y")
        except:
            return "8/24/2016"

    df['date'] = df['Time'].apply(parse_or_default_date)

    file_id = os.path.splitext(file)[0]
    df['site_id'] = df['Point_Id'].astype(str) + "_" + file_id
    df['lat'] = df['Lat']
    df['lon'] = df['Lon']
    df['thaw_depth'] = pd.to_numeric(df['Thaw depth [cm]'], errors='coerce')
    df = df.dropna(subset=['thaw_depth'])  # Drop missing thaw_depths
    df['obs_limit'] = 125
    df['pf_observed'] = np.where(df['thaw_depth'] < 125, 1, 0)
    df['pf_depth'] = np.where(df['thaw_depth'] < 125, df['thaw_depth'], np.nan)
    df['method'] = 'tp'
    df['source'] = source

    final_dfs.append(df[['site_id', 'lat', 'lon', 'date', 'thaw_depth', 'obs_limit', 'pf_observed', 'pf_depth', 'method', 'source']])

final_combined_df = pd.concat(final_dfs, ignore_index=True)
# Save to CSV
data_utils.check_columns(final_combined_df)

final_combined_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
