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
  "Rows with site_id = polysample are retained under the project team's decision to include visually interpreted permafrost presence/absence observations when their basis is explicitly flagged.",
  "The 314 polysample rows are representative points randomly sampled from team-created permafrost and non-permafrost polygons at 100 m minimum within-class and global spacing; they are not instrument measurements made at the sampled coordinates and are not machine-learning model predictions.",
  "Polysample rows retain blank pf_depth, thaw_depth, and obs_limit values because no point-specific measurement depth or observation limit supports them.",
  "The source pf_obs Y/N flags are mapped directly to pf_observed 1/0.",
  "For direct field rows, the source depth_obs field is carried into obs_limit where reported.",
  "For direct field rows lacking depth_obs, 96 cm is assigned as a conservative source-specific observation limit: it is the maximum observed permafrost depth among the direct field rows and is below the approximately 100 cm general field limit described in the local metadata.",
  "For direct permafrost-present rows, the source pf_depth column is interpreted as both pf_depth and thaw_depth.",
  "method is set to tp for direct rows where depth_obs is reported and unknown for rows whose exact field method is not recoverable row by row, including visual polygon samples.",
]
temporal_handling = [
  "A single campaign-average date of 2018-07-08 is assigned to every row because the source table does not provide per-observation dates.",
]
spatial_handling = [
  "Coordinates are read directly from the source CSV without reprojection.",
  "Direct-row coordinates represent field observations; polysample coordinates are randomly sampled representative locations within interpreted polygons, with 100 m minimum spacing documented in koyukuk_readme.txt.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all rows share the same campaign-average date.",
  "The 96 cm observation limit is a conservative source-level inference rather than a row-specific measured limit for 24 observations.",
  "The 314 visually interpreted polygon samples do not have point-specific measurement depths or observation limits and should be excluded from analyses requiring instrument-observed or depth-bounded records by filtering quality flag VI.",
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

visual_mask = (
    df['site_id'].astype('string').str.strip().eq('polysample').fillna(False)
)
if int(visual_mask.sum()) != 314:
    raise ValueError(
        "Expected 314 polygon-sampled Koyukuk rows; source contents may have changed."
    )

source_obs_limit = pd.to_numeric(df['depth_obs'], errors='coerce')
source_pf_depth = pd.to_numeric(df['pf_depth'], errors='coerce')
df['source'] = source
df['date'] = '2018-07-08'
df.rename(columns={'pf_obs':'pf_observed',
                   'depth_obs':'obs_limit', 'pf_depth':'thaw_depth'}, inplace=True)
df['pf_observed'] = (
    df['pf_observed'].astype('string').str.strip().map({'Y': 1, 'N': 0})
)
if df['pf_observed'].isna().any():
    raise ValueError("Unexpected values found in pf_observed for Koyukuk_2018.")
df['pf_observed'] = df['pf_observed'].astype(int)
df['thaw_depth'] = source_pf_depth.where(
    df['pf_observed'].eq(1) & ~visual_mask
)
df['pf_depth'] = df['thaw_depth']
df.loc[df['pf_observed'].eq(0), 'thaw_depth'] = np.nan

direct_mask = ~visual_mask
missing_direct_limit = direct_mask & source_obs_limit.isna()
df['obs_limit'] = source_obs_limit
df.loc[missing_direct_limit, 'obs_limit'] = 96.0
df.loc[visual_mask, 'obs_limit'] = np.nan
df['method'] = np.where(direct_mask & source_obs_limit.notna(), 'tp', 'unknown')

df['koyukuk_observation_basis'] = np.where(
    visual_mask,
    'visual_polygon_sample',
    'direct_field_observation',
)
df['koyukuk_polygon_sample_spacing_m'] = np.where(visual_mask, 100.0, np.nan)

df['quality_flag_date_assigned'] = True
df['quality_flag_obs_limit_assumed'] = missing_direct_limit
df['quality_flag_visual_interpretation'] = visual_mask
df['quality_flag_upper_bound_presence'] = (
    df['pf_observed'].eq(1) & df['thaw_depth'].isna()
)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

