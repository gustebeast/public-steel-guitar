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

## ⚠ READ THIS BEFORE THE 2026-09-29 SECTIONS BELOW -- FIVE OF THEM ARE SUPERSEDED

Everything from here to the end was written across one long session, in the order the work
happened, and SOME OF IT WAS LATER DISPROVED BY MY OWN MEASUREMENTS. The wrong turns are kept
deliberately -- what was tried and why it failed is the most reusable part -- but a reader
working top-down would act on stale text. The state of each claim:

    LIVE, and the numbers reproduce:
      * the Y swap is DONE at 110 unintended against a measured pre-swap 114 (NOT the 112 in
        "THE Y SWAP IS DONE AND NET-POSITIVE", which predates two more fixes)
      * body_adapter's TOP FACE z -73.82 is the rule for that corner
      * the two disconnected USB leads, and tools/check_cable_ends.py
      * the three boards' DRC, measured with kicad-cli
      * the LED cable is an INSTALL step (INSTALL_NOTES.md section 8)
      * the stitcher runs BEFORE the fill, so a post-fill repair pass is the only place a
        reach-measuring fix can live
      * bus B's 3.20 mm is mctrl_pt's documented side-entry approximation

    SUPERSEDED -- do not act on these:
      * "THE SWAP CANNOT BE FINISHED BY PLACEMENT -- the cradle must be trimmed"  -> it WAS
        finished: the ring shallowed, the M4 left the ear, and the board placed at -41.5..20.5
      * "The 24 V TAIL is not solved: the slot fits ONE pair, and feed 2 has it"  -> RETRACTED.
        The chassis at x -588 is empty in that band; my probe envelope was reaching into
        material at -586. The tail sits at x -588.4 / z -52 and the block is CLOSED
      * "THE Y SWAP IS DONE ... 112 vs a pre-swap 114"                            -> now 110
      * "The LED cable needs a CHANNEL ... specified"                             -> IMPOSSIBLE,
        it takes all ten nut slide inserts; see the two sections after it
      * "the fix is in layout.py's stitcher -- measure reach" (in several places) -> the
        stitcher runs 140 lines BEFORE the fill and cannot measure a plane that does not exist

    THE FOUR THINGS I TRIED THAT WERE WRONG, with their measurements, are worth more than the
    fixes: dropping led_strip's stitch_nets (1 -> 3), the LED channel (ten inserts), "the
    stitcher should measure reach" (ordering), and "bus B needs mctrl_pin()" (side entry).

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

### Cluster A is CLOSED: the motor's M4 moved off the ear (2026-09-29)

    ring depth 13 -> 4 beads          nut_height_screw_1 76.17 and nut_height_insert_1 18.50 GONE,
                                      nut_slide_insert_1 236.72 -> 15.33
    M4 off the ear, beside the -Y     ALL remaining chassis_2 <-> nut_* GONE, incl. the 625.45
    screw + insert follow the hold    board_insert_0 clear
    full gate                         128 -> 121   (pre-swap baseline 114)

THE M4 IS NOW BESIDE THE BOARD'S -Y EDGE, via `pcb_hold_xy`, the same helper, arrangement and SKU
as the Pi's. It had to leave the ear: the boss under it buries an M4 insert (~8.5 mm) against a
3.6 mm budget before the nut height-adjust block, the thing it hit is a HEAT-SET INSERT for the
string-nut slide (so the obstacle cannot move), and the board cannot move either --

    clear the block   ymax < -38.91 - EAR_H/2
    clear the adapter ymin > -97.15, i.e. ymax >= -35.15 for a 62 mm board
    infeasible by 3.76 + EAR_H/2

⚠ AND THE ESCAPE HATCH IS SHUT, MEASURED: the board's dip below the adapter's top face
(z -73.82) is the FULL 62 mm. It stands vertically, so its bottom edge runs at z -83.85 along its
whole length -- there is no short plug region to slide past the adapter. That measurement is what
ruled out moving the board and sent the fix to the mounting instead.

⚠ THE EAR IS VESTIGIAL NOW. elec/motor_ctrl.py still carries EAR_* and its 4.5 mm hole, unused.
Deliberate: removing it re-opens a board at 0 unconnected / 0 violations. Drop it at the next
motor_ctrl revision, not before.

OPEN, SMALL: chassis_2 <-> board_screw_0, 0.72 mm3, y -48.30..-48.10 -- a 0.2 mm sliver on one
side of the screw's circle. A head-clearance cut at the hold point (the Pi's remedy) left it
EXACTLY unchanged, one-sided and symmetric both, so the material is CHASSIS STRUCTURE, not the
cradle, and cutting the frame cannot reach it. The cut was reverted rather than left in doing
nothing. Whoever picks it up: find which chassis feature owns the face at y -48.3, x -601.5..
-599.3, z -46.8..-44.4.

REMAINING SWAP DEBT (12 vs pre-swap 114): the 24 V feed to the motor board, 8 pairs
(wire_pwr_{hot,gnd}_{11,12} x chassis_2 and x motor_0) -- the 5 V cable's problem again, and
scratchpad/segtest.py makes it mechanical; chassis_2 <-> pi_cap 291.79 mm3 (the cap 0.37 mm past
the board's -Y edge into the wall); and three grazes (body_adapter_0 2.2, wire_link 2.8,
board_screw_0 0.72).

