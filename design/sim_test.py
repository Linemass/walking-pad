"""Drive the simulated walk in a browser and assert the live moments fire."""
import os
import asyncio, sys
from playwright.async_api import async_playwright
OUT = sys.argv[1]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None)
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto("http://127.0.0.1:8799/")
        seen = set(); shots = 0
        for i in range(70):                                   # ~1 s per simulated minute while moving
            await pg.wait_for_timeout(1000)
            t = await pg.evaluate("document.getElementById('toast').innerText + '|' + (document.querySelector('.toast') ? document.querySelector('.toast').innerText : '') + '|' + (document.querySelector('#overlay h1') ? document.querySelector('#overlay h1').innerText : '') + '|' + (document.querySelector('.livebig') ? 'LIVE' : '')")
            for part in t.split("|"):
                if part and part not in seen:
                    seen.add(part); print(f"t={i:2}s  {part}")
                    if shots < 6 and part != "LIVE":
                        await pg.screenshot(path=f"{OUT}/sim-{shots}.png"); shots += 1
            if i == 40:
                await pg.evaluate("fetch('/sim',{method:'POST',body:JSON.stringify({moving:false})})")
        print("summary shown:", await pg.evaluate("!!document.body.innerText.match(/nicely done/)"))
        await pg.screenshot(path=f"{OUT}/sim-end.png")
        print("errors:", errs)
        await b.close()
asyncio.run(main())
