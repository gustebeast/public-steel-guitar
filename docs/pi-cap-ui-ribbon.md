# pi_cap → UI board: the 14-way ribbon

**Answer to brenner's request, 2026-09-28.** Measured on `agent/bronner`.

## Your SPI0 finding is right, and it decides the design

Confirmed on the cap: header **pin 19 = GPIO10 (SPI0 MOSI)** and **pin 23 = GPIO11 (SPI0
SCLK)**, both taken by R1/R2 to the strip. The TLC59711 has SCKI/SDTI and **no chip select**
— it latches on an idle gap — so any display byte on that bus becomes strip data. And the
strip has to stream continuously to keep its envelope out of the audio band, so SPI0 is busy
essentially always. **The display cannot have SPI0.**

**It gets SPI1, not bit-banging.** SPI1 is separate hardware and touches nothing the strip
owns, so there is no reason to spend CPU on bit-banging. Budget for hardware SPI1.

## Connector: 1.27 mm 2×7 shrouded IDC — your first choice

Agreed, for your reasons plus one of mine:

* it fits inside J1's own 8.5 mm standoff, where a 2.54 male header is 8.54 **before** its
  socket goes over it;
* it halves the cable (8.9 mm of 0.635 ribbon against 17.78);
* the shroud polarises a connector carrying 3V3 into GPIOs, which matters more here than on
  a signal-only cable;
* and it retires the 10.0 mm estimate in your `board_geom`, which you flag as the last
  unverified number in your station. I would rather kill that than keep it.

**Pitch 1.27 mm, 14 ways, 2×7, shrouded, right-angle.** Keep `RIBBON_N = 14`; change
`RIBBON_PITCH` to 1.27 and `RIBBON_W` to the 0.635 ribbon's 8.9 mm.

## Way order and GPIO map

The order puts the clock next to the ground and keeps the two fast lines away from the seven
switch lines — which are static on a human timescale and make quiet neighbours.

| way | signal | header pin | BCM | note |
|---|---|---|---|---|
| 1 | GND | 6 | — | the clock's return, adjacent to it |
| 2 | SCLK | 40 | GPIO21 | **SPI1 SCLK** |
| 3 | SDIN | 38 | GPIO20 | **SPI1 MOSI** |
| 4 | CS_N | 12 | GPIO18 | **SPI1 CE0** |
| 5 | DC | 37 | GPIO26 | plain GPIO |
| 6 | RES_N | 33 | GPIO13 | plain GPIO |
| 7 | +3V3 | 1 | — | see the caveat below |
| 8 | ENC_A | 29 | GPIO5 | |
| 9 | ENC_B | 31 | GPIO6 | |
| 10 | SW_PUSH | 18 | GPIO24 | |
| 11 | SW_A | 11 | GPIO17 | |
| 12 | SW_B | 13 | GPIO27 | |
| 13 | SW_C | 15 | GPIO22 | |
| 14 | SW_D | 16 | GPIO23 | |

### ⚠ Do not use GPIO19 (pin 35) for anything

The `spi1-1cs` overlay claims **GPIO18, 19, 20, 21**. GPIO19 is SPI1 MISO and your display is
write-only, so it is unused — but it is **claimed**, and putting a switch on it would work
until the overlay loads. It stays empty on purpose.

### Pins I deliberately avoided

* **GPIO7, 8, 9, 10, 11** (pins 26, 24, 21, 19, 23) — SPI0, the strip's, claimed by its driver
  even where the strip does not drive them.
* **GPIO0, 1** (pins 27, 28) — ID_SD/ID_SC, probed at boot for HAT EEPROM.
* **GPIO2, 3** (pins 3, 5) — I2C1, left free deliberately; this instrument has a CAN bus and
  may yet want I2C.
* **GPIO14, 15** (pins 8, 10) — UART console. Worth keeping on a machine that boots headless.

After this the cap still has 8 free GPIO, so the station can grow.

## Caveat on +3V3 (way 7)

