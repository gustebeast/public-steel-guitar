"""unwick never moves a via where the track it drags would short (brain_board pv_s1, 2026-11-24).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_unwick_drag.py <run dir holding
        output_board.kicad_pcb + .board.json (brain_board pv_s1)>

pv_s1 came out of the router with no shorts and out of unwick with three: the via moved out of
Q202.3 dragged its 2.61 mm VIN_BRAIN F.Cu stub over C306.2 (GND) and a PWR_GATE track, and the
one moved out of C297.2 dragged a GND track across a BST_VIN via. unwick checked the via's own
disc at the new spot, never the copper that followed it.

On a scratch copy of the finished board each of those two vias (and the track ends on it) is put
back in its land's centre, where unwick found them; unwick runs; KiCad DRC is read.
  1  setup: both vias sit in their lands, and the board has no short on VIN_BRAIN or GND
  2  after unwick: still no short or crossing on VIN_BRAIN or GND (the dragged copper's nets)
     -- a via is moved only where its tracks stay clear, else reported (A14)
Fails without the fix (cadkit c5218ad): 2 -- shorting_items VIN_BRAIN (B.Cu trunk) / GND via and
GND track / BST_VIN via. With it: Q202.3's via moves 1.20 mm to a spot its tracks clear, C297.2's
is retired for a GND via already 1.58 mm away.
Exit 0 = PASS. The run dir is not written.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import wx
    wx.DisableAsserts()
except Exception:
    pass
import pcbnew  # noqa: E402
import unwick  # noqa: E402

M, FM = pcbnew.ToMM, pcbnew.FromMM
CLI = os.environ.get("KICAD_CLI", "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
# (the via unwick left, the land it came out of)
CASES = [((173.77, 122.61), "Q202", "3"), ((168.44, 137.96), "C297", "2")]
NETS = {"VIN_BRAIN", "GND"}


def drc(pcb):
    out = pcb + ".drc.json"
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-error", "--refill-zones",
                    "-o", out, pcb], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    bad = []
    for v in json.load(open(out, encoding="utf-8")).get("violations", []):
        if v["type"] not in ("shorting_items", "tracks_crossing"):   # netclass clearance is the flow's own noise
            continue
        d = " + ".join(i["description"] for i in v["items"])
        if any("[%s]" % n in d for n in NETS):
            bad.append("%s: %s" % (v["type"], d))
    return bad


def main(run):
    bad = []

    def want(ok, msg):
        print("%s %s" % ("PASS" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    d = tempfile.mkdtemp(prefix="unwickdrag_")
    stem = os.path.join(d, "b")
    shutil.copyfile(os.path.join(run, "output_board.kicad_pcb"), stem + ".kicad_pcb")
    shutil.copyfile(os.path.join(run, "output_board.board.json"), stem + ".board.json")
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    lands = []
    for xy, ref, num in CASES:
        v = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"
             and abs(M(t.GetPosition().x) - xy[0]) < 0.02 and abs(M(t.GetPosition().y) - xy[1]) < 0.02]
        at = v[0].GetPosition() if v else None
        pad = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]
        if not v:
            want(False, "setup: no via at %s" % (xy,))
            return bad
        v, c = v[0], pad.GetPosition()
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA" or t.GetNetCode() != v.GetNetCode():
                continue
            if t.GetStart() == at:
                t.SetStart(c)
            if t.GetEnd() == at:
                t.SetEnd(c)
        v.SetPosition(c)
        lands.append((pad, "%s.%s" % (ref, num), v.GetNetname()))
    b.Save(stem + ".kicad_pcb")
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    inland = []
    for _p, n, _net in lands:          # the pads again, from the board as reloaded
        ref, num = n.split(".")
        p = [q for q in b.FindFootprintByReference(ref).Pads() if q.GetNumber() == num][0]
        if any(t.GetClass() == "PCB_VIA" and p.GetBoundingBox().Contains(t.GetPosition())
               and t.GetNetCode() == p.GetNetCode() for t in b.GetTracks()):
            inland.append(n)
    before = drc(stem + ".kicad_pcb")
    want(len(inland) == 2 and not before, "1 setup: vias back in %s, no %s short (%s)"
         % (", ".join(inland), "/".join(sorted(NETS)), before or "none"))
    unwick.main(stem)
    after = drc(stem + ".kicad_pcb")
    want(not after, "2 after unwick: no short on the dragged copper's nets (%s)"
         % ("; ".join(after) or "none"))
    return bad


if __name__ == "__main__":
    bad = main(os.path.abspath(sys.argv[1]))
    print("PASS" if not bad else "FAIL: %d" % len(bad))
    sys.stdout.flush()
    os._exit(1 if bad else 0)
