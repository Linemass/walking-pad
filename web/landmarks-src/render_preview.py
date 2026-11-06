"""Screenshot web/landmarks-preview.html with Playwright (Edge).
Usage: python -P render_preview.py OUT_DIR
"""
import asyncio, os, sys, pathlib
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = (HERE.parent / "landmarks-preview.html").as_uri()


async def main(out):
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge")
        pg = await b.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(PAGE)
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(out, "preview_full.png"), full_page=True)
        await pg.locator("#light").screenshot(path=os.path.join(out, "icons_light.png"))
        await pg.locator("#dark").screenshot(path=os.path.join(out, "icons_dark.png"))
        await pg.locator("#map").screenshot(path=os.path.join(out, "map.png"))
        big = await b.new_page(viewport={"width": 1000, "height": 700}, device_scale_factor=2)
        await big.goto(PAGE)
        await big.locator("#light").screenshot(path=os.path.join(out, "icons_light_2x.png"))
        print("errors:", errs)
        await b.close()

asyncio.run(main(sys.argv[1]))
