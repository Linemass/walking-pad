// End-to-end tests for the Walking Pad Community API.
// Spawns two local `wrangler dev --local` instances, each with its own fresh D1 state:
//   - main (port 8787): generous rate limits, CORS allow-list set
//   - limited (port 8788): tiny rate limits, for 429 tests
// Run with: npm test   (node --test test/)
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync, execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const IS_WIN = process.platform === "win32";
const ORIGIN_OK = "https://app.example";
const ORIGIN_OK2 = "https://pad.example";
const ORIGIN_BAD = "https://evil.example";
const LIMITED = { perMin: 5, regPerHour: 3 };

const servers = [];

// Run npx without a shell (avoids Windows .cmd shims and argument concatenation).
const NPX_CLI = path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npx-cli.js");
const npx = (args) => (IS_WIN && fs.existsSync(NPX_CLI) ? [process.execPath, [NPX_CLI, ...args]] : ["npx", args]);

function run(args, opts = {}) {
  const [cmd, argv] = npx(args);
  const r = spawnSync(cmd, argv, { cwd: ROOT, encoding: "utf8", env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, ...opts });
  if (r.status !== 0) throw new Error(`npx ${args.join(" ")} failed (${r.status}):\n${r.stdout}\n${r.stderr}`);
  return r.stdout;
}

async function startServer({ port, inspectorPort, name, vars }) {
  const busy = await fetch(`http://127.0.0.1:${port}/`).then(() => true, () => false);
  if (busy) throw new Error(`port ${port} is already in use (stop any running "npm run dev" first)`);
  const persist = path.join(ROOT, ".wrangler", `test-${name}`);
  fs.rmSync(persist, { recursive: true, force: true });
  fs.mkdirSync(persist, { recursive: true });
  const envFile = path.join(persist, "test.env");
  fs.writeFileSync(envFile, Object.entries(vars).map(([k, v]) => `${k}=${v}`).join("\n") + "\n");
  run(["wrangler", "d1", "migrations", "apply", "DB", "--local", "--persist-to", persist]);
  const [cmd, argv] = npx(
    ["wrangler", "dev", "--local", "--port", String(port), "--inspector-port", String(inspectorPort),
      "--persist-to", persist, "--env-file", envFile, "--show-interactive-dev-session=false"]);
  const child = spawn(cmd, argv,
    { cwd: ROOT, env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: ["ignore", "pipe", "pipe"] }
  );
  let log = "";
  child.stdout.on("data", (d) => (log += d));
  child.stderr.on("data", (d) => (log += d));
  servers.push(child);
  const base = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`wrangler dev (${name}) exited early:\n${log}`);
    try {
      const r = await fetch(base + "/v1/health");
      if (r.ok) return base;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`wrangler dev (${name}) did not become healthy:\n${log}`);
}

function killTree(child) {
  if (child.exitCode !== null) return;
  try {
    if (IS_WIN) execSync(`taskkill /pid ${child.pid} /T /F`, { stdio: "ignore" });
    else child.kill("SIGTERM");
  } catch {}
}

let BASE, LBASE;

before(async () => {
  [BASE, LBASE] = await Promise.all([
    startServer({
      port: 8787, inspectorPort: 9301, name: "main",
      vars: { ALLOWED_ORIGINS: `${ORIGIN_OK},${ORIGIN_OK2}`, RATE_LIMIT_PER_MIN: "100000", REGISTER_LIMIT_PER_HOUR: "100000" },
    }),
    startServer({
      port: 8788, inspectorPort: 9302, name: "limited",
      vars: { ALLOWED_ORIGINS: "", RATE_LIMIT_PER_MIN: String(LIMITED.perMin), REGISTER_LIMIT_PER_HOUR: String(LIMITED.regPerHour) },
    }),
  ]);
}, { timeout: 180_000 });

after(() => {
  for (const s of servers) killTree(s);
});

// ---------- helpers ----------

async function api(method, p, { token, body, raw, headers = {}, base = BASE } = {}) {
  const h = { ...headers };
  if (token) h.Authorization = `Bearer ${token}`;
  let payload;
  if (raw !== undefined) payload = raw;
  else if (body !== undefined) {
    payload = JSON.stringify(body);
    h["Content-Type"] = "application/json";
  }
  const res = await fetch(base + p, { method, headers: h, body: payload });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  return { status: res.status, data, headers: res.headers };
}

