# Fastener migration: remaining work

**Goal (user, 2026-09-10), in priority order:**

1. **One tool for every fastener**: a **2.5 mm hex key**.
2. **One screw diameter**, so there is only **one heat-set insert SKU (M4)**.

What that means in practice:

- Every M4 is an **ISO 7380 button head** (2.5 mm hex).
- The NEMA17 motors stay on **M3 socket caps**. They take the same 2.5 mm key, and they thread the motor's own tapped holes rather than an insert, so the one-insert rule still holds.
- Specialty parts (for example ultra-low-head M4s with a 2 mm socket) are **out**: obscure parts are expensive.
- The hex size follows the screw **type**, not the thread. An M4 set screw is 2 mm by standard, so every remaining grub is the thing that has to change.

**PCB rule:** plastic captures the board in every direction except **one** install direction. A **single M4 beside the board** (never through it) blocks that direction: its head laps the board edge. The helper is cadkit `pcb_cradle(..., hold_edge=...)` (see `cadkit/pcb.py`).

## Already done (for context)

| Commit | What |
|---|---|
| `f25dbd0` | BOM + comments caught up with the 100 mm bridge axle SKU |
| `116efe0` | Chassis shear pins M4×35 button, keyhead hold-down M4×18 button, optical board grips drawn with the real Ø7.6 head + an assert that parts clear the **head**, BOM rows (M4×35, M3×10 motor screws, 2.5 mm key in Tools) |
| cadkit `b11dc8b` | `pcb_cradle` side hold-down (`hold_edge`, `pcb_hold_xy`, `pcb_hold_overlap`), `M4_BUTTON_HEAD_D/_H`; propagated to 9/10 projects |
| `7121240` | 11 bus-A CAN tees on one M4 beside the board (+X edge), anchors **re-bored after the chassis fuse**; electronics tray / OLED / AFE retention removed (deferred); BOM M4×10 + insert count |

Gates at `7121240`: `check_overlaps --full` green (1 inherited: `chassis_0 ↔ wire_pwr_hot_10`), sweep green.

---

## 1. Knee lever / foot pedal (needs a design decision)

These parts are shared by the left knee lever (`src/knee_lever.py`), the vertical knee lever (`src/knee_lever_vert.py`) and the foot pedal (`src/foot_pedal.py`), via `KL.feel_dummies` and `KL.cut_axle_bore`.

### 1a. Spring-tension set screws: M4 cup-tip, **2 mm key**, 2 per housing

The screw threads an insert in the cartridge back wall (`HS_BACK_X`), and its cup pushes the guide post to set coil preload. A key reaches it **through the hollow printed backstop** (`_cart_backstop`, bore `HS_BSTOP_BORE` = 5.0). The backstop sets the cartridge's X home. The two adjustments must stay independent.

**Why a plain M4 button head doesn't fit:**

- The head would have to sit outboard of the backstop flange. That face is the housing's +X extent (x 76.80 in the build frame).
- A comment says only **1.44 mm** of leg clearance remains there. That number is **not** a constant or an assert, and it doesn't say whose leg (the instrument's or the player's). **Verify it.**

**Why a button-head backstop beside a button-head tension screw doesn't fit (the user's idea, checked):**

1. Two solid screws can't share an axis, so the backstop would sit beside the tension screw's Ø8.4 head counterbore.
2. Clearing that counterbore needs **≥ 6.4 mm between the two axes** (4.2 counterbore radius + 2.2 shank clearance).
3. The backstop tip must still land on the cartridge back face: 10.5 wide (`HS_CART_WY`), spanning −3.0 / +5.0 about the coil axis (floor 3.8, cap top 11.8, axis 6.8).
4. The farthest off-axis a Ø4 shank's centre can land on that face is about **4.4 mm**, so it misses.

**Options:**

- **(a)** Give the cartridge back a **tab** reaching past the counterbore, for a button-head backstop to land on. The Z room in the housing back wall is **unmeasured**. The cartridge is authored in a build frame and placed by `feel_place` (mirror YZ, +`_FEEL_DZ`), so measure in the placed frame.
- **(b)** Keep the printed hollow backstop, and make the tension screw an **M5 set screw** (2.5 mm hex; the key passes the Ø5 bore). An M5 insert leaves about 1.75 mm of wall in the 10.5 cartridge back; confirm against the real insert OD. This costs a second insert SKU, which the priority order allows. *Recommended in-session as the smallest change.*
- **(c)** Leave the M4 grub as a documented 2 mm exception.

