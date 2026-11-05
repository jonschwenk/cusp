"""
metadata_schema_version = 1
source_key = "Yukon_Permafrost_Database"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "CUSP maintainers + Codex"
last_substantive_update = "2026-11-05"
source_dataset = '''
Yukon Geological Survey (2026), Yukon Permafrost Database, geotechnical and
temperature table exports dated 2025-09-21, accessed 2026-11-03.
https://data.geology.gov.yk.ca/permafrost; issue #43.
Catalogue: https://open.yukon.ca/data/permafrost-database
'''
processing_assumptions = [
  "Retain direct numeric SURFACE_THAW only when the same row explicitly identifies permafrost, has a valid interval and investigation date, and does not exceed hole depth. These are instantaneous thaw boundaries, not annual maximum ALT.",
  "Additional source-labelled permafrost intervals are presence upper bounds at the shallowest valid interval bottom, never exact ALT or exact permafrost-table depths.",
  "August-September frozen intervals without an explicit seasonal-frost qualification are interpreted as permafrost presence with PA and UB flags; the maintainer accepted this documented late-thaw-season assumption for v1.3 on 2026-11-05. No winter/spring depth threshold is used to infer perennial freezing.",
  "Bounds are limited to intervals ending within 10 m, the near-surface screening depth used for this staging exercise. Multiple intervals produce one observation per borehole investigation.",
  "KZK geotechnical records are held because checked original-report values conflict with the export. Missing dates are not recovered by guessing from borehole identifiers.",
  "Four non-detections use explicit negative evidence: one source comment no permafrost encountered with a 2 m described reach, and three continuous Not frozen profiles. Retain only valid logged intervals within hole depth and report their contiguous observed reach, never an unobserved hole bottom.",
  "Temperature inclusion uses two consecutive well-covered calendar years at the same subsurface depth: at least 95 percent distinct observed days in each year, maximum missing run 7 days including endpoints, and every valid raw reading colder than negative documented instrument accuracy. Select the shallowest qualifying sensor within 10 m. These are inferred presence upper bounds, not interpolated ALT.",
  "Unknown thermal instrument accuracy, sensor interval readings, sentinel values, metadata conflicts, and uncertain thermal candidates remain in audit tables. No absence is inferred from a warm shallow sensor, annual mean, missing frozen descriptions, or incomplete X intervals.",
  "Retain native providers, identifiers and exact dates; annual thermal summaries use September 1 with DA, TI, UB and SS flags. Repeated independent years remain distinct.",
  "Overlap screening uses native identities, dates/periods, support, values and coordinates together; no proximity-only removal. Detailed overlap evidence and explicit holds are documented in README and overlap_review.json.",
]
temporal_handling = [
  "Parse provider two-digit years against the 2025 export; retain original date strings and investigation end dates. Inconsistent or missing dates are held. Annual thermal year labels remain separate from assigned September 1 dates.",
]
spatial_handling = [
  "Geotechnical NAD83 UTM zones 7-9 are transformed to WGS84. Hold records whose supplied decimal coordinates disagree by more than 10 m. No inferred zone repairs. Preserve original coordinates and acquisition descriptions.",
  "Where UTM is unavailable but source coordinates explicitly come from GPS/DGPS/Survey/Avenza, use the supplied decimals as approximate WGS84 and flag CF. No location is reconstructed. This allows a 2023 source-labelled PF bound and three continuous-unfrozen profiles.",
  "Thermal supplied decimal coordinates are treated as WGS84 site coordinates; retain the provider's location accuracy. Values are not the rounded map-popup coordinates.",
]
manual_steps = [
  "Download the pinned geotechnical ZIP from the portal Downloads tab. The large temperature ZIP is local/ignored; summarize_temperature.py regenerates the checked compact annual raw-extrema audit and metadata from it. See raw_manifest.json and README.",
]
known_limitations = [
  "Late-summer frozen ground can include residual seasonal freezing; PA marks the documented assumption accepted by the maintainer for v1.3. Approval does not remove these scientific limitations.",
  "Source interval boundaries may be lithological or recovery boundaries. UB observations do not claim an exact top-of-permafrost depth.",
  "Daily coverage and instrument-accuracy margins reduce but cannot eliminate missed extremes, calibration bias or undocumented sensor changes. Same-depth continuity is assumed only within the documented station/provider/method combination.",
  "Open Government Licence - Yukon requires attribution and excludes third-party rights the provider cannot license. Retain underlying provider attribution and source-specific limitations.",
]
external_dependencies = ["pyproj", "Pinned provider snapshots and thermal audit checksums in raw_manifest.json; no network needed for the normal processor."]
notes = "Issue #43. On 2026-11-05 the maintainer authorized committing the reviewed 973-observation ingestion, incrementing the dataset to v1.3, and pushing its commit and tag. This accepts the documented assumptions for this source; it does not create upstream permission or remove the Yukon licence third-party-rights qualification."
"""
from __future__ import annotations

