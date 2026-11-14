"""Open the SQLite database, create the tables and load the seed rows (section 6.4)."""
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute("PRAGMA foreign_keys = ON")  # off by default in SQLite
    db.executescript((DB_DIR / "schema.sql").read_text(encoding="utf-8"))
    db.executescript((DB_DIR / "seed.sql").read_text(encoding="utf-8"))
    return db
