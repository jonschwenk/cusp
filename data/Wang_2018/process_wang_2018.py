"""
metadata_schema_version = 1
source_key = "Wang_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Joel Rowland"
last_substantive_update = "2026-05-19"
source_dataset = '''
Kang Wang, Irina Overeem, Elchin Jafarov, Gary Clow, Vladimir Romanovsky,
Kevin Schaefer, Frank Urban, William Cable, Mark Piper, Christopher Schwalm,
Tingjun Zhang, Alexander Kholodov, Pamela Sousanes, Michael Loso,
David Swanson, and Kenneth Hill. (2018). A synthesis dataset of near-surface
permafrost conditions for Alaska, 1997-2016. Arctic Data Center.
doi:10.18739/A24X54G8D.
'''
processing_assumptions = [
  "The annual thaw-depth estimate for each site is taken from the deepest positive soil-temperature depth observed in that year.",
  "If no deeper negative temperature is observed below the deepest thawed depth, the row is treated as pf_observed = 0; if a deeper negative temperature exists, pf_observed = 1 and pf_depth is set to the thaw depth.",
  "Rows are skipped when the logic cannot evaluate deeper temperatures because required deeper sensors are missing.",
]
temporal_handling = [
  "Month abbreviations are mapped to integers and each annual record is assigned a mid-month date with day = 15.",
]
spatial_handling = [
  "Lat and Lon are read directly from the source synthesis dataset.",
]
manual_steps = []
known_limitations = [
  "Depth resolution is limited to the available 25 cm sensor spacing.",
  "Years with incomplete deeper temperature coverage can be skipped entirely.",
  "Some Wang_2018 station-years spatially overlap with CALM/GTN-P annual ALT records, but the Wang publication and metadata describe PF-AK as a synthesis from GI-UAF, USGS, and NPS monitoring networks rather than as a CALM-derived table. CUSP therefore treats Wang_2018 as an independent source pending explicit station-year deduplication review.",
]
external_dependencies = []
notes = ""
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Wang_2018'

# Load the CSV file
df = pd.read_csv(_ROOT_DIR / "data" / source /"PF_AK_v0.1.csv")


# Replace -9999 with NaN
df.replace(-9999, np.nan, inplace=True)

# Convert month names to numbers
month_map = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}
df['Month'] = df['Month'].map(month_map)

# Define temperature columns by depth
depth_columns = {
    25: 'Ts25cm',
    50: 'Ts50cm',
    75: 'Ts75cm',
    100: 'Ts100cm'
}

# Process one row per site-year using best thaw depth across available data
output_records = []

for (site, year), group in df.groupby(['Name', 'Year']):
    site_rows = df[df['Name'] == site]
    site_depths = [
        depth for depth, col in depth_columns.items()
        if not site_rows[col].isna().all()
    ]
    obs_limit = max(site_depths) if site_depths else np.nan

    best_thaw_depth = -1
    best_row_result = None

    for _, row in group.iterrows():
        lon = row['Lon']
        lat = row['Lat']
        site_id = site
        source = 'Wang_2018'
        method = 'temp'
        month = row['Month']
        date = f"{int(year)}-{int(month):02d}-15"

        temps = {depth: row[col] for depth, col in depth_columns.items()}
        valid_depths = [d for d in temps if not np.isnan(temps[d])]
        if not valid_depths:
            continue

        thaw_depth = max((d for d in temps if temps[d] > 0), default=None)
        if thaw_depth is None:
            continue

        if thaw_depth == 100:
            pf_observed = 0
            pf_depth = np.nan
        else:
            deeper_depths = sorted([d for d in depth_columns if d > thaw_depth])
            skip = False
            for deeper in deeper_depths:
                deeper_temp = temps.get(deeper, np.nan)
                if np.isnan(deeper_temp):
                    skip = True
                    break
                if deeper_temp < 0:
                    pf_observed = 1
                    pf_depth = thaw_depth
                    break
            else:
                pf_observed = 0
                pf_depth = np.nan
            if skip:
                continue

        if thaw_depth > best_thaw_depth:
            best_thaw_depth = thaw_depth
            best_row_result = {
                'site_id': site_id,
                'date': date,
                'lon': lon,
                'lat': lat,
                'source': source,
                'method': method,
                'obs_limit': obs_limit,
                'thaw_depth': thaw_depth,
                'pf_depth': pf_depth,
                'pf_observed': pf_observed
            }

    if best_row_result:
        output_records.append(best_row_result)

# Convert to DataFrame and save if needed
output_df = pd.DataFrame(output_records)

data_utils.check_columns(output_df)

output_df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
