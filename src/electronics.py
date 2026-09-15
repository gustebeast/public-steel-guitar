"""Electronics bay: compute hardware mounts + purchased-part dummies.

The PRO compute stack (per the compute plan) lives on one printed TRAY in the
keyhead bay (x -608..-530 - between the keyhead bulkhead and motor 9, under
the strings, above the open floor):

  - Raspberry Pi 5            (pro: 10ch audio->MIDI + Dexed + USB audio)
  - Teensy 4.1 + audio shield (basic+pro: sensors, CAN servo loop, UI, USB)
  - multichannel TDM ADC stack (pro: 10ch analog in; modeled stacked)
  - buck converter            (24V -> 5V for Pi + Teensy)
  - CAN transceiver breakout  (SN65HVD230: Teensy logic <-> CAN-H/L bus)

A BASIC build prints the SAME tray and just leaves the Pi/ADC/buck mounts
empty - the sockets are the upgrade path.

Mounting is tool-free and zero-hardware: each board sits on corner posts
between low locator strips and is retained by two 45-degree snap fingers
(all clearance-fit in the model - posts stop 0.2 under the board, finger
nubs hover 0.15 over it, so the gate sees no contact). The tray itself
drops in from above: a 40-wide tab on each side edge rides a vertical
channel cut in the rail web (open at the top, floor at the tab's z) -
gravity plus the wire loom holds it; lift straight out for service.

Panel I/O (TS line out, DC power in, USB-C) mounts through a 4 mm recessed
wall in the bridge endplate's lower -Y corner - the endplate prints flat so
the holes are print-trivial, and the inside there is empty floor band.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
# Everything chassis reaches BACK for lives above the chassis import -- see the note
# below. (The AFE board's footprint used to live here; it is deleted.)
# The jack row below is DERIVED from the bridge axle, not hardcoded. The endplate's inboard wall follows
# BRIDGE_AXLE_X (= BRIDGE_X - OD/2, because the string rides the OD and has to leave
# at x = 0), so when the bearing grew Ø8 -> Ø13 the axle stepped 2.5 -X and the wall
# came with it — straight through this board's +X edge, which sat at a constant.
# NOTE: this block sits ABOVE the chassis import ON PURPOSE. chassis builds at
# import time and used to reach BACK here for the AFE_* constants to cut its
# matching boss; the AFE is gone but the ordering still matters for the rest.
# boss (it once also read the tray tab/channel constants, now gone). With the constants below the import, that reach-back hit a
# half-initialised module and `import src.electronics` failed outright with a
# circular-import ImportError -- only working at all because everything else
# happened to import chassis first. These are plain literals, so hoisting them is
# free and makes the module importable on its own.
# ---- bay geometry (the tray's FLAT frame; see STANDING TRAY below) ----
TRAY_X0, TRAY_X1 = -607.0, -547.0
TRAY_Y0, TRAY_Y1 = -127.5, 53.5        # 1.25 off each rail inner face
TRAY_Z0, TRAY_Z1 = -64.0, -61.0        # plate band (3 thick) - 1.15 ABOVE the
                                       # x -575 rib top so the bay rib passes
                                       # under the tray


from . import chassis as CH          # only early constants (X_*, Z_*) used here
from .helpers import box_at, cyl, cyl_x
from cadkit.pcb import PCB_T as _PCB_T, jst_xh_header, jst_xh_side_header

# ---- board footprints (x0, x1, y0, y1); board bottom z = TRAY_Z1 + post ----
POST_H = 4 * D.BEAD                    # 3.2 printed standoff posts under each board
BD_T = 1.6
PI_FP     = (-603.0, -547.0, -50.0, 35.0)     # Pi 5: 56 x 85 (long side on Y);
                                       # slid 19 SOUTH (FLUSH round): the wired
                                       # leg's jack chimney + cable drop own the
                                       # tray's west-north corner (x > -603 must
                                       # stay clear of y > 35 there; east is
                                       # walled by motor 0)
# THE SOUTH HALF WAS RE-LAID-OUT around the motor controller (2026-09-14). The
# Teensy stack and the teensy_ifc carrier are both gone -- one 40 x 35 board does
# their job -- and 40 does not fit across 60 of tray beside the 36-wide buck, so
# the new board stands 90 deg to the tray's X (35 across, 40 along) in the -X -Y
# corner and the buck turns with it into the strip east of it. The ADC shifted
# 3 south to clear it; 0.5 of gap is all that is left between them, which is the
# honest state of a 60 x 181 tray holding four boards.
MCTRL_FP  = (-607.0, -572.0, -127.5, -87.5)   # motor controller, 35 x 40 (ROTATED)

BOARD_Z = TRAY_Z1 + POST_H             # every bottom board sits at -67

# ── STANDING TRAY (user, 2026-09-11) ─────────────────────────────────────────
# Everything above is the tray's FLAT layout -- plate, posts, boards -- and it is still
# the frame the tray PRINTS in. In the instrument the whole thing stands on its end with
# the plate's underside against the keyhead endplate's inboard face, so it takes only
# its stack depth in X instead of its 60 mm length, and the motor bank packs up to it
# (dimensions.MOTOR_X0). ONE rigid transform poses every part, so nothing inside the tray
# moves relative to anything else: rotate +90 deg about Y through the flat tray's -X
# bottom edge (up -> +X, the old +X end -> down), plate underside onto the keyhead face,
# bottom edge STAND_Z0.
# NO MOUNT YET (user): bronner is reworking the keyhead endplate, so retention is left
# for that round. The old drop-in side tabs and their rail channels are gone -- they
# do not line up with a standing tray.
STAND_Z0 = -62.0                       # bottom edge: 1.1 above the wired leg's TRRS pigtail
                                       # (top -63.1) where it runs east under this corner
STAND_DX = D.KEYHEAD_INBOARD_X - TRAY_X0
STAND_DZ = (STAND_Z0 + (TRAY_X1 - TRAY_X0)) - TRAY_Z0


def stand(wp: cq.Workplane) -> cq.Workplane:
    """Pose a part authored in the flat tray frame into the standing position."""
    return (wp.translate((-TRAY_X0, 0.0, -TRAY_Z0))
              .rotate((0, 0, 0), (0, 1, 0), 90.0)
              .translate((TRAY_X0 + STAND_DX, 0.0, TRAY_Z0 + STAND_DZ)))


def stand_pt(x: float, y: float, z: float):
    """The same transform for a single point (wiring endpoints on the boards)."""
    dx, dz = x - TRAY_X0, z - TRAY_Z0
    return (TRAY_X0 + STAND_DX + dz, y, TRAY_Z0 + STAND_DZ - dx)


# the dimensions datum the motor bank is packed against has to hold the real boards:
# tallest part above the plate's underside in the flat frame = depth in X once standing
_PI_TOP = BOARD_Z + BD_T + 14.0                # Pi 5 USB/ethernet block top (see pi5)
_MCTRL_TOP = BOARD_Z + BD_T + 9.8              # a MATED XH on the motor controller
_STACK = max(_PI_TOP, _MCTRL_TOP, BOARD_Z + BD_T + 9.0) - TRAY_Z0   # (+ buck caps)
assert _STACK <= D.ELEC_STACK_D + 1e-6, (
    f"the electronics stack is {_STACK:.2f} deep standing, over dimensions.ELEC_STACK_D "
    f"{D.ELEC_STACK_D} -- the motor bank is packed against that number")

# ---- panel jacks (through the endplate recess wall, kept 4 mm thick) ----
# The real connectors are deep (TS ~22 mm, DC ~15.5 mm). Behind the endplate
# the corner is open in X for ~100 mm (out to motor 0 at x -89) EXCEPT the low
# bridge cross-rib (tops at z -65). So the jacks ride HIGH (z -41), clear above
# the rib (and above where the AFE board used to sit) - their bodies then reach
# freely into the open bay.
# The +X face is now the centred 25 mm bridge's tip (BRIDGE_AXLE_X + 25/2 = 8.5), NOT
# X_BRIDGE+WALL -- the block is centred on the axle, not pinned to the rail end. Keep a
# 4 mm panel at that tip and slide the connectors (authored with their panel face at
# x~14) by JACK_FACE_DX so they ride the tip wherever it lands.
JACK_TIP = D.BRIDGE_AXLE_X + D.ENDPLATE_W / 2        # bridge +X face = centred block (8.5).
                                                     # Reads the BRIDGE's width, not the keyhead's:
                                                     # it used KH_EP_THK back when they were one
                                                     # number, which is now simply the wrong end
JACK_WALL_X = JACK_TIP - 4.0                          # inner face of the 4 mm panel (4.5)
JACK_FACE_DX = JACK_TIP - 14.0                        # authored face sits at x~14; ride the +X tip
JACK_Z = -51 * D.BEAD                  # -40.8 jack row centre height
# THE PANEL ROW IS NO LONGER EVENLY PITCHED, and it is not meant to be. TS and USB
# are now BOARD parts on output_panel and their spacing (31.27) is set by that board;
# only the DC inlet is still a free-standing panel jack, and it MOVED OUT of the
# board's span. It had been at -86, between the other two -- which put the 24 V pair
# for ten stepper drivers straight through the board that carries the output buffer,
# and the overlap gate found the wires passing through the PCB. At -118 it is 10 mm
# clear of the board, 10.75 from the -Y rail's inner face, and 50 mm from the audio
# jack, which is the separation that matters.
TS_Y = -68.0                           # THE ONE PANEL INPUT. Every other panel hole
                                       # is now an OUTPUT of the output+panel board
                                       # (DC_Y, USB_Y, defined after it) -- put all
                                       # three jacks on one PCB and the board, not
                                       # this file, decides where the holes go.

# ---- UI: OLED + joystick on the top deck (mounted to the top plate) ----
# Centred along X. NOTE: the strings cover the deck within +-42.75 with only
# ~2 mm clearance, and the +Y/string-10 edge is just ~12 mm wide before the
# rail - too narrow for the 38 mm screen. So the UI sits on the WIDE -Y deck
# band (86 mm, over the motor PCBs, clear of the strings). The joystick (Alps
# RKJXT1F42001: 2-way rotary + 4-way + push) is the sole control.
UI_X      = (CH.X_BRIDGE + CH.X_NUT) / 2     # instrument X centre
DECK_TOP  = D.DECK_TOP_Z                      # 6.4 — THE deck datum (was a stale
                                              # STRING_Z - 10 = 6.0, which sank the UI
                                              # dummies 0.4 into the deck plate); 9.6
                                              # under the strings, bar still can't bottom
OLED_Y    = -100.0                            # wide -Y deck band (clear of strings)
OLED_W, OLED_L, OLED_T = 38.0, 72.0, 1.6      # 2.42" module PCB (Y x X)
JOY_X     = UI_X + 70 * D.BEAD                # 56: just +X of the screen
JOY_Y     = -102 * D.BEAD                     # -81.6


def oled() -> cq.Workplane:
    """2.42" 128x64 OLED module dummy: PCB + glass + header, face up."""
    b = box_at(OLED_L, OLED_W, OLED_T, x=UI_X, y=OLED_Y, z=DECK_TOP + OLED_T / 2)
    b = b.union(box_at(62.0, 33.0, 2.0, x=UI_X, y=OLED_Y,
                       z=DECK_TOP + OLED_T + 1.0))          # glass active area
    b = b.union(box_at(20.0, 2.5, 5.0, x=UI_X, y=OLED_Y - OLED_W / 2 + 2.0,
                       z=DECK_TOP + OLED_T + 2.5))          # pin header (-Y edge)
    return b


