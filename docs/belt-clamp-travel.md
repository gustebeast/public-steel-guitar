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
   - clamp 9 ↔ clamp 10: **clear** — see the next section.

## Clamp against clamp (`py -3.12 -m tools.clamp_pair 8 A 9 B 10`)

Both clamps move, and independently, so every position of one was tried against every
position of the other (8 mm grid, each on its right run).

| pair | worst overlap | where |
|---|---|---|
| 9 (A) ↔ 10 (B) | **none**; closest approach 6.7 mm | — |
| 1↔2, 3↔4, 5↔6, 7↔8 (near A ↔ next far B) | none | — |
| 2↔3, 4↔5, 6↔7 (far B ↔ next near A) | 0.9–1.1 mm³ | both clamps at their screw ends |
| 8 (B) ↔ 9 (A) | 0.5 mm³ | clamp 8 within 29–83 mm of its screw pulley AND clamp 9 within 29–37 of its own |

The touching corner is always both clamps hard against the screw end, where the belt is a
vertical ribbon and the two rows' clamps point at each other. Every clear span in the table
above already starts further out than that, so clamp-to-clamp adds no new limit.

## Twist margin (user, 2026-10-01)

The clamp turns with the belt as it travels: sideways (deep side into the next lane) at
the screw end, flat at the motor end. The table above poses it at ONE angle per position,
from the assumption that the 90° spreads evenly over the free belt. A real belt will not be
that tidy, so the study was re-run with the clamp also posed **20° either side**; a position
counts only if all three poses are clear (`clamp_study 8 out.json A 20 1,3,5,7,9`).

| string | run | nominal twist | with ±20° | what stops it |
|---|---|---|---|---|
| 1 | B / A | 9.6 | **1.1 / 2.8** | chassis |
| 2 | B | 25.6 | 21.6 | next belt |
| 3 | A | 20.8 | 16.8 | next belt |
| 4 | B | 20.9 | 16.4 | next belt |
| 5 | A | 16.0 | 12.5 | next belt |
| 6 | B | 15.7 | 11.2 | next belt |
| 7 | A | 11.3 | 9.0 | next belt |
| 8 | B | 8.3 | **6.1** | next belt, chassis |
| 9 | A | 6.7 | **5.0** | next belt |
| 10 | B | 3.4 | **1.1** | bridge endplate, chassis |

So allowing for twist error costs every string 2–4 mm of travel, and takes strings 1 and 8
below 7.97 as well as 9 and 10. String 1's limit is the chassis, not a neighbour. ±20° is a
guess at the error; nothing has been measured on a real belt.

## The sizing rule was wrong in kind

`CARRIAGE_TRAVEL` is derived from the shortest pulley-to-pulley distance. The clamp's room
is not that: it is the span its neighbours, the chassis and the endplate leave clear, which
differs per string and is a measured quantity. The number should come from the measured
clear span, per string, with the twist margin in it.

## Install rule

**Near row (odd strings): clamp on the UPPER run. Far row (even strings): clamp on the
LOWER run.** Also in INSTALL_NOTES.md.

## Not decided

Whether to relieve the endplate along string 10's belt lane, shorten the clamp, move the
motor bank, or accept a shorter travel on strings 9 and 10. `CARRIAGE_TRAVEL` is unchanged.

## A screwless clip, as a stand-in (2026-10-02)

`CLAMP_BOX=26,8.2,5.35,1.6 py -3.12 -m tools.clamp_study 8 out.json A 20` studies a box in
place of the real clamp: 26 along the belt, 8.2 across its width, 5.35 through it. That is
the envelope of a one-piece toothed clip with no screw. Motors as they are today, twist
margin ±20°, each string on its right run:

| string | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| clear travel (mm) | 36.0 | 32.8 | 29.6 | 26.4 | 23.2 | 18.9 | 16.8 | 11.9 | 10.4 | 8.9 |

Every string clears 7.97, and nothing blocks the right-run span at all: each is limited
only by the 5 mm end clearances. The screw, not the clamp's length, was the problem. The
clip is not designed; clip-against-clip is not re-measured; tension adjustment without a
screw is open.
