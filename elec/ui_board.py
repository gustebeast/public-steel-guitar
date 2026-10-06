"""THE UI BOARD -- the encoder, the display's connector, and one ribbon to the Pi.

    py -3.12 elec/ui_board.py       # -> elec/out/ui_board.{net,board.json}
    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/finish.py elec/out/ui_board

WHAT IT IS. The whole user interface of the instrument is one display and one control,
and the display is a bought MODULE (Newhaven NHD-2.7-12864WDW3: white on black at
63.41 x 32.69, which is the size the legibility budget in BOM.md settles on, and that
combination is not sold as a bare panel). So this board carries the CONTROL, the
module's connector, and the single cable that leaves the station.

THE CONTROL IS ONE PART. Alps RKJXT1F42001 (LCSC C160841): a 15-pulse / 30-detent
incremental encoder that turns for ever either way, a 4-direction stick, and a centre
push, all on one 17 x 17 shaft. Stepped, clicky, infinite, plus N/E/S/W in a single
through-hole part -- which is the entire UI requirement.

  WARNING: THE DIRECTION LETTERS ARE NOT COMPASS POINTS. Alps names the four contacts
  A B C D and the drawing's arrows are the part's own frame; which one is "north" to a
  player depends on how the part is clocked in the deck and which way they sit. The
  nets are therefore SW_A..SW_D, and the N/E/S/W assignment is made once in firmware
  against the built instrument. Naming them north/east here would be a guess frozen
  into copper.

THE GEOMETRY COMES FROM src/ui_panel.py, AND SO DOES THE CAD'S. That module owns where
the station sits on the deck, and both sides read it: this file derives every placement
from it, and after routing src/board_geom.py reads the finished .kicad_pcb back and the
CAD draws THAT. Nothing is typed twice, and nothing downstream can drift from what was
actually fabbed -- which is the failure elec/export_geom.py exists to have ended.

-- WHY THE HEADERS ARE THE HEADERS THEY ARE ---------------------------------
J1 is a MALE 1x20 and the module gets the female. Newhaven ships the module with plated
holes and no header at all, so both halves are ours to choose. Socket on our board and
the module needs a long-pin header to reach down through it; socket on the module and
both halves are stock parts with 6 mm of engagement. See src/ui_panel.py.

J2 is a RIGHT-ANGLE 2x7 IDC box header, and every word of that was forced:
  * IDC, because fourteen crimps is fourteen chances to get one wrong and a ribbon is
    one press. The project's no-solder-off-a-PCB rule is satisfied either way.
  * right-angle, because the board hangs UNDER the deck with 11.74 mm of air over it and
    a vertical box header stands about 13.5. The ribbon leaves -X, under the deck,
    toward the keyhead bay, which is where the Pi is.
  * 2x7 and not 2x10, because the board is 34 deep and a 2x10's shroud is 33.2 long. It
    would fit nowhere that also clears the display module above it. The cost is the
    interleaved ground returns a 20-way would have carried: SCLK gets GND on one side
    and +3V3 -- an AC ground -- on the other, and that is the best a 14-way can do.

-- WHY THERE ARE SEVEN RESISTORS AND NO DEBOUNCE CAPACITORS ------------------
Every contact on the encoder is a dry switch to a common, so each of the seven signals
needs a pull-up. 10k external rather than the Pi's own ~50k internal, because the run is
half a metre of ribbon through an instrument full of stepper drivers and a CAN bus.

No capacitor across any of them. An RC debounce puts the cap's charge through the
contact at every make, and this contact is rated 10 mA with a 50,000-cycle life on the
directions and 15,000 on the encoder -- the cheapest way to spend that life. Debouncing
is done in the Pi's software, where it costs nothing and can be tuned.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# SKiDL names its log after the script and drops it in the CWD at IMPORT time, so this
# has to happen before the skidl import. Every derived file belongs in elec/out.
os.makedirs(OUT_DIR, exist_ok=True)
os.chdir(OUT_DIR)

import json  # noqa: E402

from skidl import ERC, Net, Part, Pin, generate_netlist, subcircuit  # noqa: E402

import netcheck                                      # noqa: E402
from src import ui_panel as UI                       # noqa: E402

P = Pin.types.PASSIVE

ENC_FP = "Steel:Alps_RKJXT1F42001"
DISP_FP = "Connector_PinHeader_2.54mm:PinHeader_1x20_P2.54mm_Vertical"
# ⚠ THE SAME HEADER AS THE PI CAP'S END (user, 2026-10-02: "both ends of the connection are
# our custom PCB so we can pick whatever connector we want"). This was a 2.54 mm IDC box
# header, which takes 1.27 ribbon; the cap's end is a 1.27 mm header, which takes 0.635.
# No cable joins those. The cap cannot take 2.54 (it lives in an 8.5 mm gap), so this end
# moves to the HX PZ1.27 right-angle family (a 2 x 7 at first). It is NOT shrouded --
# nobody stocks a shrouded 1.27 header this size -- so pin 1 is marked in silk at both
# ends.
# ⚠ 2x8 SINCE THE POWER BUTTON (2026-10-04): the same family's next size, HX PZ1.27-2x8P WZ,
# LCSC C22438114, and a stock 16-way lead. Ways 1-14 are where they were.
RIBBON_FP = "Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Horizontal"
PWR_FP = "Steel:Legion_PB-22E85"

PULLUP = "10k"

# -- J1: the display module, 4-wire SPI -------------------------------------
# Newhaven's pin table (datasheet p.4, Serial Interface) read 2026-09-25. Everything
# not listed is VSS on their own table, so it is wired to GND rather than left open --
# a floating pin on a 20-way header is an antenna and a probing hazard both.
#
# BS1 = 0, BS0 = 0 SELECTS 4-WIRE SPI, and that is now READ, not inferred: the
# "MPU Interface Pin Selections" table on p.5 gives BS1/BS0 as 1/1, 1/0, 0/1, 0/0 for
# 6800, 8080, 3-wire and 4-wire respectively. An earlier note in BOM.md flagged this as
# the standard SSD1322 mapping that wanted a human's eyes on the PDF before the board
# was fabbed. It has had them, and the standard mapping was right.
#
# /SHDN is tied to VDD rather than run to the Pi. It is internally pulled high, so this
# changes nothing electrically and removes a node that would otherwise float at the end
# of half a metre of ribbon. The display is blanked by command, not by dropping its
# boost converter.
DISP_PINS = {
    1: "GND", 2: "+3V3", 3: "NC_BC_VDD", 4: "DC", 5: "GND", 6: "GND",
    7: "SCLK", 8: "SDIN", 9: "NC_9", 10: "GND", 11: "GND", 12: "GND",
    13: "GND", 14: "GND", 15: "NC_VCC", 16: "RES_N", 17: "CS_N", 18: "+3V3",
    19: "GND", 20: "GND",
}

# -- J2: the ribbon to the Pi -----------------------------------------------
# ⚠ THE FAR END OF THIS CONNECTOR IS NOT DECIDED, so this order is provisional (user
# asked how the cable reaches the Pi, 2026-09-28). A 2x7 IDC socket pushes onto any seven
# adjacent pin-pairs of the Pi's 40-way header, and NO seven of them fit these 14 ways:
# the best block offers 11 GPIO (pins 11-24 or 15-28) against the 12 signals below, and
# wanting hardware SPI0 costs two more (it lives on pins 19/21/23/24 and claims GPIO9 for
# a MISO the display never uses). Pins 1-14, the obvious block, is the worst: 8 GPIO, and
# motor_ctrl's J5 already feeds 5 V onto four of them.
#
# THE ADAPTER THAT RESOLVES IT ALREADY EXISTS: bronner's elec/pi_cap.py, a 2x20 socket on
# the Pi's header with every unused pin explicitly netted PI_NC_<n> -- so all fourteen ways'
# worth of GPIO is already on its copper and the "which seven pins" problem goes away
# entirely. It has no room for a 2.54 IDC (its connectors live in an 8.5 mm gap and a 2.54
# male header is 8.54 before its socket goes on), so it wants a 1.27-pitch 2x7 or an FFC,
# and it is not on main yet. See BOM.md -- and note that IT WILL REORDER THESE WAYS either
# way, because a connector reaching the Pi has its pin positions chosen for it, which is
# exactly the freedom the order below was chosen for.
#
# ORDERED FOR THE CLOCK. A 14-way flat cable has one ground to give, so it is spent
# where it buys the most: conductor 8 sits beside SCLK on 9, and +3V3 on 10 sits on its
# other side. Both are AC grounds at the Pi, so the clock runs between two quiet
# conductors for the whole length. The switch lines are slow and share the far end.
# ⚠ THE ORDER IS harness.UI_RIBBON NOW, the list the Pi cap's J5 is also held to. The
# order that stood here (switches on 1-7, ground on 8) was this board's own and matched
# nothing at the far end.
import harness as _H  # noqa: E402
RIBBON_PINS = {_i + 1: _n for _i, _n in enumerate(_H.UI_RIBBON)}

# -- SW1: the Alps part's own pin names, off its drawing and LCSC's symbol --
ENC_PINS = {
    "A": "SW_A", "B": "SW_B", "C": "SW_C", "D": "SW_D",
    "5": "SW_PUSH",     # centre push
    "6": "GND",         # common for the four directions AND the push
    "7": "ENC_B", "8": "ENC_A",
    "9": "GND",         # encoder common
    "10": "GND",        # the frame's ground lug
}
PULLED_UP = ("SW_A", "SW_B", "SW_C", "SW_D", "SW_PUSH", "ENC_A", "ENC_B")

# -- SW2: the power button (user, 2026-10-04) --------------------------------
# A self-locking 2P2T push switch. It switches NOTHING on this board: both poles are
# paralleled, their commons go to the ribbon's GND, and each throw rides its own way to
# the output board, which is where the supply comes in and the only place it can be cut.
# So the state arrives there as one line shorted to GND and the other open, and that
# board picks whichever polarity fails the way it wants.
# ⚠ NO PULL-UP HERE, on purpose. The seven above hang off +3V3, which is the Pi's rail and
# is DEAD when this switch has done its job; a pull-up to it would be a path from the
# output board's standby supply back into an unpowered Pi.
# ⚠ 12 V 0.3 A IS THE SWITCH'S RATING, so what pulls these lines up at the far end has to
# be a logic-level standby node, never the 24 V rail.
# ⚠ WHICH THROW IS WHICH IS OFF THE DRAWING'S SCHEMATIC, NOT A METER: it shows each common
# joined to one end terminal, taken here as the button-OUT state and as pads 3 and 6.
# Check the first one with a meter. If it is the other way round the button's sense
# inverts, nothing worse -- and a part fitted half a turn round does the same thing.
PWR_PINS = {1: "PWR_SW_DN", 2: "GND", 3: "PWR_SW_UP",
            4: "PWR_SW_DN", 5: "GND", 6: "PWR_SW_UP"}


# THE RIBBON'S SHAPE IS THE CAD'S AND THE NETLIST'S BOTH. src/ui_panel.py draws sixteen
# conductors at 1.27; this is the connector they come off. If a way is ever added here,
# the drawing has to follow or the cable drawn is not the cable the header takes.
assert len(RIBBON_PINS) == UI.RIBBON_N, (
    "J2 has %d ways and the CAD draws a %d-way ribbon"
    % (len(RIBBON_PINS), UI.RIBBON_N))
assert abs(UI.RIBBON_PITCH * 2 - 1.27) < 1e-9, (
    "the ribbon's %.3f pitch is not half the header's 1.27" % UI.RIBBON_PITCH)


def _r(tag, value, desc):
    return Part(name="R", ref_prefix="R", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc,
                footprint="Resistor_SMD:R_0402_1005Metric",
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


def _c(tag, value, desc, pkg="Capacitor_SMD:C_0402_1005Metric"):
    return Part(name="C", ref_prefix="C", ref=tag, tag=tag, dest="NETLIST", tool="skidl",
                value=value, description=desc, footprint=pkg,
                pins=[Pin(num=1, func=P), Pin(num=2, func=P)])


@subcircuit
def ui_board():
    nets = {n: Net(n) for n in ("GND", "+3V3", "SCLK", "SDIN", "DC", "CS_N", "RES_N",
                                "ENC_A", "ENC_B", "SW_PUSH",
                                "SW_A", "SW_B", "SW_C", "SW_D",
                                "PWR_SW_UP", "PWR_SW_DN")}
    for n in ("GND", "+3V3"):
        nets[n].drive = Pin.drives.POWER
    # the module's three no-connects, each on a net of its own so nothing shorts them
    # together and no pin is left orphaned (netcheck.no_orphan_pins)
    for n in ("NC_BC_VDD", "NC_9", "NC_VCC"):
        nets[n] = Net(n)

    sw1 = Part(name="RKJXT1F42001", ref_prefix="SW", ref="SW1", tag="SW1",
               dest="NETLIST", tool="skidl", value="RKJXT1F42001",
               description="Alps 4-way stick + encoder + push (LCSC C160841)",
               footprint=ENC_FP,
               pins=[Pin(num=k, name=v, func=P) for k, v in ENC_PINS.items()])
    for pin, net in ENC_PINS.items():
        nets[net] += sw1[pin]

    j1 = Part(name="PinHeader_1x20", ref_prefix="J", ref="J1", tag="J1",
              dest="NETLIST", tool="skidl", value="KH-2.54PH180-1X20P-L11.5",
              description="1x20 2.54 male: the NHD-2.7-12864WDW3 plugs onto this",
              footprint=DISP_FP,
              pins=[Pin(num=k, name=v, func=P) for k, v in DISP_PINS.items()])
    for pin, net in DISP_PINS.items():
        nets[net] += j1[pin]

    sw2 = Part(name="PB-22E85", ref_prefix="SW", ref="SW2", tag="SW2",
               dest="NETLIST", tool="skidl", value="PB-22E85-S-5.7C-C-W",
               description="Legion self-locking push switch, 2P2T (LCSC C22462024): "
                           "the power button",
               footprint=PWR_FP,
               pins=[Pin(num=k, name=v, func=P) for k, v in PWR_PINS.items()])
    for pin, net in PWR_PINS.items():
        nets[net] += sw2[pin]

    j2 = Part(name="PinHeader_2x08", ref_prefix="J", ref="J2", tag="J2",
              dest="NETLIST", tool="skidl", value="PZ1.27-2x8P",
              description="1.27 mm 2x8 right-angle header (LCSC C22438114): the 16-way "
                          "ribbon to the Pi cap's J5, way for way",
              footprint=RIBBON_FP,
              pins=[Pin(num=k, name=v, func=P) for k, v in RIBBON_PINS.items()])
    for pin, net in RIBBON_PINS.items():
        nets[net] += j2[pin]

    for i, sig in enumerate(PULLED_UP):
        r = _r("R%d" % (i + 1), PULLUP, "%s pull-up" % sig)
        nets[sig] += r[1]
        nets["+3V3"] += r[2]

    # THE MODULE'S WHOLE SUPPLY IS PIN 2: logic, and the boost converter that makes the
    # panel's 15 V. Newhaven's table (datasheet p.6, default jumpers): 345 mA typical,
    # 375 mA maximum at 3.3 V with every pixel lit. A white-on-black screen lights a
    # fraction of them, but the copper here is sized for the table.
    c1 = _c("C1", "100nF", "3V3 decoupling at the display header's VDD pin")
    c2 = _c("C2", "10uF/25V", "3V3 bulk at the display's VDD pin: its boost converter "
            "draws up to 375 mA", pkg="Capacitor_SMD:C_0805_2012Metric")
    for c in (c1, c2):
        nets["+3V3"] += c[1]
        nets["GND"] += c[2]


# ---------------------------------------------------------------------------
# THE BOARD, placed from src/ui_panel.py's datums
# ---------------------------------------------------------------------------
BOARD_W, BOARD_L = UI.BOARD_W, UI.BOARD_L
_HW, _HL = BOARD_W / 2.0, BOARD_L / 2.0

# J1's pad row IS the module's header row: the module plugs straight down onto it, so
# placing this places the display. Rotated 90 so the row runs along X, which is the way
# the module's own row runs.
_J1_X, _J1_Y = UI.board_local(UI.ui_x(), UI.header_row_y())
# SW1's SHAFT sits under the knob, whose X is its own rule -- the same gap to the deck
# panel's +X seam that the Y layout gives it to everything else (user, 2026-09-28). It
# used to share the display's X centre, which left it equally spaced in Y and 45 mm from
# that seam in X.
# The placement names the pad centroid and the switch's terminals are not symmetric
# about its shaft, so the offset between the two is added here -- see
# ui_panel.enc_anchor_offset(), which reads it out of the footprint file.
_SW_BODY_X, _SW_BODY_Y = UI.board_local(UI.knob_x(), UI.y_layout()[1])
_ENC_OFF = UI.enc_anchor_offset()
_SW_X, _SW_Y = _SW_BODY_X + _ENC_OFF[0], _SW_BODY_Y + _ENC_OFF[1]

# J2: its shroud's mouth flush with the board's -X edge, facing -X.
# Rotated 180, so the body lies -X of the pad centroid.
# ⚠ THE PINS OVERHANG THE EDGE ON PURPOSE. The mating IDC socket is about 5.5 mm across
# its two rows and the rows stand ~1.4 and ~2.7 off the board, so a socket pushed on over
# laminate would have to go 0.7 mm INTO it. The header's plastic stops at the edge and its
# 4 mm of pin, and the socket on them, hang past it.
_J2_FAB_AHEAD = 2.135      # KiCad PinHeader_2x08_P1.27mm_Horizontal, from the PAD CENTROID:
_J2_FAB_BACK = 1.775       #   2.135 to the plastic's front face (the pins run 4.0 further),
_J2_FAB_HALF = 5.08        #   1.775 behind the rows; 5.08 either way along the rows
_J2_X = -_HW + _J2_FAB_AHEAD
# ...and its +Y end has to stay clear of the display module hanging over the board.
# The module's -Y edge, in board coordinates:
_MOD_EDGE_Y = UI.board_local(0.0, UI.module_centre()[1] - UI.MOD_L / 2.0)[1]
_J2_Y = -2.5
assert _J2_Y + _J2_FAB_HALF <= _MOD_EDGE_Y - 1.0, (
    "J2's shroud reaches y %+.2f and the display module's edge is at %+.2f -- the "
    "ribbon header would stand under the module"
    % (_J2_Y + _J2_FAB_HALF, _MOD_EDGE_Y))
assert _J2_Y - _J2_FAB_HALF >= -_HL + 1.0, (
    "J2's shroud reaches y %+.2f against a -Y edge at %+.2f" % (_J2_Y - _J2_FAB_HALF, -_HL))

# SW2, the power button: its cap's -X edge on the window's -X edge and its centre on the
# knob's Y (user's sketch, 2026-10-04) -- ui_panel.power_x() is the rule. The footprint is
# symmetric about its centre, so the placement IS the body's.
_PWR_X, _PWR_Y = UI.board_local(UI.power_x(), UI.y_layout()[1])
_PWR_HALF = 4.25
# ...and that X is what the cap's diameter was chosen for: the clamp plate under this
# board takes a relief round each through-hole part, and the web left between this one's
# and J2's has to be two beads.
assert (_PWR_X - _PWR_HALF) - (_J2_X + _J2_FAB_BACK) - 2 * UI.CLAMP_RELIEF \
    >= UI.D.MIN_WALL_2P - 1e-9, (
    "the power switch's body starts at x %+.2f and the ribbon header's ends at %+.2f: "
    "the clamp plate's web between their reliefs is under two beads"
    % (_PWR_X - _PWR_HALF, _J2_X + _J2_FAB_BACK))

# ONE M4, and it only holds Z: the two spigots that come down off the deck through the
# board into the clamp plate are what hold the station in X, Y and rotation. Central,
# because that is what a Z-only fastener wants.
_SCREW_X, _SCREW_Y = UI.SCREW_XY
_BOSS_D = 8.0              # the deck-side boss the screw threads into (cadkit M4)
_ENC_CRTYD = UI.ENC_SQ / 2.0 + 0.25

# The pull-ups run in a ROW along the top, not a column. A column of seven at 3 mm pitch
# is a picket fence across the middle of the board, and all seven switch nets have to
# cross it to reach J2 at the -X edge: the router left SW_PUSH 0.42 mm short on the far
# side of it. A row turns the same seven parts into a +3V3 rail with the pull-ups hanging
# off it and an empty lane underneath for the signals. It routed clean. The two
# decoupling parts sit beside J1's VDD pin, which is the one place on this board where
# position IS the value.
# ⚠ PIN 2, AT THE ROW'S -X END (manual quality pass, 2026-10-05). They stood at the +X end
# beside pin 18, which is /SHDN -- tied to +3V3, drawing nothing -- 40 mm of 0.25 mm track
# from the pin the module's whole 345 mA goes in at.
_R_Y = 10.0
_R_X0, _R_DX = -20.0, 4.0
assert _R_X0 + 6 * _R_DX + 0.5 <= _SW_BODY_X - _ENC_CRTYD - 1.0,     "the pull-up row laps the encoder"
assert _R_X0 - 0.5 >= _J2_X + _J2_FAB_BACK + 1.0,     "the pull-up row laps the ribbon header"

# EVERY HOLE IN THE BOARD HAS TO LAND ON BARE BOARD -- the M4 with its deck-side boss
# round it, and the two spigots with their own O4 posts. The spigots are the ones worth
# checking: they are placed for the widest rotation base the board allows, which pushes
# them toward the parts.
_HOLES = ([(UI.SCREW_XY[0], UI.SCREW_XY[1], _BOSS_D, "screw boss")]
          + [(x, y, UI.SPIGOT_D + 2.0, "spigot") for x, y in UI.SPIGOTS])
# ...and _rad, not _r: _r is the resistor helper above, and shadowing it here turned
# every pull-up into a TypeError halfway through the netlist.
for _hx, _hy, _d, _what in _HOLES:
    _rad = _d / 2.0
    assert (_hy + _rad <= _R_Y - 0.82 or _hx - _rad > _R_X0 + 6 * _R_DX + 0.5
            or _hx + _rad < _R_X0 - 0.5),         "the %s at (%+.1f, %+.1f) laps the pull-up row" % (_what, _hx, _hy)
    assert (abs(_hx - _SW_BODY_X) > _ENC_CRTYD + _rad
            or abs(_hy - _SW_BODY_Y) > _ENC_CRTYD + _rad),         "the %s at (%+.1f, %+.1f) laps the encoder" % (_what, _hx, _hy)
    assert _hx - _rad > _J2_X + _J2_FAB_BACK or abs(_hy - _J2_Y) > _J2_FAB_HALF + _rad,         "the %s at (%+.1f, %+.1f) laps the ribbon header" % (_what, _hx, _hy)
    assert (abs(_hx - _PWR_X) > _PWR_HALF + 0.25 + _rad
            or abs(_hy - _PWR_Y) > _PWR_HALF + 0.25 + _rad), \
        "the %s at (%+.1f, %+.1f) laps the power switch" % (_what, _hx, _hy)
    assert abs(_hy - _J1_Y) > 1.32 + _rad,         "the %s at (%+.1f, %+.1f) laps the display header" % (_what, _hx, _hy)

PLACEMENTS = {
    "J1": (round(_J1_X, 3), round(_J1_Y, 3), 90.0),
    "J2": (round(_J2_X, 3), round(_J2_Y, 3), 180.0),
    "SW1": (round(_SW_X, 3), round(_SW_Y, 3), 0.0),
    "SW2": (round(_PWR_X, 3), round(_PWR_Y, 3), 0.0),
    "C1": (-23.5, 10.5, 0.0),
    "C2": (-27.0, 10.5, 0.0),
}
for _i in range(7):
    PLACEMENTS["R%d" % (_i + 1)] = (round(_R_X0 + _i * _R_DX, 3), _R_Y, 0.0)

BOARD_NOTES = {
    "outline_mm": (BOARD_W, BOARD_L),
    "cutouts": ([{"xy": list(UI.SCREW_XY), "d": UI.SCREW_CLR_D}]
                + [{"xy": list(xy), "d": UI.SPIGOT_D + 2 * UI.SPIGOT_CLR}
                   for xy in UI.SPIGOTS]),
    "layers": 2,
    "thickness_mm": UI.BOARD_T,
    "placements": PLACEMENTS,
    # 0.375 A out on +3V3 and back on GND, and the module wants 3.0 V at its pin: 0.25 mm
    # the length of this board was 0.13 V there and back on its own
    "net_widths": {"+3V3": 0.40, "GND": 0.40},   # 0.50 left PWR_SW_DN no way past SW2
    "edge_escape": ("J2",),       # the ribbon header's edge-side row: layout._edge_row_escape
    # no via among the power switch's six lands: the first route put one 0.26 from a
    # terminal's hole, against the fab's 0.45 hole-to-hole
    "via_keepouts": [[round(_PWR_X - 4.0, 3), round(_PWR_Y - 4.2, 3),
                      round(_PWR_X + 4.0, 3), round(_PWR_Y + 4.2, 3)]],
    "quality": {
        # the display module's logic and its own boost converter, every pixel lit:
        # Newhaven's maximum (the note at C1). Pin 18 is /SHDN, a logic input.
        "power_paths": [{"net": "+3V3", "from": "J2.10", "to": ["J1.2"], "amps": 0.375}],
        # a switch's two throws, each shorted to GND or open: signal, not supply
        "not_power": ["PWR_SW_UP", "PWR_SW_DN"],
        "pinouts": {
            "J1": "Newhaven NHD-2.7-12864WDW3 datasheet p.4, Serial Interface pin table; "
                  "header pin n is module pin n",
            "J2": "way n is header pin n is IDC conductor n, both ends the same family "
                  "(HX PZ1.27-2xNP WZ); the order is harness.UI_RIBBON",
            "SW1": "Alps RKJXT1F42001 product drawing (terminal names A-D, 5-10) and "
                   "LCSC's symbol for C160841",
            "SW2": "Legion PB-22E85-S-5.7C-C-W drawing, P.C.B LAYOUT and SCHEMATIC: the "
                   "middle terminal of each row is its common. Which end is closed with "
                   "the button out is read off the schematic, NOT metered",
        },
        "waive": {"A2:J2": "J2 is where +3V3 arrives off the ribbon, not a load; the "
                           "bulk and the 100n are at the display header, which is"},
        # Signed 2026-10-05 against the routed board and the makers' sheets. M12 stays
        # open on purpose: what is left of it can only be done on the day of the order.
        "manual": {
            "M1": "two joints. J2 to the Pi cap's J5: the same footprint both ends "
                  "(PinHeader_2x08 P1.27 Horizontal, C22438114) and the same net on every "
                  "pad 1 to 16, read off this routed board (SW_A SW_B SW_C SW_D SW_PUSH "
                  "ENC_A ENC_B GND SCLK +3V3 SDIN DC CS_N RES_N PWR_SW_UP PWR_SW_DN) and "
                  "off the cap's (its own M1); the order is one constant, "
                  "harness.UI_RIBBON, asserted in both generators. A straight-through "
                  "16-way 1.27 mm IDC lead. The header has no shroud: pin 1 is marked in "
                  "silk and INSTALL_NOTES has the stripe-to-pin-1 step. J1 to the display "
                  "module: header pin n is module pin n (1 GND, 2 VDD, 4 D/C, 7 SCLK, 8 "
                  "SDIN, 16 /RES, 17 /CS, 18 /SHDN, 19 BS1, 20 BS0), Newhaven's table p.4; "
                  "the module sits in its deck pocket, so the row cannot go on reversed "
                  "or one pin along",
            "M3": "decision: no plane (the note at silk_labels says why). +3V3 and GND "
                  "are routed at the same 0.40 mm from J2 to J1 pins 2 and 1, each with "
                  "10.4 mm of 0.15 in J2's edge fan and one 0.6 / 0.3 via; the return "
                  "is as wide as the supply everywhere and necks nowhere the supply does "
                  "not. About 0.1 V there and back at 375 mA",
            "M4": "no regulator. C2 10 uF / 25 V 0805 (Samsung CL21A106KAYNNNE, C15850: "
                  "barely derated at 3.3 V) and C1 100 nF, 5.4 and 2.7 mm from J1's VDD "
                  "pin, for a module that carries its own boost converter and its own "
                  "capacitors",
            "M5": "+3V3: capacitors 25 V and 16 V or more, 0402 resistors 50 V, the module "
                  "3.0 to 3.5 V. J2's contacts are 1 A and J1's 3 A against 0.375 A. "
                  "Encoder and stick contacts: 10 mA at 5 V DC maximum (Alps), carrying "
                  "0.33 mA from a 10k pull-up to 3.3 V. Power switch: 12 V 0.3 A (Legion), "
                  "seeing the output board's 10 V zener (9.4 to 10.6 V) open and 2.55 mA "
                  "closed -- output_panel.py, at D8",
            "M9": "no MCU, nothing to program. Every net is on a through-hole pin of J1, "
                  "J2, SW1 or SW2, all open to a probe from the back of the board; "
                  "ground is on J1 pins 1, 5, 6, 10 to 14, 19 and 20",
            "M10": "decision: no clamp here. A hand reaches two things, both printed "
                   "plastic: the knob on the encoder's shaft and the power button's cap. "
                   "The encoder's metal frame is on GND through its lug (pin 10), so a "
                   "strike that gets past the knob lands on ground, not on a contact. "
                   "The ribbon is inside the instrument, to our own board; the 3.3 V it "
                   "brings is limited at the Pi cap. Nothing here can back-feed a rail",
            "M11": "elec/cad_geom_check.py ui_board, 2026-10-05: 13 of 13 routed parts "
                   "present in the CAD, the three cut-outs match (49.1 mm2), the switch "
                   "is on the deck's spacing rule and the cradle's posts stand on bare "
                   "board. The M4 hole and the two spigot holes are unplated with no "
                   "copper at them, and the generator asserts no part stands under the "
                   "deck boss or a spigot. The ribbon leaves over the -X edge with the "
                   "socket hanging past the laminate. All four through-hole parts have "
                   "LCSC codes; none is left for hand fitting",
            "M16": "decision: no added damping, and none is needed. The only supply is "
                   "3.3 V over the ribbon: about 0.4 uH and 0.34 ohm of AWG 30 pair "
                   "into 10 uF is a characteristic impedance of 0.2 ohm against 0.34 "
                   "ohm in series plus the cap's switch -- overdamped, no overshoot. The "
                   "source is a current-limited switch on the Pi cap",
            "M28": "Alps RKJXT1F42001 (C160841), Legion PB-22E85-S-5.7C-C-W (C22462024), "
                   "hanxia HX PZ1.27-2x8P WZ (C22438114), Kinghelm "
                   "KH-2.54PH180-1X20P-L11.5 (C2905493): each listing read 2026-10-05 and "
                   "each pinout above taken from that maker's own drawing. No transistor, "
                   "regulator or IC on the board",
            "M29": "two layers, 1.6 mm, 1 oz, inside JLCPCB's standard table (cadkit "
                   "quality FAB, capabilities page read 2026-10-04; A12 measured 15 "
                   "things against it). No pour on either layer, so every 0402 and the "
                   "0805 have a track on each pad and nothing to tombstone them",
            "M30": "JLCPCB's assembly capabilities page, read 2026-10-05: Economic PCBA "
                   "takes single-sided SMT and through-hole on 2 layers at 1.6 mm, a "
                   "single board from 10 x 10 mm, 0402 and larger. This board is 72 x "
                   "34, all parts on one face, nine 0402 / 0805 passives and four "
                   "through-hole parts. Standard PCBA starts at 70 x 70 and would need "
                   "rails. Seven BOM lines: three basic passives and four extended "
                   "parts. 'Confirm Production File' and 'Confirm Parts Placement' are "
                   "in the package's ORDER.txt",
            "M31": "'UI BOARD r1' and 'POWER' on the front, every designator at 1.0 mm. "
                   "J1's and J2's pin-1 marks are the footprints', outside the bodies. "
                   "Decision: no pin names at J2 or J1 -- sixteen ways at 1.27 mm and "
                   "twenty at 2.54 leave no room at a legible size, neither is wired by "
                   "hand, and the order is in harness.UI_RIBBON and Newhaven's table",
            "M32": "pitches read off the KiCad footprints: J2 1.27 x 1.27, J1 2.54. J2 is "
                   "the 0.635 mm-ribbon IDC family the Pi cap's J5 is (1 A a contact, "
                   "0.375 A on the one supply way and the one ground way); J1 is a "
                   "plain 2.54 header for the module's own row, 3 A. The ribbon carries "
                   "a ground with its single-ended signals (way 8, beside SCLK)",
            "M33": "one rail. +3V3: the display module, 345 mA typical and 375 mA maximum "
                   "with every pixel lit (Newhaven p.6, default jumpers), plus seven 10k "
                   "pull-ups at 0.33 mA each when closed. 0.375 A is declared, and every "
                   "contact and track here carries it (A1). The rail is the Pi's own "
                   "3.3 V through the Pi cap's limiter: that budget is the cap's M33",
            "M34": "the module wants 0.8 x VDD high and 0.2 x VDD low (Newhaven p.6): "
                   "2.64 V at 3.3. The Pi drives its 3.3 V rail into inputs that draw "
                   "microamps, and the module's own VDD is the same rail less the ribbon, "
                   "so the threshold falls with it. /RES and /CS are active low, D/C is "
                   "high for data: wired to nets of those names, driven by the Pi. /SHDN "
                   "is active low and tied high; BS1 = BS0 = 0 is 4-wire SPI (p.5). The "
                   "seven contacts close to ground against a pull-up: low is active",
            "M36": "no supply leaves this board: it is the far end of the ribbon",
            "M37": "elec/fab.py ui_board, 2026-10-05: zones refilled and DRC re-run by "
                   "finish.py, gerbers and drill written together by fab_package. Opened "
                   "outside KiCad: every layer rendered with pygerber 2.4.3 and looked "
                   "at, the Excellon file parsed separately and laid over both copper "
                   "layers -- 72 of 72 plated holes have copper all round them on each, "
                   "the one unplated hole is the encoder's peg, and paste is on the nine "
                   "surface-mount parts only. Stack-up and finish are in ORDER.txt",
            "M38": "the one ceramic over 0603 is C2, an 0805, 6.5 mm from the nearest "
                   "edge of a 72 x 34 board held by a screw and two spigots; routed "
                   "outline, no V-score, no tab. The M4 and both spigot holes are "
                   "unplated and isolated on purpose (they meet printed plastic). The "
                   "knob, the button and the display all face the player; the ribbon "
                   "plugs from the open -X edge",
            "M40": "10k, 100 nF and 10 uF are stock values. The encoder, the power "
                   "switch and both headers carry their part numbers as their values; "
                   "the generator says at each why it is that part (the header heights "
                   "and the switch's 12 V limit are the ones that must not change)",
            "M41": "decision, stated in the module docstring: the seven encoder and "
                   "stick contacts are debounced in the Pi's software, with no capacitor "
                   "across them (the contact is rated 10 mA and a capacitor's charge "
                   "would be spent through it at every make). None of them wakes or "
                   "resets anything. The power switch latches mechanically and is "
                   "filtered where it is read: R35 / C50, 1 ms, on the output board",
            "M42": "stock at JLCPCB on 2026-10-05: encoder 7,310, power switch 2,537, "
                   "ribbon header 2,050, display header 1,131, all three passives basic "
                   "parts in the millions. The display module is bought, not placed. "
                   "Single-maker parts: the Alps encoder has no drop-in alternate (the "
                   "footprint is its own); the switch and both headers are generic "
                   "outlines other makers fill. Three passive values, none odd",
        },
    },
    "ref_pos": {
        # past the row's +X end: under the row it printed on top of R3's own
        "J1": (round(_J1_X + 28.5, 3), round(_J1_Y, 3)),
        "J2": (round(_J2_X + 3.0, 3), round(_J2_Y - 6.4, 3)),
        "SW1": (round(_SW_X, 3), round(_SW_Y - 10.4, 3)),
        "SW2": (round(_PWR_X, 3), round(_PWR_Y - 5.8, 3)),
        "C1": (-23.5, 8.2), "C2": (-27.0, 8.2),
        **{"R%d" % (i + 1): (round(_R_X0 + i * _R_DX, 3), _R_Y + 1.6) for i in range(7)},
    },
    # NO GROUND POUR, and it was tried. A B.Cu pour is the obvious thing to want here --
    # the clock runs the length of the board from J2 to J1 and a plane under it is a
    # clean return. On two layers it cannot be had: leave B.Cu open to the router and it
    # lays signals across the pour, which came back as TWO GND islands and an unconnected
    # board; close B.Cu to the router and the only remaining layer has to carry five SPI
    # signals from the -X edge to a 20-way row that +3V3 already crosses. And the plane
    # would be perforated anyway, by twenty through-hole pins at 2.54 leaving 0.7 mm webs
    # straight across it. So GND is a routed net like every other one, which on a 72 mm
    # board with a metre of ribbon either side is what it was always going to be worth.
    "silk_labels": {"SW2": "POWER"},
    "mounting_hole_xy": UI.SCREW_XY,
    "single_sided": True,      # every part on the deck-facing face
    "qty_per_instrument": 1,
}


# -- the checks that would catch the station moving under this file ----------
def _check_against_cad():
    """Does everything still fit the board, and the board the deck?

    These are the numbers that would go wrong silently. The placements are derived from
    src/ui_panel.py, so moving the display moves them -- but nothing in that chain knows
    how big a connector is, and the first symptom of a part running off the edge is a
    DRC error on a board that has already been routed."""
    # 1. every part inside the outline with a 1.0 component-to-edge margin
    # (margin_x, margin_y): 1.0 of bare board everywhere EXCEPT J2's mouth, which is
    # flush with the -X edge on purpose -- a right-angle shroud that stops short of the
    # edge is a shroud the ribbon's strain relief fouls on the board.
    # (centre x, centre y, half-extent x, half-extent y, margin x, margin y). The
    # centre is the BODY's, which for SW1 is not its placement -- see _ENC_OFF.
    extents = {
        "J1": (_J1_X, _J1_Y, UI.HDR_PITCH * (UI.HDR_N - 1) / 2.0 + 1.32, 1.32, 1.0, 1.0),
        "SW1": (_SW_BODY_X, _SW_BODY_Y, UI.ENC_SQ / 2.0, UI.ENC_SQ / 2.0, 1.0, 1.0),
        "SW2": (_PWR_X, _PWR_Y, _PWR_HALF, _PWR_HALF, 1.0, 1.0),
        "J2": (_J2_X - (_J2_FAB_AHEAD - _J2_FAB_BACK) / 2.0, _J2_Y,
               (_J2_FAB_AHEAD + _J2_FAB_BACK) / 2.0, _J2_FAB_HALF, 0.0, 1.0),
    }
    for ref, (x, y, ex, ey, mx, my) in extents.items():
        assert abs(x) + ex <= _HW - mx + 1e-9, (
            "%s reaches x %+.2f on a %.1f board" % (ref, abs(x) + ex, BOARD_W))
        assert abs(y) + ey <= _HL - my + 1e-9, (
            "%s reaches y %+.2f on a %.1f board" % (ref, abs(y) + ey, BOARD_L))
    # 2. the board stays inside the display module's own X shadow, which is what keeps
    #    the station clear of the swappable band region at the bridge end
    from src import top_plate as TP
    bx, by = UI.board_centre()
    assert bx + _HW <= UI.ui_x() + UI.MOD_W / 2.0 + 1e-9 and \
        bx - _HW >= UI.ui_x() - UI.MOD_W / 2.0 - 1e-9, (
            "the UI board is wider than the display module it hides behind")
    assert UI.ui_x() + UI.MOD_W / 2.0 + UI.POCKET_CLR + UI.EDGE_WALL \
        <= TP.REGION_X1 + 1e-9, (
            "the display pocket's +X wall is inside the band region's seam")
    # 3. the board clears the -Y rail's inner face
    assert by - _HL >= TP.YL + 1.0, (
        "the UI board reaches y %.2f and the -Y rail's inner face is %.2f"
        % (by - _HL, TP.YL))
    # 4. the ribbon header fits under the deck
    gap = UI.z_stack()[1] - UI.z_stack()[4]          # deck underside - board top
    assert gap >= RIBBON_H + 1.0, (
        "the right-angle ribbon header stands %.1f and there is %.2f under the deck"
        % (RIBBON_H, gap))


# The right-angle box header's height above the board. ESTIMATED, not read: the KiCad
# footprint carries no Z and ZHOURI publish no drawing through LCSC. 10.0 is a standard
# 2.54 shrouded right-angle body with room to spare, and the clearance assertion below
# is written against it. CONFIRM IT AGAINST THE PART BEFORE THE DECK IS PRINTED -- the
# deck's underside is 11.74 above the board and that is all the room there is.
RIBBON_H = 10.0

_check_against_cad()


if __name__ == "__main__":
    ui_board(tag="ui")
    ERC()
    generate_netlist(file_=os.path.join(OUT_DIR, "ui_board.net"))
    netcheck.grounds_meet(os.path.join(OUT_DIR, "ui_board.net"))
    netcheck.no_orphan_pins(os.path.join(OUT_DIR, "ui_board.net"))
    with open(os.path.join(OUT_DIR, "ui_board.board.json"), "w") as f:
        json.dump(BOARD_NOTES, f, indent=2)
    print("board %.1f x %.1f at world (%.2f, %.2f), display header row y %.2f"
          % (BOARD_W, BOARD_L, UI.board_centre()[0], UI.board_centre()[1],
             UI.header_row_y()))
