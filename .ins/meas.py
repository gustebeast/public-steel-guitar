import sys; sys.path.insert(0,'.')
import cadquery as cq, glob, os
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRep import BRep_Builder
def load(n):
    s=TopoDS_Shape(); BRepTools.Read_s(s, f'.scratch_cache/{n}.brep', BRep_Builder()); return cq.Shape.cast(s)
for f in sorted(glob.glob('.scratch_cache/*.brep')):
    n=os.path.basename(f)[:-5]
    if not any(k in n for k in ('nut_','string_nut','pi5','motor_ctrl','keyhead')): continue
    bb=load(n).BoundingBox()
    if bb.xmax<-595:
        print(f'{n:28s} x {bb.xmin:8.1f} {bb.xmax:8.1f}  y {bb.ymin:7.1f} {bb.ymax:7.1f}  z {bb.zmin:6.1f} {bb.zmax:6.1f}')
