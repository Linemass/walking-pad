"""Find UI bugs on every screen: text overlapping other text, and text overflowing its box.
Usage: python -P overlap_check.py [scenario,scenario]   (exit code 1 when anything is found)"""
import os
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
SCEN = ["onboard", "home", "padoff", "tiny", "live", "celebrate", "milestone", "summary",
        "progress", "awards", "map", "goals", "community", "cjoin", "comeback", "shield", "bigsteps"]
DEV = {"desktop": {"width": 1440, "height": 900}, "phone": {"width": 390, "height": 844}}

JS = r"""
() => {
  const out = [];
  const name = el => (el.className && typeof el.className === "string" ? "." + el.className.split(" ")[0] : el.tagName.toLowerCase())
                     + " '" + (el.textContent || "").trim().slice(0, 28) + "'";
  // text boxes = rects of every non-empty text node
  const boxes = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const t = w.currentNode; if (!t.textContent.trim()) continue;
    const el = t.parentElement; const cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || +cs.opacity === 0) continue;
    if (el.closest(".confetti,svg")) continue;                  // decorative
    const r = document.createRange(); r.selectNodeContents(t);
    // clip to the nearest ancestor that hides overflow (ellipsis text is not visible past its box)
    let clip = null; for (let a = el; a && a !== document.body; a = a.parentElement) { if (getComputedStyle(a).overflow !== "visible") { clip = a.getBoundingClientRect(); break; } }
    for (let b of r.getClientRects()) {
      if (clip) b = { left: Math.max(b.left, clip.left), right: Math.min(b.right, clip.right), top: Math.max(b.top, clip.top), bottom: Math.min(b.bottom, clip.bottom) };
      const w = b.right - b.left, h = b.bottom - b.top;
      if (w > 1 && h > 1) boxes.push({ el, b: { left: b.left, right: b.right, top: b.top, bottom: b.bottom, width: w, height: h } });
    }
  }
  const inter = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const A = boxes[i], B = boxes[j]; if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) continue;
    const area = inter(A.b, B.b), min = Math.min(A.b.width * A.b.height, B.b.width * B.b.height);
    if (area > 0.15 * min) out.push({ kind: "overlap", a: name(A.el), b: name(B.el) });
  }
  // text that pokes out of its own box, or a box that spills out of a card
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest("svg,.confetti")) continue;
    const cs = getComputedStyle(el);
    if (cs.overflow !== "visible" || el.scrollWidth <= el.clientWidth + 2) continue;
    if (el.clientWidth === 0) continue;
    out.push({ kind: "overflow-x", a: name(el), b: `${el.scrollWidth} > ${el.clientWidth}` });
  }
  for (const card of document.querySelectorAll(".card,.stat,.opt,.chip,.btn,.tier,.pace,.banner,.sumrow div")) {
    const c = card.getBoundingClientRect();
    for (const ch of card.querySelectorAll("*")) {
      if (ch.closest("svg")) continue;
      const r = ch.getBoundingClientRect(); if (!r.width) continue;
      if (r.right > c.right + 1 || r.left < c.left - 1) { out.push({ kind: "spill", a: name(ch), b: "out of " + name(card) }); break; }
    }
  }
  // ring centre text must sit inside the inner circle of the ring (founder bug, 6 Nov)
  for (const wrap of document.querySelectorAll(".ringwrap")) {
    const svg = wrap.querySelector("svg.ring"), trk = svg && svg.querySelector("circle.trk"); if (!trk) continue;
    const sb = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, k = sb.width / vb.width;
    const cx = sb.left + sb.width / 2, cy = sb.top + sb.height / 2;
    const rin = (trk.r.baseVal.value - (+trk.getAttribute("stroke-width")) / 2) * k - 2;
    const tw = document.createTreeWalker(wrap.querySelector(".ringc"), NodeFilter.SHOW_TEXT);
    while (tw.nextNode()) { const t = tw.currentNode; if (!t.textContent.trim()) continue;
      const r = document.createRange(); r.selectNodeContents(t);
      for (const b of r.getClientRects()) {
        const far = Math.max(...[[b.left, b.top + 3], [b.right, b.top + 3], [b.left, b.bottom - 3], [b.right, b.bottom - 3]].map(([x, y]) => Math.hypot(x - cx, y - cy)));
        if (far > rin) out.push({ kind: "ring-text", a: name(t.parentElement), b: `reaches ${far.toFixed(0)}px of inner ${rin.toFixed(0)}px` });
      } }
  }
  // phone: nothing may be wider than the viewport
  if (document.documentElement.scrollWidth > innerWidth + 1) out.push({ kind: "page-scroll-x", a: "page", b: `${document.documentElement.scrollWidth}px` });
  const seen = new Set(); return out.filter(o => { const k = JSON.stringify(o); if (seen.has(k)) return false; seen.add(k); return true; });
}
"""

async def main():
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else SCEN
    total = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge" if os.name == "nt" else None)
        for theme in ("light", "dark"):
          for dev, vp in DEV.items():
            pg = await b.new_page(viewport=vp, color_scheme=theme)
            for s in only:
                await pg.goto((HERE / "screens.html").as_uri() + f"?s={s}&d={dev}&theme={theme}")
                await pg.wait_for_timeout(900)
                found = await pg.evaluate(JS)
                for f in found:
                    print(f"{theme:5} {dev:7} {s:10} {f['kind']:13} {f['a']}  <>  {f['b']}")
                total += len(found)
        await b.close()
    print("TOTAL", total)
    sys.exit(1 if total else 0)

asyncio.run(main())
