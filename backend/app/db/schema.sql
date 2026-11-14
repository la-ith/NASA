-- SQLite schema for the MVP: the v3.1 tables, keys and relationships (section 6.4), plus the section 9 cache.
-- Foreign keys must be switched on per connection. An analysis and every row that belongs to it are
-- written once and never updated, so an earlier result never changes.

CREATE TABLE IF NOT EXISTS field (
  field_id    INTEGER PRIMARY KEY,
  label       TEXT,
  latitude    REAL NOT NULL,             -- rounded to 0.1 degree; exact coordinates are never stored
  longitude   REAL NOT NULL,
  area_value  REAL NOT NULL CHECK (area_value > 0),
  area_unit   TEXT NOT NULL CHECK (area_unit IN ('dunum', 'hectare', 'acre')),
  irrigation  TEXT NOT NULL CHECK (irrigation IN ('rain-fed', 'irrigated', 'mixed', 'unknown')),
  soil_input  TEXT NOT NULL DEFAULT 'unknown'
);

CREATE TABLE IF NOT EXISTS crop (
  crop_id            INTEGER PRIMARY KEY,
  name               TEXT NOT NULL UNIQUE,
  crop_type          TEXT NOT NULL
                     CHECK (crop_type IN ('cereal', 'grain_legume', 'forage_legume', 'fallow', 'unclassified')),
  season             TEXT,              -- 'winter' for supported candidate crops; NULL for history-only choices
  water_need_min_mm  REAL,              -- NULL: no confirmed figure
  water_need_max_mm  REAL,
  water_source       TEXT,
  review_state       TEXT NOT NULL CHECK (review_state IN ('draft-unreviewed', 'reviewed', 'retired'))
);

CREATE TABLE IF NOT EXISTS crop_season (
  season_id   INTEGER PRIMARY KEY,
  field_id    INTEGER NOT NULL REFERENCES field (field_id),
  start_date  TEXT NOT NULL,             -- ISO date, 1 October; the label (for example 2025/26) follows from it
  end_date    TEXT NOT NULL,             -- ISO date, 31 May
  crop_id     INTEGER REFERENCES crop (crop_id),
  unknown     INTEGER NOT NULL CHECK (unknown IN (0, 1)),
  source      TEXT NOT NULL CHECK (source IN ('farmer', 'team')),
  confidence  TEXT,                      -- how sure the person entering it was, if they said
  UNIQUE (field_id, start_date),
  CHECK ((crop_id IS NULL) = (unknown = 1))  -- an unknown season stays explicit; no crop is ever fabricated
);

CREATE TABLE IF NOT EXISTS rotation_rule (  -- every rule: H1-H3 and R1-R6
  rule_id       INTEGER PRIMARY KEY,
  code          TEXT NOT NULL,
  version       TEXT NOT NULL,
  condition     TEXT NOT NULL,
  effect        TEXT NOT NULL,
  citation      TEXT,                    -- NULL until the agronomy owner locates it
  region        TEXT NOT NULL,
  reviewer      TEXT,
  review_state  TEXT NOT NULL CHECK (review_state IN ('draft-unreviewed', 'reviewed', 'retired')),
  UNIQUE (code, version)
);

CREATE TABLE IF NOT EXISTS analysis (
  analysis_id      TEXT PRIMARY KEY,     -- random, never sequential
  field_id         INTEGER NOT NULL REFERENCES field (field_id),
  created_utc      TEXT NOT NULL,
  goal             TEXT NOT NULL CHECK (goal IN ('conserve_water', 'improve_soil_rotation', 'balance_both')),
  input_snapshot   TEXT NOT NULL,        -- JSON: the validated request, including mode and candidate season
  engine_version   TEXT NOT NULL,
  rules_version    TEXT NOT NULL,
  status           TEXT NOT NULL CHECK (status IN ('complete', 'partial')),
  result_snapshot  TEXT NOT NULL         -- added in v3.2: the response returned to the UI
);