def joystick() -> cq.Workplane:
    """Alps RKJXT1F42001 multi-control dummy: ~13 mm body + actuator cap."""
    b = box_at(13.0, 13.0, 9.0, x=JOY_X, y=JOY_Y, z=DECK_TOP + 4.5)
    b = b.union(cyl(7.0, 6.0, z=DECK_TOP + 9.0).translate((JOY_X, JOY_Y, 0)))
    return b

# ---- analog front end (bridge-end -Y corner, near the pickup + jacks) ----
# JFET buffer + SPDT signal relay (true-bypass: de-energized = raw straight to
# the jack; energize = the Q-processed DAC output) + relay driver/flyback +
# a local low-noise LDO fed from the nearby 24 V inlet. Clustering all the
# noise-sensitive analog here (away from the motor drivers) is the whole point;
# only buffered/line-level/logic runs make the long trip to the keyhead bay.


def _support_posts(fp, bz):
    """Four plain corner posts for one board footprint (tops flush with the board bottom --
    the board RESTS on them). Support only: NO retention for now (user, 2026-09-10). The M2
    corner anchor, its fat boss and the two locator strips that used to live here are gone;
    these boards are revisited later under the one-M4-beside-the-board rule
    (cadkit.pcb.pcb_cradle hold_edge), so nothing here should grow an M2 back."""
    x0, x1, y0, y1 = fp
    out = cq.Workplane("XY")
    for px in (x0 + 5, x1 - 5):
        for py in (y0 + 5, y1 - 5):
            out = out.add(cyl(5.0, bz - TRAY_Z1, z=TRAY_Z1).translate((px, py, 0)))
    return out


