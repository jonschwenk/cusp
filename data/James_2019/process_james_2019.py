"""
metadata_schema_version = 1
source_key = "James_2019"
release_clearance = "approved"
permission_basis = "public_repository_terms"
last_substantive_update = "2026-04-10"
source_dataset = '''
James, S.R.; Minsley, B.J.; Waldrop, M.P.; McFarland, J.W.; Manies, K.L.;
Pastick, N.J. 2021. Permafrost characterization at the Alaska Peatland
Experiment (APEX): Geophysical and related field data collected from 2018-2020.
U.S. Geological Survey data release. https://doi.org/10.5066/P90M04ST
'''
processing_assumptions = [
  "Dates are parsed from YYYYMMDD strings and grouped by site and calendar year.",
  "pf_depth is assigned as the maximum thaw_depth observed at each site-year, but only if that maximum occurs on or after July 15 of that year.",
  "pf_observed is set to 0 when thaw_depth exceeds the 250 cm probe limit and 1 otherwise.",
  "obs_limit is fixed at 250 cm for all processed rows based on the frost-probe description in the source documentation.",
  "method is set to tp for all retained rows because the source documentation describes frost-probe measurements.",
]
temporal_handling = [
  "Original per-observation dates are preserved after parsing from the source CSV.",
  "The July 15 threshold is applied separately within each site-year group when deriving pf_depth.",
]
spatial_handling = [
  "Latitude and longitude are carried directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "pf_depth is a site-year derived field, so early-season observations inherit a later annual permafrost-depth estimate rather than a same-day measurement.",
  "The script does not preserve an explicit method field even though the source documentation identifies frost-probe measurements.",
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

source = 'James_2019'
df = pd.read_csv(_ROOT_DIR / "data" / source / "APEX_2018_2019_ThawDepth_Data.csv".format(source))

# --- PF_DEPTH CALCULATION (added by request) ---
df.rename(columns={'Date' : 'date',
                    'Lon_WGS84' : 'lon',
                    'Lat_WGS84' : 'lat',
                    'SiteID':'site_id',
                    'ThawDep_cm' : 'thaw_depth'},
                   inplace=True)

# print("Sample 'date' values and dtype after renaming:")
# print(df['date'].head(10))
# print(df['date'].dtype)


# Parse date and extract year
df['date_dt'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d')
df['year'] = df['date_dt'].dt.year

df['july_15'] = pd.to_datetime(df['year'].astype(str) + '-07-15')

def get_pf_depth(group):
    """
    For a (site, year) group:
    - Find the maximum thaw_depth value.
    - If that maximum occurs on/after July 15 of that year, return that max.
    - Otherwise return NaN.

    Returns a scalar suitable for .groupby(...).apply(get_pf_depth).
    """

    thaw_col = "thaw_depth"  # change if your column name differs

    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(group["date"]):
        group = group.copy()
        group["date"] = pd.to_datetime(group["date"], errors="coerce")

    # If no valid depths, bail
    if thaw_col not in group.columns or not group[thaw_col].notna().any():
        return np.nan

    # Max thaw depth for the group
    max_val = group[thaw_col].max(skipna=True)

    # Rows where the max occurs
    is_max = group[thaw_col] == max_val

    # Determine the year for the cutoff (use the date year from the group)
    # If your DataFrame already has a 'year' column aligned with the group, you could also use that.
    # Using the first non-null year from the 'date' is robust.
    year_vals = group["date"].dt.year.dropna().astype(int)
    if year_vals.empty:
        return np.nan
    year = int(year_vals.iloc[0])

    cutoff = pd.Timestamp(year=year, month=7, day=15)

    # If any occurrence of the max is on/after July 15, return max; else NaN
    if (group.loc[is_max, "date_dt"] >= cutoff).any():
        return float(max_val)
    return np.nan

pf_depths = (
    df.groupby(['site_id', 'year'])
      .apply(get_pf_depth)             # returns a scalar per group
      .rename('pf_depth')              # <-- name the Series
      .reset_index()                   # <-- turn into a 2-col DataFrame
)

df = df.merge(pf_depths, on=['site_id', 'year'], how='left')

df.drop(columns=['date_dt', 'july_15'], inplace=True)
# --- END PF_DEPTH CALCULATION ---


# Take the maximum observed pf depth as the observation limit
obs_limit =250
df['pf_observed'] = 1
df.loc[df['thaw_depth'] > obs_limit, 'pf_observed'] = 0
df['obs_limit'] = obs_limit
df['method'] = 'tp'



df['date'] = df['date'].astype(str)
df['date'] = [d[0:4] + '-' + d[4:6] + '-' + d[6:] for d in df['date']]

df['source'] = source


df.drop(columns=['X_UTMz6', 'Y_UTMz6', 'Altitude_m', 'Adjacency', 'FID', 'year'], inplace=True)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
