#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Zhao_2021"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Zhao, L.; Zou, D.; Hu, G.; Wu, T.; Du, E.; Liu, G.; Xiao, Y.; Li, R.; Pang,
Q.; Qiao, Y.; Wu, X.; Sun, Z.; Xing, Z.; Sheng, Y.; Zhao, Y.; Shi, J.; Xie,
C.; Wang, L.; Wang, C.; Cheng, G. 2021. A synthesis dataset of permafrost
thermal state for the Qinghai-Tibet (Xizang) Plateau, China. Earth System
Science Data 13: 4207-4218. https://doi.org/10.5194/essd-13-4207-2021
'''
processing_assumptions = [
  "For each site-year, the script searches all temperature-depth observations and keeps the deepest depth that is above 0 C, subject to the deeper-sensor decision rules in process_sheet().",
  "pf_observed is set to 1 only when a deeper sensor exists with temperature below 0 C; years with deeper readings that are all above 0 C or entirely missing are treated as indeterminate and skipped.",
  "obs_limit is set to the maximum depth column available for each site's worksheet.",
  "method is set to temp for all processed rows, and pf_depth is set equal to thaw_depth where pf_observed = 1.",
]
temporal_handling = [
  "Daily observations are reduced to one representative record per site-year based on the deepest valid thaw depth and warmest tie-breaking temperature.",
]
spatial_handling = [
  "Coordinates are attached by normalizing site names and joining to Site_Location_Info_Structured.csv without reprojection.",
]
manual_steps = []
known_limitations = [
  "Years with insufficient deeper-sensor information are dropped entirely rather than carried forward as unknown permafrost states.",
  "The site-name normalization removes trailing parenthetical descriptors, which could collapse distinct labels if future source naming changes.",
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

source = "Zhao_2021"




# ------------------------------------------------------------------
# 1. paths to your uploads
# ------------------------------------------------------------------
EXCEL_PATH = Path(_ROOT_DIR) / "data" / source /"Active layer of ground temperature.xlsx"
SITE_CSV   = Path(_ROOT_DIR) / "data" / source /"Site_Location_Info_Structured.csv"

# ------------------------------------------------------------------
# 2. helper utilities
# ------------------------------------------------------------------
def normalize(name: str) -> str:
    """Strip whitespace / parentheses so 'QT09 (XDT)' → 'QT09'."""
    return re.split(r'[\s(]', str(name))[0].strip()

def depth_columns(df):
    """Return (depth_cols, depth_cm_dict) from any sheet."""
    dcols, depths = [], {}
    for c in df.columns:
        if c.lower().startswith(("year", "month", "day")):
            continue
        m = re.search(r"(\d+(?:\.\d*)?)", str(c))         # 10cmGT → 10
        if m:
            depth = float(m.group(1))
            dcols.append(c)
            depths[c] = depth
    return dcols, depths

def process_sheet(site, df):
    """Return one row per YEAR for a single sheet/site."""
    dcols, dcm = depth_columns(df)
    if not dcols or not {"Year", "Month", "Day"}.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(dict(year=df.Year, month=df.Month, day=df.Day),
                                errors="coerce")

    records = []
    for yr, g in df.groupby(df.date.dt.year):
        best = None
        for _, row in g.iterrows():

            # all depths with T > 0 °C on this date
            gt0 = [c for c in dcols if pd.notna(row[c]) and row[c] > 0]
            if not gt0:
                continue

            # deepest such depth & its temp
            deep_col  = max(gt0, key=lambda c: dcm[c])
            deep_cm   = dcm[deep_col]
            deep_temp = row[deep_col]

            # deeper sensors, if any
            deeper    = [c for c in dcols if dcm[c] > deep_cm]
            vals      = [row[c] for c in deeper]

            deeper_lt0   = any(pd.notna(v) and v < 0 for v in vals)
            deeper_data  = any(pd.notna(v) for v in vals)

            # --------------------------------------------------
            # apply your decision tree
            # --------------------------------------------------
            if not deeper:                    # deepest sensor overall
                thaw_depth = deep_cm
                pf_flag    = 0
            elif deeper_lt0:                  # deeper frozen layer seen
                thaw_depth = deep_cm
                pf_flag    = 1
            elif not deeper_data:             # no readings below → unknown
                thaw_depth = np.nan
                pf_flag    = np.nan
            else:                             # deeper readings but all >0
                thaw_depth = np.nan
                pf_flag    = np.nan

            if np.isnan(thaw_depth):
                continue          # skip years with indeterminate thaw depth

            # keep row with greatest thaw depth; tie-break by warmest temp
            if (best is None or
                thaw_depth > best["thaw_depth_cm"] or
                (thaw_depth == best["thaw_depth_cm"] and deep_temp > best["temp_C"])):
                best = dict(site=site, year=int(yr), date=row.date,
                            thaw_depth_cm=thaw_depth, pf_observed=pf_flag,
                            temp_C=deep_temp)

        if best:
            records.append(best)

    return pd.DataFrame(records)

# ------------------------------------------------------------------
# 3. run across every sheet
# ------------------------------------------------------------------
xls = pd.ExcelFile(EXCEL_PATH)
all_rows = []
for sheet in xls.sheet_names:
    sheet_df = pd.read_excel(xls, sheet_name=sheet)
    all_rows.append(process_sheet(sheet, sheet_df))

combined = pd.concat(all_rows, ignore_index=True)

# Compute obs_limit: max depth per site (based on columns)
obs_limits = {}
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet, nrows=1)  # header only
    _, depth_map = depth_columns(df)
    if depth_map:
        obs_limits[normalize(sheet)] = max(depth_map.values())

combined["obs_limit"] = combined["site"].apply(lambda s: obs_limits.get(normalize(s), np.nan))

# ------------------------------------------------------------------
# 4. attach lat / lon from the site list
# ------------------------------------------------------------------
meta = pd.read_csv(SITE_CSV)
meta["site_key"]    = meta["Site Name"].apply(normalize)
combined["site_key"] = combined["site"].apply(normalize)

combined = combined.merge(
    meta[["site_key", "Latitude (°N)", "Longitude (°E)"]],
    on="site_key", how="left"
).drop(columns="site_key")

# ----- Drop unneeded columns and standardize names
combined = combined.drop(columns = ['year'])

combined.rename(columns={"site": "site_id",
                   'Latitude (°N)':"lat",
                   'Longitude (°E)':"lon",
                   "thaw_depth_cm":"thaw_depth"
                   }, inplace=True)

combined['source'] = source
combined['method'] = 'temp'
combined["pf_depth"] = np.nan
combined["pf_depth"] = np.where(combined["pf_observed"] == 1,
                                combined["thaw_depth"], np.nan)

# ------------------------------------------------------------------
# 5. save
# ------------------------------------------------------------------
data_utils.check_columns(combined)

combined.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
