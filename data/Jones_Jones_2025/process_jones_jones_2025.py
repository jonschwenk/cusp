#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jones_Jones_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-20"
source_dataset = '''
Melissa Ward Jones and Benjamin Jones. (2025). Permafrost and Environmental
Monitoring in 2023 and 2024 at the Teshekpuk Lake Observatory, Northern Alaska.
Arctic Data Center. doi:10.18739/A29Z90D9R.
'''
processing_assumptions = [
  "Each input CSV filename encodes the site code and survey date used in the processed output.",
  "Mean_ThawDepth_cm > 100 is treated as pf_observed = 0; otherwise pf_observed = 1.",
  "pf_depth is left empty for all rows because only thaw-depth observations are retained.",
  "The source metadata maps the HCP grid to CALM site U60 and the LCP grid to CALM site U60a.",
  "To avoid double-counting once CALM is used as the canonical monitoring-network source, HCP rows are filtered out for years represented by CALM_U60 in data/CALM/processed_calm.csv.",
  "LCP/U60a rows are retained because the current CALM processed table does not contain U60a as a separate site.",
]
temporal_handling = [
  "Observation dates are parsed from the source filenames and formatted as calendar dates.",
]
spatial_handling = [
  "Lat_Decimal_Degrees and Long_Decimal_Degrees are used directly from each source CSV.",
]
manual_steps = []
known_limitations = [
  "The permafrost classification uses a simple 100 cm threshold rather than an explicit observation-limit field from the source.",
  "method is fixed to tp for all rows.",
  "The CALM overlap handling here is source-specific and intentionally not a general CUSP duplicate detector.",
  "If future CALM processing adds U60a as a distinct site, revisit whether LCP rows should also be filtered or retained.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np
from datetime import datetime

import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Jones_Jones_2025"

# Define the list of file paths
files = [
    "HCP_Grid_Point_Measurements_12July2023.csv",
    "HCP_Grid_Point_Measurements_19July2024.csv",
    "LCP_Grid_Point_Measurements_13July2023.csv",
    "LCP_Grid_Point_Measurements_21July2024.csv"
]

compiled_records = []

def calm_years_for_site(calm_site_id):
    calm_path = _ROOT_DIR / "data" / "CALM" / "processed_calm.csv"
    if not calm_path.exists():
        raise FileNotFoundError(
            f"{calm_path} is required for Jones_Jones_2025 CALM-overlap filtering."
        )

    calm = pd.read_csv(calm_path, usecols=["site_id", "date"])
    calm["year"] = pd.to_datetime(calm["date"], errors="coerce").dt.year
    return set(
        calm.loc[calm["site_id"].eq(calm_site_id), "year"]
        .dropna()
        .astype(int)
        .tolist()
    )

def parse_filename(filename):
    base = os.path.basename(filename).replace('.csv', '')
    parts = base.split('_')
    site_code = parts[0]
    date_str = parts[-1]
    date_parsed = datetime.strptime(date_str, "%d%B%Y")
    return site_code, date_parsed.strftime("%m/%d/%Y"), date_parsed.year

calm_u60_years = calm_years_for_site("CALM_U60")

for file in files:
    site_code, date_str, year = parse_filename(file)
    if site_code == "HCP" and year in calm_u60_years:
        continue

    df = pd.read_csv(_ROOT_DIR / "data" / source /file)

    for _, row in df.iterrows():
        thaw_depth_cm = row.get('Mean_ThawDepth_cm', None)
        pf_observed = 0 if thaw_depth_cm > 100 else 1
        pf_depth = None

        compiled_records.append({
            'site_id': f"{site_code}_{year}_{row['GridID']}",
            'date': date_str,
            'lat': row['Lat_Decimal_Degrees'],
            'lon': row['Long_Decimal_Degrees'],
            'thaw_depth': thaw_depth_cm,
            'pf_observed': pf_observed,
            'pf_depth': pf_depth,
            'method': 'tp',
            'obs_limit': 100,
            'source' : source
        })

# Output to CSV
df_out = pd.DataFrame(compiled_records)


# Save to CSV
data_utils.check_columns(df_out)

df_out.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
