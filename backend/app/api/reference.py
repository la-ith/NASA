"""GET /api/v1/crops, /api/v1/rules and /api/v1/demo (section 10)."""
from fastapi import APIRouter, Request

from app.domain.crops import TYPE_LABEL, candidates, load_crops
from app.domain.rules import RULES_VERSION

router = APIRouter()

DEMO_CASE = {  # the section 1 demo field; illustrative, not a real farm
    "mode": "sample",
    "field": {"label": "Sample field", "lat": 31.5, "lon": 35.1, "area": {"value": 20, "unit": "dunum"},
              "irrigation": "rain-fed", "soil": "unknown"},
    "history": [{"season": "2023/24", "crop": "unknown"}, {"season": "2024/25", "crop": "wheat"},
                {"season": "2025/26", "crop": "wheat"}],
    "candidate_season": "2026/27",
    "goal": "improve_soil_rotation",
    "extra_candidates": ["maize"],
}


@router.get("/crops")
async def list_crops(request: Request) -> dict:
    crops = load_crops(request.app.state.db)
    return {
        "candidates": [
            {"name": name, "type": TYPE_LABEL[crops[name].crop_type], "water_need_min_mm": crops[name].water_need_min_mm}
            for name in candidates(crops)
        ],
        "history_choices": [{"name": name, "type": TYPE_LABEL[p.crop_type]} for name, p in crops.items()]
        + [{"name": "unknown", "type": "unknown"}],
    }


@router.get("/rules")
async def list_rules(request: Request) -> list[dict]:
    rows = request.app.state.db.execute(
        "SELECT code, version, condition, effect, citation, region, reviewer, review_state FROM rotation_rule"
        " WHERE version = ? ORDER BY rule_id", (RULES_VERSION,)
    )
    keys = ("code", "version", "condition", "effect", "citation", "region", "reviewer", "review_state")
    return [dict(zip(keys, row)) for row in rows]


@router.get("/demo")
async def demo_case() -> dict:
    return {"label": "Sample case: illustrative, not a real farm", "request": DEMO_CASE}
