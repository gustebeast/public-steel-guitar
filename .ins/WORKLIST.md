# bronner loop worklist (started 2026-09-21)

The /loop re-reads this each tick. Tick = take the top OPEN item, do it, commit, re-render
(copy scratch.step -> assembly.step: the user's "bronner" FreeCAD tab tracks assembly.step),
mark it here. Items needing the user go to NEEDS USER, not skipped silently.

## OPEN
11. motor_ctrl respin -- bus B becomes a 5 V PH pass-through (handed over by branner):
    * J2 -> S8B-PH-SM4-TB (LCSC C265121, SMT side-entry), trunk IN on ways 1-4, OUT on
      5-8, in elec/harness.py's pin order: the controller is a MID-BUS node now (user
      topology option B -- pedals and the lever chain both arrive at -X).
    * J2's +V moves off v24 to the board's 5 V rail (U5 out). CHECK U5 HEADROOM: ~11
      nodes x ~50 mA = ~0.5 A on top of its existing 5 V loads.
    * DROP the bus-B 120 ohm termination (end-of-bus part; the controller is no longer an
      end). Keep bus A's. Termination now = JP1 + R4 closed on exactly two boards, the
      +X-end lever and the far-end pedal.
    * Stale header comment: bus B has 11 sensor boards (6 knee levers + 5 pedals), not 8.
    * Board spec: docs/lever-sensor-respin.md. cad_geom_check lever_sensor MISMATCHES until
      the lever board is re-spun -- that is the handoff, not a regression.
12. LED strip re-spin for direct board-to-board (user, 2026-09-22). BLOCKED ON PART
    GEOMETRY -- do not place by eye, that is what hung both connectors off the ends last time.
    * SETTLED: the pitch that makes a junction invisible is DERIVED, not chosen --
      2*(W/2 - 4P) + G = P  ->  P = (W + G)/9, where G is the mated board-edge gap. The
      connectors go in the DRIVER band (empty at both ends: the first driver is 3 pitches
      in), so the LED band runs past them to within half a pitch of each edge.
      With G = 2.0 and the chassis seat's 568.0 clear run: W = 140, P = 15.778, four
      sections + three junctions = 566.0, and LED-to-LED across a junction = 15.78 = P.
    * SETTLED: the mating PIN MAP mirrors. Derived from the two KiCad footprints' pads --
      male pin 1 meets female pin 5, 3 meets 3, 5 meets 1, 2-6, 4-4, 6-2. Generate both
      pinouts from ONE column list (as harness.py does for the trunk), never type them twice.
      Suggested columns: (GND,V5), (SCK,SDI), (GND,V5) -- signals flanked by rails.
    * BLOCKER: G itself is unknown. KiCad's courtyards (header x -1.77..13.09, socket
      x -13.10..1.75) are NOT mating depths, and worked through end to end they say a
      coplanar edge-to-edge mate needs the socket body to overhang its board edge by ~4 mm
      into a 2 mm gap -- i.e. the two parts collide. Either the real insertion depth is
      shorter than the courtyard implies, or these generic horizontal parts are not meant to
      mate each other coplanar. NEEDS the actual drawing for PZ254R-12-6P (C492431) and the
      chosen socket (C56182 / C22373944) before anything is placed.
    * ALTERNATIVE worth pricing if the drawings disappoint: CARD EDGE -- board B's own gold
      fingers into a card-edge socket on board A. One part instead of two, and the mating
      depth is just the socket's slot, so the geometry is knowable without a drawing.
    * PH: fits on EVERY board in the same free driver band (user asked for this if it costs
      no LED spacing) -- its 15.9 body spans +-7.95 against a lip inner edge at +-8.4.
10. Next checkpoint submit after 3-7 land.

## DONE
- Output board analog rewrite from datasheets: PCM1808/PCM5102A/CH334F/G6K/ESD5B5, MCLK pin 39,
  VBAT, mid-rail buffers; 0 unconnected 0 violations, all USB groups pass; fab builds (415264e)
