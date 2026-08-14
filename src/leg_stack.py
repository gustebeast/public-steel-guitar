"""REDESIGNED LEG — a chain of through-mortise sleeves joined by floating tenons.

Built fresh alongside the old legs.py (which is untouched) so it can be looked at
without destabilising the build. ONE leg only: the -X/+Y (TRRS) station.

THE CHAIN, top to bottom:

    pedal bar (mortise)
      |__ HEIGHT-ADJUST floating tenon   <- sets leg height; screw through a hole
    height-adjust leg (mortise)
      |__ FIXED floating tenon           <- joins the two sleeves; screw-locked
    fixed-height leg (mortise)
      |__ ...and the leg's OWN 44.8 section plugs the body adapter
    body quick-release adapter (mortise) -> body

WHY THE BODY END IS NOT A FLOATING TENON (design change, and it is load-driven).
The user's chain had the fixed tenon protrude out the bottom into the adapter.
It cannot: the kick case (250 N at 100 mm, leg at ~800 max = 175 N.m) puts the
instrument's worst moment at exactly that joint, and a 45-degree tenon is capped
at 24.6 mm across flats by the 44.8 leg and a 5 mm wall. That gives

    sleeve 44.8 sq   Z 13937 mm^3   12.6 MPa   SF 4.0
    tenon  24.0      Z  1629 mm^3  107.4 MPa   SF 0.47   <- fails
    tenon  31.7 (zero wall!)        46.6 MPa   SF 1.07

which is the SAME argument that ruled out a tenon-shaped adapter (user): bending
strength goes as the cube of the section, and the smallest section in the stack
must not be the one at the largest moment. So the fixed sleeve's own 44.8 body
enters the adapter and the full section carries the kick. The floating tenon
still runs the sleeve's length -- it just terminates inside rather than
protruding, so it aligns and stiffens instead of carrying.

That also keeps the LATCH handedness we already have: the removed piece (the
leg) presents the outer 44.8 section as the male, the adapter is the mortise, so
the button rides the male and the hook grabs OUTWARD into the adapter wall --
exactly latch.py as built. Only the PEDAL BAR end needs the mirrored variant
(button on a mortise, hook inward), because there the removed piece is the bar.

PROFILE: a square with its corners chamfered to a CHAM-wide flat -- an octagon
whose four extra sides are 1.6 (user: sharp corners cause joint fit issues).
Used rotated 45 degrees, which is what makes the mortise self-supporting: the
leg prints ON ITS SIDE, so a rotated square puts an APEX at the top and the
mortise roof is two 45-degree faces instead of a flat bridge down the whole
length.

NOT DONE YET / deliberately out of scope: cable management (space is reserved
for the TRRS jacks, nothing is routed), the mirrored bar-end latch, and the
detent rack for the height adjust (holes are drawn, the screw is not).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl

B = D.BEAD

# ── the section ─────────────────────────────────────────────────────────────
LEG_W = 56 * B                    # 44.8 outer square of every sleeve (unchanged
                                  # from the old leg, so chassis interfaces hold)
TEN_W = 30 * B                    # 24.0 floating-tenon across flats
CHAM = 2 * B                      # 1.6 chamfer face width -- the octagon's four
                                  # extra sides. A true square's sharp corner is
                                  # where a printed joint binds: the outside
                                  # corner rounds to the nozzle radius while the
                                  # inside stays sharp, so the fit fights itself.
FIT = 0.30                        # slide fit, tenon in mortise (a CLEARANCE: it
                                  # is a gap, so the bead grid does not apply)

# The 45-degree rotation is what makes the mortise printable, and it also sets
# the wall: the octagon's DIAGONAL points at the sleeve's faces.
WALL_MIN = LEG_W / 2 - (TEN_W + 2 * FIT) * math.sqrt(2) / 2
assert WALL_MIN >= 2 * D.MIN_WALL_2P, (
    "mortise wall %.2f is under two two-bead walls -- shrink TEN_W" % WALL_MIN)

# A self-crossing profile still EXTRUDES -- it just yields a mangled corner and a
# wrong section. Gate it on the one number that cannot lie: a chamfered square is
# the square minus its four corner triangles, w^2 - cham^2 exactly.
def _profile_area(w: float, cham: float = CHAM) -> float:
    return octagon(w, cham).extrude(1.0).val().Volume()


# ── lengths (a single leg; the height range lives in the adjust section) ─────
ADJ_L = 250 * B                   # 200.0 adjust sleeve
FIX_L = 250 * B                   # 200.0 fixed sleeve
ADJ_TEN_L = 220 * B               # 176.0 adjust tenon: reaches the bar and sinks
                                  # a long way into the adjust sleeve
FIX_TEN_L = 240 * B               # 192.0 fixed tenon: spans the fixed sleeve and
                                  # protrudes UP into the adjust sleeve only
ENGAGE = 60 * B                   # 48.0 least engagement of any tenon in a sleeve

# ── height adjust: a ladder of holes, not friction ──────────────────────────
ADJ_HOLE_D = 5 * B                # 4.0 through-hole for the M4 locking screw
ADJ_WEB = 2 * B                   # 1.6 material between holes -- this web, not
                                  # the screw, is what tears out under load, so
                                  # it is the number that sets pull-out strength
ADJ_PITCH = ADJ_HOLE_D + ADJ_WEB  # 5.6 and therefore the HEIGHT STEP
ADJ_N = 12                        # -> 12 * 5.6 = 67.2 mm of adjustment
# Two rows, offset half a pitch, on opposite faces: halves the step to 2.8
# without thinning any web (each row keeps its full 1.6).
ADJ_ROWS = (0.0, ADJ_PITCH / 2.0)

TRRS_D = 12 * B                   # 9.6 reserved bore for the TRRS jack body
TRRS_Z = 40 * B                   # 32.0 up from the sleeve's bottom face


def octagon(w: float, cham: float = CHAM):
    """Square of `w` across flats with its corners chamfered to `cham`-wide
    faces, as a closed 2-D wire on XY. Drawn at 45 degrees -- the pose it is
    USED in -- so an apex points +Y and the mortise roof self-supports."""
    h = w / 2.0
    c = cham / math.sqrt(2.0)          # the corner leg the chamfer cuts off
    pts = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        pts.append((sx * (h - c), sy * h))
        pts.append((sx * h, sy * (h - c)))
    # WALK THE PERIMETER. Getting this order wrong does not fail -- it makes a
    # self-crossing polygon that still extrudes, and the damage shows up as one
    # mangled corner (the -Y one) while the other three chamfer correctly. The
    # area check below is what actually catches it.
    #   flat, chamfer, flat, chamfer, ... counter-clockwise from the +Y top edge
    loop = [pts[0], pts[2],      # top flat      (h-c, h) -> (-(h-c), h)
            pts[3], pts[5],      # -X flat       (-h, h-c) -> (-h, -(h-c))
            pts[4], pts[6],      # bottom flat   (-(h-c), -h) -> (h-c, -h)
            pts[7], pts[1]]      # +X flat       (h, -(h-c)) -> (h, h-c)
    # NB: draw it SQUARE-ON and rotate the SOLID after extruding. Rotating the
    # Workplane here does nothing -- polyline().close() leaves a PENDING wire,
    # not an object on the stack, so extrude() would consume the unrotated
    # profile and the 45 would silently vanish (caught by the bounding box:
    # 24.0 across instead of 24 * sqrt2 = 33.9).
    return cq.Workplane("XY").polyline(loop).close()


def _at45(solid):
    """Into the INSTALL pose. The leg prints on its side, so an apex must point
    up: that turns the mortise roof into two 45-degree faces instead of a flat
    bridge running the whole length."""
    return solid.rotate((0, 0, 0), (0, 0, 1), 45)


def tenon(length: float, w: float = TEN_W):
    """A floating tenon: the octagon bar, extruded along +Z."""
    return _at45(octagon(w).extrude(length))


def mortise_cutter(length: float, w: float = TEN_W, fit: float = FIT):
    """The matching through-hole, grown by the slide fit on every face."""
    return _at45(octagon(w + 2 * fit).extrude(length))


def _sleeve(length: float, trrs: bool = False):
    """A leg section: LEG_W square, octagon mortise straight through."""
    b = box_at(LEG_W, LEG_W, length, z=length / 2.0)
    b = b.cut(mortise_cutter(length + 2.0).translate((0, 0, -1.0)))
    if trrs:
        # SPACE ONLY -- nothing is routed yet (user). A blind pocket in the wall
        # on the +X side, clear of the mortise, big enough for the jack body.
        b = b.cut(cyl(TRRS_D, 20.0, z=TRRS_Z)
                  .rotate((0, 0, 0), (0, 1, 0), 90)
                  .translate((LEG_W / 2 - 6.0, 0, TRRS_Z)))
    return b


def adjust_sleeve():
    """The HEIGHT-ADJUST section: the long one, so the tenon can be set over a
    wide range. Carries the locking screw's clearance hole."""
    b = _sleeve(ADJ_L, trrs=True)
    for dz in ADJ_ROWS:
        b = b.cut(cyl(ADJ_HOLE_D + 0.8, LEG_W + 4.0, z=ADJ_L * 0.5 + dz)
                  .rotate((0, 0, 0), (1, 0, 0), 90)
                  .translate((0, LEG_W / 2 + 2.0, 0)))
    return b


