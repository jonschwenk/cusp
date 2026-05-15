"""
metadata_schema_version = 1
source_key = "Seward_2022"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Thaler, E.; Del Vecchio, J.; Farley, M.; Thomas, L.; Rowland, J. 2024.
Active Layer Depth and Permafrost Temperatures at the Teller 47 Field Site,
Seward Peninsula, Alaska, 2022. NGEE Arctic / ESS-DIVE.
doi:10.15485/2395957
'''
processing_assumptions = [
  "PF is mapped directly to pf_observed, PfDepth to thaw_depth, and PfTemp to temp.",
  "pf_depth is set equal to thaw_depth where pf_observed = 1.",
  "obs_limit is fixed at 120 cm and method is set to tp for all processed observations.",
  "A source convention of thaw_depth > 120 cm for non-permafrost observations is retained through the processed output rather than recoded.",
]
temporal_handling = [
  "All rows are assigned the single campaign-average date 2022-08-16 because the processed source table does not preserve per-observation dates.",
]
spatial_handling = [
  "The source Easting/Northing coordinates are interpreted as EPSG:32603 and reprojected to WGS84 before export.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all records share one campaign-average date.",
]
external_dependencies = []
notes = ""
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Seward_2022'


df = pd.read_csv(_ROOT_DIR / "data" / source /"Aug2022SurveyTarget_PFdata.csv")
df.rename(columns={"PF": "pf_observed",
                   "PfDepth":"thaw_depth",
                   "PfTemp":"temp"}, inplace=True)
df['date'] = "2022-08-16" # average date

gdf = data_utils.geoify_working(df.copy(), 
                                crs="EPSG:32603",
                                lat_name="Northing",
                                lon_name="Easting",
                                col_tokeep=["pf_observed", "thaw_depth", "temp", "date"])
gdf = gdf.to_crs(epsg=4326)
gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 
gdf['site_id'] = 'TL47'
gdf['pf_depth'] = np.nan

gdf = pd.DataFrame(gdf.drop(columns='geometry'))

gdf['temp'] = df['temp'].replace(-9999, np.nan)

gdf.loc[gdf['pf_observed'] == 1, 'pf_depth'] = gdf.loc[gdf['pf_observed'] == 1, 'thaw_depth']
gdf['source'] = source
gdf['obs_limit'] = 120
gdf['method'] = 'tp'


data_utils.check_columns(gdf)

gdf.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
