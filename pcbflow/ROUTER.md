# pcbflow's own router

Started 2026-11-08. Replaces freerouting in `finish.py` (layout -> **route** -> unwick ->
repair_planes -> DRC -> close_last); the default since 2026-11-09, when all 15 boards reached
0 / 0 / 0 FAIL through the full chain on it (`PCBFLOW_ROUTER=freerouting` brings back route.py).

## Why

freerouting is a black box that routes nets one at a time in an order of its choosing and
rips up whatever is in the way. Three costs follow, all measured on our boards:

- **Order chaos.** A 0.1 mm nudge reshuffles the whole board, so "does it route" can only
  be answered statistically: the 11-route series (2.5 h) exists to measure luck.
- **No intent.** It cannot be told which side of a chip a signal should leave, which
  corridor to keep free, or which nets matter. Declared copper steers it indirectly, and
  it routes round the declaration and fails a different net (output_panel, 2026-11-08:
  every per-net cure moved the failure).
- **No reuse, no speed.** 20 passes are most of a 25-minute run, and nothing learned in
  one run is available to the next or to placement.

## What an engineer does, and what this router does for each

| Engineer | Router stage |
|---|---|
| Looks at the whole ratsnest before drawing anything | **plan**: every net's terminals, connected pieces, width, class |
| Routes power, pairs and critical nets first, by hand | declared copper and frozen nets stay as layout lays them; routed nets get a class order |
| Plans each dense part's fan-out: which pin leaves which way, on which layer, in what order | **escape**: per fine-pitch part, a direction and layer per pin |
| Gives each layer a job (inner layer runs one way) | layer preference costs |
| Sees where channels are over-subscribed and moves parts | **congestion map**: coarse global route, also a score layout can use |
| Draws each trace with all the others in mind, nudging earlier ones aside | **negotiated detailed routing** (PathFinder): every net routed together, contested space priced up each round until nobody shares |
| Tidies: straight runs, 45° corners, fewest vias | **cleanup**: grid path to segments, pull tight, exact-geometry check |

Negotiation is the opposite of "keep trying random combinations": it is deterministic, it
does not depend on net order, and when it fails it says where (the cells still shared),
which is placement feedback rather than a coin flip.

## Model

- **Grid.** 0.05 mm pitch over the outline, one plane per routing layer (plane layers
  such as output_panel's In1.Cu are not routed; vias pierce them and the pour clears).
- **Static obstacles** (pads, declared copper, frozen nets, vias, keepouts, edges) are
  reduced to a per-layer distance field: distance to the nearest copper `d1` and its net
  `n1`, and distance to the nearest copper of any other net `d2`. Net m's centreline may
  stand on a cell iff its foreign distance (`d1` if `n1 != m` else `d2`) is at least
  `w_m/2 + clearance + margin`. Exact shapes come from `repair_search`'s parsers (pads as
  inset rectangles plus corner radius, the hard-won model).
- **Routed copper** is marked per cell as a count of the nets whose keep-out covers it;
  the negotiation prices those counts.
- **Vias** must clear foreign copper on every copper layer, and the drill must clear
  every other hole (hole clearance, hole-to-hole). No via in any land, own net included.
- **Keep-outs** ban by the copper's EDGE: the track field is the true distance to the
  area, the via ban grows by the via radius.
- **Widths, as an engineer sets them**: signals at `SIGNAL_W` 0.2 (the class's 0.25
  everywhere left nets open on optical and output_panel). A power_paths net is sized by
  `power_width`: the larger of IPC-2221 heating width and the width whose resistance
  over Manhattan x `DETOUR` keeps the drop within `DROP_SHARE` of quality's budget,
  capped at `POWER_W_MAX` (wider: pour it). `net_widths` wins. Wide nets neck to 0.2
  within 1.2 mm of their own copper.
