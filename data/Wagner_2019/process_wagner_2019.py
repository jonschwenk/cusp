"""
metadata_schema_version = 1
source_key = "Wagner_2019"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Lawrence Vulis"
last_substantive_update = "2023-06-20"
source_dataset = '''
Wagner, Anna; Barker, Amanda (2018). Data for: Distribution of Polycyclic
Aromatic Hydrocarbons (PAHs) from Legacy Spills at an Alaskan Arctic Site
Underlain by Permafrost. Mendeley Data, V1.
doi:10.17632/2dn4rdmsxn.1
'''
processing_assumptions = [
  "The location and permafrost-depth tables are joined after reformatting station names to a common pattern.",
  "UTM Zone 4 coordinates are converted from EPSG:32604 to WGS84.",
  "A 150 cm pf_depth threshold is used to classify pf_observed in order to accommodate the documented 20 cm uncertainty in permafrost depth.",
]
temporal_handling = [
  "A single field-campaign date of 2015-09-01 is assigned to all processed rows.",
]
spatial_handling = [
  "Easting and Northing coordinates are projected in EPSG:32604 and reprojected to WGS84 before export.",
]
manual_steps = []
known_limitations = [
  "thaw_depth is not reported and remains empty in the processed output.",
  "The processed dates are campaign-level approximations rather than per-observation timestamps.",
]
external_dependencies = []
notes = ""
"""
import pandas as pd
import geopandas as gpd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Wagner_2019'
location_data = pd.read_excel(_ROOT_DIR / "data" / source /"location_data.xlsx".format(source))
pf_obs = pd.read_excel(_ROOT_DIR / "data" / source /"modified_permafrost_depth.xlsx".format(source))

# replace station name from P/A Number to the same as the one in location
#integer_val = pf_obs['Name'].str.replace("(P|A)", "").str.zfill(3)


# Assuming your DataFrame is called df
station_val = pf_obs['Name'].str.replace(r'([A-Z]+)(\d+)', lambda m: f"{m.group(1)}{int(m.group(2)):03d}", regex=True)

#station_val = pf_obs['Name'].str.replace("\d+", "")

new_name = station_val.str.replace("P", "PH-UV-")
new_name = new_name.str.replace("A", "AS-UV-")

#new_name = dummy_name+integer_val
pf_obs['new_name'] = new_name
pf_obs.drop('Name', axis=1, inplace=True)

#  Merge location & pf data tables
combined_data = location_data.merge(right=pf_obs, how='left', left_on='Name', right_on='new_name')

# Convert data into geopandas dataframe
combined_gdf = data_utils.geoify_working(combined_data.copy(),
                                          lon_name='Easting',
                                          lat_name='Northing',
                                          crs='EPSG:32604',                                          
                                          col_tokeep=["MaxDepthPermafrost", 'Final Depth (m)', 'Name'])
combined_gdf = combined_gdf.to_crs(epsg=4326)
combined_gdf['lon'] = [g.coords.xy[0][0] for g in combined_gdf.geometry.values] 
combined_gdf['lat'] = [g.coords.xy[1][0] for g in combined_gdf.geometry.values] 

combined_gdf = data_utils.csvify_working(combined_gdf.copy(),
                                          lon_name='lon',
                                          lat_name='lat',
                                          source=source,                                          
                                          col_tokeep=["MaxDepthPermafrost", 'Final Depth (m)', 'Name'])

combined_gdf.rename(columns={"MaxDepthPermafrost": "pf_depth",
                             'Final Depth (m)': 'obs_limit',
                             'Name':'site_id'},
                    inplace=True)
combined_gdf['date'] = "2015-09-01"
combined_gdf['pf_depth'] = round(combined_gdf['pf_depth'], 2)*100
combined_gdf['obs_limit'] = round(combined_gdf['obs_limit'], 2)*100
combined_gdf['pf_observed'] = (combined_gdf['pf_depth'] < 150)*1
combined_gdf['thaw_depth'] = np.nan
combined_gdf['method'] = 'aug'

data_utils.check_columns(combined_gdf)

#combined_gdf.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
output_path = _ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv"
combined_gdf.to_csv(output_path, index=False)
