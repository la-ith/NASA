"""National source imagery plus immutable derived-grid catalog and tiles."""
import asyncio
from datetime import date
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import Response,FileResponse
from app.adapters import AdapterError
from app.services import raster_layers as layers

router=APIRouter(prefix='/api/v2/map')


@router.get('/build-status')
async def build_status():
    import json
    path=layers.LAYER_ROOT/'national-build-status.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(state='not_started')


@router.get('/layers')
async def catalog():
    return dict(scope='50 US states including Alaska across the antimeridian and Hawaii',
        source_layers=[{**x,'tiles':f'/api/v2/map/nasa/{x["id"]}/{{date}}/{{z}}/{{x}}/{{y}}.png',
                        'bounds':[-180,18,180,72],'clipped_to':'US50 Census boundary','attribution':'NASA GIBS; see source-layer metadata',
                        'quantitative_pixel_query':False} for x in layers.GIBS['layers']],
        derived_grids=layers.derived_catalog(),
        distinction='NASA imagery is pre-rendered context. Derived deficit rasters require the separate daily physical-model pipeline.')


@router.get('/nasa/{layer_id}/{day}/{z}/{x}/{y}.png')
async def nasa(layer_id:str,day:date,z:int,x:int,y:int,request:Request):
    try:
        layers.tile_bounds(z,x,y)
        data=await layers.nasa_tile(request.app.state.http,layer_id,day,z,x,y)
    except KeyError:raise HTTPException(404,'unknown layer')
    except ValueError as e:raise HTTPException(422,str(e))
    except AdapterError as e:raise HTTPException(502,dict(code=e.code,message=str(e)))
    return Response(data,media_type='image/png',headers={'Cache-Control':'public, max-age=3600'})


@router.get('/grids/{artifact_id}')
async def manifest(artifact_id:str):
    try:return layers.derived_manifest(artifact_id)
    except KeyError:raise HTTPException(404,'unknown grid')


@router.get('/grids/{artifact_id}/data.tif')
async def cog(artifact_id:str):
    try:layers.derived_manifest(artifact_id)
    except KeyError:raise HTTPException(404,'unknown grid')
    return FileResponse(layers.LAYER_ROOT/'published'/artifact_id/'data.tif',media_type='image/tiff')


@router.get('/grids/{artifact_id}/records')
async def records(artifact_id:str):
    try:layers.derived_manifest(artifact_id)
    except KeyError:raise HTTPException(404,'unknown grid')
    return FileResponse(layers.LAYER_ROOT/'published'/artifact_id/'records.json',media_type='application/json')


@router.get('/grids/{artifact_id}/{metric}/value')
async def value(artifact_id:str,metric:str,lon:float,lat:float):
    try:return layers.derived_value(artifact_id,metric,lon,lat)
    except KeyError:raise HTTPException(404,'unknown grid or quantity')
    except ValueError as e:raise HTTPException(422,str(e))


@router.get('/grids/{artifact_id}/{metric}/{z}/{x}/{y}.png')
async def tile(artifact_id:str,metric:str,z:int,x:int,y:int):
    try:return Response(await asyncio.to_thread(layers.derived_tile,artifact_id,metric,z,x,y),media_type='image/png')
    except KeyError:raise HTTPException(404,'unknown grid or quantity')
    except ValueError as e:raise HTTPException(422,str(e))
