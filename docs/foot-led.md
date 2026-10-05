# Foot lighting — the strip that fires down (brenner, 2026-09-30)

The second of the two lighting jobs. `docs/fret-led.md` is the first; between them they
replace the single side-firing strip `elec/led_strip.py` was built for, which was trying
to light the frets and the floor from one place and losing most of it bouncing around
inside the instrument.

    elec/foot_led.py     286.36 x 17.20, 4 layers, 36 LEDs, 12 zones, 4 x TLC59711
    src/foot_light.py    the window, the Z stack, the channel, the optics
                         ONE board design, TWO per instrument

## 1. What it lights, measured

`chassis._light_band()` is a transparent band through the bottom prism: **572.72 mm**
from x -592.46 to -19.74 (the run between the legs' feet), 8.00 wide in Y at y 50.35, and
10.50 deep — from the motor bay's floor at z -71.35 out to the bed face at -81.85. The
strip lies on top of it and shines in; that 10.50 of PCTG is the diffuser, and the
player's feet are what comes out the other side.

**The whole lane above it is empty, which is why this was easy.** A 15 x 5.85 box swept
the full run (`tools/_probe_mouth.py`): clear end to end. The only two things anywhere
near are the belt tensioners, whose lowest feature is z **-65.22** across y 38.15..47.08,
and the +Y rail's inner face at y **55.55**. Both mouths are open too — 44.8 mm of clear
approach at the keyhead end, 34.4 at the bridge — bounded only by the endplates.

## 2. ⚠ TWO BOARDS, and it is the assembler's limit, not a choice

JLCPCB's published assembly capability, read off the page 2026-09-30:

| | single PCB | panel |
|---|---|---|
| **Economic PCBA** | 10x10 — **470 x 500** | 10x10 — 250x250 |
| **Standard PCBA** | 70x70 — 460 x 500 | 70x70 — 250x250 |

572.72 is past both. One board cannot be built at any price. (Same page also settles
something for the fret work: Economic PCBA does **not** support castellated holes or edge
plating, so the castellated-edge variant of the seam joint was never available either.)

## 3. ⚠ ...BUT ONE PART NUMBER, and the install is what buys it

> "we install this LED before we put the -x endplate on so it can slide in from -x"
> (user, 2026-09-30)

Both halves go in the same way up and the same way round, one after the other through the
same mouth. So the +X board is **not a mirror** of the -X board — it is the SAME board,
286.36 mm further along. One design, one fab setup, one assembly setup, routed once.

A first draft had them as mirror images with their drops at opposite outer ends. That
cost a second setup and stranded one harness at the bridge end, 600 mm from the Pi.
Sliding both from -X deletes all of it.

### And it forces the chain

The +X board is pushed the full length first, so its own connector ends up 286 mm inside
and its cable can never reach the mouth. **Nor can it rise out of the channel**: below the
board is the trough, and the trough is under a board everywhere except at a board EDGE.
So the strip is a chain — every board carries an IN at its -X end and an OUT at its +X
end, both in the **component lane**, joined by a short jumper lying in the relief groove:

    Pi -> J1 [board A] J2 -> jumper -> J1 [board B] J2 (a 21-cent spare)

24 V passes straight through and the SPI runs J1 -> U1 -> U2 -> U3 -> U4 -> J2, so all
eight drivers are one stream from one Pi pin. Only the -X board's J1 leaves the instrument.

**The seam costs no light.** The connectors are in the lane, not at the board ends, so the
LED row runs to within half a pitch of both edges and the boards butt: 72 LEDs at one
pitch end to end, the seam falling exactly half a pitch past LED 35.

## 4. The pitch, and why 72

Same Lambertian model as the fret cells, and the same lesson: evenness is decided by the
ratio of SPACING to DEPTH. Here the depth is fixed at **10.80** by the bottom prism, so
the pitch is the only lever -- and the pitch is the run over the LED count:

| LEDs | pitch | S/h | ripple | courtyard gap |
|--:|--:|--:|--:|--:|
| 48 | 11.932 | 1.105 | 1.095 : 1 | 5.83 |
| **72** | **7.954** | **0.737** | **1.008 : 1** | **1.85** |
| 96 | 5.966 | 0.552 | 1.001 : 1 | **-0.13 -- overlaps** |

**72 is the densest the row can physically be.** The XL-5050RGBW's courtyard is 6.10 mm,
so at 96 LEDs neighbours overlap by 0.13 and `check_placement` rejects the board before
anything is routed. Optically the run is finished well before that: 1.008 : 1 is flat.

## 4a. Zones, series strings, and where the money is

Two numbers describe the strip's addressing and they are not independent:

    zones    = N_LED / N_SERIES          (how finely it can be addressed)
    channels = zones x 4                 (RGBW -- and what the DRIVERS cost)

A TLC59711 carries twelve channels, i.e. three zones, so the zone count has to be a
multiple of three. **24 zones, three LEDs each** is where this landed:

| | |
|---|--:|
| LEDs per instrument | 72 |
| zones | 24, of 23.86 mm |
| channels | 96 |
| TLC59711 | 8 (4 per board) |
| rail | 11.50 V (11.00 until 2026-10-05, see the last section) |
| rail current | 1.44 A |

> "I'd like to have closer to 24 controllable zones" (user, 2026-09-30)
> "would it benefit us to put 3 LEDs per zone instead of 2? Same number of zones just
> increase LED density" (user, 2026-09-30)

**The second question is the cheap one and the answer is yes.** Channels follow ZONES, so
holding zones at 24 and raising the string from 2 to 3 leaves the channel count -- and
therefore the driver count, the driver cost, the board area and the rail CURRENT -- exactly
where they were. A channel draws 15.0 mA whether it feeds two dice or three:

| | 48 LEDs, 2 a zone | **72 LEDs, 3 a zone** |
|---|--:|--:|
| zones / channels / drivers | 24 / 96 / 8 | **24 / 96 / 8** |
| driver cost | $19.28 | **$19.28** |
| LED cost | $3.12 | $4.68 |
| rail | 7.67 V | 11.50 V |
| rail current | 1.44 A | **1.44 A** |
| light | 1x | **1.5x** |
| ripple | 1.095 : 1 | 1.008 : 1 |

Half again the light for **$1.56 an instrument**, paid for in rail volts -- the one thing
this rail has spare. The whole electrical change is the feedback divider: 100k over
10k || 200k on the LMR33630's 1.000 V reference is 11.50 V, against a 10.2 V string at the
LED's 3.4 V maximum (it was 100k / 10k = 11.00 V against a "3.2 V maximum" the datasheet
does not give -- corrected 2026-10-05).

