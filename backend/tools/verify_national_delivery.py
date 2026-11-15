"""Verify national grid publication and its canonical source hashes; never an accuracy certificate."""
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import rasterio

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.adapters import content_hash
from app.services.raster_layers import LAYER_ROOT


def verify():
    status=json.loads((LAYER_ROOT/'national-build-status.json').read_text(encoding='utf-8'))
    if status['state']!='complete' or status['failures']:
        raise ValueError('The national plan is not complete without provider failures')
    report=dict(verified_utc=datetime.now(timezone.utc).isoformat(),year=status['year'],
                scope=status['states'],planned_cells=status['planned_cells'],
                crop_season_scenarios=[],scientific_qualification='not_qualified',
                meaning='Complete processing plan; valid scientific pixels are counted separately. No field accuracy claim.')
    for aid in status['artifacts']:
        folder=LAYER_ROOT/'published'/aid
        m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        records=json.loads((folder/'records.json').read_text(encoding='utf-8'))
        expected=content_hash(dict(schema=m['schema'],job=m['job'],records=records))[:32]
        if aid!=expected:raise ValueError('Published record hash mismatch')
        actual_sha=hashlib.sha256((folder/'data.tif').read_bytes()).hexdigest()
        if actual_sha!=m['raster_sha256']:raise ValueError('Published raster hash mismatch')
        if len(records)!=status['planned_cells']:raise ValueError('Incomplete record set')
        if len({r['cell']['id'] for r in records})!=len(records):raise ValueError('Duplicate cells')
        with rasterio.open(folder/'data.tif') as src:
            if src.tags(ns='IMAGE_STRUCTURE').get('LAYOUT')!='COG':raise ValueError('Not a COG')
            valid={key:int(np.sum(src.read(band)!=src.nodata)) for key,band in m['bands'].items()}
        if valid!=m['coverage']['metric_valid_cells']:raise ValueError('Per-metric no-data count mismatch')
        states=Counter(r['cell']['state'] for r in records)
        if len(states)!=50:raise ValueError('The national plan does not cover all 50 states')
        report['crop_season_scenarios'].append(dict(crop=m['job']['crop'],artifact_id=aid,
            raster_sha256=actual_sha,coverage=m['coverage'],planned_by_state=dict(sorted(states.items())),
            valid_irrigation_by_state=dict(sorted(Counter(r['cell']['state'] for r in records
                if r.get('values',{}).get('irrigated_net_irrigation') is not None).items())),
            exclusions=dict(Counter(r['reason'] for r in records if r['status']!='ok')),
            spatial_support=m['spatial_support']))
    db_path=LAYER_ROOT/'grid-sources.db'
    with sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True) as db:
        counts=Counter()
        for provider,manifest,raw in db.execute('SELECT provider,manifest,raw_response FROM v2_source_record'):
            if content_hash(json.loads(raw))!=json.loads(manifest)['content_sha256']:
                raise ValueError('Canonical source JSON hash mismatch')
            counts[provider]+=1
    report['canonical_source_json_hashes_verified']=dict(counts)
    target=ROOT/'docs/validation/results/national-grid-delivery.json'
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(scope=report['scope'],planned_cells=report['planned_cells'],
        artifacts=[dict(crop=x['crop'],id=x['artifact_id'],valid=x['coverage']['metric_valid_cells'])
                   for x in report['crop_season_scenarios']],source_hashes_verified=dict(counts)),indent=2))


if __name__=='__main__':verify()
