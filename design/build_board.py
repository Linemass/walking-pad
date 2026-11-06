"""Build the infinity board (Obsidian Canvas): every screen, desktop + phone, linked by the UX flow."""
import json, sys, uuid
from pathlib import Path
from PIL import Image

VAULT = Path(sys.argv[1])
BOARD = Path(sys.argv[2])                      # .../infinity-board
REN = BOARD / "renders"
REL = REN.relative_to(VAULT).as_posix()
nodes, edges = [], []
nid = lambda: uuid.uuid4().hex[:16]

def add(n): nodes.append(n); return n["id"]
def text(x, y, w, h, t, color=None):
    n = {"id": nid(), "type": "text", "text": t, "x": x, "y": y, "width": w, "height": h}
    if color: n["color"] = color
    return add(n)
def img(x, y, w, f):
    W, H = Image.open(REN / f).size
    h = int(w * H / W)
    add({"id": nid(), "type": "file", "file": f"{REL}/{f}", "x": x, "y": y, "width": w, "height": h})
    return h

DW, PW, GAPI, PAD = 760, 250, 40, 30          # desktop width, phone width
GW = PAD * 2 + DW + GAPI + PW                  # group width

def screen(x, y, key, title, note, color):
    gid = nid()
    ny = y + PAD
    text(x + PAD, ny, GW - 2 * PAD, 170, note)
    iy = ny + 190
    text(x + PAD, iy, 200, 50, "**Desktop**"); text(x + PAD + DW + GAPI, iy, 200, 50, "**Phone**")
    dh = img(x + PAD, iy + 56, DW, f"desktop-{key}.png")
    ph = img(x + PAD + DW + GAPI, iy + 56, PW, f"phone-{key}.png")
    h = iy + 56 + max(dh, ph) + PAD - y
    nodes.insert(0, {"id": gid, "type": "group", "label": title, "x": x, "y": y, "width": GW, "height": h, "color": color})
    return gid, h

def link(a, b, label, fs="right", ts="left", color=None):
    e = {"id": nid(), "fromNode": a, "fromSide": fs, "toNode": b, "toSide": ts, "toEnd": "arrow", "label": label}
    if color: e["color"] = color
    edges.append(e)

STEP = GW + 260
# ---- header ----
text(0, -760, 1700, 640,
"""# Walking Pad: infinity board (step 3 of 4)
Direction **C · Playful Bold** · streak style **both** (daily streak kept by a 5-min tiny walk + weekly goal days).

**How to read it:** the top row is the main walking flow, left to right. The middle row is what you reach from the menu. The bottom row is edge states (pad off, missed day, rest shield, milestone). Every step shows **desktop** (1440×900 app window) and **phone** (390 wide) side by side. Arrows are the user flow, labelled with what triggers them.

**Data:** your real history from 1–6 Nov, viewed on the morning of Sat 7 Nov. Bottom-row states marked *what-if* are future examples.

**Review:** move things, add a card with a comment anywhere, or tell me in chat. Nothing is built until you approve this board.""", "6")
text(1760, -760, 1100, 640,
"""## Mechanics on this board
- **Daily goal = minutes:** Tiny 5 · Goal 30 · Stretch 45
- **Daily streak:** kept by the 5-min tiny walk. Earned **rest shields** (1 per 7 walking days, max 2) cover a missed day automatically
- **Week:** 5 goal days of 7, Sunday to Saturday
- **Month:** a challenge of 12 *different* goal days (one binge can't clear it)
- **Comeback day** after a miss counts double toward week and month
- **3 celebration tiers:** micro toasts → 2-s goal takeover → full milestone moment
- **Medals** only for rare things, **personal records** vs your own best, **Walk across Arabia** journey
- **No:** XP on your own goal, leaderboards, guilt copy, more than 1 nudge a day""", "4")

