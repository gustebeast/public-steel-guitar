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

Partial rip (2026-11-10, `PLANE_PARTIAL`): a plane net whose last few joins still share is no
longer ripped whole -- only the sharing joins come out (`n_open` counts them) and the pour
re-joins the pieces. Open work is weighed per connection (`_open_w`), and the pair finish locks
every pair already to the rules, so `_displace` can no longer trade a pair for +3V3D's 55 joins
or the other way round. Optical C102 +0.12/+0.48: HUB_PHY pair fault + island -> 0 open.

Coupled pairs (2026-11-10, `router/coupled.py`, milestone 3): a declared diff pair is laid as one
trace twice. Its centreline is searched first as a temporary net as wide as the pair (w + spacing,
both rails' copper its own, vias only where two fit), from straight out of each pin pair to the
next; each rail then runs in a lane round its offset of that line -- a strip on ITS side (the side
its pins are on, the line extended back to between them by a straight stem), free room round its
lands and where the line changes layer, priced cheapest on the exact offset. A chirality twist
(USB on the unmoved board: DP leaves U31 on the left, lands on J1 A6 on the right) is swapped at a
layer change of the line. The pair wall is via-aware. The finish tries the coupled lay first, and
re-lays a pair already to the rules if it runs more than `COUPLE_MIN_MM` apart, keeping it only
`COUPLE_GAIN_MM` closer. HUB_PHY apart (mm of rail not beside its mate): unmoved 13.5 -> 3.7,
C102 +0.27/+0.18 14.7 -> 2.6, 2 vias each, 0 faults. USB not yet: a coupled lay to the rules
opens a +3V3D join on displacement (unmoved), or finds no way (C102).

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

**Pad-scale escape and RUDY, measured (2026-11-09) -- neither is the score either.**
Against the detailed router's contention (`hist`) on optical, output_panel and motor_ctrl:

- *Per-part escape* (max-flow from a part's lands to a ring 1 mm out, track-pitch blocks,
  vias where one fits; demand = nets with a terminal outside the ring and no layout copper
  already leaving it): every part has 3-20x the lanes it needs, and demand / capacity
  correlates 0.24 with the part's contention (n 45). A part's own fan-out is not where
  these boards fight.
- *RUDY* (each MST edge's wire spread over its box) over pad-scale supply: Spearman
  0.18-0.52 by board and block size, the supply term adding nothing, and none of the
  router's top-10 blocks among the score's top 20 on optical or output_panel.
- Where the router does fight: spread out (the top 8 blocks hold 17-35 %), among dense
  clusters of small passives round an IC (U10's caps; Q1/Q2's resistors; motor_ctrl
  U8/U9) -- short nets of neighbouring parts competing for the same gaps.

With the router at 15-75 s a board (HMAP), the route itself is the affordable score:
open nets, pair faults, contention, length and vias, several placements at once, a
process each (the "parallelism one level up" above).

**`router/score.py` is that score (2026-11-10).** `py -3.12 router/score.py <stem>... [--jobs N]`
routes each placed board router-alone, a process each, and prints one JSON line a board sorted by
`key` = (open, pair faults, islands, uncoupled mm, contention, vias, length). For a small fixed
candidate set inside a placement search -- a few boards, minutes -- not a sweep. Checked:
- it reproduces the series gate's open / pairs / islands / uncoupled exactly (u10a c00-c02);
- on output_panel (op1) it ranks three deliberately bad placements -- 0402/0805 caps swapped
  between parts 30-55 mm apart, 1 / 2 / 3 swaps, all legal by courtyard and declared copper --
  below both good ones: contention 3142 and 3185 good, 3302 / 3859 / 3689 bad (+5 to +23 %),
  length 1988 good, 2032 to 2185 bad. All five still route closed, so `open` alone cannot
  rank them and contention is the term that does. ~45 s a board, three at once.

**Order-dependent pin-row escapes (output_signal, 2026-11-13) -- not a placement score, not
a local repair.** 16 candidates of 3-4 passives moved 1-4 mm (6 legal) and 9 jitters of
0.05-0.15 mm, all routed with the same router. The unmoved board and 8 of 9 jitters route
clean; every real move opened 2-7 nets, ALL at the USB3300 (U4: PHY_XI, PHY_1V8A,
ULPI_*), although the moved parts sat 10-54 mm from it (one cap turned 15 mm away opened
ULPI_D3/D4). Neither the global plan (overflow 2.8-3.5 throughout) nor a pad-scale escape
ratio per IC (flat to the third decimal) moves with these placements: the escape is
routable, and whichever order the negotiation falls in decides it. Logged, ULPI_D3/D4
never lack a path -- they end sharing each other's (and D2's) space at U4's pins, and
priority repair and wall repair both fail before `_rip` opens them. Tried and reverted
(patch kept outside the repo): (1) region rip-up -- every net within 1.5 / 3 / 6 mm of the
conflict (9 / 14 / 27 nets) lifted and re-laid stuck-first, shorter- or longer-first: no
order better; (2) the same with the history zeroed for the lifted set: no change; (3) the
lifted set re-negotiated with `_rounds` from pf 0.5: worse, 10 nets open including GND --
**`_rounds` on a subset disturbs the plane nets** (their keep_paths / joins), so it is not
a sub-solver until plane nets and everything outside the lift are locked. Read placements
over several jitters (`placescore --spread`) rather than one route. If this shows again at
a large pin row (an H743 or CM5 escape), making `_rounds` subset-safe and retrying (3) is
the next step.

## Design note: a declared pair negotiated as ONE unit (proposed 2026-11-14, NOT BUILT)

**The problem it removes.** Optical v101 (owner trace, `who.py`): from round 8 USB_DP
shared space with USB_DM and nothing else, HUB_PHY_DP with HUB_PHY_DM likewise; rounds 11-19
ran with pf 55 -> 2361 until the 8-round no-gain stop, and the priority repair then cleared
the pair in 1.4 s by laying one rail and the other round it. Both rails pay the same price
for the same cells, so each moves and they meet again: negotiation cannot break a
symmetric conflict, an order can. `MATE_STOP` (opt-in) is the stop-gap: it ends the main
negotiation once every sharing net shares only with its mate and hands over to the repairs.

**The fix.** The pair finish already lays a declared pair as one (`coupled.py`: the
centreline as a temporary net as wide as the pair, then each rail in a lane at half the
spacing either side, the second keeping the first as a wall). Use the same lay INSIDE the
negotiation, so the two rails never compete for cells at all.

- **Where it plugs in.** `_rounds`' per-net loop: for a declared pair's head net (`mate`
  set, `partner is None`, `_pair_spec` declared), call a `_route_pair_unit(a, pf)` in
  place of `_route_net(a)` then `_route_net(b)`, and skip `b` when the order reaches it. It
  searches the centreline at the round's pf / history (so the pair is priced against
  everyone else as one wide net), lays both lanes, and returns both rails' paths. The
  per-net sharing loop after the round is unchanged: rails share with OTHER nets only,
  and history lands on the cells they share.
