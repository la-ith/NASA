"""Units/QA and independent metric checks; no live calls or holdout reads."""
import csv
import io
import json
import math
from app.validation.pilot import metrics, normalize_station, SITES, number


def test_metrics_known_errors_and_missing():
    r=metrics([(2,1),(3,5),(None,4)],3)
    assert r['n']==2 and r['missing_or_excluded']==1
    assert r['bias']==-.5 and r['mae']==1.5 and r['rmse']==math.sqrt(2.5)
    assert metrics([],153)['bias'] is None
    assert number('-999') is None and number('NaN') is None


def test_azmet_flags_and_height_conversion():
    row={'datetime':'2020-05-01','meta_needs_review':'1','wind_spd_mean_mps':'3'}
    parsed=normalize_station(SITES[0],json.dumps({'data':[row]}).encode())
    v,qa=next(iter(parsed.values()))
    assert v['u2'] is None and qa==['station_review_flag']
    row.update(meta_needs_review='0')
    v,_=next(iter(normalize_station(SITES[0],json.dumps({'data':[row]}).encode()).values()))
    assert 2 < v['u2'] < 3


def test_coagmet_fraction_qa_and_radiation_conversion():
    columns=['Date','Max Temp','Min Temp','Solar Rad','Wind Run','Liquid Precip','ASCE ETo','RH Max','RH Min']
    buff=io.StringIO();w=csv.writer(buff)
    w.writerow(columns);w.writerow(['units']*len(columns))
    w.writerow(['07/01/2020',30,15,250,172.8,0,5,.8,.001])
    v,qa=next(iter(normalize_station(SITES[1],buff.getvalue().encode()).values()))
    assert v['ea'] is None and v['eto'] is None and v['station_forced_eto'] is None
    assert v['rs']==21.6 and qa==['suspect_rh_min_le_0.01']
    assert abs(v['u2']-2)<.01
