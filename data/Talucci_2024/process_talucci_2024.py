"""
metadata_schema_version = 1
source_key = "Talucci_2024"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-21"
source_dataset = '''
Talucci, Anna; Loranty, Michael; Holloway, Jean; Rogers, Brendan; Alexander,
Heather; Baillargeon, Natalie; Baltzer, Jennifer; Berner, Logan; and others.
2024. FireALT: active layer thickness estimates for paired burned and unburned
sites in northern high latitudes. Arctic Data Center.
doi:10.18739/A2RN3092P
'''
processing_assumptions = [
  "Natali Bonanza Creek rows already represented by the direct ViPER_2018 source are removed before FireALT aggregation: BCB 2015 and BCU 2015, 2017, and 2018.",
  "Where both msrType = thaw and msrType = active exist for the same grouped site, only the active records are retained.",
  "Repeated measurements at the same lat/lon, burn status, and time-since-fire grouping are summarized using mean estimated thaw depth rather than mean measured thaw depth.",
  "pf_observed is fixed to 1 and pf_depth is set equal to the estimated thaw depth used for aggregation.",
  "Single-record locations retain measured_thaw_depth and measured_date alongside the aggregated estimated-depth output.",
]
temporal_handling = [
  "Aggregated dates are reconstructed from year and mean estimated day-of-year.",
  "For single-record locations, measured_date is reconstructed separately from msrDoy.",
]
spatial_handling = [
  "Latitude and longitude are used directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "The main processed thaw_depth field is based on estimated rather than measured depth for multi-observation groups.",
  "Unburned control rows have no numeric time-since-fire value, so timeSinceFire is blank after ingestion.",
  "method is exported as unknown because the source combines modeled and measured information without one clean field that maps to the CUSP method vocabulary.",
  "CUSP prefers the direct ViPER_2018 thaw-probe observations over FireALT's synthesized Natali Bonanza Creek rows where the two overlap.",
]
external_dependencies = []
notes = ""
"""




import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils
from datetime import datetime, timedelta
source = "Talucci_2024"



# Load and clean the dataset
df = pd.read_csv(_ROOT_DIR / "data" / source / "FireAltEstimatedRawData.csv")
df.replace(to_replace=[-9999, "u"], value=np.nan, inplace=True)

# Convert types
df['estDepth'] = pd.to_numeric(df['estDepth'], errors='coerce')
df['orgDepth'] = pd.to_numeric(df['orgDepth'], errors='coerce')
df['estDoy'] = pd.to_numeric(df['estDoy'], errors='coerce')
df['year'] = pd.to_numeric(df['year'], errors='coerce')
df['msrDepth'] = pd.to_numeric(df['msrDepth'], errors='coerce')
df['msrDoy'] = pd.to_numeric(df['msrDoy'], errors='coerce')

# Remove FireALT rows that are now represented by the direct ViPER_2018 ingest.
natali_bonanza_viper_overlap = (
    (df["submitNm"].astype(str).str.lower().eq("natali") | df["lastNm"].astype(str).str.lower().eq("natali"))
    & (
        (df["siteId"].eq("BCB") & df["year"].eq(2015))
        | (df["siteId"].eq("BCU") & df["year"].isin([2015, 2017, 2018]))
    )
)
df = df.loc[~natali_bonanza_viper_overlap].copy()

# Identify and keep only 'active' if both 'thaw' and 'active' exist
def filter_thaw_if_active(group):
    if set(group['msrType'].unique()) == {'thaw', 'active'}:
        return group[group['msrType'] == 'active']
    return group

group_cols = ['lat', 'lon', 'distur', 'tsf']
# Avoid groupby.apply here so the grouping columns stay attached under newer pandas.
grouped_types = df.groupby(group_cols, dropna=False)['msrType']
has_thaw = grouped_types.transform(lambda s: s.eq('thaw').any())
has_active = grouped_types.transform(lambda s: s.eq('active').any())
keep_active_only = has_thaw & has_active
df_filtered = df.loc[~keep_active_only | df['msrType'].eq('active')].copy()

# Count rows per lat-lon
location_counts = df_filtered.groupby(['lat', 'lon']).size().reset_index(name='count')
df_filtered = df_filtered.merge(location_counts, on=['lat', 'lon'])

# Aggregation
agg_fields = {
    'estDepth': ['mean', 'std'],
    'estDoy': 'mean',
    'orgDepth': 'mean',
    'siteId': 'first',
    'year': 'first',
    'count': 'first'
}
df_avg = df_filtered.groupby(group_cols, dropna=False).agg(agg_fields).reset_index()
df_avg.columns = ['lat', 'lon', 'burn_unburn', 'timeSinceFire', 'estDepth', 'pf_depth_std', 'estDoy', 'orgDepth', 'site_id', 'year', 'record_count']

# Convert estDoy to date
def convert_day_to_date(year, doy):
    try:
        base_date = datetime(year=int(year), month=1, day=1)
        final_date = base_date + timedelta(days=int(round(doy)) - 1)
        return final_date.strftime("%m-%d")
    except:
        return np.nan

df_avg['month_day'] = df_avg.apply(lambda row: convert_day_to_date(row['year'], row['estDoy']), axis=1)

# Populate output fields
df_avg['source'] = source
df_avg['pf_observed'] = 1
df_avg['pf_depth'] = df_avg['estDepth'].round(2)
df_avg['pf_depth_std'] = df_avg['pf_depth_std'].round(2)
df_avg['thaw_depth'] = df_avg['estDepth'].round(2)
df_avg['obs_limit'] = np.nan
df_avg['method'] = 'unknown'
df_avg['org_thick'] = df_avg['orgDepth']
df_avg['date'] = df_avg['year'].astype(str) + "-" + df_avg['month_day']
df_avg['n_measurements'] = df_avg['record_count']

# Basic output table
output_df = df_avg[[
    'site_id', 'source', 'date', 'lat', 'lon', 'pf_observed',
    'pf_depth', 'pf_depth_std', 'n_measurements', 'thaw_depth',
    'obs_limit', 'method', 'timeSinceFire', 'org_thick', 'burn_unburn',
]]

# Attach measured values for single-record sites
single_obs_keys = df_avg[df_avg['record_count'] == 1][['lat', 'lon']]
df_single_obs = df_filtered.merge(single_obs_keys, on=['lat', 'lon'])
df_single_obs['measured_date'] = df_single_obs.apply(
    lambda row: convert_day_to_date(row['year'], row['msrDoy']), axis=1
)
df_single_obs['measured_date'] = df_single_obs.apply(
    lambda row: f"{int(row['year'])}-{row['measured_date']}" if pd.notnull(row['measured_date']) else np.nan, axis=1
)
df_single_obs = df_single_obs[['lat', 'lon', 'msrDepth', 'measured_date']]
df_single_obs = df_single_obs.rename(columns={'msrDepth': 'measured_thaw_depth'})

# Merge and finalize
output_df = output_df.merge(df_single_obs, on=['lat', 'lon'], how='left')

# Save to CSV
data_utils.check_columns(output_df)

output_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
