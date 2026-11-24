"""KEYHOLE v3 STUDY (user, 2026-11-22: "the cable idea is out ... make the keyhole the best it can be").

Goals:
  * take the heaviest gauge we support (.080), with room for it to swell near the ball end;
  * seat the ball only HOLE UP (cylinder axis along Z): its Ø4 then spans the vertical slit,
    which is its strongest way round;
  * two states only, SEATED or OUT: no ledge between the entry hole and the seat a ball can stop
    on and feel seated.

THE BALL. A ball end is a Ø4 x 3 brass cylinder; the string loops through its hole and leaves from
its curved side, so the ball's axis always lies across the string (in YZ) and its one free motion
here is the ROLL about the string, phi. Hole up = phi 0 (Y 4, Z 3 as the plate sees it); hole
sideways = phi 90 (Y 3, Z 4).

THE PLATE: one CNC-machined 304 part, 7 thick, replacing the 3 + 4 laser sheets. Same outline, ears,
M3 holes and frame (+X face at x = 0, axis y = z = 0). The ball side is the -X face. The cuts:
  SLIT     through, SLIT_W wide: the string's way, from below the axis up into the entry hole.
           3.2 passes a .080's ~2.45 neck with 0.75 to spare, and a hole-SIDEWAYS ball (Y 3.0)
           falls straight through it: a wrongly rolled ball can't hang in the seat; it comes out.
  CRADLE   on the -X face round the axis: a half-cylinder groove, axis Z, radius CR (the ball's 2.0
           + 0.1), CRADLE_Z long at its floor. Only a hole-up ball lies in it, along the groove.
           It bears on the groove's two flanks outside the slit, about 8 mm^2 of brass.
  RIDGE    the cradle's top end rises at RAMP from X to a KNIFE EDGE on the -X face. The
           entry side falls away from the same edge at the same angle into the entry hole. A ball
           pulled +X anywhere between slides off one flank or the other (cot 30 deg = 1.7 >> brass
           on steel's mu). Below the ridge it goes into the seat, and the string's line (the bend
           bearing's exit is on the axis) pulls it down there too. Above the ridge it goes into the
           entry hole and out.
  ENTRY    through, Ø ENTRY_D: passes the ball in any roll (its 4 x 3 corner-to-corner is 5.0).

    PYTHONPATH=. py -3.12 src/test/keyhole_v3_study.py
"""
from __future__ import annotations

import math
import os

import cadquery as cq

from src import dimensions as D
from src import direct_bench as B

T = B.YK_ROOF                       # 7: the plate, x -7 .. 0
BALL_D, BALL_L = D.STRING_NUT_D, D.STRING_NUT_L     # Ø4 x 3
NECK_MAX = 2.7                      # a .080's neck: ~2.45 measured-scaled, plus swell
SLIT_W = 3.2                        # > BALL_L + 0.2 (hole-sideways falls through) and > NECK_MAX
SLIT_Z0 = -3.2                      # its bottom: a sideways ball's corners (y +-1.5, z -2) clear its round end
CR = BALL_D / 2 + 0.1               # 2.1 cradle radius
CRADLE_Z = BALL_L + 0.2             # 3.2 at the cradle's floor, centred on the axis
RAMP = 20.0                         # flank angle from the X axis (steep: cot = 2.7)
CD = BALL_D + 0.1                   # 4.1: the cradle is a U-channel, the seated ball flush with the -X face
                                    # (the screw tip lands on that face at coil-close)
ENTRY_D = 5.4
ENTRY_FLANK_U = 1.0                 # the entry flank's depth from the -X face
TAN = math.tan(math.radians(RAMP))
Z_RIDGE = CRADLE_Z / 2 + CD * TAN   # the knife on the -X face
Z_ENTRY = Z_RIDGE + ENTRY_FLANK_U * TAN + ENTRY_D / 2
X_FACE = -T                         # the ball side


