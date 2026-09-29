# bronner — open work items (2026-09-28)

**Priority: optical first.** Everything else is route-downtime work.

---

## 1. OPTICAL — **the bring-up pads are IN, 0 unconnected / 0 violations**

Six pads: `TP6`/`TP7` I2C2 SDA/SCL, `TP8` BOOT0, `TP9` +24V, `TP10` +5V, `TP11` +3V3A. 248
placements, SI all four pass, ULPI skew 47.93/80, USB_HS 0.18/8.30, audit_board all checks pass.

**Two things made it possible, and both are reusable.**

1. **The pads are placed AFTER routing** (`post_route_refs`, applied in `route.py`'s repair
   block). Given to the router they cost a net in four consecutive runs; placed after it they
   cannot change what it did, and DRC still checks every clearance. `post_route_nets` does the
   same for a net that does not exist pre-route, so the DSN stays identical.
2. **The sites are searched, not chosen** — `scratchpad/padsite.py` sweeps a grid for a clear
   circle that already overlaps its own net's copper and clears every segment, via, pad,
   courtyard and the outline. Three bugs it had are worth remembering: the courtyard radius is
   the FOOTPRINT's (1.297 for a D1.5 pad), not the pad's; distance-to-outline is not the same
   question as being ON the board; and the edge keep-out that binds is the CAD's 1.2 mm, not
   DRC's 0.300.

**And the second way in was already on the board.** AN2606 puts the H74x bootloader's I2C2 on
PF0/PF1 — the converter control bus, routed since day one, at slave address 0x4E against the
converters' 0x4C. The USART1 pads that four routes were spent on cannot escape PA9/PA10 at all.

**`ROUTE_REUSE_SES=1` turns a 30-minute iteration into three minutes** when the placement and
netlist have not changed — which is exactly the case for a post-route change. It already
existed in `route.py`.

## 1b. Item 6, converter isolation — the last diagnostic gap, and it is ALIVE

**The gap:** five converters at one address with `SHDNZ` tied hard high, so one part holding
`SDA` low kills the control bus and there is no way to identify or remove it. Per-device
`SDOUT` already names a *silent* converter; this is the other failure.

**Measured 2026-09-28, and the first answer is yes.** The question the doc says everything
hinges on — can pin 14 escape a cell — was tested with `scratchpad/mkshdnz.py` (re-net the five
pin 14s, drop the `+3V3D` stubs that tie them) plus `maze.py` on the finished board:

| track | result |
|---|---|
| 0.26 mm | no path (19 cells) |
| **0.20 mm** | **path: 21.5 mm, 2 vias, U14 pin 14 to U15 pin 14** |
| 0.16, 0.14 mm | the same path |

