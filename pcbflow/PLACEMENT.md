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

    py -3.12 place_flow.py <dir> <intent.json> [--no-auto] [--soft-forbid] [--skip-finish] [--fold-post]

`<dir>` holds `<stem>.net`, `<stem>.board.json` (the notes: outline, cutouts, slots, pairs,
layers, `post_route_refs`) and `<stem>.parts.json`. A fresh board needs no layout: when
parts.json is missing the flow writes it with `place_geom.py <stem> pads --from-net`, each
netlist part's pads and courtyard from its footprint alone (on motor_ctrl the 107 parts'
pads match a layout dump exactly). Write it yourself first if the intent script reads it. Set PCBFLOW_FOOTPRINT_DIRS / PCBFLOW_PROJECT as for layout.py.

The stages:
1. The intent. Unless `--no-auto`, auto_decaps and auto_floorplan are added for any set the
   file does not already carry. auto_singles is opt-in (`--auto-singles`, lead ruling
   2026-11-12): test pads' 8 mm `near` cost routing on two boards (output_panel op12: a pair
   fault, 20.9 mm uncoupled); their `access` rule is what matters.
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
   * `between` for a part on the path between two others (a transceiver between its MCU
     and its connector, a series resistor between driver and load): `{kind: "between",
     ref, a, b, max_mm}`, where a and b are parts or pins. It is met when the part's centre is
     within max_mm of the a-b segment. In place_init it is two equal springs, so its optimum
     is the midpoint.
   * `decap` where auto_decaps' pin choice is wrong (optical's C130 at U10's VBUS pin).
   * `current` for power nets, which sets the widths.
   * Declared `diff_pairs` with a `chain` in the notes: a pass-through part in a chain is
     turned to face it.
5. **The defaults, through place_flow:**
   * auto_decaps: a decap at each IC supply pin.
   * auto_singles (opt-in, `--auto-singles`): test pads at their driver pin.
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

**Post-route parts are placed with the rest: `--fold-post` (2026-11-11).** A
post_route_ref is dropped onto the FINISHED route at the free spot the copper left. That
spot was searched against one hand route, so on any other placement it lands on tracks.
Optical's auto board had 39 unexpected DRC items of this kind: Rs/Cs pads bridged by
I2C2_SCL, and SHDNZ left open.

`--fold-post` empties post_route_refs and post_route_nets, places those parts by the
intent, and routes their nets with everything else. For optical:
* The converter `group`s take Rsk1 (the SHDNZ pull-up) beside Csk9.
* Every TP gets an `access` rule.

parts.json must carry their geometry: place_geom on a layout of the full netlist. If any is
missing, the flow stops and names it. **For a fresh board, write no post_route_refs at
all.**

Two finish-chain gaps were found the same way:
* **layout `_flip_merge` handled only a USB-C pad row along X.** output_panel's placement
  turned J3, so HUB_UP_DM's duplicated pads were never joined (1 unconnected). The merge
  now works in the row's own frame.
* **verify measured the merge's own stub as the transmission line** (A3: HUB_UP 4 vias, a
  split layer set) wherever a group declared no `merge_at`. A group now takes its merge
  refs from the netlist: a connector (J*) carrying each of its nets on exactly two pads.
  Pass-through parts are excluded, since their copper is the line.

| finish + quality | unconnected | violations | quality FAIL / OPEN |
|---|---|---|---|
| optical hand, stripped | 20 | 78 (20 declared) | 22 / 6 |
| **optical auto, folded** | **0** | **22: 20 declared D/PD + 2 silk_edge warnings, 0 unexpected** | **3 / 6** |
| output_panel hand, stripped | 1 | 7 | 11 / 5 |
| **output_panel auto, flip fix** | **0** | **6 silk_edge (the hand board's 6)** | **6 / 5** |

What is left, and where it belongs:
* **optical**
  * A2: U8.2 is 5.4 mm from C100 (the limit is 5.0).
  * A17: J2's pinout fits on the back face only.
  * The silk labeller found no free site for the TP1, TP2 and TP8 words, which the report
    prints on its NO ROOM line.
* **output_panel**
  * A1 (+24V 0.5 mm, J1_VBUS 0.2 mm) fails on the hand board too. The notes' net_widths are
    below their declared currents, so give the intent `current` rules
    (`place_intent.widths`).
  * The PI pair splits F.Cu/In2.Cu. This is a real routing result.
  * A17: J6's back_only declaration is stale on this placement.
  * The 6 silk_edge_clearance on J2/J3/J4 are the panel connectors' silk at the edge, the
    same on the hand board.

**Second round (2026-11-11, lead: A2 reach, `current` -> widths, A3).**
* **auto_decaps: every IC on a rail gets a cap.** Nearest-pin assignment gave all 16 of
  U6's +3V3D caps to U6 and none to U8, the LDO whose output is +3V3D (A2: U8.2 at 5.4 mm).
  An IC left without a cap on a supply rail now takes one from the IC holding the most on
  that rail. The donor gives up the cap whose pin has another capped pin nearest it in the
  package. That neighbour's rule gains `also` (decap rule: a cap serving several pins,
  seated at their mean, judged by the farthest) at A2's 5 mm.
  * ICs in a designed cell (`group`, the `cells=` argument) are never given one: their
    caps are the cell's.
  * Result: optical A2 0 FAIL.