- layout.py: all duplicate-numbered pads get their net (USB-C SH); SMD stitch exceptions honoured
- motor_ctrl VBAT tied to 3V3 (e1e2d26)
- Motor ctrl J4 USB-C -> top-entry XH (+ USB-A->XH lead in BOM), re-routed clean (bd63bb4)
- Output-board tray: rectangle not bbox, -X open, J2 pad moved, 45 deg gussets (75dbea2)
- Cable run-throughs 9 -> 0: trunk conductors on their own pins + per-conductor heights (0ee4419)
- Optical 20 courtyard overlaps: already declared + verified intentional (PDnA/PDnB vs own Dn, optical.py docstring) (item 5)
- lever_sensor CAD size: branner-owned (knee_lever.py); handed to lead for branner (item 6)
- Motor ctrl CAD from routed geom; checker box-centre fix -> output 60/60, mctrl 60/60, optical 156/156 (items 3+4)
- Body widened 2.8 -Y (chassis.RAIL_GAP), notch gone, pigtail 9 + bus B rerouted (a1ad309)
- SUBMITTED eabbc571 (4faab2c..a1ad309)
- Pi cradle = column frame cut by keyhead_endplate._slot_shadow (bbda046); ceilings 6587->2582
- M4 through-board ears (a98762e), motor controller frame cradle + ear screws (f52686c)

## IN THE BACK POCKET
- **O-SHAPED OPTICAL PCB** (user, 2026-09-22): "keep it in your back pocket in case that is
  our only way out". Today the board is a C -- the +Y wrap reaches the main body only
  through the sensing strip on the -X side. Adding a second band on the +X side closes it
  into an O and gives the DIGITAL nets a path that does not cross the analog strip.
  * WHAT IT WOULD FIX: the two +3V3D opens for certain -- that annulus-to-wrap hop has NO
    single-layer path across the strip (searched: no straight lane, and no 3-segment dogleg
    over a 26 x 60 x 26 grid, checking pads AND outline). Probably SAI_SCK too, plus
    whatever the freed strip space recovers.
  * WHAT IT WOULD NOT FIX: U15's analog inputs. Those come from the strip and a +X band sits
    ~32 mm away from them. (Moot if the five-in-the-strip column works -- see below.)
  * WHAT IT COSTS: the opening is not empty. bridge_endplate fills it with 20,268 mm3 at
    z 9.3..16.0, which IS the board's own z band. So this is an endplate redesign, and the
    endplate has to be able to grow back to that +z height without overhangs (user).
  * ⚠ AND IT NO LONGER BUYS ROD RETENTION. The idea of letting the PCB hold the guide rods
    down died with the rod-ring support cap (2026-09-22): PCB_X0 now stops 1.6 mm short of
    the rod holes so their bearing rings can close, so the board never reaches the rods.
    Ring support wins -- an unsupported bore is structural, retention was convenience.
  * PREFER FIRST: all five converters in the strip beside their own quads (committed
    2026-09-22, 8.7 mm runs). If that routes clean the O is not needed at all.

