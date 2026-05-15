#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Sadeghi_etal_2023"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "ksolander"
last_substantive_update = "2026-04-11"
source_dataset = '''
Sadeghi Chorsi, Taha. 2023. Active Layer Thickness Estimation using InSAR,
Meteorological data and Soil parameters. Zenodo.
https://doi.org/10.5281/zenodo.10023340
'''
processing_assumptions = [
  "The script reads a single alt.dat file of InSAR-derived thaw-depth estimates and converts thaw_depth from meters to centimeters.",
  "pf_observed is fixed to 1 for all retained rows.",
  "pf_depth is left missing and method is set to insar.",
  "site_id and obs_limit remain missing because the source grid file does not provide them directly.",
]
temporal_handling = [
  "All observations are assigned the representative date 2019-08-13 even though the source analysis spans summers from 2017 to 2022.",
]
spatial_handling = [
  "Longitude and latitude are read directly from the alt.dat grid points without reprojection.",
]
manual_steps = []
known_limitations = [
  "The processed output collapses a multi-year InSAR product to one representative date.",
  "The script treats modeled InSAR-derived thaw-depth estimates as permafrost-present observations rather than direct field observations.",
]
external_dependencies = []
notes = ""
"""
import pandas as pd
import geopandas as gpd
import numpy as np
import os
import sys
import datetime
from pandas import DataFrame  

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

# Define path to read in data
source = 'Sadeghi_etal_2023' 
#os.chdir(r"/Users/ksolander/Documents/GitHub/cusp/data/{}".format(source)) 


# read in data and reformat
df = pd.read_csv(_ROOT_DIR / "data" / source / 'alt.dat',delimiter='\t')
df.columns = ['lon','lat','thaw_depth']
df['thaw_depth'] = df['thaw_depth']*100 # convert to cm
df['pf_observed'] = 1
df['obs_limit'] = np.nan
df['site_id'] = np.nan
df['pf_depth'] = np.nan

# reformat date information
df['year'] = np.repeat(2019,len(df['thaw_depth']))
df['month'] = np.repeat(8,len(df['thaw_depth'])) # Assume end of thaw season for Southern Hemisphere sites is March 1st
df['day'] = np.repeat(13,len(df['thaw_depth']))
Dates = {'Day': df['day'],  
        'Month': df['month'],  
        'Year': df['year']}  
dates_df = DataFrame(Dates, columns = ['Day', 'Month', 'Year'])
df['date'] = pd.to_datetime(dates_df.Year*10000 + dates_df.Month*100 + dates_df.Day,format='%Y%m%d')

# Read data source and nans for missing data
df['source'] = source

# comment about dates
df['comment'] = 'Date shown is the mean. Actual dates of analysis from June to Sept 2017 to 2022'

data_utils.check_columns(df)

# Merge
df = df[~pd.isna(df['pf_observed'])]
df['pf_observed'] = df['pf_observed'].astype(int)
df['method'] = 'insar'

# Check columns
data_utils.check_columns(df)

# Write data to csv
#os.chdir(r"/Users/ksolander/Documents/GitHub/cusp/data/{}".format(source)) 
df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