- **Pours**: a regional pour is priced (`REGION_COST`) for other nets, not banned; a
  poured land of a small part (`RING_PADS` or fewer pads) gets a thermal room of
  `RING_MM` priced `RING_COST`, so its spokes are not starved (ringing IC pins too
  priced every escape and left a net open).
- **Pad holes**: no via within the fab's pad-hole rule (`HOLE_PAD` 0.45, quality.FAB
  hole_hole_pad) of a drilled pad -- the rules file's hole-to-hole is the via figure.
- **Diff-pair chains are an order**: `diff_pairs[].chain` (U31 -> U10 -> J1) is routed
  hop by hop, each hop clear of the net's other copper, so a series part (the ESD
  clamp) can never be bypassed. A part is one node: a hop lands on whichever of its
  pads it reaches, so a clamp whose far pin faces a wall is tapped on the near pin
  (its own link a 2 mm stub) instead of the pair wrapping round it.
- **Forced pair swaps are symmetric**: when one rail of a same_layer pair has to dive
  to cross the other (outside the merge circle), its mate's nearest hop must pass
  through the same layer within `WP_MM` of the dive -- vias on both, one layer set,
  as an engineer swaps P and N. `congestion.pair_dives` still names the spot.
- **Declared landing pads hold**: a part with `diff_pairs[].pads` (J1: A6, A7) is not
  widened to its whole piece, so the merge stub cannot hand the hop B6 and reverse the
  pair's sense at the socket (a second crossing, 4 vias, on 4 of 11 placements).
- **Pairs are finished as pairs** (`_finish_pairs`): the negotiation only asks that no
  cell is shared, which a split pair passes. After it, a pair that breaks verify's rules
  (`pair_faults`: layer set, via budget, skew, measured exactly as verify.py does) is
  laid again, everything else held: home layers; else one dive on one named layer, the
  mate following, each order, plain / dives x4 / vias x5. The first attempt that meets
  the rules and shares nothing is kept; failing that, the best rule-meeting attempt is
  held and the nets it crosses re-negotiate round it (`_displace`), kept only if no more
  nets end open. `OWNROUTE_SNAPSHOT` pickles the negotiated board to replay this stage.
- **A pour join must reach the main fill** (`_pour_islands`): a regional pour's join
  via counts only if the refill reaches it. After the pair finish each such net is judged
  as the refill will lay it: its region minus every other net's keep-out, opened by
  `FILL_MIN_W`, joined through the net's own lands, tracks and vias. A piece off the main
  body is re-joined to the main body only, the others re-negotiating round it, and the
  result is kept only if no more nets end open. Optical +3V3D, 2026-11-09: an islanded
  join on 16 of 19 nudges became close_last's 13.5 mm closure across a 1.7 mm gap (A23).
  Only the cut-off pieces are re-joined (`keep_paths`): re-routing the whole net moved a
  good join under U6 onto ULPI_D5/D6 (a locked match group), so on every optical run the
  re-join was put back. Now it holds, and the step takes 1 s instead of 35.
  The fill is judged by the ZONE's own rules (`model._zone_rules`: optical's pours keep
  0.5 mm off other copper, 0.25 mm minimum width), not the netclass's 0.127/0.2: the judge
  saw fill under U6 that KiCad never lays, so four join vias stood on islands, the tidy
  removed them as dangling and close_last closed six stranded pads. Now 0 stranded.
- **A slot in the return plane is crossed square** (`model._ref_voids`, `VOID_COST`): each
  routing layer's reference plane is the nearest ground copper in the stack, as quality
  A15 reads it; where that plane is void for `VOID_MIN_MM` or more (a socket's row of
  antipads, the cut under a photodiode) a signal pays 3x a cell, so it crosses short and
  never runs along. pi_cap UI_ENC_A ran 11.77 mm along the 40-pin row against 9.3 signed.
