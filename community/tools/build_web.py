"""Copy the web app from ../web into public/ for Workers static assets.
index.html stays at the root; everything else is served under /static/ (same paths as the PC logger)."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT.parent / "web"
OUT = ROOT / "public"
shutil.rmtree(OUT, ignore_errors=True)
(OUT / "static" / "fonts").mkdir(parents=True)
shutil.copy(WEB / "index.html", OUT / "index.html")
for f in ("app.css", "ui.js", "landmarks.js", "icon.png"):
    shutil.copy(WEB / f, OUT / "static" / f)
for f in ("Nunito-Variable.ttf", "Nunito-OFL.txt"):
    shutil.copy(WEB / "fonts" / f, OUT / "static" / "fonts" / f)
total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
print(f"public/ built: {sum(1 for p in OUT.rglob('*') if p.is_file())} files, {total / 1024:.0f} KB")
