"""The section 9 cache: validated POWER responses, exactly as received, reused for 30 days.
It sits outside the relational model in section 6.4; no stored result depends on it."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone

CACHE_TTL = timedelta(days=30)


def _key(query: dict[str, str]) -> str:
    return "|".join(query[k] for k in ("latitude", "longitude", "parameters", "community", "start", "end"))


def cache_get(db: sqlite3.Connection, query: dict[str, str]) -> tuple[dict, datetime] | None:
    row = db.execute(
        "SELECT retrieved_utc, raw_response FROM power_cache WHERE request_key = ?", (_key(query),)
    ).fetchone()
    if row is None or datetime.now(timezone.utc) - datetime.fromisoformat(row[0]) > CACHE_TTL:
        return None
    return json.loads(row[1]), datetime.fromisoformat(row[0])


def cache_put(db: sqlite3.Connection, query: dict[str, str], raw: dict, retrieved: datetime) -> None:
    with db:
        db.execute(
            "INSERT OR REPLACE INTO power_cache VALUES (?, ?, ?, ?)",
            (_key(query), retrieved.isoformat(), raw["header"]["api"]["version"], json.dumps(raw)),
        )
