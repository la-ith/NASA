"""Write one finished analysis and the rows that belong to it (section 6.4). Rows are never updated afterwards."""
import json
import sqlite3
from datetime import datetime, timezone

from app.domain.rules import RULES_VERSION
from app.services.climate_context import ClimateContext
from app.services.climate_provider import ADAPTER_VERSION, COMMUNITY
from app.services.validation import PARAMETER, PLAUSIBLE_MAX_MM_PER_DAY, UNITS

RULE_ID = "(SELECT rule_id FROM rotation_rule WHERE code = ? AND version = ?)"


def _quality(value: float | None) -> str:
    if value is None:
        return "missing"
    return "flagged" if value > PLAUSIBLE_MAX_MM_PER_DAY else "valid"


def save_analysis(db: sqlite3.Connection, request: dict, result: dict, climate: ClimateContext) -> None:
    field, record, analysis_id = request["field"], climate.record, result["analysis_id"]
    qualities = [_quality(v) for v in record.values.values()]
    with db:  # the analysis with everything that belongs to it, or nothing
        field_id = db.execute(
            "INSERT INTO field (label, latitude, longitude, area_value, area_unit, irrigation, soil_input)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (field["label"], field["lat"], field["lon"], field["area"]["value"], field["area"]["unit"],
             field["irrigation"], field["soil"]),
        ).lastrowid
        db.executemany(  # an unknown season gets crop_id NULL and unknown = 1; no crop is invented
            "INSERT INTO crop_season (field_id, start_date, end_date, crop_id, unknown, source)"
            " VALUES (?, ?, ?, (SELECT crop_id FROM crop WHERE name = ?), ?, 'farmer')",
            [(field_id, f"{s['season'][:4]}-10-01", f"{int(s['season'][:4]) + 1}-05-31", s["crop"],
              int(s["crop"] == "unknown")) for s in request.get("history", [])],
        )
        db.execute(
            "INSERT INTO analysis (analysis_id, field_id, created_utc, goal, input_snapshot, engine_version,"
            " rules_version, status, result_snapshot) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, field_id, datetime.now(timezone.utc).isoformat(), request["goal"], json.dumps(request),
             result["versions"]["engine"], result["versions"]["rules"], result["status"], json.dumps(result)),
        )
        dataset_id = db.execute(
            "INSERT INTO climate_dataset (analysis_id, provider, product, variable, latitude, longitude, start_date,"
            " end_date, units, retrieved_utc, valid_days, missing_days, flagged_days, mode, community, api_version,"
            " sources, fill_value, time_standard, cell_elevation_m, site_check, adapter_version)"
            " VALUES (?, 'NASA POWER', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, record.api_name, PARAMETER, field["lat"], field["lon"], climate.period[0].isoformat(),
             climate.period[1].isoformat(), UNITS, climate.retrieved_utc.isoformat(), record.valid_days,
             record.missing_days, qualities.count("flagged"), climate.mode, COMMUNITY, record.api_version,
             json.dumps(record.sources), record.fill_value, record.time_standard, record.cell_elevation_m,
             climate.site.result, ADAPTER_VERSION),
        ).lastrowid
        db.executemany(
            "INSERT INTO climate_observation VALUES (?, ?, ?, ?)",
            [(dataset_id, day.isoformat(), value, quality)
             for (day, value), quality in zip(record.values.items(), qualities)],
        )
        for order, plan in enumerate(result["plans"], start=1):
            if any(c["rule"] == "H1" for c in plan["criteria"]):
                continue  # an unsupported crop has no crop row; the snapshots keep this plan
            plan_id = db.execute(
                "INSERT INTO candidate_plan (analysis_id, crop_id, role, display_order, plan_code, why_included)"
                " VALUES (?, (SELECT crop_id FROM crop WHERE name = ?), ?, ?, ?, ?)",
                (analysis_id, plan["crop"], plan["type"], order, plan["id"], plan["why_included"]),
            ).lastrowid
            db.executemany(
                "INSERT INTO plan_evidence (plan_id, rule_id, criterion, label, explanation, rule_state)"
                f" VALUES (?, {RULE_ID}, ?, ?, ?, ?)",
                [(plan_id, c["rule"], RULES_VERSION, c["criterion"], c["label"], c["explanation"], c["rule_state"])
                 for c in plan["criteria"]],
            )
            db.executemany(
                "INSERT INTO plan_input_status VALUES (?, ?, ?, ?, ?)",
                [(plan_id, i["name"], i["state"], i.get("source"), i["effect"]) for i in plan.get("inputs", [])],
            )
