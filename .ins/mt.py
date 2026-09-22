import sys; sys.path.insert(0,'.')
import src.electronics as E
print({r: tuple(round(v,2) for v in E.mctrl_pt(r)) for r in ('J1','J2','J3','J4','J5')})
p=E.motor_ctrl_pcb(True); bb=p.val().BoundingBox(); print('pcb', bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmax, len(p.val().Solids()))
