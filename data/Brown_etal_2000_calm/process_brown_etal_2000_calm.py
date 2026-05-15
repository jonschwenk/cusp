"""
metadata_schema_version = 1
source_key = "Brown_etal_2000_calm"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "Kurt Solander"
last_substantive_update = "2026-04-10"
source_dataset = '''
Brown, J.; Hinkel, K. Muc; Nelson, F. E. 2000. The Circumpolar Active Layer
Monitoring (CALM) program: research designs and initial results. Polar
Geography 24(3): 166-258. The processed table in this directory is a reformatted
CALM summary workbook assembled for CUSP processing.
'''
processing_assumptions = [
  "The reformatted CALM workbook is sliced into fixed row blocks and then concatenated into a single summary table.",
  "Annual observations are expanded from wide year columns into long-form records.",
  "Values reported with a leading > are treated as no near-surface permafrost observations and pf_observed is set to 0.",
  "pf_depth is taken to equal thaw_depth wherever a numeric thaw depth is reported.",
]
temporal_handling = [
  "All annual observations are assigned a synthetic date of September 1 for the reported year because the summary table does not provide exact measurement dates.",
]
spatial_handling = [
  "Latitude and longitude are taken directly from the summary table without reprojection.",
]
manual_steps = [
  "The original north- and south-hemisphere CALM spreadsheets were reformatted and merged into CALM_Summary_table.xlsx before this script runs.",
]
known_limitations = [
  "The parser depends on fixed row ranges in the reformatted workbook and will break if that layout changes.",
  "obs_limit is left missing because the summary source does not report a consistent observation-limit field.",
]
external_dependencies = []
notes = ""
"""

# Package Imports
import pandas as pd
import geopandas as gpd
import numpy as np
import os
import sys
import datetime
import xlrd
import xlrd.book
from pandas import DataFrame  
from math import nan
import re
import unidecode

# Define path to import data_utils
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

# Define path to read in data
source = 'Brown_etal_2000_calm' 

# Read xls data from excel
#df = pd.read_excel(r"CALM_Summary_table.xls", engine = 'xlrd')

xls_path = _ROOT_DIR / "data" / source / "CALM_Summary_table.xlsx"
df = pd.read_excel(xls_path, engine="openpyxl")
 
# combine all data blocks
df_block1 = df[28:71]
df_block2 = df[74:98]
df_block3 = df[101:103]
df_block4 = df[106:141]
df_block5 = df[145:151]
df_block6 = df[154:177]
df_block7 = df[180:194]
df_block8 = df[197:223]
df_block9 = df[226:232]
df_block10 = df[235:238]
df_block11 = df[242:245]
df_block12 = df[248:249]
df_block13 = df[252:256]
df_block14 = df[259:263]
df_block15 = df[266:268]
df_block16 = df[271:283]
df_block17 = df[287:334]
df_block18 = df[337:348]
df_block19 = df[351:354]
df_all = pd.concat([df_block1,df_block2,df_block3,df_block4,df_block5,df_block6,df_block7,df_block8,df_block9,df_block10,df_block11,df_block12,df_block13,df_block14,df_block15,df_block16,df_block17,df_block18,df_block19],axis=0)

# Re-write column names to correspond with data
columnNames = df_all.iloc[0,0:41]
columnNames[0:2] = ["Site Code", "Site Name"]
columnNames[4:5]  = ["Method"]
columnNames[7:11]  = [1992,1993,1994,1995]
columnNames[12:13]  = [1997]
columnNames[39:41] = ["Site Code2", "Site Name2"]
df_all.columns=columnNames
df_all = df_all.iloc[1:270,:]

# convert unknown characters to nan & remove bad characters
df_all = df_all.replace('-',np.nan,regex=True) # convert dash to nan
df_all = df_all.replace('inactive',np.nan,regex=True) # convert inactive to nan
df_all = df_all.replace("*",np.nan) # convert single asterisk to nan
df_all = df_all.replace({r'\*': ''}, regex=True) # remove asterisk appended to thaw depth
df_all = df_all.replace({r'\<': ''}, regex=True) # remove less than signs from thaw depth
df_all = df_all.replace("\xa0", " ", regex=True) # remove non breaking spaces