### What 3 a zone costs, stated plainly

| | 2 a zone | 3 a zone |
|---|--:|--:|
| through the -X J1 and the seam pogo | 0.52 A | **0.77 A** of a 3 A XH contact and a 12 A pogo |
| LED dissipation per board | 4.25 W | **6.37 W** (14.8 -> 22.2 mW per mm of strip) |
| dissipation per driver | 0.32 W | 0.39 W |
| clear lane between LED courtyards | 5.83 mm | **1.85 mm** |
| solder joints per board | 192 LED pads | 288 |
| LEDs in series per zone | 2 | 3 |

Four of those are worth keeping in mind rather than merely noting:

1. **0.77 A through one contact**, because the -X board's inlet and the seam carry BOTH
   boards. It was the tightest number on the strip when the inlet was a 1 A JST SH; on the
   XH socket it is 26 % of the rating.
   It is an every-zone-full-white worst case that the effects daemon caps, the same way it
   caps the fret boards' 1.38 A -- but it is the number that would have to be solved first
   if the strip ever grew again.
2. **6.37 W of LED heat per board** goes into a still-air plastic channel, 0.30 mm off a
   PCTG window. The 4-layer GND plane is the heatsink and 286 mm is a lot of it, but this
   is the first thing to measure on the prototype.
3. **1.85 mm between courtyards** means the LED row is full. There is no room left to
   substitute a physically larger RGBW 5050 -- a second source with a wider courtyard would
   not fit, where at 48 LEDs it would have had 5.83 mm to grow into.
4. **Three dice in series instead of two** is 1.5x the exposure to an OPEN failure taking a
   whole zone dark. The zone goes dark either way; there are simply more parts that can do
   it. A SHORT costs one die's light and nothing else.

### ⚠ It does NOT match the fret boards, and that is worth being exact about

The fret cells are **four** in series on a **14.0 V** rail (`src/fret_light.py`,
`elec/fret_led.py` line 112: "FOUR DICE IN SERIES: W/G/B are 3.0-3.2 V each, so 12.8 V").
So neither 2 nor 3 matches them, and 4 is not available here: four a zone at 24 zones is
96 LEDs, which is the 5.966 pitch whose courtyards overlap. Four a zone is only reachable
by going back to 12 zones, which is what 24 zones replaced.

