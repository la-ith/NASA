"""Account, field and saved-analysis contracts. Recovery never requires sending an email."""
import hmac
import json
import os
import re
import secrets
import sqlite3
import base64
import binascii
from datetime import date
from io import BytesIO
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import BaseModel,Field,field_validator,model_validator
from typing import Literal
from PIL import Image, ImageOps, UnidentifiedImageError
from app.services import accounts as service
from app.geo.boundaries import state_at
from app.domain.crop_catalog import load_catalog

router=APIRouter(prefix='/api/v2')


class Credentials(BaseModel):
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=12,max_length=128)
    @field_validator('email')
    @classmethod
    def email_value(cls,v):
        v=v.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v):raise ValueError('Enter a valid email address')
        return v


class Registration(Credentials):
    name:str=Field(min_length=1,max_length=80)
    @field_validator('name')
    @classmethod
    def clean_name(cls,v):
        if not v.strip():raise ValueError('Enter a name')
        return v.strip()


@router.get('/auth/me')
async def me(request:Request):return dict(user=request.state.user)


@router.post('/auth/register',status_code=201)
async def register(body:Registration,request:Request,response:Response):
    if request.state.user:raise HTTPException(409,'Sign out before creating another account')
    service.throttle(request,'register',limit=20,seconds=3600)
    encoded=await service.hash_password(request,body.password)
    user_id=secrets.token_hex(16);recovery=secrets.token_urlsafe(24)
    try:
        with request.app.state.db:
            request.app.state.db.execute('INSERT INTO fs_user VALUES (?,?,?,?,?,?)',
                (user_id,body.email,body.name,encoded,service.digest(recovery),service.now()))
    except sqlite3.IntegrityError:raise HTTPException(409,'This account cannot be registered; try signing in')
    service.start_session(request,response,user_id)
    return dict(user=dict(id=user_id,email=body.email,name=body.name,email_verified=False),recovery_code=recovery,
                recovery_notice='Save this code privately. It is shown only now and is needed if you forget your password.')


@router.post('/auth/login')
async def login(body:Credentials,request:Request,response:Response):
    if request.state.user:raise HTTPException(409,'Sign out before signing in to another account')
    service.throttle(request,'login-ip',limit=30)
    service.throttle(request,'login',body.email)
    row=request.app.state.db.execute('SELECT user_id,password_hash,display_name FROM fs_user WHERE email=?',(body.email,)).fetchone()
    valid=await service.password_matches(request,row[1] if row else None,body.password)
    if not row or not valid:raise HTTPException(401,'Email or password is incorrect')
    if service.HASHER.check_needs_rehash(row[1]):
        replacement=await service.hash_password(request,body.password)
        with request.app.state.db:request.app.state.db.execute('UPDATE fs_user SET password_hash=? WHERE user_id=?',(replacement,row[0]))
    service.start_session(request,response,row[0])
    return dict(user=dict(id=row[0],email=body.email,name=row[2],email_verified=False))


@router.post('/auth/logout',status_code=204)
async def logout(request:Request,response:Response):
    token=request.cookies.get(service.COOKIE)
    if token:
        with request.app.state.db:request.app.state.db.execute('DELETE FROM fs_auth_session WHERE token_hash=?',(service.digest(token),))
    response.delete_cookie(service.COOKIE,path='/',httponly=True,samesite='strict',secure=request.url.scheme=='https')


class Recovery(Credentials):
    recovery_code:str=Field(min_length=20,max_length=128)


@router.post('/auth/recover')
async def recover(body:Recovery,request:Request,response:Response):
    service.throttle(request,'recovery',body.email,limit=5)
    db=request.app.state.db
    row=db.execute('SELECT user_id,recovery_hash FROM fs_user WHERE email=?',(body.email,)).fetchone()
    if not row or not hmac.compare_digest(row[1],service.digest(body.recovery_code)):
        raise HTTPException(401,'Email or recovery code is incorrect')
    encoded=await service.hash_password(request,body.password);new_code=secrets.token_urlsafe(24)
    with db:
        changed=db.execute('UPDATE fs_user SET password_hash=?,recovery_hash=? WHERE user_id=? AND recovery_hash=?',
                          (encoded,service.digest(new_code),row[0],row[1])).rowcount
        if changed!=1:raise HTTPException(409,'Recovery code already used')
        db.execute('DELETE FROM fs_auth_session WHERE user_id=?',(row[0],))
    response.delete_cookie(service.COOKIE,path='/')
    return dict(recovery_code=new_code,message='Password reset. Save the new recovery code, then sign in.')


