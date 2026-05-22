#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Moore_et_al_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-20"
source_dataset = '''
Moore, M.A., K. Schaefer, L.K. Clayton, E.E. Hoy, M. Auclair,
K. Bakian-Dogaheh, M.J. Battaglia, K. Bennett, W.R. Bolton,
L.L. Bourgeau-Chavez, A.E. Bredder, D. Chen, R.H. Chen, A.C. Chen,
J. Chen, D. Chiasson, R. Chitra-tarak, A. Collins, L. Cornette,
J. Dann, E. Devoie, M. Dominico, T.A. Douglas, S. Gagnon, S.E. Grelick,
P. Griffith, J. He, G. Iwahana, E. Jafarov, L.K. Jenkins, E.S. Kasischke,
S. Kim, P.B. Kirchner, B. Lecavalier, J. Ledman, S. Liben, L. Liu,
T.V. Loboda, S. Ludwig, M.J. Macander, N. Matsui, R.J. Michaelides,
M. Moghaddam, S. Natali, S.K. Panda, A.D. Parsekian, M. Pearce,
W. Quinton, A.V. Rocha, H. Rodenhizer, P. Roy-Leveillee, N. Saravanan,
Z. Sauve, S.R. Schaefer, E.A.G. Schuur, O. Sonnentag, T.D. Sullivan,
A. Tabatabaeenejad, L. Thomas, B. Thorne, K. Turner, K. Wang, C.J. Wilson,
H.A. Zebker, T. Zhang, Y. Zhao, and S. Zwieback. 2025.
ABoVE: Soil Moisture and Active Layer Thickness in Alaska, USA and Canada,
2005-2022. ORNL DAAC, Oak Ridge, Tennessee, USA.
https://doi.org/10.3334/ORNLDAAC/2369
'''
processing_assumptions = [
  "ALT == -9999 and rows with missing lat/lon are dropped before aggregation.",
  "Duplicate rows at the same site_name/latitude/longitude/date are averaged for ALT.",
  "Near-surface permafrost is inferred from thaw depth using a July 15 cutoff: ALT < 130 cm after July 15 implies pf_observed = 1 and pf_depth = ALT; ALT > 130 cm after July 15 implies pf_observed = 0.",
  "Rows that remain unresolved after the July 15 inference step are dropped rather than exported with missing pf_observed.",
  "method is inferred from ALT_instrument and mapped to tp or gp when the group is internally consistent; otherwise method is set to unknown.",
]
temporal_handling = [
  "Per-record dates are parsed from the input CSV and kept at the observation level.",
  "The July 15 threshold is applied separately within each year.",
]
spatial_handling = [
  "Coordinates are used as provided in the source CSV without reprojection.",
]
manual_steps = [
  "Download ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv into data/Moore_et_al_2025 before running the script.",
]
known_limitations = [
  "The source file does not provide explicit probe lengths or direct permafrost presence/absence labels, so pf_observed and pf_depth are inferred.",
  "obs_limit remains unreported because the input file does not provide a usable observation-limit field.",
  "CALM overlap review found spatial/site-year overlap with CALM but no exact coordinate/date/depth duplicate rows; source documentation indicates ABoVE/SMALT field observations, so Moore_et_al_2025 is treated as independent for now.",
]
external_dependencies = [
  "Gitignored raw input ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv hosted outside the repo; see EXTERNAL_DATA_SOURCES.md.",
]
notes = ""
"""

import argparse
import sys
import pandas as pd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils
from scipy import stats

source = 'Moore_et_al_2025'

# <<< EDIT THESE TWO LINES >>>
INPUT_FILE = _ROOT_DIR / "data" / source /"ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv"
#OUTPUT_FILE = _ROOT_DIR / "data" / source /r"processed_{}.csv"

def coerce_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.date

def method_from_instruments(group: pd.DataFrame):
    if "ALT_instrument" not in group.columns:
        return "unknown"
    vals = (
        group["ALT_instrument"]
        .astype("string")
        .str.strip()
        .str.lower()
        .replace({"nan": None, "na": None, "": None})
        .dropna()
        .unique()
        .tolist()
    )
    if len(vals) == 1:
        inst = vals[0]
        if inst in {"probe", "thermal probe", "thaw probe"}:
            return "tp"
        if inst in {"gpr", "ground penetrating radar"}:
            return "gp"
        return "unknown"
    return "unknown"

def map_instrument_series_to_method(s: pd.Series):
    vals = (
        s.astype("string").str.strip().str.lower()
         .replace({"nan": None, "na": None, "": None})
         .dropna().unique().tolist()
    )
    if len(vals) == 1:
        v = vals[0]
        if v == "probe":
            return "tp"
        if v == "gpr":
            return "gp"
        return "unknown"
    return "unknown"

def main():
    df = pd.read_csv(INPUT_FILE, low_memory=False)

    # Drop invalid ALT
    df = df[df["ALT"] != -9999]
    #drop missing lat and lon
    df = df[df["latitude"] != -9999]
    df = df[df["longitude"] != -9999]
    

    # Parse dates
    df["_date"] = coerce_date(df["date"])
    df = df.dropna(subset=["_date"])

       

    # keys should already be defined as:
    keys = ["site_name", "latitude", "longitude", "_date"]
    
    # Average ALT per group (keep whatever you already have if identical)
    alt_mean = (
        df.groupby(keys, dropna=False, as_index=False)["ALT"]
          .mean()
          .rename(columns={"ALT": "_thaw_depth"})
    )

    # Derive _method using groupby.agg (stable across pandas versions)
    if "ALT_instrument" in df.columns:
        method_df = (
            df.groupby(keys, dropna=False)
              .agg(_method=("ALT_instrument", map_instrument_series_to_method))
              .reset_index()
        )
    else:
        # If column truly missing, ensure _method exists so downstream never KeyErrors
        method_df = alt_mean[keys].copy()
        method_df["_method"] = pd.NA
    
    # Add team_name if unique within group
    
    
    # Left-join guarantees `_method` exists on `result`
    result = alt_mean.merge(method_df, on=keys, how="left")
    team_tag = (
        df.groupby(keys, dropna=False)
          .agg(team_nunique=("team_name", "nunique"), team_first=("team_name", "first"))
          .reset_index()
    )
    
    team_tag["team_name_out"] = np.where(
        team_tag["team_nunique"] == 1,
        team_tag["team_first"],
        pd.NA  # or "mixed" if you prefer
    )
    
    # Merge into result
    result = result.merge(
        team_tag[keys + ["team_name_out"]],
        on=keys, how="left"
    )

    # Build output
    site_part = result["site_name"].astype(str)
    team_part = result["team_name_out"].fillna("").astype(str)  # avoids "_<NA>" in IDs
    site_id = site_part.where(team_part.eq(""), site_part + "_" + team_part)
    out = pd.DataFrame({
        "site_id": site_id,
        "date": result["_date"].astype("string"),
        "lat": result["latitude"],
        "lon": result["longitude"],
        "thaw_depth": result["_thaw_depth"],
    })

    # July 15 logic
    out["obs_limit"] = pd.NA
    dates = pd.to_datetime(out["date"], errors="coerce")
    years = dates.dt.year.astype("Int64")
    july15 = pd.to_datetime(years.astype("string") + "-07-15", errors="coerce")

    later_than = dates > july15
    alt = out["thaw_depth"]

    pf_observed = pd.Series(pd.array([pd.NA] * len(out), dtype="Int64"))
    pf_depth = pd.Series(pd.array([pd.NA] * len(out), dtype="Float64"))

    # ALT < 130 and later → pf_observed=1, pf_depth=ALT
    maskA = (alt < 130) & later_than
    pf_observed[maskA] = 1
    pf_depth[maskA] = alt[maskA]

    # ALT > 130 and later → pf_observed=0
    maskC = (alt > 130) & later_than
    pf_observed[maskC] = 0

    out["pf_observed"] = pf_observed.astype("Int64")
    out["pf_depth"] = pf_depth
    out["method"] = result["_method"]
    out['source'] = source
    out = out.dropna(subset=["pf_observed"]).copy()

    # Final column order
    out = out[["site_id", "date", "lat", "lon", "thaw_depth",
               "pf_observed", "pf_depth", "obs_limit", "method", "source"]]
    
    data_utils.check_columns(out)

    out.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
   

if __name__ == "__main__":
    main()
