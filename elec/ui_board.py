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
RIBBON_FP = "Connector_IDC:IDC-Header_2x07_P2.54mm_Horizontal"

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
RIBBON_PINS = {
    1: "SW_A", 2: "SW_B", 3: "SW_C", 4: "SW_D", 5: "SW_PUSH", 6: "ENC_A",
    7: "ENC_B", 8: "GND", 9: "SCLK", 10: "+3V3", 11: "SDIN", 12: "DC",
    13: "CS_N", 14: "RES_N",
}

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


# THE RIBBON'S SHAPE IS THE CAD'S AND THE NETLIST'S BOTH. src/ui_panel.py draws fourteen
# conductors at 1.27; this is the connector they come off. If a way is ever added here,
# the drawing has to follow or it is fourteen conductors on a sixteen-way plug.
assert len(RIBBON_PINS) == UI.RIBBON_N, (
    "J2 has %d ways and the CAD draws a %d-way ribbon"
    % (len(RIBBON_PINS), UI.RIBBON_N))
assert abs(UI.RIBBON_PITCH * 2 - 2.54) < 1e-9, (
    "the ribbon's %.2f pitch is not half the header's 2.54" % UI.RIBBON_PITCH)


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
                                "SW_A", "SW_B", "SW_C", "SW_D")}
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

    j2 = Part(name="DC3-2.54-14P", ref_prefix="J", ref="J2", tag="J2",
              dest="NETLIST", tool="skidl", value="DC3-2.54-14PAL",
              description="2x7 right-angle IDC: the 14-way ribbon to the Pi's GPIO",
              footprint=RIBBON_FP,
              pins=[Pin(num=k, name=v, func=P) for k, v in RIBBON_PINS.items()])
    for pin, net in RIBBON_PINS.items():
        nets[net] += j2[pin]

    for i, sig in enumerate(PULLED_UP):
        r = _r("R%d" % (i + 1), PULLUP, "%s pull-up" % sig)
        nets[sig] += r[1]
        nets["+3V3"] += r[2]

    c1 = _c("C1", "100n", "3V3 decoupling at the display header")
    c2 = _c("C2", "10u", "3V3 bulk: the module's boost converter pulls ~100 mA",
            pkg="Capacitor_SMD:C_0805_2012Metric")
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
_J2_FAB_AHEAD = 12.06      # KiCad IDC-Header_2x07..Horizontal, measured from the PAD
_J2_FAB_BACK = 1.64        #   CENTROID: the shroud reaches 12.06 toward its mouth and
_J2_FAB_HALF = 12.77       #   1.64 behind the rows; 12.77 either way along the rows
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
# decoupling parts sit beside J1's +X VDD pin (18), which is the one place on this board
# where position IS the value.
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
    assert abs(_hy - _J1_Y) > 1.32 + _rad,         "the %s at (%+.1f, %+.1f) laps the display header" % (_what, _hx, _hy)

PLACEMENTS = {
    "J1": (round(_J1_X, 3), round(_J1_Y, 3), 90.0),
    "J2": (round(_J2_X, 3), round(_J2_Y, 3), 180.0),
    "SW1": (round(_SW_X, 3), round(_SW_Y, 3), 0.0),
    "C1": (19.0, 10.5, 0.0),
    "C2": (24.5, 10.5, 0.0),
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
    "ref_pos": {
        "J1": (round(_J1_X - 12.0, 3), round(_J1_Y - 2.8, 3)),
        "J2": (round(_J2_X - 2.0, 3), round(_J2_Y - 14.2, 3)),
        "SW1": (round(_SW_X, 3), round(_SW_Y - 10.4, 3)),
        "C1": (19.0, 8.2), "C2": (24.5, 8.2),
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
