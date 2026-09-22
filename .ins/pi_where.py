import sys
sys.path.insert(0, '.')
from src import electronics as EL
from src import keyhead_endplate as KH

parts = KH.assembly()
solids = [b for _n, b in parts] if isinstance(parts[0], tuple) else parts
ep = solids[0]
for q in solids[1:]:
    ep = ep.union(q)

for name, body in (("pi5 alone", EL.pi5()), ("pi_cap alone", EL.pi_cap())):
    for mm in (0, 30):
        r = body.translate((0, 0, mm)).intersect(ep)
        if not r.solids().size():
            print('%-13s +Z %2d mm : clear' % (name, mm))
            continue
        bb = r.val().BoundingBox()
        print('%-13s +Z %2d mm : %7.1f mm3  at x %8.2f..%8.2f y %7.2f..%7.2f z %7.2f..%7.2f'
              % (name, mm, r.val().Volume(), bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
