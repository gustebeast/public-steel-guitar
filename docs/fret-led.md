# Fret lighting — the separated strip (brenner, 2026-09-29)

The user split the one-source scheme in two: **this** board lights the FRETS from the
underside of the top panels, and a second board (not this document) mounts inverted above
the light window and fires down at the player's feet. The reason is loss — a single source
trying to do both spends most of its light bouncing around inside the instrument.

Taking over from `docs/led-handoff-brenner.md` (bronner). That document is still the
record for the old side-firing strip, its DRC state and the pickup-noise problem; what
follows replaces its **geometry**, not its rules.

---

## 0. What has to be lit, measured

    fret line inlay     2.40 wide (X)  x  79.60 long (Y)     <- the hard one
    marker symbols      4.80 across                          <- trivial
    transparent base under the colour band   4.80
    deck slab                                6.40  (TZ 6.40, BZ 0.00, FRET_T 1.60)

24 marked frets and 10 marker symbols, split by the mid/key seam at −380.80:

| panel | frets | markers | LED span in X |
|---|---|--:|--:|
| mid | 10–24 (15) | 7 | 191.4 |
| keyhead | 1–9 (9) | 3 | 214.8 |

(Seam moved to −361.15 on 2026-09-29 — keyhead panel set to 249.60, see `top_plate.KEY_L`.
The keyhead board is now the long one. Nothing above changes: both spans are still far
inside every JLCPCB limit, and **`MID_X0` did not move**, so the 14.08 mm pickup clearance
in section 4 is unaffected.)

**The fret line is 79.6 mm long. That single number drives everything below.**

---

## 1. JLCPCB cost vs board length — measured, and it does not constrain us

Read off the live quote form on 2026-09-29, 2-layer, 5 pcs, at 12 mm wide:

| length | 100 | 150 | 193 | 212 | 236 | 254 | 400 | 470 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| price | $4.20 | $5.10 | $5.40 | $5.50 | $5.60 | $5.70 | $6.60 | $7.00 |

And width, at 212 long: **12 → $5.50, 20 → $6.20, 30 → $7.20, 45 → $8.60.**

Two things fall out, and the second is the useful one:

* **Length is nearly free.** 193 → 254 mm costs **$0.30 on an order of five boards — six
  cents a board.** There is no cliff anywhere in our range.
* **Width is ~13× more expensive per mm than length**, because it multiplies the whole
  length. That is the axis to be careful with, and section 2 spends it deliberately.

**Limits, from the capability pages, not inferred:** fab takes 2-layer up to **670 × 600
mm**; **Economic PCBA takes a single PCB from 10 × 10 to 470 × 500 mm.** (The oft-quoted
250 × 250 is the *panel* limit; a single board is not a panel.)

### So: TWO boards, one per panel. Three is not needed, and the seam is free.

212 and 193 mm are both a long way inside every limit. Moving the panel seam to a
marker-free fret space does not change that:

