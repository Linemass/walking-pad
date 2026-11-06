"""Write design/fixture.js from the real engine on a COPY of the database (morning of Sat 7 Nov 2026),
so the design board always shows exactly what the app computes."""
import json, shutil, sqlite3, sys, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import engine

tmp = Path(tempfile.mkdtemp()) / "fx.db"
shutil.copy(ROOT / "tests" / "fixtures" / "sample.db", tmp)
db = sqlite3.connect(tmp)
engine.save_settings(db, {"onboarded": True})
s = engine.compute(db, {"connected": True, "device": {"name": "URTM041"}}, datetime(2026, 11, 7, 9, 0))
s.pop("_days", None)
# sample community data for the board only (clearly fictional people)
s["community"] = {"enabled": True, "handle": "mohammed", "user_id": "u7Kq2mX9pLs4", "display_name": "Mohammed", "public": True,
                  "last_sync": "2026-11-07T08:55:00", "server": "local"}
s["cdata"] = {
    "me": {"display_name": "Mohammed", "groups": [
        {"group_id": "g1", "name": "DCSI walkers", "members": 6, "invite_code": "KX7P4MQA", "role": "owner"},
        {"group_id": "g2", "name": "Family", "members": 4, "invite_code": "HB3RZW8N", "role": "member"}]},
    "board": {"rows": [
        {"rank": 1, "handle": "noura_a", "display_name": "Noura A", "value": 21480, "me": False},
        {"rank": 2, "handle": "faisal", "display_name": "Faisal K", "value": 18905, "me": False},
        {"rank": 3, "handle": "mohammed", "display_name": "Mohammed", "value": 9859, "me": True},
        {"rank": 4, "handle": "lama_s", "display_name": "Lama S", "value": 7212, "me": False},
        {"rank": 5, "handle": "omar_w", "display_name": "Omar W", "value": 3340, "me": False}],
        "me": {"rank": 3, "value": 9859}},
}
(Path(__file__).parent / "fixture.js").write_text("window.FIXTURE = " + json.dumps(s, ensure_ascii=False) + ";\n", encoding="utf-8")
print("fixture written:", s["goal"], s["today"]["value"], s["journey"]["track"]["name"])