# ---- row 1: main flow ----
row1 = [
 ("onboard", "1 · First run: pick a goal", "**Goal suggested from your own data** (typical day 37 min → 30 min). Adaptive goals beat a fixed 10,000 (Zhou 2018). The streak only needs 5 min; the goal is a separate ring (Duolingo split: +3.3% day-14 retention).", "6"),
 ("home", "2 · Today, pad on, not walking", "**One clear action.** The pad itself is the cue: stepping on starts the session, no button needed. Ring shows tiny marker at 5 min. Week row + November challenge = nested horizons.", "5"),
 ("tiny", "3 · Live: tiny goal reached (5 min)", "**Tier 1 micro-celebration:** a toast at 5 min, *streak safe*. Focus mode turned on by itself when the belt moved (sky blue = live).", "5"),
 ("live", "4 · Live: 75% of the goal", "**Goal-gradient:** the closer you are, the bigger the 'min to go' number and the finish time. Toasts at 25/50/75% and every km. Stops by itself when you step off.", "5"),
 ("celebrate", "5 · Goal reached (30 min)", "**Tier 2:** a 2-second takeover, mascot cheers, confetti, then fades back to the live screen so you can keep walking. Respects reduced-motion.", "4"),
 ("summary", "6 · Walk finished", "**What this walk earned:** goal day, streak, week, journey km. Progress as information, not payment (self-determination theory). Personal records compare you only with yourself.", "4"),
]
ids1 = []
for i, (k, t, nt, c) in enumerate(row1):
    gid, h = screen(i * STEP, 0, k, t, nt, c); ids1.append((gid, h))
labels1 = ["Save goal", "Step on the pad", "Keep walking", "Reach 30 min", "Step off the pad"]
for i, lab in enumerate(labels1):
    link(ids1[i][0], ids1[i + 1][0], lab)
row1_h = max(h for _, h in ids1)

# ---- row 2: menu screens ----
y2 = row1_h + 420
row2 = [
 ("progress", "7 · Progress", "**Consistency made visible:** minutes per day against the goal line, a year heatmap and a month calendar with goal, tiny and shield days. Current against best.", "3"),
 ("awards", "8 · Awards", "**Medals for rare milestones only** (streak 3/7/30/100/365, lifetime km, special moments). **Walk across Arabia:** lifetime km moves you Masmak → Kingdom Centre → Wadi Hanifa → At-Turaif.", "3"),
 ("goals", "9 · Goals & cues", "**Three tiers, adaptive suggestion you accept,** your cue (*After I start my first meeting, I step on*), at most one nudge a day, and pause modes: Ramadan (−40%), travelling, unwell. Paused, never broken.", "3"),
]
ids2 = []
for i, (k, t, nt, c) in enumerate(row2):
    gid, h = screen((i + 1) * STEP, y2, k, t, nt, c); ids2.append((gid, h))
for gid, _ in ids2:
    link(ids1[1][0], gid, "Menu", "bottom", "top", "3")
link(ids1[5][0], ids1[1][0], "Back to Today", "top", "top")
row2_h = max(h for _, h in ids2)

# ---- row 3: edge states ----
y3 = y2 + row2_h + 420
row3 = [
 ("padoff", "E1 · Pad off", "**Sleepy mascot, calm copy.** History is safe on the PC; the pad connects by itself about 20 s after it's switched on.", "1"),
 ("comeback", "E2 · Missed a day (what-if: Tue 10 Nov)", "**Never miss twice:** a comeback day counts double toward week and month. The best performer of 54 interventions in the StepUp megastudy (Milkman 2021). No guilt copy.", "2"),
 ("shield", "E3 · Rest shield used (what-if: Fri 20 Nov)", "**Forgiveness by design:** an earned rest shield covered yesterday automatically. The 12-day streak survives, told kindly.", "2"),
 ("milestone", "E4 · 7-day streak milestone (what-if)", "**Tier 3:** full-screen medal moment. The next milestone (14 days) is visible in advance, so anticipation is part of the reward.", "4"),
]
ids3 = []
for i, (k, t, nt, c) in enumerate(row3):
    gid, h = screen(i * STEP, y3, k, t, nt, c); ids3.append((gid, h))
link(ids3[0][0], ids1[1][0], "Pad switched on", "top", "bottom", "1")
link(ids3[1][0], ids1[2][0], "Step on: 5 min", "top", "bottom", "2")
link(ids3[2][0], ids1[1][0], "Next day", "top", "bottom", "2")
link(ids1[4][0], ids3[3][0], "On day 7 / 30 / 100 / 365", "bottom", "top", "4")

out = BOARD / "Walking Pad Infinity Board.canvas"
out.write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=1), encoding="utf-8")
print(out, len(nodes), "nodes", len(edges), "edges")
