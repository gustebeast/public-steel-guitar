import sys; sys.path.insert(0,'.')
import cadquery as cq
import src.electronics as E
from src import keyhead_endplate as K
print('HS_X1',K.HS_X1, 'HS_Y', K.HS_Y0, K.HS_Y1, 'HS_Z', K.HS_Z0, K.HS_Z1)
cr=E.keyhead_cradles(pi_cut=K._slot_shadow())
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN
s=cr.val().wrapped
def ins(p): c=BRepClass3d_SolidClassifier(s,gp_Pnt(*p),1e-4); return c.State()==TopAbs_IN
print('cradle at slab?', [ins((-608.7,-24.8,z)) for z in (-50,-30,-10)])
sh=K._slot_shadow(); bb=sh.val().BoundingBox(); print('shadow bb', bb.xmin,bb.xmax,bb.ymin,bb.ymax)
s2=sh.val().wrapped
def ins2(p): c=BRepClass3d_SolidClassifier(s2,gp_Pnt(*p),1e-4); return c.State()==TopAbs_IN
print('shadow covers slab pt?', [ins2((-608.7,y,-30)) for y in (-34,-30,-24.8,-20,-16, -3.2, 9.7)])