function utcDate(offsetDays = 0) {
  return new Date(Date.now() + offsetDays * 86400000).toISOString().slice(0, 10);
}

const D = (i) => utcDate(-i); // D(0)=today, D(1)=yesterday...
const FROM = D(6);
const TO = D(0);
const day = (i, steps, goal = false, minutes = 30, km = 2.5) => ({ date: D(i), steps, minutes, km, goal_met: goal });

const U = {}; // handle -> {token, user_id}

function lb(token, q) {
  return api("GET", "/v1/leaderboard?" + new URLSearchParams(q).toString(), { token });
}

// ---------- tests ----------

test("health", async () => {
  const r = await api("GET", "/v1/health");
  assert.equal(r.status, 200);
  assert.deepEqual(r.data, { ok: true });
});

test("register 4 users", async () => {
  for (const [handle, name] of [["alice", "Alice A"], ["bob", "  Bob B  "], ["carol", "Carol C"], ["dave", "Dave D"]]) {
    const r = await api("POST", "/v1/register", { body: { handle, display_name: name } });
    assert.equal(r.status, 201, JSON.stringify(r.data));
    assert.equal(r.data.handle, handle);
    assert.equal(r.data.display_name, name.trim());
    assert.match(r.data.token, /^[0-9a-f]{64}$/);
    assert.match(r.data.user_id, /^[a-z0-9]{12}$/);
    U[handle] = r.data;
  }
  const me = await api("GET", "/v1/me", { token: U.bob.token });
  assert.equal(me.status, 200);
  assert.equal(me.data.handle, "bob");
  assert.equal(me.data.display_name, "Bob B");
  assert.equal(me.data.public, false);
  assert.deepEqual(me.data.groups, []);
  assert.ok(!Number.isNaN(Date.parse(me.data.created_at)));
});

test("register validation", async () => {
  const bad = [
    [{ handle: "ab", display_name: "x" }, 400],
    [{ handle: "bad-handle!", display_name: "x" }, 400],
    [{ handle: "a".repeat(21), display_name: "x" }, 400],
    [{ display_name: "x" }, 400],
    [{ handle: "erin", display_name: "   " }, 400],
    [{ handle: "erin", display_name: "x".repeat(41) }, 400],
    [{ handle: "erin", display_name: "bad\u0007name" }, 400],
    [{ handle: "erin", display_name: 42 }, 400],
    [{ handle: "alice", display_name: "Imposter" }, 409],
    [{ handle: "ALICE", display_name: "Imposter" }, 409], // handles are case-insensitive (lower-cased)
  ];
  for (const [body, code] of bad) {
    const r = await api("POST", "/v1/register", { body });
    assert.equal(r.status, code, `${JSON.stringify(body)} -> ${r.status} ${JSON.stringify(r.data)}`);
    assert.equal(typeof r.data.error, "string");
  }
  const badJson = await api("POST", "/v1/register", { raw: "{not json", headers: { "Content-Type": "application/json" } });
  assert.equal(badJson.status, 400);
  const big = await api("POST", "/v1/register", { raw: JSON.stringify({ handle: "big", display_name: "x".repeat(70000) }), headers: { "Content-Type": "application/json" } });
  assert.equal(big.status, 413);
});

test("auth required", async () => {
  for (const [m, p] of [["GET", "/v1/me"], ["POST", "/v1/sync"], ["POST", "/v1/groups"], ["GET", "/v1/leaderboard"], ["DELETE", "/v1/me"]]) {
    const r = await api(m, p);
    assert.equal(r.status, 401, `${m} ${p}`);
  }
  const wrong = await api("GET", "/v1/me", { token: "0".repeat(64) });
  assert.equal(wrong.status, 401);
  const malformed = await api("GET", "/v1/me", { headers: { Authorization: "Bearer nope" } });
  assert.equal(malformed.status, 401);
  const notFound = await api("GET", "/v1/nope");
  assert.equal(notFound.status, 404);
  const wrongMethod = await api("PUT", "/v1/me", { token: U.alice.token });
  assert.equal(wrongMethod.status, 405);
});