**The commonality that matters is already complete.** The foot strip and the fret boards
share the LED (C7371891), the driver (C116842), the buck (C2071783) and the inductor
(C57269) -- every active part. The only thing that differs is R11's value, and that would
still differ at any string length that fits: a series string sets the rail, and a 572 mm
floor wash and a 9.14 mm fret cell are not going to want the same one.

## 5. ⚠ The trough is 1.90 mm deep, and the LED is what sets it

Everything on this board hangs from its underside, and the LED has to end up 0.30 off the
window — so the clear depth is AIR_GAP + LED_H = **1.90**. That fits a TLC59711 (1.20)
and an 0805 (1.45) and nothing else:

| part | height | fits 1.90? |
|---|--:|---|
| XL-5050RGBW | 1.60 | ✅ (it sets the budget) |
| TLC59711 HTSSOP-20 | 1.20 | ✅ |
| LMR33630 VQFN-HR | 0.90 | ✅ |
| SWPA4030 inductor (SWPA5040S, 4.00, since 2026-10-05) | 3.00 | ❌ |
| **JST PH side-entry** | **5.50** | ❌ |
| **JST SH side-entry** | **2.95** | ❌ without relief |

So the opaque bottom is **relieved 1.50 mm under the component lane only** — 6.50 wide,
running the WHOLE length. Running it the whole length is the point: a local pocket would
tie the board's layout to an X in the chassis, which is exactly what the user asked to be
rid of. It takes the bottom prism from 10.50 to 9.00 over a 6.50 strip, nowhere near the
light window, and buys 3.40 mm.

⚠ **The 2.95 is off JST's own drawing** (SH catalogue, side-entry side view), not a
catalogue attribute. That distinction is the whole lesson of the pogo retraction in
`docs/fret-led.md` section 9.1, and it is the one new sourcing line on this board:
**SM04B-SRSS-TB(LF)(SN), C160404**, 4-way, 1.0 A / 50 V against 0.24 A at 24 V, 3,495 in
stock. Every other part is already bought for another board.

## 6. ⚠ Four layers — and NOT for the pickup's sake

On noise this board wants two. The fret boards took four because their +X edge comes
within 14.08 mm of the magnetic pickup; this strip lies in the chassis bottom, ~66 mm from
the coil in Y and Z together, and coupling falls as 1/r³:

    fret board, 4-layer   15.9 mm2 / 14.08^3 = 0.0057
    this board, 2-layer   96   mm2 / 66^3    = 0.00033

**17x quieter on two layers than the board already judged acceptable on four.** That
argument stands and it is not what decided this.

**What decided it is that a pour cannot stay in one piece on a 17 mm board.** Two layers
puts the GND pour on F.Cu with the parts, and the LED row's 6.10 courtyard plus the lane's
7.80 leave it 3.30 mm to get past every LED, in 24 places. The first route came back with
7 unconnected and **four of them were GND zone islands** — the pour cut into pieces that
never met. The other three were zone returns that ran out of room in the same squeeze.

Widening is the cheap fix and the chassis will not have it: the motor bay's structure
comes in below y ~40 and the rail's inner face is at 55.55. Four layers puts GND and the
rail on their own planes and gives both outer layers back to routing, for about $19 on an
order of five. In1 = +14V and In2 = GND, for the reason `fret_led.py` records: the
conductor that mirrors a zone's long F.Cu run is the RAIL, because the bulk sits at the
driver.

## 7. The channel

A plain slot the board slides into, built into the chassis bottom by `foot_light.channel()`
and cut clear first by `slot_cut()` — the channel is additive, so unioning walls onto the
bottom says nothing about what was already standing in the slot.

    z -71.35   the window's top face = the channel floor
       -71.05  the LED's emitting face (0.30 of print tolerance, not optics)
       -69.45  the board's underside
       -67.85  the board's top -- and the retaining lips' 45 deg ramp starts here
       -67.55  the ramp over the board's EDGE: 0.30 of lift, = the lateral play
       -66.75  the ramp reaches 0.80 over the board and the flat cap starts
       -65.95  the cap's top -- 0.73 clear of the belt tensioners

Shoulders under the board's edges, lips over them, a wall on -Y and the chassis's own body
as the wall on +Y.

