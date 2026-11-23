"""unconnected.py BOARD.kicad_pcb [...]: KiCad's own count of unconnected joins (ratsnest lines) per board.

    "C:/Program Files/KiCad/10.0/bin/python.exe" unconnected.py a.kicad_pcb b.kicad_pcb

One line a board: "<path> <count>". ab_judge reads it when a run's log carries no router
joins_open: a place_flow --no-score run never runs router/score.py, so every A/B of finished
boards read None there (rPS_sqe / sov, 2026-11-22). This counts on the finished board itself.
"""
import os
import sys

try:
    import wx as _wx
    _wx.DisableAsserts()
except Exception:
    pass
import pcbnew  # noqa: E402

for p in sys.argv[1:]:
    b = pcbnew.LoadBoard(p)
    b.BuildConnectivity()
    print("%s %d" % (p, b.GetConnectivity().GetUnconnectedCount(True)), flush=True)
os._exit(0)
