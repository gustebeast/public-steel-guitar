# -*- coding: utf-8 -*-
"""MKS SERVO42D on its NEMA17 -- a DETAILED dummy, drawn from pictures. NOT IN THE BUILD YET.

Why it exists: components.motor() is a 42.3 x 48 box with a smaller 36.3 x 22 box on its
-Y end, and the user (2026-10-01) pointed out it does not look like the part. It does not:
the driver is a BARE board the full size of the motor, standing on four short spacers,
components and screw terminals facing AWAY from the motor, and the coil lead loops outside
the motor's envelope.

Frame, same as components.motor(): shaft along +Y, centred on X = Z = 0; here the
FACEPLATE is y = 0 and everything else is -Y. The coil lead and the 4-way terminal are on
+Z as drawn; the 5-way (comms) and 6-way (power) terminals are then on -X and +X, wires
entering from the SIDE. The three buttons hang off the -Z edge.

WHERE EVERY NUMBER COMES FROM -- nothing here was measured on a part:
  * NEMA17 frame (square, pilot, bolt circle, corner chamfer, shaft) -- the NEMA standard
    and the common 17HS-series drawings. Solid.
  * the LAYOUT (bare board, spacers, terminals outboard, OLED, buttons, coil plug in the
    rear cap's side) -- two frames of the user's video of the unit, 2026-10-01.
  * BODY_L = 40 and the ~11 mm shroud -- scaled off the user's SIDE-ON photo of two shrouded
    units (the only square-on view; 39 and 44 for the bodies, 9.5 and 11 for the shrouds,
    against the 42.3 width). A close-up video frame scaled to 47, but its perspective
    stretches the near end. components.motor() says 48 + 22. +-3 mm: MEASURE -- dimensions.py
    hangs the motor pockets and the chassis' -Y rail off this length.
  * terminal lengths -- 2.54 mm pitch blocks, by way count.
  * which connector is which -- Makerbase's schematic (MKS SERVO42D_CAN V1.0_003):
      6-way  V+  GND  COM  EN  STP  DIR      <- 24 V goes in here (3 A fuse)
      5-way  5V  GND  IN1  CANH  CANL        <- CAN is here, on the OPPOSITE edge
      4-way  A+ A- B+ B-                     <- the coil lead
    So power and CAN are two cables per motor, not one 6-pin pigtail. The RS485 variant
    has the same 5-way block (A/B for H/L); the plain variant differs there.
"""
from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at, cyl_y

# -- the motor (NEMA17) --------------------------------------------------------
BODY_L = 40.0            # photo estimate -- see the docstring
CAP_F, CAP_R = 9.0, 10.0   # front and rear end caps; the lamination stack is between them
STACK_INSET = 0.4        # the laminations sit this far inside the caps, per side
CHAMFER = 4.1            # corner chamfer leg: 42.3 square inside a 54 mm circle
PILOT_D, PILOT_H = D.NEMA17_PILOT_D, 2.0
SHAFT_L = 24.0           # from the faceplate, pilot included (components.motor draws 18)
BOLT_SQ = D.NEMA17_BOLT_SQ
M3_TAP_D, M3_TAP_DEPTH = 3.0, 4.5

# the motor's own coil connector: a JST header in the SIDE of the rear cap, plug standing out
MCONN_W, MCONN_L, MCONN_PROUD = 8.0, 6.0, 4.0

# -- the driver (SERVO42D) -----------------------------------------------------
PCB_SQ, PCB_T = 42.0, 1.6
PCB_CORNER_R = 3.0
PCB_GAP = 2.5            # estimate: motor back -> PCB, the spacer length
SPACER_D = 6.0
TERM_H = 6.0             # estimate: terminal block height off the board
TERM_D = 6.6             # block depth, in the board plane
TERM_OUT = 0.5           # how far a block's wire face stands outside the PCB edge
TERM_5_L, TERM_6_L, TERM_4_L = 13.4, 16.0, 10.9   # 2.54 pitch
SCREW_HEAD_D, SCREW_HEAD_H = 5.6, 2.0   # the four M3 pan heads at the corners
OLED_W, OLED_H, OLED_T = 14.0, 10.0, 1.6   # the display, toward the button edge
OLED_DZ = -7.0
BTN_W, BTN_D, BTN_H, BTN_PITCH = 4.0, 3.5, 2.0, 6.5   # side-push buttons on the -Z edge
BTN_OUT = 1.0

# the optional black plastic shroud (user's third photo, 2026-10-01): a tray the full motor
# square, open toward the motor, notched where each terminal block shows
SHROUD_WALL = 1.0
SHROUD_L = PCB_GAP + PCB_T + TERM_H + SHROUD_WALL

# the coil lead: four wires from the 4-way terminal round the board edge to the motor's plug
LOOP_W, LOOP_PROUD = 12.0, 5.0

HALF = D.MOTOR_SQ / 2.0
TOTAL_L = BODY_L + SHROUD_L


def _square(length, y_far, inset=0.0):
    """A chamfered-corner square prism along Y, its -Y face at y_far."""
    s = D.MOTOR_SQ - 2 * inset
    return (cq.Workplane("XZ").rect(s, s).extrude(-length).edges("|Y").chamfer(CHAMFER)
            .translate((0, y_far, 0)))


