
"""
metadata_schema_version = 1
source_key = "Jorgenson_Kanevskiy_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
source_dataset = '''
Jorgenson, Mark; Kanevskiy, Mikhail. 2025. Alaska Permafrost Soils Inventory
and Thermokarst Monitoring Database 2024 Update. Arctic Data Center.
doi:10.18739/A27P8TG0G
'''
processing_assumptions = [
  "Soil stratigraphy rows are grouped by SiteIDFnl and effective year after parsing embedded year values out of SiteIDFnl where available.",
  "Site metadata are resolved by trying exact SiteID/year matches first, then composite IDs, then relaxed SiteID/SiteIDFld matches.",
  "Permafrost presence/absence uses the source SoilPFrost field (P=present, A=absent); source-unknown U records are excluded.",
  "thaw_depth uses the source SoilThawDep_cm field after treating 999 as missing.",
  "pf_depth is retained only when thaw_depth is unavailable and a definite permafrost or massive-ice CryostratFnl horizon supplies a depth.",
  "ALF denotes frozen active-layer or seasonal-frost material and is not interpreted as permafrost; TL, PT, and TLP are also not treated as exact permafrost tops.",
  "Organic thickness is derived from O horizons above the first non-O horizon.",
  "method is fixed to aug_pit, and rows with unresolved/conflicting site metadata are dropped before export.",
  "obs_limit is blank for permafrost-presence rows. For absence rows it is the deepest valid value among SoilObsDep_cm and SoilThawDep_cm, with profile bottom used only when neither site field supplies a limit.",
  "The 2022 Jago and Gosling dedicated releases are primary where their normalized site ID and observation year match this compiled inventory; 93 Jago and 15 Gosling copies are removed.",
  "A zero-depth placeholder profile cannot support either state or depth and is excluded.",
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
  "SoilPFrost defines P as proven or highly likely permafrost; present records without a reported thaw depth or definite permafrost horizon are retained but flagged as assumed state.",
  "The source contains several soil sampling methods, but this legacy processor retains the combined pit/auger canonical method and flags it as approximate.",
  "Although the inventory metadata says SoilObsDep_cm includes frost-probe depth, 58 raw site rows report SoilThawDep_cm deeper than SoilObsDep_cm. The dedicated Gosling release identifies the smaller field as soil-profile depth and independently uses SoilThawDep_cm as frost-probe reach. CUSP therefore treats these as different measurement extents rather than swapped values, uses the larger absence value as the actual search limit, and retains both source fields for audit.",
]
external_dependencies = [
  "data/Jorgenson_Kanevskiy_2022_Jago/processed_jorgenson_kanevskiy_2022_jago.csv is required for source-specific overlap filtering.",
  "data/Jorgenson_Kanevskiy_2022_Gosling/processed_jorgenson_kanevskiy_2022_gosling.csv is required for source-specific overlap filtering.",
]
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
PRIMARY_SOURCE_PATHS = {
    "Jago": (
        _ROOT_DIR / "data" / "Jorgenson_Kanevskiy_2022_Jago"
        / "processed_jorgenson_kanevskiy_2022_jago.csv"
    ),
    "Gosling": (
        _ROOT_DIR / "data" / "Jorgenson_Kanevskiy_2022_Gosling"
        / "processed_jorgenson_kanevskiy_2022_gosling.csv"
    ),
}
EXPECTED_PRIMARY_OVERLAPS = {"Jago": 93, "Gosling": 15}


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
site_df['SoilPFrost_norm'] = site_df['SoilPFrost'].astype('string').str.strip().str.upper()
site_df['SoilThawDep_cm_num'] = pd.to_numeric(site_df['SoilThawDep_cm'], errors='coerce')
site_df.loc[
    site_df['SoilThawDep_cm_num'].isin([999, 9999]), 'SoilThawDep_cm_num'
] = np.nan
site_df['SoilObsDep_cm_num'] = pd.to_numeric(site_df['SoilObsDep_cm'], errors='coerce')
site_df.loc[site_df['SoilObsDep_cm_num'].eq(9999), 'SoilObsDep_cm_num'] = np.nan
site_df['SoilMethod_norm'] = site_df['SoilMethod'].astype('string').str.strip()

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
        return pd.Series([
            np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
            year_disagreement,
        ])

    def resolve(values):
        values = list(pd.unique(pd.Series(values).dropna()))
        return values[0] if len(values) == 1 else "cnflt" if len(values) > 1 else np.nan

    return pd.Series([
        resolve(matches['SiteID'].dropna()),
        resolve(matches['LatWGS84'].dropna()),
        resolve(matches['LonWGS84'].dropna()),
        resolve(matches['Date'].dropna()),
        resolve(matches['SoilPFrost_norm'].dropna()),
        resolve(matches['SoilThawDep_cm_num'].dropna()),
        resolve(matches['SoilObsDep_cm_num'].dropna()),
        resolve(matches['SoilMethod_norm'].dropna()),
        year_disagreement
    ])

soil_df[[
    'site_id',
    'lat',
    'lon',
    'date',
    'source_pf_state',
    'source_thaw_depth',
    'source_obs_limit',
    'source_soil_method',
    'year_disagreement',
]] = soil_df.apply(resolve_site_metadata, axis=1)

# Convert numeric fields
soil_df['DepthTop_cm'] = pd.to_numeric(soil_df['DepthTop_cm'], errors='coerce')
soil_df['DepthBot_cm'] = pd.to_numeric(soil_df['DepthBot_cm'], errors='coerce')

# These codes identify definite permafrost or massive ground ice in the source
# reference table. Active-layer and transitional codes are intentionally absent.
DEFINITE_PERMAFROST_CODES = {
    "PF", "PC", "PE", "PG", "PGB", "PER", "PS", "PQ", "PQB", "PQD",
    "PQP", "PQW", "PU", "PP", "PEC", "PIW", "MC", "MG", "MI", "MU",
    "MWE", "MWS",
}


# Summarize each stratigraphic profile using the explicit site-level state.
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
    profile_bottom = group['DepthBot_cm'].max()
    if pd.notna(profile_bottom) and profile_bottom <= 0:
        profile_bottom = np.nan
    source_obs_limit = pd.to_numeric(
        pd.Series([group['source_obs_limit'].iloc[0]]), errors='coerce'
    ).iloc[0]
    if pd.notna(source_obs_limit) and source_obs_limit <= 0:
        source_obs_limit = np.nan
    method = "aug_pit"

    o_layers = group[group['HrznFnl'].astype(str).str.startswith("O", na=False)]
    non_o = group[group['HrznFnl'].astype(str).str.match("^[^O]", na=False)]
    org_thick = o_layers['DepthBot_cm'].max() if non_o.empty else         o_layers[o_layers['DepthTop_cm'] < non_o['DepthTop_cm'].min()]['DepthBot_cm'].max()

    cryo = group.copy()
    cryo['cryo_code'] = cryo['CryostratFnl'].astype('string').str.strip().str.upper()
    definite_pf = cryo[cryo['cryo_code'].isin(DEFINITE_PERMAFROST_CODES)]
    cryo_pf_depth = definite_pf['DepthTop_cm'].min() if not definite_pf.empty else np.nan

    source_state = str(group['source_pf_state'].iloc[0]).strip().upper()
    pf_observed = {"P": 1, "A": 0}.get(source_state, pd.NA)
    is_presence = source_state == "P"
    is_absence = source_state == "A"
    source_thaw_depth = pd.to_numeric(
        pd.Series([group['source_thaw_depth'].iloc[0]]), errors='coerce'
    ).iloc[0]

    thaw_depth = source_thaw_depth if is_presence else np.nan
    # Prefer the explicitly reported thaw depth. The cryostratigraphic top remains
    # in provenance and fills pf_depth only when no reported thaw depth exists.
    pf_depth = (
        thaw_depth
        if is_presence and pd.notna(thaw_depth)
        else cryo_pf_depth if is_presence else np.nan
    )
    state_assumed = is_presence and pd.isna(source_thaw_depth) and pd.isna(cryo_pf_depth)
    source_limits = [
        value for value in (source_obs_limit, source_thaw_depth)
        if pd.notna(value) and value > 0
    ]
    obs_limit = (
        max(source_limits)
        if is_absence and source_limits
        else profile_bottom if is_absence else np.nan
    )
    profile_bottom_limit = is_absence and not source_limits and pd.notna(profile_bottom)
    thaw_depth_used_as_limit = (
        is_absence
        and pd.notna(source_thaw_depth)
        and source_thaw_depth > 0
        and (pd.isna(source_obs_limit) or source_thaw_depth > source_obs_limit)
    )

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
        'jorgenson_source_pf_state': source_state,
        'jorgenson_reported_soil_obs_depth_cm': source_obs_limit,
        'jorgenson_reported_thaw_depth_cm': source_thaw_depth,
        'jorgenson_cryo_pf_depth_cm': cryo_pf_depth,
        'jorgenson_profile_bottom_cm': profile_bottom,
        'jorgenson_source_soil_method': group['source_soil_method'].iloc[0],
        'quality_flag_pf_state_assumed': state_assumed,
        'quality_flag_obs_limit_profile_bottom': profile_bottom_limit,
        'quality_flag_source_unit_or_code_recoded': thaw_depth_used_as_limit,
        'quality_flag_method_approximate_or_unknown': True,
        'year_disagreement': group['year_disagreement'].any()
    })

# Apply summarization
grouping_columns = ['SiteIDFnl', 'effective_Year']
profile_columns = [column for column in soil_df.columns if column not in grouping_columns]
summary = (
    soil_df.groupby(grouping_columns, group_keys=False)[profile_columns]
    .apply(summarize)
    .reset_index(drop=True)
)

# Final filtering: drop rows missing lat/lon or thaw_depth/pf_observed
summary_filtered = summary[summary[['lat', 'lon', 'pf_observed']].notna().all(axis=1)].copy()

summary_filtered = summary_filtered.drop(columns = ['Year', 'SiteIDFnl', 'year_disagreement'])
conflict_columns = ['site_id', 'lat', 'lon', 'date']
has_metadata_conflict = summary_filtered[conflict_columns].astype('string').eq('cnflt').any(axis=1)
summary_filtered = summary_filtered.loc[~has_metadata_conflict].copy()
summary_filtered['date'] = summary_filtered['date'].replace('', pd.NA)
summary_filtered.dropna(subset=['date'], inplace=True)

summary_filtered['pf_observed'] = summary_filtered['pf_observed'].astype('Int64')  # Handles NaN
summary_filtered['pf_depth'] = pd.to_numeric(summary_filtered['pf_depth'], errors='coerce')
invalid_absence = summary_filtered['pf_observed'].eq(0) & (
    summary_filtered['obs_limit'].isna() | summary_filtered['obs_limit'].le(0)
)
summary_filtered = summary_filtered.loc[~invalid_absence].copy()
summary_filtered['source'] = source


def normalized_site_year(frame):
    """Build the stable site/year identity used for dedicated-source filtering."""

    site = (
        frame['site_id'].astype('string').str.upper()
        .str.replace(r'[^A-Z0-9]', '', regex=True)
    )
    year = pd.to_datetime(frame['date'], errors='coerce').dt.year.astype('Int64')
    return pd.MultiIndex.from_arrays([site, year])


inventory_keys = normalized_site_year(summary_filtered)
removed_counts = {}
remove_primary_copy = np.zeros(len(summary_filtered), dtype=bool)
for primary_name, primary_path in PRIMARY_SOURCE_PATHS.items():
    if not primary_path.exists():
        raise FileNotFoundError(f"{primary_path} is required for overlap filtering.")
    primary = pd.read_csv(primary_path, low_memory=False)
    primary_keys = normalized_site_year(primary).drop_duplicates()
    matches = inventory_keys.isin(primary_keys)
    count = int(matches.sum())
    expected = EXPECTED_PRIMARY_OVERLAPS[primary_name]
    if count != expected:
        raise ValueError(
            f"Expected {expected} {primary_name}/2025 inventory overlaps; found {count}."
        )
    removed_counts[primary_name] = count
    remove_primary_copy |= matches

summary_filtered = summary_filtered.loc[~remove_primary_copy].copy()

# Save final output


data_utils.check_columns(summary_filtered)

summary_filtered.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
print(
    f"Removed {removed_counts['Jago']} Jago and {removed_counts['Gosling']} "
    f"Gosling copies; wrote {len(summary_filtered):,} inventory observations."
)
