"""US50-masked NASA imagery and quantitative COG tiles. Never infer data from image colours."""
import asyncio
import hashlib
import io
import json
import math
import os
from datetime import date
from datetime import datetime,timezone
from functools import lru_cache
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import rasterize
from affine import Affine
from rasterio.warp import transform_geom,reproject,Resampling
from PIL import Image
from app.adapters import ProviderUnavailable,SourceIntegrityError
from app.geo.boundaries import BOUNDARY_FILE

ROOT=Path(__file__).resolve().parents[3]
LAYER_ROOT=Path(os.environ.get('FIELD_SHIFT_LAYER_DIR',str(ROOT/'outputs/scientific-layers')))
GIBS=json.loads((ROOT/'data/catalogs/nasa_gibs_layers.json').read_text(encoding='utf-8'))
LIMIT=20037508.342789244


def tile_bounds(z,x,y):
    if not 0<=z<=12 or not 0<=x<2**z or not 0<=y<2**z:raise ValueError('tile index outside supported range')
    span=2*LIMIT/2**z
    return (-LIMIT+x*span,LIMIT-(y+1)*span,-LIMIT+(x+1)*span,LIMIT-y*span)


def tile_transform(z,x,y):
    left,bottom,right,top=tile_bounds(z,x,y)
    return Affine((right-left)/256,0,left,0,(bottom-top)/256,top)


@lru_cache(maxsize=1)
def shapes_3857():
    data=json.loads(BOUNDARY_FILE.read_text(encoding='utf-8'))
    return [transform_geom('EPSG:4326','EPSG:3857',f['geometry']) for f in data['features']]


@lru_cache(maxsize=256)
def us_mask(z,x,y):
    return rasterize([(g,1) for g in shapes_3857()],out_shape=(256,256),
                     transform=tile_transform(z,x,y),fill=0,dtype='uint8')


def png(array):
    out=io.BytesIO();Image.fromarray(array).save(out,format='PNG');return out.getvalue()


def gibs_layer(layer_id):
    layer=next((x for x in GIBS['layers'] if x['id']==layer_id),None)
    if layer is None:raise KeyError(layer_id)
    return layer


def date_supported(layer,day):
    return any(date.fromisoformat(interval.split('/')[0])<=day<=date.fromisoformat(interval.split('/')[1])
               for interval in layer['intervals'])


async def nasa_tile(client,layer_id,day,z,x,y):
    layer=gibs_layer(layer_id)
    if z>layer['maxzoom'] or not date_supported(layer,day):raise ValueError('unsupported source date or zoom; no silent latest-date substitution')
    mask=us_mask(z,x,y)
    if not mask.any():return png(np.zeros((256,256,4),dtype='uint8'))
    url=layer['tile_template'].format(Time=day.isoformat(),TileMatrixSet=layer['matrix_set'],TileMatrix=z,TileRow=y,TileCol=x)
    cache=LAYER_ROOT/'source-tiles'/layer_id/day.isoformat()/str(z)/str(x)/f'{y}.png'
    if cache.exists():
        raw=cache.read_bytes()
        manifest=cache.with_suffix('.manifest.json')
        if not manifest.exists() or hashlib.sha256(raw).hexdigest()!=json.loads(manifest.read_text(encoding='utf-8'))['sha256']:
            raise SourceIntegrityError('cached NASA imagery failed its source hash check')
    else:
        try:
            async with asyncio.timeout(25):response=await client.get(url,timeout=25)
            response.raise_for_status();raw=response.content
        except Exception as e:raise ProviderUnavailable('NASA imagery request failed') from e
        try:
            im=Image.open(io.BytesIO(raw));im.load()
            if im.format!='PNG' or im.size!=(256,256):raise ValueError('unexpected tile dimensions or format')
        except Exception as e:raise SourceIntegrityError('invalid NASA PNG tile') from e
        cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_bytes(raw)
        cache.with_suffix('.manifest.json').write_text(json.dumps(dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),
            source_date=day.isoformat(),source_layer=layer['source_layer'],retrieved_utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf-8')
    # Native no-data alpha is retained, and countries/ocean outside the US scope become transparent.
    rgba=np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA')).copy()
    rgba[:,:,3]=np.where(mask,rgba[:,:,3],0)
    return png(rgba)


def derived_catalog():
    if not (LAYER_ROOT/'published').exists():return []
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((LAYER_ROOT/'published').glob('*/manifest.json'))]


def derived_manifest(artifact_id):
    if len(artifact_id)!=32 or any(x not in '0123456789abcdef' for x in artifact_id):raise KeyError(artifact_id)
    path=LAYER_ROOT/'published'/artifact_id/'manifest.json'
    if not path.exists():raise KeyError(artifact_id)
    return json.loads(path.read_text(encoding='utf-8'))


def derived_tile(artifact_id,metric,z,x,y):
    m=derived_manifest(artifact_id)
    if metric not in m['bands']:raise KeyError(metric)
    grid=np.full((256,256),np.nan,dtype='float32')
    path=LAYER_ROOT/'published'/artifact_id/'data.tif'
    with rasterio.open(path) as source:
        reproject(rasterio.band(source,m['bands'][metric]),grid,src_transform=source.transform,src_crs=source.crs,
                  src_nodata=source.nodata,dst_transform=tile_transform(z,x,y),dst_crs='EPSG:3857',
                  dst_nodata=np.nan,resampling=Resampling.nearest)
    valid=np.isfinite(grid)&(us_mask(z,x,y)>0)
    high=m['legend_max'][metric]
    t=np.clip(np.nan_to_num(grid,nan=0)/high,0,1)
    rgba=np.zeros((256,256,4),dtype='uint8')
    rgba[:,:,0]=(255*t).astype('uint8');rgba[:,:,1]=(170*(1-t)).astype('uint8');rgba[:,:,2]=(255*(1-t)).astype('uint8')
    rgba[:,:,3]=valid.astype('uint8')*220
    return png(rgba)


def derived_value(artifact_id,metric,lon,lat):
    from app.geo.boundaries import state_at
    if state_at(lon,lat) is None:raise ValueError('outside US50 scope')
    m=derived_manifest(artifact_id)
    if metric not in m['bands']:raise KeyError(metric)
    with rasterio.open(LAYER_ROOT/'published'/artifact_id/'data.tif') as source:
        value=float(next(source.sample([(lon,lat)],indexes=m['bands'][metric]))[0])
    from app.services.layers import METRICS
    return dict(value=value if math.isfinite(value) and value!=-9999 else None,unit=m['units'][metric],
                spatial_support=m['spatial_support'],result_type=METRICS[metric][2],
                coverage=m['coverage'],validation='field accuracy not established')
