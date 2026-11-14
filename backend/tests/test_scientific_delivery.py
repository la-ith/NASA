"""Meaningful validation gates, private configuration, provider failure and raster-integrity checks."""
import asyncio
import copy
import io
import json
import math
import os
from datetime import date,timedelta
from pathlib import Path
import httpx
import numpy as np
import rasterio
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import load_private_env
from app.adapters import cimis,SourceIntegrityError
from app.services import raster_layers as rasters,grid_pipeline,assistant
from app.validation.holdout import evaluate_gates,bias_interval,load_protocol


def test_dotenv_literal_private_and_process_precedence(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_MODEL','process-model')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('SHOULD_NOT_LOAD',raising=False)
    p=tmp_path/'.env';p.write_text('OPENAI_API_KEY="literal-${HOME}-example"\nOPENAI_MODEL=file-model\nSHOULD_NOT_LOAD=bad\n')
    load_private_env(p)
    assert os.environ['OPENAI_API_KEY']=='literal-${HOME}-example'
    assert os.environ['OPENAI_MODEL']=='process-model' and 'SHOULD_NOT_LOAD' not in os.environ


def test_frozen_protocol_and_failed_gates_are_not_hidden():
    p,lock=load_protocol()
    assert lock['evaluation_started'] and lock['sha256']
    m=dict(eto=dict(n=153,bias=.1,rmse=.8),eto_season_total=dict(available=True,model_sum=610,reference_sum=600),
           rain_season_total=dict(available=True,model_sum=400,reference_sum=200))
    r=evaluate_gates(m,p)
    assert r['status']=='failed' and r['reasons']==['rain season relative bias gate failed']
    m['rain_season_total']['model_sum']=210
    assert evaluate_gates(m,p)['status']=='passed'
    m['eto']['n']=100
    assert 'insufficient paired ET0 days' in evaluate_gates(m,p)['reasons']


def test_block_bootstrap_constant_error_and_repeatability():
    p,_=load_protocol()
    errors=[(date(2020,5,1)+timedelta(days=i),2.0) for i in range(30)]
    assert bias_interval(errors,p)==bias_interval(errors,p)
    assert bias_interval(errors,p)['bias_95_percent_interval']==[2,2]


def test_quota_failure_is_distinct_and_secret_is_not_echoed(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','private-test-value');monkeypatch.setenv('OPENAI_MODEL','gpt-6-luna')
    def handler(request):
        assert json.loads(request.content)['reasoning']=={'effort':'none'}
        return httpx.Response(429,json={'error':{'code':'credit_balance_exhausted','message':'private-test-value'}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await assistant.answer(c,'water demand',None,[])
    r=asyncio.run(run())
    assert r['service_status']=='quota_exhausted' and 'private-test-value' not in json.dumps(r)


def test_arabic_fallback_preserves_limits_and_citations(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    r=asyncio.run(assistant.answer(None,'كيف أحسب الماء للمحصول؟',None,[]))
    assert r['language']=='ar' and 'الأدلة' in r['answer']
    assert all(x['url'].startswith('https://') for x in r['evidence'])
    assert 'تنبؤ' in r['limitation'] and 'مرحلة' in r['questions'][0]


@pytest.mark.parametrize('question,expected',[
    ('maize flowering care','maize-care'),('soybean pod fill care','soybean-care'),
    ('كيف أعتني بالذرة الرفيعة؟','sorghum-care')])
def test_crop_evidence_is_relevant_and_arabic_is_curated(monkeypatch,question,expected):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    r=asyncio.run(assistant.answer(None,question,None,[]))
    ids=[x['id'] for x in r['evidence']]
    assert expected in ids
    assert not any(x.endswith('-care') and x!=expected for x in ids)


def test_analysis_fallback_uses_engine_numbers_without_model(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    summary={k:dict(spread={'median':123.4},unit='mm per season') for k in
             ('etc_standard','rainfed_deficit','irrigated_net_irrigation','et0','precipitation')}
    analysis=dict(analysis_id='example',limitations=['Historical only'],strategies=[dict(id='S1',name='Maize',result=dict(summary=summary))])
    r=asyncio.run(assistant.answer(None,'What is the deficit?',analysis,[]))
    cards=[x for x in r['evidence'] if x.get('metric')=='rainfed_deficit']
    assert cards and cards[0]['value']==123.4 and '123.4' in r['answer']


def cimis_fixture():
    values={field:dict(Value='2',Qc=' ',Unit=next(iter(units))) for _,field,units in cimis.ITEMS.values()}
    row=dict(Date='2020-05-01',Station='80',Scope='daily',Standard='metric',**values)
    return dict(Data=dict(Providers=[dict(Name='cimis',Type='station',Records=[row])]))


def test_cimis_current_contract_flags_dates_units_and_station():
    raw=cimis_fixture();start=date(2020,5,1);end=date(2020,5,2)
    parsed=cimis.normalize(raw,80,start,end)
    assert parsed['records']['2020-05-01']['values']['eto']==2
    assert parsed['records']['2020-05-02']['values']['eto'] is None
    raw['Data']['Providers'][0]['Records'][0]['DayAsceEto']['Qc']='Y'
    assert cimis.normalize(raw,80,start,end)['records']['2020-05-01']['values']['eto'] is None
    with pytest.raises(SourceIntegrityError):cimis.normalize(raw,81,start,end)
    raw['Data']['Providers'][0]['Records'][0]['DayPrecip']['Unit']='(in)'
    with pytest.raises(SourceIntegrityError):cimis.normalize(raw,80,start,end)


def test_cimis_key_only_in_header(monkeypatch):
    monkeypatch.setenv('CIMIS_APP_KEY','private-cimis-key')
    def handler(request):
        assert request.headers['Ocp-Apim-Subscription-Key']=='private-cimis-key'
        assert 'private-cimis-key' not in str(request.url)
        assert request.url.path=='/StationWeb/GetDataByStationNumber'
        return httpx.Response(200,json=cimis_fixture())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await cimis.daily(c,80,date(2020,5,1),date(2020,5,1))
    raw,result=asyncio.run(run())
    assert 'private-cimis-key' not in json.dumps(result)


def tile_for(lon,lat,z=6):
    return z,int((lon+180)/360*2**z),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*2**z)


@pytest.mark.parametrize('lon,lat',[(-99.33,38.85),(-149.1,61.58),(-156.45,20.85),(173.2,52.93)])
def test_us_mask_contains_mainland_alaska_hawaii_and_positive_longitude(lon,lat):
    z,x,y=tile_for(lon,lat)
    # Small islands may fall between coarse display pixels; valid land in their tile must be retained.
    assert rasters.us_mask(z,x,y).any()


def test_nasa_tile_keeps_source_alpha_masks_and_rejects_date_gap(tmp_path,monkeypatch):
    monkeypatch.setattr(rasters,'LAYER_ROOT',tmp_path)
    z,x,y=tile_for(-99.33,38.85)
    source=np.full((256,256,4),255,dtype='uint8');source[0,:,3]=0
    def handler(request):return httpx.Response(200,content=rasters.png(source))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await rasters.nasa_tile(c,'imerg_rain_rate',date(2020,7,1),z,x,y)
    b=asyncio.run(run());a=np.asarray(Image.open(io.BytesIO(b)))
    assert np.array_equal(a[:,:,3],np.where(rasters.us_mask(z,x,y),source[:,:,3],0))
    layer=rasters.gibs_layer('imerg_rain_rate')
    assert not rasters.date_supported(layer,date(2025,10,25))
    cache=next(tmp_path.rglob('*.png'));cache.write_bytes(b'corrupt')
    with pytest.raises(SourceIntegrityError):asyncio.run(run())


def test_cog_values_nodata_and_immutable_publication(tmp_path,monkeypatch):
    monkeypatch.setattr(grid_pipeline,'LAYER_ROOT',tmp_path);monkeypatch.setattr(rasters,'LAYER_ROOT',tmp_path)
    record=dict(status='ok',cell=dict(row=68,col=129,lat=39,lon=-99.375,state='KS'),
                values={k:10+i for i,k in enumerate(grid_pipeline.BANDS)})
    m=grid_pipeline.publish([record],dict(year=2020,crop='maize_grain'),2)
    assert not m['coverage']['complete'] and m['coverage']['computed_cells']==1
    value=rasters.derived_value(m['artifact_id'],'rainfed_deficit',-99.375,39)
    assert value['value']==13 and value['unit']=='mm per season'
    assert rasters.derived_value(m['artifact_id'],'rainfed_deficit',-98.75,39)['value'] is None
    old=(tmp_path/'published'/m['artifact_id']/'data.tif').read_bytes()
    other=copy.deepcopy(record);other['values']['rainfed_deficit']=25
    newer=grid_pipeline.publish([other],dict(year=2020,crop='maize_grain'),2)
    assert newer['artifact_id']!=m['artifact_id']
    assert (tmp_path/'published'/m['artifact_id']/'data.tif').read_bytes()==old
    with rasterio.open(tmp_path/'published'/m['artifact_id']/'data.tif') as source:
        assert source.tags(ns='IMAGE_STRUCTURE')['LAYOUT']=='COG'


def test_map_routes_catalog_and_invalid_requests():
    with TestClient(app) as c:
        catalog=c.get('/api/v2/map/layers').json()
        assert len(catalog['source_layers'])==3 and not any(x['quantitative_pixel_query'] for x in catalog['source_layers'])
        assert c.get('/api/v2/map/nasa/imerg_rain_rate/2025-10-25/6/14/24.png').status_code==422
        assert c.get('/api/v2/map/nasa/imerg_rain_rate/2020-07-01/6/999/0.png').status_code==422
        assert c.get('/api/v2/map/grids/not-a-file').status_code==404
        readiness=c.get('/api/v2/validation/status').json()
        assert readiness['engineering_weather_screening']=='not_qualified'
        assert readiness['holdouts_consumed'] and not readiness['release_ready']
