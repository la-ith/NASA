"""From request to climate evidence: the NASA data part of one analysis (section 6, steps 3-5)."""
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from app.services.climate_cache import cache_get, cache_put
from app.services.climate_provider import fetch_power_daily, power_query
from app.services.indicators import BASELINE_YEARS, Indicators, SeasonTotal, compute_indicators, seasonal_totals
from app.services.site_check import SiteCheck, StationReference, run_site_check
from app.services.validation import DailyRecord, parse_power_response

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "demo"
SAMPLE_RECORD = DATA_DIR / "power_pilot_19911001_20260531.json"  # {"retrieved_utc": ..., "response": <POWER JSON>}
STATION_FILE = DATA_DIR / "site_check.json"


@dataclass(frozen=True)
class ClimateContext:
    mode: str
    retrieved_utc: datetime
    period: tuple[date, date]
    record: DailyRecord
    seasons: list[SeasonTotal]
    indicators: Indicators
    site: SiteCheck


def load_station() -> StationReference | None:
    if not STATION_FILE.exists():
        return None
    return StationReference(**json.loads(STATION_FILE.read_text(encoding="utf-8")))


async def build_climate_context(
    mode: str, lat: float, lon: float, candidate_year: int, client: httpx.AsyncClient, db: sqlite3.Connection
) -> ClimateContext:
    start, end = date(BASELINE_YEARS.start, 10, 1), date(candidate_year, 5, 31)
    query = power_query(lat, lon, start, end)
    fresh = False
    if mode == "sample":
        saved = json.loads(SAMPLE_RECORD.read_text(encoding="utf-8"))
        raw, retrieved = saved["response"], datetime.fromisoformat(saved["retrieved_utc"])
    elif cached := cache_get(db, query):
        raw, retrieved = cached
    else:
        raw, retrieved, fresh = await fetch_power_daily(client, lat, lon, start, end), datetime.now(timezone.utc), True

    # Validate every time, cached copies included. Raises DataIntegrityError or UnusableRecord.
    record = parse_power_response(raw, lat, lon, start, end)
    if fresh:
        cache_put(db, query, raw, retrieved)  # only validated responses are cached
    seasons = seasonal_totals(record, BASELINE_YEARS.start, candidate_year - 1)
    return ClimateContext(
        mode, retrieved, (start, end), record, seasons,
        compute_indicators(seasons, candidate_year), run_site_check(seasons, load_station()),
    )
