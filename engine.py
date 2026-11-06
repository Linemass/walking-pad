"""Habit engine: turns sessions in urevo.db into the full app state the UI renders.

Rules (approved on the infinity board 2026-11-06, extended the same day):
- Goals are fully customizable: any number of goals (1..8), each on steps, minutes or km,
  per day or per week, with any target. ONE daily goal is the main goal: it drives the ring,
  the streak and "goal days". Each daily goal has a tiny level (keeps the streak when it is
  the main goal) and a stretch level.
- Rest shields: earn 1 per 7 streak days, hold max 2; a missed day uses one automatically.
- Pause modes (travel, unwell) mark days as paused. Ramadan lowers daily targets by 40%.
- Week = Sunday..Saturday, target = N goal days. Month challenge = M goal days.
- Comeback day: a goal day right after an unprotected miss counts double toward week and month.
- Past days are judged by the main goal that applied on that day (goal history).
"""
import json
import statistics
import uuid
from datetime import date, datetime, timedelta

BOGUS_SESSIONS = ()   # per install: settings key "excluded_sessions" (see excluded())
STREAK_MEDALS = [3, 7, 30, 100, 365]
NEXT_STREAK = [3, 7, 14, 30, 60, 100, 180, 365, 730]
DIST_MEDALS = [5, 10, 25, 50, 100, 250, 500, 1000]
# Walk across Saudi Arabia: places (approximate coordinates) and preset tracks. Distances are the
# straight-line distance between consecutive landmarks (haversine), so they are honest and reproducible.
PLACES = {
    "masmak": ("Masmak Fortress", "Riyadh", 24.6312, 46.7133), "murabba": ("Al Murabba Palace", "Riyadh", 24.6475, 46.7106),
    "museum": ("National Museum", "Riyadh", 24.6475, 46.7101), "kingdom": ("Kingdom Centre", "Riyadh", 24.7113, 46.6744),
    "boulevard": ("Riyadh Boulevard", "Riyadh", 24.7680, 46.6000), "wadi": ("Wadi Hanifa", "Riyadh", 24.6600, 46.6000),
    "turaif": ("At-Turaif, Diriyah", "Diriyah", 24.7335, 46.5727), "edge": ("Edge of the World", "Jebel Fihrayn", 24.9500, 45.9900),
    "ushaiqer": ("Ushaiqer Heritage Village", "Ushaiqer", 25.3425, 45.1833), "buraydah": ("Buraydah date market", "Buraydah", 26.3260, 43.9750),
    "hail": ("Jubbah rock art", "Hail", 27.5219, 41.6907), "alula": ("Elephant Rock", "AlUla", 26.6892, 37.9817),
    "hegra": ("Hegra", "AlUla", 26.7920, 37.9530), "balad": ("Al-Balad", "Jeddah", 21.4858, 39.1925),
    "fountain": ("King Fahd Fountain", "Jeddah", 21.5146, 39.1500), "jtower": ("Jeddah Corniche", "Jeddah", 21.6000, 39.1100),
    "dammam": ("Dammam Corniche", "Dammam", 26.4430, 50.1150), "taif": ("Taif rose farms", "Taif", 21.2700, 40.4160),
    "abha": ("Abha", "Abha", 18.2160, 42.5050),
}
TRACKS = [
    {"id": "old-riyadh", "name": "Old Riyadh loop", "desc": "A first short walk through historic Riyadh.", "stops": ["masmak", "murabba", "museum", "kingdom"]},
    {"id": "riyadh-diriyah", "name": "Riyadh to Diriyah", "desc": "From Masmak to the UNESCO site of At-Turaif.", "stops": ["masmak", "kingdom", "wadi", "turaif"]},
    {"id": "edge", "name": "To the Edge of the World", "desc": "Diriyah to the cliffs of Jebel Fihrayn.", "stops": ["turaif", "edge"]},
    {"id": "jeddah", "name": "Jeddah seafront", "desc": "Al-Balad to the Corniche along the Red Sea.", "stops": ["balad", "fountain", "jtower"]},
    {"id": "najd", "name": "Heart of Najd", "desc": "Riyadh north through Ushaiqer and Buraydah to Hail.", "stops": ["masmak", "ushaiqer", "buraydah", "hail"]},
    {"id": "alula", "name": "Hail to AlUla", "desc": "Rock art to Elephant Rock and Hegra.", "stops": ["hail", "alula", "hegra"]},
    {"id": "south", "name": "Mountains of the south", "desc": "Taif rose farms to the Abha highlands.", "stops": ["taif", "abha"]},
    {"id": "coast", "name": "Coast to coast", "desc": "The Gulf to the Red Sea, across the Kingdom.", "stops": ["dammam", "masmak", "taif", "balad"]},
]
WD = "SMTWTFS"

METRICS = {
    "steps":   {"unit": "steps", "max": 150000, "inc": 500, "round": 250, "tiny": 500},
    "minutes": {"unit": "min",   "max": 1440,   "inc": 5,   "round": 5,   "tiny": 5},
    "km":      {"unit": "km",    "max": 200,    "inc": .5,  "round": .25, "tiny": .3},
    # all-day steps from Apple Health (phone + watch + pad); falls back to pad steps when Health has no number
    "allsteps": {"unit": "steps", "max": 150000, "inc": 1000, "round": 250, "tiny": 2000},
}

