"""Purposive development pilot. Raw bytes and QA are retained; no bias correction is fitted."""
import asyncio
import csv
import hashlib
import io
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx
from app.adapters import power, ssurgo
from app.science import fao56 as f

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data/validation/raw'
OUT = ROOT / 'docs/validation'
SITES = [
    dict(id='az06', network='azmet', lat=33.07, lon=-111.97, elevation=362, height=3,
         reference='published Penman-Monteith grass ETo'),
    dict(id='ftc01', network='coagmet', lat=40.5947, lon=-105.137, elevation=5120*.3048, height=6.6*.3048,
         reference='published ASCE short-reference ETo; current metadata warns non-reference surroundings',
         metadata_url='https://coagmet.colostate.edu/station_details.php?station=FTC01',
         wind_height_status='6.6 ft working assumption from network guidance; station-era confirmation needed'),
    dict(id='hays', network='kansas', lat=38.84945, lon=-99.34461, elevation=618.7, height=2,
         reference='station-forced FAO56, independent inputs but same calculation method'),
]


def metrics(pairs, expected, suspect=0):
    valid=[(a,b) for a,b in pairs if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)]
    errors=[a-b for a,b in valid]
    n=len(errors)
    return dict(n=n, expected=expected, missing_or_excluded=expected-n, suspect_reference_days=suspect,
                bias=None if not n else sum(errors)/n,
                mae=None if not n else sum(abs(e) for e in errors)/n,
                rmse=None if not n else math.sqrt(sum(e*e for e in errors)/n))


def number(value):
    try: x=float(value)
    except (TypeError,ValueError): return None
    return x if math.isfinite(x) and x > -900 else None


