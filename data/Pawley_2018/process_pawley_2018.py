#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Pawley_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Annalise Khandelwal"
last_substantive_update = "2026-05-19"
source_dataset = '''
Pawley, S.M.; Utting, D.J. 2018. Permafrost site location training data for
northern Alberta (tabular data, tab-delimited format). Alberta Energy
Regulator, AER/AGS Digital Data 2018-0006.
http://ags.aer.ca/document/DIG/DIG_2018_0006.zip
'''
processing_assumptions = [
  "The source training table is joined to a Source-to-Year lookup table to construct a representative date field.",
  "Rows with no resolved Year after the Source-to-Year join are dropped because the observation year is not known.",
  "Resolved year-only dates are encoded as September 1 of that year, following the project convention for Northern Hemisphere thaw-season observations without a reported month or day.",
  "Coordinates are transformed from Alberta 10TM NAD83 coordinates into WGS84 using a custom PROJ pipeline.",
  "Perm is mapped to pf_observed and Perm_cm to pf_depth, while thaw_depth and obs_limit are left missing.",
  "The source reports permafrost presence/absence was established with soil probes, augers, hand-dug soil pits, or shallow coring equipment, but the exact method is not recoverable per row; method is therefore set to unknown.",
  "The source does not provide site IDs, so site_id is left missing rather than assigning synthetic identifiers.",
  "Original Source, Dataset_Source, and Alberta 10TM coordinate fields are retained as all-fields provenance columns.",
]
temporal_handling = [
  "date is derived from the joined Year field as YYYY-09-01.",
  "Rows without a resolved Year are excluded from the processed output.",
]
spatial_handling = [
  "The script transforms only rows within a plausible Alberta 10TM coordinate range and leaves invalid transformations as missing coordinates.",
]
manual_steps = []
known_limitations = [
  "The source table does not provide full per-observation dates; retained rows use a representative September 1 date derived from source-level year metadata.",
  "The exact per-row observation tool is not reported, so method is unknown even though the source-level methods are direct field observations.",
]
external_dependencies = []
notes = ""
"""

import numpy as np
import pandas as pd
from pyproj import Transformer

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Pawley_2018"
source_dir = _ROOT_DIR / "data" / source

df = pd.read_csv(
    source_dir / "DIG_2018_0006_permafrost_training_data.txt",
    sep="\t",
    dtype=str,
    engine="python",
)
dates = pd.read_csv(source_dir / "unique_source_values.csv")

# Build the Alberta 10TM NAD83 -> WGS84 transformer.
PIPE = (
    "+proj=pipeline "
    "+step +inv +proj=tmerc +lat_0=0 +lon_0=-115 +k=0.9992 +x_0=500000 +y_0=0 "
    "+datum=NAD83 +units=m +no_defs "
    "+step +proj=longlat +datum=WGS84 +no_defs"
)
tx = Transformer.from_pipeline(PIPE)

# Preserve source-specific provenance columns before normalizing names.
df["pawley_source"] = df["Source"]
df["pawley_dataset_source"] = df["Dataset_Source"]
df["pawley_e_10tm83"] = df["E_10TM83"]
df["pawley_n_10tm83"] = df["N_10TM83"]

df["E_10TM83"] = pd.to_numeric(df["E_10TM83"], errors="coerce")
df["N_10TM83"] = pd.to_numeric(df["N_10TM83"], errors="coerce")

# Restrict to plausible ranges from metadata to avoid invalid transformations.
e_ok = df["E_10TM83"].between(191112, 807012, inclusive="both")
n_ok = df["N_10TM83"].between(6204062, 6658979, inclusive="both")
valid = df["E_10TM83"].notna() & df["N_10TM83"].notna() & e_ok & n_ok

df["lon"] = np.nan
df["lat"] = np.nan
lon, lat = tx.transform(
    df.loc[valid, "E_10TM83"].to_numpy(),
    df.loc[valid, "N_10TM83"].to_numpy(),
)
df.loc[valid, "lon"] = lon
df.loc[valid, "lat"] = lat

bad = ~np.isfinite(df["lat"]) | ~np.isfinite(df["lon"])
if bad.any():
    print("Non-finite results after transform (showing a few):")
    print(df.loc[bad, ["E_10TM83", "N_10TM83", "lon", "lat"]].head(5))

dates_renamed = dates.rename(columns={"Unique Source Values": "Source"})
df = df.merge(dates_renamed[["Source", "Year"]], on="Source", how="left")

df["pawley_year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
df = df.loc[df["pawley_year"].notna()].copy()
df["date"] = df["pawley_year"].astype(str) + "-09-01"

df = df.drop(columns=["Year", "E_10TM83", "N_10TM83", "Dataset_Source", "Source"])

df.rename(
    columns={
        "Perm": "pf_observed",
        "Perm_cm": "pf_depth",
    },
    inplace=True,
)

df["pf_observed"] = pd.to_numeric(df["pf_observed"], errors="raise").astype(int)
df["pf_depth"] = pd.to_numeric(df["pf_depth"], errors="coerce")
df["method"] = "unknown"
df["source_method_summary"] = "soil_probes_augers_hand_dug_pits_or_shallow_coring"
df["obs_limit"] = np.nan
df["thaw_depth"] = np.nan
df["source"] = source
df["site_id"] = pd.NA


# SAVE CLEANED CSV
# -----------------------------------------------------
data_utils.check_columns(df)

df.to_csv(source_dir / f"processed_{source.lower()}.csv", index=False)