DEFAULT_GOALS = [
    {"id": "steps", "metric": "steps", "period": "day", "target": 2500, "tiny": 500, "stretch": 4000, "primary": True},
    {"id": "minutes", "metric": "minutes", "period": "day", "target": 30, "tiny": 5, "stretch": 45, "primary": False},
]
DEFAULTS = {
    "onboarded": False, "week_goal": 5, "month_goal": 12,
    "goals": None,                 # None = not migrated yet (see load_settings)
    "cue": "start my first meeting of the day",
    "nudge": {"on": True, "time": "16:00"},
    "modes": {"ramadan": False, "travel": False, "sick": False},
    "mode_days": {},
    "goal_history": [],            # [{"from": "YYYY-MM-DD", "metric", "tiny", "goal", "stretch"}] for the MAIN goal
    "track": {"id": "riyadh-diriyah", "custom": [], "start_km": 0.0, "done": []},
    "community": {"enabled": False, "server": "https://walking-pad-staging.walking-pad-community.workers.dev", "user_id": None, "handle": None,
                  "display_name": None, "token": None, "public": False, "last_sync": None},
}


# ------------------------------------------------------------------ settings

def _put(db, k, v):
    db.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (k, json.dumps(v)))


def load_settings(db):
    db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    s = json.loads(json.dumps(DEFAULTS))
    raw = {k: json.loads(v) for k, v in db.execute("SELECT key, value FROM settings")}
    s.update({k: v for k, v in raw.items() if k in DEFAULTS})
    s["community"] = {**DEFAULTS["community"], **(raw.get("community") or {})}
    s["track"] = {**DEFAULTS["track"], **(raw.get("track") or {})}
    if s["goals"] is None:
        # migrate v3 (one minutes goal) -> v4 goal list: steps becomes the main goal (founder preference),
        # the existing minutes goal is kept as a second goal.
        goals = json.loads(json.dumps(DEFAULT_GOALS))
        if "goal" in raw:
            goals[1].update(target=raw["goal"], tiny=raw.get("tiny", 5), stretch=raw.get("stretch", raw["goal"] + 15))
        hist = [{**h, "metric": h.get("metric", "minutes")} for h in raw.get("goal_history", [])]
        if not hist and "goal" in raw:
            hist = [{"from": "0000-01-01", "metric": "minutes", "tiny": raw.get("tiny", 5), "goal": raw["goal"], "stretch": raw.get("stretch", 45)}]
        if raw.get("onboarded"):
            hist.append({"from": date.today().isoformat(), "metric": "steps", "tiny": 500, "goal": 2500, "stretch": 4000})
        s["goals"], s["goal_history"] = goals, sorted(hist, key=lambda h: h["from"])
        _put(db, "goals", s["goals"]); _put(db, "goal_history", s["goal_history"]); db.commit()
    return s


def _num(metric, v, lo=0.0):
    v = float(v)
    if not (v == v) or v < lo:           # NaN or negative
        raise ValueError("numbers must be positive")
    v = min(v, METRICS[metric]["max"])
    return int(round(v)) if metric != "km" else round(v, 2)


def clean_goals(goals):
    if not isinstance(goals, list) or not 1 <= len(goals) <= 8:
        raise ValueError("keep between 1 and 8 goals")
    out = []
    for g in goals:
        m = g.get("metric")
        if m not in METRICS:
            raise ValueError("metric must be steps, minutes or km")
        period = "week" if g.get("period") == "week" else "day"
        target = _num(m, g.get("target", 0))
        if target <= 0:
            raise ValueError("a goal needs a target above zero")
        x = {"id": str(g.get("id") or uuid.uuid4().hex[:8])[:16], "metric": m, "period": period,
             "target": min(target, METRICS[m]["max"] * (7 if period == "week" else 1)), "primary": bool(g.get("primary")) and period == "day"}
        if period == "day":
            x["tiny"] = min(_num(m, g.get("tiny", METRICS[m]["tiny"])), target)
            x["stretch"] = max(_num(m, g.get("stretch", target * 1.5)), target)
        out.append(x)
    daily = [g for g in out if g["period"] == "day"]
    if not daily:
        raise ValueError("keep at least one daily goal: it drives your streak")
    prim = [g for g in daily if g["primary"]]
    for g in out:
        g["primary"] = False
    (prim[0] if prim else daily[0])["primary"] = True
    return out


