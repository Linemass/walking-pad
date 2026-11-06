"""UREVO walking pad logger + local dashboard + tray icon (one process).

The pad accepts a single Bluetooth LE central, so everything that wants live
data lives here: the BLE connection (FTMS 0x1826 / Treadmill Data 0x2ACD), the
SQLite store, a local web server for the dashboard (http://127.0.0.1:8765) and
the system-tray icon. Reconnects forever, so it can run at logon and be forgotten.

The dashboard only talks to /api/* JSON endpoints, so the same web/ folder can
later be hosted on Cloudflare Pages with the API backed by a synced database.
"""
import asyncio
import logging
import os
import sqlite3
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from aiohttp import web
from bleak import BleakClient, BleakScanner

import app_shell
import community_client
import engine
import pad_control

NAME_PREFIX = os.environ.get("WALKINGPAD_NAME_PREFIX", "URTM")   # UREVO pads advertise as URTM…
TREADMILL_DATA = "00002acd-0000-1000-8000-00805f9b34fb"
HOME = Path(__file__).resolve().parent
app_shell.DATA.mkdir(parents=True, exist_ok=True)
DB_PATH = app_shell.DATA / "urevo.db"
WEB_DIR = app_shell.RESOURCES / "web"
FTMS_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
HOST, PORT = "127.0.0.1", int(os.environ.get("WALKINGPAD_PORT", "8765"))
URL = f"http://{HOST}:{PORT}/"
RETRY_SECONDS = 15
# Session 1 (18 Oct) carried counters over from before logging started; it is
# kept in the DB but excluded from analytics.
BOGUS_SESSIONS = (1,)