test("sync valid data", async () => {
  // alice: 7 x 5000 = 35000, goal 7 days, streak 7
  let r = await api("POST", "/v1/sync", { token: U.alice.token, body: { days: [0, 1, 2, 3, 4, 5, 6].map((i) => day(i, 5000, true, 40.25, 3.333)), streak: 7 } });
  assert.equal(r.status, 200, JSON.stringify(r.data));
  assert.deepEqual(r.data, { saved: 7 });
  // bob: 5 x 7000 = 35000 (ties alice), goal 3, streak 3; first sync wrong, then upsert corrects it
  r = await api("POST", "/v1/sync", { token: U.bob.token, body: { days: [0, 1, 2, 3, 4].map((i) => day(i, 1000)), streak: 1 } });
  assert.equal(r.status, 200);
  r = await api("POST", "/v1/sync", { token: U.bob.token, body: { days: [0, 1, 2, 3, 4].map((i) => day(i, 7000, i < 3, 60, 5)), streak: 3 } });
  assert.deepEqual(r.data, { saved: 5 });
  // carol: 2 x 10000 = 20000, goal 2, streak 12 (+ an old day outside the range that must not count)
  r = await api("POST", "/v1/sync", { token: U.carol.token, body: { days: [day(0, 10000, true), day(1, 10000, true), day(20, 99999, true)], streak: 12 } });
  assert.deepEqual(r.data, { saved: 3 });
  // dave (stays private): 1 x 50000, goal 1, streak 1
  r = await api("POST", "/v1/sync", { token: U.dave.token, body: { days: [day(2, 50000, true)], streak: 1 } });
  assert.deepEqual(r.data, { saved: 1 });
  // boundaries accepted: tomorrow and exactly 400 days ago
  r = await api("POST", "/v1/sync", { token: U.dave.token, body: { days: [{ ...day(0, 0), date: utcDate(1) }, { ...day(0, 0), date: utcDate(-400) }] } });
  assert.equal(r.status, 200, JSON.stringify(r.data));
  assert.equal(r.data.saved, 2);
});

test("sync validation", async () => {
  const t = U.alice.token;
  const cases = [
    { days: [{ ...day(0, 1), date: "2026-02-30" }] },
    { days: [{ ...day(0, 1), date: "06/11/2026" }] },
    { days: [{ ...day(0, 1), date: utcDate(2) }] },
    { days: [{ ...day(0, 1), date: utcDate(-401) }] },
    { days: [day(0, 150001)] },
    { days: [day(0, -1)] },
    { days: [day(0, 1.5)] },
    { days: [day(0, 100, false, 1441)] },
    { days: [day(0, 100, false, 30, 200.01)] },
    { days: [day(0, 100, false, 30, -1)] },
    { days: [{ ...day(0, 1), goal_met: "yes" }] },
    { days: [{ date: D(0), steps: 1 }] },
    { days: Array.from({ length: 63 }, (_, i) => day(i, 1)) },
    { days: "nope" },
    { days: [], streak: 10001 },
    { days: [], streak: -1 },
  ];
  for (const body of cases) {
    const r = await api("POST", "/v1/sync", { token: t, body });
    assert.equal(r.status, 400, `${JSON.stringify(body).slice(0, 120)} -> ${r.status}`);
    assert.equal(typeof r.data.error, "string");
  }
  // 62 days is fine (re-asserting alice's values for the last 7 days so totals are unchanged)
  const days = Array.from({ length: 62 }, (_, i) => (i < 7 ? day(i, 5000, true, 40.25, 3.333) : day(i, 0)));
  const ok = await api("POST", "/v1/sync", { token: t, body: { days, streak: 7 } });
  assert.equal(ok.status, 200);
  assert.equal(ok.data.saved, 62);
});

test("profile: PATCH /v1/me", async () => {
  for (const h of ["alice", "bob", "carol"]) {
    const r = await api("PATCH", "/v1/me", { token: U[h].token, body: { public: true } });
    assert.equal(r.status, 200);
    assert.equal(r.data.public, true);
  }
  const r = await api("PATCH", "/v1/me", { token: U.carol.token, body: { display_name: " Carol the Walker " } });
  assert.equal(r.data.display_name, "Carol the Walker");
  assert.equal((await api("PATCH", "/v1/me", { token: U.carol.token, body: {} })).status, 400);
  assert.equal((await api("PATCH", "/v1/me", { token: U.carol.token, body: { public: "yes" } })).status, 400);
  assert.equal((await api("PATCH", "/v1/me", { token: U.carol.token, body: { display_name: "" } })).status, 400);
});

let G; // {group_id, name, invite_code}

