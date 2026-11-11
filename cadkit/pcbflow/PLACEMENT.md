# Placement from intent (design, 2026-11-10)

Fresh boards are coming: an instrument revision will re-lay several boards, with many
placement decisions made from scratch. Today a board's placement is a dict of hand-typed
coordinates in its generator, each with a paragraph of reasoning, and the only feedback is
a full finish. This file is the plan for placing a board from **intent** -- what has to be
where, and why -- in minutes, with the router itself as the judge.

Nothing here replaces the existing chain. The output of every step below is the same
`notes["placements"]` dict that layout.py already consumes, so a placed board goes through
layout's gates, the router, close_last and verify exactly as a hand-placed one does, and
any part can still be pinned by hand.

## Writing intent for a new board (start here)

One command runs a board end to end:

    py -3.12 place_flow.py <dir> <intent.json> [--no-auto] [--soft-forbid] [--skip-finish]

`<dir>` holds `<stem>.net`, `<stem>.board.json` (the notes: outline, cutouts, slots, pairs,
layers, `post_route_refs`) and `<stem>.parts.json` (`place_geom.py` on any laid-out copy of
the board). Set PCBFLOW_FOOTPRINT_DIRS / PCBFLOW_PROJECT as for layout.py.

The stages:
1. The intent. Unless `--no-auto`, auto_decaps, auto_singles and auto_floorplan are added
   for any set the file does not already carry.
2. place_init, then place_cells.
3. layout.py, as the legality gate. A refusal stops the run.
4. score.py --intent, then finish.py (router + finish chain), then quality.py --brief.
5. `flow/report.md` and `report.json`: the route score; FLOOR and FORBID lines; finish
   unconnected / violations; quality FAIL / OPEN; and provenance, i.e. for every ref the
   rule or stage that set it (`flow/provenance.json`).

`--skip-finish` stops after the score.

