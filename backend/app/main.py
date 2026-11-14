"""FastAPI app: startup cache warm-up, the error shapes from section 10, and the web app."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.analyses import router as analyses_router
from app.api.reference import router as reference_router
from app.api.v2 import router as v2_router
from app.db.database import connect
from app.services.climate_context import build_climate_context
from app.services.climate_provider import ProviderError
from app.services.validation import UnusableRecord

log = logging.getLogger("field_shift")
DB_PATH = os.environ.get("FIELD_SHIFT_DB", "field_shift.db")  # created in the working directory
WARM_UP = os.environ.get("FIELD_SHIFT_WARMUP", "1") != "0"  # tests switch it off to stay offline
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient()
    app.state.db = connect(DB_PATH)
    if WARM_UP:
        try:  # warm the pilot cache, so the demo does not depend on a live call
            await build_climate_context("live", 31.5, 35.1, 2026, app.state.http, app.state.db)
        except (ProviderError, UnusableRecord) as exc:
            log.warning("Pilot cache warm-up failed; live requests will try again: %s", exc)
    yield
    await app.state.http.aclose()
    app.state.db.close()


app = FastAPI(title="Field Shift API", version="1.0.0", lifespan=lifespan)
app.include_router(analyses_router, prefix="/api/v1")
app.include_router(reference_router, prefix="/api/v1")
app.include_router(v2_router)  # spec v4.0: U.S. release; /api/v1 stays for the Hebron regression fixtures


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = jsonable_encoder(exc.errors())
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
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
