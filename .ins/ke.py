p='src/keyhead_endplate.py'; s=open(p,encoding='utf-8').read()
old='''    from .electronics import keyhead_cradles
    w = w.union(keyhead_cradles())'''
new='''    from .electronics import keyhead_cradles
    w = w.union(keyhead_cradles(pi_cut=_slot_shadow()))'''
assert s.count(old)==1; s=s.replace(old,new)
old='''def _build():'''
new='''def _slot_shadow():
    """The insert slots, plus everything straight above them in +X (this part's build
    direction) -- what the Pi's cradle columns must not stand in or hang over.

    The Pi's columns rise from this part's wall to the board, and most of them land on the
    height-adjust prism, whose +X face (HS_X1) is cut through by the insert slots. A column
    in a slot fills it; a column continuing ABOVE a slot is a ceiling with nothing under it.
    So: the slot negatives themselves, and each slot's opening in the HS_X1 face swept
    +X past the board. What survives stands on a fin, the band, or the wall."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    neg = _height_negatives()
    skin = neg.intersect(box_at(2.0, 400.0, 400.0, x=HS_X1 - 1.0 + 0.01, y=0.0, z=0.0))
    out = neg
    for f in skin.faces().vals():
        n = f.normalAt()
        if n.x > 0.99 and abs(f.Center().x - (HS_X1 + 0.01)) < 0.02:
            out = out.union(cq.Workplane("XY").add(cq.Shape.cast(
                BRepPrimAPI_MakePrism(f.wrapped, gp_Vec(40.0, 0.0, 0.0)).Shape())))
    return out


def _build():'''
assert s.count(old)==1; s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
