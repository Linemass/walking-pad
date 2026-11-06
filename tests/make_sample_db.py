"""Build tests/fixtures/sample.db: a small, INVENTED walking history used by tests and the design board.
It mirrors the shape of a real first week (tiny days, goal days, two missed days, a near-miss) so the
engine tests are meaningful, without shipping anyone's real data. Run: python -P tests/make_sample_db.py"""
import sqlite3
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures" / "sample.db"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.unlink(missing_ok=True)
db = sqlite3.connect(OUT)
db.executescript("""
CREATE TABLE samples (ts TEXT NOT NULL, session_id INTEGER NOT NULL, speed_kmh REAL, distance_m INTEGER, steps INTEGER,
                      kcal INTEGER, elapsed_s INTEGER, heart_rate INTEGER, raw TEXT NOT NULL);
CREATE TABLE sessions (id INTEGER PRIMARY KEY, start_ts TEXT, end_ts TEXT, distance_m INTEGER, steps INTEGER, kcal INTEGER,
                       elapsed_s INTEGER, max_speed_kmh REAL);
""")
# id, start, end, distance_m, steps, kcal, elapsed_s, max_speed   (invented numbers)
S = [
    (1, "2026-10-18T21:00:00", "2026-10-18T21:01:00", 3100, 5300, 170, 3100, 0.0),   # counters carried over: excluded
    (2, "2026-11-01T14:30:00", "2026-11-01T14:38:00", 410, 640, 22, 480, 3.5),
    (3, "2026-11-01T15:00:00", "2026-11-01T15:19:00", 1190, 1830, 63, 1140, 5.5),    # Sun: 27 min  -> tiny
    (4, "2026-11-02T16:50:00", "2026-11-02T17:18:00", 1420, 2610, 81, 1680, 4.0),
    (5, "2026-11-02T19:00:00", "2026-11-02T19:08:30", 240, 390, 18, 510, 2.5),       # Mon: 36.5 min -> goal
    (6, "2026-11-05T09:50:00", "2026-11-05T10:19:30", 950, 1460, 66, 1770, 2.0),     # Thu: 29.5 min -> near miss
    (7, "2026-11-06T15:30:00", "2026-11-06T16:06:00", 1500, 2700, 94, 2160, 6.0),
    (8, "2026-11-06T16:55:00", "2026-11-06T17:11:00", 260, 210, 27, 960, 1.0),       # Fri: 52 min -> goal
]
db.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)", S)
# a short speed trace for the last walk (summary sparkline)
for i in range(60):
    sp = [0, 1.0, 1.0, 1.0][min(i // 15 + (1 if i else 0), 3)] if i not in (0, 59) else 0
    db.execute("INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?)",
               (f"2026-11-06T16:{55 + i // 30:02d}:{(i * 2) % 60:02d}", 8, sp, i * 4, i * 3, i // 3, i * 16, None, "00"))
db.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
db.execute("INSERT INTO settings VALUES ('excluded_sessions', '[1]')")
db.commit()
print("wrote", OUT)