- **Kept cheap in the rounds.** The finish tries `COUPLE_ENDS` (3) pin-pair choices x
  `MID_SLACKS` (3): up to 9 centreline searches. In the rounds: one end choice (the last
  round's winner, cached on the net; the best-ranked on round 1) and one slack (0.1). The
  full exploration stays in the finish.
- **Fallback.** A unit lay that fails (no centreline, or a lane cannot reach a land)
  falls back to the current two-net route for that round. That keeps today's behaviour as
  the floor, with `MATE_STOP` still catching that case.
- **What it replaces.** `MATE_STOP`, which no longer has anything to catch for declared
  pairs. The priority repair's partner orders (`grp`, `grp[::-1]`) for declared pairs,
  where the lane wall IS the order. Most of the finish's coupled re-lay, which becomes a
  check that re-lays only a faulted or apart pair rather than the default path. Also the
  partner band in `_route_net` (`negotiate.py` ~1021) for declared pairs; undeclared mates
  keep it.

**Measure first, before building.** Where are the 11-15 cells the mates share in rounds
11-19: at the fine-pitch lands (U10 / J1, 0.5 mm pitch, where the two pins sit closer than
the band's spacing and the rails MUST neck) or mid-run? If they are at the lands, the
symmetric conflict is a land-exit problem: the cheaper fix is that mate-vs-mate overlap
within `COUPLE_END_MM` of their own lands, where both run necked, is not counted as
sharing. The unit lay is the fix only if the overlap is along the run. (`who.py` +
the cells' distance to each rail's lands answers it; one route.)

**Risks.**
1. CPU per round: a centreline search plus two lane searches per pair, against two plain
   searches. The centreline is wider, so its window is tighter. Judge by the A/B, not by
   argument.
2. Fine-pitch ends: the centreline starts BETWEEN the lands. Where the escape stubs
   (`ESC_*`) or a neighbour's via block that midpoint, the unit fails every round and the
   fallback carries it; count fallbacks in the A/B.
3. Layer relax (`RELAX_AFTER`): today each rail relaxes on its own. As a unit the
   centreline relaxes, and both rails follow it.
4. Rescore / delta (`rescore.delta_run`): a pair must be kept or re-routed whole. That
   already holds in practice (a moved land changes both rails' pieces) but should be
   asserted.
5. Plane joins and `keep_paths` are untouched (pairs are never plane nets).

**Gate.** The 12 optical variants plus output_board mL2: open, pair faults, uncoupled mm
(the key ranks it, and v101's `MATE_STOP` run already lost 2.6 mm on HUB_PHY) and CPU,
each against `MATE_STOP` and against neither.

## Design note: decide a pair's twist BEFORE routing (proposed 2026-11-14, NOT BUILT)

**What the pair finish's displacements do (output_board, rob_d1 placement; rob_close,
rob_d1 and rob_kf2 route logs, parsed per displacement).** Each attempt that lays a pair to the rules
through other nets' space runs `_displace`: one sub-negotiation of up to `PAIR_RENEG_S`
(120 s), kept only if no more nets are open, the pair has no faults, and it shares nothing.

| run | wins | CPU on wins | losses | CPU on losses | losses ending >20 open |
|---|---|---|---|---|---|
| rob_close, first route | 2 | 260 s | 11 | 1387 s | 6 |
| rob_close, close pass | 2 | 53 s | 9 | 956 s | 4 |
| rob_d1 | 2 | 246 s | 13 | 1420 s | 5 |
| rob_kf2 (RENEG 50) | 2 | 54 s | 17 | 970 s | 15 |

- **Wins** are the same few pairs every time, laid through FEW cells: USBA_DP_J (16),
  MCU_DP (55; 12 in the close pass), USBA_DP (6). They are local pushes.
- **Losses** are 84-95% of the displacements' CPU. Each spends its whole budget, and 4 in 9
  to 15 in 17 end with 35-132 open (GND, +3V3D, CAN, ...): a pushed pair re-negotiates far past
  its own neighbourhood.
- **USBB_DP/DM and FLASH_DP/DM lose every attempt in every run** and end "layers, vias --
  no attempt met the rules". Afterwards the router reports them as "the pair crosses itself
  there -- a placement twist; routing cannot keep it on one layer" (`congestion.pair_dives`).
  rob_close spends 751 s (first route) + 676 s (close pass) on the two of them; rob_d1
  605 s. If they are twisted, no displacement CAN win: the fault is topology, not congestion.
- An anomaly to fix on its own: rob_d1 MCU_DP left 1 net open (was 8), the board better,
  and was put back, because the keep test also requires the pair fault-free. That is
  the case `DISPLACE_KEEP_FEWER` was written for (parked: its only A/B was worse).

**The change.** A coupled pair is a ribbon, and in one plane a ribbon keeps its handedness:
which rail is on the left, seen along the direction of travel. At each end of a hop that
handedness is fixed by the lands: the outward normal `n` of the part's side the pins sit on,
and the rail order `d = P - N` across it. Leaving end A, `s_A = sign(n_A x d_A)`; arriving at
end B, travel is `-n_B`, so `s_B = sign(-n_B x d_B)`. **`s_A != s_B` means a twisted hop:**
no same-layer coupled route exists, and one rail must change layer once, somewhere. (U10 ->
U31 on optical, `pair_dives`' own docstring, is this case.) Hops split at pass-through parts
(`merge_at`), as the pair finish already splits them.

Computed once, after `build_nets` and before the negotiation, for every declared pair hop:
1. **Negotiation.** A twisted pair is routed relaxed from round 1, budgeted one crossing
   (max_vias counted with it), instead of being held to its layers for `RELAX_AFTER` (10)
   rounds it cannot meet.
2. **Finish.** No displacement whose aim is `layers` or `vias` for a twisted pair. It is
   laid once, fewest faults, and the fault is reported as placement (the twist, with the
   parts at each end). Skew and open still get their attempts.
3. **Placement feedback.** The twist goes into the score / placement report up front (which
   part to turn, which pin order to swap), not as a post-hoc guess from where a rail dived.
   `pair_dives` today calls every dive a twist.

**Measure first (seconds, no route).** Run the handedness test on rob_d1's placement for
every declared pair. It must flag USBB and FLASH and NOT USBA / MCU / GADGET, whose
displacements do win, or lose to congestion. If it flags none, the USBB / FLASH losses are
congestion after all and this note is wrong; say so here.

**MEASURED 2026-11-14: THE NOTE IS WRONG AS STATED; not built.** The handedness test on
rob_d1 (each pad's own long axis for its normal, both pins of the pair agreeing) flags
USBA (FL3 -> U17), USBB (FL4 -> U17 and FL4 -> J2), MCU (J202 -> U1) and FLASH (all three
hops) as twisted, and only GADGET as straight. USBA and MCU are twisted too, yet their
displacements WIN, and in rob_close's final board neither left its layers (only USBB and
FLASH did). The premise fails because the handedness is fixed only for a COUPLED ribbon,
and the finish's "to the rules" is layers, vias and skew, not coupling. In a plane two
rails can always untwist if one goes round the end of a land row or round a part, so a
twisted hop can be laid to the rules uncoupled, paying in uncoupled mm. A twist is
therefore a coupling cost, not "routing cannot", and it does not separate USBB / FLASH's
losses from USBA / MCU's wins. What does separate them is still open: candidates are
whether the untwisting detour has room (USBB has two twisted hops in a row through FL4;
FLASH three, through the two U209 / U210 switches 4 mm apart), and whether a corner pin
lets the rail enter its land from the side (U17's USBA pins are 1 / 2, at the row end).
The twist IS worth reporting as placement feedback, and since 2026-11-14 it is: place_flow's
report prints a TWIST line per twisted hop (`place_intent.pair_twists`). No rotation fixes a
twist (a turn keeps orientation, so the normal and the rail order turn together); a mirror
does, and so does swapping the rails between a pass-through part's identical channels (a
CMC's windings, a clamp's), or a polarity swap at an IC. `congestion.pair_dives`' post-hoc
label should come from this test rather than from where a rail dived.

**MEASURED 2026-11-15: UNTWISTING USBB BY A CHANNEL SWAP DOES NOT HELP -- it is worse.**
`swap_plan` on rob_d1 proposed FL4's windings swapped (pins 1<->2, 3<->4: twisted hops 6 -> 4,
both of USBB's straightened). Two instrumented routes of the same placement and netlist, one
with the swap applied (`apply_swaps`), started together on the same machine load, close pass
off: base 0 nets open, 2998 s, 15 displacements, USBB lost 3 of 3; swap 4 nets open (USBA_DP /
DM, GADGET_DP / DM), 3280 s, 16 displacements, USBB STILL lost 3 of 3. A straight hop did not
make USBB's displacement win, and the swap's changed copper cost two other pairs. So the twist
is not what USBB's losses come from, and a TWIST / SWAP line stays placement feedback only:
nothing should apply a swap without a route showing it helps. The generator keeps FL4's
original windings.

**Risks.**
1. The outward normal for a pin on a corner or on a BGA / centre pad is ambiguous; such a
   hop is "unknown" and keeps today's path.
2. A ribbon CAN un-twist by going round a part's far end (a pass-through clamp, or a
   connector with pins on two faces). Treat a land with pins on more than one side as
   unknown.
3. Relaxing early may let a twisted pair take more vias than the one crossing; budget it
   at one.

**Gate (one A/B, when memory allows).** The rob_d1 placement, router alone, `OWNROUTE_TWIST`
0 vs 1, run back to back: finish CPU (expect -600 to -1400 s), first-route open, close-pass
open, pair faults (must not rise; USBB / FLASH were already faulted), and uncoupled mm.
Then the 12 optical variants for no regression (optical's USB_HS through U10 may test
twisted on some placements).

## Tried and parked (2026-11-14)

Measured negatives, so nobody retries them blind. "Kept on" names a `parked/*` branch
in canonical cadkit, each one commit off main (not for merging; cadkit main is vendored
everywhere). Optical = the 12 `rank/v100-v111` variants unless a board is named.

| Idea | Measured | Verdict | Kept on |
|---|---|---|---|
| **Fixed-copper cache**: legality / price masks built once per net and window, not every round | Bit-identical on optical, but 78.5 -> 79.7 CPU s. Hit rate ~50% (a net's window recurs about twice, then moves); `_route_in` itself 13.2 -> 12.7 s. Its time is the per-round congestion arithmetic, not legality. | Reverted | not kept |
| **A\* memo**: skip identical repeat searches (9.4 s, 21% of A\* on optical) | A route's cost arrays total 6.7 GB; a blake2b key costs ~9 s, the whole saving. crc32 (~2 s) needs a stored copy to verify each hit. A version-counter key misses per-net inputs (walls, lanes, partner paths, necks, pf, corridors) and would silently return a wrong route. | Dropped before coding | none |
| **No-path early reject** (`_reachable` at every A\* call site, not only the leg search) | v100: no-path searches 2.7 s of a 66 s route, 2.0 s at the main search (12 calls, 9 whole-board). The check costs 7.4-7.6 s there at any size threshold 50k-500k cells; above 800k it saves 0.38 s for ~7 s. Never wrong, just dearer than what it skips. | Not built | none (the check already exists: `REACH_MIN`, line ~1248) |
| **HCOST**: cost-aware A\* heuristic (`search.hcost_map`, multi-source Dijkstra from the targets) | 1336 vs 1242 CPU s (+7.6%); 5 of 12 faster; v102 gained 3 pair faults. Swings both ways (v102 94 -> 181 s, v107 120 -> 92 s): a different heuristic picks different paths and the negotiation takes another trajectory. Both arms ran under memory pressure. | Parked | `parked/hcost-and-knobs` |
| **PAIR_RENEG_S 50 + DISPLACE_KEEP_FEWER** | output_board rob_d1: first route 6 open (RELAY, USBA_DP/DM, PDA_SDA, GADGET_DP/DM) vs 4 at RENEG 120; the capped close pass got 23, so 6 open stood vs rob_close's 0, at the same ~3100 s. | Parked | `parked/hcost-and-knobs` (opt-in env knobs) |
| **MATE_STOP**: stop the main negotiation once every sharing net shares only with its pair mate | v101 alone: 124.3 -> 109.8 s. Six variants: uncoupled 26.65 -> 32.59 mm; HUB_PHY 0.0 -> 1.6 / 2.58 / 3.32 mm on v100-v102 (the negotiation had not coupled it yet); CPU +2.8%, unusable (arms ran 0.5-1.5 GB free apart). 0 open, 0 faults. | Parked; `MATE_LAND_MM` (negotiate.py, opt-in, A/B pending) targets the same tail | `parked/mate-stop` |
| **Pair-corridor release** in `rescore.delta_run`: when a moved part carries a coupled pair, release kept nets crossing its area | conn_cluster_J1: the moved pads' area (+1.5 mm) released nothing (J1 moved into clear board; 0 nets even at 5 mm). The pair's corridor box (+1 mm) gave uncoupled 58.5 -> 11.6 mm vs the full route's 0.21. ic_shift_U7 then re-routed 42 nets in 246 s against a 169 s full route. Capped at 8 nets (+2 mm): J1 11.5, U7 unchanged. A pessimistic delta only loses candidates (the winner is full-routed). | Parked | `parked/pair-release` |
| **U220 placement order**, three forms (place_init) | output_board mN. v1 (U220 first): foreign pads in pours 31 -> 56, L204 between U220 and its FETs. v2 (every near spring followed): hard breaks on U14 / U17. v3 (pour members wait for their anchors): U220 strands 10 -> 3 but L204, 17 x 17, found no room. | Parked | `parked/u220-order` (form v3) |
| **U220 drop zone**: a big pour part kept off its IC's pin patches | mN: stranded 10 -> 3, off-pin 2 -> 1, but foreign pads 32 -> 98. With L204 / Q202 kept clear, U220 took its target and the boost power stage spread round it, so the BST_LMID / +24V pour hulls closed over U220's pins (34 of the new pads). A courtyard box instead of the circumscribed disc gave the identical result: the pin-patch discs decide it. cb / opt / fk unchanged (the zone never fires there). | Parked | `parked/u220-dropzone` |

## Known traps

- **A pour re-join that walls the board (output_board mL2, 2026-11-14).** Once
  `_islands` judged whole-layer planes (`model.plane_cells`), GND's piece at R36
  (76.3, 101.4) was found on a fill island and re-joined to the main body on its own --
  and the re-join opened 77 nets (was 0), so `_pour_islands` put it back. The island sits
  in the dense band beside the isolated-audio moat, and the only way to the main plane is
  across everything else's corridor. Read it as a PLACEMENT fact (the piece's pad needs a
  plane via it cannot have where it is), not as a reason to loosen the keep-only-if-better
  rule: that rule is what stopped a 1-open fix costing 77.
- **Pricing is not judging.** `region_net` skips pours over 80 % of the board so other
  nets cross whole planes at no extra cost; `_islands` used to read the same array to
  decide what to judge, so whole planes were never checked (GND cut into 25 + 28
  islands, 18 joins on them). The judge reads `plane_cells`; the price stays `region_net`.
- **Kept joins are claimed before fresh ones** (`_to_plane`): claimed in piece order, a
  fresh join for an earlier piece dropped its via 0.20 mm from a later kept one (drills
  overlapping, A12). Only the claims move up -- making kept paths targets early changed
  which pieces join where and cost fret_led_key GND at U10.
- **A kept-board replay starts from `layout.py`, not from the kept board stripped**
  (2026-11-14). Stripping a kept board's tracks takes its DECLARED copper too (notes
  `tracks` / `vias`, e.g. optical's comb lanes): optical then had 20 nets with no path, ran
  ~96 s a round and never finished in 55 min -- read at first as the router being slow.
  `layout.py <stem>` on the board's net + notes gives the same placement as `elec/kept`
  (270 of 270 parts unmoved; the kept board's extra parts are post-route ones) with the
  declared copper laid: optical routes in 66 s. `NOPATH_RETRY` came out of the bad replay
  -- sound, but no real board has needed it yet.
- **A price on whole planes is not how to keep them whole** (output_board mL2,
  2026-11-14). Signals cross GND's In1 / B.Cu planes free, and on mL2 they walled off
  thin strips (J240.29's via landed in one). Pricing other nets on a whole plane's cells
  (tried as PLANE_COST, removed): x3 -> 6 unconnected (was 4), x8 -> 9 and 3673 s. The
  displaced signals went to F.Cu and onto In2's VIN pours and cut those instead. Nor did
  re-routing the walling nets with the re-join (tried, removed): every attempt left
  more islands than it closed. On a 4-layer board where every layer carries signals, a
  plane strip is a placement and layer-plan fact.
- **A plane net "sharing" only for its islands must not be ripped** (output_board mL2,
  2026-11-14). `_rounds` lists a plane net with a pour piece cut off as sharing, though
  none of its joins shares space. Once `_left_w` priced such a net as its island pieces
  (2 open, not 279), pair re-negotiations that left GND so were accepted -- and `_rip`,
  finding no sharing join (`_bad_joins` None), took ALL of GND out: 260 unconnected, three
  times in one pair finish. `_rip` now keeps a plane net none of whose joins or vias share
  space; the island pass re-joins its pieces. Any change to how a left net is weighed has
  to be read against what `_rip` then does to it.
- **The island judge's grid error is not a constant** (2026-11-14). The judged fill is a
  grid fill: routed copper is stamped at cell centres within R0, grown by an EDT, and
  emitted straightened up to `STRAIGHT_TOL` off those centres; the min-width trim is a grid
  opening (disk round(2.5) = 2 cells against KiCad's 0.125). Both errors are sub-cell and
  vary by place, so no slack constant reproduces KiCad. The default (`FILL_SLACK` /
  `FILL_SLACK_FD` 0.03 on both) is CHOSEN BY ROUTE OUTCOME on mL2 (2 open / 0 clearance,
  against 7 open for the derived pitch/sqrt2 on routed copper and 0 on fixed) -- it is not
  a KiCad match, and fret_led_key's +14V5 island (a 0.226 neck against 0.25, at the end
  of a strip between two diagonal tracks) still reads as joined under it. Do not "fix" a
  count by tuning the constant. The exact judge (`OWNROUTE_FILL_EXACT`, opt-in, island
  pass only) measures the band against emit's own geometry and reads connectivity off the
  exactly eroded set; it agrees with KiCad on fret_led_key and optical, and costs ~5x the
  grid judge per call (mL2 GND 7.9 s vs 1.5 s).
- **Compare like states with KiCad.** The island judge on the snapshot taken BEFORE
  `_pour_islands` (`OWNROUTE_SNAPSHOT_ISLANDS`) is not comparable with KiCad's refill of the
  routed board: the island pass re-routes joins in between (mL2's "3 pieces = KiCad" rested
  on that, and was void). Judge the FINAL state (pickled after `_no_shorts`) against the
  board that route wrote -- and load the UNROUTED board as the model's base, or every
  routed track counts twice (as fixed copper and as paths).
- **The router's budgets are CPU time, never the wall clock** (2026-11-14). The same code
  on the same placed board (output_board mL2) ended 0, 2 and 7 nets open: the logs, timings
  stripped, are identical until a re-route phase stopped "out of time" after round 6 on a
  quiet machine and after round 4 beside renders and three other routes. `negotiate._clock`
  is `time.process_time` (the router is single-threaded; score.py runs a process per
  board). Any comparison made under the wall clock -- old-vs-new gates run at different
  loads, `score.py --jobs N` sets, the 11-09 "negotiation chaos" labels -- is suspect until
  repeated. Prove determinism by routing the same board twice at once.
- **Parent replays do not test the router.** `OWNROUTE_PARENT` reuses the stored paths:
  a fix inside negotiation is verified only by a full router-alone run on the same placed
  board, old code against new.

## Runtime

Python 3.12 + numpy + numba (installed 2026-11-08). The finish chain runs steps under
KiCad's Python; `ownroute.py` re-runs itself under `py -3.12` for the compiled core.
