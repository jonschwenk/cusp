"""
metadata_schema_version = 1
source_key = "Chen_2015"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Lawrence Vulis"
last_substantive_update = "2023-06-20"
source_dataset = '''
Chen 2015 ReSALT ALT/GPR source material from ORNL DAAC:
https://daac.ornl.gov/cgi-bin/dsviewer.pl?ds_id=1265
'''
processing_assumptions = [
  "ALT Ave (cm) is treated as the active-layer-thickness input for near-surface permafrost inference.",
  "ALT values greater than 130 cm are treated as not indicating near-surface permafrost.",
]
temporal_handling = [
  "Dates are read directly from the source table and carried into the processed output.",
]
spatial_handling = [
  "Coordinates are read directly from Lon (deg) and Lat (deg) in the source CSV.",
]
manual_steps = []
known_limitations = [
  "This source is intentionally excluded from the canonical combine because it is already represented within another source workflow.",
]
external_dependencies = []
notes = ""
"""
# %% load libraries
import geopandas as gpd
import pandas as pd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Chen_2015' 

full_data = pd.read_csv(_ROOT_DIR / "data" / source /"probe_data.csv",
                        low_memory=False)
full_data[full_data == -9999] = np.nan
full_data[full_data == '-9999'] = np.nan
# remove missing values
full_data = full_data.loc[~np.isnan(full_data['ALT Ave (cm)'])]
# convert to geodataframe
full_data.rename(columns={'Date' : 'date'}, inplace=True)
full_df = data_utils.csvify_working(full_data.copy(),
                                       lon_name="Lon (deg)",
                                       lat_name="Lat (deg)",
                                       source = source,
                                       col_tokeep=['ALT Ave (cm)', 'date', 'Site']) 
full_df= full_df.loc[~np.isnan(full_df['lon'])]

# Process ALT into obs_depth/pf_depth columns. 
full_gdf = data_utils.process_pf_observations(full_df.copy(),
                        alt_name='ALT Ave (cm)', 
                        pf_limit=130)
full_gdf['data_source'] = 'Chen_2015'
full_gdf.drop('pf_depth', axis=1, inplace=True)
full_gdf['method'] = 'tp'
full_gdf['obs_limit'] = 130
                            
full_gdf.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