def fixed_sleeve():
    """The FIXED section. Its own 44.8 body is what enters the body adapter, so
    the kick moment never passes through a tenon (see the module docstring)."""
    return _sleeve(FIX_L)


def adjust_tenon():
    """Floating tenon, pedal bar <-> adjust sleeve. The LADDER of holes is the
    height setting: pick a hole, drop the screw, and every leg set to the same
    hole index is at the same height -- repeatable without measuring, which
    friction alone never is."""
    t = tenon(ADJ_TEN_L)
    for row, dz0 in enumerate(ADJ_ROWS):
        for i in range(ADJ_N):
            z = ENGAGE + dz0 + i * ADJ_PITCH
            if z > ADJ_TEN_L - ENGAGE / 2:
                break
            t = t.cut(cyl(ADJ_HOLE_D, TEN_W + 8.0, z=z)
                      .rotate((0, 0, 0), (1, 0, 0), 90)
                      .translate((0, TEN_W / 2 + 4.0, 0)))
    return t


def fixed_tenon():
    """Floating tenon, adjust sleeve <-> fixed sleeve. Spans the fixed sleeve
    and protrudes UP only; the bottom end stops inside, because the body joint
    is carried by the sleeve's own section."""
    return tenon(FIX_TEN_L)


def body_adapter():
    """Quick-release adapter: bolts to the body, receives the leg's OUTER 44.8
    section. Unchanged in role from the old design -- only the socket shape
    moved to the chamfered square. The latch female would be cut in this wall."""
    wall = 2 * D.MIN_WALL_2P
    h = 70 * B                                   # 56.0 socket depth
    b = box_at(LEG_W + 2 * wall, LEG_W + 2 * wall, h, z=h / 2)
    b = b.cut(box_at(LEG_W + 2 * FIT, LEG_W + 2 * FIT, h + 2.0, z=h / 2 + 1.0))
    return b


