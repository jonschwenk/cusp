#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Smith_Burgess_2002"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
source_dataset = '''
Smith, S. L.; Burgess, M. M. 2002. A digital database of permafrost thickness
in Canada. Geological Survey of Canada, Open File 4173. Natural Resources
Canada. https://doi.org/10.4095/213043
'''
processing_assumptions = [
  "Only the active-layer-thickness field from the broader permafrost-thickness database is used for CUSP processing.",
  "The largest integer found in each active-layer-thickness cell is taken as the usable thaw depth.",
  "Rows lacking a numeric active-layer thickness are dropped unless explicitly marked no pf. Exact observation matches and additional coordinate/site-identifier matches represented in Smith_Burgess_2000 are removed in favor of that CUSP-relevant ground-temperature product.",
  "A midpoint year is extracted from PERIOD and exported as July 1 of that year.",
  "West longitudes stored as positive degrees W are converted to negative WGS84 longitude.",
  "pf_depth is set equal to thaw_depth for all retained rows, and method is exported as unknown because the source workbook aggregates multiple monitoring contexts.",
]
temporal_handling = [
  "Date is reduced to July 1 of a midpoint year inferred from the PERIOD field rather than a full observation date.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the workbook without reprojection.",
]
manual_steps = []
known_limitations = [
  "The processed output uses only the active-layer-thickness information from a broader permafrost database product.",
  "Temporal precision is limited to an inferred midpoint year.",
  "Thirty-five exact observation matches and 11 additional coordinate/site-identifier matches are removed against Smith_Burgess_2000; differing active-layer values at those 11 sites are treated as alternate compiled representations rather than independent observations.",
  "Bounded, approximate, or ranged active-layer text is converted to one representative numeric value and carries source_value_approximate.",
]
external_dependencies = [
  "data/Smith_Burgess_2000/processed_smith_burgess_2000.csv is required for source-specific overlap filtering.",
]
notes = ""
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Smith_Burgess_2002"




# ------------------------------------------------------------------
# CONFIG – point to Excel file & basic parameters
# ------------------------------------------------------------------
EXCEL_PATH = Path(_ROOT_DIR) / "data" / source /'Permafrost Database3.xlsx'
SHEETS       = ["NWT-Nunavut", "Yukon", "Provinces"]          # sheets to load
KEEP_COLS    = ["SITE LOCATION", "SITE IDENTIFIER", "LAT(°N)", "LONG (°W)", "PERIOD",
                "ACTIVE LAYER THICKNESS (cm)"]
HEADER_ROW   = 0                                    # 0-based row index with headers
TARGET_COL   = "ACTIVE LAYER THICKNESS (cm)"        # column to clean
# ------------------------------------------------------------------

# -------- helper: extract largest integer from any cell -----------
def extract_max_int(val):
    """Return largest integer found or NaN."""
    if isinstance(val, (int, float)) and not pd.isna(val):
        return int(val)

    if isinstance(val, str):
        nums = re.findall(r"\d+", val)
        if nums:
            return max(map(int, nums))
    return np.nan

# -------- helper: full cleaning of the thickness column ----------
def clean_thickness(series: pd.Series) -> pd.DataFrame:
    """Return 2-col DF: numeric thickness & is_no_flag."""
    txt = series.astype(str).str.lower().str.strip()

    # numeric thickness (integer cm) – take largest number present
    numeric = txt.replace({"~": ""}, regex=True).apply(extract_max_int)

    # NaN out obvious text placeholders
    numeric = numeric.where(~txt.isin({"no", "na", ""}))

    # flag: 0 if the *original* text contains 'no', else 1
    flag = (~txt.str.contains(r"\bno\b", na=True)).astype(int)
    approximate = numeric.notna() & ~txt.str.fullmatch(r"\d+(?:\.\d+)?", na=False)

    return pd.DataFrame({
        "thickness_cm_int": numeric,
        "is_no_flag": flag,
        "source_value_approximate": approximate,
    })
# ------- extract a date from the period column
def extract_mid_year(val):
    """Convert a year or range like '1980-1990' into an integer midpoint year."""
    if isinstance(val, (pd.Timestamp, np.datetime64)) or (
        hasattr(val, 'year') and not isinstance(val, (str, int, float))
    ):
        return pd.Timestamp(val).year

    if isinstance(val, str):
        nums = re.findall(r'\d{4}', val)
        if nums:
            nums = list(map(int, nums))
            return int(sum(nums) / len(nums))  # single year → itself; range → average

        short_years = re.findall(r'/([0-9]{2})(?:\D|$)', val)
        if short_years:
            years = [1900 + int(year) for year in short_years]
            return int(sum(years) / len(years))

    elif isinstance(val, (int, float)):
        if not pd.isna(val) and 1800 <= float(val) <= 2200:
            return int(val)

    return np.nan


# ---------------- main load & process routine --------------------
def load_concat_clean() -> pd.DataFrame:
    xls   = pd.ExcelFile(EXCEL_PATH)
    frames = []

    for sheet in SHEETS:
        # read only requested columns; ignore rows fully empty
        df = (pd.read_excel(xls, sheet_name=sheet, header=HEADER_ROW,
                            usecols=KEEP_COLS)
                .dropna(how="all"))

        # run cleaning on target column and append cleaned cols
        cleaned = clean_thickness(df[TARGET_COL])
        df      = df.join(cleaned)
        
        # Extract midpoint year
        df['PERIOD_MIDYEAR'] = df['PERIOD'].apply(extract_mid_year)

        frames.append(df)

    # concatenate all sheets vertically
    return pd.concat(frames, ignore_index=True)