* **`current` -> widths in the flow.**
  * place_flow writes `place_intent.widths(rules)` into net_widths, never narrowing what
    the notes state.
  * A net with no `current` rule is still sized by the router from quality.power_paths.
  * A stated net_width under a declared, unwaived path's need is printed as a WIDTH line:
    output_panel's +24V, 0.5 mm stated against 1.3 mm for 2.9 A. That is the notes' to fix.
* **route.post_route widens necks.** The router necks a wide net to 0.2 mm wherever full
  width will not fit at its lands, and drew the whole neck at 0.2. Each narrower track is
  now widened to the widest 0.05 mm step that clears every other net's pad, track and via,
  and the board edge.
  * output_panel J1_VBUS: narrowest 0.2 -> 0.5 mm (0.53 needed), drop 59 -> 53 mV.
  * Land-limited from there: the next step would hit J1's CC2 pad.
  * DRC: 0 errors.
* **A3 was measurement, then a real twist.**
  * **output_panel PI:** the In2 stub was J2's own flip merge, now laid since the socket
    is turned. verify centres the merge exclusion on the pair's pads on the connector, not
    the footprint origin. All 7 groups pass; the shipped boards still verify 0.
  * **optical USB_HS:** both rails dived to B.Cu beside U10 in every route. The router's
    `_pin_pairs` paired each D+ pad with its single nearest D- pad. On a USB-C row
    (B7 A6 A7 B6), A6 ties at 0.5 mm with A7 and B7, so B6/B7, the one combination
    uncrossed against U10, was never offered. Every same-facing partner within reach is
    now offered and `_choose_ends` ranks them. A3 USB_HS passes.

| optical auto, folded | unconnected | violations | quality FAIL |
|---|---|---|---|
| first round | 0 | 20 declared + 2 silk_edge | 3 (A2, A17 x2) |
| this round | 0 | 20 declared + 2 silk_edge | 4: A1 V5_PRE drop 51 mV vs 50 (x2, placement-marginal), A17 x2 |

**Third round (2026-11-11, lead: V5_PRE, widen the trunk rather than rework placement).**
* **place_flow raises a stated width that is under its power path's need**, once the
  parts have positions.
  * The need is the router's own power_width: IPC-2221 heating plus the drop over the
    placed distance, capped at POWER_W_MAX.
  * Waived A1 paths are left alone.
  * `--keep-widths` only reports.
  * Optical V5_PRE: 0.35 -> 0.46 mm, and its A1 drop FAILs are gone.
  * output_panel +24V: 0.5 -> 1.0 mm, the cap. J7's path still needs 1.3 mm, which is a
    pour, not a track.
* **A `split` path is modelled as a tapped trunk in the flow's raise.** Its taps sit along
  the run, so it drops about what half its current would over the full length. Charging the
  whole current to the far end asked 0.92 mm for 0.21 A. This is NOT in the router's own
  sizing (router.model.power_width): putting it there failed the series gate, with a pair
  on ONX03 and uncoupled 254.7 -> 291.8 mm.
* **close_last stitched a net's pour islands once, then skipped every other zone-to-zone
  item on that net.** A pour sliver round U7.1/2 that the stitcher could not drill stayed
  open, 1.1 mm from a GND via. Stitching is still done once, but if the board's
  unconnected count does not drop, the item is routed like any other: GND closed with
  8.6 mm and one via, 0 unconnected.

