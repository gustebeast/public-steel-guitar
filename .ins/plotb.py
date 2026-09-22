import sys, json
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
d = json.load(open('.ins/board_dump.json'))
cx, cy = d['fp'][sys.argv[1]]; R = float(sys.argv[2])
col = {'F': 'red', 'I2': 'orange', 'B': 'blue', 'I1': 'gray'}
fig, ax = plt.subplots(figsize=(11, 11))
for (s, e, w, l, n) in d['tracks']:
    xs = [s[0]-cx, e[0]-cx]; ys = [s[1]-cy, e[1]-cy]
    if min(map(abs, xs)) > R or min(map(abs, ys)) > R: continue
    ax.plot(xs, ys, color=col.get(l, 'k'), lw=w*18, alpha=.6, solid_capstyle='round')
for (x, y, n) in d['vias']:
    if abs(x-cx) < R and abs(y-cy) < R: ax.add_patch(Circle((x-cx, y-cy), .3, color='green', alpha=.5))
for (p, w, h, n, r) in d['pads']:
    x, y = p[0]-cx, p[1]-cy
    if abs(x) > R or abs(y) > R: continue
    ax.add_patch(Rectangle((x-w/2, y-h/2), w, h, fill=False, ec='k', lw=.5))
    ax.text(x, y, n.replace('ADC', 'A').replace('TIA_', '')[-7:], fontsize=5, ha='center', va='center')
ax.set_xlim(-R, R); ax.set_ylim(-R, R); ax.set_aspect('equal')
plt.savefig('.ins/draw.png', dpi=100, bbox_inches='tight')