CREATE TABLE IF NOT EXISTS climate_dataset (
  dataset_id        INTEGER PRIMARY KEY,
  analysis_id       TEXT NOT NULL REFERENCES analysis (analysis_id),
  provider          TEXT NOT NULL,       -- 'NASA POWER'
  product           TEXT NOT NULL,       -- header.api.name, exactly as received
  variable          TEXT NOT NULL,       -- 'PRECTOTCORR'
  latitude          REAL NOT NULL,       -- the requested (rounded) point
  longitude         REAL NOT NULL,
  start_date        TEXT NOT NULL,
  end_date          TEXT NOT NULL,
  units             TEXT NOT NULL,
  retrieved_utc     TEXT NOT NULL,
  valid_days        INTEGER NOT NULL,    -- quality counts; valid days include flagged days
  missing_days      INTEGER NOT NULL,
  flagged_days      INTEGER NOT NULL,
  mode              TEXT NOT NULL CHECK (mode IN ('live', 'sample')),  -- added in v3.2, as are the columns below
  community         TEXT NOT NULL,
  api_version       TEXT NOT NULL,       -- source metadata, exactly as received
  sources           TEXT NOT NULL,       -- JSON list, exactly as received
  fill_value        REAL NOT NULL,
  time_standard     TEXT NOT NULL,
  cell_elevation_m  REAL NOT NULL,
  site_check        TEXT NOT NULL CHECK (site_check IN ('representative', 'not_representative', 'not_checked')),
  adapter_version   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS climate_observation (
  dataset_id      INTEGER NOT NULL REFERENCES climate_dataset (dataset_id),
  obs_date        TEXT NOT NULL,         -- ISO date
  value_mm        REAL,                  -- exactly as returned; NULL only for NASA's fill value
  quality_status  TEXT NOT NULL CHECK (quality_status IN ('valid', 'flagged', 'missing')),
  PRIMARY KEY (dataset_id, obs_date),
  CHECK ((value_mm IS NULL) = (quality_status = 'missing'))
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS candidate_plan (
  plan_id        INTEGER PRIMARY KEY,
  analysis_id    TEXT NOT NULL REFERENCES analysis (analysis_id),
  crop_id        INTEGER NOT NULL REFERENCES crop (crop_id),
  role           TEXT NOT NULL CHECK (role IN ('current_practice', 'alternative')),
  display_order  INTEGER NOT NULL,
  plan_code      TEXT NOT NULL CHECK (plan_code IN ('A', 'B', 'C')),  -- added in v3.2, with why_included
  why_included   TEXT NOT NULL,
  UNIQUE (analysis_id, plan_code)
);

CREATE TABLE IF NOT EXISTS plan_evidence (
  evidence_id  INTEGER PRIMARY KEY,
  plan_id      INTEGER NOT NULL REFERENCES candidate_plan (plan_id),
  rule_id      INTEGER REFERENCES rotation_rule (rule_id),  -- NULL only for a rotation result no single rule produced
  criterion    TEXT NOT NULL CHECK (criterion IN ('hard_constraint', 'rotation_soil', 'water_fit', 'risk')),
  label        TEXT NOT NULL CHECK (label IN ('rejected', 'favorable', 'mixed', 'concern', 'insufficient_evidence')),
  explanation  TEXT NOT NULL,            -- the reason and evidence shown to the user
  rule_state   TEXT NOT NULL,            -- added in v3.2: the rule's review state when the analysis ran
  UNIQUE (plan_id, criterion),
  CHECK ((criterion = 'hard_constraint') = (label = 'rejected'))
);

CREATE TABLE IF NOT EXISTS plan_input_status (
  plan_id    INTEGER NOT NULL REFERENCES candidate_plan (plan_id),
  input_key  TEXT NOT NULL,              -- for example 'crop 2023/24'
  status     TEXT NOT NULL CHECK (status IN ('entered', 'estimated', 'assumed', 'missing')),
  source     TEXT,                       -- the source, or the stated default
  effect     TEXT NOT NULL,
  PRIMARY KEY (plan_id, input_key)
) WITHOUT ROWID;

-- The section 9 cache. It sits outside the relational model: no foreign keys, and no stored result depends on it.
CREATE TABLE IF NOT EXISTS power_cache (
  request_key    TEXT PRIMARY KEY,       -- latitude|longitude|parameter|community|start|end
  retrieved_utc  TEXT NOT NULL,
  api_version    TEXT NOT NULL,
  raw_response   TEXT NOT NULL           -- exactly as received; re-validated on every use
);
