# bronner — open work items (2026-09-28)

**Priority: optical first.** Everything else is route-downtime work.

**Status 2026-09-28 22:1x — OPTICAL IS DONE AND SUBMITTED.** Every debug feature the user
called a strict improvement is in: six bring-up pads (I2C2 SDA/SCL for the ROM bootloader,
BOOT0, and the three rails) plus per-converter `SHDNZ` isolation. 0 unconnected, 0 violations,
`audit_board` clean, SI clean, In1 web unchanged at 0.266 mm, fab rebuilt. The one item that
did not make it — the buck's power-good — is closed with measurements, not deferred.
**Now on the chassis_2 mounting rework (item 5), IN PROGRESS and passing its gates.** The
cradles are fused into the chassis, the frames are re-rooted in the floor, and the long columns
into the endplate are gone with `_slot_shadow()` and `pi_cut`.

| gate | result |
|---|---|
| `check_overlaps --only chassis,keyhead_endplate,pi5,motor_ctrl` | **0 unintended** |
| `build.py`'s new one-solid assert after the fuse | holds — the cradles really attached |
| `check_ceilings --only chassis_2` | worst span **0.80 mm**, "a ledge, not a bridge" |

**The printability question is answered.** These frames were shaped for the endplate's X-up build
and the chassis prints **Z-up**, which would have made the ring's upper member an 85.6 mm
unsupported bridge. It is cut away with the mouth — a board standing vertically is carried by the
lip under its BOTTOM edge, and its top edge needs retention, which is what the M4 is — and the
Pi's foot is one continuous rib rather than two legs so its bottom lip has no span at all.

**The full overlap gate is run: 113 unintended across the whole model, and the rework adds
none of them.** Every one is pre-existing — the 5 V pair sharing a lane (229–243 mm³), the
harness over the Pi, the screws through boards — except that one entry **changed owner**, which
is a finding in itself:

### ⚠ The lead's `keyhead_endplate ↔ body_adapter_3` was the MOTOR CRADLE, not the endplate

That pair is **gone** from the gate and `chassis_2 ↔ body_adapter_3` has appeared in its place at
**170.65 mm³**, measured at `x −615.2…−599.5, y −114.90…−97.15, z −80.85…−73.82` — which is
exactly the motor frame's −Y wall where it runs down inside the floor slab. The collision moved
with the cradle, so it was never the endplate's plug latches.

**And it cannot be fixed on my side, because the board itself is in it too:** the gate also reports
`body_adapter_3 ↔ motor_ctrl` at 0.9 mm³. The adapter occupies space the motor board needs, so
trimming my frame's wall there would delete 170 of the 171 mm³ and leave the real conflict looking
trivial — which is the same thing the `{keyhead_endplate, chassis}` allowance was doing to the
2717 mm³ lump. **Left visible and handed over**: `body_adapter_3` is brenner's part, the requirement
is "the leg/body adapter must clear x −615.2…−599.5, y ≤ −97.15 below z −73.8", and the decision is
whose geometry gives way.

Also seen, and NOT mine: `chassis_2 ↔ wire_led_{sck,sdi,gnd_b}` at 0.10 mm³ each, at x −610.4,
y 33.8…36.9 — the keyhead end, nowhere near either the restored +Y wall (y 55.55) or the new
frames. Grazes, pre-existing.

**⚠ AND A SEPARATE DEFECT FOUND AND FIXED WHILE IN THERE (user report):** `led_wall_reliefs()`
was cutting **four 140 × 25 mm windows, 12.4 mm deep through a 10.4 mm wall — 173,600 mm³** out
of the +Y rail, one per LED board. The band reached 1.0 mm outside the wall face, so it caught
each board's laminate as well as its tails; laminate and tails intersect as ONE solid and the
code pocketed that solid's **bounding box**, which is the whole board. Same trap `mctrl_floor_ports`
records one function above. And the depth was `CH.T + 2.0` through a wall of `CH.T`, against its
own docstring's "leaves about 6.5 mm of it". **The right answer here is zero reliefs**: the
strip's only connector is `S6B-PH-SM4-TB`, SMD side-entry, so nothing penetrates. 145,374 mm³ of
wall restored, and the guard is a volume ceiling because what failed was a wrong SHAPE.

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

