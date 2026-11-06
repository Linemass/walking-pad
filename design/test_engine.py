"""Engine checks against a COPY of the real database. Usage: python -P design/test_engine.py"""
import shutil, sqlite3, sys, tempfile
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine

tmp = Path(tempfile.mkdtemp()) / "t.db"
shutil.copy(ROOT / "tests" / "fixtures" / "sample.db", tmp)
db = sqlite3.connect(tmp)
# start from a fixed v3-style settings snapshot (not the founder's live settings) so the test is repeatable
db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
db.execute("DELETE FROM settings")
db.executemany("INSERT INTO settings VALUES (?, ?)", [("onboarded", "true"), ("tiny", "5"), ("goal", "45"), ("stretch", "60"),
    ("goal_history", '[{"from": "0000-01-01", "tiny": 5, "goal": 30, "stretch": 45}, {"from": "2026-11-06", "tiny": 5, "goal": 45, "stretch": 60}]')])
db.commit()
live = {"connected": True}
fails = 0
def check(cond, msg):
    global fails
    print(("ok   " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1

s = engine.compute(db, live, datetime(2026, 11, 6, 21))
check(s["goal"]["metric"] == "steps", "main goal migrated to steps")
check(any(g["metric"] == "minutes" and not g["primary"] for g in s["goals"]), "old minutes goal kept as a second goal")
check(s["streak"]["days"] == 2, f"streak 2 (got {s['streak']['days']})")
check([w["state"] for w in s["week"]][:6] == ["tiny", "goal", "miss", "miss", "tiny", "goal"], "past days judged by their own goal")
check(len(s["stats"]) >= 8, "progress stats present")
for t in engine.TRACKS:
    b = engine.build_track(t["id"])
    print(f"     {b['name']:26} {b['total']:8.1f} km  stops at {[x['km'] for x in b['stops']]}")
j = s["journey"]
check(j["track"]["id"] == "riyadh-diriyah" and 0 < j["done"] <= j["total"], f"default track progress {j['done']} of {j['total']} km")
engine.set_track(db, "old-riyadh")
j = engine.compute(db, live)["journey"]
check(j["done"] == 0, "switching track restarts track progress at 0")
engine.set_track(db, "custom", ["balad", "taif", "abha"])
check(engine.compute(db, live)["journey"]["track"]["name"] == "My track", "custom track builds")
for bad, label in ((("custom", ["balad"]), "custom track needs 2 places"), (("nope", None), "unknown track")):
    try:
        engine.set_track(db, *bad); check(False, label)
    except ValueError:
        check(True, label + " rejected")
for bad in ({"goals": []}, {"goals": [{"metric": "km", "period": "week", "target": 5}]},
            {"goals": [{"metric": "laps", "target": 5}]}, {"goals": [{"metric": "steps", "target": -1}]}):
    try:
        engine.save_settings(db, bad); check(False, f"bad goals rejected {bad}")
    except ValueError:
        check(True, f"bad goals rejected {list(bad['goals'][:1])}")
g = engine.compute(db, live)["settings"]["goals"] + [{"metric": "km", "period": "week", "target": 12}]
engine.save_settings(db, {"goals": g}, date(2026, 11, 6))
check(len(engine.compute(db, live)["goals"]) == 3, "third (weekly km) goal saved")
print("FAILURES", fails)
sys.exit(1 if fails else 0)
