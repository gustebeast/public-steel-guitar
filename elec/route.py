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
import re
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
# ⚠ PASSES BUY CONNECTIVITY ON A HARD BOARD, AND THIS COMMENT USED TO SAY THEY DO NOT.
# The old claim was that freerouting finds connectivity in the first pass or two and
# every pass after that only shortens track, so "the curve is flat after about 10". It
# was measured on the small boards, where it is true because they finish. On the optical
# board it is false, and not marginally:
#
#     1 pass  -> 105 unconnected
#     3       ->  50
#    10       ->  13
#    25       ->   6          (1069 s, against ~700 for ten)
#
# Half the failures of a ten-pass run are still there because the optimiser has not got
# to them yet. That is what a board near its routing limit looks like: the early passes
# leave a mess that later passes rip up and re-lay, and stopping early freezes the mess.
# 60% more wall clock for 54% fewer failures is not a marginal trade.
#
# SO THE RULE IS PER-BOARD, not global. Boards that finish easily gain nothing past ten
# and should not pay for the passes; boards that do not finish should ask for more via
# `router_passes` (optical does). Keep this default low for iteration.
#
# ⚠ AND RAISE `timeout` WITH THE PASS COUNT. 25 passes on the optical board needs about
# 1070 s and the default was 900, so the first attempt at this measurement was KILLED --
# and the DRC that followed reported 266 unconnected, which is the UNROUTED board. A
# timeout that fires looks exactly like a routing result unless you read the log.
DSN_CLEAR_MARGIN_UM = 10      # see the clearance block in route()
NL = chr(10)
PASSES = 10


def failing_nets(stem):
    """The nets the last DRC left unconnected, for an incremental re-route."""
    d = json.load(open(stem + ".finish.drc.json", encoding="utf-8"))
    out = set()
    for v in d.get("unconnected_items", []):
        for item in v["items"]:
            m = re.search(r"\[([^\]]+)\]", item.get("description", ""))
            if m:
                out.add(m.group(1))
    return sorted(out)


