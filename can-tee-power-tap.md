# CAN tee: continuous power trunk, one tap per tee (bronner, 2026-09-30)

**Status: DECIDED BY BRONNER AS THE WORKING ASSUMPTION, NOT YET CONFIRMED BY THE USER, NOT
BUILT.** The user asked (2026-09-30) to explore "dual two pin connectors on each motor T,
two for power and ground, two for data" out of worry about the motor line's power budget.
This is the version of that idea the numbers support. Nothing below is in the model yet
except the tee's 2 mm trunk copper (`6346db5`), which is right either way.

## ⚠ CORRECTED BY THE USER, 2026-10-01: 2 + 2, NOT 2 + 4

> "I was saying 2 pin for CAN data not the 4 pin, so it would be 2 + 2 not 2 + 4"

So the CAN pair is a continuous trunk with a tap at each tee too, exactly like power, and
the tee carries **two 2-way taps and the drop**. Everything below that says "4-way XH CAN
in/out" is superseded by this section; the power reasoning is unchanged.

    power trunk   one continuous pair, a tap crimped at each tee      J3  2-way JST VH
    CAN trunk     one continuous pair, a tap crimped at each tee      J1  2-way JST XH
    drop          to the motor's own 6-pin plug, unchanged            J2  4-way JST XH

**Better for CAN than what it replaces:** the bus becomes one unbroken pair with a ~60 mm
stub per node instead of passing through two contacts and a board at every tee. The 120 Ω
terminator and its switch stay on the board; only the end tee has its switch ON.

