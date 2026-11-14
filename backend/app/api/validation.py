"""Scientific readiness: numerical test success does not establish field accuracy."""
import json
import hashlib
from fastapi import APIRouter,HTTPException
from app.validation.pilot import OUT

router=APIRouter(prefix='/api/v2/validation')


@router.get('/status')
async def status():
    path=OUT/'results/holdout-evaluation-v1.json'
    report=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    california=OUT/'results/fresno-cimis-comparison.json'
    ca=json.loads(california.read_text(encoding='utf-8')) if california.exists() else None
    return dict(numerical_verification='FAO-56 worked examples and conservation checks',
        engineering_weather_screening=report['engineering_weather_screening'] if report else 'not_evaluated',
        field_irrigation_accuracy='not validated',expert_review='pending',
        california_status=ca['status'] if ca else 'not_evaluated',
        california='Reference ET0 comparison only; crop irrigation field validation remains pending',
        holdouts_consumed=bool(report and report['holdouts_consumed']),release_ready=False,
        report_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
        report_url='/api/v2/validation/holdout' if report else None)


@router.get('/holdout')
async def holdout():
    path=OUT/'results/holdout-evaluation-v1.json'
    if not path.exists():raise HTTPException(404,'holdout study has not run in this deployment')
    return json.loads(path.read_text(encoding='utf-8'))