def route(stem, passes=None, timeout=3600, incremental=False):
    """Route the board at `stem`.

    ⚠ `incremental` ROUTES FROM THE BOARD AS IT STANDS, NOT FROM A FRESH PLACEMENT, and
    it is the answer to "must every experiment cost a full run". The normal path throws
    the routing away (finish.py re-runs layout.py first) and hands freerouting all 96
    nets; incremental hands it the routed board with every net FROZEN except the handful
    DRC says are still unconnected. The router then has one small problem instead of a
    whole board, and the copper it already got right cannot be disturbed.

    It only became possible once the frozen-copper restore existed. Freezing a wire in
    the DSN is half the operation -- the session file does not carry fixed wires, so
    without the re-lay below an incremental run would delete everything it froze, which
    is exactly the bug that cost a routing run to find.

    ⚠ IT IS NOT A SUBSTITUTE FOR A FULL RUN. The frozen copper is an obstacle the router
    cannot move, so a net that fails because its neighbour took the only channel will go
    on failing. Use it to attack the last few nets on a board that is otherwise good;
    use a full run after anything that changes the netlist or the placement.
    """
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

    # ⚠ THE ROUTER IS GIVEN MORE CLEARANCE THAN THE FAB RULE, ON PURPOSE. freerouting
    # routes right up to the clearance it is handed, and its geometry and KiCad's do not
    # round the same way -- so a board it considers finished comes back with tracks
    # 0.1212-0.1247 mm apart against a 0.127 mm rule. Four such violations on the optical
    # board, all of them 4-6 um short, all of them freerouting's own copper touching
    # freerouting's own copper. There is nothing to fix on the board; the router simply
    # aims at the line instead of inside it.
    #
    # THE FIX BELONGS IN THE DSN, NOT IN THE DESIGN RULE. Raising the netclass to 0.137
    # would raise it for the fab as well, and 0.127 mm is what the cheap JLCPCB process
    # is quoted at -- we want the real rule checked by the real DRC. So the exported DSN
    # gets the margin and the board keeps its rule: the router aims 10 um inside the
    # line, DRC still measures against the line.
    #
    # The smd_smd clearance is deliberately NOT bumped. That one is pad-to-pad, decided
    # by placement before the router ever runs, and widening it only makes the router
    # refuse geometry that is already legal and already built.
    txt = open(dsn, encoding="utf-8").read()
    bumped = set()

    def _bump(m):
        v = float(m.group(1))
        bumped.add(v)
        return "(clearance %g)" % (v + DSN_CLEAR_MARGIN_UM)

    txt, n_bump = re.subn(r"\(clearance ([\d.]+)\)", _bump, txt)
    if not n_bump:
        raise SystemExit("no plain (clearance N) rule in the DSN -- cannot add the "
                         "router margin, and routing without it produces violations")
    # ⚠ THE COPPER THE GENERATOR LAID IS HANDED TO THE ROUTER AS A SUGGESTION, AND FOR
    # THE DIFFERENTIAL PAIR THAT IS A BUG. kicad-cli exports every existing track as
    # `(type route)`, which in Specctra means the router owns it and may rip it up -- so
    # all 223 pre-laid segments are advisory. For the GND stitches and the local nets
    # that is fine and arguably the point; they were measured as a help, not a promise.
    #
    # FOR A COUPLED PAIR IT DEFEATS THE ENTIRE ROUTINE THAT LAID IT. _diff_pairs exists
    # because freerouting has no concept of a differential pair and routes D+ and D- as
    # two independent nets; it builds both rails by offsetting ONE centreline so they
    # cannot diverge. Measured on 2026-09-17, the generator handed over
    #     DP 11.62 mm / 8 segments / 0 vias      DM 11.80 mm / 8 segments / 0 vias
    # -- matched to 0.18 mm, same shape -- and freerouting gave back
    #     DP 12.78 mm / 7 segments / 1 via       DM 15.44 mm / 12 segments / 0 vias
    # which is 2.66 mm of mismatch, different segment counts, and a via on one rail
    # only. That is not a pair. It is the exact defect the docstring of _diff_pairs
    # opens by describing, reintroduced one step downstream, and nothing downstream
    # could see it: DRC checks copper against the netlist and both nets were connected.
    #
    # `(type fix)` is freerouting's "do not touch" -- its FixedState has UNFIXED,
    # SHOVE_FIXED, USER_FIXED and SYSTEM_FIXED, and only the last two survive a rip-up
    # pass unchanged. SHOVE_FIXED would let the pair be shoved, which changes the
    # geometry and so is no better for coupling.
    #
    # ONLY THE DECLARED PAIRS ARE FROZEN BY DEFAULT. Freezing everything is a different
    # question with a real trade behind it -- pre-laid copper becomes a hard obstacle
    # instead of negotiable, which this project has measured going the wrong way before
    # -- so it is exposed as `fix_prelaid` in the board notes to be MEASURED rather than
    # assumed. The pairs are not a trade: copper that must not move, must not move.
    frozen = set()
    for spec in (notes or {}).get("diff_pairs", ()):
        frozen.update(spec.get("nets", ()))
    pair_nets = None if (notes or {}).get("fix_prelaid") else frozen
    if incremental:
        # Everything that HAS copper is frozen except the nets still unfinished.
        free = set(failing_nets(stem))
        have = {t.GetNetname() for t in board.GetTracks() if t.GetNetname()}
        frozen = have - free
        pair_nets = frozen
        print("  incremental: %d net(s) left free (%s), %d frozen"
              % (len(free), ", ".join(sorted(free)) or "-", len(frozen)))

    def _fix(m):
        if pair_nets is None or m.group(1) in pair_nets:
            _fix.n += 1
            return "(net %s)(type fix)" % m.group(1)
        return m.group(0)
    _fix.n = 0
    txt = re.sub(r"\(net ([^)]+)\)\(type route\)", _fix, txt)
    if frozen and not _fix.n:
        raise SystemExit(
            "no pre-laid wiring found for the declared differential pair(s) %s -- the "
            "pair is supposed to be generated before the router sees it, so either it "
            "was not laid or the DSN's wire syntax has changed. Routing on would hand "
            "the pair to freerouting, which does not know it is one."
            % ", ".join(sorted(pair_nets)))

    # ⚠ LAYER COSTS, BECAUSE ONE LAYER WAS HALF EMPTY WHILE ANOTHER OVERFLOWED. Measured
    # in the MCU approach corridor on the optical board: F.Cu 10.6% copper, In2.Cu 12.8%,
    # B.Cu 4.6% -- the bottom layer carrying less than half what the top does, in the one
    # region where the board ran out of room. freerouting will not use a layer it has no
    # reason to prefer, and by default it has none.
    # `layer_costs` in the board notes maps a layer to its trace cost: below 1.0 makes the
    # router prefer it. Emitted as an autoroute_settings block.
    #
    # THE BLOCK GOES INSIDE (structure ...), AND THAT IS NOT A STYLE POINT. The first
    # version of this emitted it as a sibling of `structure`, one line above `(placement`,
    # and freerouting produced a BYTE-IDENTICAL board -- the same three nets unconnected,
    # the same 2426 segments, the same md5. A DSN reader skips a scope it does not know at
    # the level it is reading, silently and with no warning, so a mis-placed block looks
    # exactly like a lever that does not work. The scope is read by
    # app/freerouting/io/specctra/parser/Structure, confirmed by grepping the jar for the
    # class that references AutorouteSettings; the keywords below are its spelling,
    # singular `_cost`, checked the same way.
    #
    # ⚠ SO AN EXPERIMENT THAT CHANGES NOTHING AT ALL IS A BUG REPORT, NOT A RESULT. Two
    # earlier experiments on this board (60 passes, incremental) also returned identical
    # output, and there the identity was the honest answer. Here it meant the input never
    # arrived. Compare the md5 of the routed board before concluding a lever is dead.
    #
    # ⚠ (autoroute on) AND (postroute on) ARE NOT OPTIONAL PADDING -- LEAVING THEM OUT
    # TURNS THE ROUTER OFF. AutorouteSettings.readScope keeps two local flags and calls
    # setRunRouter/setRunOptimizer with them once the scope closes, whether or not the
    # clauses appeared; absent means false. Emitting the layer rules alone therefore reads
    # as "route nothing, optimise nothing", and the board came back with 294 segments
    # instead of 2426 and 190 nets unconnected. The block is not a patch over the
    # defaults, it REPLACES the two run flags.
    #
    # ⚠ THE COST KEYWORDS ARE PLURAL, AND A SUBSTRING GREP CANNOT TELL YOU THAT. Checking
    # the jar for "preferred_direction_trace_cost" matched -- because the real keyword,
    # PREFERRED_DIRECTION_TRACE_COSTS, contains it. The singular form was skipped as an
    # unknown key word. Match keywords whole, or read what the writer emits: the writer in
    # that same class writes "(preferred_direction_trace_costs ".
    costs = (notes or {}).get("layer_costs")
    if costs:
        rules = "".join(
            NL + "    (layer_rule %s (active on)"
            " (preferred_direction_trace_costs %s)"
            " (against_preferred_direction_trace_costs %s))"
            % (ln, c, round(float(c) * 1.6, 3)) for ln, c in sorted(costs.items()))
        blk = ("  (autoroute_settings" + NL
               + "    (autoroute on)" + NL          # see above -- absent means OFF
               + "    (postroute on)" + rules + NL + "  )" + NL)
        # the last line of the structure scope, i.e. the ")" that closes it
        anchor = "  )" + NL + "  (placement"
        if anchor not in txt:
            raise SystemExit("cannot find the end of the (structure scope in the DSN -- "
                             "autoroute_settings would be read by nothing")
        txt = txt.replace(anchor, blk + anchor, 1)   # BEFORE the closing ")"
        assert txt.index("(autoroute_settings") < txt.index("  (placement")
        print("  layer costs: %s" % ", ".join("%s=%s" % kv for kv in sorted(costs.items())))

    open(dsn, "w", encoding="utf-8").write(txt)
    if _fix.n:
        print("  froze %d pre-laid wire(s) as (type fix)%s" % (
            _fix.n, "" if pair_nets is None else " -- the declared pair(s)"))
    print("  router clearance %s um (fab rule %s um + %g um of rounding margin)"
          % ("/".join("%g" % (v + DSN_CLEAR_MARGIN_UM) for v in sorted(bumped)),
             "/".join("%g" % v for v in sorted(bumped)), DSN_CLEAR_MARGIN_UM))

    if not os.path.isfile(JAVA):
        raise SystemExit("no Java 25 runtime at %s" % JAVA)
    # -Djava.awt.headless=true: freerouting has no --no-gui flag and pops an
    # "Autorouter Confirmation" dialog on every run, which steals focus from
    # whoever is at the machine -- and this gets run many times per board.
    # Headless AWT suppresses it and the router works unchanged.
    # ⚠ -mt 1 BY DEFAULT: freerouting warns that its multi-threaded optimiser is broken
    # and generates clearance violations, and a board that cannot be manufactured is not
    # worth any amount of wall clock. The note that used to sit here also claimed single
    # threading "costs a fraction of a second on boards this size" -- true when the boards
    # were 20 parts, and badly false now: the optical board takes ten minutes, which is
    # the main brake on iterating it.
    # So `threads` is exposed per board to be MEASURED rather than assumed. Raising it is
    # only defensible if the result is both violation-free and reproducible, and both are
    # checkable.
    # ⚠ THE OPTIMISER'S STRATEGY IS A BOARD-LEVEL CHOICE, not a global constant. It
    # changes which nets freerouting revisits and in what order, and on a board that is
    # one or two connections short that is exactly the lever that matters -- far more
    # than the pass count, which buys track length and not connectivity. It is only
    # worth exposing now: before the pipeline was reproducible, comparing two strategies
    # meant comparing two samples from a distribution wider than the difference.
    strat = json.load(open(stem + ".board.json", encoding="utf-8")).get("router")
    cmd = [JAVA, "-Djava.awt.headless=true", "-jar", JAR, "-de", dsn, "-do", ses,
           "-mp", str(passes), "-mt", str((strat or {}).get("threads", 1))]
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
            "none. Lower the pass count or raise `timeout` -- and note that passes DO "
            "buy connectivity on this board, so lowering them has its own cost."
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

    # PUT THE FROZEN COPPER BACK, BECAUSE THE SESSION FILE DOES NOT CARRY IT. This is
    # the half of `(type fix)` that a reasonable reading of Specctra misses, and it cost
    # a routing run to find: a SESSION file reports what the ROUTER did, and a fixed
    # wire is by definition not something the router did. freerouting therefore omits it
    # -- measured, 797 wires in the session and not one of them on either pair net --
    # and ImportSpecctraSES replaces the board's routing wholesale, so the frozen pair
    # was not preserved but DELETED. The board came back with the pair 11.62 mm shorter
    # and five of its eight unconnected items on USB_DP/USB_DM, which reads exactly like
    # a router that ran out of room and is nothing of the kind.
    #
    # The router still SAW the copper -- it routed around it as an obstacle, which is
    # what freezing is for -- so re-laying it here is geometrically consistent with
    # everything else in the session, not a patch over a conflict.
    #
    # ⚠ THIS IS ALSO THE MECHANISM FOR INCREMENTAL ROUTING, and the reason to get it
    # right rather than revert. "Freeze what already routed, re-run only the failures"
    # needs exactly these two halves: fix the wires in the DSN so the router leaves them
    # alone, and re-lay them here so they survive the import.
    if frozen:
        src = pcbnew.LoadBoard(stem + ".unrouted.kicad_pcb")
        back = 0
        for t in src.GetTracks():
            if t.GetNetname() not in frozen:
                continue
            net = board.FindNet(t.GetNetname())
            if net is None:
                raise SystemExit("frozen net %s is not on the board after import"
                                 % t.GetNetname())
            if t.GetClass() == "PCB_VIA":
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(t.GetPosition())
                v.SetWidth(t.GetWidth())
                v.SetDrill(t.GetDrill())
                v.SetViaType(t.GetViaType())
                v.SetNet(net)
                board.Add(v)
            else:
                k = pcbnew.PCB_TRACK(board)
                k.SetStart(t.GetStart())
                k.SetEnd(t.GetEnd())
                k.SetWidth(t.GetWidth())
                k.SetLayer(t.GetLayer())
                k.SetNet(net)
                board.Add(k)
            back += 1
        print("  re-laid %d frozen wire(s) the session file does not carry" % back)
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
    # ⚠ SNAP THE HAIRLINES FIRST. A gap of a couple of microns cannot be repaired by
    # laying copper across it -- the segment that results is itself degenerate and the
    # clean-up below removes it again, which is a loop the logs do not show. Move the
    # endpoint instead; see snap_hairline_gaps.
    n_snap = layout.snap_hairline_gaps(board)
    if n_snap:
        print("  snapped %d hairline gap(s) shut (no copper added)" % n_snap)
        board.BuildConnectivity()
    # ⚠ AND THE LAYER CHANGES THE ROUND TRIP DROPPED. Two tracks of one net ending at
    # the same point on DIFFERENT layers is a via that went missing, not a gap -- no
    # amount of re-routing recovers it and no copper can bridge it. See add_missing_vias.
    n_via = layout.add_missing_vias(board)
    if n_via:
        print("  dropped in %d via(s) where a net changed layer with nothing to carry it"
              % n_via)
        board.BuildConnectivity()
    n_link = layout.link_close_gaps(board, layout._outline_pts(notes),
                                   same_part_only=False)
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

    # ⚠ POUR AGAIN, BECAUSE THE REPAIRS ABOVE ADDED COPPER AFTER THE LAST POUR. The
    # zones were last filled before the repair block; snap/add_missing_vias/link then
    # put down vias and tracks, and a zone does not know to clear around copper that
    # arrived after it was computed. The result is a via sitting in un-cleared pour --
    # which DRC reports as a clearance AND a hole-clearance violation against the zone,
    # and which looks like a badly placed via rather than a stale pour.
    # Measured: five violations on the optical board, four of them this, from two vias.
    if board.Zones():
        board.BuildConnectivity()
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
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
    _p = None
    for _a in sys.argv[2:]:
        if _a.startswith("--passes="):
            _p = int(_a.split("=", 1)[1])
    route(os.path.abspath(sys.argv[1]), passes=_p,
          incremental="--incremental" in sys.argv[2:])