test("groups: create, join (case-insensitive), outsider 403", async () => {
  const c = await api("POST", "/v1/groups", { token: U.alice.token, body: { name: "Office Walkers" } });
  assert.equal(c.status, 201, JSON.stringify(c.data));
  assert.equal(c.data.name, "Office Walkers");
  assert.match(c.data.invite_code, /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$/);
  G = c.data;
  assert.equal((await api("POST", "/v1/groups", { token: U.alice.token, body: { name: "" } })).status, 400);
  assert.equal((await api("POST", "/v1/groups", { token: U.alice.token, body: { name: "x".repeat(41) } })).status, 400);

  const j = await api("POST", "/v1/groups/join", { token: U.bob.token, body: { invite_code: G.invite_code.toLowerCase() } });
  assert.equal(j.status, 200, JSON.stringify(j.data));
  assert.deepEqual(j.data, { group_id: G.group_id, name: G.name });
  const again = await api("POST", "/v1/groups/join", { token: U.bob.token, body: { invite_code: G.invite_code } });
  assert.equal(again.status, 200); // idempotent
  assert.equal((await api("POST", "/v1/groups/join", { token: U.dave.token, body: { invite_code: ` ${G.invite_code} ` } })).status, 200);
  assert.equal((await api("POST", "/v1/groups/join", { token: U.dave.token, body: { invite_code: "ZZZZZZZZ" } })).status, 404);
  assert.equal((await api("POST", "/v1/groups/join", { token: U.dave.token, body: {} })).status, 400);

  const g = await api("GET", `/v1/groups/${G.group_id}`, { token: U.bob.token });
  assert.equal(g.status, 200);
  assert.equal(g.data.invite_code, G.invite_code);
  assert.deepEqual(g.data.members, [
    { handle: "alice", display_name: "Alice A", role: "owner" },
    { handle: "bob", display_name: "Bob B", role: "member" },
    { handle: "dave", display_name: "Dave D", role: "member" },
  ]);
  const outsider = await api("GET", `/v1/groups/${G.group_id}`, { token: U.carol.token });
  assert.equal(outsider.status, 403);
  assert.equal((await lb(U.carol.token, { scope: `group:${G.group_id}`, metric: "steps", from: FROM, to: TO })).status, 403);
  assert.equal((await api("GET", "/v1/groups/doesnotexist", { token: U.carol.token })).status, 404);

  const me = await api("GET", "/v1/me", { token: U.alice.token });
  assert.deepEqual(me.data.groups, [{ group_id: G.group_id, name: "Office Walkers", role: "owner", invite_code: G.invite_code, members: 3 }]);
});

test("leaderboard: global steps, ties, public vs private, me row", async () => {
  const q = { scope: "global", metric: "steps", from: FROM, to: TO };
  const a = await lb(U.alice.token, q);
  assert.equal(a.status, 200, JSON.stringify(a.data));
  assert.equal(a.data.scope, "global");
  assert.equal(a.data.metric, "steps");
  assert.equal(a.data.from, FROM);
  assert.equal(a.data.to, TO);
  assert.deepEqual(a.data.rows.map((r) => [r.rank, r.handle, r.value, r.me]), [
    [1, "alice", 35000, true],
    [1, "bob", 35000, false],
    [3, "carol", 20000, false], // standard competition ranking: 1,1,3
  ]);
  assert.deepEqual(a.data.me, { rank: 1, value: 35000 });
  // dave is private: absent from rows, but still gets his own rank among public users
  const d = await lb(U.dave.token, q);
  assert.ok(!d.data.rows.some((r) => r.handle === "dave"));
  assert.ok(d.data.rows.every((r) => r.me === false));
  assert.deepEqual(d.data.me, { rank: 1, value: 50000 });
  const c = await lb(U.carol.token, q);
  assert.deepEqual(c.data.me, { rank: 3, value: 20000 });
  // limit
  const l = await lb(U.carol.token, { ...q, limit: 1 });
  assert.equal(l.data.rows.length, 1);
  assert.deepEqual(l.data.me, { rank: 3, value: 20000 });
  // default range (last 7 days) gives the same result
  const def = await lb(U.alice.token, { scope: "global", metric: "steps" });
  assert.deepEqual(def.data.rows, a.data.rows);
});

