"""Development-only Fresno station ET0 comparison; no parameter fitting or irrigation-accuracy claim."""
import asyncio
import json
import math
import os
import re
import sys
from datetime import date,datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import load_private_env
from app.adapters import cimis,power,content_hash
from app.validation.pilot import ROOT,RAW,OUT,download,metrics
import httpx


async def run():
    load_private_env()
    report=dict(development_years=[2020,2021,2022],station=80,location='Fresno State; station metadata must confirm location',
        checked_utc=datetime.now(timezone.utc).isoformat(),status='blocked',calibration_applied=False,
        limitation='Published reference ET0 comparison is not measured maize water use or irrigation validation')
    if not os.environ.get('CIMIS_APP_KEY'):report['blocker']='CIMIS_APP_KEY not configured'
    else:
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                meta=await cimis.fetch(client,'/StationWeb/GetStationByStationNumber',dict(stationNbr=80))
                station=next(x for x in meta['Stations'] if int(x['StationNbr'])==80)
                # Official station metadata includes HMS and decimal coordinates separated by '/'.
                lat=float(station['HmsLatitude'].split('/')[-1]);lon=float(station['HmsLongitude'].split('/')[-1])
                report['station_metadata']=station
                report['years']={}
                for year in report['development_years']:
                    start,end=date(year,5,1),date(year,9,30)
                    raw,ref=await cimis.daily(client,80,start,end)
                    p=RAW/f'cimis_fresno_{year}_{content_hash(raw)[:12]}.json'
                    p.write_text(json.dumps(dict(response=raw,manifest=ref,retrieved_utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf-8')
                    payload,manifest=await download(client,f'power_cimis_fresno_{year}',power.URL,power.query(lon,lat,start,end))
                    w=power.validate_and_normalize(json.loads(payload),lon,lat,start,end,datetime.fromisoformat(manifest['retrieved_utc']))
                    from app.science import fao56 as f
                    pairs=[]
                    for i,d in enumerate(w.dates):
                        v=w.values;ref_eto=ref['records'][d.isoformat()]['values']['eto']
                        args=[v[k][i] for k in ('t_max','t_min','t_dew','shortwave_down','wind_2m','surface_pressure')]
                        model=None
                        if all(x is not None for x in args):
                            tx,tn,dew,rs,wind,pressure=args
                            model=f.daily_et0(d,lat,tx,tn,f.actual_vapour_pressure_from_dewpoint(dew),rs,wind,pressure,w.cell_elevation_m).et0_mm
                        pairs.append((model,ref_eto))
                    valid=[(a,b) for a,b in pairs if a is not None and b is not None and math.isfinite(a+b)]
                    report['years'][str(year)]=dict(eto=metrics(pairs,153),source_artifact=p.relative_to(ROOT).as_posix(),
                        power_manifest=manifest,paired_model_total=sum(a for a,b in valid),paired_reference_total=sum(b for a,b in valid))
                report['status']='reference_compared'
                report['remaining']='Inspect weather components, local crop calendar and management; no correction or irrigation validation follows automatically'
        except Exception as e:report['blocker']=f'{type(e).__name__}: {str(e)[:160]}'
    (OUT/'results/fresno-cimis-comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('station_metadata','years')},indent=2))


if __name__=='__main__':asyncio.run(run())
