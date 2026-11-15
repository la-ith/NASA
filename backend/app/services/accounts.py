"""Argon2id passwords, revocable opaque sessions, owned field records and recovery codes."""
import asyncio
import hashlib
import os
import secrets
import time
from datetime import datetime,timedelta,timezone
from argon2 import PasswordHasher,exceptions
from fastapi import HTTPException

HASHER=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
COOKIE='field_shift_auth'
SESSION_SECONDS=30*86400
DUMMY_HASH=HASHER.hash(secrets.token_urlsafe(24))


def now():return datetime.now(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()
def cookie_secure(request):
    forced=os.environ.get('FIELD_SHIFT_COOKIE_SECURE','').strip().lower() in {'1','true','yes'}
    return forced or request.url.scheme=='https'


def identify(db,token):
    if not token or len(token)!=43:return None
    row=db.execute('SELECT u.user_id,u.email,u.display_name FROM fs_auth_session s JOIN fs_user u '
        'ON u.user_id=s.user_id WHERE s.token_hash=? AND s.expires_utc>?',(digest(token),now())).fetchone()
    return None if row is None else dict(id=row[0],email=row[1],name=row[2],email_verified=False)


def require_user(request):
    if not request.state.user:raise HTTPException(401,'Sign in to save fields and access your account')
    return request.state.user


def throttle(request,kind,email='',limit=8,seconds=900):
    key=digest(kind+'|'+(request.client.host if request.client else 'unknown')+'|'+email)
    db=request.app.state.db;clock=int(time.time())
    with db:
        row=db.execute('SELECT window_start,attempts FROM fs_auth_rate WHERE rate_key=?',(key,)).fetchone()
        if row and clock-row[0]<seconds:
            if row[1]>=limit:raise HTTPException(429,'Too many attempts; please try again later')
            db.execute('UPDATE fs_auth_rate SET attempts=attempts+1 WHERE rate_key=?',(key,))
        else:db.execute('INSERT OR REPLACE INTO fs_auth_rate VALUES (?,?,1)',(key,clock))


async def password_matches(request,encoded,password):
    def verify():
        try:return HASHER.verify(encoded or DUMMY_HASH,password)
        except (exceptions.VerificationError,exceptions.InvalidHashError):return False
    async with request.app.state.auth_slots:return await asyncio.to_thread(verify)


async def hash_password(request,password):
    async with request.app.state.auth_slots:return await asyncio.to_thread(HASHER.hash,password)


def start_session(request,response,user_id,claim_guest=True):
    token=secrets.token_urlsafe(32);created=datetime.now(timezone.utc)
    db=request.app.state.db
    with db:
        db.execute('DELETE FROM fs_auth_session WHERE expires_utc<=?',(created.isoformat(),))
        db.execute('INSERT INTO fs_auth_session VALUES (?,?,?,?)',
            (digest(token),user_id,created.isoformat(),(created+timedelta(seconds=SESSION_SECONDS)).isoformat()))
        if claim_guest and not request.state.user:
            for table in ('v2_job','v2_analysis','v2_chat_session','v2_product_record'):
                db.execute(f'UPDATE {table} SET owner=? WHERE owner=?',('user:'+user_id,request.state.owner))
    response.set_cookie(COOKIE,token,max_age=SESSION_SECONDS,httponly=True,samesite='strict',
                        secure=cookie_secure(request),path='/')
