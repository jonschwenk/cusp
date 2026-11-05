"""Non-destructive Yukon overlap screening. No proximity match is a deletion rule.

Run from any directory with Python standard library only.
Inputs are archive and current canonical/processed snapshots; hashes are recorded.
Distances: spherical great-circle, Earth radius 6371008.8 m. Threshold sensitivity
10--2000 m is a search envelope, not estimated location accuracy. SURFACE_THAW is
converted m to cm only for numerical comparison; interval tops are never ALT.
"""
from pathlib import Path
import collections, csv, hashlib, io, json, math, re, zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs'/'yukon_overlap_recheck'
OUT.mkdir(parents=True, exist_ok=True)
ARCHIVE = SOURCE/'Yukon_Permafrost_Geotech_Data.zip'
R = 6371008.8
def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError): return None
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_csv(name, rows):
    if not rows: (OUT/name).write_text(''); return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def year(date):
    if not date: return None
    if re.match(r'^\d{4}-',date): return int(date[:4])
    m=re.match(r'\d{2}-[A-Z]{3}-(\d{2})',date)
    if m: return 1900+int(m[1]) if int(m[1])>=30 else 2000+int(m[1])
def period(row):
    text=row.get('source_period','')
    years=[int(v) for v in re.findall(r'(?:18|19|20)\d{2}',text)]
    if not years and text:
        years=[1900+int(v) for v in re.findall(r'/([0-9]{2})(?:\D|$)',text)]
    # Recover abbreviated endpoint such as 1983-85, without treating month/day as year.
    m=re.search(r'((?:19|20)\d{2})\s*[-–]\s*(\d{2})(?!\d)',text)
    if m: years.append(int(m[1])//100*100+int(m[2]))
    if years: return min(years),max(years),'source_period'
    y=year(row.get('date',''));return (y,y,'canonical_year')
def norm(s): return re.sub('[^A-Z0-9]','',s.upper())
def xyz(rows,lat,lon):
    a=[(math.radians(float(r[lat])),math.radians(float(r[lon]))) for r in rows]
    return [(math.cos(x)*math.cos(y),math.cos(x)*math.sin(y),math.sin(x)) for x,y in a]
def chord(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def digits(s):
    return len(s.split('.')[1]) if '.' in s else 0

z=zipfile.ZipFile(ARCHIVE)
tables={n:list(csv.DictReader(io.StringIO(z.read(n).decode('utf-8-sig').lstrip()))) for n in ['PF_LOCATIONS.CSV','PF_PERMAFROST_DESC.CSV']}
loc=tables['PF_LOCATIONS.CSV'];pf=tables['PF_PERMAFROST_DESC.CSV']
assert len(loc)==15436 and len({r['SITE_ID'] for r in loc})==15436
by_pf=collections.defaultdict(list)
for r in pf: by_pf[r['SITE_ID']].append(r)
canonical_path=ROOT/'data/cusp_observations.csv'
canonical=read_csv(canonical_path)
paths=sorted(p for p in (ROOT/'data').glob('*/processed_*.csv') if p.parent.name!='Yukon_Permafrost_Database')
processed=[]
hashes={str(canonical_path.relative_to(ROOT)):sha(canonical_path),'geotech.zip':sha(ARCHIVE)}
for path in paths:
    hashes[str(path.relative_to(ROOT))]=sha(path)
    for i,r in enumerate(read_csv(path),2):
        if number(r.get('lat')) is not None and number(r.get('lon')) is not None and 58<=float(r['lat'])<=71 and -142<=float(r['lon'])<=-123:
            r['_path']=str(path.relative_to(ROOT));r['_line']=i; processed.append(r)
assert processed
print('Regional processed rows:',len(processed),flush=True)
existing_xyz=xyz(processed,'lat','lon')
candidate_xyz=xyz(loc,'LATITUDE','LONGITUDE')
grid=collections.defaultdict(list)
unique={}
for j,r in enumerate(processed):
    grid[(math.floor(float(r['lat'])*10),math.floor(float(r['lon'])*10))].append(j)
    unique.setdefault((r['lat'],r['lon']),j)
print('Unique regional coordinates:',len(unique),flush=True)
pairs=[]; nearest=[]; inventory=[]
thresholds=[10,50,100,500,1000,2000]
for i,l in enumerate(loc):
    sid=l['SITE_ID']; profiles=by_pf[sid]
    thaw=[number(p['SURFACE_THAW'])*100 for p in profiles if (number(p['SURFACE_THAW']) or 0)>0]
    subset='surface_thaw' if thaw else ('permafrost_profile' if profiles else 'other_location')
    cy=year(l['START_DATE'])
    inv={**l,'audit_subset':subset,'audit_year':cy,'audit_thaw_values_cm':json.dumps(thaw),'audit_pf_interval_ids':';'.join(p['ID'] for p in profiles),'audit_lat_decimal_digits':digits(l['LATITUDE']),'audit_lon_decimal_digits':digits(l['LONGITUDE'])}
    inventory.append(inv)
    if profiles:
        nearest_j=min(unique.values(),key=lambda j:chord(candidate_xyz[i],existing_xyz[j]))
        n=processed[nearest_j]
        nearest.append({'candidate_site_id':sid,'subset':subset,'candidate_date':l['START_DATE'],'candidate_year':cy,'nearest_source':n.get('source'),'nearest_site_id':n.get('site_id'),'nearest_date':n.get('date'),'nearest_source_period':n.get('source_period',''),'nearest_distance_m':round(2*R*math.asin(min(1,chord(candidate_xyz[i],existing_xyz[nearest_j])/2)),3)})
    gy,gx=math.floor(float(l['LATITUDE'])*10),math.floor(float(l['LONGITUDE'])*10)
    # At max regional latitude 71 N, 2 km is <0.056 degrees longitude;
    # a 0.1-degree cell plus all eight neighboring cells fully covers radius.
    js=[j for dy in [-1,0,1] for dx in [-1,0,1] for j in grid.get((gy+dy,gx+dx),[])]
    for j in js:
        r=processed[j]; dist=2*R*math.asin(min(1,chord(candidate_xyz[i],existing_xyz[j])/2))
        if dist>2000: continue
        a,b,basis=period(r); period_match=cy is not None and a is not None and a<=cy<=b
        depth=number(r.get('thaw_depth')); delta=min((abs(v-depth) for v in thaw), default=None) if depth is not None else None
        aliases=[r.get(k,'') for k in ['site_id','source_site_identifier','source_plot','calm_site_code','calm_site_name','site_location','Site_Name','SiteCode']]
        rawid=sid.removeprefix('GINT_')
        alias=next((v for v in aliases if norm(v) and norm(v) in [norm(sid),norm(rawid)]),'')
        # Identity strings shorter than six characters are weak local labels.
        strong_alias=bool(alias and len(norm(alias))>=6)
        pairs.append({'candidate_site_id':sid,'subset':subset,'candidate_date':l['START_DATE'],'candidate_year':cy,'candidate_lat':l['LATITUDE'],'candidate_lon':l['LONGITUDE'],'candidate_project':l['PROJECT_NAME'],'candidate_project_number':l['PROJECT_NUMBER'],'candidate_consultant':l['CONSULTANT'],'candidate_client':l['CLIENT'],'candidate_coord_acq':l['COORD_ACQ'],'candidate_hole_depth_m':l['HOLE_DEPTH'],'candidate_thaw_cm':json.dumps(thaw),'candidate_profile_ids':';'.join(p['ID'] for p in profiles),'existing_source':r.get('source'),'existing_site_id':r.get('site_id'),'existing_source_site_identifier':r.get('source_site_identifier',''),'existing_site_name':r.get('site_location',r.get('calm_site_name',r.get('Site_Name',''))),'existing_path':r['_path'],'existing_line':r['_line'],'existing_lat':r['lat'],'existing_lon':r['lon'],'existing_date':r.get('date'),'existing_source_period':r.get('source_period',''),'existing_period_first_year':a,'existing_period_last_year':b,'period_basis':basis,'same_period':period_match,'same_canonical_year':cy==year(r.get('date','')) if cy else False,'existing_method':r.get('method'),'existing_thaw_cm':depth,'existing_raw_depth':r.get('source_active_layer_text',r.get('calm_ald_raw','')),'depth_delta_cm':delta,'distance_m':round(dist,3),'exact_normalized_alias':alias,'strong_alias':strong_alias,'hypothesis':'identity_requires_provenance_review' if strong_alias and period_match else 'same_year_nearby_measurement_requires_provenance' if period_match else 'different_or_unknown_period_nearby_location'})

write_csv('candidate_inventory.csv',inventory)
write_csv('nearest_existing.csv',nearest)
write_csv('pairs_within_2000m.csv',pairs)
write_csv('surface_thaw_pairs.csv',[p for p in pairs if p['subset']=='surface_thaw'])
alias_index=collections.defaultdict(list)
for r in processed:
    for k in ['site_id','source_site_identifier','source_plot','calm_site_code','calm_site_name','site_location','Site_Name','SiteCode']:
        if norm(r.get(k,'')): alias_index[norm(r[k])].append((r,k))
alias_matches=[]
for l in loc:
    for key in {norm(l['SITE_ID']),norm(l['SITE_ID'].removeprefix('GINT_'))}:
        for r,k in alias_index.get(key,[]):
            alias_matches.append({'candidate_site_id':l['SITE_ID'],'candidate_project':l['PROJECT_NAME'],'candidate_date':l['START_DATE'],'existing_source':r['source'],'existing_site_id':r['site_id'],'existing_alias_field':k,'existing_alias':r[k],'existing_date':r['date'],'existing_source_period':r.get('source_period',''),'weak_local_label':len(key)<6,'existing_path':r['_path'],'existing_line':r['_line']})
write_csv('global_alias_matches.csv',alias_matches)
source_sites=collections.defaultdict(list)
for r in processed: source_sites[(r['source'],r['site_id'],r['lat'],r['lon'])].append(r)
write_csv('existing_regional_sites.csv',[{'source':k[0],'site_id':k[1],'lat':k[2],'lon':k[3],'rows':len(rs),'first_canonical_date':min(r['date'] for r in rs),'last_canonical_date':max(r['date'] for r in rs),'source_periods':';'.join(sorted({r.get('source_period','') for r in rs})),'aliases':';'.join(sorted({r.get(f,'') for r in rs for f in ['source_site_identifier','site_location','calm_site_code','calm_site_name','source_plot'] if r.get(f)}))} for k,rs in sorted(source_sites.items())])
sens=[]
for subset in ['all','permafrost_profile','surface_thaw']:
    for d in thresholds:
        ps=[p for p in pairs if (subset=='all' or p['subset']==subset or (subset=='permafrost_profile' and p['subset']=='surface_thaw')) and p['distance_m']<=d]
        same=[p for p in ps if p['same_period']]
        for tolerance in [1,5]:
            eq=[p for p in same if p['depth_delta_cm'] is not None and p['depth_delta_cm']<=tolerance]
            sens.append({'subset':subset,'radius_m':d,'depth_tolerance_cm':tolerance,'nearby_pairs':len(ps),'nearby_candidate_sites':len({p['candidate_site_id'] for p in ps}),'same_period_pairs':len(same),'same_period_candidate_sites':len({p['candidate_site_id'] for p in same}),'same_period_depth_agreement_pairs':len(eq),'same_period_depth_agreement_candidate_sites':len({p['candidate_site_id'] for p in eq}),'strong_alias_same_period_pairs':sum(p['strong_alias'] for p in same)})
write_csv('sensitivity.csv',sens)
summary={'archive_sha256':sha(ARCHIVE),'canonical_row_count':len(canonical),'regional_processed_row_count':len(processed),'regional_source_counts':dict(collections.Counter(r['source'] for r in processed)),'candidate_counts':dict(collections.Counter(r['audit_subset'] for r in inventory)),'candidate_coord_acq_counts':dict(collections.Counter(r['COORD_ACQ'] for r in loc)),'candidate_coordinate_decimal_digits':{'lat':dict(collections.Counter(digits(r['LATITUDE']) for r in loc)),'lon':dict(collections.Counter(digits(r['LONGITUDE']) for r in loc))},'pair_counts_by_source':dict(collections.Counter(r['existing_source'] for r in pairs)),'surface_thaw_pair_counts_by_source':dict(collections.Counter(r['existing_source'] for r in pairs if r['subset']=='surface_thaw')),'sensitivity':sens,'input_sha256':hashes,'exclusions':0,'decision':'Retain independent measurements; zero confirmed republished observations. Proximity/year/value are screening evidence only; no removal rule established.'}
summary['global_normalized_alias_matches']=len(alias_matches)
summary['global_strong_alias_matches']=sum(not r['weak_local_label'] for r in alias_matches)
summary['nearest_surface_thaw_distance_m']=min(r['nearest_distance_m'] for r in nearest if r['subset']=='surface_thaw')
assert sum(r['audit_subset']=='surface_thaw' for r in inventory)==73
assert not [p for p in pairs if p['subset']=='surface_thaw']
assert len({p['candidate_site_id'] for p in pairs if p['subset']!='other_location'})==44
assert not [p for p in pairs if p['subset']!='other_location' and p['same_period']]
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['input_sha256','sensitivity']},indent=2))