| this round | unconnected | violations | quality FAIL |
|---|---|---|---|
| optical auto, folded | 0 (after the close_last fix) | 20 declared + 2 silk_edge | 2: A17 x2 (J2 labels) |
| output_panel auto | 0 | 6 silk_edge (hand's 6) | 5: A1 x4 (+24V J7 1.0 vs 1.3; J1_VBUS land-limited 0.5 vs 0.53, 53 mV), A17 J6 stale |

**Pours from intent (2026-11-11, lead).** A current no track can carry is a
`pour(net, layer, region | along [, width_mm, priority])` rule.
* place_flow builds the outline at the placed pins: the named region, or the hull of
  circles round each `along` pin. The default width is 1.5x the IPC width of the declared
  path between those pins, at least 2 mm.
* The outline is written into notes["zones"] at priority 1, so it wins over a board-wide
  ground pour on the same layer.
* The report prints a POUR line counting other nets' pads inside the outline on its layer.
  That is the room check: a pour goes only where its layer has room (the +3V3-on-In2
  lesson).
* **quality A1 measured a pour's cross-section over its whole extent**, so a cut across
  the rounded tip, past the pad, read 0.20 mm and failed a 3.8 mm pour. It now measures
  only the cuts between the path's two ends. The shipped boards' quality is unchanged.
* **output_panel +24V Q2->J7 (2.9 A) on F.Cu.**
  * First run: A1 passed (narrowest cut 3.80 mm against 1.30 needed), but BOOT went open.
    Taking a corridor for the pour exposed C4, the bootstrap cap, sitting 7.8 mm from
    U5.4: auto_decaps gave a cap across two pins of one IC no rule at all.
  * Now it does, at the pin of the net with fewer pads: bootstrap caps, output_panel C32
    on the DAC.
  * With that: **0 open, 252 vias (281 before), 2150.8 mm, finish 0 unconnected,
    quality 4 FAIL (5 before).**

**From-scratch authoring trial: motor_ctrl R2 (2026-11-11, lead).** The intent
(`examples/intent_motor_ctrl.py`) was written from the netlist only, its part descriptions
and nets, plus the mechanical facts in src/electronics.py:
* the +X edge stands on the floor, and the bus-B side-entry plugs come in through it;
* the Pi lies off -Y;
* the board is a 61.8 x 55 rectangle, single-sided, with no holes.

The hand placement was not read; parts.json's `at` was zeroed.

Time (agent wall clock, from the session log):
* 2.5 min to the first intent;
* 6 min to the first full flow;
* about 25 min and three intents to the third, including the system fixes below.

| motor_ctrl | open (score) | vias | finish | quality FAIL |
|---|---|---|---|---|
| hand, stripped (equal terms) | 2 (SENSE_24V, SEL_LINK) | | 2 unconnected, 0 violations | 9, all A1 |
| auto v1 | 1 | 129 | 0 unconnected, 2 copper_edge (J2/J6 mounting pads) | 20 |
| auto v2 (exclusive bands, grown power region) | 4 | 123 | 4 unconnected (crystal, CAN1) | 18 |
| auto v3 (+ a logic region for the MCU) | 2 | 139 | 1 unconnected (SWDIO), 0 violations | 14 |

**What the vocabulary and the defaults lacked**, in the order the trial hit them. The first
four are fixed here.
1. **auto_decaps assumed a placement.** Unplaced, every distance is 0, and all +3V3 caps
   went to L1.2, the buck inductor, by sort order. Now:
   * caps are dealt out by caps per supply pin, ICs before sources;
   * bulk caps go to the rail's source;
   * caps the intent already places are left alone;
   * **the netlist description decides**: "U8 switch decoupling" names its IC, and "MCU
     supply decoupling" matches U4's "RISC-V MCU" (`read_descriptions`).
2. **A cap across two pins of one IC** (bootstrap, CB-SW) got no rule. It now gets one,
   at the pin.
3. **A region held its members in but nobody out.** The Pi band filled with other parts
   and J4 had no room. `region ... exclusive: true` is now closed to all but its members
   and their satellites.
4. **The report hid the NO ROOM line when layout refused.** Fixed.
5. **parts.json needs a laid-out board** (place_geom), and its `at` rotations leak into
   place_init as defaults. For a fresh board, part geometry should come from the
   footprints alone. **CLOSED:** `place_geom --from-net`. The flow calls it when parts.json
   is missing; every `at` is 0.
   * What that exposes: the turn stage now decides every rotation. The hand board's 270 on
     U4 had been leaking in. From footprints, U4 starts at 0 and OSC_IN faces the logic
     region's edge, so Y1 lands 5.7 mm off U4.5 against its 4 mm `near`.
   * Tried and reverted: charging a turn for each satellite pin that faces out of the
     region. The quadratic turn picked 180, but the local pass turned U4 back to 0 on net
     cost and stranded Y1 16 mm off, giving 13 broken soft rules instead of 10.
   * Equal-terms result, footprint geometry, clean notes: 0 open in the route score, finish
     1 unconnected (+5V_RAW), 0 violations, quality 14 FAIL. That is v3's result, with no
     hand rotation in it.
   * **CLOSED (turns judged with satellites re-seated):** the local pass ranks each turn by
     (satellites left outside their radius, cost), and accepts a move that strands fewer
     even at a wirelength cost. A part with a stranded satellite is tried in place even when
     it already sits at its net optimum (the pass used to skip it).
   * motor_ctrl from footprints: U4 turns to 270, Y1 meets its `near`, and broken soft
     rules drop from 7 to 4.
   * Still open: Y1 at its pin is not the same as OSC routed. In f6, U4's decap C8 sat
     between U4.5/6 and Y1, and OSC_IN/OSC_OUT stayed open.
   * **Tight paths reserved (place_init step 5b).**
     * A satellite sharing a `tight` net with its anchor seats first.
     * After the local pass, the strip (CHANNEL_W 0.6 mm) from each anchor pin to its
       satellite's pin on that net is stamped into the grid.
     * The anchor's other satellites are lifted and re-seated together round the strips.
       Any other part on a strip is dropped again nearby.
     * motor_ctrl: C8 and C9 leave the U4 -> Y1 path, and OSC_IN/OSC_OUT route (open in f6).
   * Tried and reverted on the way there:
     * Charging a courtyard inside the net's pad HULL. OSC_IN's hull (U4.5, Y1, C4) covers
       half the logic band; decaps stranded 14-16 mm.
     * Charging MST-strip crossings in the local pass. A satellite is placed by its seat,
       not by that cost, so C8 never moved, and the members' charge cascaded into 8
       broken rules.
     * Stamping strips at seat time. That froze U4's first turn: the pass could not re-seat
       Y1, and U4 went back to 0.
     * Re-seating one intruder at a time. C8 went to U4.1's far side, into the U4 -> U7
       channel (f7: BOOT0, LINK_TX, SWDIO, SENSE_24V open).
   * **Still open: motor_ctrl from footprints ends with 4 unconnected (f8):** +3V3, PG_5V,
     SENSE_24V and SWDIO.
     * U4's corner at pin 1 holds C14, the OSC paths, TP1 and R7. C8 cannot get within 5 mm
       of U4.1, and the repacked caps crowd U4's west escapes (hot spot: C9, C12, R21).
     * f5 (U4 at 0, Y1 5.66 mm off its pin, a 4 mm `near`) had 0 open in the route score.
       Holding the crystal to 4 mm costs this board routing room. The next lever is U4's
       escape halo versus its decaps, not the crystal.
   * Stranding priority, checked against the two small regressions it caused:
     * output_panel 252 -> 263 vias: the buck group (U5, L1, caps) moved 36 mm. Stranded
       satellites went 4 -> 1 (C17, C2 and the BOOT cap C4 back at their pins).
     * optical's new A2 (U9.5): stranded satellites went 2 -> 1 (C141).
     * A bounded price per stranded satellite (25, 40 and 80 mm) left U4 at 0 with Y1
       stranded, on every value. Lexicographic is kept: those are trades for rescued
       satellites, not losses.
6. **`panel` knows the body front, not the pads.** Side-entry J2/J6 with overhang 0 put
   their mounting pads inside the copper edge clearance (v1). The panel rule should
   check pad-to-edge copper clearance. **CLOSED:** `check` adds a pad line, so every pad's
   far side must stay `edge_clear` (default 0.3, layout's copper-to-edge) inside the
   outline. place_init pulls the body in by the shortfall and logs it. With v1's overhang 0,
   J2 and J6 come in 0.40 mm. output_panel's six panel parts all pass.
7. **A pour cannot go round a pin row, and placement does not see the pour.**
   * Also seen: two pours of different nets on one layer at the same priority. The
     footprint-only run's +5V_RAW (L2-F2) and +5V (F2-J5) met at F2, giving DRC
     zones_intersect. FIXED: a later pour on a layer that already holds another net's pour
     goes one priority above it.
   * J3.1->J3.6 (2.7 A) runs along J3's own row, and the J3->J1 capsule crosses J1.2-4.
   * The POUR room check names them but does not act. **Open.**
   * Needed: either a pour corridor treated as a keepout for other nets' pads on its
     layer, or "turn the connector so its power pin faces its load".
   * **CLOSED in placement:** the local pass charges POUR_W (25 mm) for every pad of another
     net inside a pour's corridor on its layer. A pour's endpoint part pays for every
     foreign pad its corridor then holds, so it can turn or move.
   * motor_ctrl f6: all three pours clear (they had F1.2, D6, C17 and R21 in them). The
     +5V pour's narrowest cut goes from 0.00 to 1.24 mm (1.37 asked); the two pours that
     were cut to zero pass A1.
8. **Floorplanning is still the author's job.**
   * v2 left the MCU unregioned and the net graph put it beside the 5 V buck. The 10 mm
     zone was then NOT MET, and the crystal was pushed 15 mm off its pins.
   * One region fixed it (v3).
   * Nothing warned that a sensitive IC had no region while a switcher did. **CLOSED as a
     warning, not automation:** the report's `WARN` line (`unregioned_sensitive`) names it.
     On the v2 intent it reads "U4 Y1 unregioned while switcher L2 U5 is"; v3 is silent.
9. **Locality across bands.** U2 (bus A transceiver) followed J1 to the top edge, and
   CAN1_TX ran 34 mm to the MCU (A23). `near` pulls a part to one target; a part between
   two (a transceiver between its MCU and its connector) had no rule. **CLOSED:** `between`.
   * Its first use did not help. On U2, which also has `near J1`, U2 stays a satellite
     dropped at J1: a small part's `near` wins, and `between` only reaches the local pass.
   * The re-drop moved Y1's load caps, and OSC_IN/OSC_OUT failed in the footprint-only
     run. Without the rule, U2 already sat on the J1-U4 line.
   * Use `between` INSTEAD of a `near` on a part, not as well as one. Making a satellite's
     seat respect `between` is **open**.

Verdict: placing from scratch works, and every board finishes through the same flow. On
equal terms, though, this board ends with fewer unconnected than the hand placement but
more quality FAILs. The open items above (5-9) are what a re-layout author would hit next.

The report's **WARN** lines name a sensitive IC or crystal left unregioned while the
switcher that auto_floorplan keeps off it is held in a region.

The report's **NO ROOM** line lists every part the placer or the silk labeller found no
room for, with the region it was held to.

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
* The best TWO by place_refine's key are each full-routed. The better full route is kept
  if it also beats the parent, and it becomes the next cell's parent.
  * One re-score is one sample. Optical opt7 kept U7_90 (re-score 2.34) and full-routed it
    at 5.52 uncoupled.
  * Confirming the runner-up too, opt8 kept U7_0 (re-score 6.49, full 3.11 uncoupled,
    208 vias).
* Bounded at 3 candidates + 2 confirms per cell (CONFIRM_TOP).
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

## Where it stands for the re-layout (2026-11-12)

**What works from scratch** (netlist + footprints + an intent file; no hand coordinates):
* Part geometry from the footprints alone (`place_geom --from-net`, called by the flow when
  parts.json is missing). Rotations are all decided by the turn stage.
* Decoupling without authoring: `auto_decaps` deals caps out per supply pin, matches ICs by
  netlist description, gives bootstrap caps a pin rule, and keeps ONE tight cap per supply
  pin per rail. The extra caps of a covered rail go loose (`near` the IC, 8 mm, weight 0.5).
* Noise floorplan by default (`auto_floorplan`): switch node vs sensitive parts is a hard
  forbid zone, and the USB/relay edge rules are soft. The flow WARNs when a switcher is held
  in a region and a sensitive part is not.
* Pours from the intent (`pour` rules, per-layer priority, stale zones replaced), with the
  pour corridor charged in placement (POUR_W).
* Panel parts sit their pads clear of the copper edge.
* Tight escape paths of an anchor's satellites are reserved (CHANNEL_W 0.6), and the anchor's
  other satellites are re-seated around them.
* `between a b` for a part that belongs on a signal path.
* Cell turns are chosen by routing them: the top two candidates are full-routed (CONFIRM_TOP)
  and forbid zones are hard.
* `auto_singles` is opt-in (`--auto-singles`). By default output_panel is back to op14.
* Finish is bounded: close_last stops a rip-up join at the deadline. It ran 11 h on f10;
  on f11 it ran 721 s.

**Results, equal terms (declared copper stripped, notes placements stripped):**

| board | open in score | uncoupled | vias | finish | quality FAIL |
|---|---|---|---|---|---|
| optical (opt13, auto + cells) | 0 | 2.4 | 202 | 0 unconnected | 0 |
| output_panel (op15, default) | 0 | 0.52 | 253 | 0 unconnected | 3 |
| motor_ctrl from footprints (f10) | 2 | -- | -- | 1 unconnected (CAN1_TX) | 10 |
| motor_ctrl + `between J1 U4` on U2 (f11) | -- | -- | -- | 1 unconnected (CAN1_TX) | 11 |
| **motor_ctrl, logic band 2 mm wider (f21, f22 from the example)** | **0** | 0.0 | 125 | **0 unconnected, 0 violations** | 11 |

All three route. **But f21/f22 break Y1's `near` (4 mm) by 1.66 mm** -- found 2026-11-12
after the result was reported: with the band at 4, U4 turns to 0 and Y1 still cannot seat
off U4.5 (west of U4 there is 0.6 mm of band for a 3.5 mm crystal), so it sits north at
5.7 mm. The lead's ruling holds Y1's near, so this is a trade for the lead to decide, not a
result. On motor_ctrl the score takes 31 s and the finish 53 s (it was 5-7 min and 12 min
while CAN1 fought its way out). Its 11 FAILs are the buck region's power-path
widths, U2.5's cap distance and connector-label declarations; none is at the MCU.

**Tried this round and reverted:**
* A loose cap aimed at its supply pin instead of the IC centre. Optical went to 3.11
  uncoupled and 2 FAIL (A17 x2), output_panel to 1.03 / 259 vias, and motor_ctrl with
  `between` to 3 unconnected / 12 FAIL (f13).

**Open gaps, in order:**
1. ~~motor_ctrl CAN1 escape~~ **CLOSED (2026-11-12)**: see "The CAN1 escape" below.
2. **`between` loses to a satellite rule** on the same part: the satellite wins. On f11 U2
   moved onto the J1-U4 line and CAN1_TX still failed, so the line was not the fix by itself.
3. **Gap 7, the placement corridor**, is only part done: pours are charged, signal corridors
   are not.
4. **Optical GND finish noise**: close_last results vary from run to run on GND stitching.
5. `auto_singles` stays off until it helps a board without costing output_panel.

**The CAN1 escape (2026-11-12).** It was not the parts in front of the pins:
* The router's own words: "CAN1_TX still shares space ... beside CAN1_RX, CAN2_RX, CAN2_TX,
  SWDIO". U4 sat at 270, so CAN1 (pins 46/47, bound for U2 at -X) was east of CAN2 (35/36,
  bound for U3 at +X) on the same 0.4 mm row. The two buses crossed in front of the pins,
  CAN2 ran along the pin tips, and CAN1 had no exit.
* Counted as crossing escape chords (each pin's angle round U4 against its net's far pads):
  177 at 270, 72 at 0.
* U4 could not turn to 0: U4.5 (OSC_IN) then faced the `logic` band's -X edge, which the
  trial floorplan drew flush with U4's courtyard. Y1 seated 1.7 mm past its 4 mm `near`, and
  stranding ranks first, so 270 won.
* The fix is the floorplan: the band moved 6 -> 4 mm (examples/intent_motor_ctrl.py). U4 turns
  to 0 on net cost alone. 0 open, 0 unconnected, 0 violations (f21, f22).
* **What the system gained: `TANGLE HINT`.** place_init records, for each fine-pitch IC, each
  turn's crossings and stranded satellites. When the turn it kept crosses 1.5x as often (and
  10 more) as a turn a stranded satellite forbade, it says so, in flow.log and report.md:
  "U4 at 270 has 85 crossing escapes, at 0 only 33 -- but there Y1 lands 1.7 mm past its rule
  (in region logic). Give it room ... and it will turn." Log only: optical, output_panel and
  motor_ctrl place byte-identically.

