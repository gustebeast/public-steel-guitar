# pcbflow's own router

Started 2026-11-08. Replaces freerouting in `finish.py` (layout -> **route** -> unwick ->
repair_planes -> DRC -> close_last), behind `PCBFLOW_ROUTER=own` until it wins on every board.

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

## Placement feedback

Every run prints the most contested 2 mm blocks (history summed over the negotiation)
with the nearest parts: where moving a part buys routing room. On output_panel the top
block was U1 west / C52, the spot that ate the freerouting nudge series.

## Results so far (2026-11-08)

- output_panel nudge series, 11 placements: 10 at 0 unconnected / 0 DRC through the
  whole finish chain (freerouting managed 9-10 of 11), router 220-300 s each. The 11th
  was a via clipping a keep-out corner -- fixed (edge-based ban).
- motor_ctrl and pi_cap at their targets; optical routes standalone at 0 unconnected.

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
   targets through `PCBFLOW_ROUTER=own`; then it becomes the default.

Each milestone is measured against the freerouting baseline on the same placed board
(`<stem>.unrouted.kicad_pcb`): unconnected, DRC errors, quality FAILs, wall time.

## Runtime

Python 3.12 + numpy + numba (installed 2026-11-08). The finish chain runs steps under
KiCad's Python; `ownroute.py` re-runs itself under `py -3.12` for the compiled core.
