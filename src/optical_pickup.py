"""OPTICAL per-string pickup — a reflective IR strip that reads all 10 strings
individually, for pitch detection (calibration + audio->MIDI).

WHY optical, not a second magnetic hex pickup: a Cycfi Nu Multi is ~$33/string and
a per-string magnetic coil bleeds into its neighbours at 9.5 mm pitch. Reflective IR
has ZERO magnetic crosstalk, is fundamental-dominant (a DISPLACEMENT sensor, not a
velocity one -> the fundamental is the strongest partial, which is what a pitch
tracker wants), and the whole 10-channel front end is ~$12 of parts that a PCBA house
solders for us. See BOM.md "PCB buying plan".

GEOMETRY (user's brief):
  * the strip gets its OWN deck band at the BRIDGE end -- as close to the changer as
    the deck can start (OPT_X0 = the deck's +X end, flush with the bridge endplate);
  * that band is THIN (OPT_BAND_W = 12, vs the 20 mm standard slot) so the magnetic
    pickup, which moves -X to make room, gives up only 12.05 mm of its approach to
    the changer instead of a whole 20.05 mm slot;
  * NO height adjustment. The user allowed adjustability ONLY if it cost no extra X
    width, and it can't: the strip is 12 mm wide in X and both ends of its Y run are
    already spoken for (rails at +/-54.75, strings out to +/-42.2), so there is
    nowhere to put a jack that doesn't either widen the band or foul string 1.
    Height is set by the carrier SHELF instead (SHELF_Z) -- a build-time number.
    To retune it, change OPT_GAP and reprint the band: it is a 12 x 110 x 6 part,
    the cheapest reprint in the instrument. SHIM_T documents the shim stack-up for
    fine trim without a reprint.

SENSING LAYOUT -- per string, THREE parts in a row across Y:
      [PD] --2.0-- [IR LED] --2.0-- [PD]
  The string sits directly over the emitter. Light goes up, reflects off the string,
  and returns to both photodiodes. SUM of the pair tracks the string's Z (vertical)
  motion; DIFFERENCE tracks its Y (lateral) motion. Taking the magnitude of that 2-D
  vector is what kills the sustain dropouts a single-axis sensor suffers when the
  string's vibration plane precesses (it does, always) -- the one failure mode that
  makes naive optical pickups drop notes mid-sustain.

  The pair straddles Y, NOT X, because the string's transverse motion is in the Y-Z
  plane; flanking along X would put both detectors on the same point of the string.

WHAT SETS THE DIMENSIONS:
  * OPT_GAP (5.0) -- the reflective standoff. Matches the Pololu QTR family's stated
    5 mm optimal range, which is the closest published figure for this class of
    emitter/detector pair and the part we prototype against.
  * PD_DY (2.0) -- detector offset. Big enough that the difference signal has real
    amplitude, small enough that at the 9.39 mm string pitch AT THIS X the outer
    detector of one string sits 5.4 mm from its neighbour's -- no optical crossover.
  * PCB_L -- sized to the string fan AT THE BAND'S X, plus end room for the MCU and
    the connector. The strings FAN (9.5 pitch at the changer -> 6.5 at the nut), so
    the sensors are NOT on a uniform pitch: each one is placed on its own string's
    interpolated Y. That is the whole argument for a custom PCB over an off-the-shelf
    fixed-pitch array (a Pololu QTR-MD-08A is 8.0 mm pitch and would only line up at
    one X station, and only for 8 of the 10 strings).

Frames: PCB centred on the band in X, on the string field in Y; Z absolute.
"""

from __future__ import annotations

import cadquery as cq

from . import dimensions as D
from .helpers import box_at

# ── the thin deck band that carries the strip ────────────────────────────────
OPT_BAND_W = 12.0                 # X width of the band (vs the 20.0 standard slot)
OPT_GAP    = 5.0                  # sensor face -> string: the reflective standoff
PCB_T      = 1.6                  # FR4
PCB_W      = 10.0                 # PCB X width (band minus a 1.0 support wall each side)
WALL_T     = (OPT_BAND_W - PCB_W) / 2      # 1.0 -- above D.MIN_WALL (0.85)

