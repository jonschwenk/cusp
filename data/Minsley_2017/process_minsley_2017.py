"""
metadata_schema_version = 1
source_key = "Minsley_2017"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Lawrence Vulis"
last_substantive_update = "2026-04-10"
source_dataset = '''
Pastick, N.J.; Kass, M.A.; Wylie, B.K.; James, S.R.; Rey, D.M.; Minsley, B.J.;
Ebel, B.A. 2018. Alaska permafrost characterization: Geophysical and related
field data collected from 2016-2017. U.S. Geological Survey data release.
https://doi.org/10.5066/P99PTGP4
'''
processing_assumptions = [
  "This script processes the point-soil observations only; the ERT portion of the release is intentionally not included.",
  "ActiveLayerThickness values reported with a leading > are treated as observation-limit non-permafrost observations.",
  "Rejected probes with DepthtoRejection < 100 cm have their active-layer thickness cleared before permafrost presence is derived.",
  "Near-surface permafrost is inferred with data_utils.process_pf_observations using a 132 cm threshold and a fixed observation-limit value of 132 cm.",
  "method is set to tp for all retained rows because this script only exports the point-soil thaw-probe observations from the release.",
]
temporal_handling = [
  "Per-observation dates are parsed from SampleDate using the source mm/dd/yy format and preserved in the processed output.",
]
spatial_handling = [
  "Latitude and longitude are read directly from the source CSV in WGS84 decimal degrees.",
]
manual_steps = []
known_limitations = [
  "The 132 cm permafrost threshold is a CUSP processing assumption rather than an explicit field in the source CSV.",
]
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

source = 'Minsley_2017'
df = pd.read_csv(_ROOT_DIR / "data" / source /"Permafrost_Soil_Measurements_in_Alaska_2016-2017.csv".format(source))

df[df == -9999] = np.nan
df[df == '-9999'] = np.nan

# identify which observations are at observation limit (contain a >)
obs_limit_mask = df['ActiveLayerThickness'].str.contains(">", na=False)
org_obs_limit_mask = df['SurfOrg'].str.contains(">", na=False)

# less explicit version
# full_data['ActiveLayerThickness'] = full_data['ActiveLayerThickness'].str.replace(">", "")

# more explicit version
df.loc[obs_limit_mask, 'ActiveLayerThickness'] = df.loc[obs_limit_mask, 'ActiveLayerThickness'].str.replace(">", "")
df['ActiveLayerThickness'] = pd.to_numeric(df['ActiveLayerThickness'])
df.loc[org_obs_limit_mask, 'SurfOrg'] = df.loc[org_obs_limit_mask, 'SurfOrg'].astype(str).str.replace(">", "")
df['SurfOrg'] = pd.to_numeric(df['SurfOrg'])

# remove data which had a rejected probe, not clear what to say with it. No PF detected or PF detected?
rejected = np.logical_and(~np.isnan(df['DepthtoRejection']), (df['DepthtoRejection'] < 100))
df.loc[rejected, 'ActiveLayerThickness'] = np.nan
# full_data['DepthtoRejection'] = full_data['DepthtoRejection'].str.replace(">", "")
# subset data to only be those which have ALT or surforganic thickness measurements
has_probe_mask = np.logical_or(
    np.logical_or(~np.isnan(df['ActiveLayerThickness']),
                  ~np.isnan(df['SurfOrg'])),
    ~np.isnan(df['DepthtoRejection'])
)

subset_data = df.loc[has_probe_mask]

subset_data.rename(columns={'SurfOrg': 'org_thick',
                            'SampleDate': 'date'},
                   inplace=True)

subset_data['date'] = pd.to_datetime(subset_data['date'], format="%m/%d/%y").astype(str).values

subset_data = data_utils.process_pf_observations(subset_data.copy(),
                        alt_name='ActiveLayerThickness', 
                        pf_limit=132,
                        obs_limit_val=132,
                        obs_limit_mask=obs_limit_mask)
                            
# new columns. If ALT  < 130 cm, near surface pf was observed
# subset_data['pf_observed'] = (subset_data['ActiveLayerThickness'].values < 130)*1
# anywhere where the probes are at limit should NOT be permafrost.
subset_data.loc[obs_limit_mask & ~rejected, 'pf_observed'] = 0
# subset_data['pf_depth'] = subset_data.loc[:,'ActiveLayerThickness']

# subset_data.loc[subset_data['pf_observed']==0, 'pf_depth'] = 0
subset_data.rename({'Long_deg':'lon', 'Lat_deg':'lat', 
                    'SiteID':'site_id'},
                    axis=1, inplace=True)
subset_data['source'] = source
subset_data['method'] = 'tp'

to_drop = ['ElectrodeNumber', 'distance', 'Height', 'Satellites', 'PDOP', 'Status', 'HRMS', 'VRMS', 'X_UTMz6', 'Y_UTMz6', 'LinDist_m', 'DepthtoRejection', 'Comment']
subset_data.drop(to_drop, axis=1, inplace=True)

data_utils.check_columns(subset_data)

subset_data.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
