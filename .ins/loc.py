import sys; sys.path.insert(0,'.')
import cadquery as cq
from src import build
comps = dict(build.body_work_components())
a = comps['chassis_0']; b = comps['wire_pwr_hot_12']
i = a.intersect(b)
bb = i.val().BoundingBox(); print(bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax, i.val().Volume())
