"""Current CIMIS station API. AppKey is sent only in the subscription header, never a URL/log."""
import asyncio
import math
import os
from datetime import date,timedelta
import httpx
from app.adapters import NotCovered,ProviderUnavailable,SourceIntegrityError,content_hash

BASE='https://et.water.ca.gov'
ITEMS={
 'eto':('day-asce-eto','DayAsceEto',{'(mm)':1}),
 'rain':('day-precip','DayPrecip',{'(mm)':1}),
 'tmax':('day-air-tmp-max','DayAirTmpMax',{'(C)':1,'(°C)':1}),
 'tmin':('day-air-tmp-min','DayAirTmpMin',{'(C)':1,'(°C)':1}),
 'dew':('day-dew-pnt','DayDewPnt',{'(C)':1,'(°C)':1}),
 'solar':('day-sol-rad-avg','DaySolRadAvg',{'(W/sq.m)':.0864,'(W/m²)':.0864}),
 'wind':('day-wind-spd-avg','DayWindSpdAvg',{'(m/s)':1}),
}


def normalize(raw,station,start,end):
    expected={start+timedelta(days=i) for i in range((end-start).days+1)}
    out={d.isoformat():dict(values={k:None for k in ITEMS},qa=['missing_record']) for d in sorted(expected)}
    try:
        providers=raw['Data']['Providers'];seen=set()
        for provider in providers:
            if provider['Name'].lower()!='cimis' or provider['Type']!='station':raise ValueError('unexpected reference provider')
            for row in provider['Records']:
                d=date.fromisoformat(row['Date'])
                if d not in expected or d in seen or int(row['Station'])!=station or row['Scope']!='daily':
                    raise ValueError('CIMIS date, station or scope mismatch')
                if row['Standard'].lower()!='metric':raise ValueError('CIMIS did not return metric data')
                seen.add(d);values={};qa=[]
                for key,(_,field,units) in ITEMS.items():
                    v=row.get(field)
                    if v is None:values[key]=None;qa.append(key+':missing_item');continue
                    if v['Unit'] not in units:raise ValueError(f'unexpected CIMIS unit for {field}')
                    if v['Value'] is None or str(v.get('Qc','')).strip():
                        values[key]=None;qa.append(key+':missing_or_flagged');continue
                    if isinstance(v['Value'],bool):raise ValueError('boolean CIMIS measurement')
                    x=float(v['Value'])*units[v['Unit']]
                    if not math.isfinite(x) or key in ('eto','rain','solar','wind') and x<0:raise ValueError('invalid CIMIS value')
                    values[key]=x
                if values['tmax'] is not None and values['tmin'] is not None and values['tmin']>values['tmax']:
                    raise ValueError('CIMIS minimum exceeds maximum')
                out[d.isoformat()]=dict(values=values,qa=qa)
    except (KeyError,TypeError,ValueError) as e:raise SourceIntegrityError(str(e)) from e
    if not seen:raise NotCovered('No CIMIS station records returned for this interval')
    original_units={field:sorted({row[field]['Unit'] for provider in providers for row in provider['Records']
                                if isinstance(row.get(field),dict) and isinstance(row[field].get('Unit'),str)})
                    for _,field,_ in ITEMS.values()}
    return dict(station=station,records=out,adapter_version='cimis-station-1.1',original_units=original_units,
                reference='CIMIS published ASCE grass-reference ETo; not observed crop ET',
                qc='Only unflagged nonmissing values retained; all original QC flags remain in raw response',
                units=dict(eto='mm/day',rain='mm/day',tmax='C',tmin='C',dew='C',solar='MJ/m2/day',wind='m/s'),
                content_sha256=content_hash(raw))


async def fetch(client,path,params):
    key=os.environ.get('CIMIS_APP_KEY')
    if not key:raise ProviderUnavailable('CIMIS_APP_KEY is not configured privately')
    try:
        async with asyncio.timeout(40):
            response=await client.get(BASE+path,params=params,
                headers={'Ocp-Apim-Subscription-Key':key,'Accept':'application/json'},timeout=40)
        response.raise_for_status();return response.json()
    except Exception as e:
        # Never stringify transport exceptions: their request may contain sensitive provider diagnostics.
        status=response.status_code if 'response' in locals() else None
        raise ProviderUnavailable(f'CIMIS request failed; HTTP status {status or "unavailable"}') from None


async def daily(client,station,start,end):
    if start>end or (end-start).days>365:raise ValueError('CIMIS reference request must span at most 366 ordered days')
    params=dict(stationNbrs=str(station),startDate=start.isoformat(),endDate=end.isoformat(),isHourly='false',
                unitOfMeasure='M',dataItems=','.join(x[0] for x in ITEMS.values()))
    raw=await fetch(client,'/StationWeb/GetDataByStationNumber',params)
    return raw,{**normalize(raw,station,start,end),'request':dict(url=BASE+'/StationWeb/GetDataByStationNumber',params=params)}