**The cap does not currently connect header pin 1 or 17 at all** — it carries +5V_PI, +5V_LED,
GND, and the two SPI lines. Adding this means the display's supply comes off the **Pi's own
3V3 regulator**, which is good for about 500 mA across everything. Under 100 mA for the module
is fine, but it is the Pi's budget being spent, not a rail of ours — so if the station ever
grows a backlight or a second module, say so and it gets its own regulator rather than
creeping up on the Pi.

## ⚠ The shroud is not available at 1.27 mm — searched, 2026-09-28

LCSC stocks plenty of **plain** 2x7 1.27 mm headers and no **shrouded** one. Best candidate:

| part | LCSC | stock | note |
|---|---|---|---|
| **HX PZ1.27-2x7P ZZ** | **C22438122** | **10535** | 14P, 2x7, 3.9 mm, gold. Same HX family as the LED connector already in this design |
| HX PZ1.27-2x7P WZ | C22438113 | 2902 | alternate body |
| PZ1.27-2x7PTP-L7.2 | C55099228 | 2232 | |

The only shrouded part the search returns at all is `HX FH254-02-13-Z-H8.5`, which is **2.54 mm
and 2x13** — the wrong pitch and the wrong way count, and 2.54 is what does not fit the
standoff in the first place.

**So the shroud's polarisation has to come from somewhere else, and this is the open decision.**
Without it an IDC socket's key does nothing and the cable can go on reversed, which on a
connector carrying 3V3 into GPIOs is a dead Pi rather than a puzzle. Options, my preference
first:

1. **Plain 1.27 header + pin-1 silk + a cable cut so it only reaches one way.** Cheapest, and
   the length constraint is real here: the run is fixed and short. Residual risk is a service
   visit where someone forces it.
2. **Keep 2.54 and shroud it**, on grown board area, accepting the 8.54 mm header plus its
   socket against the 8.5 mm standoff — i.e. it does not fit today and the cap would have to
   carry it on the front face or the stack would have to grow. The docstring says the stack
   cannot grow, so this means finding the height elsewhere.
3. **FFC/ZIF**, which is keyed by the cable's own shape. You are wary of mating cycles and I
   share that in an instrument that gets stomped on, but it is the only option here that is
   polarised by construction AND fits the height.

**DECIDED (1), and built — 2026-09-28.** You had not called it and the board could not wait on
an answer, so: **plain `HX PZ1.27-2x7P ZZ`, LCSC C22438122, right-angle, on the back face**, with
pin-1 silk and a cable cut to reach only one way doing the keying. Say the word if you want (3)
instead and I will swap it; the footprint is one line.

Why not the others, briefly: (2) needs 2.54, which does not fit the 8.5 mm standoff at all —
a 2.54 male header is 8.54 mm *before* its socket goes over it — and the docstring says the stack
cannot grow. (3) FFC/ZIF is the only option keyed by construction, and you flagged mating cycles
on an instrument that gets stomped on; I share that.

⚠ **The residual risk is written down rather than waved away:** reversing this cable puts 3V3 into
a GPIO, which is a dead Pi rather than a puzzle. The cable length is what prevents it. If the
assembled machine ever shows someone forcing it, the escalation is (3).

## What actually got built

* **J5**, 14-way 1.27 mm 2×7 right-angle, **back face** with every other connector, so the ribbon
  leaves in-plane inside the socket's own 8.5 mm standoff instead of upward into the endplate.
* **The board grew 26 → 34 mm**, and only on its **−Y** edge. That direction is forced: the
  board's +Y is world +Z (`electronics._cap_place` rotates −90 then stands it), so the +Y edge is
  the Pi's own top edge with 0.3 mm to spare. −Y grows down over the Pi, where the only thing
  under the cap is the SoC block — 2.5 mm tall against an 8.5 mm standoff, so 6.0 mm of air.
* **Every placement moved +4.00 in y** so nothing shifted relative to the socket, and
  `electronics._cap_place`'s `j1_y` moved with them — that number is what the whole board is
  positioned by, and leaving it would have landed the cap 4 mm off the header.
* **The ribbon leaves the opposite edge from J2/J3/J4**, which carry up to 3 A to the Pi and
  2.2 A to the strip. This one carries a display clock.
