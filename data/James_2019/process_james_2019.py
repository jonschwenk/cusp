"""
metadata_schema_version = 1
source_key = "James_2019"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
James, S.R.; Minsley, B.J.; Waldrop, M.P.; McFarland, J.W.; Manies, K.L.;
Pastick, N.J. 2021. Permafrost characterization at the Alaska Peatland
Experiment (APEX): Geophysical and related field data collected from 2018-2020.
U.S. Geological Survey data release. https://doi.org/10.5066/P90M04ST
'''
processing_assumptions = [
  "Dates are parsed from YYYYMMDD strings and retained per observation.",
  "Ordinary numeric thaw depths are direct frost-probe detections and are copied to pf_depth with pf_observed = 1.",
  "The documented sentinel 999 means no detection with the 250 cm frost probe; those rows have pf_observed = 0, obs_limit = 250 cm, and empty thaw/pf depths.",
  "Repeated probes sharing an instrument/electrode coordinate, date, and state are averaged because the source reports that individual measurements were taken within 1 m of the published support coordinate.",
  "method is set to tp for all retained rows because the source documentation describes frost-probe measurements.",
]
temporal_handling = [
  "Original per-observation dates are preserved after parsing from the source CSV.",
  "No annual maximum or date interpolation is applied; every retained row keeps its source observation date.",
]
spatial_handling = [
  "Latitude and longitude are carried directly from the source CSV without reprojection.",
  "Published coordinates represent the adjacent seismometer, NMR borehole, or ERT electrode; coordinate-level summaries retain native counts and receive coord_site_level flags.",
]
manual_steps = []
known_limitations = []
external_dependencies = []
notes = ""
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'James_2019'
df = pd.read_csv(_ROOT_DIR / "data" / source / "APEX_2018_2019_ThawDepth_Data.csv".format(source))

df.rename(columns={'Date' : 'date',
                    'Lon_WGS84' : 'lon',
                    'Lat_WGS84' : 'lat',
                    'SiteID':'site_id',
                    'ThawDep_cm' : 'thaw_depth'},
                   inplace=True)
df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d').dt.strftime('%Y-%m-%d')
df['james_thaw_depth_raw'] = pd.to_numeric(df['thaw_depth'], errors='coerce')
no_detection = df['james_thaw_depth_raw'].eq(999)
if int(no_detection.sum()) != 12:
    raise ValueError(f"Expected 12 James 2019 no-detection sentinels; found {int(no_detection.sum())}.")

df['thaw_depth'] = df['james_thaw_depth_raw'].mask(no_detection)
df['pf_depth'] = df['thaw_depth']
df['pf_observed'] = np.where(no_detection, 0, 1)
df['obs_limit'] = np.where(no_detection, 250.0, np.nan)
df['method'] = 'tp'
df['source'] = source
df['quality_flag_source_unit_or_code_recoded'] = no_detection
df['james_adjacency'] = df['Adjacency'].astype('string').fillna('unspecified')
df['site_id'] = (
    df['site_id'].astype(str)
    + '_'
    + df['james_adjacency'].str.replace(r'[^A-Za-z0-9]+', '_', regex=True).str.strip('_')
)

group_columns = [
    'site_id', 'james_adjacency', 'date', 'lat', 'lon',
    'pf_observed', 'obs_limit', 'method', 'source',
]
df = (
    df.groupby(group_columns, as_index=False, dropna=False)
    .agg(
        thaw_depth=('thaw_depth', 'mean'),
        pf_depth=('pf_depth', 'mean'),
        james_reported_depth_min_cm=('james_thaw_depth_raw', 'min'),
        james_reported_depth_max_cm=('james_thaw_depth_raw', 'max'),
        james_native_count=('james_thaw_depth_raw', 'size'),
        quality_flag_source_unit_or_code_recoded=('quality_flag_source_unit_or_code_recoded', 'max'),
    )
)
if int(df['james_native_count'].sum()) != 578:
    raise ValueError("James 2019 coordinate aggregation lost source observations.")
df['quality_flag_summary_statistic'] = df['james_native_count'].gt(1)
df['quality_flag_coord_site_level'] = True

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
