# Where the belt clamps can live (2026-10-01)

`CARRIAGE_TRAVEL` = 7.97 mm assumes each belt's tension clamp may run the whole straight
span between its two pulley flanges, less 5 mm at each end. **It may not.** This is the
measurement that says so. Reproduce with `py -3.12 -m tools.clamp_study 8 out.json B`
(and `A`).

## Method, and what it assumes

- The clamp (both halves, screw, insert, lifters: 39.6 long, 8.8 across the belt, 12.7
  through it with 10.2 of that on the belt's OUTER face) is stepped every 8 mm along a run.
- It is turned to the belt's local twist. The belt turns 90° between a screw pulley (axis
  Z) and a motor pulley (axis Y); the clamp is rigid, so the twist is spread evenly over the
  free belt on either side of it. Near the screw the belt is a vertical ribbon and the
  clamp's deep side points sideways into the next lane; near the motor it lies flat.
- It is intersected with every OTHER string's belt, motor, motor pulley, screw pulley and
  bearing, the bridge endplate and the chassis. Neighbouring belts are as the build draws
  them.
- **Not tested:** clamp against a neighbouring clamp. Resolution is the 8 mm step, so each
  span below is good to about ±0.6 mm of nut travel.

## Result: longest clear span, as nut travel (span / 14)

| string | row | run (mm) | lower run B | upper run A | best | what stops it |
|---|---|---|---|---|---|---|
| 1 | near | 551 | 9.6 | 9.0 | 9.6 (B) | next belt (B); chassis (A) |
| 2 | far | 530 | **25.6** | 8.0 | 25.6 (B) | next belt, screw pulley |
| 3 | near | 461 | 7.3 | **20.8** | 20.8 (A) | next belt |
| 4 | far | 440 | **20.9** | 6.2 | 20.9 (B) | next belt, screw pulley |
| 5 | near | 372 | 5.7 | **16.0** | 16.0 (A) | next belt |
| 6 | far | 351 | **15.7** | 3.9 | 15.7 (B) | next belt, screw pulley |
| 7 | near | 282 | 0.6 | **11.3** | 11.3 (A) | next belt |
| 8 | far | 262 | **8.3** | 1.1 | 8.3 (B) | next belt, screw pulley |
| 9 | near | 193 | 0.0 | **6.7** | **6.7 (A)** | next belt; string 10's motor pulley (B) |
| 10 | far | 172 | **3.4** | 0.0 | **3.4 (B)** | the bridge endplate |

## What it means

1. **The row decides the run.** A clamp's deep side hangs off the belt's outer face, which
   is down and toward −Y on run B, up and toward +Y on run A. Near-row belts ride the high
   plane, so their clamps must be on the UPPER run (leaning up, away from the low-plane
   neighbours); far-row clamps on the LOWER run. On the wrong run a clamp is in its
   neighbour's belt for most of the span.
2. **Strings 1-8 carry 7.97 mm** on the right run (string 8 with 0.3 to spare, inside the
   sampling error; string 1 is the odd one out, better on B).
3. **String 9 carries about 6.7 mm.** Short by ~1.3.
4. **String 10 carries about 3.4 mm.** Its clamp cannot come within ~64 mm of the screw
   pulley: for the first 93 mm of the run it is inside the bridge endplate (460 mm3 of
   overlap at the 5 mm position). The pulley-to-pulley figure the travel was sized from
   counted that span as free.
5. The three conflicts first seen by posing the clamps:
   - clamp ↔ neighbouring belt: **real**, and it is the governing constraint everywhere.
   - clamp 9 ↔ string 10's motor pulley: **real on run B** (up to 10.6 mm3); avoided on run A.
   - clamp 9 ↔ clamp 10: not measured here.

## Not decided

Whether to relieve the endplate along string 10's belt lane, shorten the clamp, move the
motor bank, or accept a shorter travel on strings 9 and 10. `CARRIAGE_TRAVEL` is unchanged.