# ------------------------------------------------------------------
# USAGE EXAMPLE
# ------------------------------------------------------------------
if __name__ == "__main__":
    combined_df = load_concat_clean()
    print(combined_df.head())
    
combined_df = combined_df[~(combined_df['thickness_cm_int'].isna() & (combined_df['is_no_flag'] == 1))]
combined_df = combined_df.reset_index(drop=True)
combined_df['source_active_layer_text'] = combined_df[TARGET_COL]
combined_df['source_period'] = combined_df['PERIOD']

#clean up data frame and rename columns

combined_df.rename(columns={"is_no_flag": "pf_observed",
                   "LAT(°N)":"lat",
                   "LONG (°W)":"lon",
                   "thickness_cm_int" : "thaw_depth",
                   "SITE LOCATION":"site_location",
                   "SITE IDENTIFIER":"source_site_identifier",
                   "PERIOD_MIDYEAR":"date"
                   }, inplace=True)
combined_df = combined_df.drop(columns = ['ACTIVE LAYER THICKNESS (cm)', 'PERIOD'])

location = combined_df['site_location'].astype('string').str.strip()
identifier = combined_df['source_site_identifier'].astype('string').str.strip()
has_identifier = identifier.notna() & ~identifier.isin(['', '-'])
combined_df['site_id'] = location.where(
    ~has_identifier, location + ' | ' + identifier
)
combined_df['lon'] = -pd.to_numeric(combined_df['lon'], errors='coerce').abs()
combined_df['lat'] = pd.to_numeric(combined_df['lat'], errors='coerce')
combined_df['obs_limit'] = np.nan
combined_df['method'] = 'unknown'
combined_df['source'] = source
combined_df['pf_depth'] = combined_df['thaw_depth']
combined_df['quality_flag_date_assigned'] = True
combined_df['quality_flag_date_source_approximate'] = True
combined_df['quality_flag_source_unit_or_code_recoded'] = True
combined_df['quality_flag_source_value_approximate'] = combined_df[
    'source_value_approximate'
]

#drop site without a measurement date
combined_df['date'] = combined_df['date'].replace('', pd.NA)
combined_df.dropna(subset=['date'], inplace=True)
combined_df['date'] = combined_df['date'].astype(int).astype(str) + '-07-01'

earlier_path = (
    _ROOT_DIR / "data" / "Smith_Burgess_2000"
    / "processed_smith_burgess_2000.csv"
)
if not earlier_path.exists():
    raise FileNotFoundError(
        f"{earlier_path} is required for Smith/Burgess overlap filtering."
    )
earlier = pd.read_csv(earlier_path, low_memory=False)

def add_overlap_keys(frame):
    keyed = frame.copy()
    keyed['_lat_key'] = pd.to_numeric(keyed['lat'], errors='coerce').round(6)
    keyed['_lon_key'] = pd.to_numeric(keyed['lon'], errors='coerce').round(6)
    keyed['_depth_key'] = pd.to_numeric(
        keyed['thaw_depth'], errors='coerce'
    ).fillna(-9999).round(3)
    keyed['_pf_key'] = pd.to_numeric(
        keyed['pf_observed'], errors='coerce'
    ).astype('Int64')
    keyed['_date_key'] = keyed['date'].astype('string')
    return keyed

overlap_columns = [
    '_lat_key', '_lon_key', '_date_key', '_pf_key', '_depth_key'
]
keyed = add_overlap_keys(combined_df)
earlier_keys = add_overlap_keys(earlier)[overlap_columns].drop_duplicates()
matches = keyed[overlap_columns].merge(
    earlier_keys.assign(_smith_2000_overlap=True),
    on=overlap_columns,
    how='left',
)['_smith_2000_overlap'].fillna(False).astype(bool)
match_count = int(matches.sum())
if match_count != 35:
    raise ValueError(
        "Expected 35 exact Smith_Burgess_2002 overlaps with Smith_Burgess_2000; "
        f"found {match_count}. Source contents may have changed."
    )
print(
    f"Removed {match_count} Smith_Burgess_2002 rows already represented "
    "by Smith_Burgess_2000."
)
combined_df = combined_df.loc[~matches.to_numpy()].copy()

def normalize_identifier(series):
    return (
        series.astype('string').str.upper()
        .str.replace(r'[^A-Z0-9]', '', regex=True)
        .str.replace(r'SITE$', '', regex=True)
        .replace('', pd.NA)
    )

keyed_remaining = add_overlap_keys(combined_df)
keyed_remaining['_identifier_key'] = normalize_identifier(
    keyed_remaining['source_site_identifier']
)
earlier_identity = add_overlap_keys(earlier)
earlier_identity['_identifier_key'] = normalize_identifier(
    earlier_identity['source_site_identifier']
)
identity_columns = ['_lat_key', '_lon_key', '_identifier_key']
earlier_identity_keys = (
    earlier_identity.dropna(subset=['_identifier_key'])[identity_columns]
    .drop_duplicates()
)
identity_matches = keyed_remaining[identity_columns].merge(
    earlier_identity_keys.assign(_smith_2000_identity_overlap=True),
    on=identity_columns,
    how='left',
)['_smith_2000_identity_overlap'].fillna(False).astype(bool)
identity_match_count = int(identity_matches.sum())
if identity_match_count != 11:
    raise ValueError(
        "Expected 11 additional Smith/Burgess site-identity overlaps; "
        f"found {identity_match_count}. Source contents may have changed."
    )
print(
    f"Removed {identity_match_count} additional Smith_Burgess_2002 rows "
    "matching Smith_Burgess_2000 site identifiers and coordinates."
)
combined_df = combined_df.loc[~identity_matches.to_numpy()].copy()

# SAVE CLEANED CSV
# -----------------------------------------------------
data_utils.check_columns(combined_df)

combined_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
