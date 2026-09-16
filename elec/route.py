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

import json
import os
import shutil
import subprocess
import sys

import pcbnew
import wx
# ⚠ NO MODAL DIALOGS IN A BUILD STEP. KiCad's Python is a wxWidgets application, and a
# failed internal assertion pops a GUI alert -- "Do you want to stop the program?" -- and
# WAITS. On a developer's machine that is a surprise; in any automated run it is a hang
# with no output and no exit code, and the whole point of this directory is that someone
# can run it unattended years from now. One real assertion (a KiCad 10 API change in
# PCB_VIA::GetWidth) surfaced this, and the assertion was worth fixing on its own -- but
# a pipeline that CAN block on a dialog is a defect independent of which dialog it is.
wx.DisableAsserts()


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout                                        # noqa: E402  (needs the path above)

JAVA = os.path.expandvars(
    r"%LOCALAPPDATA%\Programs\temurin\jdk-25.0.4.1+1-jre\bin\java.exe")
# Freerouting 2.4.1 is built for Java 25 (class file 69) -- a Java 21 runtime
# fails to load it at all, which is the first thing to check if this breaks.
JAR = os.path.expandvars(
    r"%LOCALAPPDATA%\Temp\claude\C--Users-gus-Sync-Documents-Archive-3D-public-steel-guitar"
    r"\d7576032-b257-4aee-8a45-89e587fe4007\scratchpad\freerouting.jar")
# ⚠ PASSES ARE OPTIMISER PASSES, AND THEY ARE NOT WHERE THE ROUTING HAPPENS.
# Freerouting finds connectivity in the first pass or two; every pass after that
# re-optimises the whole board, single-threaded, and on the optical board (153 parts)
# each one costs roughly half a minute. 20 passes is ~10 minutes PER ATTEMPT.
#
# MEASURED, on the optical board: 10 passes -> 17 unconnected, 20 -> 15, 30 -> 15 and
# occasionally worse. The curve is flat after about 10, so the extra time buys track
# length and not connectivity. Keep this low while ITERATING on a design and raise it
# for the final run, where shorter tracks are worth the wall clock.
#
# ⚠ THOSE MEASUREMENTS PREDATE THE REPRODUCIBILITY FIX and are worth less than they
# look. They were taken when the same board routed to 14, 17 and 30 on identical input,
# so a 10-versus-20 comparison was one sample each from a distribution wider than the
# difference being measured. The shape of the claim is probably right -- connectivity is
# found early, later passes shorten track -- but the numbers are not evidence. Re-measure
# before leaning on them.
PASSES = 10


