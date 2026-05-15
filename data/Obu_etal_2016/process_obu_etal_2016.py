#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Obu_etal_2016"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "ksolander"
last_substantive_update = "2026-04-11"
source_dataset = '''
Obu, Jaroslav; Lantuit, Hugues; Myers-Smith, Isla H.; Heim, Birgit; Wolter,
Juliane; Fritz, Michael. 2016. Permafrost cores and active layer pits on
Herschel Island: core attributes [dataset]. PANGAEA.
https://doi.org/10.1594/PANGAEA.859664
'''
processing_assumptions = [
  "All records in the shapefile are treated as permafrost-present observations, so pf_observed is fixed to 1.",
  "thaw_depth is read directly from THAWDEPTH, while pf_depth is left missing.",
  "obs_limit is read directly from COREDEPTH and site_id from CORENR.",
  "The script preserves ice_content as an ancillary field in the processed output.",
  "method is set to pit for all retained rows because the source archive describes permafrost cores and active-layer pits.",
]
temporal_handling = [
  "All observations are assigned the representative campaign date 2013-06-23.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the shapefile attributes without reprojection.",
]
manual_steps = []
known_limitations = [
  "The script assumes every retained record corresponds to a permafrost-present core or pit observation.",
  "Observation timing is approximate because all rows share one campaign date.",
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
source = 'Obu_etal_2016' 
#os.chdir(r"/Users/ksolander/Documents/GitHub/cusp/data/{}".format(source)) 

# Open the shapefile & extract the data 
dat = gpd.read_file(_ROOT_DIR / "data" / source /'Cores_Herschel_Island_2013_Obu.shp')
dat = pd.DataFrame(dat)
lon = dat['LONGITUDE']
lat = dat['LATITUDE_']
pf_depth = np.nan
thaw_depth = dat['THAWDEPTH']
pf_observed = pd.DataFrame(np.ones(len(thaw_depth)))
pf_observed = pf_observed.squeeze() # convert from dataframe to data series
pf_observed = pf_observed.astype(int) # convert to integer
ice_content = dat['ICECONT']
obs_limit = dat['COREDEPTH']
site_id = dat['CORENR']
date = np.repeat("6/23/2013",len(thaw_depth))
date = pd.Series(pd.to_datetime(date))
year = date.dt.year
month = date.dt.month
day = date.dt.day

# Combine everything into single dataframe
df = pd.DataFrame({
    'Column1': lon,
    'Column2': lat,
    'Column3': pf_depth, # cm depth
    'Column4': pf_observed,
    'Column5': ice_content, # Gravimetric ice content (%)
    'Column6': obs_limit,
    'Column7': site_id,
    'Column8': thaw_depth,    
    'Column9': year,
    'Column10': month,
    'Column11': day,    
    'Column12': date,  
})
df['source'] = source
df['method'] = 'pit'


# Define column names
df.columns = ['lon','lat','pf_depth','pf_observed','ice_content','obs_limit','site_id','thaw_depth','year','month','day','date','source','method']

# Check columns
data_utils.check_columns(df)

# write data to csv

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

