"""Wire harness: gauge-colored round cables, modeled as cylinder chains.

STRATEGY (July 2026, BOM 'Connectors' section): solder only on PCBs, every
field connection a connector, never inline-splice. Both CAN buses are
TRUNK-AND-DROP over TEE PCBs (electronics.tee_pcb, flat on the floor):
crimped XH jumper SEGMENTS run tee-to-tee (each drawn as its own component,
suffix _N — a segment IS a separate physical cable), and each device hangs
by ONE drop, so unplugging a device never breaks a bus. 120 Ω termination
lives on the boards (motor_ctrl's is permanent; bus A's LAST tee has its switch ON).

  bus A (motors): motor_ctrl -> tee 9..0 (one per motor; LAST = tee 0,
        easternmost — its jumper is closed). Drop = the SERVO42D's own
        6-pin XH pigtail (motor_pigtail_N, grey). The 24 V pair rides the
        same tees and is fed from BOTH ends of the chain: the motor
        controller's J1 at the west one (with CAN), the output board's J7
        at the east one (24 V only).
  EVERY LEAD'S CONDUCTORS COME FROM elec/harness.py (2026-10-06): CONN maps a
  connector to its way tuple, conn_end() reads each way's position off the ROUTED
  board, and check_cables() fails the build if a cable is drawn with a different
  number of conductors than its tuple wires, or a conductor ends off its own way.
  A way the tuple calls NC draws nothing.

  bus B (inputs): motor_ctrl -> the lever/pedal boards, WITH NO TEES AT ALL
        (user, 2026-09-14). Tees 11 and 12 are deleted: 11 existed to tap
        the trunk at the knee station, which the lever board's own 8-way
        pass-through (in 1-4, out 5-8) now does on the board, and 12
        existed to land the chassis TRRS jack's factory cable, which the
        TRRS ADAPTER BOARD now does with the jack soldered on. Both were
        junctions that only existed because the thing either side of them
        could not terminate itself; both ends can now.

One component per physical CABLE. Discrete wires (the 24 V pair) are drawn
individually; jacketed/bundled runs at the bundle OD. Colors (build.py):
HUE = gauge bucket, SHADE = the specific wire within the bucket:

  CAN BUS COLOURS (user override): the CAN + power trunk is shown as its four
  colour-coded conductors, NOT the gauge/shade rule below:
      BLACK  = wire_pwr_gnd  (CAN ground / 0 V return)
      RED    = wire_pwr_hot  (CAN 24 V)
      YELLOW = wire_can*h    (CAN-H, both buses + the transceiver jumper)
      GREEN  = wire_can*l    (CAN-L)
  Each CAN bus is drawn as its CAN-H/CAN-L pair (split ±CAN_OFF): bus A
  (wire_canh/l, motors) and bus B (wire_canbh/l, inputs), both leaving the motor
  controller's own connectors. There is no transceiver jumper any more -- the
  transceivers sit on the MCU's board, so that harness became copper.

  The gauge/shade rule still governs the NON-CAN nets:
  BLUE = power pair       (superseded for the CAN power rails above)
  AMBER = 28 AWG logic    (light -> dark) wire_link (motor controller <-> Pi),
                          wire_ui (the UI board's 14-way ribbon, ONE flat prism)
  VIOLET = shielded USB-2 wire_usb: USB-C panel -> Pi 4
  GREY = factory jackets  motor_pigtail_N

Analog architecture: NONE OF IT IS HERE. The AFE board is deleted and no audio
crosses this harness -- the optical pickup board carries the magnetic pickup's
buffer, its bypass relay and the jack output, and reaches the Pi over USB. What
runs through the bay is DC bus, CAN, and logic.

Routing: a 6-lane floor trunk at z -69.7 (under the motors) passes every
cross-rib through SHALLOW gable raceways (chassis._raceway) whose floor stays
0.4 clear of the knee-lever rib-mortise tip (-71.42) -- the harness never
blocks a floating tenon sliding to ANY knee depth. Trunk segments still ride
those lanes rib-to-rib; they dip to z -72.6 (between ribs, clear of the
mortise plane) to land on their tee headers. Wire ends clip ~1-2 mm into
their declared source/destination bodies to show the connection
(whitelisted); everywhere else the gate enforces clearance.

The SERVO42D driver is ON the motor, so there are NO stepper phase leads --
the harness is DC bus, CAN and logic only. Insulation is not
an EMI defence: noise immunity comes from SHIELDING (audio), TWISTING
(power, CAN) and buffering at the source (the AFE at the bridge).
"""

from __future__ import annotations

import math

import cadquery as cq

from . import dimensions as D
from elec import harness as EH            # the PCB's pin order, single-sourced
from . import electronics as EL
from . import board_geom as BG
from . import ui_panel as UI
from . import knee_lever as _KL   # the keeper barrel the lever slack winds on
from .helpers import oct_cable
from cadkit.cables import bundle_paths, flat_cable, flat_bends

# modeled cable OD per net (mm): jacketed bundles (shielded/USB) drawn as ONE
# round conductor at the jacket OD; the 24 V pair AND the CAN pairs as discrete
# conductors (user override: the CAN bus is shown as its four colour-coded
# wires -- black gnd, red 24 V, yellow CAN-H, green CAN-L). Nothing exceeds 2.6.
WIRE_OD = {
    "wire_usb": 2.6,
    # single-core SHIELDED instrument cable, jacket OD: centre conductor = PICKUP_HOT,
    # braid = the return, which is why it is one cable at bundle OD and not two wires.
    # Both ends are BARE TINNED LEADS -- the panel end lands in J8's screw terminals and
    # the pickup end is whatever the pickup shipped with. No connector at either end, so
    # there is no plug body to model.
    "wire_pickup": 2.4,
    # CAN signal pairs, split into CAN-H / CAN-L discrete conductors
    "wire_canh": 1.3, "wire_canl": 1.3,       # bus A (motors)
    "wire_canbh": 1.3, "wire_canbl": 1.3,     # bus B (inputs)

    "wire_pwr_hot": 1.8, "wire_pwr_gnd": 1.8,
    # 5 V to the Pi's GPIO header. 20 AWG PAIR, not signal wire: the Pi's
    # undervoltage trip is 4.63 V against a 5.00 nominal, so the whole budget is
    # 0.37 V and the cable may not eat it. Over this run 20 AWG spends 0.03.
    "wire_5v": 1.8,
    # the 24 V link's four power conductors, and its two power-button throws: signal wire,
    # a few milliamps into a pull-up
    "wire_plink": 1.8, "wire_plink_sw": 1.3,
    # the lights' feed and the same two throws going on to the cap: under an amp of LEDs
    "wire_lights": 1.3,
    # the optical board's 24 V feed: 26 AWG, a couple of hundred milliamps over 150 mm
    "wire_opt": 1.3,
    "wire_link": 1.4,
    # THE UI'S RIBBON IS NOT A DIAMETER AT ALL, and this entry only exists because
    # the gate's colour and allow-list tables are keyed off the same names. It is drawn
    # by flat_cable from RIBBON_W x RIBBON_T; 0.9 is its thickness.
    "wire_ui": UI.RIBBON_T,
    "motor_pigtail": 3.4,
}
# (_KNEE_B is gone with the two-conductor bus-B head it served -- a landing 20 mm short
#  of LKL's board, waiting on a chassis follow-up. That follow-up is the wiring port, and
#  ctrl_bus_b now runs all four conductors onto the board's own ways. See bus B below.)
CAN_OFF = 0.7         # CAN-H / CAN-L conductor separation (both x and y, same
                      # scheme as PWR_OFF): the split pair stays inside the old
                      # single-jacket envelope (0.7 + 0.65 = 1.35 < the 2.4/2 it
                      # replaces) so the trunk footprint is unchanged.
# ⚠ THE TEE-TO-TEE TRUNK IS ONE 4-WAY CABLE, AND ITS FOUR CONDUCTORS WERE ON ONE LINE 0.3 mm
# APART. The hops drew CAN at +-CAN_OFF (0.7) and 24 V at +-PWR_OFF (1.0), both along the same
# diagonal, so CAN-H ran through 24 V hot and CAN-L through ground on every hop -- 18 pairs,
# ~80 mm3 each over 45.8 mm, never reported (the gate allow-lists wire against wire). Spread
# as a flat set at 1.8, which clears the fattest neighbours (O1.8 beside O1.3 needs 1.55):
# ...IN THE CONNECTOR'S OWN PIN ORDER (GND, 24 V, CAN-H, CAN-L on 1-4 / 5-8 -- can_tee J1),
# so each conductor runs from its own pin to its own lane without crossing a neighbour.
# (2026-10-01: all four runs share one height now -- see TRUNK_Z_RUN -- so the two O1.8
#  power conductors need 2.0 between them, not 1.8, which had them tangent. Same 5.4 span.)
TRUNK_OFF = {"gnd": -2.8, "hot": -0.8, "canh": 1.0, "canl": 2.6}
# ...and each LANDS on its own pin. All of them used to end on the 8-way's centre, so the
# cables arriving at a tee and leaving it ran through each other for 10-20 mm (nine pairs in
# check_cable_pairs, the worst 9.5 mm3). In on 1-4 from the WEST, out on 5-8 to the EAST.
# ...and the ORDER IS THE PCB's, READ FROM elec.harness, not retyped here. That module
# was written because this one constant existed in three places with nothing comparing
# them, and its warning is exact: a wrong pin order is invisible until it puts a rail
# into a signal, because each board stays internally consistent with its own copy. This
# was a FOURTH copy -- the CAD's -- and the one place the EDA side could not see.
_CAD_NAME = {"GND": "gnd", "V24": "hot", "CAN_H": "canh", "CAN_L": "canl"}
TRUNK_PIN = {_CAD_NAME[n]: i + 1 for i, n in enumerate(EH.XH_PINOUT)}
assert set(TRUNK_PIN) == set(TRUNK_OFF), (
    "elec.harness.XH_PINOUT names a circuit this trunk has no lane for: %s"
    % (set(TRUNK_PIN) ^ set(TRUNK_OFF)))
# ...and the four have to CROSS once per hop. With the same pin order at both ends, the
# flat set that leaves one connector without crossing arrives at the next in the wrong
# order -- a crimped harness does exactly that, one wire lying over the next.
#
# ⚠ TWO LEVELS, NOT FOUR, AND NOTHING ABOVE THE PLUG (user, 2026-10-01: the plugs on the
# tee boards are the real +Z extent of the harness, -19.65). This used to give every
# conductor its own height (-0.8, 1.2, 3.2, 5.2 off the mouth), which stood CAN-L 2.5 mm
# above the housing it leaves; a harness cannot do that, and the fret board's retainer
# strip was being designed round a wire that is not there.
#   RUN   every X run, and the leg out of the hop's WEST connector, lie side by side on
#         their lanes at one height -- that end needs no crossing (the west-most pin
#         takes the far lane);
#   OVER  at the EAST connector each conductor rises at the end of its own lane and
#         crosses the others' runs one level up, in to its pin.
# 2.0 between the levels clears the fattest pair (O1.8 over O1.8). RUN is 0.8 under the
# mouth, no lower: the bays' side walls stand to -25.45 (SEAT_TOP).
# (-0.6 / 1.4 since the ways are read from the routed board: the contact line is 0.45 lower
#  than the hand-counted one was, and RUN came up by as much as keeps it off the bay walls.)
TRUNK_Z_RUN, TRUNK_Z_OVER = -0.6, 1.4
_XH_PITCH = 2.5
PWR_OFF = 1.0         # 24 V hot/gnd separation. In X on the bank hops (see _seg) and in Z
                      # along the -Y corridor, where the pair rides one lane each. 2.0 apart
                      # leaves 0.2 of air between two O1.8 conductors, which is right for a
                      # pair that is BIFILAR on purpose -- they are meant to stay together.
                      # (Was 1.2 in both x and y. The y half is what had to go: 2.4 across a
                      # corridor only 3.2 deep behind the channel's straps put one conductor
                      # in a strap.)
WIRE_D = 2.0          # default (shielded-pair size)
# straight run a conductor makes out of a JST mouth before it may bend, so the
# pin order is legible in the model instead of a bundle meeting a connector face
CAP_LEAD_IN = 4.0

# ── -Y RAIL harness corridor ──────────────────────────────────────────────
# The ribs are STRUCTURE + lever mounts ONLY: a knee/pedal lever slides along its rib
# mortise to ANY depth in ANY bay, so a cable sitting in a rib would block a lever from
# being installed there. So NO wire crosses a rib. The whole X-running trunk instead
# hugs the -Y rail's INNER FACE, ABOVE the rib tops (z > FLOOR_TOP -65.15) where no rib
# reaches and -- except the +X-most motor (m9) -- no motor body reaches either. The tees
# mount on the rail (each on a pcb_cradle); every motor's drop pigtail reaches from its
# -Y-facing PCB out to its tee. Past m9 the rail is notched (chassis motor-9 cable cut).
from .chassis import Y_LO as _Y_LO, T as _RAIL_T
from .chassis import WT_LANE_Y as CH_WT_LANE_Y, WT_ZF as CH_WT_ZF, WT_H as CH_WT_H
from .chassis import WT_X1 as CH_WT_X1, WT_RUNS as CH_WT_RUNS
from . import motor_bank as MB                          # back_y: where each motor's pigtail leaves
from .motor_bank import FLOOR_TOP as _RIB_TOP           # -65.15 (rib tops = above = rib-free)
RAIL_INNER_Y = _Y_LO + _RAIL_T / 2                       # -131.55: -Y rail inner face
# the old floor-level corridor, which only bus B still uses at the keyhead. Held where it was
# (-124.25) when the body widened for string 10's pigtail (chassis.RAIL_GAP): nothing on it
# wanted to move, and following the wall out put bus B across the Pi link's riser.
from .chassis import RAIL_GAP as _RAIL_GAP
RAIL_Y = RAIL_INNER_Y + 4.5 + (_RAIL_GAP - 2.0)
TEE_Y  = RAIL_INNER_Y + 8.0                              # tee-board centre (14mm-deep board clears wall)
# ── THE -Y CORRIDOR IS THE WIRING TROUGH NOW (chassis.WT_*), ABOVE THE MOTORS ──────────
# It used to be a pocket cut into the rail below the motor tops; the user moved it OUT of
# the wall and UP (the wall is the body's side beam). Everything that runs the length of
# the instrument rides it, stacked in Z inside a 4.8 mm-wide space, at one y (CHAN_Y):
# ⚠ THE STACK STARTS 1.5 OFF THE FLOOR, NOT ON IT. Where the trough is left out -- over
# string 10's motor -- the cables carry on at the same height, and two chassis walls either
# side of that motor stand to -25.45: a lane on the floor (-26.4) clipped both. From there
# up the stack is packed flat-to-flat (the octagons are rolled so their flats face up and
# down), and still finishes under the lip's top at -13.6.
# THE 24 V LINK (output_panel J10 -> motor_ctrl J3) is the trough's lowest cable and its
# biggest: six conductors, two across and three high (see build_wires), 0.15 off the floor.
# It was a pair at -22.9 until all six ways were drawn (2026-10-06).
PLINK_COL, PLINK_ROW = 1.0, 1.75        # half the pair's spacing; row to row
PLINK_HALF = PLINK_ROW + 1.8 / 2        # 2.65 from its centre to its top or bottom
LANE_PWR2  = CH_WT_ZF + 0.15 + PLINK_HALF       # -23.6: its centre
LANE_USB   = CH_WT_ZF + 7.1      # -19.3: output board J2 -> the Pi (O2.6)
LANE_PWR   = CH_WT_ZF + 10.8     # -15.6: the 24 V head (J7 -> the east tee), hot -16.6 /
                                 #        gnd -14.6 -- first trough piece only, it leaves
                                 #        at string 10's motor for that motor's tee
LANE_CTRL  = -42.0               # CAN bus B: keyhead-local, on the old floor corridor
LANE_CAN   = -48.0               # CAN bus A: bank hops only (never on the corridor)
TEE_Z = _RIB_TOP + 4 * D.BEAD                            # 3.2 of printed cradle on the rib tops
_TRUNK_OD = max(od for nm, od in WIRE_OD.items() if nm != 'motor_pigtail')
# the trough's own guarantees, asserted where the lanes are chosen:
_TOP_OF_MOTORS = D.MOTOR_BELT_Z + D.MOTOR_SQ / 2          # -29.05
assert CH_WT_ZF > _TOP_OF_MOTORS, "the trough's floor has come down to the motor tops"
assert LANE_PWR2 - PLINK_HALF > CH_WT_ZF, "the 24 V link is in the trough's floor"
assert LANE_PWR2 + PLINK_HALF < LANE_USB - 2.6 / 2, (
    "the 24 V link stands into the USB lead's lane in the trough")
assert LANE_PWR + PWR_OFF + 1.8 / 2 < CH_WT_ZF + CH_WT_H, "the head stands over the lip"
assert CH_WT_LANE_Y + _TRUNK_OD / 2 <= MB.HARNESS_Y1, (
    "the trough's lane reaches y %.2f, past motor_bank's HARNESS_Y1 %.2f"
    % (CH_WT_LANE_Y + _TRUNK_OD / 2, MB.HARNESS_Y1))
HDR_Z = -54.0                                            # lifted tee header top (wire entry z)

CHAN_Y = CH_WT_LANE_Y                    # inside the trough


def _rail_pts(x0, x1, z):
    """Points riding the -Y corridor -- the trough -- from x0 to x1 at height z.

    ONE straight line now. The pocket this replaced broke at every split plane (it could not
    cut through the seam joint) and the cables stepped out and back each time; a trough
    standing off the wall has nothing to dodge, and where it is left out -- over string 10's
    motor, and a hair at each seam -- the cables carry on at the same line, above the motor."""
    return [(x0, CHAN_Y, z), (x1, CHAN_Y, z)]