## 1b. Item 6, converter isolation — BUILT

`Rs11`..`Rs51`: one 10k `SHDNZ` pull-up per converter, ground `Rs<k>1` pad 1 and that converter
alone drops off the I2C bus. With the per-device `SDOUT` lines already present that is complete
localization — the strongest of the four options the diagnostics doc listed, and the last
diagnostic gap on the board.

Resistors and both stubs are **post-route**, like the bring-up pads. Per cell: a 2.4 mm `SHDNZ`
stub from pin 14, and a 7.3 mm `+3V3D` run on F.Cu then B.Cu with **one** via, landing on the
`_v3_trunk` foot via. Sites and paths are searched against the finished board and verified
continuously at 0.02 mm; worst gap 0.360 mm against the 0.127 rule.

### What it cost, and every item is mechanism rather than design

1. **The old `SHDNZ` channel had to go**, and it fought back twice. Its head via went dangling,
   `tidy_router_vias` removed it, and that orphaned the B.Cu leg — **ten unconnected `+3V3D`
   items**. Keeping the via alive with a repair track was worse: it then sat in **the only
   escape from pin 14**, giving five `SHDNZ`↔`+3V3D` shorts, and no track width clears a 0.6 mm
   via 0.383 mm off the centreline.
2. **The FOOT via is not the head via.** `_v3_trunk`'s spine lands on it in every cell, so it is
   how each converter's IOVDD reaches the digital rail. It was deleted with the head for one
   edit — which would have floated all five supplies — and caught by reading `_v3_trunk`.
3. **The second stub must be searched against the first.** Mazed independently they cross.
   `lay.py` puts one down and the other is searched against a board carrying it.
4. **An 0402 is not its circumscribed circle.** As a circle the site search offered 0.090 mm of
   headroom; as a rectangle the same search found one offset legal in **all five cells at
   0.510 mm**. `padsite.py` takes `PAD_RECT="w,h"` now.
5. **Verifying one cell is not verifying five.** The first `+3V3D` path put its B.Cu leg at
   cell x −3.960, which is **0.02 mm from the `I2C2_SCL` B.Cu spine** — and in cell 0 that is
   fine, because the spine starts at y 61.269, below it. In the other four it is a short, and
   DRC said so three times. A repeated pattern is only repeated where the *surroundings* repeat;
   the path is now searched in cell **1** and checked in all five.
6. **Removing pre-laid copper is the one change that can safely reuse a routing session** — a
   route that was legal with an obstacle present stays legal once it is gone. That is what kept
   the channel removal to a 3-minute pass instead of a 30-minute route.

7. **The scratch harness drifted from `route.py`.** `trypads.py` netted ONE pad per
   reference, which is true of a test pad and false of a resistor — pad 2 came out with no net,
   so the maze read the pull-up's own land as a foreign obstacle and refused to leave it. When a
   mechanism gains a case, every copy of it needs the case.

### ⚠⚠ The obstacle model itself was wrong, and it is the biggest finding of the session

`repair_search._pads` built its pad capsules with the transform of **+a** where KiCad means
**−a** (counter-clockwise angles, y axis pointing down), so **every rotated part's pads came out
mirrored through its centre** — 456 of 982 pads on the optical board, by up to **10.65 mm**.

- On a symmetric two-pad passive it silently swaps which end carries which net. That is how it
  surfaced: `audit_board` reported fifteen problems that were each a track ending on its **own**
  pad.
- On an asymmetric part it is simply wrong, and it has been wrong for every search run through
  this file — `repair_search`, `audit_board`, and `padsite.py`.
- It is now **checked rather than argued**: `scratchpad/padtest.py` walks every real pad with
  pcbnew and asks whether a parsed capsule sits at its position with its net. Before: 456
  misplaced. After: **0 of 982 misplaced, 0 with the wrong net.**
