"""
metadata_schema_version = 1
source_key = "Douglas_Koyukuk_2022"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Joel Rowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Douglas Koyukuk 2022 field observations compiled in
PermafrostMeasurementsDatesFinal.csv for the CUSP release workflow.
'''
processing_assumptions = [
  "All 2018 rows are dropped from the source table.",
  "Duplicate latitude/longitude locations are collapsed to unique sites and permafrost/thaw-depth values are blanked where repeated visits make the depth ambiguous.",
  "The source Permafrost Y/N field is mapped directly to pf_observed 1/0 and method is forced to tp.",
]
temporal_handling = [
  "Dates are reconstructed from the Year, Month, and Day columns.",
]
spatial_handling = [
  "Latitude and Longitude are used directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "site_id is currently left blank in the processed output.",
  "Depth_to_permafrost_cm is nulled at locations with repeated observations instead of attempting a multi-visit reconciliation.",
]
external_dependencies = []
notes = ""
"""
import pandas as pd
import numpy as np
import os
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Douglas_Koyukuk_2022'
df = pd.read_csv(_ROOT_DIR / "data" / source / "PermafrostMeasurementsDatesFinal.csv")

df = df[df['Year'] != 2018] #drop 2018 data

# find unique sampleing locations to drop duplicates and retain ALT measurements at locations with only one measurement, 
lat_lon= df.groupby(['Latitude', 'Longitude']).size().reset_index(name='count')
#df = df.drop(columns=df[lat_lon.count() > 1])

df_unique = df.drop_duplicates(subset=['Latitude', 'Longitude'])
df_unique = df_unique.merge(lat_lon, on=['Latitude', 'Longitude'])

#df_unique.loc[df_unique['Count'] > 1, 'Depth_to_permafrost_cm'] = np.nan
df = df_unique.copy()
df.loc[df['count'] > 1, 'Depth_to_permafrost_cm'] = np.nan
df.loc[df['count'] > 1, 'thaw_depth'] = np.nan
df['source'] = source
df['date'] = pd.to_datetime(df[['Year', 'Month', 'Day']])
df.rename(columns={'Permafrost':'pf_observed', 'Latitude':'lat', 'Longitude':'lon',
                   'Method':'method','Depth_to_permafrost_cm':'pf_depth'}, inplace=True)
df['method'] = 'tp'
df['obs_limit'] = 200
# Normalize Y/N flags using a pandas-safe assignment path.
df['pf_observed'] = df['pf_observed'].replace({'Y': 1, 'N': 0})
if df['pf_observed'].isna().any():
    raise ValueError("Unexpected values found in pf_observed for Douglas_Koyukuk_2022.")
df['pf_observed'] = df['pf_observed'].astype(int)
df['site_id'] = ''
df = df.drop(columns=['Year', 'Month', 'Day','Date_UTC-9', 'Horizontal_distance_m',
                      'Depth_cm', 'Horizontal_to_permafrost_cm', 'count'])

#df.drop(['ID', 'Method', 'Year', 'Horizontal_distance_m',
#       'Depth_to_permafrost_cm', 'Depth_cm', 'Horizontal_to_permafrost_cm', 'Relative_age', 'Geomorphic_unit', 'Count'], axis=1, inplace=True)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)