def motor_body() -> cq.Workplane:
    b = _square(CAP_F, -CAP_F)
    b = b.union(_square(BODY_L - CAP_F - CAP_R, -(BODY_L - CAP_R), STACK_INSET))
    b = b.union(_square(CAP_R, -BODY_L))
    b = b.union(cyl_y(PILOT_D, PILOT_H, y0=0.0))
    b = b.union(cyl_y(D.MOTOR_SHAFT_D, SHAFT_L, y0=0.0))
    for sx in (1, -1):
        for sz in (1, -1):
            b = b.cut(cyl_y(M3_TAP_D, M3_TAP_DEPTH + 0.1, y0=-M3_TAP_DEPTH,
                            x=sx * BOLT_SQ / 2, z=sz * BOLT_SQ / 2))
    # the coil plug, standing out of the rear cap on the coil side
    b = b.union(box_at(MCONN_W, MCONN_L, MCONN_PROUD + 2.0, x=0.0,
                       y=-(BODY_L - CAP_R / 2), z=HALF + MCONN_PROUD / 2 - 1.0))
    return b


def driver() -> cq.Workplane:
    y0 = -BODY_L                       # the motor's back face
    ypcb = y0 - PCB_GAP - PCB_T        # the board's outward (-Y) face
    d = (cq.Workplane("XZ").rect(PCB_SQ, PCB_SQ).extrude(-PCB_T).edges("|Y")
         .fillet(PCB_CORNER_R).translate((0, ypcb, 0)))
    for sx in (1, -1):
        for sz in (1, -1):
            x, z = sx * BOLT_SQ / 2, sz * BOLT_SQ / 2
            d = d.union(cyl_y(SPACER_D, PCB_GAP, y0=y0 - PCB_GAP, x=x, z=z))
            d = d.union(cyl_y(SCREW_HEAD_D, SCREW_HEAD_H, y0=ypcb - SCREW_HEAD_H, x=x, z=z))
    # everything below stands on the outward face
    yterm = ypcb - TERM_H / 2
    tx = PCB_SQ / 2 + TERM_OUT - TERM_D / 2
    d = d.union(box_at(TERM_D, TERM_H, TERM_5_L, x=-tx, y=yterm, z=0.0))   # comms
    d = d.union(box_at(TERM_D, TERM_H, TERM_6_L, x=tx, y=yterm, z=0.0))    # power
    d = d.union(box_at(TERM_4_L, TERM_H, TERM_D, x=0.0, y=yterm, z=tx))    # coil
    d = d.union(box_at(OLED_W, OLED_T, OLED_H, y=ypcb - OLED_T / 2, z=OLED_DZ))
    for i in (-1, 0, 1):
        d = d.union(box_at(BTN_W, BTN_H, BTN_D, x=i * BTN_PITCH, y=ypcb - BTN_H / 2,
                           z=-(PCB_SQ / 2 + BTN_OUT - BTN_D / 2)))
    return d


def shroud() -> cq.Workplane:
    y0 = -BODY_L
    sh = _square(SHROUD_L, y0 - SHROUD_L)
    inner = D.MOTOR_SQ - 2 * SHROUD_WALL
    sh = sh.cut(cq.Workplane("XZ").rect(inner, inner).extrude(-(SHROUD_L - SHROUD_WALL))
                .translate((0, y0 - (SHROUD_L - SHROUD_WALL), 0)))
    yterm = y0 - PCB_GAP - PCB_T - TERM_H / 2
    for (wx, wz, cx, cz) in ((8.0, TERM_5_L + 1, -HALF, 0.0), (8.0, TERM_6_L + 1, HALF, 0.0),
                             (TERM_4_L + 1, 8.0, 0.0, HALF),
                             (2 * BTN_PITCH + BTN_W + 1, 8.0, 0.0, -HALF)):
        sh = sh.cut(box_at(wx, TERM_H + 2 * SHROUD_WALL + 0.2, wz, x=cx, y=yterm, z=cz))
    return sh


def coil_lead() -> cq.Workplane:
    """The four-wire loop's ENVELOPE: out of the 4-way terminal's +Z face, round the board
    edge, to the plug in the rear cap. It stands LOOP_PROUD outside the 42.3 square."""
    y_term = -BODY_L - PCB_GAP - PCB_T - TERM_H / 2
    y_plug = -(BODY_L - CAP_R / 2)
    return box_at(LOOP_W, abs(y_term - y_plug) + 4.0, LOOP_PROUD, x=0.0,
                  y=(y_term + y_plug) / 2, z=HALF + LOOP_PROUD / 2)


def servo42d(shrouded: bool = True) -> cq.Workplane:
    m = motor_body().union(driver()).union(coil_lead())
    return m.union(shroud()) if shrouded else m


def report() -> str:
    b = servo42d().val().BoundingBox()
    return ("SERVO42D dummy: %.1f long behind the faceplate (motor %.1f + driver %.1f); "
            "components.motor() says %.1f\n  envelope x %.2f..%.2f  z %.2f..%.2f  "
            "(the square is +-%.2f; the coil lead stands %.1f proud on +Z)\n"
            "  terminal wire faces at x +-%.2f, wires leave sideways"
            % (-b.ymin, BODY_L, -b.ymin - BODY_L, D.MOTOR_BODY_L, b.xmin, b.xmax, b.zmin,
               b.zmax, HALF, LOOP_PROUD, PCB_SQ / 2 + TERM_OUT))


if __name__ == "__main__":
    import pathlib
    from cadkit.step_export import export_step
    from cadkit.freecad import show
    # its own folder: the viewer hub names a tab after the STEP's parent folder
    out = pathlib.Path(__file__).resolve().parent.parent / "servo42d" / "servo42d.step"
    out.parent.mkdir(exist_ok=True)
    export_step(servo42d(), str(out))
    print(report())
    print("wrote", out)
    show(str(out))
