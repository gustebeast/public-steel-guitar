# Lever sensor board: re-spin spec

**From:** branner (the plastic side). **For:** bronner (the board). **Date:** 2026-09-21.
The housing CAD (`src/knee_lever.py`) is already built to this spec. Until the board is
re-spun, `elec/cad_geom_check.py lever_sensor` will report that the CAD board isn't the
routed board. That report is the handoff, not a regression.

## Summary (user decisions, 2026-09-21)

1. **The lever bus runs at 5 V**, not 24 V. The board can lose its 24 V buck.
2. **The bus connectors are PH, not XH.** Using a different family from the 24 V XH motor
   tees means **no harness can put 24 V on a lever board**. brenner's leg wiring uses PH as
   well. ⚠ **2026-10-19 (user): J1 + J2, two S4B-PH-K-S** (LCSC C157926, 4-way THT
   side-entry, 39,976 in stock), not one S8B-PH-SM4-TB — see "Two 4-ways" below.
3. **Single-sided**, like every board on the shared panel (`elec/fab.py`). J1 and J2 go on
   the magnet face. They stand 4.85 (the SMT 8-way stood 5.5), inside the existing 6.4 gap
   to the housing: they never cut the housing wall, and the magnet stack didn't have to
   move. Their pins come through to the back, where the cradle has no wall.
4. **Trim the top**, not the bottom. The foot pedal installs the board **turned over** so J1
   points down into the bar (the wiring hides in the trough). That puts the board's top edge
   toward the player-side face, where there's 10.15 of room.

## Coordinates

Looking at the **magnet face**. The origin is the MT6701 package centre, which sits on the
axle axis and isn't negotiable. **+X** points toward the lever (the knee side), **+Z** up
(the chassis side). All dimensions in mm. In the routed board's frame the chip is at
(11.0, −0.6), so routed x = spec x + 11.0 and routed y = spec z − 0.6.

## The spec