import collections
import csv
from datetime import date, datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.name
FROZEN = {'F','N','NF','NB','NBN','NBE','V','VX','VC','VR','VS','ICE'}
NEGATIVE = re.compile(r'\bno\b.{0,40}\bpermafrost\b|non[- ]permafrost|\bnot\b.{0,30}\bpermafrost\b|permafrost.{0,30}\bnot\b', re.I)
UNCERTAIN = re.compile(r'possibl|probabl|likely|may be|suspect', re.I)

def number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def provider_date(value):
    if not value:
        return None
    result=datetime.strptime(value.split(' ')[0],'%d-%b-%y').date()
    if result.year>2025:
        result=result.replace(year=result.year-100)
    return result

def text(row):
    return ' | '.join(row.get(k,'') for k in ('PERMAFROST_DESC','COMMENTS'))

def explicit_permafrost(row):
    value=text(row)
    return bool(re.search(r'\bpermafrost\b',value,re.I)) and not NEGATIVE.search(value) and not UNCERTAIN.search(value)

def frozen(row):
    tokens=set(re.findall(r'[A-Za-z]+',row['ICE_CODE'].upper()))
    seasonal='seasonal' in text(row).lower() and 'seasonal depth to permafrost' not in text(row).lower()
    negative_frozen=re.search(r'unfrozen|not frozen|no frozen',text(row),re.I)
    return bool(tokens & FROZEN) and 'X' not in tokens and not seasonal and not UNCERTAIN.search(text(row)) and not NEGATIVE.search(text(row)) and not negative_frozen

def valid_interval(row,hole):
    top,bottom=number(row['TOP_DEPTH']),number(row['BOT_DEPTH'])
    return top is not None and bottom is not None and 0<=top<=bottom<=hole+1e-8

def base_record(site,lat,lon,day,method,tier):
    return dict(lon=lon,lat=lat,date=day,source=SOURCE,site_id=site,pf_observed=1,
                pf_depth=None,thaw_depth=None,obs_limit=None,method=method,ingestion_tier=tier)

def method_for(location):
    equipment=location.get('EQUIPMENT','').lower()
    if 'auger' in equipment or 'solid stem' in equipment or 'solidstem' in equipment:
        return 'aug'
    if location.get('HOLE_TYPE')=='T' or 'excavator' in equipment or 'shovel' in equipment:
        return 'pit'
    return 'unknown'

def read_geotech(archive):
    with zipfile.ZipFile(archive) as z:
        def read(name):
            return list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig').lstrip('\r\n'))))
        locations=read('PF_LOCATIONS.CSV')
        profiles=collections.defaultdict(list)
        for r in read('PF_PERMAFROST_DESC.CSV'): profiles[r['SITE_ID']].append(r)
    if len(locations)!=15436 or sum(map(len,profiles.values()))!=6531:
        raise ValueError('Unexpected provider snapshot counts; review before processing.')
    if len({l['SITE_ID'] for l in locations})!=len(locations):
        raise ValueError('Ambiguous native site identifiers.')
    return locations,profiles

