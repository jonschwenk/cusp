#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jones_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2025-07-25"
source_dataset = '''
Benjamin Jones, Mikhail Kanevskiy, Melissa Ward Jones, Phillip Wilson,
Isaiah Ditmer, Benjamin Gaglioti, Eric Klein, Rodrigo Rangel, Kristi Wallace,
Miriam Jones, Matthew Wooller, and Yuri Shur. (2025). Near-surface permafrost
studies near Bethel and remotely sensing ice wedge networks across the Yukon
Kuskokwim Delta, Alaska 2025. Arctic Data Center. doi:10.18739/A24B2X68B.
'''
processing_assumptions = [
  "Thaw depths are computed from the difference between ground-surface and top-of-permafrost elevations in the source table.",
  "Rows marked 'greater than probe length' are treated as pf_observed = 0 with thaw_depth and pf_depth left empty.",
  "method is set to tp by default and upgraded to aug when thaw_depth exceeds 150 cm.",
]
temporal_handling = [
  "Fixed dates of 2024-10-03 and 2024-10-01 are assigned to the BET-7 and BET-31 transects, respectively.",
]
spatial_handling = [
  "Latitude and longitude values added by Ben Jones are used directly from the source CSV.",
]
manual_steps = []
known_limitations = [
  "obs_limit is only recorded for tp rows and remains empty for aug rows.",
  "The processed output is derived from two fixed transect dates rather than per-point timestamps.",
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

source = "Jones_2025"

# Load the dataset
df = pd.read_csv(_ROOT_DIR / "data" / source /"Bethel_Thaw_Depth_Transects.csv", encoding="ISO-8859-1")

records = []
for _, row in df.iterrows():
    # BET-7
    thaw_7_raw = row['BET-7 Thaw depth']
    is_gtpl_7 = str(row['BET-7 Thaw Depth (m asl)']).strip().lower() == 'greater than probe length'
    thaw_depth_7 = None if is_gtpl_7 else thaw_7_raw
    pf_observed_7 = 0 if is_gtpl_7 else 1
    pf_depth_7 = thaw_depth_7 if pf_observed_7 == 1 else None
    method_7 = 'aug' if thaw_depth_7 and thaw_depth_7 > 150 else 'tp'
    obs_limit_7 = np.nan if method_7 == 'aug' else 150
    records.append({
        'site_id': f"BET_7_{int(row['Distance (m)'])}",
        'date': '10/3/2024',
        'lat': float(row['BET-7 Lat']),
        'lon': float(row['BET-7 Lon']),
        'thaw_depth': thaw_depth_7,
        'pf_observed': pf_observed_7,
        'pf_depth': pf_depth_7,
        'method': method_7,
        'obs_limit': obs_limit_7,
        'source' : source
    })

    # BET-31
    thaw_31_raw = row['BET-31 Thaw depth']
    is_gtpl_31 = str(row['BET-31 Thaw Depth (m asl)']).strip().lower() == 'greater than probe length'
    thaw_depth_31 = None if is_gtpl_31 else thaw_31_raw
    pf_observed_31 = 0 if is_gtpl_31 else 1
    pf_depth_31 = thaw_depth_31 if pf_observed_31 == 1 else None
    method_31 = 'aug' if thaw_depth_31 and thaw_depth_31 > 150 else 'tp'
    obs_limit_31 = np.nan if method_31 == 'aug' else 150
    records.append({
        'site_id': f"BET_31_{int(row['Distance (m)'])}",
        'date': '10/1/2024',
        'lat': float(row['BET-31 Lat']),
        'lon': float(row['BET-31 Lon']),
        'thaw_depth': thaw_depth_31,
        'pf_observed': pf_observed_31,
        'pf_depth': pf_depth_31,
        'method': method_31,
        'obs_limit': obs_limit_31,
        'source' : source
    })

# Save to CSV
out_df = pd.DataFrame(records)

data_utils.check_columns(out_df)

out_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
