"""
metadata_schema_version = 1
source_key = "Minsley_2015"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Pastick, N.J.; Kass, M.A.; Wylie, B.K.; James, S.R.; Rey, D.M.; Minsley, B.J.;
Ebel, B.A. 2018. Alaska permafrost characterization: Geophysical and related
field data collected from 2016-2017. U.S. Geological Survey data release.
https://doi.org/10.5066/P99PTGP4
'''
processing_assumptions = [
  "This script processes the point-soil observations only; the ERT portion of the release is intentionally not included.",
  "Active-layer-thickness values reported with a leading > are treated as observation-limit non-permafrost observations.",
  "Rejected probes with DepthtoRejection < 100 cm have their active-layer thickness cleared before permafrost presence is derived.",
  "Ordinary numeric active-layer thickness is treated as permafrost presence at the reported depth, regardless of depth.",
  "Only explicit >x values are treated as lower-bound absence, with obs_limit set to the row's reported x value; nonpositive >0 records are excluded.",
  "method is set to tp for all retained rows because this script only exports the point-soil thaw-probe observations from the release.",
]
temporal_handling = [
  "All retained observations are assigned the representative campaign date 2015-08-29.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the source workbook in WGS84 decimal degrees.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all rows share one campaign-average date.",
  "Rows with probe rejection shallower than 100 cm do not establish permafrost state and are excluded.",
]
external_dependencies = []
notes = ""
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os
import warnings
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = 'Minsley_2015'
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="Unknown extension is not supported and will be removed",
        category=UserWarning,
        module="openpyxl",
    )
    full_data = pd.read_excel(_ROOT_DIR / "data" / source /"AK2015-soilsDataCombined.xlsx".format(source))
full_data[full_data == -9999] = np.nan
full_data[full_data == '-9999'] = np.nan
full_data[full_data == -999] = np.nan
full_data[full_data == '-999'] = np.nan

# identify which observations are at observation limit (contain a >)
obs_limit_mask = full_data['ActiveLayerThickness(cm)'].str.contains(">", na=False)
org_obs_limit_mask = full_data['SurfOrg(cm)'].str.contains(">", na=False)

# 
full_data.loc[obs_limit_mask, 'ActiveLayerThickness(cm)'] = full_data.loc[obs_limit_mask, 'ActiveLayerThickness(cm)'].str.replace(">", "")
full_data['ActiveLayerThickness(cm)'] = pd.to_numeric(full_data['ActiveLayerThickness(cm)'])
full_data.loc[org_obs_limit_mask, 'SurfOrg(cm)'] = full_data.loc[org_obs_limit_mask, 'SurfOrg(cm)'].astype(str).str.replace(">", "")
full_data['SurfOrg(cm)'] = pd.to_numeric(full_data['SurfOrg(cm)'])

# Rejected probes do not establish permafrost presence or absence.
rejected = np.logical_and(~np.isnan(full_data['DepthtoRejection(cm)']), (full_data['DepthtoRejection(cm)'] < 100))
valid_lower_bound = (
    obs_limit_mask
    & ~rejected
    & full_data['ActiveLayerThickness(cm)'].gt(0)
)
direct_depth = (
    ~obs_limit_mask
    & ~rejected
    & full_data['ActiveLayerThickness(cm)'].notna()
)

# New day of year is given by (234 + 248)/2 = 241 = Aug 29, 2015.
full_data['date'] = '2015-08-29'
subset_data = full_data.loc[valid_lower_bound | direct_depth].copy()
subset_obs_limit_mask = valid_lower_bound.loc[subset_data.index]

subset_data.rename(columns={'SurfOrg(cm)' : 'org_thick', 'Site':'site_id'},
                   inplace=True)

# rename, create thresholded columns
subset_data = data_utils.process_pf_observations(subset_data.copy(),
                        alt_name='ActiveLayerThickness(cm)', 
                        obs_limit_val=subset_data['ActiveLayerThickness(cm)'],
                        obs_limit_mask=subset_obs_limit_mask)
                            

# anywhere where the probes are at limit should NOT be permafrost.
subset_data.loc[obs_limit_mask & ~rejected, 'pf_observed'] = 0

subset_gdf = data_utils.csvify_working(subset_data.copy(), 
                                       source=source,
                                       lat_name="Lat_WGS84dd",
                                       lon_name="Lon_WGS84dd",
                                       col_tokeep=["thaw_depth", "pf_observed", 'pf_depth', "date", 'org_thick', 'obs_limit', 'site_id']) 

subset_gdf['pf_observed'] = subset_gdf['pf_observed'].astype(int)
subset_gdf['method'] = 'tp'
data_utils.check_columns(subset_gdf)

subset_gdf.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
