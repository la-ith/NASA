-- Additive account/field migration. No v1 results are overwritten.
CREATE TABLE IF NOT EXISTS fs_user (
 user_id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
 password_hash TEXT NOT NULL, recovery_hash TEXT NOT NULL, created_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fs_auth_session (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES fs_user(user_id) ON DELETE CASCADE,
 created_utc TEXT NOT NULL, expires_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS fs_auth_user ON fs_auth_session(user_id);
CREATE TABLE IF NOT EXISTS fs_auth_rate (
 rate_key TEXT PRIMARY KEY, window_start INTEGER NOT NULL, attempts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fs_field (
 field_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES fs_user(user_id) ON DELETE CASCADE,
 name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, state TEXT NOT NULL,
 crop TEXT NOT NULL, irrigation TEXT NOT NULL, history TEXT NOT NULL,
 created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS fs_field_owner ON fs_field(user_id,updated_utc);
CREATE TABLE IF NOT EXISTS fs_field_observation (
 observation_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES fs_user(user_id) ON DELETE CASCADE,
 field_id TEXT NOT NULL REFERENCES fs_field(field_id) ON DELETE CASCADE,
 observed_on TEXT NOT NULL, crop TEXT NOT NULL, category TEXT NOT NULL, note TEXT NOT NULL,
 photo_data BLOB, photo_mime TEXT, created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS fs_observation_field ON fs_field_observation(user_id,field_id,observed_on DESC);
CREATE TABLE IF NOT EXISTS fs_expert_request (
 request_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES fs_user(user_id) ON DELETE CASCADE,
 field_id TEXT REFERENCES fs_field(field_id) ON DELETE SET NULL, analysis_id TEXT,
 observation_id TEXT REFERENCES fs_field_observation(observation_id) ON DELETE SET NULL,
 field_snapshot TEXT NOT NULL DEFAULT '{}', question TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','replied')),
 response TEXT, created_utc TEXT NOT NULL, responded_utc TEXT
);
CREATE INDEX IF NOT EXISTS fs_expert_queue ON fs_expert_request(status,created_utc);