class PasswordConfirmation(BaseModel):
    password:str=Field(min_length=12,max_length=128)


@router.delete('/auth/account',status_code=204)
async def delete_account(body:PasswordConfirmation,request:Request,response:Response):
    user=service.require_user(request);db=request.app.state.db
    service.throttle(request,'delete',user['email'],limit=5)
    encoded=db.execute('SELECT password_hash FROM fs_user WHERE user_id=?',(user['id'],)).fetchone()[0]
    if not await service.password_matches(request,encoded,body.password):raise HTTPException(401,'Password is incorrect')
    # Active jobs must finish before their owner records can be removed.
    if db.execute("SELECT 1 FROM v2_job WHERE owner=? AND state IN ('queued','running')",(request.state.owner,)).fetchone():
        raise HTTPException(409,'Wait for running analyses to finish before deleting the account')
    with db:
        for table in ('v2_chat_session','v2_product_record','v2_job','v2_analysis'):
            db.execute(f'DELETE FROM {table} WHERE owner=?',(request.state.owner,))
        db.execute('DELETE FROM fs_user WHERE user_id=?',(user['id'],))
    response.delete_cookie(service.COOKIE,path='/')


class CropHistory(BaseModel):
    year:int=Field(ge=1981,lt=date.today().year)
    crop:str=Field(min_length=1,max_length=80)


DETAIL_KEYS=('area_acres','soil_texture','drainage','slope','water_source','notes',
             'soil_test','priorities','budget','equipment','marketing')


class FieldInput(BaseModel):
    name:str=Field(min_length=1,max_length=80)
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    crop:str='unknown'
    irrigation:Literal['rain-fed','irrigated','unknown']='unknown'
    history:list[CropHistory]=Field(default_factory=list,max_length=10)
    area_acres:float|None=Field(default=None,gt=0,le=10_000_000)
    soil_texture:Literal['unknown','sand','loam','clay','silt','mixed']='unknown'
    drainage:Literal['unknown','fast','moderate','slow']='unknown'
    slope:Literal['unknown','flat','gentle','steep']='unknown'
    water_source:Literal['unknown','rainfall','well','surface_water','municipal','mixed']='unknown'
    notes:str=Field(default='',max_length=500)
    # Farmer context from the add-land wizard. Descriptive only: none of it changes the physical model.
    soil_test:Literal['unknown','recent','old','none']='unknown'
    priorities:list[Literal['improve_soil','livestock_feed','economics','reduce_risk']]=Field(default_factory=list,max_length=4)
    budget:Literal['unknown','limited','moderate','adequate']='unknown'
    equipment:Literal['unknown','limited','moderate','adequate']='unknown'
    marketing:Literal['unknown','limited','moderate','adequate']='unknown'
    @model_validator(mode='after')
    def field_validity(self):
        self.name=self.name.strip()
        if not self.name:raise ValueError('Enter a field name')
        if state_at(self.lon,self.lat) is None:raise ValueError('Choose a location within the 50 US states')
        if self.crop not in {'unknown',*load_catalog().crops}:raise ValueError('Choose a supported crop or unknown')
        if len({h.year for h in self.history})!=len(self.history):raise ValueError('History years must be unique')
        return self


def field_record(row):
    return dict(id=row[0],name=row[1],lat=row[2],lon=row[3],state=row[4],crop=row[5],irrigation=row[6],history=json.loads(row[7]),
                details=json.loads(row[10] or '{}') if len(row)>10 else {},created_utc=row[8],updated_utc=row[9])