### The 24 V feed: the EAST approach to motor_ctrl J3 is dead (2026-09-29)

8 pairs: wire_pwr_{hot,gnd}_{11,12} against chassis_2 and motor_0. All four wires hit in the
SAME place -- x -585.6..-576.2, y 4.17..10.97, z -63.45..-29.05 -- which is the final approach
to J3, NOT the trough transit. `_feed2` already uses the trough properly (down to CHAN_Y, along
the rail at LANE_PWR2, out on a fly column at `_FEED2_X`), and that part is still fine.

⚠ ANOTHER STALE PREMISE, THE THIRD TONIGHT. `_FEED2_X = BAY_X + 4.5` carries the comment "there
is no motor at x -582 (string 1's sits far +Y), so the column is free". True when J3 sat at
y ~-100. The swap put J3 at (-591.70, 5.07, -61.55) -- inside the motor bank -- so the column
now descends through motor 0.

WHAT THE SWEEPS RULE OUT (search the site, do not choose it):
  * THE WHOLE X AXIS, at the connector's own y. A vertical column at y 10.07:
        x -600..-590   motor_ctrl (the board itself)
        x -588..-582   chassis_2  (its cradle)
        x -586..-558   motor_0    -- 28 mm of motor
    There is no clear column at any x. This is NOT fixable by retuning _FEED2_X.
  * x -584 AT EVERY Y from -46 to +23: chassis_2 blocks all of it. That x is inside chassis.

⚠ AND ONE SWEEP WAS A STRAWMAN -- do not repeat it. Testing "the x-leg from -560 to the board
face at y 10.07" was blocked at every z from -72 to -43, but that leg is 32 mm long and crosses
motor 0's whole span by construction. The real cable does not start at x -560; it leaves the
trough. A probe has to model the route the cable would actually take.

THE HYPOTHESIS FOR THE NEXT ATTEMPT, not yet tested: come through the GAP BETWEEN THE TWO
BOARDS. The Pi ends at y -50 and the motor board starts at y -42, and those 8 mm are the Pi's
M4 boss gap -- the one piece of clear y in this region. Drop there at x just east of the board
face (~-589, NOT -584), then run +Y along the board's own face to J3 at y 5.07. Test it with
scratchpad/segtest.py on the real polyline, segment by segment, BEFORE editing -- that is what
fixed the 5 V cable on the third try after two attempts that made the gate worse.

### The 24 V TAIL (_11) is not solved: the slot fits ONE pair, and feed 2 has it (2026-09-29)

feed 2 (_12) is fixed and committed -- through the gap between the boards at _GAP_X -588,
face z -58, and the gate went 121 -> 117 with nothing new. The TAIL (_11) has the same four
pairs from the same cause (it descends at xt = BAY_X +- 1 onto J3's y, through motor 0) and the
same route does NOT simply transfer:

    THE SLOT IS ~2 mm WIDE. The board's face is x -591.70 and chassis_2 starts at -588, and the
    pair spans 3.80 (PWR_OFF 1.00). One pair fits; two do not, side by side.

    x -590 / -586 / -585 all put the face run into motor_ctrl (31.2) or chassis_2 (393.8).
    Only x -588 clears structure -- and only at ONE height:

        face z -52   chassis_2 24.6 on the face, 7.3 on the drop
        face z -50   chassis_2 24.6 / 8.3
        face z -64   chassis_2 26.0 / 3.7, and the descent picks up 0.8
        face z -66   chassis_2 26.0 / 4.7
        face z -58   CLEAN of structure -- and that is where feed 2 now runs.

Stacking the tail 4 mm off feed 2 does not work either: pair 3.80 + clearance needs ~6 mm of
separation, and +-6 from -58 is -52 or -64, both of which are in the chassis.

WHAT THE TAIL WOULD TRADE, IF SOMEONE TAKES IT AS-IS: today it is motor_0 95.90 (hot) + 43.79
(gnd) and chassis_2 4.29 + 25.68. Through the gap at z -52 it becomes chassis_2 ~24.6 plus
cable grazes. Physically much better -- a 24 V pair through a MOTOR is not buildable, resting on
a cable is -- but the gate counts PAIRS, so it may not score better. That is a judgement call
about the gate's metric, not a measurement, and it is left for the user.

THE OTHER WAYS OUT, none tried: give the tail a different LANDING on J3 (it lands on the
connector's own y while feed 2 lands two pin pitches off, so they could instead share a face
line and separate only at the end); or widen the slot by moving chassis_2's wall at x -588; or
accept the tail on the far side of the board.

## THE Y SWAP IS DONE AND NET-POSITIVE (2026-09-29): 112 vs a pre-swap 114

Every pair the swap introduced is resolved except three grazes. The count is now BELOW where it
started, against a baseline measured from 991e095 rather than quoted.

    pre-swap (measured)                     114
    naive swap                              132   (+18, and the adapter conflict got WORSE)
    5 V cable under the Pi                  128
    mounting: ring depth + M4 off the ear   121   (~977 mm3 of cradle-in-hardware)
    24 V feed 2 through the gap             117
    pi_cap pocket in the -Y wall            116
    24 V tail, its own slot in the gap      112

STILL ADDED BY THE SWAP, all grazes:
    chassis_2 <-> board_screw_0   0.72 mm3  y -48.30..-48.10 -- a 0.2 mm sliver. The Pi's
        head-clearance remedy does NOT apply: a cut at the hold point left it EXACTLY unchanged,
        one-sided and symmetric both, so the face belongs to chassis structure, not the cradle.
        Find which feature owns y -48.3, x -601.5..-599.3, z -46.8..-44.4.
    chassis_2 <-> body_adapter_0  2.2 mm3   (was the 170.65 handover at the other corner)
    chassis_2 <-> wire_link       2.8 mm3

NOT THE SWAP'S, AND STILL OPEN:
    the LED cable crosses keyhead_endplate (68.2) and chassis_2 (46.5) -- PRE-EXISTING, in the
    114. It runs pi_cap J3 (y -119.72) to the strip (y +51.20), 171 mm across the instrument.
    That is a cable crossing STRUCTURE: it wants a PORT through the chassis, which belongs with
    the chassis rework, not a bent cable.

⚠ THE FOUR THINGS THAT FOOLED ME, ALL THE SAME SHAPE -- a sweeping negative that arrived cheaply:
  1. `cmd | tail -N` into a background file leaves only N lines, and check_ceilings prints
     DESCENDING -- so the tail shows the BEST spans and cuts the header. That is how "worst span
     0.80 mm" got into an MR note and into my own report. The truth is 7.70, unchanged all
     session, 200 mm from anything either of us touched.
  2. scratchpad/lanefind.py first walked src.build.PARTS -- 69 entries, containing NEITHER pi5
     NOR motor_ctrl NOR motor_0 -- and reported 585 clear lanes. Against
     src.build.collect_components() (what the gate scans) the same search returns 95.
  3. My 24 V pair probe was 6.6 mm wide: the conductor plus an INVENTED +3.6. PWR_OFF is 1.00,
     so the pair spans 3.80. That turned a tight slot into an impossible one for two ticks.
  4. "The slot fits one pair" -- the chassis at x -588 is EMPTY; my envelope was reaching into
     material at -586. Measure the OBSTACLE, not the probe's verdict.

⚠⚠ AND THE RULE THAT WOULD HAVE PREVENTED MOST OF THE SWAP'S FALLOUT: four hard-won constants
were falsified by one board moving -- root_d's 13 beads ("nothing lies in this board's y band"),
MCTRL_HOLE on the ear, the 5 V mid-plate leg, and _FEED2_X ("there is no motor at x -582").
Each was measured and documented when written. None could notice the thing it measured had
moved. DERIVE FROM THE GEOMETRY (pi_cap_relief reads pi_cap()'s own bbox; the 5 V fly height
reads pi5()'s) rather than freezing a number with a comment explaining why it is safe.

### board_screw_0's 0.72 mm3 is SOLVED, and the cause was arithmetic (2026-09-29)

The motor's M4 boss sits beside its -Y edge at y ~-48.2. The PI CRADLE'S +Y WALL lands at
-50 + CLR + WALL = -48.2. Coincident BY CONSTRUCTION -- both derive from the same 8 mm
inter-board gap -- which is why the Pi's own head-clearance remedy changed the number by
exactly zero when I tried it: the material was the Pi's cradle, not the motor's.

    _MCTRL_CY -11.0 -> -10.0     the board to y -41..21, 1.15 of room before the adapter's 21.15
    full gate                    112 -> 111,  FIXED chassis_2 <-> board_screw_0,  NEW none
    ceilings 7.70 unchanged;  one-solid assert passes;  sweep green

⚠ AND THE TICK'S "chassis_2 mounting rework (NOT STARTED)" IS STALE -- it is DONE:
  * the motor board's floor slot is cut (electronics.mctrl_floor_ports, cut in build.py)
  * the Pi has a continuous FOOT RIB, not 10 mm posts -- posts were rejected because the
    chassis prints Z-UP and two legs would have left the bottom lip spanning
  * keyhead_endplate does NOT fuse keyhead_cradles: only build.py:225 unions them, into the
    CHASSIS segment. build.py's comment still claimed "fused into keyhead_endplate now" and has
    been corrected -- a comment asserting the opposite of the design is worse than none.

REMAINING SWAP DEBT: two grazes, chassis_2 <-> body_adapter_0 (2.2) and <-> wire_link (2.8).
111 against a measured pre-swap 114.

### THE LAST 0.75 mm IS A HANDOVER, NOT A BUG (2026-09-29)

The motor board is pinned between two features that are 0.75 mm too close together, and NO
placement satisfies both:

    boss must clear the PI CRADLE'S +Y WALL, whose face is -50 + CLR + WALL = -48.2
        -> motor ymin > -42.0
    the cradle's +Y WALL must clear body_adapter_0, whose -Y face is y 21.15
        -> ymax < 19.25, i.e. ymin < -42.75

Measured at three positions (_MCTRL_CY):

    -11.0   112 pairs   body_adapter_0 2.20   wire_link 2.80   board_screw_0 0.72
    -10.0   111 pairs   body_adapter_0 5.22   wire_link 0.71   --
    -10.5   111 pairs   body_adapter_0 3.73   wire_link 1.77   --      <- taken

⚠ AND -10.0 WAS A TRADE I REPORTED AS A WIN. It dropped a pair (112 -> 111) while MORE THAN
DOUBLING the pair it left behind (2.20 -> 5.22). Reading the gate's COUNT instead of the
geometry is exactly the failure the count invites. -10.5 keeps the count and halves that back.

THE WALL CANNOT BE TRIMMED. It spans y 21.0..22.9, so cutting at the adapter's 21.15 leaves
0.15 mm of a 1.9 mm member -- and that member is one of the two side walls that run down inside
the floor slab and ROOT the cradle into the chassis. build.py's one-solid assert exists to catch
exactly the cradle those walls would stop holding.

SO: body_adapter_0 at 3.73 mm3 (x -600.60..-599.50, y 21.15..22.40, z -79.46..-75.66) needs the
ADAPTER to give about 1 mm at that corner. This is the ORIGINAL handover at 2% of its size -- the
170.65 mm3 version was retired by MOVING the board, and this residue cannot be moved away from,
because moving -Y puts the M4 back into the Pi's cradle wall.

### ⚠ THE USB LEAD TO THE PI ENDED IN OPEN AIR, AND ONLY A 1.77 mm3 GRAZE SHOWED IT (2026-09-29)

wire_link -- motor_ctrl J4 to the Pi, the lead the Pi writes travel offsets over -- had its Pi
end HARDCODED: `_lp = SP(-585.0, 20.0, -58.0)`, world y 20. Pre-swap the Pi spanned y -50..35,
so 20 was on the board. It spans -135..-50 now, so that lead terminated about 80 mm from the Pi,
in the space the Pi used to occupy. Fixed: `SP(-585.0, EL.PI_FP[3] - 9.0, -58.0)`, which is the
expression pi5() itself uses to place the USB/ethernet block. The cable now ends at y -59.7,
inside that block's -68..-50 span.  Gate 111 -> 110, FIXED chassis_2 <-> wire_link, NEW none.

⚠⚠ AND THE GATE COULD NEVER HAVE TOLD ME. check_overlaps is a COLLISION check, not a
CONNECTIVITY check: it reports two things sharing space, and has no opinion about two things
that SHOULD touch and do not. The only reason this surfaced is that the lead happened to clip a
chassis wall on its way to nowhere. Had I "fixed" that graze the way I fixed the two 24 V pairs
-- a millimetre nudge -- the result would have been a clean gate and a USB lead connected to
nothing.

THE FOLLOW-UP THIS ARGUES FOR, not done: a check that walks every cable and measures the DISTANCE
from each end to the part it terminates on. Cheap, general, and it would have caught this without
the accidental graze. The Y swap moved a board 85 mm; wire_link is unlikely to be the only lead
with a frozen endpoint, it is just the only one that left a mark.

That makes FIVE constants this swap falsified -- root_d's 13 beads, MCTRL_HOLE on the ear, the
5 V mid-plate leg, _FEED2_X, and this -- and this is the only one whose failure was SILENT.

### tools/check_cable_ends.py -- and it found a SECOND stranded lead on its first run

Built because check_overlaps is a COLLISION check with no opinion about things that SHOULD touch
and do not. It walks src.wiring.WIRE_OK (each cable -> the parts it may touch) and reports any
cable far from EVERY part it is declared to touch. Advisory, not a gate.

    wire_usb       8.10 mm from pi5     -- SP(-575.0, 20.0, -44.0), the SAME frozen y 20
    wire_link     ~80    mm from pi5     -- fixed the commit before, found only by its graze
    wire_canbl_0   3.20 mm from motor_ctrl -- PRE-EXISTING, see below

⚠ TWO LEADS TO THE PI WERE BOTH STRANDED AT ITS OLD POSITION and the overlap gate saw ONE of
them, by luck, because it clipped a wall on the way. Moving one board 85 mm silently
disconnected two cables while the gate's count went DOWN. Both now derive from
PI_FP[3] - 9.0, the expression pi5() uses to place the USB/ethernet block.

wire_canbl_0 IS NOT THE SAME BUG and is not the swap's. Bus B's start IS derived
(SP(*EL.mctrl_pt("J2"))), but both conductors are then offset +-CAN_OFF in x AND y, so the pair
straddles the connector's reference point diagonally instead of landing on pins -- canbl ends up
~3.2 mm off the board BY CONSTRUCTION. The 5 V and 24 V pairs land per-pin (pi_cap_pin,
_pin(west[k], ...)); bus B is the one that does not. Worth the same treatment, low priority.

    gate 110, pair set unchanged by the wire_usb fix.

## THE THREE BOARDS' REAL DRC STATE, MEASURED (2026-09-29)

kicad-cli pcb drc on each elec/out/*.kicad_pcb. The tick's STATE block is wrong in BOTH
directions, so these are the numbers to work from.

    pi_cap        0 unconnected   13 violations   silk_edge_clearance x13 (warnings)
    motor_ctrl    0 unconnected   30 violations   courtyards_overlap x17 (ERRORS),
                                                  silk_overlap x10 + silk_over_copper x3 (warn)
    led_strip     1 UNCONNECTED   35 violations   track_dangling x2, silk x33 (all warnings)

⚠ motor_ctrl IS BETTER THAN RECORDED. The STATE says "3 unconnected (+3V3, CANB_H, NRST), 27
violations" with copper_edge_clearance x4 and solder_mask_bridge x3 "still unexplained". It is
FULLY ROUTED -- 0 unconnected -- and NEITHER of those violation types exists on the board at
all. What is really there is 17 courtyard-overlap ERRORS (placement density, on a board that
gained the LED buck) and 13 silkscreen warnings. The unexplained pair was chasing a ghost.

⚠⚠ led_strip IS WORSE THAN RECORDED, and its 1 unconnected is DELIBERATE. A 2.0 mm GND track on
F.Cu with both ends loose, sitting in the GND zone it never joins. It reproduces exactly on a
re-run (ROUTE_REUSE_SES=1), so it is generated, not corruption. The cause is in the log:

    stitched 23 pad(s) on GND straight to the plane
    ⚠ 3 stitch via(s) landed where the plane is not: GND at 136.35,100.33, 55.35,100.33,
      95.85,100.33     -- board-local x -44.65, -4.15, 36.35, all at y -0.33, at EXACTLY
                          40.5 mm pitch, so it is a repeated per-section feature

AND elec/layout.py's own docstring says what to do about it: "this is a placement problem.
Report it, do not tidy it away." It also records that an earlier probe suggested deleting these
and was WRONG TWICE OVER -- GetPosition() is a track's START, so a track whose END lands on the
via reads as absent, and deleting the via would leave the stub and could cut the pad's only
return. DO NOT TIDY. The fix is to make the GND plane REACH those three points (or move the
pads): an led_strip layout change, pre-existing, not the swap's.

INVOCATION, because I got it wrong first: finish.py needs KICAD'S python and a PATH --
  "C:/Program Files/KiCad/10.0/bin/python.exe" elec/finish.py elec/out/led_strip
py -3.12 cannot import pcbnew, and a bare board NAME is not a path.

### led_strip's 1 unconnected, DIAGNOSED to the millimetre (2026-09-29) -- not fixed, deliberately

TWO of the three driver clusters have a GND ISLAND that never reaches the pour. The passives'
pads and their joining tracks ARE connected to each other (touch 2/1 at every end); the island
as a whole floats.

    working clusters      tracks at kicad y 91.90 / 93.50 / 95.10 / 96.90, pour at BOTH ends
    the two stranded      tracks at kicad y 100.33, pour at NEITHER end
        (56.10,100.33)->(54.10,100.33)  2.00 mm    <- the DRC's "Track [GND] ... 2.0000 mm"
        (96.60,100.33)->(94.60,100.33)  2.00 mm

    island (54.10,100.33): nearest pour 1.30 mm away at (53.99,99.03), bearing 265 deg
    island (94.60,100.33): nearest pour 0.10 mm away at (94.63,100.42), bearing  70 deg

x 55.35 and 95.85 are exactly the coordinates layout.py's own warning names, and the clusters sit
at 3 x LED_PITCH = 40.5 mm, so this is the per-driver passive cluster described at
elec/led_strip.py "tracks": the three parts' GND pads joined by one track and "hopped to the via
beside them", with the honest note that "stacked 1.6 apart with traces round them, the pour
cannot get in".

⚠ WHY I DID NOT PATCH IT. The two gaps are 1.30 and 0.10 mm, so ONE declared length cannot fix
both -- and 0.10 mm is suspicious in itself: GetFilledPolysList returns EVERY island of the zone,
connected or not, so the "pour" 0.10 mm from that cluster may be another stranded fragment rather
than the plane. Patching to it could join two islands and still leave both floating.

THE CONSTRAINTS ANY FIX MUST RESPECT, from the board's own notes:
  * NO stitching vias -- with one pour there is nothing to stitch TO; laid before routing they
    were deleted as dangling, laid after they landed on the router's own tracks.
  * pour on F.Cu ONLY -- B.Cu carries 36 cathode runs and a pour there returns as fragments.
  * elec/layout.py: "this is a placement problem. Report it, do not tidy it away", and it records
    that deleting these was WRONG TWICE OVER (GetPosition() is a track's START, so a track whose
    END lands on the via reads as absent; and deleting the via could cut the pad's only return).

SO THE FIX IS A PLACEMENT/POUR CHANGE ON led_strip, not a longer stub: give the pour a way INTO
the cluster (open a channel between the stacked passives, or move the cluster off y -0.33 to the
y band where the other clusters' tracks sit and the pour demonstrably reaches). Pre-existing, not
the swap's; the board has been through three layouts and deserves better than a guess.

#### led_strip, FULLY DIAGNOSED: the stitcher's stub, 2 mm short, and the plane is ONE island

Correcting my own note above: the stranded tracks at kicad y 100.33 are NOT elec/led_strip.py's
declared cluster tracks (those land at y 93.50 and are all connected). They are the STITCHER's
stubs -- "stitched 23 pad(s) on GND straight to the plane" -- which is why elec/layout.py's
docstring owns them.

THE POUR IS ONE ISLAND, 2089.23 mm2, x 30.80..169.20 y 88.30..111.70. No fragments. So my worry
about joining two stranded islands was unfounded: ANY contact with it connects.

Mapped along the stub's own line (# = pour, 0.25 mm per character):

    cluster A  y=100.33  x 50..60   #########......................##########
    cluster B  y=100.33  x 90..100  ##############....#..............########

    A: stub (56.10,100.33)->(54.10,100.33); pour ends at x 52.25 -- 1.85 mm short in -x,
       or 1.30 mm in -y (nearest point 53.99,99.03)
    B: stub (96.60,100.33)->(94.60,100.33); pour ends at x 93.25, AND there is a one-sample
       FINGER of pour at x 94.5 -- which is the 0.10 mm neighbour measured earlier

⚠ SO A 2 mm LONGER STUB, ALONG ITS OWN LINE, REACHES THE MAIN PLANE AT BOTH: A would land at
52.10 against pour from 52.25, B at 92.60 against pour from 93.25.

THE FIX BELONGS IN THE STITCHER, NOT THIS BOARD. layout.py lays each stub a fixed length toward
the plane; where the plane has been pushed back by local congestion the stub falls short and is
left dangling BY DESIGN ("this is a placement problem. Report it, do not tidy it away"). A
stitcher that measured the distance to the nearest plane point and either laid THAT length or
skipped the stub entirely would fix this class on every board. NOT attempted here: layout.py is
shared by every board in the fleet and a change there needs its own validation pass, not a
2 a.m. edit at the end of a long session.

#### ⚠ TESTED AND WRONG: dropping led_strip's stitch_nets makes it WORSE (1 -> 3 unconnected)

My reasoning was: the pour is F.Cu only on a 2-layer board, so a stitch via reaching B.Cu "lands
on nothing", and the board's own note says "with one pour there is nothing to stitch TO". Full
route without the stitcher:  **3 unconnected**, against 1 with it. REVERTED.

WHY IT IS WRONG. A via to B.Cu is not a connection to a plane -- it is an ESCAPE TO THE OTHER
LAYER, and the router can then reach that pad with a track. The stitcher's value on this board is
getting GND pads off the congested face, not tying them to a second pour. Removing it traded
three real connections for two dangling stubs.

AND I MISREAD THE NOTE. "No stitching vias: with one pour there is nothing to stitch TO" is about
explicit vias BETWEEN TWO POURS -- a different mechanism from the per-pad escape vias
_stitch_plane_pads lays. One mechanism's comment does not govern another.

⚠⚠ AND REVERTING THE SOURCE DOES NOT REVERT THE BOARD. elec/out/ is GITIGNORED, so
`git checkout -- elec/led_strip.py` restored the generator and left the WORSE routed
.kicad_pcb on disk. It had to be regenerated and fully re-routed (~30 min) to get back to 1
unconnected. Any experiment on a board costs that on the way out as well as in.

SO led_strip's 1 unconnected STANDS, and it is now understood rather than mysterious: two stitch
stubs fall ~2 mm short of a pour that is ONE 2089 mm2 island, the stitcher is still net +2
connections, and layout.py's instruction is to report rather than tidy. The fleet-wide fix -- a
stitcher that MEASURES reach before laying, and lays that length or skips -- is now backed by
evidence instead of my assumption, and is the right next attempt.

### The LED cable needs a CHANNEL through the height-adjust block -- specified (2026-09-29)

I opened this tick believing the cable just needed a ~1.5 mm inboard shift off the block's face.
WRONG, and the sweep says so: moving inboard is 2-3x WORSE, and the crossing is invariant in z.

    x -611.05 (as routed)  keyhead_endplate  68.2   <- the gate's own figure for this pair
    x -609.60 .. -608.00   keyhead_endplate 143..222
    z -44, -40, -34.23, -30, -26   keyhead_endplate  68.2 at EVERY height
    z -22                  keyhead_endplate 204.0

So it is a THROUGH-crossing, not a graze, and the cable is already on the least-bad line.

WHAT IT CROSSES, and the y range names it: y -38.91..33.20 is the NUT HEIGHT-ADJUST BLOCK --
the same block the motor cradle's ring had to stop short of (root_d 13 -> 4 beads) and the same
one the motor's M4 boss had to leave the ear to avoid. The cable runs 72 mm THROUGH it,
lengthwise, at x -611.75..-610.35 (the block's inboard face is x -610.1).

THE CHANNEL, sized from the bundle rather than guessed:
    x   -611.75 .. -610.35   (1.4 wide + clearance; the run sits at x -611.05)
    z   -34.93  .. -23.53    (11.4 tall: gnd_a's conductor at the bottom, sdi's at the top)
    y   -38.91  .. 33.20     (72 mm, the block's own y extent)
    and z -30 is the best height on the OTHER pair: chassis_2 drops 29.6 -> 13.4 there while
    keyhead_endplate stays 68.2, so route the run at z -30 when the channel is cut.

⚠ CHECK IT AGAINST THE INSERT SLOTS FIRST. The block is cut through by the nut height-adjust
insert slots (that is why keyhead_cradles' old columns had to be carved around them), and a
72 mm channel at this x/z may cross them. Measure before cutting -- and remember
led_wall_reliefs cut four board-sized WINDOWS through a wall of this same nominal thickness by
taking a depth that was convenient rather than the depth the part needed.

NOT ATTEMPTED TONIGHT: a 72 mm channel through a structural block is a design change, not a
tidy-up, and it belongs at the start of a tick rather than the end of a long one.

#### ⚠ AND THE CHANNEL IS IMPOSSIBLE AS SPECIFIED -- it runs through ALL TEN nut slide inserts

The check the previous note demanded, done before cutting anything. The channel
(x -612.15..-609.95, y -38.91..33.20, z -35.33..-23.13, 1935 mm3) would pass through:

        586.23 mm3   keyhead_endplate        <- intended
         97.36 mm3   nut_slide_insert_9
         74.18 mm3   nut_slide_insert_8, _7
         49.84 mm3   nut_slide_insert_0..6   <- ALL TEN, ~594 mm3 of heat-set brass

That is the string-nut height-adjust hardware for every string on the instrument. The block is
not empty material with a cable grazing it; it is FULL of the mechanism it exists to carry, and
the cable's 11.4 mm z spread (gnd_a at the bottom, sdi at the top) is what makes the channel
tall enough to catch all of them.

SO THE PORT IDEA IS DEAD AT THIS LOCATION. What is left, in rough order of cost:
  1. BUNDLE THE CONDUCTORS TIGHTER. The 11.4 mm spread comes from the strip connector's pin
     order being carried the whole 171 mm. A tighter stack (2 rows of 3, ~4 mm) would need a
     much smaller channel -- the earlier z sweep at a 1.8 mm probe showed only
     nut_slide_insert_9 (11.3) and _8 (8.6) at z -40/-44, against 49..97 for all ten here.
  2. GO ROUND THE BLOCK. It spans y -38.91..33.20 and x -630..-610.1; the cable currently
     threads its inboard face. Outboard or under is unexplored.
  3. ACCEPT IT. 68.2 + 46.5 mm3 of cable-in-structure, pre-existing, on a flexible cable that a
     real build dresses around the hardware. It has been in the 114 baseline all along.

⚠⚠ THE GENERAL LESSON, AND IT COST NOTHING TO LEARN HERE: enumerate what a proposed cut passes
through -- ALL of it, sorted -- rather than checking the one part you have in mind. I specified
this channel from the cable's own envelope and the endplate's face, both correctly measured, and
it would still have destroyed ten inserts nobody was thinking about.

#### CLOSED: the LED cable is an INSTALL step, not a geometry defect (2026-09-29)

Option 2 (go round the block) is dead too. Every position crosses keyhead_endplate:

    x -613  57.3   x -616  63.4   x -620/-625  74.3   x -631  538.7   x -634  461.1
    z -50 / -56 / -18 at the current x:  68.2 / 68.2 / 204.0

So: no channel (it would take all ten nut slide inserts), and no way round. The cable is a
FLEXIBLE six-conductor lead and the model draws it straight -- the same choice src/wiring.py
already makes for the pickup lead, whose comment says modelling a service loop "would only
invent a shape nobody has to build to".

Recorded as INSTALL_NOTES.md section 8: dress it around the block, clip it clear of the slide
inserts. The 68.2 + 46.5 mm3 stays in the gate as a known modelling artefact -- it was in the
114 baseline before the swap and it is not a defect anyone can print their way out of.

### layout.py's stray-stitch warning now reports the GAP (2026-09-29)

"landed where the plane is not" says a stitch via is stray; it never said whether the plane was
0.1 mm away or 12, and those want OPPOSITE fixes -- a longer stub versus a placement change.
Now:

    ⚠ 3 stitch via(s) landed where the plane is not: GND at 136.35,100.33 (1.30 mm away),
      GND at 55.35,100.33 (1.30 mm away), GND at 95.85,100.33 (1.30 mm away)

⚠ AND THE NUMBER CORRECTS MY OWN SCRATCHPAD MEASUREMENT. My probes reported 1.30 AND 0.10 mm;
the report says 1.30 for all three. Both are right and they measure different points -- mine
walked out from the STUB'S FREE END, the report walks from the VIA. The 0.10 was a finger of
pour reaching toward the stub's tip, not toward the via. The VIA's distance is the actionable
one, because the via is what the stitcher places: a "fix" built on my 0.10 would have come up
1.1 mm short on every one of them.

REPORT-ONLY, DELIBERATELY. The stitcher lays exactly what it laid before -- led_strip is
unchanged at 1 unconnected, pi_cap unchanged at 0/0 with no stray line at all (its pours are on
both faces). layout.py is shared by all seven boards and this session already produced one
plausible-and-wrong change on this exact board (dropping stitch_nets, 1 -> 3). A diagnostic that
hands the next attempt the deciding number is worth more than a geometry change made tired.

### ⚠ WHY THE STITCHER CANNOT "MEASURE REACH": IT RUNS BEFORE THE FILL (2026-09-29)

I proposed twice that layout.py's stitcher should measure the distance to the plane and lay that
length or skip. IT CANNOT. The order in elec/layout.py is:

    3990   _stitch_plane_pads(...)           vias placed
    4128   ZONE_FILLER(board).Fill(...)      the plane comes into existence
    4129   _check_stitches_landed(...)       strays found, and now reported with their gap

At stitch time there is NO FILL to test against. The stitcher places a via beside each pad in
the first of eight directions that clears other pads -- which is all it CAN do, because the pour
it is aiming at does not exist for another 140 lines. That is also why the docstring says "this
is a placement problem. Report it, do not tidy it away": not a shrug, an ORDERING CONSTRAINT.

SO THE REAL FIX IS A POST-FILL REPAIR PASS, not a smarter stitcher: after the fill, for each
stray via, lay a track toward the nearest filled plane point (_plane_gap already finds it and
now prints it), then REFILL and re-check. Bounded to one iteration it is contained; unbounded it
could chase its own tail, because new copper changes the fill that defines what is stray.

NOT ATTEMPTED. It needs a second fill on every board in the fleet and validation across all
seven, and this session has already produced one plausible-and-wrong change in exactly this area
(dropping led_strip's stitch_nets, 1 -> 3 unconnected). What it now has that it did not have this
morning: the gap printed inline (1.30 mm on all three of led_strip's strays), the knowledge that
the pour is ONE 2089 mm2 island so any contact connects, and proof that the stitcher is net +2
connections even leaving the strays behind.

### bus B's 3.20 mm is a DOCUMENTED modelling limit, not a defect -- and the fix is bigger (2026-09-29)

check_cable_ends flags wire_canbl_0 as 3.20 mm from motor_ctrl. I had put that down to the pair
straddling the connector point (+-CAN_OFF in x AND y, where the 5 V and 24 V pairs land per-pin).
That is only half of it, and electronics.py already says the other half:

    "⚠ J2 AND J6 ARE THE BUS-B PAIR, AND THEY ARE SIDE ENTRY (2026-09-25). ... two 4-way
     S4B-PH-SM4-TB on the board's flat +X edge -- the edge stand() maps to world -Z -- so each
     half of the lever/pedal bus unplugs DOWNWARD ... mctrl_pt's mated-height lookup only knows
     the VERTICAL parts, so what it returns for these two is the body's reach, not a seated plug."

So mctrl_pt is ALREADY approximate for J2/J6 by design, and an mctrl_pin() helper mirroring
pi_cap_pin() would inherit that approximation -- a per-pin landing on a connector point that is
itself the wrong height is not an improvement, it is a more precise wrong answer.

AND BUS B HAS TWO CONNECTORS. J2 and J6 are one half of the bus each; src/wiring.py draws from
J2 only. Whether J6's half is meant to be drawn is a separate question from the 3.20 mm.

THE REAL PREREQUISITE, then, is not mctrl_pin() -- it is teaching the mated-height lookup about
SIDE-ENTRY parts, so mctrl_pt returns a seated-plug point for J2/J6 instead of the body's reach.
Per-pin landing follows for free once that exists. Recorded rather than attempted: it touches
the helper every cable on that board reads.

STATUS: the 3.20 mm stays in check_cable_ends as a KNOWN, EXPLAINED advisory. It is not a
stranded lead -- the ones that mattered (wire_link ~80 mm, wire_usb 8.10 mm) are fixed.

### led_strip's post-fill repair, SPECIFIED by prototype -- three refinements, all measured

Prototyped OUTSIDE the pipeline (scratchpad/postfill.py, on a copy) so layout.py stayed
untouched. Three attempts, each corrected by what it measured:

  1. REPAIR THE STRAY VIAS.  Found ZERO. The stitch via that lands off-plane DOES NOT SURVIVE
     to the saved board: tidy_router_vias deletes it as dangling ("tidied 23 router via(s) --
     dangling GND" in the log). So _check_stitches_landed reports three strays mid-run and the
     final file has no vias to find. ⚠ This "passed" while the board still read 1 unconnected --
     a clean result arriving too cheaply, again.
     AND IT MOVES THE INSERTION POINT: a repair must run AFTER tidy_router_vias, not merely
     after the fill, which is what I recorded last tick.

  2. REPAIR THE ORPHANED STUBS.  Also ZERO, and for a better reason: the 2.0 mm stub touches
     other GND copper at BOTH ends (measured earlier: "touch 2/1"). It is not orphaned in
     isolation -- the whole CLUSTER is. The passives' pads and their joining tracks are
     internally connected and collectively isolated from the pour.

  3. SO IT IS A CONNECTED-COMPONENT PROBLEM, not a geometric one. No per-item test can see it,
     which is precisely why KiCad's DRC reports it and four hand-written probes did not. The
     repair must ask the CONNECTIVITY which GND items share a component with the zone, take the
     components that do not, and extend ONE member of each toward the pour (1.30 mm away, and
     the pour is ONE 2089 mm2 island so any contact connects).

THE SPEC, then, for whoever takes it:
    * run after tidy_router_vias, after the fill
    * use board connectivity (or parse kicad-cli's DRC json, which already names the item) to
      find same-net components disjoint from the zone
    * extend one member per component toward the nearest filled plane point, OVERSHOOTING by a
      track width -- landing on the fill's edge is a touch, and connectivity wants overlap
    * refill, re-check, bounded to one iteration
    * validate on all seven boards: led_strip 1 -> 0 expected, everything else unchanged

NOT LANDED IN layout.py. The prototype never reached a working repair, so there is nothing to
adopt yet -- but the three dead ends above are the expensive part and they are now paid for.
