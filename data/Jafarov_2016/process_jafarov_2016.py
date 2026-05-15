#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jafarov_2016"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Annalise Khandelwal"
last_substantive_update = "2026-04-11"
source_dataset = '''
Jafarov, E.; Parsekian, A.; Schaefer, K.; Liu, L.; Chen, A.; Panda, S.K.;
Zhang, T. 2018. Pre-ABoVE: Active Layer Thickness and Soil Water Content,
Barrow, Alaska, 2013. ORNL DAAC. https://doi.org/10.3334/ORNLDAAC/1355
'''
processing_assumptions = [
  "The source table is split into separate probe and GPR views so that each method can keep its own coordinates and thaw-depth field.",
  "Probe and GPR active-layer-thickness values are both converted from meters to centimeters.",
  "All processed observations are treated as permafrost-present, so pf_observed is fixed to 1 and pf_depth is set equal to thaw_depth.",
  "method is set to tp for probe rows and gp for GPR rows.",
]
temporal_handling = [
  "All observations are assigned the representative field date 2013-08-12.",
]
spatial_handling = [
  "Probe and GPR coordinates are taken from separate source columns and preserved without reprojection.",
]
manual_steps = []
known_limitations = [
  "Observation timing is approximate because all rows share one campaign-average date.",
  "The script assumes all retained observations come from continuous permafrost terrain and therefore does not represent non-permafrost cases.",
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

source = 'Jafarov_2016'

df = pd.read_csv(_ROOT_DIR / "data" / source /"prb_gpr_alt_hd.csv", skiprows=[0,1,2,4], header=0)

#split the data into 2 to record lat and lon for gpr and probe separately 

df_gpr = df.copy()

# dorp unneeded columns
df = df.drop(columns = ['unc_alt_prb', 'lat_gpr', 'lon_gpr', 'owtt', 'velocity', 'unc_vel', 'cv_vel',
                        'alt_gpr','unc_alt_gpr', 'vwc','unc_vwc'])
df_gpr = df_gpr.drop(columns = ['unc_alt_prb', 'lat_prb', 'lon_prb', 'owtt', 'velocity', 'unc_vel', 'cv_vel',
                            'alt_prb', 'vwc','unc_alt_gpr','unc_vwc'])

#remane columns
df.rename(columns={"lat_prb": "lat",
                   "lon_prb":"lon",
                   "alt_prb":"thaw_depth",
                   "site_ID": "site_id"}, inplace=True)
df_gpr.rename(columns={"lat_gpr": "lat",
                   "lon_gpr":"lon",
                   "alt_gpr":"thaw_depth",
                   "site_ID": "site_id"}, inplace=True)
#add method column for each df
df['method'] = 'tp'
df_gpr['method'] = 'gp'

#merge two dataframs
df_comb = pd.concat([df, df_gpr]).reset_index(drop=True)

#convert thaw_depth to cm
#df_comb['thaw_depth'] = pd.to_numeric(df_comb['thaw_depth'], errors='coerce')
df_comb['thaw_depth'] = df_comb['thaw_depth'] * 100
# -----------------------------------------------------
# ADD REQUIRED COLUMNS
# -----------------------------------------------------
df_comb["obs_limit"] = np.nan
df_comb["pf_observed"] = 1 # site is in continous PF and all ALT values are below standard probe length
df_comb['pf_depth'] = df_comb['thaw_depth'] # given the late season date assume ALT = depth to pf
df_comb["source"] = source
df_comb["date"] = '2013-08-12' # using average date of filed work in metadata



# SAVE CLEANED CSV
# -----------------------------------------------------
data_utils.check_columns(df_comb)

df_comb.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