@router.get('/fields')
async def fields(request:Request):
    user=service.require_user(request)
    rows=request.app.state.db.execute('SELECT field_id,name,lat,lon,state,crop,irrigation,history,created_utc,updated_utc,details '
                                     'FROM fs_field WHERE user_id=? ORDER BY updated_utc DESC',(user['id'],)).fetchall()
    return dict(fields=[field_record(r) for r in rows])


@router.post('/fields',status_code=201)
async def save_field(body:FieldInput,request:Request):
    user=service.require_user(request);db=request.app.state.db
    if db.execute('SELECT count(*) FROM fs_field WHERE user_id=?',(user['id'],)).fetchone()[0]>=100:
        raise HTTPException(422,'Field limit reached')
    field_id=secrets.token_hex(12);stamp=service.now()
    with db:db.execute('INSERT INTO fs_field (field_id,user_id,name,lat,lon,state,crop,irrigation,history,created_utc,updated_utc,details) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (field_id,user['id'],body.name,body.lat,body.lon,state_at(body.lon,body.lat).code,body.crop,body.irrigation,
         json.dumps([h.model_dump() for h in body.history]),stamp,stamp,json.dumps({k:getattr(body,k) for k in DETAIL_KEYS})))
    return dict(id=field_id,state=state_at(body.lon,body.lat).code)


@router.put('/fields/{field_id}')
async def edit_field(field_id:str,body:FieldInput,request:Request):
    user=service.require_user(request)
    with request.app.state.db:
        changed=request.app.state.db.execute('UPDATE fs_field SET name=?,lat=?,lon=?,state=?,crop=?,irrigation=?,history=?,updated_utc=?,details=? '
            'WHERE field_id=? AND user_id=?',(body.name,body.lat,body.lon,state_at(body.lon,body.lat).code,body.crop,body.irrigation,
             json.dumps([h.model_dump() for h in body.history]),service.now(),json.dumps({k:getattr(body,k) for k in DETAIL_KEYS}),field_id,user['id'])).rowcount
    if not changed:raise HTTPException(404,'Field not found')
    return dict(id=field_id,state=state_at(body.lon,body.lat).code)


@router.delete('/fields/{field_id}',status_code=204)
async def delete_field(field_id:str,request:Request):
    user=service.require_user(request)
    with request.app.state.db:
        changed=request.app.state.db.execute('DELETE FROM fs_field WHERE field_id=? AND user_id=?',(field_id,user['id'])).rowcount
    if not changed:raise HTTPException(404,'Field not found')


class FieldObservationInput(BaseModel):
    observed_on:date
    crop:str=Field(min_length=1,max_length=80)
    category:Literal['water','pest_disease','growth','weather','other']='other'
    note:str=Field(min_length=5,max_length=2000)
    photo_data:str|None=Field(default=None,max_length=5_600_000)

    @field_validator('note')
    @classmethod
    def clean_note(cls,value):
        value=value.strip()
        if len(value)<5:raise ValueError('Add a little more detail to the observation')
        return value


def normalize_observation_photo(encoded:str|None)->bytes|None:
    if not encoded:return None
    if encoded.startswith('data:'):
        encoded=encoded.split(',',1)[-1]
    try:raw=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):raise HTTPException(422,'Choose a valid photo file')
    if len(raw)>4_000_000:raise HTTPException(413,'Photo must be smaller than 4 MB')
    try:
        with Image.open(BytesIO(raw)) as original:
            if original.width*original.height>24_000_000:raise HTTPException(413,'Photo dimensions are too large')
            photo=ImageOps.exif_transpose(original).convert('RGB')
            photo.thumbnail((1600,1600))
            out=BytesIO();photo.save(out,format='JPEG',quality=84,optimize=True)
            data=out.getvalue()
            if len(data)>700_000:
                out=BytesIO();photo.save(out,format='JPEG',quality=68,optimize=True);data=out.getvalue()
            if len(data)>700_000:raise HTTPException(413,'Photo could not be compressed below 700 KB')
            return data
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError):
        raise HTTPException(422,'The photo format could not be opened')


