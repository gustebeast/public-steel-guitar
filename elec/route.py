"""Autoroute a placed board: .kicad_pcb -> Specctra .dsn -> freerouting -> .ses -> board.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/route.py elec/out/lever_sensor

RUNS UNDER KICAD'S PYTHON, like layout.py and for the same reason (pcbnew).

WHY AUTOROUTE THIS ONE AND NOT THE OTHERS. The tee and the TRRS adapter are four
nets of straight track and a pour -- hand-routing them in `tracks` gives better
copper than any router would, and the source stays readable. The lever board is
29 parts and 20 nets on four layers, where hand-specifying every segment would be
neither reviewable nor better. Freerouting is the right tool at that size.

The router is NOT authoritative: it produces a candidate, and `kicad-cli pcb drc`
is what says whether the candidate is acceptable. Re-running can give a different
result, so the routed .kicad_pcb is a build artifact like the netlist -- the
placement in <board>.board.json is the thing under version control.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pcbnew

JAVA = os.path.expandvars(
    r"%LOCALAPPDATA%\Programs\temurin\jdk-25.0.4.1+1-jre\bin\java.exe")
# Freerouting 2.4.1 is built for Java 25 (class file 69) -- a Java 21 runtime
# fails to load it at all, which is the first thing to check if this breaks.
JAR = os.path.expandvars(
    r"%LOCALAPPDATA%\Temp\claude\C--Users-gus-Sync-Documents-Archive-3D-public-steel-guitar"
    r"\d7576032-b257-4aee-8a45-89e587fe4007\scratchpad\freerouting.jar")
PASSES = 20


def route(stem, passes=PASSES):
    pcb, dsn, ses = stem + ".kicad_pcb", stem + ".dsn", stem + ".ses"
    board = pcbnew.LoadBoard(pcb)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("Specctra DSN export failed")
    print("exported %s (%.0f kB)" % (os.path.basename(dsn), os.path.getsize(dsn) / 1e3))

    if not os.path.isfile(JAVA):
        raise SystemExit("no Java 25 runtime at %s" % JAVA)
    # -Djava.awt.headless=true: freerouting has no --no-gui flag and pops an
    # "Autorouter Confirmation" dialog on every run, which steals focus from
    # whoever is at the machine -- and this gets run many times per board.
    # Headless AWT suppresses it and the router works unchanged.
    # -mt 1: freerouting warns that its multi-threaded optimiser is broken and
    # generates clearance violations. Single-threaded costs a fraction of a
    # second on boards this size.
    cmd = [JAVA, "-Djava.awt.headless=true", "-jar", JAR, "-de", dsn, "-do", ses,
           "-mp", str(passes), "-mt", "1"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    tail = (r.stdout or "").strip().splitlines()[-6:]
    print("\n".join("  " + t for t in tail))
    if not os.path.isfile(ses):
        raise SystemExit("freerouting produced no session file\n" + (r.stderr or "")[-800:])

    # Import onto a FRESH copy: ImportSpecctraSES adds tracks to the board it is
    # given, so importing twice onto the same file stacks two routings.
    shutil.copyfile(pcb, stem + ".unrouted.kicad_pcb")
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit("Specctra SES import failed")
    # CLAMP ANY TRACK THE ROUTER NECKED BELOW THE FAB FLOOR. Freerouting works in
    # its own units and rounds, so it lands a couple of segments at 0.125 against
    # JLCPCB's 0.127 minimum -- 2 microns under, but under. Widening a track can
    # only reduce clearance, never create an open, and the DRC pass afterwards is
    # what confirms the widening did not cost anything.
    floor = board.GetDesignSettings().m_TrackMinWidth
    necked = 0
    for t in board.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < floor:
            t.SetWidth(floor)
            necked += 1
    if necked:
        print("  widened %d track(s) back up to the %.3f mm floor"
              % (necked, pcbnew.ToMM(floor)))

    # REFILL THE POURS. layout.py fills them at creation, before any routing
    # exists, so every via the router adds lands in copper that has no clearance
    # cut-out around it -- 164 violations on the first try, all of them a zone
    # against a via that was not there when it was filled.
    if board.Zones():
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(pcb)
    n = len(list(board.GetTracks()))
    print("%s: %d track segments + vias imported" % (os.path.basename(pcb), n))
    return pcb


if __name__ == "__main__":
    route(os.path.abspath(sys.argv[1]))
