"""
metadata_schema_version = 1
source_key = "Ebel_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
source_dataset = '''
Ebel, B.A. 2018. Physical and hydraulic properties at recently burned and
long-unburned boreal forest areas in interior Alaska, USA. U.S. Geological
Survey data release. https://doi.org/10.5066/F7610Z7J
'''
processing_assumptions = [
  "pf_observed, thaw_depth, and obs_limit are carried directly from the revised source CSV.",
  "Coordinates are reconstructed from Easting/Northing using the per-row EPSG code and then exported in WGS84.",
  "pf_depth is left missing because the source table does not provide a separate permafrost-depth field.",
  "Rows matching Minsley_2017 within 30 m, one campaign day, permafrost state, and depth within 1 cm are removed in favor of the direct thaw-probe release.",
]
temporal_handling = [
  "Observation dates are preserved directly from the source CSV without additional aggregation.",
]
spatial_handling = [
  "Rows are split by EPSG:32605 and EPSG:32606 before reprojection to WGS84.",
]
manual_steps = []
known_limitations = [
  "Two nearby Ebel active-layer measurements differ materially from the nearest Minsley_2017 value and are retained as potentially independent soil-sampling-site observations.",
  "The overlap filter is guarded at nine rows so source revisions cannot silently change the result.",
  "method is exported as unknown because the revised source CSV does not include a reliable observation-tool field.",
]
external_dependencies = [
  "data/Minsley_2017/processed_minsley_2017.csv is required for source-specific overlap filtering.",
]
notes = ""
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import os
from scipy.spatial import cKDTree

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Ebel_2018'
df = pd.read_csv(_ROOT_DIR / "data" / source /"Table_1_Locations_revised_formatted.csv")
MINSLEY_PATH = (
    _ROOT_DIR / "data" / "Minsley_2017" / "processed_minsley_2017.csv"
)
EARTH_RADIUS_M = 6_371_008.8

def to_wgs84(frame, epsg):
    subset = df[df['epsg'] == epsg].copy()
    geometry = gpd.points_from_xy(x=subset['Easting (m)'], y=subset['Northing (m)'])
    gdf = gpd.GeoDataFrame(subset, geometry=geometry, crs=f"EPSG:{epsg}")
    return gdf.to_crs(epsg=4326)

gdf32605 = to_wgs84(df, 32605)
gdf32606 = to_wgs84(df, 32606)

gdf = pd.concat([gdf32605, gdf32606])
gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 
df = pd.DataFrame(gdf.drop(columns=['Easting (m)', 'Northing (m)', 'geometry', 'epsg']))

df['source'] = source
df['obs_depth'] = np.nan
df['pf_depth'] = np.nan
df['method'] = 'unknown'
df.loc[df['pf_observed'].eq(1), 'obs_limit'] = np.nan


def unit_sphere(frame):
    """Return Cartesian unit-sphere coordinates for WGS84 point matching."""

    lat = np.radians(pd.to_numeric(frame['lat'], errors='coerce').to_numpy())
    lon = np.radians(pd.to_numeric(frame['lon'], errors='coerce').to_numpy())
    return np.column_stack((
        np.cos(lat) * np.cos(lon),
        np.cos(lat) * np.sin(lon),
        np.sin(lat),
    ))


if not MINSLEY_PATH.exists():
    raise FileNotFoundError(f"{MINSLEY_PATH} is required for overlap filtering.")
minsley = pd.read_csv(MINSLEY_PATH, low_memory=False)
tree = cKDTree(unit_sphere(minsley))
chord_distance, nearest_index = tree.query(unit_sphere(df), k=1)
nearest = minsley.iloc[nearest_index].reset_index(drop=True)
distance_m = 2 * EARTH_RADIUS_M * np.arcsin(
    np.clip(chord_distance / 2, 0, 1)
)
ebel_depth = pd.to_numeric(df['thaw_depth'], errors='coerce').combine_first(
    pd.to_numeric(df['obs_limit'], errors='coerce')
).reset_index(drop=True)
minsley_depth = pd.to_numeric(
    nearest['thaw_depth'], errors='coerce'
).combine_first(pd.to_numeric(nearest['obs_limit'], errors='coerce'))
date_difference = (
    pd.to_datetime(df['date'], format='mixed', errors='coerce').reset_index(drop=True)
    - pd.to_datetime(nearest['date'], format='mixed', errors='coerce')
).abs()
same_campaign_day = date_difference.le(pd.Timedelta(days=1))
same_state = pd.to_numeric(
    df['pf_observed'], errors='coerce'
).reset_index(drop=True).eq(
    pd.to_numeric(nearest['pf_observed'], errors='coerce')
)
overlap = (
    (distance_m <= 30.0)
    & same_campaign_day.to_numpy()
    & same_state.to_numpy()
    & ebel_depth.sub(minsley_depth).abs().le(1.0).to_numpy()
)
overlap_count = int(overlap.sum())
if overlap_count != 9:
    raise ValueError(
        "Expected nine high-confidence Ebel/Minsley overlaps; "
        f"found {overlap_count}. Review the source files before proceeding."
    )
df = df.loc[~overlap].copy()

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