**The intent file** is a JSON list of rules (vocabulary in place_intent.py's docstring), each
with a `why` and a `src`. Write it from a small generator script, so it can derive positions
from the CAD. Two worked examples are in `examples/`: `intent_output_panel.py` and
`intent_optical.py`. Each reads `<stem>.parts.json` and `<stem>.board.json` beside itself
and writes the intent JSON there. The optical one takes `AUTO_FLOOR=1` (auto_floorplan
instead of hand regions) and `CELLS=1` (buck and PHY as free cells), which is the
combination the proofs ran. Write it in this order:

1. **What the instrument fixes: `fixed` / `panel` / `hole` / `keepout` / `mate` /
   `access`.** Optical fixes its emitters, photodiodes and ballast resistors to the string
   fan, J1 and J2 to the -Y face, and the converter anchors to the comb geometry (op ~578,
   ~2387, ~2100). output_panel's connectors are `panel` rules: the mouth is at the
   endplate face, `at` sets the position along the edge. A fresh board is mostly these.
2. **The designed cells: `group`.** A cell laid out around its pins (a TIA, a converter, a
   buck, a PHY) is the design; one rule per instance, members as offsets in the anchor's
   frame.
   * On a fixed anchor (optical's string and converter cells) the cell is pinned.
   * On a free anchor (optical's buck U13 and PHY U7) place_init places it whole and
     place_cells picks its turn by routing.
   * Do not dissolve a cell into free parts: the legaliser scatters them.
3. **The floorplan: `region` + `in_region`, BEFORE anything electrical.**
   * Every free part in the board's section (optical: `compute`, south of the sensing
     strip).
   * **Reserve the power corner by the inlet as its own region, holding the buck cell or
     buck parts.**
   * ⚠ LESSON (optical, 2026-11-11): with only auto_floorplan's zones, the buck lost its
     inlet corner to the MID divider and analog LDO. Each was placed for its own nets
     first, and when the PHY turn forced a zone repair, the only spot clear of every zone
     was beside the USB chain: 3 soft breaches, rules met, a worse board. Zones say what
     to keep APART; only a region says where something GOES. On output_panel, the
     `power24` region holding U5, L1, D6, Q2, J7, U16 and D10 is the same rule.
4. **The electrical rules the defaults do not know:**
   * `tight` for loops a datasheet wants small (the buck's SW/BOOT 10 mm and FB 6 mm, a
     crystal's legs 6 mm, a reference divider).
   * `near` for parts that belong at a part or pin (an ESD clamp at its connector, CC
     resistors at their CC pins, a PHY near its socket). On an IC, `near` is a spring that
     stiffens until it holds.
   * `decap` where auto_decaps' pin choice is wrong (optical's C130 at U10's VBUS pin).
   * `current` for power nets, which sets the widths.
   * Declared `diff_pairs` with a `chain` in the notes: a pass-through part in a chain is
     turned to face it.
5. **The defaults, through place_flow:**
   * auto_decaps: a decap at each IC supply pin.
   * auto_singles: test pads at their driver pin.
   * auto_floorplan: switch nodes 10 mm off sensitive parts (hard, `forbid`); USB/relay
     edges off analog parts (soft).
   * Review what they propose (`place_intent.py <stem> <intent>` prints every rule's slack
     on any placement). Pass `skip`, or your own regexes, where a default is wrong.
6. **No `rot` rules, unless a rotation is a mechanical fact** (a panel connector). Turns
   are pin-facing decisions that place_init, `_pair_turns` and place_cells make better than
   a typed angle. The hand board's angles went stale every time a neighbour moved.

**Proof (2026-11-11).** Both boards were run through `place_flow.py` with the inputs of
the step-by-step runs. The route scores match exactly:
* output_panel (`--no-auto`, op_intent_floor): 0 open, 0 pairs, 0.0 mm, 278 vias,
  2205.2 mm, floor 5. Same as vF3.
* optical (cells intent): 0 open, 0 pairs, 0.0 mm, 197 vias, 2354.9 mm, floor 3. Same as
  the hard-forbid place_cells run.

finish.py and quality.py had not been run on these placements before. The stripped hand
boards went through the same finish chain for the baseline:

| finish + quality | unconnected | violations | quality FAIL / OPEN |
|---|---|---|---|
| optical hand, stripped | 20 | 78 | 22 / 6 |
| optical auto (flow) | 22 | 61 | 9 / 6 |
| output_panel hand, stripped | 1 | 7 | 11 / 5 |
| output_panel auto (flow) | 1 | 6 | 6 / 5 |

Neither stripped board finishes clean, hand or auto:
* Optical's DRC is mostly its post-route machinery. The Rs*/Cs* SHDNZ parts and TP6-12 are
  placed after routing at sites searched against one hand route (PLACEMENT.md (p)
  survey), plus the 5 SHDNZ post_route_nets.
* 20 of the "violations" are the declared emitter/photodiode courtyard overlaps.
* The shipped boards close with hand repair copper, which equal terms strips.

So a fresh board's post-route parts need the same treatment as its placement: sites chosen
against the route that exists, not carried from another one. That is the next gap before
the re-layout.

**Reading the report:**
* `open` / `pairs` first.
* `floor` and `FORBID` next. A FORBID NOT MET means the floorplan does not fit as written:
  move a fixed part, shrink the zone, or give the cell room. `--strict` on place_init and
  the default in place_cells refuse it.
* Then finish and quality.
* The provenance count says how much of the board the rules decided (`fixed by rule`,
  `group (cell)`, `decap at pin`, `near its target`) and how much the net graph did.

## What exists, and what it taught

* **Generators** (`elec/<board>.py`) write `BOARD_NOTES["placements"] = {ref: (x, y, rot)}`
  in the board frame (centre origin, +Y up, mm), plus outline, cutouts, declared copper.
  output_panel's placement block is several hundred lines, most of it the WHY: panel
  overhangs, connector fronts measured off F.Fab, an ear for an M4 head, three noise
  bands. That reasoning is the intent; the numbers are derived from it by hand.
* **optical already places from the CAD** (`src/optical_pickup.py`): coordinates are
  envelope centres, and layout anchors them by courtyard (`_anchor_on_courtyard`). So
  "the mechanical model decides where a part goes" already works, for one board.
* **layout.py** applies placements (pad-centroid or courtyard anchor), takes
  `PCBFLOW_NUDGE` moves, and refuses courtyard overlaps and declared-copper crowding.
  It is the legality gate; nothing here duplicates it.
* **geom.json** (`cadkit/board_geom.py`) is the read-back: the routed board drawn in the
  CAD, so the housing is cut to the real parts. Fresh boards need the other direction as
  well: the CAD's panel, walls and outline driving the placement.
* **Scoring** (`router/score.py`, `placescore.py`): the route itself, minutes per board.
  ROUTER.md records why: every cheaper proxy (escape max-flow, RUDY, global-plan overflow,
  wirelength, crossings) failed to rank placements. And `placescore`'s note: one route is
  one sample -- the score is not smooth in the placement (C112 by 0.3-0.7 mm flipped
  optical between clean and faulted), so a candidate is read against its neighbours.
* **The router reports where nets fought** (`congestion.hotspots`, ownroute's "most
  contested space ... beside X, Y" and "a placement twist (turn a part, or swap a pin
  order)"). That is the refinement signal.

## The four pieces, landed in order (each its own cadkit hash, each proved on a known-good board)

### (a) Intent vocabulary -- `place_intent.py`

A board declares `BOARD_NOTES["place"]`: a list of constraints, plus a `mech` block the
CAD side can produce. HARD constraints must hold (a placement that breaks one is illegal);
SOFT ones carry a weight and are what placement optimises.

**Mechanical (from the CAD -- fresh boards are mostly driven by these):**

| constraint | meaning |
|---|---|
| `outline(poly, cutouts)` | Edge.Cuts; already in notes, may come from the CAD |
| `hole(xy, d, keepout_mm)` | mounting hole + the head's keep-out (parts and copper) |
| `keepout(poly, what, layers)` | deck walls, standoffs, ribs, cable runs: no parts / no tall parts / no copper |
| `height(poly, max_mm, side)` | max part height under a lid, a deck, a string |
| `panel(ref, edge, at, face_x, anchor="body_front", overhang)` | a connector whose MOUTH is fixed by the panel or enclosure: position along the edge, how far the body front stands past it. Replaces the hand `_FRONT` arithmetic: the front is measured off the footprint, as board_geom does |
| `fixed(ref, xy, rot, anchor)` | anything the CAD pins (pads / courtyard / body anchor) |
| `mate(ref, dir, length, clear)` | the plug / cable INSERTION STROKE as a swept keep-out (THT and JST plugs collide along the stroke, not where they sit); `dir` in board axes or the part's own (`L+X`), or `up` for a top-entry plug |
| `access(ref or xy, side, tool_d)` | reached after assembly: test pads, buttons, a USB mouth, the 2.5 mm hex key to a mounting screw |

The `mech` block is plain data (polygons in the board frame), so a CAD module can export
it -- `src/<part>.py` already knows the panel face, the walls and the hole -- and the board
generator reads it instead of re-typing the numbers. Same rule as geom.json in the other
direction: one source, read, never copied.

**Electrical / floorplan:**

| constraint | meaning |
|---|---|
| `region(name, poly)` + `in_region(refs, name)` | floorplan bands (analog / digital / 24 V) |
| `apart(group_a, group_b, min_mm)` | noise separation (switch node vs preamp) |
| `thermal(ref, others, apart_mm)` | regulators and drivers off the sensors (MA730, photodiodes) and off each other |
| `decap(cap, ic.pin, max_mm=1.5)` | a capacitor at its pin, on the pin's side, smallest first |
| `near(ref, ref_or_pin, max_mm)` | pull-ups, crystals, ESD at the connector |
| `chain(refs)` | a pair's path order (U31 -> U10 -> J1): the parts are placed to lay it straight |
| `rot(ref, allowed)` / `side(ref, F|B)` | orientation freedom and face |
| `array(refs, axis, pitch)` | one rule for a repeat: optical's photodiodes, per-string cells, LED rows (refs may be a regex) |
| `pin(ref)` | the hand placement is kept as is |

Parts named nowhere are free. Every constraint keeps a `why` and a `src` -- the datasheet
section, user ruling or memory, or CAD part it comes from ("hand" when it has none) -- so a
re-layout can tell which rules still hold when the thing they came from changes.

**LANDED (2026-11-10):** `place_geom.py` (KiCad Python: each part's local pads with
number and net, courtyard, F.Fab box, in the placements' own frame and anchor -- every pad
round-trips to 0.00003 mm on output_panel) and `place_intent.py` (plain Python: the rules
above, a checker reporting each rule's slack in mm, `auto_decaps` proposing a decap /
bulk-near rule for every capacitor across a supply, `--selftest`). Proof: output_panel R2's
hand placement as 261 rules (mechanical, bands, thermal, auto decaps, pair chains):
**0 hard rules broken**; 14 soft ones report the hand board's real decap distances
(3-7 mm where the rule asks 3; C57 and C28 sit by a connector, not an IC -- the auto rule
is a proposal a board overrides). Checked in 0.7 s.

**Proof:** output_panel R2's hand placement expressed as intent; a checker reports every
hand coordinate's slack against its constraints (all hard ones satisfied, which proves the
vocabulary can say what the board needs).

### (b) Initial placement -- `place_init.py`

From intent + netlist to a legal placement, constructively, in seconds:
1. Mechanical and `panel`/`fixed` parts go where they must.
2. Free large parts (ICs, modules) by quadratic (force-directed) placement on the net
   graph inside their regions: two-pin nets pull hard, wide nets weakly, `chain` and diff
   pairs strongest; `apart` as a repulsion between groups.
3. Legalise: courtyard overlaps removed by the smallest moves (tetris on a 0.05 grid),
   rotations snapped to `rot`, keep-outs and height zones respected.
4. Satellites last: each `decap`/`near` part to the best free spot within its radius,
   preferring the pin's escape side (the router's escape map), the cap's GND end toward
   the nearest pour stitch.
5. layout.py's own gates run on the result; anything refused is reported against the
   constraint that put it there.

**LANDED (2026-11-10):** `place_init.py <stem> <intent.json>` -> `<stem>.init.json`
(placements) + `.init.why.json` (which rule or stage set each coordinate). Quadratic
placement on the net graph (nets over 12 pins left to the planes, diff pairs x4, chain hops
sprung), rotation by pad pull within `rot`, then an FFT occupancy-grid legaliser (0.1 mm,
biggest first, region-confined, satellites straight after their IC). Every placed part
keeps an ESCAPE HALO later parts may not enter: 0.25 mm for passives, 0.15 mm per pin on a
side for an IC (1.0-2.5 mm). Without it, U1's pull-ups walled its pins and SWDIO /
JACK_MODE / I2C2_SCL failed. 1.6 s on output_panel; panel parts land on the hand
coordinates to 0.05 mm.

Proof, output_panel, same router, held copper (hand tracks, vias, frozen nets, and the
stitch exceptions that existed for them) stripped from both:

| placement | open | pair faults | uncoupled | contention | vias | route |
|---|---|---|---|---|---|---|
| hand R2 WITH its held copper | 0 | 0 | 6.2 | 4525 | 234 | 165 s |
| hand R2, stripped | 3 (+3V3, CC1, ROLE_VDET) | 1 (THRU_DP) | 60.8 | 9176 | 253 | 929 s |
| intent only (88 rules), stripped | 1 (SWDIO) | 1 (THRU_DP) | 2.5 | 8265 | 345 | 680 s |

These are single routes, so each figure is one sample. The intent placement is level with
the hand placement once the held copper is gone; the remaining gap to the shipped board is
that copper, which (p) is for. More vias (345 vs 253): the intent board spreads parts
wider, so more nets change layer. Two fixes came out of this proof:
* the paste-window bug in `repair_search._pads` (see (p));
* auto_decaps targets: only an IC's first, smallest cap gets 3 mm (weight 1); further caps
  get 5 mm (weight 0.5). The hand board went from 14 soft breaks to 9.

**SWDIO, the last open (2026-11-11): two bugs, neither in the router.** SWDIO (U1.48 to
TP1) could not route even alone on an empty board.
* layout's GND stitch for U1.49 had taken an L across the outer ends of pins 48 and 47.
  On a 0.4 mm QFN that is a signal pin's only exit.
* It took the L because K1's pad sat 1.5 mm from U1's courtyard, inside U1's 2.5 mm
  escape halo. The legaliser placed K1 (bigger) first, and a halo only kept out parts
  placed after its owner.

Fixes:
* place_init: the gap between two parts is now the larger of their halos, whichever goes
  first (two occupancy grids: grown courtyards checked against plain masks, plain
  courtyards against grown masks).
* layout: a fine-pitch part's GND stitch tries every hop that stays off its neighbours'
  exit lanes before one that crosses, and names any pad that had to cross.

Result on the same router, held copper stripped: **0 open, 0.0 mm uncoupled**, 328 vias,
303 s. The one fault left is THRU_DP, which is parked. The stripped hand placement on the
same router: 3 open.

`auto_singles`: a `near` rule tying a single-net part to its driver pin. By default it
covers test pads only, at 8 mm and weight 0.5 (lead ruling 2026-11-11). Two-pad parts
whose other end is ground are opt-in (`two_pad=True`). Applied flat to those at 5 mm, it
put 26 more satellites against U1's pins and routed 4 open against 1. A pull-up's place is
a judgement about escapes that a flat rule does not make.

**Check at re-layout: stitches that cross an exit lane.** On the 0-open intent board, three
fine-pitch GND pads could reach a via only by crossing a neighbouring signal pin's exit
lane: **U5.6** (LMR33630 VQFN-HR 0.5 mm), **U13.10** and **U13.11** (X2QFN-12, 0.4 mm). The
board routes, so the crossings stranded nobody here. On a re-layout, layout names them
again ("stitch: N fine-pitch pad(s) could only reach a via across a neighbour's exit
lane"). Either widen those parts' neighbourhoods, or check that the signal pins beside
them still route.

**Proof:** re-place output_panel from intent alone (mechanical + floorplan; no hand
coordinates except the panel), route it, and compare `score.py` with the hand placement.
The target is not "beats the engineer" on the first try -- it is a legal board the router
closes, within reach of the hand score, from a description a fraction of the length.

### (p) Power and ground without hand copper -- router-native distribution

**Why it is its own step (2026-11-10, (b)'s first proof).** output_panel's hand placement
routes 0 open WITH its held copper (67 vias, 212 tracks) and 2 open WITHOUT it: +24V and
GND -- exactly the two the intent placement also fails. The held copper is power
distribution typed by hand (17 +24V tracks, 10 vias; GND, PWR_GND and V5_PRE stubs), and a
fresh board has none. Without this step, every re-laid board needs hand copper again,
however good the placement, so it ranks with (c)/(d).

What the router must do itself, from intent:
* **Power nets as power:** route nets with a `net_widths` entry first, wide, short and
  low-via (no snaking through signal channels), before the negotiation fills the board --
  and say which pads a rail could not reach and what stood in the way.
* **Pours from intent:** a `pour(net, layer, region)` rule (the 24 V island, a local
  3V3 pour under an IC) the router treats as copper to join, not a hand zone.
* **Ground reach:** every GND pad reaches the plane by a stitch via or the pour, checked as
  a connection and reported against the part that blocks it (layout's stitch gate already
  says which pads lack a via spot; the router has to close the ones it can).

**Proof:** output_panel's hand placement with the held copper stripped routes +24V and
GND closed; then the intent placement does too.

**First finding (2026-11-10): both opens were bugs and stale hand data, not missing
features.**
* **+24V:** paste windows were read as copper. A footprint's net-less F.Paste-only pads (on
  the TO-252 tab and the QFN belly) were parsed with "no .Cu layer = every layer", which put
  foreign copper inside the land. No cell of Q2's tab was legal for a 0.5 track, so the
  rail could not leave it on an empty board. Fixed in `repair_search._pads`: a pad with no
  copper layer and no drill is dropped.
* **GND:** U4.25 (the hub's belly) was a hand `stitch_exception`, made because the held
  DN2 pair ran under it. With the held copper gone, the exception left the belly with no
  via, and it is walled in by its own 0.5-pitch pins. Without the stale exceptions, layout
  stitches all 15 pads, and GND closes on the stripped hand board and on the intent board.

Lesson for fresh boards: stitch exceptions belong to the copper that made them needed, so
they go wherever that copper goes.

**Where the intent board's extra vias came from (2026-11-11).** The 0-open intent board had
328 vias against the hand board's 253; both had their held copper stripped. Counted net by
net, the excess was not on the power nets.
* It was on short local nets that the hand board routes with no via at all. The worst
  were the buck's SW node at 44 mm (hand 9), FB at 34 mm (3.4) and DAC_R_FILT at 52 mm
  (3.6).
* Total wirelength was the same as the hand board's. A few parts had simply been dropped
  across the board: the legaliser places greedily, and nothing pulled them back.

Fixes, in place_init:
* **Local pass.** Each part is lifted and dropped at the free spot nearest its nets'
  optimum, each allowed turn tried on its own. It is kept only if its nets plus RULE_W x
  its soft-rule breaches get cheaper.
* **Group moves.** An anchor moves with its decap/near satellites, which are re-seated at
  their pins.
* **No circular pull.** An anchor's target ignores its own satellites. L1's V5_PRE target
  had been its own caps, so it never moved toward U5.
* **New rule kind `tight(nets, max_mm, weight)`** for a loop the datasheet wants small: a
  buck's SW/BOOT, its FB, a crystal's legs. It is weighted in both stages and checked.

Results on the same router (single routes):

| intent placement | open | vias | routed mm | route |
|---|---|---|---|---|
| before the local pass | 0 | 328 | 2594 | 303 s |
| local pass, first turn that fits | 0 | 280 | 2258 | 122 s |
| local pass, cheapest turn | 2 (FLASH_RX, POT_SCK at U1) | 262 | 2131 | 340 s |
| hand R2, stripped (+3V3 open) | 3 | 253 | 2484 | 603 s |

On equal terms the 280 is level with the hand board's 253. The hand board leaves +3V3
open, and +3V3 alone takes 27 vias and 189 mm on the intent board.

**Power is a width; a pour only where a layer is spare (measured 2026-11-11, lead
ruling).** +3V3 on the same 0-open placement, one route each:

| +3V3 as | open | pair faults | vias (+3V3's) | signal mm on In2 |
|---|---|---|---|---|
| signal tree | 0 | 1 | 280 (27) | 668 |
| pour on In2 over the digital band | 0 | 3 | 318 (51) | 216 |
| 0.4 mm tree | 0 | 0 | 271 (30) | 648 |

On a 4-layer board whose In2 is the only inner signal layer, the pour costs a via per pin
and pushes the escapes off In2. The rules:
* A power net gets a width, from a `current(net, amps)` rule in the intent:
  `place_intent.widths(rules)` gives {net: mm} (IPC-2221 outer curve, 10 C rise, 1 oz,
  rounded up to 0.05, at least 0.2), which the generator writes into `net_widths`.
  Examples: 1 A is 0.35 mm, 1.5 A 0.55, 3 A 1.4.
* A pour (a zone with net, layer and poly) is for a region whose layer has nothing else to
  carry there, like optical's +3V3D on B.Cu under U6.

Against the hand board's 253: the 0.4 mm tree is 271 with +3V3 routed, and 241 without it.

**Held copper on paste-window lands, every board (survey 2026-11-10, main 622e87e).** These
are lands with F.Paste-only windows, which the router could not start a path from before
e8f7d95, that also carry held copper or an exception. No board is edited: each one is held
as it is until it is re-laid, and the re-layout tests whether (p) makes its copper
unnecessary.

| board | land | held copper | reason the generator gives | (p) should make it unnecessary? |
|---|---|---|---|---|
| output_panel | Q2.2 (TO-252 tab, +24V) | 8 vias, 2 tracks (+24V; 11 tracks / 9 vias on the net) | none specific | **yes** -- proved: +24V closes on the stripped board |
| output_panel | U4.25 (hub belly) | 1 GND via + `stitch_exception` | held DN2 pair under the hub | **yes** -- goes with the held DN2 copper |
| optical | U14-U18.25, U7.33 (QFN bellies) | 3 GND tracks each (AVSS pin 4, ADDR pins 15/16 into the EP) | TI: AVSS straight to the pad; "the F.Cu pour cannot enter" | **test** -- the router could not start in these EPs either; the short pin-to-EP join is still the design intent, so the question is only whether it can be laid by the router |
| led_strip | U1-U3.21 (HTSSOP EP) | GND and +5V tracks at the land | -- | **test** |
| motor_ctrl | U4.69 (QFN68 belly) | 2 GND tracks | -- | **test** |
| lever_sensor | U3.29 (MCU belly) | 1 GND track, pin 1 VSS into the land | an escape-pocket fix for SDA | **test** |
| lever_sensor | U4.17 (MA730 belly) | `stitch_exception` + a GND track to pin 8 | quality A14: a via would drink the paste on the pad that sets the magnet gap | **no** -- deliberate, keep |
| foot_led_a/_b, fret_led_key/_mid | every VQFN-24 belly (13 parts) | 4 GND vias each | (thermal array) | **no** -- thermal design, not routing | Still open: power routed as power (widths first, few
vias), and pours from intent.

### (c) A score fast enough to iterate -- router-alone, region-limited

`score.py` is minutes per board; refinement needs tens of candidates. Two levers:
* **Region-limited re-route:** a candidate that moves a few parts re-routes only the nets
  touching them (plus whatever the negotiation drags in), the rest held from the parent's
  route (the keep_paths machinery the plane re-join already uses). Checked against full
  routes on the series: same ranking, a fraction of the time.
* **Robustness:** a candidate is believed only with its neighbours (small jitters), as
  placescore already does. Scored in parallel, a process each.
Budget: one candidate under a minute, one refinement round under ten.

**LANDED (2026-11-11): `router/rescore.py`, `score.py --save auto` / `--parent <route.pkl>`.**
A full route saves itself by net: paths, necks, piece keys, pair faults, the negotiation's
history and its closing price. A candidate keeps every net whose pieces are cell-for-cell
the parent's and whose parent copper still clears the candidate's fixed copper. A plane net
keeps the joins of its unchanged pieces (keep_paths). The rest is routed, starting from the
parent's history at its closing price (capped at 50), and the finish stages look only at
nets that changed. Two rules came from measurement:
* **Warm start.** Started cold (no history, pf 0.5), one resistor moved 0.6 mm on
  output_panel dragged 42 nets back in and ended 9 open against the full route's 1. Warm,
  2-6 nets move and the result matches the parent.
* **Lock only pairs the parent could not finish.** Leaving THRU free cost 140 s of a 210 s
  re-score, re-finishing the same fault. Locking every kept pair left optical u10e/c05 2
  open where the full route closes, because its clean ULPI pairs could not make way.

**Proof, the placement series (10 families, 99 nudged candidates against each family's
first):**
* Clean-or-not agrees with the full route on **99/99**.
* Total time **x4.4** less: median 7 s, p90 49 s, max 65 s, against 40-140 s full.
* output_panel's intent board (a 430-520 s full route): three nudges re-scored in 20-65 s.

What it does NOT do: it does not reproduce the full route's spread in uncoupled mm. A kept
pair keeps its parent copper, so a nudge away from the pair leaves the figure exactly as it
was. The full-route spread there (1.4-3.2 mm on u10a for nudges nowhere near the pair) is
route-to-route noise, which placescore already warned about. A move that does touch a pair
changes its pieces, or makes its copper illegal, and is re-routed and re-finished. So (d)
reads the re-score as "what this change does", and confirms its accepted moves with a full
route.

### (d) Refinement from the router's own reports -- `place_refine.py`

The router says where nets fought and which parts stand there. Each round proposes moves
for those parts only -- shift along the free axis, rotate within `rot`, swap a decap to the
pin's other side, mirror a pin-symmetric part to undo a twist -- scores them (c), keeps
the best robust improvement, and stops when a round gains nothing. Every move respects the
hard constraints, so the result is always a legal intent-satisfying placement. Bounded:
rounds x candidates fixed up front, never an open-ended sweep.

**Proof:** from (b)'s output_panel, refinement closes the gap to (or passes) the hand
placement's score, in minutes.

**EXPERIMENTAL (2026-11-11, lead ruling): `place_refine.py`**: it works as a driver but gained nothing in four runs. No more investment unless a board shows a use for it.
* Each round reads the parent's failed nets, faulted pairs and hotspots, and names parts
  in that order: small parts on failed nets, then on faulted pairs, then beside hotspots.
* Moves: a "pull" (place_init's legaliser drops the part at the free spot nearest the far
  end of its failed net), 0.5 / 1.0 mm steps, and turns within `rot`.
* Moves that break a hard rule or meet a courtyard are dropped. The rest are laid out and
  re-scored (c) 4 at a time. The best is confirmed by a full route before it becomes the
  next parent.
* First runs, on the board before the SWDIO fix: no move fixed SWDIO, because its blocker
  was in layout. The one move that won on re-score (R17 -0.5: pair faults 0) lost its
  full-route confirm (3 faults, 12.8 mm uncoupled). The confirm rule earned its keep.
* Moves that touch the THRU pair's parts (D2/D3) re-score at ~220 s, because the pair is
  re-finished. Next: re-run from the 0-open board, aiming at THRU_DP once it is unparked.

* Fourth run (vT3: 2 open, FLASH_RX and POT_SCK; 262 vias), with push moves added (the
  legaliser drops a part 1.5 / 3 mm away from the nearest failed pin): 11 parts named,
  98 legal moves, 8 re-scored, none beat the parent. The failed set shifted (POT_SDI in,
  FLASH_RX out), so that corner is at capacity, and moving single passives cannot relieve
  it. What did close it was place_init (vN below: 0 open). **Lesson: fix the placer, not
  the placement.**

### Generality: optical, the whole pipeline (2026-11-11)

The lead's test: if the system only works on output_panel, we need to know before the
re-layout. Optical R1 has noise bands, the photodiode array and the U10 clamp.

**Equal terms.** The hand placement and the auto placement were stripped the same way:
tracks, vias, repair tracks/vias, escape_runs, pin_escapes and via_keepouts all removed. Two
things were kept on BOTH, because they belong to the design, not to one route: the ADC and
PHY stitch_exceptions (layout refuses either board without them), and `local_nets`. The
post_route_refs sit at their hand sites on both (layout skips them). The R1 netlist
(elec/out/optical.net) matches R1's board.json; the kept .kicad_pcb is R2 and has 12 more
parts.

**Intent** (scratchpad `op2/opt_intent.py`, 147 rules):
* Fixed: what the instrument fixes (the D/PD/R sensing column, J1, J2, and the converter
  anchors, whose positions come from the comb geometry).
* Rigid groups (new kind `group`): the 10 string cells and the 5 converter cells, each on
  its anchor.
* Free: all **86 compute-section parts**, with no hand xy and no rot rules.

| optical R1, stripped | open | pairs | uncoupled | vias | length | soft rules broken | floor |
|---|---|---|---|---|---|---|---|
| hand | 0 | 0 | 0 | 223 | 2745 | 17 | 0 |
| vI: first auto | 0 | 0 | 9.6 | 222 | 2379 | 15 | - |
| vI2: decaps inside the halo | **10** | 0 | 5.9 | 176 | 1816 | 8 | 6 |
| vI3: + hand-written floorplan regions | 0 | 0 | 4.4 | 210 | 2347 | 8 | 4 |
| **vI8: auto_floorplan + stiffened near + zones kept** | **0** | **0** | 3.2 | **208** | **2339** | 4 | **0** |

The same code on output_panel (op_intent_free + auto_floorplan), both stripped:

| output_panel R2, stripped | open | pairs | uncoupled | vias | length | floor |
|---|---|---|---|---|---|---|
| hand (shipped) | 3 | - | - | 253 | - | 10 |
| vT3 (before today's fixes) | 2 | 1 | 3.0 | 262 | 2131 | - |
| vN: fixes, no auto_floorplan | 0 | 0 | 1.8 | 265 | 2157 | 7 (L1 0.67 mm from Y1) |
| vF: every auto rule a forbid zone | **8** | 0 | 4.7 | 205 | 1778 | - |
| **vF3: switch zones forbid, edges soft** | **0** | **0** | **0** | 278 | 2205 | 5 (edge rules) |

5. **A zone is not for trading.** The local pass moved L1 28 mm and accepted a 9.3 mm
   breach of the crystal's zone, because it cost 93 in the penalty against 2100 of other
   soft-rule gains. Local moves and satellite re-seats now keep forbid zones (`fz` in
   `_local`).
6. **A part listed twice in a group was unstamped twice** (C130 had two decap rules). That
   left a negative grid count, and R33 was dropped into U10's courtyard; layout refused the
   board. Groups are now deduplicated, and place() raises if the grid ever goes negative.

Bugs it found in place_init, all fixed:
1. **An IC with a `near` rule was a satellite** (U7 near J1). Its own decaps were never
   seated, because seating ran only for parts in the drop order (C121 ended up 26 mm from
   U7.6). Now `near` on a part with more than IC_PADS pads is a quadratic spring, and
   seating recurses (a satellite's satellites follow it).
2. **The escape halo kept the decap ring out.** U6 (LQFP-176) has a 2.5 mm halo, which
   pushed C117 24 mm from its pin. A decap may now stand inside its own anchor's halo, down
   to HALO_SMALL (`_drop_sat`).
3. **Quadratic clumping.** The buck landed beside the PHY and 1.2 mm from the MID divider
   that feeds all twenty TIAs. That board routed BETTER than the hand one, and a clumped
   PHY was also what failed vI2. Fixed with `auto_floorplan` (below), which `_drop` now
   honours as a forbid zone (`_apart_forbid`, falling back if there is no room).
4. **A fixed `near` weight is a guess.** U7's spring to J1 (weight 2) lost to twelve ULPI
   springs, leaving U7 20 mm from J1 and the USB pair 4.4 mm uncoupled. A `near` spring
   whose rule is still broken after the solve is now tripled and re-solved, up to 3
   rounds. U7 and U13 needed x18.

**Free-anchor cells (2026-11-11, lead request for the re-layout).** A `group` whose anchor
is not fixed becomes one COMPOSITE part for every stage of place_init (`place()` wraps
`_place()`):
* Its pads are the anchor's plus each member's, numbered "M/num" and carried in the
  anchor's frame. Its courtyard is the union of the members' (`crtyd_multi`). Its halo is
  the anchor's own (`n_own`).
* Rules that name a member are rewritten: a member pin target becomes "A.M/num", a member
  in a list becomes A, and a member's own decap/near rule is dropped (the cell already
  seats it).
* The quadratic stage, the turn stage, the legaliser and the local pass all move the cell
  as one rigid part. Members are expanded from the anchor's pose at the end.
* A board with no free cells places byte-identically (output_panel checked).
* Optical, with the buck cell (U13 + 10) and the PHY cell (U7 + 13) free (vI9):

| | open | pairs | uncoupled | vias | length | floor |
|---|---|---|---|---|---|---|
| vI9 | 0 | 0 | 4.9 | 202 | 2342 | 2 (buck 7.3 mm from the PHY crystal; rule 10) |

  The PHY cell came out identical to the hand cell. The buck cell turned 90 degrees into a
  column beside the inlet, as one unit.

**An unmet forbid zone is not a soft breach (lead, 2026-11-11).** After the local pass,
place_init re-checks every `forbid` rule and repairs what breaks:
* It lifts the breaking part (either side, free parts only) with its satellites and drops
  it inside its zone near its target.
* If that fails, it lifts the six nearest free parts too, retries, then re-drops them.
* Anything that does not land reverts.
* What is left is logged as `FORBID NOT MET: <part> <distance> -- <why>` and summarised on
  stderr. `--strict` exits 3.
* Composite cells are now judged by their hull in the checker. That alone cleared optical
  vI9's buck-to-PHY-crystal breach: the local pass now sees the whole cell, and init10 has
  0 floor breaches.
* Tested with an impossible zone (U13 60 mm from J2, which its region keeps it beside):
  NOT MET, exit 3. Optical (auto) and output_panel place byte-identically.
* The lift-the-neighbours path has not yet fired on a real board.

**A pair's pass-through parts face the chain (2026-11-11).** The USB pair's uncoupled length
on the auto optical boards (3-5 mm, against 0 on the hand board) was not the router's
fault.
* On the hand placement, layout's coupled-pair layer lays U7 -> U10 -> J1 before routing.
  On the auto placements it said "no clear path U7->U10" and left the run to the router.
* The cause: U10, a pass-through clamp carrying DP and DM on both ends, was turned across
  the chain. The turn stage scores pads against their nets' centroids, and a pass-through
  scores the same in every rotation.
* Probe (scratchpad `op2/probe_unc.py`): 2.4 of vI8's 3.2 mm were at U10's J1 end, where the
  rails leave pads stacked along the hop.
* Fix, `_pair_turns`: the mid-chain parts with two pads on each pair net are turned to
  minimise each hop's facing-pad distance, plus 20 mm for crossed rails, plus 3 mm x |cos|
  per end whose DP-DM baseline is not square to the hop. The in-hop and out-hop use
  different pads. All declared pairs are decided together.
* The turn is decided again after the drop, on the real positions (stage 4b). A satellite
  does not land at its quadratic target: U10 cost 70 at its first turn there and 21 at 90.
* Chain ENDS are not turned. Turning output_panel's hub U4 and U14 by this cost took its
  uncoupled from 0 to 15.2 mm.

| optical, stripped | open | uncoupled | vias | length | note |
|---|---|---|---|---|---|
| auto intent (vI8 -> vI13) | 0 -> 0 | 3.2 -> **1.15** | 208 -> 199 | 2339 -> 2319 | U10 turned 90, as on the hand board |
| cells intent (vI10 -> vI16) | 0 -> **2** | 4.0 -> **0.0** | 198 -> 202 | 2302 -> 2341 | layout lays the pair coupled; ULPI_D5/D6 open |

output_panel places byte-identically: it has no pass-through parts.
OPEN: on the cells board the pre-laid pair costs two ULPI nets. The PHY cell landed at 270
from the turn stage, which made the layout pair possible, and the ULPI fan then had no way
out past it.

**`place_cells.py`: a cell's turn is chosen by routing it (2026-11-11, lead ruling).**
* For each free-anchor cell, the other three quarter turns are tried. Each turned cell is
  dropped whole at the free spot nearest the anchor, laid out, and re-scored against the
  parent route with `--intent`.
* The best by place_refine's key must also beat the parent in a full route before it is
  kept. It then becomes the next cell's parent.
* Bounded at 3 candidates + 1 confirm per cell.
* Without free cells it writes the placements unchanged: output_panel is byte-identical to
  vF3.

Optical cells board (vI16: 2 open, ULPI_D5/D6; USB pair 0.0 mm):

| step | open | uncoupled | vias | length | forbid breaks |
|---|---|---|---|---|---|
| parent (U13 0, U7 270) | 2 | 0.0 | 202 | 2341 | 0 |
| U13 -> 90 (confirmed) | 2 | 0.0 | 196 | 2319 | 0 |
| **U7 -> 90 (confirmed)** | **0** | **0.0** | **194** | **2299** | **2**: the buck's switch node 9.2 / 9.4 mm from the PHY crystal Y2, zone 10 |
| U7 -> 90 + forbid repair (**default**, confirmed) | **0** | **0.0** | 197 | 2355 | **0** (3 soft: the buck 5.5-7.5 mm from the USB chain, rule 9) |

**A forbid zone is hard (lead ruling, 2026-11-11).** A turn that breaks more zones than its
parent gets ONE repair:
* The unit breaking the zone (a free cell or free part, never the cell being turned) is
  re-dropped, aimed at its own `near` targets.
* It must clear EVERY zone it is in, not only the broken one: the first try fixed the
  crystal zone and broke the buck's 45 mm photodiode zone.
* The soft `apart` rules are tried as zones first. They are dropped only if that leaves no
  room.
* The repaired candidate is re-scored and confirmed by a full route like any other.
* A turn the repair cannot clear is not eligible, logged as FORBID.
* `--soft-forbid` keeps the best route as-is (the row above with 2 forbid breaks).

On this board the repair found no room by the inlet: the MID divider and analog LDO hold
the -X side. With the soft zones it found no room at all, so it fell back to the forbid
zones alone. The buck now sits clear of every hard zone but 5.5-7.5 mm from the USB chain.
The rules are met; a better floorplan would give the buck its inlet corner.

Note: rescore said **0 open for all three buck turns**, and the full route of U13_90 said 2
(the same ULPI pair). A re-score near the parent's failed nets is optimistic; the
full-route confirm is what caught it.

**auto_floorplan(parts)** (place_intent, alongside auto_decaps; lead request). These are
default noise `apart` rules derived from the netlist:
* Switch nodes are found from an inductor on a small non-supply net shared with an IC pin.
  They stay 10 mm from every sensitive part and 9 mm from the USB parts.
* USB and relay edges stay 6 mm from the analog sensitive parts.
* Sensitive parts are: photodiodes; ICs on reference, MID, ADC/amplifier-input or pickup
  nets; two-pin parts whose nets are all of those; crystals and their load caps. An MCU
  that drives a crystal is not sensitive.
* The regexes, distances and `skip` are all arguments.
* Only switch node vs sensitive carries `"forbid": true` (the legaliser keeps that zone
  clear). The edge rules are soft. With every rule a zone, output_panel routed 8 open (vF).
* Check: the hand optical breaks 0 of them, so the defaults agree with a known-good noise
  floorplan.
* The shipped output_panel breaks 10. After dropping pairs where both parts are fixed by
  the CAD: L1 is 2.5 mm from the MCU crystal Y1, the buck U5 is 5 mm from the hub crystal
  Y2, and K1 is 2 mm from J8 (the pickup header). Reported only; the shipped board is left
  alone.

**`score.py --intent <rules.json> [--parts]`** prints the floorplan breaches beside the
route: `floor` (a count) and `floor_breaches` (the worst ten) in the JSON, plus a FLOOR
line on stderr. They are never folded into `key`. A placement that routes well but is
electrically wrong can no longer pass quietly.

## Rules carried over

* Keep every run to minutes; no hour-plus sweeps (ROUTER.md, route-time notes).
* The router is the judge; no new proxy scores unless validated against routes.
* The output is `placements` + provenance (`elec/<board>.place.json`: which constraint set
  each coordinate), so a later hand edit is a `pin`, not a fork.
* layout.py stays the single legality gate.
