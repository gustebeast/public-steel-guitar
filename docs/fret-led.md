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
| mid | 9–24 (16) | 7 | 211.9 |
| keyhead | 1–8 (8) | 3 | 193.1 |

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
this whole split exists to eliminate. Build them as **opaque PCTG walls with the aperture
left transparent**, as a separate part clipped under the deck carrying the LED board, not
as deck geometry — the deck prints face-down, so tunnels hanging off its underside would be
unsupported ceilings, and a separate part prints in its own orientation.

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

⚠ **Two things to settle before committing:** the pogo's **working travel and preload
force** against the panel's 0.05 mm design gap (read the drawing — the catalogue's "6 mm /
8 mm" fields are length and stroke and I have not confirmed which is which), and whether a
**proud contact** is acceptable at a blind mate given the project's standing rule about
that joint class.

⚠ **AND CONSIDER NOT JOINING THEM AT ALL.** Each panel is already a separate assembly that
comes off on its own. Giving each board its own 4-way drop off the main harness costs one
more connector on the harness and deletes the seam joint, its alignment problem and its
preload problem outright. The UI station's install order — build the panel off the
instrument, slide it on, plug it — is the pattern that already works here.

---

## 4. What is NOT decided

1. **RGBW per fret, or one colour for all?** Everything above assumes per-fret RGBW
   (96 channels, 8 drivers). If the frets are one static colour the drivers disappear
   entirely and the LEDs become series strings off the 24 V rail — a large cost difference,
   and it depends on whether fret lighting is ever meant to indicate anything.
2. **The LED rail voltage** — see section 2, 12 V vs 5 V.
3. **Fret 1 has 8.27 mm, not 17 mm**, because `wire_ui` and the Pi are under it. Either the
   harness moves or fret 1 gets a shallower tunnel and a 4th LED.
4. **Which LED.** The existing XL-5050RGBW is a side-mount 5050 chosen for a side-firing
   strip; this board fires UP, so the package choice is open again.
