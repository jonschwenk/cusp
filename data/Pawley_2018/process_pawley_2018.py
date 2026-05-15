#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Pawley_2018"
release_clearance = "deferred"
permission_basis = "public_repository_terms"
original_author = "Annalise Khandelwal"
last_substantive_update = "2026-04-11"
source_dataset = '''
Pawley, S.M.; Utting, D.J. 2018. Permafrost site location training data for
northern Alberta (tabular data, tab-delimited format). Alberta Energy
Regulator, AER/AGS Digital Data 2018-0006.
http://ags.aer.ca/document/DIG/DIG_2018_0006.zip
'''
processing_assumptions = [
  "The source training table is joined to a Source-to-Year lookup table to construct a date field.",
  "Coordinates are transformed from Alberta 10TM NAD83 coordinates into WGS84 using a custom PROJ pipeline.",
  "Perm is mapped to pf_observed and Perm_cm to pf_depth, while thaw_depth is left missing and method is set to assorted.",
  "All rows are assigned one site_id value of N_Alberta rather than preserving individual source identifiers.",
]
temporal_handling = [
  "date is currently populated from the joined Year field rather than a full observation date.",
]
spatial_handling = [
  "The script transforms only rows within a plausible Alberta 10TM coordinate range and leaves invalid transformations as missing coordinates.",
]
manual_steps = []
known_limitations = [
  "The source table does not provide a full per-observation date, and the current workflow relies on a joined Source-to-Year lookup instead.",
  "Many rows still lack a resolved Year after the current Source-to-Year join, so inclusion requires either a more complete year crosswalk or an explicit policy for dropping undated rows and assigning representative dates.",
  "The current script reads the main input file twice, and the second read uses a cwd-relative path that makes the workflow fragile outside the source directory.",
  "This source is currently deferred pending an inclusion audit and cleanup of the processing workflow.",
]
external_dependencies = []
notes = ""
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pyproj import Transformer
import os
from pyproj import CRS, Transformer
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Pawley_2018'

df = pd.read_csv(_ROOT_DIR / "data" / source /"DIG_2018_0006_permafrost_training_data.txt",  sep='\t')
dates = pd.read_csv(_ROOT_DIR / "data" / source /"unique_source_values.csv")

# 0) Read: this file is TAB-delimited per the metadata
df = pd.read_csv("DIG_2018_0006_permafrost_training_data.txt", sep="\t", dtype=str, engine="python")

# 1) Build the transformer once (module-level or before the loop)
PIPE = (
    "+proj=pipeline "
    "+step +inv +proj=tmerc +lat_0=0 +lon_0=-115 +k=0.9992 +x_0=500000 +y_0=0 "
    "+datum=NAD83 +units=m +no_defs "
    "+step +proj=longlat +datum=WGS84 +no_defs"
)
tx = Transformer.from_pipeline(PIPE)

# 2) Make sure your columns are numeric
df["E_10TM83"] = pd.to_numeric(df["E_10TM83"], errors="coerce")
df["N_10TM83"] = pd.to_numeric(df["N_10TM83"], errors="coerce")

# 3) Optional: restrict to plausible ranges from metadata to avoid garbage inputs
e_ok = df["E_10TM83"].between(191112, 807012, inclusive="both")
n_ok = df["N_10TM83"].between(6204062, 6658979, inclusive="both")
valid = df["E_10TM83"].notna() & df["N_10TM83"].notna() & e_ok & n_ok

# 4) Transform only valid rows
df["lon"] = np.nan
df["lat"] = np.nan
lon, lat = tx.transform(df.loc[valid, "E_10TM83"].to_numpy(),
                        df.loc[valid, "N_10TM83"].to_numpy())
df.loc[valid, "lon"] = lon
df.loc[valid, "lat"] = lat

# 5) Sanity check and handle any non-finite results
bad = ~np.isfinite(df["lat"]) | ~np.isfinite(df["lon"])
if bad.any():
    print("Non-finite results after transform (showing a few):")
    print(df.loc[bad, ["E_10TM83", "N_10TM83", "lon", "lat"]].head(5))
    # choose one:
    # df = df.loc[~bad].copy()
    # or: df[["lon","lat"]] = df[["lon","lat"]].where(~bad)



dates_renamed = dates.rename(columns={"Unique Source Values": "Source"})
df = df.merge(dates_renamed[["Source", "Year"]], on="Source", how="left")
df["date"] = df["Year"]
df["date"] = df["date"].replace("", np.nan)
df['lat'] = lat
df['lon'] = lon
df = df.drop(columns=["Year", "E_10TM83", "N_10TM83", "Dataset_Source","Source"])


#remane columns
df.rename(columns={"Perm": "pf_observed",
                   "Perm_cm":"pf_depth",
                   }, inplace=True)

df['method'] = 'assorted'
df['obs_limit']= np.nan
df['thaw_depth']= np.nan
df["source"] = source
df['site_id'] = 'N_Alberta'


# SAVE CLEANED CSV
# -----------------------------------------------------
data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
