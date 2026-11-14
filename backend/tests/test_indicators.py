import copy
import json
from datetime import date
from pathlib import Path

import pytest

from app.domain.rules import rainfall_risk, water_fit
from app.services.indicators import compute_indicators, seasonal_totals, seasons_meeting
from app.services.site_check import StationReference, run_site_check
from app.services.validation import DataIntegrityError, parse_power_response

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo"
LAT, LON, START, END = 31.5, 35.1, date(1991, 10, 1), date(2026, 5, 31)


def series(raw: dict) -> dict:
    return raw["properties"]["parameter"]["PRECTOTCORR"]


@pytest.fixture(scope="module")
def raw():
    return json.loads((DEMO / "power_pilot_19911001_20260531.json").read_text(encoding="utf-8"))["response"]


@pytest.fixture(scope="module")
def record(raw):
    return parse_power_response(raw, LAT, LON, START, END)


@pytest.fixture(scope="module")
def seasons(record):
    return seasonal_totals(record, 1991, 2025)


def test_values_kept_exactly(raw, record):
    assert (record.valid_days, record.missing_days) == (12662, 0)
    assert (record.api_name, record.api_version, record.sources, record.fill_value) == (
        "POWER Daily API", "v2.10.3", ["MERRA2"], -999.0)
    for key, value in series(raw).items():
        assert record.values[date(int(key[:4]), int(key[4:6]), int(key[6:]))] == value  # exact, no tolerance


def test_fill_value_becomes_explicit_missing(raw):
    edited = copy.deepcopy(raw)
    series(edited)["20000101"] = raw["header"]["fill_value"]
    record = parse_power_response(edited, LAT, LON, START, END)
    assert record.values[date(2000, 1, 1)] is None
    assert record.missing_days == 1


MISMATCHES = {
    "date missing": lambda r: series(r).pop("20000101"),
    "extra date": lambda r: series(r).update({"20260601": 0.0}),
    "header end date": lambda r: r["header"].update({"end": "20260530"}),
    "parameter renamed": lambda r: r["properties"]["parameter"].update(
        {"PRECTOT": r["properties"]["parameter"].pop("PRECTOTCORR")}),
    "units changed": lambda r: r["parameters"]["PRECTOTCORR"].update({"units": "mm/hour"}),
    "time standard changed": lambda r: r["header"].update({"time_standard": "UTC"}),
    "other location": lambda r: r["geometry"].update({"coordinates": [35.0, 31.5, 342.96]}),
    "negative value": lambda r: series(r).update({"20000101": -0.1}),
    "text value": lambda r: series(r).update({"20000101": "0.5"}),
    "metadata removed": lambda r: r["header"].pop("sources"),
}


@pytest.mark.parametrize("mismatch", MISMATCHES)
def test_any_mismatch_fails(raw, mismatch):
    broken = copy.deepcopy(raw)
    MISMATCHES[mismatch](broken)
    with pytest.raises(DataIntegrityError):
        parse_power_response(broken, LAT, LON, START, END)


@pytest.fixture(scope="module")
def site(seasons):
    station = StationReference(**json.loads((DEMO / "site_check.json").read_text(encoding="utf-8")))
    return run_site_check(seasons, station)


def test_pilot_indicators(seasons):
    ind = compute_indicators(seasons, candidate_year=2026)
    assert ind.baseline_mean_mm == pytest.approx(225.2, abs=0.05)
    assert ind.baseline_sd_mm == pytest.approx(77.8, abs=0.05)
    assert ind.baseline_cv_pct == pytest.approx(34.5, abs=0.05)
    assert seasons_meeting(ind, 450) == (1, 30)
    expected = {"2021/22": 80.8, "2022/23": 46.9, "2023/24": 55.2, "2024/25": -36.6, "2025/26": 45.6}
    assert ind.anomalies_pct == pytest.approx(expected, abs=0.05)
    assert ind.recent_shift_pct == pytest.approx(38.4, abs=0.05)


def test_pilot_site_check(site):
    assert site.result == "not_representative"
    assert site.cell_mean_mm == pytest.approx(229.4, abs=0.05)
    assert site.ratio == pytest.approx(0.49, abs=0.005)


def test_pilot_climate_labels(seasons, site):
    ind = compute_indicators(seasons, candidate_year=2026)
    assert water_fit(450.0, "rain-fed", site, ind).label == "insufficient_evidence"
    assert water_fit(None, "rain-fed", site, ind).reason.endswith("no confirmed water figure for this crop")
    assert rainfall_risk(ind).label == "mixed"