def _blank() -> cq.Workplane:
    """The plate's outline and M3 holes, as the two laser sheets had them, in one 7 mm body."""
    w = B.cyl_x(B.YK_D, T, -T, y=0, z=0)
    for a in B.STACK_ANG:                       # no ears since 2026-11-23 (the stack without ears)
        dy, dz = B.at_ang(a, B.STACK_R)
        w = w.cut(B.cyl_x(3.4, T + 2, -T - 1, y=dy, z=dz))
    return w


def _xz_prism(pts, y0, y1) -> cq.Workplane:
    """A prism from an (x, z) polygon, y0..y1."""
    return (cq.Workplane("XZ").workplane(offset=-y0).polyline(pts).close()
            .extrude(-(y1 - y0)))


def cuts() -> dict:
    u = lambda d: X_FACE + d            # depth into the plate from the ball side
    # SLIT: through, round bottom
    r = SLIT_W / 2
    slit = (B.cyl_x(SLIT_W, T + 2, -T - 1, y=0, z=SLIT_Z0 + r)
            .union(B.box_at(T + 2, SLIT_W, Z_ENTRY - (SLIT_Z0 + r), x=-T / 2, y=0,
                            z=(Z_ENTRY + SLIT_Z0 + r) / 2)))
    # CRADLE: the half-cylinder about Z through (X_FACE, 0), cut off above by the top flank
    zc0 = -CRADLE_Z / 2
    h = Z_RIDGE - zc0 + 1
    cyl = (cq.Workplane("XY").add(cq.Solid.makeCylinder(CR, h, cq.Vector(u(CD - CR), 0, zc0), cq.Vector(0, 0, 1)))
           .union(B.box_at(CD - CR + 1, 2 * CR, h, x=u((CD - CR - 1) / 2), y=0, z=zc0 + h / 2)))
    flank = _xz_prism([(u(-1), zc0), (u(CD + 1), zc0), (u(CD + 1), CRADLE_Z / 2 - TAN),
                       (u(-1), Z_RIDGE + TAN)], -CR - 1, CR + 1)
    cradle = cyl.intersect(flank)
    # ENTRY: the bore, and the flank from the knife up into it (planar, the ball's width and more)
    entry = B.cyl_x(ENTRY_D, T + 2, -T - 1, y=0, z=Z_ENTRY)
    # ...carried on in, the cradle's width, until it runs out inside the bore everywhere the ball
    # can touch: no land left between the ramp and the bore (it was a 0.7 step at y 1.85)
    ud = (Z_ENTRY - math.sqrt((ENTRY_D / 2) ** 2 - CR ** 2) - Z_RIDGE) / TAN + 0.2
    ramp = (_xz_prism([(u(-1), Z_RIDGE - TAN), (u(ENTRY_FLANK_U), Z_ENTRY - ENTRY_D / 2),
                       (u(ENTRY_FLANK_U), Z_ENTRY), (u(-1), Z_ENTRY)], -ENTRY_D / 2, ENTRY_D / 2)
            .union(_xz_prism([(u(-1), Z_RIDGE - TAN), (u(ud), Z_RIDGE + ud * TAN), (u(ud), Z_ENTRY),
                              (u(-1), Z_ENTRY)], -CR, CR)))
    return dict(slit=slit, cradle=cradle, entry=entry, ramp=ramp)


def plate() -> cq.Workplane:
    w = _blank()
    for c in cuts().values():
        w = w.cut(c)
    return w


def ball(phi: float, x_c: float, z_c: float = 0.0) -> cq.Workplane:
    """The ball, rolled phi about X (0 = hole up), centre at (x_c, 0, z_c)."""
    b = cq.Workplane("XY").add(cq.Solid.makeCylinder(BALL_D / 2, BALL_L, cq.Vector(0, 0, -BALL_L / 2),
                                                     cq.Vector(0, 0, 1)))
    return b.rotate((0, 0, 0), (1, 0, 0), phi).translate((x_c, 0, z_c))


