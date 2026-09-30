# Foot lighting — the strip that fires down (brenner, 2026-09-30)

The second of the two lighting jobs. `docs/fret-led.md` is the first; between them they
replace the single side-firing strip `elec/led_strip.py` was built for, which was trying
to light the frets and the floor from one place and losing most of it bouncing around
inside the instrument.

    elec/foot_led.py     286.36 x 17.20, 4 layers, 24 LEDs, 6 zones, 2 x TLC59711
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

24 V passes straight through and the SPI runs J1 -> U1 -> U2 -> J2, so all four drivers
are one stream from one Pi pin. Only the -X board's J1 leaves the instrument.

**The seam costs no light.** The connectors are in the lane, not at the board ends, so the
LED row runs to within half a pitch of both edges and the boards butt: 48 LEDs at one
pitch end to end, the seam falling exactly half a pitch past LED 23.

## 4. The pitch, and why 48

Same Lambertian model as the fret cells, and the same lesson: evenness is decided by the
ratio of SPACING to DEPTH. Here the depth is fixed at **10.80** by the bottom prism, so
the pitch is the only lever:

| S/h | pitch | ripple |
|--:|--:|--:|
| 0.95 | 10.26 | 1.04 : 1 |
| **1.11** | **11.93** | **1.095 : 1** |
| 1.29 | 13.50 | 1.20 : 1 |
| 1.52 | 16.00 | 1.40 : 1 |

11.93 is also where the arithmetic divides: 48 LEDs, four in series per channel, is 12
zones and exactly 4 x TLC59711 with nothing wasted — 24 LEDs, 6 zones and 2 drivers on
each board. One LED coarser and it stops dividing.

## 5. ⚠ The trough is 1.90 mm deep, and the LED is what sets it

Everything on this board hangs from its underside, and the LED has to end up 0.30 off the
window — so the clear depth is AIR_GAP + LED_H = **1.90**. That fits a TLC59711 (1.20)
and an 0805 (1.45) and nothing else:

| part | height | fits 1.90? |
|---|--:|---|
| XL-5050RGBW | 1.60 | ✅ (it sets the budget) |
| TLC59711 HTSSOP-20 | 1.20 | ✅ |
| LMR33630 VQFN-HR | 0.90 | ✅ |
| SWPA4030 inductor | 3.00 | ❌ |
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
