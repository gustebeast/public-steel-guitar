import sys; sys.path.insert(0,'.')
import src.electronics as E
from src import keyhead_endplate as K
from src.helpers import box_at
cr=E.keyhead_cradles(pi_cut=K._slot_shadow())
# world: board underside plane for the Pi at world x = -601.6; take slab x -602.0..-601.7
x0,x1,y0,y1=E.PI_FP
sl=cr.intersect(box_at(0.3, 200, 100, x=-601.85, y=(y0+y1)/2, z=-34))
for s in sl.val().Solids():
    bb=s.BoundingBox(); print(f'y {bb.ymin:6.1f}..{bb.ymax:6.1f}  z {bb.zmin:6.1f}..{bb.zmax:6.1f}  area {s.Volume()/0.3:6.1f}')
