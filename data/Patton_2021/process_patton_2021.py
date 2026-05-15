"""
metadata_schema_version = 1
source_key = "Patton_2021"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "Lawrence Vulis"
last_substantive_update = "2026-04-10"
source_dataset = '''
Patton, A. I.; Rathburn, S. L.; Capps, D. M.; McGrath, D.; Brown, R. A. 2021.
Ongoing landslide deformation in thawing permafrost. Geophysical Research
Letters 48, e2021GL092959. https://doi.org/10.1029/2021GL092959
'''
processing_assumptions = [
  "Three GPR transects are processed separately and then concatenated into one output table.",
  "alt_m is converted from meters to centimeters before permafrost presence is inferred.",
  "data_utils.process_pf_observations is used with a 130 cm threshold and fixed per-transect survey dates of 2018-08-14, 2018-08-15, and 2018-08-16.",
  "transect_point is assigned from the generated point index after interpolation along each transect line.",
  "method is set to gp and pf_depth is left missing in the final output.",
]
temporal_handling = [
  "Each transect is assigned a fixed survey date hardcoded in the script.",
]
spatial_handling = [
  "Transect coordinates are interpreted in EPSG:6334, transformed through UTM zone 5N, and exported in WGS84.",
]
manual_steps = []
known_limitations = [
  "The script assumes NAD83(2011) and WGS84 are close enough for this application, which the original author flagged as an unresolved source of roughly meter-scale horizontal error.",
  "The script notes that transects are not yet resampled to a coarser regular spacing beyond the generated point series.",
]
external_dependencies = []
notes = ""
"""

# %% load libraries
import pandas as pd
import geopandas as gpd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Patton_2021'
sp_line01 = pd.read_csv(_ROOT_DIR / "data" / source /"GPR" / "SP_LINE0202_picks.csv".format(source), delimiter='\t')
sp_line02 = pd.read_csv(_ROOT_DIR / "data" / source /"GPR" / "SP_LINE0302_picks.csv".format(source))
pt_line03 = pd.read_csv(_ROOT_DIR / "data" / source /"GPR" / "PT_LINE0403_picks.csv".format(source), delimiter='\t')

#  try with new function (which will have to be ported elsewhere.)
sp_line01['alt_m'] = sp_line01['alt_m'] * 100 # convert m to cm
sp_line02['alt_m'] = sp_line02['alt_m'] * 100 
pt_line03['alt_m'] = pt_line03['alt_m'] * 100

sp_line01_df = data_utils.process_pf_observations(working_df=sp_line01.copy(), alt_name='alt_m', 
                                                  pf_limit=130, date='2018-08-14')

sp_line02_df = data_utils.process_pf_observations(working_df=sp_line02.copy(), alt_name='alt_m', 
                                                  pf_limit=130,  date='2018-08-15')

pt_line03_df = data_utils.process_pf_observations(working_df=pt_line03.copy(), alt_name='alt_m', 
                                                  pf_limit=130, date='2018-08-16')

# TO DO: RESAMPLE TRANSECTS TO BE EVERY 2 or 3 m...
sp_line01_gdf = data_utils.geoify_working(sp_line01_df, crs="EPSG:6334", lat_name="northing_m", lon_name="easting_m").to_crs("EPSG:32605")
sp_line02_gdf = data_utils.geoify_working(sp_line02_df, crs="EPSG:6334", lat_name="northing_m", lon_name="easting_m").to_crs("EPSG:32605")
pt_line03_gdf = data_utils.geoify_working(pt_line03_df, crs="EPSG:6334", lat_name="northing_m", lon_name="easting_m").to_crs("EPSG:32605") 

sp_line01_gdf = sp_line01_gdf.to_crs(epsg=4326)
sp_line02_gdf = sp_line02_gdf.to_crs(epsg=4326)
pt_line03_gdf = pt_line03_gdf.to_crs(epsg=4326)

# add transect name/point, will definitely need to revisit this later to do it "better"
sp_line01_gdf['transect_name'] = 'sp_line01'
sp_line01_gdf['transect_point'] = sp_line01_gdf.index.values.copy()
sp_line01_gdf['site_id'] = 'sp_line01'
sp_line01_gdf.to_crs(epsg=4326)

sp_line02_gdf['transect_name'] = 'sp_line02'
sp_line02_gdf['transect_point'] = sp_line02_gdf.index.values.copy()
sp_line02_gdf['site_id'] = 'sp_line02'
sp_line02_gdf.to_crs(epsg=4326)

pt_line03_gdf['transect_name'] = 'pt_line03'
pt_line03_gdf['transect_point'] = pt_line03_gdf.index.values.copy()
pt_line03_gdf['site_id'] = 'pt_line03'
pt_line03_gdf.to_crs(epsg=4326)

# other stuff
for df in [sp_line01_gdf, sp_line02_gdf, pt_line03_gdf]:

    df['lon'] = [g.coords.xy[0][0] for g in df.geometry.values] 
    df['lat'] = [g.coords.xy[1][0] for g in df.geometry.values] 
    df['source'] = source

# merge
df_out = pd.concat([pd.DataFrame(sp_line01_gdf.drop(columns='geometry')), 
                   pd.DataFrame(sp_line02_gdf.drop(columns='geometry')), 
                   pd.DataFrame(pt_line03_gdf.drop(columns='geometry'))])

df_out['method'] = 'gp'
df_out['pf_depth'] = np.nan

data_utils.check_columns(df_out)

df_out.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
