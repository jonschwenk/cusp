
"""
metadata_schema_version = 1
source_key = "Jorgenson_Kanevskiy_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland and ChatGPT"
last_substantive_update = "2026-04-11"
source_dataset = '''
Jorgenson, Mark; Kanevskiy, Mikhail. 2025. Alaska Permafrost Soils Inventory
and Thermokarst Monitoring Database 2024 Update. Arctic Data Center.
doi:10.18739/A27P8TG0G
'''
processing_assumptions = [
  "Soil stratigraphy rows are grouped by SiteIDFnl and effective year after parsing embedded year values out of SiteIDFnl where available.",
  "Site metadata are resolved by trying exact SiteID/year matches first, then composite IDs, then relaxed SiteID/SiteIDFld matches.",
  "pf_depth is inferred from the shallowest CryostratFnl horizon containing P or M, with an F-based fallback if no P/M horizon is present.",
  "thaw_depth is inferred from AL horizons above the permafrost horizon, and organic thickness is derived from O horizons above the first non-O horizon.",
  "method is fixed to aug_pit, and rows with unresolved/conflicting site metadata are dropped before export.",
]
temporal_handling = [
  "Dates are normalized from the site metadata table and carried through as site-level observation dates for each summarized record.",
]
spatial_handling = [
  "Latitude and longitude are attached by matching summarized soil records to the site metadata table; no reprojection is performed in the script.",
]
manual_steps = []
known_limitations = [
  "Relaxed site matching can fall back to non-year-specific metadata when exact year matches are unavailable.",
  "Rows with conflicting site metadata are dropped rather than resolved automatically.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np

import re
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Jorgenson_Kanevskiy_2025"


# Load data
soil_df = pd.read_csv(
    _ROOT_DIR / "data" / source / "tbl_Soil_Stratigraphy_2024.csv",
    encoding="latin1",
    low_memory=False,
)
site_df = pd.read_csv(_ROOT_DIR / "data" / source /"tbl_Site_2024.csv", encoding="latin1")

# Normalize Date to unambiguous ISO before it ever gets merged out
site_df["Date"] = site_df["Date"].astype(str).str.strip().replace({"": pd.NA, "nan": pd.NA})

dt = pd.to_datetime(site_df["Date"], format="%m/%d/%y %H:%M", errors="coerce")

# If some rows might be "m/d/yy" without time, try that too
mask = dt.isna() & site_df["Date"].notna()
dt.loc[mask] = pd.to_datetime(site_df.loc[mask, "Date"], format="%m/%d/%y", errors="coerce")

# write back as ISO date string
site_df["Date"] = dt.dt.strftime("%Y-%m-%d")

# Normalize site metadata for matching
site_df['SiteID_lower'] = site_df['SiteID'].astype(str).str.lower()
site_df['SiteIDFld_lower'] = site_df['SiteIDFld'].astype(str).str.lower()
site_df['Year_int'] = pd.to_numeric(site_df['Year'], errors='coerce')

# Extract site and year from SiteIDFnl if embedded
def extract_siteid_and_year(s):
    match = re.match(r"^(.*?)-(\d{4})$", str(s).strip())
    if match:
        return pd.Series([match.group(1), int(match.group(2))])
    else:
        return pd.Series([s, np.nan])

soil_df[['parsed_SiteIDFnl', 'parsed_Year']] = soil_df['SiteIDFnl'].apply(extract_siteid_and_year)
soil_df['parsed_SiteIDFnl_lower'] = soil_df['parsed_SiteIDFnl'].astype(str).str.lower()
soil_df['effective_Year'] = soil_df['parsed_Year']
soil_df.loc[soil_df['effective_Year'].isna(), 'effective_Year'] = soil_df['Year']

# Match metadata using SiteID, composite, SiteIDFld
def resolve_site_metadata(row):
    sid = row['parsed_SiteIDFnl_lower']
    yr = row['effective_Year']
    composite_id = f"{sid}-{int(yr)}" if not pd.isna(yr) else None
    year_disagreement = False
    matches = pd.DataFrame()

    if not pd.isna(yr):
        matches = site_df[(site_df['SiteID_lower'] == sid) & (site_df['Year_int'] == yr)]
        if matches.empty and composite_id:
            matches = site_df[site_df['SiteID'].astype(str).str.lower() == composite_id]
            year_disagreement = True

    if matches.empty:
        matches = site_df[
            (site_df['SiteID_lower'] == sid) |
            (site_df['SiteIDFld_lower'] == sid)
        ]
        year_disagreement = True

    if matches.empty:
        return pd.Series([np.nan, np.nan, np.nan, np.nan, year_disagreement])

    def resolve(values):
        values = list(values)
        return values[0] if len(values) == 1 else "cnflt" if len(values) > 1 else np.nan

    return pd.Series([
        resolve(matches['SiteID'].dropna()),
        resolve(matches['LatWGS84'].dropna()),
        resolve(matches['LonWGS84'].dropna()),
        resolve(matches['Date'].dropna()),
        year_disagreement
    ])

soil_df[['site_id', 'lat', 'lon', 'date', 'year_disagreement']] = soil_df.apply(resolve_site_metadata, axis=1)

# Convert numeric fields
soil_df['DepthTop_cm'] = pd.to_numeric(soil_df['DepthTop_cm'], errors='coerce')
soil_df['DepthBot_cm'] = pd.to_numeric(soil_df['DepthBot_cm'], errors='coerce')

# Summarize site by year with relaxed 'all U' logic
def summarize(group):
    # Newer pandas/groupby.apply paths may exclude grouping columns from `group`.
    group_name = getattr(group, "name", (pd.NA, pd.NA))
    if isinstance(group_name, tuple) and len(group_name) == 2:
        siteidfnl, year = group_name
    else:
        siteidfnl = group['SiteIDFnl'].iloc[0] if 'SiteIDFnl' in group else pd.NA
        year = group['effective_Year'].iloc[0] if 'effective_Year' in group else pd.NA
    site_id = group['site_id'].iloc[0]
    lat = group['lat'].iloc[0]
    lon = group['lon'].iloc[0]
    date = group['date'].iloc[0]
    obs_limit = group['DepthBot_cm'].max()
    if pd.notna(obs_limit) and obs_limit <= 0:
        obs_limit = np.nan
    method = "aug_pit"

    o_layers = group[group['HrznFnl'].astype(str).str.startswith("O", na=False)]
    non_o = group[group['HrznFnl'].astype(str).str.match("^[^O]", na=False)]
    org_thick = o_layers['DepthBot_cm'].max() if non_o.empty else         o_layers[o_layers['DepthTop_cm'] < non_o['DepthTop_cm'].min()]['DepthBot_cm'].max()

    cryo = group.copy()
    cryo['CryostratFnl'] = cryo['CryostratFnl'].astype(str)

    pf_depth = cryo[cryo['CryostratFnl'].str.contains("P|M", na=False)]['DepthTop_cm'].min()
    thaw = cryo[cryo['CryostratFnl'].str.contains("AL", na=False)]
    if not np.isnan(pf_depth):
        thaw = thaw[thaw['DepthTop_cm'] < pf_depth]
    thaw_depth = thaw['DepthBot_cm'].max() if not thaw.empty else np.nan
    if np.isnan(pf_depth):
        pf_depth = cryo[cryo['CryostratFnl'].str.contains("F", na=False)]['DepthTop_cm'].min()

    all_u_like = cryo['CryostratFnl'].notna().all() and cryo['CryostratFnl'].str.contains("U", na=False).all()
    has_al = cryo['CryostratFnl'].str.contains("AL", na=False).any()
    has_pm = cryo['CryostratFnl'].str.contains("P|M", na=False).any()

    if all_u_like and not has_al and not has_pm:
        thaw_depth = cryo['DepthBot_cm'].max()
        pf_observed = 0
    elif not np.isnan(pf_depth):
        pf_observed = 1
    elif not np.isnan(thaw_depth):
        pf_observed = 0
    else:
        pf_observed = pd.NA

    return pd.Series({
        'SiteIDFnl': siteidfnl,
        'Year': year,
        'site_id': site_id,
        'lat': lat,
        'lon': lon,
        'date': date,
        'org_thick': org_thick,
        'thaw_depth': thaw_depth,
        'pf_depth': pf_depth,
        'pf_observed': pf_observed,
        'obs_limit': obs_limit,
        'method': method,
        'year_disagreement': group['year_disagreement'].any()
    })

# Apply summarization
summary = soil_df.groupby(['SiteIDFnl', 'effective_Year']).apply(summarize).reset_index(drop=True)

# Final filtering: drop rows missing lat/lon or thaw_depth/pf_observed
summary_filtered = summary[
    summary[['lat', 'lon', 'pf_observed']].notna().all(axis=1)
]

summary_filtered = summary_filtered.drop(columns = ['Year', 'SiteIDFnl', 'year_disagreement'])
summary_filtered.drop(summary_filtered[summary_filtered['site_id'] == 'cnflt'].index, inplace=True)
summary_filtered['date'] = summary_filtered['date'].replace('', pd.NA)
summary_filtered.dropna(subset=['date'], inplace=True)

summary_filtered['pf_observed'] = summary_filtered['pf_observed'].astype('Int64')  # Handles NaN
summary_filtered['pf_depth'] = pd.to_numeric(summary_filtered['pf_depth'], errors='coerce')
summary_filtered['source'] = source

# Save final output


data_utils.check_columns(summary_filtered)

summary_filtered.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
