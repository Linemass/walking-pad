// Walking Pad Community API — Cloudflare Worker + D1. Zero runtime dependencies.
// All routes live under /v1. JSON in, JSON out. Errors: {"error": "<message>"}.

const MAX_BODY_BYTES = 64 * 1024;
const MAX_STATE_BYTES = 384 * 1024;   // app state snapshot pushed by the PC
const MAX_PENDING_COMMANDS = 50;
const PAIR_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const MAX_SYNC_DAYS = 62;
const MAX_OWNED_GROUPS = 20;
const MAX_GROUP_MEMBERS = 50;
const MAX_RANGE_DAYS = 31;
const PAST_DAYS_ALLOWED = 400;
const FUTURE_DAYS_ALLOWED = 1;
const DAY_MS = 86400000;

const ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789";
const INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"; // no 0/O/1/I/L
const HANDLE_RE = /^[a-z0-9_]{3,20}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
// C0/C1 control characters plus bidi override/isolate characters.
const BAD_NAME_CHARS = /[\u0000-\u001f\u007f-\u009f‪-‮⁦-⁩]/;

const METRICS = {
  steps: "COALESCE(SUM(d.steps), 0)",
  minutes: "ROUND(COALESCE(SUM(d.minutes), 0), 1)",
  km: "ROUND(COALESCE(SUM(d.km), 0), 2)",
  goal_days: "COALESCE(SUM(d.goal_met), 0)",
  streak: "MAX(u.streak)",
};

class HttpError extends Error {
  constructor(status, message, headers) {
    super(message);
    this.status = status;
    this.headers = headers || {};
  }
}

// ---------- helpers ----------

function json(status, body, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers },
  });
}

function randomString(len, alphabet) {
  // Rejection sampling to avoid modulo bias.
  const max = 256 - (256 % alphabet.length);
  let out = "";
  while (out.length < len) {
    const buf = crypto.getRandomValues(new Uint8Array(len * 2));
    for (const b of buf) {
      if (b < max) out += alphabet[b % alphabet.length];
      if (out.length === len) break;
    }
  }
  return out;
}

function hex(bytes) {
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Hex(text) {
  return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)));
}

function todayUtc(now = Date.now()) {
  return new Date(now).toISOString().slice(0, 10);
}

function addDays(dateStr, n) {
  return new Date(Date.parse(dateStr + "T00:00:00Z") + n * DAY_MS).toISOString().slice(0, 10);
}

function isRealDate(s) {
  if (typeof s !== "string" || !DATE_RE.test(s)) return false;
  const t = Date.parse(s + "T00:00:00Z");
  return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === s;
}

function dayDiff(a, b) {
  return Math.round((Date.parse(b + "T00:00:00Z") - Date.parse(a + "T00:00:00Z")) / DAY_MS);
}

function validateDisplayName(v) {
  if (typeof v !== "string") throw new HttpError(400, "display_name must be a string");
  const name = v.trim();
  const len = [...name].length;
  if (len < 1 || len > 40) throw new HttpError(400, "display_name must be 1-40 characters");
  if (BAD_NAME_CHARS.test(name)) throw new HttpError(400, "display_name contains control characters");
  return name;
}

function validateGroupName(v) {
  if (typeof v !== "string") throw new HttpError(400, "name must be a string");
  const name = v.trim();
  const len = [...name].length;
  if (len < 1 || len > 40) throw new HttpError(400, "name must be 1-40 characters");
  if (BAD_NAME_CHARS.test(name)) throw new HttpError(400, "name contains control characters");
  return name;
}

