p = 'elec/optical.py'
s = open(p, encoding='utf-8').read()
a = s.index('''    "tracks": [("GND", "F.Cu", 0.2, [(_placements(CX, CY)["U%d" % (14 + k)][0] - 1.962,''')
b = s.index('''             for y in (0.75, -3.27)],''', a) + len('''             for y in (0.75, -3.27)],''')
s = s[:a] + '''    "tracks": _cell_tracks(),
    "vias": [("+3V3D",) + _cell_pt(k, -2.85, y) for k in range(5) for y in (0.75, -3.27)],''' + s[b:]

# the helpers: every laid cell feature is an offset from the converter's centre, in the frame
# of a part turned 180; a part turned 0 (the two at the +Y end) mirrors it through the centre.
s = s.replace('''def _fan_tracks():
    out = []
    near, far = OP.CELL_NEAR - 0.48, OP.CELL_FAR - 0.48
    for k in range(5):
        ux, uy = _placements(CX, CY)["U%d" % (14 + k)][:2]''', '''def _cell_pt(k, dx, dy):
    """A point given as an offset from converter k's centre in the frame of a part turned
    180 -- the frame every cell offset in this file and in src/optical_pickup.py is written
    in. The two converters at the +Y end are turned 0, so the offset mirrors through the
    centre."""
    ux, uy, rot = _placements(CX, CY)["U%d" % (14 + k)]
    sgn = 1.0 if abs(rot - 180.0) < 1e-6 else -1.0
    return (ux + sgn * dx, uy + sgn * dy)


def _cell_tracks():
    out = []
    for k in range(5):
        # ADDR1 / ADDR0 (pins 15/16) and AVSS (pin 4) straight into the EP
        for dy in (0.25, -0.25):
            out.append(("GND", "F.Cu", 0.2, [_cell_pt(k, -1.962, dy), _cell_pt(k, -0.9, dy)]))
        out.append(("GND", "F.Cu", 0.2, [_cell_pt(k, 1.962, 0.25), _cell_pt(k, 0.9, 0.25)]))
    return out + _fan_tracks() + _shdn_tracks()


def _fan_tracks():
    out = []
    near, far = OP.CELL_NEAR - 0.48, OP.CELL_FAR - 0.48
    for k in range(5):''')
s = s.replace('''            pts = [(pin_x, 1.96), (pin_x, 2.60), (cx, 2.60 + abs(d)), (cx, row)]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [(ux + x, uy + y) for x, y in pts]))''', '''            pts = [(pin_x, 1.96), (pin_x, 2.60), (cx, 2.60 + abs(d)), (cx, row)]
            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [_cell_pt(k, x, y) for x, y in pts]))''')
s = s.replace('''            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [(ux + px, uy + py), (ux + cx, uy + py), (ux + cx, uy + row)]))''', '''            out.append(("ADC%d_%s" % (k + 1, name), "F.Cu", 0.15,
                        [_cell_pt(k, px, py), _cell_pt(k, cx, py), _cell_pt(k, cx, row)]))''')
s = s.replace('''    out = []
    for k in range(5):
        ux, uy = _placements(CX, CY)["U%d" % (14 + k)][:2]
        out += [("+3V3D", "F.Cu", 0.15, [(ux - 1.96, uy + 0.75), (ux - 2.85, uy + 0.75)]),''', '''    out = []
    for k in range(5):
        P = lambda dx, dy, k=k: _cell_pt(k, dx, dy)
        out += [("+3V3D", "F.Cu", 0.15, [P(-1.96, 0.75), P(-2.85, 0.75)]),''')
s = s.replace('''                ("+3V3D", "B.Cu", 0.15, [(ux - 2.85, uy + 0.75), (ux - 2.85, uy - 3.27)]),
                ("+3V3D", "F.Cu", 0.15, [(ux - 2.85, uy - 3.27), (ux - 1.25, uy - 3.27)]),
                # and IOVDD's own pin 19 straight down onto that same pad
                ("+3V3D", "F.Cu", 0.2, [(ux - 1.25, uy - 1.96), (ux - 1.25, uy - 3.27)])]''', '''                ("+3V3D", "B.Cu", 0.15, [P(-2.85, 0.75), P(-2.85, -3.27)]),
                ("+3V3D", "F.Cu", 0.15, [P(-2.85, -3.27), P(-1.25, -3.27)]),
                # and IOVDD's own pin 19 straight down onto that same pad
                ("+3V3D", "F.Cu", 0.2, [P(-1.25, -1.96), P(-1.25, -3.27)])]''')
open(p, 'w', encoding='utf-8').write(s)
import re
left = re.findall(r'\bux \+|\buy \+|\bux -|\buy -', s[s.index('def _cell_pt'):s.index('def _outline_poly')])
print('ok; raw ux/uy offsets left in the helpers:', left)