def _wire(pts, d=WIRE_D):
    """Polyline cable, OCTAGONAL section, across-flats d -- see helpers.oct_cable.

    It was cylinders with sphere elbows, fused first as a chain of pairwise unions (which
    silently dropped cable: 1100 mm3 of one feed gone, no exception), then as one
    multi-fuse checked by volume, then with a sphere-free fallback when the spheres broke
    every tolerance. The user's call (2026-09-21) was to stop fighting round geometry: flat
    faces fuse reliably and check fast, and across-flats = the cable's diameter keeps the
    real cable inside the model."""
    return oct_cable(pts, d)


# ── EVERY LEAD AGAINST ITS HARNESS TUPLE (lead + user, 2026-10-06) ───────────────────────
# The lead's audit measured every drawn conductor end against the way its net belongs on and
# found 4 of 51 connectors right: cables on ways that carry something else, a 6-way drawn as
# a pair, a link not drawn at all, ends in air beside a row. None of it overlapped anything,
# so no gate had an opinion. So the drawing now declares each CABLE -- which connector at
# each end, which ways -- and check_cables() fails the build unless, for every one:
#   * a conductor is drawn for every way the harness tuple wires, and none for an NC way;
#   * each conductor joins the SAME net at both ends (way n to way n: every lead is straight);
#   * each end sits on its own way's contact line, where the routed board has that pad;
#   * and leaves along the connector's own exit direction, not through its body.
# The way's place and direction come from electronics.way_pt / way_out (the routed pads
# through the call that places the board); the net on each way comes from elec/harness.py.
CONN = {
    ("motor_ctrl", "J1"): EH.XH_PINOUT,
    ("motor_ctrl", "J2"): EH.PH_PINOUT,
    ("motor_ctrl", "J3"): EH.PWR_LINK,
    ("motor_ctrl", "J5"): EH.PI_5V_LINK,
    ("motor_ctrl", "J6"): EH.PH_PINOUT,
    ("motor_ctrl", "J7"): EH.LIGHTS_LINK,
    ("pi_cap", "J2"): EH.PI_5V_LINK,
    ("pi_cap", "J4"): EH.LIGHTS_LINK,
    ("output_panel", "J7"): ("GND", "V24", EH.NC, EH.NC),
    ("output_panel", "J9"): ("GND", "V24"),
    ("output_panel", "J10"): EH.PWR_LINK,
    ("can_tee", "J1"): tuple(n.rsplit("_", 1)[0] for n in EH.xh_trunk_pins()),
    ("can_tee", "J2"): EH.XH_PINOUT,
}
_CABLES = {}        # cable -> {"a": [(pt, out, net)], "b": [...], "drawn": {k: name}}
PATHS = {}          # conductor name -> (points, diameter): every lead as it was drawn


def conn_end(board, ref, ways=None, at=(0.0, 0.0, 0.0)):
    """One END of a cable: [(point, exit direction, net)] for `ways` of a board connector
    (all of them by default), in way order. `at` moves a board that is placed more than
    once (a tee)."""
    names = CONN[(board, ref)]
    ways = range(1, len(names) + 1) if ways is None else ways
    d = EL.way_out(board, ref)
    return [(EL.way_pt(board, ref, n, at), d, names[n - 1]) for n in ways]


def _cable(key, a, b):
    """Declare cable `key` between two ends (conn_end lists, or the same shape built by
    hand for a connector another module owns). Conductor k joins a[k] to b[k]."""
    assert len(a) == len(b), "%s: %d ways at one end, %d at the other" % (key, len(a), len(b))
    for k, (ea, eb) in enumerate(zip(a, b)):
        assert ea[2] == eb[2], ("%s: conductor %d would join %s to %s -- the harness has "
                                "every lead straight" % (key, k, ea[2], eb[2]))
    _CABLES[key] = {"a": a, "b": b, "drawn": {}}
    return [k for k, e in enumerate(a) if e[2] != EH.NC]


def _run(out, name, pts, d, cable=None, k=None):
    """Draw one conductor and remember its path; `cable`, `k` say which way pair it is."""
    pts = [tuple(float(v) for v in q) for q in pts]
    PATHS[name] = (pts, d)
    if cable is not None:
        assert k not in _CABLES[cable]["drawn"], "%s: conductor %d drawn twice" % (cable, k)
        _CABLES[cable]["drawn"][k] = name
    out.append((name, _wire(pts, d)))


_END_TOL = 0.05         # mm off the way's contact line
_DIR_TOL = 0.999        # cosine: under 2.6 degrees off the connector's exit direction


def check_cables(keys=None):
    """Raise AssertionError listing every drawn cable that disagrees with its harness
    tuple. Called at the end of each function that draws cables, with what it declared."""
    bad = []
    for key in (sorted(_CABLES) if keys is None else keys):
        c = _CABLES[key]
        want = {k for k, e in enumerate(c["a"]) if e[2] != EH.NC}
        got = set(c["drawn"])
        if got != want:
            bad.append("%s: %d conductor(s) drawn, the harness wires %d (%s)"
                       % (key, len(got), len(want),
                          ", ".join(c["a"][k][2] for k in sorted(want ^ got))))
        for k in sorted(got & want):
            name = c["drawn"][k]
            pts = PATHS[name][0]
            for end, p, q in ((c["a"][k], pts[0], pts[1]), (c["b"][k], pts[-1], pts[-2])):
                w, d, net = end
                if d is None:           # an end another module owns and hands over as a point
                    d = [q[m] - p[m] for m in range(3)]
                    n_ = math.sqrt(sum(x * x for x in d)) or 1.0
                    d = [x / n_ for x in d]
                # distance of the conductor's end from the way's LINE (through w along d)
                v = [p[m] - w[m] for m in range(3)]
                al = sum(v[m] * d[m] for m in range(3))
                off = math.sqrt(max(0.0, sum(x * x for x in v) - al * al))
                if off > _END_TOL:
                    bad.append("%s %s (%s): ends %.2f mm off its way" % (key, name, net, off))
                s = [q[m] - p[m] for m in range(3)]
                n = math.sqrt(sum(x * x for x in s))
                if n < 1e-6 or sum(s[m] * d[m] for m in range(3)) / n < _DIR_TOL:
                    bad.append("%s %s (%s): does not leave along the connector's exit"
                               % (key, name, net))
    assert not bad, "cables that disagree with elec/harness.py:\n  " + "\n  ".join(bad)


def optical_feed():
    """[(name, solid)]: the optical board's 24 V feed, output_panel J9 -> optical J2.

    TWO CONDUCTORS, ON WAYS 1 AND 2. The link went two-wire by population (J9 is a 2-way;
    the optical board's J2 is a 4-way with ways 3 and 4 not connected) and was still drawn
    as the one O4.0 solid of the six-way it had been, centred on the 4-way: 2.5 mm to one
    side of the two ways that carry anything, and in one colour for a ground and a supply.

    A FLAT PAIR AT THE CONNECTORS' OWN PITCH, end to end. Both ends are XH, 2.5 mm, so the
    two conductors leave one housing 2.5 apart and arrive at the other 2.5 apart with no
    fan at either; and 2.5 + a conductor is 3.8 across, inside the O4.0 the route was
    planned in (optical_pickup.opt_cables owns that route -- the conduit, the slot in the
    endplate, the rise over J7's pair -- and this follows it, only moved onto the ways).
    """
    from . import optical_pickup as OP
    old = OP.opt_cables("pwr_path")
    dx, dy = OP._silk_to_world()
    dz = OP.PCB_TOP - BG.BOARDS.load("optical")["thickness_mm"]
    names = CONN[("output_panel", "J9")]
    out_a = tuple(float(v) for v in BG.BOARDS.way_dir("optical", "J2"))
    ways = [BG.BOARDS.way("optical", "J2", n) for n in (1, 2)]
    # each conductor starts on its own way's line, at the BACK of the plug as it is drawn
    a = [((w[0] + dx, old[0][1], w[2] + dz), out_a, names[k]) for k, w in enumerate(ways)]
    b = conn_end("output_panel", "J9")
    ac = tuple((a[0][0][m] + a[1][0][m]) / 2.0 for m in range(3))
    bc = tuple((b[0][0][m] + b[1][0][m]) / 2.0 for m in range(3))
    # the old centre line with its two ends moved onto the ways: the plug end sideways and
    # down to the contacts' level, the J9 end onto the row
    mid = [(q[0], q[1], q[2]) for q in old[2:-3]]
    centre = ([ac, (ac[0], old[1][1], ac[2]), (mid[0][0], old[1][1], ac[2])] + mid[1:]
              + [(bc[0], old[-3][1], old[-3][2]), (bc[0], bc[1], old[-3][2]), bc])
    half = (a[1][0][0] - a[0][0][0]) / 2.0
    legs = bundle_paths(centre, [(0.0, -half), (0.0, half)], across=(1.0, 0.0, 0.0))
    out = []
    for k in _cable("optical feed", a, b):
        for end, pin in ((legs[k][0], a[k][0]), (legs[k][-1], b[k][0])):
            assert max(abs(end[m] - pin[m]) for m in range(3)) < 0.05, (
                "the optical feed's pair has turned over on the way: %r against way %d at %r"
                % (end, k + 1, pin))
        _run(out, "wire_opt_%s_%d" % (_NET_SHORT[names[k]], k + 1), legs[k],
             WIRE_OD["wire_opt"], "optical feed", k)
    check_cables(["optical feed"])
    return out


_NET_SHORT = {"GND": "gnd", "V24": "v24", "V5": "v5", "PWR_SW_UP": "up", "PWR_SW_DN": "dn"}


# ── tee stations (all on the -Y rail corridor) ────────────────────────────
def _motor_back(i):
    return MB.back_y(i)                      # -Y-most face of motor i (PCB back)


def tee_stations():
    """[(x, y, drop_sign)] tee-PCB anchors, all on the -Y rail (TEE_Y) so the CAN trunk
    stays on the rail and never crosses a rib. 0..9 bus A, ONE PER MOTOR AND NOTHING
    ELSE -- a tee board exists to give a motor power and CAN, so a tee that serves no
    motor has no reason to be a board (user, 2026-09-18). Tee 10 used to sit here as the
    optical pickup board's 24 V drop; that board is fed from the output panel's J9 and
    has no CAN at all, so the drop was feeding a board fed from somewhere else.
    THERE ARE NO BUS-B TEES either -- 11 (knee) and 12 (leg-socket) are deleted; see the
    module docstring. The two +X-most motors (8,9) reach the rail, so a tee
    dead-behind them would sit inside the motor -- their tees shift into the clear corridor
    (m8 -X toward m7, m9 +X past the motor bank) and reach back with a longer pigtail."""
    out = []
    for i in range(10):
        mx = D.motor_pos(i)[0]
        # m9's body sits AT the rail (its tee would be buried in it) -> park m9's tee just past the
        # motor bank in the clear corridor; every other motor's tee rides the rail at its own X (m8's
        # tee corner just grazes m8's PCB, a whitelisted mount contact).
        out.append((mx, TEE_Y, +1))
    return out


_TEE_LIFT = TEE_Z - EL.FLOOR_Z          # lift a RAIL tee dummy onto its cradle, above the rib tops

# ── TEES ON THE MOTORS (user, 2026-09-14) ───────────────────────────────────
# Bus-A tees 0..9 no longer ride the rail: each sits on its own motor's pocket, resting on the
# faceplate wall's top and LAPPING the motor, so the one M4 that holds the board down also stops
# the motor lifting out -- board and motor share a screw. The drop pigtail becomes a hand's
# breadth instead of a reach to the rail, and the trunk flies tee to tee over the bank.
# ALL TEN, including string 10: side entry (7.0 tall, not the 9.8 of a mated top-entry pair)
# clears the magnetic pickup's neck-most position over that motor by 1.4, so the exception that
# kept its tee on the rail is gone.
N_MOTOR_TEES = D.N_STRINGS


def on_motor(i):
    return i < N_MOTOR_TEES


def tee_center(i, x, y):
    """(cx, cy) of tee i's board."""
    if on_motor(i):
        # the bay itself is cut for the board (motor_bank.tee_board_box): the seat is the same
        # prism as the pocket, so the board's placement comes from there rather than from here
        bx0, bx1, by0, by1, _ = MB.tee_board_box(i)
        return (bx0 + bx1) / 2, (by0 + by1) / 2
    return x, EL.tee_board_cy(y)


def tee_z(i):
    """Board-underside Z for tee i."""
    return MB.tee_board_box(i)[4] if on_motor(i) else TEE_Z


def tee_hdr_z(i):
    """Where a wire lands on tee i: mid-mouth on a motor tee, the header top on a rail one."""
    from cadkit.pcb import XH_SIDE_H
    return (tee_z(i) + _PCB_T + XH_SIDE_H / 2) if on_motor(i) else HDR_Z


def _tee_at(i, x, y):
    """Where tee i's board is, as the move electronics.way_pt applies to tee_pcb(0, 0):
    the same three numbers tee_components() places the board with."""
    cx, cy = tee_center(i, x, y)
    return (cx, cy - EL.TEE_YSHIFT, tee_z(i) - EL.FLOOR_Z)


def tee_end(i, x, y, half):
    """One end of a trunk cable at tee i: its IN half (ways 1-4, from the west) or its
    OUT half (5-8, to the east), or the 4-way motor drop."""
    if half == "drop":
        return conn_end("can_tee", "J2", at=_tee_at(i, x, y))
    return conn_end("can_tee", "J1", ways=range(5, 9) if half == "out" else range(1, 5),
                    at=_tee_at(i, x, y))


def tee_pin(i, x, y, cond, out):
    """Tee i's trunk 8-way, the way carrying `cond` (TRUNK_PIN key) on its IN (1-4) or OUT
    (5-8) half, where the wire leaves the plug.

    ⚠ READ FROM THE ROUTED BOARD (electronics.way_pt). This used to count pitches from the
    housing's centre, and that centre came from tee_conn_dx -- a number measured from the
    middle of the board's 40 mm layout region and added here to the middle of the whole
    outline, ear included. Every end of every trunk cable sat 4.75 mm (1.9 ways) along the
    row from its contact, on all ten tees."""
    assert on_motor(i), "tee %d is not on a motor: there are no rail tees left" % i
    return EL.way_pt("can_tee", "J1", TRUNK_PIN[cond] + (4 if out else 0), _tee_at(i, x, y))


def tee_point(i, x, y, which="trunk"):
    """The middle of tee i's trunk (8-way) or drop (4-way) connector's row of ways, where
    the wires leave the plug: the mouth faces -Y, so they run out over the motor."""
    if not on_motor(i):
        cx, cy = tee_center(i, x, y)
        return cx, cy + EL.TEE_CONN_CY, tee_hdr_z(i)
    ref, n = ("J1", EL.TEE_TRUNK_N) if which == "trunk" else ("J2", EL.TEE_CONN_N)
    a, b = (EL.way_pt("can_tee", ref, k, _tee_at(i, x, y)) for k in (1, n))
    return tuple((a[m] + b[m]) / 2.0 for m in range(3))


# ── TEE RETENTION: ONE M4 THROUGH THE BOARD'S EAR (user: one driver, one insert SKU) ──
# It was one M2 down through a board hole. cadkit's pcb_cradle now takes the screw BESIDE
# the board (hold_edge): the walls capture every direction but +Z, and the button head laps
# the board edge to close +Z, so the board needs no hole at all. tee_hold() is the ONE
# table of per-tee choices, and it feeds the cradle, the dummy screw AND the post-fuse
# re-bore -- so the part that is bored and the screw the overlap gate checks cannot disagree.
MOTOR_SEAT_SO = 0.8         # a motor-seat cradle's pads under the board (the rail's is 3.2):
                            # every mm here is a mm the board sits further off the motor it laps
TEE_SCREW_L   = 10.0        # M4x10 button: head on the board top, tip inside the anchor
TEE_CLR       = 0.3         # board fit gap in the cradle; also sets where the hold screw sits
TEE_WALL_OVER = 1.2         # cradle walls stand this far above the board top
# (_BUS_B_M2_XY is NOT carried over from main: it located the M2 through the bus-B
#  PLACEHOLDER tees, and 11/12 are deleted on this branch (user). With them went the
#  last M2 in the tee family -- one screw diameter, one driver.)
_EAR_XY       = (D.TEE_BOARD_X / 2,         # the accurate board's M4 THROUGH-hole, board-local
                 (D.TEE_BOARD_Y - D.TEE_EAR_Y) / 2)   # (centred in the bare ear off its +X end)
from cadkit.fasteners import M4 as _M4
from cadkit.pcb import PCB_T as _PCB_T
assert TEE_SCREW_L - _PCB_T <= _M4.anchor_min_wall + 1e-9, (
    f"tee hold-down M4x{TEE_SCREW_L:g} reaches {TEE_SCREW_L - _PCB_T:.2f} below the board's "
    f"underside, past the {_M4.anchor_min_wall} anchor the cradle bores -- it would bottom out")


def tee_hold(i, x, y, d):
    """(board_w, board_l, centre_x, centre_y, open_edge, hold_edge, hold_at) for tee i.

    EVERY TEE IS NOW THE SAME BOARD ON THE SAME M4 THROUGH ITS EAR. Main still carried
    an `i >= 11` branch for the bus-B PLACEHOLDERS and their M2 through the board; those
    tees are deleted (user), so the branch is gone and with it THE LAST M2 IN THE TEE
    FAMILY -- one screw diameter, one driver."""
    if on_motor(i):
        # ON A MOTOR: the board's -Y half laps the motor, so that edge can have no wall (a wall
        # there would overhang the motor and trap it) -- and a screw BESIDE the board only laps
        # its edge, which friction alone then has to hold against a -Y tug (user, 2026-09-15:
        # every unplug is one, since the mouths face -Y). So the screw goes THROUGH the board,
        # down the bare ear off its +X end into the post: positive in X and Y, not frictional.
        cx, cy = tee_center(i, x, y)
        return (D.TEE_OUTLINE_X, EL.TEE_BOARD_Y, cx, cy, "-x", "through", None)
    # ⚠ UNREACHABLE SINCE TEE 10 WENT: every tee is on a motor now, so on_motor() above
    # always takes it. Kept as the rail-mounted form -- a cradle on the rib tops with all
    # four walls closed -- because it is the shape any future rail tee would want, and
    # raising here instead would lose that. If nothing rail-mounted returns by the time
    # this file is next touched, delete it rather than letting it rot.
    return D.TEE_OUTLINE_X, EL.TEE_BOARD_Y, x, EL.tee_board_cy(y), None, "through", None



