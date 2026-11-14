"""NASA POWER Daily API adapter for the FAO-56 weather inputs (spec v4.0, sections 18.2 and 18.3).

Verified by a live call on 14 Nov 2026 (POWER Daily API v2.10.3, community AG): every variable below is
returned in the unit FAO-56 needs, so normalization converts nothing. The adapter checks that the response
matches the request exactly and fails on physically impossible values; NASA's fill value becomes missing.
"""
import asyncio
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import httpx

from app.adapters import NotCovered, ProviderUnavailable, SourceIntegrityError, content_hash

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
COMMUNITY = "AG"
TIME_STANDARD = "LST"
ADAPTER_VERSION = "power-daily-2.1.0"
ATTEMPT_TIMEOUT_S = 20.0
RETRY_DELAY_S = 2.0
FIRST_DATE = date(1981, 1, 1)  # MERRA-2 era start of POWER daily meteorology

# Canonical quantity -> (POWER parameter, unit POWER returns and FAO-56 uses)
VARIABLES = {
    "precipitation": ("PRECTOTCORR", "mm/day"),
    "t_mean": ("T2M", "C"),
    "t_max": ("T2M_MAX", "C"),
    "t_min": ("T2M_MIN", "C"),
    "t_dew": ("T2MDEW", "C"),
    "rh_mean": ("RH2M", "%"),
    "wind_2m": ("WS2M", "m/s"),
    "shortwave_down": ("ALLSKY_SFC_SW_DWN", "MJ/m^2/day"),
    "surface_pressure": ("PS", "kPa"),
}
PHYSICAL_LIMITS = {  # values outside these cannot be real at the land surface
    "precipitation": (0.0, 1000.0), "t_mean": (-90.0, 60.0), "t_max": (-90.0, 60.0), "t_min": (-90.0, 60.0),
    "t_dew": (-100.0, 40.0), "rh_mean": (0.0, 100.0), "wind_2m": (0.0, 75.0), "shortwave_down": (0.0, 45.0),
    "surface_pressure": (30.0, 110.0),
}


def describe_product() -> dict:
    return {
        "provider": "NASA POWER", "product": "POWER Daily API, single point", "community": COMMUNITY,
        "variables": {k: {"parameter": p, "unit": u} for k, (p, u) in VARIABLES.items()},
        "temporal": "daily, local solar time (LST)", "support": "native grid cell of each source (MERRA-2 0.5° × 0.625°; "
        "radiation from CERES SYN1deg 1°), returned for the requested point",
        "license": "NASA open data; cite the POWER Referencing Guide", "adapter_version": ADAPTER_VERSION,
    }


def check_coverage(lon: float, lat: float, start: date, end: date) -> dict:
    """POWER is global; coverage depends only on the dates (1981 onward, with a few months of latency)."""
    if start < FIRST_DATE:
        return {"status": "partial", "reason": f"POWER daily meteorology starts on {FIRST_DATE.isoformat()}"}
    if end > date.today() - timedelta(days=90):
        return {"status": "partial", "reason": "the most recent months may not be published yet"}
    return {"status": "supported", "reason": "global daily record"}


def query(lon: float, lat: float, start: date, end: date) -> dict[str, str]:
    return {
        "parameters": ",".join(p for p, _ in VARIABLES.values()), "community": COMMUNITY,
        "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON", "time-standard": "LST",
    }


async def fetch(client: httpx.AsyncClient, lon: float, lat: float, start: date, end: date) -> dict:
    """One retry on timeout, network error, 429 or 5xx, honouring Retry-After up to 30 s. 4xx is not retried."""
    params = query(lon, lat, start, end)
    for attempt in (1, 2):
        wait = RETRY_DELAY_S
        try:
            async with asyncio.timeout(ATTEMPT_TIMEOUT_S):
                response = await client.get(URL, params=params, timeout=ATTEMPT_TIMEOUT_S)  # httpx default is 5 s
        except (TimeoutError, httpx.TransportError) as exc:
            problem, retryable = f"no response from NASA POWER ({exc!r})", True
        else:
            if response.status_code == 200:
                return response.json()
            problem = f"NASA POWER returned HTTP {response.status_code}"
            retryable = response.status_code == 429 or response.status_code >= 500
            if response.headers.get("Retry-After", "").isdigit():
                wait = min(float(response.headers["Retry-After"]), 30.0)
        if attempt == 1 and retryable:
            await asyncio.sleep(wait)
            continue
        raise ProviderUnavailable(problem)
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class DailyWeather:
    """Normalized daily weather: values[quantity][i] is the value on dates[i], or None where NASA sent its fill value."""
    dates: list[date]
    values: dict[str, list[float | None]]
    latitude: float
    longitude: float
    cell_elevation_m: float
    manifest: dict = field(compare=False)

    def missing(self, quantity: str) -> int:
        return sum(v is None for v in self.values[quantity])


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise SourceIntegrityError(message)


