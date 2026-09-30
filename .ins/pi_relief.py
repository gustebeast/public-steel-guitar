import sys
sys.path.insert(0, '.')
import cadquery as cq                                  # noqa: E402
from src import electronics as EL                      # noqa: E402
from src import keyhead_endplate as KH                 # noqa: E402

parts = KH.assembly()
solids = [b for _n, b in parts] if isinstance(parts[0], tuple) else parts
ep = solids[0]
for q in solids[1:]:
    ep = ep.union(q)

pi = EL.pi4()
swept = None
for mm in range(0, 70, 2):                 # the whole +Z install stroke
    m = pi.translate((0, 0, mm))
    swept = m if swept is None else swept.union(m)
r = swept.intersect(ep)
print('material the Pi sweeps through on a +Z -> -Z install: %.0f mm3' % r.val().Volume())
for s in r.val().Solids():
    b = s.BoundingBox()
    print('   %7.1f mm3  x %8.2f..%8.2f  y %7.2f..%7.2f  z %7.2f..%7.2f'
          % (s.Volume(), b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax))
