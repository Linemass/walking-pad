"""Build dist/WalkingPad.exe: one self-installing Windows program (Python, Bluetooth, server, tray, web app).
Usage: python -P tools/build_exe.py      (needs: pip install pyinstaller bleak aiohttp pystray pillow)"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
STAGE = BUILD / "stage-web" / "web"
shutil.rmtree(BUILD, ignore_errors=True)
(STAGE / "fonts").mkdir(parents=True)
for f in ("index.html", "app.css", "ui.js", "landmarks.js", "icon.png"):
    shutil.copy(ROOT / "web" / f, STAGE / f)
for f in ("Nunito-Variable.ttf", "Nunito-OFL.txt"):
    shutil.copy(ROOT / "web" / "fonts" / f, STAGE / "fonts" / f)

cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
       "--name", "WalkingPad", "--icon", str(ROOT / "walkingpad.ico"),
       "--add-data", f"{STAGE};web",
       "--collect-submodules", "winrt", "--collect-submodules", "bleak", "--hidden-import", "pystray._win32",
       "--distpath", str(ROOT / "dist"), "--workpath", str(BUILD / "work"), "--specpath", str(BUILD),
       str(ROOT / "urevo_logger.py")]
r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
if r.returncode:
    print(r.stdout[-3000:], r.stderr[-6000:]); sys.exit(1)
exe = ROOT / "dist" / "WalkingPad.exe"
print(f"built {exe} ({exe.stat().st_size / 1e6:.1f} MB)")