def save_settings(db, patch, today=None):
    """Merge a patch from the UI. Raises ValueError for bad input (the API answers 400)."""
    s = load_settings(db)
    today = (today or date.today()).isoformat()
    old_main = main_goal(s)
    changed = set()
    if "goals" in patch:
        s["goals"] = clean_goals(patch["goals"]); changed.add("goals")
    for k, lim in (("week_goal", (1, 7)), ("month_goal", (1, 31))):
        if k in patch:
            s[k] = max(lim[0], min(lim[1], int(patch[k]))); changed.add(k)
    if "cue" in patch:
        s["cue"] = str(patch["cue"]).strip()[:120] or s["cue"]; changed.add("cue")
    if "onboarded" in patch:
        s["onboarded"] = bool(patch["onboarded"]); changed.add("onboarded")
    if "nudge" in patch and isinstance(patch["nudge"], dict):
        n = {**s["nudge"], **{k: v for k, v in patch["nudge"].items() if k in ("on", "time")}}
        n["on"] = bool(n["on"])
        try:
            datetime.strptime(str(n["time"]), "%H:%M")
        except ValueError:
            n["time"] = s["nudge"]["time"]
        s["nudge"] = n; changed.add("nudge")
    if "modes" in patch and isinstance(patch["modes"], dict):
        s["modes"] = {**s["modes"], **{k: bool(v) for k, v in patch["modes"].items() if k in s["modes"]}}; changed.add("modes")
    new_main = main_goal(s)
    key = lambda g: (g["metric"], g["tiny"], g["target"], g["stretch"])
    if key(new_main) != key(old_main):
        hist = s["goal_history"] or [{"from": "0000-01-01", "metric": old_main["metric"], "tiny": old_main["tiny"],
                                      "goal": old_main["target"], "stretch": old_main["stretch"]}]
        hist = [h for h in hist if h["from"] != today]
        hist.append({"from": today, "metric": new_main["metric"], "tiny": new_main["tiny"], "goal": new_main["target"], "stretch": new_main["stretch"]})
        s["goal_history"] = sorted(hist, key=lambda h: h["from"]); changed.add("goal_history")
    for k in changed:
        _put(db, k, s[k])
    db.commit()
    return s


def save_community(db, patch):
    s = load_settings(db)
    s["community"] = {**s["community"], **patch}
    _put(db, "community", s["community"]); db.commit()
    return s["community"]


def record_mode_day(db, s, today):
    mode = "travel" if s["modes"].get("travel") else "sick" if s["modes"].get("sick") else None
    key = today.isoformat()
    if mode and s["mode_days"].get(key) != mode:
        s["mode_days"][key] = mode
        _put(db, "mode_days", s["mode_days"]); db.commit()


# ------------------------------------------------------------------ helpers

def main_goal(s):
    return next(g for g in s["goals"] if g["primary"])


def rnd(metric, v):
    q = METRICS[metric]["round"]
    v = q * round(v / q)
    return int(v) if metric != "km" else round(v, 2)


def fmtv(metric, v):
    if metric in ("steps", "allsteps"):
        return f"{int(round(v)):,}"
    if metric == "km":
        return f"{v:.2f}".rstrip("0").rstrip(".") if v < 100 else f"{v:.0f}"
    return f"{v:.1f}".rstrip("0").rstrip(".")


def fmtu(metric, v):
    return f"{fmtv(metric, v)} {METRICS[metric]['unit']}"


def val(t, metric):
    if metric == "allsteps":
        return max(t.get("health", 0) or 0, t["steps"])
    return t["steps"] if metric == "steps" else t["min"] if metric == "minutes" else t["distance_m"] / 1000


def ensure_health(db):
    db.execute("CREATE TABLE IF NOT EXISTS health_days (date TEXT PRIMARY KEY, steps INTEGER NOT NULL, km REAL, updated_at TEXT NOT NULL)")


def save_health(db, day, steps, km=None):
    """All-day totals read from Apple Health (arrive from the phone through the cloud command queue)."""
    ensure_health(db)
    d = date.fromisoformat(str(day)[:10]).isoformat()
    steps = max(0, min(150000, int(steps)))
    db.execute("INSERT INTO health_days(date, steps, km, updated_at) VALUES(?,?,?,?) ON CONFLICT(date) DO UPDATE SET "
               "steps=excluded.steps, km=excluded.km, updated_at=excluded.updated_at", (d, steps, km, datetime.now().isoformat(timespec="seconds")))
    db.commit()


def health_export(db, live_session=None, days=14):
    """Pad walks for Apple Health (Shortcuts writes them as step + walking-distance samples).
    Times carry the PC's UTC offset so the phone places them correctly; the walk in progress is left out."""
    off = datetime.now().astimezone().strftime("%z")
    off = off[:3] + ":" + off[3:]
    since = (date.today() - timedelta(days=days)).isoformat()
    bogus = excluded(db)
    out = []
    for sid, st, en, steps, dist in db.execute(
            f"SELECT id, start_ts, end_ts, steps, distance_m FROM sessions WHERE id NOT IN ({bogus}) AND start_ts >= ? AND end_ts IS NOT NULL ORDER BY id",
            (since,)):
        if live_session and sid == live_session:
            continue
        if not steps and not dist:
            continue
        out.append({"id": sid, "start": st + off, "end": en + off, "steps": int(steps or 0), "km": round((dist or 0) / 1000, 3)})
    return out


def goals_for(s, d):
    """Main goal that applied on day d."""
    g = main_goal(s)
    out = {"metric": g["metric"], "tiny": g["tiny"], "goal": g["target"], "stretch": g["stretch"]}
    for h in s["goal_history"]:
        if h["from"] <= d.isoformat():
            out = {"metric": h.get("metric", "minutes"), "tiny": h["tiny"], "goal": h["goal"], "stretch": h["stretch"]}
    return out


def ramadan(s, metric, v):
    return rnd(metric, v * .6) if s["modes"].get("ramadan") else v


