"""Where v4 source records come from: a live call, the 30-day cache, or the saved demo fixtures.

Every path ends in the same validation, so a cached or saved record is checked as strictly as a fresh one.
Original responses are stored unchanged with their manifest (spec v4.0, section 18.4).
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.adapters import NotCovered, content_hash, power, ssurgo
from app.science.crop import Horizon
from app.services.analysis_v2 import SoilInput, soil_from_ssurgo

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "fixtures"
DEMO_SITES = {"ks_hays": (-99.33, 38.85), "ia_ames": (-93.62, 42.03)}  # (lon, lat)
FIXTURE_PERIOD = (date(2001, 1, 1), date(2025, 12, 31))
CACHE_TTL = timedelta(days=30)


class SampleNotAvailable(Exception):
    code = "sample_not_available"


def demo_site(lon: float, lat: float) -> str | None:
    return next((name for name, (x, y) in DEMO_SITES.items() if (round(lon, 4), round(lat, 4)) == (x, y)), None)


def _store(db: sqlite3.Connection, provider: str, key: str, manifest: dict, raw: dict, retrieved: str) -> None:
    with db:
        db.execute("INSERT OR IGNORE INTO v2_source_record VALUES (?, ?, ?, ?, ?, ?)",
                   (content_hash([provider, key, retrieved, content_hash(raw)])[:32], provider, key, retrieved,
                    json.dumps(manifest), json.dumps(raw)))


def _cached(db: sqlite3.Connection, provider: str, key: str) -> tuple[dict, str] | None:
    row = db.execute("SELECT raw_response, retrieved_utc FROM v2_source_record WHERE provider = ? AND request_key = ?"
                     " ORDER BY retrieved_utc DESC LIMIT 1", (provider, key)).fetchone()
    if row is None or datetime.now(timezone.utc) - datetime.fromisoformat(row[1]) > CACHE_TTL:
        return None
    return json.loads(row[0]), row[1]


async def weather(db: sqlite3.Connection, client: httpx.AsyncClient, lon: float, lat: float, start: date, end: date,
                  mode: str) -> power.DailyWeather:
    if mode == "sample":
        site = demo_site(lon, lat)
        if site is None:
            raise SampleNotAvailable(f"sample data exists only for the demo sites {sorted(DEMO_SITES)}")
        if start < FIXTURE_PERIOD[0] or end > FIXTURE_PERIOD[1]:
            raise SampleNotAvailable("the saved sample covers 2001-2025 only")
        saved = json.loads((FIXTURES / f"power_{site}_2001_2025.json").read_text(encoding="utf-8"))
        return power.validate_and_normalize(saved["response"], lon, lat, *FIXTURE_PERIOD,
                                            datetime.fromisoformat(saved["retrieved_utc"]))
    key = json.dumps({"q": power.query(lon, lat, start, end), "v": power.ADAPTER_VERSION}, sort_keys=True)
    hit = _cached(db, "power", key)
    if hit:
        raw, retrieved = hit
        return power.validate_and_normalize(raw, lon, lat, start, end, datetime.fromisoformat(retrieved))
    raw = await power.fetch(client, lon, lat, start, end)
    retrieved = power.now_utc()
    result = power.validate_and_normalize(raw, lon, lat, start, end, retrieved)  # only valid records are stored
    _store(db, "power", key, result.manifest, raw, retrieved.isoformat())
    return result


@dataclass(frozen=True)
class SoilOutcome:
    soil: SoilInput | None
    coverage: str  # "supported", "user", "unsupported"
    reason: str


async def soil(db: sqlite3.Connection, client: httpx.AsyncClient, lon: float, lat: float, mode: str,
               override: dict | None) -> SoilOutcome:
    if override:
        depth = override["depth_cm"]
        horizons = [Horizon(0.0, depth, override["awc_mm_per_m"] / 1000.0)]
        return SoilOutcome(SoilInput("user", horizons, override["hydrologic_group"], depth,
                                     f"entered by user: {override['awc_mm_per_m']:g} mm/m to {depth:g} cm, "
                                     f"group {override['hydrologic_group']}", []), "user", "entered by the user")
    try:
        if mode == "sample":
            site = demo_site(lon, lat)
            if site is None:
                raise SampleNotAvailable(f"sample data exists only for the demo sites {sorted(DEMO_SITES)}")
            saved = json.loads((FIXTURES / f"ssurgo_{site}.json").read_text(encoding="utf-8"))
            profile = ssurgo.validate_and_normalize(saved["response"], lon, lat, saved["retrieved_utc"])
            limits = json.loads((FIXTURES / f"ssurgo_restrictions_{site}.json").read_text(encoding="utf-8"))
            profile = ssurgo.apply_restrictions(profile, limits["response"], limits["retrieved_utc"])
        else:
            key = json.dumps({"point": [round(lon, 6), round(lat, 6)], "v": ssurgo.ADAPTER_VERSION}, sort_keys=True)
            hit = _cached(db, "ssurgo", key)
            if hit:
                profile = ssurgo.validate_and_normalize(hit[0], lon, lat, hit[1])
            else:
                raw = await ssurgo.fetch(client, lon, lat)
                retrieved = power.now_utc().isoformat()
                profile = ssurgo.validate_and_normalize(raw, lon, lat, retrieved)
                _store(db, "ssurgo", key, profile.manifest, raw, retrieved)
            hit = _cached(db, "ssurgo_restrictions", key)
            if hit:
                profile = ssurgo.apply_restrictions(profile, hit[0], hit[1])
            else:
                raw = await ssurgo.fetch_restrictions(client, lon, lat)
                retrieved = power.now_utc().isoformat()
                profile = ssurgo.apply_restrictions(profile, raw, retrieved)
                _store(db, "ssurgo_restrictions", key, profile.manifest["restrictions"], raw, retrieved)
    except NotCovered as exc:
        return SoilOutcome(None, "unsupported", str(exc))
    return SoilOutcome(soil_from_ssurgo(profile), "supported", "SSURGO map unit found")
