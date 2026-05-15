#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Cable_2017"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jrowland"
last_substantive_update = "2026-04-10"
source_dataset = '''
William Cable & Vladimir Romanovsky. 2017. Network of Permafrost
Observatories in Western Alaska. Arctic Data Center.
doi:10.18739/A23N20D37
'''
processing_assumptions = [
  "Three borehole records and the network sampling table are harmonized into a single processed output.",
  "Within each site-year group, thaw_depth is set to the deepest profile depth for which all shallower temperature measurements are above 0 C.",
  "A special 3 cm thaw rule is applied: the 25 cm sensor must be present and the qualifying observation must occur after July 1 for that year.",
  "pf_observed is set to 0 if any observation within the annual group has all monitored temperatures above 0 C; otherwise it is set to 1.",
  "Organic thickness for network records is approximated by extracting the largest centimeter value mentioned in soilDescription.",
]
temporal_handling = [
  "Source dates are parsed from borehole and network files, then observations are aggregated to annual records.",
  "The output date for each annual record is the date associated with the deepest valid thaw observation in that year.",
]
spatial_handling = [
  "Borehole coordinates are supplied as fixed metadata in the script for Kugurak Cabin, Selawik Thaw Slump, and Selawik Village.",
  "Network coordinates are read directly from the source CSV without reprojection.",
]
manual_steps = []
known_limitations = [
  "The annualized output discards within-season temperature-profile detail.",
  "org_thick is only available where soilDescription contains a parseable centimeter value.",
]
external_dependencies = []
notes = ""
"""

import pandas as pd
import numpy as np
import re

import os
from pathlib import Path
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Cable_2017"

def parse_dates_with_formats(values, formats):
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    raw = values.astype("string").str.strip()
    for fmt in formats:
        mask = parsed.isna() & raw.notna()
        if not mask.any():
            break
        parsed.loc[mask] = pd.to_datetime(raw.loc[mask], format=fmt, errors='coerce')
    return parsed

def extract_year_and_datetime(df):
    df.columns = [col.strip() for col in df.columns]
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            df['Datetime'] = parse_dates_with_formats(df[col], ["%m/%d/%y", "%m/%d/%Y"])
            df['Year'] = df['Datetime'].dt.year
            return df
    return df

def get_depth_map(df, pattern):
    return {col: int(re.search(pattern, col).group(1)) for col in df.columns if re.search(pattern, col)}

def deepest_valid_thaw(group, depth_map):
    temp_cols_sorted = sorted(depth_map.items(), key=lambda x: x[1])
    valid_records = []
    for _, row in group.iterrows():
        for i in reversed(range(len(temp_cols_sorted))):
            col, depth = temp_cols_sorted[i]
            shallower = [c for c, _ in temp_cols_sorted[:i+1]]
            if all(pd.notna(row[c]) and row[c] > 0 for c in shallower):
                datetime_col = 'Datetime' if 'Datetime' in row else 'date'
                valid_records.append((depth, row[datetime_col]))
                break
    return max(valid_records, key=lambda x: x[0]) if valid_records else (0, None)

def process_boreholes(files, coords, ids):
    records = []
    for site, path in files.items():
        if "network" in site:
            continue
        df = pd.read_csv(_ROOT_DIR / "data" / source /path)
        df = extract_year_and_datetime(df)
        if 'Year' not in df.columns: continue
        temp_cols = [col for col in df.columns if re.search(r'(TP1|temp)', col, re.IGNORECASE) and re.search(r'\d+cm', col)]
        depth_map = get_depth_map(df[temp_cols], r'(\d+)cm')
        for year, group in df.groupby('Year'):
            max_depth, max_date = deepest_valid_thaw(group, depth_map)
            if max_depth > 0:
                # Apply new condition: if thaw depth is 3 and 25cm is not NaN, then date must be after July 1
                if max_depth == 3 and '25cm' in group.columns:
                    group_valid = group[(group['25cm'].notna()) & (group['Datetime'] > pd.Timestamp(f'{year}-07-01'))]
                    if group_valid.empty:
                        continue
                above_all = (group[temp_cols] > 0).all(axis=1).any()
                pf_observed = 0 if above_all else 1
                pf_depth = max_depth if pf_observed else None
                records.append({
                    'site_id': ids[site],
                    'Year': year,
                    'thaw_depth': max_depth,
                    'lat': coords[site][0],
                    'lon': coords[site][1],
                    'date': max_date,
                    'obs_limit': max(depth_map.values()),
                    'pf_observed': pf_observed,
                    'pf_depth': pf_depth
                })
    return pd.DataFrame(records)

def process_network(path):
    path = Path(path)
    if not path.is_absolute():
        path = _ROOT_DIR / "data" / source / path
    df = pd.read_csv(path)
    df['date'] = parse_dates_with_formats(df['date'], ["%d-%b-%y", "%d-%b-%Y"])
    df['Datetime'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date', 'latitude', 'longitude'])
    df['Year'] = df['date'].dt.year
    temp_cols = [col for col in df.columns if re.search(r'temp\d+cm', col)]
    depth_map = get_depth_map(df[temp_cols], r'temp(\d+)cm')
    records = []
    for (lat, lon, year), group in df.groupby(['latitude', 'longitude', 'Year']):
        max_depth, max_date = deepest_valid_thaw(group, depth_map)
        if max_depth > 0:
            # Apply new condition: if thaw depth is 3 and 25cm is not NaN, then date must be after July 1
            if max_depth == 3 and 'temp25cm' in group.columns:
                thaw_row = group[group['date'] == max_date]
                if (
                    thaw_row.empty or
                    thaw_row['temp25cm'].isna().any() or
                    thaw_row['date'].iloc[0] <= pd.Timestamp(f'{year}-07-01')
                ):
                    continue
            above_all = (group[temp_cols] > 0).all(axis=1).any()
            pf_observed = 0 if above_all else 1
            pf_depth = max_depth if pf_observed else None
            site_row = group.dropna(subset=['siteCode']).head(1)
            site_id = site_row['siteCode'].values[0] if not site_row.empty else None
            if not (max_depth == 3 and group[(group['date'] == max_date)]['temp25cm'].isna().any()):
                records.append({
                    'site_id': site_id,
                    'Year': year,
                    'thaw_depth': max_depth,
                    'lat': lat,
                    'lon': lon,
                    'date': max_date,
                    'obs_limit': max(depth_map.values()),
                    'pf_observed': pf_observed,
                    'pf_depth': pf_depth
                })
    return pd.DataFrame(records)

def extract_max_cm(description):
    matches = re.findall(r'(\d+)\s*cm', str(description))
    return max(map(int, matches)) if matches else None

if __name__ == "__main__":
    files = {
        "Kugurak_Cabin": "Kugurak_Cabin.csv",
        "Selawik_Thaw_Slump": "Selawik_Thaw_Slump.csv",
        "Selawik_Village": "Selawik_Village.csv",
        "network_sampling_sites": "network_sampling_sites.csv"
    }
    coords = {
        "Kugurak_Cabin": (66.562380, -159.004640),
        "Selawik_Thaw_Slump": (66.501157, -157.607440),
        "Selawik_Village": (66.605569, -160.019213)
    }
    ids = {
        "Kugurak_Cabin": "KC_bore",
        "Selawik_Thaw_Slump": "STS_bore",
        "Selawik_Village": "SV_bore"
    }

    bore_df = process_boreholes(files, coords, ids)
    net_df = process_network(files["network_sampling_sites"])
    combined = pd.concat([bore_df, net_df], ignore_index=True)

    # Enrich with soil description
    meta = pd.read_csv(_ROOT_DIR / "data" / source /files["network_sampling_sites"])
    meta = meta.dropna(subset=['soilDescription', 'latitude', 'longitude'])
    meta = meta[['latitude', 'longitude', 'soilDescription']].drop_duplicates()
    meta = meta.rename(columns={'latitude': 'lat', 'longitude': 'lon'})

    enriched = pd.merge(combined, meta, how='left', on=['lat', 'lon'])
    enriched['org_thick'] = enriched['soilDescription'].apply(extract_max_cm)
    enriched['method'] = 'temp'
    enriched['source'] = source
    enriched.drop(columns=['soilDescription', 'Year'], inplace=True)
    
    # Save to CSV
    data_utils.check_columns(enriched)

    enriched.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