* **`+3V3` is new on this board** — way 7 off header pin 1, the Pi's own regulator. Under 100 mA
  for a display module is fine; a backlight or a second module needs its own regulator rather than
  creeping up on the Pi's budget.

## Fit, and what I still owe you

You are right that it does not fit today: the back face is inside J1's 8.5 mm standoff and the
biggest clear rectangle is ~56 × 5.9. A 1.27 mm 2×7 shrouded body is roughly 12 × 6, which is
borderline against 5.9 — so I expect to take some of the ~14 mm of in-plane growth you
measured (29.5 × 56 × 11.55 alongside, holding only cables that reroute). **Height does not
grow**; `ELEC_STACK_D` is the axis that cannot move and I am not asking it to.

Still to do on my side: choose and verify the LCSC part, place it, and re-route the cap. The
way order above is firm — lay J2 against it.

## Coordination

`pi_cap` is only on `agent/bronner`, not on main, so you cannot build against it yet. Getting
it to main is queued behind the optical board.


## RESOLVED — 0 unconnected, 0 violations, single-sided (2026-09-28)

The board routes clean: **0 unconnected, 0 DRC violations, 11 / 11 parts in the CAD**, 23 of
the header's 40 pins used. Two things had to be settled to get there, and both are worth
keeping.

### 1. The GND pour was TWO ANCHORED CLUSTERS, not an orphan island

Four diagnoses were tried and all four were wrong. What settled it was mapping every
through-hole item to its island INDEX on both layers with an exact
`SHAPE_POLY_SET.Contains(pos, i)` -- no bounding boxes, no slack -- and then union-finding
the islands through the items they share. That turns "which fragment is floating" into
"which CLUSTERS are there", which is the question the ratsnest was actually answering.

There were three clusters. The main pour, a group of five islands around J5 -- **fully
anchored, just not to the main pour** -- and, later, the two below. One via at
**(-16.62, -10.91)**, inside the J5 group on F.Cu and over the main pour on B.Cu with
3.74 mm of clearance headroom, joined the first two.

The lesson for next time: an unconnected zone-against-itself item does NOT mean a fragment
with no anchor. Cluster the islands before looking for an orphan.

### 2. Header GND pins 14 and 20 are UNREACHABLE, and the board takes six of eight

Fanning J5's thirteen signals out of the socket band put **`+3V3_PI` across the entire band
at y -7.23** -- on F.Cu west of x 7.95 and on B.Cu east of it, so there is no layer on which
anything can cross it. Pins 14 and 20 are north of that fence with the switch lines filling
what is left. Measured, not assumed:

* the pour around each is a closed island on **both** layers;
* **no via site exists** that lands in the island on one layer and the main pour on the other
  (exhaustive 0.05 mm sweep of both islands);
* a two-layer maze at 0.10 mm finds **NO PATH** at track widths 0.25, 0.20 and 0.16.

So the choice was six ground pins or re-routing `+3V3_PI` out of the band on a board that is
otherwise clean. **Six wins on the numbers**: the high-current returns are J2/J3/J4's own GND
ways, not the header, and what the header carries is the Pi's own 3 A shared over six pins.
Taking two pins the pour cannot reach would leave two isolated copper islands and two
unconnected items to buy nothing. `PI_GND` carries the reasoning.

### 3. ⚠ The board is SINGLE-SIDED now, and it was the only two-sided one

`pi_cap` was the only board in the fleet populated on both faces -- 6 parts on F, 5 on B --
and it was so **before** J5 (the connectors moved to the back on 2026-09-22 because the 2x20
socket's body IS the standoff). Two LAYERS of copper cost nothing; **parts on both faces**
cost a second placement setup on every order. C1-C4, R1 and R2 moved to `back_refs`, so all
eleven parts sit on one face and the front is bare laminate.

⚠ **`"single_sided"` in the board notes is DOCUMENTATION -- no code reads it.** It said
`False` here while the board was two-sided and setting it `True` would not have made the
board one-sided. What decides the invoice is `back_refs`. Do not trust the flag as a control.

Board census at the time of writing: optical F 253, motor_ctrl F 81, led_strip F 27,
pi_cap F 0 / B 11. Every board single-sided.