**GROW: the hint acts, inside the floorplan (lead, 2026-11-12).** `_place_grow` re-places once
with the stranding region edge moved:
* Only the edge nearest the stranded satellite's pin moves. It moves by the room the
  satellite needs (pin + SEAT_GAP 1.0 + its narrow side + GROW_PAD 0.5), never less than its
  shortfall + GROW_PAD.
* Blocked if the strip enters another region, or comes within any `apart`/`thermal`
  distance (forbid zones included) of the other side's placed parts.
* The grown run is kept only if the anchor took the untangled turn AND the satellite holds.
  Else the first run stands.
* Every outcome is a GROW / GROW BLOCKED / GROW TRIED line in report.md.

On motor_ctrl with the band back at 6 it is honest and blocked:

    GROW BLOCKED: region logic, edge -X 6.00 -> 1.67 (4.3 mm) would run into region power
    (for U4/Y1); stays a hint

The first version grew by the shortfall (2.2 mm): U4 turned and Y1 stayed stranded, the same
trade as f21. With the power band pulled back to x = 0 the grow is allowed. Then Y1 holds
(+0.12) but U4 stays at 270: with nothing stranded, net cost prefers 270, and the tangle is
not a cost. So on this floorplan, "U4 at 0 with Y1 held" needs the power band moved AND a
tangle term in the turn cost; both are the lead's call. optical, output_panel and motor_ctrl
place byte-identically with GROW in.

