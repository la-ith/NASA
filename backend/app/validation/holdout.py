"""Frozen, non-tuning external evaluation. Opening these groups consumes them as holdouts."""
import asyncio
import copy
import csv
import hashlib
import json
import math
from datetime import date,datetime,timezone
from pathlib import Path
import numpy as np
import httpx
from app.adapters import power
from app.science import fao56
from app.validation.pilot import ROOT,RAW,OUT,SITES,download,evaluate_site

PROTOCOL=ROOT/'data/catalogs/validation_protocol_v1.json'
LOCK=OUT/'protocol-lock-v1.json'


def load_protocol():
    protocol=json.loads(PROTOCOL.read_text(encoding='utf-8'))
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()!=lock['sha256']:
        raise ValueError('Frozen protocol changed; do not evaluate or relabel these data as untouched')
    return protocol,lock


def evaluate_gates(metrics,protocol):
    if 'blocker' in metrics:return dict(status='blocked',reasons=[metrics['blocker']])
    reasons=[]
    eto=metrics['eto'];total=metrics['eto_season_total'];g=protocol['gates']['eto']
    if eto['n']<math.ceil(153*protocol['minimum_paired_fraction']):reasons.append('insufficient paired ET0 days')
    if eto['bias'] is None or abs(eto['bias'])>g['max_abs_daily_bias_mm']:reasons.append('ET0 daily bias gate failed')
    if eto['rmse'] is None or eto['rmse']>g['max_daily_rmse_mm']:reasons.append('ET0 daily RMSE gate failed')
    if not total['available'] or not total['reference_sum']:
        reasons.append('ET0 paired season total unavailable')
    elif abs(total['model_sum']/total['reference_sum']-1)>g['max_abs_paired_season_relative_bias']:
        reasons.append('ET0 season relative bias gate failed')
    rain=metrics['rain_season_total'];g=protocol['gates']['rain']
    if not rain['available']:reasons.append('insufficient paired rain days')
    elif rain['reference_sum']<g['minimum_reference_total_mm_for_relative_gate']:
        reasons.append('rain reference total too small for relative gate')
    elif abs(rain['model_sum']/rain['reference_sum']-1)>g['max_abs_paired_season_relative_bias']:
        reasons.append('rain season relative bias gate failed')
    return dict(status='failed' if reasons else 'passed',reasons=reasons)


