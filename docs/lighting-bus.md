# The lighting bus — what the Pi cap and the motor board owe the LEDs (brenner, 2026-09-30)

Three lit things, two boards that feed them. This is the interface, written from the LED
side, so `elec/pi_cap.py` (bronner) and the motor board can be built against it.

    fret_led_mid   5 x TLC59711    J1 6-way PH   S6B-PH-SM4-TB   C265405
    fret_led_key   3 x TLC59711    J1 6-way PH   S6B-PH-SM4-TB   C265405
    foot_led  x2   8 x TLC59711    J1 4-way SH   SM04B-SRSS-TB   C160404

## 1. ⚠ THREE DROPS, NOT TWO

> "we'll need the pi to be able to drive both via the data wire and the motor board to
> drive both via the power wire" (user, 2026-09-30)

Two is the natural guess — fret lighting and foot lighting — and the foot strip really is
**one** drop: its two boards are a chain, IN at each board's −X end and OUT at its +X end,
joined by a jumper in the relief groove, and only the −X board's J1 leaves the instrument.

The fret boards are **two**, and it is the pogo retraction that makes them so.
`docs/fret-led.md` §9.1 withdrew the seam joint that would have carried power and SPI from
`fret_led_mid` into `fret_led_key` — C5203987's contact axis sits 1.90 mm above its own
board and misses a coplanar neighbour's 1.6 mm edge — and the replacement it named was
**one harness drop per fret board**. Chaining them anyway means a cable across the deck
**panel seam**, and the two panels separate when the deck slides.

So: **three headers** as it stands. Two questions were put to that and both are answered
below; neither reopens the blind-mate, one may still take the count to two.

### 1a ⚠ PIN HEADERS: right mechanism, part not in the library

> "Why can't we use either pin or pogo connectors? Pin meaning the ones the raspberry pi
> comes with" (user, 2026-09-30)

Worth taking seriously, because §9.1 of the fret doc retracted the POGO joint and the
reason does not carry over. The pogo died on a CONTACT-HEIGHT mismatch -- the pin fires
1.90 mm above its own board and the facing board presents a 1.6 mm laminate edge, so it
shoots over it. A header-and-socket pair has no such mismatch: both halves carry their
contacts at the same height above their own board. §9.1's own table concedes as much,
saying of tip-to-tip pogo that "the heights DO agree".

**What closes it is stock.** A coplanar butt joint needs RIGHT-ANGLE on both halves --
that is what R/A pin header + R/A female header are sold for. Asked JLCPCB's own parts
API, 2026-09-30:

| search | results | right-angle, in stock |
|---|--:|--:|
| `female header` | 63 | **0** |
| `pin header` | 181 | **0** |

Every in-stock female header is vertical SMD or through-hole. So the pair cannot be
assembled without consignment, which is the standing no -- and it is the same wall the
four candidates in the connector-family note hit.

The Pi's own headers fail twice over regardless. They are **through-hole**, and these
boards are SMT throughout because the underside clears the CAN harness by 1.00 mm, so a
tail would be in the cable. And at 2.54 mm the mated pair spans ~12 mm against a
**10.40 mm** seam bay -- the same 1.6 mm short that killed tip-to-tip pogo.

### 1b ⚠ MORE POGOS EXIST THAN §9.1 EVALUATED, and they fail the same way

In stock at JLCPCB: C5157217, C5157218, C5157273, C5157274, C5157283 (Xinyangze) and
C2842931 (kinghelm). None of them helps. A barrel lying on its pad puts the contact axis
above its own board whatever its diameter, so it fires over a coplanar neighbour's edge --
that is geometry, not catalogue, and it is why §9.1 called tip-to-tip the only
coplanar-valid arrangement. Tip-to-tip needs 12.00 mm against 10.40.

### 1c The jumper is the one live route to TWO headers

No blind-mate, no new sourcing risk: give `fret_led_mid` a second connector and run a
212 mm cable under the key panel to `fret_led_key`'s existing J1.

    Pi -> mid J1 (6-way PH, in) ... mid J2 (4-way SH, out) -> 212 mm -> key J1

**There is room for it.** mid's bay is tight in X -- §9 records the 6-way PH would not fit
until the board's end moved -- but its -Y half is empty, which is where F1 went for exactly
that reason. A 4-way SH is 7.80 x 6.56.