PCB_TOP = D.STRING_Z - OPT_GAP    # 11.0 -- component faces look up at the strings
PCB_BOT = PCB_TOP - PCB_T         # 9.4  -- the carrier shelf sits here
SHELF_Z = PCB_BOT
SHIM_T  = 0.4                     # printed shim step for fine standoff trim (no reprint)

# ── per-string sensor triplet ────────────────────────────────────────────────
PD_DY    = 2.0                    # photodiode offset either side of the string axis
LED_PKG  = (1.25, 2.0, 1.1)       # 0805 IR emitter: X, Y, Z
PD_PKG   = (0.8, 1.6, 0.8)        # 0603 photodiode: X, Y, Z

# ── processor + IO, in the Y end room beyond the outer strings ───────────────
MCU_PKG  = (5.0, 5.0, 0.9)        # UFQFPN32 (STM32G4 class) -- fits the 10 mm strip
XCVR_PKG = (4.0, 5.0, 1.5)        # SO-8 CAN transceiver (TJA1051)
CONN_PKG = (7.5, 12.4, 7.0)       # B4B-XH-A header (see cadkit.pcb.jst_xh_header dims)


def string_y_at(i: int, x: float) -> float:
    """String i's Y at deck X, on the linear nut->changer fan (0 at the nut block,
    1 at the changer). The sensors sit on THESE, not on a uniform pitch."""
    t = (x - D.NUT_BLOCK_X) / (D.BRIDGE_X - D.NUT_BLOCK_X)
    return D.nut_y(i) + (D.string_y(i) - D.nut_y(i)) * t


# Band X span: the deck's +X end, i.e. hard against the bridge endplate.
OPT_X0 = D.BRIDGE_BASE_X0                 # -16.5
OPT_X1 = OPT_X0 - OPT_BAND_W              # -28.5
OPT_CTR_X = (OPT_X0 + OPT_X1) / 2         # -22.5 -- the sensing station

# Y extent: outer strings at THIS x, + the detector offset, + end room for MCU/IO.
_OUTER_Y = string_y_at(0, OPT_CTR_X)      # ~+42.2 (string 1, +Y edge)
END_ROOM = 10.0                            # MCU one end, connector the other
PCB_HL   = _OUTER_Y + PD_DY + END_ROOM     # PCB half-length in Y
PCB_L    = 2 * PCB_HL                      # ~108.4


def _part(pkg, x, y, z_bot):
    dx, dy, dz = pkg
    return box_at(dx, dy, dz, x=x, y=y, z=z_bot + dz / 2)


def opt_pcb() -> cq.Workplane:
    """The assembled optical strip: FR4 + every placed component, at its true Z.

    Purchased/fab part -> NO standalone STEP (cadkit convention); it exists only in
    the assembly, as the fit-check that the strip clears the strings, the rails and
    the magnetic pickup's band."""
    pcb = box_at(PCB_W, PCB_L, PCB_T, x=OPT_CTR_X, z=PCB_BOT + PCB_T / 2)

    for i in range(D.N_STRINGS):                     # 10 sensor triplets, on the FAN
        sy = string_y_at(i, OPT_CTR_X)
        pcb = pcb.union(_part(LED_PKG, OPT_CTR_X, sy, PCB_TOP))
        for s in (1, -1):
            pcb = pcb.union(_part(PD_PKG, OPT_CTR_X, sy + s * PD_DY, PCB_TOP))

    # processor at the +Y end, IO at the -Y end -- both outside the string field
    pcb = pcb.union(_part(MCU_PKG, OPT_CTR_X, PCB_HL - 5.0, PCB_TOP))
    pcb = pcb.union(_part(XCVR_PKG, OPT_CTR_X, -(PCB_HL - 12.0), PCB_TOP))
    pcb = pcb.union(_part(CONN_PKG, OPT_CTR_X, -(PCB_HL - 5.0), PCB_TOP))
    return pcb


def opt_pcb_outline() -> cq.Workplane:
    """Bare PCB envelope (no components) — the cutter the carrier pocket is made
    from, so the pocket and the board can never drift apart."""
    return box_at(PCB_W, PCB_L, PCB_T, x=OPT_CTR_X, z=PCB_BOT + PCB_T / 2)