@router.get('/fields/{field_id}/observations')
async def field_observations(field_id:str,request:Request):
    user=service.require_user(request);db=request.app.state.db
    if not db.execute('SELECT 1 FROM fs_field WHERE field_id=? AND user_id=?',(field_id,user['id'])).fetchone():
        raise HTTPException(404,'Field not found')
    rows=db.execute('SELECT o.observation_id,o.observed_on,o.crop,o.category,o.note,o.photo_mime,o.created_utc,'
                    '(SELECT status FROM fs_expert_request r WHERE r.observation_id=o.observation_id ORDER BY r.created_utc DESC LIMIT 1) '
                    'FROM fs_field_observation o WHERE o.field_id=? AND o.user_id=? ORDER BY o.observed_on DESC,o.created_utc DESC LIMIT 100',
                    (field_id,user['id'])).fetchall()
    return dict(observations=[dict(id=r[0],observed_on=r[1],crop=r[2],category=r[3],note=r[4],
      photo_url=f'/api/v2/fields/{field_id}/observations/{r[0]}/photo' if r[5] else None,created_utc=r[6],
      expert_status=r[7],review_state='private') for r in rows])


@router.post('/fields/{field_id}/observations',status_code=201)
async def add_field_observation(field_id:str,body:FieldObservationInput,request:Request):
    user=service.require_user(request);db=request.app.state.db
    if not db.execute('SELECT 1 FROM fs_field WHERE field_id=? AND user_id=?',(field_id,user['id'])).fetchone():
        raise HTTPException(404,'Field not found')
    if body.observed_on>date.today():raise HTTPException(422,'Observation date cannot be in the future')
    if body.crop!='unknown' and body.crop not in load_catalog().crops:raise HTTPException(422,'Choose a supported crop or unknown')
    service.throttle(request,'field-observation',field_id,limit=40,seconds=86400)
    photo=normalize_observation_photo(body.photo_data)
    observation_id=secrets.token_urlsafe(15);stamp=service.now()
    with db:db.execute('INSERT INTO fs_field_observation (observation_id,user_id,field_id,observed_on,crop,category,note,photo_data,photo_mime,created_utc) VALUES (?,?,?,?,?,?,?,?,?,?)',
      (observation_id,user['id'],field_id,body.observed_on.isoformat(),body.crop,body.category,body.note,photo,'image/jpeg' if photo else None,stamp))
    return dict(id=observation_id,status='private',created_utc=stamp)


