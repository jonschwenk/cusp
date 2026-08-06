#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Bakian_Dogaheh_2020"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Bakian-Dogaheh, K.; Chen, R. H.; Moghaddam, M.; Yi, Y.; Tabatabaeenejad, A.
2020. ABoVE: Active Layer Soil Characterization of Permafrost Sites, Northern
Alaska, 2018 (Version 1). ORNL Distributed Active Archive Center.
https://doi.org/10.3334/ORNLDAAC/1759
'''
processing_assumptions = [
  "Source dates are normalized from mixed MM/DD/YY strings and Excel serial values.",
  "Rows with numeric active-layer thickness are treated as permafrost-present, so pf_observed is fixed to 1 and pf_depth is set equal to thaw_depth.",
  "Eight -9999 rows flagged water are excluded because they contain no active-layer measurement and do not establish permafrost state.",
  "method is set to tp/pit and transect is retained as transect_direction.",
  "The source publishes hundreds of 5 m transect measurements but only six distinguishable coordinate supports; rows are therefore averaged by site/date/coordinate rather than released as hundreds of colocated points.",
]
temporal_handling = [
  "Per-record dates are preserved after normalization from the source date field.",
]
spatial_handling = [
  "Coordinates are read directly from the source CSV without reprojection.",
  "Coordinate-level summaries receive coord_site_level and summary_statistic flags, and retain native counts and contributing transect names.",
]
manual_steps = []
known_limitations = [
  "The assumption that all sites are permafrost-present should be revisited if the source dataset is used outside its intended study context.",
  "Water locations without a reported active-layer value are not retained as observations.",
  "Published coordinates do not resolve individual 5 m transect positions, so within-coordinate spatial variability is represented by summary statistics.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Bakian_Dogaheh_2020'


df = pd.read_csv(_ROOT_DIR / "data" / source / "Bakian-Dogaheh2020alt.csv")

# -----------------------------------------------------
# RENAME COLUMNS
# -----------------------------------------------------
column_mapping = {
    "sample_date": "date",
    "latitude": "lat",
    "longitude": "lon",
    "alt": "thaw_depth",  # Standardize to thaw_depth
    "site": "site_id",
    "transect": "transect_direction",
}
df.rename(columns=column_mapping, inplace=True)
df['thaw_depth'] = pd.to_numeric(df['thaw_depth'], errors='coerce')
invalid_alt = df['thaw_depth'].isna() | df['thaw_depth'].eq(-9999)
if int(invalid_alt.sum()) != 8:
    raise ValueError(f"Expected 8 Bakian rows without ALT; found {int(invalid_alt.sum())}.")
df = df.loc[~invalid_alt].copy()

# -----------------------------------------------------
# FORMAT DATE COLUMN (handles MM/DD/YY and Excel serials)
# -----------------------------------------------------
def convert_dates(x):
    try:
        return pd.to_datetime(x, format='%m/%d/%y').strftime('%Y-%m-%d')
    except ValueError:
        try:
            return (pd.to_datetime("1899-12-30") + pd.to_timedelta(int(x), "D")).strftime('%Y-%m-%d')
        except:
            return x  # Leave unchanged if format is unrecognized

df["date"] = df["date"].astype(str).apply(convert_dates)

# -----------------------------------------------------
# ADD/UPDATE REQUIRED COLUMNS
# -----------------------------------------------------
df["pf_observed"] = 1 # based on the site descriptions all site are in continuous pf, study was for ALT
df["obs_limit"] = np.nan
df["source"] = source
df["pf_depth"] = df['thaw_depth'] #measurements were made late season therefore assume ALT = pf depth
df["comments"] = pd.NA
df["method"] = "tp_pit"


# -----------------------------------------------------
# CLEANING
# -----------------------------------------------------
# Drop unused columns if they exist
columns_to_drop = ["measurement_traverse", "measurement_purpose", "measurement_order", "alt_fl"]
df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)

# -----------------------------------------------------
# SELECT + REORDER FINAL COLUMNS
# -----------------------------------------------------
final_columns = [
    "lon", "lat", "date", "pf_depth", "pf_observed", "thaw_depth", "obs_limit",
    "site_id", "transect_direction", 
     "source", "comments", "method"
]
df = df[final_columns]

df = (
    df.groupby(['site_id', 'date', 'lat', 'lon'], as_index=False, dropna=False)
    .agg(
        thaw_depth=('thaw_depth', 'mean'),
        pf_depth=('pf_depth', 'mean'),
        bakian_alt_min_cm=('thaw_depth', 'min'),
        bakian_alt_max_cm=('thaw_depth', 'max'),
        bakian_native_count=('thaw_depth', 'size'),
        bakian_transects=('transect_direction', lambda values: ';'.join(sorted(set(values.dropna().astype(str))))),
    )
)
if len(df) != 6 or int(df['bakian_native_count'].sum()) != 495:
    raise ValueError("Unexpected Bakian coordinate aggregation counts.")
df['source'] = source
df['pf_observed'] = 1
df['obs_limit'] = np.nan
df['method'] = 'tp_pit'
df['comments'] = pd.NA
df['quality_flag_summary_statistic'] = True
df['quality_flag_coord_site_level'] = True

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)


