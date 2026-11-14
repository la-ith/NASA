"""API v2 for the U.S. release (spec v4.0, section 21.2). /api/v1 stays for the Hebron regression fixtures.

Analyses run as background jobs: POST returns 202 with a job handle and the browser polls the job, so it never
waits on one long request. Error envelopes carry code, stage, message and whether a retry can help.
"""
import asyncio
import json
import re
import secrets
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, model_validator

from app.adapters import AdapterError, power
from app.domain.crop_catalog import load_catalog
from app.geo.boundaries import BOUNDARY_FILE, BOUNDARY_VERSION, state_at
from app.science.equations import EQUATIONS
from app.services import sources_v2
from app.services.analysis_v2 import ENGINE_VERSION
from app.services.report_v2 import render
from app.services.run_v2 import GOAL_ORDER, run_analysis

router = APIRouter(prefix="/api/v2")
MONTH_DAY = re.compile(r"(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
_running: set[asyncio.Task] = set()  # keeps background jobs referenced until they finish


class HistoryItem(BaseModel):
    year: int = Field(ge=1981, le=2100)
    crop: str  # a catalog crop id, another crop name, or "unknown"
    provenance: Literal["farmer", "team", "cdl"] = "farmer"


class SoilOverride(BaseModel):
    awc_mm_per_m: float = Field(gt=0, le=400)  # available water capacity, mm of water per m of soil
    depth_cm: float = Field(gt=0, le=500)
    hydrologic_group: Literal["A", "B", "C", "D"]


class AnalysisRequestV2(BaseModel):
    schema_version: Literal["2.0"] = "2.0"
    mode: Literal["live", "sample"]
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start_year: int = 2001
    end_year: int = 2025
    decision_year: int = Field(default_factory=lambda: date.today().year, ge=1982, le=2100)
    goal: Literal["conserve_water", "reduce_drought_stress", "improve_soil_rotation"]
    irrigation: Literal["rain-fed", "irrigated", "unknown"] = "unknown"
    history: list[HistoryItem] = Field(default_factory=list, max_length=10)
    current_practice: str | None = None
    candidates: list[str] | None = Field(default=None, max_length=6)
    planting_dates: dict[str, str] = Field(default_factory=dict)
    initial_depletion_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    soil: SoilOverride | None = None

    @model_validator(mode="after")
    def check_period_and_dates(self) -> "AnalysisRequestV2":
        last_complete = date.today().year - 1
        if not 1981 <= self.start_year <= self.end_year <= last_complete:
            raise ValueError(f"Seasons must run from 1981 at the earliest to {last_complete} at the latest.")
        if self.end_year - self.start_year > 39:
            raise ValueError("Use at most 40 seasons.")
        for crop, md in self.planting_dates.items():
            if crop not in load_catalog().crops:
                raise ValueError(f"Unknown crop in planting_dates: {crop}")
            if not MONTH_DAY.fullmatch(md):
                raise ValueError(f"Planting date for {crop} must look like 05-01.")
            month, day = map(int, md.split("-"))
            for year in range(self.start_year, self.end_year + 1):
                try:
                    date(year, month, day)
                except ValueError as exc:
                    raise ValueError(f"Invalid planting date for {crop} in {year}: {md}. "
                                     "The date must exist in every replay year.") from exc
        years = [h.year for h in self.history]
        if len(set(years)) != len(years):
            raise ValueError("History years must be unique.")
        if self.decision_year > date.today().year + 1:
            raise ValueError("Decision year must be current or next year, or a historical year.")
        if any(y >= self.decision_year or y > date.today().year for y in years):
            raise ValueError("History must precede the decision year and cannot be in the future.")
        return self


def _error(status: int, code: str, message: str, stage: str, retryable: bool) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "stage": stage, "message": message,
                                                               "retryable": retryable}})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "engine": ENGINE_VERSION, "boundary": BOUNDARY_VERSION}


@router.get("/crops")
async def crops() -> dict:
    catalog = load_catalog()
    return {"catalog_version": catalog.version, "review_state": catalog.review_state, "scope": catalog.scope,
            "crops": [{"id": c.id, "name": c.name, "family": c.family, "planting_default": c.planting_default,
                       "season_days": c.stages.total, "kc": [c.kc_ini, c.kc_mid, c.kc_end], "p": c.p,
                       "root_depth_m": c.root_depth_m, "sources": c.sources} for c in catalog.crops.values()],
            "goals": list(GOAL_ORDER)}


@router.get("/boundaries")
async def boundaries() -> FileResponse:
    """The 50-state GeoJSON the map draws; the same file the analysis checks against."""
    return FileResponse(BOUNDARY_FILE, media_type="application/geo+json")


@router.get("/equations")
async def equations() -> dict:
    return {k: {"formula": f, "unit": u, "reference": r} for k, (f, u, r) in EQUATIONS.items()}


class PointIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    mode: Literal["live", "sample"] = "live"


@router.post("/coverage")
async def coverage(body: PointIn, request: Request) -> dict:
    """What each source can supply at this point; map coverage is not a promise of analytical coverage."""
    state = state_at(body.lon, body.lat)
    if state is None:
        return {"in_scope": False, "state": None,
                "reason": "Outside the 50 U.S. states (territories, DC, ocean and other countries are not covered)."}
    weather_cov = power.check_coverage(body.lon, body.lat, sources_v2.FIXTURE_PERIOD[0], sources_v2.FIXTURE_PERIOD[1])
    try:
        soil = await sources_v2.soil(request.app.state.db, request.app.state.http, body.lon, body.lat, body.mode, None)
        soil_cov = {"status": soil.coverage, "reason": soil.reason,
                    "label": soil.soil.label if soil.soil else None}
    except sources_v2.SampleNotAvailable as exc:
        soil_cov = {"status": "unknown", "reason": str(exc)}
    except AdapterError as exc:
        soil_cov = {"status": "unknown", "reason": f"{exc.code}: {exc}"}
    return {"in_scope": True, "state": {"code": state.code, "name": state.name},
            "demo_site": sources_v2.demo_site(body.lon, body.lat),
            "products": {"nasa_power": weather_cov, "ssurgo": soil_cov,
                         "usda_cdl": {"status": "not_integrated", "reason": "planned; history is entered by the user"},
                         "gpm_imerg": {"status": "not_integrated", "reason": "planned (spec v4.0, section 4)"},
                         "smap": {"status": "not_integrated", "reason": "planned (spec v4.0, section 4)"}}}


