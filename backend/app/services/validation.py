"""Check a raw POWER response against the request with zero tolerance (section 16.2)."""
import math
from dataclasses import dataclass
from datetime import date, timedelta

PARAMETER = "PRECTOTCORR"
UNITS = "mm/day"
TIME_STANDARD = "LST"  # daily values run from local solar midnight to midnight
PLAUSIBLE_MAX_MM_PER_DAY = 300.0  # team choice: higher values are flagged, never changed


class UnusableRecord(Exception):
    """The response cannot be used. The UI shows the data-error state."""

    code = "no_data"


class DataIntegrityError(UnusableRecord):
    """The response does not match the request exactly. No tolerance applies."""

    code = "data_integrity"


@dataclass(frozen=True)
class DailyRecord:
    values: dict[date, float | None]  # exactly as returned; None only where NASA sent its fill value
    valid_days: int
    missing_days: int
    flags: list[str]
    api_name: str  # source metadata below is stored exactly as received
    api_version: str
    sources: list[str]
    fill_value: float
    time_standard: str
    cell_elevation_m: float


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise DataIntegrityError(message)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_power_response(raw: dict, lat: float, lon: float, start: date, end: date) -> DailyRecord:
    try:
        header = raw["header"]
        returned = raw["properties"]["parameter"]
        metadata = raw["parameters"]
        returned_lon, returned_lat, cell_elevation_m = raw["geometry"]["coordinates"]
        fill_value, sources = header["fill_value"], header["sources"]
        api_name, api_version = header["api"]["name"], header["api"]["version"]
        time_standard, header_start, header_end = header["time_standard"], header["start"], header["end"]
    except (KeyError, TypeError, ValueError) as exc:
        raise DataIntegrityError(f"unexpected response structure ({exc!r})") from exc

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    keys = [d.strftime("%Y%m%d") for d in days]
    _require(set(returned) == {PARAMETER} and set(metadata) == {PARAMETER},
             f"expected only {PARAMETER}, got {sorted(returned)} and {sorted(metadata)}")
    units = metadata[PARAMETER].get("units")
    _require(units == UNITS, f"expected units {UNITS!r}, got {units!r}")
    _require(time_standard == TIME_STANDARD, f"expected time standard {TIME_STANDARD!r}, got {time_standard!r}")
    _require((header_start, header_end) == (keys[0], keys[-1]),
             f"requested {keys[0]} to {keys[-1]}, response header says {header_start} to {header_end}")
    _require((returned_lat, returned_lon) == (lat, lon),
             f"requested {lat}, {lon}; response is for {returned_lat}, {returned_lon}")
    _require(_is_number(fill_value) and _is_number(cell_elevation_m), "fill value or cell elevation is not a number")
    _require(isinstance(api_name, str) and isinstance(api_version, str) and isinstance(sources, list),
             "API name, API version or sources missing")

    series = returned[PARAMETER]
    missing_keys, extra_keys = sorted(set(keys) - set(series)), sorted(set(series) - set(keys))
    _require(not missing_keys and not extra_keys,
             f"dates differ from the request: missing {missing_keys[:3]}, extra {extra_keys[:3]}")

    values: dict[date, float | None] = {}
    flags: list[str] = []
    for day, key in zip(days, keys):
        value = series[key]
        _require(_is_number(value), f"{key}: value {value!r} is not a number")
        if value == fill_value:
            values[day] = None  # NASA's declared missing marker becomes an explicit missing status
            continue
        _require(value >= 0, f"{key}: negative precipitation {value}")
        if value > PLAUSIBLE_MAX_MM_PER_DAY:
            flags.append(f"{key}: {value} mm/day is above the plausible-range check; kept unchanged")
        values[day] = value  # never rounded or converted

    valid_days = sum(v is not None for v in values.values())
    if valid_days == 0:
        raise UnusableRecord("no valid days in the requested period")
    return DailyRecord(
        values, valid_days, len(values) - valid_days, flags,
        api_name, api_version, sources, fill_value, time_standard, cell_elevation_m,
    )