def current_goal(s):
    g = main_goal(s)
    return {"metric": g["metric"], "unit": METRICS[g["metric"]]["unit"], "tiny": g["tiny"],
            "goal": ramadan(s, g["metric"], g["target"]), "stretch": ramadan(s, g["metric"], g["stretch"])}


def week_start(d):
    return d - timedelta(days=(d.weekday() + 1) % 7)


def fmt_day(d):
    return d.strftime("%a ") + str(d.day) + d.strftime(" %b")


def short_gap(metric, gap):
    if metric == "minutes" and abs(gap - .5) < .05:
        return "30 seconds"
    return fmtu(metric, gap)


def haversine(a, b):
    import math
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def build_track(tid, custom=None):
    t = next((x for x in TRACKS if x["id"] == tid), None)
    if tid == "custom":
        keys = [k for k in (custom or []) if k in PLACES]
        if len(keys) < 2:
            keys = ["masmak", "turaif"]
        t = {"id": "custom", "name": "My track", "desc": "Your own route.", "stops": keys}
    t = t or TRACKS[1]
    stops, acc = [], 0.0
    for i, k in enumerate(t["stops"]):
        n, city, la, lo = PLACES[k]
        if i:
            acc += haversine(PLACES[t["stops"][i - 1]][2:], (la, lo))
        stops.append({"key": k, "name": n, "city": city, "lat": la, "lon": lo, "km": round(acc, 1)})
    return {"id": t["id"], "name": t["name"], "desc": t["desc"], "stops": stops, "total": round(acc, 1)}


def excluded(db):
    """Sessions to ignore (e.g. a first record with counters carried over from before logging)."""
    db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    row = db.execute("SELECT value FROM settings WHERE key='excluded_sessions'").fetchone()
    ids = [int(x) for x in json.loads(row[0])] if row else []
    return ",".join(map(str, ids)) or "-1"


def lifetime_km(db):
    bogus = excluded(db)
    return (db.execute(f"SELECT COALESCE(SUM(distance_m),0) FROM sessions WHERE id NOT IN ({bogus})").fetchone()[0] or 0) / 1000


def set_track(db, tid, custom=None):
    """Start a track: progress counts the km walked from now on (lifetime totals are untouched)."""
    s = load_settings(db)
    if tid != "custom" and not any(x["id"] == tid for x in TRACKS):
        raise ValueError("unknown track")
    custom = [k for k in (custom or []) if k in PLACES][:12]
    if tid == "custom" and len(custom) < 2:
        raise ValueError("pick at least two places for your own track")
    s["track"] = {**s["track"], "id": tid, "custom": custom, "start_km": round(lifetime_km(db), 3)}
    _put(db, "track", s["track"]); db.commit()
    return s["track"]


# ------------------------------------------------------------------ core

