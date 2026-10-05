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

## 2026-10-02: the bank moved, and where a screw can and cannot go

**The motor bank is packed against the keyhead endplate now** (the motor board stands
behind string 1's motor instead of between it and the endplate). Every belt run is 21.8
longer; string 10's is 194.0. `CARRIAGE_TRAVEL` is `TRAVEL_WANT` (8.35) again. Every table
above this line was measured on the OLD runs.

**The clamp has been drawn on the wrong side of the belt all along.** Its screw and lifter
are on the TOOTH side (the lifter's ridges mesh the teeth), and a belt's teeth face the
inside of its loop. The build and every study above pose that deep side OUTSIDE the loop.
Posed the way the teeth require:

- the two runs of one loop face each other across 9.8 at each pulley and **6.9 mid-span**
  (centre to centre: each has turned 45° toward the other). Tooth tip to tooth tip that is
  6.9 at the pulleys and **4.0 mid-span**. The clamp is 8.8 deep on that side. It does not
  fit anywhere along the run, with a button head or without one.
- and the loop's inside is not empty: the loops are 9.8 wide on a 9.5 pitch, so **the next
  string's belt runs through it**. A clamp spanning both runs of its own belt (stand-in
  40 × 8.8 × 14.7) has no clear position at all on nine strings.

So no screw goes under (or over) the belt. **A set screw in place of the button head does
not change this**: the depth is set by the lifter stack plus the screw's diameter, not by
the head, and an M5 (the set screw that takes the 2.5 key) is thicker than the M4. A set
screw also only PUSHES, where this clamp's screw pulls the halves together.

**A screw BESIDE the belt** (stand-in 36 long, 15.2 across the belt with the screw on one
side, 7.0 thick, ±20° twist margin, new runs), each string on its right run:

| string | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| clear travel (mm) | 20.4 | 21.1 | 18.0 | 17.0 | 14.0 | 13.0 | 10.2 | 8.9 | **6.2** | **6.5** |

It lies flat near the motor and its width reaches the next belt there, so it only has the
screw-end half of each run. Strings 9 and 10 are about 2 short of 8.35.

**The slim clip** (26 × 8.2 × 5.35) was clear end to end on the old runs; on the new ones
string 10 has (194.0 − 26 − 11 − 10) / 14 = 10.5 of travel.

## 2026-10-05: M3 socket head (2.5 key), beside the belt and in line with it

Stand-ins, ±20° twist margin, step 4, each string on its right run, current main (the foot
strip is in the chassis now).

**Beside the belt** (`CLAMP_BOX=36,13.7,5.6,2.4,-2.75`; the other side is worse everywhere
but string 1):

| string | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| clear travel (mm) | 24.5 | **6.6** | 20.2 | 19.6 | 15.8 | 15.1 | 11.4 | 10.5 | **6.8** | **7.5** |

Strings 9 and 10 stop on each other's belt once the clamp has turned past about 55°;
string 2 is cut short by the foot strip's lips under it. Short of 8.35 on three strings.

**In line with the belt** (`CLAMP_BOX=40,8.2,6.2,2.4`): the screw sits BETWEEN the two cut
ends of the belt, on the belt's own line, so the section is the slim clip's plus 0.85 of
thickness.

| string | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| clear travel (mm) | 36.5 | 33.6 | 30.1 | 26.7 | 23.8 | 19.7 | 17.4 | 11.6 | 11.0 | 9.5 |

Clear on all ten, limited only by the ends of each run. Every 14 of extra clamp length
costs 1.0 of travel, so string 10 has room for a clamp about 56 long. Not designed, and
clamp against clamp is not re-measured. Open: the head faces the belt, so the key has to
come in at an angle (ball end) over a gap left behind the head, or the head needs another
way to be turned.

## 2026-10-05: the in-line M3 clamp, as modelled (`src/belt_tensioner.py`)

Two halves, 8.2 across the belt, 6.4 through it, 49.2 long fully loose (45.2 closed). The
screw's head faces the belt, so a channel in the back of half A takes the ball end of the
2.5 mm key at 25°. The real solids, ±20° twist margin, step 4, each string on its right run:

| string | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| clear travel (mm) | 35.9 | 33.0 | 29.5 | 26.6 | 23.1 | 17.4 | 16.7 | 11.0 | 10.3 | 8.8 |

All ten carry the 8.35. String 10 is the tight one and is limited only by the ends of its
run. Clamp against clamp is still not re-measured, and the build still draws every clamp
at its reference spot on the lower run.

## 2026-10-05, later: channel rails over the slot mouths (user)

Each half carries a channel rail that slides over the other half's slot mouth: it closes
the way the belt went in and hooks the slot's two lips so tension on the ribs cannot creep
the slot open. A's rail runs inside the section; B's runs outside A (the head window
needs both its side walls), so the clamp is 9.15 across, 6.4 through, 49.2 long. Real
solids, ±20° twist margin, step 4:

| string | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| clear travel (mm) | 33.0 | 33.0 | 26.9 | 26.6 | 23.1 | 17.6 | 16.7 | 11.3 | 10.3 | 8.8 |

Still clear on all ten; the extra width only costs strings 1 and 3 some span near their
motor pulleys.
