import asyncio
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.db.database import connect
from app.services.analysis_store import save_analysis
from app.services.climate_cache import cache_get, cache_put
from app.services.climate_context import build_climate_context
from app.services.climate_provider import power_query

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
LAT, LON = 31.5, 35.1
QUERY = power_query(LAT, LON, date(1991, 10, 1), date(2026, 5, 31))


@pytest.fixture
def db():
    return connect(":memory:")


@pytest.fixture(scope="module")
def raw():
    return json.loads((DEMO / "power_pilot_19911001_20260531.json").read_text(encoding="utf-8"))["response"]


def criterion(name: str, label: str, rule: str) -> dict:
    return {"criterion": name, "label": label, "rule": rule, "reason": "...", "explanation": "...",
            "rule_state": "draft-unreviewed"}


def test_cache_keeps_a_response_exactly_for_30_days(db, raw):
    now = datetime.now(timezone.utc)
    cache_put(db, QUERY, raw, now - timedelta(days=31))
    assert cache_get(db, QUERY) is None  # expired
    cache_put(db, QUERY, raw, now)
    assert cache_get(db, QUERY) == (raw, now)


def test_analysis_saved_in_the_v31_tables(db, raw):
    climate = asyncio.run(build_climate_context("sample", LAT, LON, 2026, None, db))
    request = {"mode": "sample", "goal": "improve_soil_rotation", "candidate_season": "2026/27",
               "field": {"label": None, "lat": 31.5, "lon": 35.1, "area": {"value": 20, "unit": "dunum"},
                         "irrigation": "rain-fed", "soil": "unknown"}}
    result = {"analysis_id": "a9f3c2e7", "status": "partial", "mode": "sample",
              "versions": {"rules": "0.1", "engine": "1.0.0"},
              "plans": [
                  {"id": "A", "type": "current_practice", "crop": "wheat", "why_included": "Current practice.",
                   "criteria": [criterion("risk", "mixed", "R6")],
                   "inputs": [{"name": "crop 2023/24", "state": "missing", "effect": "Not needed."}]},
                  # H2 never trips in the MVP; this plan checks how a rejection is stored.
                  {"id": "B", "type": "alternative", "crop": "lentil", "why_included": "Alternative.",
                   "criteria": [criterion("hard_constraint", "rejected", "H2")]},
                  {"id": "D", "type": "sample_test", "crop": "maize", "why_included": "Shows the rejection path.",
                   "criteria": [criterion("hard_constraint", "rejected", "H1")]},
              ]}
    save_analysis(db, request, result, climate)

    assert db.execute(
        "SELECT analysis_id, mode, product, valid_days, missing_days, site_check FROM climate_dataset"
    ).fetchall() == [("a9f3c2e7", "sample", "POWER Daily API", 12662, 0, "not_representative")]
    stored = dict(db.execute("SELECT replace(obs_date, '-', ''), value_mm FROM climate_observation").fetchall())
    assert stored == raw["properties"]["parameter"]["PRECTOTCORR"]  # every value exact
    assert db.execute("SELECT plan_code FROM candidate_plan ORDER BY display_order").fetchall() == [("A",), ("B",)]
    assert db.execute(
        "SELECT p.plan_code, e.criterion, e.label, r.code FROM plan_evidence e"
        " JOIN candidate_plan p USING (plan_id) JOIN rotation_rule r USING (rule_id) ORDER BY p.plan_code"
    ).fetchall() == [("A", "risk", "mixed", "R6"), ("B", "hard_constraint", "rejected", "H2")]
    assert db.execute("SELECT status FROM plan_input_status").fetchall() == [("missing",)]
    assert json.loads(db.execute("SELECT result_snapshot FROM analysis").fetchone()[0]) == result
    assert cache_get(db, QUERY) is None  # sample data never enters the live cache


def test_constraints_keep_unknowns_explicit(db):
    db.execute("INSERT INTO field (latitude, longitude, area_value, area_unit, irrigation)"
               " VALUES (31.5, 35.1, 20, 'dunum', 'rain-fed')")
    with pytest.raises(sqlite3.IntegrityError):  # a season with no crop must be marked unknown
        db.execute("INSERT INTO crop_season (field_id, start_date, end_date, crop_id, unknown, source)"
                   " VALUES (1, '2023-10-01', '2024-05-31', NULL, 0, 'farmer')")
    with pytest.raises(sqlite3.IntegrityError):  # evidence must belong to a real plan
        db.execute("INSERT INTO plan_evidence (plan_id, criterion, label, explanation, rule_state)"
                   " VALUES (999, 'risk', 'mixed', 'x', 'draft-unreviewed')")
