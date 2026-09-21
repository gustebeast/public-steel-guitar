import sys; sys.path.insert(0,'.')
import cadquery as cq
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRep import BRep_Builder
s=TopoDS_Shape(); BRepTools.Read_s(s,'.scratch_cache/output_panel.brep',BRep_Builder()); sh=cq.Shape.cast(s)
bb=sh.BoundingBox(); print(bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax)
import src.electronics as E
bb=E.output_panel().val().BoundingBox(); print(bb.xmin,bb.xmax,bb.ymin,bb.ymax,bb.zmin,bb.zmax)
print(E.op_origin(), E.JACK_WALL_X if hasattr(E,'JACK_WALL_X') else '')
