"""POST /api/v1/analyses and GET /api/v1/analyses/{id} (sections 6 and 10)."""
import json
import re
import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, model_validator

from app.domain.crops import candidates, load_crops
from app.domain.evaluation import evaluate_plan, load_rule_states
from app.domain.plans import build_plans
from app.domain.rules import RULES_VERSION
from app.services import explanations
from app.services.analysis_store import save_analysis
from app.services.climate_context import ClimateContext, build_climate_context
from app.services.climate_provider import ADAPTER_VERSION

router = APIRouter()
ENGINE_VERSION = "1.0.0"
SEASON_LABEL = re.compile(r"(\d{4})/(\d{2})")


class AreaIn(BaseModel):
    value: float = Field(gt=0)
    unit: Literal["dunum", "hectare", "acre"]


class FieldIn(BaseModel):
    label: str | None = None
    lat: float
    lon: float
    area: AreaIn
    irrigation: Literal["rain-fed", "irrigated", "mixed", "unknown"]
    soil: str = "unknown"

    @model_validator(mode="after")
    def in_pilot_area(self) -> "FieldIn":
        if (self.lat, self.lon) != (31.5, 35.1):
            raise ValueError("This version supports only the Hebron pilot area (31.5 N, 35.1 E).")
        return self


class SeasonIn(BaseModel):
    season: str  # for example "2025/26"
    crop: str  # a crop from GET /api/v1/crops, or "unknown"


class AnalysisRequest(BaseModel):
    mode: Literal["live", "sample"]
    field: FieldIn
    history: list[SeasonIn] = Field(min_length=1, max_length=5)  # oldest first
    candidate_season: Literal["2026/27"]
    goal: Literal["conserve_water", "improve_soil_rotation", "balance_both"]
    current_practice_crop: str | None = None  # required only when the last season's crop is not a candidate
    extra_candidates: list[str] = Field(default_factory=list, max_length=1)  # sample case only (Plan D)

    @model_validator(mode="after")
    def seasons_and_sample_rules(self) -> "AnalysisRequest":
        years = []
        for s in self.history:
            match = SEASON_LABEL.fullmatch(s.season)
            if not match or (int(match[1]) + 1) % 100 != int(match[2]):
                raise ValueError(f"{s.season!r} is not a season label like 2025/26.")
            years.append(int(match[1]))
        last = int(self.candidate_season[:4]) - 1
        if years != list(range(last - len(years) + 1, last + 1)):
            raise ValueError(f"Seasons must be consecutive and end with {last}/{(last + 1) % 100:02d}.")
        if self.extra_candidates and self.mode != "sample":
            raise ValueError("extra_candidates is accepted only in sample mode.")
        return self


def _invalid(field: str, message: str) -> RequestValidationError:
    return RequestValidationError([{"type": "value_error", "loc": ("body", field), "msg": message, "input": None}])


def round1(x: float | None) -> float | None:
    return None if x is None else round(x, 1)  # round only for output, never before calculating


def climate_evidence(ctx: ClimateContext) -> dict:
    ind, site = ctx.indicators, ctx.site
    return {
        "provider": "NASA POWER", "parameter": "PRECTOTCORR", "community": "AG", "units": "mm/day",
        "api_version": ctx.record.api_version, "sources": ctx.record.sources,
        "fill_value": ctx.record.fill_value, "time_standard": ctx.record.time_standard,
        "period": [d.isoformat() for d in ctx.period], "retrieved_utc": ctx.retrieved_utc.isoformat(),
        "valid_days": ctx.record.valid_days, "missing_days": ctx.record.missing_days,
        "quality_flags": ctx.record.flags, "cell_elevation_m": ctx.record.cell_elevation_m,
        "seasons": [
            {"season": s.label, "total_mm": round1(s.total_mm), "valid_days": s.valid_days, "days": s.days}
            for s in ctx.seasons
        ],
        "indicators": {
            "baseline_mean_mm": round1(ind.baseline_mean_mm),
            "baseline_cv_pct": round1(ind.baseline_cv_pct),
            "anomalies_pct": {k: round1(v) for k, v in ind.anomalies_pct.items()},
            "recent_shift_pct": round1(ind.recent_shift_pct),
        },
        "site_check": {
            "result": site.result, "reason": site.reason,
            "cell_mm": round1(site.cell_mean_mm), "station_mm": site.station_mean_mm,
            "ratio": None if site.ratio is None else round(site.ratio, 2),
        },
    }


