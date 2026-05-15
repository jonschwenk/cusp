"""
metadata_schema_version = 1
source_key = "Bonaventure_Whati"
release_clearance = "approved"
permission_basis = "emailed_approval"
original_author = ""
last_substantive_update = "2026-04-10"
source_dataset = '''
Ground-truth point observations shared for the Whati study area by Phil
Bonaventure and approved for inclusion in CUSP.
'''
processing_assumptions = [
  "The source PF field is carried directly into pf_observed after coordinate/column normalization.",
  "pf_depth, thaw_depth, and obs_limit are left empty because the source provides presence/absence points rather than thaw-depth measurements.",
  "A single fixed date of 2019-08-15 is assigned to all rows.",
]
temporal_handling = [
  "The script assigns a single campaign date of 2019-08-15 to all observations.",
]
spatial_handling = [
  "X and Y are treated as longitude and latitude inputs for csvify_working without reprojection.",
]
manual_steps = []
known_limitations = [
  "The source contributes presence/absence observations only and does not provide thaw depth or observation-limit values.",
  "site_id remains unpopulated in the processed output.",
  "method is exported as unknown because the shared CSV does not include an observation-tool field.",
]
external_dependencies = []
notes = ""
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import os
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Bonaventure_Whati'
df = pd.read_csv(_ROOT_DIR / "data" / source / "groundTruthLocs.csv")
df[df==-9999] = np.nan
df = df.loc[:, ['X', 'Y', 'PF']]
df = data_utils.csvify_working(df.copy(), 
                                       lat_name="Y",
                                       lon_name="X",
                                       source=source,
                                       col_tokeep=["PF"]) 
df['date'] = "2019-08-15"
# add dummy columns on depth
df['pf_depth'] = np.nan
df['thaw_depth'] = np.nan
df['obs_limit'] = np.nan
# rename pf column
df.rename(columns={"PF": "pf_observed"},
                  inplace=True)
df['site_id'] = np.nan
df['method'] = 'unknown'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
