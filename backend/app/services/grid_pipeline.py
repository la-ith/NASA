"""Resumable native-meteorology-grid scenarios. Every populated cell is calculated from its own sources."""
import asyncio
import hashlib
import json
from datetime import date
from pathlib import Path
import numpy as np
import rasterio
from affine import Affine
from app.adapters import content_hash,power
from app.db.database import connect
from app.domain.crop_catalog import load_catalog
from app.geo.boundaries import state_at,BOUNDARY_VERSION,BOUNDARY_FILE
from app.services import sources_v2
from app.services.analysis_v2 import ENGINE_VERSION,simulate_season,simulate_climate_only,planting_date
from app.services.layers import METRICS
from app.services.raster_layers import LAYER_ROOT
import httpx

DX,DY=.625,.5
WIDTH,HEIGHT=576,113
WEST,NORTH=-180.3125,73.25
BANDS={name:i+1 for i,name in enumerate(METRICS)}
GRID_SCHEMA='grid-cog-1.0'


def plan(states=None):
    """One representative point per native meteorological cell; coastal subpixels are not inferred."""
    known={x['properties']['stusps'] for x in json.loads(BOUNDARY_FILE.read_text(encoding='utf-8'))['features']}
    if states and set(states)-known:raise ValueError('unknown state codes in grid plan')
    cells=[]
    for row in range(HEIGHT):
        lat=73-row*DY
        for col in range(WIDTH):
            lon=-180+col*DX
            state=state_at(lon,lat)
            if state and (not states or state.code in states):
                cells.append(dict(id=f'{row}-{col}',row=row,col=col,lat=lat,lon=lon,state=state.code))
    return cells


async def calculate_cell(cell,year,crop_id,db,client):
    weather=await sources_v2.weather(db,client,cell['lon'],cell['lat'],date(year,1,1),date(year,12,31),'live')
    soil=await sources_v2.soil(db,client,cell['lon'],cell['lat'],'live',None)
    crop=load_catalog().crops[crop_id];start=planting_date(year,crop.planting_default)
    index={d:i for i,d in enumerate(weather.dates)}
    if soil.soil:
        from app.science.crop import layered_total_available_water
        depth=min(crop.root_depth_m,soil.soil.depth_cm/100)
        taw=layered_total_available_water(soil.soil.awc_by_horizon,depth)
        status,result=await asyncio.to_thread(simulate_season,crop,weather,index,start,taw,soil.soil.curve_number,.5)
    else:status,result=await asyncio.to_thread(simulate_climate_only,crop,weather,index,start)
    return dict(cell=cell,status=status,reason=result if isinstance(result,str) else None,
        values={key:getattr(result,key) for key in BANDS} if status=='ok' else {},
        provenance=dict(weather=weather.manifest,soil=soil.soil.manifest if soil.soil else None),
        soil_coverage=soil.coverage,soil_support='dominant SSURGO component at cell centre; not area-averaged soil')


