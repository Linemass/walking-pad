"""End-to-end: real logger web app (DB COPY, no Bluetooth) on :8799 + real community Worker (wrangler dev --local) on :8790,
driven in Edge. Usage: python -P design/e2e.py <screenshot dir>"""
import asyncio, os, shutil, sqlite3, subprocess, sys, tempfile, time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
import engine, community_client as cc
import urevo_logger as L
from aiohttp import web
from playwright.async_api import async_playwright

CW = ROOT / "community"; SERVER = "http://127.0.0.1:8790"; PERSIST = ".wrangler/e2e"
fails = []
def check(c, msg):
    print(("ok   " if c else "FAIL ") + msg)
    if not c: fails.append(msg)

def start_worker():
    shutil.rmtree(CW / PERSIST, ignore_errors=True)
    npx = "npx.cmd" if os.name == "nt" else "npx"
    subprocess.run([npx, "wrangler", "d1", "migrations", "apply", "DB", "--local", "--persist-to", PERSIST], cwd=CW, check=True,
                   capture_output=True, input=b"y\n")
    p = subprocess.Popen([npx, "wrangler", "dev", "--local", "--port", "8790", "--persist-to", PERSIST, "--ip", "127.0.0.1"],
                         cwd=CW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    for _ in range(90):
        try:
            if cc.call(SERVER, "GET", "/v1/health").get("ok"): return p
        except cc.CommunityError:
            time.sleep(1)
    raise SystemExit("worker did not start")

async def main():
    worker = start_worker()
    tmp = Path(tempfile.mkdtemp()) / "e2e.db"; shutil.copy(ROOT / "tests" / "fixtures" / "sample.db", tmp)
    store = L.Store(tmp)
    engine.save_settings(store.db, {"onboarded": True})
    engine.save_community(store.db, {"server": SERVER})
    L.LIVE.update(connected=True, device={"name": "URTM041"}, status="connected")
    runner = web.AppRunner(L.build_app(store), access_log=None); await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8799).start()
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None)
            pg = await b.new_page(viewport={"width": 1440, "height": 900})
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto("http://127.0.0.1:8799/"); await pg.wait_for_timeout(1500)
            check(await pg.locator(".ringc").inner_text() != "", "today renders with the steps ring")
            check("steps" in (await pg.locator(".ringc small").inner_text()), "main goal is steps")
            # ---- goals: add a goal, switch its measure, type a number
            await pg.click("[data-go=goals]"); await pg.wait_for_timeout(500)
            n0 = await pg.locator(".goalcard").count()
            await pg.click("[data-act=gadd]"); await pg.wait_for_timeout(600)
            check(await pg.locator(".goalcard").count() == n0 + 1, "add goal")
            last = pg.locator(".goalcard").last
            await last.locator("[data-act=gmetric][data-v=km]").click(); await pg.wait_for_timeout(600)
            last = pg.locator(".goalcard").last
            inp = last.locator("input[data-f=target]")
            await inp.fill("8.5"); await inp.press("Enter"); await pg.wait_for_timeout(800)
            gs = engine.load_settings(store.db)["goals"]
            check(gs[-1]["metric"] == "km" and gs[-1]["period"] == "week" and gs[-1]["target"] == 8.5, f"custom weekly km goal saved {gs[-1]}")
            main = pg.locator(".goalcard.main input[data-f=target]")
            await main.fill("3200"); await main.press("Enter"); await pg.wait_for_timeout(800)
            check(engine.main_goal(engine.load_settings(store.db))["target"] == 3200, "main steps goal edited to 3200")
            await pg.screenshot(path=str(OUT / "e2e-goals.png"), full_page=True)
            # ---- progress
            await pg.click("[data-go=progress]"); await pg.wait_for_timeout(500)
            await pg.click("[data-act=barmetric][data-v=km]"); await pg.wait_for_timeout(300)
            check("Kilometres per day" in await pg.inner_text("main"), "progress chart switches to km")
            check("avg steps per walking day" in await pg.inner_text("main"), "averages shown")
            # ---- tracks + map
            await pg.click("[data-go=awards]"); await pg.wait_for_timeout(500)
            check("Walk across Saudi Arabia" in await pg.inner_text("main"), "journey renamed")
            await pg.click("[data-act=map] >> nth=0"); await pg.wait_for_timeout(600)
            await pg.click("[data-act=track][data-v=jeddah]"); await pg.wait_for_timeout(800)
            check(engine.load_settings(store.db)["track"]["id"] == "jeddah", "track switched to Jeddah seafront")
            await pg.screenshot(path=str(OUT / "e2e-map.png"), full_page=True)
            # ---- community: join, make a group
            await pg.click("[data-go=community]"); await pg.wait_for_timeout(500)
            await pg.fill("#chandle", "mohammed"); await pg.fill("#cname", "Mohammed")
            await pg.click("[data-act=cjoin]"); await pg.wait_for_timeout(2500)
            c = engine.load_settings(store.db)["community"]
            check(c["enabled"] and c["handle"] == "mohammed" and c["token"], "joined community; token kept in local DB")
            check(c["token"] not in await pg.content(), "token never reaches the page")
            await pg.fill("#gname", "DCSI walkers"); await pg.click("[data-act=gcreate]"); await pg.wait_for_timeout(1500)
            me = cc.call(SERVER, "GET", "/v1/me", c["token"]); code = me["groups"][0]["invite_code"]
            check(bool(code), f"group created with invite code {code}")
            # two friends join with the code and sync walks
            today = date.today()
            for h, nm, steps in (("noura_a", "Noura A", 4200), ("faisal", "Faisal K", 1800)):
                r = cc.call(SERVER, "POST", "/v1/register", None, {"handle": h, "display_name": nm})
                cc.call(SERVER, "POST", "/v1/groups/join", r["token"], {"invite_code": code.lower()})
                cc.call(SERVER, "POST", "/v1/sync", r["token"], {"days": [{"date": (today - timedelta(days=i)).isoformat(), "steps": steps, "minutes": steps / 70, "km": steps * .0006, "goal_met": steps > 2500} for i in range(3)], "streak": 3})
            await pg.click(f"[data-act=lscope][data-v='group:{me['groups'][0]['group_id']}']"); await pg.wait_for_timeout(1500)
            rows = await pg.locator(".lbrow").all_inner_texts()
            check(len(rows) >= 3 and "Noura A" in rows[0], f"group leaderboard ranks friends: {[r.split(chr(10))[1] if chr(10) in r else r for r in rows][:3]}")
            await pg.click("[data-act=lmetric][data-v=goal_days]"); await pg.wait_for_timeout(1200)
            check(await pg.locator(".lbrow").count() >= 3, "goal-days leaderboard loads")
            await pg.screenshot(path=str(OUT / "e2e-community.png"), full_page=True)
            pg2 = await b.new_page(viewport={"width": 390, "height": 844})
            await pg2.goto("http://127.0.0.1:8799/"); await pg2.wait_for_timeout(1500)
            await pg2.click(".tab[data-go=community]"); await pg2.wait_for_timeout(1800)
            await pg2.screenshot(path=str(OUT / "e2e-community-phone.png"), full_page=True)
            # ---- leave: server data deleted
            pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
            await pg.click("[data-act=cleave]"); await pg.wait_for_timeout(1500)
            try:
                cc.call(SERVER, "GET", "/v1/me", c["token"]); check(False, "leaving deletes the account")
            except cc.CommunityError as e:
                check(e.status == 401, "leaving deletes the account on the server")
            check(not engine.load_settings(store.db)["community"]["enabled"], "local community settings cleared")
            check(not errs, f"no page errors {errs}")
            await b.close()
    finally:
        await runner.cleanup()
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(worker.pid)], capture_output=True)
    print("FAILURES", len(fails))

asyncio.run(main())