test("leaderboard: minutes, km, goal_days, streak", async () => {
  const base = { scope: "global", from: FROM, to: TO };
  const m = await lb(U.alice.token, { ...base, metric: "minutes" });
  assert.deepEqual(m.data.rows.map((r) => [r.rank, r.handle, r.value]), [[1, "bob", 300], [2, "alice", 281.8], [3, "carol", 60]]);
  const k = await lb(U.alice.token, { ...base, metric: "km" });
  assert.deepEqual(k.data.rows.map((r) => [r.rank, r.handle, r.value]), [[1, "bob", 25], [2, "alice", 23.33], [3, "carol", 5]]);
  const g = await lb(U.alice.token, { ...base, metric: "goal_days" });
  assert.deepEqual(g.data.rows.map((r) => [r.rank, r.handle, r.value]), [[1, "alice", 7], [2, "bob", 3], [3, "carol", 2]]);
  const gd = await lb(U.dave.token, { ...base, metric: "goal_days" });
  assert.deepEqual(gd.data.me, { rank: 4, value: 1 });
  // streak ignores the range: even a range with no data returns stored streaks
  const s = await lb(U.alice.token, { scope: "global", metric: "streak", from: "2026-01-01", to: "2026-01-05" });
  assert.equal(s.status, 200);
  assert.deepEqual(s.data.rows.map((r) => [r.rank, r.handle, r.value]), [[1, "carol", 12], [2, "alice", 7], [3, "bob", 3]]);
  // narrower range: only today
  const t = await lb(U.alice.token, { scope: "global", metric: "steps", from: TO, to: TO });
  assert.deepEqual(t.data.rows.map((r) => [r.rank, r.handle, r.value]), [[1, "carol", 10000], [2, "bob", 7000], [3, "alice", 5000]]);
});

test("leaderboard: validation", async () => {
  const t = U.alice.token;
  assert.equal((await lb(t, { scope: "global", metric: "calories", from: FROM, to: TO })).status, 400);
  assert.equal((await lb(t, { scope: "planet", metric: "steps", from: FROM, to: TO })).status, 400);
  assert.equal((await lb(t, { scope: "global", metric: "steps", from: TO, to: FROM })).status, 400);
  assert.equal((await lb(t, { scope: "global", metric: "steps", from: utcDate(-31), to: TO })).status, 400); // 32 days
  assert.equal((await lb(t, { scope: "global", metric: "steps", from: utcDate(-30), to: TO })).status, 200); // 31 days
  assert.equal((await lb(t, { scope: "global", metric: "steps", from: "2026-13-01", to: TO })).status, 400);
  assert.equal((await lb(t, { scope: "global", metric: "steps", limit: "0" })).status, 400);
});

test("leaderboard: group scope", async () => {
  const q = { scope: `group:${G.group_id}`, metric: "steps", from: FROM, to: TO };
  const d = await lb(U.dave.token, q);
  assert.equal(d.status, 200, JSON.stringify(d.data));
  // group members are ranked regardless of public flag (dave is private but a member)
  assert.deepEqual(d.data.rows.map((r) => [r.rank, r.handle, r.value, r.me]), [
    [1, "dave", 50000, true],
    [2, "alice", 35000, false],
    [2, "bob", 35000, false],
  ]);
  assert.deepEqual(d.data.me, { rank: 1, value: 50000 });
  const b = await lb(U.bob.token, q);
  assert.deepEqual(b.data.me, { rank: 2, value: 35000 });
  assert.ok(!b.data.rows.some((r) => r.handle === "carol"));
  const s = await lb(U.bob.token, { ...q, metric: "streak" });
  assert.deepEqual(s.data.rows.map((r) => [r.rank, r.handle, r.value]), [[1, "alice", 7], [2, "bob", 3], [3, "dave", 1]]);
});

test("groups: leave and ownership transfer", async () => {
  // carol joins late; alice (owner) leaves -> bob (earliest remaining) becomes owner
  assert.equal((await api("POST", "/v1/groups/join", { token: U.carol.token, body: { invite_code: G.invite_code } })).status, 200);
  const l = await api("POST", `/v1/groups/${G.group_id}/leave`, { token: U.alice.token });
  assert.equal(l.status, 200);
  assert.deepEqual(l.data, { ok: true });
  assert.equal((await api("GET", `/v1/groups/${G.group_id}`, { token: U.alice.token })).status, 403);
  assert.equal((await api("POST", `/v1/groups/${G.group_id}/leave`, { token: U.alice.token })).status, 403);
  const g = await api("GET", `/v1/groups/${G.group_id}`, { token: U.carol.token });
  assert.deepEqual(g.data.members.map((m) => [m.handle, m.role]), [["bob", "owner"], ["dave", "member"], ["carol", "member"]]);

  // a solo group is deleted when its owner leaves
  const solo = await api("POST", "/v1/groups", { token: U.alice.token, body: { name: "Solo" } });
  assert.equal((await api("POST", `/v1/groups/${solo.data.group_id}/leave`, { token: U.alice.token })).status, 200);
  assert.equal((await api("GET", `/v1/groups/${solo.data.group_id}`, { token: U.alice.token })).status, 404);
  assert.equal((await api("POST", "/v1/groups/join", { token: U.bob.token, body: { invite_code: solo.data.invite_code } })).status, 404);
});