def publish(records,job,planned_count):
    data=np.full((len(BANDS),HEIGHT,WIDTH),-9999,dtype='float32')
    for record in records:
        if record.get('status')!='ok':continue
        cell=record['cell']
        for key,band in BANDS.items():
            v=record['values'].get(key)
            if v is not None and np.isfinite(v):data[band-1,cell['row'],cell['col']]=v
    digest=content_hash(dict(schema=GRID_SCHEMA,job=job,records=records))[:32]
    dest=LAYER_ROOT/'published'/digest
    if (dest/'manifest.json').exists():return json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
    dest.mkdir(parents=True,exist_ok=True)
    with rasterio.open(dest/'data.tif','w',driver='COG',height=HEIGHT,width=WIDTH,count=len(BANDS),
        dtype='float32',crs='EPSG:4326',transform=Affine(DX,0,WEST,0,-DY,NORTH),nodata=-9999,
        compress='DEFLATE',blocksize=256,overview_resampling='nearest') as target:
        target.write(data)
        for name,band in BANDS.items():target.set_band_description(band,name)
    raster_sha=hashlib.sha256((dest/'data.tif').read_bytes()).hexdigest()
    completed=sum(x.get('status')=='ok' for x in records)
    m=dict(schema=GRID_SCHEMA,artifact_id=digest,job=job,bands=BANDS,units={k:v[1] for k,v in METRICS.items()},
        result_types={k:v[2] for k,v in METRICS.items()},
        raster_sha256=raster_sha,format='Cloud Optimized GeoTIFF',crs='EPSG:4326',
        spatial_support='0.5 degree latitude × 0.625 degree longitude meteorological grid-centre scenarios; radiation is coarser 1 degree',
        coverage=dict(planned_cells=planned_count,processed_cells=len(records),computed_cells=completed,
                      complete=len(records)==planned_count,excluded_cells=sum(x.get('status') not in ('ok','provider_error') for x in records),
                      note='Uncomputed, unsupported, coastal/land-centre gaps and missing-source cells are nodata, never interpolated'),
        source_versions=dict(engine=ENGINE_VERSION,crop_catalog=load_catalog().version,boundary=BOUNDARY_VERSION),
        assumptions=['Fixed source-tabulated crop calendar for every cell; not locally confirmed planting dates',
                     'Soil is a cell-centre SSURGO scenario, not a mapped average of the entire climate cell',
                     'Initial depletion 0.5 TAW; fixed maximum roots; no crop yield, profit or forecast',
                     'Fresno and nationwide field irrigation accuracy remain unvalidated'],
        legend_max={k:float(max(1,np.max(data[i-1][data[i-1]!=-9999]))) if np.any(data[i-1]!=-9999) else 1 for k,i in BANDS.items()},
        tiles={k:f'/api/v2/map/grids/{digest}/{k}/{{z}}/{{x}}/{{y}}.png' for k in BANDS},
        cog_url=f'/api/v2/map/grids/{digest}/data.tif',records_url=f'/api/v2/map/grids/{digest}/records')
    (dest/'records.json').write_text(json.dumps(records,allow_nan=False),encoding='utf-8')
    (dest/'manifest.json').write_text(json.dumps(m,indent=2,allow_nan=False),encoding='utf-8')
    return m


async def build(year,crop_id,states=None,max_cells=None):
    if crop_id not in load_catalog().crops:raise ValueError('crop not in supported source-traced catalog')
    if not 1981<=year<date.today().year:raise ValueError('a complete historical year is required')
    cells=plan(states);job=dict(year=year,crop=crop_id,states=sorted(states) if states else 'US50',engine=ENGINE_VERSION,
                              crop_catalog=load_catalog().version,boundary=BOUNDARY_VERSION,
                              initial_depletion_fraction=.5,calendar='catalog default',soil='cell-centre SSURGO')
    key=content_hash(job)[:32];work=LAYER_ROOT/'builds'/key;work.mkdir(parents=True,exist_ok=True)
    (work/'plan.json').write_text(json.dumps(dict(job=job,cell_count=len(cells),cells=cells)),encoding='utf-8')
    db=connect(str(LAYER_ROOT/'grid-sources.db'))
    records=[];requests=0
    try:
        async with httpx.AsyncClient() as client:
            for cell in cells:
                target=work/(cell['id']+'.json')
                if target.exists():record=json.loads(target.read_text(encoding='utf-8'))
                elif max_cells is not None and requests>=max_cells:continue
                else:
                    try:record=await calculate_cell(cell,year,crop_id,db,client)
                    except Exception as e:
                        # Provider failures remain retryable; never persist an invented scientific value.
                        print(cell['id'],type(e).__name__,flush=True);requests+=1;continue
                    target.write_text(json.dumps(record,allow_nan=False),encoding='utf-8');requests+=1
                records.append(record)
                if requests:print(f"{len(records)}/{len(cells)} processed",flush=True)
    finally:db.close()
    return publish(records,job,len(cells))
