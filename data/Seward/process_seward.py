"""
metadata_schema_version = 1
source_key = "Seward"
release_clearance = "approved"
permission_basis = "public_repository_terms"
last_substantive_update = "2026-04-10"
source_dataset = '''
Thaler, E.; Uhlemann, S.; Rowland, J.; Dafflon, B.; Schwenk, J.; Bennett, K.;
Thomas, L. 2023. Machine learning predictions of near-surface permafrost extent
at Teller 27, Teller 47, and the Kougarok 64 Hillslope sites on the Seward
Peninsula, Alaska: Supporting Data. NGEE Arctic / ESS-DIVE.
doi:10.5440/1970774
'''
processing_assumptions = [
  "Three site tables (KG, T47, and T27) are processed separately and concatenated into one output.",
  "Only permafrost presence/absence is retained from the source tables; pf_depth and thaw_depth remain missing.",
  "obs_limit remains missing because the supporting tables do not provide a consistent observation-limit field.",
]
temporal_handling = [
  "KG and T47 records are assigned the representative date 2019-09-15.",
  "T27 records are assigned the representative date 2019-08-15.",
]
spatial_handling = [
  "Source X/Y coordinates are interpreted in EPSG:32603 and reprojected to WGS84 before export.",
]
manual_steps = []
known_limitations = [
  "The processed output contains presence/absence only and does not preserve measured thaw depth or permafrost depth values.",
  "Observation dates are approximate because the script uses representative campaign dates for each site group.",
  "method is exported as unknown because the supporting tables do not include a reliable observation-tool field.",
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

source = 'Seward'

# KG points
df = pd.read_csv(_ROOT_DIR / "data" / source /"KG_points.csv")
df.rename(columns={"PF": "pf_observed"}, inplace=True)
df['date'] = "2019-09-15" # average date

gdf = data_utils.geoify_working(df.copy(), 
                                crs="EPSG:32603",
                                lat_name="Y",
                                lon_name="X",
                                col_tokeep=["pf_observed", "date"])
gdf = gdf.to_crs(epsg=4326)
gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 
gdf['site_id'] = 'KG'

kg = pd.DataFrame(gdf.drop(columns='geometry'))

# T47
df = pd.read_csv(_ROOT_DIR / "data" / source /"T47CombinedTrainingData.csv")
df.rename(columns={"PF": "pf_observed"}, inplace=True)
df['date'] = "2019-09-15" # average date

gdf = data_utils.geoify_working(df.copy(), 
                                crs="EPSG:32603",
                                lat_name="Y",
                                lon_name="X",
                                col_tokeep=["pf_observed", "date"])
gdf = gdf.to_crs(epsg=4326)
gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 
gdf['site_id'] = 'T47'

T47 = pd.DataFrame(gdf.drop(columns='geometry'))

# T27
df = pd.read_csv(_ROOT_DIR / "data" / source /"Teller27_points_trimmed.csv")
df.rename(columns={"PF": "pf_observed"}, inplace=True)
df['date'] = "2019-08-15" # average date

gdf = data_utils.geoify_working(df.copy(), 
                                crs="EPSG:32603",
                                lat_name="Y",
                                lon_name="X",
                                col_tokeep=["pf_observed", "date"])
gdf = gdf.to_crs(epsg=4326)
gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 
gdf['site_id'] = 'T27'

T27 = pd.DataFrame(gdf.drop(columns='geometry'))

df = pd.concat([kg, T47, T27])
df['source'] = source
df['pf_depth'] = np.nan
df['thaw_depth'] = np.nan
df['obs_limit'] = np.nan
df['method'] = 'unknown'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
