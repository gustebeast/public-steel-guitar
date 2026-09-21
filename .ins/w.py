import sys; sys.path.insert(0,'.')
import src.helpers as H
cap={}
orig=H.oct_cable
def spy(pts,d):
    spy.last=(pts,d); return orig(pts,d)
import src.wiring as W
W.oct_cable=spy
import src.dimensions as D, src.motor_bank as MB
names={}
_w=W._wire
def w2(pts,d=W.WIRE_D):
    r=_w(pts,d); names[id(r)]=(pts,d); return r
W._wire=w2
comps=W.wire_components() if hasattr(W,'wire_components') else None