# reformat date information
year = columnNames[5:39]
month = np.repeat(9,len(year)) # Assume end of thaw season for Northern Hemisphere sites is March 1st
day = np.repeat(1,len(year))
Dates = {'Day': day,  
        'Month': month,  
        'Year': year}  
dates_df = DataFrame(Dates, columns = ['Day', 'Month', 'Year'])
date = pd.to_datetime(dates_df.Year*10000 + dates_df.Month*100 + dates_df.Day,format='%Y%m%d')

# pre-allocate arrays
site_code = df_all.iloc[:,0]
site_id = df_all.iloc[:,1] 
lat = df_all.iloc[:,2] 
lon = df_all.iloc[:,3] 
method = df_all.iloc[:,4] 
thaw_depth = df_all.iloc[0,5:39] 

# define arrays, repeat single values and concatenate to full arrays
site_code_all = np.array([])
site_id_all = np.array([])
lat_all = np.array([])
lon_all = np.array([])
method_all = np.array([])
thaw_depth_all = np.array([])
for i in range(0,len(df_all)):
    site_code = np.repeat(df_all.iloc[i,0],len(year))
    site_id = np.repeat(df_all.iloc[i,1],len(year))
    lat = np.repeat(df_all.iloc[i,2],len(year))
    lon = np.repeat(df_all.iloc[i,3],len(year))
    method = np.repeat(df_all.iloc[i,4],len(year))
    thaw_depth = df_all.iloc[i,5:39]
    site_code_all = np.concatenate([site_code_all, site_code])
    site_id_all = np.concatenate([site_id_all, site_id])
    lat_all = np.concatenate([lat_all, lat])
    lon_all = np.concatenate([lon_all, lon])
    method_all = np.concatenate([method_all, method])    
    thaw_depth_all = np.concatenate([thaw_depth_all, thaw_depth])

# Remove bad characters from data (Note some still persist in final .csv file)
thaw_depth_all_pd = pd.DataFrame(thaw_depth_all)
thaw_depth_all_pd.columns = ['thaw_depth_m']
#thaw_depth_all = thaw_depth_all_pd['thaw_depth_m'].replace("\u00A0", " ")

# reformat methods used
# convert data type to list
method_list = method_all.tolist()

# determine indices where T (frost probe transect/grid), B (Borehole) and TT (thaw tube) characters are used
method_T = list(map(lambda x: 'T' in x, method_list))
method_T_idx = [i for i, x in enumerate(method_T) if x]
method_B = list(map(lambda x: 'B' in x, method_list))
method_B_idx = [i for i, x in enumerate(method_B) if x]
method_TT = list(map(lambda x: 'TT' in x, method_list))
method_TT_idx = [i for i, x in enumerate(method_TT) if x]

# Find union of datasets (no repitition) to determine which values lack T, B or TT characters
def Union(lst1, lst2, lst3):
    final_list = list(set().union(lst1, lst2, lst3))
    return final_list
 
method_union = Union(method_T_idx, method_B_idx, method_TT_idx) 

method_full = np.arange(len(method_list)) # create vector with length of methods

# find indices for different data types
method_TB_idx = list(set(method_T_idx).intersection(method_B_idx)) # Both T & B
method_num_idx = [ele for ele in method_full if ele not in method_union] # no T, B or TT
method_Tonly_idx = [ele for ele in method_TB_idx if ele not in method_B_idx] # T only but no B
method_Bonly_idx = [ele for ele in method_TB_idx if ele not in method_T_idx] # B only but no T

