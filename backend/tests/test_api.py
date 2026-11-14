"""The whole API on the saved sample record: offline, with an in-memory database."""
import copy
import os

os.environ["FIELD_SHIFT_DB"] = ":memory:"
os.environ["FIELD_SHIFT_WARMUP"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.reference import DEMO_CASE  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def demo(client):
    response = client.post("/api/v1/analyses", json=DEMO_CASE)
    assert response.status_code == 200, response.text
    return response.json()


def labels(plan: dict) -> dict:
    return {c["criterion"]: (c["label"], c["rule"]) for c in plan["criteria"]}


def test_demo_matches_the_section_18_expected_results(demo):
    plans = {p["id"]: p for p in demo["plans"]}
    assert labels(plans["A"]) == {"rotation_soil": ("concern", "R1"), "water_fit": ("insufficient_evidence", "R5"),
                                  "risk": ("mixed", "R6")}
    for code in ("B", "C"):
        assert labels(plans[code]) == {"rotation_soil": ("favorable", "R2"),
                                       "water_fit": ("insufficient_evidence", "R5"), "risk": ("mixed", "R6")}
    assert (plans["D"]["status"], plans["D"]["criteria"][0]["rule"]) == ("rejected", "H1")
    assert [plans[c]["display"] for c in "ABC"] == ["wheat → wheat", "wheat → lentil", "wheat → vetch"]
    assert demo["status"] == "partial"
    assert demo["banners"] == {"sample_data": True, "illustrative_rules": True}
    assert demo["summary"] == ("Rotation/soil differs: wheat (current practice) is a concern; lentil is favorable; "
                               "vetch is favorable. Water fit could not be assessed for any plan.")


def test_tc_water_001_site_check_blocks_water_fit(demo):
    """TC-WATER-001 (outputs/field-shift-test-cases): section 16.1, rule R5."""
    site = demo["data"]["site_check"]
    assert (site["result"], site["cell_mm"], site["station_mm"], site["ratio"]) == (
        "not_representative", 229.4, 470.8, 0.49)
    wheat_water = next(c for c in demo["plans"][0]["criteria"] if c["criterion"] == "water_fit")
    assert wheat_water["label"] == "insufficient_evidence"
    assert "49% of the rainfall recorded at Hebron station" in wheat_water["reason"]


def test_unknown_season_that_is_not_needed(demo):
    inputs = {i["name"]: i for i in demo["plans"][0]["inputs"]}
    assert inputs["crop 2023/24"]["state"] == "missing"
    assert inputs["crop 2023/24"]["effect"] == "Not needed for this plan's rotation check."
    assert inputs["seasonal rainfall"]["state"] == "estimated"


def test_goal_orders_criteria_but_never_changes_labels(client, demo):
    water_first = client.post("/api/v1/analyses", json={**DEMO_CASE, "goal": "conserve_water"}).json()
    assert [c["criterion"] for c in water_first["plans"][0]["criteria"]] == ["water_fit", "risk", "rotation_soil"]
    assert [labels(p) for p in water_first["plans"]] == [labels(p) for p in demo["plans"]]


def test_saved_result_and_history(client, demo):
    assert client.get(f"/api/v1/analyses/{demo['analysis_id']}").json() == demo
    assert client.get("/api/v1/analyses/nope").status_code == 404
    rows = client.app.state.db.execute(
        "SELECT s.start_date, s.crop_id IS NULL, s.unknown FROM crop_season s JOIN analysis a USING (field_id)"
        " WHERE a.analysis_id = ? ORDER BY s.start_date", (demo["analysis_id"],)).fetchall()
    assert rows == [("2023-10-01", 1, 1), ("2024-10-01", 0, 0), ("2025-10-01", 0, 0)]


@pytest.mark.parametrize("change, field", [
    ({"history": [{"season": "2023/24", "crop": "wheat"}]}, "body"),  # must end with 2025/26
    ({"history": [{"season": "2024/25", "crop": "wheat"}, {"season": "2025/26", "crop": "unknown"}]},
     "current_practice_crop"),  # unknown last season needs a chosen current practice
    ({"mode": "live"}, "body"),  # extra_candidates only in sample mode
    ({"history": [{"season": "2025/26", "crop": "rice"}]}, "history"),
    ({"extra_candidates": ["lentil"]}, "extra_candidates"),
])
def test_invalid_input(client, change, field):
    response = client.post("/api/v1/analyses", json={**copy.deepcopy(DEMO_CASE), **change})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert response.json()["error"]["fields"][0]["loc"][-1] == field


def test_unknown_last_season_with_chosen_current_practice(client):
    body = {**DEMO_CASE, "history": [{"season": "2025/26", "crop": "unknown"}], "current_practice_crop": "lentil",
            "extra_candidates": []}
    plans = client.post("/api/v1/analyses", json=body).json()["plans"]
    assert [(p["crop"], p["display"]) for p in plans] == [
        ("lentil", "unknown → lentil"), ("wheat", "unknown → wheat"), ("vetch", "unknown → vetch")]
    assert all(labels(p)["rotation_soil"] == ("insufficient_evidence", None) for p in plans)


def test_reference_routes(client):
    crops = client.get("/api/v1/crops").json()
    assert [c["name"] for c in crops["candidates"]] == ["wheat", "lentil", "vetch"]
    assert crops["history_choices"][-1]["name"] == "unknown"
    assert [r["code"] for r in client.get("/api/v1/rules").json()] == [
        "H1", "H2", "H3", "R1", "R2", "R3", "R4", "R5", "R6"]
    assert client.get("/api/v1/demo").json()["request"] == DEMO_CASE
    assert client.get("/api/v1/health").json() == {"status": "ok"}