### 1b. Axle axial retention: M2 set screw, **0.9 mm key** (lever hub, onto the D-flat)

- **Where:** `AXLE_SET_*` block and `cut_axle_bore` in `knee_lever.py` (~line 960).
- **Why no M4:** the hub wall over the flat is 3.2 thick.
- **What already stops what:** the +Y axle flange (`AXLE_SHOULDER_Y`) stops −Y travel against the housing contact rib. **+Y** travel is what the grub prevents.
- **Why the +Y end can't be the stop:** the magnet cap turns with the axle, and the sensor chip is only `AIR_GAP` = 1.5 beyond the magnet.

**Options:**

- A **printed threaded cap on the −Y journal** that clamps the −Y bearing's inner race (a standard shaft-nut arrangement). This needs the −Y pocket's blind back wall (about 0.7 thick, −13.2 → −13.90) opened. It's unverified what sits −Y of the housing, and whether the knee-depth Y slide leaves room.
- Keep the M2 as a documented exception.

### 1c. Depth lock (not built yet)

- **Plan of record:** an M2 self-tapping set screw up through the housing top (`knee_lever.py` ~line 485; `chassis.py` ~line 318 comment).
- **Constraint:** an M4 was already ruled out (the W=6 octagon leaves a 2 mm rib side column).
- **Next step:** design it without a screw, or find another spot for an M4, when it lands.

### 1d. Open question for the user

The knee lever also has **printed** drives:

- The backstop's drive **slots**
- The magnet cap's **3/8" hex socket** (`CAP_HEX_AF`)

Do these count against the one-tool rule?

---

## 2. Pickup −Y retention screw: blocked on the plate/deck collision

**Now:** a horizontal M4 cup-tip set screw (**2 mm key**) in a heat-set insert on the height plate's −Y boss (`top_plate.py`: `RET_SCREW_*`, `RET_BOSS_*`, `_pickup_zplate`).

**Target:** **M4×12 button head**. It needs ≥ 11.5 to keep the full 5.5 mm reach (`GRUB_SWEEP`).

**Measured clashes for the button head:**

- Its head sweeps y −66.1 … −58.4 at x −65.13.
- That clips the −Y jack's plate **nub arm** by about 1.4 in X and 0.6 in Z, at `RET_SCREW_Z` = −7.578.
- Raising the screw one bead (0.8) clears the arm top by 0.2.
- It clears the −Y jack's insert boss by only 0.2.

**Access question (ask the user):**

- The boss mouth is at y −57.90, **−Y of the deck cavity edge (−55.05)**.
- The socket faces −Y under solid deck, so no key reaches it from above.
- Is it meant to be set on the bench with the pickup panel slid out?

**Blocker: the height plate collides with the deck panel.** This was filed as a separate task.

- **At the modelled 22 mm Alumitone (lowest plate):**
  - 37.24 mm³: the +Y jacks' X-arms poke 0.72 into the pickup panel's end walls.
- **At a 15 mm pickup (`PK_H_MIN`; plate +7.00 higher):**
  - 308 mm³ in total.
  - Each of the three jack nut bosses is 84.35 mm³ into the solid deck underside.
  - The retention boss is 128.38 mm³.
  - From the boss tops, any pickup shallower than about 17.6 mm stops the jacks early.
- **Why the gate is silent:**
  - `tools/check_overlaps.py`'s `TP_FAMILY` block accepts **any** contact between the deck panels and `pickup_zplate` / jack screws / inserts / pickup / chassis / endplates.
  - The gate only checks the demo pose.
- **Fix the collision first:** sweep the plate across the depth window, and narrow that allowance. The retention boss is one of the colliding features.

---

## 3. Electronics retention (deferred by the user)

For now these have **no fasteners and no plastic retention**, only plain support posts: the electronics tray boards (Pi 5, Teensy stack, ADC, buck, `teensy_ifc`; see `_support_posts` in `electronics.py`), the OLED (`top_plate._band`) and the AFE (`chassis.py` pedestal posts). Revisit them under the PCB rule. Don't re-add M2s meanwhile.