- **A net stuck in a stalled negotiation looks wider** (`WIDEN_AFTER`, `STALL_ROUNDS`):
  the window grew only when it held NO path, and a shared one always exists, so two
  pi_cap nets fought over one gap at pf 576 and were ripped out. Once the negotiation is
  `STALL_ROUNDS` without gain, a net sharing `WIDEN_AFTER` rounds starts at 12 mm, then
  the whole board. Only when stalled, never a matched pair: widening while it still
  improved moved optical's nets round its USB pair and left the pair unfinishable.
- **A pair attempt whose rails overlap is no attempt** (`_pair_try`): "fewest shared
  cells" counted the rails sharing with each other, which `_displace` (pair held, rest
  moved) can never undo; USB_DP and USB_DM were written 0.33 mm into each other.
- **A net still sharing when negotiation stops is routed first** (`_priority_repair`,
  before `_rip`): it is lifted with its pair partner and the nets it shares with, then
  routed in each order (it first, its partner first, the others first) and the best kept
  if the board has fewer nets sharing or open; else put back. Optical with ten resistors
  moved 20 mm from J1 (2026-11-09) ended with D+ and D- each wanting the one via site
  beside J1's lands; D- first closes it. Fires only when nets are stuck, so a board that
  closes is unchanged (15/15 router-alone identical). Not fixed by it: two nets of one
  part moved where both its pads cannot escape (R40, FB/V5_PRE) -- a placement fault, which
  the 1-round placement proxy flags. Tried and dropped: a whole-board window pass (no gain).
- **Exact clearance of what is written** (`geomcheck.check`, ROUTER.md M2): every emitted
  segment and via against other nets' pads (exact shape), tracks, vias and new copper,
  each shortfall named with what drew it (run, stub, via). 0 on every board, 2026-11-09;
  run it after any change to emit or the pair finish.

## Placement feedback

Every run prints the most contested 2 mm blocks (history summed over the negotiation)
with the nearest parts: where moving a part buys routing room. On output_panel the top
block was U1 west / C52, the spot that ate the freerouting nudge series.

## Results so far (2026-11-08)

- output_panel nudge series, 11 placements: 10 at 0 unconnected / 0 DRC through the
  whole finish chain (freerouting managed 9-10 of 11), router 220-300 s each. The 11th
  was a via clipping a keep-out corner -- fixed (edge-based ban).
- motor_ctrl and pi_cap at their targets; optical routes standalone at 0 unconnected.
- optical at target through the whole chain (0 / 0, 0 FAIL) on its committed
  placement once chains were ordered and the USB swap made symmetric: the pair's
  crossing was the clamp, socket and hub pinning out in opposite senses with no room
  to turn U10 (plug cutout south, MCU north, PHY decoupling east).

## Stages and milestones

1. **M1 detailed router**: model, numba A* in 3D (8-way, via cost), PathFinder loop,
   Steiner growth for multi-pin nets, write segments/vias. Target: output_panel signal
   nets routed with zero shared cells, deterministic, in minutes.
2. **M2 cleanup + DRC**: segment merging, pull-tight, exact clearance check, then the
   rest of the finish chain unchanged; kicad-cli DRC clean.
3. **M3 escape planning** for QFN/QFP parts, layer discipline, class ordering.
4. **M4 congestion map** from a coarse global route; a `routability` score for
   layout.py, so placement is judged before a detailed route is spent on it.
5. **M5 parity**: all four boards (optical, motor_ctrl, pi_cap, output_panel) at their
   targets on it, then every finish-chain board. Router-alone: all 15 boards, 0 nets
   open, 0 pair faults; full chain: all 15 at 0 unconnected / 0 violations / 0 quality
   FAIL, unmoved (2026-11-09, cadkit 1d4fbee). DONE: it is the default.

Each milestone is measured against the freerouting baseline on the same placed board
(`<stem>.unrouted.kicad_pcb`): unconnected, DRC errors, quality FAILs, wall time.

## Speed (2026-11-09)

Optical router-alone 800 s -> about 100 s (1440 s -> about 2 min inside finish under load),
same nets, same pair verdicts. Profile first: the cost was never where it looked.