**The re-prove at x = 6 (lead decisions (a) + (b), 2026-11-12).** Four things, each needed:
1. (a) The trial floorplan's power band ends at x = 0 (was 2), so GROW has room. The `logic`
   band is back at 6.
2. (b) The tangle is a cost after stranding: TANGLE_W 3 mm per crossing escape. It applies
   to fine-pitch ICs of TANGLE_PINS (24) pads and up. With every fine-pitch part counted,
   output_panel's 10-pin U14/U16 turned 180 on 2-3 crossings.
3. **A tight-loop satellite may stand inside its anchor's escape halo, in front of its OWN
   pins, as a fallback** (`_drop_sat`). The 2.5 mm ring held Y1's centre 4.25 mm out,
   past its 4 mm `near` on any straight side. That is why U4 only ever fitted Y1 at 270's
   corner.
   * Let into the whole ring, Y1 sat on U4's north edge, and BOOT0 / PG_5V went open.
   * So the window is the outward side of the edge carrying its tight pins, the pins'
     span +- half the satellite.
   * Judged by the rule: the plain drop is kept if the rule holds. Always open, it moved
     51 parts on output_panel, whose crystals already held.
4. **GROW holds the anchor where the first run put it**, clipped to its own region. With the
   band grown, the quadratic stage pulled U4 1.9 mm west into the room meant for Y1, so Y1
   stranded again; in-place turn retries could not help, because U4 was already there before
   the local pass.
   * The grown regions go to `init.grow.json`; place_flow rewrites intent.json with them,
     so the score judges the floorplan the board was placed in.

