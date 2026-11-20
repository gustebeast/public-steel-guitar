"""THE CM5 ON THE OUTPUT (BRAIN) BOARD -- its mechanical reference, and the check that the
routed board still matches it.

    py -3.12 elec/cm5_mech.py        # checks elec/geom/brain_board.geom.json

SOURCES. Raspberry Pi's own carrier, CM5IO (RP-008099-DD-1, CM5IO.kicad_pcb, footprint
`Raspberry-Pi-5-Compute-Module`), and the CM5 datasheet RP-008180-DS-7 section 4.1.1 / Fig. 4.
In the CM5IO footprint's frame (KiCad, y DOWN, origin on the pin-1-side hole):

    pins   1-100 (our J201): odd column x -2.04, even +1.04; pin 1 y -31.3 .. pin 99 y -11.7
    pins 101-200 (our J202): odd column x 31.96, even 35.04; same y range
    NPTH 2.7 (M2.5) holes at (0, 0), (33, 0), (0, -48), (33, -48)
    module 40 x 55, PCB 1.24 thick, holes 3.5 in from its edges; 1.5 mm DF40 stack

⚠ WHY THIS FILE EXISTS (2026-11-14). The merged board had both DF40s placed at 90 degrees from
numbers SCALED OFF FIG. 4 (34.4 apart): each connector's pin 1 sat at the wrong end with the
odd column on the wrong side -- every CM5 pin landed on a different net, and the module could
not have been fitted. Nothing checked it, because the placement was the only copy of the
geometry. The reference is now read off Raspberry Pi's own carrier, the board's placement
and its holes both come from here, and check() reads the ROUTED board back (geom.json pads by
number) so a later re-placement cannot regress it.

OUR FRAME: the brain board's board-centre frame (geom.json, y UP), component side up. The
CM5IO frame maps in with a y flip only (same component side -- a y flip is KiCad's y-down to
our y-up, not a mirror): ours = (HOLE0.x + x, HOLE0.y - y).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# the module's pin-1-side hole in the brain board's frame: the module sits 40 (x) by 55 (y)
# near the top-right corner, centre (50.0, 21.5)
# ⚠ THE SEAT IS SET BY THE UI BOARD, NOT CHOSEN (lead / branner, 2026-11-19): at (38.5, -2.5) the
# module's +X edge reached instrument x -149.985 and overlapped the UI board (ui_pcb, edge -146.96)
# by 3.0, the UI encoder (body to -147.96) by 2.0, and its top-right screw head met the UI clamp
# bar -- the gate skipped ui_pcb, so nobody saw it. 5 mm toward board -X: ~2.0 to the UI board,
# ~3.0 to the encoder (both seat in printed parts, so they need print tolerance, not 0.98). Do not
# move it back toward board +X.
HOLE0 = (33.5, -2.5)
HOLE_D = 2.7                    # CM5IO: MountingHole_2.7mm_M2.5_DIN965, NPTH
STANDOFF_H = 1.5                # the DF40 stack height: the module's underside above our top
STANDOFF_OD = 5.0               # M2.5 x 1.5 spacer (round, 5 OD); keep copper out from under it
HEAD_D = 4.5                    # M2.5 DIN965 head under the board
MODULE = (40.0, 55.0)
MODULE_PCB_T = 1.24
TOL = 0.02

_REF_HOLES = ((0.0, 0.0), (33.0, 0.0), (0.0, -48.0), (33.0, -48.0))
# (ref, CM5 pin offset, odd-column x, even-column x) in the CM5IO frame
_COLS = (("J201", 0, -2.04, 1.04), ("J202", 100, 31.96, 35.04))
_Y1, _Y99 = -31.3, -11.7


def _ours(x, y):
    return (round(HOLE0[0] + x, 4), round(HOLE0[1] - y, 4))


def holes():
    """The four module holes in our frame."""
    return [_ours(x, y) for x, y in _REF_HOLES]


def outline():
    """The module's outline in our frame (x0, y0, x1, y1): the holes are 3.5 in from it."""
    xs = [h[0] for h in holes()]
    ys = [h[1] for h in holes()]
    return (min(xs) - 3.5, min(ys) - 3.5, max(xs) + 3.5, max(ys) + 3.5)


def pad_ref(ref, pad):
    """Where pad `pad` (1..100) of J201 / J202 must be, in our frame."""
    _, _, xo, xe = next(c for c in _COLS if c[0] == ref)
    k = (pad - 1) // 2                                   # 0..49 along the row
    y = _Y1 + k * (_Y99 - _Y1) / 49.0
    return _ours(xo if pad % 2 else xe, y)


def placement(ref):
    """(x, y, rot) for the intent: the connector's centre and KiCad rotation that put its
    pads on pad_ref() -- the DF40 footprint at 270 has pad 1 at (-1.54, +9.8) of its centre."""
    p1 = pad_ref(ref, 1)
    return (round(p1[0] + 1.54, 4), round(p1[1] - 9.8, 4), 270.0)


def cutouts():
    """BOARD_NOTES cutouts: the four NPTH holes, copper kept out from under the spacer (front)
    and the screw head (back)."""
    return [{"xy": list(h), "d": HOLE_D, "keepout_d": STANDOFF_OD, "head_d": STANDOFF_OD,
             "head_side": "both", "what": "CM5 M2.5 mount (CM5IO; %.1f mm spacer)" % STANDOFF_H}
            for h in holes()]


def check(geom):
    """[problems] for a geom.json dict: every DF40 pad on its CM5IO position, the four holes
    cut, and no other part's body under the module (the 1.5 mm stack leaves no room)."""
    bad = []
    fps = {f["ref"]: f for f in geom["footprints"]}
    for ref, off, _, _ in _COLS:
        f = fps.get(ref)
        if f is None:
            bad.append("%s missing" % ref)
            continue
        if f.get("side", "F") != "F":
            bad.append("%s on the back" % ref)
        for n in range(1, 101):
            got = f["pads"].get(str(n))
            want = pad_ref(ref, n)
            if got is None or math.hypot(got[0] - want[0], got[1] - want[1]) > TOL:
                bad.append("%s pad %d (CM5 pin %d) at %s, CM5IO puts it at %s"
                           % (ref, n, n + off, got, want))
                if len(bad) > 6:
                    return bad
    # geom.json holes are polygons: compare each one's centre and mean diameter
    have = []
    for poly in geom.get("holes", ()):
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        have.append((cx, cy, 2.0 * sum(math.hypot(p[0] - cx, p[1] - cy) for p in poly) / len(poly)))
    for hx, hy in holes():
        if not any(math.hypot(cx - hx, cy - hy) < 0.05 and abs(d - HOLE_D) < 0.1
                   for cx, cy, d in have):
            bad.append("no %.1f hole at (%.2f, %.2f)" % (HOLE_D, hx, hy))
    x0, y0, x1, y1 = outline()
    for r, f in fps.items():
        if r in ("J201", "J202") or not f.get("fab") or f.get("side", "F") != "F":
            continue
        fx0, fx1, fy0, fy1 = f["fab"]
        if fx0 < x1 and fx1 > x0 and fy0 < y1 and fy1 > y0:
            bad.append("%s's body is under the CM5 (%.1f..%.1f, %.1f..%.1f)" % (r, fx0, fx1, fy0, fy1))
    return bad


def main(argv):
    p = argv[1] if len(argv) > 1 else os.path.join(HERE, "geom", "brain_board.geom.json")
    bad = check(json.load(open(p)))
    for b in bad:
        print("  CM5: " + b)
    print("cm5_mech: %s (%s)" % ("FAIL, %d" % len(bad) if bad else "ok", p))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