**Constraints found:**

- **Tray:** boards sit 4–7 mm apart, and several are flush to the tray edge. An M4 boss (Ø8, anchor 8.5 deep) can't sit *between* boards; it has to go under a board edge or at a free tray edge.
- **Purchased boards:** their dummies are plain boxes, so **edge component keep-outs are unknown**. Get each board's mechanical drawing before placing heads (the head laps about 1.3 mm).
- **OLED:** the module is 72×38 PCB with 62×33 glass, leaving **5.0 mm glass-free margin on the X ends**. The deck is only 6.4 thick, so an insert boss must hang below it (check the deck's print orientation).
- **AFE:** our own board, 20×30 on the bridge-rib pedestal.
- **Anything fused into the chassis** must have its anchor **re-bored after the fuse**. See the tee re-bore in `build.py`; the union refills holes cut before it.

## 4. Bus-B placeholder CAN tees (11, 12): the last M2s in the tee family

`wiring.tee_hold` returns `hold_edge=None` for them, so they keep an M2 through the board (`_BUS_B_M2_XY`). There's no clear spot for an M4: tee 11 sits on rib −501 against `tee_pcb_1`, tee 12 against `knee_housing`, and their own connectors crowd every lappable edge. The existing TODO in `electronics._tee_pcb_placeholder` folds the bus-B tap into the lever PCBs. Resolve these then.

## 5. Owned elsewhere (don't touch without coordinating)

- **Leg stack and pedal bar:** brenner is reworking these. Their fasteners are theirs:
  - leg-sleeve pinch grubs (M4, thread-formed, 2 mm)
  - the TRRS jack M2 set screw in the wired stub
  - `leg_stack` adapter bolts (head type unspecified)
  - leg end-wall lock (already M4×10 button)
- **Keyhead nut block:** the sliding-insert drive / retention screw is **undesigned**. Make it an M4 button head from the start. The keyhead hold-down's Ø3.6 thread-forming pilot isn't modelled yet.
- **Bridge axle:** main carries a note that the shaft goes **Ø8 with the 688ZZ decision**. Revisit the 100 mm SKU (`BRIDGE_AXLE_L`) when that lands.

## 6. BOM cleanup

- **Row "M4 cup-tip set screw":** still lists "10 nut clamps" (the keyhead uses sliding inserts now). Real uses: pickup retention (1) + knee/pedal spring tension (2 per control). Recount.
- **Row "M4 heat-set insert" (qty 29):**
  - Stale entries: 10 nut clamps, 4 leg-sleeve pinch collars.
  - Missing: 10 belt-tensioner insert-nuts, 2 optical grips, knee/pedal tension inserts.
  - **Recount before ordering.**
- **Row "M4 mount screw":** the leg-sleeve pinch note waits on brenner's rework.
- **Row "M2 grub screw":** knee-lever axle, pending §1b.
- **NEMA17 motor screws, M3×10:** derived as the 6.4 plate plus 3.6 of thread. **The SERVO42D tap depth is unmeasured**; check one motor.
- **Confirm stocked lengths at purchase:** M4×10, ×12, ×18 (16/20 are the common neighbours), ×20, ×35 button heads.

## 7. Small stale bits noticed

- **`src/pickup_mount.py` docstring:** still describes toe clamps and set-screw jacks; both retired.
- **`src/build.py`, near the leg TRRS jack:** the comment "an M2 set screw through the fin wall clamps the jack" refers to a fin that no longer exists.
- **`src/knee_lever.py` sensor cradle:** the comments say both "NO retaining screw" and "it is the M4 that sets it". Reconcile them.
- **`KL.M4_SELFTAP`:** defined and unused.
- **cadkit `fasteners.py`:** `headed_screw` is **defined twice** (~lines 412 and 437); the second silently wins. Fix it in canonical `../cadkit`, then `py -3.12 tools/propagate.py`.
- **`retractable-cable-spool`:** it didn't receive cadkit `b11dc8b` (its tree was dirty). Commit there, then re-run `propagate.py`.
