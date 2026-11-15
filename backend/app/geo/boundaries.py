"""Point-in-polygon test against the versioned 50-state boundary (spec v4.0, section 3).

Boundary: U.S. Census Bureau 2023 cartographic boundary, 1:20,000,000 (data/catalogs/us_states_50_cb_2023_20m.geojson,
built by tools/census_states_to_geojson.py). At this scale coastlines are generalized by roughly a kilometre, so the
test answers "is this point in one of the 50 states", not "is this point a farm field". Alaska's islands west of
180° are stored as separate parts with positive longitudes, so no polygon crosses the antimeridian.
"""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BOUNDARY_FILE = Path(__file__).resolve().parents[3] / "data" / "catalogs" / "us_states_50_cb_2023_20m.geojson"
BOUNDARY_VERSION = "census-cb-2023-us-state-20m"


@dataclass(frozen=True)
class State:
    code: str  # USPS code, for example "KS"
    name: str
    fips: str


def _in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Even-odd ray casting: count edges crossed by a ray from the point towards +longitude."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


@lru_cache(maxsize=1)
def _states() -> list[tuple[State, list[tuple[tuple[float, float, float, float], list[list[list[float]]]]]]]:
    collection = json.loads(BOUNDARY_FILE.read_text(encoding="utf-8"))
    states = []
    for feature in collection["features"]:
        props = feature["properties"]
        polygons = []
        for polygon in feature["geometry"]["coordinates"]:
            xs = [p[0] for p in polygon[0]]
            ys = [p[1] for p in polygon[0]]
            polygons.append(((min(xs), min(ys), max(xs), max(ys)), polygon))
        states.append((State(props["stusps"], props["name"], props["statefp"]), polygons))
    return states


def state_at(lon: float, lat: float) -> State | None:
    """The state containing the point, or None outside the 50 states (territories, DC, ocean, other countries)."""
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        return None
    for state, polygons in _states():
        for (x0, y0, x1, y1), polygon in polygons:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and _in_ring(lon, lat, polygon[0]) \
                    and not any(_in_ring(lon, lat, hole) for hole in polygon[1:]):
                return state
    return None


def state_count() -> int:
    return len(_states())
