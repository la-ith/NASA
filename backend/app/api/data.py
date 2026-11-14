"""Frontend-independent result, map and provenance endpoints with v2 ownership checks."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.api.v2 import _load, AnalysisRequestV2, create_analysis
from app.services import layers

router=APIRouter(prefix='/api/v2')


@router.get('/sources')
async def sources():
    from app.adapters import power,ssurgo
    return dict(integrated=[power.describe_product(),ssurgo.describe_product()],
        supplemental=['usda_cdl','gpm_imerg','smap'],
        note='Consult supplemental product routes for access status; no source is silently substituted.')


@router.get('/analyses/{analysis_id}/layers')
async def get_layers(analysis_id:str,request:Request):
    return dict(layers=layers.manifests(_load(request,analysis_id)),national_rasters=False)


@router.get('/analyses/{analysis_id}/layers/{layer_id}/geojson')
async def geojson(analysis_id:str,layer_id:str,request:Request,year:int|None=None):
    result=_load(request,analysis_id)
    try:return dict(type='FeatureCollection',features=[layers.feature(result,layer_id,year)])
    except KeyError:raise HTTPException(404,'layer not found')


class Comparison(BaseModel):
    strategy_a:str=Field(max_length=20)
    strategy_b:str=Field(max_length=20)
    metric:str=Field(max_length=80)


@router.post('/analyses/{analysis_id}/compare')
async def compare(analysis_id:str,body:Comparison,request:Request):
    result=_load(request,analysis_id)
    try:return layers.compare(result,body.strategy_a,body.strategy_b,body.metric)
    except KeyError:raise HTTPException(422,'unknown strategy or metric')


@router.get('/analyses/{analysis_id}/timeseries')
async def timeseries(analysis_id:str,request:Request):
    result=_load(request,analysis_id)
    return dict(analysis_id=analysis_id,period=result['period'],result_types=result['result_types'],
                strategies=[dict(id=s['id'],crop=s['crop'],seasons=s['result']['seasons'],
                                 exclusions=s['result']['seasons_excluded']) for s in result['strategies']])


@router.get('/analyses/{analysis_id}/provenance')
async def provenance(analysis_id:str,request:Request):
    r=_load(request,analysis_id)
    return dict(analysis_id=analysis_id,provenance=r['provenance'],versions=r['versions'],
                equations=r['equations'],inputs=r['inputs'],limitations=r['limitations'],
                scientific_validation='numerically verified; field irrigation accuracy not established')


class Scenario(BaseModel):
    changes:dict=Field(default_factory=dict)


@router.post('/analyses/{analysis_id}/scenarios',status_code=202)
async def scenario(analysis_id:str,body:Scenario,request:Request):
    import json
    _load(request,analysis_id)
    allowed={'goal','current_practice','candidates','planting_dates','initial_depletion_fraction','soil','irrigation'}
    if set(body.changes)-allowed:raise HTTPException(422,'scenario can only change crop/calendar/soil/management/goal')
    row=request.app.state.db.execute('SELECT request FROM v2_analysis WHERE analysis_id=? AND owner=?',
                                    (analysis_id,request.state.owner)).fetchone()
    params={**json.loads(row[0]),**body.changes,'parent_analysis_id':analysis_id}
    try:validated=AnalysisRequestV2.model_validate(params)
    except ValueError:raise HTTPException(422,'scenario parameters invalid; check crop dates and management inputs')
    return await create_analysis(validated,request)


@router.get('/analyses/{analysis_id}/weather')
async def weather_export(analysis_id:str,request:Request):
    """Read the exact source artifact used, not a fresh provider fetch."""
    import json
    from app.adapters import content_hash
    from app.services.sources_v2 import FIXTURES,demo_site
    result=_load(request,analysis_id)
    digest=result['provenance']['weather']['content_sha256']
    row=request.app.state.db.execute('SELECT raw_response FROM v2_source_record '
        "WHERE provider='power' AND json_extract(manifest,'$.content_sha256')=? LIMIT 1",(digest,)).fetchone()
    raw=json.loads(row[0]) if row else None
    if raw is None and result['mode']=='sample':
        params=json.loads(request.app.state.db.execute('SELECT request FROM v2_analysis WHERE analysis_id=?',
                                                     (analysis_id,)).fetchone()[0])
        site=demo_site(params['lon'],params['lat'])
        if site:raw=json.loads((FIXTURES/f'power_{site}_2001_2025.json').read_text(encoding='utf-8'))['response']
    if raw is None:raise HTTPException(409,'original source artifact unavailable; do not substitute a fresh response')
    if content_hash(raw)!=digest:raise HTTPException(409,'source artifact integrity failure')
    return dict(analysis_id=analysis_id,manifest=result['provenance']['weather'],original_response=raw)
