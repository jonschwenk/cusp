#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Langer_etal_2020"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "ksolander"
last_substantive_update = "2026-04-11"
source_dataset = '''
Langer, Moritz; Kaiser, Soraya; Oehme, Alexander; Schneider von Deimling,
Thomas; Jacobi, Stephan. 2020. Active layer thickness (ALT) on the North Slope
of Alaska (USA) and Manitoba (Canada) in summer 2018 and 2019 [dataset].
PANGAEA. https://doi.org/10.1594/PANGAEA.913423
'''
processing_assumptions = [
  "Only rows with numeric active-layer depth are retained from the source table.",
  "Rows with comment = rocks are dropped before permafrost presence is derived.",
  "pf_observed is set to 0 only for comment = end of probe and 1 otherwise.",
  "obs_limit is assigned by year using a fixed mapping of 145 cm for 2018 and 200 cm for 2019.",
  "pf_depth is set equal to thaw_depth where pf_observed = 1.",
  "method is set to tp for all retained rows because the source reports active-layer depth probe measurements.",
]
temporal_handling = [
  "Source dates are parsed directly from the PANGAEA table and preserved per observation.",
]
spatial_handling = [
  "Coordinates are read directly from the source table without reprojection.",
]
manual_steps = []
known_limitations = [
  "The probe-length assumption is hardcoded from source interpretation rather than an explicit observation-limit field in each row.",
]
external_dependencies = []
notes = ""
"""

import geopandas as gpd
import numpy as np
import os
import sys
import datetime
from datetime import date
import pandas as pd
from pandas import DataFrame  
import xarray as xr
from netCDF4 import Dataset
import itertools
from itertools import product

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

# Define path to read in data
source = 'Langer_etal_2020' 


# Open the dat file & extract the data 
dat = pd.DataFrame(pd.read_csv(_ROOT_DIR / "data" / source /'NorthSlope_Alaska-Manitoba_Canada_Active_layer_depth.tab', sep='\t',skiprows=202,header=0))
df = dat
df[['Event', 'Area', 'ID', 'Latitude', 'Longitude','Date/Time','ALD [cm]','Comment']]

df['ALD [cm]'] = pd.to_numeric(df['ALD [cm]'], errors='coerce')  # convert invalid to NaN
df = df.dropna(subset=['ALD [cm]'])

# Extract data from dataframe

df.rename(columns={'Latitude':'lat', 'Longitude':'lon',
                   'ALD [cm]':'thaw_depth','Date/Time':'date', 'ID':'site_id', 'Comment':'comment'}, inplace=True)

df.drop(df[df['comment'] == 'rocks'].index, inplace=True)

df['pf_observed'] = (~df['comment'].isin(['end of probe'])).astype(int)


df['date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['date'])
df['year'] = df['date'].dt.year

df['source'] = source
df['method'] = 'tp'

df['obs_limit'] = df['year'].map({2018: 145, 2019: 200})
df['pf_depth'] = np.where(df['pf_observed'] == 1, df['thaw_depth'], np.nan)

df = df.drop(columns = ['year', 'comment', 'Event', 'Area'])

# Define column names
# df.columns = ['lon','lat','thaw_depth','pf_observed','obs_limit','site_id','method','year','month','day','date','source','comments', 'pf_depth']

# Check columns
data_utils.check_columns(df)

# write data to csv
df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

