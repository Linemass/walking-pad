# Walking Pad Community API

Cloudflare Worker + D1 backend for the Walking Pad Community: people register a handle, sync **daily aggregates only** (no raw sessions), join groups by invite code and see leaderboards.

- `src/index.js` - the Worker (plain ES module, zero runtime dependencies)
- `migrations/0001_init.sql` - D1 schema and indexes
- `test/api.test.mjs` - end-to-end tests (`node --test`), start and stop their own local servers
- `wrangler.toml` - Worker + D1 binding config (`database_id` is a placeholder until deploy)

Requires Node 20+ (tested on Node 24) and wrangler 4 (used through `npx wrangler`, tested on 4.158.0).

## Run locally

```bash
cd community
npm run migrate:local   # npx wrangler d1 migrations apply DB --local  (creates .wrangler/state)
npm run dev             # npx wrangler dev --local --port 8787
curl http://127.0.0.1:8787/v1/health   # {"ok":true}
```

Local data lives in `.wrangler/state` (git-ignored). Delete that folder to reset.

To override vars locally, create `.dev.vars` (git-ignored), e.g.:

```
ALLOWED_ORIGINS=http://localhost:5173
RATE_LIMIT_PER_MIN=120
REGISTER_LIMIT_PER_HOUR=10
```

## Tests

```bash
npm test
```

One command. It starts two `wrangler dev --local` instances, each with its own fresh D1 state under `.wrangler/test-*`:

- port 8787: high rate limits, `ALLOWED_ORIGINS=https://app.example,https://pad.example`
- port 8788: `RATE_LIMIT_PER_MIN=5`, `REGISTER_LIMIT_PER_HOUR=3`, for the 429 tests

It stops both when it finishes. Ports 8787/8788 and inspector ports 9301/9302 must be free, so stop `npm run dev` first.

## Configuration (`[vars]` in wrangler.toml)

| var | default | meaning |
|---|---|---|
| `ALLOWED_ORIGINS` | `""` | Comma-separated browser origins allowed by CORS. Empty means no browser origin is allowed. Server-to-server calls don't need CORS. |
| `RATE_LIMIT_PER_MIN` | `120` | Requests per minute per token (fixed window, counted in D1). |
| `REGISTER_LIMIT_PER_HOUR` | `10` | Registrations per hour per `CF-Connecting-IP`. |

## API (all JSON, all under `/v1`)

Errors always look like `{"error": "<message>"}` and use a 4xx status (400 validation, 401 auth, 403 not a member, 404 not found, 405 method, 409 conflict, 413 body > 64 KB, 429 rate limit with a `Retry-After` header).

Every endpoint except `/v1/health` and `/v1/register` needs `Authorization: Bearer <token>`.

| method | path | body / query | response |
|---|---|---|---|
| GET | `/v1/health` | | `{ok:true}` |
| POST | `/v1/register` | `{handle, display_name}` | 201 `{user_id, handle, display_name, token}` |
| GET | `/v1/me` | | `{user_id, handle, display_name, public, created_at, groups:[{group_id,name,role,invite_code,members}]}` |
| PATCH | `/v1/me` | `{display_name?, public?}` | same as GET /v1/me |
| DELETE | `/v1/me` | | `{ok:true}` |
| POST | `/v1/sync` | `{days:[{date,steps,minutes,km,goal_met}], streak?}` | `{saved:n}` |
| POST | `/v1/groups` | `{name}` | 201 `{group_id, name, invite_code}` |
| POST | `/v1/groups/join` | `{invite_code}` | `{group_id, name}` |
| POST | `/v1/groups/{id}/leave` | | `{ok:true}` |
| GET | `/v1/groups/{id}` | | `{group_id, name, invite_code, members:[{handle,display_name,role}]}` |
| GET | `/v1/leaderboard` | `scope, metric, from, to, limit` | `{scope, metric, from, to, rows:[{rank,handle,display_name,value,me}], me:{rank,value}\|null}` |

### Rules

- **handle**: trimmed and lower-cased, then must match `[a-z0-9_]{3,20}`. So `Alice` is stored as `alice` and conflicts with an existing `alice` (409).
- **display_name / group name**: trimmed, 1-40 characters, no control or bidi-override characters.
- **token**: 32 random bytes as hex (64 chars), returned once. Only its SHA-256 is stored, so a lost token can't be recovered (re-register under a new handle, or keep it safe).
- **sync**: at most 62 days per call. Each day is upserted per (user, date). If a date appears twice in one call, the last one wins. Each date must be a real `YYYY-MM-DD` between today-400 and today+1 (UTC). `steps` is an integer 0..150000, `minutes` 0..1440, `km` 0..200, `goal_met` a boolean. `streak` is an integer 0..10000 stored on the user; if you leave it out, the stored streak stays as it is. `days` may be empty.
- **groups**: you can own at most 20 groups (409 beyond that). A group holds at most 50 members (409 when full). Invite codes are 8 characters from `ABCDEFGHJKMNPQRSTUVWXYZ23456789` and are matched case-insensitively. Joining twice is idempotent. When the owner leaves or deletes their account, ownership passes to the earliest-joined remaining member; if nobody is left, the group is deleted.
- **leaderboard**:
  - `scope`: `global` (default) or `group:<group_id>`. Group scope is for members only (403 otherwise, 404 if the group doesn't exist).
  - `metric`: `steps` (default), `minutes` (sum, 1 dp), `km` (sum, 2 dp), `goal_days` (days with `goal_met` in range) or `streak` (the stored current streak; range is ignored).
  - `from`/`to`: inclusive, at most 31 days, `from <= to`. Defaults to the last 7 days ending today (UTC).
  - `limit`: 1..100, default 50.
  - Global rows contain only users with `public=true`. `me` is always the caller's own `{rank, value}`; for a private caller it is the rank they would hold among public users.
  - Group rows contain all members, whatever their `public` setting.
  - Users with no data in the range appear with value 0.
  - **Ranking is standard competition ranking ("1224")**: tied values share a rank and the next rank skips. Ties are listed by handle.

## Deploying later (instructions only, nothing has been deployed)

1. `npx wrangler login`
2. `npx wrangler d1 create walking-pad-community` and copy the printed `database_id`.
3. Replace `database_id = "LOCAL-ONLY-REPLACE-ON-DEPLOY"` in `wrangler.toml` with that id.
4. Set `ALLOWED_ORIGINS` in `wrangler.toml` to the Pages origin(s), if a browser app will call the API.
5. `npx wrangler d1 migrations apply DB --remote`
6. `npx wrangler deploy`
7. Check it: `curl https://walking-pad-community.<your-subdomain>.workers.dev/v1/health`

## Calling from Python (stdlib only)

```python
import json, urllib.request

BASE = "http://127.0.0.1:8787"   # later: https://walking-pad-community.<sub>.workers.dev

def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "UrevoLogger/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")   # {"error": "..."}

status, me = call("POST", "/v1/register", {"handle": "mohammed", "display_name": "Mohammed"})
token = me["token"]   # store this locally; it is shown only once

call("POST", "/v1/sync", {
    "days": [{"date": "2026-11-06", "steps": 8421, "minutes": 62.5, "km": 5.9, "goal_met": True}],
    "streak": 4,
}, token=token)

call("GET", "/v1/leaderboard?scope=global&metric=steps&from=2026-10-31&to=2026-11-06", token=token)
```