async def _run_job(app, job_id: str, body: AnalysisRequestV2) -> None:
    db = app.state.db

    def update(state: str, stage: str, **extra) -> None:
        fields = {"state": state, "stage": stage, "updated_utc": _now(), **extra}
        with db:
            db.execute(f"UPDATE v2_job SET {', '.join(f'{k} = ?' for k in fields)} WHERE job_id = ?",
                       (*fields.values(), job_id))

    stage = "retrieving_weather"
    try:
        update("running", stage)
        request = body.model_dump(exclude_none=True)
        weather = await sources_v2.weather(db, app.state.http, body.lon, body.lat, date(body.start_year, 1, 1),
                                           date(body.end_year, 12, 31), body.mode)
        stage = "retrieving_soil"
        update("running", stage)
        soil = await sources_v2.soil(db, app.state.http, body.lon, body.lat, body.mode,
                                     body.soil.model_dump() if body.soil else None)
        stage = "simulating"
        update("running", stage)
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(app.state.analysis_executor, run_analysis, request,
                                      state_at(body.lon, body.lat), weather, soil.soil, load_catalog(), body.mode)
        try:
            result = await asyncio.shield(future)
        except asyncio.CancelledError:
            # Finish pure computation before shutdown closes shared resources.
            await future
            raise
        result["coverage"] = {"soil": {"status": soil.coverage, "reason": soil.reason}}
        if soil.soil is None:
            result["limitations"].append(f"Soil: {soil.reason}.")
        stage = "saving"
        analysis_id = secrets.token_urlsafe(12)
        result["analysis_id"] = analysis_id
        with db:
            owner = db.execute("SELECT owner FROM v2_job WHERE job_id = ?", (job_id,)).fetchone()[0]
            db.execute("INSERT INTO v2_analysis "
                       "(analysis_id, created_utc, status, engine_version, request, result, owner) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (analysis_id, _now(), result["status"], ENGINE_VERSION, json.dumps(request), json.dumps(result), owner))
        update("succeeded", "done", analysis_id=analysis_id)
    except asyncio.CancelledError:
        update("failed", stage, error=json.dumps({"code": "server_shutdown", "stage": stage,
                                                  "message": "Server stopped; retry the analysis.", "retryable": True}))
        raise
    except (AdapterError, sources_v2.SampleNotAvailable) as exc:
        retryable = exc.code == "provider_error"
        update("failed", stage, error=json.dumps({"code": exc.code, "stage": stage, "message": str(exc),
                                                  "retryable": retryable}))
    except Exception as exc:  # noqa: BLE001 - a job must always end in a recorded state
        update("failed", stage, error=json.dumps({"code": "internal_error", "stage": stage,
                                                  "message": f"{type(exc).__name__}: {exc}", "retryable": False}))


@router.post("/analyses", status_code=202)
async def create_analysis(body: AnalysisRequestV2, request: Request):
    state = state_at(body.lon, body.lat)
    if state is None:
        return _error(422, "outside_scope", "This location is outside the 50 U.S. states covered by this release.",
                      "validation", False)
    if len(_running) >= 16:
        return _error(503, "queue_full", "Analysis queue is full; retry later.", "queue", True)
    job_id = secrets.token_urlsafe(12)
    with request.app.state.db:
        request.app.state.db.execute("INSERT INTO v2_job (job_id, created_utc, updated_utc, state, stage, owner)"
                                     " VALUES (?, ?, ?, 'queued', 'queued', ?)",
                                     (job_id, _now(), _now(), request.state.owner))
    task = asyncio.create_task(_run_job(request.app, job_id, body))
    _running.add(task)
    task.add_done_callback(_running.discard)
    return {"job_id": job_id, "state": "queued", "status_url": f"/api/v2/jobs/{job_id}"}


@router.get("/jobs/{job_id}")
async def job(job_id: str, request: Request) -> dict:
    row = request.app.state.db.execute(
        "SELECT state, stage, analysis_id, error, updated_utc FROM v2_job WHERE job_id = ? AND owner = ?",
        (job_id, request.state.owner)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    out = {"job_id": job_id, "state": row[0], "stage": row[1], "updated_utc": row[4]}
    if row[2]:
        out["analysis_url"] = f"/api/v2/analyses/{row[2]}"
        out["analysis_id"] = row[2]
    if row[3]:
        out["error"] = json.loads(row[3])
    return out


def _load(request: Request, analysis_id: str) -> dict:
    row = request.app.state.db.execute("SELECT result FROM v2_analysis WHERE analysis_id = ? AND owner = ?",
                                       (analysis_id, request.state.owner)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return json.loads(row[0])


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, request: Request) -> dict:
    return _load(request, analysis_id)


@router.get("/analyses/{analysis_id}/report", response_class=PlainTextResponse)
async def report(analysis_id: str, request: Request) -> PlainTextResponse:
    return PlainTextResponse(render(_load(request, analysis_id), analysis_id), media_type="text/markdown")