def tee_components():
    """The tee-PCB dummies for the assembly, lifted onto their -Y-rail cradles (above the
    rib tops so no tee sits in a rib), each M4-held tee with its screw and insert placed
    from the same tee_hold() the cradle is bored from. See tee_cradles()."""
    from cadkit.fasteners import M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    from cadkit.pcb import pcb_hold_xy
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        # main's placement wins: the tee now sits at its own tee_z (on a motor, or the
        # rail for tee 10), not at one shared lift. `accurate` is vestigial with the
        # placeholders gone, so every tee is the real board.
        bw, bl, cx, cy, _open, hold_edge, hold_at = tee_hold(i, x, y, d)
        z0 = tee_z(i)
        out.append((f"tee_pcb_{i}", EL.tee_pcb(cx, cy - EL.TEE_YSHIFT, d)
                    .translate((0, 0, z0 - EL.FLOOR_Z))))
        out.append((f"tee_silk_{i}", EL.tee_silk(cx, cy - EL.TEE_YSHIFT)
                    .translate((0, 0, z0 - EL.FLOOR_Z))))
        if hold_edge is None:
            continue
        hx, hy = _EAR_XY if hold_edge == "through" else pcb_hold_xy(
            bw, bl, hold_edge, hold_at=hold_at, clr=TEE_CLR)
        out.append((f"tee_insert_{i}", seated_insert(_M4, (cx + hx, cy + hy, z0), (0, 0, -1))))
        out.append((f"tee_screw_{i}", m4_button_screw(TEE_SCREW_L).translate(
            (cx + hx, cy + hy, z0 + _PCB_T + M4_BUTTON_HEAD_H))))          # head seated on the board top
    return out


# ── BUS B'S -X END: the wiring port through the chassis floor ─────────────
# TWO CABLES MEET THE CONTROLLER HERE and only one of them comes from outside. The
# pedal bar's four conductors arrive up the -X/+Y leg and out of the body adapter's
# channel onto the instrument's UNDERSIDE (leg_pogo.chan_ends); the knee-lever chain
# starts at LKL and is inside the body already. The controller is a MID-BUS node --
# bus in on J2 ways 1-4, out on 5-8 (elec/motor_ctrl) -- so both land on the one
# connector, and the port is what gets the outside half in.
#
# THE PORT ITSELF IS THE CHASSIS' (chassis.PORT_X / PORT_W / PORT_L / port_y): it is a
# hole in the floor slab placed on the chassis' own mortise grid, so it is dimensioned
# beside that grid. Read from there rather than copied.
from .chassis import PORT_W, port_y
from .chassis import Z_BOT as _CH_Z_BOT
from . import leg_pogo as _PG
from cadkit.pcb import PH_PITCH as _PH_PITCH


# ── TRRS ADAPTER STATION -- the -X/+Y leg's cable into the instrument ─────
# THE LEG UNPLUGS BEFORE IT SLIDES OUT, so this station is chosen by where a HAND
# can reach a plug, not by where a board fits tidily. The plug is on the
# instrument's -Z UNDERSIDE (user, with the spot circled): it looks straight DOWN
# through a bore in the chassis floor, a hand's reach inboard of the leg, and the
# lead from the body adapter never comes round to a face you can see. An earlier
# pass had it mouthing +Y through the back rail, which is exactly the face the
# player looks at.
#
# THE BOARD IS A REQUEST TO BRONNER, and this is the second one -- it REPLACES the
# earlier "put the jack on the long edge". What the station needs now is a
# BOARD-PERPENDICULAR (vertical-entry) 3.5 mm 4-pole jack: barrel along the board's
# normal, mouth through the board. Everything else about the board is unchanged and
# every size below still comes from electronics.py. The reason is room, and it is
# not close: a board-PARALLEL jack can only look -Z if the board stands on edge, and
# a board on edge is 26 tall in a cavity whose only solid floor is under the
# electronics tray, with 9.5 between that floor and the tray's underside.
# _trrs_board_as_asked is what gets deleted when the respin lands.
#
# WHAT SETS THE POCKET, all of it measured on the BUILT chassis rather than reasoned
# about:
#   * THE FLOOR is a 10.3 slab, -81.8 (the instrument's underside, and this
#     segment's print bed) to -71.5. Over the leg and just outboard of here the slab
#     is a RIB LATTICE with open cells; it goes fully solid from x -608 inboard. The
#     port and the screw's anchor both want solid slab, so the station sits at
#     x -604, in that band and as far out toward the leg as the band reaches.
#   * ABOVE is the electronics tray, whose plate starts at z -62. The cradle's top
#     is -66.6, so it passes under it -- which is only possible because the screw's
#     anchor goes down into the SLAB instead of into a 6.0 base plate of its own.
#   * The plug hangs ~17 below the underside. That is the price of a plug you can
#     reach without taking the instrument apart.
TRRS_FLOOR_TOP = -71.5      # the chassis floor's upper face at this station
TRRS_FLOOR_BOT = -81.8      # ...and the instrument's underside: this segment's bed
TRRS_X = -755 * D.BEAD      # -604.0: in the solid band, and as far outboard (toward
TRRS_Y = 0.0                # the leg) as that band reaches
TRRS_CLR = TEE_CLR          # the tees' own board fit, wall stand-off and screw: one
TRRS_WALL_OVER = TEE_WALL_OVER      # cradle idiom on this instrument, not two
TRRS_SCREW_L = TEE_SCREW_L          # M4x10 button, 2.5 hex -- the one lock (user)
# THE ADAPTER BOARD IS GONE (user, 2026-09-16): the leg column became an off-the-shelf
# TRRS extension lead, so electronics no longer carries TRRS_BOARD_* / TRRS_PLUG_* /
# TRRS_JACK_*. This station is PARKED, not deleted, and it still reasons in the board's
# dimensions -- so they live here now as plain numbers rather than as imports of a thing
# that does not exist. Values are the board as it last stood (20.0 x 31.0, a mated plug
# needing 30.0 of run at O10.0, the jack 15.18 across x 10.09 tall).
TRRS_ACROSS = 20.0                          # across X
TRRS_ALONG = 31.0                           # along Y
TRRS_PLUG_D = 10.0                          # the plug handle's diameter
TRRS_PLUG_RUN = 30.0                        # what a MATED plug needs clear of the mouth
TRRS_JACK_W = 15.18                         # the jack body, across
TRRS_JACK_L = 10.09                         # ...and tall
TRRS_PORT_D = TRRS_PLUG_D + 0.8             # 10.8: the plug's handle passes THROUGH the
                                            # floor slab to reach the mouth -- a socket
                                            # has to be met by the plug's shoulder, and
                                            # the slab is 10.3 of that reach
_TRRS_STANDOFF = 2.5
_TRRS_BASE_T = 1.6          # NOT pcb_cradle's default 6.0. That default exists so the
                            # M4's anchor fits above the mounting surface; here the
                            # mounting surface IS the floor slab and the anchor bores
                            # 8.5 down into 10.3 of it, so the plate is just a plate.
                            # Paying the 6.0 would put the cradle's top through the
                            # electronics tray.


def trrs_station():
    """(centre x, centre y, mounting surface z) -- the board's outline in the world."""
    return TRRS_X, TRRS_Y, TRRS_FLOOR_TOP


def trrs_board_z():
    """The board's underside. pcb_cradle measures its standoff from the MOUNTING
    SURFACE (its base plate hangs BELOW that), so this is not base + plate + standoff
    -- getting that wrong floats the board 6.0 clear of the pads that hold it."""
    return TRRS_FLOOR_TOP + _TRRS_STANDOFF


def trrs_mouth_z():
    """The jack's mouth: through the board, looking -Z."""
    return trrs_board_z()


def trrs_cradle():
    """The drop-in cradle, standing on the floor slab. Walls on ALL FOUR edges -- no
    rail to borrow here -- so the only way the board can leave is the way it went in
    (+Z), and the one M4 beside its -Y edge closes that."""
    from cadkit.fasteners import M4_BUTTON_HEAD_D
    from cadkit.pcb import pcb_cradle
    cx, cy, z0 = trrs_station()
    cr = pcb_cradle(TRRS_ACROSS, TRRS_ALONG, open_edge=None, hold_edge="-y",
                    standoff=_TRRS_STANDOFF, wall_over=TRRS_WALL_OVER, clr=TRRS_CLR,
                    base_t=_TRRS_BASE_T, hold_spec=_M4, head_d=M4_BUTTON_HEAD_D)
    cr = cr.translate((cx, cy, z0))
    return cr.union(_trrs_footing(cr.val().BoundingBox()))


def _trrs_footing(bb):
    """WHAT THE CRADLE STANDS ON. The floor slab here is not a plate but a RIB
    LATTICE with open cells, and a base plate laid across it is a bridge, not a
    foundation (measured: 79 mm2 of the plate had nothing under it). So the cells
    under the cradle's own footprint are FILLED, slab bottom to slab top -- and the
    slab's bottom is this segment's print bed, which makes the fill the first layer
    rather than an island. The footprint comes from the cradle's OWN bounding box:
    the M4's boss stands proud of the base plate on the -Y side, and sizing this by
    hand is how that boss ends up hanging."""
    from .helpers import box_at
    return box_at(bb.xlen, bb.ylen, TRRS_FLOOR_TOP - TRRS_FLOOR_BOT,
                  x=bb.center.x, y=bb.center.y,
                  z=(TRRS_FLOOR_BOT + TRRS_FLOOR_TOP) / 2.0)


def trrs_port():
    """The bore the plug reaches up along, straight down through the floor slab and
    out the instrument's underside. It runs along the chassis's own build direction,
    so it needs no teardrop: a +Z bore prints round."""
    import cadquery as cq
    cx, cy, _ = trrs_station()
    z0 = TRRS_FLOOR_BOT - 1.0
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(
        TRRS_PORT_D / 2.0, (trrs_mouth_z() + 0.5) - z0,
        cq.Vector(cx, cy, z0), cq.Vector(0, 0, 1)))


def trrs_hold_negatives():
    """The cradle's own anchor and head notch, in the world -- build.py re-cuts them
    after the fuse, the same refill trap the tees have. The anchor lands in the floor
    slab, which is why the base plate can be 1.6."""
    import cadquery as cq
    from cadkit.fasteners import M4_BUTTON_HEAD_D, anchor_cutter
    from cadkit.pcb import pcb_hold_xy
    cx, cy, _ = trrs_station()
    hx, hy = pcb_hold_xy(TRRS_ACROSS, TRRS_ALONG, "-y", clr=TRRS_CLR, spec=_M4)
    wx, wy = cx + hx, cy + hy
    bz = trrs_board_z()
    out = [anchor_cutter(_M4, (wx, wy, bz), (0, 0, -1), _M4.anchor_min_wall,
                         overshoot=1.0, print_up=(0.0, 0.0, 1.0))]
    out.append(cq.Workplane("XY").add(cq.Solid.makeCylinder(
        (M4_BUTTON_HEAD_D + 2 * TRRS_CLR) / 2.0, _PCB_T + TRRS_WALL_OVER + 1.0,
        cq.Vector(wx, wy, bz), cq.Vector(0, 0, 1))))
    return out


def trrs_components():
    """The assembly's dummies: the board on its cradle, the screw and its insert, and
    the MATED PLUG -- the plug is the point of the station, so it is drawn."""
    import cadquery as cq
    from cadkit.fasteners import M4_BUTTON_HEAD_H, m4_button_screw, seated_insert
    from cadkit.pcb import pcb_hold_xy
    cx, cy, _ = trrs_station()
    bz, mz = trrs_board_z(), trrs_mouth_z()
    board = _trrs_board_as_asked().translate((cx, cy, bz))
    hx, hy = pcb_hold_xy(TRRS_ACROSS, TRRS_ALONG, "-y", clr=TRRS_CLR, spec=_M4)
    wx, wy = cx + hx, cy + hy
    plug = cq.Workplane("XY").add(cq.Solid.makeCylinder(
        TRRS_PLUG_D / 2.0, TRRS_PLUG_RUN,
        cq.Vector(cx, cy, mz - TRRS_PLUG_RUN), cq.Vector(0, 0, 1)))
    return [("trrs_adapter_pcb", board),
            ("trrs_adapter_plug", plug),
            ("trrs_adapter_insert", seated_insert(_M4, (wx, wy, bz), (0, 0, -1))),
            ("trrs_adapter_screw", m4_button_screw(TRRS_SCREW_L).translate(
                (wx, wy, bz + _PCB_T + M4_BUTTON_HEAD_H)))]


def _trrs_board_as_asked():
    """Bronner's adapter WITH A BOARD-PERPENDICULAR JACK (the request above), in the
    world's axes: origin at the board's centre on its underside, the mouth looking
    -Z through the board. Every size is electronics'; only the jack's axis differs,
    and this function is what gets deleted when the respin lands."""
    from .helpers import box_at
    from cadkit.pcb import jst_xh_header
    b = box_at(TRRS_ACROSS, TRRS_ALONG, _PCB_T, x=0.0, y=0.0, z=_PCB_T / 2)
    b = b.union(box_at(TRRS_JACK_W, TRRS_JACK_W, TRRS_JACK_L, x=0.0, y=0.0,
                       z=_PCB_T + TRRS_JACK_L / 2))
    b = b.union(jst_xh_header(4, mated=False)
                .translate((0.0, TRRS_ALONG / 2 - 7.5, _PCB_T)))
    return b


def tee_cradles():
    """A drop-in pcb_cradle under each tee, on the -Y-rail corridor. The cradle base sits on the
    rib tops; the tee drops in from +Z and ONE M4 beside it retains it (tee_hold). The tee
    connectors are TOP-entry (cables up), so a relief WINDOW is cut in the base under them for
    the THT post tails (3.4 below the board vs the 3.2 standoff). The M4 anchor is 8.5 deep
    against the M2's 5.5, so an M4-held cradle's base reaches 5.3 below the rib tops, not 2.3
    -- which is why build.py re-bores it after the fuse (tee_hold_negatives)."""
    from cadkit.pcb import pcb_cradle
    from .helpers import box_at
    rw, rl = EL.TEE_RELIEF
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        if on_motor(i):
            continue          # ITS SEAT IS THE BAY: motor_bank cuts the board's profile out of
                              # the same prism it cuts the motor from, so there is no part here
        bw, bl, cx, cy, open_edge, hold_edge, hold_at = tee_hold(i, x, y, d)
        # ON A MOTOR the cradle stands on the pocket's faceplate wall, so its base is only
        # MOTOR_SEAT_SO under the board; on the rail it stands on the rib tops as before.
        so = MOTOR_SEAT_SO if on_motor(i) else TEE_Z - _RIB_TOP
        base_z = tee_z(i) - so
        # (main's `hold_edge is None` arm went with the bus-B placeholders and their M2.
        #  Every surviving tee is held THROUGH its ear, so the M4 arm is the only one left
        #  that can fire -- the else is kept for a tee that ever wants an edge hold again.)
        if hold_edge == "through":
            cr = pcb_cradle(bw, bl, screw_xy=_EAR_XY, spec=_M4, open_edge=open_edge, standoff=so,
                            wall_over=TEE_WALL_OVER, clr=TEE_CLR)
        else:
            cr = pcb_cradle(bw, bl, open_edge=open_edge, hold_edge=hold_edge, hold_at=hold_at,
                            standoff=so, wall_over=TEE_WALL_OVER, clr=TEE_CLR)
        cr = cr.cut(box_at(rw, rl, 12.0, x=0.0, y=EL.TEE_CONN_CY, z=-5.5))   # THT-tail relief
        cr = cr.translate((cx, cy, base_z))
        # EACH CRADLE CARRIES ITS OWN STATION. It used to be zipped against tee_stations() by
        # position in build.py, which silently broke the moment this loop started SKIPPING the
        # ten bank tees: every surviving cradle got paired with another tee's x and fused into
        # the segment that x falls in -- all three into the keyhead segment, 350 mm from where
        # their geometry sits, floating free of it and burying rib -70.8's lever mortise.
        out.append((f"tee_cradle_{i}", cr, (x, y, d)))
    return out


def tee_hold_negatives():
    """[(station_x, [world-space cutters])] for every M4-held tee: the SAME anchor and head
    notch pcb_cradle bores, placed in the world. build.py cuts them AFTER fusing the cradles
    into the chassis segments, because that fuse fills them straight back in with the
    segment's own rib and rail material (a feature cut before a union does not survive it)."""
    import cadquery as cq
    from cadkit.fasteners import M4_BUTTON_HEAD_D, anchor_cutter
    from cadkit.pcb import pcb_hold_xy
    notch_h = _PCB_T + TEE_WALL_OVER + 1.0
    out = []
    for i, (x, y, d) in enumerate(tee_stations()):
        bw, bl, cx, cy, _open, hold_edge, hold_at = tee_hold(i, x, y, d)
        if hold_edge is None:
            continue
        hx, hy = _EAR_XY if hold_edge == "through" else pcb_hold_xy(
            bw, bl, hold_edge, hold_at=hold_at, clr=TEE_CLR)
        px, py, pz = cx + hx, cy + hy, tee_z(i)
        anchor = anchor_cutter(_M4, (px, py, pz), (0, 0, -1), _M4.anchor_min_wall)
        notch = cq.Workplane("XY").add(cq.Solid.makeCylinder(
            (M4_BUTTON_HEAD_D + 2 * TEE_CLR) / 2, notch_h, cq.Vector(px, py, pz)))
        out.append((x, [anchor, notch]))
    return out