**The two taps are different families on purpose, and it is not optional for power.** A tap
on a continuous wire is two conductors in one crimp. An XH contact takes AWG 30–22
(0.05–0.33 mm² — from memory of JST's XH sheet, not re-read today), so it holds two AWG 26
(0.26 mm²): fine for CAN, far too thin for a power trunk. Two AWG 22 need the VH contact.
So power is VH and CAN is XH, which also means neither lead fits the other's socket.

**Scratch prototype, 2 + 2 (same throw-away method as below):** 0 unconnected, 0 violations,
first pass. The row is VH −18.97..−10.03, XH 2-way −9.25..−0.75, drop 4.95..18.44: **31.7 of
40 mm**, with 5.7 mm free between the CAN tap and the drop. The VH overhang in Y is the same
3.9 mm; working assumption is to KEEP the board 16 deep (the outline and the panel quote do
not move) and let the header overhang.

## Why

Today the trunk's 24 V passes THROUGH every tee: one XH contact in, board copper, one XH
contact out, ten times. The contact is 3 A. The far end is fed through the motor board,
whose J3→J1 path is ~91 mΩ on a 0.5 mm inner track (BOM.md, dual-feed section), so the
"dual feed" splits about 64 / 36 and puts the west share on copper rated under 1 A.

Splitting power and data onto two XH connectors changes none of that: it is still one XH
contact per rail per direction, and three 4-way XH in a row is 40.47 mm on a 40 mm board.

## What

    power trunk   ONE continuous pair, panel J7 -> tee 9 .. tee 0, a tap crimped at each tee
    tee           J3  2-way JST VH, side entry   power tap (this motor's current only)
                  J1  4-way JST XH, side entry   CAN in (H, L) + CAN out (H, L)
                  J2  4-way JST XH, side entry   drop to the motor (GND, 24V, H, L) -- unchanged
    motor board   fed by panel J10 -> J3 as now; J1 carries CAN only (its 24 V way unused)

Trunk current never crosses a contact or a board. Each tap carries one motor. The motor
board leaves the motor power path, so its J3→J1 copper stops mattering. The dual feed and
its balance arithmetic go away: a continuous pair fed from one end drops ~70 mV at ten
motors moving.

Power and CAN are different families, so a power lead cannot be plugged into a CAN socket
(BOM.md "two incompatible pinouts share one 4-way XH housing" -- closed for the tees).

## Verified (JST eVH.pdf, read 2026-09-30)

| | |
|---|---|
| current | 10 A per contact (AWG 16, standard header) |
| contact resistance | 10 mΩ max initial |
| wire range | SVH-21T-P1.1: AWG 22–18 (0.33–0.83 mm²); SVH-41T-P1.1: AWG 20–16 (0.5–1.25 mm²) |
| two wires in one crimp | 2 × AWG 22 = 0.66 mm² fits either contact; 2 × AWG 20 = 1.04 mm² fits the 41T. JST does not publish a double-crimp rating -- common practice, pull-test the first ones |
| S2P-VH (side entry) | 7.86 wide, 8.5 tall over the board, 10.9 deep; housing VHR-2N 7.86 × 10.5 section |
| row on the tee | 7.86 + 2 × 13.49 (courtyards) ≈ 36–37 mm on a 40 mm board |

## Height: it fits, measured

The old limit came from string 10's tee under the pickup piece at its neck-most position.
Measured on the placed model: tee connector tops are at z −19.7 (XH, 7.0 over the board);
the pickup piece's shallow run and the height plate bottom are at z −13.4. That is 6.3 mm
of air today. A VH header at 8.5 leaves 4.8; a mated housing at up to 10.5 leaves 2.8.

## Stock: all three halves, read from JLCPCB's parts catalogue 2026-09-30

| part | LCSC | stock | price |
|---|---|--:|--:|
| S2P-VH(LF)(SN), side-entry header, JST | C160355 | 6,950 | $0.1259 @50 |
| VHR-2N-BK, housing, JST | C595405 | 30,543 | $0.0402 @100 |
| SVH-41T-P1.1, contact AWG 20–16, JST | C160350 | 98,611 | $0.0293 @1000 |
| SVH-21T-P1.1, contact AWG 22–18, JST | C160349 | 265,205 | $0.0223 @1000 |

All "extended" library. KiCad footprint: `Connector_JST:JST_VH_S2P-VH_1x02_P3.96mm_Horizontal`.
LCSC's own search endpoint refuses automated requests; JLCPCB's catalogue API answers.

⚠ **HOLD (lead, 2026-09-30): this stays a document until the user confirms it.** No board
re-route and no CAD change on it. The outline is intended to stay 49.5 × 16 with its ear, so
the JLCPCB panel quote does not move; `tools/lcsc_prices.py` prices housings and crimps for
XH/PH/SH only and needs the VH pair added (lead's, once this is confirmed).

## Scratch prototype: it fits in X and routes; the VH body overhangs in Y (2026-09-30)

A throw-away copy of the board (`can_tee_vh`, never tracked, never in the CAD; the script is
kept in the session scratchpad only) with J3 = S2P-VH at x −14.5, J1 = 4-way XH at −2.5 and
J2 unchanged at 11.7, power on the same 2 mm bars:

| | |
|---|---|
| route | **0 unconnected, 0 violations**, first pass |
| connector row | courtyards span x −18.97 .. 18.44 = **37.41 of the 40 mm** layout region; 0.78 and 0.70 between them, 1.03 and 1.56 to the ends |
| VH in Y | its courtyard runs y −11.94 .. 4.55 with the pad row at 2.0, and the board's −Y edge is at −8.0: **the VH header's envelope stands 3.9 mm past the edge**, out over the motor. XH stops at −7.75, inside it |

So the estimate held in X. In Y there are two honest options, and it is an outline question
for the lead's panel quote either way:

* **leave the board 16 deep** and let the VH body overhang — it is carried by its two posts
  and ~7 mm of body on the laminate, with the motor's top face 2.4 mm below; or
* **grow the board −Y to ~20** so the header sits wholly on it. That laps the motor 13.6
  instead of 9.6 and changes `D.TEE_BOARD_Y`, the cradle and the JLCPCB outline.

## Not verified / open

1. ~~LCSC stock~~ done, above.
2. The mated height of VHR-2N lying on a side-entry header (8.5 or 10.5): either clears.
3. The output panel's J7 is 2 × XH contacts per rail = 6 A; ten motors at the derived
   0.8 A is 8 A. J7 becomes the limit, so it wants VH too or a firmware cap of 7 movers.
4. The 0.8 A per moving motor is still derived, not measured.

## Work, in order

1. `elec/can_tee.py`: J1 8-way → 4-way CAN, add J3 VH tap, keep the 2 mm rails from J3 to J2.
2. `src/electronics.py` `tee_pcb` and `src/wiring.py`: the tee is hand-modelled and the trunk
   is built per conductor through `tee_pin`; power becomes its own pair with taps.
3. `elec/harness.py`: a CAN-only trunk pinout; the bus-A lead from the motor board drops 24 V.
4. BOM: VH parts in, 8-way XH out; delete the dual-feed leg table.

## 2026-10-01 — the 2 + 2 tee was built, and the VH tap DOES NOT FIT (measured)

The user corrected the tap to 2 + 2 (2-way VH power + 2-way XH CAN + the 4-way drop). It was
built in full — netlist, 2 mm bars, CAD, per-conductor wiring — and routes `0 unconnected,
0 violation(s)`, no FAIL. It is NOT committed: the work is in `git stash` on `agent/bronner`
("2+2 tee with S2P-VH power tap"). The tree is back on the merged 8-way tee.

**Item 2 above ("8.5 or 10.5: either clears") was wrong.** Read off the JST assembly drawing
for the stopper-type side header (S2P-VH, the stocked one):

| | value |
|---|---|
| mated housing, pin row → its rear | 19 mm (I had modelled 13.4) |
| housing thickness incl. the latch | 10.5 mm, and it rides ~0.5 mm above the board → **~11.05 mm above the board top** (scaled off the drawing, ±0.3) |
| housing body without the latch | ~9.1 mm above the board top |

Headroom above the board top, measured on the built instrument per tee (`scratchpad/head.py`):

| what is overhead | headroom | tees |
|---|---|---|
| fret LED board (`fret_pcb_key` / `fret_pcb_mid`) | 10.5 | 0–7 |
| `ui_clamp` | 10.8 | 8, 9 |
| top-plate rib at y −38.7..−35.5 (`top_plate_color_3`) | 9.7 | 5, 6, 7 |
| `fret_strip_key_py` | 8.9 | 0 |
| fret M4 (`fret_m4_mid`) | 8.3 | 5 |
| chassis, immediately −X of every board | 0.3 | all — a −X-facing header is impossible |

So 11.05 mm needs more than any tee has. Sliding the header in Y does not rescue it either:
tee 5 needs the pin row > 2.4 mm toward +Y to get its latch off the rib, tee 6 needs < 0.6.
The overlap gate caught two of these (tee 5 × fret M4, tee 6 × top plate) even with the
too-small plug; with the true envelope it is all ten.

**What still fits:** the XH side header (7.0 mm) — which is what the merged tee uses.

**Options, for the user:**
1. Stay on the merged tee: 8-way XH trunk (paralleled contacts), 2 mm copper, dual feed.
2. 2 + 2 with the power tap on XH as well — only if the trunk wire can be AWG 22 (XH's
   largest), which 8 A all-moving does not allow on one run. Not recommended.
3. A lower ≥ 5 A crimp family for the tap (Molex Micro-Fit RA is the candidate; its mated
   height and stock are NOT verified, and it cannot take a double crimp, so the trunk would
   pass through board copper: power in + power out + CAN = 2 + 2 + 2).
4. XT30PW right-angle (stocked, ~5 mm high) — but its cable half is solder-cup, against the
   solder-only-on-PCBs rule.
5. Buy headroom: ≥ 1 mm more between the motor tops and the fret board / rib (brenner's and
   the deck's geometry, not bronner's).

Also found on the way: the CAD's R1/JP1 box sat 2.5 mm off the routed position in the 2 + 2
layout (the `!! MIRRORED` report from `cad_geom_check`); fixed inside the stash only.

### Option 3 checked (2026-10-01): Micro-Fit fits in height, but buys almost nothing

Read off the CJT C3030 (Micro-Fit 3.0 compatible) drawings; Molex's own site timed out.

| | value |
|---|---|
| right-angle 2-way header (Molex 43650-0200, C192562, 3,576 in stock, $0.58) | 9.65 wide, ~4.6–5.6 high, 9.8 deep |
| receptacle (43645-0200, C114089, 54,993) | body 5.26 thick, 14.0 long; mated ≈ 7 mm above the board (estimate) — under the 8.3 mm worst headroom |
| crimp (43030-0001, C259786) | **AWG 20–24 only** — no double crimp, so the trunk must cross board copper: power in + power out |
| current | ~7 A per contact at AWG 20 (Molex's 8.5 A figure is the family maximum) |
| row | 2 × 9.65 + XH 2-way 7.4 + XH 4-way 12.4 = **39.1 mm of a 40 mm row** — no gaps, does not place |

So it clears the fret board but (a) does not fit the row without growing the tee in X, and
(b) rates ~7 A against the merged tee's 6 A (two paralleled XH contacts per rail), with the
same two contact pairs in series per tee. Not worth a new connector family and crimp tool.

**Standing recommendation: stay on the merged tee.** With the dual feed each end carries at
most half of the 8 A all-moving case (4 A through 6 A of contact), and the thing that
actually unbalances it is the motor board's J3 → J1 pass-through (~91 mΩ on 0.5 mm track) —
fix THAT, which is in bronner's lane, rather than change the tee.

## Option 6 (2026-10-01): all-XH — power owns the 8-way, CAN taps on a 6-way drop. ROUTES.

The thing the user is worried about is real and still there on the merged tee: the trunk's
+24 V crosses each tee on ONE 3 A XH contact in and one out, and with the dual feed at
54 / 46 all ten motors moving puts **4.4 A** through the east-most one (so today the honest
limit is ~5.5 A total, about six motors slewing at once). VH would have fixed it and does
not fit. This does, with the connector family that already clears the deck (7.0 mm):

| | merged tee | option 6 |
|---|---|---|
| J1, 8-way XH | trunk: GND 24 H L in, same out | **power only**: GND 24 24 GND in, same out — the instrument's standard 4-way power order, as on J7 / J10 / motor J3 |
| J2 | 4-way drop | **6-way** (S6B-XH-A, C157919, 22,452 in stock, $0.17; XHP-6 C144405, 22,775): 1–4 the motor drop, 5–6 a CAN tap |
| trunk +24 V per tee | 1 contact, 3 A | **2 contacts, 6 A** — against 4.4 A worst case |
| CAN trunk | through 2 contacts per tee, 20 in series | **continuous pair**, one double-crimped tap per tee (2 × AWG 26 = 0.26 mm², inside SXH-001T's 0.33) — nothing in series |
| board | 40 × 16 layout + ear | **42 × 16** layout + ear: the row is 22.4 + 1.0 + 17.4 = 40.8 of body |

Scratch prototype (`scratchpad/can_tee_p6.py`, not in the tree): 2 mm bars to all nine
power lands, **0 unconnected, 0 violations, audit passes**.

**What it costs, and what is NOT yet checked:**
1. **+2 mm of board in X.** It has to go +X, into the notch under the ear: −X has only
   1.65 mm before the neighbouring motor (the note in `elec/can_tee.py`). The next tee's
   board is 4.7 mm past today's edge, so 2.7 mm would remain — room for a 1.6 mm locating
   wall with ~0.5 each side, but the cradle (`wiring.tee_cradles`) and `D.TEE_BOARD_X`
   have to be re-cut and re-gated. Not done.
2. The fabbed outline stays 49.5 × 16 overall (the ear already reaches there), so the
   lead's panel quote does not change; the L just gets a shallower notch.
3. A second SKU of cable: the power trunk becomes its own 4-wire run (2 × 24 V, 2 × GND),
   and CAN a separate twisted pair with taps. Harness, `wiring.py` and BOM follow.
4. The far limit moves to the cables' own contacts at the panel (J7 / J10: 2 contacts per
   rail, 6 A) — matched, no longer exceeded.

**Recommendation changes: option 6 over staying put.** It is the only option that fits
under the fret board AND removes the 3 A contact from the trunk. Needs the user's go-ahead
because it changes the tee's outline, pinout and both trunk cables.

### Option 6 re-checked, and 6b (2026-10-01, later): take CAN off the tee altogether

**Option 6 has a problem I had not checked: the retaining screw.** Growing the row to
40.8 mm of body puts the 6-way's corner at x +21.6, and the M4 button head (Ø7.6, centred
at +24.75, +3.65 in the ear) reaches +20.95: the head lands 0.57 mm INTO the connector
body. Moving the hole +0.7 / +0.5 in the ear buys 0.05 mm. Option 6 is not clean as drawn.

**6b: the tee becomes a pure power board, in the outline it already has.**

| | merged tee | 6b |
|---|---|---|
| J1, 8-way XH (unchanged part, unchanged position) | GND 24 H L in / out | **power only**: GND 24 24 GND in / out — 2 contacts per rail, 6 A |
| J2 | 4-way drop | **2-way** power drop (S2B-XH-A, C157931, 41,564 in stock), same centre |
| R1 / JP1 terminator | on the board | gone from the board (see below) |
| CAN | through 2 contacts per tee | **never touches the tee**: one continuous twisted pair, double-crimped (2 × AWG 26) into H and L of each MOTOR's own plug |
| board | 40 × 16 + ear | **identical outline, seat, ear and screw** — the row shrinks to 30.8 mm |

Scratch prototype (`scratchpad/can_tee_p6b.py`): **0 unconnected, 0 violations, zero DRC
warnings, audit passes.** Two nets; the board could be single-sided.

It is the user's "two for power, two for data" with the data pair's tap sitting in the
motor's plug instead of on the tee — which is where the trunk pair ends up anyway.

**Open before it can be built:**
1. **Bus-A termination.** The far-end 120 R has no board to live on. Either the SERVO42D's
   own termination (I believe the MKS board has a selectable 120 R — NOT verified against
   its manual), or a leaded 120 R crimped across H / L in the last motor's plug, which is
   solder-free and uses the same double-crimp. Verify before committing.
2. The motor plug's H / L contacts take 2 × AWG 26 = 0.26 mm² (SXH-001T: 0.08–0.33) — in
   range; the insulation crimp on two wires wants a test crimp.
3. Harness, `wiring.py` (power trunk as its own 4-wire run, CAN pair motor-to-motor) and
   BOM follow; the motor-bay seat and the cradle do NOT change.

**Recommendation: 6b.** Same 6 A trunk as option 6, no outline change, no new header SKU
beyond a 2-way, and it removes 20 series contacts from the CAN bus.

### 6b open item 1 CLOSED (2026-10-01): the motor terminates the bus itself

Read off Makerbase's own schematic (`MKS SERVO42D_CAN V1.0_003 Schematic.pdf`, repo
makerbase-motor/MKS-SERVO42D-57D, Hardware/): the TJA1051T/3's CANH / CANL carry **R13,
120 Ω, in series with SW1, a 2-pin header** ("排针2P"). Fit a jumper cap on SW1 of the
LAST motor and bus A's far end is terminated on the motor's own board — no resistor in a
crimp, no terminator on the tee. (An ESDA6V1L sits across the pair on every motor.)

So the tee's R1 / JP1 were duplicating something every motor already carries. The same
header on the other nine motors must be left OPEN; that is an INSTALL_NOTES line when 6b
is built. The near end stays where it is, on the motor controller.

Remaining before build: the 2 × AWG 26 test crimp. Nothing else is open.

### 6b: two costs I had not counted (2026-10-01, on reading the harness model)

Before touching the real board I read how the drop is actually made, and 6b is NOT the
board-only change the section above makes it sound like:

1. **The drop is the SERVO42D's FACTORY pigtail** (`motor_pigtail_N`; BOM: "over their
   native XH pigtails — power AND CAN"). Its contacts are already crimped, so the CAN pair
   cannot be double-crimped into it. 6b means REPLACING the pigtail with a made-up cable:
   XHP-6 at the motor, two power wires to an XHP-2 on the tee, and the trunk pair
   double-crimped into its H and L. Ten more cables to make, and the factory part unused.
2. **The CAN trunk moves, and other agents designed against where it is.** `fret_light.py`
   and `ui_panel.py` (brenner's) both take `wire_canl`'s height over the motor bank
   (top −17.15) as their cable floor. A motor-to-motor CAN pair runs at the motors' backs
   instead — probably lower and better for them, but it is their clearance to re-derive,
   not mine to move under them.

Neither kills it. Both make it a harness decision across three agents rather than a tee
respin, so it is NOT started. What stands on its own, whatever is chosen:

* the merged tee's limit is one 3 A contact per rail, ~5.5 A total with the 54 / 46 feed;
* a tee whose 8-way is power-only (6 A) routes clean in today's outline;
* the last motor can terminate the bus itself (R13 / SW1).

**The cheapest thing that fixes the limit with NO harness change at all is firmware:** cap
simultaneous slewing at six motors (5.5 A / 0.8 A, rounded down), or measure the real
per-motor current first — the 0.8 A is still derived, not measured, and if a real move
draws 0.5 A the merged tee already covers all ten.

## The budget the instrument already has (2026-10-01) — and what it does to this question

I had been sizing against "all ten motors moving, 8 A". That case does not exist:

| limit | value | source |
|---|---|---|
| PSU | **6.67 A** (Mean Well GST160A24-R7B desktop adapter, 160 W; was LRS-150-24, 6.5 A, until 2026-10-01) — for the WHOLE instrument, not just the motors | BOM `psu_24v_160w` |
| the design budget for the motor bus | **< 5 A, fleet slew staggered** | BOM, 24 V bus row and its notes |
| the merged tee's trunk contact, with the 54 / 46 dual feed | 3 A / 0.54 = **5.5 A** total | this doc + BOM dual-feed section |

So the tee's single 3 A contact is NOT below the budget: at the budgeted 5 A the worst
contact (east-most tee) carries **2.7 A of its 3 A**, and the supply itself gives out at
6.5 A before a 6 A trunk would matter. The 8 A figure was ten motors × the derived 0.8 A —
more than the PSU can deliver.

What that leaves, honestly:
* **The merged tee meets the documented budget, with 10 % margin on the worst contact**
  — and only because the dual feed and the motor board's 2 mm bar are both in (before the
  bar it was 64 / 36: 3.2 A at 5 A, over).
* The budget itself is a FIRMWARE promise ("staggered"). Nothing in hardware enforces it,
  and 0.8 A per moving motor is still unmeasured. The cap that keeps the worst contact at
  3 A is 5.5 A, i.e. six motors at 0.8 A.
* A power-only 8-way (6b) would raise the trunk to 6 A — more than the PSU's share for the
  motors — so it buys margin, not capability. Not worth ten made-up cables on its own.

**Recommendation, settled unless the user wants the margin:** keep the merged tee; write
the stagger cap into the motor controller firmware as a hard limit (≤ 5 A commanded, six
movers at the derived figure) and measure one motor's real slew current at bring-up
(`docs/board-bringup-diagnostics.md`), which is the number every line above leans on.

## 2026-10-01, later — the motor has two connectors, and the tee still stands

Makerbase's schematic and the user's video agree: the SERVO42D takes power on a 6-way screw
terminal and CAN on a 5-way one on the opposite edge. There is no factory pigtail. That
removes the objection that sank 6b ("it replaces the factory pigtail") -- and does not
revive it, because the user has since chosen the supply: 160 W, ~4.6 A for the motors,
inside the merged tee's 5.5 A. The pigtail becomes a made part (four ferruled wires into the
two blocks, one XHP-4 at the tee) and the tee, the trunk and the pinout are unchanged.
What the finding DOES cost is in the motor bay, not the harness: `docs/servo42d-fit.md`.