| seam | mid board | key board | 5-pc fab cost |
|---|--:|--:|---|
| −380.80 (today, 1.49 mm off the fret-9 pentagon) | 211.9 | 193.1 | $5.50 + $5.40 |
| −399.20 (space 8's midpoint, marker-free) | 233.7 | 170.0 | $5.60 + $5.40 |

**Ten cents.** So the LED board has no opinion about where the seam goes, and the
objection to moving it is the one I raised before and still stands: −399.20 leaves the mid
DECK panel 253.84 mm long against a 255 bed — **1.16 mm of margin**, which is not a
printable margin — and takes the two deck panels from 5.49 mm apart to 42.29. If the
pentagon proximity is what bothers you, the cheaper fix is to **move the pentagon**:
`MARK_X_ADJ` already exists for exactly this and the marker has 21.75 mm of space to sit in.

---

## 2. Spreading light along the fret — depth is the cheap variable

**One LED under the middle of a fret cannot work, and here is the size of it.** For a
Lambertian source at depth `h` under a diffusing aperture, illuminance falls as
`(h²/(h²+y²))²`. With the LED just under the deck (h ≈ 4.8 mm) the ends of a 79.6 mm line
are **~1000× dimmer** than the centre. Even using the full depth available (below), **22×**.
The user's instinct about the bright spot is right and then some.

The governing number is **S/h — LED spacing over depth.** Direct-lit backlights are even
at S/h ≈ 1, acceptable at 1.5, visibly scalloped past 2.

### ⚠ We have 17 mm of depth we are not using

Probed by intersecting a 60 mm slab under the whole fret field with every part:

    under most of the field    highest obstruction is the CAN harness at z −17.15
    at the keyhead end         wire_ui at −8.27, pi5 −9.00 (x −590 … −574, i.e. at fret 1)

So a tunnel floor at z ≈ −16 is free for frets 2–24, and fret 1 needs the harness moved or
a shallower tunnel. With the aperture at +4.80, that gives **h ≈ 20.8 mm**:

| LEDs per fret | spacing | S/h | brightness at the dim point |
|--:|--:|--:|--:|
| 1 | 79.6 | 3.8 | 0.05 |
| 2 | 39.8 | 1.9 | 0.27 |
| **3** | **26.5** | **1.3** | **0.51** |
| 4 | 19.9 | 1.0 | 0.66 |

### What 3-per-fret actually costs — ~$5, and the biggest line does not move

The worry is "fret count × 3 LEDs and a much wider PCB". Both are real and both are small,
because **the expensive part of this board is the DRIVERS, and 3-per-fret adds none of
them.** Seriesing the three LEDs of a fret onto one channel (above) means the channel count
is set by FRETS, not by LEDs — 96 either way.

Per instrument (two boards). LED `C7371891` $0.0524@100 (42,600 in stock), driver
`C116842` TLC59711 $2.41@10 (3,632), bare boards from the quotes in section 1 divided by
the 5-piece minimum, joints at JLCPCB's published **$8 setup + $0.0016 per solder joint**:

| | 1 LED/fret | 3 LEDs/fret | delta |
|---|--:|--:|--:|
| LEDs (34 vs 82, incl. 10 markers) | $1.78 | $4.30 | +$2.52 |
| solder joints (8 per 5050) | $0.44 | $1.05 | +$0.61 |
| bare boards (212+193, 12 mm vs 60 mm wide) | $2.18 | $3.96 | +$1.78 |
| **TLC59711 × 8** | **$19.28** | **$19.28** | **—** |
| **total** | **$23.68** | **$28.59** | **+$4.91** |

**About five dollars an instrument**, against a driver stack of $19.28 that is identical in
both columns. The LEDs themselves are five cents each; going from 34 to 82 of them costs
less than one driver.

**RECOMMENDATION: 3 LEDs per fret**, at y = −26.5, 0, +26.5. That is S/h = 1.3, and the
figures above are for a *bare* aperture — the deck's own **4.80 mm of printed transparent
PCTG is a heavy diffuser**, which is worth roughly a factor of two in evenness and pushes
3-per-fret into comfortable territory. 2 per fret is the fallback if cost bites; 4 buys
little over 3.

**Cost: 24 × 3 = 72 fret LEDs + 10 marker LEDs = 82.** A marker symbol is 4.80 across and
needs exactly one LED — at h = 20.8 a 4.8 mm spot is flat to within a percent.

### ⚠ The driver count is the cost, not the LEDs — so series them

The three LEDs of one fret must always be the same colour and brightness; nothing wants
them independent. **Wire the three in SERIES on one driver channel.** They then carry
identical current by construction (a match no binning can buy), and the driver count
divides by three: 24 frets × 4 channels RGBW = 96 channels = **8 × TLC59711**, not 24.

⚠ **OPEN, and it needs a decision before the schematic: the LED rail voltage.** Three white
dice in series is ~9.6 V. On a 24 V rail the TLC59711 sinks would drop 14.4 V × 20 mA =
0.29 W per channel × 96 = **27 W burnt in the drivers** — impossible. Bucking to ~12 V on
each board makes the same stack drop 2.4 V → 4.6 W total, which is manageable. So the plan
to "buck to 5 V on each board" needs to become **buck to ~12 V** if the LEDs are seriesed,
or the LEDs stay parallel at 5 V and the driver count goes back to 24. **12 V is the better
trade and it is a change to the stated plan** — flagging rather than assuming.

### Tunnels: worth it, but not for the spreading

The printed light tunnels are worth building, and the reason is **not** that they spread
light — depth does that. They earn their place by *containing* it: an opaque tunnel per
fret stops cross-talk between neighbouring frets and stops the leakage into the body that
this whole split exists to eliminate. ⚠ **CORRECTION (user, 2026-09-29): THE TUNNELS BELONG ON THE DECK ITSELF.** I had written
that a tunnel hanging off the deck's underside would be an unsupported ceiling. That is
wrong, and backwards. `PIECE_UP = (0,0,-1)`: the deck's TOP face is on the bed and the part
builds in −Z, so **the underside is the LAST thing printed and grows UPWARD** — a wall
hanging below the deck is a wall standing up off the print, which needs no support at all.
The precedent was already in this repo and in my own work: the UI station's cradle hangs
**14.30 mm** below the deck and `check_ceilings top_plate_3` reports zero ceilings.

So the tunnels are **deck geometry, printed with the panel**, which is strictly better than
the separate part I proposed: **registration to the fret inlay becomes exact by
construction** instead of a tolerance stack, and the tunnel that lights a line is the same
printed object as the line. That matters more here than usual — a 2.40 mm aperture does not
forgive a 0.3 mm clip-on misalignment.

What the orientation still forbids is a horizontal feature with nothing between it and the
bed: an inward-protruding retaining lip at the tunnel's mouth is an overhang unless it is
chamfered at 45°, and a solid tunnel FLOOR would be a bridge across the tunnel's full
width. Neither is wanted — **the LED board is the tunnel floor**, and it closes each tunnel
when it is screwed up against the deck.

Walls go in the **opaque colour material**, standing down from the colour band, so `_split`
assigns them as it already does for the ±Y side skin. ⚠ That is ~16 mm of second-material
wall × 24 tunnels, and a two-filament print pays a purge every layer that mixes — **estimate
the purge waste before committing**; if it is ugly, the fallback is transparent walls plus a
separate opaque insert, at the cost of the exact registration above.

**Board width follows from the LED spread:** ±26.5 plus package ≈ **60 mm wide**. At 212
long that is about $10.50 for five, ~$2 a board. That is the width spend from section 1,
made on purpose.

---

## 3. The connector — pogo works here, and the mechanics are why

bronner's investigation ended with pogo rejected for two reasons, and **the new geometry
answers both**:

* *"needs sustained compression, which nobody has designed a mechanism for"* — the deck
  panels are pushed home along X against the bridge endplate. **The seam IS a compression
  joint along the mating axis.** No new mechanism; the existing assembly motion is it.
* *"a coplanar butt joint needs the pins to fire ALONG the board plane"* — which is exactly
  what a **right-angle SMD pogo** does, the one stone bronner's doc names as never turned.

Enumerated on 2026-09-29, right-angle SMD pogo, and there is real stock:

| part | LCSC | ways | pitch | rating | cycles | JLC stock | $ |
|---|---|--:|--:|---|--:|--:|--:|
| YZ165615055F-04025-01 | **C5296819** | **4P** | 2.5 | 1 A, **12 V** | 10,000 | **897** | 1.61 / 0.98@300 |
| YZF0002-38080-02 | **C5203987** | 1P | — | **12 A, 24 V** | 10,000 | **602** | 0.70 / 0.38@500 |
| YZ104614067F-03020-02 | C5296820 | 3P | 3.0 | 2 A, 12 V | 10,000 | 225 (LCSC) | 1.57 |
| PG5001-02-009P | C49451497 | 2P | 5.0 | 1 A, 12 V | 5,000 | 1,375 (LCSC) | 0.43 |

Both top rows are **Extended in the JLCPCB assembly library — setup fee, no consignment**,
and both clear the 50-unit bar by an order of magnitude.

**RECOMMENDATION: four × C5203987, on our own pitch.** It is the only one of these rated
for the **24 V** rail, it is rated 12 A where we need well under one, 602 in stock, and
$1.51 a joint at reel price. The 4P module C5296819 is tidier but is a **12 V part on a
24 V rail**, which is a creepage rating, not a margin to spend.

**And the decisive advantage over every part in bronner's table: pogo is single-gender.**
The mating side is a gold pad on the other board — nothing to source. That dodges the wall
that killed the entire board-to-board search ("JLCPCB's split is Female 82 / Male 26; a
joint where *we* supply both halves is the case the library is worst at"). It also makes
the joint blind-mate as the panel slides home, which is the motion the deck already has.

### The install order, and the one thing that breaks it

The user's sequence (2026-09-29): attach each LED board to its own panel off the
instrument; slide panel 1 on with its board; slide panel 2 on so the pogo pins contact;
pull the cable from the end and plug it into the Pi daughter board; fit the endplate.

That works, and it fixes the feed end: the deck installs **+X → −X**, so panel 1 is the MID
panel and panel 2 is the KEYHEAD panel. The cable has to be plugged AFTER panel 2 is on,
which means **the harness drop lands on the KEYHEAD board's −X end** — it is the one next to
the Pi, and it is the last panel fitted, so nothing is covering the route. The pogo then
carries power and data +X across the seam to the mid board. (Feeding the mid board instead
would force the plug BEFORE panel 2, which is how the UI ribbon has to be done and is the
more awkward of the two.)

⚠ **BUT NOTHING HOLDS THE PANELS TOGETHER IN X, AND A POGO IS A SPRING.** The stack is
built so it cannot bind: the first panel butts the bridge endplate flush, "then each panel
keeps GAP clearance to the previous", and the last one stops `EP_TOP_CLR` (0.4) short of the
keyhead face so the keyhead can slide in past it. Nothing preloads the stack. Four pogo pins
pushing ≈ 2–4 N will simply shove the keyhead panel −X until they reach free length, and the
joint reads open.

**The fix is already the last step of the user's own sequence: let the keyhead endplate bear
on the panel and push the stack +X.** The endplate goes on last, which is exactly when you
want the joint closed, and it lands the whole deck in compression against the bridge
endplate at the far end. Travel needed is the stack-up it has to swallow — 0.4 of
`EP_TOP_CLR` plus 0.05 per panel seam — so **under 0.7 mm**, which any of these pogos has
several times over. The side effect is that every panel sits up to 0.25 mm further +X than
drawn; fret lines are at absolute X, so that is worth knowing, but it is the same size as
the `GAP` tolerance already in the design.

⚠ **Two things to settle before committing:** the pogo's **working travel and preload
force** against the panel's 0.05 mm design gap (read the drawing — the catalogue's "6 mm /
8 mm" fields are length and stroke and I have not confirmed which is which), and whether a
**proud contact** is acceptable at a blind mate given the project's standing rule about
that joint class.

(An earlier note here suggested **not joining them at all** — a 4-way harness drop per
panel, deleting the seam joint outright. The user has chosen the pogo seam, so that is
settled; it stays recorded only as the fallback if the preload above turns out to be
unwelcome in the endplate.)

---

## 4. DECIDED: per-fret zones — and cost scales with ZONES, not LEDs

Settled by the user 2026-09-29: **one controllable RGBW zone per fret.** 24 zones,
96 channels, 8 × TLC59711.

**And the user's reading of the cost is right, for a precise reason worth writing down.**
With external constant-current drivers and the three LEDs of a fret in SERIES on one
channel, the two marginal costs are:

    one more ZONE   $0.80   (a TLC59711 is $2.41 and carries 3 RGBW zones)
    one more LED    $0.065  ($0.0524 part + 8 joints at $0.0016)

**A zone costs 12× what an LED costs.** That is the whole reason 3-per-fret is cheap: it
buys evenness with the cheap unit. It also holds for CURRENT, not just money — LEDs in
series share one channel's 20 mA, so a third LED per fret adds rail VOLTAGE, not rail
amps. Zones set the current draw too.

⚠ **Zones come in THREES.** 24 × 4 = 96 channels is exactly 8 drivers with nothing wasted.
A 25th zone costs a whole 9th driver, so the staircase is at multiples of 3 zones, not at 1.

### ⚠ The $15 question this raised, and why it is CLOSED

The zone/LED split above is a property of the ARCHITECTURE, and there is another one where
it does not hold. An addressable LED with its driver built in — `SK6812MINIRGBW-NW-P6`,
**C7423107, 12,215 in stock, $0.1039@50** — needs no TLC59711 at all:

| | XL-5050RGBW + 8 × TLC59711 | SK6812MINI-RGBW |
|---|--:|--:|
| 82 LEDs | $4.30 | $8.52 |
| drivers | $19.28 | — |
| **total** | **$23.58** | **$8.52** |

**About $15 an instrument, and it deletes 8 ICs and 96 driver traces from the board** —
which is why it was worth checking. Two things kill it: every LED becomes its own zone, so
cost and current go back to scaling with LED count (3-per-fret starts costing real money and
real amps again), and, decisively, the noise argument below does not hold up.

⚠⚠ **AND IT STAYS REJECTED. I GOT THE DISTANCE WRONG BY 5× AND THE ARGUMENT DOES NOT
SURVIVE THE REAL NUMBER** (user caught it, 2026-09-29).

I claimed the nearest fret LED was 74.6 mm from the pickup and that the coupling was
therefore **550×** weaker than the old strip's. **It is 14.08 mm and 3.7×.** Three separate
errors, all in the reassuring direction:

1. I measured to the pickup CAVITY's **+X** edge — its far side — instead of the pickup's
   own −X face, the near one.
2. I counted only the piece's 40.10 mm of slot travel and missed that **the pickup slides
   another 6.75 mm −X inside its own cavity**. Neck-most, its −X face is at −131.28.
3. I measured to the LED position rather than to the BOARD EDGE — and the aggressor in
   bronner's analysis is the **supply loop**, which is board copper, not the die.

And the number that sets it is not fret 24 at all. **The board cannot reach past `MID_X0`
= −145.36, the mid panel's own +X edge**, so the nearest approach is fixed at
**145.36 − 131.28 = 14.08 mm** by the deck, not by where we choose to put an LED.

    board +X edge to pickup     14.08 mm    3.7x weaker than the old strip's 9.1
    nearest LED (fret 24)       22.47 mm     15x weaker

**3.7× is about 11 dB against the ~65 dB bronner's two fixes were worth. It is nothing.**
So the SK6812 saving is off the table on the evidence available, the TLC59711's ~19.5 kHz
enhanced-spectrum PWM keeps its reason, and **`docs/led-handoff-brenner.md` section 5 applies
to this board very nearly in full.** I had written the opposite one commit ago.

⚠ This is the second clearance in this project I have reported from a derivation instead of
a measurement, and the second one that was wrong. bronner's method note says it plainly:
put a box where the part would go and intersect it.

### What that means for the layout

The exposure is CONFIGURATION-DEPENDENT and one-ended, which is the one piece of good news:
14 mm happens only with the pickup slid fully to the neck (as drawn it is ~61 mm), and only
the mid board's **+X end** — frets 24, 23, 22 — is anywhere near it. So:

* put the **buck converter and the bulk supply loop at the KEYHEAD end**, as far from the
  pickup as the board is long;
* treat the mid board's +X 40 mm as a noise-critical zone and keep its loop area minimal;
* the 4-layer ground plane bronner measured at ~25× is still available, and their attempt
  failed on the OLD board's routing, not on the idea.

## 5. What is NOT decided

1. **The LED rail voltage** — see section 2, 12 V vs 5 V.
2. **Fret 1 has 8.27 mm, not 17 mm**, because `wire_ui` and the Pi are under it. Either the
   harness moves or fret 1 gets a shallower tunnel and a 4th LED.
3. **Which LED** — and see section 4: the package choice and the driver
   architecture are one decision, not two. The existing XL-5050RGBW is a side-mount 5050 chosen for a side-firing
   strip; this board fires UP, so the package choice is open again.


---

# 6. THE POWER + NOISE PLAN (2026-09-29)

How to drive 3 LEDs per fret as one controllable zone, survive the 9.14 mm pitch at the
+X end, and put as little as possible into the pickup. Everything below is measured off
the model or read off a catalogue; the open items are listed at the end and named.

## 6.1 Topology — and it divides perfectly

    zone            = one fret = 4 channels (R, G, B, W)
    channel         = THREE LEDs IN SERIES, spread along the fret at y = -26.5, 0, +26.5
    MID board       frets 10-24 = 15 zones = 60 channels = exactly 5 x TLC59711
    KEYHEAD board   frets  1-9  =  9 zones = 36 channels = exactly 3 x TLC59711

**Zero wasted channels on either board**, which fell out of the 249.60 seam rather than
being designed. Worth protecting: any change that moves a fret across the seam breaks it
and costs a whole driver for one zone (see "zones come in threes", section 4).

Series, not parallel, for three reasons: the three LEDs of a fret carry **identical current
by construction** (a match no binning sells), the channel count follows FRETS not LEDs, and
— the one that matters here — **a series string draws the same current as a single LED**, so
3-per-fret costs rail volts, not rail amps.

## 6.2 Rail and power budget

`R_IREF = 3k3` in `elec/led_strip.py` already sets **15.0 mA per channel**; keep it.

    W/G/B string   3 x 3.2 = 9.6 V        red string   3 x 2.2 = 6.6 V
    rail           12 V  (9.6 + sink headroom; TI gives TLC59711 Vin 3-17 V)

At **all 24 frets full white**, the absolute worst case and not a normal state:

| | |
|---|--:|
| LED power | 12.74 W |
| driver dissipation | 4.54 W — **567 mW per TLC59711**, 8 of them |
| total at 12 V | 17.28 W = 1.44 A |
| **from 24 V at 90 % buck** | **0.80 A** — mid 0.50, keyhead 0.30 |

⚠ **Red wastes the most**, 81 mW a channel against 36 for the others, because its string is
3 V below the rail. TLC59711's per-colour brightness control is the lever, and red wants
trimming down for colour balance anyway — so the fix and the calibration are one knob.

## 6.3 Noise — ranked by measured leverage

The pickup sits **14.08 mm** from the mid board's +X edge at its neck-most slide
(section 4). bronner measured the old strip's supply loop at **695 mm²**. So:

**1. FOUR LAYERS, GND plane directly under the LED layer. Not optional.** Each zone's
series string spans the fret's **79.6 mm**, and loop area is string length x return
distance:

| stackup | return path | loop area | vs the old strip |
|---|---|--:|--:|
| **4-layer** | plane 0.2 mm below | **15.9 mm²** | **44x smaller** |
| 2-layer | trace 2 mm away | 159.2 mm² | 4x smaller |

Cost: 4-layer at 200x60 and 224x60 quotes **$32.40 + $33.30 per five**, about **$13.14 an
instrument** against ~$4.12 for 2-layer — **+$9**, against a $19.28 driver stack. Buy it.

**2. Put the loop in a VERTICAL plane, not a horizontal one.** A magnetic pickup's coil
axis is vertical, so it answers to Bz. A current loop lying flat in the board plane makes
exactly that; a trace over its own return plane stands the loop up and points its field
sideways. Free once you are on 4 layers **but only if the return is actually underneath** —
hence the layout rule: *every zone's return is the plane directly beneath its own string,
and no zone's current may take a path that encloses board area.*

**3. Buck at the KEYHEAD end.** It is the highest di/dt thing on the board. On the mid
board that puts it ~200 mm from the pickup and leaves only smoothed 12 V at the +X end.

**4. Local bulk + HF decoupling at EVERY driver.** Otherwise each zone's PWM current is
drawn down the full-length rail and the loop is the whole board, which undoes item 1.

**5. A consequence of item 1 worth using: with a plane return you can move the +X drivers
AWAY from the pickup almost for free.** Lengthening a run 15 mm adds 15 x 0.2 = 3 mm² of
loop, while the distance term goes as 1/r³. On 2 layers that trade runs the other way.

**6. Stream continuously; do not burst.** Straight from bronner: the audio-band threat is
the ENVELOPE, not the carrier. Refreshing 24 zones at 100 Hz puts a 100 Hz envelope on the
supply, which is precisely what a pickup is built to hear. ES-PWM at ~19.5 kHz is why the
TLC59711 was chosen over SK6812/SK9822, and it only pays off if the writes never stop.

## 6.4 The +X end — the tight case, measured

Fret pitch, tightest first: **24->23 is 9.14**, then 9.69, 10.26, 10.87 ... 19.37 at 11->10.
Against `XINGLIGHT_XL-5050RGBW`: body **5.00**, copper out to ~**5.56**, courtyard **6.10**.

⚠ **CORRECTED — I COUNTED TWO WALLS WHERE THERE IS ONE.** Cell n's +X wall IS cell
n+1's −X wall; adjacent cells share it. The budget is therefore:

    pitch 9.14  -  courtyard 6.10  =  3.04 for ONE shared wall
       a 2-bead wall (1.60)   ->  1.44 mm of air.  Comfortable.
       a 1-bead wall (0.80)   ->  2.24 mm of air.

So **2-bead walls fit at every fret on the instrument**, tightest included, and
`fret_light.wall_for()` is still written generatively (falling back to one bead) so a
future pitch change fails loudly instead of silently pinching. The earlier figure of
"0.38 mm of air" was the doubled-wall error and is withdrawn.

✅ **Which answers the standing question: geometry does NOT force dropping frets 23 and
24.** They fit, at 1.44 and 1.99 mm of air respectively. If they come out it will be for
the noise reason, which the user has already said is not reason enough on its own.

The LEDs spread in **Y**, so the pitch constraint is purely in X and one package width is
all each fret needs there. Board width follows the spread: +-26.5 plus a 6.10 courtyard is
**60 mm**. The tunnel is 79.6 long, so its outer ~9.8 mm each side overhangs the board and
is closed by a deck rib at board level rather than by the PCB.

## 6.5 What this plan still needs

1. ✅ **CLOSED — the TLC59711 takes 12 V and the parts do not change** (user asked whether
   this was a change of course, 2026-09-29). It is not. The driver and the LED are both the
   ones already selected; what moves is the RAIL, because three dice in series need 9.6 V.
   Read off the datasheet rather than a parametric table:

       ABSOLUTE MAXIMUM
         Supply voltage VCC                         -0.3 to +18 V
         Input voltage  OUTR0..OUTB3                -0.3 to +18 V
         Output current (DC) OUTXn                         75 mA
       RECOMMENDED OPERATING
         VCC  Supply voltage, internal regulator used  4 to 17 V
         VREG Supply voltage, VREG connected to VCC    3 to 5.5 V
         VO   Voltage applied to output (OUTR0..OUTB3)     17 V
         IOLC Constant output sink current                 60 mA

   TI's own typicals are specified at **VCC = 12 V**, so 12 is mid-range, not a stretch.

   ⚠ **LCSC'S SPEC TABLE IS WRONG ON THIS PART.** It lists "Voltage - Input(DC) 3V~5.5V",
   which is the **VREG** row — the mode where you bypass the internal regulator and feed
   3.3 V logic directly. The **VCC** row immediately above it is 4-17 V. Same class of trap
   as the `TLV9061IDCKR` / `C693480` mix-up this project already records in `BOM.md`:
   **the catalogue is not the datasheet.**

   **And the "nothing above 5 V" finding does not apply to this architecture.** That was
   about INTEGRATED ADDRESSABLE LEDs (SK6812 / SK9822 / WS2812-class), where the driver
   silicon and the dice share one supply and the part is a 5 V part. With an external
   constant-current SINK the LED anode rail is independent of the logic supply — that is
   the defining property of the topology. The old strip's 5 V was a system choice for a
   board driving one die per channel; series-of-3 is what asks for 12.

   The four selection goals are all untouched: **ES-PWM ~19.5 kHz** (and still the reason
   SK6812 stays rejected), **a white die** on the 5050, **16-bit GS** — note bronner's
   `DRV_LED_OUTS` already handles BC being per COLOUR GROUP, so an RGBW LED mixes groups,
   all three BC fields are set equal and trimming happens in GS, which is exactly why the
   bit depth still buys the dim end — and **both parts Extended, no consignment**.
2. **Whether to light frets 23 and 24 at all.** They are the two tightest gaps AND the two
   nearest the pickup. Dropping them removes the worst routing and the worst coupling in
   one move, at the cost of two markings at the extreme treble end. A real option, not a
   recommendation.
3. ✅ **CLOSED — 15 mA is the CEILING, and it does not need changing to run dimmer.**
   (user asked whether it was about max brightness, 2026-09-29.) The datasheet stacks
   three controls:

       R_IREF  (one resistor per chip)  ->  IOLCmax,  2 mA .. 60 mA
       BC      7 bits, 128 steps        ->  0-100 % of IOLCmax   ANALOGUE, per colour group
       GS      16 bits, 65536 steps     ->  0-100 % duty          PWM, per channel

   "IOLCMax is the maximum current for each output. Each output sinks the IOLCMax current
   when it is turned on **and** global brightness control data (BC) are set to the maximum
   value of 7Fh." So 15 mA is the on-portion current at full brightness, and every figure
   in 6.2 is BC = 127 and GS = max on all 24 frets at once — the absolute worst case.

   **Dimming goes through BC, not through a different resistor.** TI: "Output currents
   lower than 2 mA can be achieved by setting IOLCMax to 2 mA or higher and then using
   global brightness control to lower the output current." `R_IREF` only wants revisiting
   if 15 mA is the wrong CEILING; there is headroom to 60 mA if it reads dim.

## 6.6 ⚠ THE FIRMWARE RULE THIS EXPOSES: it is not brightness that makes noise, it is CHANGE

BC and GS dim by different mechanisms and **only one of them switches**:

* **BC lowers the current itself.** The waveform shape does not change.
* **GS shortens the on-time.** This is what creates switching — and at **GS = FFFFh the
  output is on for the whole period, i.e. DC, with no switching at all.**

So the quietest lit state is full GS with brightness set by BC, and the quietest state of
all is off. ⚠ **But BC cannot be used per fret**: it is per colour GROUP, and bronner's
`DRV_LED_OUTS` note already establishes that all three BC fields must be set equal because
an RGBW LED necessarily mixes groups. BC is therefore one global brightness for a whole
chip. Per-fret colour has to come from GS, and GS switches.

**Which is fine, because a STATIC GS value is a steady ~19.5 kHz carrier with no
audio-band content.** The audio-band threat is the ENVELOPE (bronner, section 5 of the
handoff), and an envelope is what you get from CHANGE: fades, pulses, animation at 1-100 Hz
put precisely that rate onto the supply, 14 mm from a coil built to hear it.

    FIRMWARE CONSTRAINT: fret zones hold static GS values while the instrument is
    being played. Animate at load/idle if you like. No fades, no breathing, no
    pulsing, and no per-frame redraw at an audio-band rate, with the strings live.
    Global brightness changes ride BC, which does not switch.

This costs nothing to honour and is invisible once the board exists, which is why it is
written down here rather than discovered on a bench.


---

# 7. THE FRET CELL — the design (2026-09-29)

`src/fret_light.py`. One opaque CELL per fret, built as deck geometry, turning three LEDs
into an even line and sealing each fret from its neighbours. Datums live in that module and
are read from `top_plate` rather than copied; `check_optics()` is the proof.

## 7.1 Section, bottom to top

    z -19.00 .. -17.40   the LED board (1.6), clearing the tee PCBs at -19.65
    z -16.00             the 5050's emitting face
    z -16.00 ..   0.00   the TUNNEL: opaque walls on the fret pitch, gently tapered
    z   0.00 ..   4.80   a TRANSPARENT COLUMN through the deck's base, aperture-wide
    z   4.80 ..   6.40   the fret inlay, in the colour layer

⚠ **The isolation has to reach 4.80, not 0** — and that is the whole reason the cell is
deck geometry rather than a part clipped underneath. The deck's base is **4.80 mm of
transparent PCTG and it is continuous across the panel**: seal a tunnel at the deck's
underside and light just crosses to the neighbour INSIDE THE SLAB, 9.14 mm away at the
bridge end. So in the fret field **the base becomes opaque except for a transparent column
under each fret line and under the two border strips.** Isolation by material, not by air —
which also keeps the deck a solid plate, where 24 slots of 7 × 79.6 through a 4.8 base
would not.

**The one bleed path, and it is the one the user allowed:** the fret inlay and the border
strip meet in the COLOUR LAYER at |y| = 39.8 — a junction 2.4 wide and 1.6 tall. Narrow, at
the extreme ends, nothing below 4.80.

## 7.2 Why three LEDs land evenly

Illuminance falls as (h²/(h²+y²))², so one LED under the middle of a 79.6 line leaves the
ends **22×** down. Solved numerically over LED spacing and depth:

| | |
|---|--:|
| depth h (aperture 4.80 over LED face −16.00) | **20.80** |
| LEDs at | **y = −27.20, 0, +27.20** (34 beads) |
| end reflector | 0.85, diffuse white PCTG |
| **uniformity over the whole line** | **1.21 : 1** |

Two findings worth keeping:

* **Depth is the lever.** Same three LEDs at h = 12 give 2.6 : 1; at 20.8, 1.21 : 1. The
  17 mm of clear air under the deck was the thing to spend.
* **The end reflectors are worth more than they look** — without them the identical
  geometry is 1.9 : 1, because an end point is lit from one side where a mid-gap is lit
  from two. They also shift the optimum spacing outward, from the even-thirds 26.53 to
  27.15; the design uses 27.20 to sit on the bead grid.

The profile dips to 0.83 between LEDs and 0.82 at the ends — under half a stop, before the
deck's own 4.8 mm of scattering PCTG smooths it further.

## 7.3 The cell in plan, and it fits everywhere

Walls are shared, so a fret gap holds **one** wall (see the correction in 6.4):

| gap | pitch | wall | tunnel | air round the 6.10 courtyard | taper |
|---|--:|--:|--:|--:|--:|
| 24–23 | 9.14 | 1.60 | 7.54 | 1.44 | 7.0° |
| 23–22 | 9.69 | 1.60 | 8.09 | 1.99 | 7.8° |
| 2–1 | 32.58 | 1.60 | 30.98 | 24.88 | 34.5° |

**2-bead walls at all 23 gaps**, and the worst taper is 34.5° off vertical against a 45°
limit. The taper runs narrow-at-the-top to wide-at-the-bottom, which in the deck's print
direction (`PIECE_UP = -Z`, face on the bed) starts narrow at the bed and leans outward as
it builds — self-supporting.

## 7.4 The outboard ends

The board is 62.4 wide (outer LEDs at ±27.20 plus a courtyard) but the fret line runs to
±39.8, so the last ~8.6 mm of each cell has no board under it. Rather than widen the board
to 84 — width being the expensive axis — **the deck ramps its own floor up from the board's
edge to the aperture at 58°**. The ramp closes the cell, self-supports in this print
direction, and *is* the end reflector the optics want. One feature doing three jobs.

## 7.5 Still open on the cell

1. **The markers.** Ten symbols sit centred in a fret SPACE, i.e. in the opaque region
   between two cells. At the nut end there is room for their own cell and LED; at the
   bridge end there is not — the marker in space 24 sits in a 9.14 gap already spent on
   two cell walls. Either it shares the neighbouring fret's cell (the aperture becomes
   line + symbol) or it goes dark.
2. **The harness has to move.** The depth budget assumes the floor is the tee PCBs at
   −19.65, not `wire_canl` at −17.15. Designing to the cable costs 2.5 mm and takes the
   line from 1.21 : 1 to 1.35 : 1.
3. **Two-material volume.** Opaque walls now run the full 20.8 mm from the colour layer to
   the board, 24 of them. That is a lot of second-material purge on a two-filament print —
   worth estimating before a panel is committed.


---

# 8. ATTACHING THE BOARD TO THE PANEL (2026-09-29)

    "Ideally it relies on plastic along all directions except for one installation
     path."  (user)

## 8.1 ⚠ First, the floor: the PLUG is the floor, and the CAN wires are drawn wrong

The user called this: *"The can wires are modeled incorrectly, the plugs are the real
floor, or perhaps the height of a male connector plugged into those female connectors."*
Measured:

    tee board, placed on its cradle   top face      -26.65
    its side-entry XH + MATED plug    XH_SIDE_H 7.00  ->  -19.65
    wire_canl / wire_canh, as drawn                      -17.15

**The wires ride 2.5 mm above their own plug.** `src/wiring.py` stacks the four trunk
conductors in Z — `TRUNK_DZ = {gnd -0.8, hot 1.2, canh 3.2, canl 5.2}` — so the bus's top
conductor floats above the connector it lands in. The real envelope under the deck is the
**mated plug at −19.65**, and the cable should be inside it, not over it.

**What it costs right now:** `fret_light.BOARD_BOT` is held at −16.15 (1.0 over the wires
as drawn) rather than −17.65 (2.0 over the plugs). That is 1.5 mm of optical depth and
takes the fret line from **1.21 : 1 to 1.28 : 1**. Recovering it is a `wiring.py` change —
invert the trunk stack so `canl` is the LOWEST conductor rather than the highest — and it
is not a fret-light change. Flagged here rather than done, because the CAN trunk is shared
and its stacking order was chosen for reasons this work has not read.

## 8.2 The install path has to be +Z, and the reason kills the obvious alternative

Sliding the board in along X — the same way the panel itself goes on — looks attractive and
**cannot work**: the cell walls' undersides sit at the board's TOP FACE, and the LEDs stand
1.40 above that. Every wall would scrape every LED. The walls could be lifted 1.4 to clear
them, but then each cell leaks light all along its bottom edge and the isolation this whole
design exists for is gone.

**So the LEDs have to enter their cells vertically, and the board installs +Z.**

## 8.3 The comb is already the pocket

Three of the six directions come free, because the cell walls are exactly a close fit
around the board:

| direction | held by | how |
|---|---|---|
| **+X, −X** | plastic | the comb's two end walls, which the board butts |
| **+Y, −Y** | plastic | the two end ramps, whose inner faces are the board's edges |
| **+Z** | plastic | the cell walls' undersides — the board bottoms on them, all 23 |
| **−Z** | — | **nothing yet. This is the one that needs solving.** |

+Z is held at 23 places along the length, so the board cannot bow upward. −Z is gravity's
direction and is held nowhere, and one screw in the middle of a 220 mm board lets both ends
hang.

## 8.4 The plan: lift, shift, one screw

A **two-motion install**, which is how you get plastic capture in five directions when
only one fastener is allowed:

1. **Lift** the board +Z into the comb until it bottoms on the cell walls.
2. **Shift** it ~6 mm along X. Its long edges pass under **retaining tabs** on the ramps.
3. **One M4** through the board into a boss on the deck, locking the shift.

The tabs are the whole trick: they are short (~8 mm), they live on the ramps at the board's
long edges, and they are **outboard of every LED courtyard**, so nothing about them ever
interacts with an LED. They hold −Z continuously along both edges, which is what a 220 mm
board needs and what a single central screw cannot give.

⚠ **AND THE BOARD HAS TO GET WIDER FOR THEM.** The outer LEDs sit at ±27.20 with a 6.10
courtyard, so their copper reaches ±30.25. At today's `BOARD_HALF_W` of 31.20 a tab has
0.95 mm to live in, which is not a tab. Taking the board to **42 beads = 33.60 half-width
(67.2 mm)** gives a 2.40 mm tab reach with 0.95 clear of the courtyard. Width is the
expensive axis — this is ~+$1 per five boards — and it buys the retention scheme outright.

**Why not snap the board in?** The project's standing rule: no flex snaps. The tabs are
rigid and the motion does the engaging, which is the same trick the deck's own
tongue-and-groove uses.

**Why one screw and not two?** Because with the tabs engaged the screw is not carrying the
board — it is only stopping the 6 mm shift from reversing. That is the "one installation
path" the user asked for: every direction is plastic except the shift, and the shift is
what the screw locks.

## 8.5 Open on the attachment

1. **Where the M4 goes.** It wants to be at the keyhead end, where the harness drop already
   is, so one region carries all the service access. It must also miss a cell wall and the
   LED rows, which on a 9.14 mm pitch at the bridge end would be impossible — at the
   keyhead end the pitch is 21–32 and there is room.
2. **The shift direction.** Shifting −X (toward the keyhead) means the board is pushed the
   same way the panel slides off, so a loose screw and a tug could walk it out. +X is the
   safer sense and wants checking against the cell walls' end stops.
3. **Whether the tabs print.** They protrude inward from the ramps, i.e. they are a
   horizontal feature with air beneath them in the deck's print direction. Short ones
   bridge; long ones want a 45° chamfer underneath.


---

# 9. THE BOARDS (2026-09-29)

`elec/fret_led.py`, one module, two boards, designed to the same bar as the other seven:
generated from the instrument's geometry, placed by the board module rather than by an
auto-arranger, routed by freerouting, and read BACK into the CAD from the routed file.

    fret_led_mid   frets 24..10   15 zones   60 channels   5 x TLC59711   209.8 x 70.4
    fret_led_key   frets  9.. 2    8 zones   32 channels   3 x TLC59711   211.8 x 70.4
    92 channels, 8 drivers, 1.38 A at 14 V with every fret at full white

Every fret X, the four LED Y positions, the 70.4 width and the whole Z stack are IMPORTED
from `src/fret_light.py`. Nothing is retyped, for the reason `optical.py` gives about its
own placements: a copy of a hundred positions is exactly the drift this pipeline exists to
prevent. Move a fret and the board follows.

## 9.1 ⚠ RETRACTED: the pogo seam joint does not fit, and section 3 never measured it

Section 3 recommended joining the two boards across the deck seam with right-angle SMD
pogo pins (4 x C5203987), on the strength of the deck's sliding assembly already being a
compression joint along the mating axis. **The mechanism argument still holds. The
geometry does not, and I had not looked at it.**

**The pin fires 1.90 mm above the board it is soldered to.** Xinyangze's own drawing for
YZF0002-38080-02: the barrel's front view is 3.00 wide x 3.80 tall with the bore centred,
so lying on its pad the axis is at 1.90. The two LED boards are COPLANAR -- same comb
pocket, same Z stack, by construction -- so the facing board presents a 1.6 mm laminate
edge spanning 0.00 to -1.60 below the pogo board's top face. **The pin fires over it and
touches nothing.** Mounting on the underside instead puts the axis 1.90 below the board's
bottom, which misses by the same margin the other way.

Three ways round it, all measured, all closed:

| | what it needs | what there is |
|---|---|---|
| **tip to tip** (two pins on one axis -- the heights DO agree) | 12.00 mm between the pads' outer edges | the seam bay is **10.40** -- the clear run between the two combs' end walls, measured. (It was 9.60 when this was first checked; fixing the clamped-wall overhang in 9.2a gave back 0.80, and it is still 1.60 short) |
| **offset the boards in Z** so the axis lands inside the other's edge | 2.70 mm | UP takes the keyhead board's depth 17.75 to 15.05, under the 1.18 : 1 the cells are solved for. DOWN leaves **0.80** over the tee PCBs, and `fret_light` asserts 1.50 because the panel SLIDES over them |
| **the 4-way module** C5296819 | -- | it is a **MEZZANINE** part: its four plungers fire PERPENDICULAR to the board, 4.00 mm working height. It wants the boards stacked 5.6 mm apart in Z, not butted. LCSC's "SMD R/A" attribute is what misled section 3 |

⚠ **This is the third clearance in this project I have reported from a derivation instead
of a measurement.** The first two were the pickup distance (74.6 against a real 14.08) and
the cell wall count. bronner's method note says it plainly, and it applies to catalogue
attributes as much as to CAD: put the part where it would go and intersect it. "Right-angle
SMD pogo" in a parametric table is not a contact height.

**So: no seam joint. Each board takes its own 6-way harness drop to the Pi daughter board
and its own 24 V to 14 V buck** -- which is the fallback this document already recorded at
the end of section 3, and which is also what the user originally described ("24 V with a
buck on each board"). It costs one extra cable and one extra buck (about $1.50) and it
deletes a blind-mate joint, six notches through a light-cell wall, and two cantilevered
board tongues. The install order is unchanged except that the plug happens twice.

## 9.2 The layout, and why it routes

The whole board falls out of one observation: **the LED rows at |y| = 10.40 and 30.40 have
a 6.10 courtyard, which leaves two clear bands 13.90 mm tall running the FULL length of the
board**, at 13.45 < |y| < 27.35, plus a 14.70 mm one down the middle.

**Every driver goes in the +Y band.** Then:

* a zone's four returns leave its +Y outer LED and travel **10 mm** to the driver, crossing
  **no** row of LEDs. The obvious alternative -- drivers down the middle -- makes all twelve
  returns cross the inner row through the 3.04 mm gap between courtyards at the 9.14 mm
  fret pitch, which is the tightest routing on the instrument and would be self-inflicted.
* the SPI chain is a **straight line**: the TLC59711's inputs (SDTI 9, SCKI 10) sit at the
  bottom of its -X column and its re-buffered outputs (SCKO 11, SDTO 12) at the bottom of
  its +X column, so drivers chained left to right need no jog at all.
* the -Y band stays empty and absorbs the bay's overflow.

**A zone's LEDs rotate to face their driver.** The footprint's anodes are its -X pad column
and its cathodes its +X column, and a zone's returns leave from the cathodes -- so a zone
sitting +X of its driver is rotated 180 as a WHOLE. Rotating the whole zone keeps its three
chain links parallel. (Alternating the feed direction per COLOUR, which was the first
attempt at balancing the two sides, crosses them: four crossings per fret gap, 180 vias on
the mid board, bought nothing.)

**The rail is a plane, so the anode end of every string is a via, not a trace.** 123 pads on
the mid board stitch straight down to a plane.

## 9.2a What the routing actually did, and the two checkers it bought

**The generated part of the board routed on the first attempt.** 92 LEDs, 8 drivers, 268
nets on the mid board: **zero** unconnected in the fret field, both runs. The layout above
is why -- nothing has to cross a row of LEDs, so there is nothing for the router to fail at.

**Every defect, every run, was in the bay or in the passives I placed by hand.**

    run 1  mid   11 courtyard overlaps, 4 clearance, 1 short, 1 unconnected -- ALL in the bay
    run 2  mid    3 shorts (one spot in the bay), 1 unconnected (a driver's bulk cap)
           key    2 shorts (the same spot), 1 clearance
    run 3  key    0 unconnected, 0 shorts; ONE clearance, 18 microns short, in the same lane
    run 4  mid   ✅ 0 violations, 0 unconnected
           key   ✅ 0 violations, 0 unconnected

Four attempts, and **not one of them was a retry** -- each round changed the placement and
the next round measured it. The fret array never had a single unconnected net.

That is a useful asymmetry: the parts placed by a rule were right, and the parts placed
from remembered package sizes were wrong three different ways. So the rule got two
checkers, and both live in `elec/fret_led.py` where they run BEFORE the netlist is written
rather than forty minutes later in a DRC report.

**`check_placement` -- courtyards, read out of the footprint files, with a MINIMUM GAP.**
The inductor's land is 4.6 x 4.5, not the 4.0 x 4.0 its part number says; the 6-way PH's
courtyard is 17.2 long and the fuse was inside it. It caught its first real collision
immediately: the connector against fret 10's LEDs, 0.62 mm of overlap, which no amount of
re-routing would have fixed.

⚠ **And testing OVERLAP was not enough.** The first version asked only whether two
courtyards intersected, and a bay that passed it left a **0.10 mm lane** between a 1206's
courtyard and the 0402 beside it -- legal, and nowhere near enough room for the router to
bring a stitch via down to the plane. That lane is exactly where run 3's via landed
0.1084 mm from a GND track against a 0.127 floor. **A legal placement is not a routable
one.** The check now demands 0.30 mm, and tightening it immediately caught a second
instance that would otherwise have shipped: the feedback divider pair at 0.26.

That is what took the bay from three columns to **one**, with the 0402s paired across it.
Three columns never fitted the mid board's 10.50 mm bay except on paper -- a 1206 is 4.6
wide and eats more than half the usable width. One column leaves ~2.95 mm of clear lane
down BOTH sides for the router and the stitching, and Y was the axis with room all along:
26.6 mm between the connector's courtyard and the board edge, of which the stack uses 24.4.

**`check_walls` -- the deck is a keep-out the DRC cannot see.** Each board sits inside its
panel's comb, and the comb hangs a 1.60 mm wall onto the board's top face at every fret
boundary. Nothing in the PCB pipeline knows they exist. The first placement put each
driver's passives at xd +-4.8 and +-5.0, which at the 9.14 mm pitch between frets 24 and 23
is **0.05 mm inside the wall** -- electrically perfect, physically a collision, and it would
have surfaced an hour later in the CAD overlap gate as a part-versus-deck report. The
passives now stack in Y instead, everything within 2.7 mm of its fret centre against the
3.77 the tightest gap allows. The BODY is the test, not the courtyard: a wall may stand
over copper, it may not stand over a part.

⚠ **And fixing the bay found a latent bug in the comb.** `_boundaries` clamped a wall at a
panel edge by putting its CENTRE on the edge, so 0.80 mm of the keyhead comb's last wall
stood outside its own panel, in the seam gap. It collided with nothing -- the mid panel has
no structure under its own last 11 mm -- so the overlap gate never saw it, and the only
symptom was that the mid board's power bay was 0.80 mm shorter than the deck actually
allowed, which was exactly the margin the harness connector needed.

## 9.2b Two more, found by reading the placement rather than the DRC

Neither of these is something a checker would have reported. Both were visible in the
generated numbers and I only looked because the router was busy.

**The SPI chain ran the length of the board and back.** `fret_xs()` comes bridge-end
first, so driver one was at the +X tip and the harness -- which lands in the bay at the
-X end -- had to carry SCK and SDT 200 mm to reach it before the chain walked back. Two
passes of a clocked edge over the rail plane, the outbound one terminating at the board's
+X tip, **which is the end that comes within 14.08 mm of the magnetic pickup**. Ordering
the zones from the bay outward makes it one pass, heading away, and costs nothing.

**And the driver's pin mapping was mirrored by the same list order.** `ZONE_OUTS` keys a
trio by which side of its driver a zone sits on; with the list descending in X, `trio[0]`
was the **+X** zone being handed the **-X** pin column and the unrotated footprint. Its
cathodes faced away from its driver and its four returns had to cross the package. The
router coped, which is the point -- a routable board and a correct one are not the same
thing, and nothing downstream would ever have said so.

**The short trio, which layout.py did catch.** 8 zones on the keyhead board is two full
trios and a pair, and "the middle of two" is `trio[1]` -- the +X one, which on that board
is fret 9, **3.68 mm from the board's own +X edge**. `layout.py` refused it outright: *"no
room for a stitching via beside U3.19"*. The driver takes `trio[0]` instead, a whole fret
pitch further in. ⚠ Not the midpoint of the two, which is the obvious alternative and is
exactly where a comb wall stands.

## 9.3 ⚠ +14V on In1 and GND on In2 -- which inverts 6.3, on purpose

Section 6.3 says "GND plane directly under the LED layer", having assumed the LED loop's
return conductor is ground. **It is not.** A zone's switched current runs: local bulk ->
+14V -> four LEDs in series along 60 mm of fret -> the driver's output pin -> through the
chip to its GND pad -> back to the cap, and **the cap sits at the driver**. The conductor
that mirrors the long F.Cu run is therefore the RAIL:

    In1 = +14V    0.21 mm under F.Cu     ~15 mm2 of loop
    In2 = +14V    1.28 mm under F.Cu     ~90 mm2

Six times smaller, for a swap that costs nothing. GND is still a solid plane one layer
down, which is all a few-MHz SPI chain asks of a reference, and the two planes face each
other across 1.065 mm of core, which is free interplane decoupling. Everything else in 6.3
stands: the loop is vertical rather than flat (item 2), the buck is at the keyhead end
(item 3), and every driver has local bulk (item 4).

## 9.4 Two things the catalogue settled that this document had wrong

1. **The LED is TOP-MOUNT.** Section 5.3 called XL-5050RGBW "a side-mount 5050 chosen for a
   side-firing strip" and left the package choice open on that basis. LCSC's own attribute
   table for C7371891 reads **"Installation method: Top-mount"**, 120 degree viewing angle.
   It fires up, out of a clear encapsulant, which is exactly what a cell wants. **The
   package choice is closed and the part does not change.**
2. **Its body is 1.60 tall, not 1.40.** Same listing, same line: "Dimensions (L/W/H):
   5.0x5.0x1.6mm" -- and `elec/footprints/Steel.pretty/XINGLIGHT_XL-5050RGBW.kicad_mod` has
   carried 5.0x5.0x1.6 in its description since bronner drew it. `fret_light.LED_H` said
   1.40. It costs 0.20 mm of optical depth: h 17.95 to 17.75, the fret line 1.136 to 1.143
   : 1, still inside the threshold.

## 9.5 Parts -- and NOT ONE NEW SOURCING LINE

Every part on both boards is already sourced in `elec/fab.py`:

| | part | LCSC | why this one |
|---|---|---|---|
| LED | XL-5050RGBW | C7371891 | already selected; top-mount confirmed |
| driver | TLC59711PWPR | C116842 | ES-PWM ~19.5 kHz, 16-bit GS, a white channel |
| buck | LMR33630CRNXR | C2071783 | the **optical board's** buck, and the "C" is **2.1 MHz** |
| inductor | SWPA4030S4R7MT | C57269 | the optical board's, 4.7 uH, Isat 3.2 A |
| harness | S6B-PH-SM4-TB | C265405 | the LED strip's own connector, 4.80 deep |

**Why the 2.1 MHz variant matters here.** A 400 kHz part beside a magnetic pickup puts its
fundamental four octaves nearer the audio band, and at light load every LMR33630 pulse-skips
-- which drops the switching energy to a load-dependent rate. Measured against this board's
own floor: the eight drivers' ICC is tens of milliamps even with every LED dark, which puts
the skip rate in the hundreds of kHz. It only reaches the audio band at loads this board
cannot present while it is powered.

**And the connector was an XH for one draft.** PH is 2.00 mm pitch against XH's 2.50 and
**4.80 mm deep against 7.50** -- the mid board's bay is 9.50 mm long, and the XH fitted only
on paper. Six ways rather than four because the part is already sourced and the two spare
contacts double the rail: PH is 2 A per contact against this board's 0.60 A, so the doubling
buys a lost-contact margin, not current.

## 9.6 The bay, and both its ends were probed

The **bay** is the run at each board's -X end that lies OUTSIDE the light cells. The buck,
its inductor, the harness plug and the M4 all go there, because a part standing inside a
cell is a dark patch on that cell's floor.

    mid   -359.50 .. -350.00    9.50 mm    the mid panel's own last 10 mm, past its comb's
                                           end wall. It stops at -359.50 because the KEYHEAD
                                           comb's end wall overhangs its panel edge to
                                           -360.40 and the boards are coplanar: 0.90 mm of
                                           clearance, against the 0.70 of stack-up the
                                           panel train can take up (section 3).
    key   -573.00 .. -555.59   17.41 mm    the keyhead panel has 55 mm past its last cell.
                                           It stops at -573.00 because `wire_usb` crosses at
                                           z -14.55..-13.70 from -580.00 -X, and the board's
                                           top face IS -14.55 -- it would be lying on the
                                           cable.

Both figures come from intersecting a box with the built assembly (`tools/_probe_bay.py`),
not from reading a drawing. The same probe confirms the rest of the volume is clear: above
the boards, between the combs' end walls, there is nothing but deck.

## 9.7 Still open

1. **The mid board's cable has to get to the Pi.** It leaves the mid board's -X end into the
   seam bay, which is open to the chassis below, and then runs about 220 mm forward. That
   route is `src/wiring.py`'s to draw and it is not drawn.
2. **The M4's boss.** The hole is in the bay; the deck needs a boss hanging 14.55 mm to meet
   it. That is the same kind of feature as the UI cradle (14.30, already printed in this
   direction) but it is not modelled, and neither are section 8's retaining tabs.
3. **White solder mask.** The board IS the floor of 23 light cells and a green one absorbs.
   JLCPCB stocks white; worth pricing against what the bounce is worth.
4. **Rotations.** Unchanged from the standing warning in `elec/README.md`: the CPL carries
   KiCad's convention and JLCPCB's placement machine wants the part's. 92 LEDs make this the
   most rotation-sensitive board in the set -- check them in the previewer before paying.


---

# 10. WHERE THE BOARDS STAND (2026-09-30)

    fret_led_mid   210.8 x 70.4   4-layer   99 parts   268 nets   ✅ 0 violations, 0 unconnected
    fret_led_key   211.0 x 70.4   4-layer   61 parts   140 nets   ✅ 0 violations, 0 unconnected

Both packaged by `fab.py`: **13 BOM lines each, 8 generic passives, 0 OPEN** -- the
sourcing gate passes with nothing undecided, which is the machine-checked form of "not one
new sourcing line". Both read back into the CAD through `src/board_geom.py`, so what the
viewer shows is the routed board and its real component bodies, not a slab.

**Two pieces of shared pipeline were fixed on the way, and both were pre-existing:**

1. **`layout.drop_degenerate` compared against a flat 5 microns** when its own docstring
   argues from the ratio of a fragment's length to its WIDTH. Both boards routed clean
   except for one ~8.5 micron stub -- above the absolute floor, 3% of its own 0.25 mm
   track, so the ratio argument covers it completely and the absolute number did not. The
   floor is now `max(5 um, 0.1 x width)`.
2. **`fab.py` cannot run under `py -3.12`**, whatever `elec/README.md` said: `_check_drill`
   imports `pcbnew`, so it writes the gerbers and then dies. It needs KiCad's Python like
   the other three stages. The README is corrected.

And `elec/tidy_board.py` is new: it re-applies route.py's DETERMINISTIC post-route
clean-up to a board already on disk. Re-running a whole route to pick up an improvement in
the clean-up throws away a good board and gambles on freerouting giving another one -- the
non-determinism `elec/README.md` warns about. ⚠ It is not a repair tool and must not become
one; anything needing judgement about where copper goes belongs in route.py's repair block.
