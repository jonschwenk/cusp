#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Ruess_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Ruess, Roger; Hollingsworth, Teresa Nettleton; Bonanza Creek LTER. 2025.
Bonanza Creek LTER: Active Layer Depth or Permafrost Presence for the Regional
Site Network. LTER Network Member Node.
https://pasta.lternet.edu/package/metadata/eml/knb-lter-bnz/605/6
doi:10.6073/pasta/10324bd31b26ef97fe2cfe6a8537d941
'''
processing_assumptions = [
  "Records are grouped by site and calendar year before summary statistics are computed.",
  "Permafrost presence requires at least one valid source Hit Type = Ice measurement; thaw_depth and pf_depth are the mean of Ice depths only.",
  "Permafrost absence requires at least one valid no-barrier probe depth (blank/None Hit Type) and no Ice hits; obs_limit is the minimum full probe depth in that site-year group.",
  "Rock-only, unvisited, inaccessible, snow-obstructed, and otherwise missing site-year groups are excluded because they do not directly establish permafrost absence.",
  "method is set to tp for all retained rows.",
]
temporal_handling = [
  "A single source date is preserved when all measurements in a site-year share it; otherwise the median source date is used and flagged as assigned/approximate.",
]
spatial_handling = [
  "Latitude and longitude are taken directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "Annual aggregation discards within-year measurement timing and variation.",
  "The released table's blank Hit Type is interpreted as the metadata code for no barrier only when accompanied by a valid measured depth; this interpretation is guarded by expected absence counts.",
  "Four absence summaries also contain rock refusals at other within-site probe locations and are flagged accordingly.",
]
external_dependencies = []
notes = ""
"""

import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR

source = "Ruess_2025"

df = pd.read_csv(
    _ROOT_DIR / "data" / source / "605_RSN_ActiveLayerDepths_2024_with_coords.csv"
)

df.columns = df.columns.str.strip()
df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
df["hit_type_normalized"] = df["Hit Type"].astype("string").str.strip().str.lower()

results = []
excluded_groups = []
grouped = df.groupby(["site", "Year"])

for (site, year), group in grouped:
    valid = group.loc[group["depth"].notna() & group["depth"].ne(-9999)].copy()
    ice = valid.loc[valid["hit_type_normalized"].eq("ice")]
    rock = valid.loc[valid["hit_type_normalized"].eq("rock")]
    no_barrier = valid.loc[
        valid["hit_type_normalized"].isna()
        | valid["hit_type_normalized"].isin(["none", "no barrier"])
    ]

    if not ice.empty:
        pf_observed = 1
        thaw_depth = float(ice["depth"].mean())
        pf_depth = thaw_depth
        obs_limit = np.nan
        native_count = len(ice)
    elif not no_barrier.empty:
        pf_observed = 0
        thaw_depth = np.nan
        pf_depth = np.nan
        obs_limit = float(no_barrier["depth"].min())
        native_count = len(no_barrier)
    else:
        excluded_groups.append((site, int(year)))
        continue

    dates = group["date"].dropna().sort_values()
    if dates.empty:
        raise ValueError(f"Ruess group {site}/{year} has no usable source date.")
    representative_date = dates.iloc[len(dates) // 2]
    date_is_summary = dates.nunique() > 1

    lat_values = group["latitude"].dropna()
    lon_values = group["longitude"].dropna()
    lat = lat_values.iloc[0] if not lat_values.empty else np.nan
    lon = lon_values.iloc[0] if not lon_values.empty else np.nan

    results.append({
        "site_id": site,
        "date": representative_date.strftime("%Y-%m-%d"),
        "lat": float(lat) if pd.notna(lat) else np.nan,
        "lon": float(lon) if pd.notna(lon) else np.nan,
        "thaw_depth": thaw_depth,
        "pf_observed": pf_observed,
        "pf_depth": pf_depth,
        "method": "tp",
        "obs_limit": obs_limit,
        "source": source,
        "ruess_native_count": native_count,
        "ruess_ice_count": len(ice),
        "ruess_no_barrier_count": len(no_barrier),
        "ruess_rock_count": len(rock),
        "ruess_source_row_count": len(group),
        "quality_flag_summary_statistic": native_count > 1,
        "quality_flag_coord_site_level": True,
        "quality_flag_date_assigned": date_is_summary,
        "quality_flag_date_source_approximate": date_is_summary,
        "quality_flag_refusal_or_obstruction_note": not rock.empty,
    })

final_df = pd.DataFrame(results)
if int(final_df["pf_observed"].eq(0).sum()) != 4:
    raise ValueError(
        "Expected four directly supported Ruess absence site-years; source contents may have changed."
    )
print(
    f"Excluded {len(excluded_groups)} Ruess site-year groups without a direct Ice hit "
    "or a measured no-barrier depth."
)

data_utils.check_columns(final_df)
final_df.to_csv(
    _ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv",
    index=False,
    float_format="%.15g",
)
