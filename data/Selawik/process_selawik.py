"""
metadata_schema_version = 1
source_key = "Selawik"
release_clearance = "approved"
permission_basis = "self_generated"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Rowland, Joel. 2022. Selawik National Wildlife Refuge observations, unpublished.
'''
processing_assumptions = [
  "The source pf field is mapped directly to pf_observed; depth is exact thaw_depth for presence and source-reported supporting depth for absence.",
  "pf_depth is set equal to thaw_depth where pf_observed = 1.",
  "obs_limit is fixed at 120 cm for absence rows and method is set to tp.",
  "Rows with missing pf_observed are dropped before export.",
]
temporal_handling = [
  "All observations are assigned the representative campaign date 2022-09-15.",
]
spatial_handling = [
  "Coordinates are used as provided in the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all rows share one campaign date.",
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

source = 'Selawik'
df = pd.read_csv(_ROOT_DIR / "data" / source /"PF_points.csv".format(source))
df.rename(columns={"pf": "pf_observed",
                   "temp": "temperature",
                   "depth": "thaw_depth",
                   'site':'site_id'},
                  inplace=True)

# df['thaw_depth'] = df['thaw_depth'].str.replace(">", "")
# df["thaw_depth"] = pd.to_numeric(df["thaw_depth"])
#df['thaw_depth'] = df['thaw_depth'].astype('Int64')
# create pf_depth column. This column is np.nan if pf wasn't observed (already determined)
df['selawik_reported_depth_cm'] = df['thaw_depth']
absence = df['pf_observed'].eq(0)
df['pf_depth'] = df['thaw_depth'].where(~absence)
df['obs_limit'] = np.where(absence, 120.0, np.nan)
df.loc[absence, 'thaw_depth'] = np.nan
# df.loc[df['site'].str.contains("romanovsky"), 'obs_limit'] = 100
df.drop(columns=['X', 'Y'], inplace=True)

df['date'] = '2022-09-15'
df['source'] = source
df = df[~pd.isna(df['pf_observed'])]
df['pf_observed'] = df['pf_observed'].astype(int)
df['method'] = 'tp'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
