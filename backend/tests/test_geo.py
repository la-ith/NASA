"""The 50-state boundary check (spec v4.0, sections 3 and 22: geography group)."""
import pytest

from app.geo.boundaries import state_at, state_count


def test_fifty_states_loaded():
    assert state_count() == 50


@pytest.mark.parametrize("lon, lat, code", [
    (-99.33, 38.85, "KS"),  # Hays demo site
    (-93.62, 42.03, "IA"),  # Ames demo site
    (-157.86, 21.31, "HI"),  # Honolulu
    (-149.90, 61.22, "AK"),  # Anchorage
    (173.20, 52.85, "AK"),  # Attu Island, west of the antimeridian
    (-176.65, 51.88, "AK"),  # Adak, east of the antimeridian
    (-119.79, 36.74, "CA"),  # Fresno, Central Valley
    (-68.77, 44.80, "ME"),  # Bangor
])
def test_points_inside_states(lon, lat, code):
    assert state_at(lon, lat).code == code


@pytest.mark.parametrize("lon, lat", [
    (-90.0, 25.0),  # Gulf of Mexico
    (-79.38, 43.65),  # Toronto, Canada
    (-77.03, 38.90),  # Washington, DC: not a state
    (-66.11, 18.47),  # San Juan, Puerto Rico: a territory, outside this release
    (-150.0, 30.0),  # open Pacific
    (35.10, 31.50),  # Hebron: the old pilot is outside the U.S. scope
    (200.0, 40.0),  # invalid longitude
])
def test_points_outside_scope(lon, lat):
    assert state_at(lon, lat) is None