Result:
* GROW: region logic, edge -X 6.00 -> 1.67 (4.3 mm) -- for Y1 (U4 270 -> 0, 80 -> 40
  crossing escapes; U4 held at (10.6, 1.9)).
* U4 at 0, Y1 2.98 mm inside its 4 mm near, CAN closed.
* optical and output_panel place byte-identically and route as before: opt20 202 vias, 0
  FAIL; op22 0.52 uncoupled, 253 vias, 3 FAIL, = op15.

**OPEN: motor_ctrl is not 0/0 yet** (f24, f25: PED_H / PED_L open in the score, finish 2
unconnected (+5V_RAW, PED_H); floor 0 once the grown band reaches the score, f25).
* The new placement reshuffled the +X side. U9 (the pedal mux, 0.5 mm 10-pin) sits at 270
  with PED_L/PED_H (pins 7/8) facing J2. Its decap C37 (at U9.10) is 1 mm south-east of
  pin 8, on PED_H's way to D4 and J2.4.
* That is the same pattern as C12 at U4: a decap in a signal pin's fan-out, now on a small
  IC.

Tried and dropped on the way (each measured on all three boards):

| attempt | motor_ctrl | output_panel | optical | why dropped |
|---|---|---|---|---|
| loose cap aimed at its supply pin | 1 unconnected | 1.03 uncoupled, 259 vias | 3.11 uncoupled | worse on both others |
| fan-out band: no loose cap / small part 4.5 mm in front of an IC's leaving signal pins | 1 unconnected | 1.32-1.48 uncoupled (0.52) | same | worse on output_panel, not decisive |
| same, every part >= 8 pads (connectors, relay) | 1 unconnected | 13.5 uncoupled, 20 FAIL | same | relay K1 lifted 28 mm |
| layout: every fine-pitch part's escape lanes keep ALL stitch vias out (C12's GND via sat in front of U4.47) | no change alone | -- | layout 29 -> 472 s | slow, not decisive |
| tangle as a turn cost (3 mm per crossing) | U4 stays 270 (stranding first) | -- | -- | not decisive; the hint carries it |
| turn retried with the anchor slid back by the stranded satellite's shortfall | same spot | -- | -- | U4's hole is the only one its size |

**Authoring time:**
* Writing an intent from the netlist: 2.5 min to the first intent, 6 min to the first flow,
  and about 25 min over three intents (motor_ctrl trial).
* Machine time per full flow: place_init ~30 s, score 4-7.5 min, place_cells ~10 min when
  there are cells, finish 7-12 min. A board is about 20-30 min end to end, unattended.

## Holdouts (cold intents on boards never used to tune the system, 2026-11-12)

A holdout is written from the netlist and the CAD's mechanical facts only, run once on a
committed hash with no fixes, and reported as it comes out. A finding is fixed in the
system afterwards; the board that exposed it is then spent, and the next check is a new board.

