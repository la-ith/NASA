"""Live development-only probes. Saves original payloads and manifest hashes; never reads holdouts.

Run from backend: python tools/check_backend_sources.py
"""
import asyncio
from datetime import date,datetime,timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.adapters import content_hash,power,ssurgo,supplemental,cdl
from app.services.analysis_v2 import soil_from_ssurgo
from app.services.run_v2 import run_analysis
from app.domain.crop_catalog import load_catalog
from app.geo.boundaries import state_at

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/validation/raw'
OUT=ROOT/'docs/validation/results/backend-source-checks.json'


def save(name,raw,manifest):
    digest=content_hash(raw)
    path=RAW/f'backend_{name}_{digest[:12]}.json'
    snapshot=dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),content_sha256=digest,
                  manifest=manifest,response=raw)
    if not path.exists():path.write_text(json.dumps(snapshot,indent=2,allow_nan=False),encoding='utf-8')
    return path.relative_to(ROOT).as_posix()


async def run():
    RAW.mkdir(parents=True,exist_ok=True)
    report=dict(retrieved_utc=datetime.now(timezone.utc).isoformat(),scope='development probes only',checks={})
    checks=report['checks']
    async with httpx.AsyncClient(timeout=20) as client:
        async def weather():
            raw=await power.fetch(client,-99.33,38.85,date(2020,1,1),date(2020,12,31))
            w=power.validate_and_normalize(raw,-99.33,38.85,date(2020,1,1),date(2020,12,31),power.now_utc())
            artifact=save('power_hays_2020',raw,w.manifest)
            soilraw=await ssurgo.fetch(client,-99.33,38.85)
            p=ssurgo.validate_and_normalize(soilraw,-99.33,38.85,power.now_utc().isoformat())
            save('ssurgo_hays',soilraw,p.manifest)
            restrictions=await ssurgo.fetch_restrictions(client,-99.33,38.85)
            p=ssurgo.apply_restrictions(p,restrictions,power.now_utc().isoformat())
            save('ssurgo_restrictions_hays',restrictions,p.manifest['restrictions'])
            result=run_analysis(dict(lat=38.85,lon=-99.33,start_year=2020,end_year=2020,
                goal='conserve_water',initial_depletion_fraction=.5),state_at(-99.33,38.85),w,soil_from_ssurgo(p),load_catalog(),'live')
            return dict(status=result['status'],artifact=artifact,days=len(w.dates),
                missing={q:w.missing(q) for q in power.VARIABLES},
                strategies=[dict(crop=s['crop'],seasons=s['result']['seasons']) for s in result['strategies']],
                validation=result['validation'])
        async def product(name):
            raw,r=await supplemental.fetch(client,name,38.85,-99.33,date(2020,5,1),date(2020,5,3))
            return dict(status=r['status'],valid_values=r['valid_values'],expected_values=r['expected_values'],
                        artifact=save(name,raw,r))
        async def crop(state,lon,lat):
            raw,r=await cdl.fetch(client,state,lon,lat,2020)
            return dict(status=r['status'],class_code=r['class_code'],class_name=r['class_name'],
                        year=r['year'],farmer_confirmed=r['farmer_confirmed'],artifact=save('cdl_'+state,raw,r))
        async def check(name,fn):
            try:
                async with asyncio.timeout(90):checks[name]=await fn()
            except Exception as e:checks[name]=dict(status='blocked',error_type=type(e).__name__,message=str(e))
        await asyncio.gather(check('power_and_balance',weather),check('gpm_imerg',lambda:product('gpm_imerg')),
                             check('smap',lambda:product('smap')),check('cdl_conus',lambda:crop('KS',-99.33,38.85)),
                             check('cdl_hawaii',lambda:crop('HI',-156.45,20.85)))
    OUT.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='strategies'} for k,v in checks.items()},indent=2))


if __name__=='__main__':asyncio.run(run())