- **Worth re-auditing the other boards** — motor_ctrl, led_strip, pi_cap, lever_sensor,
  output_panel — since their audits ran on the same broken model.

⚠ **And a correction to my own reasoning.** I rejected the shared `SHDNZ` spine partly because
it wanted 8 new vias through In1, the analog reference plane. The per-cell version needs 5. That
is better but not by much, so the honest argument for per-cell is the other one: **no long net.**
The spine wanted ~86 mm of digital line down the converter column; this is two short stubs
inside each cell.

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

## 4. pi_cap — the UI board's 14-way ribbon — BUILT, one defect open

`J5` is in: plain 1.27 mm 2×7 right-angle (LCSC C22438122) on the back face, board grown 26 → 34
on its socket edge, `+3V3` off header pin 1, and `_cap_place`'s `j1_y` moved with the placements.
The polarisation question was **decided, not waited on** — see `docs/pi-cap-ui-ribbon.md`.

⚠ **DO NOT SUBMIT: 1 unconnected GND pour island** (`Zone [GND] on B.Cu` against itself). No
signal net is open and there are 0 violations. Four diagnoses were tried and all four were wrong;
they are written down in the ribbon doc so the fifth attempt does not repeat them. The live lead:
the exact containment test says both main pours are anchored only by `C1.2`–`C4.2` and the four
declared stitch vias do **not** register inside them — so the question is why a same-net via is
not reading as connected to the pour it sits in, **not** where to put a fifth via.

⚠ **And one shared-tool hazard it exposed, currently unfixed and reverted:** dropping TWO
redundant vias in one pass degrades pcbnew's container so `GetFootprints()` returns bare proxies
and `link_close_gaps` dies on `fp.Pads()`. Casting them back does not recover it, and moving the
pass breaks `route.py`'s own rule that measurements come before removals. `elec/layout.py` and
`elec/route.py` are back at HEAD; the trigger on this board was my own badly-sited via, so the
hazard is latent again rather than fixed.

## 4b. pi_cap — the original brief (brenner)

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

### ⚠⚠ IT IS A DEFECT, NOT AN IMPROVEMENT: the motor cradle is buried in the chassis floor

Measured 2026-09-28, after the boards' real edges were computed rather than read off a note:

| | world z | against the floor (top −71.35, bottom −81.85) |
|---|---|---|
| Pi board | −6.00 … **−62.00** | bottom edge **9.35 mm ABOVE** the floor |
| motor board | −10.35 … **−80.85** | passes **through** it, stopping 1.00 mm inside the underside |

The motor cradle's ring is a tube along world X whose cross-section is the board's outline, so
it spans the board's whole z range — **including the 9.5 mm that is inside the floor slab**.
Intersecting the posed cradles with the chassis segment, with the assembly's own 15 cutters
(`mctrl_floor_ports`, `led_wall_reliefs`) already applied:

```
cradles INTERSECT the cut chassis: 2717.0 mm3
   lump 2711.0 mm3  x -626.5..-599.5  y -114.9..-49.1  z -80.9..-71.3
```

**Those two parts cannot both be printed and assembled.** It is invisible today because
`check_overlaps` allow-lists `{keyhead_endplate, chassis}` wholesale — the note on the
allowance is about the endplate *seating* on the chassis and its hold-down screw, which is a
real and intended contact. A 2.7 cm³ lump of cradle inside the floor is hiding behind it.

**So the rework below is the fix, and it also has to move the support**, because the two
reasons the cradles reach x −631.3 both disappear when they leave the endplate:

* the motor cradle is carried by a wall inside the endplate (`RIB_LZ`);
* the **Pi** cradle's columns "mostly land on the NUT HARDWARE'S BLOCK", which fills
  x −630…−610.1 — so a Pi cradle fused to the chassis instead would collide with that block,
  and `pi_cut` (the insert-slot shadow) exists only to trim the columns to fit it.

Carried from BELOW instead, neither is needed: the motor cradle's ring already reaches into the
floor, so fusing it to the chassis turns 2711 mm³ of interference into a root, and the Pi needs
**9.35 mm** of foot. The long columns then come out, and `pi_cut` with them.

