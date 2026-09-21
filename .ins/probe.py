import sys; sys.path.insert(0,'.')
import cadquery as cq, glob, os
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRep import BRep_Builder
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN
def load(n):
    s=TopoDS_Shape(); BRepTools.Read_s(s, f'.scratch_cache/{n}.brep', BRep_Builder()); return s
ep=load('keyhead_endplate')
hw=[load(os.path.basename(f)[:-5]) for f in glob.glob('.scratch_cache/nut_*.brep')]
def inside(s,p):
    c=BRepClass3d_SolidClassifier(s,gp_Pnt(*p),1e-4); return c.State()==TopAbs_IN
X=float(sys.argv[1])
zs=[z for z in range(-64,0,3)]
print('x=',X,' cols: z', zs)
for y in range(-54,42,2):
    row=''
    for z in zs:
        p=(X,y,z)
        row+= '#' if inside(ep,p) else ('h' if any(inside(h,p) for h in hw) else '.')
    print(f'{y:5d} {row}')
