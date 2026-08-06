"""
metadata_schema_version = 1
source_key = "Minsley_2021"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Minsley, B.J.; James, S.R.; Pastick, N.J. 2022. Alaska permafrost
characterization: Geophysical and related field data collected in 2021.
U.S. Geological Survey data release. https://doi.org/10.5066/P9XEMDE1
'''
processing_assumptions = [
  "ALT == 999 is treated as an observation-limit code and remapped to 132 cm before permafrost presence is inferred.",
  "Rows are retained only when ALT establishes a permafrost observation; OLT-only rows are not sufficient.",
  "Ordinary numeric ALT is treated as permafrost presence, while ALT == 999 is retained as lower-bound absence with obs_limit = 132 cm.",
  "The final processed table keeps thaw_depth, pf_observed, pf_depth, org_thick, obs_limit, date, and site_id derived through csvify_working().",
  "method is set to tp for all retained rows because this script only exports the point-soil thaw-probe observations from the release.",
]
temporal_handling = [
  "Dates are parsed from YYYYMMDD strings and preserved per observation.",
]
spatial_handling = [
  "Coordinates are read directly from the source CSV in WGS84 decimal degrees.",
]
manual_steps = []
known_limitations = [
  "The 132 cm interpretation of source sentinel 999 is a processor assumption and is quality-flagged.",
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

source = 'Minsley_2021'
df = pd.read_csv(_ROOT_DIR / "data" / source /"AK_2021_SiteLocations_Characteristics_WGS84.csv".format(source))

df[df == -9999] = np.nan
df[df == '-9999'] = np.nan

# identify which observations are at observation limit (ALT==999)
obs_limit_mask = df['ALT']==999
df.loc[obs_limit_mask, 'ALT'] = 132

# subset data
has_probe_mask = ~np.isnan(df['ALT'])

subset_data = df.loc[has_probe_mask].copy()


# rename columns:
subset_data.rename(columns={'OLT': 'org_thick',
                            'Date': 'date',
                            'SiteID': 'site_id'},
                   inplace=True)
# fix date column formatting
subset_data['date'] = pd.to_datetime(subset_data['date'], format="%Y%m%d").astype(str).values

subset_data = data_utils.process_pf_observations(subset_data.copy(),
                        alt_name='ALT', 
                        obs_limit_val=132,
                        obs_limit_mask=obs_limit_mask)

subset_data['pf_observed'] = subset_data['pf_observed'].astype(int)
subset_data['quality_flag_obs_limit_assumed'] = subset_data['pf_observed'].eq(0)
subset_data['quality_flag_source_unit_or_code_recoded'] = subset_data['pf_observed'].eq(0)

df = data_utils.csvify_working(subset_data.copy(), 
                                source=source,
                                lat_name="Lat_WGS84",
                                lon_name="Lon_WGS84",
                                col_tokeep=["thaw_depth", "pf_observed", 'pf_depth', "date", 'org_thick', 'obs_limit', 'site_id', 'quality_flag_obs_limit_assumed', 'quality_flag_source_unit_or_code_recoded'])
df['method'] = 'tp'

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