def geotech_records(locations,profiles):
    from pyproj import Geod, Transformer
    geod=Geod(ellps='WGS84')
    transforms={str(z):Transformer.from_crs(26900+z,4326,always_xy=True) for z in (7,8,9)}
    output,audit=[],[]
    for l in locations:
        pp=profiles.get(l['SITE_ID'],[])
        if not pp: continue
        sid=l['SITE_ID']; reason='no_supported_permafrost_evidence'; rec=None; delta=None
        day=provider_date(l['START_DATE']); end=provider_date(l['END_DATE']); hole=number(l['HOLE_DEPTH'])
        has_utm=l['UTMZONE'] in transforms and number(l['EASTING']) is not None and number(l['NORTHING']) is not None
        decimal_fallback=l['COORD_ACQ'].lower() in {'avenza','gps','dgps','survey'} and number(l['LATITUDE']) is not None and number(l['LONGITUDE']) is not None and 58<=float(l['LATITUDE'])<=71 and -142<=float(l['LONGITUDE'])<=-123
        if sid.startswith('KZK'): reason='hold_kzk_transcription'
        elif not day: reason='hold_missing_date'
        elif end and end<day: reason='hold_inconsistent_dates'
        elif hole is None or hole<=0: reason='hold_missing_hole_depth'
        elif not has_utm and not decimal_fallback:
            reason='hold_missing_documented_crs_coordinates'
        else:
            if has_utm:
                lon,lat=transforms[l['UTMZONE']].transform(float(l['EASTING']),float(l['NORTHING']))
                supplied_lat,supplied_lon=number(l['LATITUDE']),number(l['LONGITUDE'])
                delta=geod.inv(lon,lat,supplied_lon,supplied_lat)[2] if supplied_lat is not None and supplied_lon is not None else None
            else:
                lon,lat=float(l['LONGITUDE']),float(l['LATITUDE'])
            if has_utm and (delta is None or not math.isfinite(delta) or delta>10):
                reason='hold_coordinate_disagreement'
            else:
                valid=[p for p in pp if valid_interval(p,hole)]
                direct=[p for p in valid if explicit_permafrost(p) and (number(p['SURFACE_THAW']) or 0)>0 and float(p['SURFACE_THAW'])<=hole+1e-8]
                source_pf=[p for p in valid if explicit_permafrost(p) and 0<float(p['BOT_DEPTH'])<=10]
                summer=[p for p in valid if frozen(p) and 0<float(p['BOT_DEPTH'])<=10] if day.month in (8,9) else []
                selected=None
                if direct:
                    values={float(p['SURFACE_THAW']) for p in direct}
                    if len(values)!=1: reason='hold_conflicting_surface_thaw'
                    else:
                        selected=min(direct,key=lambda p:int(p['ID']))
                        rec=base_record(sid,lat,lon,day.isoformat(),method_for(l),'direct_thaw')
                        rec.update(thaw_depth=100*values.pop(),pf_depth=100*float(selected['SURFACE_THAW']),obs_limit=100*hole)
                elif source_pf or summer:
                    tier='source_permafrost_bound' if source_pf else 'late_summer_frozen_bound'
                    selected=min(source_pf or summer,key=lambda p:(float(p['BOT_DEPTH']),int(p['ID'])))
                    # Reject actual contradictory interval overlap, not touching endpoints.
                    a,b=float(selected['TOP_DEPTH']),float(selected['BOT_DEPTH'])
                    conflict=any(p['ICE_CODE'].strip().upper()=='X' and valid_interval(p,hole) and max(a,float(p['TOP_DEPTH']))<min(b,float(p['BOT_DEPTH']))-1e-8 for p in pp)
                    if conflict: reason='hold_conflicting_frozen_unfrozen_intervals'
                    else:
                        rec=base_record(sid,lat,lon,day.isoformat(),method_for(l),tier)
                        rec.update(obs_limit=100*b,quality_flag_upper_bound_presence=True,
                                   quality_flag_pf_state_assumed=(tier=='late_summer_frozen_bound'))
                if rec is None and sid=='GINT_W14101360 TP04':
                    negative=[p for p in valid if 'no permafrost encountered in testpit' in text(p).lower() and p['ICE_CODE'].upper()=='X' and number(p['BOT_DEPTH'])==2]
                    if len(negative)!=1 or hole!=3.5:
                        raise ValueError('Changed explicitly reviewed non-detection profile.')
                    selected=negative[0]
                    rec=base_record(sid,lat,lon,day.isoformat(),'pit','explicit_profile_non_detection')
                    rec.update(pf_observed=0,obs_limit=200,quality_flag_obs_limit_profile_bottom=True,quality_flag_lower_bound_absence=True)
                if rec is None and pp and all(p['PERMAFROST_DESC'].strip().lower()=='not frozen' and not p['COMMENTS'].strip() for p in pp):
                    # Explicitly unfrozen profiles, including mobile-GPS 2023 logs.
                    reach=0.0
                    for p in sorted(valid,key=lambda p:float(p['TOP_DEPTH'])):
                        if float(p['TOP_DEPTH'])>reach+1e-8:break
                        reach=max(reach,float(p['BOT_DEPTH']))
                    if reach>0:
                        selected=max((p for p in valid if float(p['BOT_DEPTH'])==reach),key=lambda p:int(p['ID']))
                        rec=base_record(sid,lat,lon,day.isoformat(),method_for(l),'continuous_unfrozen_profile_non_detection')
                        rec.update(pf_observed=0,obs_limit=100*reach,quality_flag_obs_limit_profile_bottom=True,quality_flag_lower_bound_absence=True)
                if rec:
                    rec.update(native_location=json.dumps(l,sort_keys=True),native_profile=json.dumps(pp,sort_keys=True),
                               native_interval_id=selected['ID'],coordinate_delta_m=delta,
                               quality_flag_method_approximate_or_unknown=rec['method']=='unknown',
                               quality_flag_coord_source_flagged=not has_utm or not bool(l['COORD_ACQ']),
                               coordinate_source='NAD83_UTM_to_WGS84' if has_utm else 'provider_GPS_decimal_assumed_WGS84',
                               investigation_end=l['END_DATE'])
                    if end and end!=day: rec['quality_flag_date_source_approximate']=True
                    output.append(rec);reason='retained_'+rec['ingestion_tier']
        audit.append(dict(component='geotech',site_id=sid,date=day.isoformat() if day else '',decision=reason,coordinate_delta_m=delta,native_interval_count=len(pp)))
    return output,audit

