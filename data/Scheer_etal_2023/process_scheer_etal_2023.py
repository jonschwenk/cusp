#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Scheer_etal_2023"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
Scheer, Johanna; Caduff, Rafael; How, Penelope; Marcer, Marco; Strozzi,
Tazio; Bartsch, Annett; Ingeman-Nielsen, Thomas. 2024. Mapping the frost
susceptibility of the ground from thaw-season InSAR surface displacements and
extrapolated active layer thicknesses, Ilulissat, West-Greenland [dataset].
PANGAEA. https://doi.org/10.1594/PANGAEA.964306
'''
processing_assumptions = [
  "The source table is expanded from wide ALT_2020 and ALT_2021 columns into one row per site-year with non-null thaw depth.",
  "All retained observations are treated as permafrost-present, so pf_observed is fixed to 1 and pf_depth is set equal to thaw_depth.",
  "method is set to tp and obs_limit is left missing.",
]
temporal_handling = [
  "Each annual record is assigned September 1 because the source reports thaw-season observations without exact dates and the script uses early September as the end-of-summer proxy.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the source table without reprojection.",
]
manual_steps = []
known_limitations = [
  "Exact observation dates are not available in the processed output.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

# Define path to read in data
source = 'Scheer_etal_2023' 

def build_thaw_depth_table(in_path):
    df = pd.read_csv(in_path, sep="\t", dtype={"Site_ID": str}, na_values=["", " ", "NA", "NaN"])

    lat_col = "LATITUDE"
    lon_col = "LONGITUDE"
    alt_2020 = "ALT_2020 [cm]"
    alt_2021 = "ALT_2021 [cm]"

    records = []
    for _, row in df.iterrows():
        for year, alt_col in [(2020, alt_2020), (2021, alt_2021)]:
            val = row.get(alt_col, np.nan)
            if pd.isna(val):
                continue
            try:
                thaw_depth = float(val)
            except (TypeError, ValueError):
                continue

            records.append({
                "site_id": row.get("Site_ID"),
                "date": f"{year}-09-01",
                "lat": row.get(lat_col),
                "lon": row.get(lon_col),
                "thaw_depth": thaw_depth,
                "pf_observed": 1,
                "pf_depth": thaw_depth,
                "obs_limit": np.nan,
                "method": "tp",
                "source": source
            })

    out = pd.DataFrame.from_records(records, columns=[
        "site_id","date","lat","lon","thaw_depth","pf_observed","pf_depth","obs_limit","method", "source"
    ])
    data_utils.check_columns(out)

   # write data to csv
   
    out.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
    return out

if __name__ == "__main__":
    in_path = Path(_ROOT_DIR / "data" / source /"ILU_ALT_measurements_Vegetation_surveys_2020-2021.txt")
    #out_path = Path("alt_thaw_depth_long.csv")
    build_thaw_depth_table(in_path)
