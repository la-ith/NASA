"""The v4 engine on saved U.S. records (spec v4.0, section 22: crop/rotation and historical estimation groups).

The Kansas medians below are regression fixtures: they show the engine still gives the same numbers on the
same inputs. They are not validation against field measurements.
"""
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from app.adapters import power, ssurgo
from app.domain.crop_catalog import load_catalog
from app.geo.boundaries import state_at
from app.services.analysis_v2 import soil_from_ssurgo
from app.services.report_v2 import render
from app.services.run_v2 import run_analysis

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
LON, LAT = -99.33, 38.85


@pytest.fixture(scope="module")
def inputs():
    w = json.loads((FIXTURES / "power_ks_hays_2001_2025.json").read_text(encoding="utf-8"))
    s = json.loads((FIXTURES / "ssurgo_ks_hays.json").read_text(encoding="utf-8"))
    weather = power.validate_and_normalize(w["response"], LON, LAT, date(2001, 1, 1), date(2025, 12, 31),
                                           datetime.fromisoformat(w["retrieved_utc"]))
    soil = soil_from_ssurgo(ssurgo.validate_and_normalize(s["response"], LON, LAT, s["retrieved_utc"]))
    return weather, soil


def run(inputs, soil="ssurgo", **request):
    weather, ssurgo_soil = inputs
    body = {"lat": LAT, "lon": LON, "start_year": 2001, "end_year": 2025, "goal": "conserve_water",
            "history": [{"year": 2024, "crop": "maize_grain"}, {"year": 2025, "crop": "maize_grain"}], **request}
    return run_analysis(body, state_at(LON, LAT), weather, ssurgo_soil if soil == "ssurgo" else soil,
                        load_catalog(), "sample")


def median(result, crop, output):
    s = next(x for x in result["strategies"] if x["crop"] == crop)
    return s["result"]["summary"][output]["spread"]["median"]


def test_three_strategies_with_current_practice_first(inputs):
    r = run(inputs)
    assert r["status"] == "complete"
    assert [(s["crop"], s["role"]) for s in r["strategies"]] == [
        ("maize_grain", "current_practice"), ("soybean", "alternative"), ("sorghum_grain", "alternative")]
    for s in r["strategies"]:
        assert s["result"]["seasons_simulated"] == 25 and abs(s["result"]["max_closure_residual_mm"]) < 1e-6
        years = [season["year"] for season in s["result"]["seasons"]]
        assert years == list(range(2001, 2026))  # every candidate faces the same past seasons


def test_kansas_regression_medians(inputs):
    r = run(inputs)
    assert median(r, "maize_grain", "rainfed_deficit") == pytest.approx(371.7, abs=0.05)
    assert median(r, "sorghum_grain", "rainfed_deficit") == pytest.approx(233.3, abs=0.05)
    assert median(r, "soybean", "irrigated_net_irrigation") == pytest.approx(540.4, abs=0.05)
    taw = next(s for s in r["strategies"] if s["crop"] == "maize_grain")["result"]["taw_mm"]
    assert taw == pytest.approx(10 * (0.21 * 11 + 0.19 * 8 + 0.16 * 37 + 0.20 * 26 + 0.22 * 53), abs=0.05)


def test_physical_consistency_in_every_season(inputs):
    for s in run(inputs)["strategies"]:
        for season in s["result"]["seasons"]:
            assert 0 <= season["rainfed_eta"] <= season["etc_standard"] + 1e-9
            assert season["rainfed_deficit"] >= -1e-9 and season["irrigated_net_irrigation"] >= 0
            assert season["runoff"] <= season["precipitation"]


def test_goal_never_changes_numbers(inputs):
    a, b = run(inputs, goal="conserve_water"), run(inputs, goal="improve_soil_rotation")
    assert [s["result"] for s in a["strategies"]] == [s["result"] for s in b["strategies"]]
    assert a["output_order"] != b["output_order"]


def test_no_soil_gives_partial_climate_only_result(inputs):
    r = run(inputs, soil=None)
    assert r["status"] == "partial"
    s = r["strategies"][0]["result"]
    assert s["summary"]["etc_standard"]["spread"] is not None
    assert s["summary"]["rainfed_deficit"]["spread"] is None and s["taw_mm"] is None


def test_freezing_season_is_excluded_not_simulated(inputs):
    r = run(inputs, planting_dates={"maize_grain": "01-05"})
    maize = r["strategies"][0]["result"]
    assert maize["seasons_simulated"] == 0 and maize["seasons_excluded"]["frozen_conditions"]["count"] == 25
    assert r["status"] == "partial"


def test_unsupported_crop_is_rejected_not_replaced(inputs):
    r = run(inputs, candidates=["maize_grain", "rice", "soybean"])
    assert [s["crop"] for s in r["strategies"]] == ["maize_grain", "soybean"]
    assert r["rejected"][0]["crop"] == "rice"
    assert any("fewer than the three" in x for x in r["limitations"])


def test_input_states_and_report(inputs):
    r = run(inputs)
    states = {i["name"]: i["state"] for i in r["inputs"]}
    assert states["soil water capacity"] == "estimated" and states["irrigation"] == "missing"
    assert states["Maize (grain, field corn) planting date"] == "assumed"
    text = render(r, "test")
    assert "FAO56-Eq6" in text and "not a forecast" in text and "Harney" in text