test("groups: owned-group cap (20)", async () => {
  const t = U.alice.token;
  for (let i = 0; i < 20; i++) {
    const r = await api("POST", "/v1/groups", { token: t, body: { name: `Cap ${i}` } });
    assert.equal(r.status, 201, `group ${i}: ${JSON.stringify(r.data)}`);
  }
  const over = await api("POST", "/v1/groups", { token: t, body: { name: "One too many" } });
  assert.equal(over.status, 409);
  const me = await api("GET", "/v1/me", { token: t });
  assert.equal(me.data.groups.filter((g) => g.role === "owner").length, 20);
});

test("DELETE /v1/me cleanup and ownership transfer", async () => {
  // dave (member, private) deletes himself
  let r = await api("DELETE", "/v1/me", { token: U.dave.token });
  assert.equal(r.status, 200);
  assert.equal((await api("GET", "/v1/me", { token: U.dave.token })).status, 401);
  let g = await api("GET", `/v1/groups/${G.group_id}`, { token: U.bob.token });
  assert.deepEqual(g.data.members.map((m) => [m.handle, m.role]), [["bob", "owner"], ["carol", "member"]]);
  const grp = await lb(U.bob.token, { scope: `group:${G.group_id}`, metric: "steps", from: FROM, to: TO });
  assert.ok(!grp.data.rows.some((x) => x.handle === "dave"));

  // bob (owner, with another member) deletes -> carol becomes owner
  r = await api("DELETE", "/v1/me", { token: U.bob.token });
  assert.equal(r.status, 200);
  g = await api("GET", `/v1/groups/${G.group_id}`, { token: U.carol.token });
  assert.deepEqual(g.data.members.map((m) => [m.handle, m.role]), [["carol", "owner"]]);
  const glob = await lb(U.alice.token, { scope: "global", metric: "steps", from: FROM, to: TO });
  assert.deepEqual(glob.data.rows.map((x) => x.handle), ["alice", "carol"]);

  // carol (sole owner) deletes -> group gone; handle becomes available again
  r = await api("DELETE", "/v1/me", { token: U.carol.token });
  assert.equal(r.status, 200);
  assert.equal((await api("POST", "/v1/groups/join", { token: U.alice.token, body: { invite_code: G.invite_code } })).status, 404);
  const again = await api("POST", "/v1/register", { body: { handle: "carol", display_name: "New Carol" } });
  assert.equal(again.status, 201);
  const fresh = await lb(again.data.token, { scope: "global", metric: "steps", from: FROM, to: TO });
  assert.deepEqual(fresh.data.me, { rank: 2, value: 0 }); // no data carried over
});

test("groups: member cap (50) -> 409 when full", async () => {
  const owner = await api("POST", "/v1/register", { body: { handle: "cap_owner", display_name: "Cap Owner" } });
  const grp = await api("POST", "/v1/groups", { token: owner.data.token, body: { name: "Big Group" } });
  for (let i = 0; i < 50; i++) {
    const u = await api("POST", "/v1/register", { body: { handle: `cap_m${i}`, display_name: `Member ${i}` } });
    const j = await api("POST", "/v1/groups/join", { token: u.data.token, body: { invite_code: grp.data.invite_code } });
    assert.equal(j.status, i < 49 ? 200 : 409, `joiner ${i}: ${JSON.stringify(j.data)}`); // owner + 49 = 50
  }
  // an existing member re-joining a full group is still idempotent
  assert.equal((await api("POST", "/v1/groups/join", { token: owner.data.token, body: { invite_code: grp.data.invite_code } })).status, 200);
  const g = await api("GET", `/v1/groups/${grp.data.group_id}`, { token: owner.data.token });
  assert.equal(g.data.members.length, 50);
});

