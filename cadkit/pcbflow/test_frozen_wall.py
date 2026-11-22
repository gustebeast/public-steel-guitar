"""Every post-route copper writer asks the one frozen-band wall (lead 2026-11-22).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_frozen_wall.py [<dir holding rPS_11a4's
        routed board as b.kicad_pcb / b.kicad_pro / b.board.json> [<dir holding rPS_11a3's placed
        board as b.*>]]

1. COVERAGE (no board needed): every function in the post-route writer modules that creates or
   moves a track or via (PCB_TRACK( / PCB_VIA( / PCB_ARC( / .Duplicate() / .SetPosition( /
   .SetStart( / .SetEnd() either asks frozen_wall (FrozenWall, or _path_clear which does) or is
   in ALLOW below with the reason it may not. A new writer that does neither fails here.
2. THE HELPER, on rPS_11a4: the GND via rescue_stray_stitches walked into +24V_RIB's F.Cu band
   (106.386, 110.549) is refused for GND and not for +24V_RIB itself.
3. THE WRITER, on rPS_11a4: C136.2's stitch, stray in a plane whose only copper near it is a
   0.6 mm disc on that same band spot. Before the wall rescue_stray_stitches moved it to
   (106.885, 110.306), inside +24V_RIB's band (checked on ck_fzb 4e59444); now it must not
   end in any band.
4. THE RULE AREAS, on rPS_11a3 (optional second dir, its placed board as b.*): the audio moat
   (x 86-87, tracks + vias + fills banned) refuses a 3.79 mm VIN_BUS track centred at x 88.39 on
   B.Cu and any via of radius 0.3 inside it, and lets a 0.25 track at x 88.39 through.
Exit 0 = PASS. Works on the loaded board only; nothing is saved.
"""
from __future__ import annotations
import ast
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# the modules whose code runs after the route (route.post_route's chain and finish's stages)
MODULES = ("layout.py", "route.py", "close_last.py", "eco.py", "power_vias.py",
           "return_vias.py", "unwick.py")
WRITE = re.compile(r"PCB_TRACK\(|PCB_VIA\(|PCB_ARC\(|\.Duplicate\(\)|\.SetPosition\(|\.SetStart\(|\.SetEnd\(")
ASKS = re.compile(r"frozen_wall\.|FrozenWall\(|_path_clear\(")
# (module, top-level function): why it may write without asking the wall
ALLOW = {
    # layout time: these lay copper BEFORE the bands' baseline, which they are part of
    ("layout.py", "_place_ref"): "footprints, not copper",
    ("layout.py", "_anchor_on_courtyard"): "footprints, not copper",
    ("layout.py", "_anchor_on_pads"): "footprints, not copper",
    ("layout.py", "build"): "footprints, not copper",
    ("layout.py", "_diff_pairs"): "layout time: declared pair copper, before the route and the baseline",
    ("layout.py", "_local_nets"): "layout time, before the bands' baseline",
    ("layout.py", "_pour_pad_vias"): "layout time: a band's own barrels, on the band's net",
    ("layout.py", "_spill_vias"): "layout time: a lobe's own barrels and legs, on the band's net",
    ("layout.py", "_stitch_plane_pads"): "layout time: stitches laid before the route, part of the baseline",
    ("layout.py", "_edge_poly"): "board edge graphics, not copper",
    ("layout.py", "_cutout"): "board edge graphics, not copper",
    ("layout.py", "_edge_hole"): "board edge graphics, not copper",
    ("layout.py", "_edge_slot"): "board edge graphics, not copper",
    ("layout.py", "_edge_rect"): "board edge graphics, not copper",
    ("layout.py", "_add_track"): "layout time: declared copper from the notes",
    ("layout.py", "_add_via"): "layout time: declared copper from the notes",
    ("layout.py", "_edge_row_escape"): "layout time: declared escape stubs",
    # post-route, but cannot enter a band
    ("layout.py", "tidy_router_vias"): "merges two overlapping vias of one net: the joining track lies inside their own pads",
    ("layout.py", "snap_hairline_gaps"): "closes a sub-eps gap between two ends of one net on one layer",
    ("layout.py", "_hop_via_inner"): "every site and leg is asked through its caller's clear (link_close_gaps), which asks the wall",
    ("route.py", "_resite_post_pads"): "footprints, not copper",
    ("route.py", "post_route"): "places post-route footprints, not copper",
    ("route.py", "route"): "re-lays declared frozen nets' own copper from the unrouted board",
    ("close_last.py", "_lay"): "lays the router model's path, whose search walls the bands (frozen_d)",
    ("eco.py", "move"): "a scripted ECO; eco runs frozen_check on the result and refuses a cut",
    ("power_vias.py", "main"): "lays the sites plan() chose, and plan()'s ok() asks the wall",
    ("return_vias.py", "main"): "lays the sites plan() chose, and plan()'s ok() asks the wall",
}


