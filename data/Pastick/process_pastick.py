"""
metadata_schema_version = 1
source_key = "Pastick"
release_clearance = "approved"
permission_basis = "emailed_approval"
last_substantive_update = "2026-05-22"
source_dataset = '''
Pastick, Neal. Unpublished Alaska pedon and near-surface permafrost data
compiled from multiple sources, including NRCS-derived products represented in
this directory.
'''
processing_assumptions = [
  "YFlats_NRCS pfrost depth is treated as both pf_depth and thaw_depth when pf_observed = 1.",
  "WesternAKSitePhoriz permafrost presence is inferred from horizon names containing frozen-soil suffixes, with the shallowest frozen horizon top used as pf_depth.",
  "WesternAKSitePhoriz obs_limit is taken as the deepest horizon bottom for each pedon, and organic thickness is derived from O-horizon bottoms when present.",
  "WesternAKSitePhoriz/numeric-ID pit rows that overlap with NCSS_Lab_Data_Mart are removed in favor of NCSS: same pf_observed status and within 1 m, regardless of Pastick's update-like date fields or small depth/profile-bottom differences.",
  "The remaining site shapefiles are harmonized through column-name standardization, records with unrecognized pf_observed encodings are dropped, and source-native site identifiers are preserved where available.",
  "method is assigned explicitly for YFlats_NRCS and WesternAKSitePhoriz, and set to unknown for the remaining shapefiles when no reliable method field is available.",
]
temporal_handling = [
  "Per-record dates are carried through from the source shapefiles when present; the script does not impose a campaign-average date.",
]
spatial_handling = [
  "YFlats_NRCS and WesternAKSitePhoriz coordinates are read from source attributes.",
  "The remaining site shapefiles are reprojected to WGS84 from their source projected coordinates before latitude and longitude are extracted from point geometry.",
]
manual_steps = []
known_limitations = [
  "This source is a compiled unpublished dataset with heterogeneous schemas and uneven metadata across component files.",
  "Small coordinate precision differences can appear across rebuilds because several component shapefiles are reprojected before export.",
  "Some NCSS-overlapping WesternAKSitePhoriz rows have different depth/profile-bottom values between Pastick and NCSS; CUSP keeps NCSS as the preferred source system for these pedons.",
]
external_dependencies = [
  "data/NCSS_Lab_Data_Mart/processed_ncss_lab_data_mart.csv is required for source-specific NCSS overlap filtering.",
]
notes = "Current source key is retained for repo continuity but should eventually be renamed to NRCS_Alaska."
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import os
import math
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cusp.data_utils import _ROOT_DIR
from cusp import data_utils


source = 'Pastick'
all_dfs = []


def normalize_pf_observed(values):
    normalized = []
    for value in values:
        if pd.isna(value):
            normalized.append(np.nan)
            continue

        if isinstance(value, (int, np.integer)):
            if value in (0, 1):
                normalized.append(int(value))
                continue

        if isinstance(value, (float, np.floating)):
            if np.isfinite(value) and value in (0.0, 1.0):
                normalized.append(int(value))
                continue
            normalized.append(np.nan)
            continue

        sval = str(value).strip().lower()
        if sval in {'y', 'yes', '1', 'true', 't'}:
            normalized.append(1)
        elif sval in {'n', 'no', '0', 'false', 'f'}:
            normalized.append(0)
        else:
            normalized.append(np.nan)

    return pd.Series(normalized, index=values.index)


def distance_m(lat1, lon1, lat2, lon2):
    """Return haversine distance in meters between two WGS84 points."""

    radius = 6371008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def remove_ncss_overlaps(df, threshold_m=1.0):
    """Remove Pastick numeric-ID pit rows represented by NCSS_Lab_Data_Mart."""

    ncss_path = _ROOT_DIR / "data" / "NCSS_Lab_Data_Mart" / "processed_ncss_lab_data_mart.csv"
    if not ncss_path.exists():
        raise FileNotFoundError(
            f"{ncss_path} is required for Pastick NCSS-overlap filtering."
        )

    ncss = pd.read_csv(
        ncss_path,
        usecols=["lat", "lon", "pf_observed"],
        low_memory=False,
    ).dropna(subset=["lat", "lon", "pf_observed"])
    ncss["pf_observed"] = pd.to_numeric(ncss["pf_observed"], errors="coerce").astype("Int64")
    ncss = ncss.dropna(subset=["pf_observed"])

    candidate_mask = (
        df["method"].eq("pit")
        & df["site_id"].astype(str).str.fullmatch(r"\d+")
        & df["lat"].notna()
        & df["lon"].notna()
        & df["pf_observed"].notna()
    )
    remove_index = set()
    candidates = df.loc[candidate_mask, ["lat", "lon", "pf_observed"]]

    for index, row in candidates.iterrows():
        nearby = ncss[
            ncss["pf_observed"].eq(int(row["pf_observed"]))
            & ncss["lat"].between(row["lat"] - 0.001, row["lat"] + 0.001)
            & ncss["lon"].between(row["lon"] - 0.001, row["lon"] + 0.001)
        ]
        if nearby.empty:
            continue
        for _, ncss_row in nearby.iterrows():
            if distance_m(row["lat"], row["lon"], ncss_row["lat"], ncss_row["lon"]) <= threshold_m:
                remove_index.add(index)
                break

    if remove_index:
        print(f"Removed {len(remove_index)} Pastick rows already represented by NCSS_Lab_Data_Mart.")
    return df.drop(index=list(remove_index)).copy()

# YFlats_NRCS

gdf = gpd.read_file(_ROOT_DIR / "data" / source /"YFlats_NRCS.shp")
gdf = gdf.rename(columns={"Pfrost_dpt": "pf_depth", "Pfrost": "pf_observed", "Org_Thick": "org_thick",
                        "Rock": "rock","Dpth_of_ob": "obs_limit","User_Site": "site_id",
                        "Observatio": "date",
                        'LatDD':'lat',
                        'LongDD':'lon','Method':'method'
                        })

gdf.drop(['Rec_ID','DATUM'],axis=1, inplace=True)

gdf['pf_observed'] = normalize_pf_observed(gdf['pf_observed']).astype(int)
gdf['site_id'] = gdf['site_id'].fillna('YFlats_NRCS');
gdf['transect_name'] = np.nan;
gdf['transect_point'] = np.nan; 
gdf['source'] = source
gdf['thaw_depth'] = np.where(gdf['pf_observed'] == 1, gdf['pf_depth'], np.nan)
gdf['method'] = 'pit_aug'
gdf = gdf[~((gdf['lat'] == 0) & (gdf['lon'] == 0))].copy()

df = pd.DataFrame(gdf.drop('geometry', axis=1))
data_utils.check_columns(df)
all_dfs.append(df)

# WesternAKSitePhoriz
gdf = gpd.read_file(_ROOT_DIR / "data" / source /"WesternAKSitePhoriz.shp")
gdf = gdf[['hzname', 'hzdept','hzdepb','objwlupdat','siteobsiid','geometry','latstddeci','longstddec']]
gdf=gdf.dropna()

# GET cores with PF
# dry permafrost: hzname contains ff
# ice rich permafrost: hzname contains f
#  non permafrost soils:  hzname contains no f
# hzdept: top of horizon depth
gdf_pf = gdf[gdf.hzname.str.contains('f')]
#get a list of the unique pedon sites
pf_unqsite=(np.unique(gdf_pf.siteobsiid))
pfDepth = [];obsdepth=[];lat =[];long=[];site=[];date=[];pfobs=[];othick = [];rock = []; method =[]
for u in pf_unqsite:
    pfU = gdf_pf[gdf_pf.siteobsiid==u]
    pfU=pfU.reset_index()
    pfDepth.append(np.min(pfU.hzdept))
    obsdepth.append(np.max(pfU.hzdepb))
    lat.append(pfU.latstddeci[0]);long.append(pfU.longstddec[0])
    date.append(pfU.objwlupdat[0])
    site.append(u)
    pfobs.append(1)
    fpU = gdf[gdf.siteobsiid==u] #extract full soil profile to get the organic layer
    opfU = fpU[fpU.hzname.str.contains('O')]
    othick.append(np.max(opfU.hzdepb))
    rock.append('N')
    method.append('pit')

df = pd.DataFrame({'pf_depth':np.array(pfDepth),
                          'lat':np.array(lat),
                          'lon':np.array(long),
                          'site_id':np.array(site),
                          'date':np.array(date),
                          'pf_observed':np.array(pfobs),
                          'org_thick':np.array(othick),
                          'rock':np.array(rock),
                          'obs_limit':np.array(obsdepth),
                          'method':np.array(method)}) 

gdf[~gdf.siteobsiid.isin(gdf_pf.siteobsiid)]
# index for non permafrost cores
gdf_np= gdf[~gdf.siteobsiid.isin(gdf_pf.siteobsiid)]
npf_unqsite=(np.unique(gdf_np.siteobsiid))
pfDepth = [];obsdepth=[];lat =[];long=[];site=[];date=[];pfobs=[];othick = [];rock = []; method =[]
for u in npf_unqsite:
    pfU = gdf_np[gdf_np.siteobsiid==u]
    pfU=pfU.reset_index()
    pfDepth.append(np.nan)
    obsdepth.append(np.max(pfU.hzdepb))
    lat.append(pfU.latstddeci[0]);long.append(pfU.longstddec[0])
    date.append(pfU.objwlupdat[0])
    site.append(u)
    pfobs.append(0)
    opfU = pfU[pfU.hzname.str.contains('O')]
    othick.append(np.max(opfU.hzdepb))
    rock.append('N')
    method.append('pit')

ndf = pd.DataFrame({'pf_depth':np.array(pfDepth),
                          'lat':np.array(lat),
                          'lon':np.array(long),
                          'site_id':np.array(site),
                          'date':np.array(date),
                          'pf_observed':np.array(pfobs),
                          'org_thick':np.array(othick),
                          'rock':np.array(rock),
                          'obs_limit':np.array(obsdepth),
                          'method':np.array(method)})   

# Merge the dataframes
df = pd.concat([df, ndf], ignore_index=True)
#df=df.reset_index()
df['source'] = source
df['thaw_depth'] = np.nan
data_utils.check_columns(df)
all_dfs.append(df)

# Remaining sites
sites = ['Delta_Projected_albers','Denali5_Projected_Albers','Denali6_Projected_Albers','Fbnks_Projected_Albers','FtGreely_Projected_Albers','Gates_Projected_Albers',
         'Gulkana_Projected_Albers', 'Innoko_Projected_Albers', 'Kusko_Projected_Albers', 'Nenana_Projected_Albers', 'Yuk_char_Projected_Albers']
for site in sites:
    # site=sites[7]
    file = site + ".shp"
    gdf = gpd.read_file(_ROOT_DIR / "data" / source / file)
    gdf = gdf.to_crs(epsg=4326)
    gdf['lon'] = [g.coords.xy[0][0] for g in gdf.geometry.values] 
    gdf['lat'] = [g.coords.xy[1][0] for g in gdf.geometry.values] 

    col_renaming =  {
        "date": ["date_", "dateobs", "day", "obs_date", "date", 'Date_', 'DATE_','Date','Obs_Date','Day'],
        "pf_depth": ["depth", "dpt", "pfrost_dpt", 'Pfrost_dpt', 'Depth'],
        "obs_limit": ["dpth_of_ob", "obs_depth",'Dpth_of_ob',],
        "pf_observed": ["pfrost", "pf_ob", "pf_observed",'Pfrost'],
        "rock" : ['Rock'],
        'transect_name' : ['TRANSECTst'],
        'transect_point' :['STOPst'],
        'org_thick' :['Org_Thick'],
        'site_id' : ['Unique_ID', 'SiteID','OBJECTID_1', 'Site']
    }

    gdf = data_utils.standardize_column_names(dfs=[gdf],
                            cols=col_renaming)[0]

    if 'site_id' not in gdf.columns:
        gdf['site_id'] = pd.NA
    gdf['site_id'] = gdf['site_id'].fillna(site)
    gdf['source'] = source

    gdf['pf_observed'] = normalize_pf_observed(gdf['pf_observed'])
    gdf = gdf[~pd.isna(gdf['pf_observed'])].copy()
    gdf['pf_observed'] = gdf['pf_observed'].astype(int)

    toremove = ['Unique_ID', 'DATUM', 'UTMZONE', 'UTMEAST', 'UTMNORTH', 'LatDD', 'LongDD', 'geometry',
                'Method', 'LatDD84', 'LongDD84', 'Day', 'Zone', 'Lat', 'Lon', 'Easting', 'Northing',
                'Bottom', 'Pnt_type', 'Point','OBJECTID', 'Datum', 'UTM_Zone', 'UTM_Northi', 'UTM_Eastin',
                'Long_']
    for tr in toremove:
        if tr in gdf.columns:
            gdf.drop(tr, axis=1, inplace=True)

    if 'obs_limit' not in gdf.columns:
        gdf['obs_limit'] = np.nan
    gdf.loc[gdf['obs_limit'] == 0, 'obs_limit'] = np.nan
        
    gdf['thaw_depth'] = np.nan
    gdf['method'] = 'unknown'
    # if 'obs_depth' not in gdf.columns:
    #     gdf['obs_depth'] = np.nan

    data_utils.check_columns(gdf)

    gdf = gdf[~((gdf['lat'] == 0) & (gdf['lon'] == 0))].copy()
    all_dfs.append(pd.DataFrame(gdf))

final = pd.concat(all_dfs)
final.loc[final['pf_observed'] == 0, 'pf_depth'] = np.nan
final.loc[final['obs_limit'] == 0, 'obs_limit'] = np.nan
final = final[~((final['lat'] == 0) & (final['lon'] == 0))].copy()
final = remove_ncss_overlaps(final)
outfile = "processed_" + source + ".csv"
final.to_csv(_ROOT_DIR / "data" / source / outfile, index=False)