def electronics_tray(standing: bool = True) -> cq.Workplane:
    """The printed tray: plate + board support posts. Prints flat (plate on the bed,
    posts up); stands against the keyhead endplate in the instrument (see STANDING TRAY).
    Pass standing=False for the print pose."""
    body = box_at(TRAY_X1 - TRAY_X0, TRAY_Y1 - TRAY_Y0, TRAY_Z1 - TRAY_Z0,
                  x=(TRAY_X0 + TRAY_X1) / 2, y=(TRAY_Y0 + TRAY_Y1) / 2,
                  z=(TRAY_Z0 + TRAY_Z1) / 2)
    # each board rests on four plain posts -- no retention yet (see _support_posts)
    for fp, bz in ((PI_FP, BOARD_Z), (MCTRL_FP, BOARD_Z), (PWR_FP, BOARD_Z)):
        body = body.union(_support_posts(fp, bz))
    # (the NORTH-SHELF lane channel for the TRRS pigtail is gone: standing, the tray's
    #  bottom edge rides above that pigtail instead of lying over it)
    return stand(body) if standing else body


def _board(fp, bz, t=BD_T):
    x0, x1, y0, y1 = fp
    return box_at(x1 - x0, y1 - y0, t, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                  z=bz + t / 2)


def _ctr(fp):
    return (fp[0] + fp[1]) / 2, (fp[2] + fp[3]) / 2


def pi5() -> cq.Workplane:
    """Raspberry Pi 5 dummy: board + USB/eth block + SoC."""
    cx, cy = _ctr(PI_FP)
    b = _board(PI_FP, BOARD_Z)
    b = b.union(box_at(50.0, 18.0, 14.0, x=cx, y=PI_FP[3] - 9.0,
                       z=BOARD_Z + BD_T + 7.0))
    b = b.union(box_at(15.0, 15.0, 2.5, x=cx, y=cy, z=BOARD_Z + BD_T + 1.25))
    return stand(b)


# (adc_stack is DELETED, 2026-09-14. It modelled a three-PCM1864 carrier that
# digitised ten string signals for the Pi -- a path BOM.md struck out when the
# optical pickup board took on its own 20-channel conversion and sent audio over
# USB. The board had been struck in the BOM and left standing in the CAD, which
# is the wrong way round: the model is what other agents measure against.)


# ── POWER BOARD ──────────────────────────────────────────────────────────────
# IT REPLACES THE PURCHASED BUCK MODULE, and drops into the slot that module
# already held -- 22 x 36 inside the module's 23 x 36 -- so the tray does not move.
# BOM.md carried a Pololu D24V50F5 at $29.95 for the Pi plus a D24V10F5 at $12.95
# that existed only to power the Teensy, which is gone. Both are through-hole
# modules on 0.1 in headers and neither is an LCSC line, so neither can be placed
# by the assembler: they are hand-soldered wiring in the tray, which is the thing
# the whole connector strategy exists to delete.
#
# ⚠ THE CROWBAR IS THE POINT OF IT, not the buck. The Pi has to be fed from its
# GPIO header (its USB-C port is the front panel's gadget port), and on the Pi 4B
# the USB-C VBUS pin and the GPIO 5 V pins are THE SAME NODE with no polyfuse
# between them -- so feeding the header skips every input protection the Pi has.
# F2 in series with the 5 V output and D2 across it rebuild it: if the converter
# ever fails SHORT, 24 V lands on that rail and takes the Pi, the OLED and the
# joystick with it. D2 conducts, F2 opens, damage stops at a $0.30 part.
# See elec/power.py.
PWR_BOARD_X, PWR_BOARD_Y = 22.0, 36.0
PWR_FP = (-569.5, -547.5, -127.5, -91.5)     # inside the module's old 23 x 36 slot
PWR_J = {"J1": (0.0, -15.0, 180.0),          # 24 V in from the trunk tail
         "J2": (0.0, 15.0, 0.0)}             # 5 V out to the Pi's GPIO 2/4 + 6/9
# Board-local, GENERATED from the laid-out board: XY is the KiCad courtyard about
# each pad centroid, height is package-family typical (the one hand-entered column,
# and the one to distrust). The connectors are modelled properly by cadkit.
PWR_BOM = (
    ("C1", "10uF/50V",      4.69, 2.39, 1.60,  -7.00, -4.50),
    ("C2", "10uF/50V",      4.69, 2.39, 1.60,  -1.50, -4.50),
    ("C3", "100nF",         1.91, 1.01, 0.55,   3.00, -4.50),
    ("C4", "1uF",           1.91, 1.01, 0.55,  -9.00,  3.60),
    ("C5", "100nF",         1.91, 1.01, 0.55,  -9.00,  4.80),
    ("C6", "22uF/16V",      3.49, 2.05, 1.45,  -3.00,  6.00),
    ("C7", "22uF/16V",      3.49, 2.05, 1.45,  -3.00,  8.50),
    ("D1", "SMAJ30A",       7.09, 3.59, 2.20,   1.00, -8.50),
    ("D2", "SMBJ5.0A",      7.39, 4.59, 2.30,   4.00,  7.00),
    ("F1", "1A",            4.65, 2.35, 1.10,  -7.00, -8.50),
    ("F2", "4A",            4.65, 2.35, 1.10,  -7.50,  7.00),
    ("L1", "6.8uH",         6.69, 6.29, 2.80,   5.50,  0.00),
    ("R1", "100k",          1.95, 1.03, 0.50,  -9.00, -2.00),
    ("R2", "preset",        1.95, 1.03, 0.50,  -9.00, -0.50),
    ("R3", "preset",        1.95, 1.03, 0.50,  -9.00,  1.00),
    ("R4", "preset",        1.95, 1.03, 0.50,  -9.00,  2.40),
    ("U1", "LMR33630ADDAR", 7.49, 5.49, 1.75,  -3.00,  0.00),
)
USBP_BOM = (
    ("D1", "ESD",  2.59, 1.49, 0.75,   6.50, -2.50),
    ("D2", "ESD",  2.59, 1.49, 0.75,   6.50, -4.50),
    ("R1", "5k1",  1.95, 1.03, 0.50,  -6.50, -2.50),
    ("R2", "5k1",  1.95, 1.03, 0.50,  -6.50, -4.50),
)


