-- Phone/web link: the PC pushes its app state; paired devices read it and queue commands for the PC.

-- Devices paired to an account (phone, laptop browser). Only the SHA-256 of the token is stored.
CREATE TABLE IF NOT EXISTS devices (
  token_hash TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label      TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_seen  TEXT
);
CREATE INDEX IF NOT EXISTS devices_user ON devices(user_id);

-- Short-lived pairing codes shown on the PC (10 minutes, single use).
CREATE TABLE IF NOT EXISTS pair_codes (
  code       TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL
);

-- Latest app state snapshot pushed by the PC (one row per user).
CREATE TABLE IF NOT EXISTS app_state (
  user_id    TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  state      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Commands queued by paired devices for the PC to apply (goals, track, pad control).
CREATE TABLE IF NOT EXISTS app_commands (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       TEXT NOT NULL,
  payload    TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS app_commands_user ON app_commands(user_id, id);

-- Apple Health (via iOS Shortcuts): which pad walks were already written to Health, and the
-- all-day step totals read back from Health.
CREATE TABLE IF NOT EXISTS health_acked (
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  walk_id    TEXT NOT NULL,
  acked_at   TEXT NOT NULL,
  PRIMARY KEY (user_id, walk_id)
);
CREATE TABLE IF NOT EXISTS health_days (
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date       TEXT NOT NULL,
  steps      INTEGER NOT NULL,
  km         REAL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, date)
);
