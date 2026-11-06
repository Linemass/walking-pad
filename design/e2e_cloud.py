"""E2E for the hosted phone app, fully local: wrangler dev (Worker + static web app) on :8790 and the real
logger web app (DB COPY, stub pad) on :8799. The 'phone' is a browser at http://padphone.test:8790 (mapped to
127.0.0.1) so the page runs in REMOTE mode. Usage: python -P design/e2e_cloud.py <screenshot dir>"""
import asyncio, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
import engine, pad_control, community_client as cc
import urevo_logger as L
from aiohttp import web
from playwright.async_api import async_playwright

CW = ROOT / "community"; SERVER = "http://127.0.0.1:8790"; PERSIST = ".wrangler/e2e-cloud"
fails, calls = [], []
def check(c, msg):
    print(("ok   " if c else "FAIL ") + msg)
    if not c: fails.append(msg)

async def fake_command(action, speed=None, user_max=6.0):
    calls.append((action, speed))
    if action == "speed": pad_control.PAD["target_speed"] = float(speed)

def start_worker():
    subprocess.run([sys.executable, "-P", str(CW / "tools" / "build_web.py")], check=True, capture_output=True)
    shutil.rmtree(CW / PERSIST, ignore_errors=True)
    npx = "npx.cmd" if os.name == "nt" else "npx"
    subprocess.run([npx, "wrangler", "d1", "migrations", "apply", "DB", "--local", "--persist-to", PERSIST], cwd=CW, check=True, capture_output=True, input=b"y\n")
    p = subprocess.Popen([npx, "wrangler", "dev", "--local", "--port", "8790", "--persist-to", PERSIST, "--ip", "127.0.0.1"],
                         cwd=CW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(90):
        try:
            if cc.call(SERVER, "GET", "/v1/health").get("ok"): return p
        except cc.CommunityError:
            time.sleep(1)
    raise SystemExit("worker did not start")

async def main():
    worker = start_worker()
    tmp = Path(tempfile.mkdtemp()) / "cloud.db"; shutil.copy(ROOT / "tests" / "fixtures" / "sample.db", tmp)
    store = L.Store(tmp)
    engine.save_settings(store.db, {"onboarded": True})
    r = cc.call(SERVER, "POST", "/v1/register", None, {"handle": "mohammed", "display_name": "Mohammed"})
    engine.save_community(store.db, {"enabled": True, "server": SERVER, "user_id": r["user_id"], "handle": "mohammed", "display_name": "Mohammed", "token": r["token"]})
    L.LIVE.update(connected=True, device={"name": "URTM041"}, status="connected", last={"speed_kmh": 0}, last_ts=None)
    pad_control.PAD.update(control=True, speed_range={"min": 1.0, "max": 6.0, "inc": 0.5}, paused=False)
    pad_control.command = fake_command
    runner = web.AppRunner(L.build_app(store), access_log=None); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8799).start()
    link = asyncio.create_task(L.cloud_forever())
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None, args=["--host-resolver-rules=MAP padphone.test 127.0.0.1"])
            pc = await b.new_page(viewport={"width": 1440, "height": 900})
            errs = []; pc.on("pageerror", lambda e: errs.append("pc: " + str(e)))
            await pc.goto("http://127.0.0.1:8799/"); await pc.wait_for_timeout(1200)
            await pc.click("[data-go=goals]"); await pc.wait_for_timeout(600)
            await pc.click("[data-act=pair]"); await pc.wait_for_timeout(2500)
            code = (await pc.locator(".paircode .code").inner_text()).strip()
            check(len(code) == 6, f"PC shows a pairing code {code}")
            await pc.screenshot(path=str(OUT / "pc-pair.png"), full_page=True)

            ph = await b.new_page(viewport={"width": 390, "height": 844})
            ph.on("pageerror", lambda e: errs.append("phone: " + str(e)))
            ph.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
            await ph.goto("http://padphone.test:8790/"); await ph.wait_for_timeout(1500)
            check(await ph.locator("#pcode").count() == 1, "phone opens on the pairing screen")
            await ph.fill("#pcode", "WRONG1"); await ph.click("[data-act=claim]"); await ph.wait_for_timeout(1200)
            check("didn't work" in (await ph.inner_text("body")) or "wrong" in (await ph.inner_text("body")), "a wrong code is refused with a message")
            await ph.fill("#pcode", code.lower()); await ph.click("[data-act=claim]"); await ph.wait_for_timeout(6000)
            check(await ph.locator(".ringc").count() == 1, "after linking, the phone shows Today from the PC")
            check("Live from your PC" in await ph.inner_text("body") or "Synced from your PC" in await ph.inner_text("body"), "phone says the data comes from the PC")
            await ph.screenshot(path=str(OUT / "phone-today.png"), full_page=True)
            # goal edit on the phone -> applied by the PC
            await ph.click(".tab[data-go=goals]"); await ph.wait_for_timeout(800)
            inp = ph.locator(".goalcard.main input[data-f=target]")
            await inp.fill("6500"); await inp.press("Tab"); t0 = time.monotonic()
            while time.monotonic() - t0 < 25 and engine.main_goal(engine.load_settings(store.db))["target"] != 6500:
                await asyncio.sleep(.5)
            check(engine.main_goal(engine.load_settings(store.db))["target"] == 6500, f"goal edited on the phone is applied on the PC after {time.monotonic() - t0:.1f}s")
            await ph.screenshot(path=str(OUT / "phone-goals.png"), full_page=True)
            # Apple Health guide + simulated Shortcut calls with the phone's own token
            await ph.click("[data-go=health]"); await ph.wait_for_timeout(800)
            body = await ph.inner_text("body")
            check("/v1/health/export" in body and "Bearer " in body, "Apple Health guide shows URLs and the header value")
            await ph.screenshot(path=str(OUT / "phone-health.png"), full_page=True)
            dtok = await ph.evaluate("JSON.parse(localStorage.getItem('wp.device')).token")
            ex = cc.call(SERVER, "GET", "/v1/health/export", dtok)
            check(ex["count"] > 0 and "start" in ex["items"][0] and "+" in ex["items"][0]["start"], f"Shortcut export lists pad walks with time zone ({ex['count']})")
            cc.call(SERVER, "POST", "/v1/health/ack", dtok, {"ids": ex["ids"]})
            check(cc.call(SERVER, "GET", "/v1/health/export", dtok)["count"] == 0, "acked walks are not exported twice")
            cc.call(SERVER, "POST", "/v1/health/import", dtok, {"date": datetime.now().date().isoformat(), "steps": "8,120"})
            t0 = time.monotonic()
            while time.monotonic() - t0 < 25 and engine.compute(store.db, L.LIVE)["health"]["today"] != 8120:
                await asyncio.sleep(.5)
            print(f"     health reached the PC after {time.monotonic() - t0:.1f}s")
            st = engine.compute(store.db, L.LIVE)
            check(st["health"]["today"] == 8120, f"steps read from Health reach the PC ({st['health']})")
            # pad speed from the phone (live screen)
            L.LIVE["last"] = {"speed_kmh": 2.5, "elapsed_s": 300, "steps": 400, "distance_m": 200}
            for _ in range(8):
                L.LIVE["last_ts"] = datetime.now().isoformat(timespec="seconds"); await asyncio.sleep(1)
            await ph.wait_for_timeout(3000)
            check(await ph.locator(".padctl").count() == 1, "phone shows pad controls while walking")
            await ph.screenshot(path=str(OUT / "phone-live.png"), full_page=True)
            await ph.click("[aria-label=Faster]")
            for _ in range(10):
                L.LIVE["last_ts"] = datetime.now().isoformat(timespec="seconds"); await asyncio.sleep(1)
                if ("speed", 3.0) in calls: break
            check(("speed", 3.0) in calls, f"speed + on the phone reaches the pad through the PC {calls}")
            # unlink from the PC locks the phone out
            await pc.reload(); await pc.wait_for_timeout(800); await pc.click("[data-go=goals]"); await pc.wait_for_timeout(1500)
            pc.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
            await pc.click("[data-act=revoke] >> nth=0"); await pc.wait_for_timeout(1500)
            await ph.reload(); await ph.wait_for_timeout(4000)
            check(await ph.locator("#pcode").count() == 1, "after unlinking on the PC the phone is back on the pairing screen")
            check(not errs, f"no page errors {errs}")
            await b.close()
    finally:
        link.cancel(); await runner.cleanup()
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(worker.pid)], capture_output=True)
    print("FAILURES", len(fails))

asyncio.run(main())