@router.post("/analyses")
async def create_analysis(body: AnalysisRequest, request: Request) -> dict:
    db = request.app.state.db
    crops = load_crops(db)
    supported = candidates(crops)
    history = [(s.season, s.crop) for s in body.history]
    for _, crop in history:
        if crop != "unknown" and crop not in crops:
            raise _invalid("history", f"Unknown crop choice {crop!r}. Use GET /api/v1/crops for the choices.")
    if any(crop in supported for crop in body.extra_candidates):
        raise _invalid("extra_candidates", "Plan D is for a crop this version does not support.")
    last_season, last_crop = history[-1]
    if last_crop in supported:
        if body.current_practice_crop not in (None, last_crop):
            raise _invalid("current_practice_crop", f"Current practice repeats {last_crop}, recorded for {last_season}.")
        current = last_crop
    elif body.current_practice_crop in supported:
        current = body.current_practice_crop
    else:
        raise _invalid("current_practice_crop", f"The crop for {last_season} is not a supported candidate; "
                                                f"choose the crop for current practice ({', '.join(supported)}).")

    climate = await build_climate_context(
        body.mode, body.field.lat, body.field.lon, int(body.candidate_season[:4]), request.app.state.http, db,
    )
    states = load_rule_states(db)
    field = body.field.model_dump()
    order = explanations.CRITERION_ORDER[body.goal]
    plans = []
    for plan in build_plans(history, current, supported, crops, body.extra_candidates, body.candidate_season):
        evaluated = evaluate_plan(plan, history, field, crops, climate, states)
        if evaluated["status"] == "evaluated":
            evaluated["criteria"].sort(key=lambda c: order.index(c["criterion"]))
        plans.append(evaluated)
    criteria = [c for p in plans if p["status"] == "evaluated" for c in p["criteria"]]
    illustrative = any(c["rule_state"] != "reviewed" for p in plans for c in p["criteria"])
    partial = any(c["label"] == "insufficient_evidence" for c in criteria) or bool(climate.record.flags)
    result = {
        "analysis_id": secrets.token_hex(4),
        "status": "partial" if partial else "complete",
        "mode": body.mode,
        "banners": {"sample_data": body.mode == "sample", "illustrative_rules": illustrative},
        "versions": {"rules": RULES_VERSION, "engine": ENGINE_VERSION, "adapter": ADAPTER_VERSION,
                     "power_api": climate.record.api_version},
        "field": field,
        "history": [s.model_dump() for s in body.history],
        "candidate_season": body.candidate_season,
        "goal": body.goal,
        "criterion_order": order,
        "summary": explanations.summary(body.goal, plans),
        "data": climate_evidence(climate),
        "plans": plans,
        "limitations": explanations.limitations(climate, illustrative),
        "local_questions": explanations.LOCAL_QUESTIONS,
        "notice": explanations.NOTICE,
        "acknowledgement": explanations.ACKNOWLEDGEMENT,
        "data_reference": explanations.data_reference(climate),
    }
    save_analysis(db, body.model_dump(), result, climate)
    return result


@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, request: Request) -> dict:
    """Return the stored snapshot unchanged, so a saved result is reproduced exactly."""
    row = request.app.state.db.execute(
        "SELECT result_snapshot FROM analysis WHERE analysis_id = ?", (analysis_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return json.loads(row[0])
