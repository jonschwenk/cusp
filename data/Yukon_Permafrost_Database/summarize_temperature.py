"""Stream the full raw thermal export once; preserve annual maxima/coverage."""
import argparse
import calendar
import collections
import csv
from datetime import datetime, date
import io
import json
import hashlib
from pathlib import Path
import time
import zipfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive',type=Path,default=Path(__file__).parent/'temperature.zip')
parser.add_argument('--output-dir',type=Path,default=Path(__file__).parent)
args=parser.parse_args()
HERE=args.output_dir
HERE.mkdir(parents=True,exist_ok=True)
with args.archive.open('rb') as source:
    digest=hashlib.file_digest(source,'sha256').hexdigest()
if digest!='bc7b954bd29399d67c94744c2f3e5bef7923079168fbbca125d6b6be7d4b91f7':
    raise ValueError('Thermal export changed: review before regenerating evidence.')
z=zipfile.ZipFile(args.archive)
def rows(name):
    stream=io.TextIOWrapper(z.open(name),encoding='utf-8-sig',newline='')
    next(stream) # provider leading blank line
    return csv.DictReader(stream)
locations={r['ID']:r for r in rows('PFT_LOCATIONS.CSV')}
methods={r['ID']:r for r in rows('PFT_METHOD.CSV')}
for name in ['PFT_LOCATIONS.CSV','PFT_METHOD.CSV','PFT_WHO.CSV','V_PFT_SUMMARY_ANNUALLY.CSV']:
    (HERE/name).write_bytes(z.read(name))
date_cache={}
groups={}
types=collections.Counter()
excluded=collections.Counter()
thaw=[]
start=time.monotonic()
for i,r in enumerate(rows('PFT_OBSERVATIONS.CSV'),1):
    types[r['OBSERVATION_TYPE']]+=1
    if r['OBSERVATION_TYPE']=='Thaw depth':
        thaw.append(r)
    if r['OBSERVATION_TYPE']!='Ground temperature':
        excluded['not_ground_temperature']+=1; continue
    try:
        lo,hi=float(r['DEPTH_MIN']),float(r['DEPTH_MAX'])
        value=float(r['NUMERICAL_VALUE'])
    except ValueError:
        excluded['missing_numeric_or_depth']+=1; continue
    if lo!=hi or not -10<=lo<0:
        excluded['not_point_subsurface_at_most_10m']+=1; continue
    if not -50<=value<=40:
        excluded['invalid_or_sentinel_temperature']+=1; continue
    text=r['TIME_START']
    if text not in date_cache:
        try: date_cache[text]=datetime.strptime(text,'%d-%b-%y').date()
        except ValueError: date_cache[text]=None
    day=date_cache[text]
    if day is None or not 1990<=day.year<=2025 or r['TIME_START']!=r['TIME_END']:
        excluded['invalid_date_or_interval_summary']+=1; continue
    key=(r['LOCATION_ID'],lo,day.year)
    g=groups.setdefault(key,{'n':0,'max':-999.,'min':999.,'days':0,'methods':set(),'who':set(),'comments':set()})
    g['n']+=1; g['max']=max(g['max'],value); g['min']=min(g['min'],value)
    g['days']|=1<<((day-date(day.year,1,1)).days)
    g['methods'].add(r['METHOD_ID']); g['who'].add(r['WHO_ID'])
    if r['COMMENTS']:g['comments'].add(r['COMMENTS'])
    if i%1000000==0:print(i,round(time.monotonic()-start,1),flush=True)
output=[]
for (loc,depth,year),g in sorted(groups.items()):
    nday=366 if calendar.isleap(year) else 365
    mask=format(g['days'],f'0{nday}b')[::-1]
    maxgap=max(map(len,mask.split('1')))
    accuracies=[float(methods[m]['ACCURACY']) for m in g['methods'] if m in methods and methods[m]['ACCURACY']]
    accuracy=max(accuracies) if len(accuracies)==len(g['methods']) else None
    output.append(dict(location_id=loc,name=locations.get(loc,{}).get('NAME',''),depth_m=-depth,year=year,
        n=g['n'],days=g['days'].bit_count(),coverage=g['days'].bit_count()/nday,maxgap=maxgap,
        max_temp=g['max'],min_temp=g['min'],accuracy=accuracy,methods=';'.join(sorted(g['methods'])),
        who=';'.join(sorted(g['who'])),comments=' | '.join(sorted(g['comments'])),day_mask=str(g['days'])))
with (HERE/'thermal_annual_audit.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=output[0]); w.writeheader();w.writerows(output)
assert i==32722705 and len(output)==7979, 'Unexpected raw thermal snapshot counts'
summary={'raw_rows':i,'types':dict(types),'excluded':dict(excluded),'annual_point_groups':len(output),'thaw_depth_rows':len(thaw),'seconds':time.monotonic()-start,'archive_sha256':digest}
(HERE/'thermal_inventory.json').write_text(json.dumps(summary,indent=2))
if thaw:
    with (HERE/'thermal_explicit_thaw.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=thaw[0]);w.writeheader();w.writerows(thaw)
print(json.dumps(summary,indent=2),flush=True)
