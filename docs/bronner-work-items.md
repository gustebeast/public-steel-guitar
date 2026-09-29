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

    ⚠⚠⚠ THE LED STRIP RUNS 9.1 mm FROM THE MAGNETIC PICKUP, AND NOTHING FLAGS IT
    (measured 2026-09-29, while answering the user's question about buck noise). This is a
    LIVE DESIGN PROBLEM in the shipped layout, not a question about a proposed change.

        led_strip_0 -> pickup   385.6 mm
        led_strip_1             239.3 mm
        led_strip_2              94.8 mm
        led_strip_3               9.1 mm     <-- strip z -43.2..-19.2, pickup z -11.0

    Section 3 carries ~0.54 A of PWM-ENVELOPED current (19.5 kHz segments, plus frame-rate
    brightness changes, so the envelope is IN the audio band) in a supply loop whose area is
    the board length by the V5/GND separation -- roughly 139 x 5 = 695 mm2. As a magnetic
    dipole at 9.1 mm that is ~99,600 nT at the pickup.
    ⚠ FOR SCALE: a 24->5 V BUCK's hot loop, the thing we were worried about, is 5 mm2 and
    ~730 nT at the same distance. THE EXISTING SUPPLY LOOP IS 136x THE AGGRESSOR THE BUCK
    WOULD BE. The buck question is second-order; this is first-order and already built.

    TWO INDEPENDENT LEVERS, and they multiply (ratios are robust; the absolute nT are
    order-of-magnitude, because converting field to induced volts needs the coupling
    efficiency and the Alumitone's turns-area, and an Alumitone is a LOW-IMPEDANCE current
    loop rather than a conventional high-impedance coil):
        LEVER 1  V5 and GND as OVERLAPPING PLANES on a 4-layer section     ->  25x
                 ⚠ TRIED AND REVERTED. Set layers 4 with a solid GND on In1.Cu
                 (plane_layers In1.Cu) -- the RIGHT pair, because in JLC's 1.6 mm
                 4-layer stackup F-In1 is 0.2 mm prepreg while the In1-In2 CORE is
                 1.065, so "adjacent inner planes" would have been 5x worse than it
                 sounds. The board then would NOT ROUTE: 3 unconnected, one LED
                 cathode per driver (D2_K6/U1, D5_K7/U2, D8_K6/U3), and finish.py's
                 retry (rounds=3, which is not reachable from the CLI) did not improve
                 it. A 25x loop gain is not worth a board with unrouted nets, so this
                 is reverted and the board is back at 0 unconnected / 0 violations.
                 On 2 layers the achievable version is V5 stacked directly over the
                 GND pour -- separation = board thickness 1.6 -> 222 mm2 -> only 3.1x,
                 and it is the ROUTER's choice, not something the notes can declare.
                 ⚠ SO LEVER 2 NOW CARRIES THE NOISE CASE ALONE.
        LEVER 2  strip off the +Y rail and onto the chassis floor (user's
                 suggestion; 9.1 -> ~37 mm is only 28 mm of travel)      ->  67x
        BOTH                                                             -> 1680x, ~59 nT
    At 59 nT the strip lands an ORDER OF MAGNITUDE BELOW what a buck would add at the old
    distance -- i.e. do both and the buck question stops mattering.
    ⚠ LEVER 2 CHANGES WHERE THE LIGHT GOES. The strip currently lives in a channel on the
    +Y rail's inner face and lights the body from the side; on the floor it lights upward.
    That is a lighting-design decision for the user, not a noise one. LEVER 1 IS FREE AND
    SHOULD HAPPEN WHEREVER THE STRIP ENDS UP.
    ⚠ MY FIRST ESTIMATE ASSUMED 150 mm AND WOULD HAVE BEEN WRONG BY ~4500x, reassuringly.
    Coupling is 1/r^3; never estimate it against an assumed distance when the CAD holds the
    real one.

    NOISE IN dB, asked for directly ("how much db would you expect us to add to the pickup
    signal"). THE ONE FIGURE THAT IS DEFENSIBLE IS THE DELTA, because it is a ratio and the
    unknowns cancel:
        strip residual with both fixes   59 nT
        one local buck on the floor      11 nT
        ADDING BUCKED 24 V COSTS         20*log10(70/59) = ~1.5 dB
    The two fixes themselves are ~1700x = ~65 dB of improvement.

    ⚠ THE ABSOLUTE LEVEL IS NOT DEFENSIBLE FROM A MODEL, and the reason is worth keeping:
    induced volts go as dB/dt, so THE LIGHT'S BEHAVIOUR SETS THE NOISE, not its presence.
    Against a 150 mV signal, across coupling assumptions spanning 1%..100%:
        slow fades ~1 Hz        -104 .. -144 dB   silent
        20 Hz                    -78 .. -118 dB
        200 Hz                   -58 ..  -98 dB
        full depth at 1 kHz      -44 ..  -84 dB   audible at the pessimistic end
        the 19.5 kHz PWM carrier -18 ..  -58 dB   largest term, above the audible band
    That is a 40 dB spread, because I do not have the Alumitone's turns-area product or the
    coupling efficiency -- and an Alumitone is a LOW-IMPEDANCE SINGLE-TURN CURRENT LOOP, not
    a multi-thousand-turn coil, so the conventional-pickup model used here may not transfer.
    ⚠ SAY "adding the bucks costs ~1.5 dB" and "the fixes buy ~65 dB". DO NOT quote a single
    absolute dB figure for the LED system from this analysis.
    TWO THINGS THAT PUSH THE REAL NUMBER BELOW THE TABLE: the TLC59711's enhanced-spectrum
    PWM spreads that 19.5 kHz across 128 segments rather than leaving a tone, and a pickup
    is well past its resonance by 19.5 kHz. ONE THING THE TABLE CANNOT SEE: RF rectification
    of the buck's 1-2 MHz at the preamp input -- layout and filtering, not distance. Bench
    it with the TLC59711 sub-audio test that is already pending.

    ⚠⚠ USER ASKS, 2026-09-29 -- FOUR, IN THE ORDER GIVEN. Two done, two open. Do not lose
    the open ones: they were given while I was mid-turn on something else, which is exactly
    how an ask gets dropped.

      1. DONE -- "the retention pieces you have designed are under the 1.6mm quality bar.
         If you do go all the way to 1.6mm we still may have some inaccuracy so ideally we
         can work even larger than that". LIP and RETAIN were BOTH 1.2: under
         D.MIN_WALL_2P and not even on the bead grid. Now 3 * D.BEAD = 2.4, written as
         bead counts so they stay on-grid if the nozzle changes.

      2. DONE -- "on the +y side of the pi the retention is clipping into the pi's
         components". Measured 56.3 mm3 into pi5 along the board's WHOLE length, sitting
         1.7 mm ABOVE the laminate's top face, i.e. in component space. ⚠ NOTHING IN THE
         PROJECT COULD SEE IT: cradle-to-board contact is a DESIGNED contact, so
         check_overlaps says nothing and the render is the only witness. Raising RETAIN to
         2.4 tripled it to 194.3 -- the two asks had to land together. Fixed by subtracting
         the boards' own solids from the cradles: lip and locating wall survive (they are
         outside the footprint), only what leans OVER a board is trimmed. Now 0.0 for pi5,
         pi_cap and motor_ctrl, with all four fasteners still 0.0.

      3. OPEN -- "we should also ensure the pi wiring connections are accurate. The USB for
         example enters the pi from +x which doesn't seem like how the USB would be
         oriented". Confirmed: wire_usb lands at SP(-575.0, PI_FP[3] - 9.0, -44.0) and
         wire_link at x -585.0 -- both OUTBOARD of pi5 (x -601.60..-586.00) approaching
         the board's FACE. A Pi 5's USB and Ethernet are on a 56 mm END, not the face.
         ⚠ THE ROOT CAUSE IS THAT pi5() IS A PLAIN ENVELOPE BLOCK -- 15.60 mm thick at
         every point, no ports modelled -- so every cable to it is drawn to an invented
         point. The fix is to give the Pi its connector geometry the way board_geom gives
         the routed boards theirs, then derive the cable ends from it. ⚠ AND THERE IS A
         CONFLICT TO RESOLVE FIRST: the port end can only be +Y (the -Y end is now flush
         to the bay wall), and the gap there is 4.68 mm, which will not take a USB-A plug.

      4. OPEN -- "the wiring run for the 6 pin from the LED clips through the pi and the
         chassis, it should go +x of the pi". The gate already reports it and I read past
         it: pi5 <-> wire_led_gnd_a / v5_a / sck / v5_b / gnd_b / sdi, 2.6 mm3 EACH, plus
         chassis_2 <-> the same six at 0.1.
         ⚠ WHAT CLIPS IS THE FIRST LEG, NOT THE TRAVERSE. The long run is ALREADY outboard
         at x -607 (pi5 is -601.60..-586.00). The cable leaves the cap at x -591.5 and
         crosses the Pi's full 15.6 mm thickness to reach it. Fix that leg, not the run.
         ⚠⚠ RETRACTED, 2026-09-29. I wrote here that item 4 was BLOCKED on item 3 because
         "pi5 is a plain envelope block, 15.60 mm thick at every point, no ports modelled"
         and "the cap is entirely inside the Pi's envelope". BOTH CLAIMS ARE FALSE, and I
         reached them the same way I reached two other wrong numbers this session: I
         sampled the Pi's thickness only 0.5..6.0 mm in from the +Y edge -- every sample
         inside the USB block -- and read a uniform 15.60 as "featureless".
         SAMPLED ACROSS THE WHOLE BOARD:
              0..18 mm in from the +Y edge   15.60 = laminate + USB/Ethernet block
             20..40 mm in                     1.60 = BARE LAMINATE
             45 mm in                         4.10 = laminate + SoC
         pi5() already builds exactly that -- _board(), a 50 x 18 x 14 USB/eth block at
         y = PI_FP[3] - 9.0, and a 15 x 15 x 2.5 SoC. The ports ARE modelled, on the +Y
         END, which is where a Pi 5's ports are.
         AND THE CAP IS NOT INSIDE THE PI: at the cap's y the Pi is 1.60 thick spanning
         x -601.60..-600.00 while pi_cap spans -600.00..-589.90. ADJACENT, sharing a face.
         So item 4 was never blocked and its 2.6 mm3 per conductor is an ordinary routing
         error, fixable on its own.
         ⚠ ITEM 3 IS ALSO NARROWER THAN I SAID: the geometry is fine, the CABLE ENDPOINT is
         wrong. The USB/eth block sits at world x -600..-586, y -64.18..-46.18, z -59..-9
         with its ports facing +Y out of the board's END. wire_usb lands at x -575.0, which
         is outboard of the whole Pi (xmax -586) -- approaching the component FACE from +X
         instead of the PORT FACE from +Y. That is exactly what the user saw. Fix the
         endpoint, not the model.

         ⚠ ONE ATTEMPT MADE IT MUCH WORSE -- 109 -> 154, REVERTED. Going out to x -583,
         +Y alongside the Pi, then back -X above the motor board (z -19.05) did clear all
         six pi5 clips, and then added 51: the six conductors OVERLAPPED EACH OTHER in 15
         pairs, because every one of them used the SAME three waypoints and collapsed onto
         a single line. The per-conductor endpoints are what keep them apart, so any
         re-route has to carry a per-conductor offset the way CAN_OFF/PWR_OFF do -- the
         same lesson as the tee-to-tee trunk note about four conductors 0.3 mm apart.
         It also crossed wire_pwr_hot/gnd_11 and _12 and both bus-B conductors (24 more),
         so the return lane needs a z that clears those, not just the motor board.

      5. OPEN -- "I see wires joining the LED segments, that seems like it would lead to
         reduced LED density. Can we have connectors that connect board to board directly
         instead?" The user is right, and the penalty is bigger than the wires look:

             LED_PITCH        13.5 mm
             bare board past the end LED   15.5 each side (108 mm of LEDs on a 139 board)
             JUNCTION_GAP      8.0
             DARK SPAN AT A JUNCTION  15.5 + 8.0 + 15.5 = 39.0 mm -- 2.9x the pitch, x3

         ⚠ AND THE CONNECTORS ALREADY SET THE PITCH OF THE WHOLE STRIP. led_strip.py says
         so in as many words: "The END LED sets this, not the light -- the connector
         centroid sits _J_ANCHOR out, and its courtyard reaches 7.8 back toward the
         middle, so the last LED has to stop short of that. 14.0 overlapped both end
         courtyards." So the junction costs density twice: once as the gap, once as the
         pitch it forces on all 9 LEDs of every section.

         ⚠ A WIRE-FREE JOINT WAS TRIED AND REJECTED, and the rejection is narrower than it
         reads: "every stocked 2.54 right-angle MALE is 2.5 mm insulation height and every
         stocked right-angle FEMALE is H8.5, so their contact axes cannot line up on
         coplanar boards, and card-edge sockets take a card vertically". That rules out
         2.54 right-angle HEADERS. It does not rule out a soldered board-to-board joint.

         ⚠⚠ I PROPOSED CASTELLATED EDGES, BUTTED AND SOLDERED ACROSS THE SEAM, AND IT IS
         RULED OUT. I argued the standing rule "solder only on PCBs" positively allowed it
         because both sides are PCBs. The user corrected the rule twice in one turn:
         "can you rewrite this rule to say no hand soldering, only PCBA soldering?" and
         then, when I still had it half right, "the rule does not allow hand soldering on
         a PCB". So: NO HAND SOLDERING ANYWHERE. Only what the assembly house reflows.
         A seam soldered during instrument assembly is hand soldering whatever it joins --
         the fact that both sides are PCBs is irrelevant. Built, then reverted (the
         footprint too); the memory rule is rewritten.
         ⚠ THE LESSON: I read a permissive clause in a rule as licence for the case it did
         not cover, and the wording let me. When a rule seems to permit exactly the thing
         that is otherwise hard, check the rule rather than bank the permission.

      5b. USER, same turn: "I'm surprised they don't stock this part. Also why do we need
         6 wires? The LED strips I use only take three, ground power data."

         WHY SIX, answered from the source rather than from memory:
           * 2 of the 6 are PURE CURRENT CAPACITY, and it is a CONNECTOR limit, not physics
             -- led_strip.py: "2.2 A at full white against PH's 2 A per contact". So V5 and
             GND are doubled only because a JST-PH contact is rated 2 A. A connector with a
             higher per-contact rating makes the joint FOUR (V5, GND, SCK, SDI), and taking
             the strip's power off the section joint entirely makes it THREE.
           * 2 signals, not 1, because the TLC59711 takes a CLOCKED TWO-WIRE input. The
             user's strips need one data wire because the controller is inside each LED.

         WHY NOT A 3-WIRE ADDRESSABLE STRIP: the docstring argues it and the argument holds.
         The brief ranks quality first -- real white channel, deep bit depth, and PWM ABOVE
         THE AUDIO BAND because the strip sits in the body beside a MAGNETIC PICKUP. Every
         buyable addressable RGBW chip PWMs at 1-4 kHz (SK6812 RGBW 1.2 kHz, UCS8904B and
         SM16825E 4 kHz); the one that does all three, HD108 RGBW, is quote-only, which the
         no-quote-only-suppliers rule already forbids. So the conductor count is mostly the
         price of keeping switching noise out of the pickup.

         ⚠ THE STOCKING CLAIM IS NOT RE-VERIFIED AND THE USER IS RIGHT TO DOUBT IT. "Every
         stocked 2.54 right-angle male is 2.5 mm insulation height and every stocked
         right-angle female is H8.5" comes from an earlier session; I inherited it and
         built an argument on top without testing it. It also searched ONE narrow family --
         2.54 mm right-angle THT headers. Board-to-board MEZZANINE connectors (Hirose
         DF11/DF40, Molex SlimStack, JST board-to-board) are a different product line,
         stocked in depth, and made for exactly this joint. RE-SEARCH THE MEZZANINE FAMILY
         at 4 ways before concluding anything is unsourceable.

      5c. SEARCHED (user: "can you search to see if there is a 6 way connector that wasn't
         found last time? Also search for 4 way which have pins rated to handle the full
         current"). ⚠ THE "NOT SOURCEABLE" CLAIM IS WRONG, and the reason is instructive.

         HARWIN SAYS COPLANAR IS A SUPPORTED CONFIGURATION, in as many words: "in coplanar
         configurations, both connectors are in a horizontal orientation, where connectors
         mate edge-to-edge". M20 right-angle SOCKETS and right-angle HEADERS are the SAME
         SERIES and are designed to mate; M20 is 2.54 mm, 1 and 2 row, and stocked at RS
         and DigiKey in many way-counts including 6.
         ⚠ WHY THE OLD SEARCH MISSED IT: it compared a male from one family against a
         female from ANOTHER ("stocked RA male 2.5 mm insulation height" vs "stocked RA
         female H8.5") and concluded the axes cannot line up. Within a MATCHED SERIES they
         line up by design -- that is what a series is. The part was never missing; the
         search was looking across families instead of within one.

         4-WAY AT FULL CURRENT -- yes, but NOT on Harwin M20: its sockets are rated 2 A per
         contact, short of the 2.2 A the strip draws at full white. The 2.54 mm families
         that quote 3 A per contact are Amphenol DUBOX and BERGSTIK, and GCT BG043 (3 A,
         right-angle board-to-board). 3 A carries 2.2 A with 36 % headroom, which collapses
         the doubled rails: J_PINS becomes (V5, GND, SCK, SDI) -- FOUR ways, not six.
         Mill-Max also offers "horizontal board-to-board connections using right angle and
         Z-bend interconnects", boards "plugged in on a horizontal plane", but publishes no
         current rating on that page.

         NOT YET VERIFIED, and needed before this is a decision: (a) that Dubox/BergStik/
         BG043 offer a COPLANAR-mating RA-socket + RA-header pair, not just right-angle
         parts; (b) LCSC stock and C-numbers, since the BOM is LCSC-based; (c) the mated
         height, which sets whether the two sections stay in one channel.

      5d. ⚠ I WAS TOO HARD ON THE ORIGINAL REJECTION, AND THE LCSC CHECK IS WHY. I said the
         old search "looked across families" and that a matched series (Harwin M20, which
         does document coplanar edge-to-edge mating) proved the part sourceable. Then I
         checked LCSC, and its 2.54 mm female sockets are listed at "3 A, 8.5 mm insulation
         height" -- H8.5 is EXACTLY the figure the original note quoted. So that note was
         measuring LCSC-STOCKED GENERIC PARTS, and against those its conclusion stands: a
         generic RA male (pin axis 2.5) and a generic RA female (body 8.5) do not line up
         coplanar. My critique was right about the reasoning and wrong about the verdict.

         ⚠ AND THE SUPPLIER IS NOT A FREE CHOICE ANY MORE, which I under-weighted. Hand
         soldering is banned, so this connector must be PCBA-PLACED -- which means it must
         be in the ASSEMBLER'S library, i.e. an LCSC part for JLCPCB assembly. Harwin M20
         from DigiKey/RS is stocked, but it is not LCSC, so choosing it also chooses
         consigned-parts assembly. That is a real option with a real cost, not a free win.

         SO THE OPTIONS, honestly ranked:
           * MEZZANINE ON OVERLAPPING SECTIONS, both parts LCSC and matched: a straight
             header and a straight socket are the most reliably matched pair there is, and
             both are 3 A at 2.54. Cost: the mated height is ~8.5 mm, so section k+1 stands
             8.5 mm off section k -- a large step for a strip living in a channel. Needs a
             LOW-PROFILE mezzanine to be viable; check LCSC for 1.27 mm stacking pairs and
             their current rating, which will likely be well under 2.2 A and so force the
             power back off the joint.
           * FEWER, LONGER SECTIONS. Every junction costs 39 mm of dark span, so halving
             the count halves the loss. 580 mm exceeds a typical fab panel, so ONE board is
             out, but 2 x 290 may not be -- price it.
           * CONSIGNED HARWIN M20, coplanar by design, 2 A per contact (so the power rails
             stay doubled: 6 ways, not 4).
         ⚠ NOTE THE 4-WAY PRIZE ONLY SURVIVES AT 3 A. Harwin M20 is 2 A and cannot carry
         the 2.2 A on one contact, so "collapse the dual V5/GND" and "use the coplanar part
         that actually mates" are, on current evidence, mutually exclusive.

      5f. USER: "are there any high PWM, high bit rate WLEDs which can run at 24V?"
         SEARCHED. The closest part is UCS7624 and it FAILS on the one criterion that
         matters, in a way worth recording because the datasheet invites the mistake:
             16-bit (65535-level) greyscale   YES
             RGBW, 4-channel                  YES
             DC24V native                     YES
             "32K port refreshing frequency"  -- that is the DATA PORT rate, not PWM
             PWM FREQUENCY                    1600 Hz or 3200 Hz   <-- IN THE AUDIO BAND
         So it joins SK6812 (1.2 kHz), UCS8904B and SM16825E (4 kHz) on the same objection
         the custom strip exists to avoid: PWM switching inches from a MAGNETIC PICKUP.
         ⚠ DO NOT QUOTE THE 32K FIGURE AS PWM. It is the pixel-data refresh; the light is
         still chopped at 1.6-3.2 kHz. Any future "high frequency" addressable claim needs
         the PWM number specifically, not the refresh or the data rate.

      5g. ⚠ BUT THE 24 V IDEA IS RIGHT, JUST ONE LAYER UP -- distribute 24 V ALONG the
         strip and buck it to 5 V ON EACH SECTION. The LED/driver architecture does not
         change; only what crosses the joint does:
             now:   5 V at 2.2 A  -> 2 x V5 + 2 x GND to stay under a 2 A PH contact
             then:  24 V at ~0.51 A (11 W / 0.9 / 24) -> ONE contact, 4x headroom
         J_PINS becomes (V24, GND, SCK, SDI) -- FOUR ways, with the EXISTING connector and
         no sourcing question at all. It also answers led_strip.py's own open item ("where
         the strip's 5 V comes from"): nowhere, it is made locally.
         ⚠⚠ I CLAIMED "the switcher argument inverts in our favour -- four local bucks are
         a BETTER neighbour for the pickup". THAT WAS GLIB AND THE USER CAUGHT IT: "I was
         going to suggest the buck but I thought you had said earlier that we shouldn't
         consider that due to audio interference." They were right to check. THIS PROJECT
         ALREADY TREATS A BUCK BESIDE A MAGNETIC SENSOR AS A HAZARD, in three places:
             elec/lever_sensor.py:137  a LINEAR regulator is used INSTEAD of a buck,
                                       "the right call beside a magnetic angle sensor"
             BOM.md:596                "4 LAYERS, and not for density: the buck switches
                                       ~10 mm from a magnetic angle sensor"
             output_panel_sklib.py     "buck output inductor, SHIELDED -- it sits on the
                                       same board as a magnetic pickup's preamp"
         MY FREQUENCY ARGUMENT WAS TRUE BUT NOT THE WHOLE STORY. 1-2 MHz is indeed far
         above the audio band, but a magnetic pickup does not care about the FUNDAMENTAL --
         it couples to the INDUCTOR'S FIELD and to the ripple current loop, which is a
         magnetic loop antenna, and switching edges carry broadband harmonics that can
         intermodulate down. That is precisely why this project specifies a SHIELDED
         inductor and 4 layers where a buck cannot be avoided, and a LINEAR regulator where
         it can.
         SO THE 24 V DISTRIBUTION PLAN IS NOT FREE: it puts FOUR switching inductors along
         the +Y rail, which is where the strip lives and the pickup sits. It is viable ONLY
         with the mitigations this project already uses -- shielded inductors, a 4-layer
         section, and placement as far from the pickup as the run allows -- and the linear
         alternative is impossible here (24 -> 5 V at 0.55 A is ~10 W in a linear pass).
         Weigh that against today's arrangement, which is ONE buck at the far end and the
         doubled conductors that follow from carrying 5 V at 2.2 A down the whole strip.

      5h. USER: "does our current plan use an LED that can be PCBA'd without consignment?"
         VERIFIED AGAINST JLCPCB'S OWN PART PAGES, both YES:
             C7371891  XINGLIGHT XL-5050RGBW   PCBA type "Economic and Standard"
             C116842   TI TLC59711PWPR         PCBA type "Economic and Standard"
         So the light engine and its driver are both in the assembly library and need no
         consignment. Neither page showed a stock QUANTITY, so confirm stock at order time
         and note that an Extended part carries a per-unique-part setup fee.
         ⚠ AND THIS IS THE BAR THE CONNECTOR MUST ALSO CLEAR. The whole board is
         consignment-free today; choosing Harwin M20 for the section joint would make the
         WHOLE ASSEMBLY consigned for the sake of one part, which is a much larger cost
         than the joint. Any connector candidate must have a JLCPCB part page saying
         "Economic and Standard" (or Basic/Preferred), exactly as these two do -- that is
         now the first filter, before pitch, current or coplanarity.

      5i. USER: "the PWM is key, double check none of the PCBA options run at the high
         PWM" + "also can you include 12V in the JLC search". DONE, AND THE ANSWER IS NO --
         ONE PCBA-AVAILABLE PART DOES CLEAR THE AUDIO BAND. That contradicts the premise
         the custom strip was built on, so it is worth stating plainly.

           IC              PWM        audio band?   JLCPCB assembly part
           HD107S          26-27 kHz  ABOVE         not found in the library (unconfirmed)
           APA102          20 kHz     ABOVE   <--   C9900160678, and C2887942 (2020 pkg)
           APA107           9 kHz     inside        -
           GS8208           8 kHz max inside        12-15 V, 3-channel
           SK9822           4.7 kHz   inside        -
           UCS7624        1.6-3.2 kHz inside        -
           SK6812           1.2 kHz   inside        -
           WS2812/14/15   ~400 Hz     inside        many, incl. 12 V RGBW parts below

         12 V, PCBA-AVAILABLE, RGBW (the user's second ask):
           WS2815B-RGBW      C19188610      12 V RGBW, built-in IC
           WS2815B-RGBW-4P   C42417619      12 V RGBW
           WS2814 / WS2814C  C965562 / C22371810   12 V RGBW driver
         All of these are WS281x-family PWM, i.e. hundreds of Hz to ~2 kHz -- so 12 V buys
         a 2.4x current reduction at the joint but does NOT buy the PWM.

         ⚠ WHAT APA102 COSTS, and it is the whole brief except the PWM: it is RGB with NO
         WHITE DIE, and 8-bit per channel plus a 5-bit global current. The brief wants a
         real white channel and deep bit depth for smooth low fades. So the choice is not
         "APA102 instead" -- it is a three-way trade the user should make knowingly:
             custom TLC59711  16-bit + RGBW + ~19.5 kHz segments, 6 conductors, our board
             APA102           20 kHz + 2 wires + off-the-shelf, but RGB and 8-bit
             WS2815B-RGBW     12 V + RGBW + 2 wires, but PWM in the audio band
         ⚠ AND THE PWM FIGURES ABOVE COME FROM STRIP-VENDOR COMPARISON PAGES, NOT DATASHEETS.
         I have already been caught twice quoting a REFRESH or DATA rate as PWM (UCS7624's
         "32K", GS8208's "8 kHz max refresh"). Confirm APA102's 20 kHz from the manufacturer
         datasheet before anything is decided on it.

      5j. ⚠ THE 12 V OPTION EXISTS, IT USES THE PARTS WE ALREADY HAVE, AND THE DATASHEET
         NOW BACKS IT. User's four criteria are high PWM, deep bit depth, a white channel,
         and PCBA with no consignment. Those are properties of the PARTS (TLC59711 +
         XL-5050RGBW, both JLCPCB "Economic and Standard"), so VOLTAGE IS A TOPOLOGY
         CHOICE, not a part choice. The XL-5050RGBW has separate anodes AND cathodes per
         die, so dice can be wired IN SERIES ACROSS LEDS.

         VERIFIED against TI's datasheet, Absolute Maximum Ratings p.3 -- the number that
         was blocking this:
             Supply voltage VCC                        -0.3 .. +18 V
             Output voltage OUTR0-R3/G0-G3/B0-B3       -0.3 .. +18 V   <-- 12 V is INSIDE
             Output current (DC)                              75 mA    (we run 15 mA)
         Three dice in series is ~9.6 V of Vf, which is what makes 12 V the natural rail.

                              now (5 V, 1 die/ch)     12 V, 3 in series
             channels              144                     48
             TLC59711s              12                      4
             strip current         2.16 A                  0.72 A
             the joint        2xV5 + 2xGND + SCK + SDI   V12, GND, SCK, SDI  = FOUR WAYS
             addressability     36 LEDs                 12 groups of 3

         0.72 A is comfortably under a single 2 A PH contact, so this delivers the 4-way
         joint with NO new connector, NO consignment and NO sourcing question -- the thing
         three ticks of connector search could not find. It also cuts driver ICs 3x and the
         sink's wasted dissipation with them.
         COST: spatial resolution. 12 groups over 580 mm is ~48 mm per group against 16 mm
         now. That is near the 10-string granularity for per-string lighting but a real
         loss for fine gradients -- the user's call, and the only real question left here.
         ⚠ Absolute max is a STRESS rating, not an operating recommendation. 12 V against
         18 V is a 33 % derate, which is ordinary practice, but check the Recommended
         Operating Conditions table before committing.

      5k. ⚠ AND THE 12 V OPTION IS RULED OUT BY THE USER'S CONDITION: "I'm open to having
         groups of LEDs instead of individually addressable ones BUT ONLY IF WE KEEP THE
         SAME ADDRESSABLE LED/M DENSITY". That condition is fatal to series grouping, and
         the arithmetic is short:
             today                36 LEDs / 580 mm, each its own pixel  = 62 addressable/m
             12 V, 3 in series    12 groups / 580 mm                    = 21 addressable/m
             to hold 62/m         62 groups/m = 186 LEDs/m at 5.4 mm pitch, 3x the LEDs
                                  and 3x the power -- which defeats the entire purpose
         The only escape would be an LED with the series stack INSIDE ONE PACKAGE, so a
         package is still one pixel. SEARCHED: that is not how 12 V strips are built. The
         standard arrangement puts THREE SEPARATE 5050 PACKAGES in series per colour
         ("three red, three green, three blue... three series devices"), and no 5050 RGBW
         with separate anodes/cathodes and an internal series stack turned up.
         SO THE STRIP STAYS AT 5 V, and with it the 2.2 A that a 2 A PH contact cannot
         carry on one pin. The conductor count is not a voltage problem after all.

         WHAT SURVIVES ALL OF THIS, and it is the 5e decision unchanged: FEWER JUNCTIONS.
         It is the one lever that needs no new part, no new voltage, no consignment and
         costs NO addressable density -- 4 sections -> 2 halves the dark span from 117 mm
         to 39 mm. Every other avenue in 5a..5k either failed a rule (hand soldering), a
         spec (PWM in the audio band), sourcing (consignment) or now this density
         condition. Build that, and revisit the connector only if the remaining single
         junction still reads badly.

      5l. ⚠ THE CONNECTOR EXISTS. Searched JLCPCB's ACTUAL ASSEMBLY LIBRARY through
         yaqwsx.github.io/jlcparts (the parametric mirror of the assembly catalogue) using
         the user's Chrome extension -- which is the only way to answer this, because web
         search cannot filter by pitch x gender x current x stock.
             Board-to-Board and Backplane Connector: 452 parts in the assembly library
             ALL 452 are "Extended" -- a per-unique-part SETUP FEE, but NOT consignment
             pitches 0.35..2.54 mm; currents 300 mA..5 A; mated heights from 1.5 mm
             mounting: 401 SMD vertical, 24 SMD right angle, 6 right angle, 14 through hole

         ⚠ THE FILTER THAT MATTERS IS "ARE BOTH HALVES STOCKED", and it is what every
         earlier candidate failed. Gender counts in the library are Female 82 vs Male 26,
         so most series have only ONE half. FX23L looked ideal (0.5 mm, 3 A, 64P, stock 72,
         $1.92) and is PLUG-ONLY -- all three variants are the -P half, no socket.

         HIROSE DF40 HAS BOTH HALVES:
             DS receptacles  DF40C-10DS/-24DS/-30DS, DF40B(2.0)-12DS, DF40B-30DS,
                             DF40GL-44DS, DF40HB(4.0)-50DS, DF40TC(3.5)-30DS,
                             DF40HC(2.5)-30DS, DF40GB(3.0)-70DS
             DP headers      DF40C-20DP/-34DP/-40DP, DF40GB-70DP, DF40TC-30DP, DF40GB-48DP
         0.4 mm pitch, 300 mA per contact, stack heights 1.5..4.0 mm, Slot Type Butting.
         300 mA is under the 0.38 A joint current, so PARALLEL CONTACTS: at 70P, ~17 pins
         each on V24 and GND is 5 A of margin, with the rest for SCK/SDI. 70P in two rows
         is ~14 mm long on a 139 mm board.
      5m. ⚠⚠ AND THE STOCK CHECK KILLS IT. The user asked "what's the stock like for that
         DF40" and the answer retires the recommendation I had just made:

             pins   socket (DS)              header (DP)
             10P    1,000                    --
             12P    198 / 24 / 13            --
             20P    --                       132
             24P    805                      --
             30P    15,099 / 984 / 84        5
             34P    --                       27
             40P    --                       121
             48P    --                       692
             70P    184                      4      <-- the pair I recommended
             100P   1                        --

         THERE IS NO DF40 PIN COUNT WHERE BOTH HALVES HAVE USABLE STOCK. 70P is the only
         matched count and its HEADER has FOUR units; we need three per instrument. Every
         other count has one half and not the other.

         ⚠ THIS IS STRUCTURAL, NOT BAD LUCK, AND IT IS THE FOURTH CANDIDATE TO DIE THE SAME
         WAY. The library's gender split is Female 82 vs Male 26 across all 452
         board-to-board parts: JLCPCB stocks SOCKETS far more than HEADERS, because most of
         its customers mate a board to a module that already carries the other half. A
         board-to-board pair where WE supply both halves is exactly the case the library is
         worst at. FX23L was plug-only; DF40 is socket-rich and header-poor; Harwin was not
         in the library at all; the "1.27 mm 2X10P" was a DC3 ribbon header.
         ⚠ SO CHECK BOTH HALVES' STOCK FIRST, BEFORE pitch, current, height or coplanarity.
         That one filter would have retired all four candidates in minutes.

         WHAT THIS MEANS FOR THE DESIGN: a direct board-to-board mate is not reliably
         sourceable from the assembly library at any voltage, so 24 V does not rescue it --
         24 V solves the CURRENT problem (0.38 A vs 2.2 A) and that was never the binding
         one. FEWER JUNCTIONS (5e) remains the robust answer, and it needs no part at all.

      5e. DECISION, so this stops consuming ticks: FEWER JUNCTIONS FIRST, better connector
         second. Three ticks of sourcing have produced no part that satisfies all of
         (coplanar OR low-profile) + (LCSC/JLCPCB so it can be PCBA-placed) + (>= 2.2 A or
         power off the joint). The JLCPCB 1.27 mm "2X10P" that looked promising is a DC3
         RIBBON header -- it mates to a cable, so it reintroduces the wire it was meant to
         remove.
         Meanwhile the arithmetic is unarguable: each junction costs 39 mm of dark span, so
         HALVING THE JUNCTION COUNT BUYS MORE THAN ANY CONNECTOR CHOICE DOES. 4 sections =
         3 junctions = 117 mm of dark. 2 sections = 1 junction = 39 mm. That is a 2/3
         improvement using the EXISTING part, with no sourcing risk, no rule to re-read and
         nothing consigned.
         ⚠ IT IS NOT FREE and the cost is on the board, not the joint: a 290 mm section
         carries ~19 LEDs on 6 TLC59711s instead of 9 on 3, so the per-section current
         doubles and the 2 A PH contact limit gets worse, not better -- the doubled V5/GND
         stays and may need trebling. Price that against the panel saving before building.
         The sectioning rationale was never electrical: "each small enough to share the
         panel with the tee and sensor boards". That is a cost optimisation, and 117 mm of
         dark strip is a strange price to pay for it.

         STILL TO SOLVE, with the corrected constraint. The joint must be a CONNECTOR the
         assembly house reflows onto each board, mating board to board with no wire. The
         2.54 right-angle HEADER rejection stands (male 2.5 mm insulation height vs female
         H8.5 -- contact axes that cannot line up coplanar). Candidates not yet costed:
           * a MEZZANINE pair with the sections OVERLAPPING rather than butting -- male
             reflowed on section k's top, female on k+1's underside. Both are PCBA parts,
             the joint is a plug, and the overlap can be as short as the connector. It puts
             a board-thickness step in the strip, which the channel may or may not take.
           * ONE board for the whole 580 mm run, which deletes the problem outright. The
             only reason for sections is panel sharing with the tee and sensor boards, so
             this is a panel-cost question, not an electrical one -- worth pricing before
             designing around it.
         It removes the junction gap AND the end courtyard, so the end LEDs can move out
         and the seam can fall mid-pitch: 6.75 + ~0.5 + 6.75 = 14.0, one pitch, uniform.
         Cost: the sections stop being separable by hand (18 solder joints over 3 seams).
         (The sectioning rationale still holds and is useful for whatever replaces it:
         led_strip.py's WHY SECTIONS note says the boards exist so each "can share the
         panel with the tee and sensor boards" -- panel economics, not serviceability.)

    LIVE, and the numbers reproduce:
      * ⚠ SOLVED: motor_ctrl's M4 was buried in the PI's CRADLE, not its own. Its boss
        stands beside the motor board's -Y edge at y -44.0; the Pi's cradle wall stands at
        y -44.28 (the Pi's edge -46.18 plus CLR + WALL), and the overlap's far boundary
        measured -44.28 to the millimetre. Clearance now cut in the TRAY frame, where both
        cradles are already placed, sized on the BUTTON HEAD (at the insert's diameter the
        head still clipped 1.8 mm3). insert 30.4 -> 0.0, screw 47.6 -> 0.0.
        ⚠ IT WAS A BUILD DEFECT, NOT A GATE NUMBER: an M4 boss inside another part's
        cradle has no hole for its heat-set, so the board could not have been mounted.
        ⚠ THE LESSON, AND IT COST FIVE ATTEMPTS: every one of those was a correct
        measurement of the WRONG SOLID. Cutting the motor's own frame at its own hold
        point did nothing in EITHER z direction, while a head cut on that same frame DID
        help -- both true at once, because the two fasteners were never in one solid.
        boss_d, an insert pocket, and single-sourcing the hold point were all irrelevant,
        and instrumenting pcb_hold_xy proved both call sites return an identical
        (17.0, -33.5). What settled it was refusing to reason about the local frame any
        further: cut a O20 MARKER at the hold point, measure where the void lands, and
        notice the material runs to y -52 -- far past anything the motor owns.
        WHEN A FRAME LOOKS INCOHERENT, SUSPECT TWO SOLIDS BEFORE SUSPECTING THE FRAME.
      * ⚠ THE PI IS FLUSH TO THE BAY WALL and pi_cap_relief is DELETED (user, 2026-09-29:
        the Pi "requires cutting into the chassis wall which reduces its strength"). +3.82,
        cap face measured ON -131.55 at +0.00, wall back to its full 10.40. MEASURE THE
        STACK NOT THE BOARD: the cap overhangs the laminate 0.37, so the board's own 3.45
        would have left it proud and still needing a relief.
      * The Pi's M4 was CLIPPING the Pi -- gate confirms pi5 <-> board_screw_2 is gone. It
        is on the board's UNDERSIDE, not the +Z face the user suggested: the deck covers
        that edge end to end, 1.3 mm3 into top_plate_5 at EVERY hold.
      * The motor board CANNOT move +Y: 0.65 mm to body_adapter_0, which re-opens the
        retired handover. It did not need to -- clearing both screws out of the inter-board
        gap freed the room on its own.
      * MCTRL_HOLD / PI_HOLD single-source the hold point. keyhead_cradles BORES the anchor
        and board_screws DRAWS the screw and each had its own literal edge; moving one gave
        four chassis_2 overlaps, fasteners in unbored cradle.
      * WIRE_OK's bus-B entry is ALREADY FIXED (9303bd5) -- {motor_ctrl, kl_pcb}. Gate 110
        unchanged, so tee_pcb was absorbing nothing. A tick prompt still lists it as next.
      * IN FLIGHT: the motor board's EAR IS REMOVED. It was not merely a spare hole -- it
        made the board 70.50 wide instead of 61.80 and electronics.py hands THAT width to
        pcb_hold_xy, so every hold point was computed against a rectangle the laminate does
        not occupy. _MCTRL_CX now anchors on MCTRL_FLOOR_EDGE_X so the bottom edge stays on
        the floor when the width changes. Routing now; the motor screw's final home depends
        on it.
      * OPTICAL (2026-09-29 tick): item 6 was ALREADY BUILT; the board measures 0
        unconnected / 0 unexpected. Its 21 courtyard errors are all DECLARED and reasoned
        (20 sensor triplets + TP8/R30). But optical_declared's OWN measurements were all
        three wrong, and it is the thing that stops DRC reporting them: it claimed bodies
        clear by 0.350 when they ABUT by 0.035. Copper clears by 0.475, not the claimed
        0.200, so the board is buildable and the 35 um is an accepted assembly note --
        PD_DY cannot widen. Corrected in place; see the commit.
      * chassis_2 mounting rework is DONE, not "NOT STARTED": mctrl_floor_ports is cut in
        build.py, the posts are POST_H/MCTRL_POST_H, and keyhead_cradles fuses into the
        CHASSIS SEGMENT rather than the endplate. That was the Y-swap work.
      * the Y swap is DONE at 110 unintended against a measured pre-swap 114 (NOT the 112 in
        "THE Y SWAP IS DONE AND NET-POSITIVE", which predates two more fixes)
      * body_adapter's TOP FACE z -73.82 is the rule for that corner
      * the two disconnected USB leads, and tools/check_cable_ends.py
      * the three boards' DRC, measured with kicad-cli
      * the LED cable is an INSTALL step (INSTALL_NOTES.md section 8)
      * the stitcher runs BEFORE the fill, so a post-fill repair pass is the only place a
        reach-measuring fix can live -- BUILT AND LANDED, elec/repair_planes.py, run by
        finish.py after each route.py. led_strip 1 unconnected -> 0/0; the other seven
        boards are byte-identical after running the stage against each. It had to become
        its own SCRIPT: at layout.py's pour it printed nothing (that pour runs during
        PLACEMENT, no tracks exist yet), and at the end of route.py it RAISED, because
        drop_degenerate's board.Remove() leaves the whole interpreter handing back raw
        SwigPyObjects -- a fresh LoadBoard in that process had no BuildConnectivity
      * motor_ctrl's 17 courtyard overlaps are FIXED -- 0 violations of any kind at
        placement. Two findings came out of it: D6/D7 are USB ESD clamps that sat 53 mm
        from the connector they protect, and the crystal Y1 does not FIT anywhere on the
        +X half (every corridor there is 3.37..3.46 mm against its 3.59). See the commit
      * bus B's side entry is FIXED. board_geom.lead_exit() now answers "where does a lead
        leave this connector", because board_geom is the module that already knows a
        side-entry plug leaves through the board EDGE (it grows the solid that way for
        _SIDE_PLUG_RUN). mctrl_pt delegates to it: the four VERTICAL connectors come back
        bit-identical, J2/J6 move 7.45 mm out to a seated plug instead of a point inside
        the socket.
      * ⚠ AND THE LEVER CABLE WAS ON THE WRONG CONNECTOR. elec/motor_ctrl.py has called
        J2 "bus B IN -- from the pedals at the leg" and J6 "bus B OUT -- to the lever
        chain" since the 8-way PH was split in two on 2026-09-25, but wiring.py drew the
        run to the KNEE LEVERS out of J2. Now J6. Nothing could catch this:
        check_cable_ends asks whether an end reaches its PART, and J2 and J6 are the same
        part -- the same blind spot as the two disconnected USB leads, one level finer.
      * ⚠ NEXT TICK, FIRST ITEM: WIRE_OK declares wire_canbh/canbl as touching
        {motor_ctrl, tee_pcb}, and BUS B HAS NO TEES AT ALL -- that is the header comment
        four lines above it. The true far end is the LKL lever board (kl_pcb), which the
        trunk deliberately stops a few mm short of (a chassis follow-up, see _KNEE_B).
        So the destination end is declared against a part that is not on the path and
        NOT declared against the one that is. check_cable_ends still passes because it
        only flags a cable far from EVERY declared part and the motor_ctrl end is right
        -- a cable can be half wrong and read clean. WIRE_OK is ALSO the overlap gate's
        allow-list ("everything else a wire grazes is a routing bug"), so correcting it
        may surface grazes that tee_pcb has been absorbing. Do it on its own, with its
        own gate run, NOT folded into another change.
      * STILL OPEN: bus B's PEDAL half (J2, leg -> controller) is not drawn at all. It
        lands at the TRRS adapter station, which is PARKED pending the respin; when that
        un-parks, its cable starts at EL.mctrl_pt("J2").

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

### THE POST-FILL REPAIR WORKS -- AND AS WRITTEN IT SHORTS THE BOARD (2026-09-29)

Prototyped end to end on a COPY (scratchpad/repair.py); elec/layout.py untouched.

    detector   connectivity, UUID-keyed:  2 loose GND tracks, matching DRC's 1 unconnected
    repair     extend from whichever END is nearer the plane, overshooting by a track width
    result     2 loose -> 0,  and kicad-cli agrees: 1 unconnected -> 0

    ⚠ BUT THE VIOLATIONS MOVED:  track_dangling 2 -> 1  AND  tracks_crossing 0 -> 1.
    tracks_crossing is two DIFFERENT NETS crossing -- A SHORT. Strictly worse than a floating
    GND stub. One of the two repair tracks (1.60 mm from 54.10,100.33 or 1.35 mm from
    56.64,100.33) runs straight across another net's copper.

SO THE SPEC IS COMPLETE AND IT HAS THREE PARTS, NOT TWO:
  1. DETECT by connectivity -- ask which same-net items share a component with the zone, and key
     on m_Uuid.AsString(). NEVER id(): SWIG returns a fresh wrapper per call, so id() never
     matches and every item reads as disconnected (that mistake reported 52 loose items here,
     against DRC's 1).
  2. CLEAR THE PATH FIRST -- sample from the loose end to the target plane point and abandon the
     repair if any sample lands in another net's copper, or on its clearance. THIS IS THE STEP
     THE PROTOTYPE LACKS AND IT IS WHY IT SHORTS. Try the other end, or the next-nearest plane
     point, before giving up.
  3. LAY, OVERSHOOTING BY A TRACK WIDTH (landing on the fill's edge is a touch; connectivity
     wants overlap), then refill and re-check, bounded to one iteration.

AND IT RUNS AFTER tidy_router_vias, not merely after the fill -- the stray VIA is deleted by
then, and what survives is the orphaned stub.

⚠⚠ NOTHING ADOPTED. A change that trades an unconnected stub for a SHORT is not an improvement,
and I am not landing one in a file seven boards share. But the expensive parts are now paid for:
the detector is proven against DRC, the failure mode of the naive repair is known and named, and
what is missing is one clearance walk.

### ✅ THE POST-FILL REPAIR IS PROVEN ON led_strip: 1 unconnected -> 0, ZERO ERRORS (2026-09-29)

The clearance walk was the missing piece, and with it the design is demonstrated end to end on a
real board (prototype run on a COPY; elec/layout.py still untouched).

    before                     1 unconnected   35 violations (track_dangling 2 + silk 33)
    naive repair (no clearance) 0 unconnected   AND tracks_crossing 1 -- A SHORT, rejected
    with the clearance walk     0 unconnected   0 ERRORS, violations {track_dangling 2, silk 33}

    "no CLEAR path to the plane from either end -- left alone"      <- one track, correctly DECLINED
    "from (56.64,100.33): laid 1.35 mm, path CLEAR"                 <- the other, and since both
                                                                       are ONE cluster, that single
                                                                       track connected all of it

⚠ THE DECLINE IS THE POINT, not a limitation. A pass that refuses when it cannot prove the route
is the only kind safe to run unattended across seven boards -- and it re-reads layout.py's
"report it, do not tidy it away" as sound engineering rather than resignation: tidying is safe
only when the path is proven.

⚠⚠ track_dangling STAYS AT 2 AND THAT IS CORRECT. The stubs still have loose ENDS; they are no
longer ISOLATED. A warning about a stub's shape is not an unconnected net, and the number to
watch is unconnected (1 -> 0) and errors (0).

THE DESIGN, every parameter now measured:
    run AFTER tidy_router_vias and after ZONE_FILLER (the stray via is already deleted by then;
        what survives is the orphaned stub)
    DETECT   conn.GetConnectedItems(zone), keyed on m_Uuid.AsString() -- NEVER id(), SWIG hands
             back a fresh wrapper per call and that reported 52 loose against DRC's 1
    TARGET   plane candidates nearest-first, so a blocked path tries the next
    CLEAR    sample the straight run at 0.1 mm and reject if any sample sits in another net's
             copper; try the other end, then the next candidate; DECLINE if none is clear
    LAY      overshoot the fill edge by a track width (landing on it is a touch; connectivity
             wants overlap), then refill and re-check, one iteration

STILL NOT LANDED IN layout.py, and that is the only thing left: it needs validating on the other
six boards (optical, motor_ctrl, pi_cap, lever_sensor, can_tee, output_panel) -- each should be
unchanged, since none of them reports a stray stitch today. The prototype is kept as
scratchpad_postfill_repair.py so the next session adopts a DEMONSTRATED design rather than a
described one.

### 5n. ⚠⚠ THE CONNECTOR WAS SOLVED ALL ALONG, AND I SEARCHED THE WRONG FAMILY (2026-09-29, user)

The user asked "have you considered a variety of direct connection connector types? For
example pogo pins" and then "there's also the pin connectors used on the pi". Both land,
and together they retire five sections of investigation above (5a-5m).

**I FILTERED ON MEZZANINE VIRTUES FOR A JOINT THAT HAS NO MEZZANINE CONSTRAINTS.** Every
candidate I chased -- DF40, FX23L, Harwin M20, the "1.27 mm 2X10P" -- was a FINE-PITCH
LOW-PROFILE part, and I ranked them on pitch, stack height and coplanarity. The LED strip
has 20.0 mm of board width to spend and sits in a printed channel with no height ceiling.
I was optimising constraints we do not have, and the one we DO have -- both halves in
stock -- I checked last, four times.

**THE PI'S OWN FAMILY: 0.1 in (2.54 mm) PIN HEADER + FEMALE RECEPTACLE.** Measured on
jlcparts 2026-09-29, 1x6P, gold, 3 A/pin, Extended (setup fee, NO consignment):

        half     LCSC        part                    stock    $/unit
        male     C7501264    ZX-PZ2.54-1-6PZZ        10031    0.031
        male     C18078203   BX-PZ2.54-1-6PZZ         5763    0.032
        male     C17702637   DZ254S-11-06-50          2734    0.069   <- SMD, vertical
        female   C7500775    FH2.54-09-06PZD          2141    0.153
        female   C7509518    DS1023-1x6SF11            428    0.057

A mated pair is ~$0.18 and there are >2000 of them. DF40's matched pin count had FOUR.
6 x 2.54 = 15.24 mm across a 20.0 mm board -- it fits with 2.38 mm each side.

**AND IT RETIRES THE CURRENT ARGUMENT COMPLETELY.** 3 A per pin at 5 V means a section's
2.2 A passes on a SINGLE pin, no doubling, no 4-way collapse. So 24 V was never needed
for the connector either -- 5 A pogo singles say the same. The whole 24 V thread (5g-5m)
was solving a problem the coarse-pitch part does not have.

**POGO PINS: 69 parts, and the gender problem does not exist.** All are 1P SINGLES (gold,
50 mOhm, 10k cycles, Extended), so THE PITCH IS OURS -- there is no connector body to
source, we place N pins wherever we want them. Current runs 1 A to 5 A:

        C7471680   YZP0561-23061-01   5 A   500 stock   $0.539
        C7471708   YZP0521-22075-01   5 A   490 stock   $0.851
        C7471715   YZP0334-30082-01   4 A   147 stock   $0.559
        C7471672   YZ85915058P-03     3 A   483 stock   $0.548

⚠ AND POGO IS THE ONLY CANDIDATE THAT SUITS THIS JOINT MECHANICALLY. Two rigid boards
butted in a PRINTED channel will never be coplanar to a mezzanine part's tolerance; a
pogo pin has 1.3-12 mm of travel and absorbs it. That is a reason to prefer it, not just
availability. It needs a feature that holds the joint COMPRESSED -- which is the channel,
geometry we already own.

**THE ONE REAL COST, AND IT IS A FEE NOT A WALL.** A vertical mate needs a part on the
two FACING surfaces, so one board carries a part on its bottom face. Per the panel rule
(memory UPDATE 5) that is billed "Both Sides": +$25.75 setup plus a $16.54 fixture per
order, and it forces Standard PCBA over Economic. ~$42 ONE-TIME against the whole order,
not per board. Right-angle parts would keep everything on one face but both genders are
thin (C18214186 male 21, C6825574 female 28) -- do not build on those.

**OTHER DIRECT-MATE FAMILIES, for the record, none yet searched:**
  * CARD EDGE -- the board's own edge IS the male half, so one side costs no part at all.
    Needs gold fingers, which the HASL panel cannot give (same blocker as bare pogo pads).
  * STAMPED SPRING / battery-contact fingers -- single-gender like pogo, presses a pad.
  * SOLDERLESS LED STRIP CLIPS -- a mechanical push-on part, nothing soldered at all, so
    it satisfies the no-hand-solder rule trivially. Sold for flex strip; rigid-PCB fit
    unverified, and it is not a PCBA part.

**WHAT THIS DOES TO 5e.** Fewer junctions is still worth doing on LIGHT (dark span
117 -> 39 mm), but it is no longer the ONLY answer, and it is no longer forced. A
2.54 header pair or a pogo set makes the 4-section strip mate board-to-board directly at
~$0.20 a joint, which is what the user asked for in the first place.

**RULE, and it is the same shape as the stock rule from 5m:** ask what the joint's real
constraints ARE before picking a connector family. A fine-pitch mezzanine part is the
answer to "no room and no height"; this joint has both.

### ASK #3 (USB ORIENTATION) IS BUILT -- and the note that diagnosed it read the frame wrong

**⚠ CORRECTION FIRST. Item 3 above says wire_usb "lands at x -575.0, which is outboard of
the whole Pi (xmax -586)". THAT IS A TRAY COORDINATE READ AS A WORLD ONE.** stand_pt's
three arguments are tray (x, y, z) and it returns world (z - 543.8, y, -609 - x), so
SP(-575.0, PI_FP[3] - 9.0, -44.0) is world **(-587.8, -55.18, -34.0)** -- 1.8 mm INSIDE
the USB/ethernet block's outer face at x -586, not outboard of anything. The lead ran in
along world x at z -15 straight through the block's interior and stopped in the middle of
it. The user's observation ("enters the pi from +x") was exactly right; the sentence I
wrote under it was not. Never read stand_pt's first argument as a world x.

**THE PORTS ARE NOW MODELLED AND THE LEADS ARE DERIVED FROM THEM.** `EL.pi_port_pt(which)`
returns the tray point of a port mouth on the Pi's +Y end -- the end pi5() already builds
the 50 x 18 x 14 block on, and the end a real Pi 5's ports are on:

        PI_PORT_Z  = BOARD_Z + BD_T + 7.0     mid-block, world x -593.0
        PI_PORT_IN = 1.0                      1 mm inside the face, so the lead CONTACTS
        PI_PORTS   = eth -594.0  usb3 -576.0  usb2 -560.0     tray x
        -> world z -15.0 / -33.0 / -49.0, all inside the block's -59..-9

wire_usb takes "usb3", wire_link takes "usb2" -- 16 mm apart in z, so they cannot collapse
onto each other the way the six LED conductors did. Both approach from **+Y**, the only
direction a USB-A plug can enter, via _PORT_APR = PI_FP[3] + 8.0 (world y -38.18, mid-gap).

**AND THE REAL BLOCKER WAS NOT THE ENDPOINT AT ALL: THERE WAS NO ROOM TO PLUG IN.**
Measured pi5 ymax -46.18 against motor_ctrl ymin -41.50 = **4.68 mm**. A USB-A plug's
overmould needs ~10 mm of Y beyond the port face even right-angled and ~22 straight, so
nothing plugged into that Pi at all -- a defect no gate could see, because a cable ending
in air is not an overlap.
⚠ AND THE 5.7 mm OF CLEAR HEIGHT IS NOT A WAY OUT: motor_ctrl spans world x
-606.50..-591.70 and the block -600..-586, so the top 5.7 mm of the port face does have
open +Y air above the motor board -- but a USB-A plug body is 8-12 mm tall and does not
fit in 5.7. Placement was the only fix.

**⚠⚠ AND THE BAND CANNOT BE OPENED -- I TRIED, AND IT COST 5 CONFLICTS. RETRACTED
BELOW.** I first read the Y-budget note as holding 8.1 mm for the Pi's +Y M4 boss, reclaimable
now that PI_HOLD is ("+x", 0.0), and moved _MCTRL_CY -10.5 -> -0.5. The gate went 110 -> 115
and every new conflict was mine: motor_ctrl into **body_adapter_0, 91.41 mm3** (brenner's part,
and the exact conflict the Y swap was done to retire) plus 4.0 mm3 into each of the four 5 V
conductors. Reverted.

**THE MEASUREMENT THAT SETTLES IT:** body_adapter(-X,+Y) spans **y 21.15..65.95**, so with the
motor board's +Y edge at 20.50 there was **0.65 mm** of slack above it -- not 8.1.

        band     body_adapter inner 21.15 down to the Pi's -Y face -131.18    152.33
        boards   Pi 85.00 + motor 62.00                                       147.00
        SLACK                                                                   5.33

5.33 mm is the WHOLE budget and it is already spent -- 4.68 between the boards, 0.65 above.
So the maximum inter-board gap achievable by placement is 5.33, and a right-angle USB-A plug
needs ~10. **Nothing can be plugged into this Pi, and no nudge fixes it.** The Y-budget note
is right that the band is exact; what is wrong in it is the idea that the 8.1 was ever
reclaimable. The adapter caps the other end.
⚠ RULE, and it replaces the one I wrote two paragraphs ago: when a datum's comment says a
gap exists FOR something, check BOTH ends of the band before spending it. I checked that the
boss had left and not that anything else had arrived.

**WHAT IS BUILT, AND IT IS STILL WORTH HAVING.** The leads now end at real ports, approached
from the only direction a plug could enter, in a gap no plug fits. That is strictly better
than a lead buried inside the block -- the defect is now WHERE THE DEFECT IS, in placement,
instead of hidden in a cable endpoint. _PORT_APR = PI_FP[3] + 2.3 runs inside the real 4.68.

**GATE: 110 -> 109, and body_adapter_0 <-> motor_ctrl is GONE.** The port retarget is net
-1 with no regressions -- one lead that used to graze now does not. The four
motor_ctrl <-> wire_5v_* at 4.0 mm3 each survive from the baseline and are NOT from this
change (_board_gap_y is (PI_FP[3] + MCTRL_FP[2])/2 = -43.84, unmoved); they are the next
thing to look at in the bay.

**THREE WAYS OUT, all bigger than a placement tweak, none started:**
  1. **SHORTEN motor_ctrl IN Y.** 62.00 comes off its own routed outline, so it is ours to
     change, and -8 mm buys a 12.68 gap. A board re-layout, and the cheapest of the three
     in risk because nothing outside the bay moves.
  2. **ROTATE THE PI 90 deg in its own plane** -- 56 along Y instead of 85 frees 29 mm of
     band, and the tray has the Z for it. Relays the whole bay, both cradles, every lead.
     Per the orientation rule this is a RE-AUTHOR in the new orientation, not a rotate.
  3. **TAKE wire_link OFF USB.** The Pi<->motor_ctrl link is travel offsets at a low rate and
     could ride the GPIO header pi_cap already sits on -- one plug gone for no geometry. It
     does NOT solve wire_usb, which is the output board's 20-channel USB audio.
⚠ 2 and 3 are not mine alone to pick: 2 touches the cradles and brenner's adapter, 3 is a
control-architecture change. 1 is inside my scope.

**ON THE ORIGINAL READING (kept, because the reasoning was right and the premise was not).** The Y-budget note above _MCTRL_CY
reserves 8.1 mm of the band for the Pi's M4 boss standing BESIDE its +Y edge -- and that
boss is GONE, PI_HOLD being ("+x", 0.0) since the user asked for it on the +Z side. So the
one thing between the Pi's port end and the motor board was space held for a screw that
had already moved. _MCTRL_CY -10.5 -> -0.5 spends it: motor_ctrl y -31.50..30.50, **gap
14.68**, and 11.6 mm of band still left before the +Y limit 42.1.
⚠ RULE: when a datum's comment says a gap exists FOR something, check the something is
still there. This is the second constant in two days invalidated by a change to a part it
never mentions.

### 5o. RIGHT-ANGLE PAIRS: the male half is abundant, the FEMALE half is scarce AGAIN (2026-09-29)

User: "can we find right angle plugs that line up? To me pins sound better than pogo since
they seat more reliably and are presumably cheaper/more in stock". Pins ARE cheaper and
better stocked, and right-angle is the configuration we want -- BOTH parts end up on the
TOP face, so the "Both Sides" assembly fee from 5n disappears and two coplanar boards butt
end-to-end. Measured on jlcparts 2026-09-29.

**RIGHT-ANGLE MALE -- plentiful, gold, 3 A, pennies:**

        C7501291    ZX-PZ2.54-1-3PWZ        1x3P   7834   $0.025  gold
        C7429379    PZ254-3-03-W-2.5-G0     3x3P   3559   $0.232  HCTL
        C18197985   PZ254-1-09-W-2.5-G1     1x9P   3305   $0.178  HCTL
        C18198034   PZ254-2-20-W-2.5-G1    2x20P   1586   $0.728  HCTL
        C7501292    ZX-PZ2.54-1-4PWZ        1x4P   1144   $0.031  gold
        C18198024   PZ254-2-10-W-2.5-G1    2x10P    699   $0.385  HCTL
        C18198017   PZ254-2-03-W-2.5-G1     2x3P    143   $0.113  HCTL (6 ways)

**RIGHT-ANGLE FEMALE -- 23 parts TOTAL, almost all Samtec, tens of units, dollars each.**
The only abundant one is C18198068 X6521FRS-2x04-C59D11 (2x4P, SMD right-angle, 3 A,
**6798** stock, $0.436, XKB) -- and XKB has no right-angle MALE in the library to match it.

⚠⚠ **THIS IS THE SAME GENDER ASYMMETRY THAT KILLED THE FOUR MEZZANINE CANDIDATES (5m),
showing up in a completely different family.** Female 23 parts vs male 75, and the stock
ratio is worse than the part-count ratio. It is a property of JLCPCB's catalogue, not of
any one connector: assume the female half is the binding constraint on ANY board-to-board
mate here and check it first.

**TWO MATCHED-SERIES PAIRS EXIST -- designed to mate, so they line up by construction:**

        HCTL      male C7429379  PZ254-3-03-W-2.5-G0   3x3P  3559
                female C7429380  PM254-3-03-W-8.5-G0   3x3P    61     <- 9 ways, 3 rows
        Samtec    male C7365809  TSW-103-08-F-D-RA     2x3P    20
                female C7370092  SSQ-103-02-G-D-RA     2x3P    20     <- 6 ways, 2 rows

HCTL's PZ/PM254 pair is the better one: same vendor, same 3x3P layout, complementary
prefixes, and 61 female units is ~20 instruments at 3 joints each. Thin, but a usable
number rather than DF40's 4. 3 rows x 3 = 9 ways covers the 6 we need with 3 spare.

⚠ **"LINE UP" IS A DATASHEET QUESTION AND I HAVE NOT ANSWERED IT.** For a right-angle
pair what must match is the HEIGHT OF THE PIN/HOLE CENTRELINE ABOVE THE PCB, to within
about 0.3 mm, and the catalogue text does not give it -- it gives insulation height (male
PZ254 2.5 mm, female X6521FRS 5.9 mm, female PM254 8.5 mm), which is NOT the same number.
Mixing vendors on a right-angle pair is exactly how a joint that looks right on paper
fails to seat. NEXT ACTION: pull the HCTL PZ254-3-03 and PM254-3-03 datasheets and check
the centreline heights against each other before anything is designed around them.

**AND THE STEP MATTERS TOO.** Two coplanar 1.6 mm boards butted end to end put both
parts' centrelines at the same height only if both parts are the same height class. If the
matched pair turns out to need a height offset, the channel can provide it -- one board
shimmed by the difference -- but that is a geometry consequence to design in, not a
detail to discover at assembly.

### OPTION 1 IS CHEAPER THAN IT LOOKED: 9.0 mm OF motor_ctrl's PI-FACING EDGE IS EMPTY

Measured from elec/motor_ctrl.py's own BOARD_NOTES["placements"], 82 parts, 2026-09-29:

        BOARD_W, BOARD_L        61.80, 62.00   -> board-local y spans -31.00..31.00
        lowest  placements      D6, D7 at y -22.00   (the USB ESD clamps)
        highest placements      C30/C31/R14..R17 at y 28.50
        occupied span           50.50 of 62.00

        margin below the lowest part      -31.00 to -22.00 =  9.00 mm  EMPTY
        margin above the highest part      28.50 to 31.00 =   2.50 mm

**AND THE EMPTY 9 mm IS THE END THAT FACES THE PI.** _MCTRL_CY is -10.5, so board-local
-31.00 maps to world y -41.50 -- the edge 4.68 mm off the Pi's port face. The board is
carrying 9 mm of bare laminate exactly where the gap has to come from.

**THE CHANGE, and it needs NO re-placement, only a re-centre and a re-route:**

        BOARD_L      62.00 -> 55.00        (-7.00, leaving D6/D7 ~2.0 mm of edge)
        placements   all y  -3.50          keeps every part where it is vs the +Y edge
        _MCTRL_CY    -10.5 -> -7.0         holds the +Y edge at 20.50, unchanged

Result: motor_ctrl y **-34.50..20.50**, so the +Y edge does not move (body_adapter still
clear by its 0.65) and **the Pi gap opens 4.68 -> 11.68**, which takes a right-angle USB-A
plug. New span -25.50..25.00 inside +-27.50: 2.00 of edge clearance at -Y, 2.50 at +Y.

⚠ COSTS, both real: the outline change is a DSN change so **ROUTE_REUSE_SES=1 is invalid**
and this is a full ~30-minute route; and motor_ctrl is at 0 unconnected / 0 violations
today, which a 7 mm narrower board may not hold. Re-route BEFORE touching _MCTRL_CY so a
routing failure is separable from a placement failure.
⚠ The 82 placements are written literally in the file (the note at elec/motor_ctrl.py:738
records the last such shift: "BOARD_W drops 6.20 and all 64 placements moved +3.10 in x").
A y -3.50 on all 82 is a mechanical edit -- do it programmatically and verify by reading
BOARD_NOTES back, not by trusting the edit script.

### THE PI CANNOT LIE FLAT -- and checking it RETRACTED option 2 as well (user, 2026-09-29)

User: "perhaps the pi could sit flat on the chassis floor? The motor board needs to be
upright so its lever/pedal plugs are accessible but the pi is free to sit flat if it fits
that way". The reasoning is right -- the Pi's constraints ARE looser than the motor
board's, so the Pi is where a compromise should land -- and the pose does not fit. The Pi
is 85 x 56 x 15.6 and all three poses were measured against the real room:

        pose               X (depth)   Y      Z      verdict
        standing (today)      15.6     85     56     fits; costs 85 mm of the Y band
        FLAT                  85/56  56/85   15.6    X available = ELEC_STACK_D = 21.8
                                                     SHORT BY 34.2 (or 63.2)
        rotated in plane      15.6     56     85     Z available = 78.85
                                                     SHORT BY 6.15

**WHY FLAT IS NOT CLOSE, and it is a datum not a clearance.** The bay is not a floor, it is
a VERTICAL 60 x 181 PLATE 3.0 mm thick at world x -607.8..-604.8, with the boards standing
off it on posts into a stack 21.8 mm deep. That 21.8 is `D.ELEC_STACK_D`, and
`MOTOR_X0 = -(KEYHEAD_INBOARD_X + ELEC_STACK_D + MOTOR_ELEC_CLR + MOTOR_SQ/2)` -- the motor
bank's X is DERIVED FROM IT. Growing the stack to take a flat Pi pushes the whole motor
bank +X and with it the drivetrain, the belts and the instrument's length. Not a bay change
at all, and not mine.
⚠ Laying the Pi flat with its 85 along Y instead would need 56 of depth AND free no Y, so
there is only one useful flat orientation and it is the one that is 63.2 mm short.

**⚠⚠ RETRACTION: OPTION 2 ("rotate the Pi 90 deg in plane") IS NOT VIABLE EITHER, and I
listed it as the 29 mm win without measuring the Z.** Rotated, the Pi wants 85 mm along
world Z. From the tray top (world z -2.00) down to the chassis floor (-80.85) there is
**78.85**, so it is **6.15 mm short** -- and the motor board already occupies z
-19.05..-83.85 in that band. Option 2 is not a free 29 mm; it is 6.15 mm of chassis
datum plus a fight with the motor board.
⚠ BUT 6.15 IS A SMALL NUMBER AND WORTH KEEPING ON THE LIST. If the tray can start 6.2 mm
higher, or the floor is locally lower where the Pi would sit, rotating in plane frees
29 mm of Y -- which solves the USB gap outright with 17 mm to spare rather than the 11.68
option 1 scrapes. Someone who owns the chassis datums should price that 6.15 before
option 1's re-route is spent.

**SO THE LIST IS NOW: option 1 (mine, measured, cheap) and option 3 (architecture).**
Option 2 is parked on a 6.15 mm chassis question. The user's instinct stands even though
the pose does not -- but the only Pi-side pose that helps is blocked by a top-level datum,
so the compromise has to land on the motor board after all, which is option 1.
