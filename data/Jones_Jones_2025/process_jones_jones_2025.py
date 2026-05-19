#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jones_Jones_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-05-19"
source_dataset = '''
Melissa Ward Jones and Benjamin Jones. (2025). Permafrost and Environmental
Monitoring in 2023 and 2024 at the Teshekpuk Lake Observatory, Northern Alaska.
Arctic Data Center. doi:10.18739/A29Z90D9R.
'''
processing_assumptions = [
  "Each input CSV filename encodes the site code and survey date used in the processed output.",
  "Mean_ThawDepth_cm > 100 is treated as pf_observed = 0; otherwise pf_observed = 1.",
  "pf_depth is left empty for all rows because only thaw-depth observations are retained.",
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
  "The source metadata describes the HCP grid as CALM site U60 and the LCP grid as CALM site U60a, so this source overlaps conceptually and spatially with CALM/GTN-P. The current CUSP duplicate detector only removes exact canonical duplicates and will not catch this source-level/grid-level overlap.",
  "Before CALM and Jones_Jones_2025 are both included in the release, CUSP should use a less strict deduplication review or a source-specific filter; U60 versus U60a may not be sufficient by itself to decide which rows to retain.",
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

def parse_filename(filename):
    base = os.path.basename(filename).replace('.csv', '')
    parts = base.split('_')
    site_code = parts[0]
    date_str = parts[-1]
    date_parsed = datetime.strptime(date_str, "%d%B%Y")
    return site_code, date_parsed.strftime("%m/%d/%Y"), date_parsed.year

for file in files:
    site_code, date_str, year = parse_filename(file)
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