**What it actually buys, stated honestly:** one fewer Pi header. It trades a long Pi-to-key
cable for a shorter mid-to-key one plus a connector, and it moves the unplug-for-service
point from the Pi into the seam. Note that separate drops do NOT avoid an unplug -- each
board already has a cable that must be freed before its panel can lift -- so this is a
wash on service, not a loss. **Not taken yet: it is a board change to a board that has
just routed 0/0, and the header count is bronner's constraint to weigh, not mine.**

## 2. ⚠ THE DRIVER HAS NO CHIP SELECT, WHICH DECIDES THE DATA TOPOLOGY

A TLC59711 is write-only and unaddressed: it takes SCK and SDT, shifts 224 bits through
itself, and passes the overflow out of SCKO/SDTO to the next one. There is no way to talk
to one chain and not another on a shared pair — two chains on one data line show the
**same picture**. So independent content leaves exactly two topologies:

| | wires from the Pi | cost |
|---|---|---|
| one long daisy chain | 1 SCK + 1 SDT | needs the seam hop §1 rules out |
| **a data line per chain** | **1 SCK + 3 SDT** | **4 GPIO, no seam crossing** |

**Take the second.** SCK is common to all three headers; each chain gets its own SDT.
They latch together, which is what you want — the whole instrument's lighting updates on
one edge.

**The chains are unequal (5, 3, 8 drivers) and that is free.** Clock the longest — 8 ×
224 = 1792 bits — and pad the two short chains at the FRONT with dummy words. The padding
shifts off the end of each short chain and is discarded; its last driver's SCKO/SDTO are
netted `SCKO_CHAIN_END_NC` / `SDTO_CHAIN_END_NC` precisely because nothing is downstream.
One 1792-bit burst at 10 MHz is **0.18 ms**, so the whole instrument redraws inside a
fifth of a millisecond.

## 3. Power: one 24 V bus, and the LED boards make their own rails

Every lit board carries its own buck, so what the motor board owes them is **24 V and
nothing else**. That is deliberate and the foot strip records why: a made rail sent down a
600 mm cable at 1.44 A drops ~0.37 V in the wire, nearly a third of the sink headroom, and
it drops further the brighter the strip gets — the zones would dim as a group.

| drop | 24 V draw | rail it makes |
|---|--:|---|
| fret_led_mid | 0.583 A | 14.0 V |
| fret_led_key | 0.311 A | 14.0 V |
| foot (both boards, through one inlet) | **0.733 A** | 11.0 V |
| **total, every zone full white** | **1.63 A** | 39 W |

⚠ **That total is the software-capped worst case**, not the operating point — it is every
LED of all three boards at full white simultaneously. The effects daemon caps it the same
way it caps the fret boards' 1.38 A on its own.

⚠ **0.73 A of it goes through ONE SM04B-SRSS contact**, because the foot strip's −X inlet
and its seam jumper carry both foot boards. 73% of the contact's rating, and the first
thing to revisit if the foot strip ever grows again.

## 4. What the Pi cap needs

1. **Three LED headers.** Two 6-way (fret mid, fret key) and one 4-way (foot), or three
   6-way with the foot cable's far end crimped to SH — the board-side part numbers above
   are fixed, the cap side is bronner's choice.
2. **Pin-out per header**, matching each board's J1 exactly:
   - fret, 6-way PH: `GND, V24, V24, GND, SCK, SDT` — power is doubled, signal is not.
   - foot, 4-way SH: `V24, GND, SCK, SDT`, with **V24 on an end pad** (the SH is 1.00 mm
     pitch and an interior pad cannot be entered by a 0.15 track past two 0.127
     clearances — three separate routes failed on it before it moved).
3. **Four GPIO**: one SCK fanned to all three headers, three separate SDT.
4. **24 V in from the motor board**, 2 A of headroom, bussed to all three headers.

## 5. Still open

1. **`elec/pi_cap.py` is on `agent/bronner` and not on main**, so nothing here can be
   built against it yet (BOM.md says the same of the UI ribbon's fourteen ways). This
   document is the ask.
2. **Cable lengths are unspecified.** All three run from the Pi to their boards and want
   fixing off the placed geometry rather than guessed here.
3. **Whether SCK wants a series resistor per header.** Three stubs off one driver on
   cables of different lengths is a reflection story; at 10 MHz into 1 m of ribbon it is
   worth a look before the cap is laid out, and it is the cap's component to carry.