assert abs(_profile_area(TEN_W) - (TEN_W ** 2 - CHAM ** 2)) < 1e-6, (
    "octagon() is not a chamfered square -- the perimeter order is wrong. It "
    "extrudes anyway; only the area catches it (one corner comes out jagged).")


PARTS = {
    "adjust_sleeve": adjust_sleeve,
    "adjust_tenon": adjust_tenon,
    "fixed_sleeve": fixed_sleeve,
    "fixed_tenon": fixed_tenon,
    "body_adapter": body_adapter,
}


# ── CONTEXT (not printed parts -- just enough to read the chain end to end) ──
BODY_T = 20 * B                   # 16.0 slab standing in for the chassis underside
BAR_W = 56 * B                    # 44.8 pedal bar section, same as the leg
BAR_L = 200 * B                   # 160.0 of bar shown either side of the joint


def body_stub_context():
    """The chassis underside the adapter bolts to. NOT a printed part."""
    w = LEG_W + 8 * D.MIN_WALL_2P
    return box_at(w, w, BODY_T, z=-70 * B - BODY_T / 2)


def pedal_bar_context():
    """A length of pedal bar with the mortise that receives the adjust tenon.
    NOT a printed part -- the real bar lives in pedal_bar.py; this is the
    socket end only, so the chain can be read end to end."""
    top = FIX_L + FIX_TEN_L - 2 * ENGAGE + ADJ_L - ENGAGE + ADJ_TEN_L
    b = box_at(BAR_W, BAR_L, BAR_W, z=top - BAR_W / 2 + ENGAGE / 2)
    b = b.cut(mortise_cutter(BAR_W + 2.0).translate((0, 0, top - BAR_W - 1.0 + ENGAGE / 2)))
    return b


def assembly():
    """The chain, posed. Z=0 is the body adapter's mouth; the leg runs +Z."""
    out = []
    out.append(("body_adapter", body_adapter().translate((0, 0, -70 * B))))
    out.append(("fixed_sleeve", fixed_sleeve()))
    out.append(("fixed_tenon", fixed_tenon().translate((0, 0, FIX_L - ENGAGE))))
    out.append(("adjust_sleeve",
                adjust_sleeve().translate((0, 0, FIX_L + FIX_TEN_L - 2 * ENGAGE))))
    out.append(("adjust_tenon",
                adjust_tenon().translate(
                    (0, 0, FIX_L + FIX_TEN_L - 2 * ENGAGE + ADJ_L - ENGAGE))))
    out.append(("body_CONTEXT", body_stub_context()))
    out.append(("pedal_bar_CONTEXT", pedal_bar_context()))
    return out
