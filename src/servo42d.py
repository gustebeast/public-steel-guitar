# -*- coding: utf-8 -*-
"""MKS SERVO42D on its NEMA17 -- a DETAILED dummy, drawn from pictures. NOT IN THE BUILD YET.

Why it exists: components.motor() is a 42.3 x 48 box with a smaller 36.3 x 22 box on its
-Y end, and the user (2026-10-01) pointed out it does not look like the part. It does not:
the driver is a full-square finned shell, its three connectors are screw terminals on three
edges, and the coil lead loops OUTSIDE the motor's envelope.

Frame, same as components.motor(): shaft along +Y, centred on X = Z = 0; here the
FACEPLATE is y = 0 and everything else is -Y. The coil lead and the 4-way terminal are on
+Z as drawn; the 5-way (CAN) and 6-way (power) terminals are then on -X and +X, wires
entering from the SIDE.

WHERE EVERY NUMBER COMES FROM -- nothing here was measured on a part:
  * NEMA17 frame (square, pilot, bolt circle, corner chamfer, shaft) -- the NEMA standard
    and the common 17HS-series drawings. Solid.
  * BODY_L = 40 -- scaled off product photos against the 42.3 width (39.8 and 40.2 on two
    photos). components.motor() says 48. THIS IS THE NUMBER TO MEASURE: dimensions.py hangs
    the motor pockets AND the chassis' -Y rail off it.
  * the driver board, its terminals and their positions -- scaled off Makerbase's own top
    view using the 31.0 mm mounting holes as the ruler (20.6 px/mm). Good to ~0.5 mm in the
    board plane.
  * SHELL_L, the stand-off and every height along the motor axis -- ESTIMATED from an
    oblique photo and the length of the kit's screws. +-2 mm. Measure.
  * which connector is which -- Makerbase's schematic (MKS SERVO42D_CAN V1.0_003):
      6-way  V+  GND  COM  EN  STP  DIR      <- 24 V goes in here (3 A fuse)
      5-way  5V  GND  IN1  CANH  CANL        <- CAN is here, on the OPPOSITE edge
      4-way  A+ A- B+ B-                     <- the coil lead
    So power and CAN are two cables per motor, not one 6-pin pigtail.
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

# the motor's own coil connector: a JST header sunk in the rear cap, lead plug standing out
MCONN_W, MCONN_L, MCONN_PROUD = 16.0, 6.0, 5.0

# -- the driver (SERVO42D) -----------------------------------------------------
SHELL_L = 16.0           # estimate: motor back -> the shell's rear face
SHELL_WALL = 2.0
PCB_SQ, PCB_T = 37.6, 1.6
PCB_GAP = 4.0            # estimate: motor back -> PCB (magnet + encoder air gap)
TERM_H = 8.5             # estimate: terminal block height off the board
TERM_D = 6.6             # block depth, in the board plane
TERM_OUT = 1.6           # how far a block's wire face stands outside the PCB edge
TERM_5_L, TERM_5_OFF = 13.6, 1.3     # CAN block: length, centre offset toward the coil side
TERM_6_L, TERM_6_OFF = 16.8, -0.35   # power block
TERM_4_L = 10.9                      # coil block, centred
SCREW_HEAD_D, SCREW_HEAD_H = 5.6, 2.0   # the four M3 pan heads at the rear corners

# the coil lead: four wires from the 4-way terminal over the shell to the motor's plug
LOOP_W, LOOP_PROUD = 12.0, 10.0

HALF = D.MOTOR_SQ / 2.0
TOTAL_L = BODY_L + SHELL_L


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
    shell = _square(SHELL_L, y0 - SHELL_L)
    # hollow it from the motor side: it is a tray, open toward the motor
    inner = (cq.Workplane("XZ").rect(D.MOTOR_SQ - 2 * SHELL_WALL, D.MOTOR_SQ - 2 * SHELL_WALL)
             .extrude(-(SHELL_L - SHELL_WALL)).translate((0, y0 - (SHELL_L - SHELL_WALL), 0)))
    shell = shell.cut(inner)
    ypcb = y0 - PCB_GAP - PCB_T / 2
    pcb = box_at(PCB_SQ, PCB_T, PCB_SQ, y=ypcb)
    yterm = y0 - PCB_GAP - PCB_T - TERM_H / 2
    out = PCB_SQ / 2 + TERM_OUT          # a block's wire face, from the axis
    tx = out - TERM_D / 2
    # windows through the shell's sides where the three blocks show
    for (wx, wz, cx, cz) in ((TERM_D + 2, TERM_5_L + 1, -HALF, TERM_5_OFF),
                             (TERM_D + 2, TERM_6_L + 1, HALF, TERM_6_OFF),
                             (TERM_4_L + 1, TERM_D + 2, 0.0, HALF)):
        shell = shell.cut(box_at(wx, TERM_H + 1.0, wz, x=cx, y=yterm, z=cz))
    can = box_at(TERM_D, TERM_H, TERM_5_L, x=-tx, y=yterm, z=TERM_5_OFF)
    pwr = box_at(TERM_D, TERM_H, TERM_6_L, x=tx, y=yterm, z=TERM_6_OFF)
    coil = box_at(TERM_4_L, TERM_H, TERM_D, x=0.0, y=yterm, z=tx)
    d = shell.union(pcb).union(can).union(pwr).union(coil)
    for sx in (1, -1):
        for sz in (1, -1):
            d = d.union(cyl_y(SCREW_HEAD_D, SCREW_HEAD_H, y0=y0 - SHELL_L - SCREW_HEAD_H,
                              x=sx * BOLT_SQ / 2, z=sz * BOLT_SQ / 2))
    return d


def coil_lead() -> cq.Workplane:
    """The four-wire loop's ENVELOPE: from the 4-way terminal, up over the shell, to the
    motor's plug. It stands LOOP_PROUD outside the 42.3 square on the coil side."""
    y_term = -BODY_L - PCB_GAP - PCB_T - TERM_H / 2
    y_plug = -(BODY_L - CAP_R / 2)
    return box_at(LOOP_W, abs(y_term - y_plug) + 4.0, LOOP_PROUD, x=0.0,
                  y=(y_term + y_plug) / 2, z=HALF + LOOP_PROUD / 2)


def servo42d() -> cq.Workplane:
    return motor_body().union(driver()).union(coil_lead())


def report() -> str:
    b = servo42d().val().BoundingBox()
    return ("SERVO42D dummy: %.1f long behind the faceplate (motor %.1f + driver %.1f); "
            "components.motor() says %.1f\n  envelope x %.2f..%.2f  z %.2f..%.2f  "
            "(the square is +-%.2f; the coil lead stands %.1f proud on +Z)\n"
            "  terminal wire faces at x +-%.2f -- %.2f INSIDE the square, wires leave sideways"
            % (-b.ymin, BODY_L, -b.ymin - BODY_L, D.MOTOR_BODY_L, b.xmin, b.xmax, b.zmin,
               b.zmax, HALF, LOOP_PROUD, PCB_SQ / 2 + TERM_OUT, HALF - PCB_SQ / 2 - TERM_OUT))


if __name__ == "__main__":
    import pathlib
    from cadkit.step_export import export_step
    from cadkit.freecad import show
    out = pathlib.Path(__file__).resolve().parent.parent / "test_servo42d.step"
    export_step(servo42d(), str(out))
    print(report())
    print("wrote", out)
    show(str(out))
