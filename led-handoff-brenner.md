# LED strip — handoff from bronner to brenner (2026-09-29)

Everything bronner knows about the LED strip, its inter-section joint, and its noise
coupling. Written to be read cold. Where this disagrees with a prompt, **this and
`docs/bronner-work-items.md` are the record** — several prompt snapshots have gone stale.

---

## 1. What the strip is, as built

`elec/led_strip.py`. Four sections in a channel on the +Y rail's inner face, lighting the
body from the side.

    BOARD_W, BOARD_L   139.0, 20.0 + SLOT_TAB
    LED_PITCH          13.5
    JUNCTION_GAP       8.0
    layers             2        zones: ("GND", "F.Cu", 0.3)
    J_PINS             ("GND", "V5", "V5", "GND", "SCK", "SDI")   <- SIX, see section 3

Bare board past the end LED is 15.5 mm each side, so a 139 mm board carries 108 mm of
LEDs. **That is the density cost the user objected to**, and it is why the joint matters.

### ⚠ DRC state — `led_strip` has 1 UNCONNECTED and it is DELIBERATE

A 2.0 mm GND track on F.Cu with both ends loose, sitting in the GND zone it never joins.
Reproduces exactly on re-run, so it is generated, not corruption. Cause is in the log:

    ⚠ 3 stitch via(s) landed where the plane is not: GND at 136.35,100.33,
      55.35,100.33, 95.85,100.33  -- board-local x -44.65, -4.15, 36.35, all at
      y -0.33, at EXACTLY 40.5 mm pitch, so it is a repeated per-section feature

`elec/layout.py`'s docstring says what to do: "this is a placement problem. Report it, do
not tidy it away." An earlier probe suggested deleting the tracks and was **wrong twice
over** — `GetPosition()` is a track's START, so a track whose END lands on the via reads as
absent, and deleting the via would leave the stub and could cut the pad's only return.
**DO NOT TIDY.** The fix is to make the GND plane REACH those three points, or move the
pads. It is an `led_strip` layout change, pre-existing.

**Invocation, because it is easy to get wrong:**

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/finish.py elec/out/led_strip

`py -3.12` cannot import `pcbnew`, and a bare board NAME is not a path. Run
`py -3.12 elec/led_strip.py` first if you changed the source — `finish.py` refuses a
netlist older than its generator, and that guard is the only reason the numbers mean
anything.

---

## 2. The joint between sections — the whole investigation, and where it landed

The user's ask: "I see wires joining the LED segments, that seems like it would lead to
reduced LED density. Can we have connectors that connect board to board directly instead?"

### The rule that governs every option

**NO HAND SOLDERING ANYWHERE. Only PCBA soldering — what the assembly house reflows onto a
board. Not allowed even ON a PCB.** The user restated this twice. It kills castellated
sections butted and soldered across the seam, which bronner proposed on a misreading of the
older wording ("solder only on PCBs") and had to withdraw.

### Candidates that died, and the single reason most of them died

| candidate | why it failed |
|---|---|
| Castellation + solder | hand soldering |
| Harwin M20 | not in the JLCPCB assembly library at all |
| "1.27 mm 2X10P" | a DC3 ribbon header — mates to a cable, not a board |
| FX23L | plug only, no socket |
| Hirose DF40 | no pin count with usable stock on BOTH halves (70P header: **4 units**) |
| Card edge (ED06BGFBK, C5173287) | 15.6 mm height above board, slot faces UP — takes a card inserted downward, not a board butted in-plane |
| Mezzanine generally | needs the boards to OVERLAP; these lie flat in one channel |
| 2.00 mm pitch | right-angle FEMALE stocked (C22465680, 602), matching MALE is not |

**⚠ THE RULE THIS TAUGHT: check that BOTH halves have stock FIRST — before pitch, current,
height or coplanarity.** JLCPCB's board-to-board split is Female 82 / Male 26, because its
customers usually mate to a module that already carries the other half. A joint where *we*
supply both halves is the case the library is worst at.

