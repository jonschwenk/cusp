
"""
metadata_schema_version = 1
source_key = "Petrone_etal_2016"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Petrone, Johannes; Sohlenius, Gustav; Johansson, Emma; Lindborg, Tobias;
Näslund, Jens-Ove; Strömgren, Mårten; Brydsten, Lars. 2016. Using
ground-penetrating radar, topography and classification of vegetation to model
the sediment and active layer thickness in a periglacial lake catchment,
Western Greenland. PANGAEA. Supplement to Earth System Science Data 8(2),
663-677. https://doi.org/10.1594/PANGAEA.845258
'''
processing_assumptions = [
  "All processed observations are treated as permafrost-present records, so pf_observed is fixed to 1.",
  "The GPR workbook is assumed to already contain thaw-depth values converted from return times using the class-specific values described in Petrone et al. 2016.",
  "GPR transects are labeled GPRT* and thaw-probe transects are labeled PT* based on sheet names.",
]
temporal_handling = [
  "All GPR observations are assigned the single campaign date 2011-08-18.",
  "Probe-transect dates are parsed from the workbook when a date column is available.",
]
spatial_handling = [
  "Coordinates are read directly from the source workbooks without reprojection.",
]
manual_steps = []
known_limitations = [
  "The processed output does not include non-permafrost observations, so absence conditions are not represented directly.",
  "obs_limit is left missing because the workbooks do not provide a consistent usable observation-limit field.",
]
external_dependencies = []
notes = ""
"""


#!/usr/bin/env python3
import re
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import os

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

# Define path to read in data
source = 'Petrone_etal_2016' 
# Construct paths relative to your project root
gpr_file = _ROOT_DIR / "data" / source / "GPR/GPR_profiles_with_depths_by_class.xlsx"
probe_file = _ROOT_DIR / "data" / source / "Probe_transects/Probe_transects.xlsx"
out_file = _ROOT_DIR / "data" / source / "processed_petrone_etal_2016.csv"

def extract_number(text):
    m = re.findall(r"\d+", str(text))
    return int(m[0]) if m else None

def find_col(df, candidates):
    lower_map = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        k = cand.lower().strip()
        if k in lower_map:
            return lower_map[k]
    for c in df.columns:
        cl = c.lower().strip()
        for cand in candidates:
            if cand.lower().strip() in cl:
                return c
    return None

def build_csv(gpr_xlsx, probe_xlsx, out_csv):
    gpr_xls = pd.ExcelFile(gpr_xlsx)
    probe_xls = pd.ExcelFile(probe_xlsx)

    rows = []

    # GPR
    gpr_date = pd.to_datetime("2011-08-18")
    for sheet in gpr_xls.sheet_names:
        if sheet.upper().startswith("SUMMARY") or sheet.upper().startswith("VEG_"):
            continue
        df = gpr_xls.parse(sheet)
        lat_col = find_col(df, ["Latitude", "lat"])
        lon_col = find_col(df, ["Longitude", "lon"])
        depth_col = find_col(df, ["Depth_m", "depth (m)"])
        if lat_col is None or lon_col is None or depth_col is None:
            continue
        num = extract_number(sheet)
        site_id = f"GPRT{num}" if num is not None else f"GPRT_{sheet}"
        out = pd.DataFrame({
            "site_id": site_id,
            "date": gpr_date,
            "lat": df[lat_col],
            "lon": df[lon_col],
            "thaw_depth": (df[depth_col] * 100.0),
            "pf_observed": 1,
            "pf_depth": (df[depth_col] * 100.0),
            "obs_limit": np.nan,
            "method": "gp"
        })
        rows.append(out)

    # Probe
    for sheet in probe_xls.sheet_names:
        df = probe_xls.parse(sheet)
        lat_col = find_col(df, ["Latitude", "lat"])
        lon_col = find_col(df, ["Longitude", "lon"])
        depth_col = find_col(df, ["Active Layer Depth [m]", "Active Layer Depth (m)", "ALT (m)", "ALT_m", "Active Layer (m)"])
        date_col = find_col(df, ["Date", "date", "Observation Date", "Obs Date"])
        if lat_col is None or lon_col is None or depth_col is None:
            continue
        num = extract_number(sheet)
        site_id = f"PT{num}" if num is not None else f"PT_{sheet}"
        dates = pd.to_datetime(df[date_col], errors="coerce") if date_col is not None else pd.NaT
        out = pd.DataFrame({
            "site_id": site_id,
            "date": dates,
            "lat": df[lat_col],
            "lon": df[lon_col],
            "thaw_depth": (df[depth_col] * 100.0),
            "pf_observed": 1,
            "pf_depth": (df[depth_col] * 100.0),
            "obs_limit": np.nan,
            "method": "tp"
        })
        rows.append(out)

    combined = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["site_id","date","lat","lon","thaw_depth","pf_observed","pf_depth","obs_limit","method"])
    combined = combined.dropna(subset=["lat","lon","thaw_depth"]).reset_index(drop=True)
    combined['source'] = source
    
    data_utils.check_columns(combined)
    
    combined.to_csv(out_csv, index=False)

if __name__ == "__main__":
    build_csv(gpr_file, probe_file, out_file)
    print(f"CSV written to {out_file}")
