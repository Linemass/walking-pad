"""Windows app shell for the packaged WalkingPad.exe: where files live, self-install, shortcuts, the app window.

Running from source (python urevo_logger.py) keeps the old behaviour: data next to the code.
The packaged exe keeps data in %LOCALAPPDATA%\\WalkingPad and installs itself to
%LOCALAPPDATA%\\Programs\\WalkingPad on first run (no admin rights needed)."""
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
SRC = Path(__file__).resolve().parent
RESOURCES = Path(getattr(sys, "_MEIPASS", SRC))          # bundled web/ when frozen
LOCAL = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
DATA = Path(os.environ.get("WALKINGPAD_DATA") or (LOCAL / "WalkingPad" if FROZEN else SRC))
INSTALL_DIR = LOCAL / "Programs" / "WalkingPad"
EXE_NAME = "WalkingPad.exe"
EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]
NO_WINDOW = 0x08000000


def open_window(url):
    """Open the app in its own window (Edge app mode), or the default browser."""
    if os.environ.get("WALKINGPAD_NO_WINDOW"):        # tests
        return
    edge = next((p for p in EDGE if p.exists()), None)
    if edge:
        DATA.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([str(edge), f"--app={url}", "--window-size=1180,860", f"--user-data-dir={DATA / '.edge-app'}"])
    else:
        webbrowser.open(url)


def _shortcut(path, target, args="", icon=None, desc="Walking Pad"):
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:WP_LNK);"
          "$s.TargetPath=$env:WP_TARGET;$s.Arguments=$env:WP_ARGS;$s.WorkingDirectory=$env:WP_DIR;"
          "$s.IconLocation=$env:WP_ICON;$s.Description=$env:WP_DESC;$s.Save()")
    env = {**os.environ, "WP_LNK": str(path), "WP_TARGET": str(target), "WP_ARGS": args, "WP_DIR": str(Path(target).parent),
           "WP_ICON": f"{icon or target},0", "WP_DESC": desc}
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], env=env, creationflags=NO_WINDOW, check=False)


def _folders():
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    programs = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    desktop = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    return desktop, programs, programs / "Startup"


def install_if_needed():
    """First run of a downloaded exe: copy to Programs, add shortcuts (Desktop, Start menu, Startup,
    Uninstall), start the installed copy and return True so the caller exits. Returns False otherwise."""
    if not FROZEN:
        return False
    me = Path(sys.executable).resolve()
    target = INSTALL_DIR / EXE_NAME
    if me == target.resolve() if target.exists() else False:
        return False
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(me, target)
    except PermissionError:
        # an older copy is running: stop it, then replace it
        subprocess.run(["taskkill", "/F", "/IM", EXE_NAME], creationflags=NO_WINDOW, capture_output=True)
        shutil.copy2(me, target)
    desktop, programs, startup = _folders()
    _shortcut(desktop / "Walking Pad.lnk", target)
    _shortcut(programs / "Walking Pad.lnk", target)
    _shortcut(startup / "Walking Pad.lnk", target, "--background", desc="Walking Pad (keeps logging your walks)")
    _shortcut(programs / "Uninstall Walking Pad.lnk", target, "--uninstall", desc="Remove Walking Pad")
    subprocess.Popen([str(target)], cwd=str(INSTALL_DIR))
    return True


def uninstall():
    """Remove shortcuts and the program. Walking data in %LOCALAPPDATA%\\WalkingPad is kept on purpose."""
    desktop, programs, startup = _folders()
    for p in (desktop / "Walking Pad.lnk", programs / "Walking Pad.lnk", startup / "Walking Pad.lnk", programs / "Uninstall Walking Pad.lnk"):
        p.unlink(missing_ok=True)
    # the running exe can't delete itself: a short-lived cmd does it after we exit
    # retry for up to 60 s: the folder is deletable only after this program (and its message box) has exited
    script = INSTALL_DIR.parent / "walkingpad-uninstall.cmd"
    # (`timeout` needs a console; ping works in a hidden window as a 1-second pause)
    script.write_text(f'@echo off\r\nfor /l %%i in (1,1,60) do (\r\n  ping -n 2 127.0.0.1 >nul\r\n  rmdir /s /q "{INSTALL_DIR}" 2>nul\r\n'
                      f'  if not exist "{INSTALL_DIR}" goto done\r\n)\r\n:done\r\n(goto) 2>nul & del "%~f0"\r\n', encoding="utf-8")
    subprocess.Popen(["cmd", "/c", str(script)], creationflags=NO_WINDOW, cwd=str(INSTALL_DIR.parent))
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Walking Pad was removed.\n\nYour walking history is kept in\n{DATA}\nDelete that folder too if you want it gone.",
                                         "Walking Pad", 0x40)
    except Exception:
        pass
