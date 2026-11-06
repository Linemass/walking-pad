# Walking Pad

A habit app for a Bluetooth walking pad (treadmill). It logs every walk from the pad, turns it into daily goals,
streaks, records and a "Walk across Saudi Arabia" journey, lets you control the pad (start, pause, stop, speed),
and works on your phone through Cloudflare, with a walking community, leaderboards and Apple Health sync.

Built for a UREVO pad (Bluetooth name `URTM…`); any pad that speaks the standard **Bluetooth FTMS** treadmill
protocol should work.

## Download (Windows)

Get **WalkingPad.exe** from the [latest release](../../releases/latest) and double-click it. It installs itself
(no admin rights), adds a desktop icon, starts with Windows and opens the app. Windows may say "Windows protected
your PC" because the app isn't code-signed yet: **More info → Run anyway**. Uninstall from the Start menu.

Want to help build it? See [CONTRIBUTING.md](CONTRIBUTING.md).

## How it fits together

```
 Walking pad ──Bluetooth FTMS──► PC: urevo_logger.py  ── one process, starts at logon
                                   │  BLE read + pad control (pad_control.py)
                                   │  SQLite urevo.db (never committed)
                                   │  habit engine (engine.py) → app state
                                   │  local web app  http://127.0.0.1:8765  (web/)
                                   │  tray icon + one daily nudge
                                   │
                                   ▼  pushes state, takes commands (community_client.py)
                         Cloudflare Worker + D1 (community/)
                           /v1 API: accounts, groups, leaderboards, phone pairing,
                                    state + command queue, Apple Health endpoints
                           static web app (the same web/ files) for the phone
                                   ▲
                    iPhone browser ┘ ── Apple Health via iOS Shortcuts
```

The pad accepts **one** Bluetooth connection, so everything that needs the pad runs in the logger on the PC. The
phone never talks to the pad: it reads the state the PC pushes and queues commands the PC applies (about 3 s).

## Folders

| Path | What |
|---|---|
| `urevo_logger.py` | The PC program: Bluetooth, SQLite, local web server, tray, cloud link. |
| `engine.py` | Habit rules: goals (steps/minutes/km/all-day, daily/weekly), streak + rest shields, week/month, records, medals, tracks, adaptive suggestion. Pure functions over the DB. |
| `pad_control.py` | FTMS control point: start, pause, stop, target speed. |
| `community_client.py` | Python client for the Worker. |
| `web/` | The app UI: `app.css` (design system), `ui.js` (state → HTML screens), `index.html` (router + API layer for PC and phone modes), `landmarks.js` (original landmark art + Saudi map). |
| `community/` | Cloudflare Worker + D1 migrations + tests. See `community/README.md`. |
| `design/` | Design board renderer, screen fixtures, and the UI/e2e test scripts. |
| `tests/` | Sample database (invented data) used by tests and the design board. |

## Run it on a PC (Windows)

From source: Python 3.12+ and `pip install -r requirements.txt`. Then:

```
python urevo_logger.py          # or pythonw for no console
```

Open http://127.0.0.1:8765. A different pad brand: set `WALKINGPAD_NAME_PREFIX` to the start of its Bluetooth name.

## Tests (run before every pull request)

| Check | Command |
|---|---|
| Engine rules | `python -P design/test_engine.py` |
| UI layout (overlap, overflow, ring text, light + dark, desktop + phone) | `python -P design/make_fixture.py && python -P design/overlap_check.py` (needs `pip install playwright && playwright install chromium`) |
| Worker API | `cd community && npm test` |
| Pad controls (stub pad) | `python -P design/test_controls.py <out-dir>` |
| Phone link end to end (local Worker) | `python -P design/e2e_cloud.py <out-dir>` |

Run Python with `-P` so scripts in the current folder can't shadow the standard library.

## Deploy

Staging first, always: `cd community && python tools/build_web.py && npx wrangler deploy --env staging`.
Production only after the owner has tried staging. Details in `community/README.md`.

## Privacy

Only daily totals ever leave the PC (steps, minutes, km, goal met, streak) plus the app state for your own paired
phone. Walk-by-walk samples, your database and account keys stay on the PC. Never commit `urevo.db`, logs, or tokens.

## Releasing

Bump nothing by hand: tag and push, e.g. `git tag v0.6.1 && git push origin v0.6.1`. GitHub Actions
(`.github/workflows/release.yml`) builds `WalkingPad.exe` on Windows and attaches it to the release with
`RELEASE_NOTES.md`. Local build: `python -P tools/build_exe.py` → `dist/WalkingPad.exe`.
