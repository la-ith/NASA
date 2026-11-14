"""FAO-56 worked examples (Allen et al., 1998, chapters 3 and 4), read from fao.org on 14 Nov 2026.

Expected values are FAO-56's printed results, not outputs of this code. FAO-56 rounds intermediate values
when it prints them, so each tolerance is half a unit of the last printed digit, widened only where FAO
carried an already-rounded intermediate into the next step (noted at the assertion).
"""
import math
from datetime import date

import pytest

from app.science import fao56


def test_example_2_pressure_and_psychrometric_constant():
    p = fao56.atmospheric_pressure(1800)
    assert p == pytest.approx(81.8, abs=0.05)
    assert fao56.psychrometric_constant(p) == pytest.approx(0.054, abs=0.0005)


def test_example_3_saturation_vapour_pressure():
    assert fao56.saturation_vapour_pressure(24.5) == pytest.approx(3.075, abs=0.0005)
    assert fao56.saturation_vapour_pressure(15.0) == pytest.approx(1.705, abs=0.0005)
    assert fao56.mean_saturation_vapour_pressure(24.5, 15.0) == pytest.approx(2.39, abs=0.005)
    assert fao56.saturation_vapour_pressure(19.75) == pytest.approx(2.30, abs=0.005)


def test_examples_5_and_6_actual_vapour_pressure_and_deficit():
    ea = fao56.actual_vapour_pressure_from_rh_extremes(25.0, 18.0, 82.0, 54.0)
    assert ea == pytest.approx(1.70, abs=0.005)
    assert fao56.actual_vapour_pressure_from_rh_mean(25.0, 18.0, 68.0) == pytest.approx(1.78, abs=0.005)
    assert fao56.mean_saturation_vapour_pressure(25.0, 18.0) - ea == pytest.approx(0.91, abs=0.005)


def test_example_8_extraterrestrial_radiation():
    j = date(2026, 9, 3).timetuple().tm_yday
    assert j == 246
    assert fao56.inverse_relative_distance(j) == pytest.approx(0.985, abs=0.0005)
    assert fao56.solar_declination(j) == pytest.approx(0.120, abs=0.0005)
    assert fao56.sunset_hour_angle(math.radians(-20), fao56.solar_declination(j)) == pytest.approx(1.527, abs=0.0005)
    assert fao56.extraterrestrial_radiation(-20, j) == pytest.approx(32.2, abs=0.05)


def test_examples_10_to_12_radiation_chain():
    j = 135  # 15 May
    lat = -22.90  # Rio de Janeiro, 22°54'S
    ra = fao56.extraterrestrial_radiation(lat, j)
    assert ra == pytest.approx(25.1, abs=0.05)
    n_max = fao56.daylight_hours(lat, j)
    assert n_max == pytest.approx(10.9, abs=0.05)
    rs = fao56.solar_radiation_from_sunshine(220 / 31, n_max, ra)
    assert rs == pytest.approx(14.5, abs=0.05)
    # Example 11 uses Eq. 36 (Rso = 0.75 Ra, sea level), which is Eq. 37 with z = 0.
    rso = fao56.clear_sky_radiation(ra, 0)
    assert rso == pytest.approx(18.8, abs=0.05)
    rnl = fao56.net_longwave_radiation(25.1, 19.1, 2.1, rs, rso)
    assert rnl == pytest.approx(3.5, abs=0.05)
    assert fao56.net_shortwave_radiation(rs) - rnl == pytest.approx(7.6, abs=0.1)  # FAO subtracts rounded parts


def test_example_14_wind_speed_height():
    assert fao56.wind_speed_at_2m(3.2, 10) == pytest.approx(2.4, abs=0.05)


def test_example_18_daily_et0_uccle():
    """Uccle (Brussels), 6 July, 50°48'N, 100 m. FAO-56 result: ET0 = 3.88 ≈ 3.9 mm/day."""
    lat, z, day = 50 + 48 / 60, 100.0, date(2026, 7, 6)  # J = 187 in a non-leap year, as in FAO-56
    u2 = fao56.wind_speed_at_2m(10 / 3.6, 10)
    assert u2 == pytest.approx(2.078, abs=0.0005)
    ea = fao56.actual_vapour_pressure_from_rh_extremes(21.5, 12.3, 84, 63)
    assert ea == pytest.approx(1.409, abs=0.0005)
    ra = fao56.extraterrestrial_radiation(lat, 187)
    assert ra == pytest.approx(41.09, abs=0.005)
    n_max = fao56.daylight_hours(lat, 187)
    assert n_max == pytest.approx(16.1, abs=0.05)
    rs = fao56.solar_radiation_from_sunshine(9.25, n_max, ra)
    assert rs == pytest.approx(22.07, abs=0.05)  # FAO used n/N rounded to 0.57
    result = fao56.daily_et0(day, lat, 21.5, 12.3, ea, rs, u2, fao56.atmospheric_pressure(z), z)
    assert result.gamma == pytest.approx(0.0666, abs=0.00005)
    assert result.delta == pytest.approx(0.122, abs=0.0005)
    assert result.es_kpa == pytest.approx(1.997, abs=0.0005)
    assert result.rso == pytest.approx(30.90, abs=0.05)
    assert result.rns == pytest.approx(17.00, abs=0.05)
    assert result.rnl == pytest.approx(3.71, abs=0.05)
    assert result.rn == pytest.approx(13.28, abs=0.05)
    assert result.et0_mm == pytest.approx(3.88, abs=0.03)  # FAO sums two terms printed to 0.01


def test_polar_day_and_night_stay_defined():
    """Northern Alaska (71.3°N): the sun never sets in late June and never rises in late December."""
    assert fao56.sunset_hour_angle(math.radians(71.3), fao56.solar_declination(172)) == pytest.approx(math.pi)
    assert fao56.extraterrestrial_radiation(71.3, 355) == pytest.approx(0.0, abs=1e-9)
    assert math.isnan(fao56.net_longwave_radiation(-20, -30, 0.1, 0.0, 0.0))