**The lips are 45 deg ramps, and there is no horizontal overhang anywhere in the channel.**
The chassis builds world +Z, so a lip reaching flat over the slot is an unsupported
ceiling: 2 mm of it bridges, but a bridge sags and its underside comes out rough -- and
that underside is the face that holds the board down. So each lip rises off its wall at
45 deg instead, 1.10 mm out and 1.10 mm up, then a flat 0.80 cap. Every layer lands on the
one below it.

**The ramp also deletes a number.** It starts at exactly the board's top plane on the wall
face, which is SLOT_PLAY outboard of the board's edge -- so over the edge the ramp stands
0.30 proud, and the clearance above the board IS the lateral play rather than a second
figure to keep in step with it. The old flat lip had a separate `SLOT_CLR = 0.20`; there
is nothing left for it to mean. Effective grip over the board: 0.80 mm each side against
0.30 of Y play it could ever use.

The middle of the slot is still open, which lets the drivers' heat out into the bay.

**No mounting hole.** The channel holds five faces and the sixth is the sliding axis,
which the -X endplate closes when it goes on — the same argument `elec/lever_sensor.py`
records for its grooves.

## 8. Install

1. Assemble the chassis. **Leave the -X endplate off.**
2. Join the two boards with the jumper, outside the instrument.
3. Slide the pair in from -X, far board first, until the -X board's end is flush with
   the window's -X end.
4. Plug the -X board's J1 cable and run it to the Pi daughter board.
5. Fit the -X endplate, which closes the channel.

## 9. Still open

1. **The Pi daughter board now owes three lighting drops** — two fret, one foot — plus
   whatever else. bronner's `pi_cap` has not been asked for the third.
2. **`elec/led_strip.py` is now superseded** and still in `fab.py`'s BOARDS. It is the old
   single-source strip; both of its jobs are done by `fret_led` and `foot_led`. It should
   be retired, but deleting a board touches BOM.md and the fab packages, so it is flagged
   rather than done.
3. **The jumper is not specified.** ~16 mm of free wire between two SH plugs, in the
   relief groove. LCSC do custom cables at MOQ 1; the length wants fixing off the routed
   boards rather than off this document.


## The manual quality pass, 2026-10-05: what changed and why

Read against the makers' sheets and the routed boards (cadkit/PCB_QUALITY.md, M1-M42):

1. **Rail 11.00 -> 11.50 V.** XINGLIGHT give green, blue and white 3.0 to 3.4 V at 20 mA,
   not 3.2. Three in series is 10.2 V; the old rail's low limit (10.64 V) left the sink
   0.44 V, the new one's (11.12 V) leaves 0.92. 24 V draw, every zone full white: 0.77 A
   for both boards.
2. **The buck's layout is TI's now** (`elec/buck_cell.py`, shared with the keyhead fret
   board): a 100 nF / 50 V at each of the package's two VIN/PGND pairs, the feedback
   divider at the FB pin, and copper slabs under the input side. The slabs are for heat:
   the RNX package has no thermal pad and loses about 0.9 W here whatever the load
   (24 V in, 2.1 MHz).
3. **Seven vias under each TLC59711**, not one: about 0.6 W typical, 0.75 W worst, per
   driver at full white.
4. **Every 1206 stands across the strip**, the fuse included: a 290 x 24 mm board bends
   along its length.
5. **Values carry their ratings and the fuses are part numbers**: board A JFC1206-1200FS
   (2 A, it carries both boards), board B JFC1206-1100FS (1 A).
6. **Three labelled test pads** by the buck on each board: +24V, +11V5, GND.
7. **The inductor is SWPA5040S3R3NT** (C305173; 3.3 uH, 5 x 5 x 4 mm), not the 4 x 4
   SWPA4030S4R7MT. The old part saturates at 2.90 A guaranteed (3.20 typical) and TI
   require an inductor that does not saturate below the regulator's low-side limit,
   3.5 A typical. The new one is 3.95 A guaranteed at less than half the resistance, and
   3.3 uH is TI's own table value for 12 V out at 2.1 MHz.
8. **1 k in series with SCK and SDT at the cable socket** (R21, R22). A Pi that is up
   while this board is dark -- a fuse open, the 24 V lead off, a Pi on USB power on the
   bench -- would otherwise power the first driver's logic through its input protection
   diodes. 1 k holds that to 2.7 mA.
9. **The regulator's VCC capacitor stands at its pin**, with its ground pad on the track
   from the pin beside it; it was reached through two vias.
