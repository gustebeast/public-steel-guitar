"""unwick keeps a land's vias while they fit the budget layout placed them to (2026-11-22).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_unwick_budget.py <run dir holding
        output_board.unrouted.kicad_pcb + output_board.board.json (esc12 rPS_12a1)>

layout's power vias put one VIN_BRAIN via in R112.2 (23 % of its paste, inside the 25 %
budget); unwick then moved it 1.2 mm out, off the F.Cu lobe, and the trunk's end field lost a
barrel on 4 of 5 esc12 seeds. On a copy of the unrouted board:
1. the R112.2 via stays where layout put it;
2. a 0.3 mm via dropped into a small capacitor land (the router's case unwick exists for,
   ~100 % of the paste) is still moved out.
Exit 0 = PASS. Works on a scratch copy; the run dir is not written.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew  # noqa: E402
import unwick  # noqa: E402

MM, FM = pcbnew.ToMM, pcbnew.FromMM


def main(run):
    bad = []
    d = tempfile.mkdtemp(prefix="unwick_")
    stem = os.path.join(d, "b")
    shutil.copy(os.path.join(run, "output_board.unrouted.kicad_pcb"), stem + ".kicad_pcb")
    shutil.copy(os.path.join(run, "output_board.board.json"), stem + ".board.json")
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    r112 = [p for p in fps["R112"].Pads() if p.GetNumber() == "2"][0]
    keep = [(t.GetPosition().x, t.GetPosition().y) for t in b.GetTracks()
            if t.GetClass() == "PCB_VIA" and r112.GetBoundingBox().Contains(t.GetPosition())]
    if not keep:
        return ["no via in R112.2 on this board -- not the esc12 case"]
    # a small capacitor land with no via in it, on a net with a plane (GND)
    cap = None
    for ref, f in sorted(fps.items()):
        if not ref.startswith("C"):
            continue
        for p in f.Pads():
            sz = p.GetSize()
            if (p.GetNetname() == "GND" and max(MM(sz.x), MM(sz.y)) < 1.0
                    and p.IsOnLayer(pcbnew.F_Paste)
                    and not any(t.GetClass() == "PCB_VIA" and p.GetBoundingBox().Contains(t.GetPosition())
                                for t in b.GetTracks())):
                cap = p
                break
        if cap:
            break
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(cap.GetPosition())
    v.SetWidth(FM(0.6))
    v.SetDrill(FM(0.3))
    v.SetNet(cap.GetNet())
    b.Add(v)
    cp = (cap.GetPosition().x, cap.GetPosition().y)
    pcbnew.SaveBoard(stem + ".kicad_pcb", b)
    unwick.main(stem)
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    now = {(t.GetPosition().x, t.GetPosition().y) for t in b.GetTracks() if t.GetClass() == "PCB_VIA"}
    for q in keep:
        print("R112.2 via at (%.2f, %.2f): %s" % (MM(q[0]), MM(q[1]), "kept" if q in now else "MOVED"))
        if q not in now:
            bad.append("the R112.2 power via (inside the land budget) was moved")
    name = "%s.%s" % (cap.GetParentFootprint().GetReference(), cap.GetNumber())
    print("via dropped in %s: %s" % (name, "still there" if cp in now else "moved out"))
    if cp in now:
        bad.append("a via over the budget in %s was left in the land" % name)
    return bad


if __name__ == "__main__":
    bad = main(os.path.abspath(sys.argv[1]))
    for x in bad:
        print("  FAIL:", x)
    print("PASS" if not bad else "FAIL")
    sys.stdout.flush()
    os._exit(1 if bad else 0)