def route(stem, passes=None, timeout=900):
    pcb, dsn, ses = stem + ".kicad_pcb", stem + ".dsn", stem + ".ses"
    # ⚠ A BOARD MAY ASK FOR MORE PASSES, and recording that beats remembering it.
    # "Raise it for the final run" is an instruction to a person, and a person who is
    # not there when someone regenerates this in three years. A board that needs 30 says
    # so in its own notes and gets 30 every time it is built.
    if passes is None:
        passes = json.load(open(stem + ".board.json", encoding="utf-8")).get(
            "router_passes", PASSES)
    notes = None
    if os.path.isfile(stem + ".board.json"):
        notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    board = pcbnew.LoadBoard(pcb)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("Specctra DSN export failed")
    print("exported %s (%.0f kB)" % (os.path.basename(dsn), os.path.getsize(dsn) / 1e3))

    # ⚠ DECLARE THE PLANE LAYERS AS PLANES, or the router treats them as free copper.
    # KiCad's Specctra exporter marks EVERY copper layer "(type signal)", so a 4-layer
    # board hands freerouting four routing layers -- including the one the design calls
    # an unbroken ground plane and relies on for the USB pair's impedance reference.
    # It duly routes through it: the optical board's In1.Cu pour came back at 1043 mm2
    # of an original 5729, shredded into islands by tracks laid across it, and the
    # "continuous reference plane" in the header was simply not true of any routed board
    # here. Specctra's own word for this is (type power); freerouting honours it and
    # leaves the layer alone.
    #
    # It also makes the routing PROBLEM smaller and better posed, which is the happy
    # part: two signal layers with a solid reference between them, instead of four
    # layers of contention and a reference that is not there.
    planes = notes.get("plane_layers", ()) if notes else ()
    if planes:
        txt = open(dsn, encoding="utf-8").read()
        for layer in planes:
            marker = "(layer %s\n      (type signal)" % layer
            if marker not in txt:
                raise SystemExit("plane layer %s not found in the DSN as expected"
                                 % layer)
            txt = txt.replace(marker, "(layer %s\n      (type power)" % layer)
        open(dsn, "w", encoding="utf-8").write(txt)
        print("  declared %s as plane layer(s) -- the router will not route on them"
              % ", ".join(planes))

    if not os.path.isfile(JAVA):
        raise SystemExit("no Java 25 runtime at %s" % JAVA)
    # -Djava.awt.headless=true: freerouting has no --no-gui flag and pops an
    # "Autorouter Confirmation" dialog on every run, which steals focus from
    # whoever is at the machine -- and this gets run many times per board.
    # Headless AWT suppresses it and the router works unchanged.
    # -mt 1: freerouting warns that its multi-threaded optimiser is broken and
    # generates clearance violations. Single-threaded costs a fraction of a
    # second on boards this size.
    # ⚠ THE OPTIMISER'S STRATEGY IS A BOARD-LEVEL CHOICE, not a global constant. It
    # changes which nets freerouting revisits and in what order, and on a board that is
    # one or two connections short that is exactly the lever that matters -- far more
    # than the pass count, which buys track length and not connectivity. It is only
    # worth exposing now: before the pipeline was reproducible, comparing two strategies
    # meant comparing two samples from a distribution wider than the difference.
    strat = json.load(open(stem + ".board.json", encoding="utf-8")).get("router")
    cmd = [JAVA, "-Djava.awt.headless=true", "-jar", JAR, "-de", dsn, "-do", ses,
           "-mp", str(passes), "-mt", "1"]
    # ⚠ THE VALUES ARE CASE-SENSITIVE AND A WRONG ONE IS IGNORED IN SILENCE, which is
    # the worst way for an option to fail: a sweep of four strategies came back with four
    # identical boards -- 668 segments each -- and read as "strategy does not matter on
    # this board" when in fact none of them had been applied. Spelled as freerouting
    # spells them, checked here rather than trusted, and the command is printed so the
    # next person can see what actually ran.
    US = {"greedy": "Greedy", "global": "Global", "hybrid": "Hybrid"}
    IS = {"sequential": "Sequential", "random": "random", "prioritized": "prioritized"}
    for flag, key, table in (("-us", "updating", US), ("-is", "selection", IS)):
        want = (strat or {}).get(key)
        if not want:
            continue
        if want.lower() not in table:
            raise SystemExit("%s: router %s=%r is not one of %s"
                             % (os.path.basename(stem), key, want, sorted(table)))
        cmd += [flag, table[want.lower()]]
    if (strat or {}):
        print("  router strategy: %s" % " ".join(cmd[cmd.index("-mt") + 2:]))
    # ⚠ A TIMEOUT HERE MUST NOT LOOK LIKE A ROUTING RESULT. subprocess.run raises
    # TimeoutExpired, which a caller redirecting stderr will never see -- and the board
    # is then left exactly as it was, PLACED AND UNROUTED. Downstream that reads as
    # "the router could not connect anything", which sent me chasing a phantom
    # regression twice. Catch it and say what actually happened.
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SystemExit(
            "freerouting exceeded %d s on %s at %d passes and was killed. The board is "
            "UNROUTED -- it has not silently produced a bad result, it has produced "
            "none. Lower the pass count (the curve is flat past ~10) or raise `timeout`."
            % (timeout, os.path.basename(stem), passes))
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
        # ⚠ AND BUILD CONNECTIVITY FIRST, exactly as layout.py does. The filler uses
        # the connectivity graph to decide which islands are attached to their net, and
        # a board loaded from a file and modified by script has no graph until asked.
        # Skipping it here is subtler than skipping it there, because the board ARRIVES
        # correctly poured: layout.py filled it properly, and this refill then silently
        # discards the lot. The optical board's F.Cu ground pour vanished at exactly
        # this line and took 74 pads with it -- the routed board came back WORSE than
        # before the pour existed, which is a confusing way to learn it.
        board.BuildConnectivity()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        # ⚠ AND CHECK THE STITCHES AGAIN HERE, NOT ONLY IN layout.py. At layout time the
        # plane is poured around 60 parts and every stitch via lands in copper. THIS
        # refill pours it around those parts plus 700 routed tracks, and the plane that
        # results is a different shape -- so a via that was in the plane before routing
        # can be in a hole after it. Every board passes the check in layout.py and
        # output_panel failed it here, which is exactly why it has to run twice.
        if layout._check_stitches_landed(board, notes):
            n_moved = layout.rescue_stray_stitches(board, notes)
            if n_moved:
                # moving copper changes the pour that was just computed, so pour again
                board.BuildConnectivity()
                pcbnew.ZONE_FILLER(board).Fill(board.Zones())
                print("    moved %d of them into the plane and re-poured" % n_moved)
            if layout._check_stitches_landed(board, notes):
                print("    (the rest have nowhere to go: move the part or except the "
                      "pad -- another routing run will not help)")
    # ⚠ THE ROUTER LEAVES SAME-PART GAPS, and they are cheap to close once it has
    # finished. Done here rather than before routing because before routing the same
    # idea is a constraint that costs more than it buys -- see link_same_part_gaps.
    n_link = layout.link_same_part_gaps(board)
    if n_link:
        print("  joined %d same-net pad pair(s) the router left in separate islands"
              % n_link)

    # ⚠ COUNT BEFORE REMOVING. board.Remove() leaves the track container in a state
    # where GetTracks() raises -- the same SWIG ownership hazard that made fp.Remove()
    # corrupt the footprint IO plugin earlier in this file's history. The rule that
    # comes out of both: take every measurement you need from a board BEFORE deleting
    # anything from it, and delete last.
    n = len(list(board.GetTracks()))
    n_junk = layout.drop_degenerate(board)
    if n_junk:
        # the Specctra round trip rounds, and rounding leaves sub-micron fragments
        print("  dropped %d degenerate track fragment(s) from the import" % n_junk)
        n -= n_junk
    board.Save(pcb)
    # ⚠ CANONICALISE THE ROUTED BOARD TOO, for the same reason layout.py does it --
    # and the reason is now MEASURED rather than argued. Two independent runs of the
    # whole pipeline lay 2,299 copper items that are byte-identical: freerouting is
    # deterministic given deterministic input, which is what makes "run the script" a
    # promise rather than a hope. All that separated the two files was 12,268 lines of
    # random UUID. Left alone it would put noise in every diff of a routed board and
    # make "did this change anything?" unanswerable at exactly the point where the
    # answer matters most.
    layout._canonical_uuids(pcb)
    print("%s: %d track segments + vias imported" % (os.path.basename(pcb), n))
    return pcb


if __name__ == "__main__":
    route(os.path.abspath(sys.argv[1]))