def rest_x(phi: float, z_c: float = 0.0, p=None) -> float:
    """How far +X the ball goes before it touches the plate (its centre x), or +inf: through."""
    p = p or plate()
    lo, hi = X_FACE - 3.0, 2.0 + BALL_D       # hi: wholly past the +X face
    if p.intersect(ball(phi, hi - 0.01, z_c)).val().Volume() < 1e-4:
        # sweep it: is any position on the way blocked?
        path_ok = all(p.intersect(ball(phi, x, z_c)).val().Volume() < 1e-4
                      for x in [lo + k * 0.25 for k in range(int((hi - lo) / 0.25) + 1)])
        if path_ok:
            return math.inf
    for _ in range(30):
        m = (lo + hi) / 2
        if p.intersect(ball(phi, m, z_c)).val().Volume() > 1e-4:
            hi = m
        else:
            lo = m
    return lo


def contact_span(phi: float, z_c: float, p=None):
    """At the ball's stop, the Z span of what it touches (plate pushed 0.05 into it). The string pulls
    at the ball's middle (z_c): inside the span the ball rests; outside it, the pull tips the ball
    off the edge it is on, into the seat below or the entry hole above. None: it went through."""
    p = p or plate()
    x = rest_x(phi, z_c, p)
    if x == math.inf:
        return None
    hit = p.intersect(ball(phi, x + 0.05, z_c)).val()
    bb = hit.BoundingBox()
    return x, bb.zmin, bb.zmax


def report():
    p = plate()
    print(f"slit {SLIT_W} (neck {NECK_MAX}, sideways ball {BALL_L}), cradle R{CR} x {CRADLE_Z}, ridge at z {Z_RIDGE:.2f},"
          f" entry Ø{ENTRY_D} at z {Z_ENTRY:.2f}")
    print("roll phi -> where the ball stops, pulled +X with its centre on the axis (z 0)")
    for phi in (0, 15, 30, 45, 60, 75, 90):
        x = rest_x(phi, 0.0, p)
        state = "THROUGH (comes out)" if x == math.inf else f"stops, centre {x - X_FACE:+.2f} from the -X face"
        print(f"  phi {phi:3d}: {state}")
    print("hole-up ball, centre height z_c -> what it touches and whether the pull at its middle holds it")
    for zc in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 2.81, 3.0, 3.5, 4.0, 4.5, 5.0, Z_ENTRY):
        c = contact_span(0, zc, p)
        if c is None:
            print(f"  z_c {zc:5.2f}: THROUGH (out)"); continue
        x, z0, z1 = c
        if z0 - 0.05 <= zc <= z1 + 0.05 and z1 - z0 > 0.6:
            st = "RESTS"
        elif zc < z0:
            st = "tips DOWN (pull below the contact)"
        elif zc > z1:
            st = "tips UP (pull above the contact)"
        else:
            st = "balanced on a knife (unstable)"
        print(f"  z_c {zc:5.2f}: centre {x - X_FACE:+.2f} from the face, touches z {z0:+.2f}..{z1:+.2f}: {st}")
    print("any roll through the entry hole (centre at the entry)")
    for phi in (0, 45, 90):
        print(f"  phi {phi}: {'THROUGH' if rest_x(phi, Z_ENTRY, p) == math.inf else 'BLOCKED'}")
    # bearing area of the seated ball on the cradle: the arc outside the slit
    a0 = math.asin((SLIT_W / 2) / CR)
    area = 2 * CR * (math.pi / 2 - a0) * BALL_L
    print(f"seated bearing (cradle flanks outside the slit): ~{area:.1f} mm^2 -> {200 / area:.0f} MPa at 200 N")


if __name__ == "__main__":
    report()
    os.makedirs("out/keyhole_v3", exist_ok=True)
    cq.exporters.export(plate(), "out/keyhole_v3/keyplate_v3_cnc.step")
    print("wrote out/keyhole_v3/keyplate_v3_cnc.step")
