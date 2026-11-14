"""Session-scoped agricultural assistant API. No account database is introduced."""
import json
import os
import secrets
from datetime import datetime,timezone
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
from typing import Literal
from app.api.v2 import _load
from app.services.assistant import answer

router=APIRouter(prefix='/api/v2/chat')


class SessionIn(BaseModel):
    analysis_id:str|None=Field(default=None,max_length=100)


class MessageIn(BaseModel):
    message:str=Field(min_length=1,max_length=4000)
    language:Literal['auto','en','ar']='auto'


@router.get('/status')
async def status():
    return dict(provider='OpenAI Responses API',configured=bool(os.environ.get('OPENAI_API_KEY') and os.environ.get('OPENAI_MODEL')),
                default_mode='grounded evidence selection; deterministic fallback',free_form_claims=False)


@router.post('/sessions',status_code=201)
async def session(body:SessionIn,request:Request):
    if body.analysis_id:_load(request,body.analysis_id)
    db=request.app.state.db
    if db.execute('SELECT count(*) FROM v2_chat_session WHERE owner=?',(request.state.owner,)).fetchone()[0]>=10:
        raise HTTPException(429,'session limit reached')
    sid=secrets.token_urlsafe(16)
    with db:db.execute('INSERT INTO v2_chat_session VALUES (?,?,?,?,?)',
        (sid,request.state.owner,body.analysis_id,datetime.now(timezone.utc).isoformat(),'[]'))
    return dict(session_id=sid,analysis_id=body.analysis_id)


@router.post('/sessions/{sid}/messages')
async def message(sid:str,body:MessageIn,request:Request):
    db=request.app.state.db
    async with request.app.state.chat_lock:
        row=db.execute('SELECT analysis_id,messages FROM v2_chat_session WHERE session_id=? AND owner=?',
                       (sid,request.state.owner)).fetchone()
        if row is None:raise HTTPException(404,'chat not found')
        messages=json.loads(row[1])
        if len(messages)>=20:raise HTTPException(429,'message limit reached; start a new session')
        if os.environ.get('OPENAI_API_KEY') and os.environ.get('OPENAI_MODEL'):
            today=datetime.now(timezone.utc).date().isoformat()
            count=db.execute('SELECT requests FROM v2_ai_usage WHERE utc_day=?',(today,)).fetchone()
            if count and count[0]>=int(os.environ.get('FIELD_SHIFT_AI_DAILY_CALL_LIMIT','50')):
                raise HTTPException(429,'daily AI request budget reached; analysis remains available')
            with db:db.execute('INSERT INTO v2_ai_usage VALUES (?,1) ON CONFLICT(utc_day) DO UPDATE SET requests=requests+1',
                               (today,))
        analysis=_load(request,row[0]) if row[0] else None
        result=await answer(request.app.state.http,body.message,analysis,[m['question'] for m in messages],body.language)
        messages.append(dict(question=body.message,response=result))
        with db:db.execute('UPDATE v2_chat_session SET messages=? WHERE session_id=? AND owner=?',
                           (json.dumps(messages),sid,request.state.owner))
    return result


@router.get('/sessions/{sid}')
async def history(sid:str,request:Request):
    row=request.app.state.db.execute('SELECT analysis_id,messages FROM v2_chat_session WHERE session_id=? AND owner=?',
                                    (sid,request.state.owner)).fetchone()
    if row is None:raise HTTPException(404,'chat not found')
    return dict(session_id=sid,analysis_id=row[0],messages=json.loads(row[1]))


@router.delete('/sessions/{sid}',status_code=204)
async def delete(sid:str,request:Request):
    with request.app.state.db:
        request.app.state.db.execute('DELETE FROM v2_chat_session WHERE session_id=? AND owner=?',(sid,request.state.owner))
