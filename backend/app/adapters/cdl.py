"""USDA CroplandCROS classified point history. Never a farmer-confirmed crop record."""
import asyncio
import json
import math
import httpx
from app.adapters import NotCovered, ProviderUnavailable, SourceIntegrityError, content_hash

SERVICES={
 'conus':'https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer',
 'HI':'https://pdi.scinet.usda.gov/image/rest/services/CDL_WM_Hawaii/ImageServer',
}
CLASS_TO_CROP={1:'maize_grain',4:'sorghum_grain',5:'soybean'}


def normalize(raw,year,lon,lat):
    try:
        catalog,identified,legend=raw['catalog'],raw['identify'],raw['classes']
        if any('error' in x for x in (catalog,identified,legend)):raise ValueError('service returned an error')
        items=catalog['features']
        if len(items)!=1:raise ValueError('a single year-specific raster is required')
        attrs=items[0]['attributes']
        actual=identified['catalogItems']['features']
        if len(actual)!=1 or actual[0]['attributes']['OBJECTID']!=attrs['OBJECTID'] or attrs['Year']!=year:
            raise ValueError('returned raster does not match requested year')
        if actual[0]['attributes']['Year']!=year:raise ValueError('identified year mismatch')
        point=identified['location'];sr=point['spatialReference']
        if sr.get('latestWkid',sr['wkid'])!=3857:raise ValueError('unexpected returned CRS')
        if any(isinstance(point[k],bool) or not isinstance(point[k],(int,float)) or not math.isfinite(point[k]) for k in ('x','y')):
            raise ValueError('nonfinite returned point')
        x=6378137*math.radians(lon);y=6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))
        # Serialization precision in metres, not a field-scale accuracy tolerance.
        if abs(point['x']-x)>.01 or abs(point['y']-y)>.01:raise ValueError('returned point mismatch')
        value=identified['value']
        if value in ('NoData','No Data',None):code=None
        else:
            code=int(value)
            if str(code)!=str(value) or not 0<=code<=255:raise ValueError('invalid classification code')
        classes={r['attributes']['Value']:r['attributes'] for r in legend['features']}
        if code is not None and (code not in classes or not classes[code].get('Class_Names')):
            raise ValueError('classification has no verified label')
        resolution=attrs['LowPS']
        if isinstance(resolution,bool) or not isinstance(resolution,(int,float)) or not math.isfinite(resolution) or resolution<=0:
            raise ValueError('invalid raster resolution')
    except (KeyError,TypeError,ValueError,OverflowError) as e:raise SourceIntegrityError(str(e)) from e
    return dict(product='usda_cdl',year=year,status='no_data' if code in (None,0) else 'available',
                class_code=code,class_name=None if code is None else classes[code]['Class_Names'],
                catalog_crop_id=CLASS_TO_CROP.get(code),provenance='cdl',farmer_confirmed=False,
                raster_id=attrs['OBJECTID'],raster_name=attrs['Name'],catalog_low_pixel_size_m=resolution,
                point=dict(lon=lon,lat=lat),content_sha256=content_hash(raw),
                limitation='Classified pixel, not a field boundary, planting date or confirmed crop history. '
                           'Does not automatically alter farmer history or engine inputs.')


async def fetch(client,state,lon,lat,year):
    if state=='AK':raise NotCovered('Alaska CDL is not supported by this adapter')
    base=SERVICES['HI' if state=='HI' else 'conus']
    requests=[]
    async def get(path,params):
        async with asyncio.timeout(20):
            response=await client.get(base+path,params={'f':'json',**params},timeout=20)
        response.raise_for_status()
        data=response.json();requests.append(str(response.request.url))
        if 'error' in data:raise SourceIntegrityError('USDA service returned an error')
        return data
    try:
        catalog=await get('/query',dict(where=f'Year = {year}',outFields='*',returnGeometry='false'))
        if not catalog.get('features'):raise NotCovered('No raster for this year in this regional service')
        if len(catalog['features'])!=1:raise SourceIntegrityError('Ambiguous year-specific raster')
        rid=catalog['features'][0]['attributes']['OBJECTID']
        identified=await get('/identify',dict(geometry=json.dumps(dict(x=lon,y=lat,spatialReference=dict(wkid=4326))),
            geometryType='esriGeometryPoint',mosaicRule=json.dumps(dict(mosaicMethod='esriMosaicLockRaster',lockRasterIds=[rid])),
            renderingRule=json.dumps(dict(rasterFunction='None')),returnGeometry='false',returnCatalogItems='true',returnPixelValues='true'))
        classes=await get('/rasterAttributeTable',{})
    except (httpx.HTTPError,TimeoutError) as e:raise ProviderUnavailable('USDA crop-classification request failed') from e
    except (ValueError,KeyError,TypeError) as e:raise SourceIntegrityError('Malformed USDA crop-classification response') from e
    raw=dict(catalog=catalog,identify=identified,classes=classes)
    return raw,{**normalize(raw,year,lon,lat),'service':base,'requests':requests}