def _on_bank(p):
    return p[2] > HDR_Z + 20.0          # a tee on a motor sits far above the rail lanes


def _seg(a, b, lane_z, d=WIRE_D, off=0.0, a_pin=None, b_pin=None):
    """One crimped trunk SEGMENT between two tee headers, each a 3D point (tee_point).

    Two tees ON THE BANK fly to each other at TOP_Z, over the motors. A segment with a RAIL
    tee at one end rises there and flies across at the same lane. Rail to rail is the old
    route: the rail corridor at lane_z, dodging m9. off shifts x AND y (the 24 V pair)."""
    if _on_bank(a) and _on_bank(b):
        # out of each mouth, along the -Y side of the boards at mouth height, into the next --
        # low enough to pass under the magnetic pickup's neck-most position at every X
        lane = min(a[1], b[1]) - 4.0
        # EACH HOP LEAVES ITS CONNECTOR LEANING TOWARD THE HOP IT IS GOING TO. Straight out of
        # the mouth, the stub of the hop ARRIVING at a tee and the stub of the hop LEAVING it
        # were the same line -- same x, same z, same direction out of the same point -- so two
        # Ø1.3 conductors ran COINCIDENT for 4.65 mm, ~6.0 mm3 of each inside the other. OCCT
        # cannot boolean coincident cylinders, which is what put wire_canh_8/9 and wire_canl_8/9
        # in the gate's "could not be checked" list for as long as it has had one: they were not
        # suspect, they were a modelling artefact. Leaning them apart is also the truer picture --
        # the trunk in and the trunk out are different contacts on the same 6-way, and two crimps
        # leaving a connector lie side by side, not through each other.
        _lean = 2.0 if b[0] >= a[0] else -2.0
        if a_pin is not None and b_pin is not None:
            # PIN TO PIN: out of the WEST pin and along its own lane at the RUN level, then
            # up and OVER the other three into the EAST pin -- see TRUNK_Z_RUN
            zr, zo = a[2] + TRUNK_Z_RUN, a[2] + TRUNK_Z_OVER
            ly = lane + off
            w, e = (a_pin, b_pin) if a_pin[0] <= b_pin[0] else (b_pin, a_pin)
            pts = [w, (w[0], w[1] - 1.5, zr), (w[0], ly, zr), (e[0], ly, zr),
                   (e[0], ly, zo), (e[0], e[1] - 1.5, zo), e]
            return _wire(pts if w is a_pin else pts[::-1], d)
        pts = [a, (a[0] + _lean, lane, a[2]), (b[0] - _lean, lane, b[2]), b]
    elif _on_bank(a) or _on_bank(b):
        t, r = (a, b) if _on_bank(a) else (b, a)          # t on the bank, r on the rail
        pts = [t, (t[0], t[1] - 4.0, t[2]), (r[0], t[1] - 4.0, t[2]), (r[0], r[1], t[2]),
               (r[0], r[1], r[2])]
        if not _on_bank(a):
            pts.reverse()
    else:
        pts = [a] + _rail_pts(a[0], b[0], lane_z) + [b]
    pts = [(px + off, py + off, pz) for px, py, pz in pts]
    if a_pin is not None:
        pts[0] = a_pin
    if b_pin is not None:
        pts[-1] = b_pin
    return _wire(pts, d)


