"""Open the SQLite database and create or migrate the AstroRoot tables."""
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute("PRAGMA foreign_keys = ON")  # off by default in SQLite
    db.executescript((DB_DIR / "schema_v2.sql").read_text(encoding="utf-8"))
    db.executescript((DB_DIR / "schema_accounts.sql").read_text(encoding="utf-8"))
    if "details" not in {r[1] for r in db.execute("PRAGMA table_info(fs_field)")}:
        db.execute("ALTER TABLE fs_field ADD COLUMN details TEXT NOT NULL DEFAULT '{}'")
    if "field_snapshot" not in {r[1] for r in db.execute("PRAGMA table_info(fs_expert_request)")}:
        db.execute("ALTER TABLE fs_expert_request ADD COLUMN field_snapshot TEXT NOT NULL DEFAULT '{}'")
    if "observation_id" not in {r[1] for r in db.execute("PRAGMA table_info(fs_expert_request)")}:
        db.execute("ALTER TABLE fs_expert_request ADD COLUMN observation_id TEXT REFERENCES fs_field_observation(observation_id) ON DELETE SET NULL")
    for table in ("v2_job", "v2_analysis"):
        if "owner" not in {r[1] for r in db.execute(f"PRAGMA table_info({table})")}:
            db.execute(f"ALTER TABLE {table} ADD COLUMN owner TEXT")
    if 'field_id' not in {r[1] for r in db.execute('PRAGMA table_info(v2_analysis)')}:
        db.execute('ALTER TABLE v2_analysis ADD COLUMN field_id TEXT')
    # Previous in-process jobs cannot resume after restart. Historical results are untouched.
    db.execute("UPDATE v2_job SET state = 'failed', stage = 'interrupted', "
               "error = ? WHERE state IN ('queued', 'running')",
               ('{"code":"server_restart","message":"Server restarted; retry analysis.","retryable":true}',))
    db.commit()
    return db
