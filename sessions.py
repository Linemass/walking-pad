"""Print recorded walking sessions; `python sessions.py --csv` writes sessions.csv."""
import csv
import sqlite3
import sys
from pathlib import Path

HOME = Path(__file__).resolve().parent
db = sqlite3.connect(HOME / "urevo.db")
rows = db.execute("""SELECT id, start_ts, end_ts, distance_m, steps, kcal, elapsed_s, max_speed_kmh
                     FROM sessions ORDER BY id""").fetchall()
header = ["id", "start", "end", "distance_m", "steps", "kcal", "elapsed_s", "max_speed_kmh"]

if "--csv" in sys.argv:
    with open(HOME / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([header, *rows])
    print("wrote", HOME / "sessions.csv")
else:
    for r in rows:
        mins = (r[6] or 0) // 60
        print(f"#{r[0]:<4} {r[1]} -> {r[2][11:] if r[2] else '?':8}  "
              f"{(r[3] or 0) / 1000:5.2f} km  {r[4] or 0:6} steps  {r[5] or 0:4} kcal  {mins:3} min")