### Next increment, and two things found while reading for it (2026-09-28)

1. **The motor board's floor slot already exists.** `electronics.mctrl_floor_ports()` cuts it
   and `build.py` applies it to every chassis segment — it was cut so a mated PH plug's latch
   is reachable from outside, and the board already hangs 3.10 mm proud of the underside. So
   this increment is not a cut, it is **support**: the cradle has to land on the floor material
   either side of that port (y −130…−106, or the island at −82).
2. **There is already a pattern for fusing a cradle into the chassis rather than the endplate**
   — `wiring.tee_cradles()` in `build.py`, which picks the segment by x and unions into it, then
   re-cuts the rib mortises the union filled back in. `keyhead_cradles` should go the same way:
   union into the chassis segment, and stop `keyhead_endplate` fusing it.

**The frame maths for the column root.** `_frame()` builds every column spanning local **z**
(zb → post_h), and local +z is world +x — which is why they cantilever horizontally off the
endplate face. Standing on the floor means material spanning local **x** instead, because local
+x is world −z (downward):

| | board edge (local x) | the floor top (local x) | what it needs |
|---|---|---|---|
| `PI_FP` | −547.00 | −537.00 | **10 mm of foot**, straight down |
| `MCTRL_FP` | −528.15 | −537.00 | nothing below: it already **crosses** the floor, so the floor holds it if the ring lands either side of the port |

Keep the ring, lip, wall, lean and M4 boss exactly as they are — only the root changes.

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

## The Pi/motor Y swap is APPLIED BUT NOT CLEAN (2026-09-28)

The user asked for the two boards to swap ends along Y, with a diagram. Applied in
src/electronics.py: PI_FP y -113..-28, _MCTRL_CY 11.1 (motor -19.9..42.1). The Y budget is
exact and has NO slack -- Pi 85 + 8.1 for the Pi's M4 boss (it stands BESIDE the +Y edge,
reaching 7.1 past the board) + motor 62 = 155.1 in a band of exactly 155.1.

WHAT THE SWAP WAS SUPPOSED TO BUY, AND DID NOT. The claim was that it retires the
chassis_2 <-> body_adapter_3 handover, because the motor cradle's walls run down INSIDE the
floor slab (they must: the board's bottom edge sits at the floor so its two bus-B plugs can
enter it) while the Pi's foot rib stops at FLOOR_TOP + a bead, z -72.15, clear of the
z -80.85..-73.82 conflict zone. The Pi end is indeed clean now. But THERE IS A BODY ADAPTER AT
BOTH CORNERS, and nobody checked what the motor board would meet at +Y:

    before   chassis_2 <-> body_adapter_3   170.65 mm3   + motor_ctrl <-> adapter_3   0.9 mm3
    after    chassis_2 <-> body_adapter_0   157.6  mm3   + motor_ctrl <-> adapter_0 158.3 mm3

⚠ THIS IS WORSE, NOT LATERAL. Before, the conflict was almost entirely MY PLASTIC (170.65 of
wall vs a 0.9 board graze) -- trimmable in principle. After, the two numbers are equal, which
means THE BOARD ITSELF is ~158 mm3 inside body_adapter_0. A board buried in a printed part is
not a handover; no amount of trimming the adapter fixes a part that has to occupy that space.
And Y cannot absorb it: the budget above is full to the millimetre. The fix has to come from
X, from Z, or from the adapter -- NOT from sliding the board along Y again.

THE HARNESS FOLLOWED THE ENDPOINTS BUT NOT THE ROUTE. 13 of the 15 new gate pairs are wires.
The endpoints are derived (EL.mctrl_pt("J5"), EL.pi_cap_pin("J2", n)) so they moved correctly;
what broke is the WAYPOINTS. wire_5v_* runs motor J5 -> pi_cap J2, and with those connectors
now at opposite ends the straight mid-run crosses the boards. Same for the six wire_led_*
through pi5, and wire_pwr_*/wire_canb* through chassis_2.

    check_overlaps --only chassis,keyhead_endplate,pi5,motor_ctrl   0 unintended
    check_overlaps + body_adapter                                   2 unintended (the pair above)
    check_overlaps (full)                                         128 vs 113 before = 15 new
    check_ceilings --only chassis_2         worst 0.80 mm, a ledge (unchanged by the swap)
    check_sweep                             green, 20 rotating parts