@router.get('/fields/{field_id}/observations/{observation_id}/photo')
async def field_observation_photo(field_id:str,observation_id:str,request:Request):
    user=service.require_user(request)
    row=request.app.state.db.execute('SELECT photo_data,photo_mime FROM fs_field_observation WHERE observation_id=? AND field_id=? AND user_id=?',
                                     (observation_id,field_id,user['id'])).fetchone()
    if not row or not row[0]:raise HTTPException(404,'Photo not found')
    return Response(content=row[0],media_type=row[1] or 'image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


@router.delete('/fields/{field_id}/observations/{observation_id}',status_code=204)
async def delete_field_observation(field_id:str,observation_id:str,request:Request):
    user=service.require_user(request)
    with request.app.state.db:
        changed=request.app.state.db.execute('DELETE FROM fs_field_observation WHERE observation_id=? AND field_id=? AND user_id=?',
                                              (observation_id,field_id,user['id'])).rowcount
    if not changed:raise HTTPException(404,'Observation not found')


@router.get('/account/analyses')
async def analyses(request:Request):
    service.require_user(request)
    rows=request.app.state.db.execute('SELECT analysis_id,created_utc,result,field_id FROM v2_analysis WHERE owner=? '
                                     'ORDER BY created_utc DESC LIMIT 100',(request.state.owner,)).fetchall()
    items=[]
    for aid,created,payload,fid in rows:
        r=json.loads(payload);items.append(dict(id=aid,created_utc=created,field_id=fid,status=r['status'],mode=r['mode'],
            state=r['location']['state'],period=r['period']['requested'],goal=r['goal'],summary=r['summary']))
    return dict(analyses=items)


@router.get('/account/export')
async def export_account(request:Request):
    user=service.require_user(request);db=request.app.state.db
    saved_fields=await fields(request)
    analyses=[json.loads(r[0]) for r in db.execute('SELECT result FROM v2_analysis WHERE owner=?',(request.state.owner,))]
    chats=[dict(id=r[0],analysis_id=r[1],created_utc=r[2],messages=json.loads(r[3])) for r in db.execute(
        'SELECT session_id,analysis_id,created_utc,messages FROM v2_chat_session WHERE owner=?',(request.state.owner,))]
    observations=[dict(id=r[0],field_id=r[1],observed_on=r[2],crop=r[3],category=r[4],note=r[5],
        photo_data=base64.b64encode(r[6]).decode('ascii') if r[6] else None,photo_mime=r[7],created_utc=r[8])
        for r in db.execute('SELECT observation_id,field_id,observed_on,crop,category,note,photo_data,photo_mime,created_utc '
                            'FROM fs_field_observation WHERE user_id=? ORDER BY observed_on DESC',(user['id'],))]
    return dict(user=user,fields=saved_fields['fields'],analyses=analyses,conversations=chats,observations=observations)


class ExpertQuestion(BaseModel):
    message:str=Field(min_length=10,max_length=3000)
    field_id:str|None=Field(default=None,max_length=64)
    analysis_id:str|None=Field(default=None,max_length=100)
    observation_id:str|None=Field(default=None,max_length=64)


class ExpertAnswer(BaseModel):
    message:str=Field(min_length=10,max_length=5000)


@router.post('/expert/requests',status_code=201)
async def ask_expert(body:ExpertQuestion,request:Request):
    user=service.require_user(request);db=request.app.state.db
    field_id=body.field_id
    observation=None
    if body.observation_id:
        observation=db.execute('SELECT field_id,observed_on,crop,category,note FROM fs_field_observation WHERE observation_id=? AND user_id=?',
                               (body.observation_id,user['id'])).fetchone()
        if not observation:raise HTTPException(404,'Observation not found')
        if field_id and field_id!=observation[0]:raise HTTPException(422,'Choose the field linked to this note')
        field_id=observation[0]
    if field_id and not db.execute('SELECT 1 FROM fs_field WHERE field_id=? AND user_id=?',(field_id,user['id'])).fetchone():
        raise HTTPException(404,'Field not found')
    if body.analysis_id:
        row=db.execute('SELECT field_id FROM v2_analysis WHERE analysis_id=? AND owner=?',(body.analysis_id,request.state.owner)).fetchone()
        if not row:raise HTTPException(404,'Analysis not found')
        if field_id and row[0] and row[0]!=field_id:raise HTTPException(422,'Choose a field linked to this comparison')
        field_id=field_id or row[0]
    snapshot={}
    if field_id:
        row=db.execute('SELECT name,state,crop,irrigation,history,details FROM fs_field WHERE field_id=? AND user_id=?',(field_id,user['id'])).fetchone()
        if not row:raise HTTPException(404,'Field not found')
        snapshot=dict(name=row[0],state=row[1],crop=row[2],irrigation=row[3],history=json.loads(row[4] or '[]'),details=json.loads(row[5] or '{}'))
    service.throttle(request,'expert-request',limit=10,seconds=3600)
    request_id=secrets.token_urlsafe(15);stamp=service.now()
    with db:db.execute('INSERT INTO fs_expert_request (request_id,user_id,field_id,analysis_id,observation_id,field_snapshot,question,status,created_utc) VALUES (?,?,?,?,?,?,?,\'open\',?)',
        (request_id,user['id'],field_id,body.analysis_id,body.observation_id,json.dumps(snapshot),body.message.strip(),stamp))
    return dict(request_id=request_id,status='open',created_utc=stamp)


@router.get('/expert/requests')
async def my_expert_requests(request:Request):
    user=service.require_user(request)
    rows=request.app.state.db.execute('SELECT r.request_id,r.field_id,f.name,r.analysis_id,r.question,r.status,r.response,r.created_utc,r.responded_utc '
        'FROM fs_expert_request r LEFT JOIN fs_field f ON f.field_id=r.field_id WHERE r.user_id=? ORDER BY r.created_utc DESC LIMIT 50',(user['id'],)).fetchall()
    return dict(requests=[dict(request_id=r[0],field_id=r[1],field_name=r[2],analysis_id=r[3],message=r[4],status=r[5],response=r[6],created_utc=r[7],responded_utc=r[8]) for r in rows])


def require_expert(request:Request):
    expected=os.environ.get('FIELD_SHIFT_EXPERT_KEY','')
    supplied=request.headers.get('x-expert-key','')
    if not expected:raise HTTPException(503,'Expert inbox is not configured on this server')
    if len(supplied)>256 or not hmac.compare_digest(expected,supplied):raise HTTPException(401,'Expert access denied')


@router.get('/expert/queue')
async def expert_queue(request:Request):
    require_expert(request);db=request.app.state.db
    rows=db.execute("SELECT r.request_id,r.field_id,f.name,f.state,f.crop,f.irrigation,f.history,f.details,r.analysis_id,r.question,r.status,r.created_utc,u.display_name,r.field_snapshot,a.result,"
       "o.observation_id,o.observed_on,o.crop,o.category,o.note,(o.photo_data IS NOT NULL) "
       "FROM fs_expert_request r LEFT JOIN fs_field f ON f.field_id=r.field_id JOIN fs_user u ON u.user_id=r.user_id "
       "LEFT JOIN v2_analysis a ON a.analysis_id=r.analysis_id "
       "LEFT JOIN fs_field_observation o ON o.observation_id=r.observation_id "
       "WHERE r.status='open' ORDER BY r.created_utc ASC LIMIT 100").fetchall()
    items=[]
    for x in rows:
        snapshot=json.loads(x[13] or '{}')
        analysis=json.loads(x[14]) if x[14] else None
        items.append(dict(request_id=x[0],field_id=x[1],field_name=x[2] or snapshot.get('name'),state=x[3] or snapshot.get('state'),
          crop=x[4] or snapshot.get('crop'),irrigation=x[5] or snapshot.get('irrigation'),history=json.loads(x[6] or '[]') or snapshot.get('history',[]),
          details=json.loads(x[7] or '{}') or snapshot.get('details',{}),analysis_id=x[8],message=x[9],status=x[10],created_utc=x[11],farmer_name=x[12],
          observation=dict(id=x[15],observed_on=x[16],crop=x[17],category=x[18],note=x[19],photo_available=bool(x[20])) if x[15] else None,
          analysis_summary=analysis.get('summary') if analysis else None,
          risk_assessment=[dict(crop=s['name'],**s.get('water_stress_exposure',{})) for s in analysis.get('strategies',[])] if analysis else []))
    return dict(requests=items)


@router.post('/expert/queue/{request_id}/reply')
async def expert_reply(request_id:str,body:ExpertAnswer,request:Request):
    require_expert(request);db=request.app.state.db
    stamp=service.now()
    with db:
        changed=db.execute("UPDATE fs_expert_request SET response=?,status='replied',responded_utc=? WHERE request_id=? AND status='open'",
                           (body.message.strip(),stamp,request_id)).rowcount
    if not changed:raise HTTPException(404,'Open request not found')
    return dict(request_id=request_id,status='replied',responded_utc=stamp)


@router.get('/expert/queue/{request_id}/observation-photo')
async def expert_observation_photo(request_id:str,request:Request):
    require_expert(request)
    row=request.app.state.db.execute('SELECT o.photo_data,o.photo_mime FROM fs_expert_request r JOIN fs_field_observation o ON o.observation_id=r.observation_id '
                                     'WHERE r.request_id=?',(request_id,)).fetchone()
    if not row or not row[0]:raise HTTPException(404,'Photo not found')
    return Response(content=row[0],media_type=row[1] or 'image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