function intEnv(env, key, fallback) {
  const n = parseInt(env[key], 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

async function readJson(request, max = MAX_BODY_BYTES) {
  const declared = request.headers.get("Content-Length");
  const label = `request body too large (max ${Math.round(max / 1024)} KB)`;
  if (declared && Number(declared) > max) throw new HttpError(413, label);
  const buf = await request.arrayBuffer();
  if (buf.byteLength > max) throw new HttpError(413, label);
  if (buf.byteLength === 0) return {};
  let data;
  try {
    data = JSON.parse(new TextDecoder().decode(buf));
  } catch {
    throw new HttpError(400, "invalid JSON body");
  }
  if (data === null || typeof data !== "object" || Array.isArray(data)) throw new HttpError(400, "JSON body must be an object");
  return data;
}

// Fixed-window counter in D1. Throws 429 when over the limit.
async function rateLimit(env, key, limit, windowSec) {
  const nowSec = Math.floor(Date.now() / 1000);
  const windowStart = nowSec - (nowSec % windowSec);
  const row = await env.DB.prepare(
    `INSERT INTO rate_limits (key, window_start, count) VALUES (?1, ?2, 1)
     ON CONFLICT (key, window_start) DO UPDATE SET count = count + 1
     RETURNING count`
  ).bind(key, windowStart).first();
  // Opportunistic cleanup of stale windows (~1% of requests).
  if (Math.random() < 0.01) {
    await env.DB.prepare("DELETE FROM rate_limits WHERE window_start < ?1").bind(nowSec - 7200).run();
  }
  if (row && row.count > limit) {
    const retry = Math.max(1, windowStart + windowSec - nowSec);
    throw new HttpError(429, "rate limit exceeded", { "Retry-After": String(retry) });
  }
}

async function authenticate(request, env) {
  const h = request.headers.get("Authorization") || "";
  const m = /^Bearer\s+([0-9a-fA-F]{64})\s*$/.exec(h);
  if (!m) throw new HttpError(401, "missing or invalid bearer token");
  const tokenHash = await sha256Hex(m[1].toLowerCase());
  let user = await env.DB.prepare(
    "SELECT id, handle, display_name, public, streak, created_at FROM users WHERE token_hash = ?1"
  ).bind(tokenHash).first();
  if (user) user.scope = "account";
  else {
    user = await env.DB.prepare(
      `SELECT u.id, u.handle, u.display_name, u.public, u.streak, u.created_at, d.last_seen FROM devices d
       JOIN users u ON u.id = d.user_id WHERE d.token_hash = ?1`
    ).bind(tokenHash).first();
    if (user) {
      user.scope = "device";
      const now = new Date().toISOString();
      if (!user.last_seen || Date.parse(now) - Date.parse(user.last_seen) > 600000) {
        await env.DB.prepare("UPDATE devices SET last_seen = ?1 WHERE token_hash = ?2").bind(now, tokenHash).run();
      }
    }
  }
  if (!user) throw new HttpError(401, "missing or invalid bearer token");
  await rateLimit(env, "tok:" + tokenHash, intEnv(env, "RATE_LIMIT_PER_MIN", 120), 60);
  return user;
}

// Removes userId from groupId; transfers ownership or deletes the group as needed.
// Returns the list of statements to run (caller batches them).
async function leaveStatements(env, groupId, userId, role) {
  const db = env.DB;
  const stmts = [db.prepare("DELETE FROM memberships WHERE group_id = ?1 AND user_id = ?2").bind(groupId, userId)];
  if (role === "owner") {
    const next = await db.prepare(
      `SELECT user_id FROM memberships WHERE group_id = ?1 AND user_id != ?2
       ORDER BY joined_at ASC, rowid ASC LIMIT 1`
    ).bind(groupId, userId).first();
    if (next) {
      stmts.push(db.prepare("UPDATE memberships SET role = 'owner' WHERE group_id = ?1 AND user_id = ?2").bind(groupId, next.user_id));
    } else {
      stmts.push(db.prepare("DELETE FROM memberships WHERE group_id = ?1").bind(groupId));
      stmts.push(db.prepare("DELETE FROM groups WHERE id = ?1").bind(groupId));
    }
  } else {
    // A non-owner leaving can still empty a group only if it had no owner (should not happen); guard anyway.
    const left = await db.prepare("SELECT COUNT(*) AS n FROM memberships WHERE group_id = ?1 AND user_id != ?2").bind(groupId, userId).first();
    if (!left || left.n === 0) stmts.push(db.prepare("DELETE FROM groups WHERE id = ?1").bind(groupId));
  }
  return stmts;
}

async function membership(env, groupId, userId) {
  return env.DB.prepare("SELECT role FROM memberships WHERE group_id = ?1 AND user_id = ?2").bind(groupId, userId).first();
}

async function requireGroupMember(env, groupId, userId) {
  const g = await env.DB.prepare("SELECT id, name, invite_code FROM groups WHERE id = ?1").bind(groupId).first();
  if (!g) throw new HttpError(404, "group not found");
  const m = await membership(env, groupId, userId);
  if (!m) throw new HttpError(403, "not a member of this group");
  return { group: g, role: m.role };
}

// ---------- handlers ----------

async function register(request, env) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  await rateLimit(env, "reg:" + ip, intEnv(env, "REGISTER_LIMIT_PER_HOUR", 10), 3600);
  const body = await readJson(request);
  if (typeof body.handle !== "string") throw new HttpError(400, "handle is required");
  const handle = body.handle.trim().toLowerCase();
  if (!HANDLE_RE.test(handle)) throw new HttpError(400, "handle must be 3-20 characters of a-z, 0-9 or _");
  const displayName = validateDisplayName(body.display_name);

  const token = hex(crypto.getRandomValues(new Uint8Array(32)));
  const tokenHash = await sha256Hex(token);
  const userId = randomString(12, ID_ALPHABET);
  const now = Date.now();
  try {
    await env.DB.prepare(
      "INSERT INTO users (id, handle, display_name, token_hash, public, streak, created_at) VALUES (?1, ?2, ?3, ?4, 0, 0, ?5)"
    ).bind(userId, handle, displayName, tokenHash, now).run();
  } catch (e) {
    if (String(e && e.message).includes("UNIQUE") && String(e.message).includes("handle")) throw new HttpError(409, "handle already taken");
    throw e;
  }
  return json(201, { user_id: userId, handle, display_name: displayName, token });
}

async function getMe(env, user) {
  const { results } = await env.DB.prepare(
    `SELECT g.id AS group_id, g.name, m.role, g.invite_code,
            (SELECT COUNT(*) FROM memberships m2 WHERE m2.group_id = g.id) AS members
     FROM memberships m JOIN groups g ON g.id = m.group_id
     WHERE m.user_id = ?1 ORDER BY m.joined_at ASC`
  ).bind(user.id).all();
  return json(200, {
    user_id: user.id,
    handle: user.handle,
    display_name: user.display_name,
    public: user.public === 1,
    created_at: new Date(user.created_at).toISOString(),
    groups: results,
  });
}

async function patchMe(request, env, user) {
  const body = await readJson(request);
  const sets = [];
  const vals = [];
  if (body.display_name !== undefined) {
    sets.push(`display_name = ?${vals.length + 1}`);
    vals.push(validateDisplayName(body.display_name));
  }
  if (body.public !== undefined) {
    if (typeof body.public !== "boolean") throw new HttpError(400, "public must be a boolean");
    sets.push(`public = ?${vals.length + 1}`);
    vals.push(body.public ? 1 : 0);
  }
  if (sets.length === 0) throw new HttpError(400, "nothing to update (display_name and/or public)");
  vals.push(user.id);
  await env.DB.prepare(`UPDATE users SET ${sets.join(", ")} WHERE id = ?${vals.length}`).bind(...vals).run();
  const fresh = await env.DB.prepare("SELECT id, handle, display_name, public, streak, created_at FROM users WHERE id = ?1").bind(user.id).first();
  return getMe(env, fresh);
}

async function deleteMe(env, user) {
  const db = env.DB;
  const { results: mships } = await db.prepare("SELECT group_id, role FROM memberships WHERE user_id = ?1").bind(user.id).all();
  const stmts = [];
  for (const m of mships) stmts.push(...(await leaveStatements(env, m.group_id, user.id, m.role)));
  stmts.push(db.prepare("DELETE FROM memberships WHERE user_id = ?1").bind(user.id));
  stmts.push(db.prepare("DELETE FROM days WHERE user_id = ?1").bind(user.id));
  for (const t of ["devices", "pair_codes", "app_state", "app_commands", "health_acked", "health_days"]) {
    stmts.push(db.prepare(`DELETE FROM ${t} WHERE user_id = ?1`).bind(user.id));
  }
  stmts.push(db.prepare("DELETE FROM users WHERE id = ?1").bind(user.id));
  await db.batch(stmts);
  return json(200, { ok: true });
}

async function sync(request, env, user) {
  const body = await readJson(request);
  const days = body.days === undefined ? [] : body.days;
  if (!Array.isArray(days)) throw new HttpError(400, "days must be an array");
  if (days.length > MAX_SYNC_DAYS) throw new HttpError(400, `at most ${MAX_SYNC_DAYS} days per call`);
  const today = todayUtc();
  const minDate = addDays(today, -PAST_DAYS_ALLOWED);
  const maxDate = addDays(today, FUTURE_DAYS_ALLOWED);
  const rows = new Map(); // date -> row (last one wins on duplicates)
  days.forEach((d, i) => {
    const at = `days[${i}]`;
    if (!d || typeof d !== "object" || Array.isArray(d)) throw new HttpError(400, `${at} must be an object`);
    if (!isRealDate(d.date)) throw new HttpError(400, `${at}.date must be a valid YYYY-MM-DD date`);
    if (d.date < minDate || d.date > maxDate) throw new HttpError(400, `${at}.date must be between ${minDate} and ${maxDate} (UTC)`);
    if (!Number.isInteger(d.steps) || d.steps < 0 || d.steps > 150000) throw new HttpError(400, `${at}.steps must be an integer 0..150000`);
    if (typeof d.minutes !== "number" || !Number.isFinite(d.minutes) || d.minutes < 0 || d.minutes > 1440) throw new HttpError(400, `${at}.minutes must be a number 0..1440`);
    if (typeof d.km !== "number" || !Number.isFinite(d.km) || d.km < 0 || d.km > 200) throw new HttpError(400, `${at}.km must be a number 0..200`);
    if (typeof d.goal_met !== "boolean") throw new HttpError(400, `${at}.goal_met must be a boolean`);
    rows.set(d.date, d);
  });
  let streak = null;
  if (body.streak !== undefined) {
    if (!Number.isInteger(body.streak) || body.streak < 0 || body.streak > 10000) throw new HttpError(400, "streak must be an integer 0..10000");
    streak = body.streak;
  }
  const now = Date.now();
  const db = env.DB;
  const stmts = [];
  for (const d of rows.values()) {
    stmts.push(
      db.prepare(
        `INSERT INTO days (user_id, date, steps, minutes, km, goal_met, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
         ON CONFLICT (user_id, date) DO UPDATE SET steps = excluded.steps, minutes = excluded.minutes,
           km = excluded.km, goal_met = excluded.goal_met, updated_at = excluded.updated_at`
      ).bind(user.id, d.date, d.steps, d.minutes, d.km, d.goal_met ? 1 : 0, now)
    );
  }
  if (streak !== null) stmts.push(db.prepare("UPDATE users SET streak = ?1, last_sync_at = ?2 WHERE id = ?3").bind(streak, now, user.id));
  else stmts.push(db.prepare("UPDATE users SET last_sync_at = ?1 WHERE id = ?2").bind(now, user.id));
  await db.batch(stmts);
  return json(200, { saved: rows.size });
}

async function createGroup(request, env, user) {
  const body = await readJson(request);
  const name = validateGroupName(body.name);
  const owned = await env.DB.prepare("SELECT COUNT(*) AS n FROM memberships WHERE user_id = ?1 AND role = 'owner'").bind(user.id).first();
  if (owned.n >= MAX_OWNED_GROUPS) throw new HttpError(409, `you already own ${MAX_OWNED_GROUPS} groups (maximum)`);
  const groupId = randomString(12, ID_ALPHABET);
  const now = Date.now();
  for (let attempt = 0; attempt < 5; attempt++) {
    const code = randomString(8, INVITE_ALPHABET);
    try {
      await env.DB.batch([
        env.DB.prepare("INSERT INTO groups (id, name, invite_code, created_at) VALUES (?1, ?2, ?3, ?4)").bind(groupId, name, code, now),
        env.DB.prepare("INSERT INTO memberships (group_id, user_id, role, joined_at) VALUES (?1, ?2, 'owner', ?3)").bind(groupId, user.id, now),
      ]);
      return json(201, { group_id: groupId, name, invite_code: code });
    } catch (e) {
      if (!String(e && e.message).includes("invite_code")) throw e;
    }
  }
  throw new HttpError(503, "could not allocate an invite code, try again");
}

async function joinGroup(request, env, user) {
  const body = await readJson(request);
  if (typeof body.invite_code !== "string") throw new HttpError(400, "invite_code is required");
  const code = body.invite_code.trim().toUpperCase();
  if (!/^[A-Z0-9]{8}$/.test(code)) throw new HttpError(400, "invite_code must be 8 characters");
  const g = await env.DB.prepare("SELECT id, name FROM groups WHERE invite_code = ?1").bind(code).first();
  if (!g) throw new HttpError(404, "invalid invite code");
  if (await membership(env, g.id, user.id)) return json(200, { group_id: g.id, name: g.name });
  // Conditional insert so the cap holds even under concurrent joins.
  const res = await env.DB.prepare(
    `INSERT INTO memberships (group_id, user_id, role, joined_at)
     SELECT ?1, ?2, 'member', ?3
     WHERE (SELECT COUNT(*) FROM memberships WHERE group_id = ?1) < ?4
     ON CONFLICT (group_id, user_id) DO NOTHING`
  ).bind(g.id, user.id, Date.now(), MAX_GROUP_MEMBERS).run();
  if (res.meta.changes === 0 && !(await membership(env, g.id, user.id))) throw new HttpError(409, `group is full (${MAX_GROUP_MEMBERS} members)`);
  return json(200, { group_id: g.id, name: g.name });
}

async function leaveGroup(env, user, groupId) {
  const g = await env.DB.prepare("SELECT id FROM groups WHERE id = ?1").bind(groupId).first();
  if (!g) throw new HttpError(404, "group not found");
  const m = await membership(env, groupId, user.id);
  if (!m) throw new HttpError(403, "not a member of this group");
  await env.DB.batch(await leaveStatements(env, groupId, user.id, m.role));
  return json(200, { ok: true });
}

async function getGroup(env, user, groupId) {
  const { group } = await requireGroupMember(env, groupId, user.id);
  const { results } = await env.DB.prepare(
    `SELECT u.handle, u.display_name, m.role FROM memberships m JOIN users u ON u.id = m.user_id
     WHERE m.group_id = ?1 ORDER BY m.joined_at ASC, m.rowid ASC`
  ).bind(groupId).all();
  return json(200, { group_id: group.id, name: group.name, invite_code: group.invite_code, members: results });
}

async function leaderboard(url, env, user) {
  const p = url.searchParams;
  const scope = p.get("scope") || "global";
  const metric = p.get("metric") || "steps";
  if (!(metric in METRICS)) throw new HttpError(400, "metric must be one of steps|minutes|km|goal_days|streak");
  const to = p.get("to") || todayUtc();
  const from = p.get("from") || addDays(to, -6);
  if (!isRealDate(from) || !isRealDate(to)) throw new HttpError(400, "from/to must be valid YYYY-MM-DD dates");
  if (from > to) throw new HttpError(400, "from must be <= to");
  if (dayDiff(from, to) + 1 > MAX_RANGE_DAYS) throw new HttpError(400, `range must be at most ${MAX_RANGE_DAYS} days`);
  let limit = 50;
  if (p.has("limit")) {
    limit = Number(p.get("limit"));
    if (!Number.isInteger(limit) || limit < 1 || limit > 100) throw new HttpError(400, "limit must be an integer 1..100");
  }

  // Build the candidate set: global = public users + the caller; group = members.
  const cteBinds = [];
  let join = "";
  if (metric !== "streak") {
    join = "LEFT JOIN days d ON d.user_id = u.id AND d.date BETWEEN ? AND ?";
    cteBinds.push(from, to);
  }
  let filter;
  let ranked; // predicate (on the agg alias) for who is ranked in rows
  if (scope === "global") {
    filter = "(u.public = 1 OR u.id = ?)";
    cteBinds.push(user.id);
    ranked = (alias) => `${alias}.public = 1`;
  } else if (scope.startsWith("group:")) {
    const groupId = scope.slice(6);
    await requireGroupMember(env, groupId, user.id);
    filter = "u.id IN (SELECT user_id FROM memberships WHERE group_id = ?)";
    cteBinds.push(groupId);
    ranked = () => "1 = 1";
  } else {
    throw new HttpError(400, "scope must be global or group:<id>");
  }
  const cte = `WITH agg AS (
      SELECT u.id, u.handle, u.display_name, u.public, ${METRICS[metric]} AS value
      FROM users u ${join}
      WHERE ${filter}
      GROUP BY u.id
    )`;
  // Standard competition ranking ("1224"): ties share a rank, the next rank skips.
  const rowsStmt = env.DB.prepare(
    `${cte}
     SELECT a.id, a.handle, a.display_name, a.value, RANK() OVER (ORDER BY a.value DESC) AS rank
     FROM agg a WHERE ${ranked("a")}
     ORDER BY a.value DESC, a.handle ASC LIMIT ?`
  ).bind(...cteBinds, limit);
  // Caller's rank = 1 + number of ranked users (other than the caller) with a strictly higher value.
  const meStmt = env.DB.prepare(
    `${cte}
     SELECT a.value, 1 + (SELECT COUNT(*) FROM agg b WHERE ${ranked("b")} AND b.id != a.id AND b.value > a.value) AS rank
     FROM agg a WHERE a.id = ?`
  ).bind(...cteBinds, user.id);
  const [rowsRes, meRes] = await env.DB.batch([rowsStmt, meStmt]);
  const rows = rowsRes.results.map((r) => ({
    rank: r.rank,
    handle: r.handle,
    display_name: r.display_name,
    value: r.value,
    me: r.id === user.id,
  }));
  const meRow = meRes.results[0];
  return json(200, {
    scope,
    metric,
    from,
    to,
    rows,
    me: meRow ? { rank: meRow.rank, value: meRow.value } : null,
  });
}


// ---------- phone/web link ----------
// The PC (account token) pushes its full app state; paired devices (device tokens) read it and queue
// commands that the PC applies. Pairing: the PC asks for a 6-character code, the phone claims it.

function accountOnly(user) {
  if (user.scope !== "account") throw new HttpError(403, "only the PC can do this");
}

async function pairStart(env, user) {
  accountOnly(user);
  const code = randomString(6, PAIR_ALPHABET);
  const expires = Math.floor(Date.now() / 1000) + 600;
  await env.DB.batch([
    env.DB.prepare("DELETE FROM pair_codes WHERE user_id = ?1 OR expires_at < ?2").bind(user.id, Math.floor(Date.now() / 1000)),
    env.DB.prepare("INSERT INTO pair_codes (code, user_id, expires_at) VALUES (?1, ?2, ?3)").bind(code, user.id, expires),
  ]);
  return json(201, { code, expires_in: 600 });
}

async function pairClaim(request, env) {
  const ip = request.headers.get("CF-Connecting-IP") || "local";
  await rateLimit(env, "pair:" + ip, 20, 3600);
  const body = await readJson(request);
  const code = String(body.code || "").trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (code.length !== 6) throw new HttpError(400, "enter the 6-character code shown on your PC");
  const label = String(body.label || "Phone").trim().slice(0, 40) || "Phone";
  if (BAD_NAME_CHARS.test(label)) throw new HttpError(400, "invalid device name");
  const row = await env.DB.prepare("SELECT user_id, expires_at FROM pair_codes WHERE code = ?1").bind(code).first();
  if (!row || row.expires_at < Math.floor(Date.now() / 1000)) throw new HttpError(404, "that code is wrong or has expired");
  const token = hex(crypto.getRandomValues(new Uint8Array(32)));
  const now = new Date().toISOString();
  await env.DB.batch([
    env.DB.prepare("DELETE FROM pair_codes WHERE code = ?1").bind(code),
    env.DB.prepare("INSERT INTO devices (token_hash, user_id, label, created_at, last_seen) VALUES (?1, ?2, ?3, ?4, ?4)")
      .bind(await sha256Hex(token), row.user_id, label, now),
  ]);
  const u = await env.DB.prepare("SELECT handle, display_name FROM users WHERE id = ?1").bind(row.user_id).first();
  return json(201, { token, handle: u.handle, display_name: u.display_name });
}

async function listDevices(env, user) {
  accountOnly(user);
  const { results } = await env.DB.prepare(
    "SELECT substr(token_hash, 1, 12) AS id, label, created_at, last_seen FROM devices WHERE user_id = ?1 ORDER BY created_at"
  ).bind(user.id).all();
  return json(200, { devices: results });
}

async function revokeDevices(request, env, user) {
  accountOnly(user);
  const body = await readJson(request);
  if (body.id) {
    await env.DB.prepare("DELETE FROM devices WHERE user_id = ?1 AND substr(token_hash, 1, 12) = ?2").bind(user.id, String(body.id)).run();
  } else {
    await env.DB.prepare("DELETE FROM devices WHERE user_id = ?1").bind(user.id).run();
  }
  return json(200, { ok: true });
}

async function putState(request, env, user) {
  accountOnly(user);
  const body = await readJson(request, MAX_STATE_BYTES);
  if (!body.state || typeof body.state !== "object") throw new HttpError(400, "state must be an object");
  const now = new Date().toISOString();
  await env.DB.prepare(
    `INSERT INTO app_state (user_id, state, updated_at) VALUES (?1, ?2, ?3)
     ON CONFLICT (user_id) DO UPDATE SET state = excluded.state, updated_at = excluded.updated_at`
  ).bind(user.id, JSON.stringify(body.state), now).run();
  const pending = await env.DB.prepare("SELECT COUNT(*) AS n FROM app_commands WHERE user_id = ?1").bind(user.id).first();
  const devices = await env.DB.prepare("SELECT COUNT(*) AS n FROM devices WHERE user_id = ?1").bind(user.id).first();
  return json(200, { saved: true, pending_commands: pending.n, devices: devices.n });
}

async function getState(env, user) {
  const row = await env.DB.prepare("SELECT state, updated_at FROM app_state WHERE user_id = ?1").bind(user.id).first();
  if (!row) return json(200, { state: null, updated_at: null });
  return json(200, { state: JSON.parse(row.state), updated_at: row.updated_at });
}

const COMMAND_KINDS = { settings: 1, track: 1, pad: 1 };
async function queueCommand(request, env, user) {
  const body = await readJson(request);
  const kind = String(body.kind || "");
  if (!COMMAND_KINDS[kind]) throw new HttpError(400, "kind must be settings, track or pad");
  if (!body.payload || typeof body.payload !== "object" || Array.isArray(body.payload)) throw new HttpError(400, "payload must be an object");
  if (kind === "pad" && !["start", "pause", "stop", "speed"].includes(body.payload.action)) throw new HttpError(400, "unknown pad action");
  const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM app_commands WHERE user_id = ?1").bind(user.id).first();
  if (n.n >= MAX_PENDING_COMMANDS) throw new HttpError(409, "your PC hasn't picked up earlier changes yet; is it on?");
  await env.DB.prepare("INSERT INTO app_commands (user_id, kind, payload, created_at) VALUES (?1, ?2, ?3, ?4)")
    .bind(user.id, kind, JSON.stringify(body.payload), new Date().toISOString()).run();
  return json(202, { queued: true });
}

async function takeCommands(env, user) {
  accountOnly(user);
  const { results } = await env.DB.prepare(
    "SELECT id, kind, payload, created_at FROM app_commands WHERE user_id = ?1 ORDER BY id LIMIT 50"
  ).bind(user.id).all();
  if (results.length) {
    await env.DB.prepare("DELETE FROM app_commands WHERE user_id = ?1 AND id <= ?2").bind(user.id, results[results.length - 1].id).run();
  }
  return json(200, { commands: results.map((r) => ({ id: r.id, kind: r.kind, payload: JSON.parse(r.payload), created_at: r.created_at })) });
}

// ---------- Apple Health via iOS Shortcuts ----------
// export: pad walks (from the PC's latest state) not yet written to Health; ack marks them done.
// import: all-day steps read from Health; stored and forwarded to the PC as a command.

async function healthExport(env, user) {
  const row = await env.DB.prepare("SELECT state FROM app_state WHERE user_id = ?1").bind(user.id).first();
  const walks = row ? (JSON.parse(row.state).healthExport || []) : [];
  const { results } = await env.DB.prepare("SELECT walk_id FROM health_acked WHERE user_id = ?1").bind(user.id).all();
  const done = new Set(results.map((r) => r.walk_id));
  const items = walks.filter((w) => !done.has(String(w.id))).slice(0, 30);
  return json(200, { count: items.length, items, ids: items.map((w) => String(w.id)).join(",") });
}

async function healthAck(request, env, user) {
  const body = await readJson(request);
  let ids = body.ids;
  if (typeof ids === "string") ids = ids.split(",");
  if (!Array.isArray(ids)) throw new HttpError(400, "ids must be a list or a comma-separated string");
  ids = ids.map((x) => String(x).trim()).filter((x) => /^[0-9]{1,12}$/.test(x)).slice(0, 100);
  const now = new Date().toISOString();
  if (ids.length) {
    await env.DB.batch(ids.map((id) => env.DB.prepare(
      "INSERT OR IGNORE INTO health_acked (user_id, walk_id, acked_at) VALUES (?1, ?2, ?3)").bind(user.id, id, now)));
  }
  return json(200, { acked: ids.length });
}

async function healthImport(request, env, user) {
  const body = await readJson(request);
  const date = String(body.date || "").slice(0, 10);
  if (!isRealDate(date)) throw new HttpError(400, "date must be YYYY-MM-DD");
  const steps = Math.round(Number(String(body.steps).replace(/[^0-9.]/g, "")));
  if (!Number.isFinite(steps) || steps < 0 || steps > 150000) throw new HttpError(400, "steps must be 0..150000");
  const kmRaw = body.km === undefined || body.km === "" ? null : Number(String(body.km).replace(/[^0-9.]/g, ""));
  const km = kmRaw !== null && Number.isFinite(kmRaw) && kmRaw >= 0 && kmRaw <= 300 ? Math.round(kmRaw * 100) / 100 : null;
  const now = new Date().toISOString();
  await env.DB.batch([
    env.DB.prepare(`INSERT INTO health_days (user_id, date, steps, km, updated_at) VALUES (?1, ?2, ?3, ?4, ?5)
                    ON CONFLICT (user_id, date) DO UPDATE SET steps = excluded.steps, km = excluded.km, updated_at = excluded.updated_at`)
      .bind(user.id, date, steps, km, now),
    env.DB.prepare("INSERT INTO app_commands (user_id, kind, payload, created_at) VALUES (?1, 'health', ?2, ?3)")
      .bind(user.id, JSON.stringify({ date, steps, km }), now),
  ]);
  return json(200, { saved: true, date, steps });
}

// ---------- CORS + router ----------

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin");
  const headers = { Vary: "Origin" };
  if (!origin) return headers;
  const allowed = String(env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (allowed.includes(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS";
    headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type";
    headers["Access-Control-Max-Age"] = "86400";
  }
  return headers;
}

async function route(request, env, url) {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = request.method;
  const notAllowed = () => { throw new HttpError(405, "method not allowed"); };

  if (path === "/v1/health") return method === "GET" ? json(200, { ok: true }) : notAllowed();
  if (path === "/v1/register") return method === "POST" ? register(request, env) : notAllowed();
  if (path === "/v1/pair/claim") return method === "POST" ? pairClaim(request, env) : notAllowed();

  const routes = [
    [/^\/v1\/me$/, { GET: (u) => getMe(env, u), PATCH: (u) => patchMe(request, env, u), DELETE: (u) => { accountOnly(u); return deleteMe(env, u); } }],
    [/^\/v1\/sync$/, { POST: (u) => { accountOnly(u); return sync(request, env, u); } }],
    [/^\/v1\/groups$/, { POST: (u) => createGroup(request, env, u) }],
    [/^\/v1\/groups\/join$/, { POST: (u) => joinGroup(request, env, u) }],
    [/^\/v1\/groups\/([a-z0-9]{1,32})\/leave$/, { POST: (u, m) => leaveGroup(env, u, m[1]) }],
    [/^\/v1\/groups\/([a-z0-9]{1,32})$/, { GET: (u, m) => getGroup(env, u, m[1]) }],
    [/^\/v1\/leaderboard$/, { GET: (u) => leaderboard(url, env, u) }],
    [/^\/v1\/pair\/start$/, { POST: (u) => pairStart(env, u) }],
    [/^\/v1\/devices$/, { GET: (u) => listDevices(env, u) }],
    [/^\/v1\/devices\/revoke$/, { POST: (u) => revokeDevices(request, env, u) }],
    [/^\/v1\/app\/state$/, { GET: (u) => getState(env, u), POST: (u) => putState(request, env, u) }],
    [/^\/v1\/app\/commands$/, { GET: (u) => takeCommands(env, u), POST: (u) => queueCommand(request, env, u) }],
    [/^\/v1\/health\/export$/, { GET: (u) => healthExport(env, u) }],
    [/^\/v1\/health\/ack$/, { POST: (u) => healthAck(request, env, u) }],
    [/^\/v1\/health\/import$/, { POST: (u) => healthImport(request, env, u) }],
  ];
  for (const [re, handlers] of routes) {
    const m = re.exec(path);
    if (!m) continue;
    const h = handlers[method];
    if (!h) notAllowed();
    const user = await authenticate(request, env);
    return h(user, m);
  }
  if (!path.startsWith("/v1") && env.ASSETS) return env.ASSETS.fetch(request);
  throw new HttpError(404, "not found");
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    let res;
    try {
      res = await route(request, env, new URL(request.url));
    } catch (e) {
      if (e instanceof HttpError) res = json(e.status, { error: e.message }, e.headers);
      else {
        console.error("unhandled error", e && e.stack ? e.stack : e);
        res = json(500, { error: "internal error" });
      }
    }
    for (const [k, v] of Object.entries(cors)) res.headers.set(k, v);
    return res;
  },
};
