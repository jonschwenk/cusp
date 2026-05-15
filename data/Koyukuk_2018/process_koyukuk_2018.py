"""
metadata_schema_version = 1
source_key = "Koyukuk_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Jon Schwenk"
last_substantive_update = "2026-04-10"
source_dataset = '''
Schwenk J.; Piliouras A.; Rowland J. (2023). Observations and Machine-Learned
Models of Near-Surface Permafrost along the Koyukuk River, Alaska, USA.
ESS-DIVE repository. doi:10.15485/1922517
'''
processing_assumptions = [
  "The source pf_obs Y/N flags are mapped directly to pf_observed 1/0.",
  "The source depth_obs field is carried into obs_limit without additional reinterpretation.",
  "The source pf_depth column is interpreted as thaw_depth in the processed output.",
  "method is set to tp for all rows based on the field thaw-probe workflow described in the source dataset.",
]
temporal_handling = [
  "A single campaign-average date of 2018-07-08 is assigned to every row because the source table does not provide per-observation dates.",
]
spatial_handling = [
  "Coordinates are read directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all rows share the same campaign-average date.",
]
external_dependencies = []
notes = ""
"""
import pandas as pd
import numpy as np
import os
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Koyukuk_2018'
#df = pd.read_csv(r"data\{}\koyukuk_field_obs_2018.csv".format(source))
df = pd.read_csv(_ROOT_DIR / "data" / source / "koyukuk_field_obs_2018.csv")

df['source'] = source
df['date'] = '2018-07-08' # based on average field campaign date
df.rename(columns={'pf_obs':'pf_observed',
                   'depth_obs':'obs_limit', 'pf_depth':'thaw_depth'}, inplace=True)
# Normalize Y/N flags using a pandas-safe assignment path.
df['pf_observed'] = df['pf_observed'].replace({'Y': 1, 'N': 0})
if df['pf_observed'].isna().any():
    raise ValueError("Unexpected values found in pf_observed for Koyukuk_2018.")
df['pf_observed'] = df['pf_observed'].astype(int)
df['pf_depth'] = np.nan
df['method'] = 'tp'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

