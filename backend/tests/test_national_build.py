"""A provider failure must remain a gap, then resume without recomputing successful checkpoints."""
import asyncio
import hashlib
import json
from app.services import grid_pipeline as grid


def test_all_crop_resume_and_per_metric_nodata(monkeypatch,tmp_path):
    monkeypatch.setattr(grid,'LAYER_ROOT',tmp_path)
    cells=[dict(id='68-129',row=68,col=129,lat=39,lon=-99.375,state='KS'),
           dict(id='69-129',row=69,col=129,lat=38.5,lon=-99.375,state='KS')]
    monkeypatch.setattr(grid,'plan',lambda states=None:cells)
    calls=[];failing=True
    async def calculate(cell,year,crop,db,client):
        calls.append((cell['id'],crop))
        if failing and cell['id']=='69-129':raise ConnectionError('provider offline')
        values={key:10.0 for key in grid.BANDS}
        if crop=='sorghum_grain' and cell['id']=='68-129':values['rainfed_deficit']=None
        return dict(cell=cell,status='ok',values=values,provenance={},soil_coverage='available')
    async def no_delay(seconds):pass
    monkeypatch.setattr(grid,'calculate_cell',calculate)
    monkeypatch.setattr(grid.asyncio,'sleep',no_delay)
    partial=asyncio.run(grid.build_all(2020,concurrency=1))
    assert all(m['coverage']['processed_cells']==1 and not m['coverage']['complete'] for m in partial)
    status=json.loads((tmp_path/'national-build-status.json').read_text())
    assert status['state']=='partial' and len(status['failures'])==1
    before=len(calls);failing=False
    complete=asyncio.run(grid.build_all(2020,concurrency=1))
    assert len(calls)-before==3
    assert all(m['coverage']['complete'] and m['coverage']['processed_cells']==2 for m in complete)
    sorghum=next(m for m in complete if m['job']['crop']=='sorghum_grain')
    assert sorghum['coverage']['metric_valid_cells']['rainfed_deficit']==1
    assert sorghum['coverage']['metric_valid_cells']['precipitation']==2
    target=tmp_path/'published'/sorghum['artifact_id']/'data.tif'
    assert hashlib.sha256(target.read_bytes()).hexdigest()==sorghum['raster_sha256']
    assert json.loads((tmp_path/'national-build-status.json').read_text())['state']=='complete'
