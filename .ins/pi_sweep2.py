import sys
sys.path.insert(0, '.')
from src import electronics as EL
from src import keyhead_endplate as KH

parts = KH.assembly()
solids = [b for _n, b in parts] if isinstance(parts[0], tuple) else parts
ep = solids[0]
for q in solids[1:]:
    ep = ep.union(q)

body = EL.pi5().union(EL.pi_cap())


def overlap(d):
    m = body.translate(d)
    r = m.intersect(ep)
    return r.val().Volume() if r.solids().size() else 0.0


rest = overlap((0, 0, 0))
print('AT REST the Pi + cap overlap the endplate by %.1f mm3 (the cradle gripping it)' % rest)
for axis, vec in (("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Z", (0, 0, 1)),
                  ("-Z", (0, 0, -1)), ("+Y", (0, 1, 0)), ("-Y", (0, -1, 0))):
    row = []
    for mm in (2, 6, 12, 20, 30, 45):
        v = overlap(tuple(c * mm for c in vec))
        row.append('%d:%.0f' % (mm, v))
        if v < 1.0:
            row.append('FREE')
            break
    print('  %s  %s' % (axis, '  '.join(row)))
