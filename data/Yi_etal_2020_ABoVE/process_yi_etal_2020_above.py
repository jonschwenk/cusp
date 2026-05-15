#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Yi_etal_2020_ABoVE"
release_clearance = "deferred"
permission_basis = "published_literature"
original_author = "Kurt Solander"
last_substantive_update = "2024-09-20"
source_dataset = '''
Yi, Y., Kimball, J. S., Chen, R. H., Moghaddam, M., Reichle, R. H.,
Mishra, U., Zona, D., and Oechel, W. C. Characterizing permafrost active
layer dynamics and sensitivity to landscape spatial heterogeneity in Alaska.
The Cryosphere, 12, 145-161. https://doi.org/10.5194/tc-12-145-2018
'''
processing_assumptions = [
  "ALT is converted from meters to centimeters.",
  "Every non-null ALT grid-cell value is treated as pf_observed = 1.",
  "The netCDF grid is flattened into point-like rows for each time slice.",
]
temporal_handling = [
  "Year is derived from time_bnds and each annual record is assigned a fixed date of July 2.",
]
spatial_handling = [
  "The 1 km netCDF lon/lat grid is repeated and flattened into one row per grid cell per year.",
]
manual_steps = [
  "Download Alaska_active_layer_thickness_1km_2001-2015.nc4 into data/Yi_etal_2020_ABoVE before running the script.",
]
known_limitations = [
  "The current flattening approach would emit about 43,956,000 rows and is therefore not suitable for the canonical observation-level release as-is.",
]
external_dependencies = [
  "Gitignored raw input Alaska_active_layer_thickness_1km_2001-2015.nc4 hosted outside the repo; see EXTERNAL_DATA_SOURCES.md.",
]
notes = ""
"""

import numpy as np
import pandas as pd
import xarray as xr
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Yi_etal_2020_ABoVE"
source_dir = _ROOT_DIR / "data" / source
input_path = source_dir / "Alaska_active_layer_thickness_1km_2001-2015.nc4"
output_path = source_dir / f"processed_{source.lower()}.csv"

# Open the NetCDF file & extract the data 
dat = xr.open_dataset(input_path)
lon = dat['lon']
lat = dat['lat']
pf_depth = np.array(dat['ALT']).flatten()
pf_depth = pf_depth*100 #convert to cm

# Presence or absence of permafrost
pf_observed = pf_depth
pf_observed = np.where((~np.isnan(pf_observed.astype(float))), 1, 0)

# convert 2D to 1D data
lon_np = np.repeat(np.array(lon).flatten(),len(dat['time']))
lat_np = np.repeat(np.array(lat).flatten(),len(dat['time']))

# extract the date information
time_bnds = dat['time_bnds']
year = time_bnds.dt.year[:,0]
year_np = np.repeat(year,len(np.array(lon).flatten()))
month = [7] * 15 * len(np.array(lon).flatten())
day = [2] * 15 * len(np.array(lon).flatten())
date = pd.to_datetime(pd.DataFrame({'year': year_np, 'month': month, 'day': day}))

# define blank variables as nan
obs_limit = np.nan
site_id = np.nan
obs_depth = np.nan


# Combine everything into single dataframe
df = pd.DataFrame({
    'Column1': lon_np,
    'Column2': lat_np,
    'Column3': pf_depth,
    'Column4': pf_observed,
    'Column5': obs_limit,
    'Column6': site_id,
    'Column7': obs_depth,    
    'Column8': year_np,
    'Column9': month,
    'Column10': day,    
    'Column11': date,  
})
df['source'] = source

# Define column names
df.columns = ['lon','lat','pf_depth','pf_observed','obs_limit','site_id','obs_depth','year','month','day','date','source']

# Check columns
data_utils.check_columns(df)

# write data to csv
df.to_csv(output_path, index=False)