logging.basicConfig(
    filename=app_shell.DATA / "urevo_logger.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("urevo")

# Shared, read by the web server and the tray thread.
LIVE = {
    "connected": False,
    "device": None,
    "status": "starting",          # starting | scanning | connected
    "session_id": None,
    "last": None,                  # latest decoded sample
    "last_ts": None,
}


def parse_treadmill_data(data: bytes) -> dict:
    """Decode FTMS Treadmill Data (Bluetooth FTMS spec 4.9)."""
    flags = int.from_bytes(data[0:2], "little")
    i = 2
    out = {}

    def take(n, signed=False):
        nonlocal i
        v = int.from_bytes(data[i:i + n], "little", signed=signed)
        i += n
        return v

    if not flags & 0x0001:            # bit 0 clear => instantaneous speed present
        out["speed_kmh"] = take(2) / 100
    if flags & 0x0002:
        out["avg_speed_kmh"] = take(2) / 100
    if flags & 0x0004:
        out["distance_m"] = take(3)
    if flags & 0x0008:
        out["incline_pct"] = take(2, True) / 10
        take(2, True)                 # ramp angle
    if flags & 0x0010:
        take(2); take(2)              # elevation gain +/-
    if flags & 0x0020:
        take(1)                       # instantaneous pace
    if flags & 0x0040:
        take(1)                       # average pace
    if flags & 0x0080:
        out["kcal"] = take(2)
        take(2); take(1)              # kcal/hour, kcal/minute
    if flags & 0x0100:
        out["heart_rate"] = take(1)
    if flags & 0x0200:
        take(1)                       # MET
    if flags & 0x0400:
        out["elapsed_s"] = take(2)
    if flags & 0x0800:
        take(2)                       # remaining time
    if flags & 0x1000:
        take(2, True); take(2, True)  # force on belt, power
    if flags & 0x2000 and len(data) - i >= 3:
        out["steps"] = take(3)        # UREVO vendor extension (RFU bit 13)
    return out


class Store:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS samples (
                ts TEXT NOT NULL, session_id INTEGER NOT NULL,
                speed_kmh REAL, distance_m INTEGER, steps INTEGER, kcal INTEGER,
                elapsed_s INTEGER, heart_rate INTEGER, raw TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY, start_ts TEXT, end_ts TEXT,
                distance_m INTEGER, steps INTEGER, kcal INTEGER, elapsed_s INTEGER,
                max_speed_kmh REAL);
            CREATE INDEX IF NOT EXISTS samples_session ON samples(session_id);
        """)
        row = self.db.execute(
            "SELECT id, distance_m, elapsed_s FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.session_id, self.last_dist, self.last_elapsed = (
            (row["id"], row["distance_m"] or 0, row["elapsed_s"] or 0) if row else (0, 0, 0))
        self.last_raw = None
        last = self.db.execute(
            """SELECT ts, session_id, speed_kmh, distance_m, steps, kcal, elapsed_s
               FROM samples ORDER BY rowid DESC LIMIT 1""").fetchone()
        if last:                      # show the last reading until the pad speaks again
            LIVE["last"] = {k: last[k] for k in
                            ("speed_kmh", "distance_m", "steps", "kcal", "elapsed_s")}
            LIVE["last_ts"], LIVE["session_id"] = last["ts"], last["session_id"]

    def add(self, raw: bytes):
        hexraw = raw.hex()
        if hexraw == self.last_raw:
            return
        self.last_raw = hexraw
        d = parse_treadmill_data(raw)
        now = datetime.now().isoformat(timespec="seconds")
        LIVE["last"], LIVE["last_ts"] = d, now
        dist, elapsed = d.get("distance_m", 0), d.get("elapsed_s", 0)
        if elapsed == 0 and dist == 0:
            return                    # idle pad with counters cleared: nothing to keep
        # Counters going backwards means the pad started a new workout.
        if self.session_id == 0 or elapsed < self.last_elapsed or dist < self.last_dist:
            self.session_id += 1
            self.db.execute("INSERT INTO sessions (id, start_ts, max_speed_kmh) VALUES (?, ?, 0)",
                            (self.session_id, now))
            log.info("new session %s", self.session_id)
        LIVE["session_id"] = self.session_id
        self.last_dist, self.last_elapsed = dist, elapsed
        self.db.execute(
            "INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?)",
            (now, self.session_id, d.get("speed_kmh"), dist, d.get("steps"),
             d.get("kcal"), elapsed, d.get("heart_rate"), hexraw))
        self.db.execute(
            """UPDATE sessions SET end_ts=?, distance_m=?, steps=?, kcal=?, elapsed_s=?,
               max_speed_kmh=MAX(max_speed_kmh, ?) WHERE id=?""",
            (now, dist, d.get("steps"), d.get("kcal"), elapsed,
             d.get("speed_kmh") or 0, self.session_id))
        self.db.commit()


# ---------------------------------------------------------------- BLE loop

async def ble_forever(store: Store):
    if os.environ.get("WALKINGPAD_NO_BLE"):          # tests: never touch the real pad
        LIVE.update(status="disabled", connected=False)
        return
    while True:
        try:
            LIVE.update(status="scanning", connected=False)
            dev = await BleakScanner.find_device_by_filter(
                lambda d, adv: (adv.local_name or d.name or "").startswith(NAME_PREFIX)
                               or FTMS_SERVICE in [u.lower() for u in (adv.service_uuids or [])],   # any FTMS treadmill
                timeout=20)
            if dev is None:
                await asyncio.sleep(RETRY_SECONDS)
                continue
            disconnected = asyncio.Event()
            async with BleakClient(dev, disconnected_callback=lambda _: disconnected.set(),
                                   timeout=20) as client:
                log.info("connected to %s (%s)", dev.name, dev.address)
                LIVE.update(status="connected", connected=True,
                            device={"name": dev.name, "address": dev.address})
                await client.start_notify(TREADMILL_DATA, lambda _, data: store.add(bytes(data)))
                try:
                    await pad_control.attach(client)
                except Exception as e:
                    log.warning("pad discovery failed: %r", e)
                await disconnected.wait()
                pad_control.detach()
                log.info("disconnected")
        except Exception as e:
            log.warning("connection error: %r", e)
        LIVE.update(status="scanning", connected=False)
        await asyncio.sleep(RETRY_SECONDS)


# ---------------------------------------------------------------- web API

app_ctx = {}


def build_app(store: Store) -> web.Application:
    db = store.db

    def full_state():
        st = engine.compute(db, LIVE)
        st.pop("_days", None)
        st["pad"].update(pad_control.info())
        if st["moving"]:
            pad_control.PAD["paused"] = False
        return st
    bogus = engine.excluded(db)

    async def live(_):
        return web.json_response({**LIVE, "server_ts": datetime.now().isoformat(timespec="seconds")})

    async def sessions(req):
        limit = int(req.query.get("limit", 50))
        rows = db.execute(
            f"""SELECT id, start_ts, end_ts, distance_m, steps, kcal, elapsed_s, max_speed_kmh,
                       id IN ({bogus}) AS excluded
                FROM sessions ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()
        return web.json_response([dict(r) for r in rows])

    async def daily(req):
        days = int(req.query.get("days", 365))
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = db.execute(
            f"""SELECT substr(start_ts,1,10) AS day, COUNT(*) AS sessions,
                       SUM(distance_m) AS distance_m, SUM(steps) AS steps, SUM(kcal) AS kcal,
                       SUM(elapsed_s) AS elapsed_s, MAX(max_speed_kmh) AS max_speed_kmh
                FROM sessions WHERE id NOT IN ({bogus}) AND substr(start_ts,1,10) >= ?
                GROUP BY day ORDER BY day""", (since,)).fetchall()
        return web.json_response([dict(r) for r in rows])

    async def session_trace(req):
        sid = int(req.match_info["sid"])
        rows = db.execute(
            """SELECT ts, speed_kmh, distance_m, steps, kcal, elapsed_s
               FROM samples WHERE session_id=? ORDER BY rowid""", (sid,)).fetchall()
        step = max(1, len(rows) // 400)          # keep the payload small
        return web.json_response([dict(r) for r in rows[::step]])

    async def state(_):
        return web.json_response(full_state())

    async def pad(req):
        try:
            b = await req.json()
            await pad_control.command(str(b.get("action")), b.get("speed"))
        except (ValueError, TypeError, RuntimeError) as e:
            return web.json_response({"error": str(e)}, status=409 if isinstance(e, RuntimeError) else 400)
        except Exception as e:
            log.warning("pad command failed: %r", e)
            return web.json_response({"error": "The pad didn't accept the command."}, status=502)
        return web.json_response(full_state())

    async def settings(req):
        try:
            patch = await req.json()
            if not isinstance(patch, dict):
                raise ValueError("expected an object")
            engine.save_settings(db, patch)
        except (ValueError, TypeError) as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response(full_state())

    async def track(req):
        try:
            body = await req.json()
            engine.set_track(db, str(body.get("id")), body.get("custom") or [])
        except (ValueError, TypeError, AttributeError) as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response(full_state())

    # ---------------- community (proxy: the token stays in the local DB) ----------------
    def cset():
        return engine.load_settings(db)["community"]

    async def ccall(method, path, body=None, token=True):
        c = cset()
        return await asyncio.to_thread(community_client.call, c["server"], method, path, c["token"] if token else None, body)

    def cerr(e):
        return web.json_response({"error": str(e)}, status=e.status if 400 <= e.status < 600 else 502)

    async def c_sync_now():
        c = cset()
        if not c["enabled"] or not c["token"]:
            return None
        st = engine.compute(db, LIVE)
        r = await ccall("POST", "/v1/sync", community_client.sync_payload(st))
        engine.save_community(db, {"last_sync": datetime.now().isoformat(timespec="seconds")})
        return r

    async def c_join(req):
        b = await req.json()
        try:
            r = await ccall("POST", "/v1/register", {"handle": str(b.get("handle", "")).strip().lower(), "display_name": str(b.get("display_name", "")).strip()}, token=False)
            engine.save_community(db, {"enabled": True, "user_id": r["user_id"], "handle": r["handle"], "display_name": r["display_name"], "token": r["token"], "public": False})
            if b.get("public"):
                await ccall("PATCH", "/v1/me", {"public": True}); engine.save_community(db, {"public": True})
            await c_sync_now()
        except community_client.CommunityError as e:
            return cerr(e)
        return web.json_response(engine.compute(db, LIVE)["community"])

    async def c_me(_):
        try:
            return web.json_response(await ccall("GET", "/v1/me"))
        except community_client.CommunityError as e:
            return cerr(e)

    async def c_board(req):
        q = req.query
        today = datetime.now().date()
        if q.get("period") == "month":
            frm = today.replace(day=1)
        else:
            frm = engine.week_start(today)
        qs = f"?scope={q.get('scope', 'global')}&metric={q.get('metric', 'steps')}&from={frm.isoformat()}&to={today.isoformat()}&limit=50"
        try:
            return web.json_response(await ccall("GET", "/v1/leaderboard" + qs))
        except community_client.CommunityError as e:
            return cerr(e)

    async def c_post(req):
        b = await req.json() if req.can_read_body else {}
        what = req.match_info["what"]
        try:
            if what == "groups":
                r = await ccall("POST", "/v1/groups", {"name": str(b.get("name", "")).strip()})
            elif what == "joingroup":
                r = await ccall("POST", "/v1/groups/join", {"invite_code": str(b.get("invite_code", "")).strip()})
            elif what == "leavegroup":
                gid = "".join(ch for ch in str(b.get("group_id", "")) if ch.isalnum() or ch in "-_")
                r = await ccall("POST", f"/v1/groups/{gid}/leave", {})
            elif what == "public":
                r = await ccall("PATCH", "/v1/me", {"public": bool(b.get("public"))}); engine.save_community(db, {"public": bool(b.get("public"))})
            elif what == "sync":
                r = await c_sync_now() or {}
            elif what == "leave":
                try:
                    await ccall("DELETE", "/v1/me")
                except community_client.CommunityError as e:
                    if e.status not in (401, 404):
                        raise
                engine.save_community(db, {**engine.DEFAULTS["community"], "server": cset()["server"]})
                r = {"ok": True}
            else:
                return web.json_response({"error": "unknown action"}, status=404)
        except community_client.CommunityError as e:
            return cerr(e)
        return web.json_response(r)

    app_ctx["sync"] = c_sync_now

    # ---------------- cloud link: phone app on Cloudflare ----------------
    cloud = {"last_push": 0.0, "devices": 0, "last_poll": 0.0, "pair_until": 0.0}

    async def apply_command(kind, payload):
        try:
            if kind == "settings":
                engine.save_settings(db, payload)
            elif kind == "track":
                engine.set_track(db, str(payload.get("id")), payload.get("custom") or [])
            elif kind == "pad":
                await pad_control.command(str(payload.get("action")), payload.get("speed"))
            elif kind == "health":
                engine.save_health(db, payload["date"], payload["steps"], payload.get("km"))
            log.info("cloud command applied: %s", kind if kind != "pad" else "pad " + str(payload.get("action")))
        except Exception as e:
            log.warning("cloud command %s failed: %r", kind, e)

    async def cloud_tick(force_push=False):
        """Push state (5 s while walking/paused, 60 s otherwise) and take queued commands when a phone is paired."""
        c = cset()
        if not c["enabled"] or not c["token"]:
            return
        import time
        now = time.monotonic()
        st = full_state()
        busy = st["moving"] or st["pad"].get("paused")
        if force_push or now - cloud["last_push"] >= (5 if busy else 60):
            st["healthExport"] = engine.health_export(db, LIVE.get("session_id") if st["moving"] else None)
            st["cloudPushedAt"] = datetime.now().isoformat(timespec="seconds")
            r = await ccall("POST", "/v1/app/state", {"state": st})
            cloud["last_push"] = now
            cloud["devices"] = r.get("devices", 0)
        if (cloud["devices"] or now < cloud["pair_until"]) and now - cloud["last_poll"] >= 3:
            cloud["last_poll"] = now
            r = await ccall("GET", "/v1/app/commands")
            if r.get("commands"):
                for cmd in r["commands"]:
                    await apply_command(cmd["kind"], cmd["payload"])
                await cloud_tick(force_push=True)

    app_ctx["cloud_tick"] = cloud_tick

    async def cloud_pair(_):
        try:
            r = await ccall("POST", "/v1/pair/start")
            cloud["last_push"] = 0.0                 # make sure the phone has fresh state right away
            import time
            cloud["pair_until"] = time.monotonic() + 600    # take the new phone's commands right away (it claims after this push)
            await cloud_tick(force_push=True)
            return web.json_response({**r, "url": cset()["server"].rstrip("/") + "/"})
        except community_client.CommunityError as e:
            return cerr(e)

    async def cloud_devices(_):
        try:
            return web.json_response(await ccall("GET", "/v1/devices"))
        except community_client.CommunityError as e:
            return cerr(e)

    async def cloud_revoke(req):
        b = await req.json() if req.can_read_body else {}
        try:
            r = await ccall("POST", "/v1/devices/revoke", {"id": b.get("id")} if b.get("id") else {})
            cloud["devices"] = 0 if not b.get("id") else cloud["devices"]
            return web.json_response(r)
        except community_client.CommunityError as e:
            return cerr(e)

    async def index(_):
        return web.FileResponse(WEB_DIR / "index.html",
                                headers={"Cache-Control": "no-store"})

    app = web.Application()
    app.add_routes([
        web.get("/", index),
        web.get("/api/live", live),
        web.get("/api/sessions", sessions),
        web.get("/api/daily", daily),
        web.get("/api/sessions/{sid}/samples", session_trace),
        web.get("/api/state", state),
        web.post("/api/settings", settings),
        web.post("/api/track", track),
        web.post("/api/pad", pad),
        web.post("/api/community/join", c_join),
        web.get("/api/community/me", c_me),
        web.get("/api/community/leaderboard", c_board),
        web.post("/api/cloud/pair", cloud_pair),
        web.get("/api/cloud/devices", cloud_devices),
        web.post("/api/cloud/revoke", cloud_revoke),
        web.post("/api/community/{what}", c_post),
        web.static("/static", WEB_DIR),
    ])
    return app


# ---------------------------------------------------------------- tray icon

def start_tray(stop):
    """Tray icon near the clock: green when the pad is connected."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception as e:              # tray is optional; logging must not depend on it
        log.warning("tray unavailable: %r", e)
        return None

    def make_icon(color):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((2, 2, 62, 62), 14, fill=color)
        d.ellipse((18, 10, 34, 34), fill="white")   # footprint: sole
        d.ellipse((22, 36, 34, 54), fill="white")   # heel
        d.ellipse((38, 8, 46, 16), fill="white")    # toe
        return img

    on_img, off_img = make_icon((22, 150, 110)), make_icon((120, 120, 120))

    def status_text(_=None):
        if not LIVE["connected"]:
            return "Pad not connected — searching…"
        s = LIVE["last"] or {}
        return (f"Connected · {s.get('speed_kmh', 0):.1f} km/h · "
                f"{(s.get('distance_m') or 0) / 1000:.2f} km · {s.get('steps') or 0} steps")

    def open_dash(*_):
        launcher = HOME / "open_app.pyw"
        if app_shell.FROZEN or not launcher.exists():
            app_shell.open_window(URL)
        elif launcher.exists():
            import subprocess, sys
            pyw = Path(sys.executable).with_name("pythonw.exe")
            subprocess.Popen([str(pyw), str(launcher)])
        else:
            webbrowser.open(URL)

    def quit_app(icon, _):
        icon.stop()
        stop()

    icon = pystray.Icon(
        "urevo", off_img, "UREVO walking pad",
        menu=pystray.Menu(
            pystray.MenuItem(status_text, None, enabled=False),
            pystray.MenuItem("Open Walking Pad", open_dash, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit logger", quit_app),
        ))

    def refresh():
        import time
        while True:
            try:
                icon.icon = on_img if LIVE["connected"] else off_img
                icon.title = "UREVO — " + status_text()
                icon.update_menu()
            except Exception:
                pass
            time.sleep(2)

    icon.run_detached()
    threading.Thread(target=refresh, daemon=True).start()
    return icon


# ---------------------------------------------------------------- cloud link (phone app)

async def cloud_forever():
    """Keeps the hosted phone app in step with this PC. Quiet when no account exists."""
    while True:
        await asyncio.sleep(2)
        try:
            if app_ctx.get("cloud_tick"):
                await app_ctx["cloud_tick"]()
        except Exception as e:
            log.info("cloud link: %s", e)
            await asyncio.sleep(20)                  # back off while the server or internet is down


# ---------------------------------------------------------------- community sync

async def community_forever():
    """Every 10 minutes, send daily totals to the community server (only when the user joined)."""
    while True:
        await asyncio.sleep(600)
        try:
            if app_ctx.get("sync"):
                await app_ctx["sync"]()
        except Exception as e:
            log.info("community sync skipped: %s", e)


# ---------------------------------------------------------------- daily nudge

async def nudge_forever(store: Store, icon):
    """At most ONE gentle reminder a day: at the chosen time, only if nothing is walked yet,
    and never in a pause mode. Runs on the event loop because the DB lives on this thread."""
    sent_on = None
    while True:
        await asyncio.sleep(60)
        try:
            s = engine.load_settings(store.db)
            now = datetime.now()
            n = s["nudge"]
            if (not n["on"] or sent_on == now.date() or icon is None or now.strftime("%H:%M") < n["time"]
                    or s["modes"].get("travel") or s["modes"].get("sick")):
                continue
            st = engine.compute(store.db, LIVE)
            sent_on = now.date()
            g = st["goal"]
            if st["today"]["value"] < g["tiny"]:
                icon.notify(f"After you {s['cue']}, {engine.fmtu(g['metric'], g['tiny'])} on the pad keeps your streak going.", "Walking Pad")
                log.info("nudge sent")
        except Exception as e:
            log.warning("nudge error: %r", e)


# ---------------------------------------------------------------- main

async def main():
    store = Store(DB_PATH)
    runner = web.AppRunner(build_app(store), access_log=None)   # the UI polls; keep the log for real events
    await runner.setup()
    try:
        await web.TCPSite(runner, HOST, PORT).start()
    except OSError:
        # Port taken = another copy is already running and owns the pad: just show its window.
        log.warning("port %s busy — another logger is running; exiting", PORT)
        if app_shell.FROZEN and "--background" not in sys.argv:
            app_shell.open_window(URL)
        return
    log.info("logger started, db=%s, dashboard=%s", DB_PATH, URL)
    if app_shell.FROZEN and "--background" not in sys.argv:
        app_shell.open_window(URL)                 # double-clicked: show the app (at logon it stays in the tray)

    loop = asyncio.get_running_loop()
    done = asyncio.Event()
    icon = start_tray(lambda: loop.call_soon_threadsafe(done.set))
    ble = asyncio.create_task(ble_forever(store))
    nudge = asyncio.create_task(nudge_forever(store, icon))
    csync = asyncio.create_task(community_forever())
    clink = asyncio.create_task(cloud_forever())
    await done.wait()
    log.info("quit from tray")
    ble.cancel(); nudge.cancel(); csync.cancel(); clink.cancel()
    await runner.cleanup()


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        app_shell.uninstall(); os._exit(0)
    if app_shell.install_if_needed():
        os._exit(0)
    asyncio.run(main())
    os._exit(0)                        # don't wait on the tray thread after "Quit"
