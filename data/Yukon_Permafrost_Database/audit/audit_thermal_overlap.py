"""Screen 241 thermal station locations; annual summaries supply coverage only.

No annual temperature is interpreted as permafrost evidence here. -999 values,
nonnegative sensor depths and years before 1950 cannot establish coverage in this
screen. Raw measurements and completeness remain the ingestion processor's task.
"""
import csv,io,json,math,runpy,zipfile,collections
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
SOURCE=SCRIPT.parent
a=runpy.run_path(str(SCRIPT/'audit_overlap.py'))
OUT=a['OUT']
processed=a['processed'];period=a['period'];number=a['number'];norm=a['norm'];write=a['write_csv'];xyz=a['xyz'];chord=a['chord'];R=a['R']
def table(name): return list(csv.DictReader(io.StringIO((SOURCE/name).read_text(encoding='utf-8-sig').lstrip())))
stations=table('PFT_LOCATIONS.CSV');annual=table('V_PFT_SUMMARY_ANNUALLY.CSV');meta=table('V_PFT_SUMMARY_META.CSV')
years=collections.defaultdict(set)
for r in annual:
    if (number(r['ANNUALTEMP']) is not None and float(r['ANNUALTEMP'])>-100 and number(r['DEPTH']) is not None and float(r['DEPTH'])<0 and 1950<=int(r['YEAR'])<=2026): years[r['NAME']].add(int(r['YEAR']))
by_meta=collections.defaultdict(list)
for r in meta: by_meta[r['NAME']].append(r)
ex=xyz(processed,'lat','lon');pairs=[];nearest=[];aliases=[]
for s in stations:
    coord=xyz([s],'LATITUDE','LONGITUDE')[0]
    js=sorted(range(len(processed)),key=lambda j:chord(coord,ex[j]))
    first=processed[js[0]]; nd=2*R*math.asin(min(1,chord(coord,ex[js[0]])/2))
    nearest.append({**s,'annual_summary_valid_subsurface_years':';'.join(map(str,sorted(years[s['NAME']]))),'provider_method_ids':json.dumps(by_meta[s['NAME']]),'nearest_source':first['source'],'nearest_site_id':first['site_id'],'nearest_distance_m':round(nd,3)})
    for j in js:
        r=processed[j];dist=2*R*math.asin(min(1,chord(coord,ex[j])/2))
        alias=next((r.get(k) for k in ['site_id','source_site_identifier','calm_site_name','site_location','Site_Name'] if norm(r.get(k,''))==norm(s['NAME'])),'')
        if alias: aliases.append({'station':s['NAME'],'source':r['source'],'site_id':r['site_id'],'alias':alias})
        if dist>2000: continue
        lo,hi,basis=period(r); shared=sorted(y for y in years[s['NAME']] if lo is not None and lo<=y<=hi)
        pairs.append({'station':s['NAME'],'station_lat':s['LATITUDE'],'station_lon':s['LONGITUDE'],'station_accuracy_m':s['LOCATION_ACCURACY'],'station_pf_indicator':s['PERMAFROST'],'annual_summary_valid_subsurface_years':';'.join(map(str,sorted(years[s['NAME']]))),'existing_source':r['source'],'existing_site_id':r['site_id'],'existing_date':r['date'],'existing_period':r.get('source_period',''),'existing_period_basis':basis,'shared_years':';'.join(map(str,shared)),'existing_method':r.get('method'),'existing_thaw_cm':r.get('thaw_depth'),'existing_path':r['_path'],'existing_line':r['_line'],'distance_m':round(dist,3),'exact_alias':alias})
write('thermal_station_inventory.csv',nearest);write('thermal_pairs_within_2000m.csv',pairs);write('thermal_alias_matches.csv',aliases)
summary={'location_count':len(stations),'annual_summary_rows':len(annual),'stations_with_valid_subsurface_annual_values':len(years),'stations_within_2000m':sorted({r['station'] for r in pairs}),'stations_with_shared_years_within_2000m':sorted({r['station'] for r in pairs if r['shared_years']}),'exact_alias_matches':aliases,'temperature_archive_sha256':'bc7b954bd29399d67c94744c2f3e5bef7923079168fbbca125d6b6be7d4b91f7','location_accuracy_counts':dict(collections.Counter(s['LOCATION_ACCURACY'] for s in stations)),'sensitivity':[{'radius_m':d,'stations':len({r['station'] for r in pairs if r['distance_m']<=d}),'stations_shared_years':len({r['station'] for r in pairs if r['distance_m']<=d and r['shared_years']})} for d in [10,50,100,500,1000,2000]],'exclusions':0}
summary['stations_with_valid_subsurface_annual_values']=sum(bool(v) for v in years.values())
(OUT/'thermal_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