## NEEDS USER
- **THE OPTICAL BOARD HAS NO MOUNTING HOLES, AND PARTS SIT WHERE THEY GO** (found 2026-09-23,
  chasing the user's question about why the CAD holes are square). Both are real and the
  second is why this is not a five-minute fix.
  * opt_pcb() cuts the two M4 clearances with `box_at(M4.shaft_clr_d, M4.shaft_clr_d, ...)`
    -- a SQUARE prism where a drilled hole belongs. Nothing justifies it in the file; it
    reads as "a box was easier to type than a cylinder". It is conservative for clearance
    (it removes more material than a round hole), which is likely why nobody caught it.
  * THE FABRICATED BOARD HAS NO HOLES AT ALL. elec/out has zero Edge.Cuts circles and the
    only drilled features are J1's USB-C pins and shield tabs. mount_points() are 24.4 and
    37.2 mm inside the outline, so they are not notches either -- the gerbers would come
    back with two M4 screws driving into solid FR4.
  * AND THE PLACEMENT DOES NOT KNOW ABOUT THEM. Against a Ø4.40 clearance hole:
    head mount -- Cd11 pad 1 at 0.47 mm and pad 2 at 0.69 mm, both INSIDE it;
    tail mount -- TP1 pad 1 at 2.10 mm, inside it.
    So adding the holes destroys Cd11 and clips TP1. Either those parts move, or the
    mounts do, and both change a placement that took many routes to settle.
  * Worth deciding together with the O-band, since that is the other open placement
    question on this board.

- LED strip 5 V buck ON THE MOTOR BOARD (user asked, 2026-09-22): the circuit is worked out
  (second LMR33630 off the same 24 V, own fuse + EN/UVLO, XH out to pi_cap J4, ~0.5 A more
  on a 24 V bus sized under 5 A) and the REASON is settled -- a separate buck keeps a
  lighting cue from browning out the Pi, and the board sits at the keyhead end, furthest
  from the bridge pickup. IT DOES NOT FIT. Measured on the placed board, the only clear X
  bands are -27.0..-20.3 (6.7 mm) and 21.6..27.0 (5.4 mm); the buck needs ~8.5 for the 6x6
  inductor alone. Growing 46 -> 54 in X was not enough, and +Y is blocked by the mounting
  EAR, which reaches 8.7 into the 10.8 mm gap to the Pi. Options: (a) grow X to ~60 and
  rework the tray/cradle margins, (b) move the ear and grow +Y, (c) put the buck on its own
  small board beside the Pi cap. Reverted for now -- the committed motor_ctrl routes 0/0.
  The pi_cap already has J4 waiting for whatever generates it.

- Optical re-route after grounding the USB-C shell tabs (layout.py: stitch exceptions skip PTH
  pads too): 25 passes -> TIA_OUT_1B open, 28 -> TIA_IN_8A open (freerouting re-plans every
  net). UNCOMMITTED in the tree (layout.py, optical.py passes 28, optical geom). Superseded by
  the photodiode redesign (SFH 2400 FA-Z + per-channel RC), which re-places and re-routes the
  whole sensing row anyway -- fold it into that.
- Optical sourcing (lcsc_check 2026-09-21): VEMD4110X01 photodiode C3211080 = 95 in stock /
  20 per instrument (4.8 builds); S8B-XH-A C157914 = 88 / 21 (4.2 builds); SPX3819 62,
  USB3343 77, K3A26 108 (1/instrument, fine). Stocked alternate PIN photodiode Everlight
  PD15-22C/TR8 (LCSC C131271, 940 nm, 6 pF, 4.2 uA @1mW/cm2) is 3.3 x 2.8 mm -- does NOT fit
  the 1.6 mm optical pitch (0805 geometry); adopting it means re-doing the sensor layout.
  Choice: order VEMD4110X01 elsewhere + consign, or redesign around a bigger PD.
- Output board analog DESIGN choices to confirm: pickup load 1M (tone), coupling corners
  (1.6 Hz pickup, 16 Hz relay path), DAC -6 dB pad; independent datasheet re-check before fab.
- Optical triplet land narrowing (0.20 -> 0.35/0.45 gap): both widths broke the LED supply
  chain (V5_PRE) the router lays past the lands; reverted to stock. Doing it needs the V5_PRE
  chain given its own deliberate route (inner layer) first.
- keyhead height-prism roof over the merged slot for strings 8-10: 18.3 mm bridge at x -609.5
  (pre-existing; the Pi plate used to cover it). Roof takes the inserts' string load; a 45 deg
  gable needs 9.2 mm and the Pi board is 7.8 above. Options: move the Pi +X ~2 mm, or reshape
  the 8-10 slots (owner of nut_block geometry?).

## NEEDS USER — the axle bore's bearing stress is 4.9 MPa, and nobody had computed it
The endplate's creep margin was quoted as 14x. That figure is the BULK section resisting
-X through the block: 1683 N over 2014 mm2 = 0.84 MPa. It answers the wrong question.
The creep-critical number is the LOCAL bearing stress where the shaft presses into its
bore, and that is 1683 N over a projected 343 mm2 (9 fingers x 3.70 + 2 arms x 4.80, times
the 8.0 shaft) = **4.90 MPa**, roughly 6x higher.

It is NOT a regression from the comb work -- the run-outs only removed material above the
axle centre and the load seats at 7:20..7:43, below the equator. It is a number that had
never been taken at the bore.

Whether 4.9 MPa is safe for PCTG over years is not something I can settle from datasheets:
short-term yield is ~45-50 MPa but the sustained-load limit is far lower and vendor creep
curves for PCTG are thin. This wants a COUPON, which this project already does for
material questions.

The geometric levers are nearly exhausted: fingers are 3.70 wide because the bearing takes
5.0 of a 9.5 pitch, and the shaft is 8.0 because the bridge bearing is a 688ZZ. Dropping
the bearing side clearance 0.4 -> 0.25 buys CB_W 4.00 and takes it to ~4.5 MPa. That is
all that is free.

## optical: the last three unconnected items (2026-09-25, 03:30)

State: 3 unconnected, 0 violations, both SI groups pass, CAD and fab data agree.
Board on disk = elec/out/optical.p50.kicad_pcb (elec/out/ is gitignored, so it is NOT in
git -- regenerate with `finish.py elec/out/optical`, which reproduces it).

The three, and they are two connections plus one:
    +3V3A   the LDO's island (U9.5, U11.5, R34.1, C132.1)  ->  the array's island   31.76 mm
    +3V3A   U6.38/39 (the H7's VDDA pair)                  ->  the LDO's island     15.84 mm
    SAI_FS  U6.3                                           ->  the FS spine's end   20.97 mm

⚠ THE ANALOG RAIL HAS NO TRUNK, AND THAT IS THE FINDING. +3V3A comes back as THREE
islands: the LDO with its local caps at y -61, the MCU's two VDDA pins on their own, and
all twenty channels' decoupling at y -34 and north. Nothing carries the rail from its
regulator to its load; the router has been asked to improvise a power distribution
network and has declined three times.

What is NOT the reason:
    room       the west strip is 23 x 30 mm at 4.3% copper on In2 and 4.1% on F.Cu, eight
               capacitors and nothing else. B.Cu is the GND pour and In1 the plane, so
               two layers are free there and nearly empty.
    escape     all three pads have a via site with room over: 0.98, 1.14 and 0.60 mm
               against the 0.45 a 0.6 via needs.
    passes     50 -> 3, 100 -> 3, byte-for-byte the same 2072 segments. Converged.
    a straight lane
               there is none. Widest clear vertical lane over y -61.5..-21.0 is 0.046 mm
               on F.Cu at x -23.75, and NEGATIVE on In2 -- the strip's 4% of copper lies
               ACROSS it. Same on the east side over y -60..-34.5. Any trunk has to dodge.

TWO WAYS, AND THE USER SHOULD PICK:

  A. MOVE THE ANALOG SUPPLY NORTH. U9/U11/R34/R35/C132 sit at y -61 while everything they
     feed is north of -34.5. An analog regulator belongs near its load, and this is the
     same principle that just fixed MID_RAW (25 mm -> 2 mm) and the two LDOs' output caps
     (26.2 mm -> at the pin) -- both of which were in this row for the same reason: the
     packer spreads a row evenly and knows nothing about what serves what.
     Knock-ons: FB1, Q1 (the LED driver) and the USB-C CC resistors share that row, and
     V5_PRE feeds it. Costs a re-route.

  B. DRAW THE TRUNK. A deliberate wide (0.5+) +3V3A run from the regulator to the border,
     dodging as it must, picking up U6.38/39 on the way. Gives the rail a defined
     impedance instead of whatever the router improvises. Costs a generator function and a
     re-route, and pre-laid copper in the south has measured badly twice.

⚠ AND THE RETRY MECHANISM CANNOT HELP, FOR A REASON WORTH FIXING SEPARATELY. layout.py's
retry (and _local_nets) builds an MST over ALL PADS OF THE NET, not over what is actually
unconnected. Handed +3V3A and SAI_FS it laid 65 segments and skipped 13, and the skipped
ones are edges the spines ALREADY carry -- U30.8 -> Cd9.1, U18.23 -> U17.23. It is
island-blind, so on a net that is 95% finished it spends its budget re-laying copper that
exists and adds it as an obstacle in the tightest part of the board. That is why the
four-net retry took 6 unconnected to 9.
    The fix is known and small: retry the ISLAND-TO-ISLAND edges, which check_border.py
    already computes (its islands() + ratlines()). Not done at 03:30 on a shared routine
    every board uses, with a 45-minute verification cycle.

## optical: open a north-south lane on the EAST board edge (user, 2026-09-25) -- TRIED, NO GAIN
The crystal/oscillator column at the board's east edge -- Y1 (OSC_IN/OSC_OUT), the MID
divider, PHY_XI/PHY_XO/PHY_RBIAS and their GND pads -- sits hard against the edge, so the
strip between it and Edge.Cuts carries nothing. Moving that column slightly WEST opens a
full-height routing lane along the east edge, which is exactly the direction the ULPI and
SAI traffic wants to run. The MCU (U6) likely has to move west with it, since the column's
x is set off the MCU's east face.
TRIED 2026-09-25 and it did not pay. Two findings worth keeping:
 * the column is anchored to the ROW BAND's east limit (x1 = TAIL_X1 - EDGE_KEEP), NOT to
   _part_x("U6"). Backing the MCU off its mount 3.0 mm moved the MCU and the lane not at
   all. The user's reading that the MCU would have to move was reasonable and the
   measurement says otherwise.
 * reserving the lane costs BOARD LENGTH, which was capped by the USB-C overmold. Freeing
   that (see PLUG_L) let a 3 mm lane and a 9 mm corridor in, and the result was 5
   unconnected / 0 unexpected -- exactly what the shorter board gives. No gain.
So the lane is available if something else ever makes it worth 2.2 mm of board, but it is
not the lever it looked like.

## optical: hand-place the vias instead of letting the router pick (user, 2026-09-25)
"consider moving automatic via generation to manually specified positions. There are also
short F.Cu runs that connect component pads to vias that you could hard code, although some
F.Cu runs are longer and perhaps make more sense for auto routing. Some of the via
placements to an untrained eye seem suboptimal."
This is the generalisation of elec/optical.py's `_PIN_ESCAPES`, which was written after the
user found the SAME defect three times by eye -- SAI_FS, ULPI_D1 and ULPI_D6 were each
disconnected AND had no escape via. The router spends the good positions on whichever net
it reaches first and never goes back to make room, so the pin that loses the race is
stranded on F.Cu in a field that is full on both sides.
Plan: extend _PIN_ESCAPES to every fine-pitch pin that needs a layer change -- the MCU's
west and south flanks and the whole PHY -- with each site SCANNED against the unrouted
board (the helper in _escapes' note), and let the router keep only the long runs between
escape vias. Declared copper is NOT clearance-checked when laid, so every site must be
measured, never chosen by eye.

## optical: the +3V3A In2-crossing via is in the SAI diagonal (user, 2026-09-25)
"This +3V3A via looks like a bottle neck, could it move slightly west?" It is the link via
at x 17.20 from _v3a_vias() -- the converter-spine end of the In2 crossing -- and it sits
where SAI_SCK/SD1/SD2/SD4 run diagonally. Moving it west needs the crossing's declared
track endpoint to move with it, and the lane west must be measured empty first.

## LED strip: interboard connectors are inconsistent, and the Pi lead is unmodelled
(user, 2026-09-25) The lead has NOT taken the LED work because the interboard connectors
do not make sense as drawn. Two things:
 1. BOARD-TO-BOARD, NO WIRE. The strips should mate to each other directly -- a plug on
    one board entering a socket on the next -- rather than through a flying lead. Pick a
    pair whose mated length matches the gap the strips already sit at, so the joint is the
    spacing rather than something the spacing has to accommodate.
 2. THE PI LEAD IS NOT MODELLED. One connector leaves the chain for the Pi and there is no
    cable in the assembly for it, so nothing checks where it runs or what it collides with.
    Model it like the other harnesses (src/wiring.py) so the route is real geometry.
Resubmit once both are right so the lead can take the LED work.

## LED strip: connector bodies fouled the slot tab (2026-09-25, RESOLVED)
After the board-to-board joint went in, every section overlaps the chassis in a thin band
at y 52.05..53.65, z -40.28..-39.23 -- 0.3..1.9 mm in FRONT of the board face and about
3 mm up from the slot floor (LED_BOARD_BOT -43.23). The patches sit at the -X end of each
section, i.e. at J1, so the 4.3 mm socket body is the suspect; led_strip_0's overlap runs
the board's WHOLE length, which is a different feature and may pre-date the connector work.
RESOLVED: it was (b), and it was mine. The bottom SLOT_TAB (4.0) is blank laminate that
sits DOWN IN the chassis groove, so nothing may be fitted below y -8.0 -- and centring the
12.1 mm connector body on _YO put it at -9.05, 1.05 into the groove. The row is placed
against the TAB now, not the board, and the LED sections measure 0.00 mm3 against the
chassis. STILL OPEN from this item: the 4.3 mm connector heights are ESTIMATES and the
LCSC codes are unverified, so nothing may be ordered; and the parts are THROUGH-HOLE while
the board's back sits on the rail wall, so the tails still need a relief.

## optical: the USB cable clipped the endplate (2026-09-25, RESOLVED)
94.2 mm3, optical_cable_usb <-> bridge_endplate, at y -126.78..-125.30 -- the 1.5 mm band
of endplate just +Y of the conduit mouth. NOT caused by shrinking the conduit: it is the
BOARD GROWING. CONDUIT_Y1 = PCB_YM - 2.0, so lengthening the board (188.53 -> 190.73 for
the 9 mm corridor + 3 mm east lane) walked the conduit mouth south with it and left
material between the board's edge and the shaft, which the cable's horizontal run crosses.
RESOLVED by that measurement. Both configurations give 5 unconnected / 0 unexpected --
identical -- so the 2.2 mm bought nothing and the corridor, the east lane and the 14.0 mm
cable requirement all reverted together. Collision 0.00 mm3, board back to 188.53, and no
constraint on which USB-C cable the owner may use.


## LED strip: 2.00 mm was unsourceable, joint is 2.54 now (2026-09-25)
The 2.00 mm right-angle FEMALE is stocked (LCSC lists several 1x6, e.g. HX PM2.0-1x6P WC,
C22465680, 602 in stock, gold, 4.3 mm insulation height). The matching right-angle MALE is
NOT -- LCSC answers "No exact matches". A joint needs both halves, so the pitch moved to
2.54 where both are stocked everywhere. The row still fits: 16.33 mm of courtyard in the
20.0 mm of board above the slot tab, gap 3.0, engagement 5.84 measured.
STILL TO DO before the lead takes it:
 * pick and verify actual LCSC codes for the 2.54 right-angle header AND socket, then run
   elec/lcsc_check.py. Nothing may be ordered until that passes.
 * confirm the 5.0 mm HEIGHT estimates in board_geom off those parts' drawings. They must
   be EQUAL for the two halves or the contact axes do not line up and the joint does not
   close -- the boards are coplanar, so there is no slack to absorb a difference.

## optical: SAI_FS needs its spine to leave the SCK stub's lane (2026-09-26)
SAI_FS is the one net that has failed EVERY routing of this board, in every configuration.
Its escape via at U6.3 is placed correctly; the gap is the ~22 mm from that via to the
spine's open end at (12.65, -18.89), which the router will not make.
MEASURED, with a layer-aware checker:
 * a clear F.Cu lane exists at y -20.0..-21.25 running from x 12.65 west to x -2.0, which
   would bring the handover within ~7.5 mm of the MCU escape.
 * the DESCENT into it is blocked on F.Cu by SAI_SCK's per-cell stub (the SCK SPINE is
   B.Cu, but its stubs are F.Cu and run parallel to the FS spine 0.5 mm away).
 * the same diagonal is CLEAR on both B.Cu and In2.Cu -- so a layer hop works, except that
   no via fits anywhere along the FS spine: SAI_SCK's stub shadows all of it at 0.50.
So the fix is to separate the two spines' F.Cu lanes (_FS_SPINE / _SCK_SPINE and the
_*_JOG offsets in elec/optical.py) far enough for a via to land on the FS spine, then
declare via -> B.Cu diagonal -> via into the y -20.6 lane. Every leg above is already
verified against the unrouted board; only the via site is missing.
