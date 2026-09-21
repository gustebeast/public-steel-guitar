import sys; sys.path.insert(0,'.')
from src import keyhead_endplate as K
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN
s=K.keyhead_endplate.val().wrapped
def ins(p): c=BRepClass3d_SolidClassifier(s,gp_Pnt(*p),1e-4); return c.State()==TopAbs_IN
for y in (-34,-30,-26,-24.8,-20,-16):
    print(y, ''.join('#' if ins((x/2.0,y,-30.3)) else '.' for x in range(-1236,-1196)))
print('x from -618 to -598.5 step 0.5')
for z in (-60,-50,-40,-30,-20,-10,-4):
    print(z, ''.join('#' if ins((x/2.0,-24.8,z)) else '.' for x in range(-1236,-1196)))