# create the dataframe for methods
method_reform = pd.DataFrame(np.repeat("Frost Probe Transect or Grid",len(method_full+1)))
method_reform.iloc[method_num_idx] = "Frost Probe Transect or Grid" # for values with no T or B characters
method_reform.iloc[method_Tonly_idx] = "Frost Probe Transect or Grid" # for values with T characters but no B characters
method_reform.iloc[method_Bonly_idx] = "Borehole" # for values with B characters but no T characters
method_reform.iloc[method_TB_idx] = "Frost Probe Transect or Grid & Borehole" # for values with both T and B characters
method_reform.iloc[method_TT_idx] = "Thaw Tube" # for values with TT characters

# reformate data to array and concatenate
method_reform_np = np.array(method_reform)
method_reform_all = np.concatenate(method_reform_np)

# repeat single date information across length of time series
year_lst = year.tolist() * len(df_all)
year_all = np.array(year_lst)
month_all = np.repeat(month,(len(df_all)))
day_all = np.repeat(day,(len(df_all)))
date_all = np.repeat(date,(len(df_all)))

# determine presence/absence of permafrost
pf_observed = thaw_depth_all
pd_pf_observed = pd.DataFrame(data=pf_observed) # need pandas to replace nan with zero for structured data type
pd_pf_observed.columns = ["pf_observed"]
pd_pf_observed.replace([">"], 0, inplace=True) 
matches = pd_pf_observed.apply(lambda col: col.astype(str).str.contains(">", case=False))
rows, cols = matches.values.nonzero()
pd_pf_observed.iloc[rows] = 0
pd_pf_observed = pd.to_numeric(pd_pf_observed['pf_observed'], downcast='integer', errors='coerce')
pd_pf_observed[pd_pf_observed > 0] = 1
pd_pf_observed = pd_pf_observed.fillna(0)

# determine observation depth limits
thaw_depth = thaw_depth_all
pd_thaw_depth = pd.DataFrame(data = thaw_depth)
thaw_depth_all = pd_thaw_depth.replace({r'\>': ''}, regex=True) # remove less than signs from thaw depth
pf_depth_all = thaw_depth_all

#set obs-limit to nan - actual limit of methods not report - thaw probes typically 150-185 cm (Brown et al. 2000) but not specified)
#obs_limit_all = np.nan

# merge all data types to single matrix
df_all_all = pd.concat((pd.DataFrame(list(year_all)),pd.DataFrame(list(month_all)),pd.DataFrame(list(day_all)),pd.DataFrame(list(date_all)),pd.DataFrame(list(site_code_all)),pd.DataFrame(list(site_id_all)),pd.DataFrame(list(lat_all)),pd.DataFrame(list(lon_all)),pd.DataFrame(list(method_reform_all)),pf_depth_all,thaw_depth_all,pd.DataFrame(list(pd_pf_observed))),axis=1)
df_all_all['source'] = source
df_all_all['obs_limit'] = np.nan

df_all_all.columns = ("year","month","day","date","site_code","site_id","lat","lon","method","pf_depth","thaw_depth","pf_observed","source","obs_limit") 

# Force thaw_depth and pf_depth to be numeric (invalids -> NaN)
df_all_all["thaw_depth"] = pd.to_numeric(df_all_all["thaw_depth"], errors="coerce")
df_all_all["pf_depth"]   = pd.to_numeric(df_all_all["pf_depth"], errors="coerce")

# Make sure pf_observed is 0/1/NA and stored as pandas nullable integer
df_all_all["pf_observed"] = pd.to_numeric(df_all_all["pf_observed"], errors="coerce")
df_all_all["pf_observed"] = df_all_all["pf_observed"].astype("Int64")  # nullable int


data_utils.check_columns(df_all_all)

# Merge
#df = pd.concat([full_2018_gdf, full_1962_gdf])
df_all_all = df_all_all[~pd.isna(df_all_all['pf_observed'])]
df_all_all['pf_observed'] = df_all_all['pf_observed'].astype(int)

df_all_all=df_all_all.drop(columns = ['year', 'month', 'day', 'site_code'])

data_utils.check_columns(df_all_all)

#os.chdir(r"/Users/ksolander/Documents/GitHub/cusp/data/{}".format(source)) 
df_all_all.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)