def power_pcb() -> cq.Workplane:
    """The power board, posed in the standing tray (see PWR_FP). It DROPS INTO THE
    SLOT the purchased buck module held, so the tray does not move."""
    cx, cy = _ctr(PWR_FP)
    b = box_at(PWR_BOARD_X, PWR_BOARD_Y, BD_T, x=cx, y=cy, z=BOARD_Z + BD_T / 2)
    top = BOARD_Z + BD_T
    for ref, (jx, jy, rot) in PWR_J.items():
        p = jst_xh_header(4, mated=True, flip=True)
        if rot:
            p = p.rotate((0, 0, 0), (0, 0, 1), rot)
        b = b.union(p.translate((cx + jx, cy + jy, top)))
    for _n, _v, _w, _l, _h, _x, _y in PWR_BOM:
        b = b.union(box_at(_w, _l, _h, x=cx + _x, y=cy + _y, z=top + _h / 2))
    return stand(b)


# ── OUTPUT + PANEL BOARD ─────────────────────────────────────────────────────
# EVERY FRONT-PANEL CONNECTION ON ONE PCB (user, 2026-09-15). It merges the USB
# break-out that stops a laptop back-feeding the Pi with the analog OUTPUT STAGE
# that would not fit on the optical pickup board -- and the merge pays for itself
# twice, because putting the output stage at the panel is what lets the TS JACK
# BE A BOARD PART.
#
# ⚠ THE TS JACK ON THE BOARD FIXES A RULE VIOLATION rather than adding a part.
# BOM.md already specifies a Neutrik NMJ4HCD2 and that jack is PCB-MOUNT with a
# panel bushing -- KiCad ships its footprint. Panel-mounted as this file had it,
# its lugs would have been HAND-SOLDERED, which the project forbids outside a
# factory-assembled board. Same part, same price, and the last hand-soldered
# joint in the instrument goes away. Its nut clamps the endplate, so the PANEL
# takes the cable-yank load and the PCB does not.
#
# ⚠ TWO THINGS THE ENDPLATE HAS TO ABSORB (branner):
#   1. THE PANEL HOLES ARE NO LONGER ONE ROW AT ONE HEIGHT. A 1/4 in jack's axis
#      and a USB-C's axis sit at different heights above the board they share, so
#      the two holes differ in Z by that much (see OP_TS_AXIS_H). Their Y spacing
#      is now 31.27, set by this board rather than by the old 18 mm pitch.
#   2. THE DC BARREL JACK IS ON THIS BOARD TOO (user, 2026-09-15), and my earlier
#      objection to it was weaker than I made it sound. Two facts settled it: the
#      PJ-005A it replaces is a SOLDER-LUG jack, so it carried the same hand-soldering
#      violation the TS jack did, and BOM.md sizes the 24 V bus UNDER 5 A because the
#      fleet slew is staggered -- which is routine to carry across a board corner. The
#      noise argument survives only as a LAYOUT OBLIGATION, and it is met by keeping
#      PWR_GND a separate net that never joins AGND on this board (see J5/J6).
OP_BOARD_X, OP_BOARD_Y = 52.0, 66.0
# Connector anchors, board-local, straight out of elec/output_panel.py.
OP_J = {"J1": (18.34, 5.00, 90.0),        # panel USB-C, mouth +X
        "J2": (-17.61, 18.00, 180.0),     # USB-A to the Pi
        "J3": (-14.76, -28.00, 180.0),    # 8-way link to the optical board
        "J5": (20.92, -21.16, 0.0),       # 24 V inlet, barrel, bushing out +X
        "J6": (6.00, -26.00, 0.0)}        # 24 V trunk out, 2 contacts per rail
# (courtyard L, W, height, courtyard-centre offset from the anchor)
OP_BOX = {"J1": (9.51, 10.73, 3.26, (2.81, 0.00)),
          "J2": (15.59, 16.57, 6.60, (0.00, -4.39)),
          "J3": (21.29, 10.29, 7.00, (0.00, -1.70)),
          "J5": (11.59, 16.09, 11.00, (-0.82, -3.20)),
          "J6": (13.49, 6.84, 7.00, (0.00, -0.52))}
OP_TS_XY = (12.01, 22.24)                 # the 1/4 in jack's pad anchor
OP_TS_L, OP_TS_W = 27.62, 20.32           # its courtyard
OP_TS_OFF = (0.09, 0.00)                  # courtyard centre from the anchor
OP_TS_BODY_D = 15.0                       # Ø behind the panel (as ts_jack had it)
OP_TS_AXIS_H = 9.5                        # ⚠ THE ONE FIGURE NOT OFF A FOOTPRINT:
                                          # how high the bore sits above the board.
                                          # It sets the panel hole's Z and nothing
                                          # else checks it. Confirm against
                                          # Neutrik's drawing before cutting metal.
OP_BOM = (
    ("C1", "1nF",          1.91, 1.01, 0.55,  -0.50,   4.00),
    ("C2", "10uF",         3.49, 2.05, 1.45,  -9.00,   4.00),
    ("C3", "100nF",        1.91, 1.01, 0.55,  -5.50,   4.00),
    ("C4", "100nF",        1.91, 1.01, 0.55,  -3.00,   4.00),
    ("C5", "100nF",        1.91, 1.01, 0.55,   4.50,   4.00),
    ("C6", "2.2uF/100V",   4.69, 3.29, 1.80,   2.50, -13.00),
    ("D1", "ESD",          2.59, 1.49, 0.75,  11.00,   4.00),
    ("D2", "ESD",          2.59, 1.49, 0.75,  11.00,   2.00),
    ("D3", "flyback",      2.59, 1.49, 0.75,   9.50, -13.00),
    ("D4", "bidir clamp",  2.59, 1.49, 0.75,   6.50, -13.00),
    ("K1", "FRT5 5V",     13.15, 14.81, 5.10, -18.00,  -4.00),
    ("Q1", "AO3400A",      3.95, 3.49, 1.30,  11.31,  -6.00),
    ("R1", "5k1",          1.95, 1.03, 0.50,  11.00,   8.00),
    ("R2", "5k1",          1.95, 1.03, 0.50,  11.00,   6.00),
    ("R3", "470R",         1.95, 1.03, 0.50,   2.00,   4.00),
    ("R4", "100R",         1.95, 1.03, 0.50,  -6.50, -13.00),
    ("R5", "1M",           1.95, 1.03, 0.50,  -9.00, -13.00),
    ("R6", "100k",         1.95, 1.03, 0.50,  -1.50, -13.00),
    ("R7", "220R",         1.95, 1.03, 0.50,  -4.00, -13.00),
    ("U1", "PCM5102A",     7.79, 7.09, 1.20,  -4.00,  -6.00),
    ("U2", "RRO op-amp",   4.19, 3.49, 1.45,   6.23,  -6.00),
)