def bias_interval(errors,protocol):
    """Fixed calendar-week blocks; missing days are never imputed."""
    if not errors:return None
    blocks={}
    for day,error in errors:blocks.setdefault((day-date(day.year,5,1)).days//7,[]).append(error)
    blocks=[np.asarray(x) for x in blocks.values()]
    rng=np.random.default_rng(protocol['uncertainty']['seed'])
    estimates=[]
    for _ in range(protocol['uncertainty']['replicates']):
        draw=rng.integers(0,len(blocks),len(blocks))
        estimates.append(float(np.concatenate([blocks[k] for k in draw]).mean()))
    low,high=np.quantile(estimates,[.025,.975])
    return dict(bias_95_percent_interval=[float(low),float(high)],blocks=len(blocks),n=len(errors),
                interpretation=protocol['uncertainty']['meaning'])


def et0_errors(result,year):
    artifact=result['artifacts'][0]
    weather=power.validate_and_normalize(json.loads((RAW/artifact['file']).read_bytes()),
       result['site']['lon'],result['site']['lat'],date.fromisoformat(result['weather_manifest']['period'][0]),
       date.fromisoformat(result['weather_manifest']['period'][1]),datetime.fromisoformat(artifact['retrieved_utc']))
    ref=json.loads((OUT/'results'/f'normalized_{result["site"]["id"]}_{year}.json').read_text(encoding='utf-8'))
    errors=[];v=weather.values
    for i,d in enumerate(weather.dates):
        if d.year!=year or not 5<=d.month<=9:continue
        observed=ref.get(d.isoformat(),{}).get('values',{}).get('eto')
        needed=[v[k][i] for k in ('t_max','t_min','t_dew','shortwave_down','wind_2m','surface_pressure')]
        if observed is None or any(x is None for x in needed):continue
        tmax,tmin,dew,rs,wind,pressure=needed
        model=fao56.daily_et0(d,weather.latitude,tmax,tmin,fao56.actual_vapour_pressure_from_dewpoint(dew),rs,
                             wind,pressure,weather.cell_elevation_m).et0_mm
        if math.isfinite(model):errors.append((d,model-observed))
    return errors


async def run():
    protocol,lock=load_protocol()
    # Persist before issuing the first weather request. The lock prevents silent protocol changes.
    if not lock['evaluation_started']:
        lock.update(evaluation_started=True,first_opened_utc=datetime.now(timezone.utc).isoformat())
        LOCK.write_text(json.dumps(lock,indent=2),encoding='utf-8')
    async with httpx.AsyncClient(timeout=45,follow_redirects=True) as client:
        meta,meta_manifest=await download(client,'holdout_coagmet_metadata',
            'https://coagmet.colostate.edu/data/metadata.json',dict(stations='ftc01,akr02,gly04',units='m',instruments='yes'))
        coag=json.loads(meta)
        names,names_manifest=await download(client,'holdout_kansas_metadata','https://mesonet.k-state.edu/rest/stationnames/')
        colby=next(x for x in csv.DictReader(names.decode().splitlines()) if x['NAME']=='Colby')
        _,az_manifest=await download(client,'holdout_az01_metadata','https://azmet.arizona.edu/about/station-metadata/az01')
        sites=copy.deepcopy(SITES)
        for s in sites:
            if s['id']=='ftc01':
                s.update(height=coag['ftc01']['anemometerHeight'],elevation=coag['ftc01']['elevation'],
                         wind_height_status='Current official metadata; historical instrument-era confirmation remains pending')
        sites.append(dict(id='az01',network='azmet',lat=32.28,lon=-110.95,elevation=714,height=3,
                          reference='published AZMET Penman-Monteith grass ETo',metadata=az_manifest))
        for sid in ('akr02','gly04'):
            m=coag[sid]
            sites.append(dict(id=sid,network='coagmet',lat=m['lat'],lon=m['lon'],elevation=m['elevation'],
                height=m['anemometerHeight'],reference='published ASCE short-reference ETo',metadata=meta_manifest,
                wind_height_status='Current official metadata; historical instrument-era confirmation remains pending'))
        sites.append(dict(id='colby',network='kansas',station_name='Colby',lat=float(colby['LATITUDE']),
            lon=float(colby['LONGITUDE']),elevation=float(colby['ELEVATION']),height=2,metadata=names_manifest,
            reference='station-forced FAO56; same calculation method, independent measured inputs'))
        results=[]
        for group,g in protocol['groups'].items():
            for sid in g['sites']:
                site=next(x for x in sites if x['id']==sid)
                result=await evaluate_site(client,site,tuple(g['years']),group)
                for year,metrics in result['years'].items():
                    metrics['gates']=evaluate_gates(metrics,protocol)
                    if 'blocker' not in metrics:metrics['uncertainty']=bias_interval(et0_errors(result,int(year)),protocol)
                result['qualification']='diagnostic_only_known_siting_issue' if sid=='ftc01' else 'engineering_screening_only'
                results.append(result)
                print(group,sid,{y:m['gates']['status'] for y,m in result['years'].items()},flush=True)
    report=dict(protocol=protocol,protocol_lock=lock,engine_tuned=False,holdouts_consumed=True,results=results,
                field_irrigation_accuracy='not validated; no measured crop irrigation outcomes in this study',
                expert_review='pending',time_alignment='CoAgMet MST; POWER LST; Kansas end stamps corrected; residual sub-day windows disclosed')
    eligible=[m['gates']['status'] for r in results if r['site']['id']!='ftc01' for m in r['years'].values()]
    report['engineering_weather_screening']='passed' if len(eligible)==18 and all(x=='passed' for x in eligible) else 'not_qualified'
    report['scientific_release_ready']=False
    target=OUT/'results/holdout-evaluation-v1.json'
    target.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    lines=['# Frozen holdout evaluation v1','',f"Engineering weather screening: **{report['engineering_weather_screening']}**.",
           'Field irrigation accuracy is not validated. Expert agronomic review remains pending. No model parameters were tuned.',
           '', '| Group | Station | Year | ET0 bias mm/day | RMSE mm/day | Gate |', '|---|---|---|---:|---:|---|']
    for r in results:
        for y,m in r['years'].items():
            e=m.get('eto',{});fmt=lambda x:'unavailable' if x is None else f'{x:.3f}'
            lines.append(f"| {r['group']} | {r['site']['id']} | {y} | {fmt(e.get('bias'))} | {fmt(e.get('rmse'))} | {m['gates']['status']} |")
    lines+=['','Gates are provisional product screening limits fixed before opening data, not published guarantees. FTC01 is diagnostic-only because of known siting concerns. See JSON for missingness, failed gates, paired-season totals, block-bootstrap intervals and source hashes.',
            '', 'These evaluation groups are now consumed. After any parameter tuning, use fresh untouched data for a new final evaluation.']
    (OUT/'holdout-evaluation-v1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':asyncio.run(run())
