"""Render every scenario x device of design/screens.html to PNG (for the infinity board)."""
import os
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "renders"
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
SCEN = ["onboard", "home", "padoff", "tiny", "live", "celebrate", "milestone", "summary",
        "progress", "awards", "goals", "comeback", "shield"]
DEV = {"desktop": dict(viewport={"width": 1440, "height": 900}), "phone": dict(viewport={"width": 390, "height": 844})}
FULL = {"progress", "awards", "goals", "summary", "home", "padoff", "comeback", "shield"}

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None)
        for dev, kw in DEV.items():
            pg = await b.new_page(device_scale_factor=2, **kw)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            for s in SCEN:
                if ONLY and s not in ONLY:
                    continue
                await pg.goto((HERE / "screens.html").as_uri() + f"?s={s}&d={dev}")
                await pg.wait_for_timeout(1300)   # fonts + entry animations settle
                await pg.screenshot(path=str(OUT / f"{dev}-{s}.png"), full_page=(s in FULL))
            print(dev, "errors:", errs)
        await b.close()

asyncio.run(main())
