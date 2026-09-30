import sys
sys.path.insert(0, '.')
from src import electronics as EL
from src import keyhead_endplate as KH

parts = KH.assembly()
solids = [b for _n, b in parts] if isinstance(parts[0], tuple) else parts
ep = solids[0]
for q in solids[1:]:
    ep = ep.union(q)

pi = EL.pi4()
bb = pi.val().BoundingBox()
print('Pi occupies  x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  (so %.0f along Y, %.0f along Z)'
      % (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax,
         bb.ymax - bb.ymin, bb.zmax - bb.zmin))


def ov(d):
    r = pi.translate(d).intersect(ep)
    return r.val().Volume() if r.solids().size() else 0.0


for axis, vec, need in (("+Z", (0, 0, 1), 56), ("-Z", (0, 0, -1), 56),
                        ("+Y", (0, 1, 0), 85), ("-Y", (0, -1, 0), 85)):
    firstblock = None
    for mm in range(2, need + 20, 4):
        v = ov(tuple(c * mm for c in vec))
        if v > 1.0 and firstblock is None:
            firstblock = mm
    tot = ov(tuple(c * (need + 10) for c in vec))
    print('  slide %s (needs %d mm to clear): %s ; at full travel overlap %.0f mm3'
          % (axis, need,
             'CLEAR all the way' if firstblock is None else 'first touch at %d mm' % firstblock,
             tot))
