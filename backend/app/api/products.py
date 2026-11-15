"""Bounded supplemental context requests, catalog discovery and authenticated data artifacts."""
import json
from datetime import date,datetime,timezone
from fastapi import APIRouter,Request,HTTPException
from pydantic import BaseModel,Field,model_validator
from app.adapters import AdapterError,content_hash
from app.adapters import supplemental,cdl
from app.geo.boundaries import state_at

router=APIRouter(prefix='/api/v2/products')


class ProductQuery(BaseModel):
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    start:date
    end:date
    @model_validator(mode='after')
    def period(self):
        if self.start>self.end or (self.end-self.start).days>365 or self.end>=date.today():
            raise ValueError('use an ordered past interval of at most 366 days')
        return self


@router.get('')
async def catalog():
    return dict(products=[dict(id=k,access='POWER Daily API',source=v['source'],
                              first_date=v['start'].isoformat(),purpose=v['meaning'],
                              status='adapter_ready; availability must be checked per request')
                          for k,v in supplemental.PRODUCTS.items()],
                production_balance_forcing='NASA POWER AG LST only',
                cdl=dict(id='usda_cdl',status='adapter_ready',endpoint='/api/v2/products/usda_cdl/point',
                         scope='CONUS and separate Hawaii service; Alaska unsupported',farmer_confirmed=False))


class CropQuery(BaseModel):
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    year:int=Field(ge=2008,lt=date.today().year)


@router.post('/usda_cdl/point')
async def crop_classification(body:CropQuery,request:Request):
    state=state_at(body.lon,body.lat)
    if state is None:raise HTTPException(422,'outside US scope')
    try:raw,result=await cdl.fetch(request.app.state.http,state.code,body.lon,body.lat,body.year)
    except AdapterError as e:raise HTTPException(422 if e.code=='not_covered' else 502,dict(code=e.code,message=str(e)))
    return save_record(request,'usda_cdl',raw,result)


def save_record(request,product,raw,result):
    now=datetime.now(timezone.utc).isoformat()
    artifact_id=content_hash([request.state.owner,product,now,raw])[:32]
    with request.app.state.db:
        request.app.state.db.execute('INSERT INTO v2_product_record VALUES (?,?,?,?,?,?)',
            (artifact_id,request.state.owner,product,now,json.dumps(raw),json.dumps(result)))
    return dict(artifact_id=artifact_id,retrieved_utc=now,**result)


@router.post('/{product}/query')
async def query(product:str,body:ProductQuery,request:Request):
    if product not in supplemental.PRODUCTS:raise HTTPException(404,'unknown product')
    if state_at(body.lon,body.lat) is None:raise HTTPException(422,'outside US scope')
    if body.start < supplemental.PRODUCTS[product]['start']:
        raise HTTPException(422,'requested interval predates configured product support')
    try:raw,result=await supplemental.fetch(request.app.state.http,product,body.lat,body.lon,body.start,body.end)
    except AdapterError as e:raise HTTPException(502,dict(code=e.code,message=str(e)))
    return save_record(request,product,raw,result)


@router.get('/records/{artifact_id}')
async def record(artifact_id:str,request:Request):
    row=request.app.state.db.execute('SELECT product,retrieved_utc,raw,result FROM v2_product_record '
                                    'WHERE artifact_id=? AND owner=?',(artifact_id,request.state.owner)).fetchone()
    if row is None:raise HTTPException(404,'record not found')
    return dict(product=row[0],retrieved_utc=row[1],raw=json.loads(row[2]),result=json.loads(row[3]))
