"""link_close_gaps keeps off other nets' frozen bands (brain_board rPS_11a1, 2026-11-21).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_link_frozen.py <pcbflow dir> <stem>

On a finished brain board: the GND tracks the post-route island repair laid through
+24V_LED's frozen F.Cu band are removed, the repair runs again, and no foreign track may come
back inside the band (outline grown 0.6 mm). Before the wall it re-laid 5; after, 0 -- and VSTBY's F.Cu join
(a B.Cu band nearby) is still made: the wall is on the path's own layer.
Works on the loaded board in memory, never saves. Exit 0 = PASS.
"""
import sys, os, json
try:
    import wx; wx.DisableAsserts()
except Exception: pass
ck, stem = sys.argv[1], sys.argv[2]
sys.path.insert(0, ck)
import pcbnew, layout
b = pcbnew.LoadBoard(stem + ".kicad_pcb")
notes = json.load(open(stem + ".board.json", encoding="utf-8"))
band = [z for z in b.Zones() if z.GetZoneName() == "frozen" and z.GetNetname() == "+24V_LED"]
print("bands +24V_LED:", len(band))
ol = band[0].Outline()
def inside(t):
    for p in (t.GetStart(), t.GetEnd()):
        if ol.Collide(p, pcbnew.FromMM(0.6)): return True
    return False
# remove the GND repair tracks inside/near the band (the island repair's, w 0.25/0.2 non-router)
bad = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA" and t.GetNetname() == "GND" and t.GetLayer() == pcbnew.F_Cu and inside(t)]
print("removing", len(bad), "GND F.Cu track(s) at the band")
for t in bad: b.Remove(t)
_k = lambda t: (t.GetClass(), t.GetNetname(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)
before = {_k(t) for t in b.GetTracks()}
n = layout.link_close_gaps(b, layout._outline_pts(notes), same_part_only=False,
                           max_mm=notes.get("repair_mm", 5.0), inner=layout._local_inner(notes))
again = [t for t in b.GetTracks() if t.GetClass() != "PCB_VIA" and t.GetNetname() != "+24V_LED"
         and band[0].IsOnLayer(t.GetLayer()) and inside(t)
         and not any(t.GetStart() == q.GetStart() and t.GetEnd() == q.GetEnd() for q in [])]
new_in = [t for t in again if t.GetNetname() == "GND"]
print("link_close_gaps joined", n, "; GND F.Cu tracks at the band now:", len(new_in))
for t in new_in[:6]:
    print("  ", pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), "->", pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y), pcbnew.ToMM(t.GetWidth()))
# ...and the wall is on the path's own layer: VSTBY's F.Cu join to U5 (near a B.Cu band only) is still made
vst = [t for t in b.GetTracks() if _k(t) not in before and t.GetClass() != "PCB_VIA" and t.GetNetname() == "VSTBY"
       and abs(pcbnew.ToMM(t.GetStart().x) - 65.33) < 0.05 and abs(pcbnew.ToMM(t.GetStart().y) - 117.30) < 0.05]
good = not new_in and bool(vst)
print("PASS" if good else "FAIL: %d GND track(s) back in the band, VSTBY join %s" % (len(new_in), "made" if vst else "MISSING"))
sys.stdout.flush(); os._exit(0 if good else 1)