| Item | Routed now | **Spec** | Why |
|---|---|---|---|
| +X edge | +6.0 | **+4.025** | the groove grips CR_ENG (1.85) of this edge and U4's courtyard reaches +2.175, so the edge is the part plus the grip. Was +3.0, set against the 1.0 component-to-edge rule instead, which put the groove 0.87 inside the sensor's courtyard and 0.35 inside its bare body — the board fouled the slot on the way in |
| Top edge | +14.6 | **+10.1** | the turned-over pedal board's top faces the player: 10.15 of room |
| Bottom edge | −13.4 | **−11.8** | J1 + J2's 19.9 on end + the 1.0 edge rule at both ends |
| −X edge | −28.0 | **−29.0** | the terminator switch (the motor tee's, 8.89 over its lands) lies between the transceiver and the +X groove band; everything −X of it stands 1.0 further out |
| **Outline** | 34.0 × 28.0 | **33.025 × 21.9** | the +X edge moved out 1.025 and the −X edge 1.0; both Z edges are unchanged |
| **J1, J2** | S8B-PH-SM4-TB (SMT, until 2026-10-19) | **2 × S4B-PH-K-S** (THT), on the **magnet face**, standing **on end, end to end, 0.1 apart** (J1 spec z −0.8 … +9.1, J2 −10.8 … −0.9), **mouths facing −X**, mouth faces at x −25.95 (3.05 in from the −X edge), pin rows 6.25 behind them at x −19.7 | |
| J1 / J2 pinout | the 8-way's ways 1–4 / 5–8 | each `harness.PH_PINOUT` on ways 1–4 (5 V, GND, CAN_H, CAN_L): J1 the bus in, J2 the bus out, the same four nets; +V is the **5 V** lever bus | |
| Sides | single | **single** | shared panel settings |

## Parts the outline displaces (routed layout)

- **+X trim:** TP1, TP2, TP3.
- **Top trim:** D1, L1, R1, U1, TP4. The 5 V bus removes the buck, which is likely where
  several of these live.
- J1 is a different part now, so its footprint is new in any case.

(The CAD's own pre-route table, `knee_lever.SENSOR_BOM`, reports the same kind of list in
`knee_lever.RESPIN_MOVES`: D1, L1, R1, U1. Those parts aren't drawn on the spec board.)

## Rules on the magnet face

1. **Edge groove bands:** the outermost **1.85** of the ±X edges. No parts except the MT6701.
   The magnet face is seated by these grooves only; the cradle's front plinth is relieved
   over the whole interior.
2. **Part height:** **≤ 1.75** anywhere except J1 and J2.
3. **Magnet-cap sweep:** any part taller than 1.5 keeps its whole footprint more than **5.66**
   from the origin.
4. **J1 + J2's zone:** their 7.6-deep bodies and the mated plugs' 2.65 run past the mouths
   (x −28.6 … −18.35 over the pair's z span, −10.8 … +9.1) stay clear of other parts.

## Please check

- **J1 / J2's dimensions** are KiCad's model of S4B-PH-K (generated from JST's ePH drawing,
  which refuses a scripted fetch): 9.9 long, 7.6 deep, 4.85 tall, pins 6.25 behind the mouth
  and 3.4 below the board's top face. The plug's 2.65 run is PHR-4's 6.85 (ePH p.3) less the
  header's 4.2 pocket. `cadkit.pcb.jst_ph_side_header(smt=False)` carries them.
- **Harness side:** PHR-4 housings, SPH-002T-P0.5S contacts and a PH crimp tool. Stock read
  2026-10-19 (JLCPCB parts API): header C157926 39,976; PHR-4 C111514 77,731. 22 headers an
  instrument, 20 housings at the boards, so nothing limits.

## Two 4-ways, not one 8-way (user, 2026-10-19)

With in and out in one PHR-8 housing, each hop's cable was crimped into the same housing as
the cable after it: moving or pulling one lever meant re-making the harness either side of
it. Two 4-ways make each hop its own straight PHR-4 jumper (INSTALL_NOTES KL-5).

**Why through-hole.** The board's height is capped by the foot pedal (its housing is clipped
to the bar, and the board stands in it turned over), which leaves 19.9 for connectors on
end. Two SMT S4B-PH-SM4-TB are 23.8 end to end; two S4B-PH-K-S are 19.8, so they take the
8-way's place exactly and **no outline, tunnel or housing changed**. Lying one along the
bottom edge instead would have sent its plug out through the cradle floor toward the
player's knee. The THT pins come through to the back face 1.8 proud: the cradle is open
behind the board between its two webs, and the board's install stroke runs them down the
open slot (checked by sweeping them, not just at rest).

**Re-routed 2026-10-19**: the +5 V pass-through J1.1 → J2.1 is a declared 0.5 mm F.Cu
track (the router had put it on In2.Cu at 0.4, an inner layer that needs 0.72 for 0.57 A),
and the two courtyards' 0.9 overlap is declared in `elec/pcb_declared.py` (bodies 0.1
apart, copper 4.0).

## The +X edge is a MECHANICAL keep-out, not a fabrication one (2026-09-29)

JLCPCB's component-to-edge rule is 1.0 mm and every part on this board clears it. That
is not the rule that binds here. The board is retained by sliding down a GROOVE, and the
groove is material that grips `CR_ENG` = 1.85 mm of each X edge — so anything standing
within 1.85 mm of an edge has to pass through the housing on the way in.

U4 is centred on the axle axis by definition (it is the sensor), its courtyard reaches
2.175, and the edge was at 3.0. The groove's inner face therefore sat at 1.30: 0.87
inside the courtyard, and 0.35 inside even the bare 3.0 mm QFN body. Measured by sliding
the populated board up its own install axis, the sensor fouled the housing by 3.05 mm³
about 11 mm up the stroke, on both levers.

`src/knee_lever.py` now asserts this against the generated BOM, both edges, so a part
that moves into a groove band stops the build instead of being found in a render.

## The two copies are checked now: `tools/check_board_match.py` (2026-09-30)

The board is described twice and neither copy is derived from the other, because the
dependency genuinely runs both ways: the OUTLINE is a mechanical spec (the groove decides
how much bare edge the board needs) and the PLACEMENTS are an electrical output (the
housing's plinth relief is cut to clear the parts). Each side owns half and has to believe
the other half, and until now nothing checked that they still agreed — the CAD builds and
renders perfectly against a stale BOM, and the netlist is valid against a stale outline.

Run it. It exits 1 while the two disagree. As of this writing it disagrees on 12 things:

**The outline — DONE on both sides and re-routed, 2026-09-30.** `elec/lever_sensor.py`
had the old numbers, and they were not independent: it works in a board-CENTRED frame, so
the chip's position encoded the edges too. Rather than retype them, the four spec edges
are now the only typed numbers there and `BOARD_W`/`CHIP_XY` derive from them — and the
28 placements were re-expressed in the CHIP's frame, which is the one datum the housing,
the spec and the layout all share and the only one that does not move when an edge does.
(In the board frame they would all have shifted 0.5125 mm sideways, silently, while every
number in the file stayed the same. That is the same block move the 2026-09-21 re-spin
did by hand as +1.5, +1.45.)

Verified: every part's chip-frame position is unchanged, so nothing moved relative to the
sensor. Re-routed to **0 unconnected, 0 violations** on 32.025 × 21.9, and packaged —
`lever_sensor.zip`, 23 placements, 17 BOM lines, 0 OPEN sourcing decisions.

⚠ IT NEEDS `--rounds=2`. Pass 1 leaves NRST 0.85 mm short of U3 pad 4; the retry closes it
at no cost. `finish.py`'s docstring says the retry has never paid — that was measured on
the optical board and does not hold here. The flag did not exist before this; it does now.

**And a divergence that predates all of this**: the CAD's `SENSOR_BOM` is generated from
an OLDER layout than the one `elec/lever_sensor.py` now holds. It still carries U1 as the
buck converter and L1 as its inductor, both of which the re-spin deleted; C3, D1, R1 and
R2 are in the BOM with no placement; and C7, R6, C2, U1 and C1 sit between 1.55 and 10.65
mm from where elec puts them. The housing's plinth relief is cut against that BOM, so it
is currently clearing parts that are not there and not clearing parts that are.
Regenerating it needs the elec pipeline.

## Not ordered yet: the first board to make USB-only (user, 2026-10-13)

The lever board is not in the first prototype's order and is worked on after that
prototype is validated. Every future board is to be operational with only a host computer
and a USB cable, first flash included (`cadkit/PCB_QUALITY.md`, M43), and this is the one
board that can meet that before it is ever ordered: it has no USB today and is flashed
through a pogo jig and a WCH-LinkE (`docs/bench-order.md`, "Later: the lever sensor
boards"). A note only: no design work has been done, and how a board on a 5 V CAN drop
gets a USB path is open.
