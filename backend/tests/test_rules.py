import pytest

from app.db.database import connect
from app.domain.crops import candidates, family, load_crops
from app.domain.plans import build_plans
from app.domain.rules import hard_constraint, rainfall_risk, rotation_soil, water_fit
from app.services.indicators import Indicators
from app.services.site_check import SiteCheck

REPRESENTATIVE = SiteCheck("representative", "grid cell matches the station record")


@pytest.fixture(scope="module")
def crops():
    return load_crops(connect(":memory:"))


def indicators(totals: list[float] | None = None, cv: float | None = 30.0) -> Indicators:
    totals = totals or [500.0] * 30
    return Indicators(totals, 500.0, 50.0, cv, {}, None)


# Every branch of the section 18 rotation/soil flowchart: (candidate, history oldest first) -> (label, rule, needed)
ROTATION_CASES = [
    ("cereal", ["unknown"], "insufficient_evidence", None, 1),
    ("cereal", ["cereal", "legume"], "mixed", "R3", 1),
    ("cereal", ["cereal", "fallow"], "mixed", "R3", 1),
    ("cereal", ["unknown", "cereal"], "insufficient_evidence", None, 2),
    ("cereal", ["cereal"], "insufficient_evidence", None, 2),  # the season before was never entered
    ("cereal", ["legume", "cereal"], "mixed", "R3", 2),
    ("cereal", ["fallow", "cereal"], "mixed", "R3", 2),
    ("cereal", ["cereal", "cereal"], "concern", "R1", 2),
    ("legume", ["cereal", "unknown"], "insufficient_evidence", None, 1),
    ("legume", ["unknown", "cereal"], "favorable", "R2", 1),
    ("legume", ["cereal", "legume"], "mixed", "R3", 1),
    ("legume", ["cereal", "fallow"], "mixed", "R3", 1),
]


@pytest.mark.parametrize("candidate, history, label, rule, needed", ROTATION_CASES)
def test_rotation_flowchart(candidate, history, label, rule, needed):
    r = rotation_soil(candidate, history)
    assert (r.result.label, r.result.rule, r.seasons_needed) == (label, rule, needed)


def test_crop_families(crops):
    assert [family(c, crops) for c in ("wheat", "barley", "lentil", "chickpea", "vetch", "fallow", "other", "unknown")] \
        == ["cereal", "cereal", "legume", "legume", "legume", "fallow", "unknown", "unknown"]


def test_hard_constraints(crops):
    assert hard_constraint("maize", crops, "rain-fed").rule == "H1"  # not in the crop table
    assert hard_constraint("barley", crops, "rain-fed").rule == "H1"  # history-only choice
    assert all(hard_constraint(c, crops, "rain-fed") is None for c in candidates(crops))


@pytest.mark.parametrize("totals, label", [
    ([500.0] * 24 + [300.0] * 6, "favorable"),  # 80% of seasons reach 450 mm
    ([500.0] * 23 + [300.0] * 7, "mixed"),  # 76.7%
    ([500.0] * 15 + [300.0] * 15, "mixed"),  # 50%
    ([500.0] * 14 + [300.0] * 16, "concern"),  # 46.7%
])
def test_water_fit_cut_offs(totals, label):
    r = water_fit(450.0, "rain-fed", REPRESENTATIVE, indicators(totals))
    assert (r.label, r.rule) == (label, "R4")


def test_water_fit_needs_every_condition():
    ind = indicators()
    assert water_fit(450.0, "irrigated", REPRESENTATIVE, ind).rule == "R5"
    assert water_fit(450.0, "unknown", REPRESENTATIVE, ind).rule == "R5"
    assert water_fit(None, "rain-fed", REPRESENTATIVE, ind).reason == "no confirmed water figure for this crop"
    assert water_fit(450.0, "rain-fed", SiteCheck("not_checked", "not checked"), ind).rule == "R5"


@pytest.mark.parametrize("cv, label", [(19.9, "favorable"), (20.0, "mixed"), (35.0, "mixed"), (35.1, "concern")])
def test_risk_cut_offs(cv, label):
    assert rainfall_risk(indicators(cv=cv)).label == label


def test_plan_builder_repeats_the_last_candidate_crop(crops):
    history = [("2024/25", "wheat"), ("2025/26", "wheat")]
    plans = build_plans(history, "wheat", candidates(crops), crops, ["maize"], "2026/27")
    assert [(p.code, p.crop, p.role) for p in plans] == [
        ("A", "wheat", "current_practice"), ("B", "lentil", "alternative"),
        ("C", "vetch", "alternative"), ("D", "maize", "sample_test")]
    assert plans[0].why_included == "Current practice: repeats the crop recorded for 2025/26."


def test_plan_builder_with_an_unknown_last_season(crops):
    plans = build_plans([("2025/26", "unknown")], "lentil", candidates(crops), crops, [], "2026/27")
    assert [p.crop for p in plans] == ["lentil", "wheat", "vetch"]
    assert "the crop recorded for 2025/26 is unknown" in plans[0].why_included
