""" Utilities to work with export/import new datasources
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString
import os
import re
from typing import List, Dict # exploring this?
from pandas.api.types import is_integer_dtype

from pathlib import Path
import cusp
_ROOT_DIR = Path(next(iter(cusp.__path__))).parent 
QUALITY_FLAG_PREFIX = "quality_flag_"
DEFAULT_GPR_AGGREGATION_SPACING_M = 5.0


def add_quality_flag(df, flag, mask=None):
    """Mark rows with a CUSP observation-quality flag indicator column.

    Processors can call this repeatedly; the build step validates flag names
    against data/quality_flag_definitions.csv and emits compact mnemonic
    codes in the release `quality_flags` column.
    """

    column = f"{QUALITY_FLAG_PREFIX}{flag}"
    if column not in df.columns:
        df[column] = False
    if mask is None:
        df[column] = True
    else:
        df.loc[mask, column] = True
    return df


def aggregate_gpr_points(
    df: pd.DataFrame,
    group_columns: List[str] | None = None,
    value_columns: List[str] | None = None,
    spacing_m: float = DEFAULT_GPR_AGGREGATION_SPACING_M,
    native_count_column: str | None = None,
) -> pd.DataFrame:
    """Aggregate dense GPR picks into occupied metric grid cells.

    CUSP's default dense-GPR representation is one mean observation per
    occupied 5 m by 5 m cell within a survey unit. ``group_columns`` must
    distinguish surveys that may overlap in space, especially different
    sites, dates, or thaw years. Geographic coordinates are projected to a
    local UTM CRS separately for each survey unit before cells are assigned.

    Numeric observation fields in ``value_columns`` and coordinates are
    averaged within each cell. Other fields must be constant within a cell;
    quality-flag indicator columns are combined with logical OR. The output
    records the number of native measurements represented by each row and
    marks cells containing more than one measurement as summary statistics.

    Args:
        df: Point observations containing ``lat`` and ``lon``.
        group_columns: Columns defining an independent survey. Defaults to
            ``["site_id", "date"]``.
        value_columns: Numeric measurement columns to average. Defaults to
            ``["thaw_depth"]``.
        spacing_m: Grid-cell width in meters. The CUSP default is 5 m.
        native_count_column: Optional input column containing counts from an
            earlier exact-coordinate aggregation. Counts are summed rather
            than treated as one measurement per input row.

    Returns:
        A dataframe with one row per occupied cell and the additional columns
        ``gpr_native_count`` and ``gpr_aggregation_spacing_m``.
    """

    if not np.isfinite(spacing_m) or spacing_m <= 0:
        raise ValueError("GPR aggregation spacing must be a positive finite number.")

    group_columns = group_columns or ["site_id", "date"]
    value_columns = value_columns or ["thaw_depth"]
    required = ["lat", "lon", *group_columns, *value_columns]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"GPR aggregation input is missing required columns: {missing}")
    if native_count_column is not None and native_count_column not in df.columns:
        raise ValueError(f"GPR native-count column is missing: {native_count_column}")
    if df.empty:
        out = df.copy()
        out["gpr_native_count"] = pd.Series(dtype="Int64")
        out["gpr_aggregation_spacing_m"] = pd.Series(dtype=float)
        out[f"{QUALITY_FLAG_PREFIX}summary_statistic"] = pd.Series(dtype=bool)
        return out

    working = df.copy().reset_index(drop=True)
    working["lat"] = pd.to_numeric(working["lat"], errors="coerce")
    working["lon"] = pd.to_numeric(working["lon"], errors="coerce")
    bad_coordinates = (
        working[["lat", "lon"]].isna().any(axis=1)
        | ~working["lat"].between(-90, 90)
        | ~working["lon"].between(-180, 180)
    )
    if bad_coordinates.any():
        raise ValueError(
            f"GPR aggregation requires valid coordinates; found {int(bad_coordinates.sum())} invalid rows."
        )

    working["_gpr_x"] = np.nan
    working["_gpr_y"] = np.nan
    transformer_cache: dict[int, Transformer] = {}
    grouped = working.groupby(group_columns, dropna=False, sort=False)
    for _, row_indices in grouped.groups.items():
        indices = np.asarray(list(row_indices), dtype=int)
        median_lon = float(working.loc[indices, "lon"].median())
        median_lat = float(working.loc[indices, "lat"].median())
        zone = int(np.clip(np.floor((median_lon + 180.0) / 6.0) + 1, 1, 60))
        epsg = (32600 if median_lat >= 0 else 32700) + zone
        if epsg not in transformer_cache:
            transformer_cache[epsg] = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
        x, y = transformer_cache[epsg].transform(
            working.loc[indices, "lon"].tolist(),
            working.loc[indices, "lat"].tolist(),
        )
        working.loc[indices, "_gpr_x"] = x
        working.loc[indices, "_gpr_y"] = y

    working["_gpr_cell_x"] = np.floor(working["_gpr_x"] / spacing_m).astype("int64")
    working["_gpr_cell_y"] = np.floor(working["_gpr_y"] / spacing_m).astype("int64")
    working["_gpr_input_order"] = np.arange(len(working))
    if native_count_column is None:
        working["_gpr_native_count_input"] = 1
    else:
        counts = pd.to_numeric(working[native_count_column], errors="coerce")
        if counts.isna().any() or (counts < 1).any():
            raise ValueError("GPR native counts must be positive numeric values.")
        working["_gpr_native_count_input"] = counts

    cell_columns = [*group_columns, "_gpr_cell_x", "_gpr_cell_y"]
    helper_columns = {
        "_gpr_x",
        "_gpr_y",
        "_gpr_cell_x",
        "_gpr_cell_y",
        "_gpr_input_order",
        "_gpr_native_count_input",
    }
    excluded = set(group_columns) | set(value_columns) | {"lat", "lon"} | helper_columns
    if native_count_column is not None:
        excluded.add(native_count_column)
    retained_columns = [column for column in working.columns if column not in excluded]
    flag_columns = [column for column in retained_columns if column.startswith(QUALITY_FLAG_PREFIX)]
    constant_columns = [column for column in retained_columns if column not in flag_columns]

    cell_groups = working.groupby(cell_columns, dropna=False, sort=False)
    for column in constant_columns:
        varying = cell_groups[column].nunique(dropna=True).gt(1)
        if varying.any():
            raise ValueError(
                f"GPR aggregation field '{column}' varies within {int(varying.sum())} occupied cells; "
                "add it to group_columns or aggregate it explicitly."
            )

    aggregations: dict[str, str] = {
        "lat": "mean",
        "lon": "mean",
        "_gpr_input_order": "min",
        "_gpr_native_count_input": "sum",
    }
    aggregations.update({column: "mean" for column in value_columns})
    aggregations.update({column: "first" for column in constant_columns})
    aggregations.update({column: "max" for column in flag_columns})
    out = cell_groups.agg(aggregations).reset_index()
    out = out.sort_values("_gpr_input_order", kind="mergesort").reset_index(drop=True)
    out["gpr_native_count"] = out.pop("_gpr_native_count_input").round().astype("Int64")
    out["gpr_aggregation_spacing_m"] = float(spacing_m)

    summary_flag = f"{QUALITY_FLAG_PREFIX}summary_statistic"
    if summary_flag not in out.columns:
        out[summary_flag] = False
    out[summary_flag] = out[summary_flag].fillna(False).astype(bool) | out["gpr_native_count"].gt(1)

    drop_columns = ["_gpr_cell_x", "_gpr_cell_y", "_gpr_input_order"]
    out = out.drop(columns=drop_columns)
    original_columns = [column for column in df.columns if column != native_count_column]
    output_columns = [
        *original_columns,
        "gpr_native_count",
        "gpr_aggregation_spacing_m",
        summary_flag,
    ]
    return out.loc[:, list(dict.fromkeys(output_columns))]

def process_pf_observations(
    working_df,
    alt_name,
    obs_limit_val=None,
    obs_limit_mask=None,
    date=None,
):
    """Normalize exact and lower-bound thaw-depth observations.

    Args:
        working_df (pd.DataFrame): Contains permafrost observations, possibly coordinates/location, date, and obs_limit information
        alt_name (string): Column name of Active Layer Thickness in cm.
        obs_limit_val (numeric or array-like, optional): Positive observation
            depth for explicitly censored/no-hit rows. Defaults to None.
        obs_limit_mask (pd.Series or np.array, optional): Boolean mask for
            explicitly censored/no-hit rows. Defaults to None.
        date (str or np.array, optional): Date of obs if not already in working_df. Defaults to None.

    Raises:
        ValueError: Error raised if passing only one of obs_limit_val or obs_limit_mask.
        ValueError: Error raised if no date information is provided

    Returns:
        pd.DataFrame: Formatted df
    """
    
    if (obs_limit_val is not None ) ^ (obs_limit_mask is not None):
        raise ValueError("If you pass an obs_limit_mask you need to specify an obs_limit_val (or vector)")
    
    # Add date column
    if date is not None:
        working_df['date'] = date
    
    if 'date' not in working_df.columns:
        raise ValueError("Missing date column or observation date")
    
    working_df.rename(columns={alt_name: "thaw_depth"}, inplace=True)
    working_df["thaw_depth"] = pd.to_numeric(
        working_df["thaw_depth"], errors="coerce"
    )
    working_df["pf_depth"] = working_df["thaw_depth"].copy()
    working_df["obs_limit"] = np.nan

    censored = pd.Series(False, index=working_df.index)
    if obs_limit_mask is not None:
        censored = pd.Series(obs_limit_mask, index=working_df.index).fillna(False).astype(bool)
        if np.isscalar(obs_limit_val):
            working_df.loc[censored, "obs_limit"] = obs_limit_val
        else:
            limits = pd.Series(obs_limit_val, index=working_df.index)
            working_df.loc[censored, "obs_limit"] = limits.loc[censored]
        working_df.loc[censored, ["thaw_depth", "pf_depth"]] = np.nan

    pf_observed = pd.Series(pd.NA, index=working_df.index, dtype="Int64")
    pf_observed.loc[working_df["pf_depth"].notna()] = 1
    pf_observed.loc[censored] = 0
    working_df["pf_observed"] = pf_observed
    
    return working_df

def geoify_working(working_df, lon_name, lat_name, crs, col_tokeep=['date', 'pf_depth', 'thaw_depth', 'pf_observed', 'obs_limit']):
    """Convert working_df to an exportable geodataframe if it isn't already.

    Args:
        working_df (pd.DataFrame): Dataframe of observation. Should contain these columns: ['date', 'pf_depth', 'thaw_depth', 'pf_observed', 'obs_limit']
        lon_name (str):  Name of x/longitude column
        lat_name (str): Name of y/latitude column
        crs (str): crs info, typically given by epsg
        col_tokeep (list): list of column names to keep, defaults to include those from process_pf_observations

    Returns:
        working_df: geodataframe to export
    """

    working_gdf = gpd.GeoDataFrame(
        working_df[col_tokeep].copy(),
        geometry=gpd.points_from_xy(working_df[lon_name], working_df[lat_name]),
        crs=crs
    )
    
    return working_gdf


def csvify_working(df, lon_name, lat_name, source, col_tokeep=['date', 'pf_depth', 'thaw_depth', 'pf_observed', 'obs_limit']):
    """Convert working_df to an exportable csv if it isn't already.

    Args:
        working_df (pd.DataFrame): Dataframe of observation. Should contain these columns: ['date', 'pf_depth', 'thaw_depth', 'pf_observed', 'obs_limit']
        lon_name (str):  Name of x/longitude column
        lat_name (str): Name of y/latitude column
        source (str): name of the source dataset
        col_tokeep (list): list of column names to keep, defaults to include those from process_pf_observations

    Returns:
        working_df: dataframe to export
    """

    df_out = pd.DataFrame(
        df[col_tokeep].copy(),
    )
    df_out['lat'] = df[lat_name]
    df_out['lon'] = df[lon_name]
    df_out['source'] = source
    
    return df_out



def redistribute_vertices(geom, sample_distance, out_line=False):
    """ For a linestring geometry redistribute vertices every sample_distance. 
    

    Args:
        geom (LineString or MultiLineString): Geometry to resample
        sample_distance (numeric): New sample distance in absolute units
        out_line (bool, optional): Whether output should be a linestring or a list. Defaults to False.

    Raises:
        ValueError: Only handles LineString or MultiLineString geometries.

    Returns:
        list or Linestring: Resampled LineString(s)
    """
    if isinstance(geom, LineString):
        
        norm_dist = sample_distance/(round(geom.length))
        interp_coords = [geom.interpolate(distance, normalized = True) for 
                         distance in np.arange(start=0, stop=1+norm_dist, step = norm_dist)]
        # num_vert = int(round(geom.length / distance))
        # if num_vert == 0:
        #     num_vert = 1
        # interp_coords = [geom.interpolate(float(n) / num_vert, normalized=True)
        #      for n in range(num_vert + 1)]
        if out_line is True:
            return LineString(interp_coords)
        else:
            return interp_coords
    elif isinstance(geom, MultiLineString):
        parts = [redistribute_vertices(part, sample_distance)
                 for part in geom]
        return type(geom)([p for p in parts if not p.is_empty])
    else:
        raise ValueError('unhandled geometry %s', (geom.geom_type,))
    

def generate_transect_pts(line, sample_dist):
    """ Function generate equally spaced points along a line. 
    Credit to a S/O answer. https://stackoverflow.com/questions/62990029/how-to-get-equally-spaced-points-on-a-line-in-shapely
    And: https://stackoverflow.com/questions/34906124/interpolating-every-x-distance-along-multiline-in-shapely/35025274#35025274

    Args:
        line (GeoDataFrame): Single row GeoDataFrame this function should be applied to. Could eventually use multi-indexing to use multiple line segments.
        sample_dist (numeric): Distance along line in CRS-units.
    """
    
    points = redistribute_vertices(line.geometry.iloc[0], sample_distance=sample_dist)
    # total_len = round(line.length.copy().iloc[0])
    
    # distance_delta = sample_dist/total_len
    # # note: the 0 to 1 won't necessarily go in eihter direction
    # distances = np.arange(start=0, 
    #                         stop=1+distance_delta, 
    #                         step=distance_delta)

    # points = [line.interpolate(distance, normalized=True) for distance in distances]
    points = shapely.ops.unary_union(points)
    points = gpd.GeoSeries(points, name='geometry').explode(index_parts=True)[0]
    # test whether or not to reverse. Not really clear why this is 
    # start point of line:
    start_pt = line.geometry.boundary.explode(index_parts=True).iloc[0]
    dist_to_start = points.iloc[0].distance(start_pt)
    
    if (dist_to_start  > 0.1):
        points = points.iloc[::-1].reset_index(drop=True)
    return points


def point_distance(x):
    """ Computes distance between each pair of consecutive points. 
    Wrap with a cumsum to get distance along a curve.
    Taken from R package smoothr.

    Args:
        x (np.array): nx2 array of coordinates
    """
    # compute dx, dy. 
    d_dimensional = np.diff(x, axis = 0) 
    # Compute total distance sqrt(dx^2 + dy^2))
    d_total = np.sqrt((d_dimensional ** 2).sum(axis=1))
    return d_total

def interpolate_fz(transect_gdf, sample_dist):
    """ For a gdf containing a number of points (e.g. along a transect) along with associated measurements,
    interpolate to a constant sampling distance. 

    Args:
        transect_gdf (GeoDataFrame): GeoDataFrame containing a GeoSeries of points along with attribute columns
        sample_dist (numeric): new distance between points
        
    Returns:
        GeoDataFrame: Resampled GeoSeries along with interpolated attribute values
    """
    original_line = gpd.GeoSeries(LineString(transect_gdf.geometry), name='geometry')
    # print(original_line)
    # original arc-length
    ds = transect_gdf.apply(lambda row: original_line.project(row.geometry),axis=1)[0]
    # generate new set of points every sample_dist.
    new_points = generate_transect_pts(original_line, sample_dist)
    # compute new arc-length of points
    new_ds = new_points.apply(lambda row: original_line.project(row))
    # interpolate z(ds) at every ds
    # pd.apply()
    
    original_attributes = transect_gdf.drop(columns="geometry").copy()
    ## can't get this to work
    # original_attributes.apply(lambda attribute: np.interp(new_ds, ds, attribute)[:, 0], axis=0, raw=True)
    new_attributes = {col:np.interp(new_ds, ds, original_attributes[col].copy())[:, 0] for col in original_attributes.columns}
    # out = original_attributes.apply(lambda attribute: attribute, axis=0, raw=True)
    
    interpolated_gdf = gpd.GeoDataFrame(pd.DataFrame(new_attributes),
                     geometry=new_points,
                     crs=transect_gdf.crs)
    return interpolated_gdf


"""
Example of how to check interpolate_fz.
x = np.arange(5e5, 5e5+52, step=2)
y = np.zeros_like(x)
z = np.arange(0, 10, step = 10/x.shape[0])
w = np.arange(np.sin(1), np.sin(1.7), step = (np.sin(1.7)-np.sin(1))/x.shape[0])
original_points=gpd.GeoDataFrame(pd.DataFrame({"z": z, "w": w}), geometry=gpd.points_from_xy(x=x, y=y), crs="EPSG:32606")
interpolated_values = interpolate_fz(original_points, 5)

