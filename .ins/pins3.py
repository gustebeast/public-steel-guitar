def edit(path, pairs):
    s=open(path,encoding='utf-8').read()
    for o,n in pairs:
        assert s.count(o)==1,(path,o[:70]); s=s.replace(o,n)
    open(path,'w',encoding='utf-8').write(s)
edit('src/wiring.py',[
('''    def _tail(cond, do):
        _p = _pin(west[0], cond, False)
        zt = _w0[2] + _TAIL_DZ + do
        return [_p, (_p[0], _p[1], zt), (BAY_X + do, _p[1], zt), (BAY_X + do, _mc24[1], zt),
                (BAY_X + do, _mc24[1], _mc24[2] + do), (_mc24[0], _mc24[1], _mc24[2] + do)]''',
'''    def _tail(cond, do):
        # hot (pin 2, do -1) runs HIGH and INBOARD, gnd (pin 1, do +1) low and outboard: each
        # then passes over or beside the other's turn instead of through it, at both ends
        _p = _pin(west[0], cond, False)
        zt = _w0[2] + _TAIL_DZ - do
        xt = BAY_X - do
        return [_p, (_p[0], _p[1], zt), (xt, _p[1], zt), (xt, _mc24[1], zt),
                (xt, _mc24[1], _mc24[2] + do), (_mc24[0], _mc24[1], _mc24[2] + do)]'''),
('''    out.append(("wire_link", _wire([
        _lt, (BAY_X, _lt[1], _lt[2]), (BAY_X, _lt[1], BAYFLY), (BAY_X, _lp[1], BAYFLY),''',
'''    # it steps 2.0 -Y off the mouth before it rises: straight up at the mouth's own y it
    # stood 1.1 from bus B's drop to the floor corridor
    _ly = _lt[1] - 2.0
    out.append(("wire_link", _wire([
        _lt, (_lt[0], _ly, _lt[2]), (BAY_X, _ly, _lt[2]), (BAY_X, _ly, BAYFLY),
        (BAY_X, _lp[1], BAYFLY),'''),
])
print('ok')
