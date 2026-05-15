#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Smith_Burgess_2002"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jrowland"
last_substantive_update = "2026-04-11"
source_dataset = '''
Smith, S. L.; Burgess, M. M. 2002. A digital database of permafrost thickness
in Canada. Geological Survey of Canada, Open File 4173. Natural Resources
Canada. https://doi.org/10.4095/213043
'''
processing_assumptions = [
  "Only the active-layer-thickness field from the broader permafrost-thickness database is used for CUSP processing.",
  "The largest integer found in each active-layer-thickness cell is taken as the usable thaw depth.",
  "Rows containing explicit no markers are retained as pf_observed = 0, while rows lacking both a numeric thickness and a no marker are dropped.",
  "A midpoint year is extracted from PERIOD and used as the date field.",
  "pf_depth is set equal to thaw_depth for all retained rows, and method is exported as unknown because the source workbook aggregates multiple monitoring contexts.",
]
temporal_handling = [
  "Date is reduced to a midpoint year inferred from the PERIOD field rather than a full observation date.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the workbook without reprojection.",
]
manual_steps = []
known_limitations = [
  "The processed output uses only the active-layer-thickness information from a broader permafrost database product.",
  "Temporal precision is limited to an inferred midpoint year.",
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

source = "Smith_Burgess_2002"




# ------------------------------------------------------------------
# CONFIG – point to Excel file & basic parameters
# ------------------------------------------------------------------
EXCEL_PATH = Path(_ROOT_DIR) / "data" / source /'Permafrost Database3.xlsx'
SHEETS       = ["NWT-Nunavut", "Yukon", "Provinces"]          # sheets to load
KEEP_COLS    = ["SITE LOCATION", "LAT(°N)", "LONG (°W)", "PERIOD",
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

    return pd.DataFrame({
        "thickness_cm_int": numeric,
        "is_no_flag": flag
    })
# ------- extract a date from the period column
def extract_mid_year(val):
    """Convert a year or range like '1980-1990' into an integer midpoint year."""
    if isinstance(val, str):
        nums = re.findall(r'\d{4}', val)
        if nums:
            nums = list(map(int, nums))
            return int(sum(nums) / len(nums))  # single year → itself; range → average

    elif isinstance(val, (int, float)):
        if not pd.isna(val):
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

#clean up data frame and rename columns

combined_df.rename(columns={"is_no_flag": "pf_observed",
                   "LAT(°N)":"lat",
                   "LONG (°W)":"lon",
                   "thickness_cm_int" : "thaw_depth",
                   "SITE LOCATION":"site_id",
                   "PERIOD_MIDYEAR":"date"
                   }, inplace=True)
combined_df = combined_df.drop(columns = ['ACTIVE LAYER THICKNESS (cm)', 'PERIOD'])

combined_df['obs_limit'] = np.nan
combined_df['method'] = 'unknown'
combined_df['source'] = source
combined_df['pf_depth'] = combined_df['thaw_depth']

#drop site without a measurement date
combined_df['date'] = combined_df['date'].replace('', pd.NA)
combined_df.dropna(subset=['date'], inplace=True)

# SAVE CLEANED CSV
# -----------------------------------------------------
data_utils.check_columns(combined_df)

combined_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
