#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Beer_etal_2013"
release_clearance = "do_not_release"
permission_basis = "public_repository_terms"
original_author = "ksolander"
last_substantive_update = "2026-04-11"
source_dataset = '''
Beer, Christian; Fedorov, Alexander N.; Torgovkin, Y. 2013. Maps of subsoil
temperature and active layer depth of Yakutian ASSR (Autonomous Soviet
Socialist Republic of the Soviet Union) [dataset]. PANGAEA.
https://doi.org/10.1594/PANGAEA.808240
'''
processing_assumptions = [
  "The netCDF map product is flattened into one row per grid cell.",
  "Any non-null ALT grid-cell value is treated as pf_observed = 1, while missing ALT is treated as pf_observed = 0.",
  "pf_depth is populated from ALT and converted from meters to centimeters, while thaw_depth remains missing.",
  "The script stores the map-period note as a comments field rather than a per-observation date.",
]
temporal_handling = [
  "No observation date is assigned; the comments field notes that the map product represents the period 1960-1987.",
]
spatial_handling = [
  "All lon/lat grid combinations are expanded from the source netCDF arrays into point-like rows.",
]
manual_steps = []
known_limitations = [
  "This is a gridded map product rather than a direct observation dataset and is therefore not intended for the canonical CUSP observation release.",
  "The flattened grid representation can look observation-like even though the source is a spatial synthesis product.",
]
external_dependencies = []
notes = "Tracked in release planning as a map/synthesis product rather than an observation source."
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

import os
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

# Define path to read in data
source = 'Beer_etal_2013' 
#os.chdir(r"/Users/ksolander/Documents/GitHub/cusp/data/{}".format(source)) 

# Open the NetCDF file & extract the data 
dat = xr.open_dataset(_ROOT_DIR / "data" / source /'yakustk_active_layer_depth_map.nc')
lon = dat['lon']
lat = dat['lat']
pf_depth = np.array(dat['ALT']).flatten()
pf_depth = pf_depth*100 #convert to cm

# Presence or absence of permafrost
pf_observed = pf_depth
pf_observed = np.where((~np.isnan(pf_observed.astype(float))), 1, 0)

# Determine all possible lat lon combos from given array to make 1D
lat_lon_combo = list(product(lat,lon))
lat_np = np.array(lat_lon_combo)[:,0]
lon_np = np.array(lat_lon_combo)[:,1]

# define blank variables as nan
obs_limit = np.nan
site_id = np.nan
thaw_depth = np.nan
year = np.nan
month = np.nan
day = np.nan
date = np.nan
method = np.nan

# Combine everything into single dataframe
df = pd.DataFrame({
    'Column1': lon_np,
    'Column2': lat_np,
    'Column3': pf_depth,
    'Column4': pf_observed,
    'Column5': obs_limit,
    'Column6': site_id,
    'Column7': thaw_depth,    
    'Column8': year,
    'Column9': month,
    'Column10': day,    
    'Column11': date,  
    'Column12': method,
})
df['source'] = source
df['comments'] = "The data represent the period 1960-1987."

# Define column names
df.columns = ['lon','lat','pf_depth','pf_observed','obs_limit','site_id','thaw_depth','year','month','day','date','method','source','comments']


# df['date'].replace('', pd.NA, inplace=True)
# df.dropna(subset=['date'], inplace=True)
# Check columns
data_utils.check_columns(df)

# write data to csv
#os.chdir(r"/Users/ksolander/Documents/GitHub/cusp/data/{}".format(source)) 
#df.to_csv(os.path.join(os.getcwd(), r"processed_{}.csv".format( source)), index=False)
df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
