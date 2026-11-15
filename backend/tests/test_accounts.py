"""Real password/session flows and cross-account isolation; no external services."""
import os
os.environ['FIELD_SHIFT_DB']=':memory:'
os.environ['FIELD_SHIFT_WARMUP']='0'
import pytest
from fastapi.testclient import TestClient
from app.main import app
from test_api_v2 import wait_for
from test_review_fixes import BODY

PASSWORD='local-test-password-2026'
FIELD=dict(name='North field',lat=38.85,lon=-99.33,crop='maize_grain',irrigation='rain-fed',
           history=[dict(year=2025,crop='soybean')])


def test_export_chat_listing_and_credentials_are_private():
    with TestClient(app) as c:
        secret='short-secret'
        rejected=c.post('/api/v2/auth/register',json=dict(name='test',email='bad',password=secret))
        assert rejected.status_code==422 and secret not in rejected.text
        register(c)
        c.post('/api/v2/fields',json=FIELD)
        sid=c.post('/api/v2/chat/sessions',json={}).json()['session_id']
        exported=c.get('/api/v2/account/export').json()
        assert len(exported['fields'])==1 and exported['conversations'][0]['id']==sid
        assert 'password_hash' not in str(exported) and 'recovery_hash' not in str(exported)
        assert len(c.get('/api/v2/chat/sessions').json()['sessions'])==1
        c.post('/api/v2/auth/logout')
        assert c.get('/api/v2/account/export').status_code==401
        assert c.get('/api/v2/chat/sessions').json()=={'sessions':[]}


@pytest.fixture
def client():
    with TestClient(app) as c:yield c


def register(c,email='farmer@example.test'):
    r=c.post('/api/v2/auth/register',json=dict(name='Farmer',email=email,password=PASSWORD))
    assert r.status_code==201,r.text
    return r.json()


def test_password_hash_session_and_field_ownership(client):
    a=register(client)
    stored=app.state.db.execute('SELECT password_hash,recovery_hash FROM fs_user').fetchone()
    assert stored[0].startswith('$argon2id$') and PASSWORD not in stored[0]
    assert a['recovery_code']!=stored[1]
    assert client.get('/api/v2/auth/me').json()['user']['id']==a['user']['id']
    saved=client.post('/api/v2/fields',json=FIELD)
    assert saved.status_code==201
    fid=saved.json()['id']
    assert client.get('/api/v2/fields').json()['fields'][0]['history']==FIELD['history']
    assert client.post('/api/v2/auth/logout').status_code==204
    assert client.get('/api/v2/fields').status_code==401
    register(client,'second@example.test')
    assert client.get('/api/v2/fields').json()['fields']==[]
    assert client.put('/api/v2/fields/'+fid,json={**FIELD,'name':'stolen'}).status_code==404
    assert client.delete('/api/v2/fields/'+fid).status_code==404
    assert client.post('/api/v2/analyses',json={**BODY,'field_id':fid}).status_code==404


def test_guest_work_claim_and_cross_device_login(client):
    job=wait_for(client,client.post('/api/v2/analyses',json=BODY).json()['status_url'])
    url=job['analysis_url']
    register(client)
    assert client.get(url).status_code==200
    assert client.get('/api/v2/account/analyses').json()['analyses'][0]['id']==job['analysis_id']
    client.post('/api/v2/auth/logout');client.cookies.clear()
    assert client.get(url).status_code==404
    assert client.post('/api/v2/auth/login',json=dict(email='farmer@example.test',password=PASSWORD)).status_code==200
    assert client.get(url).status_code==200


def test_recovery_revokes_sessions_and_rotates_code(client):
    a=register(client);cookie=client.cookies.get('field_shift_auth')
    assert client.post('/api/v2/auth/recover',json=dict(email='farmer@example.test',password='new-test-password-2026',
                                                       recovery_code='wrong-recovery-code-2026')).status_code==401
    r=client.post('/api/v2/auth/recover',json=dict(email='farmer@example.test',password='new-test-password-2026',
                                                  recovery_code=a['recovery_code']))
    assert r.status_code==200 and r.json()['recovery_code']!=a['recovery_code']
    client.cookies.set('field_shift_auth',cookie)
    assert client.get('/api/v2/auth/me').json()['user'] is None
    client.cookies.clear()
    assert client.post('/api/v2/auth/login',json=dict(email='farmer@example.test',password=PASSWORD)).status_code==401
    assert client.post('/api/v2/auth/login',json=dict(email='farmer@example.test',password='new-test-password-2026')).status_code==200
    assert client.post('/api/v2/auth/recover',json=dict(email='farmer@example.test',password='another-test-password-2026',
                                                      recovery_code=a['recovery_code'])).status_code==401


def test_saved_field_analysis_binding_and_delete_account(client):
    register(client)
    fid=client.post('/api/v2/fields',json=FIELD).json()['id']
    assert client.post('/api/v2/analyses',json={**BODY,'field_id':fid,'lat':42.03,'lon':-93.62}).status_code==422
    job=wait_for(client,client.post('/api/v2/analyses',json={**BODY,'field_id':fid}).json()['status_url'])
    assert job['state']=='succeeded'
    assert client.get('/api/v2/account/analyses').json()['analyses'][0]['field_id']==fid
    assert client.request('DELETE','/api/v2/auth/account',json={'password':'wrong-password-2026'}).status_code==401
    assert client.request('DELETE','/api/v2/auth/account',json={'password':PASSWORD}).status_code==204
    assert client.get('/api/v2/auth/me').json()['user'] is None
    assert app.state.db.execute('SELECT count(*) FROM fs_user').fetchone()[0]==0
    assert app.state.db.execute('SELECT count(*) FROM fs_field').fetchone()[0]==0
    assert client.get(job['analysis_url']).status_code==404


def test_auth_origin_validation_and_rate_limit(client):
    assert client.post('/api/v2/auth/register',json=dict(name='Farmer',email='a@example.test',password=PASSWORD),
                       headers={'Origin':'https://foreign.example'}).status_code==403
    assert client.post('/api/v2/auth/register',json=dict(name='Farmer',email='bad-email',password=PASSWORD)).status_code==422
    for _ in range(8):
        assert client.post('/api/v2/auth/login',json=dict(email='none@example.test',password=PASSWORD)).status_code==401
    assert client.post('/api/v2/auth/login',json=dict(email='none@example.test',password=PASSWORD)).status_code==429


def test_vercel_proxy_origin_and_secure_cookies(client,monkeypatch):
    origin='https://field-shift-demo.vercel.app'
    monkeypatch.setenv('FIELD_SHIFT_ALLOWED_ORIGINS',origin)
    monkeypatch.setenv('FIELD_SHIFT_COOKIE_SECURE','1')
    response=client.post('/api/v2/auth/register',headers={'Origin':origin},
                         json=dict(name='Demo Farmer',email='demo@example.test',password=PASSWORD))
    assert response.status_code==201,response.text
    cookies=response.headers.get_list('set-cookie')
    assert any('field_shift_session=' in value and 'Secure' in value for value in cookies)
    assert any('field_shift_auth=' in value and 'Secure' in value for value in cookies)
