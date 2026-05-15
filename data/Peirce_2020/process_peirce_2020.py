"""
metadata_schema_version = 1
source_key = "Peirce_2020"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Lawrence Vulis"
last_substantive_update = "2026-04-10"
source_dataset = '''
Peirce, Jana; Walker, Donald A. (Skip); Watson-Cook, Emily; Kanevskiy,
Mikhail; Bergstedt, Helena. 2022. Observations in ice-rich permafrost systems,
Prudhoe Bay Alaska, August 2020. Arctic Data Center.
doi:10.18739/A2542J96D
'''
processing_assumptions = [
  "Thaw depth values reported with a leading > are treated as observation-limit non-permafrost observations.",
  "Permafrost presence is inferred with data_utils.process_pf_observations using a 120 cm threshold.",
  "Point observations are merged to generated 1 m transect points built from separate transect start/end coordinates.",
  "obs_limit is fixed to 120 cm in the final output and method is set to tp.",
]
temporal_handling = [
  "Per-record sample dates are parsed directly from the measurement CSV.",
]
spatial_handling = [
  "Transect start/end coordinates are built in WGS84, projected to UTM zone 6N for point generation, and returned to WGS84 for export.",
]
manual_steps = []
known_limitations = [
  "The current implementation assumes the generated 1 m transect points and the Distanc from start (m) field line up exactly.",
  "site_id is a generated transect identifier because the source is organized around transects rather than named sites.",
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
from shapely.geometry import Point, LineString

source = 'Peirce_2020'
pf_data = pd.read_csv(_ROOT_DIR / "data" / source /"NNA_IRPS_PBO_2020_Water_Thaw_Depth.copy.csv".format(source))
transect_data = pd.read_csv(_ROOT_DIR / "data" / source /"NNA_IRPS_PBO_2020_Transect_Locations.csv".format(source))

pf_data[pf_data == -9999] = np.nan
pf_data[pf_data == '-9999'] = np.nan

# obs limit masks:
obs_limit_mask = pf_data['Thaw depth (cm)'].str.contains(">", na=False)
pf_data.loc[obs_limit_mask, 'Thaw depth (cm)'] = pf_data.loc[obs_limit_mask, 'Thaw depth (cm)'].str.replace(">", "")
pf_data['Thaw depth (cm)'] = pd.to_numeric(pf_data['Thaw depth (cm)'])

# obs vals:
pf_data['obs_lim_tempcol'] = 0
pf_data.loc[obs_limit_mask, 'obs_lim_tempcol']  = pf_data.loc[obs_limit_mask, 'Thaw depth (cm)'].copy()

# fix date column
pf_data['Sample date'] = pd.to_datetime(pf_data['Sample date'], format = "%Y%m%d")
pf_data.rename(columns={'Sample date': 'date',
                        'Study site' : 'site_id',
                        }, inplace=True)

pf_data = data_utils.process_pf_observations(pf_data.copy(),
                        alt_name='Thaw depth (cm)', 
                        pf_limit=120,
                        obs_limit_val=pf_data['obs_lim_tempcol'].copy(),
                        obs_limit_mask=obs_limit_mask)

# Generate line strings for each transect so they can be interpolated afterwards
# Transect locations: create linestring from each transect. then will create a transect every 1-m spacing
transect_data['start_pt_geom'] = [Point(xy) for xy in zip(transect_data['Longitude start'], transect_data['Latitude start'])]
# transect_data.apply(lambda x: x.iloc[0]['Longitude end'], axis=0)
transect_data['end_pt_geom'] = [Point(xy) for xy in zip(transect_data['Longitude end'], transect_data['Latitude end'])]
transect_data['line_geom'] = [LineString(xy) for xy in zip(transect_data['start_pt_geom'], transect_data['end_pt_geom'])]

line_gdf = gpd.GeoDataFrame(transect_data, geometry='line_geom', crs = "EPSG:4326")
line_gdf = line_gdf.to_crs("EPSG:32606")
line_gdf['len'] = round(line_gdf.length)

grouped_pf = pf_data.groupby('Transect')
# grouped_pf['Transect'].group_keys
meta_list = []
for trans_id, group in grouped_pf:
    print(trans_id)
    # Get the line coords for the specific transect
    indiv_line = line_gdf.loc[line_gdf['Transect ID']==trans_id]
    linesrs = data_utils.generate_transect_pts(indiv_line, 1)
    
    axel = group.merge(right=linesrs, left_on='Distanc from start (m)', right_index=True).copy()
    
    meta_list.append(axel)
# 
full_df = pd.concat(meta_list)

full_gdf = gpd.GeoDataFrame(full_df[['date', 'thaw_depth', 'pf_depth', "obs_limit", 'pf_observed', 'Transect', 'Distanc from start (m)', 'geometry']],
                            geometry='geometry',
                            crs='EPSG:32606')

full_gdf.rename(columns={'Transect': 'transect_name',
                         'Distanc from start (m)': 'transect_point'},
                inplace=True)

full_gdf = full_gdf.to_crs(epsg=4326)
full_gdf['lon'] = [g.coords.xy[0][0] for g in full_gdf.geometry.values] 
full_gdf['lat'] = [g.coords.xy[1][0] for g in full_gdf.geometry.values] 
df = pd.DataFrame(full_gdf.drop(columns='geometry'))
df['source'] = source
df['site_id'] = df['transect_name'].astype(str).radd(source + "_")
df['obs_limit'] = 120
df['method'] = 'tp'
data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
