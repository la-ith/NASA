"""API v2 on the saved demo records: offline, in-memory database (spec v4.0, section 22: storage/API group)."""
import os
import time

os.environ["FIELD_SHIFT_DB"] = ":memory:"
os.environ["FIELD_SHIFT_WARMUP"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

KANSAS = {"mode": "sample", "lat": 38.85, "lon": -99.33, "goal": "conserve_water", "irrigation": "rain-fed",
          "history": [{"year": 2024, "crop": "maize_grain"}, {"year": 2025, "crop": "maize_grain"}]}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def wait_for(client, job_url: str) -> dict:
    for _ in range(100):
        job = client.get(job_url).json()
        if job["state"] in ("succeeded", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_job_flow_and_immutable_result(client):
    started = client.post("/api/v2/analyses", json=KANSAS)
    assert started.status_code == 202
    job = wait_for(client, started.json()["status_url"])
    assert job["state"] == "succeeded", job
    result = client.get(job["analysis_url"]).json()
    assert result["status"] == "complete" and result["location"]["state"] == "KS"
    assert len(result["strategies"]) == 3 and result["mode"] == "sample"
    assert result["location"]["public_location"] == {"lat": 38.9, "lon": -99.3}
    assert client.get(job["analysis_url"]).json() == result
    report = client.get(f"{job['analysis_url']}/report")
    assert report.status_code == 200 and report.text.startswith("# Field Shift comparison")


def test_outside_scope_is_rejected(client):
    r = client.post("/api/v2/analyses", json={**KANSAS, "lat": 31.5, "lon": 35.1})
    assert r.status_code == 422 and r.json()["error"]["code"] == "outside_scope"


def test_sample_only_for_demo_sites(client):
    job = wait_for(client, client.post("/api/v2/analyses", json={**KANSAS, "lat": 40.0, "lon": -100.0})
                   .json()["status_url"])
    assert job["state"] == "failed" and job["error"]["code"] == "sample_not_available"


def test_user_soil_override(client):
    body = {**KANSAS, "soil": {"awc_mm_per_m": 150, "depth_cm": 120, "hydrologic_group": "B"}}
    job = wait_for(client, client.post("/api/v2/analyses", json=body).json()["status_url"])
    result = client.get(job["analysis_url"]).json()
    assert result["soil"]["source"] == "user" and result["soil"]["curve_number"] == 78
    assert result["strategies"][0]["result"]["taw_mm"] == pytest.approx(150 * 1.2)  # maize roots capped at 1.2 m


@pytest.mark.parametrize("change", [{"end_year": 2030}, {"start_year": 1970}, {"goal": "maximize_profit"},
                                    {"planting_dates": {"maize_grain": "May 1"}}])
def test_invalid_requests(client, change):
    r = client.post("/api/v2/analyses", json={**KANSAS, **change})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_input"


def test_coverage_and_reference_routes(client):
    cov = client.post("/api/v2/coverage", json={"lat": 38.85, "lon": -99.33, "mode": "sample"}).json()
    assert cov["in_scope"] and cov["products"]["ssurgo"]["status"] == "supported"
    assert cov["products"]["usda_cdl"]["status"] == "not_integrated"
    assert not client.post("/api/v2/coverage", json={"lat": 18.47, "lon": -66.11}).json()["in_scope"]
    crops = client.get("/api/v2/crops").json()
    assert [c["id"] for c in crops["crops"]] == ["maize_grain", "soybean", "sorghum_grain"]
    assert "FAO56-Eq6" in client.get("/api/v2/equations").json()
    assert client.get("/api/v2/health").json()["status"] == "ok"


def test_v1_regression_route_still_works(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
