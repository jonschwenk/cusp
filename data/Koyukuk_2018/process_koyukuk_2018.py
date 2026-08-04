"""
metadata_schema_version = 1
source_key = "Koyukuk_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Schwenk J.; Piliouras A.; Rowland J. (2023). Observations and Machine-Learned
Models of Near-Surface Permafrost along the Koyukuk River, Alaska, USA.
ESS-DIVE repository. doi:10.15485/1922517
'''
processing_assumptions = [
  "Rows with site_id = polysample are excluded because they are random samples of mapped permafrost/non-permafrost polygons, not point field observations.",
  "The source pf_obs Y/N flags are mapped directly to pf_observed 1/0.",
  "The source depth_obs field is carried into obs_limit where reported.",
  "For direct observations lacking depth_obs, 96 cm is assigned as a conservative source-specific observation limit: it is the maximum observed permafrost depth among the direct field rows and is below the approximately 100 cm general field limit described in the local metadata.",
  "The source pf_depth column is interpreted as both pf_depth and thaw_depth for permafrost-present rows.",
  "method is set to tp where depth_obs is reported and unknown for bank/core observations whose exact field method is not recoverable row by row.",
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
  "The 96 cm observation limit is a conservative source-level inference rather than a row-specific measured limit for 24 observations.",
]
external_dependencies = []
notes = ""
"""
import pandas as pd
import numpy as np
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Koyukuk_2018'
df = pd.read_csv(_ROOT_DIR / "data" / source / "koyukuk_field_obs_2018.csv")

derived_mask = (
    df['site_id'].astype('string').str.strip().eq('polysample').fillna(False)
)
if int(derived_mask.sum()) != 314:
    raise ValueError(
        "Expected 314 polygon-sampled Koyukuk rows; source contents may have changed."
    )
df = df.loc[~derived_mask].copy()

source_obs_limit = pd.to_numeric(df['depth_obs'], errors='coerce')
df['source'] = source
df['date'] = '2018-07-08'
df.rename(columns={'pf_obs':'pf_observed',
                   'depth_obs':'obs_limit', 'pf_depth':'thaw_depth'}, inplace=True)
df['pf_observed'] = df['pf_observed'].replace({'Y': 1, 'N': 0})
if df['pf_observed'].isna().any():
    raise ValueError("Unexpected values found in pf_observed for Koyukuk_2018.")
df['pf_observed'] = df['pf_observed'].astype(int)
df['thaw_depth'] = pd.to_numeric(df['thaw_depth'], errors='coerce')
df['pf_depth'] = df['thaw_depth'].where(df['pf_observed'].eq(1))
df.loc[df['pf_observed'].eq(0), 'thaw_depth'] = np.nan

missing_limit = source_obs_limit.isna()
df.loc[missing_limit, 'obs_limit'] = 96.0
df['method'] = np.where(source_obs_limit.notna(), 'tp', 'unknown')

df['quality_flag_date_assigned'] = True
df['quality_flag_obs_limit_assumed'] = missing_limit
df['quality_flag_upper_bound_presence'] = (
    df['pf_observed'].eq(1) & df['thaw_depth'].isna()
)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