def year_qualifies(row):
    accuracy=number(row['accuracy'])
    return accuracy is not None and accuracy>0 and float(row['coverage'])>=.95 and int(row['maxgap'])<=7 and float(row['max_temp']) < -accuracy

def thermal_records(annual,locations):
    groups={(r['location_id'],float(r['depth_m']),int(r['year'])):r for r in annual}
    chosen={}; audit=[]
    for (loc,depth,year),r in sorted(groups.items()):
        prior=groups.get((loc,depth,year-1))
        reason='hold_insufficient_two_year_cold_evidence'
        station=locations[loc]
        if number(r['accuracy']) is None:reason='hold_unknown_instrument_accuracy'
        elif station['PERMAFROST'].strip().lower()=='no':reason='hold_station_metadata_no'
        elif prior and year_qualifies(r) and year_qualifies(prior):
            if r['methods']!=prior['methods'] or r['who']!=prior['who'] or r['comments'] or prior['comments']:
                reason='hold_sensor_provider_change_or_comments'
            else:
                reason='qualifying_two_year_sensor'
                key=(loc,year)
                if key not in chosen or depth < float(chosen[key]['depth_m']):chosen[key]=r
        audit.append(dict(component='thermal',site_id=station['NAME'],date=f'{year}-09-01',depth_m=depth,decision=reason))
    output=[]
    for entry in audit:
        if entry['decision']=='qualifying_two_year_sensor':
            loc=next(k for k,v in locations.items() if v['NAME']==entry['site_id'])
            selected=chosen[(loc,int(entry['date'][:4]))]
            entry['decision']='retained_two_year_temperature_bound' if float(selected['depth_m'])==entry['depth_m'] else 'supported_deeper_sensor_not_separate_observation'
    for (loc,year),r in sorted(chosen.items()):
        l=locations[loc]
        rec=base_record(l['NAME'],float(l['LATITUDE']),float(l['LONGITUDE']),f'{year}-09-01','temp','two_year_temperature_bound')
        rec.update(obs_limit=100*float(r['depth_m']),quality_flag_upper_bound_presence=True,
                   quality_flag_temperature_inferred=True,quality_flag_date_assigned=True,quality_flag_summary_statistic=True,
                   thermal_year=year,thermal_prior_year=year-1,native_location=json.dumps(l,sort_keys=True),
                   thermal_evidence=json.dumps([groups[(loc,float(r['depth_m']),year-1)],r],sort_keys=True))
        if 2010<=year<=2014 and (l['NAME'].startswith('HPW_Shakwak_') or l['NAME']=='YGS_BeaverCreek'):
            rec['quality_flag_possible_duplicate_or_overlap']=True
        output.append(rec)
    return output,audit

