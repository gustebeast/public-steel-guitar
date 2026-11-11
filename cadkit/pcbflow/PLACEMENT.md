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

The `mech` block is plain data (polygons in the board frame), so a CAD module can export
it -- `src/<part>.py` already knows the panel face, the walls and the hole -- and the board
generator reads it instead of re-typing the numbers. Same rule as geom.json in the other
direction: one source, read, never copied.

**Electrical / floorplan:**

| constraint | meaning |
|---|---|
| `region(name, poly)` + `in_region(refs, name)` | floorplan bands (analog / digital / 24 V) |
| `apart(group_a, group_b, min_mm)` | noise separation (switch node vs preamp) |
| `decap(cap, ic.pin, max_mm=1.5)` | a capacitor at its pin, on the pin's side, smallest first |
| `near(ref, ref_or_pin, max_mm)` | pull-ups, crystals, ESD at the connector |
| `chain(refs)` | a pair's path order (U31 -> U10 -> J1): the parts are placed to lay it straight |
| `rot(ref, allowed)` / `side(ref, F|B)` | orientation freedom and face |
| `row(refs, axis, pitch)` | LED rows, header banks |
| `pin(ref)` | the hand placement is kept as is |

Parts named nowhere are free. Every constraint keeps a `why` string, so the reasoning that
lives in comments today lives next to the rule it explains.

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

**Proof:** re-place output_panel from intent alone (mechanical + floorplan; no hand
coordinates except the panel), route it, and compare `score.py` with the hand placement.
The target is not "beats the engineer" on the first try -- it is a legal board the router
closes, within reach of the hand score, from a description a fraction of the length.

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
