"""Filled and capped vias (quality.fab via_in_pad) are one fact read everywhere (lead 2026-11-24).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_filled_vias.py <run dir holding
        output_board.kicad_pcb + .board.json (brain_board pv_s1)>

The brain board is ordered with epoxy-filled, capped vias (JLC POFV) so the router may put vias
in solder lands. unwick, written for OPEN barrels, still moved ~30 of them on pv_s1 (three into
shorts) and quality A14 still failed the rest. On a copy of pv_s1 with Q202.3's and C297.2's
vias put back in their lands (test_unwick_drag's setup):
  1  unwick, via_in_pad set     -> neither via moves; it says the vias are filled
  2  unwick, via_in_pad unset   -> they move or retire as before (the open-via board keeps it)
  3  A14, via_in_pad set        -> PASS; unset -> FAIL (open barrels over half their paste)
  4  fab_package.via_fill_unordered: via_in_pad with a POFV order option -> fine; without one
     -> refused with a reason; no via_in_pad -> fine
Fails without the fix (cadkit 04397c2): 1, 3 (A14 FAIL with the note set), 4 (no such check).
Exit 0 = PASS. The run dir is not written.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import wx
    wx.DisableAsserts()
except Exception:
    pass
import pcbnew  # noqa: E402
import quality  # noqa: E402

M = pcbnew.ToMM
CASES = [((173.77, 122.61), "Q202", "3"), ((168.44, 137.96), "C297", "2")]
POFV = "Epoxy Filled & Capped (POFV) -- REQUIRED: vias in pads (free on 6+ layers at JLC)"


def setup(run, via_in_pad):
    """A copy of the run's board with each CASES via (and its track ends) back in its land."""
    d = tempfile.mkdtemp(prefix="filledvia_")
    stem = os.path.join(d, "b")
    shutil.copyfile(os.path.join(run, "output_board.kicad_pcb"), stem + ".kicad_pcb")
    notes = json.load(open(os.path.join(run, "output_board.board.json"), encoding="utf-8"))
    q = notes.setdefault("quality", {})
    q["fab"] = dict(q.get("fab") or {}, via_in_pad=via_in_pad)
    json.dump(notes, open(stem + ".board.json", "w", encoding="utf-8"))
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    for xy, ref, num in CASES:
        v = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"
             and abs(M(t.GetPosition().x) - xy[0]) < 0.02 and abs(M(t.GetPosition().y) - xy[1]) < 0.02][0]
        at = v.GetPosition()
        c = [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0].GetPosition()
        for t in b.GetTracks():
            if t.GetClass() != "PCB_VIA" and t.GetNetCode() == v.GetNetCode():
                if t.GetStart() == at:
                    t.SetStart(c)
                if t.GetEnd() == at:
                    t.SetEnd(c)
        v.SetPosition(c)
    b.Save(stem + ".kicad_pcb")
    return stem, notes


def inland(stem):
    b = pcbnew.LoadBoard(stem + ".kicad_pcb")
    out = []
    for _xy, ref, num in CASES:
        p = [q for q in b.FindFootprintByReference(ref).Pads() if q.GetNumber() == num][0]
        if any(t.GetClass() == "PCB_VIA" and t.GetPosition() == p.GetPosition() for t in b.GetTracks()):
            out.append("%s.%s" % (ref, num))
    return b, out


def a14(b, notes):
    ctx = types.SimpleNamespace(board=b, q=notes.get("quality") or {},
                                fps={fp.GetReference(): fp for fp in b.GetFootprints()})
    return quality.via_in_land(ctx)[0]


def main(run):
    bad = []

    def want(ok, msg):
        print("%s %s" % ("PASS" if ok else "FAIL", msg))
        if not ok:
            bad.append(msg)

    for filled in (True, False):
        stem, notes = setup(run, filled)
        # its own process: unwick's saves leave this one's SWIG registry unusable (the next
        # LoadBoard came back a bare SwigPyObject -- layout's drop_redundant_pad_vias notes)
        log = subprocess.run([sys.executable, os.path.join(HERE, "unwick.py"), stem],
                             capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        b, left = inland(stem)
        if filled:
            want(len(left) == 2 and "filled and capped" in log and "moved the via out" not in log,
                 "1 filled: both vias stay in their lands (%s), nothing moved" % ", ".join(left))
        else:
            want(not left and "moved the via out of Q202.3" in log,
                 "2 open vias: unwick still clears the lands (left: %s)" % (", ".join(left) or "none"))
        stem2, notes2 = setup(run, filled)          # A14 judges the board unwick never touched
        b2, _ = inland(stem2)
        r = a14(b2, notes2)
        want(r[1] is (True if filled else False), "3 A14 with via_in_pad %s: %s -- %s"
             % (filled, {True: "PASS", False: "FAIL", None: "n/a"}[r[1]], r[2][:90]))

    sys.path.insert(0, os.path.dirname(HERE))      # fab_package lives in the pcbflow package
    from pcbflow import fab_package as fp
    want(fp.via_fill_unordered({"quality": {"fab": {"via_in_pad": True}},
                                "order_options": {"via_covering": POFV}}) is None,
         "4 via_in_pad with a POFV order option packages")
    why = fp.via_fill_unordered({"quality": {"fab": {"via_in_pad": True}},
                                 "order_options": {"finish": "ENIG"}})
    want(bool(why) and "POFV" in why, "4 via_in_pad without one is refused: %s" % (why or "")[:70])
    want(fp.via_fill_unordered({"order_options": {}}) is None, "4 no via_in_pad: nothing asked")
    return bad


if __name__ == "__main__":
    bad = main(os.path.abspath(sys.argv[1]))
    print("PASS" if not bad else "FAIL: %d" % len(bad))
    sys.stdout.flush()
    os._exit(1 if bad else 0)
