"""
metadata_schema_version = 1
source_key = "James_2020"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Lawrence Vulis"
last_substantive_update = "2026-04-11"
source_dataset = '''
James, S.R.; Minsley, B.J.; Pastick, N.J.; Sullivan, T.D. 2020. Alaska
permafrost characterization: Geophysical and related field data collected from
2019-2020. U.S. Geological Survey data release.
https://doi.org/10.5066/P9I6VUQV
'''
processing_assumptions = [
  "ThawDepth sentinel values of 999 and 888 are treated as observation-limit codes and remapped to 200 cm and 120 cm, respectively, before permafrost presence is inferred.",
  "Near-surface permafrost is inferred with data_utils.process_pf_observations using a 132 cm threshold and the sentinel-derived observation-limit array.",
  "Dates are cleaned from YYYYMMDD strings after stripping any trailing comma-delimited suffixes.",
  "The final output preserves the processed thaw depth, pf_observed, pf_depth, obs_limit, and source coordinates from the shapefile.",
  "method is set to tp for all retained rows because the source release represents thaw-depth probe observations.",
]
temporal_handling = [
  "Per-observation dates are preserved after cleanup from the source SampleDate field.",
]
spatial_handling = [
  "Coordinates are read directly from the source shapefile attributes; the geometry is dropped after tabular export.",
]
manual_steps = []
known_limitations = [
  "The meaning of the 999 and 888 thaw-depth sentinels should still be confirmed against the original field protocol; CUSP currently interprets them as 200 cm and 120 cm observation limits to stay consistent with centimeter-based thaw depths.",
  "A non-fatal PROJ/GDAL environment warning has appeared during some rebuilds, even though the shapefile still reads successfully.",
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

source = 'James_2020'
gdf = gpd.read_file(_ROOT_DIR / "data" / source /"AK2019-2020_Locations_ThawDepths.shp".format(source))
gdf[gdf == -9999] = np.nan
gdf[gdf == '-9999'] = np.nan

# identify the obs limit data
obs_limit_mask_2m = gdf['ThawDepth'] == 999
obs_limit_mask_1_2m = gdf['ThawDepth'] == 888
obs_limit_mask = np.logical_or(obs_limit_mask_2m, obs_limit_mask_1_2m)
gdf.loc[obs_limit_mask_2m, 'ThawDepth'] = 200.0
gdf.loc[obs_limit_mask_1_2m, 'ThawDepth'] = 120.0
obs_lim_array = pd.Series(np.nan, index=gdf.index, dtype='float64')
obs_lim_array.loc[obs_limit_mask_2m] = 200.0
obs_lim_array.loc[obs_limit_mask_1_2m] = 120.0

# Subset the values with data
has_probe_mask = ~np.isnan(gdf['ThawDepth'])
subset_data = gdf.loc[has_probe_mask]

subset_data.rename(columns={'SampleDate' : 'date',
                            'Lon_WGS84' : 'lon',
                            'Lat_WGS84' : 'lat',
                            'SiteID':'site_id'},
                   inplace=True)
subset_obs_limit_mask = obs_limit_mask.loc[subset_data.index]
subset_obs_lim_array = obs_lim_array.loc[subset_data.index]

# identify pf_observed
subset_data = data_utils.process_pf_observations(subset_data.copy(), 
                        alt_name='ThawDepth', 
                        pf_limit=132,
                        obs_limit_val=subset_obs_lim_array,
                        obs_limit_mask=subset_obs_limit_mask)

# reformat date string to be nicer
fix_date_mask = subset_data['date'].str.contains(",")
subset_data.loc[fix_date_mask, 'date'] = subset_data.loc[fix_date_mask, 'date'].str.split(",").str.get(0)
subset_data['date'] = pd.to_datetime(subset_data['date'], format="%Y%m%d").astype(str).values

# Drop and write
subset_data.drop(["Elevation", "ERT_x_dist", "DataType", "X_UTMz6", "Y_UTMz6", "Comment"],
                 axis=1,
                 inplace=True)
df = pd.DataFrame(subset_data.drop('geometry',axis=1))
df['source'] = source
df['method'] = 'tp'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
