"""A29 with vias: a drive's own antipads are not judged, its return vias are (2026-11-21).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_quality_a29_vias.py <stem with BST_HO on In2>

  0  as laid (2 signal vias, a GND via beside each)   -> BST_HO passes, "each with a GND via"
  1  the GND vias within 1.5 mm of BST_HO's vias gone  -> FAIL, "without a GND via"
On a copy (test_quality_a16's harness). Exit 0 = both as they should.
"""
from __future__ import annotations
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_quality_a16 import _case, pcbnew          # noqa: E402
import quality                                       # noqa: E402


def rows(stem, patch=None):
    import json, shutil, tempfile
    tmp = tempfile.mkdtemp(prefix="a29-")
    try:
        dst = os.path.join(tmp, os.path.basename(stem))
        for ext in (".kicad_pcb", ".board.json"):
            shutil.copyfile(stem + ext, dst + ext)
        if patch:
            b = pcbnew.LoadBoard(dst + ".kicad_pcb"); patch(b); b.Save(dst + ".kicad_pcb")
        quality.run(dst, verbose=False)
        res = json.load(open(dst + ".quality.json", encoding="utf-8"))["results"]
        return [(r["status"], r["text"]) for r in res if r["rule"] == "A29" and r["subject"] == "BST_HO"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_KEEP = []          # a Removed item's proxy must outlive the board (finish._REMOVED says why)


def drop_returns(b):
    sig = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "BST_HO"]
    for t in [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"
              and any(math.hypot(t.GetPosition().x - c.x, t.GetPosition().y - c.y) <= pcbnew.FromMM(1.5) for c in sig)]:
        _KEEP.append(t)
        b.Remove(t)


if __name__ == "__main__":
    st = os.path.abspath(sys.argv[1]); ok = True
    r0 = rows(st); c0 = bool(r0) and r0[0][0] == "ok" and "each with a GND via" in r0[0][1]
    print("PASS" if c0 else "FAIL", " 0 as laid:", r0)
    r1 = rows(st, drop_returns); c1 = bool(r1) and r1[0][0] == "FAIL" and "without a GND via" in r1[0][1]
    print("PASS" if c1 else "FAIL", " 1 no return vias:", r1)
    sys.stdout.flush(); os._exit(0 if c0 and c1 else 1)
