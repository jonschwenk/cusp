"""
metadata_schema_version = 1
source_key = "Holloway_2019"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "Lawrence Vulis"
last_substantive_update = "2026-04-10"
source_dataset = '''
Holloway, Jean E.; Lewkowicz, Antoni G. 2020. Half a century of discontinuous
permafrost persistence and degradation in western Canada. Permafrost and
Periglacial Processes 31(1): 85-96.
'''
processing_assumptions = [
  "The source workbook is split into 1962 and 2018 observation blocks that are processed separately and concatenated at the end.",
  "For 1962 observations, ALT_cm_1962 is treated as pf_depth and copied to thaw_depth where pf_observed = 1.",
  "For 2018 observations, ALT_cm_2018 is treated as pf_depth for permafrost-present records, with trailing * markers removed before numeric conversion.",
  "Question marks and placeholder hyphens are treated as missing values.",
  "method is set to tp for both survey years because the source reports active-layer probe observations.",
]
temporal_handling = [
  "The 1962 observations are assigned the representative date 1962-08-15.",
  "The 2018 observations are assigned the representative date 2018-08-15.",
]
spatial_handling = [
  "Coordinates are read directly from the source workbook without reprojection.",
]
manual_steps = [
  "The source observations were transcribed from a Word-document source into holloway_data.xlsx before this script runs.",
]
known_limitations = [
  "Some 2018 permafrost-depth values were modeled in the source using a thermal-gradient approach; the source * marker is stripped during numeric conversion and is not preserved in the processed output.",
  "Observation dates are approximate because both survey years are represented by a single campaign date.",
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

source = 'Holloway_2019'
df = pd.read_excel(_ROOT_DIR / "data" / source /"holloway_data.xlsx")
df[df == '-'] = np.nan

#  identify which observations are at observation limit (contain a >)
org_obs_limit_1962_mask = df['olt_cm_1962'].str.contains(">", na=False)
org_obs_limit_2018_mask = df['olt_cm_2018'].str.contains(">", na=False)


# Mark the > with observation limits on the OLT. Maybe not useful
df.loc[org_obs_limit_1962_mask, 'olt_cm_1962'] = df.loc[org_obs_limit_1962_mask, 'olt_cm_1962'].astype(str).str.replace(">", "")
df['olt_cm_1962'] = pd.to_numeric(df['olt_cm_1962'])

df.loc[org_obs_limit_2018_mask, 'olt_cm_2018'] = df.loc[org_obs_limit_2018_mask, 'olt_cm_2018'].astype(str).str.replace(">", "")
df['olt_cm_2018'] = pd.to_numeric(df['olt_cm_2018'])

# convert "Unsure" to np.nan
df['pf_observed_2018'] = df['pf_observed_2018'].replace({'Probable': 'Yes', 'Yes': 1, 'No': 0})
df['pf_observed_1962'] = df['pf_observed_1962'].replace({'Yes': 1, 'No': 0})

# Lawrence split these by year; I'll keep that and re-join at the end
full_1962_gdf = data_utils.csvify_working(df,
                                     lon_name='Long',
                                     lat_name='Lat',
                                     source=source,
                                     col_tokeep=['site_number', 'pf_observed_1962', 'ALT_cm_1962', 'olt_cm_1962', 'Canopy and Surface 1962', 'Burn Year', 'Relief', 'Soil Type'])

# rename columns
full_1962_gdf.rename(columns={'pf_observed_1962': 'pf_observed',
                              'ALT_cm_1962': 'pf_depth',
                              'olt_cm_1962': 'org_thick',
                              'Canopy and Surface 1962' : 'Canopy and Surface'},
                     inplace=True)
full_1962_gdf['pf_observed'] = pd.to_numeric(full_1962_gdf['pf_observed'], errors='coerce')

# Set date
full_1962_gdf['date'] = '1962-08-15'
# Ensure depth values are numeric before using them to populate thaw depth.
full_1962_gdf['pf_depth'] = pd.to_numeric(full_1962_gdf['pf_depth'], errors='coerce')
# get an obs depth column
full_1962_gdf['thaw_depth'] = np.nan
full_1962_gdf.loc[full_1962_gdf['pf_observed']==1, 'thaw_depth'] = full_1962_gdf.loc[full_1962_gdf['pf_observed']==1, 'pf_depth']
full_1962_gdf['pf_observed'] = full_1962_gdf['pf_observed'].astype(int)
full_1962_gdf['obs_limit'] = np.nan
full_1962_gdf['method'] = 'tp'
full_1962_gdf.rename(columns={'site_number' : 'site_id'}, inplace=True)
data_utils.check_columns(full_1962_gdf)

#  2018 section
full_2018_gdf = data_utils.csvify_working(df,
                                     lon_name='Long',
                                     lat_name='Lat',
                                     source=source,
                                     col_tokeep=['site_number', 'pf_observed_2018', 'ALT_cm_2018', 'olt_cm_2018', 'Canopy and Surface 2018', 'Burn Year', 'Relief', 'Soil Type'])


full_2018_gdf.rename(columns={'pf_observed_2018': 'pf_observed',
                              'ALT_cm_2018': 'pf_depth',
                              'olt_cm_2018': 'org_thick',
                              'Canopy and Surface 2018' : 'Canopy and Surface'},
                     inplace=True)
full_2018_gdf['pf_observed'] = full_2018_gdf['pf_observed'].replace({'Yes': 1, 'No': 0})
full_2018_gdf['pf_observed'] = pd.to_numeric(full_2018_gdf['pf_observed'], errors='coerce')

# set date
full_2018_gdf['date'] = '2018-08-15'

# modify pf_depth
full_2018_gdf.loc[full_2018_gdf['pf_observed']==0, 'pf_depth'] = np.nan

#  mark inferred pieces w/o the *
pf_depth_inferred_mask = full_2018_gdf['pf_depth'].astype(str).str.contains(r"\*", na=False)
full_2018_gdf.loc[pf_depth_inferred_mask, 'pf_depth'] = full_2018_gdf.loc[pf_depth_inferred_mask, 'pf_depth'].astype(str).str.replace("*", "", regex=False)
full_2018_gdf['pf_depth'] = pd.to_numeric(full_2018_gdf['pf_depth'])

# get thaw_depth column out of the pf_depth column
full_2018_gdf['thaw_depth'] = np.nan
full_2018_gdf.loc[full_2018_gdf['pf_observed']==1, 'thaw_depth'] = full_2018_gdf.loc[full_2018_gdf['pf_observed']==1, 'pf_depth']
full_2018_gdf['pf_observed'] = full_2018_gdf['pf_observed'].astype('Int64')
full_2018_gdf['obs_limit'] = np.nan
full_2018_gdf['method'] = 'tp'
full_2018_gdf.rename(columns={'site_number' : 'site_id',
                              }, inplace=True)

data_utils.check_columns(full_2018_gdf)

# Merge
df = pd.concat([full_2018_gdf, full_1962_gdf])
df = df[~pd.isna(df['pf_observed'])]
df['pf_observed'] = df['pf_observed'].astype(int)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
