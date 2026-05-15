"""
metadata_schema_version = 1
source_key = "Hanston_etal_2024"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Joel Rowland"
last_substantive_update = "2024-01-01"
source_dataset = '''
Hanston et al. 2024 thaw-depth measurements from Kougarok and Teller compiled
for CUSP release in the Hanston_etal_2024 source directory.
'''
processing_assumptions = [
  "The source probe length is treated as 130 cm, but thaw-depth values of 120 cm at Teller are classified as non-permafrost because measurements were collected in July before maximum thaw development.",
  "pf_depth is left empty because the measurements were made mid-summer rather than at full seasonal thaw.",
  "The Kougarok and Teller site tables are concatenated after harmonizing the same key columns.",
  "method is set to tp for all rows because the source consists of thaw-probe measurements.",
]
temporal_handling = [
  "Dates are parsed from YYYYMMDD strings in the source CSVs and normalized to calendar dates.",
]
spatial_handling = [
  "Latitude and Longitude are used directly from each source CSV.",
]
manual_steps = []
known_limitations = [
  "The pf_observed threshold is a conservative inference based on summer timing rather than a direct permafrost measurement.",
  "obs_limit is fixed to 130 cm for all rows.",
]
external_dependencies = []
notes = ""
"""
import pandas as pd
import numpy as np
import os
# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils
#import sys
#sys.path.append("/Users/jrowland/Documents/GitHub/cusp/code")
#import data_utils

source = 'Hanston_etal_2024'
#df = pd.read_csv(r"data\{}\PermafrostMeasurements.csv".format(source))
kg = pd.read_csv(_ROOT_DIR / "data" / source /"2022_ThawDepth_Kougarok_MM80_MM82.csv")
kg = kg.loc[:, ~kg.columns.str.contains('^Unnamed')]
kg = kg.dropna(how='all')

kg['source'] = source
kg.rename(columns={'Site':'site_id', 'Latitude':'lat', 'Longitude':'lon','Thaw_Depth':'thaw_depth' , 'Date':'date'}, inplace=True)
kg['date'] = pd.to_datetime(kg['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')

kg['pf_depth'] = np.nan #the measurements were made mid summer rather than full ALT therefore true depth to PF is not known
kg['pf_observed'] = (kg['thaw_depth'] < 119).astype(int) #deepest recorded depth at Teller site is 120 even though the probe is 130 and the site is dicontinuous
#since the measurments were made in July before full ALT development setting a conservative measure for PF/noPF

#df = pd.read_csv(r"data\{}\PermafrostMeasurements.csv".format(source))
tl = pd.read_csv(_ROOT_DIR / "data" / source /"2022_ThawDepth_Teller_MM27.csv")
#tl = pd.read_csv(r"/Users/jrowland/Documents/GitHub/cusp/data/Hanston_etal_2024/2022_ThawDepth_Teller_MM27.csv".format(source))
tl = tl.loc[:, ~tl.columns.str.contains('^Unnamed')]
tl = tl.dropna(how='all')

tl['source'] = source
tl.rename(columns={'Site':'site_id', 'Latitude':'lat', 'Longitude':'lon','Thaw_Depth':'thaw_depth' , 'Date':'date'}, inplace=True)
tl['date'] = pd.to_datetime(tl['date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')

tl['pf_depth'] = np.nan #the measurements were made mid summer rather than full ALT therefore true depth to PF is not known
tl['pf_observed'] = (tl['thaw_depth'] < 119).astype(int) #deepest recorded depth at Teller site is 120 even though the probe is 130 and the site is dicontinuous
#since the measurments were made in July before full ALT development setting a conservative measure for PF/noPF

df = pd.concat([kg, tl])
df['obs_limit'] = 130
df['method'] = 'tp'
#df.drop(['ID', 'Method', 'Year', 'Horizontal_distance_m',
#       'Depth_to_permafrost_cm', 'Depth_cm', 'Horizontal_to_permafrost_cm', 'Relative_age', 'Geomorphic_unit', 'Count'], axis=1, inplace=True)

data_utils.check_columns(df)

df.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

