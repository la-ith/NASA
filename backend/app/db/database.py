"""Open the SQLite database, create the tables and load the seed rows (section 6.4)."""
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute("PRAGMA foreign_keys = ON")  # off by default in SQLite
    db.executescript((DB_DIR / "schema.sql").read_text(encoding="utf-8"))
    db.executescript((DB_DIR / "seed.sql").read_text(encoding="utf-8"))
    db.executescript((DB_DIR / "schema_v2.sql").read_text(encoding="utf-8"))  # v4.0 migration, additive only
    for table in ("v2_job", "v2_analysis"):
        if "owner" not in {r[1] for r in db.execute(f"PRAGMA table_info({table})")}:
            db.execute(f"ALTER TABLE {table} ADD COLUMN owner TEXT")
    # Previous in-process jobs cannot resume after restart. Historical results are untouched.
    db.execute("UPDATE v2_job SET state = 'failed', stage = 'interrupted', "
               "error = ? WHERE state IN ('queued', 'running')",
               ('{"code":"server_restart","message":"Server restarted; retry analysis.","retryable":true}',))
    db.commit()
    return db