test("CORS", async () => {
  const pre = await api("OPTIONS", "/v1/me", { headers: { Origin: ORIGIN_OK, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization" } });
  assert.equal(pre.status, 204);
  assert.equal(pre.headers.get("access-control-allow-origin"), ORIGIN_OK);
  assert.match(pre.headers.get("access-control-allow-headers"), /Authorization/);
  assert.match(pre.headers.get("access-control-allow-methods"), /PATCH/);
  assert.equal(pre.headers.get("access-control-allow-credentials"), null);
  const pre2 = await api("OPTIONS", "/v1/sync", { headers: { Origin: ORIGIN_OK2 } });
  assert.equal(pre2.headers.get("access-control-allow-origin"), ORIGIN_OK2);
  const bad = await api("OPTIONS", "/v1/me", { headers: { Origin: ORIGIN_BAD } });
  assert.equal(bad.status, 204);
  assert.equal(bad.headers.get("access-control-allow-origin"), null);
  const get = await api("GET", "/v1/health", { headers: { Origin: ORIGIN_OK } });
  assert.equal(get.headers.get("access-control-allow-origin"), ORIGIN_OK);
  assert.match(get.headers.get("vary") || "", /Origin/);
  const getBad = await api("GET", "/v1/health", { headers: { Origin: ORIGIN_BAD } });
  assert.equal(getBad.headers.get("access-control-allow-origin"), null);
  const err = await api("GET", "/v1/me", { headers: { Origin: ORIGIN_OK } }); // error responses carry CORS too
  assert.equal(err.status, 401);
  assert.equal(err.headers.get("access-control-allow-origin"), ORIGIN_OK);
  // limited instance has ALLOWED_ORIGINS="" -> nothing is allowed, never "*"
  const none = await api("OPTIONS", "/v1/me", { base: LBASE, headers: { Origin: ORIGIN_OK } });
  assert.equal(none.headers.get("access-control-allow-origin"), null);
});

test("rate limits (limited instance)", async () => {
  // Fixed windows: making 2*limit+1 requests guarantees >limit land in one window even across a boundary.
  const regStatuses = [];
  const tokens = [];
  for (let i = 0; i < 2 * LIMITED.regPerHour + 1; i++) {
    const r = await api("POST", "/v1/register", { base: LBASE, headers: { "CF-Connecting-IP": "203.0.113.7" }, body: { handle: `rl_user_${i}`, display_name: `RL ${i}` } });
    regStatuses.push(r.status);
    if (r.status === 201) tokens.push(r.data.token);
    if (r.status === 429) assert.ok(Number(r.headers.get("retry-after")) > 0);
  }
  assert.deepEqual(regStatuses.slice(0, LIMITED.regPerHour), Array(LIMITED.regPerHour).fill(201));
  assert.ok(regStatuses.includes(429), `register statuses: ${regStatuses}`);

  const t = tokens[0];
  const statuses = [];
  let retryAfter = null;
  for (let i = 0; i < 2 * LIMITED.perMin + 1; i++) {
    const r = await api("GET", "/v1/me", { base: LBASE, token: t });
    statuses.push(r.status);
    if (r.status === 429) {
      retryAfter = r.headers.get("retry-after");
      assert.equal(r.data.error, "rate limit exceeded");
    }
  }
  assert.deepEqual(statuses.slice(0, LIMITED.perMin), Array(LIMITED.perMin).fill(200));
  assert.ok(statuses.includes(429), `token statuses: ${statuses}`);
  assert.ok(Number(retryAfter) >= 1 && Number(retryAfter) <= 60);
  // limits are per token: a different user is unaffected
  if (tokens[1]) assert.equal((await api("GET", "/v1/me", { base: LBASE, token: tokens[1] })).status, 200);
  // health is never rate limited
  assert.equal((await api("GET", "/v1/health", { base: LBASE })).status, 200);
});

// ---------- phone/web link + Apple Health (v2) ----------

test("app link: pairing, state, commands, scopes", async () => {
  const pc = await api("POST", "/v1/register", { body: { handle: "padowner", display_name: "Pad Owner" } });
  const T = pc.data.token;
  // pairing: the PC gets a code, the phone claims it once
  const code = await api("POST", "/v1/pair/start", { token: T });
  assert.equal(code.status, 201); assert.match(code.data.code, /^[A-Z0-9]{6}$/);
  assert.equal((await api("POST", "/v1/pair/claim", { body: { code: "ZZZZZZ" } })).status, 404);
  const ph = await api("POST", "/v1/pair/claim", { body: { code: code.data.code.toLowerCase(), label: "iPhone" } });
  assert.equal(ph.status, 201, JSON.stringify(ph.data)); assert.match(ph.data.token, /^[0-9a-f]{64}$/);
  assert.equal(ph.data.handle, "padowner");
  assert.equal((await api("POST", "/v1/pair/claim", { body: { code: code.data.code } })).status, 404, "single use");
  const P = ph.data.token;
  // the device token can read, but cannot do account-only things
  assert.equal((await api("GET", "/v1/me", { token: P })).status, 200);
  assert.equal((await api("POST", "/v1/pair/start", { token: P })).status, 403);
  assert.equal((await api("DELETE", "/v1/me", { token: P })).status, 403);
  assert.equal((await api("POST", "/v1/sync", { token: P, body: { days: [] } })).status, 403);
  assert.equal((await api("POST", "/v1/app/state", { token: P, body: { state: {} } })).status, 403);
  // state: PC pushes, phone reads
  assert.deepEqual((await api("GET", "/v1/app/state", { token: P })).data.state, null);
  const big = { goal: { metric: "steps", goal: 5000 }, filler: "x".repeat(150000),
                healthExport: [{ id: 7, start: "2026-11-06T15:29:46+03:00", end: "2026-11-06T16:09:57+03:00", steps: 2726, km: 1.53 },
                               { id: 8, start: "2026-11-06T16:56:13+03:00", end: "2026-11-06T17:13:27+03:00", steps: 197, km: 0.25 }] };
  const put = await api("POST", "/v1/app/state", { token: T, body: { state: big } });
  assert.equal(put.status, 200, JSON.stringify(put.data)); assert.equal(put.data.devices, 1);
  const got = await api("GET", "/v1/app/state", { token: P });
  assert.equal(got.data.state.goal.goal, 5000); assert.ok(got.data.updated_at);
  // commands: phone queues, PC takes them once
  assert.equal((await api("POST", "/v1/app/commands", { token: P, body: { kind: "rm -rf", payload: {} } })).status, 400);
  assert.equal((await api("POST", "/v1/app/commands", { token: P, body: { kind: "pad", payload: { action: "explode" } } })).status, 400);
  assert.equal((await api("POST", "/v1/app/commands", { token: P, body: { kind: "settings", payload: { week_goal: 4 } } })).status, 202);
  assert.equal((await api("POST", "/v1/app/commands", { token: P, body: { kind: "pad", payload: { action: "speed", speed: 3.5 } } })).status, 202);
  assert.equal((await api("GET", "/v1/app/commands", { token: P })).status, 403, "phone can't drain the queue");
  const take = await api("GET", "/v1/app/commands", { token: T });
  assert.deepEqual(take.data.commands.map((c) => c.kind), ["settings", "pad"]);
  assert.equal((await api("GET", "/v1/app/commands", { token: T })).data.commands.length, 0, "taken once");
  // Apple Health: export -> ack -> export again is empty; import queues a 'health' command for the PC
  const ex = await api("GET", "/v1/health/export", { token: P });
  assert.equal(ex.data.count, 2); assert.equal(ex.data.ids, "7,8");
  assert.equal((await api("POST", "/v1/health/ack", { token: P, body: { ids: "7,8" } })).data.acked, 2);
  assert.equal((await api("GET", "/v1/health/export", { token: P })).data.count, 0);
  assert.equal((await api("POST", "/v1/health/import", { token: P, body: { date: "2026-11-06", steps: "7,842", km: "5.1" } })).status, 200);
  assert.equal((await api("POST", "/v1/health/import", { token: P, body: { date: "06/11", steps: 10 } })).status, 400);
  const hc = await api("GET", "/v1/app/commands", { token: T });
  assert.deepEqual(hc.data.commands[0], { ...hc.data.commands[0], kind: "health", payload: { date: "2026-11-06", steps: 7842, km: 5.1 } });
  // devices: list + revoke
  const dv = await api("GET", "/v1/devices", { token: T });
  assert.equal(dv.data.devices.length, 1); assert.equal(dv.data.devices[0].label, "iPhone");
  assert.equal((await api("POST", "/v1/devices/revoke", { token: T, body: {} })).status, 200);
  assert.equal((await api("GET", "/v1/app/state", { token: P })).status, 401, "revoked device is locked out");
  // deleting the account removes the snapshot too
  assert.equal((await api("DELETE", "/v1/me", { token: T })).status, 200);
});
