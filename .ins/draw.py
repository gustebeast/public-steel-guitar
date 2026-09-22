import sys, pcbnew
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
b = pcbnew.LoadBoard('elec/out/optical.kicad_pcb')
ref = sys.argv[1]; R = float(sys.argv[2]) if len(sys.argv) > 2 else 6
c = b.FindFootprintByReference(ref).GetPosition()
cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
col = {pcbnew.F_Cu: 'red', pcbnew.In2_Cu: 'orange', pcbnew.B_Cu: 'blue', pcbnew.In1_Cu: 'gray'}
fig, ax = plt.subplots(figsize=(10, 10))
for t in b.GetTracks():
    if type(t) is pcbnew.PCB_VIA:
        p = t.GetPosition(); x, y = pcbnew.ToMM(p.x) - cx, pcbnew.ToMM(p.y) - cy
        if abs(x) < R and abs(y) < R: ax.add_patch(Circle((x, -y), 0.3, color='green', alpha=.6))
        continue
    if type(t) is not pcbnew.PCB_TRACK: continue
    s, e = t.GetStart(), t.GetEnd()
    xs = [pcbnew.ToMM(s.x) - cx, pcbnew.ToMM(e.x) - cx]; ys = [cy - pcbnew.ToMM(s.y), cy - pcbnew.ToMM(e.y)]
    if max(map(abs, xs + ys)) > R + 3: continue
    ax.plot(xs, ys, color=col.get(t.GetLayer(), 'k'), lw=pcbnew.ToMM(t.GetWidth()) * 20, alpha=.7, solid_capstyle='round')
for f in b.GetFootprints():
    for p in f.Pads():
        q = p.GetPosition(); x, y = pcbnew.ToMM(q.x) - cx, cy - pcbnew.ToMM(q.y)
        if abs(x) > R or abs(y) > R: continue
        bb = p.GetBoundingBox(); w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fill=False, ec='k', lw=.5))
        ax.text(x, y, (p.GetNetname() or '')[-6:], fontsize=4, ha='center')
ax.set_xlim(-R, R); ax.set_ylim(-R, R); ax.set_aspect('equal')
plt.savefig('.ins/draw.png', dpi=110, bbox_inches='tight')
