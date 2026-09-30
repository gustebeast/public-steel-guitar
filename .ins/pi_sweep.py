"""Can the Pi (and its cap) actually be put in? Sweep the install stroke, not just the rest
position -- the overlap gate only ever sees parts where they finally sit."""
import sys
sys.path.insert(0, '.')
import cadquery as cq                                   # noqa: E402
from src import electronics as EL                       # noqa: E402
from src import keyhead_endplate as KH                  # noqa: E402

pi = EL.pi4()
cap = EL.pi_cap()
try:
    parts = KH.assembly()
    if isinstance(parts, list):
        solids = [q for q in (b for _n, b in parts)] if isinstance(parts[0], tuple) else parts
        ep = solids[0]
        for q in solids[1:]:
            ep = ep.union(q)
    else:
        ep = parts
except Exception as e:                                   # noqa: BLE001
    names = [a for a in dir(KH) if not a.startswith('_')]
    print('cannot build endplate (%s); exports: %s' % (e, names[:25]))
    raise SystemExit(1)

for name, body in (("pi4", pi), ("pi_cap", cap)):
    bb = body.val().BoundingBox()
    print('%-7s rests at x %8.2f..%8.2f' % (name, bb.xmin, bb.xmax))

STEP, REACH = 2.0, 60.0
for axis, vec in (("+X", (1, 0, 0)), ("-X", (-1, 0, 0)),
                  ("+Z", (0, 0, 1)), ("-Z", (0, 0, -1)),
                  ("+Y", (0, 1, 0)), ("-Y", (0, -1, 0))):
    worst = None
    for k in range(1, int(REACH / STEP) + 1):
        d = tuple(c * STEP * k for c in vec)
        moved = pi.translate(d).union(cap.translate(d))
        v = moved.intersect(ep).val().Volume() if moved.intersect(ep).solids().size() else 0.0
        if v > 0.1:
            worst = (STEP * k, v)
            break
    print('  install along %s : %s' % (
        axis, 'CLEAR for %.0f mm' % REACH if worst is None
        else 'blocked at %.0f mm (%.0f mm3 into the endplate)' % worst))