def coverage():
    bad, seen = [], set()
    # a module that makes tracks or vias and is not scanned at all is the gap this test exists for
    import glob
    for f in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        nm = os.path.basename(f)
        if nm.startswith("test_") or nm in MODULES:
            continue
        if re.search(r"PCB_TRACK\(|PCB_VIA\(|PCB_ARC\(|\.Duplicate\(\)", open(f, encoding="utf-8").read()):
            bad.append("%s makes tracks or vias and is not in MODULES" % nm)
    for mod in MODULES:
        src = open(os.path.join(HERE, mod), encoding="utf-8").read()
        lines = src.splitlines()
        tops = [(n.lineno, n.end_lineno, n.name) for n in ast.parse(src).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for a, e, name in tops:
            body = [l for l in lines[a - 1:e] if not l.lstrip().startswith("#")]
            if not any(WRITE.search(l) for l in body):
                continue
            seen.add((mod, name))
            if (mod, name) in ALLOW:
                continue
            if not any(ASKS.search(l) for l in body):
                bad.append("%s %s writes copper and never asks frozen_wall" % (mod, name))
    for mod in ("power_vias.py", "return_vias.py"):
        src = open(os.path.join(HERE, mod), encoding="utf-8").read()
        plan = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "plan")
        if not any(ASKS.search(l) for l in src.splitlines()[plan.lineno - 1:plan.end_lineno]):
            bad.append("%s plan() no longer asks frozen_wall, and main lays what it plans" % mod)
    stale = sorted(k for k in ALLOW if k not in seen)
    for k in stale:
        bad.append("ALLOW lists %s %s, which writes nothing now -- drop it" % k)
    return bad


def on_board(d):
    try:
        import wx as _wx
        _wx.DisableAsserts()
    except Exception:
        pass
    import pcbnew
    import frozen_wall
    import layout
    F = pcbnew.FromMM
    bad = []
    b = pcbnew.LoadBoard(os.path.join(d, "b.kicad_pcb"))
    notes = json.load(open(os.path.join(d, "b.board.json"), encoding="utf-8"))
    SITE, ANCH = (106.386471, 110.548528), (107.235, 109.7)
    w = frozen_wall.FrozenWall(b)
    hit = w.band_at(F(SITE[0]), F(SITE[1]), "GND", F(0.3))
    if not hit or hit["net"] != "+24V_RIB":
        bad.append("the wall lets a GND via in at %s (band %s)" % (SITE, hit and hit["net"]))
    if w.band_at(F(SITE[0]), F(SITE[1]), "+24V_RIB", F(0.3)):
        bad.append("the wall refuses +24V_RIB its own band")
    v = next((t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"
              and abs(pcbnew.ToMM(t.GetPosition().x) - SITE[0]) < 0.01
              and abs(pcbnew.ToMM(t.GetPosition().y) - SITE[1]) < 0.01), None)
    feed = v and next((t for t in b.GetTracks() if t.GetClass() != "PCB_VIA"
                       and t.GetNetname() == "GND" and t.GetEnd() == v.GetPosition()), None)
    if feed is None:
        return bad + ["C136.2's via and its feed are not on this board -- wrong board?"]
    disc = pcbnew.SHAPE_POLY_SET()
    disc.NewOutline()
    for k in range(32):
        disc.Append(F(SITE[0] + 0.6 * math.cos(k * math.pi / 16)), F(SITE[1] + 0.6 * math.sin(k * math.pi / 16)))
    for z in b.Zones():
        if z.GetNetname() == "GND":
            for L in z.GetLayerSet().CuStack():
                z.SetFilledPolysList(L, disc)
    start = pcbnew.VECTOR2I(F(ANCH[0] + 0.6), F(ANCH[1]))
    v.SetPosition(start)
    feed.SetEnd(start)
    layout.rescue_stray_stitches(b, notes)
    p = v.GetPosition()
    hit = frozen_wall.FrozenWall(b).band_at(p.x, p.y, "GND", F(0.3))
    print("rescue left C136.2's stitch at (%.3f, %.3f)%s" % (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y),
                                                            ", in %s's band" % hit["net"] if hit else ""))
    if hit:
        bad.append("rescue_stray_stitches put a GND via in %s's frozen band" % hit["net"])
    return bad


def on_moat(d):
    try:
        import wx as _wx
        _wx.DisableAsserts()
    except Exception:
        pass
    import pcbnew
    import frozen_wall
    F = pcbnew.FromMM
    w = frozen_wall.FrozenWall(pcbnew.LoadBoard(os.path.join(d, "b.kicad_pcb")))
    bad = []
    a, e = (F(88.39), F(79.85)), (F(88.39), F(63.45))
    if w.seg_ok(a, e, "VIN_BUS", F(3.79) / 2, pcbnew.B_Cu):
        bad.append("a 3.79 mm VIN_BUS track with its edge in the moat passes the wall")
    if not w.seg_ok(a, e, "VIN_BUS", F(0.25) / 2, pcbnew.B_Cu):
        bad.append("a 0.25 track 1.39 mm off the moat is refused")
    if w.via_ok(F(86.5), F(70.0), "VIN_BUS", F(0.3)):
        bad.append("a via in the moat passes the wall")
    return bad


if __name__ == "__main__":
    bad = coverage()
    print("coverage: %s" % ("ok" if not bad else "%d problem(s)" % len(bad)))
    if len(sys.argv) > 1:
        bad += on_board(os.path.abspath(sys.argv[1]))
    if len(sys.argv) > 2:
        bad += on_moat(os.path.abspath(sys.argv[2]))
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
