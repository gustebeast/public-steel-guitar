"""A26-A31's fail harness: break a real board's power layout on purpose, in memory.

    PYTHONPATH=<headless> "C:/Program Files/KiCad/10.0/bin/python.exe" \
        cadkit/pcbflow/test_quality_a26_31.py <stem>

The stem is a brain_board run with esc10's quality notes (power_paths with switch nodes,
power_exempt, hot_loops, gate_drives, sense_pairs, supply_pins) and its declared copper laid
(brain_board esc10_pre12/pre/pre was the reference). Then:

  0  the board as it is                    -> no FAIL from A26, A27, A28, A31; A30 ISP5/ISN5 PASS
  1  SW5_1 dropped from power_paths        -> A26 FAIL for SW5_1 (an inductor net nothing sizes)
  2  a via added on SW5_1                  -> A27 FAIL: a switch node leaves its layer
  3  C218 moved 5 mm off U205              -> A28 FAIL for U205's VIN loop
  4  ISN5's In2 track moved 1 mm away      -> A30 FAIL: the pair is not side by side
  5  U44's supply_pins entry deleted       -> A31 FAIL for U44
  6  BST_LO drawn pad to pad, max_mm 1     -> A29 FAIL on length

Each case is reverted before the next. Exit code 0 = every case answered as it should.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
import quality as Q  # noqa: E402

ctx = Q.Ctx(sys.argv[1])
pcbnew.ZONE_FILLER(ctx.board).Fill(ctx.board.Zones())
bad = []


def run(rid):
    return list(Q.RULES[rid](ctx))


def fails(rid, pred=lambda s, t: True):
    return [(s, t) for s, ok, t in run(rid) if ok is False and pred(s, t)]


def check(name, cond, detail=""):
    print("%-4s %s%s" % ("ok" if cond else "BAD", name, (" -- " + detail) if detail and not cond else ""))
    if not cond:
        bad.append(name)


# 0: as it is
for rid in ("A26", "A27", "A28", "A31"):
    f = fails(rid)
    check("0 %s clean" % rid, not f, "; ".join(t for _, t in f[:3]))
check("0 A30 ISP5/ISN5 pass", any(s == "ISP5/ISN5" and ok for s, ok, _ in run("A30")))

# 1: SW5_1 out of power_paths
pp = ctx.q["power_paths"]
ctx.q["power_paths"] = [p for p in pp if p["net"] != "SW5_1"]
check("1 A26 SW5_1 FAIL", bool(fails("A26", lambda s, t: s == "SW5_1")))
ctx.q["power_paths"] = pp

# 2: a via on SW5_1
via = pcbnew.PCB_VIA(ctx.board)
via.SetPosition(ctx.pads["L202.1"].GetPosition())
via.SetDrill(pcbnew.FromMM(0.3))
via.SetWidth(pcbnew.FromMM(0.6))
via.SetNet(ctx.board.FindNet("SW5_1"))
ctx.board.Add(via)
check("2 A27 SW5_1 layers FAIL", bool(fails("A27", lambda s, t: s == "SW5_1 layers")))
ctx.board.Remove(via)

# 3: C218 off its loop
fp = ctx.fps["C218"]
p0 = fp.GetPosition()
fp.SetPosition(pcbnew.VECTOR2I(p0.x + pcbnew.FromMM(5), p0.y))
check("3 A28 VIN loop FAIL", bool(fails("A28", lambda s, t: "VIN loop" in s and "U205" in s)))
fp.SetPosition(p0)

# 4: ISN5's In2 copper pulled 1 mm away from ISP5
moved = [t for t in ctx.board.GetTracks() if t.GetNetname() == "ISN5" and t.GetClass() != "PCB_VIA"
         and ctx.board.GetLayerName(t.GetLayer()) == "In2.Cu"]
d = pcbnew.VECTOR2I(0, -pcbnew.FromMM(1.0))
for t in moved:
    t.Move(d)
check("4 A30 pair FAIL", bool(moved) and bool(fails("A30", lambda s, t: s == "ISP5/ISN5")))
for t in moved:
    t.Move(pcbnew.VECTOR2I(0, pcbnew.FromMM(1.0)))

# 5: U44 undeclared
sp = ctx.notes.get("supply_pins", {})
keep = sp.pop("U44", None)
check("5 A31 U44 FAIL", bool(fails("A31", lambda s, t: s == "U44")))
if keep is not None:
    sp["U44"] = keep

# 6: BST_LO drawn, then judged against a 1 mm limit
a, b = ctx.pads["U220.16"], ctx.pads["Q208.4"]
tr = pcbnew.PCB_TRACK(ctx.board)
tr.SetStart(a.GetPosition())
tr.SetEnd(b.GetPosition())
tr.SetWidth(pcbnew.FromMM(0.3))
tr.SetLayer(pcbnew.F_Cu)
tr.SetNet(ctx.board.FindNet("BST_LO"))
ctx.board.Add(tr)
gd = ctx.q["gate_drives"]
ctx.q["gate_drives"] = [dict(g, max_mm=1.0) if g["net"] == "BST_LO" else g for g in gd]
check("6 A29 BST_LO length FAIL", bool(fails("A29", lambda s, t: s == "BST_LO")))
ctx.q["gate_drives"] = gd
ctx.board.Remove(tr)

print("A26-A31 harness: %s" % ("PASS" if not bad else "FAIL (%s)" % ", ".join(bad)))
sys.stdout.flush()
os._exit(0 if not bad else 1)