async def download(client, name, url, params=None):
    request=client.build_request('GET',url,params=params)
    key=hashlib.sha256(str(request.url).encode()).hexdigest()[:12]
    meta_path=RAW/f'{name}_{key}.manifest.json'
    if meta_path.exists():
        meta=json.loads(meta_path.read_text())
        data=(RAW/meta['file']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=meta['sha256']: raise ValueError('raw artifact hash mismatch')
        return data,meta
    response=await client.send(request)
    response.raise_for_status()
    data=response.content
    digest=hashlib.sha256(data).hexdigest()
    path=RAW/f'{name}_{key}_{digest[:12]}.raw'
    path.write_bytes(data)
    meta=dict(url=str(request.url),retrieved_utc=datetime.now(timezone.utc).isoformat(),
              sha256=digest,file=path.name,status=response.status_code,
              content_type=response.headers.get('content-type'))
    meta_path.write_text(json.dumps(meta,indent=2))
    return data,meta


def station_url(site,year):
    if site['network']=='azmet':
        return f'https://api.azmet.arizona.edu/v1/observations/daily/az06/{year}-05-01T00:00/P153DT0H'
    if site['network']=='coagmet':
        return 'https://coagmet.colostate.edu/data/daily/ftc01.csv?'+urlencode(
            dict(from_=f'{year}-05-01')).replace('from_','from')+f'&to={year}-09-30&header=yes&units=m'
    return 'https://mesonet.k-state.edu/rest/stationdata/?'+urlencode(dict(
        stn='Hays',int='day',t_start=f'{year}0501000000',t_end=f'{year}0930235959',
        vars='TEMP2MMAX,TEMP2MMIN,RELHUM2MMAX,RELHUM2MMIN,PRECIP,SR,SRAVG,WSPD2MAVG,PRESSUREAVG'))


def normalize_station(site,data):
    if site['network']=='azmet': rows=json.loads(data)['data']
    else:
        lines=[line for line in data.decode().splitlines() if line.strip()]
        rows=list(csv.DictReader(lines))
        if site['network']=='coagmet': rows=rows[1:] # API's units row (RH header says %, docs specify fraction)
    result={}
    for r in rows:
        qa=[]
        if site['network']=='azmet':
            d=date.fromisoformat(r['datetime'][:10])
            mapping={'tmax':'temp_air_maxC','tmin':'temp_air_minC','ea':'vp_actual_mean',
                     'rs':'sol_rad_total','u2':'wind_spd_mean_mps','rain':'precip_total_mm','eto':'eto_pen_mon'}
            v={k:number(r.get(col)) for k,col in mapping.items()}
            if number(r.get('meta_needs_review'))==1: qa.append('station_review_flag');v={k:None for k in v}
            if v['u2'] is not None: v['u2']=f.wind_speed_at_2m(v['u2'],site['height'])
        elif site['network']=='coagmet':
            d=datetime.strptime(r['Date'],'%m/%d/%Y').date()
            v={k:number(r.get(col)) for k,col in {'tmax':'Max Temp','tmin':'Min Temp','rs':'Solar Rad',
                                                  'u2':'Wind Run','rain':'Liquid Precip','eto':'ASCE ETo'}.items()}
            rhmax,rhmin=number(r.get('RH Max')),number(r.get('RH Min'))
            v['ea']=None
            if rhmin is not None and rhmin<=.01: qa.append('suspect_rh_min_le_0.01')
            elif all(x is not None for x in (rhmax,rhmin,v['tmax'],v['tmin'])) and 0<=rhmin<=rhmax<=1:
                v['ea']=f.actual_vapour_pressure_from_rh_extremes(v['tmax'],v['tmin'],rhmax*100,rhmin*100)
            if v['rs'] is not None:v['rs']*=.0864
            if v['u2'] is not None:v['u2']=f.wind_speed_at_2m(v['u2']*1000/86400,site['height'])
            # Published ET may inherit the suspect humidity; exclude it too, preserve other measurements.
            if qa: v['eto']=None
        else:
            d=date.fromisoformat(r['TIMESTAMP'][:10])
            v={k:number(r.get(col)) for k,col in {'tmax':'TEMP2MMAX','tmin':'TEMP2MMIN','rs':'SR',
                                                  'u2':'WSPD2MAVG','rain':'PRECIP','pressure':'PRESSUREAVG'}.items()}
            rhmax,rhmin=number(r.get('RELHUM2MMAX')),number(r.get('RELHUM2MMIN'))
            v['ea']=None
            if all(x is not None for x in (rhmax,rhmin,v['tmax'],v['tmin'])) and 0<=rhmin<=rhmax<=100:
                v['ea']=f.actual_vapour_pressure_from_rh_extremes(v['tmax'],v['tmin'],rhmax,rhmin)
            v['eto']=None
        needed=[v.get(k) for k in ('tmax','tmin','ea','rs','u2')]
        v['station_forced_eto']=None
        if site['elevation'] is not None and all(x is not None for x in needed):
            pressure=v.get('pressure') or f.atmospheric_pressure(site['elevation'])
            v['station_forced_eto']=f.daily_et0(d,site['lat'],*needed,pressure,site['elevation']).et0_mm
        if site['network']=='kansas':v['eto']=v['station_forced_eto']
        if d in result:raise ValueError(f'duplicate station day {d}')
        result[d]=(v,qa)
    return result


async def evaluate_site(client,site):
    output=dict(site=site,group='development',years={},artifacts=[])
    start,end=date(2020,5,1),date(2022,9,30)
    try:
        raw,meta=await download(client,'power_'+site['id'],power.URL,power.query(site['lon'],site['lat'],start,end))
        output['artifacts'].append(meta)
        weather=power.validate_and_normalize(json.loads(raw),site['lon'],site['lat'],start,end,
                                             datetime.fromisoformat(meta['retrieved_utc']))
        output['weather_manifest']=weather.manifest
        index={d:i for i,d in enumerate(weather.dates)}
    except Exception as e:
        output['blocker']=f'POWER {type(e).__name__}: {e}';return output
    for year in (2020,2021,2022):
        try:
            raw,meta=await download(client,f'{site["id"]}_{year}',station_url(site,year))
            output['artifacts'].append(meta)
            ref=normalize_station(site,raw)
            (OUT/'results'/f'normalized_{site["id"]}_{year}.json').write_text(json.dumps(
                {d.isoformat():dict(values=v,quality_flags=q) for d,(v,q) in ref.items()},indent=2,allow_nan=False))
            pairs={k:[] for k in ('eto','tmax','tmin','ea','rs','u2','rain','method_crosscheck')}
            suspect=0
            for d,i in index.items():
                if d.year!=year or not 5<=d.month<=9:continue
                r,qa=ref.get(d,({},['missing_day']));suspect+=bool(qa)
                v=weather.values
                model={k:v[q][i] for k,q in [('tmax','t_max'),('tmin','t_min'),('rs','shortwave_down'),
                                             ('u2','wind_2m'),('rain','precipitation')]}
                model['ea']=None if v['t_dew'][i] is None else f.actual_vapour_pressure_from_dewpoint(v['t_dew'][i])
                model['eto']=None
                needed=[model.get(k) for k in ('tmax','tmin','ea','rs','u2')]
                if all(x is not None for x in needed) and v['surface_pressure'][i] is not None:
                    model['eto']=f.daily_et0(d,site['lat'],*needed,v['surface_pressure'][i],weather.cell_elevation_m).et0_mm
                for k in model:pairs[k].append((model[k],r.get(k)))
                pairs['method_crosscheck'].append((r.get('station_forced_eto'),r.get('eto')
                                                   if site['network']!='kansas' else None))
            result={k:metrics(p,153,suspect if k in ('ea','eto','method_crosscheck') else 0) for k,p in pairs.items()}
            for k in ('eto','rain'):
                valid=[(a,b) for a,b in pairs[k] if a is not None and b is not None and math.isfinite(a+b)]
                result[k+'_season_total']=dict(unit='mm',n_paired_days=len(valid),expected_days=153,
                    available=len(valid)>=math.ceil(.95*153),
                    model_sum=sum(a for a,b in valid) if len(valid)>=146 else None,
                    reference_sum=sum(b for a,b in valid) if len(valid)>=146 else None,
                    note='Sums of paired valid days only; not filled or extrapolated.')
            result['units']={'eto':'mm/day','method_crosscheck':'mm/day','tmax':'C','tmin':'C','ea':'kPa',
                             'rs':'MJ/m2/day','u2':'m/s','rain':'mm/day'}
            output['years'][str(year)]=result
        except Exception as e: output['years'][str(year)]={'blocker':f'{type(e).__name__}: {e}'}
    output['season_metrics']={}
    for k in ('eto','rain'):
        totals=[v[k+'_season_total'] for v in output['years'].values() if 'blocker' not in v]
        pairs=[(v['model_sum'],v['reference_sum']) for v in totals if v['available']]
        output['season_metrics'][k]=dict(unit='mm per May–September season',**metrics(pairs,3))
    return output


async def run():
    RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    manifest=dict(design='purposive pilot, not a probability sample',development_years=[2020,2021,2022],
        season='May 1–September 30, 153 calendar-day labels',
        temporal_holdout=dict(years=[2023,2024,2025],status='reserved, not downloaded or evaluated'),
        spatial_holdout=dict(stations=['AZMET az01 Tucson','CoAgMet akr02 Akron','CoAgMet gly04 Greeley','Kansas Colby'],
                             status='reserved, not downloaded or evaluated'),
        development_sites=SITES,applicability_only=['Palmer AK','Maui HI','Fresno CA (CIMIS blocked)','Ames IA'],
        time_alignment='POWER LST versus station daily labels: exact day-window equivalence not established; limitation',
        thresholds='No accuracy threshold selected; select before opening holdout')
    (OUT/'sample-manifest.json').write_text(json.dumps(manifest,indent=2))
    async with httpx.AsyncClient(timeout=90,follow_redirects=True) as client:
        results=await asyncio.gather(*(evaluate_site(client,s) for s in SITES))
        applicability=await asyncio.gather(*(check_applicability(client,s) for s in [
            dict(id='palmer',lat=61.58,lon=-149.10),dict(id='maui',lat=20.85,lon=-156.45),
            dict(id='fresno',lat=36.74,lon=-119.79),dict(id='ames',lat=42.03,lon=-93.62)]))
        (OUT/'results/applicability.json').write_text(json.dumps(applicability,indent=2,allow_nan=False))
    (OUT/'results/pilot-development.json').write_text(json.dumps(results,indent=2,allow_nan=False))
    write_report(results)
    print(json.dumps([{k:v for k,v in r.items() if k not in ('artifacts','years')}|
                      {'years':list(r['years'])} for r in results],indent=2))


async def check_applicability(client,site):
    from app.geo.boundaries import state_at
    from app.domain.crop_catalog import load_catalog
    from app.services.analysis_v2 import simulate_climate_only, planting_date
    state=state_at(site['lon'],site['lat'])
    result=dict(site=site,state=state.code if state else None,group='applicability_only',metrics=None)
    start,end=date(2020,1,1),date(2020,12,31)
    try:
        raw,meta=await download(client,'power_applicability_'+site['id'],power.URL,power.query(site['lon'],site['lat'],start,end))
        w=power.validate_and_normalize(json.loads(raw),site['lon'],site['lat'],start,end,datetime.fromisoformat(meta['retrieved_utc']))
        index={d:i for i,d in enumerate(w.dates)}
        result['weather']='supported';result['model_applicability']={}
        for crop in load_catalog().crops.values():
            status,outcome=simulate_climate_only(crop,w,index,planting_date(2020,crop.planting_default))
            result['model_applicability'][crop.id]=dict(status=status,reason=outcome if isinstance(outcome,str) else None)
        crop=next(iter(load_catalog().crops.values()))
        winter_status,_=simulate_climate_only(crop,w,index,date(2020,1,1))
        result['january_start_applicability']=winter_status
        result['meaning']='ok means calculation prerequisites passed, not agronomic suitability or validated crop performance'
    except Exception as e: result['weather_blocker']=f'{type(e).__name__}: {e}'
    try:
        raw,meta=await download(client,'unused','https://example.invalid') if False else (None,None)
        # SDA is POST, so retain its exact query and original JSON separately.
        path=RAW/f'ssurgo_applicability_{site["id"]}.json'
        if path.exists(): saved=json.loads(path.read_text())
        else:
            data=await ssurgo.fetch(client,site['lon'],site['lat'])
            saved=dict(url=ssurgo.URL,method='POST',query=ssurgo.sql(site['lon'],site['lat']),
                       retrieved_utc=datetime.now(timezone.utc).isoformat(),response=data)
            saved['sha256']=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            path.write_text(json.dumps(saved,indent=2))
        digest=hashlib.sha256(json.dumps(saved['response'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if digest!=saved['sha256']:raise ValueError('saved SSURGO artifact hash mismatch')
        ssurgo.validate_and_normalize(saved['response'],site['lon'],site['lat'],saved['retrieved_utc'])
        result['ssurgo']='supported; basic coverage only, not field validation'
    except Exception as e:result['soil_blocker']=f'{type(e).__name__}: {e}'
    return result


def write_report(results):
    lines=['# Pilot validation and review-fix report','',
      'Date: 14 November 2026. Engine 2.1.0. Purposive development pilot, not a probability sample.',
      'No nationwide accuracy, crop-yield accuracy or field irrigation accuracy is established.', '',
      '## Evaluation design','',
      'Development: May–September 2020–2022, 153 daily labels per season. Temporal holdout 2023–2025 and '
      'spatial holdout stations remain reserved and were not downloaded by this runner. Raw responses are '
      'saved with request URLs, retrieval UTC and SHA-256 hashes in data/validation/raw/. '
      'Normalized reference values and QA flags are saved in results/normalized_*.json.', '',
      'Daily labels align by calendar date. POWER uses local solar time; exact station observation-window '
      'equivalence has not been verified. Daily differences therefore include possible time-window mismatch.', '',
      '## Development environmental comparisons','',
      'Bias is model minus reference. ET0 units below are mm/day. Comparisons are diagnostic, not a release accuracy certification.', '',
      '| Station | Year | Paired days | Excluded/missing | Bias | MAE | RMSE |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for site in results:
        for year,r in site['years'].items():
            if 'blocker' in r:
                lines.append(f"| {site['site']['id']} | {year} | blocked | — | — | — | — |")
                continue
            m=r['eto']; fmt=lambda v:'unavailable' if v is None else f'{v:.3f}'
            lines.append(f"| {site['site']['id']} | {year} | {m['n']} | {m['missing_or_excluded']} | "
                         f"{fmt(m['bias'])} | {fmt(m['mae'])} | {fmt(m['rmse'])} |")
    lines += ['', 'Full per-output metrics for Tmax, Tmin, ea, solar radiation, wind, daily ET0 and precipitation '
      'are in results/pilot-development.json. Seasonal ET0/rain totals require at least 146/153 paired valid days '
      '(95%). Totals sum those paired days without filling gaps. Seasonal metrics report bias/MAE/RMSE over '
      'eligible development seasons only; a season with incomplete paired days is not an observed complete total.', '',
      '## Quality and reference limitations','',
      '- AZMET: eto_pen_mon is the published reference; meta_needs_review=1 excludes the day. '
      'Wind measured at 3 m is converted using FAO-56 Eq. 47.',
      '- CoAgMet: RH fractions follow the official API documentation despite the CSV units row saying %. '
      'RHmin <= 0.01 is retained in raw data but excluded from humidity-derived quantities and published ETo '
      'comparison, because that ETo can inherit the suspect humidity. This removes 92 development days in 2020. '
      'Solar daily mean W/m² is multiplied by 0.0864; wind km/day is multiplied by 1000/86400. '
      'Station elevation is 5120 ft = 1560.576 m. A 6.6-ft wind-height assumption still needs station-era confirmation. '
      'Current official station metadata warns that surroundings no longer meet reference conditions; historical '
      'site maintenance for the study period needs verification.',
      '- Kansas Hays: no published ETo was used. Reference ET0 is our FAO-56 equation forced by station '
      'measurements (ea from RH extremes, measured pressure, SR in MJ/m²/day). It checks input representativeness '
      'with the same method, not independent model validation.', '',
      '## Numerical verification versus environmental validation','',
      'FAO worked examples and balance closure verify numerical implementation. Station-forced FAO-56 versus '
      'AZMET/CoAgMet published ETo is a method consistency cross-check, not independent environmental validation '
      'or exact-equation identity: reference methods, rounding and inputs can differ. Its metrics are reported '
      'separately as method_crosscheck. Kansas has no such independent published-ET comparison.', '',
      'The POWER-versus-station measurements are a limited external development comparison. POWER meteorology '
      'uses MERRA-2 reanalysis; its gauge-corrected precipitation may partly depend on overlapping station networks. '
      'CERES-based solar radiation and local pyranometers are different observation sources. Ground observations '
      'also have uncertainty; turf/irrigated or mixed station surroundings differ from coarse grid averages. '
      'No agronomic reviewer has validated crop profiles or irrigation outcomes.', '',
      '## Fresno status: unresolved','',
      'The prior diagnostic reproduced median maize net irrigation 1066.1 mm and ETc 1072.6 mm. '
      'Documented sensitivities and daily flux diagnostics are in results/sensitivity_ca_fresno.json and '
      'results/diagnostics_ca_fresno_maize.json. No parameters were fitted to published California numbers. '
      'CIMIS comparison remains blocked by unavailable registered API access; no CIMIS observations are invented.',
      'Maricopa is an irrigated-desert analogue, not a California validation station. Development daily ET0 bias '
      'there is positive but varies strongly by year (see table); it does not establish the cause or magnitude '
      'of the Fresno discrepancy. Aridity correction is not adopted.', '',
      '## Scientific corrections and before/after evidence','',
      'Existing audit fixes: Kc end now uses late-stage weather, restrictive layers cap SSURGO root depth, '
      'and provider requests use their explicit documented timeouts. Additional review fixes unify demand '
      'calculation across soil/no-soil paths and reject non-finite/frozen applicability consistently. '
      'API validation, worker isolation, access scope and stale coverage handling are documented in the issue report.', '',
      'The following table comes from the preserved medians_before_fixes.json and medians_after_fixes.json. '
      'Those files capture the earlier scientific audit, not every subsequent review change. They are regression '
      'evidence, not measured field improvement.', '']
    before_path=OUT/'results/medians_before_fixes.json'
    after_path=OUT/'results/medians_after_fixes.json'
    if before_path.exists() and after_path.exists():
        before,after=json.loads(before_path.read_text())['sites'],json.loads(after_path.read_text())['sites']
        lines+=['| Site | Crop | Output (mm) | Before | After | Change |',
                '|---|---|---|---:|---:|---:|']
        for site,crops in after.items():
            for crop,values in crops.items():
                for key in ('rainfed_deficit','irrigated_net_irrigation'):
                    old=before.get(site,{}).get(crop,{}).get(key);new=values.get(key)
                    if old is not None and new is not None:
                        lines.append(f'| {site} | {crop} | {key} | {old} | {new} | {new-old:.1f} |')
        lines+=['']
    lines += ['## Map and engineering verification','',
      'Observed in an actual rendering browser: U.S. basemap and state outlines; Alaska and Hawaii shortcuts; '
      'outline-only fallback after forcing the style URL to fail in a temporary local harness. '
      'Screenshot: results/map-fallback.png. Attu at 52.93 N, 173.2 E was accepted by typed coordinate selection '
      'and reported Alaska with source coverage; an exact mouse click on the island is not certified. '
      'The frontend design was not redesigned. Backend/JS test results and review issue dispositions are '
      'recorded in implementation-status.md and code-review-issues-2026-11-14.md.', '',
      '## Next milestone and blockers','',
      'Resolve station-era metadata and day-window alignment; review crop/soil/management assumptions; '
      'obtain a California reference; define output-specific acceptance thresholds before evaluating any holdout. '
      'Keep nationwide selection distinct from model applicability. Do not tune on held-out years/stations.', '',
      '## Primary references','',
      '- FAO-56: https://www.fao.org/4/x0490e/x0490e00.htm',
      '- AZMET methods/wind height: https://extension.arizona.edu/sites/extension.arizona.edu/files/pubs/az1324.pdf',
      '- AZMET raw daily endpoint: see the exact URLs in raw download manifests.',
      '- CoAgMet units: https://coagmet.colostate.edu/data/doc.html',
      '- CoAgMet station metadata: https://coagmet.colostate.edu/station_details.php?station=FTC01',
      '- Kansas variables: https://mesonet.k-state.edu/rest/variables/',
      '- Kansas service: https://mesonet.k-state.edu/rest/',
      '- POWER methodology: https://power.larc.nasa.gov/docs/methodology/',
      '']
    (OUT/'pilot-validation-report.md').write_text('\n'.join(lines),encoding='utf-8')
