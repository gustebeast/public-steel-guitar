# bronner — open work items (2026-09-28)

**Priority: optical first.** Everything else is route-downtime work.

---

## 1. OPTICAL — the priority

**State:** routing at 16:05 with 6 bring-up pads, `local_nets` extended to the digital rail
and PHY supplies, `repair_mm` back to 8.0, and the `link_close_gaps` tuple bug fixed.

**Then:** re-search the `SAI_FS` repair against whatever route lands (it is measured against
one particular route and will not survive a placement change — the audit says so loudly,
and re-searching is ~2 minutes with `scratchpad/maze.py` + `verify_path.py`). Then
`opt_audit`, `check_north_si`, `cad_geom_check`, gate, render, commit.

**Watch:** U7 pad 9, `ULPI_D5`, `ULPI_NXT`, `+3V3A`. Every failure for six routes has been in
that one neighbourhood. If the pads still cost a net, they come out — a floating supply pin
on the USB PHY outranks bring-up convenience.

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

## 3. motor_ctrl — LED buck added, board currently BROKEN

Netlist is right; placement is not. 3 unconnected (`+3V3`, `CANB_H`, `EN_LED`), 48 violations,
against **0/0 before the change**.

* **`L3` overlaps `U6` and `C27`.** The Bourns SRN6028 land measures **6.92 × 8.11**, not the
  6×6 body I spaced it on. Shorting pads to U6 pins 5/7/8 and C27.
* **`J2`/`J6` mounting pads now fail `copper_edge_clearance`** — they sit at x 26.02 and the
  board grew in Y (46 → 54), which moved the ear (`_EAR_Y1` = BOARD_L/2 − EAR_W, 13.5 → 17.5)
  and with it the outline near them. Re-check against the new polygon.
* motor_ctrl has **no `_assert_field_clear`** like optical's, which is why a 1.5 mm overlap
  reached the router instead of failing at generation. Worth adding.

## 4. pi_cap — the UI board's 14-way ribbon (brenner)

Decided (see `docs/pi-cap-ui-ribbon.md`): **1.27 mm 2×7 shrouded IDC**, display on **SPI1**.
Remaining: pick/verify the LCSC part, fit it or grow the board ~14 mm in plane (brenner
measured 29.5 × 56 × 11.55 free alongside, holding only reroutable cables), add `+3V3` from
header pin 1 — the cap does not currently connect it.

## 5. chassis_2 mounting rework (user, 2026-09-28) — NOT STARTED

Mount the Pi and motor boards to **chassis_2 instead of the endplate**, so the endplate can
come off with the boards in place. Needs vertical chassis material so the boards keep their
orientation, and possibly swapping the two boards' ±Y positions — the Pi stack is thicker and
currently sits in the more constrained spot.

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
