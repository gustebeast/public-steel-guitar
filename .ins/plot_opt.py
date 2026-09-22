import sys
import src.optical_pickup as O
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
y0c, y1c = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (-130, 70)
fig, ax = plt.subplots(figsize=(9, 9 * (y1c - y0c) / 65))
for s in O._SECTIONS:
    a, b, c, d = s[:4]; ax.add_patch(Rectangle((c, a), d - c, b - a, fill=False, ec='k'))
for p in O.PARTS:
    if not (y0c - 5 < p['y'] < y1c + 5): continue
    w, h = O.CRTYD[p['pkg']]
    if p.get('rot', 0) in (90, 270): w, h = h, w
    ax.add_patch(Rectangle((p['x'] - w / 2, p['y'] - h / 2), w, h, fill=False, ec='r', lw=0.5))
    ax.text(p['x'], p['y'], p['ref'], fontsize=4, ha='center', va='center')
ax.set_xlim(-40, 25); ax.set_ylim(y0c, y1c); ax.set_aspect('equal')
plt.savefig('.ins/opt_place.png', dpi=130, bbox_inches='tight')