⚠ METHOD NOTE, THIS COST TIME TWICE. `py -3.12 tools/x.py | tail -N` into a background file
leaves ONLY N lines in the artefact, and grepping that truncated file for the pairs I had
moved found NOTHING -- which reads exactly like success. Keep the WHOLE output and tail it at
read time. (Same family as the pipefail lesson: verify the artefact, not the log.) Also:
check_overlaps has no --verbose, and src/build.PARTS maps name -> (function, str, str), so the
solids must be built by CALLING PARTS[name][0], not read off the tuple.

## The 5 V cable cannot be re-routed by moving one leg (2026-09-29, TWO FAILED ATTEMPTS)

After the Y swap, `wire_5v_*` (4 conductors) run through `pi5`, 48.3 mm3 each. The cause is
exact and is NOT a fly-height error:

    J5  (motor)   world (-591.70, -11.00, -27.62)
    J2  (pi_cap)  world (-591.50, -87.52, -27.45)
    pi5           x -601.60..-586.00   y -135.00..-50.00   z -62.00..-6.00

The two connectors sit at almost the same world x, and the run between them is now 76 mm of y
at that x and at z -37.45 -- mid-plate. The cable goes straight through the board.

⚠ TWO FIXES WERE TRIED AND BOTH MADE THE GATE WORSE. Baseline 132.

    attempt 1   jog outboard, x = pi5.xmax + 2.5 = -583.5        132 -> 136
                FIXED  pi5 <-> wire_5v x4
                NEW    chassis_2 <-> wire_5v x4  AND  motor_0 <-> wire_5v x4
                +X is NOT the free side: the motor bank is there.

    attempt 2   x -597.0 / z -34.0, from a lane search           132 -> 136
                FIXED  nothing
                NEW    board_screw_2 <-> wire_5v x4
                The long leg IS clear at that lane -- what still cuts the Pi is the
                TRANSVERSE segment at each end, which no lane choice fixes.

BOTH WERE REVERTED. src/wiring.py is back at the committed state and the tree is where it was.

WHAT THE MEASUREMENTS ACTUALLY SAY. There is no straight-line lane: the Pi fills z -62..-6 over
the whole run, its foot rib fills the space below it to the floor, the motor bank owns +X, and a
board screw owns the inboard lane. The cable has to use the EXISTING trough system the way
`wire_usb` does -- down into the trough at CHAN_Y, along it on a LANE_* z, and back out on a fly
column (`_rail_pts`, `BAY_X`, `BAYFLY`). That is a rewrite of the route, not a moved waypoint,
and it is the next piece of work on this cable. The same applies to the six `wire_led_*`.

⚠ scratchpad/lanefind.py WAS WRITTEN FOR THIS and is worth keeping: it sweeps a cable-sized box
along a y run against the assembly and prints every clear (x, z). One assembly build answers what
otherwise costs one 3-minute gate run per guess. ITS LIMIT, WHICH BIT ME: it iterates
`src.build.PARTS`, which is 69 solids and DOES NOT CONTAIN motor_0 -- the motor bank builds
elsewhere. A lane it calls clear can still hit a motor. Narrow with it, then let the gate rule.

⚠⚠ AND THE REAL LESSON IS THE ORDER I DID THINGS IN. I edited first and measured second, twice.
This repo already had the answer in two places -- padsite.py searches a pad site, repair_search
searches a track -- and the standing note says the router VERIFIES rather than searches. Search
the site, then edit once.

## The Y swap's REAL outstanding debt, measured against a true baseline (2026-09-29)

