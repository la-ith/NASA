"""NASA POWER supplemental products, deliberately separate from LST balance forcings."""
from datetime import date, timedelta
import asyncio
import math
from app.adapters import SourceIntegrityError, ProviderUnavailable, content_hash
from app.adapters import power

PRODUCTS={
 'gpm_imerg':dict(parameters={'IMERG_PRECTOT':'mm/day'},source='IMERG',start=date(2001,1,1),
                  unit='mm/day',meaning='UTC daily rainfall; context only, not mixed with LST forcing'),
 'smap':dict(parameters={'SFMC':'m3 m-3','RZMC':'m3 m-3'},source='SMAP',start=date(2015,3,31),
             unit='m3 m-3',meaning='Volumetric soil moisture, not field soil-water storage'),
}


def normalize(raw,product,start,end,lat,lon):
    cfg=PRODUCTS[product]
    try:
        header=raw['header'];values=raw['properties']['parameter'];meta=raw['parameters']
        point=raw['geometry']['coordinates']
        if not isinstance(header['sources'],list) or any(not isinstance(s,str) for s in header['sources']):
            raise ValueError('invalid source metadata')
        fill=header['fill_value']
        if isinstance(fill,bool) or not isinstance(fill,(int,float)) or not math.isfinite(fill):
            raise ValueError('invalid fill value')
        expected={ (start+timedelta(days=i)).strftime('%Y%m%d') for i in range((end-start).days+1)}
        if header['time_standard']!='UTC' or header['start']!=start.strftime('%Y%m%d') or header['end']!=end.strftime('%Y%m%d'):
            raise ValueError('time contract mismatch')
        if (point[1],point[0])!=(round(float(f'{lat:.4f}'),3),round(float(f'{lon:.4f}'),3)):
            raise ValueError('location mismatch')
        if set(values)!=set(cfg['parameters']) or set(meta)!=set(cfg['parameters']):raise ValueError('parameter mismatch')
        out={};valid=0
        for name,unit in cfg['parameters'].items():
            if meta[name]['units']!=unit or set(values[name])!=expected:raise ValueError('units/dates mismatch')
            out[name]={}
            for day,x in values[name].items():
                if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('nonfinite value')
                if x==header['fill_value']:out[name][day]=None;continue
                if x<0 or product=='smap' and x>1:raise ValueError('impossible physical value')
                out[name][day]=x;valid+=1
        if valid and not any(cfg['source'] in s.upper() for s in header['sources']):
            raise ValueError('source does not confirm requested product; no silent MERRA2 substitution')
    except (KeyError,TypeError,ValueError) as e:raise SourceIntegrityError(str(e)) from e
    return dict(product=product,status='available' if valid else 'no_data',values=out,valid_values=valid,
        expected_values=len(expected)*len(cfg['parameters']),time_standard='UTC',units=cfg['parameters'],
        source_metadata=header,content_sha256=content_hash(raw),meaning=cfg['meaning'],
        limitation='Does not alter the historical LST simulation. Product quality and field representativeness still require review.')


async def fetch(client,product,lat,lon,start,end):
    cfg=PRODUCTS[product]
    if start<cfg['start']:raise SourceIntegrityError('requested period predates configured product support')
    query=dict(parameters=','.join(cfg['parameters']),community='AG',latitude=f'{lat:.4f}',longitude=f'{lon:.4f}',
        start=start.strftime('%Y%m%d'),end=end.strftime('%Y%m%d'),format='JSON',**{'time-standard':'UTC'})
    try:
        async with asyncio.timeout(40):
            response=await client.get(power.URL,params=query,timeout=40)
        response.raise_for_status();raw=response.json()
    except Exception as e:raise ProviderUnavailable('Supplemental provider request failed') from e
    result=normalize(raw,product,start,end,lat,lon)
    result['request']=query
    return raw,result
