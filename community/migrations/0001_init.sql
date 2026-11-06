-- Walking Pad Community: initial schema.
-- Times are unix milliseconds (INTEGER). Dates are 'YYYY-MM-DD' (UTC calendar days as sent by the client).

CREATE TABLE users (
  id            TEXT PRIMARY KEY,               -- random 12-char id
  handle        TEXT NOT NULL UNIQUE,           -- [a-z0-9_]{3,20}
  display_name  TEXT NOT NULL,
  token_hash    TEXT NOT NULL UNIQUE,           -- hex SHA-256 of the bearer token (token itself never stored)
  public        INTEGER NOT NULL DEFAULT 0,     -- 1 = appears on the global leaderboard
  streak        INTEGER NOT NULL DEFAULT 0,     -- current streak, as reported by the client
  created_at    INTEGER NOT NULL,
  last_sync_at  INTEGER
);
CREATE INDEX idx_users_public ON users(public);

CREATE TABLE days (
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date       TEXT NOT NULL,
  steps      INTEGER NOT NULL DEFAULT 0,
  minutes    REAL NOT NULL DEFAULT 0,
  km         REAL NOT NULL DEFAULT 0,
  goal_met   INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, date)                   -- per-user range scans for leaderboards
);
CREATE INDEX idx_days_date_user ON days(date, user_id);

CREATE TABLE groups (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  invite_code TEXT NOT NULL UNIQUE,             -- 8 chars, unambiguous alphabet, stored upper-case
  created_at  INTEGER NOT NULL
);

CREATE TABLE memberships (
  group_id  TEXT NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  user_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role      TEXT NOT NULL CHECK (role IN ('owner', 'member')),
  joined_at INTEGER NOT NULL,
  PRIMARY KEY (group_id, user_id)
);
CREATE INDEX idx_memberships_user ON memberships(user_id, role);
CREATE INDEX idx_memberships_group_joined ON memberships(group_id, joined_at);

-- Fixed-window rate-limit counters.
CREATE TABLE rate_limits (
  key          TEXT NOT NULL,                   -- 'tok:<hash>' or 'reg:<ip>'
  window_start INTEGER NOT NULL,                -- unix seconds at start of window
  count        INTEGER NOT NULL,
  PRIMARY KEY (key, window_start)
);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start);
