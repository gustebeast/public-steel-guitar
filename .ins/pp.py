import pcbnew, math
def pads(fpid, cx, cy, rot, nums):
    lib, name = fpid.split(':')
    fp = pcbnew.FootprintLoad(r'C:\Program Files\KiCad\10.0\share\kicad\footprints\%s.pretty' % lib, name)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100+cx), pcbnew.FromMM(100-cy)))
    fp.SetOrientationDegrees(rot)
    out = {}
    for p in fp.Pads():
        if p.GetNumber() in nums:
            q = p.GetPosition(); out[p.GetNumber()] = (round(q.x/1e6-100,2), round(100-q.y/1e6,2))
    return out
print('U4 @90', pads('Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm', -14.5, -8, 90, {'9','10','11','12','14','15'}))
print('U4 @0 ', pads('Package_DFN_QFN:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm', -14.5, -8, 0, {'9','10','11','12','14','15'}))
print('U1', pads('Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP5.2x5.2mm', -6, -8, 0, {'61','62','1','17','18','34','35','51','52','68'}))
