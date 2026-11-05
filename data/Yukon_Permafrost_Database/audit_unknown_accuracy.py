"""Sensitivity only: these hypothetical thermal observations are NOT ingested."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).parent
with (HERE/'thermal_annual_audit.csv').open() as f: rows=list(csv.DictReader(f))
with (HERE/'PFT_LOCATIONS.CSV').open() as f:
    locations={r['ID']:r for r in csv.DictReader(line for line in f if line.strip())}
groups={(r['location_id'],r['depth_m'],int(r['year'])):r for r in rows}
out=[]
for margin in (.25,.5,1.0):
    chosen={}
    for (site,depth,year),r in groups.items():
        p=groups.get((site,depth,year-1))
        if not p or (r['accuracy'] and p['accuracy']):continue
        if locations[site]['PERMAFROST'].lower()=='no':continue
        if any(float(v['coverage'])<.95 or int(v['maxgap'])>7 or float(v['max_temp'])>=-margin for v in (p,r)):continue
        if r['methods']!=p['methods'] or r['who']!=p['who'] or r['comments'] or p['comments']:continue
        key=(site,year)
        if key not in chosen or float(depth)<float(chosen[key]['depth_m']):chosen[key]=r
    for (site,year),r in chosen.items():
        out.append(dict(assumed_margin_c=margin,site_id=locations[site]['NAME'],year=year,depth_m=r['depth_m'],metadata_pf=locations[site]['PERMAFROST'],max_temp=r['max_temp'],prior_max_temp=groups[(site,r['depth_m'],year-1)]['max_temp'],decision='sensitivity_only_unknown_accuracy_not_ingested'))
with (HERE/'unknown_accuracy_sensitivity.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['assumed_margin_c','site_id','year','depth_m','metadata_pf','max_temp','prior_max_temp','decision']);w.writeheader();w.writerows(out)
print(json.dumps({str(m):sum(r['assumed_margin_c']==m for r in out) for m in (.25,.5,1.)},indent=2))
