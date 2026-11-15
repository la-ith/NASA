"""Regression and integration tests for FS-001 through FS-007."""
import os
import time
from threading import Event
from datetime import date, timedelta

os.environ['FIELD_SHIFT_DB'] = ':memory:'
os.environ['FIELD_SHIFT_WARMUP'] = '0'

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api import v2
from app.services.analysis_v2 import simulate_season, simulate_climate_only
from app.services.run_v2 import run_analysis
from app.domain.crop_catalog import load_catalog
from app.geo.boundaries import state_at
from test_audit_fixes import synthetic_weather

BODY = {'mode':'sample','lat':38.85,'lon':-99.33,'goal':'conserve_water',
        'start_year':2020,'end_year':2020,'decision_year':2026,
        'history':[{'year':2025,'crop':'maize_grain'}]}


def test_demand_independent_of_soil_and_polar_handling():
    for crop in load_catalog().crops.values():
        days=[date(2020,5,1)+timedelta(days=i) for i in range(crop.stages.total)]
        w=synthetic_weather(days,range(50,90),range(100,len(days)))
        index={d:i for i,d in enumerate(days)}
        a,x=simulate_season(crop,w,index,days[0],200,78,.5)
        b,y=simulate_climate_only(crop,w,index,days[0])
        assert a == b == 'ok'
        assert x.etc_standard == pytest.approx(y.etc_standard,abs=1e-10)
        assert x.et0 == y.et0 and x.kc_end_adjusted == y.kc_end_adjusted
        assert y.rainfed_deficit is None
        from dataclasses import replace
        winter=[date(2020,1,1)+timedelta(days=i) for i in range(crop.stages.total)]
        polar=replace(w,dates=winter,latitude=90)
        status,_=simulate_climate_only(crop,polar,{d:i for i,d in enumerate(winter)},winter[0])
        assert status=='outside_applicability'


@pytest.mark.parametrize('change',[
    {'planting_dates':{'maize_grain':'02-31'}},
    {'planting_dates':{'maize_grain':'04-31'}},
    {'planting_dates':{'maize_grain':'02-29'},'end_year':2021},
    {'planting_dates':{'nonsense':'05-01'}},
    {'history':[{'year':2025,'crop':'soybean'},{'year':2025,'crop':'maize_grain'}]},
    {'history':[{'year':2027,'crop':'soybean'}]},
])
def test_invalid_input_does_not_enqueue(change):
    with TestClient(app) as c:
        assert c.post('/api/v2/analyses',json={**BODY,**change}).status_code == 422
        assert app.state.db.execute('SELECT count(*) FROM v2_job').fetchone()[0] == 0


def test_gap_does_not_infer_previous_crop():
    # Empty candidate list is not needed: zero weather years avoids unrelated simulation.
    from app.adapters.power import DailyWeather
    w=DailyWeather([date(2020,1,1)],{},38.85,-99.33,500,{})
    r=run_analysis({**BODY,'start_year':2021,'end_year':2020,
                    'history':[{'year':2023,'crop':'maize_grain'}]},
                   state_at(-99.33,38.85),w,None,load_catalog(),'sample')
    assert all(s['role']=='alternative' and s['rotation']['key']=='unknown_previous' for s in r['strategies'])


def test_worker_responsiveness_and_session_isolation(monkeypatch):
    started,release=Event(),Event()
    original=v2.run_analysis
    def slow(*args):
        started.set()
        assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(v2,'run_analysis',slow)
    with TestClient(app) as c:
        response=c.post('/api/v2/analyses',json=BODY).json()
        assert started.wait(3)
        before=time.monotonic()
        assert c.get('/api/v2/health').status_code==200
        assert time.monotonic()-before < 1
        owner_cookie=c.cookies.get('field_shift_session')
        c.cookies.clear()
        assert c.get(response['status_url']).status_code == 404
        c.cookies.set('field_shift_session',owner_cookie)
        release.set()
        for _ in range(100):
            job=c.get(response['status_url']).json()
            if job['state'] in ('succeeded','failed'): break
            time.sleep(.03)
        assert job['state']=='succeeded',job
        assert c.get(job['analysis_url']).status_code==200
        c.cookies.clear()
        assert c.get(job['analysis_url']).status_code==404
        assert c.get(job['analysis_url']+'/report').status_code==404


def test_restarted_jobs_become_terminal(tmp_path):
    from app.db.database import connect
    path=str(tmp_path/'review.db')
    db=connect(path)
    db.execute("INSERT INTO v2_job (job_id,created_utc,updated_utc,state) VALUES ('old','x','x','running')")
    db.commit();db.close()
    db=connect(path)
    row=db.execute("SELECT state,error FROM v2_job WHERE job_id='old'").fetchone()
    assert row[0]=='failed' and 'server_restart' in row[1]
    db.close()


def test_queue_admission_limit(monkeypatch):
    monkeypatch.setattr(v2,'_running',set(range(16)))
    # Do not run lifespan teardown with fake tasks.
    with TestClient(app) as c:
        response=c.post('/api/v2/analyses',json=BODY)
        assert response.status_code==503 and response.json()['error']['code']=='queue_full'
        v2._running.clear()
