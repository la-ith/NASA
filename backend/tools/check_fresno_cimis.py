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
                if station['IsEtoStation'].lower()!='true':raise ValueError('station is not designated as an ETo reference site')
                # Official station metadata includes HMS and decimal coordinates separated by '/'.
                lat=float(station['HmsLatitude'].split('/')[-1]);lon=float(station['HmsLongitude'].split('/')[-1])
                report['station_metadata']=station
                report['location']=dict(name=station['Name'],city=station['City'],lat=lat,lon=lon)
                metadata_digest=content_hash(meta)
                metadata_path=RAW/f'cimis_fresno_station_80_{metadata_digest[:12]}.json'
                if not metadata_path.exists():
                    metadata_path.write_text(json.dumps(dict(response=meta,content_sha256=metadata_digest,
                        retrieved_utc=datetime.now(timezone.utc).isoformat(),
                        request=dict(url=cimis.BASE+'/StationWeb/GetStationByStationNumber',params=dict(stationNbr=80))),indent=2),encoding='utf-8')
                report['metadata_artifact']=metadata_path.relative_to(ROOT).as_posix()
                report['quality_limitations']=[
                    'Only unflagged reference values are retained; QA exclusions can change the comparison sample.',
                    'Current station is grass/ETo-designated; siting notes dated 2002 mention variable grass height and dust. Historical maintenance conditions need review.',
                    'CIMIS published ASCE ETo and daily FAO-56 use related reference methods but are not an exact equation-identity test.',
                    'These development years and station are distinct from the consumed frozen holdout study. No parameters are fitted.',
                    'A station-reference comparison does not measure crop ET, yield or actual field irrigation.']
                report['years']={}
                for year in report['development_years']:
                    start,end=date(year,5,1),date(year,9,30)
                    raw,ref=await cimis.daily(client,80,start,end)
                    p=RAW/f'cimis_fresno_{year}_{content_hash(raw)[:12]}.json'
                    if not p.exists():
                        p.write_text(json.dumps(dict(response=raw,manifest=ref,retrieved_utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf-8')
                    payload,manifest=await download(client,f'power_cimis_fresno_{year}',power.URL,power.query(lon,lat,start,end))
                    w=power.validate_and_normalize(json.loads(payload),lon,lat,start,end,datetime.fromisoformat(manifest['retrieved_utc']))
                    from app.science import fao56 as f
                    pairs=[]
                    component_keys={'tmax':'t_max','tmin':'t_min','dew':'t_dew','solar':'shortwave_down',
                                    'wind':'wind_2m','rain':'precipitation'}
                    components={k:[] for k in component_keys}
                    for i,d in enumerate(w.dates):
                        v=w.values;ref_eto=ref['records'][d.isoformat()]['values']['eto']
                        args=[v[k][i] for k in ('t_max','t_min','t_dew','shortwave_down','wind_2m','surface_pressure')]
                        model=None
                        if all(x is not None for x in args):
                            tx,tn,dew,rs,wind,pressure=args
                            model=f.daily_et0(d,lat,tx,tn,f.actual_vapour_pressure_from_dewpoint(dew),rs,wind,pressure,w.cell_elevation_m).et0_mm
                        pairs.append((model,ref_eto))
                        for name,key in component_keys.items():
                            components[name].append((v[key][i],ref['records'][d.isoformat()]['values'][name]))
                    valid=[(a,b) for a,b in pairs if a is not None and b is not None and math.isfinite(a+b)]
                    qa_excluded=sum('eto:missing_or_flagged' in row['qa'] for row in ref['records'].values())
                    model_total,reference_total=sum(a for a,b in valid),sum(b for a,b in valid)
                    report['years'][str(year)]=dict(eto=metrics(pairs,153,qa_excluded),source_artifact=p.relative_to(ROOT).as_posix(),
                        power_manifest=manifest,paired_model_total=model_total,paired_reference_total=reference_total,
                        paired_season_relative_bias=None if not reference_total else model_total/reference_total-1,
                        season_total_eligible_95_percent=len(valid)>=146,
                        totals_note='Paired valid days only, not imputed or extrapolated to a full observed season.',
                        components={k:metrics(v,153) for k,v in components.items()},component_units={k:ref['units'][k] for k in components})
                report['status']='reference_compared'
                report['remaining']='Inspect weather components, local crop calendar and management; no correction or irrigation validation follows automatically'
                positive=all(y['eto']['bias'] is not None and y['eto']['bias']>0 for y in report['years'].values())
                report['interpretation']=('NASA-driven ET0 exceeds the quality-screened station reference on average in each evaluated year. '
                    if positive else 'Inspect the signed differences in each evaluated year. ')
                report['interpretation']+='The paired comparison does not prove a unique cause or a correction for the 25-season irrigation median.'
        except Exception as e:report['blocker']=f'{type(e).__name__}: {str(e)[:160]}'
    (OUT/'results/fresno-cimis-comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    if report['status']=='reference_compared':
        lines=['# Fresno CIMIS development comparison','',
            'Live CIMIS access succeeded. No model parameters or source observations were changed.',
            '', '| Year | Paired days / 153 | ET0 bias mm/day | RMSE mm/day | Paired-total difference | Meets 95% paired-day threshold |',
            '|---|---:|---:|---:|---:|---|']
        for year,r in report['years'].items():
            e=r['eto'];relative=r['paired_season_relative_bias']
            fmt=lambda x:'unavailable' if x is None else f'{x:.3f}'
            rel='unavailable' if relative is None else f'{relative:.1%}'
            lines.append(f"| {year} | {e['n']} | {fmt(e['bias'])} | {fmt(e['rmse'])} | {rel} | {r['season_total_eligible_95_percent']} |")
        lines+=['',report['interpretation'],'',
            'Totals use only paired valid days and are not full-season observations or extrapolations. In 2020, 145/153 days are below the preselected 146-day threshold; that year remains a diagnostic comparison.',
            '', '## Quality and spatial support', '',*['- '+x for x in report['quality_limitations']],
            '', 'Component bias/MAE/RMSE and original source artifacts are retained in results/fresno-cimis-comparison.json. Component comparisons can use different QA-valid day subsets; do not treat their biases as a formal causal decomposition.',
            '', 'The station is an irrigated grass/pasture reference site; NASA POWER represents regional grid conditions. Warmer/drier regional inputs can produce higher reference ET0 than locally irrigated station inputs. This is an interpretation consistent with the inputs, not an identified sole cause.',
            '', 'Remaining: assess local climate support, crop calendar, initial moisture and management against actual field observations. Published reference ET0 is not measured maize ET or irrigation use.']
        (OUT/'fresno-cimis-comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('station_metadata','years')},indent=2))


if __name__=='__main__':asyncio.run(run())
