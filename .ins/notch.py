import sys, glob, os; sys.path.insert(0,'.')
import cadquery as cq
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRep import BRep_Builder
import src.chassis as C
from src.helpers import box_at
nb=box_at(C.M9_CUT_X1-C.M9_CUT_X0, 12.0, C.M9_CUT_Z1-C.M9_CUT_Z0, x=(C.M9_CUT_X0+C.M9_CUT_X1)/2, y=C.Y_LO+C.T/2+1.0-6.0, z=(C.M9_CUT_Z0+C.M9_CUT_Z1)/2)
nbb=nb.val().BoundingBox(); print('probe box y',nbb.ymin,nbb.ymax,'x',nbb.xmin,nbb.xmax)
for f in glob.glob('.scratch_cache/*.brep'):
    n=os.path.basename(f)[:-5]
    if n.startswith('chassis'): continue
    s=TopoDS_Shape(); BRepTools.Read_s(s,f,BRep_Builder()); sh=cq.Shape.cast(s)
    bb=sh.BoundingBox()
    if bb.xmax<nbb.xmin or bb.xmin>nbb.xmax or bb.ymax<nbb.ymin or bb.ymin>nbb.ymax or bb.zmax<nbb.zmin or bb.zmin>nbb.zmax: continue
    i=sh.intersect(nb.val())
    v=i.Volume()
    if v>0.01:
        b=i.BoundingBox(); print(f'{n:24s} {v:8.1f}  y {b.ymin:.2f}..{b.ymax:.2f}  x {b.xmin:.1f}..{b.xmax:.1f} z {b.zmin:.1f}..{b.zmax:.1f}')
