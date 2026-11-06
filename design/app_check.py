"""Overlap/overflow check on the REAL app pages (served by sim_server on :8799), desktop + phone."""
import os
import asyncio, re, sys
from pathlib import Path
from playwright.async_api import async_playwright
JS = re.search(r'JS = r"""(.*?)"""', (Path(__file__).parent / "overlap_check.py").read_text(encoding="utf-8"), re.S).group(1)
OUT = sys.argv[1]
async def main():
    total = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None)
        for dev, vp in {"desktop": {"width": 1440, "height": 900}, "phone": {"width": 390, "height": 844}}.items():
            pg = await b.new_page(viewport=vp, device_scale_factor=2)
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto("http://127.0.0.1:8799/"); await pg.wait_for_timeout(1500)
            for route in ["today", "progress", "awards", "goals"]:
                await pg.click(f"[data-go={route}]"); await pg.wait_for_timeout(700)
                found = await pg.evaluate(JS)
                for f in found: print(f"{dev:7} {route:9} {f['kind']:12} {f['a']} <> {f['b']}")
                total += len(found)
                await pg.screenshot(path=f"{OUT}/app-{dev}-{route}.png", full_page=True)
            print(dev, "errors:", errs)
        await b.close()
    print("TOTAL", total)
asyncio.run(main())