"""

def standardize_column_names(dfs: List[pd.DataFrame], cols: Dict[str, List[str]]) -> List[pd.DataFrame]:
    """Standardize the column names of each df so that for the target columns in each cols value, replace it with the key.
    Example is:
    cols = {
    "date": ["date", "dateobs", "obs_date"],
    }

    Args:
        df_list (List[pd.DataFrame]): pd.DataFrames in which columns will be renamed.
        cols (List[str]): dictionary containing the columns to be renamed.
        
    Returns:
        List[pd.DataFrame]: Same list with renamed columns.
    """
    for df in dfs:
        for std_name, col_names in cols.items():
            for col_name in col_names:
                if col_name in df.columns:
                    df.rename(columns={col_name: std_name}, inplace=True)
                    break
    return dfs

def add_nans(dfs: List[pd.DataFrame], new_cols: List[str]) -> List[pd.DataFrame]:
    """ For every df in dfs, add a column of np.nans for each column in new_cols if no column exists. 

    Args:
        dfs (List[pd.DataFrame]): pd.DataFrames in which np.nan columns will be added.
        new_cols (List[str]): Columns to be added.

    Returns:
        List[pd.DataFrame]: Same list with additional columns as necessary.
    """
    for df in dfs:
        for col in new_cols:
            if col not in df.columns:
                df = df.assign(**{col: np.nan})
    return dfs

def list_local_files(suffix: str, extension: str, data_folder: str) -> List[str]:
    """ Given a suffix (subdirectory) and extension type (regex?) pull local data

    Args:
        suffix (str): Subdirectory containing the relevant pf data files
        extension (str): What's the file extension type? e.g. .csv, .json, .shp
    """
    sub_path = os.path.join(data_folder, suffix)
    sub_filenames_long = os.listdir(sub_path)
    search_string = r"\." + extension + "$"
    sub_filenames = [sub_path + file for file in sub_filenames_long if re.search(search_string, file)]
    
    return sub_filenames

def remove_duplicated_points(working_gdf, threshold, crs):
    """ Removes duplicated (points within threshold of one another) points from the df

    Args:
        working_gdf (GeoDataFrame): Geodataframe of points
        threshold (numeric): Distance threshold to use in crs units (should be m)
        crs (str): CRS to use
    """
    working_gdf_polarcoord = working_gdf.to_crs(crs)
    dist_vector = np.zeros(working_gdf_polarcoord.shape[0])
    for index, row in working_gdf_polarcoord.iterrows():
        # print(index)
        temp_join = working_gdf_polarcoord.iloc[index:index+1].sjoin_nearest(working_gdf_polarcoord.drop(index),
                                                        how='left',
                                                        distance_col='Distances')
        dist_vector[index] = temp_join['Distances'].values[0]
    
    not_duplicate_mask = dist_vector > threshold
    working_gdf = working_gdf[not_duplicate_mask]
    
    return working_gdf


def check_columns(df):
    """
    Ensures that the correct columns are present in a dataframe before final export.
    """
    required_cols = set(['lon', 'lat', 'date', 'source', 'site_id',
                     'pf_observed', 'pf_depth', 'thaw_depth', 'obs_limit'])
    
    cols = list(df.columns)
    not_there = []
    for rc in required_cols:
        if rc not in cols:
            not_there.append(rc)

    # Also check extra columns
    extras = []
    for c in cols:
        if c not in required_cols:
            extras.append(c)

    if len(not_there) > 0:
        print('Missing columns: {}'.format(not_there))

    if len(extras) > 0:
        print('Extra columns: {}'.format(extras))

    # Ensure pf_observed column is integer (it should be 0 or 1)
    if not is_integer_dtype(df['pf_observed']):
        print('pf_observed column is not integer.')

    return
