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

### (d) Refinement from the router's own reports -- `place_refine.py`

The router says where nets fought and which parts stand there. Each round proposes moves
for those parts only -- shift along the free axis, rotate within `rot`, swap a decap to the
pin's other side, mirror a pin-symmetric part to undo a twist -- scores them (c), keeps
the best robust improvement, and stops when a round gains nothing. Every move respects the
hard constraints, so the result is always a legal intent-satisfying placement. Bounded:
rounds x candidates fixed up front, never an open-ended sweep.

**Proof:** from (b)'s output_panel, refinement closes the gap to (or passes) the hand
placement's score, in minutes.

## Rules carried over

* Keep every run to minutes; no hour-plus sweeps (ROUTER.md, route-time notes).
* The router is the judge; no new proxy scores unless validated against routes.
* The output is `placements` + provenance (`elec/<board>.place.json`: which constraint set
  each coordinate), so a later hand edit is a `pin`, not a fork.
* layout.py stays the single legality gate.
