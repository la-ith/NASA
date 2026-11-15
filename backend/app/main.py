"""FastAPI app: startup cache warm-up, the error shapes from section 10, and the web app."""
import logging
import math
import os
import asyncio
import hashlib
import secrets
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import load_private_env
load_private_env()  # before routers read their storage/cache configuration

from app.api.analyses import router as analyses_router
from app.api.reference import router as reference_router
from app.api.v2 import router as v2_router
from app.api.data import router as data_router
from app.api.products import router as products_router
from app.api.chat import router as chat_router
from app.api.raster import router as raster_router
from app.api.validation import router as validation_router
from app.api.accounts import router as accounts_router
from app.services import accounts
from app.db.database import connect
from app.services.climate_context import build_climate_context
from app.services.climate_provider import ProviderError
from app.services.validation import UnusableRecord

log = logging.getLogger("field_shift")
DB_PATH = os.environ.get("FIELD_SHIFT_DB", "field_shift.db")  # created in the working directory
WARM_UP = os.environ.get("FIELD_SHIFT_WARMUP", "0") != "0"  # opt-in legacy Hebron cache warmup only
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient()
    app.state.db = connect(DB_PATH)
    app.state.analysis_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="field-analysis")
    app.state.chat_lock = asyncio.Lock()
    app.state.auth_slots = asyncio.Semaphore(2)
    if WARM_UP:
        try:  # warm the pilot cache, so the demo does not depend on a live call
            await build_climate_context("live", 31.5, 35.1, 2026, app.state.http, app.state.db)
        except (ProviderError, UnusableRecord) as exc:
            log.warning("Pilot cache warm-up failed; live requests will try again: %s", exc)
    yield
    from app.api.v2 import _running
    tasks = list(_running)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    app.state.analysis_executor.shutdown(wait=True)
    await app.state.http.aclose()
    app.state.db.close()


app = FastAPI(title="Field Shift API", version="2.3.0", lifespan=lifespan)
app.include_router(analyses_router, prefix="/api/v1")
app.include_router(reference_router, prefix="/api/v1")
app.include_router(v2_router)  # spec v4.0: U.S. release; /api/v1 stays for the Hebron regression fixtures
app.include_router(data_router)
app.include_router(products_router)
app.include_router(chat_router)
app.include_router(raster_router)
app.include_router(validation_router)
app.include_router(accounts_router)


@app.middleware("http")
async def session_scope(request: Request, call_next):
    if request.method in ('POST','PUT','PATCH','DELETE'):
        origin=request.headers.get('origin')
        allowed_origins={value.strip().rstrip('/') for value in
                         os.environ.get('FIELD_SHIFT_ALLOWED_ORIGINS','').split(',') if value.strip()}
        if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/') and origin.rstrip('/') not in allowed_origins:
            return JSONResponse(status_code=403,content={'detail':'Cross-origin writes are not allowed'})
    token = request.cookies.get("field_shift_session")
    new = not token or len(token) != 43
    if new:
        token = secrets.token_urlsafe(32)
    request.state.owner = hashlib.sha256(token.encode()).hexdigest()
    request.state.user = accounts.identify(request.app.state.db,request.cookies.get(accounts.COOKIE))
    if request.state.user:request.state.owner='user:'+request.state.user['id']
    response = await call_next(request)
    if new:
        response.set_cookie("field_shift_session", token, httponly=True, samesite="strict",
                            secure=accounts.cookie_secure(request))
    return response


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = jsonable_encoder(exc.errors(), custom_encoder={float: lambda x: x if math.isfinite(x) else str(x)})
    if request.url.path.startswith('/api/v2/auth/'):
        fields=[{k:v for k,v in field.items() if k not in ('input','ctx')} for field in fields]
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_input", "fields": fields}})


@app.exception_handler(ProviderError)
async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
    error = {"code": "provider_error", "message": str(exc), "sample_available": True}
    return JSONResponse(status_code=502, content={"error": error})


@app.exception_handler(UnusableRecord)  # also handles DataIntegrityError
async def data_error(request: Request, exc: UnusableRecord) -> JSONResponse:
    error = {"code": exc.code, "message": str(exc), "sample_available": True}
    return JSONResponse(status_code=502, content={"error": error})


if FRONTEND_DIR.is_dir():  # mounted last, so /api routes take precedence
    @app.get('/api/v2/showcase')
    async def showcase():
        from fastapi.responses import FileResponse
        return FileResponse(FRONTEND_DIR.parent/'data/fixtures/showcase_ks_hays.json',media_type='application/json')

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