def _number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate_and_normalize(raw: dict, lon: float, lat: float, start: date, end: date,
                           retrieved_utc: datetime) -> DailyWeather:
    """Zero-tolerance contract checks (spec v4.0, sections 8 and 9), then typed values. The raw dict is not changed."""
    try:
        header, block, meta = raw["header"], raw["properties"]["parameter"], raw["parameters"]
        r_lon, r_lat, elevation = raw["geometry"]["coordinates"]
        fill = header["fill_value"]
        api = header["api"]
        h_start, h_end, time_standard, sources = header["start"], header["end"], header["time_standard"], header["sources"]
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceIntegrityError(f"unexpected POWER response structure ({exc!r})") from exc

    expected = {p for p, _ in VARIABLES.values()}
    _require(set(block) == expected and set(meta) == expected,
             f"parameters differ from the request: got {sorted(block)}")
    for quantity, (param, unit) in VARIABLES.items():
        _require(meta[param].get("units") == unit, f"{param}: expected unit {unit!r}, got {meta[param].get('units')!r}")
    _require(time_standard == TIME_STANDARD, f"expected time standard LST, got {time_standard!r}")
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    keys = [d.strftime("%Y%m%d") for d in days]
    _require((h_start, h_end) == (keys[0], keys[-1]), f"requested {keys[0]}-{keys[-1]}, response says {h_start}-{h_end}")
    # POWER echoes the requested point (verified); the native cell is a different, coarser support.
    # The API returns GeoJSON coordinates at three decimals, including when the
    # request carries four (observed in the station-coordinate pilot downloads).
    # Compare that exact serialization contract, not a distance tolerance.
    sent = query(lon, lat, start, end)
    expected_point = (round(float(sent["latitude"]), 3), round(float(sent["longitude"]), 3))
    _require((r_lat, r_lon) == expected_point,
             f"requested {lat}, {lon}; response is for {r_lat}, {r_lon}")
    _require(_number(fill) and _number(elevation), "fill value or elevation is not a number")

    values: dict[str, list[float | None]] = {}
    for quantity, (param, _) in VARIABLES.items():
        series = block[param]
        _require(set(series) == set(keys), f"{param}: dates differ from the request")
        low, high = PHYSICAL_LIMITS[quantity]
        column = []
        for key in keys:
            v = series[key]
            _require(_number(v), f"{param} {key}: {v!r} is not a number")
            if v == fill:
                column.append(None)
                continue
            _require(low <= v <= high, f"{param} {key}: {v} is outside the physically possible range {low}-{high}")
            column.append(float(v))
        values[quantity] = column
    for i, key in enumerate(keys):
        t_min, t_max = values["t_min"][i], values["t_max"][i]
        _require(t_min is None or t_max is None or t_min <= t_max, f"{key}: minimum temperature above maximum")

    manifest = {
        "dataset_id": content_hash(raw)[:24], "provider": "NASA POWER", "product": api.get("name"),
        "version": api.get("version"), "community": COMMUNITY, "sources": sources,
        "variables": {q: {"parameter": p, "original_unit": u, "normalized_unit": u} for q, (p, u) in VARIABLES.items()},
        "transformations": "none: POWER units equal FAO-56 units; fill value -> missing",
        "time_standard": time_standard, "interval": "daily", "requested_point": {"lat": lat, "lon": lon},
        "returned_support": {"type": "grid cell of each source product", "cell_elevation_m": elevation,
                             "response_point": {"lat": r_lat, "lon": r_lon},
                             "coordinate_contract": "request at 4 decimals; returned point at 3 decimals"},
        "crs": "EPSG:4326", "period": [days[0].isoformat(), days[-1].isoformat()],
        "missing_values": {q: sum(v is None for v in col) for q, col in values.items()},
        "retrieved_utc": retrieved_utc.isoformat(), "content_sha256": content_hash(raw),
        "adapter_version": ADAPTER_VERSION,
        "reference": "The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research "
                     "Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth "
                     "Science Division.",
    }
    return DailyWeather(days, values, lat, lon, float(elevation), manifest)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def require_period(weather: DailyWeather, start: date, end: date) -> None:
    if weather.dates[0] > start or weather.dates[-1] < end:
        raise NotCovered("the weather record does not cover the requested period")
