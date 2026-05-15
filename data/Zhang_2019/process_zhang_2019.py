"""
metadata_schema_version = 1
source_key = "Zhang_2019"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "Lawrence Vulis"
last_substantive_update = "2026-04-11"
source_dataset = '''
Zhang, Y.; Touzi, R.; Feng, W.; Hong, G.; Lantz, T.C.; Kokelj, S.V. 2021.
Landscape-scale variations in near-surface soil temperature and active-layer
thickness: Implications for high-resolution permafrost mapping. Permafrost and
Periglacial Processes 32(4): 627-640. https://doi.org/10.1002/ppp.2104
'''
processing_assumptions = [
  "The workbook is split into separate 2016 and 2017 observation tables and then concatenated.",
  "thaw_depth and organic thickness values reported with a leading > are cleaned to numeric values before processing.",
  "Near-surface permafrost is inferred with data_utils.process_pf_observations using a 101 cm threshold and fixed obs_limit value of 100 cm.",
  "Longitude values are negated after import to convert west-longitude convention into signed decimal degrees.",
  "pf_depth is explicitly reset to missing in the final processed output even though process_pf_observations initially derives it.",
  "method is set to tp for all retained rows because the source reports active-layer probe measurements.",
]
temporal_handling = [
  "Per-observation dates are preserved from the workbook after conversion to date strings.",
]
spatial_handling = [
  "Coordinates are read directly from the workbook and adjusted only by sign-flipping longitude.",
]
manual_steps = []
known_limitations = [
  "The final script output discards the intermediate pf_depth values derived during processing and leaves pf_depth missing.",
  "The 101 cm permafrost threshold and 100 cm obs_limit value are CUSP processing assumptions.",
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

source = 'Zhang_2019'
df = pd.read_excel(_ROOT_DIR / "data" / source /"zhang_observations.xlsx")
df[df == -9999] = np.nan
df[df == '-'] = np.nan

df_2016 = df[['Site_ID', 'Ob_Date2016', 'Latitude(N)', 'Longitude(W)', 'OLT(cm)', 'ALT2016(cm)' ]]
df_2016.rename(columns={'OLT(cm)': 'org_thick',
                   'Site_ID': 'site_id',
                   'Latitude(N)' : 'lat',
                   'Longitude(W)' : 'lon',
                   'Ob_Date2016': 'date',
                   'ALT2016(cm)': 'thaw_depth'}, inplace=True)
df_2017 = df[['Site_ID', 'Ob_Date2017', 'Latitude(N)', 'Longitude(W)', 'OLT(cm)', 'ALT2017(cm)' ]]
df_2017.rename(columns={'OLT(cm)': 'org_thick',
                   'Site_ID': 'site_id',
                   'Latitude(N)' : 'lat',
                   'Longitude(W)' : 'lon',
                   'Ob_Date2017': 'date',
                   'ALT2017(cm)': 'thaw_depth'}, inplace=True)

comb_df = pd.concat([df_2016, df_2017], ignore_index=True)
comb_df.dropna(subset=['thaw_depth'], inplace=True)

# get a date column
comb_df['date'] = comb_df['date'].dt.date.astype(str).copy()

# take care of obs limit, create a new vector which is the obs limit
obs_limit_mask = comb_df['thaw_depth'].str.contains(">", na=False)
org_obs_limit_mask = comb_df['org_thick'].str.contains(">", na=False)
comb_df.loc[obs_limit_mask, 'thaw_depth'] = comb_df.loc[obs_limit_mask, 'thaw_depth'].str.replace(">", "")
comb_df['thaw_depth'] = pd.to_numeric(comb_df['thaw_depth'])
comb_df.loc[org_obs_limit_mask, 'org_thick'] = comb_df.loc[org_obs_limit_mask, 'org_thick'].str.replace(">", "")
comb_df['org_thick'] = pd.to_numeric(comb_df['org_thick'])


# add pf_depth etc. columns
comb_df = data_utils.process_pf_observations(comb_df.copy(),
                        alt_name='thaw_depth', 
                        pf_limit=101,
                        obs_limit_val=100,
                        obs_limit_mask=obs_limit_mask)


comb_df['lon'] = -comb_df['lon']

full_df = data_utils.csvify_working(comb_df.copy(), 
                                     source=source,
                                     lat_name="lat",
                                     lon_name="lon",
                                     col_tokeep=["thaw_depth", "pf_observed", 'pf_depth', "date", 'org_thick', 'obs_limit', 'site_id']) 

data_utils.check_columns(full_df)
full_df['pf_depth'] = np.nan
full_df['method'] = 'tp'

# export                            
full_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
