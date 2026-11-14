"""Rotation Evaluation Engine (section 5): hard constraints first, then R1-R6, each with evidence and an explanation."""
import sqlite3
from dataclasses import asdict

from app.domain.crops import CropProfile, family
from app.domain.plans import CandidatePlan
from app.domain.rules import RULES_VERSION, CriterionResult, hard_constraint, rainfall_risk, rotation_soil, water_fit
from app.services import explanations
from app.services.climate_context import ClimateContext


def load_rule_states(db: sqlite3.Connection) -> dict[str | None, str]:
    """Review state per rule code. The None key covers rotation results that no single rule produced."""
    states: dict[str | None, str] = dict(
        db.execute("SELECT code, review_state FROM rotation_rule WHERE version = ?", (RULES_VERSION,))
    )
    states[None] = "reviewed" if all(states.get(c) == "reviewed" for c in ("R1", "R2", "R3")) else "draft-unreviewed"
    return states


def _entry(result: CriterionResult, explanation: str, state: str) -> dict:
    return {**asdict(result), "rule_state": state, "explanation": explanation}


def evaluate_plan(
    plan: CandidatePlan, history: list[tuple[str, str]], field: dict, crops: dict[str, CropProfile],
    climate: ClimateContext, states: dict[str | None, str],
) -> dict:
    out = {"id": plan.code, "type": plan.role, "crop": plan.crop, "display": f"{history[-1][1]} → {plan.crop}",
           "why_included": plan.why_included}
    rejection = hard_constraint(plan.crop, crops, field["irrigation"])
    if rejection:
        return {**out, "status": "rejected", "rejection_reason": rejection.reason,
                "criteria": [_entry(rejection, rejection.reason, states[rejection.rule])], "inputs": []}

    profile = crops[plan.crop]
    rotation = rotation_soil(family(plan.crop, crops), [family(crop, crops) for _, crop in history])
    water = water_fit(profile.water_need_min_mm, field["irrigation"], climate.site, climate.indicators)
    risk = rainfall_risk(climate.indicators)
    criteria = [
        _entry(rotation.result, explanations.rotation(rotation.result, plan.crop, history, states[rotation.result.rule]),
               states[rotation.result.rule]),
        _entry(water, explanations.water(water, plan.crop, profile.water_need_min_mm, climate), states[water.rule]),
        _entry(risk, explanations.risk(risk, climate), states[risk.rule]),
    ]
    inputs = explanations.inputs(history, field, plan.crop, profile.water_need_min_mm, profile.water_source,
                                 rotation.seasons_needed, climate)
    return {**out, "status": "evaluated", "criteria": criteria, "inputs": inputs}
