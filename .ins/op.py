import sys; sys.path.insert(0,'.')
import src.electronics as E, src.board_geom as BG
s=E.output_panel_pcb(); bb=s.val().BoundingBox(); print('pcb', bb.xmin,bb.xmax,bb.ymin,bb.ymax, len(s.val().Solids()))
p=BG._plate('output_panel'); bb=p.val().BoundingBox(); print('plate',bb.xmin,bb.xmax,bb.ymin,bb.ymax, p.val().Volume())
import inspect; print(inspect.getsource(BG.solid)[:1500])