def output_panel_pcb() -> cq.Workplane:
    """The output + panel board in its OWN frame: board centred on the origin in
    XY, underside at z=0, parts rising +Z, the panel connectors facing +X."""
    b = box_at(OP_BOARD_X, OP_BOARD_Y, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    for ref, (jx, jy, _rot) in OP_J.items():
        l, w, h, (ox, oy) = OP_BOX[ref]
        b = b.union(box_at(l, w, h, x=jx + ox, y=jy + oy, z=_PCB_T + h / 2))
    # the 1/4 in jack: a real cylinder, because its BORE is what the endplate hole
    # has to line up with and a box would hide that
    jx, jy = OP_TS_XY
    zc = _PCB_T + OP_TS_AXIS_H
    b = b.union(box_at(OP_TS_L, OP_TS_W, OP_TS_AXIS_H, x=jx + OP_TS_OFF[0],
                       y=jy + OP_TS_OFF[1], z=_PCB_T + OP_TS_AXIS_H / 2))
    b = b.union(cyl_x(OP_TS_BODY_D, OP_TS_L, jx + OP_TS_OFF[0] - OP_TS_L / 2, jy, zc))
    for _n, _v, _w, _l, _h, _x, _y in OP_BOM:
        b = b.union(box_at(_w, _l, _h, x=_x, y=_y, z=_PCB_T + _h / 2))
    return b


# The panel holes bridge_endplate cuts. DERIVED, not typed: they follow the board.
DC_Y = TS_Y - OP_TS_XY[1] + OP_J["J5"][1]
USB_Y = TS_Y - OP_TS_XY[1] + OP_J["J1"][1]


def output_panel() -> cq.Workplane:
    """The output + panel board posed at the bridge endplate: flat, panel
    connectors out through the wall at +X.

    Z is set from the TS JACK'S BORE, not from the board: the jack is the part
    whose hole a player has to hit with a plug, so it owns the panel row's height
    and the board hangs wherever that puts it. Y is set so the jack lands on the
    existing TS_Y; the USB-C then falls 31.27 further -Y, which is where the panel
    hole has to move to."""
    # X: the jack's courtyard reaches 25.91 of a 26 half-board, so the BOARD EDGE is
    # the panel face to within 0.09 and is the honest thing to register against.
    b = output_panel_pcb().translate(
        (JACK_TIP - OP_BOARD_X / 2, TS_Y - OP_TS_XY[1],
         JACK_Z - _PCB_T - OP_TS_AXIS_H))
    return b.translate((JACK_FACE_DX, 0, 0))     # ride the panel's +X face


def op_pt(ref: str):
    """World (x, y, z) where a lead leaves the output+panel board's connector `ref`
    -- so wiring.py asks the board rather than carrying a copy of its layout, the
    same contract mctrl_pt provides for the motor controller.

    J2 (USB-A to the Pi) and J3 (the link to the optical board) both exit along the
    board's +Y; J1 is the panel USB-C and has no internal lead at all."""
    cx = JACK_TIP - OP_BOARD_X / 2 + JACK_FACE_DX
    cy = TS_Y - OP_TS_XY[1]
    jx, jy, _rot = OP_J[ref]
    l, w, h, (ox, oy) = OP_BOX[ref]
    return (cx + jx, cy + jy + oy + w / 2, JACK_Z - OP_TS_AXIS_H + h / 2)


def usb_panel_y() -> float:
    """Where the panel's USB-C hole now sits, for whoever cuts the endplate."""
    return TS_Y - OP_TS_XY[1] + OP_J["J1"][1]


# ── MOTOR CONTROLLER PCB ─────────────────────────────────────────────────────
# ONE per instrument, and it REPLACES THREE THINGS: the Teensy 4.1, its SGTL5000
# audio shield and the teensy_ifc carrier. The Teensy's value was the Audio
# Library, USB high-speed and the codec, all irrelevant once no audio touches
# this board (user: audio goes to the Pi; this board reads angles off bus B,
# applies the saved travel offsets and commands the SERVO42Ds on bus A). What
# could NOT be deleted is the pair of CAN TRANSCEIVERS -- no general-purpose MCU
# integrates one -- so the board was always going to exist; the only question was
# whether an MCU sat on it too. It now does, which is what deletes the jumper
# harness that used to run from the Teensy stack to the carrier.
#
# ⚠ THE OUTLINE IS AN OUTPUT, like the TRRS adapter and unlike every purchased
# board here: 40 x 35 is what elec/motor_ctrl.py's own contents came to, and the
# TRAY was re-laid-out around it (see MCTRL_FP). It stands 90 deg to the tray's
# X so 40 of board fits across 60 of tray beside the buck.
MCTRL_BOARD_X, MCTRL_BOARD_Y = 40.0, 35.0
MCTRL_ROT = 90.0                 # board +X -> tray +Y (see MCTRL_FP)
# Pad-row centres, board-local, straight out of elec/motor_ctrl.py's placements.
MCTRL_J = {"J1": (-10.0, 14.0, 0.0),     # bus A out -- the ten motor tees
           "J2": (4.0, 14.0, 0.0),       # bus B out -- the eight lever boards
           "J3": (15.5, 3.0, 90.0),      # 24 V in, +X edge
           "J4": (0.0, -9.0, 0.0)}       # USB-C to the Pi, -Y edge
MCTRL_USB = (10.73, 9.51, 3.26, 0.0, -11.81)   # HRO TYPE-C-31-M-12: courtyard + height
# Every populated part except the four connectors, which are modelled properly
# (cadkit XH / the USB block above). (name, value, X, Y, height, x, y), board-local
# and GENERATED from the laid-out board -- XY is the KiCad COURTYARD about the pad
# centroid, so the envelope is the assembly clearance rather than the bare body,
# which is the right error for a clearance model. HEIGHT is the one hand-entered
# column: it is package-family typical (the same figures knee_lever.SENSOR_BOM
# carries), not a footprint output, and it is the number to distrust.
MCTRL_BOM = (
    ("C1",  "4.7uF/50V",      4.69,  2.39, 1.60,  -16.50,  -3.50),
    ("C2",  "10uF/16V",       3.49,  2.05, 1.45,  -16.00,  -6.50),
    ("C3",  "100nF",          1.91,  1.01, 0.55,  -12.50,  -3.50),
    ("C4",  "12pF",           1.91,  1.01, 0.55,   -8.00,  -5.00),
    ("C5",  "12pF",           1.91,  1.01, 0.55,    0.00,  -5.00),
    ("C6",  "100nF",          1.91,  1.01, 0.55,  -11.00,   2.00),
    ("C7",  "100nF",          1.91,  1.01, 0.55,  -11.00,   5.00),
    ("C8",  "100nF",          1.91,  1.01, 0.55,  -11.00,   6.50),
    ("C9",  "100nF",          1.91,  1.01, 0.55,   -8.60,   8.50),
    ("C10", "100nF",          1.91,  1.01, 0.55,   -6.60,   8.50),
    ("C11", "100nF",          1.91,  1.01, 0.55,   -4.60,   8.50),
    ("C12", "100nF",          1.91,  1.01, 0.55,   -2.60,   8.50),
    ("C13", "100nF",          1.91,  1.01, 0.55,   -0.60,   8.50),
    ("C14", "100nF",          1.91,  1.01, 0.55,    1.40,   8.50),
    ("C15", "10uF",           3.49,  2.05, 1.45,   -8.00,  -7.50),
    ("D1",  "B5819W",         4.79,  2.39, 1.10,  -16.00,   0.00),
    ("D2",  "SMF24CA",        2.59,  1.49, 0.75,   12.30,  12.50),
    ("D3",  "SMF24CA",        2.59,  1.49, 0.75,   15.30,  12.50),
    ("D4",  "SMF24CA",        2.59,  1.49, 0.75,   10.00,  -5.50),
    ("D5",  "SMF24CA",        2.59,  1.49, 0.75,   13.00,  -5.50),
    ("D6",  "ESD",            2.59,  1.49, 0.75,    7.00, -12.50),
    ("D7",  "ESD",            2.59,  1.49, 0.75,   10.00, -12.50),
    ("JP1", "TERM",           3.39,  2.59, 0.05,   16.50,  -6.00),
    ("JP2", "TERM",           3.39,  2.59, 0.05,   16.50, -13.00),
    ("L1",  "47uH",           3.69,  3.69, 1.50,  -16.00,   3.50),
    ("R1",  "100k",           1.95,  1.03, 0.50,  -12.50,  -6.00),
    ("R2",  "30k1",           1.95,  1.03, 0.50,  -12.50,  -7.50),
    ("R3",  "10k",            1.95,  1.03, 0.50,   11.20,   6.50),
    ("R4",  "10k",            1.95,  1.03, 0.50,   11.20,   0.00),
    ("R5",  "120R",           3.05,  1.55, 0.55,   16.50,  15.00),
    ("R6",  "120R",           3.05,  1.55, 0.55,   16.50,  -9.50),
    ("R7",  "10k",            1.95,  1.03, 0.50,  -11.00,   0.50),
    ("R8",  "5k1",            1.95,  1.03, 0.50,   -7.00, -12.50),
    ("R9",  "5k1",            1.95,  1.03, 0.50,  -10.00, -12.50),
    ("U1",  "LMR16006XDDCR",  4.19,  3.49, 1.10,  -16.00,   8.00),
    ("U2",  "SN65HVD230DR",   7.49,  5.49, 1.75,    6.30,   6.50),
    ("U3",  "SN65HVD230DR",   7.49,  5.49, 1.75,    6.30,   0.00),
    ("U4",  "CH32V307WCU6",   9.29,  9.29, 0.90,   -4.00,   2.00),
    ("Y1",  "8MHz",           4.29,  3.59, 0.90,   -4.00,  -5.00),
)


def motor_ctrl_pcb(mating: bool = False) -> cq.Workplane:
    """The motor controller, in its OWN frame: board centred on the origin in XY
    with its underside at z=0 and every part rising +Z (single-sided, one
    assembly setup). `mating=True` swaps the bare XH headers for their mated
    envelope, which is the volume a housing has to leave alone.

    The three XH headers take cadkit's dummy with `flip=True`: the B4B-XH-A
    footprint puts the body on the -Y side of its pin row, and the connector is
    not symmetric about its pins, so which side the body falls on is a real
    choice at layout rather than a cosmetic one."""
    b = box_at(MCTRL_BOARD_X, MCTRL_BOARD_Y, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    for ref, (jx, jy, rot) in MCTRL_J.items():
        if ref == "J4":
            w, l, h, ox, oy = MCTRL_USB
            b = b.union(box_at(w, l, h, x=ox, y=oy, z=_PCB_T + h / 2))
            continue
        p = jst_xh_header(4, mated=mating, flip=True)
        if rot:
            p = p.rotate((0, 0, 0), (0, 0, 1), rot)
        b = b.union(p.translate((jx, jy, _PCB_T)))
    for _n, _v, _w, _l, _h, _x, _y in MCTRL_BOM:
        b = b.union(box_at(_w, _l, _h, x=_x, y=_y, z=_PCB_T + _h / 2))
    return b


def mctrl_pt(ref: str):
    """Tray FLAT-frame (x, y, z) where a lead leaves the motor controller's
    connector `ref` -- so wiring.py asks the board where its connectors are
    instead of carrying a copy of the layout. The three XH leads exit +Z off
    the top of a mated plug; the USB-C lead exits the mouth horizontally, which
    the board's 90 deg turn in the tray points at +X.

    The board-local -> tray mapping IS the MCTRL_ROT turn: board +X -> tray +Y,
    board +Y -> tray -X."""
    cx, cy = _ctr(MCTRL_FP)
    if ref == "J4":
        w, l, _h, ox, oy = MCTRL_USB
        return (cx - (oy - l / 2.0), cy + ox, BOARD_Z + BD_T + MCTRL_USB[2] / 2.0)
    bx, by, _rot = MCTRL_J[ref]
    return (cx - by, cy + bx, BOARD_Z + BD_T + 9.8)


def motor_ctrl() -> cq.Workplane:
    """The motor controller posed in the standing tray (see MCTRL_FP)."""
    cx, cy = _ctr(MCTRL_FP)
    b = (motor_ctrl_pcb(mating=True)
         .rotate((0, 0, 0), (0, 0, 1), MCTRL_ROT)
         .translate((cx, cy, BOARD_Z)))
    return stand(b)


# floor plane (bed top) — tee PCBs and the trunk-and-drop harness live here.
# = the LIVE chassis print-bed datum. Was a spelled-out -75.15, which had gone
# STALE: SCREW_TOP_Z, SCREW_PULLEY_Z and XBAR each moved onto the bead grid and
# the copy silently ended 0.2 below the real bed (-74.95). The off-grid audit is
# what caught it — a derived value that can't land on the grid means a parent
# moved without it.
FLOOR_Z = CH.Z_BOT


# ── CAN bus TEE PCB ──────────────────────────────────────────────────────────
# The SERVO42D has a SINGLE 6-pin XH (power+CAN), so it cannot be daisy-chained
# without a splice, and splicing is soldering. THAT is why the tee exists: it is
# what lets a motor be replaced with no solder. Everything else follows.
#
# TWO connectors, not three (2026-09-14, user). The trunk passes THROUGH one
# 8-way -- in on pins 1-4, out on 5-8, the same pattern and pin order the lever
# board uses -- and the motor hangs off its own 4-way. Keeping the DROP separate
# is what serves the purpose: pull one 4-way, swap the motor, plug it back, trunk
# undisturbed. Three separate 4-ways came to 40.47 mm of courtyard in a row;
# 8-way + 4-way is 36.98, and that 3.5 mm is what lets the board fit a motor top
# with locating walls on BOTH X edges instead of only +X.
#
# THE BOARD IS ALSO THE MOTOR'S RETENTION (branner): it seats 0.8 above the
# motor's top face with its +Y edge flush to the faceplate wall, so 6.4 of board
# lands on the wall and 9.6 laps the motor -- the lap IS the retention, and one
# screw does both jobs. Hence the hard constraint below: the THT tails hang 3.4
# under the board, so the whole tail band must stay within 6.4 of the +Y edge,
# over the wall. Anything further -Y hangs over the motor, where a live tail is
# the first thing the motor touches on the way out.
#
# SIDE ENTRY (branner, 2026-09-14), not the top entry this board had first. A mated
# top-entry plug stands 9.8 and string 10's tee fouled the magnetic pickup by 1.38,
# which would have left that one motor on a 45 deg screw while the other nine got
# board retention. Side entry stands 7.0 and clears, so the bank has no exception.
# Still through-hole -- the tails and their constraint survive -- and the part is
# CHEAPER: S8B-XH-A is LCSC C157914, $0.0705 with 66,430 in stock.
#
# ⚠ THE BOARD MODEL IS MINE (bronner); the STATION and the SEAT are branner's.
# TEE_YSHIFT and tee_board_cy below still carry the old rail derivation and are
# theirs to re-derive now the board sits on a motor.
TEE_CONN_N   = 4                                     # the motor DROP: gnd/24V/H/L
TEE_TRUNK_N  = 8                                     # trunk in (1-4) + out (5-8)
TEE_BOARD_X  = 40.0                                  # 36.98 of connector row + a full 1.0
                                                     # component-to-edge each end; also <= the
                                                     # 40.5 that allows both locating walls
TEE_BOARD_Y  = 16.0                                  # 6.4 on the wall + 9.6 lapping the motor
TEE_YSHIFT   = 5.0                                   # (branner's to re-derive -- see above)
TEE_TRUNK_X  = -7.0                                  # board-local pad-row centres
TEE_DROP_X   = 11.7
TEE_CONN_CY  = 2.0                                   # THE TAIL LINE. Both pin rows are
                                                     # COLLINEAR here, 6.0 from the +Y edge
                                                     # (limit 6.4), which is what keeps every
                                                     # tail over the faceplate wall. Moved from
                                                     # 4.0 with the switch to SIDE ENTRY: the
                                                     # pad row sits asymmetrically in that part
                                                     # (2.85 to the back, 9.74 to the mouth), so
                                                     # the body only fits the 16 with the row
                                                     # this far +Y.
TEE_CONN_MOUTH_DY = -3.25                            # mouth face, from the pad row: the body is
                                                     # 6.1 deep (cadkit XH_SIDE_D) and the row
                                                     # sits 2.85 from its back.
# ── THE EAR (branner, 2026-09-15) ────────────────────────────────────────────
# A SCREW BESIDE THE BOARD ONLY RESISTS PULL-OUT BY FRICTION, and the tee is
# pulled in exactly that direction whenever a cable comes off -- the connector
# mouths face -Y, so unplugging tugs -Y and only the head's grip opposes it. A
# screw THROUGH the board is positive in X and Y both.
# It does not fit inside 40 x 16: an M4 clearance hole wants 4.4 of component-free
# board and the connector courtyards reach within 3.145 of the +Y edge, 1.255
# short with nothing to give. So the OUTLINE grew and the LAYOUT did not -- every
# courtyard is where it was and TEE_CONN_CY is still 2.0.
# ⚠ THE EAR IS A TAB, NOT FULL DEPTH (branner): the motor bank staggers 9.5 in Y
# and that stagger is what lets ten ears interlock past each other. A full-depth
# ear clashed board-into-board at 48.5 mm3 per pair.
TEE_EAR_W, TEE_EAR_H = 9.5, 8.7              # off the +X end, at the +Y corner
TEE_HOLE_D = 4.5                             # M4 clearance, centred in the ear
TEE_HOLE_DX = TEE_BOARD_X / 2 + TEE_EAR_W / 2        # +24.75, board-local
TEE_HOLE_DY = TEE_BOARD_Y / 2 - TEE_EAR_H / 2        # +3.65
TEE_RELIEF   = (33.0, 3.0)                           # tail window (w x l), centred (0, CONN_CY)
# The terminator, as TWO parts rather than the one lumped box this used to carry.
# (name, X, Y, height, x, y) board-local, mirroring elec/can_tee.py's placements
# and KiCad's courtyards -- so the envelope is the assembly clearance, slightly
# larger than the bare component, which is the right error for a clearance model.
TEE_TERM = (("R1", 3.05, 1.55, 0.95, -6.0, 6.2),     # 120R, 0603
            ("JP1", 3.39, 2.59, 0.05, -1.0, 6.4))    # solder jumper -- bare pads,
                                                     # so it is flat by nature


def tee_board_cy(y: float) -> float:
    """Board (and cradle) centre Y for a tee at station y: the -Y edge stays at y-7
    (clear of the -Y rail, as before); the board grows +Y into the open corridor."""
    return y + TEE_YSHIFT


def tee_pcb(x: float, y: float, drop: int = 1, accurate: bool = True) -> cq.Workplane:
    """CAN bus TEE PCB dummy. ONE 8-way SIDE-entry XH for the trunk (S8B-XH-A, in
    on 1-4 and out on 5-8) plus ONE 4-way for the motor drop (S4B-XH-A), pin rows
    COLLINEAR at TEE_CONN_CY so every through-hole tail lands over the faceplate
    wall rather than over the motor. Plus the 120R-behind-a-jumper terminator,
    populated on all nine and closed only on the one that ends the bus.

    `drop` is kept for callers and no longer changes the geometry -- both mouths
    face -Y, out over the motor into free air, whichever side the motor is on.
    `accurate` is likewise vestigial: the two bus-B placeholder tees it used to
    select are gone, the levers having absorbed their own trunk tap."""
    top = FLOOR_Z + 1.6                              # board top face; connectors rise +Z
    cy = tee_board_cy(y)
    b = box_at(TEE_BOARD_X, TEE_BOARD_Y, 1.6, x=x, y=cy, z=FLOOR_Z + 0.8)
    # the ear, and then the hole through it
    b = b.union(box_at(TEE_EAR_W, TEE_EAR_H, 1.6,
                       x=x + TEE_HOLE_DX, y=cy + TEE_HOLE_DY, z=FLOOR_Z + 0.8))
    b = b.cut(cyl(TEE_HOLE_D, 4.0, z=FLOOR_Z - 1.0)
              .translate((x + TEE_HOLE_DX, cy + TEE_HOLE_DY, 0)))
    for dx, n in ((TEE_TRUNK_X, TEE_TRUNK_N), (TEE_DROP_X, TEE_CONN_N)):
        # side entry: cadkit's frame puts the MOUTH at y=0 with the body +Y, so
        # the part lands at the mouth, not at the pad row
        b = b.union(jst_xh_side_header(n, smt=False, mated=True)
                    .translate((x + dx, cy + TEE_CONN_CY + TEE_CONN_MOUTH_DY, top)))
    for _n, _w, _l, _h, _dx, _dy in TEE_TERM:
        b = b.union(box_at(_w, _l, _h, x=x + _dx, y=cy + _dy, z=top + _h / 2))
    return b


# ── TRRS <-> JST-XH ADAPTER PCB ──────────────────────────────────────────────
# Two of them, and they are the SAME board used in opposite directions: a passive
# four-wire pass-through, so "TRRS in, JST out" and "JST in, TRRS out" are the
# same copper. One at the chassis (trunk -> leg), one at the bar cradle.
#
# IT REPLACES THE FACTORY-CABLED TRRS PARTS. BOM.md crosses both joints with a
# Tensility 10-03404 jack-on-a-cable at $8.19 and a CA-354S plug-on-a-cable at
# $3.53, each with an XH crimped onto its cut end. Putting the jack ON A BOARD
# costs ~$0.10 of connector, deletes both crimps, and deletes the leg-socket tee.
#
# ⚠ THE OUTLINE IS AN OUTPUT HERE, NOT AN INPUT -- the opposite of every other
# board in this file. There is no housing yet (the leg-carrier CAD was never
# built; the column became an off-the-shelf extension cable), so these numbers
# are the board sizing ITSELF, derived from the two connectors' courtyards in
# elec/trrs_adapter.py. THE MECHANICAL SIDE SHOULD BE BUILT TO THEM.
#
# SIGNAL MAP, and the pin order is a SAFETY decision: tip = +24 V, ring1 = CAN_H,
# ring2 = CAN_L, sleeve = GND. A plug drags its bands across every socket contact
# on the way in, and 24 V on the wrong one lands on the CAN pair -- past the
# SN65HVD230's -4..+16 V bus-pin maximum. The escape is that each socket contact
# sits at a fixed depth and each plug band travels only as deep as its own
# resting position, so the socket's TIP contact is touched by exactly one thing
# in the whole insertion: the plug's tip band. The rail goes there, with the
# POWERED side carrying the SOCKET.
# ⚠ THE MOUTH FACES -Y, ALONG THE LONG AXIS (branner, 2026-09-14). The pocket
# over the leg is 22-26 across X between the keyhead endplate's inner wall and
# the electronics tray, so a board lying 26 across that gap (29.8 with its
# cradle) did not fit. Turned, the jack occupies 10.09 of a 20 mm width and the
# board reaches its 26 INBOARD along the plug's own line, which fits. The mouth
# also came in from 2.61 off the edge to 0.1: the jack's courtyard edge IS its
# barrel opening, so every millimetre of inset was a millimetre the plug had to
# reach through the chassis rail for nothing.
TRRS_BOARD_X, TRRS_BOARD_Y = 20.0, 26.0     # board-local, origin at its centre
TRRS_JACK_XY = (-1.085, -3.51)              # PJ-320D-4A (LCSC C95562), TURNED 90
TRRS_XH_XY   = (0.0, 9.0)                   # B4B-XH-A, turned 180 (see elec/)
TRRS_JACK_L  = 10.09                        # jack land ACROSS the board (X)...
TRRS_JACK_W  = 15.18                        # ...and along the plug's line (Y)
TRRS_JACK_OFF = (1.085, -1.80)              # courtyard centre from the pad anchor
TRRS_JACK_H  = 5.0                          # body height above the board. ⚠ the
                                            # one figure not off a footprint --
                                            # PJ-320 bodies run ~5, confirm at
                                            # purchase before a lid depends on it.
TRRS_MOUTH_Y = TRRS_JACK_XY[1] - 9.39       # -12.90: the barrel's opening face
TRRS_PLUG_RUN = 30.0                        # what a MATED plug needs -Y of the
                                            # mouth: ~14 of barrel inside plus the
                                            # moulded handle and its strain relief.
                                            # Deliberately generous -- the number
                                            # exists to reserve room, and over-
                                            # reserving is the safe error.
TRRS_PLUG_D  = 10.0                         # handle diameter to keep clear


def trrs_adapter_pcb(mating: bool = False) -> cq.Workplane:
    """The TRRS<->XH adapter, in its OWN frame: board centred on the origin in
    XY with its underside at z=0, parts rising +Z, the jack's mouth facing -Y
    along the board's LONG axis (see the note above). Pose it where a housing
    wants it -- there is no station for it yet.

    `mating=True` adds the envelope a plugged-in lead needs (TRRS_PLUG_RUN of
    Ø TRRS_PLUG_D out of the mouth, and the XH's mated height), which is the
    volume a housing has to leave alone rather than the board's own bulk."""
    b = box_at(TRRS_BOARD_X, TRRS_BOARD_Y, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    jx, jy = TRRS_JACK_XY
    b = b.union(box_at(TRRS_JACK_L, TRRS_JACK_W, TRRS_JACK_H,
                       x=jx + TRRS_JACK_OFF[0], y=jy + TRRS_JACK_OFF[1],
                       z=_PCB_T + TRRS_JACK_H / 2))
    b = b.union(jst_xh_header(4, mated=mating)
                .rotate((0, 0, 0), (0, 0, 1), 180)
                .translate((TRRS_XH_XY[0], TRRS_XH_XY[1], _PCB_T)))
    if mating:
        b = b.union(cyl(TRRS_PLUG_D, TRRS_PLUG_RUN)
                    .rotate((0, 0, 0), (1, 0, 0), 90)
                    .translate((jx + TRRS_JACK_OFF[0], TRRS_MOUTH_Y,
                                _PCB_T + TRRS_JACK_H / 2)))
    return b


# (ts_jack is DELETED: the 1/4 in jack is a PCB part on the output+panel board
#  now -- see OP_TS_XY. Modelling it as a free-floating panel jack implied
#  hand-soldered lugs, which the project forbids.)


# (dc_jack is DELETED: the 24 V inlet is a PCB part on the output+panel board now
#  -- see OP_J["J5"]. As a free-standing panel jack it was a PJ-005A, whose SOLDER
#  LUGS carried the same hand-soldering violation the TS jack did.)