def compute(db, live, now=None):
    now = now or datetime.now()
    today = now.date()
    s = load_settings(db)
    record_mode_day(db, s, today)
    bogus = excluded(db)
    rows = db.execute(f"""SELECT id, start_ts, end_ts, distance_m, steps, kcal, elapsed_s, max_speed_kmh
                          FROM sessions WHERE id NOT IN ({bogus}) AND start_ts IS NOT NULL ORDER BY id""").fetchall()
    sess = [dict(zip(("id", "start", "end", "distance_m", "steps", "kcal", "elapsed_s", "max_speed"), r)) for r in rows]

    days = {}
    for x in sess:
        d = date.fromisoformat(x["start"][:10])
        t = days.setdefault(d, {"min": 0.0, "steps": 0, "distance_m": 0, "kcal": 0, "sessions": 0, "top": 0.0, "longest": 0.0})
        m = (x["elapsed_s"] or 0) / 60
        t["min"] += m; t["steps"] += x["steps"] or 0; t["distance_m"] += x["distance_m"] or 0
        t["kcal"] += x["kcal"] or 0; t["sessions"] += 1
        t["top"] = max(t["top"], x["max_speed"] or 0); t["longest"] = max(t["longest"], m)
    ensure_health(db)
    health = {date.fromisoformat(d): st for d, st in db.execute("SELECT date, steps FROM health_days")}
    for d, st in health.items():
        days.setdefault(d, {"min": 0.0, "steps": 0, "distance_m": 0, "kcal": 0, "sessions": 0, "top": 0.0, "longest": 0.0})
    for d, t in days.items():
        t["health"] = health.get(d, 0)
    first = min(days) if days else today
    blank = {"min": 0.0, "steps": 0, "distance_m": 0, "kcal": 0, "sessions": 0, "top": 0.0, "longest": 0.0, "health": 0}
    G = current_goal(s)
    M = G["metric"]

    def day_goal(d):
        return goals_for(s, d) if d < today else {"metric": M, "tiny": G["tiny"], "goal": G["goal"], "stretch": G["stretch"]}

    # ---- day states, streak, shields
    state, weight = {}, {}
    streak = best = shields = earned = 0
    best_date = None
    walked_before = prev_miss = False
    d = first
    while d <= today:
        t = days.get(d, blank); g = day_goal(d); v = val(t, g["metric"])
        if v >= g["goal"] and v > 0:
            st = "goal"
        elif v >= g["tiny"] and v > 0:
            st = "tiny"
        elif s["mode_days"].get(d.isoformat()):
            st = "rest"
        elif d == today:
            st = "today"
        else:
            st = "miss"
        weight[d] = 2 if (st == "goal" and prev_miss and walked_before) else 1 if st == "goal" else 0
        if st in ("goal", "tiny"):
            streak += 1; earned += 1
            if earned >= 7:
                shields = min(2, shields + 1); earned = 0
            if streak >= best:
                best, best_date = streak, d
            walked_before, prev_miss = True, False
        elif st == "miss":
            if shields > 0 and streak > 0:
                shields -= 1; st = "shield"; prev_miss = False
            else:
                streak = earned = 0; prev_miss = True
        state[d] = st
        d += timedelta(days=1)

    tday = days.get(today, blank)
    yesterday = today - timedelta(days=1)
    comeback = state.get(yesterday) == "miss" and any(v in ("goal", "tiny") for k, v in state.items() if k < yesterday)
    shield_used = state.get(yesterday) == "shield"

    # ---- week
    ws = week_start(today)
    week = []
    for i in range(7):
        dd = ws + timedelta(days=i)
        st = state.get(dd, "future" if dd > today else "miss")
        if dd == today and st not in ("goal", "tiny"):
            st = "today"
        week.append({"d": WD[i], "state": st, "date": dd.isoformat()})
    week_done = sum(weight.get(ws + timedelta(days=i), 0) for i in range(7))
    days_left = 6 - (today - ws).days + (0 if state.get(today) == "goal" else 1)
    need = max(0, s["week_goal"] - week_done)
    def near_miss(dd):
        g = day_goal(dd); v = val(days.get(dd, blank), g["metric"]); gap = g["goal"] - v
        return 0 < gap <= g["goal"] * .07 and v >= g["tiny"]
    near = [dd for dd in (ws + timedelta(days=i) for i in range(7)) if dd < today and near_miss(dd)]
    if near:
        dd = near[-1]; g = day_goal(dd); v = val(days[dd], g["metric"])
        week_note = f"{dd.strftime('%A')} was {fmtu(g['metric'], v)}: {short_gap(g['metric'], g['goal'] - v)} short of the goal, and it still counted for your streak."
    elif need == 0:
        week_note = "Full week. Everything from here is a bonus."
    elif need > days_left:
        week_note = "A full week is out of reach this time. Every walk still counts for your streak and month."
    else:
        week_note = f"{need} more goal day{'s' if need != 1 else ''} to finish the week, {days_left} day{'s' if days_left != 1 else ''} left."

    # ---- month
    ms = today.replace(day=1)
    nxt = (ms + timedelta(days=32)).replace(day=1)
    month_done = sum(w for k, w in weight.items() if ms <= k < nxt)
    month = {"name": today.strftime("%B"), "target": s["month_goal"], "done": min(month_done, s["month_goal"]), "daysLeft": (nxt - today).days}

    # ---- all goals progress (today for daily, this week for weekly)
    wsum = {"min": 0.0, "steps": 0, "distance_m": 0, "health": 0}
    for i in range(7):
        t = days.get(ws + timedelta(days=i), blank)
        for k in wsum:
            wsum[k] += t.get(k, 0) if k != "health" else max(t.get("health", 0), t["steps"])
    goals_out = []
    for g in s["goals"]:
        src = tday if g["period"] == "day" else wsum
        v = val({**blank, **src}, g["metric"]) if not (g["period"] == "week" and g["metric"] == "allsteps") else wsum["health"]
        tgt = ramadan(s, g["metric"], g["target"]) if g["period"] == "day" else g["target"]
        goals_out.append({**g, "target": tgt, "value": round(v, 2), "pct": min(100, round(v / tgt * 100)) if tgt else 0,
                          "done": v >= tgt, "unit": METRICS[g["metric"]]["unit"],
                          "title": f"{fmtv(g['metric'], tgt)} {'all-day steps' if g['metric'] == 'allsteps' else METRICS[g['metric']]['unit']} {'a day' if g['period'] == 'day' else 'this week'}",
                          "left": fmtu(g["metric"], max(0, tgt - v))})

    # ---- records
    walk_days = {k: v for k, v in days.items() if v["min"] > 0}
    def rec(title, key, fmt):
        if not walk_days:
            return None
        k = max(walk_days, key=lambda x: walk_days[x][key])
        return {"title": title, "when": fmt_day(k), "value": fmt(walk_days[k][key])}
    weeks = {}
    for k, w in weight.items():
        weeks[week_start(k)] = weeks.get(week_start(k), 0) + w
    records = [r for r in (
        rec("Most steps in a day", "steps", lambda v: f"{v:,}"),
        rec("Most minutes in a day", "min", lambda v: f"{round(v)} min"),
        rec("Longest single walk", "longest", lambda v: f"{round(v)} min"),
        rec("Farthest day", "distance_m", lambda v: f"{v / 1000:.2f} km"),
        rec("Top speed", "top", lambda v: f"{v:.1f} km/h"),
    ) if r]
    if weeks and max(weeks.values()) > 0:
        bw = max(weeks, key=weeks.get)
        records.append({"title": "Best week", "when": "week of " + fmt_day(bw), "value": f"{weeks[bw]} goal days"})

    # ---- lifetime stats
    tot_steps = sum(v["steps"] for v in days.values()); tot_m = sum(v["distance_m"] for v in days.values())
    tot_min = sum(v["min"] for v in days.values()); n_walk = len(walk_days)
    span = (today - first).days + 1 if days else 1
    life_km = tot_m / 1000
    lifetime = [[f"{life_km:.2f} km", "distance walked"], [f"{tot_steps:,}", "total steps"],
                [f"{round(tot_min)} min", "time walking"], [str(len(sess)), "walks"]]
    stats = [
        [f"{round(tot_steps / n_walk):,}" if n_walk else "0", "avg steps per walking day"],
        [f"{round(tot_steps / span):,}", "avg steps per day (all days)"],
        [f"{round(tot_min / n_walk)} min" if n_walk else "0 min", "avg time per walking day"],
        [f"{life_km / n_walk:.2f} km" if n_walk else "0 km", "avg distance per walking day"],
        [f"{(life_km / (tot_min / 60)):.1f} km/h" if tot_min else "0 km/h", "avg walking speed"],
        [f"{round(tot_steps / tot_min)}" if tot_min else "0", "avg steps per minute"],
        [f"{n_walk} of {span}", "days walked"],
        [f"{best} days", "longest streak"],
    ]
    T = s["track"]
    trk = build_track(T["id"], T.get("custom"))
    on = max(0.0, life_km - (T.get("start_km") or 0))
    nxt_stop = next((x for x in trk["stops"] if x["km"] > on), None)
    complete = on >= trk["total"] > 0
    if complete and not any(dn["id"] == trk["id"] and dn.get("start_km") == T.get("start_km") for dn in T.get("done", [])):
        T.setdefault("done", []).append({"id": trk["id"], "name": trk["name"], "date": today.isoformat(), "km": trk["total"], "start_km": T.get("start_km")})
        _put(db, "track", T); db.commit()
    pos = trk["stops"][-1]
    for a, b in zip(trk["stops"], trk["stops"][1:]):
        if a["km"] <= on <= b["km"]:
            f = (on - a["km"]) / max(1e-6, b["km"] - a["km"])
            pos = {"lat": a["lat"] + (b["lat"] - a["lat"]) * f, "lon": a["lon"] + (b["lon"] - a["lon"]) * f}
            break
    journey = {"track": trk, "done": round(min(on, trk["total"]), 1), "total": trk["total"], "complete": complete,
               "next": nxt_stop["name"] if nxt_stop else trk["stops"][-1]["name"], "nextKey": nxt_stop["key"] if nxt_stop else trk["stops"][-1]["key"],
               "toNext": round(max(0, (nxt_stop["km"] if nxt_stop else trk["total"]) - on), 1), "pos": {"lat": pos["lat"], "lon": pos["lon"]},
               "stops": [x["name"] for x in trk["stops"]], "startKm": 0,
               "tracks": [{"id": x["id"], "name": x["name"], "desc": x["desc"], "total": build_track(x["id"])["total"], "stops": x["stops"]} for x in TRACKS],
               "places": [{"key": k, "name": v[0], "city": v[1], "lat": v[2], "lon": v[3]} for k, v in PLACES.items()],
               "completed": T.get("done", []), "custom": T.get("custom", [])}

    # ---- medals
    def reach_date(threshold_km):
        acc = 0
        for k in sorted(days):
            acc += days[k]["distance_m"] / 1000
            if acc >= threshold_km:
                return fmt_day(k)
        return None
    nxt_s = next((x for x in STREAK_MEDALS if x > best), None)
    streak_m = [{"kind": "flame", "label": t, "title": f"{t} days" if t < 365 else "365", "got": best >= t,
                 "sub": "earned" if best >= t else f"{t - streak} more days" if t == nxt_s else
                 {3: "a start", 7: "a week", 30: "a month", 100: "a habit", 365: "a year"}[t]} for t in STREAK_MEDALS]
    nd = next((t for t in DIST_MEDALS if t > life_km), None)
    dist_m = [{"kind": "leaf", "label": str(t), "title": f"{t} km", "got": life_km >= t,
               "sub": reach_date(t) if life_km >= t else (f"{t - life_km:.1f} km to go" if t == nd else "")} for t in DIST_MEDALS[:6]]
    walked_dates = sorted(k for k, v in state.items() if v in ("goal", "tiny"))
    comeback_dates = [k for k in walked_dates if state.get(k - timedelta(days=1)) == "miss" and k > walked_dates[0]]
    stretch_dates = [k for k in sorted(days) if val(days[k], day_goal(k)["metric"]) >= day_goal(k)["stretch"]]
    full_weeks = [k for k, w in sorted(weeks.items()) if w >= s["week_goal"]]
    special = [
        {"kind": "sky", "label": "1st", "title": "First walk", "got": bool(walked_dates), "sub": fmt_day(walked_dates[0]) if walked_dates else "your first walk"},
        {"kind": "berry", "label": "↺", "title": "Comeback", "got": bool(comeback_dates), "sub": ("walked again after a miss · " + fmt_day(comeback_dates[0])) if comeback_dates else "walk again after a missed day"},
        {"kind": "sun", "label": "+", "title": "Stretch day", "got": bool(stretch_dates), "sub": fmt_day(stretch_dates[0]) if stretch_dates else "reach your stretch level"},
        {"kind": "leaf", "label": f"{s['week_goal']}/7", "title": "Full week", "got": bool(full_weeks), "sub": ("week of " + fmt_day(full_weeks[0])) if full_weeks else f"{s['week_goal']} goal days in a week"},
    ]
    nxt_streak = next(t for t in NEXT_STREAK if t > streak)
    next_medal = {"label": nxt_streak, "title": f"{nxt_streak}-day streak",
                  "hint": f"{nxt_streak - streak} more walking day{'s' if nxt_streak - streak != 1 else ''} in a row"}

    # ---- charts
    def bar(dd, label):
        t = days.get(dd, blank)
        return {"d": label, "date": dd.isoformat(), "steps": t["steps"], "min": round(t["min"], 1), "km": round(t["distance_m"] / 1000, 2)}
    daily = {"week": [bar(ws + timedelta(days=i), WD[i]) for i in range(7)],
             "month": [bar(ms + timedelta(days=i), str(i + 1) if i % 5 == 0 else "") for i in range((nxt - ms).days)]}
    def level(dd):
        g = day_goal(dd); v = val(days.get(dd, blank), g["metric"])
        return 0 if v <= 0 else 1 if v < g["tiny"] else 2 if v < g["goal"] else 3 if v < g["stretch"] else 4
    hs = ws - timedelta(weeks=25)
    heat = [level(hs + timedelta(days=i)) if hs + timedelta(days=i) <= today else -1 for i in range(26 * 7)]
    lead = (ms.weekday() + 1) % 7
    cells = [{"s": "out"} for _ in range(lead)]
    for i in range((nxt - ms).days):
        dd = ms + timedelta(days=i); st = state.get(dd, "")
        cells.append({"d": i + 1, "s": "today" if dd == today and st not in ("goal", "tiny") else st if st in ("goal", "tiny", "shield", "rest") else ""})
    mgoal = sum(1 for k, v in state.items() if ms <= k < nxt and v == "goal")
    mtiny = sum(1 for k, v in state.items() if ms <= k < nxt and v == "tiny")
    calendar = {"title": today.strftime("%B %Y"), "legend": f"{mgoal} goal day{'s' if mgoal != 1 else ''} · {mtiny} tiny day{'s' if mtiny != 1 else ''}", "cells": cells}

    # ---- adaptive suggestion for the main goal (never auto-applied)
    last14 = [today - timedelta(days=i) for i in range(1, 15)]
    g14 = sum(1 for k in last14 if state.get(k) == "goal")
    w14 = [k for k in last14 if state.get(k) in ("goal", "tiny")]
    mg = main_goal(s)
    recent = [val(days[k], M) for k in sorted(walk_days)[-10:]]
    if (today - first).days < 14:
        sugg = {"target": mg["target"], "why": f"Holding steady while we learn your rhythm ({(today - first).days + 1} of 14 days)."}
    elif g14 >= 12:
        sugg = {"target": rnd(M, mg["target"] + METRICS[M]["inc"]), "why": f"You hit your goal on {g14} of the last 14 days. Ready for a little more?"}
    elif len(w14) >= 4 and g14 / len(w14) < .5 and recent and rnd(M, statistics.median(recent)) < mg["target"]:
        sugg = {"target": max(METRICS[M]["tiny"] * 2, rnd(M, statistics.median(recent))), "why": f"You hit your goal on {g14} of your last {len(w14)} walking days. A slightly smaller goal keeps the wins coming."}
    else:
        sugg = {"target": mg["target"], "why": f"You hit your goal on {g14} of your last {len(w14)} walking days. Holding it steady."}
    sugg.update(metric=M, unit=METRICS[M]["unit"], goal_id=mg["id"])
    med_steps = statistics.median([v["steps"] for v in walk_days.values()]) if walk_days else 0
    base = max(1000, rnd("steps", med_steps * .9)) if walk_days else 2500
    onboard = {"typical": int(med_steps), "metric": "steps", "options": [rnd("steps", base * .6), base, rnd("steps", base * 1.5)]}

    # ---- last walk
    last = sess[-1] if sess else None
    last_walk = None
    if last:
        tr = [r[0] or 0 for r in db.execute("SELECT speed_kmh FROM samples WHERE session_id=? ORDER BY rowid", (last["id"],))]
        trace = tr[::max(1, len(tr) // 60)] or [0, 0]
        moving_v = [v for v in tr if v > 0]
        ld = date.fromisoformat(last["start"][:10]); lst = state.get(ld, ""); lg = day_goal(ld)
        lv = val(days[ld], lg["metric"])
        earned = []
        if lst == "goal":
            earned.append({"c": "leaf", "icon": "check", "title": "Main goal done that day", "sub": f"{fmtu(lg['metric'], lv)} of {fmtu(lg['metric'], lg['goal'])}", "end": "+1 goal day" if weight.get(ld, 1) == 1 else "+2 comeback"})
        elif lst == "tiny":
            earned.append({"c": "leaf", "icon": "check", "title": "Tiny goal done: streak kept", "sub": f"{fmtu(lg['metric'], lv)} of {fmtu(lg['metric'], lg['goal'])}", "end": ""})
        if ld == today and streak:
            earned.append({"c": "flame", "icon": "flame", "title": f"Streak is {streak} day{'s' if streak != 1 else ''}", "sub": f"Best ever: {best} days", "end": str(streak)})
        earned.append({"c": "sun", "icon": "crown", "title": f"Week: {week_done} of {s['week_goal']} goal days", "sub": week_note, "end": f"{week_done}/{s['week_goal']}"})
        earned.append({"c": "sky", "icon": "route", "title": "Walk across Arabia", "sub": f"{journey['next']} is {journey['toNext']} km away", "end": f"+{(last['distance_m'] or 0) / 1000:.2f} km"})
        last_walk = {"id": last["id"], "when": fmt_day(ld) + ", " + last["start"][11:16], "min": round((last["elapsed_s"] or 0) / 60),
                     "steps": last["steps"] or 0, "distance_m": last["distance_m"] or 0, "kcal": last["kcal"] or 0,
                     "avgSpeed": round(statistics.mean(moving_v), 1) if moving_v else 0, "topSpeed": round(max(tr) if tr else 0, 1),
                     "trace": trace, "earned": earned, "end": last["end"]}

    # ---- live + copy
    L = live.get("last") or {}
    lt = live.get("last_ts")
    fresh = bool(lt) and (now - datetime.fromisoformat(lt)).total_seconds() < 12
    moving = bool(live.get("connected")) and fresh and (L.get("speed_kmh") or 0) > 0
    tval = val(tday, M)
    left = max(0, G["goal"] - tval)
    # pace of the main metric per minute: this walk if moving, else the typical walking pace
    lmin = (L.get("elapsed_s") or 0) / 60
    lval = {"steps": L.get("steps") or 0, "allsteps": L.get("steps") or 0, "minutes": lmin, "km": (L.get("distance_m") or 0) / 1000}[M]
    rate = (lval / lmin) if moving and lmin > 1 else (val({**blank, "min": tot_min, "steps": tot_steps, "distance_m": tot_m}, M) / tot_min if tot_min else 0)
    eta_min = left / rate if rate > 0 else None
    eta_text = (f"About {round(eta_min)} more minutes at this pace, done around {(now + timedelta(minutes=eta_min)).strftime('%H:%M')}"
                if eta_min and left > 0 else "Goal done. Everything now is bonus." if left <= 0 else "")
    hour = now.hour
    greeting = "Morning. Ready for a walk?" if hour < 12 else "Afternoon. Time for a walk?" if hour < 18 else "Evening. A short walk counts too."
    if comeback and tval < G["tiny"]:
        greeting = "Good to see you."
    if (today - ws).days == 6 and need:
        hero_note = f"Last day of the week. One goal walk makes this {week_done + (2 if comeback else 1)} goal days."
    elif comeback and tval < G["tiny"]:
        hero_note = f"{fmtu(M, G['tiny'])} starts a new streak, and today's goal counts double."
    elif shield_used:
        hero_note = "Yesterday was covered by a rest shield."
    else:
        hero_note = week_note
    banner = "comeback" if comeback and tval < G["goal"] else "shield" if shield_used else None if live.get("connected") else "padoff"
    c = s["community"]

    return {
        "now": now.isoformat(timespec="seconds"), "onboarded": s["onboarded"],
        "settings": {k: s[k] for k in ("goals", "week_goal", "month_goal", "cue", "nudge", "modes")},
        "pad": {"connected": bool(live.get("connected")), "name": (live.get("device") or {}).get("name") or "URTM041", "status": live.get("status")},
        "moving": moving, "dateLabel": now.strftime("%A · ") + str(today.day) + now.strftime(" %B"),
        "greeting": greeting, "heroNote": hero_note, "goal": G, "goals": goals_out,
        "today": {"value": round(tval, 2), "min": round(tday["min"], 1), "steps": tday["steps"], "distance_m": tday["distance_m"], "kcal": tday["kcal"], "sessions": tday["sessions"],
                  "health": tday.get("health", 0)},
        "health": {"connected": bool(health), "today": health.get(today), "lastDate": max(health).isoformat() if health else None},
        "streak": {"days": streak, "best": best, "shields": shields, "bestDate": best_date.isoformat() if best_date else None},
        "comeback": comeback, "weekGoal": s["week_goal"], "weekDone": week_done, "week": week, "weekNote": week_note,
        "month": month, "next": next_medal, "records": records, "lifetime": lifetime, "stats": stats, "daily": daily, "heat": heat,
        "calendar": calendar, "journey": journey, "medals": {"streak": streak_m, "distance": dist_m, "special": special},
        "suggestion": sugg, "onboard": onboard, "lastWalk": last_walk, "banner": banner,
        "live": {"elapsed": L.get("elapsed_s") or 0, "speed": L.get("speed_kmh") or 0, "steps": L.get("steps") or 0,
                 "distance_m": L.get("distance_m") or 0, "kcal": L.get("kcal") or 0, "session": live.get("session_id")},
        "etaText": eta_text,
        "community": {"enabled": c["enabled"], "handle": c["handle"], "user_id": c["user_id"], "display_name": c["display_name"],
                      "public": c["public"], "last_sync": c["last_sync"], "server": c["server"]},
        "_days": {k.isoformat(): {"steps": v["steps"], "minutes": round(v["min"], 1), "km": round(v["distance_m"] / 1000, 2),
                                   "goal_met": state.get(k) == "goal"} for k, v in days.items() if (today - k).days < 40},
    }
