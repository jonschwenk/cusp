#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Schwenk_PFRR"
release_clearance = "approved"
permission_basis = "self_generated"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Schwenk, Jon. 2024. Poker Flats Research Range observations, unpublished.
This script processes the frost-probing subset of the broader PFRR field
campaign package described in the local readme files.
'''
processing_assumptions = [
  "Permafrost? is mapped directly to pf_observed, and pf_depth is set equal to thaw_depth when pf_observed = 1.",
  "Rows marked Hit bedrock? = 1 are excluded from the processed output.",
  "obs_limit is fixed at 180 cm and method is set to tp for all retained observations.",
]
temporal_handling = [
  "The Date and time field is parsed and reduced to date-only precision in the processed output.",
]
spatial_handling = [
  "Coordinates are read directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "This script only processes the frost-probing subset of the broader PFRR package.",
  "Locations where the probe hit bedrock are excluded rather than represented as censored observations.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np

import re
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Schwenk_PFRR"

# Import data 
df = pd.read_csv(_ROOT_DIR / "data" / source /"fairbanks_frost_probing_Sep_2024.csv")




# Rename columns
column_mapping = {
    "Latitude": "lat",
    "Longitude": "lon",
    "Name": "site_id",
    "Permafrost?": "pf_observed",
    "Moss thickness (cm)":"org_thick",
    "Active layer thickness (cm)":"thaw_depth"
}
df.rename(columns=column_mapping, inplace=True)

df['date'] = pd.to_datetime(df['Date and time']).dt.date

df.loc[df['pf_observed'] == 1, 'pf_depth'] = df['thaw_depth']

df['obs_limit'] = 180
df['method'] = 'tp'
df = df[df['Hit bedrock?'] != 1]
df['source'] = source
df = df.drop(columns=['Description', 'Hit bedrock?', 'Maximum probe depth', 'Date and time'])

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