⚠ THE MR NOTE'S "113 unintended, ALL pre-existing" IS NOT A MEASUREMENT YOU CAN DIFF AGAINST.
A real pre-swap gate -- `git checkout 991e095 -- src/electronics.py src/wiring.py`, full
check_overlaps, restore -- gives **114**. (Note `git stash push` DOES NOTHING when the changes
are already committed: it stashes nothing, the pop then fails, and the "baseline" you just
measured is your current tree. Use `git checkout <commit> -- <paths>`.)

    pre-swap        114
    current         128   (after the 5 V fix, which took it 132 -> 128)
    swap added       18,  removed 4

REMOVED -- this is what the swap bought:
    body_adapter_3 <-> motor_ctrl        the 170.65 mm3 handover to brenner, retired
    chassis_2      <-> body_adapter_3
    pi_cap <-> wire_joy,  pi_cap <-> wire_oled

ADDED -- this is what it still owes, and it is mostly ONE problem:
    THE PI'S MOUNTING HARDWARE MOVED WITH THE BOARD AND LANDED ON CHASSIS FEATURES (7)
        chassis_2 <-> nut_slide_insert_1 / _2 / _3
        chassis_2 <-> nut_height_insert_1,  chassis_2 <-> nut_height_screw_1
        board_screw_0 <-> nut_slide_insert_2
        keyhead_endplate <-> board_insert_0
    THE CAP ITSELF NOW TOUCHES THE CHASSIS (1)
        chassis_2 <-> pi_cap
    THE 24 V FEED TO THE MOTOR BOARD IS THE 5 V PROBLEM AGAIN (8)
        wire_pwr_{hot,gnd}_{11,12} <-> chassis_2   and   <-> motor_0
        Same cause, same cure: the motor end moved, the waypoints did not. Use
        scratchpad/segtest.py, find the clear band, edit once.
    AND THE ADAPTER GRAZE (1)
        chassis_2 <-> body_adapter_0   2.2 mm3, down from 170.65 -- three orders better, but
        not zero, and it is the same corner story at the other end.
    chassis_2 <-> wire_link (1)

⚠ THE LED CABLE'S CROSSINGS ARE **PRE-EXISTING**, NOT THE SWAP'S. keyhead_endplate <-> wire_led_*
and chassis_2 <-> wire_led_* are all in the 114. The cable runs pi_cap J3 (y -119.72) to the
strip (y +51.20), 171 mm across the instrument, and segtest.py puts 68.2 mm3 in the endplate and
46.5 in chassis_2 on one segment. That is a cable crossing STRUCTURE: it wants a PORT through
the chassis, which is a chassis change and belongs with the chassis_2 mounting rework -- not a
bent cable. The swap did lengthen the run (J3 rides on pi_cap, which rides on the Pi), so the
numbers grew, but the crossings predate it.

NEXT, IN ORDER: the Pi's mounting hardware (7 + the cap = 8 pairs, one root cause, and it IS the
"chassis_2 mounting rework" backlog item), then the 24 V feed (8, a solved pattern), then the
LED port as part of the chassis work.

## THE SWAP CANNOT BE FINISHED BY PLACEMENT -- the cradle must be trimmed (2026-09-29)

Located every pair the swap added (scratchpad/pairloc.py: intersection bbox + volume against
collect_components). They are TWO clusters, not the eight-way mess the names suggest.

⚠ FIRST, A CORRECTION TO THE NOTE ABOVE: `nut_slide_insert` / `nut_height_screw` are the
STRING-NUT hardware, not the Pi's mounting parts, and what collides with them is CRADLE MATERIAL
FUSED INTO chassis_2. Moving the boards moved CHASSIS GEOMETRY into unrelated parts. Trimming
board hardware would achieve nothing.

    A. THE MOTOR CRADLE INTO THE NUT ROW   all at y +10..+22, x -630..-611
        chassis_2 <-> nut_slide_insert_2    625.45 mm3
        chassis_2 <-> nut_slide_insert_1    236.72
        chassis_2 <-> nut_height_screw_1     76.17
        chassis_2 <-> nut_slide_insert_3     22.77
        chassis_2 <-> nut_height_insert_1    18.50
        board_screw_0 <-> nut_slide_insert_2  3.18,  keyhead_endplate <-> board_insert_0 3.92,
        chassis_2 <-> wire_link               2.81

    B. THE PI CAP INTO THE CHASSIS WALL
        chassis_2 <-> pi_cap   291.79 mm3   y -135.37..-131.55
        The cap overhangs the Pi's -Y edge by 0.37 and the wall is there.