def write_csv(path,rows):
    all_fields={k for row in rows for k in row}
    canonical=['lon','lat','date','source','site_id','pf_observed','pf_depth','thaw_depth','obs_limit','method']
    fields=[k for k in canonical if k in all_fields]+sorted(all_fields-set(canonical))
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def verify_inputs():
    manifest=json.loads((HERE/'raw_manifest.json').read_text())
    for name,expected in manifest['processor_inputs'].items():
        with (HERE/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=expected:raise ValueError(f'Input checksum mismatch: {name}')

def main():
    verify_inputs()
    locations,profiles=read_geotech(HERE/'Yukon_Permafrost_Geotech_Data.zip')
    observations,audit=geotech_records(locations,profiles)
    with (HERE/'thermal_annual_audit.csv').open(encoding='utf-8',newline='') as f:annual=list(csv.DictReader(f))
    with (HERE/'PFT_LOCATIONS.CSV').open(encoding='utf-8-sig',newline='') as f:
        locations={r['ID']:r for r in csv.DictReader(line for line in f if line.strip())}
    thermal,thermal_audit=thermal_records(annual,locations)
    observations+=thermal;audit+=thermal_audit
    # Explicit provenance-based exclusions only; see audited match evidence.
    review=json.loads((HERE/'overlap_review.json').read_text())
    excluded=set(review['excluded_site_date_keys'])
    observations=[r for r in observations if f"{r['site_id']}|{r['date']}" not in excluded]
    for flag in sorted({k for r in observations for k in r if k.startswith('quality_flag_')}):
        for r in observations:r.setdefault(flag,False)
    observations.sort(key=lambda r:(r['site_id'],r['date']))
    if len({(r['site_id'],r['date']) for r in observations})!=len(observations):raise ValueError('Duplicate site investigations/year summaries.')
    counts=dict(collections.Counter(r['ingestion_tier'] for r in observations))
    expected=review.get('expected_tier_counts')
    if expected is not None and counts!=expected:raise ValueError(f'Changed staged counts: {counts} != {expected}')
    write_csv(HERE/'processed_yukon_permafrost_database.csv',observations)
    write_csv(HERE/'ingestion_audit.csv',audit)
    result=dict(total=len(observations),tier_counts=counts,clearance='approved',audit_decisions=dict(collections.Counter(r['decision'] for r in audit)))
    (HERE/'ingestion_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
