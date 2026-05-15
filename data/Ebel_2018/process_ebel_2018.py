"""
metadata_schema_version = 1
source_key = "Ebel_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
last_substantive_update = "2026-04-10"
source_dataset = '''
Ebel, B.A. 2018. Physical and hydraulic properties at recently burned and
long-unburned boreal forest areas in interior Alaska, USA. U.S. Geological
Survey data release. https://doi.org/10.5066/F7610Z7J
'''
processing_assumptions = [
  "pf_observed, thaw_depth, and obs_limit are carried directly from the revised source CSV.",
  "Coordinates are reconstructed from Easting/Northing using the per-row EPSG code and then exported in WGS84.",
  "pf_depth is left missing because the source table does not provide a separate permafrost-depth field.",
]
temporal_handling = [
  "Observation dates are preserved directly from the source CSV without additional aggregation.",
]
spatial_handling = [
  "Rows are split by EPSG:32605 and EPSG:32606 before reprojection to WGS84.",
]
manual_steps = []
known_limitations = [
  "The processed output includes location and observation metadata only; no additional thaw-depth interpretation is added beyond the revised source CSV.",
  "method is exported as unknown because the revised source CSV does not include a reliable observation-tool field.",
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

source = 'Ebel_2018'
df = pd.read_csv(_ROOT_DIR / "data" / source /"Table_1_Locations_revised_formatted.csv")

def to_wgs84(frame, epsg):
    subset = df[df['epsg'] == epsg].copy()
    geometry = gpd.points_from_xy(x=subset['Easting (m)'], y=subset['Northing (m)'])
    gdf = gpd.GeoDataFrame(subset, geometry=geometry, crs=f"EPSG:{epsg}")
    return gdf.to_crs(epsg=4326)

gdf32605 = to_wgs84(df, 32605)
gdf32606 = to_wgs84(df, 32606)

gdf = pd.concat([gdf32605, gdf32606])
gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 
df = pd.DataFrame(gdf.drop(columns=['Easting (m)', 'Northing (m)', 'geometry', 'epsg']))

df['source'] = source
df['obs_depth'] = np.nan
df['pf_depth'] = np.nan
df['method'] = 'unknown'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