- **Point-in-polygon was 57 % of a route.** A pour fill is a fractured polygon of
  thousands of points; `model._in_poly` looped its edges in Python over the whole window,
  35 s a call, every round, for +3V3D's plane joins (and 37 s more building the nets).
  Now a compiled scanline for grids (identical answers, checked polygon by polygon), and
  the join mask is cached per net and window.
- **A search must not pay for the window it does not visit.** A whole-board plane join
  allocated and cleared 130 MB for a 10-cell path. `search.astar_s/astar_turn_s` keep
  persistent buffers with a generation stamp: identical paths on 50 captured calls.
- **Plane joins look beside the pad first** (`PLANE_JOIN_MM` 2, 6, then everywhere).
- **Heuristic weight 1.2** (`ASTAR_EPS`): negotiation 123 -> 90 s, +0.4 % track, vias
  unchanged. Congestion pricing makes the straight-line heuristic weak; 1.3 halves work
  for about 5 % dearer paths.

- **Heuristic to the nearest target cell** (`HMAP`, search.astar_s_h / astar_turn_s_h):
  the box heuristic measured to the targets' bounding box, so a net whose lands are spread
  had no guidance inside it (optical BOOT0: 7.7 M states, 5.6 s, for one 46 mm net; 0.4 s
  after). A Euclidean distance transform of the target cells, max'd with the box octile:
  still admissible. 15-board router-alone: motor_ctrl 96 -> 15 s, output_panel 151 -> 48 s,
  ui_board 68 -> 17 s, optical 134 -> 75 s; 0 open, 0 pair faults, 0 shortfalls. eps 1.0 with it was
  worse on optical (two nets open): kept at 1.2.
- **A plane net re-joins only its sharing pieces** (`PLANE_KEEP`): +3V3D's ~55 joins were
  all re-searched every round it shared, 220 searches, a third of optical's negotiation.

Pair finish (same day): in a pair attempt the mate is a wall, not a price (`PAIR_WALL`) --
at the finish's congestion price the second rail went over its mate rather than through
others' space, so every attempt was refused for overlap and none reached `_displace`. A
same-layer pair with no home layers is also tried one layer at a time. `_displace` counted
the pair's own failed-attempt flag as an open net, so a displacement that left LED_ROW open
passed as "no worse": now only the other nets are counted. And the root of it: a
same_layer pair without a merge connector now runs on the layer its lands share
(`run_layers`, strict then relaxed, as the merge case) -- HUB_PHY's leading rail had dived
to B.Cu wherever its lane was busy and the negotiation ended with the pair split.

Tried and dropped, measured:

- **Corridors from the global plan** (`CORRIDORS`, off): round 1 halved, but nets shared
  longer: 123 s either way, 131 s releasing a net at its first share.
- **Parallel rounds with the serial answer**: nets in level 1 + the highest earlier
  overlapping net's level. Exactly the serial paths, and no faster -- on optical 64 nets
  fall in 45 levels, the dense MCU/USB area overlaps itself. Parallelism belongs one level
  up: several placements scored at once, a process each.

## Global plan (`globalroute.py`)

Every net planned on a 1 mm grid (capacity = free fine rows or columns over the track
pitch), PathFinder at that scale, in under 2 s on every board; the run prints the plan's
overflow and the parts beside it. **Not yet a placement score**: against the detailed
router's contention map (optical S53o0, 2 mm blocks) its overflow correlates 0.13-0.46
(Spearman) and finds at most 2 of the top 10 hot spots, whatever the capacity derate. The
detailed contention sits in pin escapes (U7's ULPI fan, U10/U31, the crystals), which
1 mm squares cannot see; a score needs escape modelling at pad scale.

## Runtime

Python 3.12 + numpy + numba (installed 2026-11-08). The finish chain runs steps under
KiCad's Python; `ownroute.py` re-runs itself under `py -3.12` for the compiled core.