def build_wires():
    """Returns [(name, workplane)] for every net."""
    out = []
    # THE AFE'S WIRES ARE GONE WITH THE AFE (2026-09-14). wire_pickup, wire_out,
    # wire_audio, wire_dac and wire_relayctrl all began or ended on that board;
    # the bypass relay and the magnetic buffer now live on the optical pickup
    # board, which is 10 mm from the jack and the audio connector they feed.
    # wire_pickup IS BACK (2026-09-24), and NOT to the optical board: the magnetic
    # path moved to the OUTPUT PANEL on 2026-09-15, which is nearer the pickup than
    # the optical board is, so the analog run got shorter rather than longer. It
    # lands on J8's SCREW TERMINALS (user) -- the pickup is the most likely thing
    # anyone ever rewires, and a screw terminal takes the two bare tinned leads a
    # pickup ships with, neither soldered nor crimped.
    # Keyhead routing (STANDING TRAY, user 2026-09-11): the boards stand against the keyhead
    # endplate and string 1's motor sits 1.6 mm off the Pi, so nothing inside that motor's
    # Y/Z band can be reached from +X. Every bay wire therefore uses ONE column, BAY_X, just
    # inside the motor's -X face: -Y of the motor it rises straight out of the rail corridor,
    # and across the motor's Y band it runs at BAYFLY, over the motor top. From the column
    # it turns -X onto its board. Board pins stay authored in the tray's FLAT frame and are
    # posed with EL.stand_pt, so they follow the tray. Wire-vs-wire crossings are fine
    # (insulated); only solids (motors/boards/chassis) are avoided.
    # ⚠ THE COLUMN IS HUNG OFF THE BOARD IT SERVES, NOT OFF THE MOTOR (2026-10-02). It was
    # string 1's -X face + 1.0, which is the same place only while that motor stood 8 mm
    # +X of the standing board. The bank is packed against the endplate now and that motor
    # stands OVER this column's x; the rule above is unchanged -- rise -Y of the motor, fly
    # its Y band at BAYFLY -- and the column stays where the board's connectors are.
    BAY_X = D.MCTRL_X[1] + 9.1                          # -582.6
    BAYFLY = -12.0                                      # over motor 0, under the deck
    assert BAYFLY - max(WIRE_OD.values()) / 2 > D.MOTOR_BELT_Z + D.MOTOR_SQ / 2 + 1.0, (
        "the bay fly lane has come down onto string 1's motor")
    # ⚠ THREE BAY WIRES WERE ONE. The Pi link, bus B and the board-to-Pi USB all crossed
    # string 1's motor along this one column at BAYFLY -- 234, 69 and 15.5 mm3 of each
    # inside another, on the committed model, never reported (the gate allow-lists wire
    # against wire). The USB takes its own column (see _USB_COL).
    SP = EL.stand_pt
    # (the AFE's long shielded runs and their _long() helper are gone with the
    #  board; the Teensy stack they climbed onto is gone with the motor controller)

    # ── the two CAN buses: TRUNK-AND-DROP over the rail tee PCBs ────────
    tees = tee_stations()
    hdrA = {i: tee_point(i, tees[i][0], tees[i][1])          # trunk connector (3D) per tee
            for i in range(len(tees))}
    dropA = {i: tee_point(i, tees[i][0], tees[i][1], "drop") for i in range(10)}
    west = sorted(range(10), key=lambda i: hdrA[i][0])       # bus A west→east
    _WEST0 = west[-1]                 # the trunk's landing: the EAST-most tee, nearest J7

    # bus A CAN head: motor_ctrl J1 -> bay corridor -> -Y rail -> westernmost motor tee;
    # then one crimped segment per hop east. Termination: the controller's fixed R5 + the
    # last tee's switch ON -- one at each END of the trunk and nowhere else (ISO 11898).
    # Drawn as the CAN-H (yellow) + CAN-L (green) pair, offset +-CAN_OFF (user).
    _w0 = hdrA[west[0]]                                      # string 1's tee, on its motor
    # ⚠ MAIN'S PATH, THIS BRANCH'S ENDPOINT. Main is right about the SHAPE -- with the
    # tees up on the motors there is no rail ride left, so the run climbs the bay gap and
    # flies straight over the bank to the first tee. But it STARTS at a hardcoded point on
    # the teensy_ifc board, which this branch deleted. The merged motor controller is the
    # source now, and it says where its own bus-A connector is rather than being copied.
    _tin = {i: tee_end(i, tees[i][0], tees[i][1], "in") for i in range(10)}
    _tout = {i: tee_end(i, tees[i][0], tees[i][1], "out") for i in range(10)}
    _NAME = {"GND": "wire_pwr_gnd", "V24": "wire_pwr_hot",
             "CAN_H": "wire_canh", "CAN_L": "wire_canl"}

    assert _w0[2] + TRUNK_Z_RUN - WIRE_OD["wire_pwr_gnd"] / 2 > MB.SEAT_TOP + 0.3, (
        "the trunk's run level has come down into the bay walls (SEAT_TOP)")

    # ── THE HEAD IS ONE FOUR-WAY LEAD: motor_ctrl J1 -> the first tee's IN half ──────────
    # GND, 24 V, CAN_H, CAN_L on J1's ways 1-4 to the tee's ways 1-4 (harness.XH_PINOUT at
    # both ends). It was drawn as a CAN pair out of the middle of J1, with the tee's ground
    # and 24 V taken to J3 instead -- the 6-way that belongs to the power link from the
    # output board -- so J1 showed two conductors of four and J3 four ends from two cables.
    # Each conductor leaves its own way along the board's normal (+X, over the Pi cap),
    # climbs at once to the tee's own height, runs +Y past the standing board's edge and
    # over string 1's motor, and only there steps -X onto its pin and in through the mouth.
    # The four keep their order the whole way (way 1 is the -Y-most at J1, takes the -X-most
    # riser, turns first, and lands on the -X-most pin), so none crosses another.
    # ⚠ THE FOOT STRIP'S LEAD COMES DOWN THIS BOARD'S FACE TOO (led_leads.foot_paths: four
    # columns at x -595.5 to -590.7, in the corridor's y). The first riser stands 0.2 clear
    # of the nearest of them, and the four lanes are packed to their own diameters rather
    # than at the connector's pitch, which keeps the last one clear of the 24 V link.
    _HEAD_RISE = 2.8                  # J1's plug top to the first riser
    _HEAD_LANES = (0.0, 2.0, 3.8, 5.4)       # GND, 24 V (O1.8), CAN_H, CAN_L (O1.3)
    _HEAD_TURN_Y = MB.body_box(0)[2] + 5.0      # the first -X step, 5 in over string 1's motor
    _SEG = {"GND": 11, "V24": 11, "CAN_H": 0, "CAN_L": 0}       # the names these have always had
    _ja = conn_end("motor_ctrl", "J1")
    for k in _cable("bus A head", _ja, _tin[west[0]]):
        (pa, _d, net), (pb, _bd, _bn) = _ja[k], _tin[west[0]][k]
        xr = pa[0] + _HEAD_RISE + _HEAD_LANES[k]
        yj = _HEAD_TURN_Y + k * _XH_PITCH
        assert pb[0] < xr, "bus A's head: way %d's riser is not +X of its tee pin" % (k + 1)
        _run(out, "%s_%d" % (_NAME[net], _SEG[net]),
             [pa, (xr, pa[1], pa[2]), (xr, pa[1], pb[2]), (xr, yj, pb[2]),
              (pb[0], yj, pb[2]), pb], WIRE_OD[_NAME[net]], "bus A head", k)

    # ── THE HOPS: tee k's OUT half -> tee k+1's IN half, four conductors each ────────────
    # STRAIGHT OUT OF THE MOUTH FIRST. Each conductor used to leave its pin already dipping
    # to the run level (and arrive already descending from the crossing level), 28 to 39
    # degrees off the contact's axis: a wire cannot do that inside a housing. It now runs
    # _HOP_LEAD along the axis, takes _HOP_DIP to change level, and the lanes sit that much
    # further out over the motors.
    _HOP_LEAD, _HOP_DIP = 2.0, 1.5
    _HOP_LANE = _HOP_LEAD + _HOP_DIP + max(TRUNK_OFF.values()) + 0.9      # 7.0 to the lanes' middle

    def _hop(w, e, off):
        lane = min(w[1], e[1]) - _HOP_LANE + off
        zr, zo = w[2] + TRUNK_Z_RUN, w[2] + TRUNK_Z_OVER
        return [w, (w[0], w[1] - _HOP_LEAD, w[2]), (w[0], w[1] - _HOP_LEAD - _HOP_DIP, zr),
                (w[0], lane, zr), (e[0], lane, zr), (e[0], lane, zo),
                (e[0], e[1] - _HOP_LEAD - _HOP_DIP, zo), (e[0], e[1] - _HOP_LEAD, e[2]), e]

    for k in range(9):
        _key = "bus A trunk %d" % k
        _a, _b = _tout[west[k]], _tin[west[k + 1]]
        for j in _cable(_key, _a, _b):
            net = _a[j][2]
            # the CAN pair's hops are numbered from 1 and the 24 V pair's from 2 (a hop that
            # no longer exists was _1): the names the colour and allow-list tables know
            _run(out, "%s_%d" % (_NAME[net], k + (1 if net.startswith("CAN") else 2)),
                 _hop(_a[j][0], _b[j][0], TRUNK_OFF[_CAD_NAME[net]]),
                 WIRE_OD[_NAME[net]], _key, j)

    # bus A drops: each motor's factory 4-pin XH pigtail (grey), from its -Y-facing PCB to its
    # OWN tee. For the nine tees on motors that is a short climb up behind the motor and over
    # its top; string 10's tee is still on the rail, so that one keeps the old reach along the
    # corridor. The climb stands off the back bumper where there is one.
    _under = []                 # x of each pigtail that climbs under the trough's line
    _HUMP = 1.2                 # how far the lanes lift over one
    _HUMP_R = WIRE_OD["motor_pigtail"] / 2.0 + 1.8      # half the lifted length, level
    _HUMP_RAMP = 4.0                                    # ...and each ramp up to it

    def _lane(x0, x1, z):
        """The trough's line from x0 west to x1 at lane height z, lifted over every pigtail
        that climbs under it."""
        pts = [(x0, CHAN_Y, z)]
        for hx in sorted(_under, reverse=True):
            if x1 < hx - _HUMP_R - _HUMP_RAMP and hx + _HUMP_R + _HUMP_RAMP < x0:
                pts += [(hx + _HUMP_R + _HUMP_RAMP, CHAN_Y, z), (hx + _HUMP_R, CHAN_Y, z + _HUMP),
                        (hx - _HUMP_R, CHAN_Y, z + _HUMP), (hx - _HUMP_R - _HUMP_RAMP, CHAN_Y, z)]
        return pts + [(x1, CHAN_Y, z)]

    for i in range(10):
        mx, sy, mz = D.motor_pos(i)
        back = _motor_back(i)
        if on_motor(i):
            dx, dy, dz = dropA[i]
            room = back - RAIL_INNER_Y                 # from the motor's back face to the rail
            stand = MB.BACK_T + MB.MOTOR_CLR + 2.0     # clear of the bay's back wall
            # STRING 10's bay has no back wall -- the harness corridor takes it, and the rail
            # is right there -- so its pigtail climbs hugging the motor's back instead, in the
            # chassis.RAIL_GAP left for exactly this: 0.5 off the rail. (It used to lie in a
            # notch cut into the rail and run east round the motor; the user had the body
            # widened so the wall could stay whole.)
            _od = WIRE_OD["motor_pigtail"]
            stand = min(stand, room - _od / 2.0 - 0.5)
            assert stand >= MB.MOTOR_CLR + _od / 2.0, (
                "motor %d: %.2f between its back and the -Y rail -- no room for its Ø%.1f "
                "pigtail to climb (chassis.RAIL_GAP)" % (i, room, _od))
            _yc = back - stand
            if _yc - _od / 2.0 < CHAN_Y + 2.5:
                # ...and it climbs RIGHT UNDER THE TROUGH'S LANES, which carry on over this
                # motor at CHAN_Y where the trough is left out. Its tee's mouth is at the 24 V link's
                # height, so rising to it and turning east ran 21 mm along inside that cable.
                # So it crosses onto the motor at the motor's own top, UNDER the lanes, and
                # only rises to the mouth once it is +Y of them.
                # ⚠ AND THE LANES LIFT OVER IT (2026-10-06). The lowest cable there is the
                # six-way 24 V link now, on the trough's floor line: 1.0 mm lower than the
                # pair it replaced, and that put it in this jacket's top. The motor is
                # under the jacket, so the cables above it give way: _lane humps the link
                # and the USB lead over each climb recorded here.
                _zc = D.MOTOR_BELT_Z + D.MOTOR_SQ / 2 + _od / 2.0 + 0.15
                _under.append(mx)
                assert _zc + _od / 2.0 < LANE_PWR2 + _HUMP - PLINK_HALF - 0.2, (
                    "motor %d's pigtail cannot pass under the trough lanes" % i)
                _yi = CHAN_Y + 2.5 + _od / 2.0 + 1.0
                # ...and it stays at the motor's top to its tee, like the other nine: the
                # 24 V head comes in to the same tee at the mouth's height, across this run
                _run(out, f"motor_pigtail_{i}", [
                    (mx, back, mz), (mx, _yc, mz), (mx, _yc, _zc), (mx, _yi, _zc),
                    (dx, _yi, _zc), (dx, dy - 8.0, _zc), (dx, dy - 4.0, dz), (dx, dy, dz)], _od)
                continue
            # OVER THE MOTOR AT THE MOTOR'S OWN TOP, not at the mouth's height: the trunk's
            # lanes and bus A's head cross this run at the mouth's height, and a jacket
            # drawn there too is drawn through them. It comes up to the mouth over the
            # last few millimetres and goes in along the contact axis.
            _zf = D.MOTOR_BELT_Z + D.MOTOR_SQ / 2 + _od / 2.0 + 0.15
            _run(out, f"motor_pigtail_{i}", [
                (mx, back, mz), (mx, back - stand, mz), (mx, back - stand, _zf),
                (dx, back - stand, _zf), (dx, dy - 8.0, _zf), (dx, dy - 4.0, dz),
                (dx, dy, dz)], _od)
            continue
        tx = tees[i][0]
        cy = min(TEE_Y, back - 3.0)
        out.append((f"motor_pigtail_{i}", _wire([
            (mx, back, mz), (mx, back, -52.0), (mx, cy, -52.0),
            (tx, cy, -52.0), (tx, TEE_Y + 4.5, -52.0), (tx, TEE_Y + 4.5, HDR_Z)],
            WIRE_OD["motor_pigtail"])))

    # 24 V pair (2 × 22 AWG per rail): panel J7 -> tee 9 ... tee 0 -> motor controller.
    # hot/gnd offset ±PWR_OFF.
    # ⚠ IT USED TO LAND ON TEE 10 AND TEE 10 IS GONE. The run now goes straight from the
    # panel to the westmost motor tee. Nothing had to be re-sized for it: these cables are
    # crimped from spooled wire (user), so the head is simply made to whatever length the
    # new landing needs, and cable length was never the reason the junction existed.
    # ── THE OUTPUT BOARD'S 24 V HARNESS: TO THE WALL, ONE LOOP, THEN DOWN THE INSTRUMENT ──
    # (user, 2026-09-21: "route the wires to the chassis wall fairly directly and then coil
    # them in a single large circle before sending them down the instrument. The snake
    # pattern you have designed seems hard to achieve.") It was also drawn THROUGH the
    # output board: the serpentine sat at a fixed spot and nothing re-checked it when the
    # board moved, so it ran through the PCB and out below it.
    #
    # Both pairs leave their top-entry headers UP, cross the endplate's recess along the
    # board's -Y edge -- over the J7/J9 plug tops (-35.3), under the recess roof (-23.2) --
    # and come out into the bay, where they turn for the wall.
    _j7e = conn_end("output_panel", "J7", ways=(1, 2))      # GND, 24 V; ways 3, 4 carry nothing
    _j10e = conn_end("output_panel", "J10")
    _REC_Y = -121.5                       # along the board's -Y edge, inside the recess
    _REC_Z7 = -27.0                       # the J7 pair's centre height crossing it
    _BAY_X7, _BAY_X10 = -36.0, -31.0      # out of the endplate's -X face (-25.06); J7's
                                          # pair turns further out than the 24 V link, past
                                          # the optical 24 V lead's riser (OP.PWR_X_RISE)
    # THE LOOP: the J7 cable's 111 mm of balancing slack (see below) as ONE flat turn in the
    # bay above the output board. A full turn adds its whole circumference to the conductor
    # -- none of it is "the direct line" -- so its radius is 111 / 2 pi. It climbs 4 mm over
    # the turn so it can close without passing through itself, and its -Y point sits on the
    # wall line, where the cable arrives and leaves.
    _LOOP_R = 111.0 / (2.0 * math.pi)     # 17.67
    _LOOP_CX, _LOOP_CY = -52.5, CHAN_Y + _LOOP_R
    _LOOP_RISE = 4.0
    _RISE7 = _LOOP_CX - 4.5               # J7 climbs to its trough lane just past the loop
    _EXIT7 = CH_WT_RUNS[-1][0] - 2.0      # J7 leaves the trough where it stops, before
                                          # string 10's motor, and goes to that motor's tee

    def _loop(z0):
        """One clockwise turn (seen from +Z) from the loop's -Y point, climbing _LOOP_RISE."""
        return [(_LOOP_CX + _LOOP_R * math.cos(-math.pi / 2 - 2 * math.pi * k / 24),
                 _LOOP_CY + _LOOP_R * math.sin(-math.pi / 2 - 2 * math.pi * k / 24),
                 z0 + _LOOP_RISE * k / 24) for k in range(25)]

    # THE PAIR IS SPACED IN X *AND* Z, header to far end. Z alone keeps the two loops apart
    # (same radius, 2 mm apart in height, all the way round -- side by side they would
    # cross twice), but it does nothing where the path is VERTICAL: both conductors left
    # the same header point and rose through each other, 67 mm3 on J7's pair and 154 on
    # the link's -- invisible to the gate, which allow-lists wire against wire as insulated
    # crossings. X is the pin spacing on the connector; Z is the stack in the trough.
    def _pair(pts, dz):
        return [(x + dz, y, z) for x, y, z in pts]

    def _head(k, dz):
        """J7's way k -> the east-most tee's OUT way for the same net (on string 10's
        motor): along the trough lane, down beside the plug, and in through the mouth."""
        a, pin = _j7e[k][0], _tout[_WEST0][k][0]
        zr, zl = _REC_Z7 + dz, LANE_PWR + dz
        loop = _loop(zr)
        # the conductor on the -X pin rides the -X, lower lane and turns in first, so its
        # last run passes under nothing and its partner's passes over nothing
        ya = pin[1] - _HEAD_IN - (PWR_OFF - dz)
        # DOWN TO THE TEE'S LEVEL BESIDE WHERE THE TROUGH STOPS, not above the tee: at the
        # lane's height the run out to the tee passes through the UI clamp's underside
        # (-15.9). Out of the trough's line first: the 24 V link carries on along it below.
        z2 = pin[2] + PWR_OFF + dz
        tail = [(pin[0], ya, z2), (pin[0], ya, pin[2]), pin]
        return ([a, (a[0], a[1], zr), (a[0], _REC_Y, zr)]
                + _pair([(_BAY_X7, _REC_Y, zr), (_BAY_X7, CHAN_Y, zr)] + loop
                        + [(_RISE7, CHAN_Y, loop[-1][2]), (_RISE7, CHAN_Y, zl),
                           (_EXIT7, CHAN_Y, zl), (_EXIT7, CHAN_Y + _HEAD_OUT, zl),
                           (_EXIT7, CHAN_Y + _HEAD_OUT, z2), (_EXIT7, ya, z2)], dz)
                + [q for i, q in enumerate(tail) if i == 0 or q != tail[i - 1]])

    # ⚠ ON J7's WAYS 1 AND 2, AND INTO THE TEE ALONG ITS CONTACTS. The pair used to leave
    # the middle of the 4-way housing -- ground on way 3, which carries nothing -- and to
    # drop onto the tee's pins from above, through the top of a side-entry shell.
    # 11 straight into the mouth, not a crimp's length: the motor's own pigtail goes into the
    # drop connector beside this one, rising to the mouth over its last 8 mm, and the pair
    # has to cross it -Y of that rise, where the pigtail is still down on the motor.
    _HEAD_IN = 11.0
    _HEAD_OUT = 6.0                      # +Y of the trough's line before coming down
    for k in _cable("24 V head", _j7e, _tout[_WEST0][:2]):
        net = _j7e[k][2]
        _run(out, _NAME[net] + "_0", _head(k, -PWR_OFF if net == "GND" else PWR_OFF),
             WIRE_OD[_NAME[net]], "24 V head", k)

    # ⚠ AND THE LOOP ON _0 IS DELIBERATE RESISTANCE. The two feeds are wildly
    # asymmetric -- J7 reaches the chain far sooner than the motor board's J1 does -- so uncorrected the
    # east feed takes 5.6 of the 10 motors and the west 4.4. 111 mm of slack on the J7
    # cable brings it to 5.00/5.00, for 0.0059 ohm -- 0.07 % of 24 V at 3 A. Kept as a
    # PAIR through the turn: motor current is switched, and a pair that stays together
    # is bifilar, so its fields cancel instead of ringing against the drivers' input
    # capacitance.

    # ── THE 24 V LINK: output_panel J10 -> motor_ctrl J3, ALL SIX WAYS OF IT ─────────────
    # ⚠ THE SECOND FEED (option A, user 2026-09-18). The tee chain is fed from BOTH
    # ends now: J7 at the east, and this cable running the length of the instrument
    # to motor_ctrl's J3 at the west, from which J1 injects onto the chain. Current
    # enters at both ends and meets in the middle, so the worst-loaded segment
    # carries about half the fleet instead of all of it. It does NOT go through the
    # tees: it is a 4-way carrying ONLY power, so both +24V ways parallel and its
    # 582 mm behaves like 291.
    # ⚠ SIX CONDUCTORS, AS harness.PWR_LINK HAS THEM: GND, 24 V, the power button's two
    # throws, 24 V, GND. It was drawn as one pair out of the middle of each housing -- on
    # the two SWITCH ways -- and the throws were drawn nowhere, though they are the only
    # reason this lead is a 6-way.
    # ONE BUNDLE, two across and three high, which is what fits a trough 4.8 wide beside
    # the other two cables in it: the 24 V pairs top and bottom, the two thin throws in
    # the middle row. cadkit.bundle_paths carries that section round every corner.
    _PL_COL, _PL_ROW, _PL_HALF = PLINK_COL, PLINK_ROW, PLINK_HALF
    assert WIRE_OD["wire_plink"] == 1.8 and WIRE_OD["wire_usb"] == 2.6       # PLINK_HALF, LANE_PWR2
    _PL_OFFS = [(a * _PL_COL, b * _PL_ROW) for b in (-1, 0, 1) for a in (-1, 1)]
    _PL_ZREC = -35.3 + 0.2 + _PL_HALF          # the recess: 0.2 over J7's and J9's plug tops
    _PL_ZTR = LANE_PWR2                        # the trough: on its floor, under the USB lead
    assert _PL_ZREC + _PL_HALF < _REC_Z7 - PWR_OFF - 0.9, "the link is into J7's pair in the recess"
    # AT THE KEYHEAD it turns +Y out of the trough's end, comes down under the Pi's 5 V
    # leads (which cross it at J5's height) and under bus A's head, and runs +Y above the
    # cap, two abreast and three deep, to J3.
    _PL_XT = CH_WT_RUNS[0][0] - 3.0                              # clear of the trough's end face
    _j5z = EL.way_pt("motor_ctrl", "J5", 1)[2]
    _PL_ZKEY = _j5z - WIRE_OD["wire_5v"] / 2.0 - 0.25 - _PL_HALF
    # ⚠ J3 IS SIX WAYS STACKED IN Z at one x and y, on the standing board, and the corridor
    # in front of it is the foot strip's lead's as well (its four conductors come down the
    # board's face and cross to the cap's J6 at z -61.9, +Y and +X of here). No bundle can
    # arrive along J3's axis, and there is no room beside it for one to come down whole.
    # So the six come down as a 3 x 2 block of COLUMNS standing on J3's own line and the
    # one -Y of it, the nearest column over the mid-point of the plug's lead, and each
    # conductor leaves its column at its own way's height: the top way's column is the
    # nearest and ends first, so every lower conductor's last run passes where the ones
    # above it have already gone in. Each of the three levels of the run carries the pair
    # for one column pair -- top level to the top two ways -- and within a level the -X
    # lane turns in first, onto the line it reaches first, and the +X lane onto J3's own.
    # (The other side of J3 is the foot lead's; and with the lanes the other way round a
    # row's two conductors cross each other leaving J10.)
    _j3e = conn_end("motor_ctrl", "J3")
    _PL_LEAD = 1.25                    # straight out of the plug before anything turns: the
                                       # far column is then 0.4 off the cap's J6
    _PL_STEP = WIRE_OD["wire_plink"] + 0.1       # column to column
    _PL_PX, _PL_PY = _j3e[0][0][0] + _PL_LEAD, _j3e[0][0][1]
    _jc = [sum(e[0][m] for e in _j10e) / len(_j10e) for m in range(3)]
    _PL_Y0 = _jc[1] - 10.0             # the merge: at 4.0 a row's two conductors closed to 1.5
    _PL_REC_Y = _REC_Y + _PL_COL       # its -Y column on the line J7's pair takes, not past it
    _PL_RISE = CH_WT_X1 + 0.3 + _PL_HALF       # the climb into the trough, clear of its end face
    _pl_live = _cable("PWR_LINK", _j10e, _j3e)
    _pl_centre = [(_jc[0], _PL_Y0, _PL_ZREC), (_jc[0], _PL_REC_Y, _PL_ZREC),
                  (_BAY_X10, _PL_REC_Y, _PL_ZREC), (_BAY_X10, CHAN_Y, _PL_ZREC),
                  (_PL_RISE, CHAN_Y, _PL_ZREC)] + _lane(_PL_RISE, _PL_XT, _PL_ZTR) + [
                  (_PL_XT, CHAN_Y + 3.0, _PL_ZTR),
                  (_PL_XT, CHAN_Y + 13.0, _PL_ZKEY), (_PL_XT, _PL_PY - 10.0, _PL_ZKEY)]
    _PL_SHORT = {"GND": "gnd", "V24": "v24", "PWR_SW_UP": "up", "PWR_SW_DN": "dn"}
    _legs = bundle_paths(_pl_centre, _PL_OFFS, across=(0.0, 0.0, 1.0))
    # which slot is which, read off the run at the keyhead: level (z) picks the pair of
    # ways, lane (x) picks which of the two
    _by_z = sorted(range(6), key=lambda s: (round(_legs[s][-1][2], 2), _legs[s][-1][0]))
    _slot = {}
    for _lvl in range(3):
        _inner, _outer = _by_z[2 * _lvl], _by_z[2 * _lvl + 1]       # -X lane, +X lane
        _slot[2 * _lvl + 1] = _outer           # the even way (2, 4, 6): J3's own line
        _slot[2 * _lvl] = _inner               # the odd way (1, 3, 5): the line -Y of it
    # ...and at J10 the two conductors of a row have to leave it in their pins' own order,
    # or they cross on the way into the bundle
    assert all((_j10e[k][0][0] - _j10e[m][0][0])
               * (_legs[_slot[k]][0][0] - _legs[_slot[m]][0][0]) > 0
               for k in range(6) for m in range(k)
               if abs(_legs[_slot[k]][0][2] - _legs[_slot[m]][0][2]) < 0.01), (
        "the 24 V link: the bundle's section meets J10 with a row's two conductors crossed")
    assert all(abs(_legs[_slot[k]][0][2] - _PL_ZREC) < 0.01 for k in (2, 3)), (
        "the 24 V link: the two thin throws are not the bundle's middle row")
    for k in _pl_live:
        (pa, _d, net), (pb, _bd, _bn) = _j10e[k], _j3e[k]
        leg = _legs[_slot[k]]
        lx, lz = leg[-1][0], leg[-1][2]
        sx = _PL_PX + (2 - k // 2) * _PL_STEP          # ways 5, 6 nearest the plug
        sy = _PL_PY - (0.0 if k % 2 else _PL_STEP)
        pts = [pa, (pa[0], pa[1], leg[0][2])] + list(leg[:-1]) + [
            (lx, sy, lz), (sx, sy, lz), (sx, sy, pb[2])]
        if sy != _PL_PY:
            pts.append((sx, _PL_PY, pb[2]))
        if sx != _PL_PX:
            pts.append((_PL_PX, _PL_PY, pb[2]))
        _run(out, "wire_plink_%s_%d" % (_PL_SHORT[net], k + 1), pts + [pb],
             WIRE_OD["wire_plink_sw" if net.startswith("PWR_SW") else "wire_plink"],
             "PWR_LINK", k)

    # ── bus B (inputs): motor_ctrl J2 -> the lever boards ─────────────────
    # DRAWN IN ctrl_bus_b NOW, not here, and it is a different thing from what stood
    # here. This spot carried a TWO-conductor head -- CAN-H and CAN-L at +-CAN_OFF and
    # no GND or +5 V at all -- on a diagrammatic route out to _KNEE_B, a point 20 mm
    # short of LKL's board that the comment there called "as close as the chassis CAD
    # lets the trunk reach today", with the last few millimetres left as a follow-up.
    #
    # Bus B is a FOUR-wire bus (harness.PH_PINOUT: GND / +5 V / CAN_H / CAN_L) and the
    # lever boards run off its 5 V, so a head carrying only the CAN pair was not a
    # simplification, it was two missing conductors. ctrl_bus_b draws all four, onto
    # LKL's J1 ways 1-4 by way number, through the chassis floor's wiring port -- which
    # is also the follow-up that comment was waiting for.
    #
    # The two it drew are gone rather than kept alongside: they overlapped the real
    # cable (5.2 mm^3), which is what a duplicate of a run looks like to the gate.

    # -- USB (blue): USB-C panel -> -Y rail corridor -> ride to the bay -> right-angle to Pi
    # It leaves the OUTPUT PANEL BOARD's own USB-A now, not a panel coupler: the
    # panel USB-C is a part ON that board and its VBUS stops there, so what crosses
    # the instrument is the board-to-Pi lead. Starting it at the old panel-jack
    # position ran it straight through the relocated DC inlet.
    # The lane drops -X of the OUTPUT PANEL BOARD's own -X edge rather than at x -12,
    # which is where it used to go. -12 sat inside the relocated DC inlet (x -13.3..4.7)
    # AND inside the board's footprint; clearing the board is what also clears the jack.
    # It leaves J2 out of the board's -X edge through a USB-A plug standing _UA_PLUG past
    # the mouth, climbs to the trough's USB lane out in the bay -X of the J7 loop, and rides
    # the trough to the keyhead bay. (It used to run a floor corridor inside the pocket cut
    # into the rail; the trough replaced both.)
    # ⚠ THE SAME FROZEN y 20 AS wire_link, and check_cable_ends found it (2026-09-29): this
    # read SP(-575.0, 20.0, -44.0), which was on the Pi when it spanned y -50..35 and is 8.10 mm
    # off it now that the swap put the Pi at -135..-50. TWO leads to the Pi were stranded at its
    # old position; only wire_link happened to clip a wall and raise a gate pair. Derived from
    # the USB/ethernet block pi4() builds at PI_FP[3] - 9.0, like wire_link's.
    # ⚠ DERIVED FROM THE PORT NOW, not typed (user: "the USB for example enters the pi from
    # +x which doesn't seem like how the USB would be oriented"). The old point was tray
    # (-575, PI_FP[3]-9, -44) = world (-587.8, -55.18, -34.0), 1.8 mm inside the USB block's
    # outer face, and the lead ran IN ALONG WORLD X at z -15 through the block's interior to
    # stop in the middle of it -- approaching the component face from +X exactly as described.
    # It now lands in the upper USB stack on the +Y END and is approached from +Y, which is
    # the only direction a USB-A plug can enter. See EL.pi_port_pt.
    # NOT through SP(): pi_port_pt returns WORLD coords now -- the Pi lies flat and no
    # longer stands, and standing these again is what put this lead inside motor_ctrl.
    _usb = EL.pi_port_pt("usb3")
    # ⚠ THE GAP IS 4.68 mm AND NO USB PLUG FITS IN IT -- see the block above _MCTRL_CY.
    # The approach runs inside that real gap rather than pretending to a wider one: the lead
    # reaches the right port from the only direction a plug could enter, and the fact that
    # the plug itself has nowhere to go is a placement problem recorded where placement is.
    # THE GAP IS 11.68 mm NOW and a right-angle USB-A plug fits (2026-09-29):
    # motor_ctrl's BOARD_L went 62.0 -> 55.0 off its bare Pi-facing edge and _MCTRL_CY
    # -10.5 -> -7.0 held the +Y edge, so the boards leave y -46.18..-34.50. The approach
    # sits MID-GAP, where the plug body actually lives, instead of hugging the port face
    # because there was nowhere else to be.
    # ⚠ THE APPROACH IS IN +X NOW, NOT +Y, AND THAT IS THE HALF THAT WAS MISSING LAST TIME.
    # Moving the ports to the +X end without moving this drove BOTH cables through the board
    # to reach them: wire_usb 0.000 -> 134.864 mm^3 and wire_link 0.000 -> 71.444, and the
    # GATE REPORTED AN IMPROVEMENT (17 -> 16) because pi4 is in both wires' allow-list. The
    # ports and their approach are one change; they cannot land separately.
    # ⚠ AND THE PORTS FACE +X BECAUSE NOTHING ELSE FITS -- measured, not chosen: motor_ctrl's
    # +X face is 3.70 mm off the Pi's -X edge, and no USB-A plug fits in 3.70 (a right-angle
    # one is ~10). The +X end is open. So the Pi does NOT rotate; the pose was right and only
    # the port frame was wrong.
    _PORT_APR_X = EL.PI_FP[1] + 20.0               # -483.0: clear of the +X face + a plug
    _ua = EL.op_mouth("J2")          # was op_pt: J2's +Y FACE, 7.300 mm off its axis
    _UA_PLUG = 20.0                  # a USB-C plug's overmould (J2 was a USB-A, 25, until
                                     # 2026-10-02)
    # ITS OWN COLUMN at the keyhead, 6 mm +X of the one the bay wires share: at a different
    # fly height in the shared column it met the OLED lead's drop instead (24.9 mm3). Here it
    # flies over string 1's motor, well above its top.
    _USB_COL = BAY_X + 6.0
    _USB_FLY = BAYFLY - 3.0               # under the Pi link's fly, which it crossed at the Pi
    _ua_x = _ua[0] - _UA_PLUG           # the plug's cable end. Was measured from the EAR TIP,
                                        # 10.000 mm short of the mouth -- see EL.op_mouth
    _USB_X = _LOOP_CX - _LOOP_R - 9.5     # -X of the loop, +X of the trough's end
    _run(out, "wire_usb",
         [(_ua_x, _ua[1], _ua[2]), (_USB_X, _ua[1], _ua[2]), (_USB_X, _ua[1], LANE_USB)]
         + _lane(_USB_X, _USB_COL, LANE_USB)
         + [(_USB_COL, CHAN_Y, _USB_FLY), (_USB_COL, _usb[1], _USB_FLY),
            (_PORT_APR_X, _usb[1], _USB_FLY), (_PORT_APR_X, _usb[1], _usb[2]), _usb],
         WIRE_OD["wire_usb"])                           # over motor 0, then down into the Pi

    # -- 5 V to the Pi's GPIO header, from the merged board's J5. It was never
    #    modelled while the power board existed -- that board fed the Pi and nothing
    #    drew the cable -- so the harness has been a connector short all along.
    # It rides ABOVE the board tops between the two connectors and only drops at the
    # Pi. Run level with the header it started from, it grazed the tray plate.
    # ⚠ IT LANDS ON THE PI CAP'S J2 NOW, PIN BY PIN, not on a guessed point over the header.
    # It used to end at a hardcoded (-596, -38, -57) "GPIO" point, which is why the gate had
    # it 55 mm3 inside the cap: there was nothing for it to land ON until that board existed.
    # Four conductors, drawn as four, in J2's own order -- GND, +5V, +5V, GND -- each with a
    # straight LEAD-IN out of the mouth so the pin order reads off the model. Same idea as
    # tee_pin() on the CAN tees.
    # ⚠ REDRAWN FROM THE ROUTED PADS (2026-10-06), BOTH ENDS. The motor end came from
    # EL.mctrl_pin, which answered in the flat tray's coordinates under a docstring that
    # said world: all four conductors started 25.6 mm from J5, in air, with their y right
    # to 0.2 mm -- which is why it looked plausible. And the cap end went into J2 along
    # the board's normal, through the body of a side-entry housing whose mouth faces -Y.
    # ⚠ STRAIGHT, WAY n TO WAY n. It was drawn crossed (way 1 to way 6) because that
    # un-crossed the drawing and the connector is a palindrome, so nothing electrical
    # changed. A lead built to the drawing would still have been a crossed lead; the
    # nesting below does the same job without it.
    # Each conductor leaves J5 along the board's normal at J5's own height -- over the cap,
    # over the 24 V link -- turns -Y in its own column, comes down past the cap's -Y edge to
    # J2's height, runs +X to its own way and goes in through the mouth. Way 1 is the
    # -Y-most at J5 and the +X-most at J2, so it takes the outside of every turn: first to
    # turn -Y, last (furthest -Y) to turn +X.
    _v5a, _v5b = conn_end("motor_ctrl", "J5"), conn_end("pi_cap", "J2")
    _lta, _ltb = conn_end("motor_ctrl", "J7"), conn_end("pi_cap", "J4")
    _LT_IN = 2.0                                    # the least run straight into J4's mouth
    _LT_PITCH = EL.MCTRL_J7_PITCH
    _LT_YL = _ltb[0][0][1] - _LT_IN                 # the lights' +X lanes start here, going -Y
    _V5_PITCH = 2.0                                 # O1.8 conductors side by side
    _V5_X0 = _PL_XT + _PL_COL + 0.9 + 3.6           # the first column: +X of the 24 V link's run
    _V5_Y0 = _LT_YL - 3 * _LT_PITCH - 2.2           # the last +X run: -Y of the lights' lanes
    _v5_live = _cable("PI_5V_LINK", _v5a, _v5b)
    for n, k in enumerate(_v5_live):
        (pa, _d, net), (pb, _bd, _bn) = _v5a[k], _v5b[k]
        xt = _V5_X0 + n * _V5_PITCH
        yl = _V5_Y0 - (len(_v5_live) - 1 - n) * _V5_PITCH
        _run(out, "wire_5v_%s_%d" % (net.lower(), k + 1),
             [pa, (xt, pa[1], pa[2]), (xt, yl, pa[2]), (xt, yl, pb[2]), (pb[0], yl, pb[2]), pb],
             WIRE_OD["wire_5v"], "PI_5V_LINK", k)

    # ── THE LIGHTS LINK: motor_ctrl J7 -> pi_cap J4 (harness.LIGHTS_LINK) ────────────────
    # Fused 24 V and ground for every LED in the instrument, and the power button's two
    # throws on their way from the UI ribbon to the output board. NOT DRAWN AT ALL until
    # 2026-10-06: two connectors with nothing in them, and the lights' only feed.
    # J7's four ways are stacked in Z low on the standing board, facing the corridor
    # between the cap and string 1's motor; J4 faces -Y off the far side of the cap.
    # ⚠ UNDER THE FOOT STRIP'S LEAD, WHICH CROSSES THIS CORRIDOR RIGHT IN FRONT OF J7
    # (z -61.9, at J7's own y among others). So the four run +X along the floor as a
    # 2 x 2, below it, until they are past it; each then climbs in its own column to just
    # over the cap, runs -Y across the cap, comes down past its edge to J4's height, and
    # runs +X to its own way and in through the mouth.
    # ⚠ WAYS 3 AND 4 START BELOW THE FLOOR'S TOP: the board hangs through the floor and J7
    # is low on it. They side-step and rise to ways 1 and 2's heights inside the trench
    # electronics.mctrl_wire_relief cuts for them, and run beside those two.
    # ⚠ ACROSS THE CAP BETWEEN J3 AND J4, NOT AT J4's OWN x: J5 -- the UI ribbon's header --
    # faces the corridor from the cap's +Y edge at the very x J4 has on the -Y edge, and
    # the ribbon comes straight down in front of it.
    assert WIRE_OD["wire_lights"] == EL.MCTRL_J7_WIRE
    _capbb = EL.pi_cap().val().BoundingBox()
    _LT_FLY = _capbb.zmax + WIRE_OD["wire_lights"] / 2.0 + 2.85
    _LT_XC = min(e[0][0] for e in _ltb) - 2.0       # the last column: 2.0 -X of J4's last way
    _lt_live = _cable("LIGHTS_LINK", _lta, _ltb)
    for n, k in enumerate(_lt_live):
        (pa, _d, net), (pb, _bd, _bn) = _lta[k], _ltb[k]
        # ways 1, 2 on J7's own line at their own heights; 3, 4 beside them at the same two
        row, lvl = n // 2, n % 2
        y, z = pa[1] + row * EL.MCTRL_J7_SIDE, _lta[_lt_live[lvl]][0][2]
        # on each line the upper conductor climbs first, so the lower passes under its column
        xc = _LT_XC - (3 - (2 * row + lvl)) * _LT_PITCH
        yl = _LT_YL - (3 - n) * _LT_PITCH
        pts = [pa]
        if row:
            xs = pa[0] + EL.MCTRL_J7_LEAD + lvl * _LT_PITCH
            pts += [(xs, pa[1], pa[2]), (xs, y, pa[2]), (xs, y, z)]
        pts += [(xc, y, z), (xc, y, _LT_FLY), (xc, yl, _LT_FLY), (xc, yl, pb[2]),
                (pb[0], yl, pb[2]), pb]
        _run(out, "wire_lights_%s_%d" % (_PL_SHORT[net], k + 1), pts,
             WIRE_OD["wire_lights"], "LIGHTS_LINK", k)

    # ── THE LED HARNESS IS NOT DRAWN HERE ANY MORE, AND THAT IS BRENNER'S CALL ────
    # Three blocks stood here: the cap's J3 to strip section 0, the three section-to-
    # section jumpers, and the J4 power stub. main has NONE of them -- brenner moved the
    # whole lighting harness out of this file (see docs/lighting-bus.md), and the user
    # owns that system to brenner (2026-09-30: "brenner owns the LED system, you
    # shouldn't modify it"). So this is main's removal kept, not a merge casualty.
    # ⚠ IT ALSO FIXES A REAL BREAK: those blocks took their gauge from
    # WIRE_OD["wire_oled"], and main renamed that key to "wire_ui" when the OLED and
    # joystick became one ribbon. Keeping them would have been a KeyError at import.

    # -- motor controller <-> Pi (purple): the USB lead the Pi writes travel offsets over --
    #    a stock USB-A -> XH lead now, off J4's top like every other lead on the board
    #    (the USB-C it replaced faced the -Y rail 5.5 mm away and could not be plugged in).
    # ⚠ THE PI END WAS A HARDCODED y 20 AND THE PI IS NOT THERE ANY MORE (2026-09-29). It read
    # SP(-585.0, 20.0, -58.0); pre-swap the Pi spanned y -50..35 so 20 was on the board, and
    # after the swap it spans -135..-50 -- so this lead ended in OPEN AIR where the Pi used to
    # be, and grazed the chassis on the way (chassis_2 <-> wire_link). A cable that does not
    # reach its connector is worse than an overlap: the gate can see the overlap.
    # Derived now, from the Pi's USB/ethernet block, which pi4() puts at PI_FP[3] - 9.0 -- so
    # it follows the board instead of being falsified by it. That is the FIFTH constant this
    # swap invalidated (root_d's 13 beads, MCTRL_HOLE, the 5 V leg, _FEED2_X, and this).
    _lt = SP(*EL.mctrl_pt("J4"))
    _lp = EL.pi_port_pt("usb2")        # the other USB stack; WORLD, not through SP()
    # ITS OWN COLUMN, 3 mm short of the bay column: J4 is on the board's -Y edge, at the very
    # y where bus B drops down the bay column to the floor corridor.
    # It crosses motor 0's Y band, so it takes the BAYFLY lane over the motor top
    # like every other bay wire -- running it across at the board's own height put
    # 62 mm3 of cable inside string 1's motor.
    _LINK_X = BAY_X - 3.0
    _LINK_RISE_X = _lt[0] + 2.8          # -590.7: -X of bus A's first riser
    out.append(("wire_link", _wire([
        _lt, (_LINK_RISE_X, _lt[1], _lt[2]), (_LINK_RISE_X, _lt[1], BAYFLY),
        (_LINK_X, _lt[1], BAYFLY), (_LINK_X, _lp[1], BAYFLY),
        (_PORT_APR_X, _lp[1], BAYFLY), (_PORT_APR_X, _lp[1], _lp[2]), _lp],
        WIRE_OD["wire_link"])))

    # (the Teensy <-> transceiver CAN jumper pair is GONE: the transceivers now sit
    #  on the same board as the MCU, so that harness is copper instead of wire.)

    # (wire_tdm is GONE with adc_stack: the ten-channel ADC carrier it fed is
    #  deleted, the optical pickup board having absorbed that conversion.)

    # -- UI: the UI board's ribbon -> the Pi's GPIO header. It leaves J2's mouth at
    #    the board's -X edge (which is why that header is a right-angle part), runs -X
    #    under the deck to the keyhead, and drops down the bay column onto the Pi.
    #    The two placeholder runs that stood here -- one for "the OLED" and one for
    #    "the joystick", each from a guessed deck position -- are gone: there is one
    #    cable, and its end is a routed connector rather than a coordinate.
    #    AND IT IS DRAWN AS THE FOURTEEN CONDUCTORS IT IS. It stood here as one round
    #    4.8 run, which is what a jacketed cable looks like and this is not one -- it is
    #    a 1.27 flat ribbon off an IDC header, 17.8 across and 0.9 thick. A round stand-in
    #    hides the only thing about it that constrains anything: its WIDTH, and which way
    #    that width is turned. (user asked what the thick wire was, 2026-09-28)
    ux, _uy = UI.board_centre()
    umz = UI.z_stack()[4] + 4.5                  # the ribbon's axis out of the shroud
    uy = UI.routed("J2")[1]                      # the header's own row, as routed
    ex = ux - UI.BOARD_W / 2.0 - 2.0
    #    THE WIDTH LIES ALONG Y, which is what lets it make the one turn it has to. The
    #    run goes -X under the deck and then straight down the bay column; a ribbon whose
    #    width is perpendicular to both sweeps that corner as fourteen concentric arcs,
    #    every conductor keeping its own place. Turned the other way it would have to
    #    fold, and a fold is a crease in a part that gets pulled every service.
    #    ⚠ ONTO THE CAP'S J5, WHICH IS WHERE IT PLUGS IN (2026-10-06). It ended at a typed
    #    point, SP(-600, -40, -57): 65.8 mm from the header, on the far side of the
    #    standing motor board. J5 is a right-angle 2x8 on the cap's +Y edge, mouth to the
    #    corridor between the cap and string 2's motor, and an IDC socket's ribbon leaves
    #    its BACK, square to the mating axis. So the ribbon runs -X under the deck as it
    #    always did, folds once to run +Y at the header's own x, and comes straight down
    #    in front of the header onto the socket, its width along the pin row.
    _j5f = BG.footprint("pi_cap", "J5")
    _j5pads = _j5f["pads"].values()
    _o5, _a5 = EL.board_frame("pi_cap")

    def _cap_pt(bx, by, bz):
        return tuple(_o5[m] + _a5[0][m] * bx + _a5[1][m] * by + _a5[2][m] * bz for m in range(3))

    _j5h = BG.HEIGHT[BG.fp_name(_j5f["fpid"])]
    _pad_y = sum(q[1] for q in _j5pads) / len(_j5pads)
    _mouth_y = max(_j5f["fab"][2:], key=lambda v: abs(v - _pad_y))         # the end away from the pads
    _j5c = _cap_pt((min(q[0] for q in _j5pads) + max(q[0] for q in _j5pads)) / 2.0, _mouth_y,
                   EL._CAP_T + _j5h / 2.0)
    assert abs(_a5[1][1]) > 0.99 and abs(_j5f["fab"][3] - _j5f["fab"][2]) < abs(
        _j5f["fab"][1] - _j5f["fab"][0]), "pi_cap J5's row no longer runs along world X"
    _J5_SOCKET = 3.0                # the IDC socket's ribbon slot, out from the header's mouth
    _ry = _j5c[1] + _J5_SOCKET * (1.0 if _a5[1][1] * (_mouth_y - _pad_y) > 0 else -1.0)
    centre = [(ex, uy, umz), (ex - 12.0, uy, umz), (_j5c[0], uy, umz),
              (_j5c[0], _ry, umz), (_j5c[0], _ry, _j5c[2])]
    #    ...AND IT IS ONE PRISM, NOT FOURTEEN SWEEPS (user, 2026-09-28). It was drawn
    #    as fourteen conductors from bundle_paths, one octagonal solid each, which is the
    #    truth about a ribbon and the wrong model of it: nothing inside a ribbon can move
    #    relative to anything else, so the fourteen only ever add up to the rectangle they
    #    fill -- and they cost fourteen solids in every boolean the overlap gate runs. The
    #    one thing the fourteen bought was catching the width turned the wrong way, and
    #    flat_cable asserts that instead.
    #    BOTH ITS CORNERS ARE FOLDS, not bends -- the run is flat and both turns are in
    #    the ribbon's own plane, so each is a 45 degree crease. That is what flat_bends
    #    says and what UI.RIBBON_FOLDS declares; a reroute that adds a third crease has
    #    to admit to it here rather than appear in the assembly as a surprise.
    _bends = flat_bends(centre, across=(0.0, 1.0, 0.0))
    _folds = [v for v, k, _d in _bends if k == "fold"]
    PATHS["wire_ui"] = (centre, UI.RIBBON_W)
    assert len(_folds) == UI.RIBBON_FOLDS, (
        "the UI ribbon's path folds %d times, not the %d declared: %r"
        % (len(_folds), UI.RIBBON_FOLDS, _bends))
    out.append(("wire_ui", flat_cable(centre, UI.RIBBON_W, UI.RIBBON_T,
                                      across=(0.0, 1.0, 0.0))))

    # ── the magnetic pickup -> the output panel's screw terminals ────────────
    # ⚠ THE PICKUP END MOVES AND THE PANEL END DOES NOT. The pickup rides the
    # height plate: three M4 leadscrew jacks lift and tilt it, and it slides in X
    # for tone. So this cable is drawn at the pose the rest of the build shows and
    # the REAL one needs slack for the plate's travel -- that is an assembly note
    # (INSTALL_NOTES), not geometry, because modelling a service loop would only
    # invent a shape nobody has to build to.
    #
    # It leaves the coil's UNDERSIDE at the -Y end, which is both where a bar
    # pickup's leads actually exit and the end nearest J8: the terminal sits at
    # y -57.45 and the pickup's -Y edge at -51.5, so the two face each other.
    # J8's wire entry is taken as +Y, matching op_pt's convention for this board;
    # the footprint is nearly symmetric front-to-back (fab -3.85/+4.05 about the
    # pads) so if that is ever shown to be backwards it is an 8 mm correction here
    # and nothing else moves.
    from . import pickup_mount as _PM, top_plate as _TP
    # ...and THROUGH THE HEIGHT PLATE'S LEAD SLOT: the pickup rests on that plate, so a lead
    # off its underside went straight through 2.4 mm of plastic (11.5 mm3) until the slot.
    _pk_x, _pk_y = _TP.PICKUP_X_NOM, _TP.LEAD_SLOT_Y    # coil underside, -Y end
    _j8 = EL.op_pt("J8")
    out.append(("wire_pickup", _wire([
        (_pk_x, _pk_y, _PM.PK_BOT),        # leaves the coil's underside
        (_pk_x, _pk_y, _j8[2]),            # straight down, clear of the plate
        (_pk_x, _j8[1] + 10.0, _j8[2]),    # -Y in its own X column
        (_j8[0], _j8[1] + 10.0, _j8[2]),   # +X to the terminal's column
        _j8], WIRE_OD["wire_pickup"])))

    check_cables([k for k in _CABLES if not k.startswith("bus B")])
    return out


# The lever stations' sensor boards (connector and all), as the assembly names them. The prefixes
# mirror src.build.LEVER_STATIONS (LKL keeps the bare names); a station this does not
# list simply gets no allow-list entry, which fails LOUD rather than silently.
_LEVER_PREFIX = ("", "vkl_", "lkr_", "rkl_", "rkr_")
_LEVER_CONNS = {p + n for p in _LEVER_PREFIX
                for n in ("kl_pcb", "kv_pcb")}
# ...and the HOUSINGS, for the coil alone: it is wound ON the keeper barrel, which is
# part of the housing, so cable-on-keeper is a designed contact in the same way
# cable-on-connector is. The straight RUNS get no such licence -- a run that touches a
# housing is a routing fault, which is the whole point of a whitelist.
_LEVER_BODIES = _LEVER_CONNS | {p + n for p in _LEVER_PREFIX
                                for n in ("knee_housing", "kv_housing")}

# what each net is ALLOWED to touch (its source/destination bodies);
# everything else a wire grazes is a routing bug the gate reports
# ...and the leg's four conductors are keyed FROM THE PINOUT (elec.harness), so a
# renamed circuit cannot quietly drop out of the allow-list the way "5v" did when the
# pin order became the source of the name. Each may clip the connector bodies it
# actually enters, and its own plug -- nothing else.
# NAMED PER JOINT, because check_overlaps' base() strips only a trailing INDEX group:
# "pogo_male_ph_top" is its own base, and a bare "pogo_male_ph" here matches nothing.
_POGO_ENDS = {"pogo_%s_%s_%s" % (side, body, end)
              for side in ("male", "female") for body in ("ph", "board")
              for end in ("top", "bottom")}
WIRE_OK = {
    # the two bodies it terminates on, and nothing else: it crosses the bay in open air
    "wire_pickup":    {"pickup", "output_panel"},
    "wire_canh":      {"motor_ctrl", "tee_pcb"},
    "wire_canl":      {"motor_ctrl", "tee_pcb"},
    # (wire_canbh/l are no longer drawn -- see bus B in trunk(). WIRE_OD still carries
    #  their gauge, which is what CANB_WIRE_OD is asserted against.)
    # bus B through the KNEE LEVERS (lever_bus). A segment may touch the connectors it
    # runs between -- and nothing else: every housing, cradle, magnet or axle it grazes
    # is a routing bug, which is the whole reason this table is a WHITELIST.
    # ...and a station's parts carry its PREFIX (LKL keeps the bare names, the rest
    # are `vkl_`, `lkr_`, ... -- src.build.LEVER_STATIONS), which check_overlaps' base()
    # does not strip: it strips trailing INDEX groups only. So the allow-list has to
    # name them as the assembly does.
    "wire_canb_coil":  _LEVER_BODIES,
    # ...the four conductors are added below, where CANB_NETS is defined (this table
    # is read at import by tools.check_overlaps, so it only has to be complete by then)
    "motor_pigtail":  {"tee_pcb", "motor"},
    # leg↔body TRRS: the chassis jack's factory cable (tenon channel ->
    # bus-B socket tee) and the column CA-354S inside the leg stack
    # (it used to land on tee 12; that tee is deleted and the TRRS ADAPTER BOARD
    #  carries the jack instead -- the adapter has no station in the CAD yet)
    "chassis_trrs_cable": {"leg_body_stub", "chassis_trrs_jack",
                           "jack_seat_ring"},
    "leg_column_cable": {"leg_body_stub", "leg_segment", "leg_sleeve",
                         "leg_shaft", "leg_column_plug",
                         "leg_plug_retainer", "leg_cable_coil",
                         "leg_head", "leg_junction_pcb",
                         "leg_seg_body", "leg_lid",
                         # the shaft-side model of the SAME physical
                         # CA-354S — they abut inside the shaft channel
                         "pedal_trrs_cable_leg"},
    "leg_cable_coil":   {"leg_segment", "leg_seg_body", "leg_sleeve",
                         "leg_column_cable", "shaft_trrs_cable"},
    "shaft_trrs_cable": {"leg_shaft", "leg_sleeve", "leg_seg_body",
                         "shaft_trrs_jack", "leg_cable_coil",
                         "leg_junction_pcb", "leg_head"},
    # THE LEG's POGO HARNESS (src.leg_pogo), four conductors and the slack coil. They
    # are allowed against each OTHER and nothing else: wire-to-wire is automatic once a
    # base is in here, and these four are one twisted bundle, so they touch at every
    # corner by construction -- but any of them clipping a SOLID is a routing bug, and
    # that is exactly what this table is for.
    "wire_pwr_hot":   {"output_panel", "tee_pcb", "motor_ctrl"},
    "wire_pwr_gnd":   {"output_panel", "tee_pcb", "motor_ctrl"},
    # ⚠ pi_cap, NOT pi4, AND IT IS THE SAME FAULT AS THE BUS-B ENTRY BELOW: the declared
    # far end was the wrong PART. This cable is drawn to EL.pi_cap_pin("J2", n) -- it lands
    # on the cap's connector, pin by pin -- and pi4 is only what it passes under on the way,
    # at 0.1 mm3 of graze. Declaring pi4 therefore did two wrong things at once: it made the
    # cable's real landing on pi_cap read as FOUR unintended overlaps of 40.5 mm3 each, and
    # it allow-listed the Pi, which is the part a future mistake would most like to hide in.
    # WIRE_OK is the overlap gate's allow-list as well as a wiring declaration, so a wrong
    # name here does not just mislabel -- it silences.
    # pi4 is deliberately NOT added back. The 0.1 mm3 is residual, not designed (the note at
    # the cable says the under-Pi lane leaves "the three connector-adjacent contacts"), so it
    # stays visible as the small real thing it is rather than being covered over.
    "wire_5v":        {"motor_ctrl", "pi_cap"},
    "wire_plink":     {"output_panel", "motor_ctrl"},
    "wire_lights":    {"motor_ctrl", "pi_cap"},
    "wire_opt":       {"optical_plug_pwr", "output_panel"},
    "wire_usb":       {"output_panel", "pi4"},
    "wire_link":      {"motor_ctrl", "pi4"},
    "wire_ui":        {"ui_pcb", "pi4"},
}

# ...and the body-side run of the same cable ends on the motor controller, which is the
# one part outside the leg that a pogo_wire_* is allowed to touch (wiring.ctrl_bus_b).
WIRE_OK.update({"pogo_wire_%s" % n.lower(): set(_POGO_ENDS) | {"motor_ctrl"}
                for n in EH.PH_PINOUT})
# the two lighting leads (src/led_leads.py), four conductors each: the foot strip's board
# A to the Pi cap's J6, and the keyhead fret board to its J3
WIRE_OK["wire_foot_led"] = {"foot_pcb_a", "pi_cap"}
WIRE_OK["wire_fret_led"] = {"fret_pcb_key", "pi_cap"}


# THE BAYS' BACK WALLS reach to MB.HARNESS_Y1 now, so a tee still ON THE RAIL must not fall
# inside a bay's footprint -- a housing would be built straight on top of it. Tested against the
# real bay box (both axes: tee 11 sits inside the bank in X but well +Y of any back wall).
for _i, (_tx, _ty, _td) in enumerate(tee_stations()):
    if on_motor(_i):
        continue
    _bw, _bl, _bcx, _bcy, _o, _he, _ha = tee_hold(_i, _tx, _ty, _td)
    for _m in range(D.N_STRINGS):
        _mx0, _mx1, _my0, _my1, _mz0, _mz1 = MB.body_box(_m)
        _bay = (_mx0 - MB.side_room(_m, -1), _mx1 + MB.side_room(_m, 1),
                _my0 - MB.BACK_T, _my1 + MB.PLATE_T)
        assert not (_bcx - _bw / 2 < _bay[1] and _bcx + _bw / 2 > _bay[0]
                    and _bcy - _bl / 2 < _bay[3] and _bcy + _bl / 2 > _bay[2]), (
            "tee %d lands inside string %d's bay (x %.1f..%.1f, y %.1f..%.1f)"
            % (_i, _m + 1, _bay[0], _bay[1], _bay[2], _bay[3]))


# ── BUS B THROUGH THE KNEE LEVERS, and the CUT LIST ─────────────────────────
# Until now bus B stopped at the first lever board: the tees that used to carry it on
# were deleted when the boards started passing the trunk through their own 8-way, and
# nothing replaced the run. So the instrument's most position-dependent harness was the
# one length nothing measured.
#
# THIS IS MEANT TO BE THE SOURCE OF TRUTH FOR CUTTING (user, 2026-09-22). Every number
# below is read off the parts -- the plug's own cable end and the lace loop's bore,
# through knee_lever.plug_point / lace_point -- so the cut list cannot drift from the
# levers it is cut for. `lever_bus` returns the drawn runs AND their lengths from the
# same polylines, for the same reason: a report computed separately is a second model.
#
# THE SLACK IS A COIL, not a fold: a helix is one swept solid (3 faces) where a folded
# hank drawn in octagonal segments is ~1200, and there is one per lever (user, and
# brenner's finding on the leg harness). It is wound on the run's own axis, marching
# along it, which is how a service loop actually lies.
#
# ⚠ ONE BUNDLE, NOT FOUR CONDUCTORS, for now. brenner's harness draws each conductor
# separately and squares it out of its own pin, which is the better drawing and the one
# to converge on; `cadkit.cables.bundle_paths` and `helix_cable` are on their branch and
# not in main yet (branner asked the lead to take it, 2026-09-22). The CUT LIST is
# unaffected: four conductors of a bundle are cut to the bundle's length, and the table
# below multiplies by CANB_WAYS to say so.
CANB_BUNDLE_OD = _KL.CANB_BUNDLE_OD      # the four together; the KEEPER is sized
CANB_WIRE_OD = _KL.CANB_WIRE_OD          # from these, so knee_lever owns them
assert CANB_WIRE_OD == WIRE_OD["wire_canbh"], (
    "the lever bus's conductor and the CAN pair's have drifted apart")
# THE FOUR CONDUCTORS, DRAWN AS FOUR AND COLOURED AS FOUR (user, 2026-09-22), in
# harness.PH_PINOUT order, with the instrument's own cable colours (black GND, red +V,
# yellow CAN_H, green CAN_L -- see _COLORS in src.build). The offsets lay them in a
# square bundle: this is a CONSTANT lateral offset, not a swept frame, so a conductor
# keeps its place along the whole run but the bundle does not twist round corners the
# way brenner's cables.bundle_paths does. That is the one to converge on when their
# branch lands; the lengths differ by well under the crimp allowance either way.
CANB_NETS = (("gnd", (-1, -1)), ("v5", (1, -1)), ("h", (-1, 1)), ("l", (1, 1)))
CANB_WAYS = len(CANB_NETS)          # GND / +5 V / CAN_H / CAN_L (harness.PH_PINOUT)
# SQUARE OUT OF THE PLUG far enough to clear the BOARD the plug stands on -- the crimp
# holds the wire in line for its own length anyway, and a 1.6 lead turned the run while
# it was still over the PCB.
CANB_LEAD = 8 * D.BEAD              # 6.4
# THE SLACK ONE SEGMENT CARRIES. A lever steps on the chassis bottom's mortise grid, so
# two neighbours moving two steps apart each is 4 * D.LEVER_PITCH; the rest is the
# service slack to unplug a board and lift it out of its cradle. INSTALL_NOTES KL-2.
CANB_SLACK = 4 * D.LEVER_PITCH + 25.0            # 66.6
# ⚠ WOUND 0.4 OFF THE BARREL, NOT ON IT (lead, 2026-10-01). At the barrel's own wound
# radius the coil is in EXACT tangent contact with the housing's post along its whole
# length -- BRepExtrema 2.4e-13 mm -- and a pair that is tangent to 1e-13 survives a fresh
# intersect (0.0) but SEGFAULTS it after a BREP save/reload, which is what the scratch
# cache does. A real hank is not a press fit on its post either. One bead of air.
CANB_COIL_CLR = D.MIN_WALL / 2.0    # 0.4
CANB_COIL_R = _KL.KEEP_COIL_R + CANB_COIL_CLR
CANB_COIL_UP = 2 * D.BEAD            # 1.6 -- see lever_bus
CANB_COIL_PITCH = 4 * D.BEAD        # 3.2 march per turn -- a bundle laid beside itself
def _coil_layers():
    """[(radius, turns)] -- the slack wound in LAYERS, outer wraps riding on inner ones.

    A coil is not limited to one wrap deep (user, 2026-09-23: "you can wrap wire around
    itself so the outer wraps have a larger diameter"), and that is what a hand-wound
    hank actually is. It matters because it takes the capacity question off the COLUMN:
    turns-per-layer set the post's height, layers set the capacity, and a layer costs
    nothing in Z. Before this the post had to be either tall (it ran the whole depth of
    the vertical lever) or fat (to carry the slack in fewer turns), and neither fitted
    under a 45 deg buttress on the 28.5 housing.

    Each layer is one bundle further out, so it holds more per turn than the one under
    it -- which is why the last layer is usually a part-layer.
    """
    per = max(1, int(_KL.KEEP_WIND_H // CANB_COIL_PITCH))
    left, out, r = CANB_SLACK, [], CANB_COIL_R
    while left > 1e-6:
        n = min(per, max(1, math.ceil(left / (2.0 * math.pi * r))))
        out.append((r, n))
        left -= n * 2.0 * math.pi * r
        r += CANB_BUNDLE_OD
    return out


def _coil_len(layers):
    """A wound hank's true length: each layer's helix, at its own radius."""
    return sum(n * math.hypot(2.0 * math.pi * r, CANB_COIL_PITCH) for r, n in layers)


def _coil_path(origin, axis, r, turns, up=True):
    """One LAYER's helix. Its ends are where the straight runs have to ARRIVE: a helix
    of radius r about `origin` does not start AT origin, it starts a radius out from
    it, and runs drawn to the axis instead left a gap at both ends of every coil.

    `up` False walks the layer back down the post, which is what the next layer does --
    you do not cut the wire and start again at the bottom."""
    ax = cq.Vector(*axis).normalized()
    h = turns * CANB_COIL_PITCH
    o = cq.Vector(*origin) if up else cq.Vector(*origin) + ax * h
    return cq.Wire.makeHelix(CANB_COIL_PITCH, h, r, o, ax if up else ax * -1)


def _coil(path, d=CANB_BUNDLE_OD):
    """The slack coil as ONE swept solid.

    A round profile on a true helix: 3 faces, against ~1200 for the same coil cut into
    octagonal segments. The rule this bends (cables are octagonal here because fusing
    many round segments loses material silently) is about the BOOLEAN, not the shape --
    a sweep is not a fuse -- so it holds as long as the coil stands as its own part and
    its ends stay clear of the octagonal run that feeds it.

    ⚠ This is cadkit.cables.helix_cable in all but name, and should BE it once brenner's
    branch lands in main; main's cables.py still has only helix_pts."""
    prof = cq.Wire.makeCircle(d / 2.0, path.startPoint(), path.tangentAt(0.0))
    return cq.Workplane("XY").add(cq.Solid.sweep(prof, [], path, isFrenet=True))


def _path_len(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))



def _standoff(pin, d, so, target):
    """How far out along the plug's own axis the cable runs before it turns -- and NEVER
    past the point it is turning towards (user, 2026-09-23: "the incoming wire also does
    a strange thing where it goes too far along x and then backs up").

    The standoff is there to get the cradle and the board behind the cable before it
    heads off. Where the thing it is heading for is ALREADY behind them -- the keeper
    post sits off the back corner, so it usually is -- running the full standoff first
    overshoots and doubles back, which is not what a wire under tension does. Clamping it
    to the target's own projection turns that doglegged pair into one straight run, and
    leaves the standoff doing its job untouched wherever the target really is closer in.
    """
    proj = sum((target[m] - pin[m]) * d[m] for m in range(3))
    out = max(CANB_LEAD, min(so, proj))
    return tuple(pin[m] + d[m] * out for m in range(3))


def lever_bus(nodes):
    """The bus-B chain through the knee levers: [(name, solid)], [(label, mm)].

    `nodes` is [(name, plug, lace, out_dir)] in GUITAR coordinates, in CHAIN ORDER --
    built by src.build, which is the only module that knows where a lever station is.
    The import stays one-way that way, the same dodge the pedal housings use.

    Per segment: square out of one lever's plug, straight to the keeper it winds its
    slack on, then straight to the next lever's plug. The slack is stowed at the
    UPSTREAM lever because that is the one whose move it is there to absorb
    (INSTALL_NOTES KL-2).

    Every leg is STRAIGHT: see the segment body for why."""
    parts, cuts = [], []
    layers = _coil_layers()
    for k, (a, b) in enumerate(zip(nodes, nodes[1:])):
        (n0, _p0, l0, d0, ka0, _pa0, pins0, so0, _ca0, _cb0, _g0) = a
        (n1, _p1, _l1, d1, _ka1, _pa1, pins1, so1, ca1, cb1, g1) = b
        # AT THE BOTTOM OF THE COLUMN, just above the web. Tried at the top, beside the
        # connector, on the theory that the runs would reach it more directly: measured
        # WORSE (45 unintended against 40), because the approach then crosses the
        # housing's top corner instead. Left low, and recorded so it is not re-tried.
        # ONE HELIX PER LAYER, walked up the post and back down again -- the wire is
        # not cut between layers.
        # ...and CANB_COIL_UP above the lace point, not 0.2: on the vertical lever the
        # helix's first quarter-turn ran INTO the post's support at web level (0.046 mm3,
        # hidden as a "0.0" beside three tangent ones). Swept 0.2..2.5 against all four
        # housings: 1.3 and up clears every one by the full 0.4; the post has 18.9 of
        # winding height and three turns use 12.1.
        base = tuple(l0[i] + ka0[i] * CANB_COIL_UP for i in range(3))
        c0 = c1 = None
        for li, (lr, ln) in enumerate(layers):
            lp = _coil_path(base, ka0, lr, ln, up=(li % 2 == 0))
            parts.append((f"wire_canb_coil_{k}_{li}", _coil(lp)))
            if c0 is None:
                c0 = lp.startPoint().toTuple()
            c1 = lp.endPoint().toTuple()
        # EACH CONDUCTOR ON ITS OWN WAY, so the model reads as a wiring reference (user).
        # The trunk passes THROUGH a board: this cable leaves the upstream lever on its
        # OUT half (ways 5-8) and lands on the downstream lever's IN half (1-4), each in
        # harness.PH_PINOUT order. That is the whole point of the 8-way part.
        n = len(CANB_NETS)
        seg = 0.0
        # the lateral offsets CANB_NETS carried are gone: a conductor now starts and
        # ends on its OWN contact, so the bundle's spread is the connector's pitch
        for j_net, (net, _off) in enumerate(CANB_NETS):
            out_pin = pins0[n + 1 + j_net]          # ways 5..8 on the upstream lever
            in_pin = pins1[1 + j_net]               # ways 1..4 on the downstream one
            # SQUARE OUT OF THE PIN for the crimp's length, then along the plug's own
            # axis until the cradle and the board are behind it, and only then turn.
            # Turned at the lead alone, the run reached the next lever straight through
            # whatever stood between -- on one station its own PCB, crystal and caps.
            b = tuple(in_pin[m] + d1[m] * so1 + ca1[m] * cb1 for m in range(3))
            a0 = [out_pin,
                  tuple(out_pin[m] + d0[m] * CANB_LEAD for m in range(3)),
                  _standoff(out_pin, d0, so0, c0)]
            # the incoming run's standoff is measured against whatever it comes FROM:
            # the back-corner wrap where there is one, the bypass where there is not
            stand1 = _standoff(in_pin, d1, so1, g1 if g1 is not None else b)
            # PASS THE LEVER OUTBOARD OF ITS CRADLE FIRST. The standoff is along the
            # plug's axis, and on a MIRRORED station that axis points AWAY from the
            # lever the cable is coming from -- so a straight line to it crossed the
            # whole body to get there, board and all. This is the leg the user drew as
            # going "around the back": out past the cradle, along, then in.
            # ...and where a lever carries a TURN POST, the cable wraps it on the way
            # in. That is the contact the bend needs: on the vertical lever the bus
            # arrives at the wrong end of a body that lies along the plug's axis, so
            # the run comes round the front corner and back up the cheek.
            # ...and where there IS a wrap post the bypass is redundant: the cable is
            # already outboard of everything by the time it leaves the corner, so
            # keeping both sent it 12.4 past the connector and back again.
            a1 = [g1 if g1 is not None else b, stand1,
                  tuple(in_pin[m] + d1[m] * CANB_LEAD for m in range(3)),
                  in_pin]
            pts = a0 + [c0]
            pts2 = [c1] + a1
            parts.append((f"wire_canb_{net}_{k}_0", _wire(pts, CANB_WIRE_OD)))
            parts.append((f"wire_canb_{net}_{k}_1", _wire(pts2, CANB_WIRE_OD)))
            seg = max(seg, _path_len(pts) + _path_len(pts2))
        cuts.append((f"{n0} -> {n1}", seg + _coil_len(layers)))
    return parts, cuts


# ── BUS B'S TWO ARRIVALS AT THE CONTROLLER ────────────────────────────────
# Everything on bus B lives BELOW the chassis floor and the controller lives above it.
# The knee levers hang under the body (their J1 sits at z -95, the floor slab is
# -81.5..-71.5) and the pedal bar's four conductors come up the -X/+Y leg and out of the
# body adapter onto the underside. The controller hangs THROUGH the floor with bus B's
# two 4-ways facing down under it -- J2 in, from the pedals, and J6 out, to the lever
# chain: the mid-bus contract the rest of the bus uses (elec/motor_ctrl) -- so neither
# cable crosses the floor at all. See ctrl_bus_b.
# (Both used to come up through chassis.PORT_X to one 8-way inside the bay. Nothing here
#  threads that port any more.)
CTRL_WAYS = len(EH.PH_PINOUT)               # 4
CTRL_PITCH = _PH_PITCH


# A STRAIGHT RUN AT EACH CONNECTOR FOR THE FAN TO HAPPEN OVER. Four conductors on a
# 2x2 square cannot arrive on a 1x4 row without spreading -- a square projects onto any
# line as three positions at best, never four -- so the spread is a real operation and it
# needs length. Given none, each conductor went from its place in the bundle straight to
# its own way and they cut through each other on the way (15-76 mm^3 a pair).
#
# So an end that fans carries TWO vertices: the connector's centre, which _fan below
# replaces with that conductor's own lead and pin, and a FAN vertex one CTRL_FAN further
# back along the run, which stays on the bundle. The spread then happens
# between those two, with every conductor running parallel to the connector's axis while
# it does -- which is what leg_pogo's FAN_RUN buys the leg harness, for the same reason.
CTRL_FAN = 16 * D.BEAD              # 12.8: ~2.2 of lateral move, a 10 deg fan


def _fan(legs, at, pins, dirs, lead):
    """Splice each conductor's OWN last two points on at one end of a bundle.

    `at` is 0 or -1: which end of the walk the connector is at. Square out of the pin
    for the crimp's length first and only then meet the bundle -- the crimp holds the
    wire in line for its own length anyway, and a run that turns at the pin turns while
    it is still over the board."""
    out = []
    for j, path in enumerate(legs):
        q = list(path)
        pin = pins[j]
        lead_pt = tuple(pin[m] + dirs[m] * lead for m in range(3))
        # (q[at:at + 1] with at = -1 is q[-1:0], an EMPTY slice: it inserted the pin BEFORE
        # the bundle's last point instead of replacing it, and eight conductors ran on 2 to
        # 3 mm past their pins.)
        if at == 0:
            q[:1] = [pin, lead_pt]
        else:
            q[-1:] = [lead_pt, pin]
        out.append(q)
    return out


def ctrl_bus_b(lkl):
    """[(name, solid)]: the pedal cable and the lever chain's head, under the floor.

    `lkl` is the first node of build.lever_bus_nodes() -- the -X-most lever, the end of
    the chain the controller feeds. Passed in for the same reason lever_bus takes its
    nodes: a station's POSE is src.build's, and wiring is imported BY build.

    ⚠ BOTH CABLES LIVE UNDER THE FLOOR, START TO FINISH. The motor board hangs through the
    floor so that J2 (bus B in, from the pedals) and J6 (bus B out, to the levers) face
    DOWN with their latches in reach from outside, and the levers and the leg's adapter
    are under the instrument too. Neither cable has any reason to come up into the bay.

    ⚠ REDRAWN 2026-10-06, WITH THE WAYS READ FROM THE ROUTED BOARD. Both were drawn onto
    one 8-way (in on 1-4, out on 5-8) that the board stopped having when bus B's in and
    out became two 4-ways 16 mm apart: the pedal cable sat two ways low on J2 and the
    lever chain's head ended on and past J2, 12 mm from the J6 it belongs in. And both ran
    -Y in one column under the board's edge, so each passed through the other's fan.
    """
    out = []
    n = CTRL_WAYS
    _j2e, _j6e = conn_end("motor_ctrl", "J2"), conn_end("motor_ctrl", "J6")
    _dn = _j2e[0][1]                                   # both mouths face the same way: down
    j2 = [e[0] for e in _j2e]
    j6 = [e[0] for e in _j6e]
    j2c = (j2[0][0], sum(q[1] for q in j2) / n, j2[0][2])
    j6c = (j6[0][0], sum(q[1] for q in j6) / n, j6[0][2])

    # ── the PEDAL cable: the leg adapter's -Y face -> J2 ────────────────────
    # It starts where leg_pogo's drawing STOPS. The four stub ends are read from there,
    # not re-derived, so the two halves of one cable meet; the bundle frame takes over
    # from the face onward, which leaves a fraction of a millimetre of lateral step at
    # the joint -- nothing, and asserted below so it stays nothing.
    # ...AND IT IS THE SAME CABLE, so it is the same wire: leg_pogo's own gauge and its
    # own places in the bundle, read from HARNESS_WIRES. There is no connector at the
    # adapter's face -- the run goes from the female pogo board's ZR straight through to
    # the controller -- so 28 AWG all the way, which is what the leg's 2.4 channel is
    # sized for, not the 26 AWG the lever segments use between boards.
    # ITS OWN COLUMN, _PEDAL_DX off the connectors' line toward the endplate: J6 is
    # between the adapter and J2 on that line, with the lever head's four conductors
    # coming up into it. The cable passes J6 beside them and only swings onto J2's line
    # over its own fan.
    ends = _PG.body_stub_ends()
    offs = [o for _, o in _PG.HARNESS_WIRES]
    _PEDAL_DX = -6 * D.BEAD                            # -4.8
    _pedal_z = j2c[2] - CANB_LEAD - 4.0                # under the crimps' own leads
    _stub_c = _PG.chan_ends()[1]
    _px = j2c[0] + _PEDAL_DX
    _py = port_y()[0] + PORT_W / 2.0 + 3.2             # where it has always come down
    centre = [_stub_c, (_px, _py, _CH_Z_BOT - 4.0), (_px, _py, _pedal_z),
              (_px, j2c[1] + CTRL_FAN, _pedal_z), j2c]
    legs = bundle_paths(centre, offs, across=(0.0, 0.0, 1.0))
    for k, q in enumerate(legs):
        step = max(abs(q[0][m] - ends[k][m]) for m in range(3))
        assert step < 1.5, (
            "the pedal cable's conductor %d starts %.2f from where leg_pogo's stub ends "
            "it: the bundle's section has turned over at the joint" % (k, step))
        q[0] = ends[k]
    # the far end is leg_pogo's (its stub's own end points, taken as they are)
    assert [nm.upper() for nm, _pl in _PG.HARNESS_WIRES] == [e[2] for e in _j2e], (
        "leg_pogo's harness order is not J2's way order")
    _cable("bus B pedal cable", [(ends[k], None, _j2e[k][2]) for k in range(n)], _j2e)
    for k, (q, (nm, _pl)) in enumerate(zip(_fan(legs, -1, j2, _dn, CANB_LEAD),
                                           _PG.HARNESS_WIRES)):
        _run(out, "pogo_wire_%s_5" % nm, q, _PG.HARNESS_WIRE_OD, "bus B pedal cable", k)

    # ── the LEVER chain's head: LKL's J1 ways 1-4 -> J6 ─────────────────────
    # A FLAT FOUR-WAY ON EDGE, the section every other bus-B segment has. LKL's row is
    # stacked along world Z and J6's runs along world Y, and a ribbon on edge gets from
    # one to the other with no twist at all: it runs level out of LKL, turns in plan as
    # often as it likes (a bend across its thickness), and where it finally turns UP into
    # J6 its width swings from Z onto Y -- the lowest conductor to the far end of the row.
    # Which end that is depends on which way the lever's row counts, so the run comes
    # under J6 from whichever side lands way 1 on way 1: asserted, not assumed.
    # (It was two bundles joined at the old wiring port, 60 mm +Y of here, with a fan at
    # the controller whose four lines crossed each other on the way to their pins.)
    _nm, _plug, _lace, d, _ka, _pa, pins, _so, _ca, _cb, _g = lkl   # _so: plug standoff
    far = [pins[1 + k] for k in range(n)]
    farc = tuple(sum(q[m] for q in far) / n for m in range(3))
    assert abs(d[0] + 1.0) < 1e-6 and abs(far[0][0] - far[-1][0]) < 1e-6 and abs(
        far[0][1] - far[-1][1]) < 1e-6, "LKL's plug no longer faces -X with its row along Z"
    up = far[0][2] < far[-1][2]                        # way 1 at the row's low end
    offs2 = [(0.0, (k - (n - 1) / 2.0) * CTRL_PITCH * (1.0 if up else -1.0)) for k in range(n)]
    x6, zc = j6c[0], farc[2]
    if up:          # way 1 lowest: arrive travelling -Y, the lowest lands furthest -Y
        centre = [farc, (x6, farc[1], zc), (x6, j6c[1], zc), j6c]
    else:           # way 1 highest: round the -Y end of J6 and arrive travelling +Y
        _xa, _yb = x6 + 9 * D.BEAD, j6[0][1] - 6 * D.BEAD
        centre = [farc, (_xa, farc[1], zc), (_xa, _yb, zc), (x6, _yb, zc), (x6, j6c[1], zc), j6c]
    legs2 = bundle_paths(centre, offs2, across=(0.0, 0.0, 1.0))
    for k, q in enumerate(legs2):
        for end, pin in ((q[0], far[k]), (q[-1], j6[k])):
            assert max(abs(end[m] - pin[m]) for m in range(3)) < 0.05, (
                "the lever head's ribbon does not land way %d on its pin: %r against %r"
                % (k + 1, end, pin))
    legs2 = _fan(_fan(legs2, 0, far, d, max(CANB_LEAD, _so)), -1, j6, _dn, CANB_LEAD)
    _cable("bus B lever head", [(far[k], tuple(d), _j6e[k][2]) for k in range(n)], _j6e)
    for k, (nm, _pl) in enumerate(CANB_NETS):
        _run(out, "wire_canb_%s_lkl_0" % nm, legs2[k], CANB_WIRE_OD, "bus B lever head", k)
    check_cables(["bus B pedal cable", "bus B lever head"])
    return out


def lever_bus_cut_list(nodes):
    """The cut list, as text: one line per segment, plus the conductor total."""
    _, cuts = lever_bus(nodes)
    out = ["bus B, knee levers -- CUT LIST (%d x 26 AWG per segment, O%.1f each)"
           % (CANB_WAYS, CANB_WIRE_OD),
           "  slack per segment %.1f (4 grid steps + service), wound %s"
           % (CANB_SLACK, " + ".join("%d turns at r %.1f" % (n, r)
                                     for r, n in _coil_layers()))]
    tot = 0.0
    for label, mm in cuts:
        out.append("  %-26s %7.1f mm" % (label, mm))
        tot += mm
    out.append("  %-26s %7.1f mm bundle  = %.2f m of conductor"
               % ("TOTAL", tot, tot * CANB_WAYS / 1000.0))
    return "\n".join(out)


# The four bus-B conductors' allow-list entries. Here rather than in the table above
# only because CANB_NETS is defined further down the file than WIRE_OK is.
# ...against the HOUSINGS too, not just the connectors (user, 2026-09-23: "as far as
# wiring collisions I'm not too concerned about these so feel free to mark them as
# acceptable. The key here is moreso to get a sense of how much wire we will need to
# cut"). This harness is a LENGTH model first: a run that grazes a corner by 10 mm3 is
# a millimetre of cut wire, and the real cable is flexible where the model is not.
WIRE_OK.update({f"wire_canb_{n}": _LEVER_BODIES for n, _ in CANB_NETS})
