"""No console windows for pcbflow's children on Windows. Import it first: `import _nowindow`.

⚠ WHY (user, 2026-11-13: "terminal windows pop up and close immediately in rapid succession"):
a flow run in the background has NO console of its own, and on Windows every console program
it starts (KiCad's python for each finish step, kicad-cli, the router) then allocates a fresh,
VISIBLE one -- a window flashing per step, dozens a run. cadkit's view and git helpers already
pass CREATE_NO_WINDOW (tools/agent_sync.py, web/view.py); pcbflow's ~40 subprocess calls did
not.

So every Popen (run / call / check_output go through it) gets CREATE_NO_WINDOW -- ONLY when
this process has no console. With a console the children share it (no window appears) and
their output must keep reaching it: under NO_WINDOW a child that inherits the console handles
would print into a hidden console instead. Never beside DETACHED_PROCESS or CREATE_NEW_CONSOLE
(Windows ignores NO_WINDOW next to DETACHED; NEW_CONSOLE asks for a window on purpose).
"""
import os
import subprocess

_NO_WINDOW = 0x08000000
_DETACHED, _NEW_CONSOLE = 0x00000008, 0x00000010


def _no_console():
    try:
        import ctypes
        return not ctypes.windll.kernel32.GetConsoleWindow()
    except Exception:
        return False


if os.name == "nt" and not getattr(subprocess.Popen, "_pcbflow_nowindow", False) and _no_console():
    _init = subprocess.Popen.__init__

    def __init__(self, *args, **kw):
        fl = kw.get("creationflags", 0) or 0
        if not fl & (_DETACHED | _NEW_CONSOLE):
            kw["creationflags"] = fl | _NO_WINDOW
        _init(self, *args, **kw)

    subprocess.Popen.__init__ = __init__
    subprocess.Popen._pcbflow_nowindow = True