THE ARITHMETIC, AND IT DOES NOT CLOSE:
        motor cradle clear of the nut row  ->  cradle ymax < 10.65  ->  motor ymax < ~8.6
        pi_cap clear of the chassis wall   ->  Pi ymin > -131.18
        needed   Pi 85 + boss 7.1 + motor 62            = 154.1
        available                    -131.18 .. 8.6     = 139.8
        SHORT BY ~14 mm.

And the boss cannot move to the Pi's -Y edge to buy it back: that reaches y -141.6, outside
CH.Y_LO -136.75. Shifting the Pi +Y to clear the cap pushes the motor +Y one-for-one and makes
cluster A worse. The constraints are coupled; there is no placement that satisfies both.

THE FIX IS THE CRADLE, AND IT IS THE chassis_2 MOUNTING REWORK. The motor cradle spans
x -631..-598 while the board it carries is only x -606.5..-591.7 -- about 20 mm of cradle width
reaches into the nut row at its +Y end and holds nothing. Narrow the cradle's +Y end in X and
cluster A goes; cluster B then needs ~4 mm of Pi shift, which the freed budget affords.

STATUS: placement is committed and correct as far as placement can go (adapter handover retired,
170.65 -> 2.2 mm3; 5 V cable fixed, 132 -> 128). The remaining 18-pair debt is ONE piece of
chassis work plus the 24 V feed (8 pairs, the 5 V cable's solved pattern).

### The motor cradle's RING is fixed; its BOSS is a design fork (2026-09-29)

`root_d` 13 beads -> 4 (10.4 -> 3.2 mm). The comment granting 13 said "Nothing of the endplate
lies in this board's y band (-113..-51 against the height-adjust block's -38.91..+33.2), so the
depth here is free" -- TRUE WHEN WRITTEN, FALSE AFTER THE SWAP: the motor is at y -42..20 now,
inside that block. The Pi's own frame is already capped at 7 beads by exactly this rule, so the
motor is now doing what the Pi always did.

    chassis_2 <-> nut_height_screw_1     76.17  ->  GONE
    chassis_2 <-> nut_height_insert_1    18.50  ->  GONE
    chassis_2 <-> nut_slide_insert_1    236.72  ->  15.33
    full gate                              128  ->  126
    build.py's one-solid assert: still passes -- the shallower ring is STILL rooted (checked,
    because the file says those side walls ARE the root and a floating cradle is what that
    assert exists to catch).

⚠ WHAT REMAINS IS THE BOSS, AND IT CANNOT BE SHALLOWED. chassis_2 <-> nut_slide_insert_2 is
unchanged at 625.45 mm3 (y 12.89..18.40) -- that is the M4 boss, not the ring. `boss_d` is not
passed for this frame so it reaches full depth, and it MUST be deep: it buries an M4 insert,
~8.5 mm, against a 3.6 mm budget before the block. Shallowing it means no insert.

THE FORK, and none of these is free:
  1. MOVE THE EAR TO THE BOARD'S -Y EDGE. Geometrically clean -- the boss then leads into empty
     band and the shallow ring may sit inside the block. But EAR_* is in elec/motor_ctrl.py: it
     is a PCB CHANGE, so re-layout and re-route a board that is currently 0/0.
  2. SHIFT THE MOTOR -Y so the boss clears the block. The band between the adapter limit
     (-97.15) and the block edge (-38.91) is 58.2 mm for a 62 mm board. SHORT BY 3.8 mm.
  3. SOMEONE ELSE GIVES: brenner trims body_adapter_3 (the handover this swap was meant to
     retire), or the height-adjust block's y extent shrinks.

Option 1 is the only one that needs no other agent, and it is the most expensive. Not chosen
unilaterally: it re-opens a routed board, and the standing rule is that a 0/0 board is not
re-opened for convenience.
