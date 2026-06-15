"""Electronics bay: compute hardware mounts + purchased-part dummies.

The PRO compute stack (per the compute plan) lives on one printed TRAY in the
keyhead bay (x -608..-530 - between the keyhead bulkhead and motor 9, under
the strings, above the open floor):

  - Raspberry Pi 5            (pro: 10ch audio->MIDI + Dexed + USB audio)
  - Teensy 4.1 + audio shield (basic+pro: sensors, CAN servo loop, UI, USB)
  - 2x CS42448 TDM ADC boards (pro: 10ch analog in; modeled stacked)
  - buck converter            (24V -> 5V for Pi + Teensy)
  - CAN transceiver breakout  (SN65HVD230: Teensy logic <-> CAN-H/L bus)

A BASIC build prints the SAME tray and just leaves the Pi/CS/buck mounts
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
from . import chassis as CH          # only early constants (X_*, Z_*) used here
from .helpers import box_at, cyl

# ---- bay geometry (chassis.py cuts the matching channels from these) ----
TRAY_X0, TRAY_X1 = -626.0, -548.0
TRAY_Y0, TRAY_Y1 = -127.5, 53.5        # 1.25 off each rail inner face
TRAY_Z0, TRAY_Z1 = -64.0, -61.0        # plate band (3 thick) - 1.15 ABOVE the
                                       # x -575 rib top so the bay rib passes
                                       # under the tray
TAB_X0, TAB_X1 = -599.0, -579.0        # one tab per side, in the only solid
                                       # web window between the leg dovetail
                                       # slot (ends -582) and the rail web
                                       # diamonds (start -560)
TAB_T = 2.7                            # into a 3-deep channel (0.3 floor gap)
CH_W, CH_D = 20.6, 3.0                 # channel cut: width / depth into web

# ---- board footprints (x0, x1, y0, y1); board bottom z = TRAY_Z1 + post ----
POST_H = 3.0
BD_T = 1.6
PI_FP     = (-612.0, -556.0, -32.0, 53.0)     # Pi 5: 56 x 85 (long side on Y)
TEENSY_FP = (-622.0, -561.0, -76.0, -58.0)    # Teensy 4.1 + shield stack
CS_FP     = (-622.0, -572.0, -124.0, -84.0)   # CS42448 x2, stacked
BUCK_FP   = (-568.0, -548.0, -120.0, -80.0)   # buck module, 20 x 40
XCVR_FP   = (-622.0, -596.0, -52.0, -39.0)    # SN65HVD230 breakout

BOARD_Z = TRAY_Z1 + POST_H             # every bottom board sits at -67

# ---- panel jacks (through the endplate recess wall, x 10..14 -> 4 thick) ----
# The real connectors are deep (TS ~22 mm, DC ~15.5 mm). Behind the endplate
# the corner is open in X for ~100 mm (out to motor 0 at x -89) EXCEPT the low
# bridge cross-rib (tops at z -65). So the jacks ride HIGH (z -41), clear above
# the rib and above the bottom-mounted AFE board - their bodies then reach
# freely into the open bay.
JACK_WALL_X = 10.0                     # inner face of the thinned wall
JACK_Z = -41.0
TS_Y, DC_Y, USB_Y = -68.0, -86.0, -104.0

# ---- UI: OLED + joystick on the top deck (mounted to the top plate) ----
# Centred along X. NOTE: the strings cover the deck within +-42.75 with only
# ~2 mm clearance, and the +Y/string-10 edge is just ~12 mm wide before the
# rail - too narrow for the 38 mm screen. So the UI sits on the WIDE -Y deck
# band (86 mm, over the motor PCBs, clear of the strings). The joystick (Alps
# RKJXT1F42001: 2-way rotary + 4-way + push) is the sole control.
UI_X      = (CH.X_BRIDGE + CH.X_NUT) / 2     # instrument X centre
DECK_TOP  = D.STRING_Z - 10.0                 # deck surface 10 mm under the
                                              # strings (bar can press strings
                                              # down without bottoming out) = +6
OLED_Y    = -100.0                            # wide -Y deck band (clear of strings)
OLED_W, OLED_L, OLED_T = 38.0, 72.0, 1.6      # 2.42" module PCB (Y x X)
JOY_X     = UI_X + 56.0                       # just +X of the screen
JOY_Y     = -82.0


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
AFE_X0, AFE_X1 = -22.0, -2.0
AFE_Y0, AFE_Y1 = -108.0, -78.0         # inboard of the pickup groove + leg barrel
AFE_Z = -59.0                          # board bottom (on the bridge-rib boss)
AFE_PED_TOP = -61.0                    # boss top (posts rise to the board)


def analog_frontend() -> cq.Workplane:
    """Bridge-end analog board dummy: relay (chunkiest), buffer/LDO/driver
    bumps. Mounted on the chassis -Y-corner pedestal."""
    bz = AFE_Z
    b = box_at(AFE_X1 - AFE_X0, AFE_Y1 - AFE_Y0, BD_T,
               x=(AFE_X0 + AFE_X1) / 2, y=(AFE_Y0 + AFE_Y1) / 2, z=bz + BD_T / 2)
    # relay (chunkiest, toward the east edge near the jacks)
    b = b.union(box_at(10.0, 7.5, 6.0, x=AFE_X1 - 7, y=AFE_Y1 - 8, z=bz + BD_T + 3.0))
    for px, py in ((AFE_X0 + 6, AFE_Y0 + 6), (AFE_X0 + 6, AFE_Y1 - 6),
                   (AFE_X1 - 6, AFE_Y0 + 6)):
        b = b.union(box_at(4.0, 4.0, 2.5, x=px, y=py, z=bz + BD_T + 1.25))
    return b


def _posts_strips_fingers(fp, bz):
    """Snap-mount set for one board footprint: 4 corner posts (top 0.2 under
    the board), 2 locator strips along the x edges (0.3 off the board), and
    2 snap fingers mid-x on the y edges, their 45-degree nubs hovering 0.15
    over the board top. All clearance - nothing touches the dummy."""
    x0, x1, y0, y1 = fp
    out = cq.Workplane("XY")
    for px in (x0 + 5, x1 - 5):
        for py in (y0 + 5, y1 - 5):
            out = out.add(cyl(5.0, bz - 0.2 - TRAY_Z1, z=TRAY_Z1)
                          .translate((px, py, 0)))
    for sy in (y0 - 1.0, y1 + 1.0):    # strips: 0.3 plan gap to the board
        out = out.add(box_at(x1 - x0 - 16.0, 1.4, bz + 1.0 - TRAY_Z1,
                             x=(x0 + x1) / 2, y=sy + (0.0 if sy < y0 else 0.0),
                             z=(TRAY_Z1 + bz + 1.0) / 2))
    xm = (x0 + x1) / 2
    nub_z = bz + BD_T + 0.15           # nub underside hovers over the board
    for sy, s in ((y0 - 1.0, 1), (y1 + 1.0, -1)):
        fin = box_at(5.0, 1.4, nub_z + 1.4 - TRAY_Z1,
                     x=xm, y=sy, z=(TRAY_Z1 + nub_z + 1.4) / 2)
        # 45-deg nub: chamfered both faces (prints standing, still retains)
        nub = (cq.Workplane("YZ")
               .polyline([(sy, nub_z), (sy + s * 1.5, nub_z + 0.7),
                          (sy, nub_z + 1.4)])
               .close().extrude(5.0).translate((xm - 2.5, 0, 0)))
        out = out.add(fin).add(nub)
    return out


def electronics_tray() -> cq.Workplane:
    """The printed tray: plate + drop-in side tabs + all snap-mount sets.
    Prints flat (plate on the bed, posts/fingers up, no overhangs beyond
    the 45-degree nubs)."""
    body = box_at(TRAY_X1 - TRAY_X0, TRAY_Y1 - TRAY_Y0, TRAY_Z1 - TRAY_Z0,
                  x=(TRAY_X0 + TRAY_X1) / 2, y=(TRAY_Y0 + TRAY_Y1) / 2,
                  z=(TRAY_Z0 + TRAY_Z1) / 2)
    for ye, s in ((TRAY_Y0, -1), (TRAY_Y1, 1)):      # side tabs into channels
        body = body.union(box_at(TAB_X1 - TAB_X0, TAB_T + 1.25, 6.0,
                                 x=(TAB_X0 + TAB_X1) / 2,
                                 y=ye + s * (TAB_T + 1.25) / 2 - s * 0.001,
                                 z=TRAY_Z0 + 3.0))
    for fp, bz in ((PI_FP, BOARD_Z), (TEENSY_FP, BOARD_Z + 1.0),
                   (CS_FP, BOARD_Z), (BUCK_FP, BOARD_Z), (XCVR_FP, BOARD_Z)):
        body = body.union(_posts_strips_fingers(fp, bz))
    return body


def _board(fp, bz, t=BD_T):
    x0, x1, y0, y1 = fp
    return box_at(x1 - x0, y1 - y0, t, x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                  z=bz + t / 2)


def pi5() -> cq.Workplane:
    """Raspberry Pi 5 dummy: board + USB/eth block (east edge, reachable
    from above) + SoC + GPIO header bar."""
    b = _board(PI_FP, BOARD_Z)
    b = b.union(box_at(18.0, 50.0, 14.0, x=PI_FP[1] - 9.0, y=10.0,
                       z=BOARD_Z + BD_T + 7.0))
    b = b.union(box_at(15.0, 15.0, 2.5, x=-590.0, y=10.0, z=BOARD_Z + BD_T + 1.25))
    b = b.union(box_at(5.0, 51.0, 8.0, x=PI_FP[0] + 4.0, y=10.5,
                       z=BOARD_Z + BD_T + 4.0))
    return b


def teensy_stack() -> cq.Workplane:
    """Teensy 4.1 with the audio shield stacked above on header pins."""
    bz = BOARD_Z + 1.0
    b = _board(TEENSY_FP, bz)
    b = b.union(_board(TEENSY_FP, bz + 11.0))                  # shield
    b = b.union(box_at(8.0, 10.0, 3.5, x=TEENSY_FP[0] + 5.0,   # micro-USB
                       y=(TEENSY_FP[2] + TEENSY_FP[3]) / 2, z=bz + BD_T + 1.75))
    for hy in (TEENSY_FP[2] + 2.6, TEENSY_FP[3] - 2.6):        # header rows
        # (inset so the tray's snap-finger nubs clear the headers)
        b = b.union(box_at(58.0, 2.4, 11.0, x=-591.5, y=hy, z=bz + BD_T + 5.5))
    return b


def cs_stack() -> cq.Workplane:
    """Two CS42448 TDM ADC boards, stacked on (printed) corner standoffs."""
    b = _board(CS_FP, BOARD_Z)
    b = b.union(_board(CS_FP, BOARD_Z + 14.0))
    for px in (CS_FP[0] + 4, CS_FP[1] - 4):
        for py in (CS_FP[2] + 4, CS_FP[3] - 4):
            b = b.union(cyl(5.0, 14.0 - BD_T, z=BOARD_Z + BD_T)
                        .translate((px, py, 0)))
    b = b.union(box_at(40.0, 4.0, 7.0, x=-597.0, y=CS_FP[3] - 3.0,
                       z=BOARD_Z + 14.0 + BD_T + 3.5))          # TDM header
    return b


def buck() -> cq.Workplane:
    """24V -> 5V buck module dummy (two caps + inductor)."""
    b = _board(BUCK_FP, BOARD_Z)
    for cy in (BUCK_FP[2] + 8, BUCK_FP[3] - 8):
        b = b.union(cyl(8.0, 9.0, z=BOARD_Z + BD_T)
                    .translate((-558.0, cy, 0)))
    b = b.union(box_at(12.0, 12.0, 7.0, x=-558.0, y=-100.0,
                       z=BOARD_Z + BD_T + 3.5))
    return b


def can_xcvr() -> cq.Workplane:
    """SN65HVD230 breakout dummy."""
    b = _board(XCVR_FP, BOARD_Z)
    b = b.union(box_at(20.0, 2.4, 8.0, x=-609.0, y=XCVR_FP[2] + 2.0,
                       z=BOARD_Z + BD_T + 4.0))
    return b


_AX = cq.Vector(1, 0, 0)                # plugs insert from +X (the panel face)


def _cyl_x(d, length, x, y, z) -> cq.Workplane:
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        d / 2, length, cq.Vector(x, y, z), _AX))


def ts_jack() -> cq.Workplane:
    """1/4-inch TS panel jack — Neutrik NMJ4HCD2 dims: Ø11.4 panel bushing,
    Ø~15 body ~22 mm deep BEHIND the panel, nut outside. Female socket bore
    Ø6.5 for the 6.35 mm plug."""
    b = _cyl_x(15.0, 22.0, -16.0, TS_Y, JACK_Z)            # deep body, behind cap
    b = b.union(_cyl_x(11.4, 8.05, 6.0, TS_Y, JACK_Z))     # bushing through cap
    b = b.union(_cyl_x(13.0, 2.0, 14.05, TS_Y, JACK_Z))    # nut, outside
    b = b.cut(_cyl_x(6.5, 33.0, -15.0, TS_Y, JACK_Z))      # female plug socket
    return b


def dc_jack() -> cq.Workplane:
    """DC barrel power inlet — Same Sky PJ-005A dims: Ø10.8 face, Ø5.7 thread,
    ~15.5 mm overall. Female Ø5.5 barrel bore with the Ø2.0 centre pin."""
    b = _cyl_x(10.8, 10.0, -4.0, DC_Y, JACK_Z)             # body behind the cap
    b = b.union(_cyl_x(5.7, 8.05, 6.0, DC_Y, JACK_Z))      # thread through cap
    b = b.union(_cyl_x(10.8, 2.0, 14.05, DC_Y, JACK_Z))    # front face, outside
    b = b.cut(_cyl_x(5.5, 22.0, -3.0, DC_Y, JACK_Z))       # female barrel bore
    b = b.union(_cyl_x(2.0, 17.0, -3.0, DC_Y, JACK_Z))     # centre pin
    return b


def usbc_jack() -> cq.Workplane:
    """Panel-mount USB-C module: body, flange, and the female receptacle - an
    8.34 x 2.56 mm racetrack opening with the centre tongue."""
    b = box_at(8.0, 22.0, 11.0, x=6.0, y=USB_Y, z=JACK_Z)
    b = b.union(box_at(4.1, 13.0, 6.6, x=12.0, y=USB_Y, z=JACK_Z))
    b = b.union(box_at(1.6, 21.0, 13.0, x=14.85, y=USB_Y, z=JACK_Z))
    # racetrack cavity (8.34 wide x 2.56 tall) + centre PCB tongue
    cav = box_at(7.0, 5.78, 2.56, x=12.5, y=USB_Y, z=JACK_Z)
    for dy in (-2.89, 2.89):
        cav = cav.union(_cyl_x(2.56, 7.0, 9.0, USB_Y + dy, JACK_Z))
    b = b.cut(cav)
    b = b.union(box_at(5.5, 6.7, 0.7, x=11.75, y=USB_Y, z=JACK_Z))
    return b
