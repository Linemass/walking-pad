"""Desktop launcher: make sure the logger is running, then open the dashboard
in its own app window (Edge app mode — no tabs, no address bar)."""
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path

URL = "http://127.0.0.1:8765/"
HOME = Path(__file__).resolve().parent
EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]


def up() -> bool:
    try:
        urllib.request.urlopen(URL + "api/live", timeout=1)
        return True
    except Exception:
        return False


if not up():
    # Start the same Scheduled Task that runs at logon, so there is only ever one logger.
    subprocess.run(["schtasks", "/Run", "/TN", "UrevoLogger"], creationflags=0x08000000)
    for _ in range(30):
        if up():
            break
        time.sleep(0.5)

edge = next((p for p in EDGE if p.exists()), None)
if edge:
    subprocess.Popen([str(edge), f"--app={URL}", "--window-size=1180,860",
                      f"--user-data-dir={HOME / '.edge-app'}"])
else:
    webbrowser.open(URL)
