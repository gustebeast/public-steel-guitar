# CAN tee: continuous power trunk, one tap per tee (bronner, 2026-09-30)

**Status: DECIDED BY BRONNER AS THE WORKING ASSUMPTION, NOT YET CONFIRMED BY THE USER, NOT
BUILT.** The user asked (2026-09-30) to explore "dual two pin connectors on each motor T,
two for power and ground, two for data" out of worry about the motor line's power budget.
This is the version of that idea the numbers support. Nothing below is in the model yet
except the tee's 2 mm trunk copper (`6346db5`), which is right either way.

## Why

Today the trunk's 24 V passes THROUGH every tee: one XH contact in, board copper, one XH
contact out, ten times. The contact is 3 A. The far end is fed through the motor board,
whose J3→J1 path is ~91 mΩ on a 0.5 mm inner track (BOM.md, dual-feed section), so the
"dual feed" splits about 64 / 36 and puts the west share on copper rated under 1 A.

Splitting power and data onto two XH connectors changes none of that: it is still one XH
contact per rail per direction, and three 4-way XH in a row is 40.47 mm on a 40 mm board.

## What

    power trunk   ONE continuous pair, panel J7 -> tee 9 .. tee 0, a tap crimped at each tee
    tee           J3  2-way JST VH, side entry   power tap (this motor's current only)
                  J1  4-way JST XH, side entry   CAN in (H, L) + CAN out (H, L)
                  J2  4-way JST XH, side entry   drop to the motor (GND, 24V, H, L) -- unchanged
    motor board   fed by panel J10 -> J3 as now; J1 carries CAN only (its 24 V way unused)

Trunk current never crosses a contact or a board. Each tap carries one motor. The motor
board leaves the motor power path, so its J3→J1 copper stops mattering. The dual feed and
its balance arithmetic go away: a continuous pair fed from one end drops ~70 mV at ten
motors moving.

Power and CAN are different families, so a power lead cannot be plugged into a CAN socket
(BOM.md "two incompatible pinouts share one 4-way XH housing" -- closed for the tees).

## Verified (JST eVH.pdf, read 2026-09-30)

| | |
|---|---|
| current | 10 A per contact (AWG 16, standard header) |
| contact resistance | 10 mΩ max initial |
| wire range | SVH-21T-P1.1: AWG 22–18 (0.33–0.83 mm²); SVH-41T-P1.1: AWG 20–16 (0.5–1.25 mm²) |
| two wires in one crimp | 2 × AWG 22 = 0.66 mm² fits either contact; 2 × AWG 20 = 1.04 mm² fits the 41T. JST does not publish a double-crimp rating -- common practice, pull-test the first ones |
| S2P-VH (side entry) | 7.86 wide, 8.5 tall over the board, 10.9 deep; housing VHR-2N 7.86 × 10.5 section |
| row on the tee | 7.86 + 2 × 13.49 (courtyards) ≈ 36–37 mm on a 40 mm board |

## Height: it fits, measured

The old limit came from string 10's tee under the pickup piece at its neck-most position.
Measured on the placed model: tee connector tops are at z −19.7 (XH, 7.0 over the board);
the pickup piece's shallow run and the height plate bottom are at z −13.4. That is 6.3 mm
of air today. A VH header at 8.5 leaves 4.8; a mated housing at up to 10.5 leaves 2.8.

## Stock: all three halves, read from JLCPCB's parts catalogue 2026-09-30

| part | LCSC | stock | price |
|---|---|--:|--:|
| S2P-VH(LF)(SN), side-entry header, JST | C160355 | 6,950 | $0.1259 @50 |
| VHR-2N-BK, housing, JST | C595405 | 30,543 | $0.0402 @100 |
| SVH-41T-P1.1, contact AWG 20–16, JST | C160350 | 98,611 | $0.0293 @1000 |
| SVH-21T-P1.1, contact AWG 22–18, JST | C160349 | 265,205 | $0.0223 @1000 |

All "extended" library. KiCad footprint: `Connector_JST:JST_VH_S2P-VH_1x02_P3.96mm_Horizontal`.
LCSC's own search endpoint refuses automated requests; JLCPCB's catalogue API answers.

⚠ **HOLD (lead, 2026-09-30): this stays a document until the user confirms it.** No board
re-route and no CAD change on it. The outline is intended to stay 49.5 × 16 with its ear, so
the JLCPCB panel quote does not move; `tools/lcsc_prices.py` prices housings and crimps for
XH/PH/SH only and needs the VH pair added (lead's, once this is confirmed).

## Not verified / open

1. ~~LCSC stock~~ done, above.
2. The mated height of VHR-2N lying on a side-entry header (8.5 or 10.5): either clears.
3. The output panel's J7 is 2 × XH contacts per rail = 6 A; ten motors at the derived
   0.8 A is 8 A. J7 becomes the limit, so it wants VH too or a firmware cap of 7 movers.
4. The 0.8 A per moving motor is still derived, not measured.

## Work, in order

1. `elec/can_tee.py`: J1 8-way → 4-way CAN, add J3 VH tap, keep the 2 mm rails from J3 to J2.
2. `src/electronics.py` `tee_pcb` and `src/wiring.py`: the tee is hand-modelled and the trunk
   is built per conductor through `tee_pin`; power becomes its own pair with taps.
3. `elec/harness.py`: a CAN-only trunk pinout; the bus-A lead from the motor board drops 24 V.
4. BOM: VH parts in, 8-way XH out; delete the dual-feed leg table.