| run | board | result | what it exposed |
|---|---|---|---|
| 1 | lever_sensor (47 parts, 45 x 21.9) | layout refused: U4 / J1 / J2 overlap | `panel.face` read as a coordinate (-19.46) put J1/J2 off the +X edge; panel never turned the part (mouth +Y on a -X panel); nothing checked a panel part against the outline |
| 1b | same, authoring corrected | layout refused: SW1 no room, on the crystal corner | a big constrained satellite (SW1: access + apart) seated after the board filled; NO ROOM reached layout overlapping |
| 2 | same, run 1's intent | intent refused at once, naming J1's negative face | (the fix working) |
| 3 | ui_board (13 parts, 121 x 32) | stopped before layout: SW1 0.24 inside a hole keep-out | the keep-out was the author's guess against a CAD-fixed part; the stop named rule, part and mm |
| 3b | ui_board, cutouts carry the CAD's `keepout_d` | **routed: 0 unconnected, 1 violation (dangling), 0 FAIL** | hole keep-outs now come from the CAD, never the author |
| 2b | lever_sensor, run 1 with face -> face_at only | NO ROOM: U3, its rules named | promoted parts placed FIRST took the middle (U2, promoted only for height) |
| 2c | same, promoted parts in area order | stopped: U2 1.75 inside the cap's 1.5 zone | place_init never treated a `height` zone as closed to a taller part |
| 2d | same, height zones forbidden to taller parts | **routed: 0 unconnected, 10 violations (9 silk, J1/J2 courtyards -- the hand board's declared pair), 2 FAIL (A17 labels)** | (cold lever_sensor places and routes) |
| 4 | fret_led_mid (97 parts, 210.8 x 70.4, 4L; 60 LEDs + 4 seam pogos fixed from the CAD, 33 free) | **no stops; 33/33 placed (28 satellites at their pins), drivers found the +Y band unasked; finish 4 unconnected (+14V5, three LED returns), 0 violations; 2 FAIL (M32 J13/J14: the hand board fails it the same way -- a netlist finding)**; 31 min (score 640 s, finish 1210 s: ownroute 629, close_last 501) | the CAD fixes an LED's position but not its turn: they kept 0 and a zone's returns left away from their driver; close_last's second attempt re-searched the same four gaps (236 s, 4 -> 8, put back) |

Fixed after them:
* `panel`: `face` is a distance (>= 0, refused otherwise), `face_at` takes the coordinate;
  without a `rot` rule the part turns its mouth (the body's side away from its SIGNAL pads) to
  the edge (`place_intent.panel_rot`; reproduces all six output_panel hand turns, and found
  motor_ctrl's J2/J6 sideways in every from-scratch run -- hand board 90, flow 0).
* the flow stops BEFORE layout on NO ROOM (the part and every rule naming it) and on a broken
  hard mechanical rule (outline incl. a panel part's pads, keepout, hole, fixed, height).
* a satellite that is big (>= SAT_BIG_MM2 courtyard), carries an access / apart / height
  constraint and is in no tight loop is placed as a part, before any satellite is seated.
* `keepout` takes `except` (optical's -Y face rule named J1/J2 in its text and nowhere else).
* board_geom HEIGHT: DSHP01 2.3.
* a cutout's `keepout_d` (the CAD's boss / post / head) makes its `hole` rule, overriding a typed one.
* a `height` zone is forbidden in place_init to every free part taller than its limit.
* constrained satellites go in area order with the other parts, not first of all.
* close_last refuses a gap over CLOSE_MAX_GAP_MM (15) as a ROUTER OPEN, net and gap named; finish gives each
  close_last attempt its own deadline (CLOSE_ATTEMPT_S 600, within CLOSE_TOTAL_S 1800). motor_ctrl f27 copy:
  finish 1496 -> ~411 s (close_last 1282 -> 12), CAN1_TX / RX named open at 29.8 / 33.3 mm; optical,
  output_panel and ui_board finish exactly as before.
* auto_floorplan's `apart` leaves out a part the intent ties (near / decap) to the other side: lever_sensor's
  U6 (`near` U3.44) had been asked 6 mm off U3 as "analog" for its BUS_SENSE input.
* finish.py prints each step's wall time and the sum by step (motor_ctrl f27: close_last 321 -> 1282 s
  on a 33 mm CAN1 gap where f24 had 4-8 mm PED gaps; the router 253 -> 363).
Optical and output_panel place_init byte-identical across all of it.

### Tried after holdout 4, and dropped (2026-11-12) -- do not rebuild without new evidence

**Turning a fixed part with no stated rotation toward its nets** (fret_led_mid's LEDs, rotation
free in the CAD). Cost: escape length to the nearest far pad + TANGLE_W per crossing chord.
Identity held on optical, output_panel, lever_sensor and ui_board.
| | holdout 4 (no turns) | per part (f5) | per zone, LED-to-LED nets grouped (f6) |
|---|---|---|---|
| route open | 5 | 6 | 10 |
| vias | 245 | 225 | 147 |
| length mm | 5412 | 4480 | 4233 |
| finish unconnected | 4 | 7 | 7 |
Per part, 14 of 15 zones came out mixed and their links crossed (fret_led.py's own note). Grouped,
every zone took the same turn (90), and all 60 returns met the driver band together. Shorter and
fewer vias, more opens. The hand design picks 0 or 180 per zone by which side of its driver the
zone sits. Diffs: scratchpad esc/fixed_turns_per_part.diff, fixed_turns_group.diff (bronner session).

**An anchor fan-in / pin-escape predictor** (per anchor side: nets ARRIVING from that direction
against the free corridor's lanes, cut by neighbour courtyards; plus wrap = quarter turns pad side
-> arrival side). Calibrated on 74 existing runs (motor_ctrl 28, output_panel 19, optical 21,
fret_led_mid 3, lever_sensor 1, ui_board 2), with no new routes. Spearman against finish unconnected:
| | route open | vias | length | wrap | peak | over | `_tangle` crossings |
|---|---|---|---|---|---|---|---|
| all 74 | **0.79** | -0.42 | -0.31 | -0.26 | -0.31 | -0.31 | -0.07 |
| motor_ctrl 28 | **0.66** | -0.06 | -0.01 | 0.07 | -0.42 | -- | -0.07 |
| output_panel 19 | **0.69** | 0.36 | 0.00 | -0.35 | -0.08 | -- | 0.06 |
fret_led_mid ran backwards: wrap 549 / 193 / 191 and crossings 101 / 86 / 82 against unconnected
4 / 7 / 7. `over` is zero on every board but optical, which finishes clean, so the corridor beside an
anchor side is never short: the 3-20x headroom score.py's 11-09 note found for escape max-flow.
The router's own route-open is still the only measure that ranks finish results. A cut-line
term was considered and skipped: the coarse global router's overflow is one already.
Script: scratchpad esc/fanin.py (bronner session).

**Handing the repairs the negotiation's BEST round, not its last** (router/negotiate.py `_rounds`).
On fret_led_mid the best round was 23 (5 nets sharing), and eight rounds without gain then ended
at 31 with 7. The repairs started from the 7. Snapshot at each new best, restore it if the
last round is worse. All 74 calibration runs fine-scored with it on. Spearman against finish
unconnected went 0.794 -> 0.831 (motor_ctrl 0.664 -> 0.688, output_panel unchanged). Better 4:
fret f6 10 -> 9, motor_ctrl f27 3 -> 2, f6 5 -> 4, f7 9 -> 6. Worse 2: motor_ctrl f5 and
"fresh" 0 -> 1, confirmed on the same code with it off. The best-counted round is not always
the better start for the repairs: on f5 the last round's sharing set repaired to 0 and the
best round's to 1. That fails the no-board-worse gate, so it is not committed. Diff: scratchpad
esc/keep_best_knobs.diff (bronner session). Parked for FINISH only, not the score: repair from
both rounds and keep the better. Quality outranks speed there, and one extra repair pass is
cheap. Revisit it when a new board's finish leaves opens.

**Two-sided placement (2026-11-13), opt-in: a `side` rule with side "B".** The output_board
(direct-drive instrument) had courtyards over 0.55 of 68 x 100 and 50 open. Its LQFP-176 is
pinned by ULPI DIR/NXT on PI11/PH4, its jack is fixed, and its box cannot grow. place_init now
runs two passes:
* the front, as before, without the back parts;
* the back on its own grid, with every front part fixed as a GHOST: through pads block,
  SMD bodies do not, and an IC over 8 pads blocks its pads plus its halo.

pi.mirror_back turns the back parts over: y -> -y, then the rotation. That was measured on
KiCad 10, where layout's Flip(pos, False) + SetOrientation is R(rot) * mirror_y. The flow
mirrors the parts file on disk and writes notes `back_refs`.

Off, it is byte-identical on lever_sensor, ui_board, output_panel, optical, output_board and
brain (place_init output and provenance).

On, it built: layout took 126 flipped parts with no courtyard overlap. It did NOT route
better:

| run | back parts | front fill | open |
|---|---|---|---|
| one-sided | 0 | 0.55 | 50 |
| decaps at their pins under U1 | 126 | 0.48 | 52 |
| front IC escape band blocked | 126 | 0.48 | 65 |

The router bans a via near ANY pad on either layer, so every back pad takes via room from the
front. Courtyard fill is not the cost for a dense board; via room is. It stays available for a
board with a spare underside, a connector or a low module. The output_board's next step is a
floorplan (regions, as optical and output_panel route with), not the back.

**Bus turn (2026-11-13), place_init `_place_bus`.** A parallel bus is BUS_MIN (4) or more
two-pin nets joining the same two ICs (ULPI, SAI). After legalisation, the anchor (the IC with
more pads) gets one retry, at the rotation that brings its bus pins' centroid nearest the
partner's seat. The retry is kept only if the bus gets shorter and no part loses its seat.

Weighting the bus in the TURN stage was tried first and failed (output_board ob11: U1 stayed
at 0). The turn judges against the quadratic targets, which pull the partner into the
anchor's bus side even where the partner's region forbids it.

Results:
* With no retry firing, it is byte-identical on lever_sensor, ui_board, output_panel, optical,
  output_board and brain.
* output_board ob12, no hand `rot`: "BUS TURN: U1 0 -> 270, its 12-net bus to U4 222 -> 170
  mm". That is the turn ob10 had been given by hand.
* Score 30 open against ob10's 25. The ULPI opens went 4 -> 4 and PD 17 -> 14; the rest moved
  to the brain-link band. Placement variance; the band is the binding constraint, not the bus.

## Rules carried over

* Keep every run to minutes; no hour-plus sweeps (ROUTER.md, route-time notes).
* The router is the judge; no new proxy scores unless validated against routes.
* The output is `placements` + provenance (`elec/<board>.place.json`: which constraint set
  each coordinate), so a later hand edit is a `pin`, not a fork.
* layout.py stays the single legality gate.
