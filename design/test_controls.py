"""Real app (DB copy) with a STUB pad: checks the toast bug fix, start countdown, live controls, pause.
Never talks to the real pad. Usage: python -P design/test_controls.py <screenshot dir>"""
import os
import asyncio, shutil, sys, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
import engine, pad_control
import urevo_logger as L
from aiohttp import web
from playwright.async_api import async_playwright

calls, fails = [], []
def check(c, msg):
    print(("ok   " if c else "FAIL ") + msg)
    if not c: fails.append(msg)

async def fake_command(action, speed=None, user_max=6.0):
    calls.append((action, speed))
    if action == "start":
        pad_control.PAD["paused"] = False
        L.LIVE["last"] = {**(L.LIVE.get("last") or {}), "speed_kmh": pad_control.PAD.get("target_speed") or 1.0, "elapsed_s": 600, "steps": 800, "distance_m": 400}
        L.LIVE["last_ts"] = datetime.now().isoformat(timespec="seconds")
    elif action == "pause":
        pad_control.PAD["paused"] = True; L.LIVE["last"]["speed_kmh"] = 0
    elif action == "stop":
        pad_control.PAD["paused"] = False; L.LIVE["last"]["speed_kmh"] = 0
    elif action == "speed":
        pad_control.PAD["target_speed"] = float(speed); L.LIVE["last"]["speed_kmh"] = float(speed)
        L.LIVE["last_ts"] = datetime.now().isoformat(timespec="seconds")

async def main():
    tmp = Path(tempfile.mkdtemp()) / "c.db"; shutil.copy(ROOT / "tests" / "fixtures" / "sample.db", tmp)
    store = L.Store(tmp); engine.save_settings(store.db, {"onboarded": True})
    L.LIVE.update(connected=True, device={"name": "URTM041"}, status="connected", last={"speed_kmh": 0, "elapsed_s": 0}, last_ts=None)
    pad_control.PAD.update(control=True, speed_range={"min": 1.0, "max": 6.0, "inc": 0.5}, target_speed=None, paused=False)
    pad_control.command = fake_command
    runner = web.AppRunner(L.build_app(store), access_log=None); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8799).start()
    async def keep_fresh():                      # the stub belt keeps "sending" data while it moves
        while True:
            if (L.LIVE["last"] or {}).get("speed_kmh"):
                L.LIVE["last_ts"] = datetime.now().isoformat(timespec="seconds")
            await asyncio.sleep(1)
    fresh = asyncio.create_task(keep_fresh())
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None)
            pg = await b.new_page(viewport={"width": 1440, "height": 900}, color_scheme="dark")
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
            await pg.goto("http://127.0.0.1:8799/"); await pg.wait_for_timeout(1500)
            # ---- toast bug
            await pg.click("[data-go=goals]"); await pg.wait_for_timeout(500)
            inp = pg.locator(".goalcard.main input[data-f=target]")
            await inp.fill("2600"); await inp.press("Tab"); await pg.wait_for_timeout(600)
            await pg.locator(".goalcard.main input[data-f=tiny]").focus()          # keep focus in a text box
            check(await pg.locator("#toast .toast").count() == 1, "'Goal saved' toast appears once")
            await pg.wait_for_timeout(4800)
            check(await pg.locator("#toast .toast").count() == 0, "toast disappears after ~4 s even while a field has focus")
            same = pg.locator(".goalcard.main input[data-f=target]")
            await same.fill("2600"); await same.press("Tab"); await pg.wait_for_timeout(700)
            check(await pg.locator("#toast .toast").count() == 0, "saving the same value again shows no toast")
            # ---- start countdown
            await pg.click("[data-go=today]"); await pg.wait_for_timeout(500)
            await pg.click("[data-act=padstart]"); await pg.wait_for_timeout(300)
            check(await pg.locator(".cdnum").count() == 1, "countdown screen shows")
            await pg.click("[data-act=padcancel]"); await pg.wait_for_timeout(3500)
            check(not any(c[0] == "start" for c in calls), "cancel: start is never sent")
            await pg.click("[data-act=padstart]"); await pg.wait_for_timeout(1500)
            check(not any(c[0] == "start" for c in calls), "start is not sent before the countdown ends")
            await pg.wait_for_timeout(3500)
            check(any(c[0] == "start" for c in calls), "start sent after the countdown")
            await pg.wait_for_timeout(2500)
            check(await pg.locator(".padctl").count() == 1, "live screen shows pad controls")
            await pg.screenshot(path=str(OUT / "controls-live.png"))
            # ---- speed
            await pg.click("[aria-label=Faster]"); await pg.wait_for_timeout(1200)
            check(("speed", 1.5) in calls, f"+ raises speed by the pad's 0.5 step {calls[-1]}")
            await pg.click(".preset >> text=Calls"); await pg.wait_for_timeout(1200)
            check(("speed", 3.5) in calls, "preset 'Calls' sets 3.5 km/h")
            await pg.keyboard.press("ArrowUp"); await pg.wait_for_timeout(1200)
            check(("speed", 4.0) in calls, "ArrowUp key raises speed")
            # ---- pause / resume / stop
            await pg.keyboard.press(" "); await pg.wait_for_timeout(2000)
            check(("pause", None) in calls and await pg.locator(".pausedtag").count() == 1, "Space pauses; paused screen stays up")
            await pg.screenshot(path=str(OUT / "controls-paused.png"))
            await pg.click("[data-act=padresume]"); await pg.wait_for_timeout(2000)
            check(calls[-1][0] == "start" and await pg.locator(".pausedtag").count() == 0, "Resume restarts the belt")
            await pg.click("[data-act=padstop]"); await pg.wait_for_timeout(1500)
            check(calls[-1][0] == "stop", "Stop (with confirm) ends the walk")
            pg2 = await b.new_page(viewport={"width": 390, "height": 844})
            L.LIVE["last"]["speed_kmh"] = 2.5; pad_control.PAD["target_speed"] = 2.5
            await pg2.goto("http://127.0.0.1:8799/"); await pg2.wait_for_timeout(2500)
            await pg2.screenshot(path=str(OUT / "controls-phone.png"), full_page=True)
            wide = await pg2.evaluate("document.documentElement.scrollWidth")
            check(wide <= 391, f"phone live controls fit the screen ({wide}px)")
            check(not errs, f"no page errors {errs}")
            await b.close()
    finally:
        fresh.cancel(); await runner.cleanup()
    print("FAILURES", len(fails))

asyncio.run(main())
