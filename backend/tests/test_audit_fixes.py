"""Regression tests for the defects confirmed in the 2026-11-14 scientific audit (docs/validation/)."""
import asyncio
from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.adapters import power, ssurgo
from app.adapters.power import DailyWeather
from app.domain.crop_catalog import load_catalog
from app.science.crop import adjust_kc_for_climate, min_relative_humidity
from app.science.water_balance import simulate
from app.services.analysis_v2 import simulate_season, stage_climate_means


def synthetic_weather(days: list[date], mid: range, late: range) -> DailyWeather:
    """Calm and humid except a windy, dry mid-season and a windy, very dry late season."""
    n = len(days)
    wind = [2.0] * n
    dew = [15.0] * n
    for i in mid:
        wind[i], dew[i] = 3.0, 8.0
    for i in late:
        wind[i], dew[i] = 5.0, 2.0
    values = {"t_max": [30.0] * n, "t_min": [16.0] * n, "t_mean": [23.0] * n, "t_dew": dew, "wind_2m": wind,
              "shortwave_down": [22.0] * n, "surface_pressure": [97.0] * n, "precipitation": [0.0] * n,
              "rh_mean": [50.0] * n}
    return DailyWeather(days, values, 40.0, -100.0, 500.0, {})


def test_kc_end_uses_late_season_weather():
    """FAO-56 Eq. 65: u2 and RHmin are means 'during the late season growth stage'."""
    crop = load_catalog().crops["sorghum_grain"]  # Kc end 0.55 >= 0.45, so Eq. 65 applies
    s = crop.stages
    days = [date(2020, 6, 1) + timedelta(days=k) for k in range(s.total)]
    mid = range(s.initial + s.development, s.initial + s.development + s.mid)
    late = range(s.total - s.late, s.total)
    weather = synthetic_weather(days, mid, late)
    status, outcome = simulate_season(crop, weather, {d: i for i, d in enumerate(days)}, days[0], 200.0, 78, 0.5)
    assert status == "ok"
    expected_end = adjust_kc_for_climate(crop.kc_end, 5.0, min_relative_humidity(2.0, 30.0), crop.height_m).kc
    expected_mid = adjust_kc_for_climate(crop.kc_mid, 3.0, min_relative_humidity(8.0, 30.0), crop.height_m).kc
    assert outcome.kc_end_adjusted == pytest.approx(expected_end)
    assert outcome.kc_mid_adjusted == pytest.approx(expected_mid)
    assert stage_climate_means(weather, list(late)) == pytest.approx((5.0, min_relative_humidity(2.0, 30.0)))


def test_kc_end_below_threshold_is_not_adjusted():
    crop = load_catalog().crops["maize_grain"]  # Kc end 0.35 < 0.45
    days = [date(2020, 5, 1) + timedelta(days=k) for k in range(crop.stages.total)]
    weather = synthetic_weather(days, range(70, 120), range(120, 150))
    _, outcome = simulate_season(crop, weather, {d: i for i, d in enumerate(days)}, days[0], 200.0, 78, 0.5)
    assert outcome.kc_end_adjusted == crop.kc_end


def restriction_table(rows):
    return {"Table": [ssurgo.RESTRICTION_COLUMNS, *rows]}


def test_restrictive_layer_caps_soil_depth():
    profile = ssurgo.SoilProfile("1", "unit", "Wakeen", 80.0, "B", "B",
                                 [ssurgo.Horizon(0, 50, 0.2), ssurgo.Horizon(50, 104, 0.15)], [], 104.0, {}, "k1")
    raw = restriction_table([["k1", "Wakeen", "80", "Paralithic bedrock", "79"], ["k1", "Wakeen", "80", "Duripan", "95"],
                             ["k2", "Other", "20", "Lithic bedrock", "30"]])
    capped = ssurgo.apply_restrictions(profile, raw, "2026-11-14T00:00:00+00:00")
    assert capped.depth_cm == 79.0 and capped.restriction == {"kind": "Paralithic bedrock", "top_cm": 79.0}
    unrestricted = ssurgo.apply_restrictions(profile, restriction_table([["k1", "Wakeen", "80", None, None]]), "t")
    assert unrestricted.depth_cm == 104.0 and unrestricted.restriction is None
    with pytest.raises(ssurgo.SourceIntegrityError):
        ssurgo.apply_restrictions(profile, restriction_table([["k9", "Elsewhere", "100", None, None]]), "t")


class RecordingClient:
    def __init__(self, response):
        self.response, self.kwargs = response, None

    async def get(self, url, **kwargs):
        self.kwargs = kwargs
        return self.response

    async def post(self, url, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_requests_pass_an_explicit_timeout():
    """httpx's default 5 s read timeout used to override the documented per-attempt timeouts."""
    import httpx
    ok = httpx.Response(200, json={"Table": [["x"]]}, request=httpx.Request("POST", "https://example.test"))
    client = RecordingClient(ok)
    asyncio.run(ssurgo.fetch(client, -99.0, 39.0))
    assert client.kwargs["timeout"] == ssurgo.ATTEMPT_TIMEOUT_S
    asyncio.run(power.fetch(client, -99.0, 39.0, date(2020, 1, 1), date(2020, 1, 2)))
    assert client.kwargs["timeout"] == power.ATTEMPT_TIMEOUT_S


def test_irrigation_trigger_and_refill_options():
    args = dict(et0=[6.0] * 40, kc=[1.0] * 40, precip=[0.0] * 40, taw=100.0, p_table=0.5, curve_number=78,
                initial_depletion=0.0, irrigate=True, adjust_p=False)
    full = simulate(**args)
    partial = simulate(**args, trigger_fraction=1.0, refill_fraction=0.5)
    assert max(full.daily_depletion) <= 50.0 + 6.0 and max(partial.daily_depletion) <= 50.0 + 6.0
    assert partial.irrigation_events > full.irrigation_events  # smaller, more frequent refills
    assert abs(partial.closure_residual) < 1e-9
    with pytest.raises(ValueError):
        simulate(**args, trigger_fraction=0.5, refill_fraction=0.5)


def test_new_fields_have_safe_defaults():
    assert replace(load_catalog().crops["soybean"]).kc_end == 0.50
