-- Migration for spec v4.0 (section 21.4). Adds tables; changes nothing in the v1 (Hebron) tables.
-- Source records and analyses are written once and never updated. Jobs are operational records and may change.

CREATE TABLE IF NOT EXISTS v2_source_record (
  record_id      TEXT PRIMARY KEY,       -- hash of provider, request, retrieval time and content
  provider       TEXT NOT NULL,          -- 'power' or 'ssurgo'
  request_key    TEXT NOT NULL,          -- provider, product, variables, point, period, time standard, adapter version
  retrieved_utc  TEXT NOT NULL,
  manifest       TEXT NOT NULL,          -- JSON dataset manifest (section 18.4)
  raw_response   TEXT NOT NULL           -- the original response, exactly as received
);
CREATE INDEX IF NOT EXISTS v2_source_lookup ON v2_source_record (provider, request_key, retrieved_utc);

CREATE TABLE IF NOT EXISTS v2_analysis (
  analysis_id     TEXT PRIMARY KEY,      -- unguessable ID; owner cookie scope is enforced by API
  created_utc     TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('complete', 'partial', 'unsupported')),
  engine_version  TEXT NOT NULL,
  request         TEXT NOT NULL,         -- JSON input snapshot
  result          TEXT NOT NULL          -- JSON result snapshot
);

CREATE TABLE IF NOT EXISTS v2_job (
  job_id       TEXT PRIMARY KEY,
  created_utc  TEXT NOT NULL,
  updated_utc  TEXT NOT NULL,
  state        TEXT NOT NULL CHECK (state IN ('queued', 'running', 'succeeded', 'failed')),
  stage        TEXT,
  analysis_id  TEXT REFERENCES v2_analysis (analysis_id),
  error        TEXT                      -- JSON error envelope when failed
);

CREATE TABLE IF NOT EXISTS v2_product_record (
 artifact_id TEXT PRIMARY KEY, owner TEXT NOT NULL, product TEXT NOT NULL,
 retrieved_utc TEXT NOT NULL, raw TEXT NOT NULL, result TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_chat_session (
 session_id TEXT PRIMARY KEY, owner TEXT NOT NULL, analysis_id TEXT,
 created_utc TEXT NOT NULL, messages TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_ai_usage (
 utc_day TEXT PRIMARY KEY, requests INTEGER NOT NULL DEFAULT 0
);