### ⚠⚠ THE VERDICT WAS WRONG, AND THIS IS THE MOST IMPORTANT PART OF THIS DOC

`.ins/WORKLIST.md` concluded, and bronner twice confirmed, that "every stocked 2.54 1x6
right-angle female is H8.5 … there is no H2.5 female", so a coplanar right-angle mate was
impossible. **Every part in that evidence list is an Asian-brand family** (hanxia,
kinghelm, XKB) where H genuinely is 8.5. **Samtec's right-angle range is 2.41 mm and was
never in the sample.** Enumerating one manufacturer's family is not enumerating the
category. Measured on LCSC 2026-09-29:

| ways | half | LCSC | part | insulation | rating | stock | $ |
|---|---|---|---|---|---|---|---|
| 4P | female | C6687085 | SSW-104-02-T-S-RA | 2.41 | 4.7 A | 53 | 0.44 |
| 4P | male | C7402910 | TSW-104-08-T-S-RA | 3.02 | — | **1** (1,749 other-supplier, 9–14 d) | 0.39 |
| **5P** | **female** | **C6687110** | **SSW-105-02-G-S-RA** | 2.41 | 4.7 A | **92** | 1.68 |
| **5P** | **male** | **C6561632** | **TSW-105-08-F-S-RA** | 3.02 | — | **122** | 0.77 |
| 8P | female | C7019030 | SSQ-108-02-T-S-RA | 2.41 | 6.3 A | 100 | 1.22 |

**RECOMMENDATION: the 5P pair, used as a four-way.** 92/122 is the only time in this whole
investigation both halves have been three-figure. The 5P female is GOLD where the 4P is
tin. Samtec TSW (male) and SSW (female) are ONE SERIES DESIGNED TO MATE, which is the
reason to trust the contact axes rather than the body numbers. Both are "E" (Extended) in
the JLCPCB assembly library — **setup fee, but no consignment**. About $2.45 a joint.
The 5th way is not waste: GND/V+/SCK/SDI uses four and the spare is best spent as a second
ground beside the data pair.

⚠ **STILL OPEN AND IT DECIDES THE JOINT:** "Insulation Height" is the plastic BODY height,
not the CONTACT-AXIS height, and no catalogue field carries the axis for either half.
`board_geom` currently carries **8.5 for BOTH as a claim to be checked, not a measurement**
(the 5.0 that stood there before was carried over from the 2.00 mm part and was wrong by
3.5 mm). **Read both mechanical drawings before ordering.** Buying a matched series is the
mitigation, not the proof.

⚠ **AND SEARCH THE REQUIREMENT, NOT THE LABEL.** The joint needs FOUR CONDUCTORS. Insisting
on a part labelled 4P nearly missed the 5P pair, which is stocked an order of magnitude
better. Same shape of error as the one-manufacturer sample above.

---

## 3. Why six conductors, and why four is now enough

`J_PINS` is `("GND", "V5", "V5", "GND", "SCK", "SDI")` — the power pair is DOUBLED because
a section draws **2.2 A at 5 V** and one pin would not carry it.

**4P is available and it is NOT because of 24 V.** The 2.54 mm parts are rated **3 A/pin**,
so 2.2 A passes on a single pin at 5 V. 24 V (0.38 A) makes it easier and is where it
matters for pogo (whose best-stocked singles are 2.5 A, almost no margin), but 24 V is not
what unlocks 4P. **The 24 V thread is retired** — it was solving a current problem that the
3 A rating had already solved.

**⚠ 4P IS NOT BUILT.** `elec/led_strip.py` still declares six pins and `src/wiring.py` still
draws six conductors (two loops, around lines 1105 and 1134). Collapsing to four is a real
change across the netlist, the CAD and `board_geom` — not a part swap.

### Pogo pins — checked, and worse than the headers here

