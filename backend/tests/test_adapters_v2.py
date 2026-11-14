"""Source integrity for the v4 adapters (spec v4.0, section 22: source integrity group). Offline, on saved records."""
import copy
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from app.adapters import NotCovered, SourceIntegrityError, power, ssurgo

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
START, END = date(2001, 1, 1), date(2025, 12, 31)


@pytest.fixture(scope="module")
def saved():
    return json.loads((FIXTURES / "power_ks_hays_2001_2025.json").read_text(encoding="utf-8"))


def parse(raw: dict):
    return power.validate_and_normalize(raw, -99.33, 38.85, START, END, datetime(2026, 11, 14))


def test_power_record_is_complete_and_unchanged(saved):
    w = parse(saved["response"])
    assert len(w.dates) == 9131 and all(w.missing(q) == 0 for q in power.VARIABLES)
    assert w.manifest["version"] == "v2.10.3" and w.cell_elevation_m == 637.87
    i = w.dates.index(date(2001, 6, 30))
    assert w.values["shortwave_down"][i] == saved["response"]["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]["20010630"]


def series(raw, param):
    return raw["properties"]["parameter"][param]


MISMATCHES = {
    "date missing": lambda r: series(r, "WS2M").pop("20100101"),
    "unit changed": lambda r: r["parameters"]["ALLSKY_SFC_SW_DWN"].update({"units": "kW-hr/m^2/day"}),
    "parameter missing": lambda r: (r["properties"]["parameter"].pop("PS"), r["parameters"].pop("PS")),
    "other location": lambda r: r["geometry"].update({"coordinates": [-99.0, 38.85, 637.87]}),
    "humidity above 100%": lambda r: series(r, "RH2M").update({"20100101": 101.0}),
    "negative rain": lambda r: series(r, "PRECTOTCORR").update({"20100101": -1.0}),
    "minimum above maximum": lambda r: series(r, "T2M_MIN").update({"20100101": 50.0}),
    "time standard changed": lambda r: r["header"].update({"time_standard": "UTC"}),
}


@pytest.mark.parametrize("name", MISMATCHES)
def test_power_mismatch_fails(saved, name):
    broken = copy.deepcopy(saved["response"])
    MISMATCHES[name](broken)
    with pytest.raises(SourceIntegrityError):
        parse(broken)


def test_power_fill_value_becomes_missing(saved):
    edited = copy.deepcopy(saved["response"])
    series(edited, "T2MDEW")["20100101"] = -999.0
    w = parse(edited)
    assert w.missing("t_dew") == 1 and w.values["t_dew"][w.dates.index(date(2010, 1, 1))] is None


def test_ssurgo_profile_and_failures():
    saved = json.loads((FIXTURES / "ssurgo_ks_hays.json").read_text(encoding="utf-8"))
    p = ssurgo.validate_and_normalize(saved["response"], -99.33, 38.85, saved["retrieved_utc"])
    assert (p.component, p.hydrologic_group, p.curve_number, p.depth_cm) == ("Harney", "C", 85, 200.0)
    assert [h.awc for h in p.horizons] == [0.21, 0.19, 0.16, 0.2, 0.22]
    with pytest.raises(NotCovered):
        ssurgo.validate_and_normalize({}, -99.33, 38.85, "now")
    renamed = copy.deepcopy(saved["response"])
    renamed["Table"][0][10] = "awc_l"
    with pytest.raises(SourceIntegrityError):
        ssurgo.validate_and_normalize(renamed, -99.33, 38.85, "now")