So a shared spine is routable. **And there is room for a per-cell resistor**: a clear 1.74 mm
circle (an 0402's circumscribed courtyard) exists ~2 mm from pin 14 in **all five cells at the
same cell-frame offset (-3.46, +2.00)** — 84 sites in the first cell, 20 in each of the others.
All five converters are at rot 180, x 11.9, y spaced 18.727, so one solution copies five times
exactly as the cells' other features do.

**Take the per-cell pull-up, not the shared spine.** The spine needs ~86 mm of digital line and
**8 new vias through In1**, whose integrity (0 cuts, 0.266 mm thinnest web) is a measured SI
property of the analog reference — that is a real trade against audio quality, and the per-cell
version has no long net and no new plane cuts at all. Per cell: `SHDNZ_k` = pin 14 + a 10k
pull-up to `+3V3D` + a bare pad. Ground the pad and that converter alone drops off the bus;
with the per-device `SDOUT` lines already there, that is complete localization.

**The one thing that does not fit:** the existing tie is only **1.09 mm** long (pin 14 at cell
dx -1.96 to the channel via at -3.05, see `_shdn_tracks`), and an 0402's land pair spans ~1.5 mm.
So the resistor cannot sit in the channel; it goes at the searched site and the two stubs are
re-laid.

### The sequence, and why it is this order

1. **Free pin 14 in the netlist** (`SHDNZ_k` in `post_route_nets`) and drop the first segment of
   `_shdn_tracks`. This changes the DSN, so it needs **one real 30-minute route** — and
   `ROUTE_REUSE_SES` is NOT valid across it.
2. **Route.** Nothing in optical is touched while it runs.
3. **Search the resistor and pad sites against the NEW board**, then place both AFTER routing:
   the resistor is a real BOM part but nothing says the router has to see it, and a site verified
   clear on the finished board cannot be perturbed by a route that has already happened.
4. **Three-minute `ROUTE_REUSE_SES` pass** to validate, with DRC as the arbiter.

⚠ `route.py`'s post-route block nets ONE pad per ref. A resistor has two on different nets
(`SHDNZ_k` and `+3V3D`), so that loop needs to walk every node of every net, not one per ref.

## 2. Routing must stay fast enough to iterate (user, 2026-09-28)

A 60-minute route makes iteration impossible. Cost splits:

* **freerouting ~32 min** at 10 passes. Lever: `route.py --incremental` freezes every routed
  net and re-routes only the failures; `--passes=N` overrides. Use those while iterating and
  the full `finish.py` only to validate — hand-calling stages skips `export_geom`, so the CAD
  renders stale, which is fine mid-iteration and never for a result.
* **post-import repair** was **31+ min** at `repair_mm` 14.0 and is seconds at 8.0.
  `link_close_gaps.clear()` walks the WHOLE obstacle list per sample, so cost goes as the
  square of the reach — and since the tuple fix stopped it crashing, every link it lays is
  appended to that list and slows the next check. **The real fix is a spatial index**, which
  the routine's own note already asks for ("these three should share one obstacle model").
  Not done.

## 3. ~~motor_ctrl~~ — DONE, with the LED buck

0 unconnected, all checks pass, board 61.8 x 62.0, gated against a freshly re-cached context.

It had been broken since ~2026-09-20 behind a stale `motor_ctrl-drc.rpt`: J2/J6's XH mounting
pads hung 0.65 mm of copper off the +X edge, and TP5/C15 sat *inside* J2's pads. Fixed first,
which is why the buck then routed clean on its first attempt.

⚠ **A `*-drc.rpt` in the repo root is not evidence** — led_strip's counts unconnected *pads*
and misses a track↔zone pair entirely. Use `finish.py` / `audit_board.py`.

## 4. pi_cap — the UI board's 14-way ribbon (brenner)

Decided (see `docs/pi-cap-ui-ribbon.md`): **1.27 mm 2×7 shrouded IDC**, display on **SPI1**.
Remaining: pick/verify the LCSC part, fit it or grow the board ~14 mm in plane (brenner
measured 29.5 × 56 × 11.55 free alongside, holding only reroutable cables), add `+3V3` from
header pin 1 — the cap does not currently connect it.

## 5. chassis_2 mounting rework (user, 2026-09-28) — MEASURED, not yet built

**Goal:** mount the Pi and motor boards to **chassis_2** instead of the keyhead endplate, so
the endplate can be removed with both boards left in place.

### What holds them today

`electronics.keyhead_cradles()` builds both cradles and `keyhead_endplate` **fuses them in**,
with every column rooted inside the endplate wall (`RIB_LZ`). That root is exactly what ties
the boards to the plate. The file even records why the columns must start there: fused at the
old tray position they attached to nothing and the motor cradle came out "a free-floating
18,121 mm³ lump, which the overlap gate cannot see".

### Measured geometry (2026-09-28)

| part | X | Y | Z |
|---|---|---|---|
| motor_ctrl | −606.5…−591.7 | −113.0…−51.0 | **−83.9…−10.4** |
| pi5 | −601.6…−586.0 | −50.0…35.0 | −62.0…−6.0 |
| pi_cap | −600.0…−588.4 | −50.4…5.6 | −32.3…−6.3 |
| chassis_2 | −632.0…−397.2 | −141.9…66.0 | −81.9…0.0 |

Both boards stand in the YZ plane — thin in X (motor **14.8**, Pi stack **15.6**).

**⚠ chassis_2 is essentially EMPTY where they sit.** Probed at x −600: material exists only at
**z −72…−78**, the floor slab. Everything from z −72 up to z 0 is open bay. So this is genuinely
new structure, not a re-use of existing walls.

**And the floor is not continuous underneath them.** At z −72 it runs y −130…−106, a narrow
island near y −82, then y −52…+44. The gap is the `mctrl_floor_ports` opening the motor board
already passes through — its Z reaches **−83.9, below the floor at −78**.

### What that implies

* **The Pi can stand on the floor**: solid runs y −52…+44 directly beneath it, and its underside
  at z −62 is ~10 mm above the slab. Short posts, straightforward.
* **The motor board cannot** — it passes *through* the floor. Its cradle has to be carried by
  the floor material either side of its own port (y −130…−106, or the island at −82), or the
  port has to be re-cut around a new support.
* **The ±Y swap the user suggested is worth doing for a different reason than thickness.** The
  stacks differ by only 0.8 mm in X (15.6 vs 14.8), which is not the constraint. What matters
  is that the **Pi's band has continuous floor under it and the motor board's does not** — so
  putting the Pi where the motor board is would put the *easy* board over the hole and the
  *hard* one over solid floor. **Swap them and both get simpler**, but every harness length,
  the `mctrl_floor_ports` cut, and pi_cap's J2/J3/J4 cable runs move with them.

### The frame maths, which changes the design (2026-09-28)

`stand_pt` gives `world_z = TRAY_Z0 + STAND_DZ - (local_x - TRAY_X0)`, so **local +x runs
downward in world** and the cradle columns' `RIB_LZ` is a *local z*, i.e. they cantilever
**horizontally** off the endplate face (world x -631.3). That is exactly why the boards cannot
outlive the plate.

Converting the chassis floor into the cradle frame: **world z -72 = local x -537.00**.

| | local x span | world z span | relation to the floor |
|---|---|---|---|
| `PI_FP` | -603.00 … **-547.00** | -6.0 … -62.0 | bottom edge **10 mm above** the slab |
| `MCTRL_FP` | -598.65 … **-528.15** | -10.4 … -80.9 | **crosses** it, 8.9 mm below the top |

**So the two boards want different mounts, and neither is what I first assumed:**

1. **The motor board needs no posts at all.** It already passes through the floor plane, so a
   **slot in the floor** holds it — the chassis becomes the mount directly, which is stronger
   than any cantilever and costs only a cut.
2. **The Pi needs 10 mm of post**, floor to its bottom edge. Short and straightforward.
3. **⚠ THE ±Y SWAP IS NOT A SWAP.** The Pi is **85 mm** in Y (-50…35) and the motor **62 mm**
   (-113…-51). They cannot exchange bands — the boundary between them has to move, which drags
   every harness length, `mctrl_floor_ports`, and pi_cap's J2/J3/J4 runs with it. Worth doing
   only if something else forces it; the floor-slot finding above removes the reason that
   prompted it, because the motor board no longer needs the easy band.

### Next increment

Cut the motor board's floor slot and add the Pi's 10 mm posts into chassis_2, then stop
`keyhead_endplate` fusing `keyhead_cradles` and let the boards stand on the chassis. The
cradles' board-capturing geometry (walls, lip, M4 boss) is good and should be kept as-is —
only the column ROOT changes.

## 6. Handed to chassis scope (branner), not mine

* **LED sections 1 and 2 bridge the printed seams** at −404.9 and −207.3, so those two boards
  are captive once the chassis closes. Not an assembly blocker; a serviceability decision
  about print segmentation. (The junction-gap blocker IS fixed — see below.)
* **0.3 mm of roof gap** over the strip = rattle on a board beside a magnetic pickup. A leaf
  or foam strip settles it without a fastener.
* I edited `chassis.py` `LED_X0/LED_X1` (two constants, LED slot only) to unblock assembly.
  Flagged so it can be reassigned cleanly.

## 7. Collisions the lead sent back

* 5 V pair still one lane, 229–243 mm³ over ~78 mm — same fix as the LED feed, one lane over.
* Harness lane over the Pi, 23 pairs; `pi_cap` in 16, `pi5` in 7.
* `keyhead_endplate` ↔ `body_adapter_3`, 262.7 mm³ — **cross-scope**, body_adapter is
  brenner's. Either pull the plug latches inside the endplate envelope or hand over the
  requirement. Do not reach into their file.
* Screws through boards (`optical_pcb`, `pi5`, `keyhead_endplate`) — declare the clamp or fix
  the missing hole.
* `pickup_zplate` ↔ `wire_pickup` — must hold across the jack travel, not just the demo pose.

## Done this session

* **LED junction gap** — `led_strip.py` needed 8.0 mm and the CAD was producing 4.00 because
  `led_sections()` divided the chassis channel evenly instead of reading the board's own
  number. The board file was right: it sizes for the rail's real clear run (585.3) and the
  channel was hardcoded 17.3 mm short. Channel widened to 580.0 (−608 … −28), the gap is now
  exported and read, and an assert fails the build loudly if they ever disagree again.
* **`link_close_gaps` tuple bug** — two append sites recorded 4-tuples into a 5-tuple obstacle
  list, so the routine poisoned its own model and crashed a whole route the first time the
  reach was raised. Latent, not new.
* **`audit_board`** — now checks EVERY segment of a repair polyline (it checked only the
  first, and found 1 problem where there were 5) and separates a rule violation from
  "tight but legal".