LCSC category 742. 6P modules exist but are unbuyable: C5280860 (34 units, 1 A),
C5200690 (1, discontinued), C7498711 (0 stock, 3 A but only 200 mating cycles). The 1P
SINGLES are abundant and the pitch would be ours (YTC1P-2010-01 C5221287, 7,790, **2.5 A**;
BWCD-L3.5W2.0H1.0 C2826547, 10,585, 1.5 A), and single-gender dodges the stock wall
entirely — but a coplanar butt joint needs the pins to fire ALONG the board plane, and pogo
also needs SUSTAINED COMPRESSION, which is a channel mechanism nobody has designed. A
right-angle SMD pogo package does exist in the category facets
(`SMD,P=5mm,Surface Mount,Right Angle`) and was **never enumerated** — that is the one pogo
stone left unturned.

---

## 4. Fewer junctions — still the no-part answer

4 sections to 2 takes the dark span from **117 mm to 39 mm** and needs no connector at all.
Cost: a 290 mm section carries about 19 LEDs on 6 drivers, doubling per-section current,
which makes the 2 A contact limit tighter — the thing 24 V would genuinely fix. The two
combine well. This was the fallback while the connector looked impossible; with the 5P pair
found, it is now a choice rather than a necessity.

---

## 5. ⚠ NOISE: the strip is 9.1 mm from the magnetic pickup

Do not touch the strip's layout without reading this.

`led_strip_3` runs **9.1 mm** from the pickup. Its **695 mm² supply loop at 0.54 A,
PWM-enveloped, is about 136× the aggressor a local buck converter would be.** bronner had
assumed 150 mm and was wrong by roughly 4500×, *in the reassuring direction*.

Two levers, both measured:

1. **4-layer with a GND plane** — worth about 25×. **Attempted and reverted**: the 4-layer
   experiment left 3 unconnected (one cathode per driver) and `rounds=3` did not help.
2. **Move the strip to the chassis floor** — worth about 67×, and it was the user's own
   suggestion. ⚠ **THIS CHANGES WHERE THE LIGHT GOES**: the strip currently sits in a
   channel on the +Y rail's inner face and lights the body from the side; on the floor it
   lights upward. That is a lighting-design decision for the user, not a noise one, and it
   has never been put to them as such.

Adding bucked 24 V costs about **1.5 dB**; the two fixes buy about 65 dB. Absolute dB
figures are NOT quotable — they depend on pickup impedance and gain that nobody has
measured.

---

## 6. Things that are DONE, so you do not redo them

* **Ask #4 — "the wiring run for the 6 pin from the LED clips through the pi and the
  chassis"** — **SOLVED**, and not by re-routing. The Pi moved flat onto the chassis floor
  and all twelve clips (`pi5` ×6, `chassis_2` ×6) vanished. An earlier attempt to fix it by
  re-routing the cable cost the gate 109 → 154 and was reverted. **If you touch that cable,
  the old failure mode is six conductors given identical waypoints collapsing onto one line
  — 15 self-overlap pairs, which is exactly C(6,2). Any re-route needs per-conductor
  offsets like `CAN_OFF` / `PWR_OFF` in `src/wiring.py`.**
* The LED cable wants a CHANNEL through the height-adjust block — specified in
  `docs/bronner-work-items.md`, not built.
* `WIRE_OK`'s bus-B entry is already `{"motor_ctrl", "kl_pcb"}`. Prompts still say
  `tee_pcb`; they are stale.

---

## 7. Where to look

| what | where |
|---|---|
| strip source | `elec/led_strip.py` |
| the cable and its endpoints | `src/wiring.py`, the `wire_led_*` loop (about line 1105) |
| section-to-section jumpers | `src/wiring.py` (about line 1134) |
| connector history, verbatim | `.ins/WORKLIST.md` — **search it before opening a browser**, it cost bronner two ticks not to |
| everything else | `docs/bronner-work-items.md` sections 5a–5s |

**Method note that earned its place:** three separate clearance questions in this work were
answered with a DATUM and all three answers were wrong. Put a box where the part would go
and intersect it. The first collision test settled in one run what three derivations had got
wrong in three different ways.
