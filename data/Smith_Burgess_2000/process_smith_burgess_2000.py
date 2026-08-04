#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Smith_Burgess_2000"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Smith, S.; Burgess, M. M. 2000. Ground temperature database for northern
Canada. Geological Survey of Canada, Open File 3954.
https://doi.org/10.4095/211804
'''
processing_assumptions = [
  "Only a subset of sheets and columns from the Canadian workbook are used, with active-layer thickness parsed out of free-form text values.",
  "The largest integer found in each active-layer-thickness cell is taken as the usable thaw depth.",
  "Rows explicitly marked no pf/no permafrost are retained as pf_observed = 0; their observation limit is the deepest row-specific ground-temperature sensor depth converted from m to cm.",
  "Rows lacking both a numeric thickness and an explicit no-permafrost marker are dropped.",
  "A midpoint year is extracted from PERIOD, including two-digit historical year ranges, and exported as July 1 of that year.",
  "West longitudes stored as positive degrees W are converted to negative WGS84 longitude.",
  "pf_depth is set equal to thaw_depth for numeric active-layer observations; method is temp for explicit no-permafrost temperature profiles and unknown for numeric active-layer values whose field method is heterogeneous.",
]
temporal_handling = [
  "Date is reduced to July 1 of a midpoint year inferred from the PERIOD field rather than a full observation date.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the workbook without reprojection.",
]
manual_steps = []
known_limitations = [
  "The processed output uses only the active-layer-thickness information from the broader ground-temperature database.",
  "Temporal precision is limited to an inferred midpoint year.",
  "Coordinates and active-layer values are compiled from heterogeneous original references and may have source-specific precision not recoverable from this workbook.",
]
external_dependencies = []
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

source = "Smith_Burgess_2000"




# ------------------------------------------------------------------
# CONFIG – point to Excel file & basic parameters
# ------------------------------------------------------------------
EXCEL_PATH = Path(_ROOT_DIR) / "data" / source /'Ground temperature database2.xlsx'
SHEETS       = ["ExDeep", "shgt", "shgt1"]          # sheets to load
KEEP_COLS    = ["SITE LOCATION", "SITE IDENTIFIER", "LATITUDE (°N)", "LONGITUDE (°W)", "PERIOD",
                "ACTIVE LAYER THICKNESS (cm)"]
HEADER_ROW   = 1                                    # 0-based row index with headers
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

    return pd.DataFrame({
        "thickness_cm_int": numeric,
        "is_no_flag": flag
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
        df = (pd.read_excel(
                    xls,
                    sheet_name=sheet,
                    header=HEADER_ROW,
                    usecols=lambda column: (
                        column in KEEP_COLS
                        or str(column).startswith("DEPTH (metre)")
                    ),
                )
                .dropna(how="all"))

        # run cleaning on target column and append cleaned cols
        cleaned = clean_thickness(df[TARGET_COL])
        df      = df.join(cleaned)
        depth_columns = [
            column for column in df.columns
            if str(column).startswith("DEPTH (metre)")
        ]
        df['deepest_temperature_depth_m'] = df[depth_columns].apply(
            pd.to_numeric, errors='coerce'
        ).max(axis=1)
        
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
                   "LATITUDE (°N)":"lat",
                   "LONGITUDE (°W)":"lon",
                   "thickness_cm_int" : "thaw_depth",
                   "SITE LOCATION":"site_location",
                   "SITE IDENTIFIER":"source_site_identifier",
                   "PERIOD_MIDYEAR":"date"
                   }, inplace=True)
depth_columns = [
    column for column in combined_df.columns
    if str(column).startswith("DEPTH (metre)")
]
combined_df = combined_df.drop(
    columns=['ACTIVE LAYER THICKNESS (cm)', 'PERIOD', *depth_columns]
)

location = combined_df['site_location'].astype('string').str.strip()
identifier = combined_df['source_site_identifier'].astype('string').str.strip()
has_identifier = identifier.notna() & ~identifier.isin(['', '-'])
combined_df['site_id'] = location.where(
    ~has_identifier, location + ' | ' + identifier
)
combined_df['lon'] = -pd.to_numeric(combined_df['lon'], errors='coerce').abs()
combined_df['lat'] = pd.to_numeric(combined_df['lat'], errors='coerce')

absence = combined_df['pf_observed'].eq(0)
combined_df['obs_limit'] = np.where(
    absence,
    pd.to_numeric(
        combined_df['deepest_temperature_depth_m'], errors='coerce'
    ) * 100,
    np.nan,
)
combined_df['method'] = np.where(absence, 'temp', 'unknown')
combined_df['source'] = source
combined_df['pf_depth'] = combined_df['thaw_depth'].where(~absence)
combined_df['quality_flag_date_assigned'] = True
combined_df['quality_flag_date_source_approximate'] = True
combined_df['quality_flag_source_unit_or_code_recoded'] = True

#drop site without a measurement date
combined_df['date'] = combined_df['date'].replace('', pd.NA)
combined_df.dropna(subset=['date'], inplace=True)
combined_df['date'] = combined_df['date'].astype(int).astype(str) + '-07-01'

missing_absence_limit = combined_df['pf_observed'].eq(0) & combined_df['obs_limit'].isna()
if missing_absence_limit.any():
    raise ValueError(
        "Smith_Burgess_2000 contains explicit absence rows without a temperature-profile depth."
    )

# SAVE CLEANED CSV
# -----------------------------------------------------
data_utils.check_columns(combined_df)

combined_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
