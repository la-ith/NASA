"""Crop demand and the daily soil water balance: FAO-56 chapter 8 examples, then physical checks."""
import pytest

from app.science.crop import (Horizon, Stages, adjust_kc_for_climate, adjusted_depletion_fraction, kc_curve,
                              layered_total_available_water, total_available_water)
from app.science.water_balance import scs_runoff, simulate, water_stress_coefficient


def test_example_34_taw_and_raw_for_maize():
    """FAO-56 Example 34: maize, Zr = 1.2 m, p = 0.55, on three soils (θFC - θWP = 0.09, 0.17, 0.12)."""
    for dtheta, taw_expected, raw_expected in [(0.09, 108, 59), (0.17, 204, 112), (0.12, 144, 79)]:
        taw = total_available_water(dtheta, 0.0, 1.2)
        assert taw == pytest.approx(taw_expected, abs=0.5)
        assert 0.55 * taw == pytest.approx(raw_expected, abs=0.5)


def test_example_35_ten_days_of_water_stress():
    """FAO-56 Example 35: tomato, TAW = 160 mm, p = 0.40, Dr0 = 55 mm, ET0 = 5, Kc = 1.2, no rain."""
    expected_end = [61.0, 67.0, 72.8, 78.3, 83.4, 88.2, 92.6, 96.9, 100.8, 104.5]
    expected_ks = [1.00, 1.00, 0.97, 0.91, 0.85, 0.80, 0.75, 0.70, 0.66, 0.62]
    r = simulate([5.0] * 10, [1.2] * 10, [0.0] * 10, taw=160.0, p_table=0.40, curve_number=78,
                 initial_depletion=55.0, adjust_p=False)
    assert r.daily_depletion == pytest.approx(expected_end, abs=0.1)  # FAO rounds each day to 0.1 mm
    assert r.daily_ks == pytest.approx(expected_ks, abs=0.005)
    assert r.drainage == 0 and r.runoff == 0


def test_kc_curve_shape():
    curve = kc_curve(Stages(2, 4, 3, 2), 0.3, 1.2, 0.35)
    assert curve == pytest.approx([0.3, 0.3, 0.525, 0.75, 0.975, 1.2, 1.2, 1.2, 1.2, 0.775, 0.35])


def test_kc_climate_adjustment_and_limits():
    standard = adjust_kc_for_climate(1.20, 2.0, 45.0, 2.0)  # standard climate: no change
    assert standard.kc == pytest.approx(1.20) and not standard.limited
    windy_dry = adjust_kc_for_climate(1.20, 4.0, 30.0, 2.0)
    assert windy_dry.kc == pytest.approx(1.20 + (0.08 + 0.06) * (2 / 3) ** 0.3)
    assert adjust_kc_for_climate(1.20, 9.0, 10.0, 2.0).limited


def test_depletion_fraction_adjustment_limits():
    assert adjusted_depletion_fraction(0.55, 5.0) == pytest.approx(0.55)
    assert adjusted_depletion_fraction(0.55, 10.0) == pytest.approx(0.35)
    assert adjusted_depletion_fraction(0.55, -20.0) == pytest.approx(0.8)


def test_layered_taw_uses_only_the_root_zone():
    horizons = [Horizon(0, 20, 0.20), Horizon(20, 60, 0.15), Horizon(60, 100, 0.10)]
    assert layered_total_available_water(horizons, 0.5) == pytest.approx(10 * (0.20 * 20 + 0.15 * 30))
    assert layered_total_available_water(horizons, 2.0) == pytest.approx(10 * (0.20 * 20 + 0.15 * 40 + 0.10 * 40))


def test_scs_runoff():
    retention = 25400 / 78 - 254
    assert scs_runoff(0.2 * retention, 78) == 0.0  # all rain below Ia infiltrates
    assert scs_runoff(100.0, 78) == pytest.approx((100 - 0.2 * retention) ** 2 / (100 + 0.8 * retention))
    assert scs_runoff(100.0, 89) > scs_runoff(100.0, 67)  # soil group D sheds more than A


def test_stress_coefficient_boundaries():
    assert water_stress_coefficient(50.0, 100.0, 0.5) == 1.0
    assert water_stress_coefficient(75.0, 100.0, 0.5) == pytest.approx(0.5)
    assert water_stress_coefficient(100.0, 100.0, 0.5) == 0.0


@pytest.mark.parametrize("irrigate", [False, True])
def test_mass_balance_closes_on_mixed_weather(irrigate):
    rain = [0, 0, 45, 0, 0, 0, 80, 2, 0, 0, 0, 0, 0, 12, 0] * 6
    r = simulate([6.0] * 90, [1.1] * 90, [float(x) for x in rain], taw=150.0, p_table=0.55, curve_number=85,
                 initial_depletion=75.0, irrigate=irrigate)
    assert abs(r.closure_residual) < 1e-9
    assert all(0.0 <= d <= 150.0 for d in r.daily_depletion)
    assert r.runoff > 0 and r.drainage >= 0


def test_wet_soil_drains_and_stays_at_field_capacity():
    r = simulate([4.0], [1.0], [40.0], taw=100.0, p_table=0.5, curve_number=67, initial_depletion=10.0)
    infiltration = 40.0 - scs_runoff(40.0, 67)
    assert r.final_depletion == pytest.approx(0.0)
    assert r.drainage == pytest.approx(infiltration - 4.0 - 10.0)


def test_rain_fed_keeps_a_deficit_and_irrigation_removes_it():
    args = dict(et0=[7.0] * 60, kc=[1.15] * 60, precip=[0.0] * 60, taw=120.0, p_table=0.5, curve_number=78,
                initial_depletion=60.0)
    dry = simulate(**args)
    wet = simulate(**args, irrigate=True)
    assert dry.deficit > 0 and dry.stress_days > 0 and dry.irrigation_net == 0
    assert wet.stress_days == 0 and wet.deficit == pytest.approx(0.0, abs=1e-9)
    assert wet.irrigation_net > 0 and abs(wet.closure_residual) < 1e-9
