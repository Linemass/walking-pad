"""Simulated walk for testing the app's live flow without the pad.
Serves web/ on :8799 and fakes /api/state from a COPY of the real DB, adding 1 walking minute every tick."""
import asyncio, copy, json, shutil, sqlite3, sys, tempfile
from datetime import datetime
from pathlib import Path
from aiohttp import web
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine
tmp = Path(tempfile.mkdtemp()) / "sim.db"; shutil.copy(ROOT / "tests" / "fixtures" / "sample.db", tmp)
db = sqlite3.connect(tmp); db.row_factory = sqlite3.Row
engine.save_settings(db, {"onboarded": True, "goal": 30, "tiny": 5, "stretch": 45})
T = {"n": 0, "moving": True}
NOW = datetime(2026, 11, 7, 10, 0)            # a fresh day with no walking yet
async def state(_):
    s = engine.compute(db, {"connected": True, "device": {"name": "URTM041"}}, NOW)
    if T["moving"]:
        T["n"] += 1
    m = min(T["n"] * 1.0, 60)
    s["today"].update(min=m, steps=int(m * 75), distance_m=int(m * 45), kcal=int(m * 2.8), sessions=1)
    s["moving"] = T["moving"]
    s["live"].update(elapsed=int(m * 60), speed=2.7 if T["moving"] else 0, steps=int(m * 75), distance_m=int(m * 45), kcal=int(m * 2.8))
    if m >= 5:   # tiny reached -> streak 3 like the engine would compute
        s["streak"]["days"] = 3; s["streak"]["best"] = 3
    return web.json_response(s)
async def ctl(req):
    T.update(json.loads(await req.text())); return web.json_response(T)
async def index(_): return web.FileResponse(ROOT / "web" / "index.html")
app = web.Application()
app.add_routes([web.get("/", index), web.get("/api/state", state), web.post("/sim", ctl), web.static("/static", ROOT / "web")])
web.run_app(app, host="127.0.0.1", port=8799, access_log=None)
