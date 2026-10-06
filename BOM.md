# Bill of Materials — purchased parts

Sourcing for the bought parts (printed parts are built from `src/`). Links were
checked for a real, in-stock listing at the spec; prices are approximate and per
the date of writing — re-validate before ordering. Avoid Amazon per project
preference. See `electromechanical-pedal-steel-spec.md` §12 for the fuller
rationale. The **motors dominate cost** (10 × ~$35 ≈ ~$350); everything else
is commodity.

> **What is on the circuit boards is not read from this file.** It is
> [`docs/order-parts.md`](docs/order-parts.md), generated from the boards' netlists by
> `tools/order_list.py`: every part, its LCSC code and its count per board and per
> instrument. The board sections below record what was chosen and why, in the order it
> was decided, so a part that was later replaced is still named where it was chosen.
> Sections headed **HISTORY** are kept for their reasoning only. `elec/bom_audit.py`
> lists every place a part that is on no board is still named.

## Price verification — full sweep, 2026-08-01

Every line item in this file was pushed at a live listing on **2026-08-01**.
Rows carrying **[v]** were confirmed against a fetched product page; rows
carrying **[m]** could not be fetched and need a **manual check by a human** —
see "Cannot verify — needs a manual check" at the bottom of this file for the
list and the reason for each. Anything with neither marker is an internal
estimate (printed-part filament mass, PCB fab terms) with no listing to check.

**Six rows moved.** Four were priced too low, one vendor is out of stock, and
one part is not stocked at all in the library we committed to:

| Row | Was | Now | Impact |
|---|---|---|---|
| Optical photodiode (VEMD4110X02) | ~$0.35 ea | **REPLACED 2026-09-21 by the Everlight `PD15-22B/TR8` (C161211), $0.067 @200, 11,271 in stock** — filtered, 940 nm peak, ~3× the photocurrent; the sensor triplet was redesigned around its 3.3 × 2.8 body | **−$10.3/board**; stock block CLEARED |
| Optical MCU STM32H743IIT6 (was ZIT6) | $7.63 | **$10.01 @10**, 548 in stock (C89597, 2026-09-17) | +$2.38/board; stock block CLEARED by the LQFP176 swap |
| TRRS jack Tensility 10-03404 | $5.15 | **$8.19 / $6.96 @10** | +$3 |
| Bridge bearing 693ZZ | ~$1 ea | **superseded 2026-08-07** | part RETIRED — the whole instrument moved to one 695ZZ (Ø5×13×4); see the ball-bearing row |
| PCTG filament | $25/kg | **$29.95/kg** | +$3 |
| Pi buck ≥3 A | ~$25 | **$29.95** (D24V50F5) | +$5 |

Two of those are **availability**, not price, and they matter more than the
dollars: the photodiode and the 144-pin MCU are the two parts the optical board
is designed around, and **neither can currently supply a run of ten** (72 and 7
units in stock, against 200 and 10 needed). Both now have correct part numbers —
the constraint is stock, not selection. See the optical-pickup section.

| Part | Spec | Qty | Source (verify stock) | ~Price | Notes |
|------|------|-----|--------|--------|-------|
| **Drive belt** | GT2 (2 mm pitch) open, **5 mm wide** | ~6.7 m | [Bulkman3D GT2 open belt](https://bulkman3d.com/product/gt000-gt0003/) | **$0.54–1.73/m** [v] | cut-to-length, splice into loops with the printed clamp. Verified 2026-08-01: range confirmed, 5 mm width is GT2-5W-1000, sold 1 m per piece |
| **Drive motor** | MKS SERVO42D closed-loop stepper, NEMA17, **CAN MT** (board + motor) | 10 | [P3D](https://p3d.mx/products/makerbase-mks-servo42d-nema17-foc-motor) · [ElectroPeak](https://electropeak.com/mks-servo42d-nema17-closed-loop-stepper-motor) | $35 ea [m] | get **MT** (board + motor = the working actuator); **MB is the board ONLY**. MB/MT confirmed 2026-08-01 from Makerbase's own listings — all four SKUs are SERVO42D {RS485,CAN} × {MB,MT}. **⚠ MANUAL CHECK — the MT price is behind a variant dropdown that no fetch can read.** What is confirmed: ElectroPeak's linked page is the **driver only at $12.50** (motor explicitly not included) — that link is WRONG for this row and should be replaced. P3D lists "from $22.00" and makerbase3d.com "from $22.99", both of which are the **MB** floor. $35 for MT is therefore *plausible* (MB ~$22 + a bare 42 mm NEMA17 ~$13) but is **not a verified figure**. This is the largest line in the BOM (10 × $35 = $350); select CAN MT in the cart and record the real number before ordering. |
| **Lead screw + nut** | **Tr8×2** trapezoidal (8 mm major, **2 mm lead, 1-start, self-locking**) — screw bought stocked-length + **hacksaw to 37.7 mm**; nut = **H-flange brass, Tr8×2 single-start** | 1 order + 10 nuts | SCREW: [ReliaBot Tr8×2 1-start](https://www.amazon.com/ReliaBot-Tr8x2-Screw-Printer-Machine/dp/B07QZ159VV) · [bulkman3d Tr8×2](https://bulkman3d.com/product/hd0022/) · [ZYLtech Tr8×2](https://www.zyltech.com/8mm-t8x2-trapezoidal-acme-lead-screw-w-brass-nut-custom-length-up-to-1000mm/) · NUT: [AliExpress H-flange, 'Pitch 2mm Lead 2mm'](https://www.aliexpress.us/item/3256804704147842.html) (4 pcs/pack) | **~$11 nuts** (3×4-pk) + screw TBD [m 2026-08-14] | ⚠ **RIGHT-HAND THREAD IS REQUIRED (2026-10-05), screw and nut.** It is the stock part, but it is now a design input and not a detail: the hand decides which way each belt runs as a nut rises, and so which end of its run each belt clamp is spliced at (`dimensions.SCREW_HAND`, INSTALL_NOTES). With a left-hand screw the clamps on strings 2, 4, 6 and 8 would start beside their screw pulleys, where they meet the next string's pulley. If a left-hand set is ever bought, change `SCREW_HAND` and re-run `tools/clamp_range.py` before printing anything.<br>🔄 **2026-09-10 — RUN THE NUT DRY; LOCK THE PULLEY WITH THREADLOCKER (user).** Pitch must change ONLY when the motor commands it, including with the power off, so self-locking margin comes first. Tr8×2's 5.2° lead angle self-locks only while the nut thread's μ > 0.088: at 147 N a dry brass nut (μ 0.2–0.3) resists unwinding with **59–110 mN·m**, a well-greased one (μ 0.10) with only 6 mN·m, and **light oil or PTFE/dry-film lube (μ ≤ 0.08) BACK-DRIVES it. Do not oil or PTFE the nut.** A dry nut is also the one the pulley has to out-grip, though: the endcap pulley is only loosened by the LOWERING torque (the raising move screws it up into its bearing), and against a dry nut its friction margin falls to 0.8–1.0× — so friction alone cannot give both a grippy nut and a secure pulley. **Threadlocker on the pulley–screw thread decouples them** (see the Threadlocker row). It replaces the axial M4 set screw that was considered, which could not be housed anyway (an insert boss under a near-row pulley would sit in the far-row belts) and added little with the strings on. **Thread hand:** stock right-hand screw + nut. The pulley's thread is formed by the screw itself, so it cannot be the other hand, and a left-hand set would only mirror the behaviour — the current arrangement already puts the higher raising torque (~156 vs ~59 mN·m) on the pulley's tightening side.<br>🔄 **2026-09-10 — IN THE MODEL NOW, as TWO SCREW ROWS + ENDCAP PULLEYS. Supersedes the "stagger" FIT note and the "MIGRATION PENDING" warning below.** **Rows:** the 10.5 flat-to-flat nut cannot share a 9.5 lane at any screw size, so strings alternate between two mirrored rows at X ∓12 (in-row pitch 19.0, 8.5 mm clear), symmetric about the bridge-bearing tangent so each string breaks ~10° off vertical instead of 47–53°. **Screw cut length is now 37.7 mm** (`D.SCREW_LEN`): it stops 2.4 mm proud of the nut at the top of travel (there is no top bearing to reach any more) and ends at the bottom in the pulley's blind socket — cut from any stocked length, **one length for all ten**. **Pulleys are ENDCAPS:** a Tr8 bore cannot pass through a 14T band (the Ø7.8 pilot groove is wider than the ~Ø6.9 tooth root), so the rod threads 4.1 mm into a blind Tr8×2 pilot-thread socket above a solid toothed band (~2.0 MPa on the formed thread). That keeps the pulley at 14T — growing it to clear a through-bore would add belt circulation, slow the drive, and at 18T+ foul the guide rod. **Nut dimensions are no longer guesses** — they are read off the seller's drawing (still [m] until one is measured).<br>🔄 **2026-08-14 — DRIVETRAIN MOVED Ø5×1 → Tr8×2 (Ø8, 2 mm lead, single-start).** WHY: the Ø5 **1 mm** lead circulates the belt ~29 mm per 1 mm of carriage, so the rigid splice clamp cannot pass the pulley on the short strings, and the traverse is slow. A **2 mm lead** halves screw revs AND belt circulation, while a **single start** keeps the **5.2° lead angle < friction angle → self-locking** (zero-power tune hold). **Tr5×2 was rejected** — its 9.0° lead sits right on the self-lock cliff (needs μ>0.16; back-drives lubricated or at 150 N), so the coarse lead has to come from the larger **Ø8**, where the margin is real. **NUT = H-flange brass, single-start Tr8×2**, dims CONFIRMED off the seller's drawing (2026-08-14, ±0.5–1 mm stated): flange **22 tip-to-tip (R11) × 10.5 flat-to-flat × 4 thick**, boss **Ø10.2 × ~11**, total **15**, **2× Ø3.5 mounting holes @ 16 mm pitch**, Tr8×2 through. SKU **'Pitch 2mm Lead 2mm'** confirms single-start (the same listing's 'Lead 8mm' variant is the 4-start — do NOT order it). Ali listing is unfetchable (blocks curl + headless); dims are **USER-READ from its drawing → [m], buy ONE and measure before the carriage is cut.** ~$4.48/4-pk → **3 packs = 12 nuts for 10 strings**. **SCREW** = any stocked-length single-start Tr8×2 (plentiful 3D-printer stock), **cut to length with a hacksaw** — the cut end lands in a non-critical spot and Ø8 hacksaws easily (chamfer/deburr the cut or it chews the nut). **NO metal machining** (user standing rule): the nut is bought pre-cut (the 'H' flats), only the screw is hand-cut to length. **FIT:** 10.5 flat-to-flat / 10.2 boss vs the **9.5 lane = ~1 mm over** in the tight axis; resolved by **STAGGERING the screws fore/aft** (neighbours offset so each flange's ~0.5 mm side-overrun meets empty space) — NOT by widening the lane. Model to the **11 mm worst case** (±1 mm tol). ⚠️ **MIGRATION PENDING IN CODE — this is more than a BOM line.** `dimensions.SCREW_OD` 5→8 cascades to: the pulley bore (Ø4.6 formed-thread → Ø~7), the MR85 (Ø5 bore) screw bearings → a Ø8-bore bearing, the 9.5 lane + carriage width, the nut mount (H-flange **2× M3.5 @16** replaces the old 2× M2 seat), and the **motor/screw stagger** (new — the flanges force it). Everything below this block is the **superseded Ø5×1 record**, kept as the fallback + migration source.<br>✅ **DECIDED AND MODELLED 2026-08-11 — the H-flange nut is the design now**, not a preference. It mounts **FLANGE UP flat against the carriage's bottom face, BOSS DOWN in free air, two M2 screws up through the ears** (`dimensions.NUT_AF`). Three things forced that: the Ø8 boss cannot go *inside* an 8.8 mm wide carriage at any printable wall thickness; the old "flange-down against the bottom face" seat had the load backwards (string pulls the carriage +Z, so the nut must pull it −Z — that seat could only ever have held by the press fit's friction); and with the ears bolted the screws take the pull in tension, so the flats are not asked to react anything. **The lathe work is gone** — no facing the flange, no turning the boss. Costs: the carriage's −X face moved out to hold the −X ear's screw, and the endplate gained a **nut-sweep slot** (one extra prism under the changer-room floor) because the boss now hangs 10 mm below the carriage at the bottom of travel.<br>⚠️ **EVERY DIMENSION IN THE MODEL IS A GUESS**, extrapolated from the confirmed round-disc drawing by taking the H cut to be that disc with two flats milled tangent to the boss: AF **8.5**, flange **18.1 × 3.2**, boss **Ø8.0 × 6.6**, total **9.8**, two Ø3 ear holes at **±6.5**. Measure all six on arrival and update `dimensions.py` — `NUT_FLANGE_L` and `NUT_HOLE_DX` are the load-bearing ones (they set the nut-sweep slot and the carriage's −X face) and both are asserted in code, so a wrong guess fails the build rather than quietly fouling something.<br>*Original sourcing note:* the "double trimmed" H-flange type — [T4–T20 line, HighQ Store](https://www.aliexpress.us/item/3256812470922908.html), SKU `T5 Lead 1mm`, $6.50, FREE shipping** (better than the $7.80 source; saves $130 over a 10-instrument run). Confirmed 2026-08-11 that **`T5 Lead 1mm` is an explicit SKU** — the lead is selectable and correct. ⚠️ **Its Specifications tab publishes NO geometry** — only `Model=T4-T20`, `Guide Width or Diameter=4mm-20mm`, `Type=H Flange nut`. So across-flats is STILL unmeasured. Use the round disc only as the machining fallback. Its flange is cut tangent to the boss — verified against the T10–T40 spec table, where *Cut Edge Diameter − Small Circle = +0.5 mm on all 15 rows*, i.e. 0.25/side. The T5 boss is Ø8.0 by two independent routes (the table's 1.60 boss/screw ratio at its T10 end, and the measured T5 disc drawing), so **T5 across flats ≈ 8.5 mm — it fits the 9.5 lane with 1.0 mm to spare.** That kills every objection to the disc at once: no lathe work, and the FLATS key it against rotation so there is no press fit to split a thin wall. ⚠️ *Still inferred, not read off the T5 row — the +0.5 pattern comes from the disc line's table, and the H-cut listing is a different line. Confirm across-flats, height and flange thickness before modelling.* Lead tried to verify independently 2026-08-11 and could NOT: the T5–T20 Amazon listing 500s, Gavan Tools publishes no dimensions, and web search surfaces no drawing. **So this rests entirely on the +0.5 pattern — buy ONE and measure it before committing the carriage.**<br>**Fallback — the round disc nut, dimensions CONFIRMED from the seller's drawing (2026-08-11):** flange **Ø20 × 3.2**, boss **Ø8 × 6.6**, total **9.8**, three Ø3 holes on a Ø13 bolt circle, Tr5×1 through. Against our model (flange Ø9.0 × 2.0, body Ø7.0 × 7.0):<br>• **Flange Ø20 → turn to Ø9.** Clean: the mounting holes span Ø10–16, so that cut removes them entirely and leaves a plain disc — nothing left to work around.<br>• **Height 9.8 vs 9.0 — absorbed, no action.** It feeds `NUT_TOP_MAX`, so the screw top moves to −8.00 and the cut length to 56.2, still mid-window (55–66).<br>• ⚠️ **Boss Ø8 vs our Ø7 — the real remaining problem.** The carriage is 9.0 wide (0.25/side in the 9.5 lane), so a Ø8.2 pocket leaves **0.40 mm walls — half the one-bead floor**, and a press fit would split them. Widening the carriage needs 9.8, which is *negative* clearance in the lane. So the boss must be turned **Ø8 → Ø7** as well, leaving 1.0 mm of brass over the thread. **Net: the round disc would need TWO lathe cuts on ten parts — MACHINING, which is ruled out** (standing constraint: no self-machining; outsourced only if low cost, and ten one-off turned brass parts is not that). So these confirmed dimensions are what DISQUALIFIES the disc — they are not a work plan for it. If the H-cut above does not pan out, the next options are **(1) PRINT THE NUT** — kills sourcing and machining at once, any OD we like (9.0 drops into the existing carriage), `cadkit.threads` cuts internal trapezoidal threads, and the duty fits: static HOLDING not traversing (self-locking 4.19°, ~147 N bearing, a semitone is ~1.5 mm), so **wear is the open question, not strength** — **(2) a round POM/nylon nut as a catalogue part** (StepperOnline SN-S-AA is Tr5×2; ask whether Tr5×1 exists without a quote), or **(3) a carriage capturing the Ø20 flange**, which needs Z-staggering since adjacent lanes' flanges collide. **Do not order ten nuts against this row yet** (the rod ships with one — measure it).<br>**BUY 2 × 350 mm — $10.97 for the whole instrument.** Full 1 mm-lead price ladder read off AliExpress [3256809702707665](https://www.aliexpress.us/item/3256809702707665.html) 2026-08-11 (100/150/200/250/300/350/400/450/500/550/1000 mm = $3.33/5.18/6.79/8.12/9.58/10.97/12.33/13.66/15.02/17.28/45.65). **Each SKU ships TWO pieces** (confirmed in the product photo, not a typo), which is what makes this cheap: at 56.6 mm (`D.SCREW_LEN` — the single source; re-read before ordering or cutting) with a 1.5 mm kerf, 350 mm yields 6 per rod → **12 screws for $10.97**, and you only need 5 per rod for ten, leaving 61 mm of slack per rod. 300 mm is $1.39 less and gives exactly ten with only 11 mm of slack — not worth the risk on a hand cut. ⚠️ **AVOID THE 1000 mm ($45.65).** Lengths 100–550 all price near $0.032/mm; the 1000 jumps to $0.046/mm, **43% worse**, and at $1.34/screw it is the *worst* buy on the ladder — the price curve is linear to 550 then breaks. Shipping is **$4.58 flat per order** (free over $250), so multiple pieces share one charge. ⚠️ Stock reads 3200+ on this listing but is thin elsewhere; re-verify before ordering. Cut to length — ~57 mm is not a SKU; the cut is forgiving (55–66 mm window) and Ø5 hacksaws easily. Chamfer/deburr the cut end or it chews the nut. *(Amazon alternative, 1 mm lead, if AliExpress rots: [B0D76YVRJD](https://www.amazon.com/dp/B0D76YVRJD) 600 mm $41.45 / [B0D76Z8SWJ](https://www.amazon.com/dp/B0D76Z8SWJ) 800 mm $50.42 — 4× the price, single piece.)*<br>**Not a McMaster part at any length:** Ø5 trapezoidal sits *below* the ISO/DIN 103 series, which starts at **Tr8**, and we cannot go up to Tr8 because of that same 9.5 mm lane (see `SCREW_OD` in dimensions.py). *(McMaster's grid would not render for verification — the Tr8-floor reasoning is from the thread standard; confirm at purchase.)* **Ø5 is not a strength compromise** — computed at 147 N: rod tension 13.7 MPa (15× margin), thread bearing 3.1 MPa (and our duty is static holding, not traversing), drive torque 0.072 N·m (5.5× a NEMA17), lead angle 4.19° vs an 8.5° friction angle so it stays self-locking, and 2 µm of stretch = 0.4% of a semitone. It is scarce because of the standards/3D-printer market, not because it is marginal.<br>*History: cut length was ~61, then ~67 after the belt-plane centring, then ~57 once the screw stopped 2.4 above the NUT instead of running to the carriage's top, and now **49.4** — the H-nut hangs entirely below the carriage, so the rod only has to reach the carriage's bottom face. At 49.4 mm with a 1.5 mm kerf a 350 mm rod yields SEVEN pieces, so the same 2×350 buy gives 14. ALM (the manufacturer) is quote-only with no published prices and is RULED OUT — an open-source build must not require emailing a factory to buy a part.* |
| **Screw bearings** | **688ZZ** deep-groove, Ø8 × Ø16 × 5, shielded — **ONE per screw**, thrust only | **40** (10 screw + 10 bridge + 10 knee lever + 10 foot pedal) | **BUY THIS ONE:** [Bearings Direct 688-ZZ, AMPEC](https://bearingsdirect.com/688-zz-mini-ball-bearing-8x16x5-shielded-mr688zz/) · cheaper alternate [VXB 10-pk](https://vxb.com/products/688zz-8x16-shielded-8x16x5-miniature-bearing-pack) | **$4.38 each** ($3.72 at 50+), 489 in stock [v] 2026-10-06 | 🔄 **2026-09-10 — ×42: the 10 BRIDGE bearings, then the 12 KNEE-LEVER and 10 FOOT-PEDAL bearings, moved onto this SKU — it is now the ONE bearing in the instrument** (the knee/pedal axles are printed PCTG, now Ø8; see the retired 695ZZ row). 🔄 **2026-09-10 — MR85ZZ ×30 → 688ZZ ×10.** MR85 is not an option any more: its bore is Ø5 and the Tr8×2 screw is Ø8. **688ZZ over the closer-fitting MR148 (Ø14) on capacity** — MR148 publishes C0r 144–309 N, i.e. 72–154 N permissible axial against the 147 N a string pulls, which is inadequate; 688ZZ publishes **474–710 N**, i.e. 237–355 N axial = **1.6–2.4× on the worst string** (P0/C0 0.21–0.31). ⚠️ **That C0r spread across makers is wider than the margin itself, so buy a BRANDED part and read its real C0r.** ✅ **2026-10-06: done. The Bearings Direct part is AMPEC brand and its listing publishes 132 lbf = 587 N static (282 lbf dynamic), so permissible axial is about 293 N = 2.0× the worst string. VXB's pack lists 710 N under its house brand.** 🔄 **2026-10-06 (user: over $100 of bearings is too much): the rated part is bought for the TEN SCREW SEATS ONLY.** The other 32 (bridge axle, levers, pedals) are any 688ZZ: the bridge load is radial, 208 N against a lowest published rating of 474 N, and the lever axles carry almost nothing. Those 32 are [Fast Eddy TFE234](https://www.fasteddybearings.com/products/10-units-8x16x5-metal-shielded-bearing-688-zz), 10 for $10.99 (100 for $98.99), the cheapest stocked listing found outside Amazon and AliExpress. Still to confirm on the first one in hand: the ring diameters the seats are sized to. **ONE per screw, not the old tandem pair:** the pair existed only because one MR85 was under-rated, and a second 688 does not fit (it drives the thrust ledge 3.55 mm into the nut's sweep). **The TOP radial bearing is DELETED:** at Ø8 bore the smallest bearing's Ø16 OD reaches exactly the guide rod at the nut's 8.0 mm hole offset, and the Ø8 screw is 6.55× stiffer in bending than Ø5, cantilevering from the thrust bearing at ~0.006 mm under the 1176 N·mm string couple — it was reacting nothing. **Seats re-sized for the 688's rings** (ring diameters are the d + 0.28·(D−d) rule; confirm on the datasheet): the rail's ledge bore is **Ø14.4**, landing on the OUTER ring (~Ø13.8–16) — Ø12.0 would have pressed the shield; the pulley's pilot boss is **Ø9.6**, landing on the INNER ring (~Ø8–10.2) — the old Ø5.6 was smaller than the Ø8 bore and would have slid straight through, retaining nothing. Unchanged: string tension preloads it (no deliberate preload wanted), and static capacity governs, not fatigue or fretting. Ø16 in the 19.0 mm in-row pitch leaves **1.4 mm** of rail web per side — the tightest wall in the layout. *The superseded MR85 record (tandem pair + top bearing, Trianglelab $0.49 ea ×30) is in git history.* |
| ~~**Axial retainer**~~ | **DELETED TWICE** — the purchased Ø5 collar 2026-08-11, then its printed replacement 2026-08-12 | — | — | **$0** (was $25) | 🔄 **2026-09-10:** still retained by the drive pulley, but the pulley is now an **ENDCAP** — the Tr8×2 rod threads into a **blind 4.1 mm pilot-thread socket** (Ø6.2 ridge / Ø7.8 groove, finished by the rod), ~**2.0 MPa** on the formed thread against the 6.5 MPa below. The Tr5×1 figures in the rest of this cell are the superseded record.<br> **Locked with a plastic-rated threadlocker** (see the Threadlocker row): against the dry, self-locking nut, friction alone leaves the pulley only 0.8–1.0× margin in the lowering direction.<br>It was a Ø5 set-screw shaft collar at $2.50 ea, and it never fitted: the smallest stocked Ø5 collar is ~Ø10–16 OD and the string lane is 9.5. **The printed collar is gone too: the DRIVE PULLEY does its job (user).** With the thrust bearings moved onto the pulley tops, the string's pull jams the pulley up into them — the same jam that held the collar — so ONE part now retains the screw AND stays put on it, and the pulley's set screw went with it. The rest is kept because the pulley's bore uses exactly the same trick: it grips by a **FORMED thread** — the bore prints plain at Ø4.6 (between the Tr5×1 minor 4.0 and major 5.0) and the steel rod cuts its own mating thread going in, like a self-tapper. Two things ruled out the alternatives: a Tr5×1 thread **cannot be printed** (1 mm pitch, 0.5 mm deep is under one 0.8 mm bead in both directions — 0.2 mm layers do not help, the missing resolution is in XY), and a **friction clamp cannot hold 147 N permanently** (it needs ~1.8 kN of normal force = ~69 MPa hoop, past PETG-GF's tensile strength before creep). ⚠️ **It is length-starved at 4.0 mm** — everything under the pulley has to fit between the pulley's bottom flange (frozen by the motor bank) and the chassis end block, a 10.7 mm budget shared with the ledge and the bearings. 4 turns is ~28 mm² of shear at full form and ~80 % of that with the pilot's engagement, so ~6.5 MPa under 147 N, roughly a quarter to a third of interlayer shear: inside the usual 25 % static-creep guideline but **the tightest margin in the drivetrain**. If it ever needs more, the lever is the chassis end block. Seat it with an **8 mm spanner** on the flats. ⚠️ **It is TURNED, not prismatic** — it rotates with the screw, so what has to fit the 9.5 mm lane is its SWEPT circle. The first version was a 12.8 × 8.0 block with spanner flats: Ø20.8 swept, and every collar would have milled both its neighbours on the first move (user caught it). The body is now a Ø8.8 cylinder with the flats milled into it, which costs nothing since the swept circle is the cylinder either way. |
| ~~Ball bearing 695ZZ~~ | **695ZZ** deep-groove, Ø5 × Ø13 × 4, shielded | **0 — RETIRED 2026-09-10** (all 32 moved to 688ZZ: bridge 10, then knee levers 12 + foot pedals 10) | [Fast Eddy 10-pk](https://www.fasteddybearings.com/10-units-5x13x4-metal-shielded-bearing-695-zz/) · [Bearings Direct](https://bearingsdirect.com/695-zz-mini-ball-bearing-5x13x4-shielded-619-5zz-r1350-zz/) | **$1.10–4.38 ea** [v] | 🔄 **2026-09-10 — DECIDED (user): ONE bearing SKU, 688ZZ, everywhere** (axles to Ø8), since the leadscrew already forces a Ø8 bore. **BRIDGE: DONE in the model** — the 10 bridge bearings are 688ZZ on an Ø8 × 100 axle (the string's bend radius r 6.5 → 8.0, static margin 1.66× → 2.3–3.4×), so they buy on the **Screw bearings** row. **Knee levers + foot pedals: DONE too** — 688ZZ on Ø8 printed axles (hub Ø13.6, flange Ø12.8, the pedal housing's race wall drawn from its fused bar so the 48.0 axle datum holds). Nothing in the instrument uses this part any more; the row stays as the record.<br>**REPLACES the old 693ZZ (Ø3×8×4) row — that part is no longer used anywhere.** One bearing for the WHOLE instrument: the Ø5 bore unifies every axle, so bridge, knee levers and foot pedals all take the same part. **Count = 10 bridge (one per string, the string rides the Ø13 OD) + 12 knee lever (6 levers × 2) + 10 foot pedal (5 × 2) = 32**; buy 40 for spares. Verified 2026-08-07: **Fast Eddy $10.99 / 10-pack = $1.099 ea** but *on backorder, ships 7–10 days*; **Bearings Direct $4.38 ea**, 47 in stock, ships in 24 h, 10 % off at 25–49 → **$3.94 ea**. That is a 4× spread — 40 pieces is **$44 vs $158**, so order Fast Eddy early rather than paying the in-stock premium. (VXB lists singles at $7.77 — ignore.) Selection rationale: the Ø13 OD is capped by the carriage ball-cage clearance in Z, and 695ZZ clears the string load with margin where 693ZZ did not; false brinelling, not static load, is the long-term risk |
| ~~**M2 pulley grub**~~ | **DELETED 2026-08-12 — the string load holds the pulley** | — | — and as of 2026-08-13 there is only ONE pulley part: it is fitted either way up (boss-A up = high plane, flipped = low), since turning it over changes how far the toothed band sits below the upper face by exactly `BELT_PLANE_DZ`. That also levels the thread engagement at **20.8 mm on every station** — the earlier two-part split gave the high-plane half only 8.8, which mattered once the pulley became the part carrying the 147 N. Prints **column-end-down with a brim** [McMaster](https://www.mcmaster.com/) | commodity | 🔄 **2026-09-10 — the ONE flip-over pulley described here is superseded.** The screw pulley is TWO SKUs again, both ENDCAPS with their column ABOVE a solid 14T band, differing only in column length (2.4 vs 8.0 mm = `BELT_PLANE_DZ`); both print FLANGE-DOWN and share one 4.1 mm socket depth, so every screw is the same length. Still 0.2-nozzle (GT2 teeth + the Tr8×2 pilot thread). Still no grub.<br>The screw pulleys' torque path — they had none at all, just a plain Ø5 bore on a round rod. **The primary grip is a PILOT THREAD**, the same as the retaining collar: the bore prints as a shallow female helix at the true 1 mm pitch and the Tr5×1 rod swages it to size through the full height going in. (It is why this part's **0.2-nozzle** requirement is now explicit — it was always needed for the GT2 teeth, but the 0.3 mm thread groove needs it too.) This grub is only a **secondary lock**, stopping the pulley walking along that thread under torque reversals — a far smaller job than holding 0.072 N·m outright, which is why a set screw is acceptable here after being rejected as the primary path (user: a tip bearing on one thread crest is a point contact relying on preload). It sits in a hub above the top flange: **above the belt** (anything at r > the tooth OD inside the band jams it once per turn) and at the flange Ø, so it adds nothing to the swept circle. Self-tapped — an M2 insert pocket is 3.5 deep and there is only 3.2 of wall to the bore.<br>**Two earlier designs died here and both are worth not repeating:** a −X lug to hold this grub reached r 8.6 and swept a **Ø17** circle straight through the endplate; and a **C-clamp** needs a full-height slit, which is fatal on a toothed pulley (user) — closing an 0.8 mm gap shortens the pitch circle ~3%, so the teeth stop matching the belt, and a clamped split part will not hold rib spacing anyway |
| ~~**M2 nut screw**~~ | **DELETED — the nut bolts to nothing now** | — | [McMaster](https://www.mcmaster.com/) | commodity | Two per station, up through the H-nut's ears into the carriage — this is what carries the string pull from carriage to nut, 73.5 N each in tension (~2.4 MPa on the self-tapped thread over a 4.8 mm bite). The **+X screw is longer** — it clamps through a printed spacer (next row), so it spans flange + spacer + bite. Both lengths track the real flange thickness and hole pitch, so **re-check them when the nut arrives** |
| ~~**H-nut spacer**~~ | **DELETED with the carriage** | — | — | **$0** | Packs the standoff under the H-nut's **+X** ear. It exists because of a printing constraint, not a layout one: the nut's boss has to be recessed into the carriage (hanging free it drives into the raised-plane pulleys), the recess has to be **Y-open** (Ø8.4 inside an 8.8 mm part leaves 0.2 mm walls), and a Y-open recess has a ceiling at its +X end that must close at 45°. That closure can only grow **downward** off the body above it — growing up from the bottom face drops a floating island into every layer for 7 mm (user caught it) — so the carriage's bottom face is simply absent from x 4.2 to 11.2 and that ear stands off. Compression only, ~20 MPa. **Both ears must be tied:** the string enters at the anchor (x +8) and leaves through the nut (x 0), a standing 1176 N·mm couple; on the −X screw alone the carriage cocks ~0.2 mm at the anchor, about 13 cents. Height is derived from the ramp, so it moves when `NUT_HOLE_DX` is measured |
| **Ø8 precision shaft** (was Ø5) | Ø8 **g6/h6 ground shafting**, **100 mm** — the bridge axle ×1 (`BRIDGE_AXLE_D` × `BRIDGE_AXLE_L`, a PURCHASED length; the endplate arms derive from it, not the other way round. Stops: the −Y blind end wall and the optical strip) **plus the nut wrap rod ×1** — the same part (see its row). The knee-lever and foot-pedal axles are NOT shaft stock: they are PRINTED PCTG, now Ø8 | 2 × 100 mm | [McMaster linear shafts](https://www.mcmaster.com/products/linear-shafts/) | ~$3 [m] ⚠ | 🔄 **2026-09-10 — Ø5 → Ø8 with the 688ZZ bearings**: the bridge axle first (branner), then the keyhead wrap rod (bronner), so ONE 100 mm SKU serves both ends and no Ø5 shaft remains in the instrument.<br>(history) Was Ø3; the 695ZZ move took every axle to Ø5. NOT an m6 dowel: a press fit would stop it sliding through all 10 bearings + the comb fingers + both arms. NO GLUE: the −Y arm's bore is blind (the 1.6 wall is the −Y stop) and the optical strip's head is the +Y stop, so NO grub — the M2 that used to retain it is gone. |
| **Guide rod** | **Ø3.5 drill blank (hardened, ground), 35.4 mm** (2026-10-02: z −23.35 → 12.05 — down to 1.6 of solid rail plate, up to 0.15 under the optical board, which now also traps it) — sized to the nut's MEASURED ear hole | 10 | [McMaster drill blanks](https://www.mcmaster.com/drill-blanks/) | ~$0.5 ea [m] | 🔄 **2026-09-10 — TWO ROWS changed its mounting and length.** Each rod rides the ear its row does NOT use for the string (near row −X, far row +X), and is now **~34 mm** (socket floor −32.0 up to just under the bridge bearing, +2.0). It no longer sockets into the rail — there is no material left between it and the Ø16 thrust bearing — so it **drops into a 1.6 mm socket in the rail plate**, which was thickened 1.6 → 3.2 → **4.0** to take it (the last 0.8 is a solid floor under the socket, above the bearing lip's window) (a printed collar round the rod's base was tried first and removed as a print overhang), and cantilevers from the slab; its load point is the ear ~17 mm up (~0.02 mm under 11 N). **Resolved 2026-09-10 (user):** the rod is now **Ø3.5**, derived from the Tr8 H-nut's ear hole (`GUIDE_ROD_D = NUT_HOLE_D`); a Ø3 rod had put back the 0.5 mm of slop this cell rejected the Ø2.5 dowel for. It is no longer the bridge axle's stock. Buy it as a **drill blank**, sold in 0.1 mm steps, and pick the size to the MEASURED hole — the seller's drawing is only ±0.5–1.<br>Anti-rotation, through the H-nut's **−X ear**. **Ø3, not the old Ø2.5 dowel, and the reason is slop not strength:** the ear's hole is the nut's own Ø3, so a Ø2.5 rod leaves 0.5 mm of play — the nut rotates 38 mrad and the string walks 0.25 mm. Ø3 g6 leaves 0.01 mm and 0.8 mrad, fifty times better, and is 2.1× stiffer besides. It also **merges a BOM line**: same shaft as the bridge axle, just ten more pieces. **Mounting inverted (user):** it is pressed into the endplate's slab ABOVE and hangs DOWN, cantilevered. The old bottom socket is impossible now — the drive relief and the nut's sweep between them take out every scrap of endplate below the room at this X — and the top is also the end that prints, since the slab is a straight −X extension of solid cap. **Press fit**, because with that much socket any clearance is amplified over the rod's ~15 mm reach; bending is a non-issue at 0.016 mm |
| **Nut break dowel** | Ø2 × 4 mm steel dowel (52100) | 10 | [McMaster 91595A018](https://www.mcmaster.com/91595A018/) | $12.70 / pack [m] | The gauged break pins — the scale "0" — dropped into their open cradles from above and held down by string pressure. **One per string; the clamp ANVIL is deleted.** A second dowel used to sit under the tail so the set screw pinched it against steel, but the wrap capstan took the clamp from 490 N to 46 N, so the plastic floor is no longer the constraint — and the anvil's pocket was the last real print overhang in the block (a vertical +X wall in a −X→+X build, with no +X face to open toward the way this dowel's own pocket has). |
| **Nut wrap rod (capstan)** | **Ø8 × 100 mm g6/h6 precision shaft — the SAME part as the bridge axle** (`D.BRIDGE_AXLE_D` × `D.BRIDGE_AXLE_L`) | 1 | [McMaster 8 mm shafts](https://www.mcmaster.com/products/linear-shafts/) | order with the bridge axle [m] | **One shaft SKU at both ends (user, 2026-09-10)** — it went Ø5 → Ø8 when the bridge moved to 688ZZ bearings. **THE PART THAT MAKES THE CLAMP WORK.** Each string winds its turns around it before reaching its sliding-insert clamp, and the capstan (Euler-Eytelwein, T = T₀·e^−µθ, µ=0.15 steel-on-steel) divides the 147 N tension down to what a light clamp can hold. Ø8 bends the .070 at 18.2% outer-fibre strain (d/(D+d)), gentler than Ø5's 26.2%. **Turns are per string and a GEOMETRY result** (`nut_block.turns`): a shared rod makes the coil climb ACROSS the strings, each turn spending NUT_PITCH (6.5 mm). The 100 mm runs past the last bay into the block's −Y extension (`nut_block.Y_LO`). Slides in from −Y through every comb web at once, so it must be a precision shaft, not a dowel; the +Y bore is blind and that wall is its +Y stop |
| ~~**M4 cup-tip set screw**~~ | **DELETED 2026-09-30 — no set screws anywhere (user: every fastener is M4 on the 2.5 mm key; a set screw takes a 2.0)** | — | — | — | The last 45 went the same day: the 44 in the lever/pedal feel cartridges became **M4 × 10 button heads** in the same inserts (see that row), and the pickup's −Y retention became an **M4 × 12 button head**. The 10 string clamps had already gone when the keyhead's sliding insert became the clamp. |
| **M4 pickup-jack screw** | M4 × 0.7, 20 mm, 18-8 SS button head (hex drive) | 3 | [McMaster 92095A-series](https://www.mcmaster.com/92095A192/) | ~$12 / pack [m] | pickup height LEADSCREW jacks: the button head is captured in a deck counterbore (free to rotate, axially fixed), the shank threads the plate's heat-set nut so turning it from +Z walks the pickup up/down; 20 mm spans the height-adjust range across the 15–22 mm pickup depths + string gap. **Confirm the ×20 length suffix (…A196-class) at purchase.** NEW part — replaces the stale "3 cup-tip height screws" (those pre-date the leadscrew jack) |
| **M4 heat-set insert** | M4 × 0.7 brass heat-set, 4.7 mm | 44 | [McMaster 94459A150](https://www.mcmaster.com/94459A150/) | $10.82 / pack 50 [m] | 10 nut clamps + 4 leg-sleeve pinch collars + 3 pickup-carrier jack nuts + 1 pickup -Y retention grub; deeply buried (no pull-out) + **11 CAN-tee side hold-downs** (one per bus-A cradle boss). + **4 leg lock pins** (one per corner, in the chassis's kept shell — `legs.lock_pin_joint`) + **1 pedal-bar latch collar** (in the bar's tower, `bar_latch`). ⚠ **Recount before ordering** — the 10 nut clamps and 4 leg-sleeve pinch collars above are stale (the keyhead uses sliding inserts; legs.py thread-forms the pinch grubs), while the 10 belt-tensioner insert-nuts, the 2 optical-strip grips and the knee/pedal spring-tension inserts are not listed. + **10 keyhead height-screw nuts** (prototype; mouth down, flush in the keyhead prism's bottom face). | ~~+ 1 leg TRRS keeper lock~~ — **withdrawn 2026-09-15**: there is no fastener at that joint at all now. It went M4×16-button-plus-insert → Ø2 TPU pin → **TPU bayonet**, each step for a reason the last one could not answer: burying a Ø7.6 head needed the keeper 8.6 tall, and the keeper's height comes straight out of the male plug's wrap; and the pin, though it freed that height, could not be got back OUT, since nothing at that flank may stand proud of a face that enters a mortise (user). A bayonet turns out with a screwdriver and adds no SKU.
| **Latch return spring** | Compression, **Ø5.0 OD × 0.6 wire × 15.0 free**, ID 3.8, 304 SS (rate ~1.9 N/mm, bracketed 1.6–2.4 off McMaster's published 1.96 for a Ø5.63 × 0.63 × 12.5; **measure on arrival**) | 6 (+ 4 spare) | [uxcell B0GCZVQFWN](https://www.amazon.com/dp/B0GCZVQFWN) — 10 to a pack, used **AS BOUGHT** | **$6.99 / 10** [a] | ONE SKU for BOTH latches (user). 4 leg↔body + 2 bar↔leg. Upper **5.7 N hold / 11.8 N press**, lower **5.7 / 13.3** — the design was drawn around 4.0 / 12.05, so the hold is firmer and the press is unchanged. Installed 12.00 (`SPR_SEAT` 6.4 → 8.0), pressed 8.80 upper / 7.75 lower against a worst-case solid of 7.2 |
| **Lever feel spring** | JIS light-load (blue) **die spring, Ø10 hole / Ø5 rod × 30 free** (±2), 142.2 N at 40% → ~11.9 N/mm (**measure on arrival**) | **22** (2 per control × 11: 6 knee levers + 5 pedals) | [uxcell B0B772B9V2](https://www.amazon.com/dp/B0B772B9V2) — 20 to a pack | **$9.99 / 20** [a] ×2 packs | Every knee lever AND pedal carries the same two cartridges (MAIN + HALF-STOP), so 22, not 12 — two packs. `knee_lever.HS_SPR_*`. See the DECIDED note below. |
| **Spring-seat / position washer** | **DIN 9021 M3 flat washer, Ø9 × 0.7–0.9, Ø3.2 hole**, zinc-plated steel | **44** (4 per control × 11) | [McMaster 91100A120](https://www.mcmaster.com/91100A120/) — 100 to a pack | **$2.97 / 100** [m] | Two per cartridge. (1) SPRING SEAT: the tension screw's cup nests in the Ø3.2 hole (its Ø4 thread cannot pass), replacing the 3.2-long printed guide post with ≤0.9 of steel. (2) POSITION STOP: seated in a Ø9.4 × 0.9 recess in the housing pocket's back face, under the position screw's socket end; the 2.0 key reaches through its hole. `knee_lever.WASHER_*`. |
| **Thread locker (position screws)** | **Vibra-Tite VC-3** reusable, plastic-safe (or nylon-patch M4 × 10 button heads) | 1 bottle (22 screws) | ⚠ **source not yet picked** — prefer a stock distributor over Amazon | — | On every cartridge's POSITION screw — see `INSTALL_NOTES.md` KL-1. NOT an anaerobic (Loctite 2xx): it can craze PETG. |

> **WHY THE LATCH COIL IS CUT, 2026-09-16 (user: one spring for BOTH latches, from
> uxcell, and geometry may move so long as 1.6 mm and 45° hold).** It is cut because
> geometry moving does not help here, which took working through to find:
>
> * uxcell stocks this wire and OD at 5, 10, 15 and 20 mm free. **Not 12.**
> * **15 mm does not fit the LOWER latch at all.** The bar collar's sleeve has to swallow
>   the coil at FREE length plus a `MIN_WALL_2P` back wall, and from the cup's floor it
>   has 25.6 − 11.2 − 1.6 = **12.8**. That is 2.2 short of the coil itself, so no
>   installed length and no chamfer could rescue it — the constraint is `free < 12.8`,
>   full stop.
> * **The collar cannot grow.** Its ±Y face IS the bar tower's half-width (`pedal_bar`
>   asserts the two are equal), so widening it widens the tower by 6.4 mm; and its cup
>   floor is pinned by a peak whose flank runs parallel to the mortise's 45° flank.
> * **10 mm free is too weak.** It has to preload at under 10 mm installed while still
>   clearing solid at full stroke, which leaves a window a few tenths wide and about
>   2–3 N of hold against the 4 N the latch was designed around.
>
> So: buy the 15 mm part and snip it to 12. Cutting **raises** the rate (k scales 1/n —
> the same arithmetic this BOM already spells out for the knee coil), which is what puts
> the forces back where they started rather than merely near them: **3.8 N hold /
> 11.4 N press against the design's 4.0 / 12.05**, with no geometry change anywhere in
> either latch. ⚠ **Cut to leave at most 10 total turns** — at 12 the coil binds under
> the thumb before the button bottoms.

> **LEVER FEEL SPRING — DECIDED 2026-09-21 (user): uxcell blue die spring, Ø10 × 30,
> [B0B772B9V2](https://www.amazon.com/dp/B0B772B9V2), $9.99 / 20.** Supersedes the note
> below: the custom Ø6 × 1.4 coil had no stock source and topped out ~1 kg at the knee.
> The user's kitchen-scale test put the good feel at ~1 kg; the chosen range is **0.5 – 1 kg
> at the knee**, set by the M4 preload screw.
>
> * JIS light-load (blue) die spring: hole Ø10 / rod Ø5, 30 free (±2), 142.2 N at the 40%
>   max (12 mm) → **~11.9 N/mm** (published max load ÷ max deflection — **measure on arrival**).
> * Worked at ≤ 80% of max for long life (9.6 mm, 114 N — ASSUMED, uxcell publishes no life
>   rating). At LOBE_RC 9.5 the stroke is 4.75, so the preload screw spans ~4.9 mm:
>   **~0.55 kg (min preload) → ~1.1 kg (max)** at full throw, knee at the 100 mm arm tip.
> * Length is set by the RANGE (≈ 15 mm × max/min), diameter by the TOP force — a 2:1 range
>   fits in 30, shorter than the old 41.4 bay; the pocket grows Ø6.6 → ~Ø10.5.
> * One pack of 20 covers every lever's main + half-stop (12) with spares, if the half-stop
>   takes the same SKU. Housing re-packaging (Ø10.5 × 30 bay) is the next step, not done yet.
>
> **LEVER / PEDAL FEEL SPRING — uxcell CANNOT supply this one, 2026-09-16.** The user
> asked whether the same supplier could cover it. It cannot, and the reason is in the
> spec rather than in the supplier:
>
> `knee_lever.HS_SPR` is **Ø6.0 OD × 1.4 mm wire**, which is a **spring index of 3.29**
> (mean Ø4.6 ÷ 1.4). Commodity coilers wind C ≥ 4 — below that the wire galls on the
> mandrel and springback goes non-linear — so *no* catalogue stocks it. That is why the
> search comes up empty rather than merely expensive.
>
> What uxcell actually stocks in this envelope is pen-grade: their Ø6, Ø8 and Ø10 × 40 mm
> families all top out at **1.0 mm wire**. The heaviest with a published load is
> [B08VF32B2G](https://www.amazon.com/dp/B08VF32B2G) (Ø8 × 1.0 × 40 free, 31.4 N at 26 mm
> = **2.24 N/mm**) — against the **17.3 N/mm** the feel needs. Five to eight times too
> soft; there is no way to make that up with installed length.
>
> **Two ways out, and both belong to whoever owns `knee_lever.py`:**
> 1. **Grow the OD.** At Ø7.4 × 1.4 the index is 4.3 and 17.3 N/mm wants 8.9 active
>    coils, solid 15.2 — comfortably inside the 42 free length. At Ø8.0 × 1.4 it is
>    6.7 coils, solid 12.1. Either is an ordinary windable spring. The blocker is the
>    note at `HS_SPR_OD`: *"arm width-limited — can't grow to drop stress"*. The
>    question is whether the arm can find **1.4–2.0 mm**.
> 2. **Buy it as a specialty part** at Ø6 × 1.4 from a coiler who will wind C 3.3 —
>    which is exactly the quote-only route the leadscrew sourcing rule rejects, and the
>    kind of order that ran $40+ before.
>
> McMaster's metric table does carry springs in this force class (their Ø12 × 2.0 × 18 is
> 38.7 N/mm at $22.28/5), so a stock answer probably exists there once the OD is settled
> — but it is not worth filtering for until the arm question is answered, because the OD
> is the input.
>
> **CAD, 2026-09-21 (`knee_lever.py`):** cartridge rebuilt around the die spring. The printed
> guide post and the printed hollow back-stop thread are GONE. Each cartridge now takes TWO
> M4 × 10 cup set screws (the existing SKU, 2.0 key) in TWO heat-set inserts in its back wall:
> TENSION on the axis (pushes the seat washer) and POSITION 9.4 above it (socket end bears
> on a washer in the housing; its protrusion is the cartridge's X home, ±1.6). Per control that
> is **+4 M4 × 10 set screws, +4 M4 inserts, +4 washers** — not yet folded into those rows'
> quantities (both already carry recount warnings). Housing −10.4 in X (−78.1 → −67.7, after the 3.2 front wall); lever
> 20 → 24 wide so the 14-wide cartridges sit on their lobes. The FOOT PEDAL housing grew 6.15
> deeper in guitar +Y (`foot_pedal.Y_GROWTH`), into the 15.6 of bar behind it.
>
> **CAD, 2026-09-30 (`knee_lever.py`): BUTTON HEADS, NOT SET SCREWS.** Both adjusters are
> **M4 × 10 button heads** on the 2.5 mm key — same inserts, same washers, heads out the back.
> The POSITION head sits on its washer at the bottom of a 3.1-deep recess in the housing's
> rear wall; the TENSION head rides a Ø8.4 way through that wall. The wall is 6.4 (was 4.2) so
> neither head ever stands out of the housing, which makes every housing 2.2 longer in −X, and
> the preload range is 4.2 (was 4.8): the advance ends when the head lands on the cartridge.

| ~~**TRRS cable, 4C jack-to-plug**~~ **SUPERSEDED 2026-09-21 by the pogo boards (Connectors → Leg blind-mates)** | [Tensility 10-02135](https://www.digikey.com/en/products/detail/tensility-international-corp/10-02135/7606584) — 3.5 mm **4-conductor TRRS**, phone JACK to phone PLUG, 914 mm (3.0 ft), 28 AWG shielded, $5.31, 420 in stock | **2** | DigiKey [d] | **THE ONE CABLE SKU FOR THE WHOLE LEG.** Its own drawing gives the parts, which is why it is here rather than an envelope: plug **3.5 × L20.7**, jack **3.5 × 7.8 × L25.8**, cable Ø3.8. **One is left WHOLE** as the leg's lead — female up (floating in the fixed tenon at the top joint), male down (floating in the adjust tenon at the bottom) — which is exactly the handedness the user's rule wants, since the part with the latch is always female. **One is CUT IN HALF** (user), and a jack-to-plug cut in half is the two pigtails this instrument needs and nothing else: the MALE half fixed in the body adapter at the top, the FEMALE half fixed in the pedal bar at the bottom, both stripped and crimped to JST-XH. A plug-to-plug cut in half would have given two males and left the bar without a female |
| ~~**TRRS float spring**~~ **SUPERSEDED 2026-09-21 (pogo boards: no float spring)** | Compression, **Ø8.0 OD × 0.7 wire × 20.0 free**, **ID 6.6**, 304 SS (rate ~0.75 N/mm, bracketed 0.6–0.9; **measure on arrival**) | 1 (+ 4 spare) | [uxcell B0C33C21K9](https://www.amazon.com/dp/B0C33C21K9) — 5 to a pack, used **AS BOUGHT** | **$6.29 / 5** [a] | SECOND SKU, and not a preference: the coil has to end up ON the lead, and a lead has two ends — the moulded jack (Ø9.7) and the moulded far plug (Ø6.1). The latch coil's 3.8 ID passes neither, so no assembly order puts it there and the joint was unbuildable with it (user found this). **ID 6.6 clears the far plug by 0.5.** Installed 13.80 → **4.7 N at rest / 6.9 N seated**. The installed length is the SOLID FLOOR here, not the preload target: at 0.75 N/mm a 5.0 N target would want 13.33 and the coil would go solid before the leg seats |


> ✅ **THE BEND RADIUS IS RESOLVED — the duty cycle is what settles it (user, 2026-09-18).**
> This lead is **SET ONCE**: the leg's height is chosen at first setup and again only if
> the instrument is resold. So the coil is a static form bent once, not a flexing
> member, and fatigue — the usual reason to respect a bend radius — does not apply.
> What breaks at a tight radius is the **foil**, and the foil does no work here: the
> shield is one of the four CIRCUIT conductors (assembly drawing: D → shield → D,
> sleeve = GND), the spiral serve carries that current and survives bending, the 3.5 mm
> connector has no shield continuity through the mate anyway, and CAN_H/CAN_L are not a
> twisted pair in a round 4C cable, so nothing was screening them to begin with.
> Outermost-conductor strain is ~14% at the design's worst radius against ~5% at the
> published one; annealed copper breaks at 20–30% and strands redistribute by slip.
> `leg_trrs.CABLE_BEND_STATIC` (7.5) records the deviation and its licence, and the
> mandrel asserts against it.
>
> **SEARCHED, AND THERE IS NOTHING BETTER TO BUY.** Tensility's whole 2750-part
> catalogue holds exactly **two** 4C audio assemblies — 10-02135 and 10-02133 — and both
> use the same 30-00179 wire at Ø3.8 / 22.8. The wider market for 4-pole 3.5 mm leads is
> consumer headphone cable, which publishes no bend radius at all, which is the reason
> this project is on Tensility. A **thinner** lead would genuinely help (Ø3.0 at 3×OD
> clears the cavity outright) and unshielded would cost us nothing electrically — but
> not at the price of an unpublished datasheet.

> ⚠⚠ **READ THE VENDOR'S PAGE, 2026-09-18 — and it BLOCKS the coil (user asked).**
> Tensility publish, for 10-02135: wire outer **Ø3.8** ✓, cable length **915** (not the
> 914 above, distributor rounding), price **$5.01** (not $5.31), PVC jacket, **spiral +
> foil** shield, and a **MINIMUM BEND RADIUS OF 22.8 mm** — 6× the jacket, which is what
> a foil shield costs. Connectors are **50-00397** plug (Ø3.5 × L20.7) and **50-00041**
> jack (Ø7.8 × L25.8); the jack figures confirm what was already modelled.
>
> **22.8 kills the coil-in-the-leg.** A coil at that radius needs a mean diameter of
> 45.6, and the adjust sleeve's cavity measures Ø24.7 — a 20.9 cap. No turn count
> reconciles those. Two other places also fail it: the coil as designed (r 9.5 relaxed,
> 7.9 stretched) and the bar's wiring chamber turn (r 6.2). Only the adjust tenon's jog
> passes, because it is nearly straight. `src/coil_mandrel.py` now asserts against
> `leg_trrs.CABLE_BEND_R` and is UNREGISTERED from the build until this is decided:
> accept exceeding the published radius on a static install, move the slack store out
> of the leg (docs/leg-trrs-routing.md option 2 — the bar's chamber, where nothing caps
> the diameter), or source a lead with a smaller bend radius.
>
> Every bend-radius figure I quoted before this was measured against a 3×OD rule of
> thumb, not against the manufacturer's number. "2.1×OD, tight but acceptable" was the
> wrong yardstick throughout.
>
> ⚠ **STILL OPEN: the plug's modelled BARREL_L.** The vendor gives the 50-00397
> connector as **L20.7**; the model has `BARREL_L` 14.0 plus a Ø6.1 × 14 overmould that
> is not a published figure at all. Their "connector length" is the CONNECTOR, not the
> finished moulded end, so the two are not the same measurement — but 14 is not 20.7
> either, and how much barrel protrudes decides the mate depth. `tools/check_part_specs.py`
> reports it every run. The bought parts are now checked against the vendor's own page
> by that tool, for all three SKUs.

> **THE INLINE JACK IS Ø7.8 × 25.8, NOT Ø9.7 × 40 — and that one number deleted a
> subsystem (2026-09-17).** `leg_trrs.JACK_D`/`JACK_L` were an ENVELOPE ("BOM: 9.1..9.7,
> pick high", "≤ 40"), never a part, and the bottom joint was being designed around them.
> On the envelope the pedal bar could not hold an inline jack at all: the chain wanted 60
> below the mortise floor against 25.1 available, so the answer was either a **PCB-mount
> jack on a small board** or **raising the bar's tower 36.5**, which would have lifted the
> foot attach point and cost the low end of the height adjustment 6.5 ladder holes.
>
> Neither is needed. The jack's nose already lives 17.0 up inside the tenon's bore
> (`bar_trrs.NOSE_H`), so only **25.8 − 17.0 = 8.8** sits below the floor:
>
> | | envelope (Ø9.7 × 40) | real part (Ø7.8 × 25.8) |
> |---|---|---|
> | below the mortise floor | 60.0 | **8.8** |
> | against 25.1 usable | 36.5 of raise, or a PCB | **fits, 14.7 spare** |
> | jack back, bar z | — | 22.30, with the trough at 3.95–20.45 right beside it |
>
> So: **no board, no solder, no raise, no height-adjustment penalty, and no new SKU** —
> the bar's female is the cut half of the same cable the leg already uses. The user's own
> question ("can we just use the other half of that cut cable?") is what forced the check;
> the only correction is that it has to be a JACK-TO-PLUG cable rather than the
> plug-to-plug one originally specced for the top, or the cut gives two males.
>
> ⚠ **`leg_trrs.JACK_D` 9.7 / `JACK_L` 40 are now known to be over-generous** at the TOP
> joint too. They are not wrong — the chain works and is verified — but the fixed tenon is
> carrying ~14 of length and ~2 of diameter it does not need. Worth reclaiming when that
> joint is next opened, and NOT worth reopening it for on its own. Note the bore there
> cannot simply follow the jack down: `JACK_BORE_D` is set by the Ø8.0 COIL, not the jack.

> **SPRING SOURCING, 2026-09-16 — OUTCOME: both leg springs are uxcell parts used AS
> BOUGHT, $13.28 the pair.** Getting there took three rejected answers and one
> observation from the user that unlocked it.
>
> The constraint that drove everything is the bar collar's sleeve: it must swallow the
> coil at **FREE** length plus a `MIN_WALL_2P` back wall, and from the cup's floor it
> had **12.8**. uxcell stocks this wire and OD at 5 / 10 / 15 / 20 free and nothing
> between, so a 15 mm coil was 2.2 too long and a 10 mm one was shorter than the
> installed length — not even in contact. The three dead ends:
> * **cut a 15 to 12** — reproduced the design almost exactly, rejected by the user: a
>   hand operation with no feedback.
> * **widen the bar** — `TOWER_WY` also drives `BAR_Y0/BAR_Y1`, so +6.4 is +12.5% of the
>   whole bar's cross-section (≈144 cm³, same on print time) and moves the player-side
>   face 3.2 mm.
> * **McMaster 2006N221** — fits, published rate, forces on the nose, **$51.30 the pair**
>   against $13.28. Worked and committed, then backed out on cost.
>
> **What unlocked it (user):** the collar carries TWO T rails *and* a screw. Drop the rail
> on the screw's side, and the ring's arm on that side is free to run out to the collar's
> own face — which lets the spring's axis move outboard, which pays one-for-one for
> pulling the cup's floor back −Y. The sleeve went **12.8 → 16.0** and the bought coil
> fits with 1.0 to spare.
>
> | | before | after |
> |---|---|---|
> | rails | 2, at ±22.75 | **1, at −22.75** — opposite the screw at +21.20 |
> | ring arm | ±19.80, symmetric | −X 19.80 (railed) / **+X 23.00** (spring, free) |
> | spring axis | +15.20 | **+18.40** |
> | cup floor | 11.20 | **8.00** |
> | sleeve | 12.80 | **16.00** |
>
> The spring stays on **+X**, with the pad — the user's first instruction was to move it
> to −X, but a rail on the spring's side is what pins this whichever side it is, and −X
> is where the surviving rail has to be to sit opposite the screw. The spring was put on
> the pad's side deliberately so the thumb's line and the coil's coincide.
>
> ⚠ **Both rates are still estimates** — uxcell publishes neither rate nor turn count, so
> both springs carry a measure-on-arrival step. `latch.SPR_RATE` and `leg_trrs.SPR_RATE`
> are single-source constants and every force and length derives from them.

> **LEVER / PEDAL FEEL SPRING — uxcell CANNOT supply this one, 2026-09-16.** The user
> asked whether the same supplier could cover it. It cannot, and the reason is in the
> spec rather than in the supplier:
>
> `knee_lever.HS_SPR` is **Ø6.0 OD × 1.4 mm wire**, which is a **spring index of 3.29**
> (mean Ø4.6 ÷ 1.4). Commodity coilers wind C ≥ 4 — below that the wire galls on the
> mandrel and springback goes non-linear — so *no* catalogue stocks it. That is why the
> search comes up empty rather than merely expensive.
>
> What uxcell actually stocks in this envelope is pen-grade: their Ø6, Ø8 and Ø10 × 40 mm
> families all top out at **1.0 mm wire**. The heaviest with a published load is
> [B08VF32B2G](https://www.amazon.com/dp/B08VF32B2G) (Ø8 × 1.0 × 40 free, 31.4 N at 26 mm
> = **2.24 N/mm**) — against the **17.3 N/mm** the feel needs. Five to eight times too
> soft; there is no way to make that up with installed length.
>
> **Two ways out, and both belong to whoever owns `knee_lever.py`:**
> 1. **Grow the OD.** At Ø7.4 × 1.4 the index is 4.3 and 17.3 N/mm wants 8.9 active
>    coils, solid 15.2 — comfortably inside the 42 free length. At Ø8.0 × 1.4 it is
>    6.7 coils, solid 12.1. Either is an ordinary windable spring. The blocker is the
>    note at `HS_SPR_OD`: *"arm width-limited — can't grow to drop stress"*. The
>    question is whether the arm can find **1.4–2.0 mm**.
> 2. **Buy it as a specialty part** at Ø6 × 1.4 from a coiler who will wind C 3.3 —
>    which is exactly the quote-only route the leadscrew sourcing rule rejects, and the
>    kind of order that ran $40+ before.
>
> McMaster's metric table does carry springs in this force class (their Ø12 × 2.0 × 18 is
> 38.7 N/mm at $22.28/5), so a stock answer probably exists there once the OD is settled
> — but it is not worth filtering for until the arm question is answered, because the OD
> is the input.

| ~~**TRRS float spring**~~ **SUPERSEDED 2026-09-21 (pogo boards: no float spring)** | Compression, **Ø8.0 OD × 0.7 wire × 20.0 free**, **ID 6.6**, 304 SS (rate ~0.75 N/mm, bracketed 0.6–0.9; **measure on arrival**) | 1 (+ 4 spare) | [uxcell B0C33C21K9](https://www.amazon.com/dp/B0C33C21K9) — 5 to a pack, used **AS BOUGHT** | **$6.29 / 5** [a] | SECOND SKU, and not a preference: the coil has to end up ON the lead, and a lead has two ends — the moulded jack (Ø9.7) and the moulded far plug (Ø6.1). The latch coil's 3.8 ID passes neither, so no assembly order puts it there and the joint was unbuildable with it (user found this). **ID 6.6 clears the far plug by 0.5.** Installed 13.80 → **4.7 N at rest / 6.9 N seated**. The installed length is the SOLID FLOOR here, not the preload target: at 0.75 N/mm a 5.0 N target would want 13.33 and the coil would go solid before the leg seats |

> **SPRING SOURCING, 2026-09-16 — OUTCOME: both leg springs are McMaster catalogue
> parts, used as bought, $51.30 the pair.** The user's constraints, in the order they
> arrived, were: affordable; from uxcell if possible; no cutting; use the parts as they
> come; geometry may move so long as the 1.6 mm and 45° rules hold. Those turn out to be
> incompatible with uxcell for the LATCH, and the reason is the bar collar's 12.8 mm of
> sleeve — see that row. uxcell would have been $13.28 and the difference is **$38**;
> the user's call was that a McMaster order is likely anyway.
>
> **What the switch bought, beyond fitting:** both rates are now PUBLISHED rather than
> estimated. Every earlier version of this joint carried a measure-the-spring-on-arrival
> step, because uxcell publishes neither rate nor turn count. That step is gone.
>
> **What it cost in geometry** (all verified against both rules):
> * the slider's spring bore opened 5.40 → 6.03 for the fatter coil, and was
>   **teardropped** while it was being touched — the slider prints +X up, so that bore is
>   horizontal and its upper arc was already ~21 mm² past 45°. It is now **zero**, i.e.
>   better than before the spring changed.
> * the bar latch's CUP got its own `CUP_SEAT_CLR` of 0.2 instead of inheriting the
>   slider's 0.4 running clearance. The cup is a SEAT the coil's end rests in, not a bore
>   it slides down, and that distinction is worth 0.2 of diameter — which is exactly what
>   the site had left. At the slider's clearance the cup overhung the ring's arm by 0.015,
>   and the axis could not move inboard to fix it (`SPR_X` also sets the channel peak,
>   whose flank must keep `MIN_WALL_2P` off the mortise's 45°; one bead in put it at 1.05).
>   Widening the ring's arm instead broke the T-rail's room. The seat clearance was the
>   only lever that did not cascade.
> * `check_thin` clean on `latch_slider`, `bar_latch_collar`, `fixed_tenon`,
>   `leg_trrs_throat`; overhang delta on `bar_latch_collar` +0.02 mm² (noise).

> **LEVER / PEDAL FEEL SPRING — uxcell CANNOT supply this one, 2026-09-16.** The user
> asked whether the same supplier could cover it. It cannot, and the reason is in the
> spec rather than in the supplier:
>
> `knee_lever.HS_SPR` is **Ø6.0 OD × 1.4 mm wire**, which is a **spring index of 3.29**
> (mean Ø4.6 ÷ 1.4). Commodity coilers wind C ≥ 4 — below that the wire galls on the
> mandrel and springback goes non-linear — so *no* catalogue stocks it. That is why the
> search comes up empty rather than merely expensive.
>
> What uxcell actually stocks in this envelope is pen-grade: their Ø6, Ø8 and Ø10 × 40 mm
> families all top out at **1.0 mm wire**. The heaviest with a published load is
> [B08VF32B2G](https://www.amazon.com/dp/B08VF32B2G) (Ø8 × 1.0 × 40 free, 31.4 N at 26 mm
> = **2.24 N/mm**) — against the **17.3 N/mm** the feel needs. Five to eight times too
> soft; there is no way to make that up with installed length.
>
> **Two ways out, and both belong to whoever owns `knee_lever.py`:**
> 1. **Grow the OD.** At Ø7.4 × 1.4 the index is 4.3 and 17.3 N/mm wants 8.9 active
>    coils, solid 15.2 — comfortably inside the 42 free length. At Ø8.0 × 1.4 it is
>    6.7 coils, solid 12.1. Either is an ordinary windable spring. The blocker is the
>    note at `HS_SPR_OD`: *"arm width-limited — can't grow to drop stress"*. The
>    question is whether the arm can find **1.4–2.0 mm**.
> 2. **Buy it as a specialty part** at Ø6 × 1.4 from a coiler who will wind C 3.3 —
>    which is exactly the quote-only route the leadscrew sourcing rule rejects, and the
>    kind of order that ran $40+ before.
>
> McMaster's metric table does carry springs in this force class (their Ø12 × 2.0 × 18 is
> 38.7 N/mm at $22.28/5), so a stock answer probably exists there once the OD is settled
> — but it is not worth filtering for until the arm question is answered, because the OD
> is the input.

| ~~**TRRS float spring**~~ **SUPERSEDED 2026-09-21 (pogo boards: no float spring)** | Compression, **Ø8.8 OD × 0.8 wire × 14.5 free**, **ID 7.2**, 302 SS, **rate 1.91 N/mm PUBLISHED**, compressed 6.1 at max load | 1 (+ 4 spare) | [McMaster 2006N232](https://www.mcmaster.com/2006N232/) — pack of 5, used **AS BOUGHT** | **$15.98** [m] | SECOND SKU, and it is not a preference: the coil has to end up ON the lead, and a lead has two ends — the moulded jack (Ø9.7) and the moulded far plug (Ø6.1). The latch coil's 4.37 ID passes neither, so no assembly order puts it there and the joint was unbuildable with it (user found this). **ID 7.2 clears the far plug by 1.1.** Installed 11.88 → **5.0 N at rest / 10.7 N seated**; the rest figure is the one that matters (it holds the jack against its keeper with the leg off) and `leg_trrs.PRELOAD_TARGET` sets it directly |

> **SPRING SOURCING, 2026-09-16 (user: Lee Spring has bitten us on price before).**
> Both springs are now catalogue parts at **$13.28 the pair** rather than a Lee Spring
> order that would have run ~$40 for the same two envelopes. McMaster stayed unreadable
> — it 302s every deep link to its home page for a session it does not recognise, and
> that is a block worth respecting rather than defeating — but Amazon's catalogue reads
> fine in a real browser session, and uxcell stocks this whole family in 5s and 10s.
>
> **WHAT IS NOT YET SETTLED, and it is the rate, not the part.** Neither listing
> publishes a spring rate, and neither is the 12 mm free length the model assumes. Both
> are LONGER, which for a given OD and wire means more coils and a SOFTER spring:
>
> | | model assumes | bought part | derived rate (G 69 GPa, coils est.) |
> |---|---|---|---|
> | latch | Ø5.0 × 0.6 × 12 free, 2.5 N/mm | Ø5.0 × 0.6 × **15** free | **1.6–2.4 N/mm** — same family |
> | TRRS float | Ø8.0 × 0.7 × 12 free, 2.5 N/mm | Ø8.0 × 0.7 × **20** free | **0.5–0.9 N/mm** — 3–5× softer |
>
> The latch lands close enough that its installed length barely moves. The TRRS float
> does not: at ~0.7 N/mm, 5 N of preload wants ~7 mm of squeeze rather than 2, so the
> coil would install at ~13 mm and `SPR_SEAT` drops ~3 mm down the tenon (there is room
> — the tenon is 252 long). Seated force falls from 12.5 N to ~7.5 N, which is still
> far more than a TRRS contact needs.
>
> **So: COUNT THE COILS ON ARRIVAL and re-derive.** `leg_trrs.SPR_RATE`/`SPR_FREE` and
> `latch.SPR_FREE` are single-source constants and the z-chain falls out of them; the
> asserts already guard solid height. Do not order a second time to chase 12 mm free —
> the geometry is the cheap thing to move here, and the spring is not.
> **MCMASTER CROSS-CHECK, same day.** Their catalogue does read in a signed-in Chrome
> session (it refuses an automated browser, not a browser) and it publishes the column
> uxcell does not. Nearest catalogue parts to our two envelopes, 302 SS, rate published:
>
> | | part | geometry | rate | price |
> |---|---|---|---|---|
> | latch | 2006N221 | 12.5 × Ø5.63 × ID 4.37 × 0.63 wire | **1.96 N/mm** | $17.66 / 5 |
> | float | 2006N232 | 14.5 × Ø8.80 × **ID 7.20** × 0.80 wire | **1.91 N/mm** | $15.98 / 5 |
>
> **The useful part of that is not the parts, it is the number.** Two springs of this
> geometry both land at ~1.9 N/mm, so the model's **2.5 N/mm was optimistic** — and the
> uxcell parts, being LONGER at the same OD and wire, will sit at or below 1.9. That
> converts the open question from "unknown" to "bracketed": 1.5–2.0 for the latch,
> 0.6–0.9 for the float, and the re-derive on arrival is a confirmation rather than a
> discovery.
>
> **DECIDED (user): buy the uxcell pair, $13.28.** The McMaster rows below stay as a
> reference for the rate, not as an order.
>
> **AND THE MODEL NOW MATCHES THE BOUGHT COILS, not the ones it was drawn around.**
> Free length is a KNOWN fact about the parts, and it is not 12 mm; the chain has
> been re-hung on it. What each side did with that:
>
> * **LATCH — no change needed, and that was checked rather than assumed.** Installed
>   length is `SPR_SEAT + SPR_GAP` = 10.40 and full press is 7.20, so the binding
>   constraint is the coil's SOLID height. The bought 15 mm-free coil is fine at any
>   count up to **11 turns** (solid 6.6) and only binds at 12 (solid 7.2), which on
>   0.6 wire would be a 1.25 mm pitch — nearly closed at rest, which catalogue
>   springs are not. Preload rises from 4.0 N to ~8.7 N at the bracketed rate, and a
>   latch button that is harder to rattle open is the right direction.
> * **TRRS FLOAT — the chain moved, because at 10.0 installed the bought coil would
>   have gone SOLID before the leg seated**, at any count from 10 turns up. Installed
>   is now derived rather than chosen: `SPR_SOLID + 1.0 + FLOAT` = **13.8**, off a
>   worst-case 14 turns (solid 9.8). `SPR_SEAT` drops 3.8 mm down the tenon, which
>   has 192 mm below it. Forces land at **4.65 N at rest / 6.90 N seated** instead of
>   5.0 / 12.5 — the rest figure is what matters (it holds the jack on its keeper
>   with the leg off) and it is essentially unchanged.
>
> `SPR_RATE` is the ONE estimated number left (0.75, bracketed 0.6–0.9). Measure it on
> arrival and edit that constant alone — both forces and the whole z-chain derive.
>
> On price McMaster is not close — 6 latch springs is two packs, so the full basket is
> **$51.30 against $13.28**. The one that might be worth buying there anyway is the
> FLOAT: 2006N232 has ID 7.20 against our required 6.5, which is 1.1 of clearance over
> the lead's moulded plug instead of 0.5, and its rate is known before it ships. That
> middle basket is $22.97.
>
> Alternative if the rate comes back unusable: a **300-piece 304 SS assortment**
> ([Dianrui, $6.99](https://www.amazon.com/s?k=Dianrui+300PCS+Compression+Springs+Assortment+Kit))
> covers 23 sizes and would let the rate be chosen by test rather than by catalogue.

| **M4 mount screw** | M4 × 0.7, 12 mm, 18-8 SS **button head** (ISO 7380, **2.5 mm hex** — the instrument's one key) | 6 | [McMaster 92095A192](https://www.mcmaster.com/92095A192/) | $14.77 / pack [m] | 2 optical-strip board grips, into the bridge endplate plinth's inserts. + **4 leg LOCK PINS** (one per corner: in through the endplate's end face, through the body adapter's tongue, into an insert in the chassis — the one screw that holds a leg on AND the endplate down; `legs.lock_pin_joint`, `LOCK_SCREW_L` = 12). *This row used to list 4 leg-sleeve pinch bolts into inserts, but legs.py draws those as thread-formed GRUBS — they come back here when they become button heads.* **M4 × 0.7** (coarse) to match the inserts — NOT the M4 × 0.5 fine-thread 90751A120. (The old "pickup X/Y clamp screw" is retired — the pickup Y-lock is now the -Y cup-tip retention grub above) |
| **M4 × 10 button screw** | M4 × 0.7, 10 mm, 18-8 SS button head (ISO 7380, 2.5 mm hex) | 69 | [McMaster 92095A-series](https://www.mcmaster.com/92095A192/) | ~$12 / pack [m] | CAN tee hold-downs, one per bus-A tee (`wiring.tee_hold`, on each board's +X edge). BESIDE the board, not through it: the head laps the board edge by 1.3 and clamps it onto its cradle boss (cadkit `pcb_cradle(hold_edge=...)`), so the tee needs no mounting hole. 10 mm puts the tip 0.10 above the insert anchor's floor (asserted in wiring.py). Replaces one M2 per bus-A tee; the 2 bus-B PLACEHOLDER tees keep their M2 for now (no clear spot for an M4 in that bay, and they are slated to fold into the lever PCBs). The leg end-wall lock screws are the same SKU but are counted with the leg-stack rework. **Confirm the ×10 length suffix at purchase.** **+ 55 on the sensed controls (2026-09-30), × 11:** 2 POSITION + 2 SPRING-TENSION in each pair of feel cartridges (they were cup set screws on a 2 mm key), and 1 in the −Y end of each axle with an M4 washer under it — the axle's axial retention, in place of the M2 grub in the lever hub. |
| ~~**TRRS pigtail** (adapter → chassis jack)~~ | **SUPERSEDED 2026-09-17 — folded into the jack-to-plug row above.** It specified **10-02155**, a PLUG-TO-PLUG cable cut in half. That is the right idea and the wrong cable: cut in half it yields TWO MALE pigtails, and the pedal-bar end of the instrument needs a FEMALE one. **10-02135** is the same cable with a jack on one end, so one cut gives the male pigtail for the body adapter AND the female pigtail for the bar — and it is the same SKU the leg's own lead already is. Same 50-00397 plug the design is dimensioned to (overmould Ø6.1 × 14, barrel Ø3.5 × 14, cable Ø3.8), so nothing upstream moves | — | — | — |
| **M4 collar screw** | M4 × 0.7, 30 mm, 18-8 SS button head (hex drive) | 1 | [McMaster 92095A-series](https://www.mcmaster.com/92095A192/) | ~$12 / pack [m] | the ONE screw locking the pedal-bar latch collar to the bar's tower. The collar is held by a cadkit slide joint — two T rails in slots in the tower's top — which locks every direction but the one it slid in along; this screw locks that one. 30 mm because it passes the collar's full 22.4 height (head recessed 2.4 in the mouth face) before biting 10 into its insert in the tower. **Confirm the ×30 length suffix at purchase.** |
| **M4 keyhead height screw** (was "hold-down") | M4 × 0.7, **20 mm**, 18-8 SS **button head** (ISO 7380, 2.5 mm hex) | 10 | [McMaster 92095A196](https://www.mcmaster.com/92095A196/) | $9.47 / pack 50 [v] | ⚠ **2026-09-30: 20 mm, NOT 18.** McMaster stocks 16 and 20 in this family and no 18. `nut_block.HS_SCREW_L` is 20 now: it is the pickup jacks' SKU already (one row, `m4_button_20`, 15 an instrument) and leaves 8.2 mm of floor over the heat-set where 16 leaves 4.2; travel is unchanged at 6.83. **The eleventh screw is no longer counted:** it was the single +Z keyhead hold-down, which the model does not draw — the keyhead is locked by the leg's lock pin (`keyhead_endplate.py`, `legs.lock_pin_joint`). If a dedicated hold-down returns, it takes this same 20. History follows.<br>**THE 4 LEG LOCK PINS LEFT THIS ROW** (2026-09-17): restoring the feet's SERVICE POSITION made them **M4 × 40** (their own row below) -- the second hole can only go in a tenon whose mortise runs the foot's full length, and at both ends that is the third station in, 39.96 from the end face. 18 reached 20.4.<br>Also the single +Z screw locking the merged keyhead nut-block endplate down — up from the floor bottom, forming its own thread in a Ø3.6 pilot in the PETG-GF boss, exactly as the leg lock screws do (the rest of the body is held by joinery). **Confirm ×18 is stocked at purchase** (16 and 20 are the common neighbours; the pilot depth decides which) **+ 10 keyhead insert HEIGHT screws** (prototype): one under each string's sliding insert, threading a heat-set in the endplate slab and pushing the insert's foot up; its head hangs in a cavity in the chassis corner rib, reached with the 2.5 mm key from below (strings 1-2: slide the +Y keyhead leg out to its service position, legs.SERVICE_SLIDE). |
| **M3 × 12 socket head** | M3 × 0.5, 12 mm, socket head cap (ISO 4762, **2.5 mm hex**, Ø5.5 head) | 10 | [McMaster 91292A114](https://www.mcmaster.com/91292A114/) | ~$7 / pack 100 [m] | The 10 belt clamps' draw screws, one per string (`belt_tensioner.SCREW_L`), turned with the BALL END of the instrument's one 2.5 mm key. **The only M3 on the instrument** (user, 2026-10-05): nothing M4 fits in line with a 5 mm belt, and the socket-head M3 shares the key. It replaces the M4 × 35 button head of the old clamp. Confirm the SKU at purchase. |
| **M3 insert (belt clamps)** | M3 × 0.5 brass insert, about Ø4.6 × 4 | 10 | — | ~$0.15 each [m] | Dropped into a side pocket in each clamp's half B as a captive nut, behind a shoulder; not heat-set. ⚠ **No SKU picked**: `belt_tensioner.INS_D` / `INS_L` are a typical short insert. Choose one, measure it, set those two numbers before printing. |
| **M4 × 40 button screw** | M4 × 0.7, 40 mm, 18-8 SS button head (ISO 7380, 2.5 mm hex) | 4 | [McMaster 92095A-series](https://www.mcmaster.com/92095A192/) | ~$12 / pack [m] | **THE 4 LEG LOCK PINS** (`legs.lock_pin_joint`, one per corner): each threads a heat-set insert in its own ENDPLATE -- in the wall the deleted straight tongue used to hollow out -- and carries on through a Ø4.4 clearance hole in the chassis floor into the foot's tenons in the bottom grid, which it pins. That is the whole leg retention: the foot cannot slide back out along Y past it, and the same screw holds the endplate to the chassis. **Why 40 and not the ×18 this row replaces:** the +Y feet have a SERVICE POSITION (`legs.SERVICE_SLIDE`, 25.6 outboard) where the same screw goes into a SECOND hole in the foot, and out there the only material left under the axis is a tenon whose mortise runs the foot's full 44.8 -- at both ends the THIRD station in, 39.96 from the end face. No shorter stocked length reaches it (35 lands 0.74 in, which pins nothing). Seated it now crosses all three tenons over the foot instead of one and stops 0.86 short of breaking out of the last. Asserted per corner in legs.py against the real grid. **Confirm the ×40 length suffix at purchase.** |
| ~~**M2 grub screw**~~ | **DELETED 2026-09-30 — no M2 anywhere (user: every fastener is M4 on the 2.5 mm key)** | — | — | — | It held each lever's axle in axially, through the hub wall onto the D-flat. An **M4 × 10 button head + M4 washer in the axle's −Y end** does that now (`knee_lever.py`: `AXLE_END_PROUD`); the washer laps the −Y bearing's inner race. |
| **Axle washer** | **ISO 7089 / DIN 125 M4 flat washer, Ø9 × 0.8, Ø4.3 hole**, 18-8 SS or zinc | **11** (1 per sensed control) | [McMaster](https://www.mcmaster.com/) | commodity | Under the axle's end screw. Ø9 on purpose: wider than the bearing's Ø8 bore, inside its Ø9.6 inner-ring abutment band, so it touches the race that turns with the axle and never the shield. A fender washer is the wrong part. |
| **Threadlocker, plastic-rated** | surface-curing threadlocker for plastic fasteners, e.g. **Loctite 425** — NOT anaerobic 242/243 | 1 small bottle | Loctite / Henkel via industrial supply (McMaster, Grainger) | TBD [m] | Locks each screw-drive **endcap pulley** onto its Tr8×2 rod (10 joints, a drop each). **A deliberate exception** to the no-adhesive joints elsewhere (bridge axle, sensor magnet): with the brass nut run dry for self-locking, friction cannot also keep the pulley from backing off in the lowering direction (0.8–1.0× margin), and there is no room for a set-screw insert under the near-row pulleys. **Why not 242/243:** anaerobic methacrylates can craze thermoplastics and cure poorly in the near-zero gap of a formed thread. **Procedure:** screw the pulley on DRY first so the rod forms its thread, back it off, apply, screw home. ⚠️ **Test on a spare printed pulley first** (crazing, breakaway torque). The pulley is **sacrificial on disassembly** — breaking a locked plastic thread will likely wreck it; it is a cheap 0.2-nozzle reprint. |

## Mechanical hardware — every purchased part, counted from the model (2026-09-30)

**This table is generated from `elec/prices.json` → `mechanical`, which is what
`tools/cost.py` prices.** It supersedes the per-row quantities in the table at the top of
this file wherever the two disagree: these counts come from the dummies the assembly
actually places (`src.build.collect_components()`), measured by bounding box, scaled for
the two things the model does not draw — the eleventh sensed control and three of the
four legs. Cost is per instrument on a **ten-instrument order with whole packs bought**.
[v] = read off the product page that day; [m] = carried from a listing or an older row.

| Part | Per instrument | Vendor | SKU | $ / instrument | | Order arithmetic and notes |
|---|---|---|---|---|---|---|
| `servo42d` | 10 | — | — | $339.90 | [v] | MKS SERVO42D CAN MT (board + MOTOR) -- makerbase3d.com variant table, in stock 2026-09-30. MB is the BOARD ONLY at $22.99 and is the wrong SKU. The listing gives the motor as **40 mm long** (user, 2026-10-01) -- the CAD draws 48; see `src/servo42d.py`. |
| `psu_24v_160w` | 1 | OnlineComponents | GST160A24-R7B | $47.70 | [v] | Mean Well **GST160A24-R7B**, a sealed DESKTOP adapter: 24 V 6.67 A 160 W, IEC C14 inlet, 1.2 m 18 AWG lead ending in a 4-pin locking power DIN (Kycon KPPX-4P). $52.40 at 1, **$47.70 at 10**, 891 in stock 2026-10-01 ([listing](https://www.onlinecomponents.com/en/productdetail/mean-well/gst160a24r7b-48236187.html)); before shipping and any tariff. The page calls it "no longer manufactured" -- Mean Well's own EOL list does not carry it and its datasheet was revised 2026-04; check at order. Fallback: TRC Electronics $61.12 at 10, 1,293 in stock. **Replaces the LRS-150-24** ($20.69), which is a chassis-mount supply with exposed mains terminals and has no home inside the instrument (user, 2026-10-01). Budget: 160 W less LED 25.3, Pi 16.7 and 7.3 of boards leaves ~111 W = **4.6 A for the motors** -- five slewing at the derived 0.8 A. ⚠ **Its plug does not fit the panel's barrel jack** -- see the DC inlet row. Mains cord: not confirmed included. |
| `bearing_688zz_screw` | 10 | Bearings Direct | [688-ZZ](https://bearingsdirect.com/688-zz-mini-ball-bearing-8x16x5-shielded-mr688zz/) | $37.20 | [v] | 10 x $3.72 -- AMPEC 688ZZ, 587 N static published on the listing. The ten screw thrust bearings only: the one seat where the rating is the margin (2.0x). $4.38 each, 5% off at 10; 489 in stock 2026-10-06 |
| `bearing_688zz` | 32 | Fast Eddy Bearings | [TFE234](https://www.fasteddybearings.com/products/10-units-8x16x5-metal-shielded-bearing-688-zz) | $31.68 | [v] | 32 x $0.99 -- 688ZZ for the 10 bridge-axle and 22 lever and pedal seats. 10 for $10.99 (TFE234) or 100 for $98.99 (TFE480), both in stock 2026-10-06. No load rating published; radial load there, 2.3x inside the lowest rating any maker publishes |
| `m4_button_8` | 2 | McMaster-Carr | 92095A189 | $1.11 | [v] | 1 x $11.11 (pack of 100) = $11.11 for 20 needed — M4x8 18-8 button, 2.5 hex -- the two female pogo boards |
| `m4_button_10` | 69 | McMaster-Carr | 92095A190 | $6.61 | [v] | 7 x $9.44 (pack of 100) = $66.08 for 690 needed — M4x10 -- 10 CAN tees, 2 bay boards, 2 fret boards, and per sensed control x 11: 2 position + 2 spring-tension (the feel cartridges) + 1 in the axle's -Y end |
| `m4_button_12` | 2 | McMaster-Carr | 92095A192 | $1.48 | [v] | 1 x $14.77 (pack of 100) = $14.77 for 20 needed — M4x12 -- 1 UI clamp, 1 pickup -Y retention (was a cup set screw; 2.5 mm key now) |
| `m4_button_20` | 17 | McMaster-Carr | 92095A196 | $3.79 | [v] | 4 x $9.47 (pack of 50) = $37.88 for 170 needed — M4x20 -- 10 keyhead nut-height screws (were M4x18, not a stocked length; `nut_block.HS_SCREW_L` = 20 since 2026-09-30), 3 pickup jacks, 2 male pogo boards, 2 optical board through its hand guard (were M4x12 on the bare board) |
| `m4_button_30` | 2 | McMaster-Carr | 92095A198 | $1.46 | [v] | 1 x $14.64 (pack of 50) = $14.64 for 20 needed — M4x30 -- pedal-bar latch collar, one per bar-to-leg joint (model draws one leg) |
| `m3_shcs_12` | 10 | McMaster-Carr | 91292A114 | $0.80 | [m] | M3x12 socket head cap screw (ISO 4762, 2.5 mm key) -- the belt clamps' draw screws, one per string. Price and SKU carried at a guess; confirm at purchase. |
| `m3_insert` | 10 | McMaster-Carr | - | $1.50 | [m] | M3 brass insert, about O4.6 x 4 -- dropped into each belt clamp's half B as a captive nut (not heat-set). NO SKU PICKED. |
| `m4_button_40` | 4 | McMaster-Carr | 92095A200 | $2.03 | [v] | 2 x $10.13 (pack of 25) = $20.26 for 40 needed — M4x40 -- the four leg lock pins |
| `m4_insert` | 84 | McMaster-Carr | 94459A150 | $18.39 | [v] | 17 x $10.82 (pack of 50) = $183.94 for 840 needed — M4 brass heat-set, 4.7 installed. 78 drawn + 4 for the eleventh control + 2 fret boards (the 10 belt clamps take an M3 insert now). AT 840 AN ORDER THIS IS THE DEAREST FASTENER LINE ($183.94) -- $0.22 each at McMaster against a few cents from an import seller; the obvious place to save if a second vendor is acceptable. |
| `washer_m3_9021` | 44 | McMaster-Carr | 91100A120 | $1.49 | [v] | 5 x $2.97 (pack of 100) = $14.85 for 440 needed — DIN 9021 M3 washer O9 x 0.8 -- spring seat + position, 4 per control x 11 |
| `washer_m4_7089` | 11 | McMaster-Carr | - | $0.55 | [m] | ISO 7089 / DIN 125 M4 washer O9 x 0.8, O4.3 hole -- under the axle's end screw, 1 per sensed control x 11. Price carried at a guess; pick the SKU at purchase. |
| `break_dowel` | 10 | McMaster-Carr | 91595A018 | $2.54 | [v] | 2 x $12.70 (pack of 50) = $25.40 for 100 needed — O2 x 4 dowel pin, 52100 -- the nut break pins |
| `guide_rod_o3_5` | 10 | McMaster-Carr | 2900A267 | $18.45 | [v] | 50 x $3.69 (each) = $184.50 for 100 needed — O3.5 M2 HSS drill blank, 73 mm long, Rockwell C60 -- CUT IN TWO for 2 x 35 mm rods, so 5 blanks an instrument. It is hardened: an abrasive wheel job, not a hacksaw. Was guessed at $0.50-1.20 a rod; it is $1.85. |
| `shaft_o8` | 2 | McMaster-Carr | 6112K44 | $8.22 | [v] | 10 x $8.22 (each) = $82.20 for 20 needed — O8 x 200 hardened steel linear shaft, CUT IN HALF for the bridge axle + nut wrap rod (both O8 x 100). Pre-cut 100 mm is 5033N131 at $14.38 EACH or 6459K118 (420 SS) at $10.18, i.e. 2.5-3.5x the price for saving one abrasive cut. |
| `die_spring` | 22 | — | — | $24.20 | [m] | uxcell O10x30 blue die spring, the control feel cartridge |
| `latch_spring` | 6 | Amazon (uxcell) | B0GCZVQFWN | $4.19 | [m] | 6 x $6.99 (pack of 10) = $41.94 for 60 needed — O5 x 0.6 x 15 compression spring -- 4 leg + 2 bar latches (BOM.md). The model draws one leg, so two. |
| `magnet_o6` | 11 | DigiKey | Radial Magnets 8995 | $3.65 | [m] | O6 x 2.5 diametric N35, $0.332 at 10+ per BOM.md -- not re-read today. Was $1.00 here. |
| `leadscrew_tr8x2` | 10 | Temu | goods 605822935500044 | $22.41 | [m] | 4 x $56.03 (2 x 600 mm + 2 nuts) = $224.12 for 100 pieces of 37.7 mm — Tr8x2 SINGLE-START, RIGHT-HAND THREAD (required: dimensions.SCREW_HAND), bought long and cut (user's plan). 100 pieces + a saw kerf each is 3.92 m; a 600 mm rod yields 15, so 7 rods, so 4 two-packs. PRICE IS FROM THE SEARCH PAGE, NOT THE PRODUCT PAGE -- Temu put a CAPTCHA in front of the listing and that is not something to click through. ALSO: nearly every T8 screw on Temu is the 3D-printer part, FOUR-START with an 8 mm LEAD, which does not self-lock and would let the strings back-drive the motors. This listing was the only true 1-start on the first two result pages. The round nuts in the pack are not the H-flange nut the carriage is cut for. |
| `leadscrew_nut_h` | 10 | AliExpress | 3256804704147842 | $9.20 | [m] | Tr8x2 single-start H-flange brass nut, ~$11 per 3 x 4-pack per BOM.md. Not re-read today; was folded into the screw line before. |
| `belt_gt2` | 8 | — | — | $6.40 | [v] | GT2 open belt, USD per metre; ~7.74 m per instrument |
| `strings` | 1 | — | — | $25.00 | [m] | one 10-string pedal steel set |
| **Total** | | | | **$585.01** | | |

**Open, and they are design questions rather than prices:**

- ~~M4 × 18 is not a length McMaster stocks~~ **RESOLVED 2026-09-30:** the ten nut-height
  screws are M4 × 20 in the model now and share the pickup jacks' row.
- **Lead screw:** nearly every "T8" screw on Temu is the 3D-printer part — four-start,
  8 mm lead — which does not self-lock. Only one true Tr8×2 single-start listing turned up,
  and its price is from the search page because the listing sits behind a CAPTCHA.
- **Heat-set inserts are $205.58 an order** at McMaster, the dearest fastener line by far.
- **Hardened stock gets cut twice** (Ø8 shaft in half, Ø3.5 drill blank in half): an
  abrasive wheel, not a hacksaw.
- **The 10 string-clamp set screws are NOT real any more** — the sliding insert is the clamp;
  the older rows above are corrected. **The M2 grubs are gone too** (2026-09-30): each lever's axle is held by an
  M4 × 10 button head and washer in its own −Y end, drawn and counted (11).

## Electronics (compute bay)

The printed tray in the keyhead bay carries tool-free snap mounts for the whole
stack. **There is no longer a basic/pro split** — every instrument gets a Pi, so
the B/P column below is historical and every row is fitted. Panel I/O (1/4" TS line out, DC
power inlet, USB-C) mounts through the recessed wall in the bridge endplate's
lower corner — the instrument's right face.

**Price verification status.** Every row in this table was checked against a live
listing on **2026-08-01**; see the sweep summary at the top of the file. The
**B/P** column is a leftover from the retired basic/pro split; every row is now
fitted on every instrument.

| Part | B/P | PN / source | ~Price | URL |
|------|-----|-------------|--------|-----|
| **Foot lighting PCB** | B | Custom, `elec/foot_led.py` — **TWO designs, one of each** (2026-10-04): `foot_led_a` 293.36 × 24.15 (the −X board: a 4-way XH cable socket on a 7 mm tail at its −X end, four seam spring pins at +X) and `foot_led_b` 286.36 × 24.15 (four seam spring pins at −X, nothing at +X). 4-layer, 36 LEDs, **12 zones**, 4× TLC5971 each. They lie end to end in a channel on the chassis bottom and fire DOWN through the 572.72 mm light window at the player’s feet; 72 LEDs at a 7.95 pitch. The boards sit 6.05 mm above the bay floor so the 5.75 mm socket clears it uncut. |
| **Foot LED harness** | B | One **4-way JST XH** lead (XHP-4 both ends), board A’s J1 to the Pi daughter board’s J6: **GND, 24 V, SCK, SDT**. About 215 mm along its route (socket, up the endplate, over string 1’s motor, down to the Pi cap) — cut 250. There is **no jumper between the two boards** any more: four spring pins on each meet tip to tip at the seam. XH because the lead carries 24 V — the instrument’s rule (2026-10-04) is **PH = 5 V, XH = 24 V**. **Conductors, way 1 to 4: black GND, red 24 V, white SCK, blue SDT** — 24 AWG, straight-through (way n to way n), drawn that way in the model (`src/led_leads.py`). |
| **Fret board retention** | B | **No loose parts.** Each LED board tilts in under a fixed 45° lip printed on its panel’s −Y edge and is held by **two M4 × 10 button heads into M4 heat-set inserts** on its +Y side: one in the bay at the −X end, one through an ear off the +Y edge at the +X end, outside the lit line — `fret_light.m4_joint`, cadkit ScrewJoints (docs/fret-led.md §8.9 – §8.11) | 4 × M4 × 10 + 4 × M4 insert, from the instrument’s stock | — |
| **Fret lighting PCBs** | B | Custom, `elec/fret_led.py` — **TWO boards, one per deck panel, ONE chain**: `fret_led_key` 211.0 × 70.4 (frets 9–2, 8 zones, 32 LEDs, 3× TLC5971) carries the harness inlet and the only supply, and feeds `fret_led_mid` 210.8 × 70.4 (frets 24–10, 15 zones, 60 LEDs, 5×) over the deck-panel seam through **four tip-to-tip side-mount pogos a side** (+14V5, GND, SCK, SDT; docs/fret-led.md §9.1f — six with the rail doubled until 2026-10-04). **4-layer**, 1.6 mm, SMT throughout (the underside clears the CAN harness by 1.00 mm, so a through-hole tail would be in the cable). One RGBW zone per fret, **four LEDs in series per channel**. Parts: **TLC5971RGER** C543004 ×8 + **XL-5050RGBW** C7371891 ×92 + **LMR33630BRNXR** C2071384 ×1 (the 1.4 MHz part, for heat; alternate LMR33630CRNXR C2071783 on the same land; 24→14.52 V for both boards, 14.0 until the 2026-10-05 quality pass) + **SWPA5040S4R7MT** C48496 (4.7 µH, 5 × 5 × 4, Isat 3.50 A min; the 4 × 4 part saturated below the regulator's limit) + **S4B-XH-SM4-TB** C161861 ×1 + **JFC1206-1200FS** C136345 (2 A fuse) + **YZF0002-38080-02** **C5203987 ×8** + one M4 through each board. ⚠ **C5203987 IS THE ONE NEW SOURCING LINE**: Extended, SMT-assemblable, gold, 24 V / 12 A — the only side-mount pogo in the library rated above 12 V — **594 in stock on 2026-10-05 = 37 instruments at 16 each (8 here, 8 on the foot strip)**, and JLCPCB flag it High assembly difficulty. 92 channels, **1.38 A at 14.52 V** (0.93 A at 24 V) with every fret at full white (the absolute worst case; the effects daemon caps it) | **~$31 of parts** [m] — 92 LEDs $4.30, 8 drivers $19.28, 12 pogos $8.43, 1 supply ~$1.50; 4-layer fab ~$13/instrument (docs/fret-led.md §6.3) | — |
| **Fret LED harness** | B | **4-way JST XH** (S4B-XH-SM4-TB, LCSC C161861, on both boards; XHP-4 both ends), the Pi daughter board’s J3 to `fret_led_key`’s J1: **GND, 24 V, SCK, SDT** — the XH bus’s own supply order, so a motor-bus lead on this socket still powers it the right way round. It was a 4-way PH for a day and a 6-way PH before that; XH because it is 24 V (**PH = 5 V, XH = 24 V**, 2026-10-04). The seam between the two fret boards is four spring pins. Its four conductors run 165–200 mm along the route — cut 230. **Conductors, way 1 to 4: black GND, red 24 V, white SCK, blue SDT** — 24 AWG, straight-through (way n to way n), drawn that way in the model (`src/led_leads.py`). |
| **Motor controller PCB** | B | Custom, `elec/motor_ctrl.py` — ⚠ **2026-09-30: the SECOND buck (U6, the LED strip's 5 V) and its inductor, fuse F4, crowbar D10 and nine passives are GONE** — the lights take fused 24 V from J7 (F3, 3 A) and each lit board regulates its own (`docs/lighting-bus.md`); what follows predates that where it mentions U6. CH32V307WCU6 + 2× SN65HVD230 + LMR16006 buck + **LMR33630ADDAR** C841384 $0.8138, U5 — the merged power PCB's 36 V 3 A synchronous buck, 24 V → 5 V for the Pi; full MPN named here 2026-09-19, it had no row anywhere + **5× B4B-XH** (the USB link to the Pi is one of them since 2026-09-21: the USB-C it replaced faced the −Y rail 5.5 mm away and no plug could reach it) + an **M4 mounting ear** (46 × 58 + 9.5 × 8.7 tab). **46 × 58**, 4-layer — size and connector count corrected 2026-09-19 from "3× XH. 40 × 35", which was **1,400 mm² against the real 2,668**, nearly double the area, on the row somebody sizes an enclosure from. Read from the board itself (`BOARD_W, BOARD_L`) and its built fab BOM, not retyped | **~$5 of parts** [m]; fab + assembly not yet quoted | — |
| ~~Teensy 4.1~~ | — | **DELETED** ($31.50), with ~~**Teensy 4 Audio Shield Rev D**~~ ($9.80) and the teensy_ifc carrier. The Teensy's value was the Audio Library, USB high-speed and the codec, all irrelevant once no audio touches this board — the Pi does audio, and this board only reads angles off bus B and commands the motors on bus A. What could not be deleted is the pair of CAN transceivers (no general-purpose MCU integrates one), so a board was always going to exist; the only question was whether an MCU sat on it too | — | — |
| **CAN transceiver** | B | SN65HVD230DR | **$0.6185 @10** [v] — **32,557 in stock** | [LCSC C12084](https://www.lcsc.com/product-detail/C12084.html) — was priced from DigiKey at $2.45/stock 0, which made it look unavailable; LCSC has it 4× cheaper and deep. Also the sensor boards' transceiver (3.3 V — single rail) |
| ~~Power PCB~~ | — | **MERGED into the motor controller** (2026-09-15). Its buck, crowbar and 5 V outlet are now U5/F1/F2/D8/D9/J5 on that board. The merge deletes a PCB, a connector and a cable — and a JUNCTION: the 24 V trunk had to feed both keyhead boards and this one had only a 4-way inlet, so that branch was the only splice in an instrument where every other branch is a board | — | — |
| **Output + panel PCB** | B | Custom, `elec/output_panel.py` — the whole front panel AND the whole magnetic audio path on one board: panel USB-C (**VBUS broken**) + USB-A pass-through to the Pi's gadget port + USB-C hub upstream + USB-A downstream to the optical board + the 1/4" TS jack + 24 V inlet and trunk out (**AP2112K-3.3TRG1** C51118 $0.1712 for 5 V→3V3 after the bead, **MX126-5.0-02P** C5188434 $0.0660 for the magnetic pickup screw terminals — both named here 2026-09-19 because this board has no per-designator table and neither part appeared anywhere in this file) + screw-terminal pickup input + CH32V307 (USB **high speed**, internal PHY) + **PCM1808PWR** ADC (C55513) + **PCM5102APWR** DAC (C107671) + **CH334F** HS hub (C5187527) + **Omron G6K-2F-Y-DC5** true-bypass relay (C326376) + two mid-rail-biased buffers + phantom guard (**ESD5B5.0ST1G** C93623) + a local 24→5 V buck. **Analog half rewired from the makers' datasheets 2026-09-21** — the 09-17 audit's invented pinouts, 5 V DAC supply, missing MCLK and ground-clipping buffers are all fixed; the pickup now sees a **1 MΩ** load (a typical amp input — the tone-setting choice, flagged for review). **74 × 66 + M4 ear**, 4-layer, 89 parts | **~$5 of parts** [m] + the jack below | — |
| **USB cable, panel PCB → Pi** | B | USB-C ↔ USB-C, **1 m**, USB 2.0 (was A ↔ C: the board's internal ports are USB-C since 2026-10-02) | ~$5 [m] | commodity |
| ~~Buck 24→5 V 1 A~~ | — | **DELETED** ($12.95, Pololu D24V10F5): it existed only to power the Teensy | — | — |
| ~~Signal relay~~ / ~~Buffer op-amp~~ | — | **DELETED as separate lines** ($2.74 Omron G5V-1-DC5 + ~$11 OPA2134PA DIP). Both were AFE parts meant to be hand-wired; the true-bypass relay and the output buffer are now SMD parts on the output + panel PCB, placed by the assembler. A DIP op-amp on a board that has no through-hole assembly step was never going to work | — | — |
| **1/4" TS jack** | B | Neutrik NMJ4HCD2 (Ø11.4 bushing) — **PCB-MOUNT, on the output + panel PCB**. Same part as before: it was always a PCB jack, and mounting it as a free-standing panel jack would have meant hand-soldered lugs | **$2.53** [v] | [DigiKey](https://www.digikey.com/en/products/detail/neutrik-americas-inc/NMJ4HCD2/29371256) |
| **DC inlet jack** | B | Kycon **KPJX-4S-S** — 4-pin snap-and-lock power jack, through-hole right angle, shielded, **7.5 A per pin** at 48 V (two pins per rail). **PCB-MOUNT, on the output + panel PCB** (J6); its Ø12.9 nose passes through a Ø13.5 hole in the endplate panel and finishes flush with the face. Mates the Kycon KPPX-4P on the GST160A24-R7B supply (pins 1, 4 = +24 V; 2, 3 = return). **Replaces the Same Sky PJ-102AH barrel jack (5 A) on 2026-10-01** — the supply is 6.67 A and its plug is not a barrel. Footprint drawn from Kycon's land pattern (`elec/footprints/Steel.pretty`) | **$4.10** [v] | [JLCPCB C2875467](https://jlcpcb.com/partdetail/C2875467) — **44 in stock 2026-10-01, thin**; [DigiKey](https://www.digikey.com/en/products/detail/kycon-inc/KPJX-4S-S/9990088) |
| ~~USB-C panel coupler~~ | — | **DELETED** ($7.50, Adafruit 4261 F↔F). ⚠ It would have caused the fault the USB panel PCB exists to prevent: a F↔F coupler passes VBUS, and with the Pi fed from its GPIO header that puts a laptop's VBUS straight onto the power board's output. On the Pi 4B the USB-C VBUS pin and the GPIO 5 V pins are the **same node**, with no polyfuse between them | — | — |
| **Rotary encoder + 4-way** | B | Alps **RKJXT1F42001** (sole UI control) — **15 pulses / 30 detents** incremental encoder, **infinite both ways**, + 4-way directional + centre push, one 17.0×17.0×10.5 part | **$5.27** [v] (10+: $4.57) | [LCSC C160841](https://www.lcsc.com/product-detail/multi-directional-switches_alpsalpine-rkjxt1f42001_C160841.html) |
| **OLED display** | B | **2.7" 128×64 SSD1322** — Newhaven **NHD-2.7-12864WDW3**, **WHITE on BLACK**, active **61.41×30.69** (viewing window 63.41×32.69), 0.48 dot pitch, module 82.0×47.5×5.5, 3.3 V. A module on a short lead; the **encoder** and its connector are what go on our UI board | **$38.08** [v] (2,057 in stock) | [DigiKey](https://www.digikey.com/en/products/detail/newhaven-display-intl/NHD-2-7-12864WDW3/7355953) |
| ~~USB 2.0 hub (module)~~ | — | **DELETED as a MODULE** ($4.50, Adafruit CH334F) — but the function came back as a **chip on the output + panel PCB** (2026-09-15), for a different reason than it was first bought. It no longer shares a panel port; it puts the optical board's 480 Mbps link on a ~100 mm cable to the panel instead of an ~800 mm one to the keyhead, and it must be a **high-speed** hub or both devices behind it pay a Transaction Translator's ~1 ms | — | — |
| **USB lead, motor controller → Pi** | B | **USB-A male → JST PH 2.0 mm 4-way** (`PHR-4` housing) into motor_ctrl **J4** (`B4B-PH-K-S`). A stock USB-A pigtail with its four wires crimped into the PH housing; adapter leads sold ready-made are mostly XH 2.54, which does not fit | ~$5 [m] | J4 is in the instrument's one way order — **1 GND, 2 VBUS (not connected on the board), 3 D−, 4 D+**. Crimped, no solder. Full speed is all the link uses |
| **USB cable, optical board → output panel** | B | **USB-C ↔ USB-C (was A ↔ C until 2026-10-02), ~150 mm, USB 2.0 HIGH SPEED, STRAIGHT plug, overmold ≤ 17.5 mm** (mating face → cable exit) | ~$5–8 [m] | commodity. **Two changes, 2026-09-15.** *Destination*: it lands on the output panel's hub downstream port, not the Pi — which is the whole point of putting a hub there, and takes this 480 Mbps link from ~800 mm to ~100 mm, so the length drops from 1 m. *Overmold*: **20 → 17.5 mm**. Spacing the optical board's layout by land rather than by body moved its −Y face 2.58 mm further out, and that came straight off the conduit's depth budget (`PLUG_L` in `src/optical_pickup.py`, asserted against the endplate's exterior wall). Surveyed overmolds run 10–25 mm, so this rules out the long boots, not the market — but it is now a **purchasing constraint to check, not a preference** |
| **Raspberry Pi 4, 1 GB** (user, 2026-09-30; was 2 GB / $55 — the 2 GB SKU is capped at one per order across the trade, see `elec/prices.json` `pi4_1gb`) | B | Dexed + USB gadget (MIDI/audio/DFU) + USB host for the optical board | **$35.00** [v] | [PiShop](https://www.pishop.us/product/raspberry-pi-4-model-b-1gb/) |
| ~~Buck 24→5 V ≥3 A~~ | — | **DELETED** ($29.95, Pololu D24V50F5) — see the Power PCB row above and the note below | — | — |
| ~~10-ch audio ADC~~ | — | **DELETED.** Three PCM1864 + a carrier PCB existed to digitise ten string signals for the Pi. The optical pickup board now does its own 20-channel conversion (STM32H743IIT6, 20× 16-bit) and sends audio over USB, so this whole path is redundant — ~$29 of ICs plus an entire board's fab, assembly and feeder cost removed | — | — |

⚠ **Both Pololu bucks are gone, and the reason is assembly, not price.** The row
above used to argue about which module to buy; the answer turned out to be
neither. They are through-hole modules on 0.1 in headers and neither is an LCSC
line, so **the assembler cannot place them** — they become hand-soldered wiring
in the tray, which is the exact thing the connector strategy exists to delete.
And neither has anywhere to put a fuse or a clamp, which matters more than usual
here: the Pi is fed from its **GPIO header** (its USB-C port is the front panel's
gadget port), and that path skips every input protection the Pi has. A designed-in
buck puts the crowbar on the same board as the converter it protects. **$42.90 of
modules → ~$3 of parts**, and one less hand-assembly step.

⚠ **THE UI CONTROL'S SOURCE WAS WRONG, not the part** (2026-09-25). The part is
exactly right and the DigiKey line was not: **0 in stock**, 1,309 past due against an
08-Sep date already gone, 11 expected 01-Oct, at **$9.22**. The same part is an LCSC
line — **C160841, 6,466 in stock, $5.27** — so it is both available and $3.95 cheaper,
and being an LCSC line it is one the **assembler can place** rather than a part someone
hand-mounts. Mouser is 0 too, with a long lead time flagged, so DigiKey was not an
outlier.

⚠ **AND DIGIKEY'S PARAMETRICS DESCRIBE IT WRONGLY** — worth recording, because the
listing talks anyone out of the part. It is filed as "2-Way Rotational … **Non-
continuous**", which reads as a rotary *switch* with end stops. Alps' own data for the
RKJXT1F series says otherwise: **15 pulses / 30 detents**, an incremental encoder, free
to turn for ever in either direction, with the 4-way stick and the centre push on the
same shaft. That is the whole requirement — stepped, clicky, infinite, plus N/E/S/W —
in one 17 mm part, which is why it is the sole UI control. Read the Alps page, not the
distributor's filter fields.

⚠ **SIZE DECIDED IT, AND WHITE + ON-OUR-BOARD DO NOT CO-EXIST AT THIS SIZE.** The
user's range is **55.0×27.5 at the smallest, 63.4×32.7 preferred**. Three parts reach
it and each gives up something:

| part | active | white | stock | JLC places it? | |
|---|---|---|---|---|---|
| **NHD-2.7-12864WDW3** *(this row)* | 63.41×32.69 | ✅ | **2,057** | ✗ module | $38.08 |
| C7466001 `HS242L03**W**2C01` | 55.01×27.49 | ✅ | ⚠ **18** | ✗ not in the library | $12.88 |
| C7466000 `HS242L03**B**2C01` | 55.01×27.49 | ✗ **blue** | ok | ✅ Extended | $12.40 |

The white 2.42" exists — but 18 in stock and JLCPCB's part page for it is empty, so
they will not place it. Only the **blue** 2.42" is assemblable. White on black was the
requirement, so the display stays a module and the **UI board carries the encoder plus
the display's connector** instead of the panel itself.

### The UI board — designed 2026-09-25 (`elec/ui_board.py`)

One 72 × 34 two-layer board under the deck's mid panel, twelve parts, JLC-assembled,
**0 unconnected / 0 DRC violations on the first routing pass**. It carries the encoder,
the display's connector and one ribbon to the Pi — nothing else, because nothing else
belongs here: all UI logic is the Pi's (see the control-architecture split).

| line | part | qty | price | source | note |
|---|---|--:|---:|---|---|
| **UI PCB** | custom 72 × 34, 2-layer, 1.6 mm, 12 placements, one M4 through-hole | 1 | ~$2 assembled (est.) | JLCPCB | panelises with the tee/sensor boards |
| **Display header** (on our board) | Kinghelm **KH-2.54PH180-1X20P-L11.5**, 1×20 male 2.54 | 1 | ~$0.10 | [LCSC C2905493](https://www.lcsc.com/product-detail/C2905493.html) — 1,131 in stock | **Insulation 2.5 / mating pin 6.0 / tail 3.0, all three read off the listing**: `src/ui_panel.py` builds the whole Z stack on them |
| **Display socket** (on the MODULE) | Kinghelm **KH-2.54FH-1X20P-H8.5**, 1×20 female 2.54 | 1 | ~$0.15 | [LCSC C2905423](https://www.lcsc.com/product-detail/C2905423.html) — 7,005 in stock | ⚠ **HAND-SOLDERED, and it is the only hand-solder step in the station.** Newhaven ship the module with plated holes and no header — their drawing only *recommends* a 1×20 — so both halves are ours to pick. Male on our board and female on the module makes both halves stock parts with 6.0 mm of engagement; the other way round needs a long-pin header nobody stocks |
| **Power switch** (2026-10-04) | Legion **PB-22E85-S-5.7C-C-W**, self-locking push switch, 2P2T, 8.5×8.5×8.5, 3.3 sq stem, THT | 1 | ~$0.15 | [LCSC C22462024](https://www.lcsc.com/product-detail/C22462024.html) — 2,535 in stock | **It carries no supply current.** Rated 12 V 0.3 A; its two throws ride ribbon ways 15/16 to the output board, which does the switching. A printed Ø15.2 cap presses onto the stem: flush with the deck = on, 1.5 proud = off. ⚠ Throw order is off the drawing's schematic, not metered |
| **Ribbon header** | HX **PZ1.27-2x8P WZ**, 1.27 mm 2×8 right-angle pin header — the SAME part as the Pi cap's end (a 2×7 of the same family until the power button took two ways, 2026-10-04; a 2.54 mm IDC box header before 2026-10-02) | 1 (+1 on the Pi cap) | ~$0.17 | [LCSC C22438114](https://www.lcsc.com/product-detail/C22438114.html) — 2,050 in stock (2026-10-04) | **The thinnest line on the board.** Right-angle is forced: the board hangs under the deck with 11.70 mm of air over it and a vertical box header stands ~13.5. It is not shrouded, so pin 1 is marked in silk at both ends |
| **Ribbon cable** | **16-way** (14 until the power button, 2026-10-04) **0.635 mm** flat ribbon (for 1.27 mm IDC), 10.2 wide (was 1.27 mm ribbon, 17.78 wide, until 2026-10-02), **500 mm** | 1 | ~$1 | ⚠ **not LCSC** — see below | **Bought to length, and the length is measured, not guessed: the modelled centreline is 449.6 mm** (it was 429.5 until the deck handed a pickup slot to the mid panel on 2026-09-29 and the whole station moved 20.05 mm +X, away from the Pi) (`cadkit.cables.path_length` over the path `src/wiring.py` draws), so 500 mm is the next stock length up and leaves ~70 mm of service slack. **It is folded twice**, 45° each, because the run is flat under the deck and both of its 90° turns are in the ribbon's own plane — `UI.RIBBON_FOLDS` declares that and `flat_bends` holds the path to it |
| **Ribbon sockets** | **2×8** (2×7 until 2026-10-04) IDC female socket, **1.27 mm** (was 2.54 mm until 2026-10-02) — or buy the cable ready-made: a 16-way 1.27 mm socket-to-socket IDC lead is a stock item | 2 | ~$0.6 | ⚠ **not LCSC** — see below | Pressed on, not crimped and not soldered, which is the whole reason this is a ribbon and not sixteen wires. One end mates the header on `ui_board`; the other the same header on the Pi cap, and the way order is chosen so SCLK runs between GND and +3V3 (see `elec/ui_board.py`) |

⚠ **AND THE PI END IS NOT DEFINED — the sentence that used to stand here, "at the Pi it
lands on GPIO pins", does not survive being checked** (user asked how it connects,
2026-09-28). A 2×7 IDC socket will physically push onto any seven adjacent pin-pairs of
the Pi's 40-way header, so the question is only which seven, and the answer is that **no
block of seven works.** Counting the header pair by pair:

* **Pins 1–14, the obvious choice, is the worst one.** It offers 8 GPIO, and the 5 V feed
  from the motor controller (`J5`, "5 V to the Pi's GPIO pins 2/4 + 6/9") is already on
  four of its fourteen pins. Landing our socket there shorts signals onto 5 V and 3V3.
* **The best block offers 11 GPIO** (pins 11–24 or 15–28) against the **12 signals** this
  ribbon carries — SW_A/B/C/D, SW_PUSH, ENC_A, ENC_B, SCLK, SDIN, DC, CS_N, RES_N — plus
  a 3V3 and a GND. One short, before any preference is expressed.
* **Wanting hardware SPI0 makes it three short.** SPI0 lives on pins 19/21/23/24, which
  only blocks 11–24 upward reach, and enabling it claims GPIO9 (MISO, pin 21) even though
  the display is write-only — so one of the eleven goes back. An 8,192-byte frame is a
  real reason to want the hardware port.

**THE ADAPTER ALREADY EXISTS — it is bronner's `elec/pi_cap.py`, and it does not have room
for this connector as it stands.** Looked at 2026-09-28, on `agent/bronner`; it is not on
main yet, so nothing here can build against it. What it is: a 56 × 26 board whose `J1` is a
full 2×20 socket pushed onto the Pi's header, JST connectors for everything else, and the
standing no-crimp-off-a-PCB rule satisfied. **Electrically it is already done for us** —
every pin `J1` does not use is explicitly netted `PI_NC_<n>`, so all fourteen ways' worth
of GPIO is already on that board's copper, waiting. That removes the whole "which seven
pins" problem: through the cap, our ways reach any GPIO on the header, contiguous or not.

Mechanically it does not fit, and the numbers are not close:

* **No face has the height for a 2.54 mm IDC.** Every connector on the cap is on the face toward the Pi,
  inside the socket's own **8.5 mm** standoff (the JSTs are 5.5 and 5.75). A 2.54 male
  header is **8.54** on its own before its socket goes over it, and a shrouded right-angle
  is ~10. The bare face has **2.5 mm** before `chassis_2` — measured by stepping slabs
  outward, clear at 2.5 and hit at 3.0. And the height budget it is packed against
  (`ELEC_STACK_D`, 14.0 above the Pi's PCB) is the one thing bronner's docstring says
  cannot grow.
* **No room in plan either.** The socket spine takes y −11.1…−5.9 across the full 50.8,
  the side-entry row takes 50.9 of the 56 mm width with gaps of 4.3 and 3.3, and the
  passives sit between them. The biggest clear rectangle is about **56 × 5.9**, against a
  25.5 × 13.7 footprint.

**But the board is small on purpose and the Pi is not.** The cap uses 26 mm of the Pi's
56, and the space alongside it — 29.5 × 56 × 11.55, ~19,000 mm³ — holds nothing but cables
that reroute plus **90.8 mm³ of `keyhead_endplate`**, confined to the deepest 2 mm in X at
the far end (z −62…−46). So ~14 mm of growth is unobstructed, and growth in the board's
PLANE costs nothing in the height budget, which is the axis that is actually full.

So the route is: **the cap grows, and the connector is one that fits an 8.5 mm gap.** A
**1.27 mm-pitch 2×7 shrouded IDC** does (halving the pitch halves the cable too: 14-way
0.635 ribbon is 8.9 wide, and it would retire the 10.0 mm ESTIMATE this file carries for
our own right-angle header). **FFC/ZIF** is the fallback — 1.2–2.5 mm sockets fit even the
front face — at the cost of a cable less happy about vibration and mating cycles.
⚠ **THE CAP IS BRONNER'S BOARD, so that growth is theirs to decide**, and until it lands
on main this end of the cable stays open.

⚠ **THE RIBBON AND ITS SOCKETS ARE NOT LCSC LINES, which is normal rather than notable:**
LCSC is where the parts that get soldered to a board come from, and everything else —
these two included — comes from DigiKey and the other distributors, same as the screws,
the bearings and the springs. Recorded only because the row above it, the ribbon *header*,
is an LCSC line and the two sit next to each other. **OPEN: no chosen SKU for either**,
though both are commodity. Their sizes are not open — width, thickness, pitch and way
count are single-sourced from `src/ui_panel.py`, which is what the board is laid out
against.

⚠ **THE SHAFT IS A D, AND THE CATALOGUE DOES NOT SAY SO** (2026-09-28). The knob is
printed, so its bore has to match the shaft, and the drawing this was first read from is
a 592-pixel GIF in which **"1.8 ±0.03" is not a length — it is the width across a
FLAT**. Alps' own 3D model (the one LCSC ship with `C160841`) settles it by slicing:
from 12.10 mm up the section is ±1.25 in one axis and −1.24…+0.55 in the other, i.e.
Ø2.5 milled to **1.79 across**. A round bore would have turned on it and the encoder
would have done nothing — a dead control on an assembled instrument.

Two more numbers came out of the same slice and both were wrong from the drawing:

| | read off the drawing | the model |
|---|---|---|
| shaft tip above the board | 14.2 | **17.10** |
| 17 × 17 body height | 10.5 | **8.30** (a collar carries on to 10.20) |
| usable key length | 1.8 | **5.00** of flat |

The catalogue's `W×D×H = 17.0×17.0×10.5` is over the COLLAR, not the body. Anyone
sizing a pocket to 10.5 is sizing it to the wrong feature.

**Clearance, measured rather than derived.** The cap and the deck's hole are both sized
off the 9° tilt, so their arithmetic agrees with itself and proves nothing. Tilting the
real solids about the real fulcrum through 36 directions leaves **1.19 mm at full
deflection** and 2.94 mm at rest, the tightest point being the shank against the wall of
the deck's hole 1.41 mm below the deck's top face. The cap's underside is a 14° cone
rather than a flat disc — a flat one has to sit its whole rim's dip above the deck, which
parked it 1.8 mm proud for a clearance only ever needed at the stop.

⚠ **RETENTION: A CLAMP PLATE AND TWO M4s** (user, 2026-09-28 — "the retention is
pretty lackluster"). One screw through a 72 mm board is a hinge, and the screen above it
was held by nothing but the ledge over it and the header under it. A printed **PETG-GF
clamp plate** lies against the board's underside with a relief under each through-hole
footprint, and a single **M4×12 button screw** pulls it up into the deck panel's own
boss; an arm off it steps up past the board and runs under the display to press the
module's far end into the window ledge. New BOM lines: 1 × M4×12 button, 1 × M4 heat-set
insert, and the printed plate itself.

**The M4 only holds Z** (user). X, Y and rotation are two printed **spigots** that come
down off the deck, pass through Ø4.6 clearance holes in the board and enter blind sockets
in the clamp — the project's own rule, that plastic captures every direction but the one
you install along. Two M4s would have been a second fastener doing a job plastic does
better, and the board would have carried two holes instead of one plus two locating
features.

⚠ **AND THE BAY UNDER THIS STATION IS NOT CLEAR.** An earlier note of mine in this file
and in `src/ui_panel.py` said there was 57.5 mm of free air under the whole station. That
came from a probe whose filter excluded almost every part in the instrument; it found
two. Measured properly, the highest things under the station are **wire_usb at −18.00**
under the board and **wire_canl at −17.24** under the display, with the tee boards at
−19.65 — against the board's own through-hole tails at −16.50. The real budget is
**1.5 mm**, which is what the clamp plate is designed around.

**Pull-ups, not debounce capacitors.** Seven 10 kΩ 0402, one per contact, and no cap
across any of them. An RC debounce dumps the capacitor's charge through the switch
contact at every make, and this contact is rated **10 mA with a 50,000-cycle life on the
directions and 15,000 on the encoder** (Alps' own figures) — the cheapest possible way to
spend that life. Debouncing is the Pi's, where it costs nothing and can be tuned. 10 kΩ
external rather than the Pi's ~50 kΩ internal because the run is half a metre of ribbon
through an instrument full of stepper drivers.

**No ground pour, and it was tried.** A B.Cu plane under the SPI clock is the obvious
thing to want. On two layers it cannot be had: leave B.Cu open to the router and it lays
signals across the pour — that came back as two GND islands and an unconnected board —
and close B.Cu to the router and the only remaining layer has to carry five SPI signals
past a 20-way row that +3V3 already crosses. The plane would be perforated anyway, by
twenty through-hole pins at 2.54 leaving 0.7 mm webs straight across it.

⚠ **BS1 = 0, BS0 = 0 IS NOW READ, NOT INFERRED.** The note below this one used to flag
the 4-wire SPI strap as the *standard* SSD1322 mapping that wanted a human's eyes on the
PDF before the board was fabbed. It has had them: page 5, "MPU Interface Pin Selections",
gives BS1/BS0 as 1/1, 1/0, 0/1, **0/0** for 6800, 8080, 3-wire and 4-wire. Both are
strapped to VSS on our board, and /SHDN — internally pulled high — is strapped to VDD
rather than run to the Pi, so it cannot float at the end of half a metre of ribbon.

⚠ **ONE HEIGHT ON THIS BOARD IS AN ESTIMATE.** `src/board_geom.HEIGHT` carries **10.0 mm**
for the right-angle ribbon header because ZHOURI publish no drawing through LCSC and the
KiCad footprint carries no Z. There is 11.70 mm between the board's top face and the
deck's underside. **Measure the part before the deck panel is printed.**

⚠ **AMOLED WAS INVESTIGATED AND IS A DEAD END THROUGH OUR CHANNELS** — recorded so it
is not re-opened. At distributors it is either absent or tiny wearable panels (1.3–2.06",
about 29×35, round, QSPI on ESP32 boards); anything 55 mm and up is phone-panel OEM
supply on MIPI-DSI, volume-only and not stocked. **And it is not needed**: both sizes
asked for are ~2:1 (55.0/27.5 = 2.00, 63.4/32.7 = 1.94), which is exactly 128×64's own
aspect, so PMOLED covers the whole range. AMOLED would only have been required for the
earlier 40–60 mm height, which is what made it a 4:3 problem.

⚠ **PMOLED vs AMOLED, FOR THE RECORD: no picture-quality difference in black and
white.** Both are OLED, so an off pixel emits nothing and black is black on either.
What differs is SCALING: a passive matrix lights one row at a time, so with 64 rows
each is lit 1/64 of the time and must be driven 64× harder — which is exactly why
PMOLED stops around 2.4–2.7" and why nothing bigger exists at any price. AMOLED holds
every pixel lit through a per-pixel transistor, so it scales, runs brighter and takes
static content better (a menu is a burn-in load). None of that buys anything here.

⚠ **MENU DEPTH COMES FROM THE PIXEL COUNT, NOT THE PANEL SIZE.** Every 128×64 panel
gives the **same 8 rows** of 5×7 text whether it is 0.96" or 2.7" — a bigger panel makes
characters bigger, not the list longer. Read at **1 ft**, where ISO 9241 wants ≥20
arcmin (1.77 mm) and 16 is the floor, this panel's 0.495 pitch gives:

⚠ **THE PANEL IS SIZED FROM THE FONT, NOT THE OTHER WAY ROUND** (user, 2026-09-25),
and the binding constraint is the **accessibility font, not the normal one**. The brief:
good legibility at 1 ft for most people, at least 3 menu items, plus a larger option for
impaired vision. A large font at 2× halves the rows — so the normal font must give **6+
rows** for the large one to still show 3 items.

| font cell | rows | cols | character | at 1 ft | |
|---|---|---|---|---|---|
| **5×7 in 8 px** | **8** | 21 | 3.36 mm | **38′** | NORMAL — 7 items + header |
| 6×8 in 10 px | 6 | 18 | 3.84 mm | 43′ | NORMAL, roomier — 5 items + header |
| 8×11 in 12 px | 5 | 14 | 5.28 mm | 60′ | LARGE — 4 items + header |
| **8×14 in 16 px** | **4** | 14 | 6.72 mm | **76′** | LARGE — 3 items + header |

Both modes clear the brief with margin, and rows trade against character size in
firmware at no cost in parts.

⚠ **THE PER-CHARACTER FLOOR IS 2.4 mm WIDE × 3.0 mm TALL, AND IT LANDS ON THE CLASSIC
5×7** (user, 2026-09-25). Two things fall out, and both read backwards off a spec sheet.

**WIDTH BINDS, NOT HEIGHT** — glyphs are narrower than they are tall, so the floor is
reached across first: the glyph needs `ceil(2.4 / pitch)` pixels wide.

**AND SO A FINER PITCH IS WORSE.** Each character costs more pixels on a denser panel,
so fewer fit. Higher resolution actively hurts under a millimetre floor:

| panel | pitch | glyph | char mm | cols × rows |
|---|---|---|---|---|
| 1.54" 128×64 | 0.274 | 9×11 | 2.46 × 3.01 | **12**×5 — too narrow |
| 2.42" 128×64 | 0.430 | 6×7 | 2.58 × 3.01 | 18×8 |
| **2.7" 128×64** *(this row)* | **0.480** | **5×7** | **2.40 × 3.36** | **21×8** |
| 3.12" 256×64 | 0.300 | 8×10 | 2.40 × 3.00 | 28×**5** |

This panel is the **coarsest available**, which under a millimetre floor is exactly
right — it spends the fewest pixels per character and so fits the most text. At 0.48
pitch, 2.4 mm **is 5 pixels exactly**, so the floor selects the canonical **5×7 font**
and the panel's full native **21 × 8** grid: **7 menu items plus a header**, every
character 2.40 × 3.36 mm, **38 arcmin** at 1 ft against ISO 9241's 20.

(Arithmetic note: at the exact 61.41/128 = 0.47977 pitch a 5 px glyph is 2.3988 mm —
1.2 µm under, 0.05%. Newhaven's own quoted dot pitch of 0.48 gives exactly 2.40. Not a
number to design around.)

⚠ **A 7 px GLYPH HAS NO TRUE DESCENDERS** (they want 9–10 px), so mixed-case g/p/y sit
on the baseline. Either caps for labels, or a 5×9 glyph at 6 rows — **height is not the
binding axis**, so a taller glyph costs rows, not legibility. The earlier 3.0 mm width
floor forced a 7×7 square glyph and only 16 columns; dropping to 2.4 buys five more
characters per label and a properly proportioned letter.

⚠ **THE LARGE-FONT OPTION still works from the same grid**: doubling to a 10×14 glyph
in a 16 px cell gives 4 rows at 6.72 mm / 76 arcmin — **3 menu items plus a header**,
which was the accessibility floor asked for.

⚠ **AND SIZE IS NOT WHY THIS PANEL WAS CHOSEN — be clear about that before anyone
"optimises" it.** Legibility alone does NOT need 2.7". ISO 9241 wants ≥20 arcmin (1.77
mm at 1 ft) and the brief's 3 items at 6 rows needs only **13.4 mm of active height**;
the 1.54" C7465999 hits 22′ and 8 rows in 17.52 mm for $6.57 on our own board. What the
1.54" cannot do is **4-bit greyscale over SPI** — it is a 1-bit I²C part, so no
antialiasing and no sub-pixel scrolling. The 2.7" is bought for the greyscale and the
bandwidth (see the notes above); 38′ instead of 22′ is a *consequence*, and a welcome
one — most eyes will never need the large font.

⚠ **THE FRAME IS 8,192 BYTES, NOT 4,096 — every rate figure below was 2× optimistic
until this was read off the drawing** (2026-09-25). The mechanical drawing maps
**Column 1 → segments 366 AND 367**, Column 128 → 112,113: **two segments per visible
dot**. The window is segments 112–367, which the drawing's `(91, 63)` corner confirms as
column addresses 28–91. SSD1322 packs 4 segments per column address at 2 bytes each, so
a frame is **64 addresses × 2 B × 64 rows = 8,192 B**. Counting the 128 *visible dots*
gives 4,096 and is wrong.

| | on 4,096 B | actual, 8,192 B |
|---|---|---|
| max full-frame @ 7.8 MHz | 238 fps | **119 fps** |
| 60 fps bus load | 20% | **50%** |
| write duty @ 110 Hz scan | 46% | **92%** |
| write duty @ 220 Hz scan | 92% | **185% — exceeds the scan** |

**So PARTIAL UPDATES ARE THE DESIGN, not an optimisation.** A full frame takes 8.40 ms
against a 9.09 ms scan at 110 Hz — it nearly fills it — and at 220 Hz it cannot fit at
all. An 8-row scroll band is 1,024 B = 1.05 ms = **12% duty**, which is comfortable. The
110 Hz / 60 fps / 7.8 MHz settings hold **only if regions are redrawn rather than
frames**.

⚠ **THE UI BOARD'S INTERFACE TO THIS MODULE**, read off the datasheet (2026-09-25):

* **Connector: 1×20 pin header, 2.54 mm pitch** (Newhaven's own recommendation, note 5
  on the mechanical drawing). The UI board carries the mating half.
* **4-wire SPI pinout** — 1 `VSS`, 2 `VDD` (3.3 V), 4 `D/C`, 7 `SCLK`, 8 `SDIN`,
  16 `/RES`, 17 `/CS`, 18 `/SHDN` (boost shutdown, internally pulled high), 19 `BS1`,
  20 `BS0`; pins 5–6 and 10–14 are `VSS`, 3/9/15 are NC.
* **`BS1`/`BS0` select the interface and are STRAPPED ON OUR BOARD, not run to the Pi** —
  likewise `/SHDN`. ⚠ The datasheet's selection table did not survive text extraction
  cleanly; the standard SSD1322 mapping for **4-wire SPI is BS1=0, BS0=0**, and that
  wants one look at the PDF before the board is fabbed.
* So the Pi only ever sees **5 SPI signals + 3.3 V + GND**, and the encoder's 7 —
  **14 conductors**, unchanged.

⚠ **CONFIRMED FROM NEWHAVEN'S OWN INIT ROUTINE**: `0xCA 0x3F` = **MUX 64** (so the scan
arithmetic above uses the right divisor), and `0xB3 0x91` = divide ratio 1 with the
oscillator at **level 9**, above the reset level 5 — the stock scan is therefore somewhat
ABOVE the 220 Hz computed at the default oscillator. And the optics are listed **"White
Color, Anti-Glare, Full View"** — the anti-glare treatment is the thing that keeps blacks
black under stage lighting, and this part has it.

⚠ **RAISING THE REFRESH RATE BUYS ALMOST NOTHING — THE ARTIFACT TO DESIGN AGAINST IS
TEARING** (user asked, 2026-09-25). Two separate things get called "refresh" and the
part already has plenty of both.

**Panel scan, ~220 Hz.** Settable by B3h (oscillator level 5 of 16 at reset, headroom to
~360 Hz; the divider only ever lowers it). Raising it shows nothing — flicker fusion is
finished above ~100 Hz — and the datasheet is explicit: *"higher frame frequency leads to
higher power consumption on the whole system."* The useful direction is DOWN.

**Update rate, up to 305 fps**, purely SPI-bound: 60 fps is 20% of the 10 Mbit/s bus,
120 fps is 39%. Above ~60 the returns vanish for a menu.

**AND NEITHER FIXES TEARING, WHICH IS WHAT WILL ACTUALLY SPOIL A SCROLL.** These modules
bring out no tearing-effect signal, so GDDRAM writes are asynchronous to the scan.
Update mid-scan and the top of the panel shows the new frame while the bottom shows the
old — a tear line crawling through the animation. More fps only moves it. What fixes it
is writing a whole frame faster than one scan takes:

| | |
|---|---|
| one scan at 220 Hz | **4.55 ms** |
| 4,096 B at 10 MHz | 3.28 ms ✅ |
| at 8 MHz | 4.10 ms ✅ |
| at 7 MHz | 4.68 ms ❌ tears |

**So the rule is SPI as fast as the part allows, not "more fps"** — and on a Pi that
ceiling is lower than it looks. The Pi divides its 250 MHz core by powers of two, giving
**7.8 or 15.6 MHz**, and the SSD1322's `tcycle` minimum of 100 ns caps it at **10 MHz**.
15.6 is 56% over spec, so **7.8 MHz is the ceiling** and tearing cannot be bought off
with a faster bus.

⚠ **DO NOT SET THE SCAN AND THE UPDATE TO THE SAME RATE** (user asked, 2026-09-25).
Three reasons, and the last one picks the setting:

  * **It cannot be held.** The scan is an internal RC — FOSC 1.75/1.94/2.13 MHz — so a
    *nominal* 110 Hz part is anywhere in **99–121 Hz** and drifts with temperature, with
    no TE output to lock onto.
  * **It would look worse if it could.** An exact ratio (1:1, 2:1) freezes the tear in
    one place: a standing seam through every scroll. A mismatched rate sweeps it through
    the display fast enough to average away. Matching is the case to avoid.
  * **What is controllable is WRITE DUTY** — the fraction of a scan period spent
    writing, which is the only window a tear can open in:

| scan / SPI | scan period | 4,096 B write | duty |
|---|---|---|---|
| 220 Hz / 7.8 MHz | 4.55 ms | 4.20 ms | **92%** |
| **110 Hz / 7.8 MHz** | 9.09 ms | 4.20 ms | **46%** |

**SETTLED: scan 110 Hz (B3h divider D=2), update 60 fps, SPI 7.8 MHz.** The scan halves
the duty and saves power; 60 sits below the scan so no frame is written that cannot be
shown; and 110/60 is not a clean ratio, so what tearing remains sweeps. Going *up* to
120 fps would put the update above the scan — writing frames the panel physically
cannot display.

And the practical escape: **menus rarely redraw a whole frame.** An eight-row scrolling
region is ~512 B = 0.53 ms, a **6% duty**. The full-frame figures bound the worst case,
not the normal one — if a scroll ever tears, redraw less rather than clock faster.

⚠ **WHAT MAKES IT LOOK GOOD IS GREYSCALE, NOT BRIGHTNESS** (user asked, 2026-09-25) —
and it is the real justification for paying $38 rather than $12. The SSD1322 is **4-bit,
16 grey levels**, with 256-step contrast and 16-step master current. Every cheap I²C
panel in JLC's library (SSD1309, SH1107) is **1-bit**: a pixel is on or off.

That is the difference between text you can ANTIALIAS and text with hard jagged edges,
and — the part that matters for the scrolling animation asked for — between motion that
glides and motion that steps. **At 1 bit, 200 fps still looks like it jumps a whole
pixel at a time; at 4 bits you can move in sixteenths of a pixel and it reads as
smooth.** Greyscale buys more perceived quality here than frame rate does.

The rest of "looks good", in order:
  * **AMBIENT contrast, not contrast ratio.** Every OLED is effectively infinite —
    an off pixel emits nothing — so that spec never separates two OLEDs. What separates
    them is whether the room reflects off the glass and greys the black. A polariser or
    AR treatment is what keeps blacks black under stage lighting.
  * **Luminance** (~100 cd/m² typical) matters for washout, not for quality, and it
    trades against lifetime: a PMOLED driven harder dies sooner.
  * **Fill factor** — how much of each 0.48 cell emits. At 1 ft the grid IS visible;
    whether it reads as deliberate or cheap is fill factor plus the font.
  * **BURN-IN is the one to design around.** A static menu is the worst possible
    content for an OLED. Low brightness, a dim/blank timeout, and shifting the UI a
    pixel now and then.

⚠ **AND IT HAS NO TOUCHSCREEN** — worth saying because it was assumed to (user) and it
would be a real waste. DigiKey lists no touch field for `NHD-2.7-12864WDW3`; the touch
version is a **separate order code, `NHD-2.7-12864WDW3-CTP`**. The price is Newhaven
being an industrial, US-distributed module: SSD1322, the DC-DC boost an OLED needs for
its ~12 V panel rail, a carrier PCB, low volume.

⚠ **COLOUR: wanted as a bonus, and it does not exist at this size.** Colour PMOLED is
only made small (1.5" 128×128, SSD1351); colour at 2.7" means AMOLED, which is not
purchasable through our channels (see the AMOLED note above). Colour and this size do
not co-exist, at any price we would pay.

⚠ **REFRESH IS ~220 Hz AND THE INTERFACE MUST BE SPI, NOT I²C.** Newhaven publishes no
refresh figure because it is not a panel property: the SSD1322 sets it, and it is
programmable — `F_FRM = FOSC / (D × K × MUX)` with FOSC 1.94 MHz typ, D 1, K 138 and
MUX 64 gives **219.7 Hz**. Flicker is a non-issue; power is the reason to lower it.

What is NOT free is pushing frames. A frame is **4,096 bytes** (SSD1322 is 4-bit
greyscale, two pixels to a byte), so 60 fps needs 246 KB/s = **1.97 Mbit/s**:

| interface | full-frame rate |
|---|---|
| 4-wire SPI @ 10 MHz (tcycle ≥ 100 ns, the part's max) | **305 fps** |
| 4-wire SPI @ 2 MHz | 61 fps |
| I²C @ 400 kHz | **10.9 fps** |
| I²C @ 1 MHz | 27 fps |

So SPI reaches 60 Hz at 2 MHz with headroom over the same five signal lines, and **I²C
cannot reach it at all**. That is a second reason to carry this part over the cheap
JLC-assemblable panels, which are I²C: they would cap near 11 fps on full frames.
(Menus rarely redraw whole frames — one scrolled row is ~512 bytes, which 400 kHz I²C
does in 11 ms — so this bounds the worst case, not the normal one.)

⚠ **AND IT MUST BE EMISSIVE, which is what ruled out everything that fit the FIRST size
asked for** (60–80 wide × 40–60 tall). **TFT** at 3.5"/320×240 is exactly that size,
cheap and well stocked — and backlit, so black is never off. **VFD** is perfect on every
count and the Noritake GU128X64-800B (83.1×41.5 viewing, 0.65 mm pixels, 336 in stock)
is **$425.46**. A **Sharp Memory LCD** has the look and fails outright: reflective, so
its white is ambient light off a grey substrate.

⚠ **A DEAD END, RECORDED SO IT IS NOT RE-WALKED.** While this row was briefly a
1.5" 128×128, the part to take was Newhaven's **UGC3** ($24.55, 316 in stock) and *not*
the **ASC3** ($29.15, 43 in stock), which carries a **microSD card reader** with no use
here; **NHD-1.5-128128G** is a third sibling and is the bare **glass**, no carrier PCB.
None of them is the line now — the panel went back to 128×64 — but the three look
identical in a parametric search, so the distinction is kept for whoever needs a small
128×128 next.

**Why the Pi dropped from a 5/8 GB to a 4/2 GB:** audio→MIDI now runs on the
optical pickup's own MCU, so the Pi's remaining jobs are Dexed (a DX7 emulation,
light), USB gadget duty, and hosting the optical board. None of that is Pi 5 work.
Pi 4 is the floor rather than a Zero 2 W because the design needs USB **host and
gadget simultaneously** — host for the optical board, gadget to the computer — and
the Zero's single OTG port can only be one at a time. The panel **USB-C** still
only needs USB 2.0 (480 Mbps).

**The analog front-end is not a separate board and the Teensy is not in it** —
both statements above were written before the 2026-09-15 respin and both were
wrong twice over (the paragraph was also duplicated). The whole magnetic path now
lives on the **output + panel PCB**:

* The pickup lands there on **screw terminals** — the one field connection that is
  neither soldered nor crimped, because swapping a pickup is a normal thing to do
  to a guitar.
* One buffer feeds **both** the relay's direct contact and the ADC, so the coil
  sees a single load whichever mode is selected. A magnetic pickup's tone *is* its
  loading, so two inputs hung straight on the coil would change the instrument's
  sound.
* The relay still defaults **de-energized to DIRECT**: with no power, no Pi and no
  firmware the pickup reaches the jack through a mechanical contact. It is
  **not** latching — I claimed elsewhere that a held coil "hums at the audio it is
  switching", which is wrong: the coil is DC and a static field does not hum. The
  real cost of holding it is ~30 mA.
* A **CH32V307** on that board presents the instrument to a computer as a USB
  audio interface at **high speed**, via the part's internal PHY. A 24-bit / 99 dB
  **PCM1808** does the capture and a PCM5102-class DAC does the return — the
  converter, not the word length, is what sets the floor (16-bit's *theoretical*
  ceiling is 98.1 dB).
* A **USB hub** on the same board carries the optical pickup board upstream on one
  cable, which is what shortens that 480 Mbps link from ~800 mm to ~100 mm. Both
  devices behind it are high speed, so neither pays for a Transaction Translator.
* The Pi does the **stereo→mono sum in software** for the TS jack, so the computer
  can get full stereo over the gadget port while the jack gets a fold-down.

**No analog signal crosses the instrument any more**, which is what deleted the
8-way link between the optical board and the panel.

The motor still does all tuning (the nut block clamps; no manual tuners). The nut
block is **reprintable per string set** — `STRING_GAUGE` in `dimensions.py` swaps
between E9 and C6; the break pins re-gauge so string tops stay coplanar.

Printed parts (no purchase): carriage, bridge_endplate, keyhead_endplate
(merged with the nut block), chassis (×3 segments), belt_clamp, screw_pulley, motor_pulley,
tension_fork (graded belt-tension lock set),
the adjustable legs: leg_socket ×4, leg_segment ×8, leg_shaft ×4 (PETG-GF),
leg_sleeve ×4 (PCTG — the pinch collar must flex) plus leg_foot ×4, leg_washer ×12 and the
TRRS blind-mate's leg_trrs_throat ×4 / leg_trrs_sleeve ×4 in **TPU**
(anti-unscrew preload washers + floor-friendly feet), electronics_tray, and
the **removable top deck**: a **pickup-carrier piece** (a tray whose floor runs
under the pickup; 3 M4 height screws set the string gap, 2 M4 clamp screws pin
X/Y — all from the packs above) + **TWO swappable filler bands** + the UI/keyhead
panels (fret lines + dust cover + hand rest + UI mount) — see
`py -3.12 -m src.build --list`.

⚠ **THE FILLERS ARE NOW ONE PART, AND THE DECK IS ONE PANEL SHORTER**
(user, 2026-09-29). Two changes that only make sense together:

* **The -X-most pickup slot was handed to the mid panel**, which takes the small
  swappable bands from three to two (a 255 bed — now `top_plate.BED_XY`, asserted
  rather than left in a comment). **Cost: the pickup's COARSE positions go 4 → 3**, i.e.
  20.05 mm less coarse reach toward the neck. The fine adjustment is untouched
  (`CLAMP = BAND_W/2` still makes the coverage continuous), and the slot that went
  is the one furthest from the changer.
* **The remaining two fillers lost their fret lines**, keeping only the border's two
  long side bands. That is what makes them ONE part: a fret line is at an absolute X,
  so a marked filler fits one slot and every slot the pickup might vacate needed its
  own printed band — which is why the build used to export a set of **spares off to
  the side of the instrument**. Unmarked, any filler fits any slot, the two installed
  ARE the whole set, and there is nothing to print twice. `top_plate` asserts the
  fillers are congruent, so the claim cannot quietly stop being true.
  **Cost: frets 25–30 are no longer marked** — the deck is marked to fret 24, the
  octave quad, which now sits on the mid panel 12.5 mm clear of its +X edge. Those
  six semitones are in the swap region, where no marking could ever have been
  consistent: fret 25 falls at −145.12, which is **0.24 mm** off the region/mid seam.
* ⚠ **SUPERSEDED THE SAME DAY — see the note after this list.** *(kept because it records
  why the balance assertion existed before it was removed.)* **The mid/key seam was re-cut
  to balance the two long panels** (user). They are the
  bulk of the printed deck — 465.39 mm of material — and the old seam split it 53/47:
  **246.45 against 218.94, 27.51 apart.** The seam is now `MID_SEAM_BEADS = 476`
  (−380.80, on the bead grid like every other length here) giving **235.44 / 229.95,
  5.49 apart**, and `SEAM_BALANCE_MAX` asserts it stays that way. The seam is now the
  DATUM and the panel lengths fall out of it, which is the right way round: nothing cares
  how long the mid panel is, and four things care where the cut falls.

  ⚠ **IT IS 4.25 MM OFF ITS FRET SPACE'S MIDPOINT, which the user asked it to be on, and
  the two requests cannot both be had.** A seam has to clear the fret lines AND the
  position markers, and **the markers sit centred in their space** — so in a marked space
  the midpoint is the one place a seam cannot go. Every space midpoint that fits the bed:

  | space | midpoint | mid / key | apart | |
  |---|---|---|--:|---|
  | 8 | −399.20 (499 beads) | 253.84 / 211.55 | 42.29 | clear of markings |
  | 9 | −376.80 (471 beads) | 231.44 / 233.95 | **2.51** | **inside the fret-9 pentagon** |
  | 10 | −355.42 | 210.06 / 255.33 | 45.27 | 0.33 **over** the bed |

  The only marker-free midpoint is space 8's, and it is **less even than what we already
  had** — so following the rule literally would have made worse the very thing the request
  was for. −380.80 is the best bead-grid position inside space 9 that clears the pentagon:
  **5.43 mm to the nearest fret line, 1.49 to the marker.** Setting `MID_SEAM_BEADS = 499`
  takes space 8's true midpoint instead and costs 36.8 mm of evenness.
* ✅ **RESOLVED (user, 2026-09-29): the KEYHEAD panel is set to 249.60 mm** — 312 beads,
  just inside the 250 the bed really gives — and the seam falls out of it at **−361.15**.
  That lands in fret **space 10, which carries no marker symbol** (the nearest marking is
  12.65 mm away, against the 1.49 mm the old seam managed off the fret-9 pentagon), with
  3.33 mm to fret 9's line and 14.79 to fret 10's.

  **What it trades is evenness: 215.79 / 249.60, 33.81 apart.** Of the three things
  competing for this seam — marker-free, on the bed, evenly split — the third is the one
  given up, and `SEAM_BALANCE_MAX` was **deleted** rather than loosened to a number that
  asserts nothing. `BED_XY` is the constraint that actually binds and it is still checked.
  The seam is 5.73 off space 10's own midpoint because the midpoint would make the keyhead
  panel 255.33; "halfway between two frets" and "250 max" cannot both hold there.

  The panel LENGTH is now the anchored datum rather than the seam's position, which is the
  right way round — the thing under constraint is how much panel has to fit on a bed. The
  seam is consequently not on the bead grid (451.44 beads), because it derives from `PX1`,
  a chassis datum that is not; 451 beads would give exactly 250.00 and 452 gives 249.20.
  **`MID_X0` did not move**, so the UI station and its ribbon are untouched.

## Control sensors (knee levers + pedals)

Every player input — **6 knee levers + 5 pedals** — is a **contactless magnetic
angle sensor** rather than a switch or a pot: a diametrically-magnetised magnet
rides the control's axle and an MT6701 reads its angle across an air gap. There
is no wiper to wear out and no mechanical calibration. The boards are our own
(they panelise with the tee PCBs — see Connectors); these are the two parts that
populate them.

| Part | Qty | ~Price | Source | Notes |
|------|-----|--------|--------|-------|
| **Angle sensor IC** | 11 | **$1.68 ea** [v] | [LCSC C2913974](https://www.lcsc.com/product-detail/Position-Sensor_Magn-Tek-MT6701QT-STD_C2913974.html) | ⚠ **Corrected 2026-08-04: $1.6815 at the 10+ break** (4,207 in stock). The $1.1139 recorded on 08-01 came from a search snippet, which reports LCSC's *volume-floor* price (the 1,000+ break is $1.1161) — not the price at the 11 pieces we buy. See the snippet-bias note in the optical section. Note the QFN part is **C2913974**; the more commonly cited **C2856764 is the MT6701*C*T-STD**, the SOP-8, which is the variant this row explicitly rejects — do not let the wrong LCSC code onto the BOM line. MagnTek **MT6701QT-STD**, 14-bit on-axis magnetic encoder. Take the **QFN-16**, *not* the SOP-8 variant: the air gap is measured to the IC's own top surface, so the package height comes straight out of the gap budget, and the SOP-8 is ~1.5 mm tall — twice the QFN — on the axis where we have the least room. Datasheet §9.2: D = E = 2.900–3.100, **A (total height) = 0.700–0.800** (the model carries the 0.800 max). §1.2: *"Sensing Center at Geometry Center"* — so the package body centres on the axle axis with no per-package offset. Assembled by JLCPCB onto our sensor PCB alongside the tee boards — no hand soldering |
| **Diametric magnet** | 11 | **$0.40 / $0.332 @10** [v] | [DigiKey](https://www.digikey.com/en/products/detail/radial-magnets-inc/8995/5126077) | Radial Magnets **8995** — NdFeB **N35, Ø6 × 2.5 mm, DIAMETRICALLY magnetised**, NiCuNi, 80 °C, 3873 G surface; ~9k in stock. ⚠ **Diametric, NOT axial** — axial discs are far more common and simply do not work here (DigiKey lists the direction in the specs, so it is checkable at order time). It is also the datasheet's own **recommended magnet** (§5: "Ø6mm x 2.5mm"), so this pair is the configuration the IC was characterised in. Drops into the axle's end pocket; `kl_magnet_cap` screws over it — no adhesive |

*(qty 11 = **11 controls**, no spare — corrected 2026-09-18 (user): the
instrument has **6 knee levers + 5 foot pedals**, each with its own sensor
board. The quantity does not move, but its MEANING does: this line read "10
controls + 1 spare", and the same 11 is now fully committed. ⚠ **Decide
whether to add a spare before ordering** — an assembled board is ~$4 and a
failed one strands a control.*

*The count is now `D.N_LEVERS + D.N_PEDALS` in `src/dimensions.py`, and
`elec/lever_sensor.py` derives `qty_per_instrument` from it, so the board file
and this row share a source instead of agreeing by coincidence. It has been
wrong twice before: an earlier revision said 4 knee levers + 3 pedals and was
sized for 7, and the CAN section sized bus B for 8.)*

**Board spec (ours, for layout).** Outline **28 × 19 × 1.6 mm**, strongly
*asymmetric* about the sensor: the chip sits on the axle axis just **3.0 mm from
the +X edge**, 25.0 mm from the −X edge and 7.0 mm below the top edge.

⚠ **This board was 17 × 19 and specified as two parts — the sensor and the
connector. That board cannot work.** It sits on a CAN bus, so it needs a
controller, a transceiver and a 3.3 V rail off the 24 V trunk; the Connectors
table below was already *buying* it a transceiver (~10 off) while this section
placed neither that nor any MCU. The real population is the table below, and it
comes to ~168 mm² — 69 % of a 17 × 19's usable area, which is not routable
single-sided, against 36 % at 28 × 19.

**28 is the MAXIMUM width**, and the foot pedal sets it: the pedal turns the board
90° to put its near edge toward the player, which swaps X and Z, and at 29 the
turned board's +Z reach passes the pedal's ceiling and the pedal loses *every*
orientation. All the growth goes −X because that is the only free direction — +X
is the face nearest the player, and Z is nearly frozen by the horizontal lever,
whose window is 21.4 mm for a 19 mm board (it has exactly ONE valid orientation,
with no margin). The 3.0 is
deliberately tight — the QFN body ends at 1.5, leaving 1.5 of edge keepout, over
JLCPCB's 1.0 mm component-to-edge rule — because every millimetre there is
millimetres off the lever's +X extent, which is the face nearest the player. **No mounting
holes** — the board drops into two grooves in the housing's printed cradle, rests
on its floor, and the instrument's own underside closes over it as the lid.

**Keepouts — PARTS and COPPER are different, and conflating them cost 60 mm² of
routing area.** The 1.85 mm is `CR_ENG`, the cradle groove's engagement depth: a
*component* there fouls the plastic groove wall. Copper does not — a trace under a
plastic groove shorts nothing and abrades nothing in a 0.15 mm slip fit assembled
once. And only the **±X** edges sit in grooves at all; the ±Z edges are free (the
top clears the chassis by 0.4, the bottom rests on the cradle floor, both *below*
the board rather than on its face).

| edge | parts keepout | copper keepout |
|------|---------------|----------------|
| ±X (in the grooves) | **1.85** (`CR_ENG`) | **0.5** |
| ±Z (free) | **1.0** (JLCPCB assembly) | **0.5** |

0.5 is the safe number for a routed outline and for V-score panelisation alike
(JLCPCB's absolute floor is 0.3). That leaves **432 mm² routable** on the 28 × 16
outline against ~168 mm² of parts — under 40 % — for ~20 nets across 6 ICs.

**4 LAYERS**, and not for density: the buck switches ~10 mm from a magnetic angle
sensor whose entire job is reading a small field. A solid ground plane between them
is worth more than the couple of dollars it costs.

⚠ **Confirm at quote time:** the connector is deliberately **flush with the top
edge (0.00 margin)**, which violates JLCPCB's 1.0 mm component-to-edge assembly
rule. Better raised in the quote than discovered at assembly.

**SINGLE-SIDED: everything goes on the −Y (magnet-facing) face**, which is what
keeps this to one assembly setup. The QFN sits on the axle axis. The CAN drop is
an **S4B-XH-SM4-TB**, mouth facing −X **at the −X edge (x −23.15)**, body running
+X to −17.05. It used to sit at x −11.9 — as close to the cap as the sweep allowed,
because the board only reached −14. With the board out at −25 the connector moves
to the edge, and that matters more than the 11.25 mm it travels: the **mated plug
runs 7.5 mm further −X still**, so at −11.9 the header *plus its plug* occupied
x −19.4…−5.8 straight across the middle of the board — 204 mm², the single largest
obstruction on it. At the edge the plug runs off the board entirely.

**Populated parts** (all prices/stock read from `lcsc.com/product-detail/C<n>.html`):

| Ref | Part | LCSC | Package | Body mm | Stock | $ @10 |
|-----|------|------|---------|---------|-------|-------|
| U1 | MT6701QT-STD angle sensor | C2913974 | QFN-16 | 3.00 × 3.00 × 0.80 | — | 1.68 |
| U2 | **CH32V203G6U6** MCU, classic CAN 2.0B | C5142280 | QFN-28 | 4.00 × 4.00 × 0.90 | 1,057 | **0.5733** |
| U3 | **SN65HVD230DR** CAN transceiver, **3.3 V** | C12084 | SOIC-8 | 6.00 × 4.90 × 1.75 | 32,557 | **0.6185** |
| U4 | **LMR16006XDDCR** buck, 4–60 V in | C87080 | SOT-23-6 | 2.90 × 1.60 × 1.10 | 18,666 | **0.5312** |
| L1 | inductor (buck) | — | 3030 | 3.00 × 3.00 × 1.50 | — | ~0.05 |
| Y1 | crystal | — | 3225 | 3.20 × 2.50 × 0.90 | — | ~0.05 |
| J1 | S4B-XH-SM4-TB CAN drop | C161861 | SMT side-entry | 6.10 × 15.00 | — | 0.6577 |

≈ **$4.36/board, ≈$48 for 11** — inside the ~$50 this section budgets.

**Why classic CAN 2.0B and not FD** (user): the motors are classic-only, but they
are on **bus A** and these boards are on **bus B**, so the motor does *not* force
this — bus B was genuinely free to be FD. The reason is bandwidth and cost. Ten
controls sending 2-byte frames is ~76 bits each; at 500 Hz that is 38 % of a
**1 Mbps** bus B (and 76 % of the BOM's 500 kbps, which is why bus B should run at
1 Mbps). FD's 64-byte payload buys nothing here. Classic also lets the transceiver
be a **3.3 V** part, which deletes the entire 5 V stage — the MCP2562FD needs
4.5–5.5 V while everything else on the board is 3.3 V. Cost: **$4.36/board versus
~$10.50** for an FD MCU + FD transceiver + two regulators. Both of those placements are forced, not chosen: the board is
installed by lowering it past the rotating magnet cap, so anything on this face
deeper than 1.5 mm must keep its whole footprint outside the cap's 5.4 mm radius.
The housing is relieved 0.85 mm behind the connector and tunnelled through the
−X web so the plug has a run-in; it needs 7.5 mm of straight travel to come off,
and there is 10.75 mm.

Routed-outline-to-copper tolerance matters here: the datasheet's max
sensing-centre-to-magnet-axis misalignment is **0.3 mm**, and JLCPCB's ±0.2 mm
outline tolerance plus the cradle's 0.15 mm slip fit spends most of it. Overrunning
it slightly costs INL only (±1.0° typ → ±1.5° max), which the per-control
calibration map removes; repeatability is untouched.

**Sizing / sourcing note.** The IC reads field **direction**, not magnitude, so
the magnet only has to land the field inside the sensor's window (datasheet §5:
**200–1,000 Gauss measured at the IC surface**, air gap **0.5 / 1.0 / 2.0 mm**
min/typ/max). Strength buys no accuracy, which in principle frees us to spend
the magnet's geometry on the axis that is actually scarce: **+Y room is tight**
(the sensor cluster sits inboard, under the body) while lateral room is free. A
diametric disc's poles sit on its curved flanks, so pole separation — and with it
how slowly the field decays across the gap — scales with **diameter**, meaning a
Ø8 × 2.0 would save 0.5 mm of Y *and* read stronger than a Ø6 × 2.5.

We are **not** doing that, on sourcing grounds: no supplier we already buy from
stocks Ø8 × 2.0. DigiKey's Ø8 diametric is 2.5 thick (saves nothing) and the
Ø8 × 2.0 is a 100-pack from a magnet specialist — a new vendor and a 12× overbuy
to save 0.5 mm, at a moment when re-anchoring the sensor cluster to the real
housing face has already reclaimed 2.6 mm of +Y. Ø6 × 2.5 is also the **reference
geometry** for this sensor class (ams' own AS5000-MD6H is D6 × 2.5), so the
published app notes apply directly rather than us estimating the field. Final
trim is the **air gap** (a printed dimension, currently 1.5 mm): measure on the
first board and adjust the gap in the model rather than re-buying magnets.

⚠ **Temperature:** the 8995 is plain N35, rated **80 °C**. That is fine in normal
use but marginal for an instrument left in a hot car; if that becomes a real duty
cycle, step up to an **N35H/SH** in the same Ø6 × 2.5 geometry (~120–150 °C).
Partial demagnetisation would weaken the field but not corrupt the angle — the
sensor reads direction — so the failure mode is graceful, not silent.

## Filament (printed parts)

Estimated at 2 perimeters (0.8 mm nozzle → 1.6 mm walls) + 15 % infill. Pickup
parts excluded. **Prices verified 2026-08-01: PCTG $29.95/kg** (was $25 — 3D-Fuel
Pro PCTG Natural), **PETG-GF $17.71/kg** (Tinmorry, measured at a real checkout 2026-09-30: the ten-roll pack is
$175, and a ten-instrument basket of 4 packs + 1 single spool blends to $17.71 — see
`elec/prices.json`; a SINGLE spool is still $25.99 on sale, $29.99 list), **TPU $22.99** (Tinmorry 95A, ⚠ **currently
SOLD OUT**). Net effect on the filament line is about **+$3**; the masses below
are model estimates and were not re-derived. The build
exports each part into its **material folder** (`petg-gf/`, `pctg/`, `tpu/`):
PETG-GF = every stiffness/creep-critical part (sustained string-tension +
ground-reaction paths); PCTG = compliant / snap-fit / fine-feature parts, and
the WHOLE deck — panels are PAIRS (transparent-PCTG base with embossed fret
lines + colour-PCTG layer) printed as one two-filament object. The deck is the
forearm rest: no glass fiber on skin-contact surfaces (abrasion exposes fiber
ends), and same-resin pairs weld/purge cleanest.

| Material | Mass | Cost | Main parts |
|----------|------|------|-----------|
| PETG-GF | ~2.3 kg | ~$41 | chassis ×3, bridge + keyhead endplates, 10 carriages, leg tubes/shafts/sockets, knee housing, pickup Z-plate |
| PCTG | ~0.65 kg | ~$16 | full deck (transparent bases + colour layers), tray, pulleys, belt clamps, knee arm, small compliant parts |
| TPU | ~45 g | ~$1 | 4 feet + 12 anti-unscrew washers + **the leg TRRS blind-mate's two retainers ×4 each** — `leg_trrs_throat` (the female jack's up-stop) and `leg_trrs_sleeve` (the male plug's cup), both on 70° bayonets. ~0.3 g each, so ~2.5 g all told; between them they replaced an M4×16 button, a brass heat-set insert, a Ø2 lock pin and two press fits |
| **Total** | ~3.0 kg | **~$58** | |

Chosen spools:

- **PCTG — [3D-Fuel Pro PCTG](https://www.3dfuel.com/collections/1-75mm-pro-pctg)**:
  [Natural/Clear](https://www.3dfuel.com/products/pro-pctg-natural-1-75mm) for the
  transparent deck bases (the fret-line light path wants the clear grade), plus a
  colour of choice for the deck colour layers + the rest of the PCTG parts.
  Publishes a TDS; AMS-compatible spool — the deck's clear+colour pair can run
  from one AMS.
- **PETG-GF — [Tinmorry PETG-GF](https://tinmorry.net/en-us/collections/petg-gf)** ($17.71/kg in the ten-roll pack, ~$26–30 for one spool).
  No published TDS, so **verify the first spool** with a bend coupon before
  committing the chassis: 10×10×140 mm bar, 120 mm span, 1 kg at centre —
  ~0.5 mm deflection ⇒ ~2.8 GPa (buy); ~0.9 mm ⇒ plain-PETG stiffness (return).
  Elegoo PETG-GF (flex modulus 3345 MPa, published) is the documented fallback.
  Vendor recommends a hardened ≥0.4 mm (ideally 0.6 mm) nozzle.
- **TPU — [Tinmorry TPU 95A](https://tinmorry.net/en-us/products/filament-tpu-1-75-mm-tinmorry-3d-printing-materials-tpu-filament-for-fdm-3d-printer-1-kg-1-spool-black)**
  — **$22.99 (from $24.99), but ⚠ SOLD OUT as of 2026-08-01.** Only ~40 g is
  needed, so any 95A spool serves; pick a substitute at order time rather than
  waiting on this SKU.
  (Shore 95A±2 — right grade for floor grip + preload washers; 68D "AMS-safe"
  TPU is 5–10× stiffer and grips poorly). Dry 70 °C / 8 h before printing;
  **not AMS-compatible** — run the feet + washers from the external spool.

## Wire

Modeled internal harness ≈ 5.2 m of single-conductor runs; physically ~10 m once
power/CAN are pairs and audio is shielded. Gauges (the SERVO42D driver rides the
motor, so there are **no stepper phase leads** — noise defence is shielding +
twisting + the bridge-side AFE buffer, not conductor size):

| Net | Cable | OD |
|---|---|---|
| 24 V bus | **2 × 22 AWG per rail** silicone, twisted/flat (fleet slew staggered <5 A; ~0.3 V drop over the run) ⚠ **was 20 AWG — see the note below** | ~2.4 |

> ⚠ **AND NEITHER IS THE PCB COPPER — the third link in the same chain, audited
> 2026-09-18.** The wire was raised to 2 × 22 AWG for <5 A and the XH contacts were
> doubled for <5 A. The board traces between them were never sized at all. Every net on
> every board in this fleet was drawn at the one board-wide netclass width, **0.25 mm**,
> because no per-net width mechanism existed in the generator — `track_mm` was a single
> number per board with nothing overriding it for a power net.
>
> ⚠ **THAT LAST SENTENCE IS NO LONGER TRUE and this note is kept for the audit trail.**
> `net_widths` was added to `elec/layout.py` the same day (a dict of net-name pattern →
> width, which builds a netclass per width and assigns it), and `output_panel` and
> `motor_ctrl` both use it to put their 24 V rails on **0.5 mm** — 1.45 A, not 0.88.
> The shortfall below is therefore the state that prompted the fix, not the state today.
> What is still true is the conclusion the fix could not reach: 0.5 mm is as far as a
> blanket netclass goes, because these nets land on 0402 pads 0.6 mm wide, so the J6→J7
> pass-through still wants deliberate 2.8 mm trunk copper that no netclass can express.
>
> By IPC-2221 at a 10 °C rise, 0.25 mm carries:
>
> | trace | capacity |
> |---|---|
> | 0.25 mm, outer, 1 oz | **0.88 A** (1.19 A if 20 °C rise is accepted) |
> | 0.25 mm, inner, 0.5 oz | **0.26 A** |
> | needed for 5 A, outer 1 oz | **2.77 mm** |
> | needed for 5 A, inner 0.5 oz | 14.4 mm — an inner layer cannot do this job |
>
> So the panel's 24 V trunk is carrying a <5 A budget on copper rated 0.88 A, a shortfall
> of roughly 5.7×, and any part of it the router put on an inner layer is far worse.
> The optical board's own 24 V inlet is fine by contrast — **79 mA** against 0.88 A — so
> this is about the TRUNK nets, not every net. (This said ~324 mA until 2026-09-18, which
> is that board's **5 V rail** current; through an 85 % buck it is 79 mA at 24 V. The
> conclusion was right and the number was four times too big.)
>
> ⚠ Nothing in the pipeline can see this. DRC checks copper against the netlist and has
> no concept of current; the netlist has no concept of width. It needs a per-net width in
> the generator, and until that exists the trunk cannot be widened even deliberately.
> (Stack-up assumed JLCPCB standard 4-layer: 1 oz outer, 0.5 oz inner. The boards do not
> declare copper weight anywhere, which is its own gap.)

> ⚠ **The wire is sized for <5 A; the connector contacts are not, in one place.**
> XH is rated **3 A per contact**, which is why the panel's 24 V outlet (J7) puts
> two contacts on each rail. Audited 2026-09-17: the motor controller's inlet J3
> was taking all of it through **one** contact — a doubled source into a
> single-contact sink is not doubled — and that is now fixed, along with the
> optical board's J2, so every 24 V connector in the instrument is
> `1=GND 2=+24V 3=+24V 4=GND`.
>
> **The bottleneck moves rather than disappears.** The motor controller's bus
> outputs J1/J2 carry 24 V on a *single* conductor, because bus A/B is the
> four-wire CAN-plus-power scheme (GND, +24 V, H, L). Bus A feeds ten SERVO42D
> drivers, so nearly the whole <5 A passes through one 3 A contact. Doubling J3
> was free (its ways were idle); doing it at J1/J2 is not, because those ways
> carry CAN. **Open:** a wider shell, a separate power bus, or a measured slew
> budget showing the staggered peak really is under 3 A.
>
> ⚠ **THE PARAGRAPH ABOVE MAY BE CHASING A PROBLEM THAT DOES NOT EXIST — audited
> 2026-09-18 and left standing only because the answer is not certain.** It assumes the
> motors draw their current *through* J1. `elec/motor_ctrl.py` states the opposite in
> as many words: *"THE MOTOR CURRENT NEVER COMES THROUGH HERE. The chain runs output
> panel → tees → keyhead and every motor taps at its own tee, so what reaches this board
> is its own draw plus the Pi's 5 V worth — about 0.7 A at 24 V."*
>
> **The harness supports the board file.** `src/wiring.py` builds the trunk from the
> output panel's J7, out to tee 10, then west along the rail through the tees, and
> *terminates* it at the motor controller's **J3** — "THE TRUNK ENDS AT THE MERGED
> BOARD … the chain simply terminates at a connector on a board". On that topology the
> motors tap upstream of this board and J1 carries CAN plus its own modest draw, not
> 5 A, and there is nothing here to fix.
>
> **What is genuinely open is narrower and different:** J1's cable carries a 24 V
> conductor to the same tees the trunk already feeds, which is a *second* path to the
> same nodes. Either it is a parallel feed nobody designed as one, or bus A's cable
> should carry CAN only. That question decides J1's current, and neither file answers
> it. Until it is answered, do not spend a wider shell on this.
>
> ⚠ **And the third option is almost certainly the right one, because the screw is
> self-locking.** `Tr8×2`'s 5.2° lead angle holds tune with the motor de-energised
> — that is why the drivetrain chose it, and it is recorded as "zero-power tune
> hold". So at rest the bus carries essentially **nothing**: the current is set
> entirely by how many motors are *moving at once*, not by how many exist. A pedal
> or lever change moves two or three strings, which at a NEMA17's few hundred mA of
> supply current is comfortably inside one XH contact's 3 A.
>
> That turns a connector problem into a **firmware limit**, and a cheap one: cap
> the number of simultaneously-slewing motors. The number to pick needs the
> SERVO42D's actual 24 V supply current, which is **not recorded anywhere in this
> file** — the only figure is the fleet's "<5 A", which is a budget rather than a
> measurement. **Measure one motor before trusting any of this**; if a single
> moving motor turns out to draw over 1 A, three at once already exceeds the
> contact and the stagger limit has to be two.
>
> ⚠ **And 20 AWG would not have fitted the connector at all.** JST's XH datasheet
> gives *Applicable wire: AWG #30 to #22* and rates the contact at **3 A at AWG
> #22**. Every 24 V connector in the instrument is XH (the lever board's is the
> smaller **PH**, AWG #32–#24 at 2 A). 20 AWG is outside both ranges — it does not
> crimp. The wire gauge was chosen for the drop budget and the connector for the
> crimp order, and nobody had put the two datasheets side by side.
>
> **The doubling resolves both at once**, which is why the row above now reads
> 2 × 22 AWG per rail. Two 22 AWG conductors in parallel are 26.4 mΩ/m against a
> single 20 AWG's 33.3 — *more* copper than the spec it replaces — and each
> contact then carries half the current, inside the 3 A rating. One change fixes
> the gauge, the rating and the drop together.
>
> ✅ **The lever board's PH connector is fine, and here is the arithmetic that
> retires the question.** Bus B feeds **eleven** sensor boards, not steppers (this
> read "eight" until 2026-09-18 — 6 knee levers + 5 pedals, see the sensor-IC row).
> Each is a CH32V203 (~30 mA), an MT6701 (~18 mA), a recessive SN65HVD230 (~10 mA)
> and an LDO — about **59 mA at 3V3**, so eleven boards are **0.65 A at 3V3**.
>
> ⚠ **That is also the bus current, because bus B is 5 V and the regulator is an
> LDO.** This line read "roughly 105 mA at 24 V" until 2026-09-23, and the mistake
> is worth naming because it is the easy one to make twice: 105 mA is what you get
> by conserving POWER across the regulator, 0.65 A × 3V3 / 24 V. That arithmetic
> describes a **buck**. An LDO is a series pass element — it burns the difference
> as heat and passes the SAME current — so dropping the bus from 24 V to 5 V did
> not divide the bus current by five, it **multiplied it by six**, to 0.65 A.
>
> The conclusion still holds, with a much smaller margin than the old number
> claimed: 0.65 A is **33 % of PH's 2 A** contact rating rather than 5 %. What the
> correction does change is that the margin is now worth watching — the leg drop's
> **ZH is rated 1 A**, and it carries only the five pedal boards (5 × 59 mA ≈
> **0.30 A, 30 % of ZH**), which is the reason that joint can use the smaller
> connector at all. Adding boards to the leg drop is no longer free. The
> 26 AWG the CAN cable already specifies sits mid-range in PH's AWG 30–24 window.
>
> **The two families map cleanly onto the two buses**, which is why this works: bus
> A (ten steppers, the high-current one) is XH end to end, and only bus B crosses
> XH→PH — at a twenty-fifth of the rating. The gauge argument above therefore
> applies to the 24 V *trunk* and to bus A, not to bus B.
>
> ⚠ **The CAN cable carries the 24 V as well, and only its signal pair is
> specified.** Bus A and bus B are the user's four-conductor scheme — black GND,
> red +24 V, yellow H, green L — so the cable row above ("26 AWG twisted pair")
> describes two of the four conductors. The other two feed **ten SERVO42D
> drivers** on bus A, i.e. very nearly the whole <5 A. At 26 AWG that would be
> 132 mΩ/m, which is not a candidate; the power pair needs its own gauge and it
> has never had one. This is the same bottleneck as the single-contact J1/J2
> above, seen from the cable end rather than the connector end — and both have to
> be answered by the same decision about how bus A carries its current.
| CAN | 26 AWG twisted pair, 120 Ω terminated — ⚠ **this is the H/L pair only; the same cable's 24 V and GND conductors have no gauge** | ~2.2 |
| 24 V → optical board | **4 × 26 AWG**, ~150 mm, XH crimps both ends — panel **J9** to optical **J2**, both `1=GND 2=+24V 3=+24V 4=GND`. ⚠ **Was missing entirely:** the connector exists at both ends and this row did not, found 2026-09-18. 26 AWG is ample here — the board draws **79 mA at 24 V** typical (324 mA on its 5 V rail through an 85 % buck), ~122 mA at the worst case in `elec/optical.py`'s budget, against XH's applicable #30–#22. It runs beside the ~150 mm USB cable between the same two boards | ~2.2 |
| **bus B, pedal segments** | **4 × 26 AWG** twisted (GND / +5 V / CAN_H / CAN_L), **~100 mm each, ×5**, PHR-8 both ends, ways 5–8 of one board to ways 1–4 of the next. Cut to fit: a pedal's station is printed into the bar, so these lengths are fixed. Each runs from its board's bay up through the **spur** into the trough (INSTALL_NOTES PB-1). The **levers** are the adjustable ones and they get the slack scheme instead — see `knee_lever.lace_loop` | ~2.5 bundled |
| pickup / audio / DAC / out | 28 AWG **shielded** pair (mA signals — the shield is the spec) | ~2.0 |
| USB panel → Pi | slim shielded USB-2 | ~2.6 |
| logic (relay, link, TDM, OLED, joystick) | 28 AWG | ~1.4 |

A 45 m hookup spool (~$20) covers power/CAN/control; ~1.5 m shielded pair
(~$16) for the pickup/audio runs. **~$35.** Excludes the **11 control sensor drops** (5 pedals + 6 knee levers,
not yet modelled) and the optical pickup's USB + 5 V feed. All cross-rib raceways pass ≤ Ø2.6 and sit above the
knee-lever mortise plane — route no fatter cable through the floor trunk.

## Connectors (wiring strategy, July 2026)

### Leg blind-mates — POGO BOARDS, 2026-09-21 (user)

Both leg joints (leg ↔ body adapter, pedal bar ↔ adjust tenon) are now **two PCBs
each**, and the whole TRRS stack is gone: no jack, plug, float spring, TPU throat,
TPU sleeve or bayonet, and no moulded cable. CAD: `src/leg_pogo.py` (boards drawn
from the component drawings; **bronner routes the real boards from it**).

| Item | Part | Qty | Unit | Note |
|---|---|---|---|---|
| **Male pogo board** | custom 13.0 × 19.0, 1.6 mm, **STANDING ON EDGE** in a slot in the tenon end: a **right-angle** 1 × 4 spring-pin header on its lower edge + a **side-entry** PH on its upper edge, mouth up the leg. **Every part on ONE face** | 2 | ~$2 assembled (est.) | on the LEG; the free tips sit **0.6 inside** the tenon face. One M4 × 20 runs **sideways** through the tenon and the board (head recessed in one flat, insert pressed into the opposite flat from outside) — the tenon end is exposed whenever the leg is off |
| **Female pogo board** | custom ~10 × 17, 1.6 mm, lies flat on the adapter's roof / the bar's floor: a **gold target** + a **side-entry ZR** on ONE face, one M4 × 6 beyond the target's end | 2 | ~$2 assembled (est.) | Single-sided. The contacts are the TARGET's own gold, so the panel stays on **HASL** — ENIG for the whole panel was +$16.60 (1 µin) / +$33.16 (2 µin) per order on one small test board, scaling with area. One screw, reached down the empty mortise |
| **Contact target, vertical 1 × 4** | Xinyangze **YZ185115035T-04025-01**, LCSC **C54930022**: 4 × Ø1.2 contacts at **2.54** pitch (the header's 2.5 — 0.06 at the ends, in the landing budget), 3.5 tall, 3 µin Au over Ni, SMT | 2 | $1.03 @10 | **210 in stock** — the thinnest-stocked part here; buy spares. Its right-angle twin C5296825 is the header's exact mate but would stand the female on edge, which the adapter's 12.8 cannot take |
| **Spring-pin header, right angle 1 × 4** | Xinyangze **YZ165615055F-04025-02**, LCSC **C54799748** — or the **-01, C5296819** (same drawing). SMT, 2.5 pitch, 11.0 × 2.5, 5.5 free / 4.0 working, Ø1.0 plunger, **120 gf**, 1 A, 12 V, 10k cycles, 3 µin Au | 2 | $1.46 @10 | **1,467 + 910 in stock** at JLCPCB. ONE pin per circuit — two headers side by side (22 of pads) do not fit the female board inside a 24-square tenon (`leg_pogo` docstring). JLCPCB flag it a hard-to-process part: tick it by hand in the BOM step (+$0.08 each) |
| **Harness header, male (side entry)** | JST **S4B-PH-SM4-TB(LF)(SN)**, LCSC **C265102** (Extended, 30k stock) | 2 | ~$0.25 | 11.9 × 6.0 (+2.6 tails) × 5.5; the PHR-4 reaches 3.6 past its mouth |
| **Harness header, female (side entry)** | JST **S4B-ZR-SM4A-TF(LF)(SN)**, LCSC **C485354** (27k stock) | 2 | ~$0.2 | 9.0 × 5.0 (+1.5 tails) × 3.7 (eZR p.5). ZR sockets are IDC; the header also takes the **ZH crimp** housing (ZHR-4 + SZH-002T), so the two female stubs are ZH-to-PH jumpers — a second crimp family (its own contacts and die) |
| **M4 × 20 button** + **M4 × 6 button** + **M4 heat-set inserts** | — | 2 + 2 + 4 | — | one screw per board (project PCB rule); the inserts have no self-tap fallback (`leg_pogo._INS_WHY`) |
| **Leg harness** | **two twisted pairs** of 28 AWG 7/36 PVC hookup wire (CAN_H/CAN_L, 5V/GND), **laid up as a 4-core** — the two pairs twisted around each other at ~5× the pair lay, capped by a 6 mm adhesive-lined heat-shrink collar behind each crimp — PHR-4 + SPH-002T at both ends | 1 leg run + 2 stubs | — | replaces the 10-02135 lead; crimped **after** threading, so the bores only have to pass contacts. Bundle ~Ø2.4 (`leg_pogo.HARNESS_D`); the leg's slack is heat-set into a coil on `coil_mandrel` (barrel now Ø16.8; stretched r 7.94 against a 7.2 floor). A round jacketed 4-core was rejected: the datasheeted ones that fit the bores are too fat (Alpha 86004 is Ø4.83) and none pairs CAN_H with CAN_L |

**Why the male board stands on edge:** the panel shares one assembly setting (user), so
no board may carry parts on both faces. The live JLCPCB quote (2026-09-21, 5 boards,
Standard, list prices) settled what that is worth: a through-hole PH on the bottom is
billed **Both Sides** — setup $25.75 → $51.50 and a **$16.54 fixture**, ~$45 an order —
and Economic PCBA has no Both Sides at all. On edge, a right-angle header and a
side-entry PH share one face. **Why the pins are on the leg:** the body adapter has 12.8
above its mortise roof; only the flat female fits there. **Why one header:** the female
board lies above the host face, so all of it must fit in the tenon's pocket, and two
headers' 22 of pads plus a connector and a screw do not (the diagonal leaves ~23 × 7).

**Open:** (1) the PHR-4's seated height on the top-entry header is an allowance (8.5
mated) — JST do not dimension the floor; (2) the pads face UP at the bar joint, so dust on
them is the thing to watch; (3) the header's plunger line (1.3 off the board) is read off
a view whose datum is not stated — confirm on a sample before bronner fixes the pads.


Rule: **solder only happens on factory-assembled PCBs; every field connection
is a connector** (no bare wire ever meets a bare module pin; never
inline-splice — user priorities: damage-free un/re-mating beats install
speed, and **no personal soldering work**: the only bench work is XH
crimping). Two classic-CAN buses at 500 kbps: **bus A motors** (the motor controller's CAN1, REMAPPED to PB8/PB9 →
10× SERVO42D, each on a MADE 4-wire pigtail (⚠ 2026-10-01: the driver has no XH -- it has screw terminals, power on a 6-way and CAN on a 5-way on the opposite edge; the pigtail is four ferruled wires into those, gathered into one XHP-4 for the tee; see `docs/servo42d-fit.md`) — power AND CAN; ~1–1.5 A input
at 24 V sits inside XH's 3 A rating, so no separate motor power connector —
120 Ω fixed at both ends) and **bus B inputs**, a **TRUNK-AND-DROP** bus:
crimped 4-wire XH jumpers run point-to-point between **TEE PCBs** (one per
pedal/lever station: 3× B4B-XH-A — trunk in, trunk out, drop — plus a 120 Ω
terminator behind a slide switch, ON only on the last tee), and
each device hangs off its tee by ONE short XH drop — so unplugging any
device NEVER breaks the bus, and every trunk segment is individually
replaceable. The trunk crosses the instrument's only TWO TRRS joints, both
SELF-MATING: the leg↔bar auto-mate (driven by the press that seats the
tower spigot) and the leg↔body joint
(the column-top plug blind-mates the chassis jack during the final thread
turn — deterministic clocking sets the depth, and the plug's annular
contacts rotate freely, so threading twists no wires). The SERVO42D is classic-CAN-only, which is why any bus with
motors runs classic; sensor boards still get FD-capable transceivers to keep
the FD option on bus B. XT30 only at the PSU trunk joints.

⚠ **OPEN: TWO INCOMPATIBLE PINOUTS SHARE ONE 4-WAY XH HOUSING** (found 2026-09-18,
user asked where the "standard" power cable is used and the premise did not survive
the question). Every 4-way XH in the instrument is one of two patterns:

| pattern | pins 1 2 3 4 | where |
|---|---|---|
| **A, CAN drop** | `GND +24V CAN_H CAN_L` | can_tee J2, motor_ctrl J1/J2 (and the 8-ways are two of these back to back: can_tee J1, lever_sensor J1) |
| **B, power only** | `GND +24V +24V GND` | optical J2, output_panel J7/J9, motor_ctrl J3 (J5 is the same at 5 V) |

**A 4-way XH plug mates with any 4-way XH header** — the family has no
per-application keying — so a CAN drop cable physically fits a power inlet and a
power cable fits a motor's CAN drop. **Pins 1 and 2 agree in both patterns**, which
makes it worse rather than better: a mis-mated node powers up normally and fails on
the signal pins. A power cable in a CAN socket puts **+24 V onto CAN_H**, against an
SN65HVD230 bus pin rated −4 to +16 V, and the bus is shared, so one wrong plug can
take several transceivers with it.

This is not hypothetical maintenance-only risk: the project's standing rule is that
every field connection is a connector, so these are all meant to be unplugged.

Not yet fixed — the options trade against each other and against the connector
strategy: (a) give pattern B a different position count, costing one housing SKU;
(b) drop the doubling so B becomes `GND +24V NC NC`, which makes BOTH mis-mate
directions harmless at zero SKU cost, but **J7 cannot take it** — it passes the
fleet's whole <5 A and needs two contacts against 3 A each; (c) move the true power
feeds to XT30, which the BOM currently restricts to PSU trunk joints.

### Dual-feed 24 V trunk (option A, locked 2026-09-18 by user)

> ⚠ **READ THIS FIRST — THE BALANCE ARITHMETIC BELOW IS SUPERSEDED (2026-09-30).** It treats
> the chain as wire. It is not: per tee, per rail, the path is
>
> | element | resistance |
> |---|--:|
> | 45 mm of 22 AWG between tees | ~2.4 mΩ |
> | tee copper, trunk-in → trunk-out | ~5.4 mΩ (was **~55 mΩ** as 0.25 mm router track until `6346db5`) |
> | two XH contacts (in, out) | up to ~20 mΩ (10 mΩ each is JST's initial maximum — a ceiling, not a measurement) |
> | **one hop** | **~28 mΩ**, so the nine-hop chain is ~250 mΩ per rail |
>
> With ten equal loads the east feed's share is `(10·Rw + 45·Rh) / (10·(Re + Rw + 9·Rh))`,
> where `Re`, `Rw` are the two feed leads and `Rh` one hop. `Re` is ~4.8 mΩ (180 mm, two
> conductors); `Rw` is ~15.4 mΩ of cable plus the motor board's J3→J1 copper plus the
> bus-A lead.
>
> ✅ **FIXED 2026-10-01: J3 → J1 is a declared 2.0 mm B.Cu bar** (45.5 mm of 1 oz outer
> copper, ~11 mΩ, ~4 A at a 10 °C rise; J3's two +24 V ways tied by 1.2 mm). Routed
> 0 unconnected / 0 violations, audit passes. `Rw` falls from ~110 to **~30 mΩ**, and with
> the same model as below (uniform load on a 250 mΩ chain, east share =
> (Rw + chain/2) / (Re + Rw + chain); it reproduces the old 64 %) the split is now
> **east 54 % / west 46 %**: all ten moving is 4.4 A east, 3.6 A west, and the west share
> rides copper rated for it. The paragraphs that follow are the BEFORE state, kept for the
> reasoning; "it is not done here either" is no longer true.
>
> ⚠ **THE MOTOR BOARD'S SHARE IS NOW MEASURED, AND IT IS THE WHOLE STORY** (traced on the
> routed board, 2026-09-30). J3 pin 2 reaches J1 pin 2 through **35.9 mm of 0.5 mm track on
> In2.Cu** (0.5 oz inner copper, ~71 mΩ), a via, and 20.7 mm of 0.5 mm on F.Cu (~20 mΩ):
> **~91 mΩ on the +24 V rail**, with J3's second +24 V pin joined to the first by 2.5 mm of
> 0.25 mm track. GND returns through planes and is not the problem. So `Rw` is ~110 mΩ
> against `Re` 4.8, and the east feed carries about **64 %**, the west 36 %.
>
> That inner track is good for well under 1 A at a 10 °C rise. Three motors moving puts
> ~0.9 A through it; all ten would put ~2.9 A. **The "board copper J3→J1 must widen" line
> in the table below was never done.** It is not done here either, deliberately: the fix
> depends on the open tee decision. If the power trunk becomes a continuous pair with one
> tap per tee, the J10 cable plugs into that trunk and the motor board is OFF the motor
> power path altogether — the cheapest possible fix. If the 8-way trunk stays, J3→J1 needs
> deliberate 2 mm copper on B.Cu, which is a re-layout of a board that is full there.
>
> **So the 111 mm coil is worth about ONE percentage point** (5.9 mΩ against a 250 mΩ
> chain), not the six it was credited with, and the split is decided by the west path's
> copper instead. Do not build or model the coil; if the split matters, widen J3→J1 on the
> motor board. The **TODO to model the coil in the CAD is withdrawn** with it.
>
> **And the limit that actually binds is unchanged:** at the derived 0.8 A per moving
> motor, half the fleet is 4 A through one 3 A XH contact whatever the split is. Either
> firmware caps the number of motors slewing at once, or the trunk's power leaves the
> 8-way connector — the open tee question (continuous power trunk, one tap per tee).

The tee chain is fed from **both ends** so the worst-loaded segment carries about half
the fleet instead of all of it. The single +24V contact between tees is a 3 A / 72 W
ceiling, and this is what relieves it without touching the tee board — which matters,
because a bigger trunk connector does not fit: the tee pitch is **44.7 mm**, set by the
motors, and an 8-way VH trunk row comes to 47.3 mm. It collides with its neighbour in
any orientation, and turning the plugs to face along X is worse (the board is 16 mm deep
and the tail band already sits 6.0 mm from the +Y edge against a 6.4 mm wall).

| leg | cable | note |
|---|---|---|
| panel **J7** → east end of the chain | 4-way XH, 2× +24V + 2× GND | **+ 111 mm of coiled slack** |
| panel **J10** → `motor_ctrl` **J3** | 4-way XH, 2× +24V + 2× GND, ~582 mm | new connector, new cable |
| `motor_ctrl` **J1** → west end of the chain | existing bus-A cable | board copper J3→J1 must widen |

**⚠ THE COIL IS 111 mm, ON THE J7 (EAST) CABLE, AND IT IS DELIBERATE RESISTANCE.** The two
feeds are wildly asymmetric: J7 reaches the chain in 180 mm while J10 travels 582 mm to
get there, so without correction the east feed carries 5.6 of the 10 motors and the west
4.4 — 56 % on the worst feed instead of 50 %. Two things fix it, and both are already
paid for:

* J10 is a **4-way carrying only power**, so both +24V ways parallel and its 582 mm
  behaves like 291 mm. The trunk cannot do this: two of its four ways are CAN.
* **111 mm of coiled slack on J7** brings the split to exactly 5.00 / 5.00.

The cost of that deliberate resistance is **0.0059 Ω, or 0.018 V of 24 at 3 A — 0.07 %**.
Without the doubling the coil would have to be 403 mm; with it, 111 mm.

**Wind the +24V and its GND return TOGETHER as a pair.** A coil carrying DC is
electrically nothing, but motor current is switched, and ~111 mm wound tightly is enough
series inductance to ring against the drivers' input capacitance. Wound bifilar the
outbound and return fields cancel. This is free if the pair is simply not separated.

**⚠ TODO — MODEL THE COIL IN THE CAD (user).** `src/wiring.py` routes trunk segments as
swept paths; 111 mm of slack needs a real home with a bend radius, a retention point and
clearance from the motors, or it becomes loose wire in a machine full of moving belts.
It is currently in no model.

**⚠ AND THE WHOLE THING RESTS ON AN UNMEASURED NUMBER.** 0.8 A per moving motor is
DERIVED — 147 N of string tension through a Tr8×2 leadscrew at 37.2 % efficiency, plus an
estimated ~4 W of copper loss — not measured. This BOM records SERVO42D's real 24 V
supply current as written down nowhere. At 0.4 A none of this is needed; at 1.2 A it is
not enough. **One clamp-meter reading during a pedal change decides whether to build any
of it**, and costs less than any of the options it would settle.

### Instrument power budget — and there is no PSU on this BOM

⚠ **NOTHING HERE SPECIFIES A SUPPLY.** There is an XT30 row "PSU trunk only" and no
supply, no wattage, no part. Every per-board budget in this file sizes a *buck*; none of
them add up to what feeds the instrument. Itemised 2026-09-18, at the 24 V inlet:

| load | worst case | playing |
|---|---|---|
| 10 × SERVO42D, bus A (the <5 A budget cap) | 120.0 W | 30.0 W |
| Raspberry Pi + USB, via buck | 16.7 W | 5.6 W |
| **Lighting: 2 fret boards + 2 foot boards, on the fused 24 V bus (F3, 3 A)** | **40.8 W** (1.70 A: frets 0.93 + feet 0.77, every LED full white, green / blue / white at their 3.4 V maximum) | firmware cap, **not yet set** |
| optical board | 2.9 W | 1.9 W |
| 11 sensor boards | 2.5 W | 2.5 W |
| output panel | 1.0 W | 0.9 W |
| motor controller | 0.9 W | 0.9 W |
| **total** | **185 W / 7.7 A** | **42 W / 1.7 A + lighting** |

**Chosen 2026-10-01: 24 V 160 W (6.67 A), Mean Well GST160A24-R7B desktop adapter** (row `psu_24v_160w`), with the lighting power-capped in firmware; 24 V 240 W
covers every load at maximum simultaneously, which nothing makes happen.

⚠ **WHAT THE 160 W LEAVES THE MOTORS DEPENDS ON THE LIGHTING CAP (re-worked 2026-10-01, after the
5 V strip was deleted).** Supply 6.67 A, less Pi 0.70, less optical + sensors + panel + controller
0.30: **5.67 A to share between motors and lights.** Lights uncapped (1.70 A) leave the motors
**3.97 A**; the 4.6 A the tee and supply discussion assumed needs the lights held to **1.07 A
(25.7 W, 63 % of full white)** — which is the old strip's figure, so the daemon's cap should be
set there, or lower while motors slew.

**The 120 W motor line is a cap, not a draw.** The self-locking screw means there is no
holding current, so motors pull only while a pedal moves, and moves stagger. See the
bus-A contact-current note above, which is the same figure viewed as a connector problem.

**The lighting is the only load that is on continuously**, so it matters more for heat and
for the supply's continuous rating than its share of the peak suggests. Every lit board makes its
own LED rail from the 24 V bus (TLC5971 constant-current drivers; `docs/lighting-bus.md`,
`docs/fret-led.md`), so the cap is one number in the effects daemon's output stage: sum the frame
and scale.

**PCB buying plan**: tee PCBs + sensor PCBs ship as ONE panel (V-score /
mouse-bite, snap apart — never hand-cut FR4), ONE assembly job, **full paid
assembly including the THT headers** (accept the standard-tier fee if
economic PCBA rejects THT; incremental tee assembly ≈ $7–12). Zero personal
soldering also applies to the former "bench-once pigtail" points: every
TRRS is either factory-molded-on-cable (Tensility, cut + crimp) or
factory-assembled on the leg carrier PCB, and XT30 arrives as **pre-wired
pigtails** (or XT30PW board-mount on the power distribution PCB) — pick
whichever quotes cleaner at order time. NO consignment anywhere: all PCB
parts are LCSC-library.

Prices **re-verified on DigiKey/LCSC 2026-08-01** (stock healthy unless noted).
This whole table held up except the chassis TRRS jack, which was **$3 low**. XH harness = crimp-your-own (contacts ~$0.03 vs
$0.59–0.78 per pre-crimped lead — 20×; needs a ~$25–45 tool, below).

| Role | Part | Qty | Price (verified) | URL | Notes |
|------|------|-----|------------------|-----|-------|
| **TRRS plug + cable** (bar cradle) | Tensility **CA-354S** (053-0113R): molded plug Ø10, barrel Ø3.5×14, 1.83 m Ø3.7 shielded 26 AWG cable, tinned ends | 2 | **$3.53 / $2.996 @10** [v] | [DigiKey](https://www.digikey.com/en/products/detail/tensility-international-corp/CA-354S/382910) | zero-solder: cut cable to length, crimp XH on the cut end. #1 = bar cradle → first bar tee; +1 spare. (The old #2 "leg-column riser" is DELETED — the column is an off-the-shelf extension cable now, next row.) [Drawing](https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/053-0113R.pdf) |
| **TRRS M→F EXTENSION cable** (the WHOLE wired leg column) | Off-the-shelf 3.5 mm 4-pole (TRRS) headset extension, ~1.2 m, shielded; **pick at purchase & verify**: molded plug handle ≤ Ø10 (head seat), inline jack barrel ≈ Ø9.1–9.7 × ≤40 (shaft seat, 10-03404-class envelope) | 1 | ~$5–8 | (commodity; e.g. DigiKey/Amazon 4-pole extension) | ZERO connections on the leg (user): the molded PLUG sits captive in the leg head (blind-mates the chassis jack), the molded FEMALE barrel seats mouth-down in the shaft block (receives the bar tower's plug), the middle gets the heat-set slack COIL (Ø8 mandrel, 85 °C). No solder, no crimps, no junction anywhere in the column. |
| **TRRS jack + cable** (chassis, above the -X/+Y socket) | Tensility **10-03404**: molded jack Ø9.1×39.4, 0.91 m Ø3.8 shielded 28 AWG cable | 1 | **$8.19 / $6.96 @10** [v] ⚠ | [DigiKey](https://www.digikey.com/en/products/detail/tensility-international-corp/10-03404/11196637) | embedded VERTICALLY above the socket — the column-top plug BLIND-MATES on the assembly press (plug spins freely in the jack → no wire twist); cable → tee 12 (crimp XH at the cut end — off-leg). [Drawing](https://tensility.s3.us-west-2.amazonaws.com/uploads/pdffiles/10-03404.pdf) |
| **TRRS jack, SMT** (leg-shaft auto-mate, on the leg carrier PCB) | LCSC-library compact SMT jack, **pick at PCB design** (SJ-4351X-class, ~13×6×5) | 2 | ~$0.30 | LCSC | the only form factor that fits the Ø20 shaft; factory-assembled on the carrier (no consignment). Pocket gets rebuilt around the chosen part's drawing. Fallback: Same Sky SJ-43514-SMT-TR via JLCPCB global sourcing |
| **XH crimp contacts** | JST **SXH-001T-P0.6** | 300 | **$0.0235–0.047** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=SXH-001T-P0.6) | 22–30 AWG; qty includes learning-curve scrap |
| **XH housings** | JST **XHP-2 / XHP-4 / XHP-6** | ~30 | **$0.10** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=XHP-4) | contacts click in by hand, extractable; ~~XHP-6 mates the SERVO42D pigtail~~ the SERVO42D has screw terminals and no XH (2026-10-01); its made pigtail ends in an **XHP-4** at the tee |
| **XH header**, SMT side-entry | JST **S4B-XH-SM4-TB** | 1 | **$0.6577 / $0.2889 @800** [v] | [LCSC C161861](https://lcsc.com/product-detail/Wire-To-Board-Connector_JST-S4B-XH-SM4-TB-LF-SN_C161861.html) | **OPTICAL board only (J2), qty 1** — corrected 2026-09-19 from "8, sensor boards only", which was true until the sensor board moved to an S8B-XH-A and stopped using this part at all. It earns the second part number: it is the piece that lets a board be SINGLE-SIDED. SMT (no post tails through a face that has to seat), side entry (a top-entry plug would have to be inserted from inside the housing). B = 15.0, 7.0 tall, 6.1 body depth, 4.5 mouth. Mates the same XHP-4 plugs and crimps as everything else, so the harness is unaffected. ~40k in LCSC stock; in JLC's library as C161861 — check it is orderable for assembly at quote time |
| **XH headers**, THT top-entry | JST **B4B-XH-A(LF)(SN)** ×6, **B2B-XH-A(LF)(SN)** ×1 | 7 | **$0.17** [v] | [DigiKey](https://www.digikey.com/en/products/result?keywords=B4B-XH-A) | motor_ctrl ×4 and output_panel ×2 (B4B) — motor_ctrl J2 (the lever bus) went **PH** 2026-09-21, see the next row, output_panel J9 ×1 (B2B). Counted from the built fab packages by `elec/part_totals.py`, not by hand — this row said "~30" and named a B6B, and there is no B6B anywhere in the design. B4B is C144395, B2B is C158012, both verified. Modelled from JST's own drawing (`cadkit.pcb.jst_xh_header`): B4B is **12.4 × 5.75**, **7.0 mm** tall bare and **9.8 mm mated** — the mated figure is the one clearances must use — with □0.64 posts reaching 3.4 mm below the seating plane, i.e. **1.8 mm proud** of a 1.6 mm board's far face. The pin row is **2.0 mm from one long edge, 3.75 from the other**, so the part is not symmetric about its pins and which way it faces is a real layout decision |
| **XH header**, SMT side-entry 8-way | JST **S8B-XH-A(LF)(SN)** | **10** | **$0.1785 / $0.1418 @50** [v] | [LCSC C157914](https://lcsc.com/search?q=S8B-XH-A) | **THE MOST NUMEROUS CONNECTOR IN THE INSTRUMENT, and it was missing from this table entirely until 2026-09-19.** 10 CAN tees, one each (**the 11 lever/pedal sensor boards moved to PH, 2026-09-21 — row below**); both carry the bus THROUGH, so the 8 ways are the trunk twice over (in on 1–4, out on 5–8) in the one pin order `elec/harness.py` defines. **Watch the stock:** 160 pieces at last check is 7.6 instruments — the second tightest part in this BOM after the photodiode, and it only became a 21-per-instrument part when the sensor board's connector changed on 09-18 |
| **PH header**, SMT side-entry 8-way | JST **S8B-PH-SM4-TB(LF)(SN)** | **12** | **$0.2885 @100 / $0.3344 @30** [v] | [LCSC C265121](https://www.lcsc.com/product-detail/C265121.html) — 19,469 in stock 2026-09-21 | The lever/pedal SENSOR boards' J1 (11) **and motor_ctrl J2** (1, 2026-09-22: the controller moved to the MIDDLE of bus B, so it is a pass-through node and takes the same 8-way trunk part, in on ways 1-4 and out on 5-8, as every other bus-B node) (user, 2026-09-21): the lever bus runs at **5 V**, so it takes a different family from the 24 V XH motor tees — **no harness can put 24 V on a lever board**. SMT (single-sided panel, no THT step), on the magnet face, on end: 19.9 long, 5.5 tall, 6.0 deep + 2.6 tabs (JST ePH p.4, side-entry). Stock was the other reason: S8B-XH-A showed 105. Harness side = PHR-8 housing + SPH-002T-P0.5S contacts (stock not yet checked) and a PH crimp tool; **brenner's leg wiring uses PH too** (user). See `docs/lever-sensor-respin.md`. |
| **XH header**, SMT side-entry 4-way | JST **S4B-XH-A(LF)(SN)** | **10** | **$0.0896 / $0.0699 @50** [v] | [LCSC C157925](https://lcsc.com/search?q=S4B-XH-A) | The CAN tee's drop to its own motor, one per tee. Also absent from this table until 2026-09-19. Same XHP-4 plug and crimp as the rest of the harness. 86,305 in stock 2026-09-19 — no sourcing concern |
| **Power connector** (PSU trunk only) | XT30 pair — DFRobot **FIT0586** | 4 pr | **$1.90** [v] | [DigiKey](https://www.digikey.com/en/products/detail/dfrobot/FIT0586/9559255) | 15 A/30 A pk, gold; pigtails bench-soldered ONCE, field = plug/unplug only |
| ~~**CAN terminator R**~~ | ~~Yageo **CFR-25JB-52-120R** (120 Ω ¼ W)~~ | **0** | — | — | **OBSOLETE 2026-09-19 — there is no site left for a discrete terminator.** Every termination in the instrument is now an on-board SMT 120R: motor_ctrl's, for bus A, wired in permanently; can_tee ×1 per tee and lever_sensor ×1 per board behind a solder jumper. This row said "motor controller + last motor", and the "last motor" end IS the last tee — one tee sits at every motor, each with its own jumpered 120R. The row already half-knew, noting "bus-B termination lives ON the tees". Qty was 10, which matched neither the two bus ends it describes nor anything else. **23 SMT 120R are FITTED per instrument** (10 tees + 11 sensor boards + 2 on the motor controller) and exactly **2 are closed** — one at each end of each bus — which is what the jumpers are for; ISO 11898 wants 120 Ω at each END of the trunk and nowhere else. They are part of each board's assembly BOM, not a separately ordered line |
| **Tee PCB** | custom 49.5 × 16 L (40 × 16 layout + a bare 9.5 × 8.7 mounting ear, M4 through-hole): ONE 8-way side-entry XH (trunk in 1-4, out 5-8) + ONE 4-way drop + 120 Ω behind a 1-position slide switch (`DSHP01TSGER`, C3293141) | **10** | ~$2 assembled (est.) | JLCPCB | panelized with the sensor boards; slide the switch to ON on the LAST tee only = bus A's far-end termination (no solder). Qty 12 → 11: tees 11/12 are deleted (the lever board passes the trunk through its own 8-way; tee 12 went with the wired leg column, which is now an off-the-shelf TRRS M→F extension cable with molded ends and no junction anywhere along it. The TRRS adapter PCB that briefly carried that jack is deleted too — the cable crosses the joint with zero connections on the leg, so the board had nothing left to do) |
| **Leg carrier PCB** | custom: LCSC SMT jack + B4B-XH-A header | 2 | ~$2 assembled (est.) | JLCPCB | rides the same panel; sits in the shaft pocket — auto-mate jack's terminals land on XH, fully factory-soldered |
| ~~**FD-capable transceiver**~~ | ~~Microchip **MCP2562FD-E/SN**~~ | — | **DROPPED** | — | Superseded by **SN65HVD230DR** (`C12084`, $0.6185 @10, 32,557 stock) on the sensor boards — see Control sensors. Two corrections this row carried: LCSC is **$1.85 @10**, not the “~$0.50” claimed here, and it needs **4.5–5.5 V**, so it dragged a second regulator onto the most area-constrained board in the project. FD is moot now that the sensor MCU is classic-only — bus B could have been FD (the motors are on bus A), but the payload does not want it |

≈ **$40 of connectors + ~$25 of tee/carrier boards** (board figures are
estimates until the JLCPCB quote; tools live in the Tools section — per
project policy they're shop infrastructure, not a line item weighed against
any one approach). Fallback if crimping
frustrates: JST pre-crimped leads [ASXHSXH22K203](https://www.digikey.com/en/products/detail/jst-sales-america-inc/ASXHSXH22K203/9961918)
(**$0.78 / $0.5878 @50** [v], 200 mm socket-socket — cut in half = 2 pigtails).
Molded TRRS cables were dropped: DigiKey's are special-order/obsolete
(SparkFun 14163/14164) and the lean topology needs none — if an external
TRRS hop ever appears, any consumer 4-pole aux cable serves. Audio stays as
already pinned above (Neutrik NMJ4HCD2 + shielded pair, single-point ground).
~~The SERVO42D's own I/O is XH2.54 native~~ **Corrected 2026-10-01:** the SERVO42D's I/O is
2.54 mm **screw terminals** (Makerbase schematic V1.0_003; the user's video of the unit). The
motor end of each pigtail is four ferruled wires; the XH standard starts at the tee.

## Optical pickup PCB (per-string sensing + on-board audio→MIDI)

> **The parts on this board: [`docs/order-parts.md`](docs/order-parts.md), section
> `optical`.** Detector `PD15-22B/TR8`, emitter `LTE-C9901`, converters
> `TLV320ADC3140`, TIA op-amps `TLV9062`, PHY `USB3300` with a 24 MHz oscillator, MCU
> `STM32H743IIT6`, buck `LMR33630BRNXR`. Anything below that names a different part for
> one of those jobs is the record of an earlier choice.

> **⚠ 2026-09-21 — detector and converter changed; parts of this section predate it.**
> * **Photodiode → Everlight `PD15-22B/TR8`** (C161211, $0.067, 11,271 in stock). The
>   VEMD4110X01 had 95 in stock against 20 per board and no 0805 substitute; the full
>   catalogue (802 photodiodes) has filtered parts in bigger packages, and the triplet was
>   redesigned around this one: detectors at ±2.375 across the string, apertures 7.6 wide.
>   Peak sensitivity 940 nm (the emitter's), ~3× the photocurrent.
> * **Converters → 5× TI `TLV320ADC3140`** ($18.23/board). The H743's own ADCs were the
>   noise floor (77 dB single-ended). The converters run at 192 kHz, the emitters are
>   square-waved at 48 kHz locked to the frame, and firmware demodulates (lock-in) — the
>   old LEDs-on/LEDs-off sampling needs a sampler, which a delta-sigma part is not.
> * **TIA: 1M / 1 pF** (was 4M7 / 2.2 pF), to pass the carrier. The photodiode is now wired
>   cathode-to-summing-node: the old anode-in wiring drove the output DOWN from a 0.33 V MID.
> * **Noise floor = the light itself** (photon shot noise, ~67 dB on the thinnest string
>   with pulsed emitters, no ambient). Ambient IR (sun, halogen) adds shot noise the filter
>   cannot remove; LED/fluorescent stage light is rejected. Net board cost ~+$8.40.
> Older text below that quotes 67/75 dB, 4M7, 96 kHz pulsing, or the VEMD part is history.

> ### ⚠ 2026-09-17 — every part audited against its manufacturer's datasheet
>
> Prompted by the user: verify the parts before routing the board again. All 155
> checked, pinout by pinout. **Seven faults, none of which DRC can see** — DRC
> checks copper against the netlist, and these were in the netlist.
>
> | What was wrong | Why it matters |
> |---|---|
> | USB3343 PHY pinout was invented — D+/D− on 16/15 (really 13/14), crystal on 10/11 (really 21/20), RBIAS on 17 (really 19) | The board could not have worked. The file had said "check against Microchip's datasheet"; nobody had |
> | Y2 was 24 MHz | The USB3343 takes **26 MHz**. Neither 24 nor the MPN table's 25 would enumerate |
> | Crystals specified by frequency only | The PHY needs **CL 20 pF, ESR ≤ 30 Ω** (T4.13). The obvious 26 MHz 3225 part is CL 10 pF / 50 Ω and fails both — a mismatched load pulls frequency off the ±500 ppm budget, and 50 Ω against a 30 Ω limit may not start |
> | TIA op-amps ran on **+5 V** and drive ADC pins | ST rates those pins at **4.0 V absolute maximum** (DS12110 T21). A saturated channel put ~4.95 V on them. Moved to +3V3A — which costs nothing, since the ADC measures against VREF+ = 3V3A and could never read above it |
> | U9's BYP pin floating | Its datasheet: **300 µVrms** without the cap, **40 µVrms** with. 40 µV is why the part was chosen. New C127 |
> | Ferrite bead had the **ten pulsed emitters on its quiet side** | The bead was keeping the buck's ripple out of a node the board's own worst aggressor already sat on. Emitters + digital LDO now on the buck side |
> | U11 ordered as the SC70 part on a SOT-23 footprint | TI gives the two packages **different pinouts** — as ordered, the mid-rail buffer drove its own input |
> | 50 passives had placeholder values (`Rf`, `Cf C0G`, `ballast`) | They were counted as sourced generics and would have reached a quote as blank lines. `fab.py` now refuses them |
>
> **What the audit cost in routing:** the sensing strip now carries two power
> rails (+3V3A to the quads, V5_PRE to the ballasts) where it carried one, which
> is the direct price of separating the pulsed emitters from the analog supply.
> Unconnected went 5 → 10 on an otherwise identical board. Zero DRC violations
> either way, beyond the 20 declared sensing-cell courtyard overlaps.
>
> ### ⚠ Second pass, same day — the parts that were still OPEN, and four more faults
>
> The first pass checked what was *written*. This one closed what was *missing*,
> and found that the two files naming each part had drifted apart.
>
> | What was wrong | Why it matters |
> |---|---|
> | **D8 and D9 were BOM'd as an output-panel relay flyback and an output clamp, both OPEN** | On this board D8 and D9 are two of the **ten IR emitters**. The CAD's sourcing table matches by longest ref prefix, and the panel's `D8`/`D9` entries beat this board's bare `D` rule. The exact-ref table exists *because* designators collide within a board; this was the same failure across boards, and nothing could see it — each file was internally consistent |
> | **Y1 and Y2 both still mapped to a 25 MHz part** | A 25 MHz crystal on the pin that has to clock the PHY at 26. The first pass fixed the netlist and left the CAD table saying "confirm vs USB3343". One `Y` rule cannot cover two different crystals |
> | L1 was **18 µH** with the part OPEN | The note computed 15.8 µH from TI's eq. 9 and rounded *up*, which is backwards — `KIND` is a choice in TI's own 20–60 % band. And the binding spec is not the load: SLVSE22B 9.2.2.4 sizes the inductor against the **IC's current limit** (0.8/1.1/**1.4** A), and no 4 × 4 part at 22 µH gets past 1.05 A. At 15 µH the same package gives Isat 1.35 A, DCR 0.299 Ω instead of 0.455, Irms 0.77 instead of 0.62. **SWPA4020S150MT**, C36407, 8,816 in stock |
> | FB1 was OPEN, and the obvious part is a trap | **"600" in a Murata or Sunlord bead part number means 60 Ω** — two digits and a decade multiplier. `BLM18PG600SN1D`, the top hit with 136,668 in stock, is a *tenth* of the specified filtering in the right package, on the right footprint, and no DRC or netlist check could ever catch it. `GZ1608D601TF` (C1002) is the 600 Ω part |
> | U10's **body** was the SOT-563's 1.6 × 1.6 | The part ordered is USBLC6-2SC6 in **SOT-23-6**. The courtyard had been corrected and the body left behind — and body is what the CAD's pairwise clearance assert measures, so a neighbour could sit closer than the real package allows |
> | J2 was OPEN pending "confirm B = 15.0" | Confirmed against JST's own drawing: S4B-XH-SM4-TB is A = 7.5, **B = 15.0**. C161861 (the `(LF)(SN)` form, 20,992 — the bare listing is zero, the same trap J1 hit on the lever board) |
> | **BOM.md was missing thirteen parts** | The whole local supply (U13, L1, C160–C163, R40/R41), the PHY's R37/R39, the LED gate pull-down R38, and the H7's two core-regulator caps — everything added when the board took the 24 V trunk on 2026-09-14. J2 still read "5 V, XH-SM-2" |
>
> **The drift is now checked mechanically.** `elec/mpn_check.py` compares the CAD's
> sourcing table against the netlist and runs on every netlist generation. It is
> what found D8/D9 and the crystals.
>
> **And the photodiode has no substitute.** LCSC's catalogue was swept for a
> daylight-filtered PIN photodiode in an 0805 land: `VEMD4110X01` is the only one.
> `TEMD7000X01` (3,904 in stock) is 350–1120 nm, `VEMD1060X01` (1,914) is
> 350–1070, `VEMD8081` (5,501) is 4.8 × 2.5 mm, visible-*enhanced* and 33 pF. The
> filter is load-bearing: at Rf = 4M7 the TIA saturates at 617 nA and open room
> light on an unfiltered diode is already that order. 95 in stock is four boards,
> against 200 for the ten-instrument basis — a purchasing problem with no design
> answer.
>
> **One number the audit corrected rather than found:** the photodiodes run at
> **zero bias**, and Vishay characterises the part at V\_R = 5 V, so both figures
> quoted in the design were the wrong line of the table — responsivity is
> **Ik 2.2 µA/(mW/cm²)**, not Ira 2.4, and diode capacitance is **7 pF**, not 2.5.
> The 3× capacitance error was still safe (Cf is ten times the stability minimum),
> but it is the number anyone re-deriving Rf needs.


One custom board lying **under the strings, firing up**, on a carrier that is part
of the bridge endplate and **rides on top of the deck**, that reads all ten
strings optically.

It spent a while hanging face-DOWN from the endplate's tie bar. Optically that is
better — a down-firing sensor is shaded by its own mount, free, and sheds debris
instead of collecting it — but it put structure 3 mm over the strings starting
14.5 mm out from the termination, straight through the **palm blocking** zone.
Blocking is core right-hand technique, so that mount lost.

Riding on the deck rather than taking a deck slot is what keeps the magnetic
pickup whole: there is a **14.0 mm clear band** between the pickup cavity's +X
edge (−30.62) and the deck's end at the endplate (−16.60), and the entire sensing
section lives in it. The carrier is monolithic with the endplate so the sensor
standoff — the signal-critical dimension — references the bridge directly rather
than through the deck panel's tolerance stack. It replaces nothing in the signal path — the
magnetic pickup is untouched — and does two jobs: per-string **pitch** (tuning
calibration + audio→MIDI) and per-string **audio**.

**The canonical part list is `src/optical_pickup.py::PARTS`.** The table below is
generated from it, so the 3D model, the clearance assertions and this BOM cannot
disagree about what is on the board. Every package is a real JEDEC/IPC outline at
max dimensions; placement in the model is representative (block order and X
columns are deliberate, exact XY of an 0402 is layout's business).

**Architecture.** Each string gets an IR emitter flanked by two photodiodes in Y.
SUM tracks vertical motion (the audio signal); DIFF tracks lateral. Both are
needed: with symmetric detectors SUM is an *even* function of lateral
displacement, so as the vibration plane precesses toward horizontal — which it
does over this instrument's long sustain — SUM's f₀ collapses and **2f₀ takes
over**, handing the detector a confident octave-up error rather than a dropout.
Each photodiode therefore gets its own transimpedance amp and its own ADC input
(20 of each); SUM/DIFF are one add and one subtract in firmware, cheaper in parts
than analog sum *and* difference stages.

Two rates share one ADC stream: **audio** = SUM at 48 kHz × 10 ch = 960 kB/s
straight out over USB; **pitch** = decimated to ~6–8 kHz, detected on-chip, MIDI
out over the same cable. The expensive stage is the only one not running at 48 k,
which is why both fit in ~15 % of the MCU.

**Why an external USB PHY.** 960 kB/s needs USB high-speed (isochronous
full-speed tops out near 1023 kB/s theoretical, with MIDI still to send). Survey
at time of writing:

| Candidate | HS PHY | Fits a 20 mm board | Verdict |
|---|---|---|---|
| STM32H7 (LQFP176, was LQFP144) | external ULPI | yes | **chosen** — M7, 3× 16-bit ADC |
| STM32F723/733 | internal | no — ≥144 pins, 22×22 over leads | too wide |
| AT32F435/437 | none (full-speed only) | yes | no HS |
| GD32F470 | external ULPI | yes | M4 240 MHz, 12-bit ADC |
| CH32V307 | internal | yes | 144 MHz, 16 ADC ch — can't run the detector |

The only part with an integrated HS PHY that fits cannot run the detector, so the
extra PHY chip is unavoidable. LQFP100 is likewise a floor, not a preference: 20
ADC inputs plus a 12-signal ULPI bus will not fit a 64-pin part.

| Qty | Ref | Part / role | Package | Envelope (mm) |
|-----|-----|-------------|---------|---------------|
| 1 | U6 | MCU — **STM32H743IIT6**, 5 SAI TDM lanes from the audio ADCs, USB OTG_HS via ULPI (its own ADCs unused since 2026-09-21) | LQFP176 | 26.00 × 26.00 × 1.60 |
| 5 | U14–U18 | **audio ADC — TI `TLV320ADC3140IRTWT`** (C1852021), 4 ch each, one per quad, 192 kHz, differential AC-coupled against MID. Replaced the H743's own ADCs 2026-09-21: they were the noise floor (77 dB single-ended), and a delta-sigma converter also filters the op-amps' out-of-band noise and samples all 20 channels on one edge | WQFN-24 (RTW) | 4.00 × 4.00 × 0.80 |
| 25 | Cs11–Cs58 | ADC supply / reference bypass — per converter 1 µF (AVDD), 10 µF (AREG, DREG, IOVDD), 1 µF (VREF): TI SBAS993B Fig. 165 less its 100 nF partners, which 0402 bulk parts make redundant | 0402 | 1.00 × 0.50 × 0.55 |
| 40 | Ci11–Cm54 | ADC input coupling — **10 nF C0G**: INxP from each TIA, INxM to GND (single-ended AC-coupled, SBAS993B Fig. 31) | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | R50, R51 | I2C2 pull-ups 4k7 ×2 (all five converters share one bus and one address, written together; SHDNZ is tied high at each part and firmware issues the software reset) | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | J1 | USB-C receptacle — 10 ch audio + MIDI + DFU | USB-C | 8.94 × 7.35 × 3.16 |
| 1 | J2 | **24 V in** from the instrument trunk — side entry, −X edge, 2 cavities empty ⚠ **no source yet, see below** | XH-SM-4 | 6.10 × 15.00 × 7.00 |
| 5 | U1–U5 | quad op-amp — 4× transimpedance amp | SOIC-14 | 6.00 × 8.65 × 1.75 |
| 1 | U7 | USB 2.0 high-speed ULPI PHY | QFN-32 | 5.00 × 5.00 × 0.90 |
| 1 | U8 | LDO — 3V3 digital, **AP2114H-3.3, tab = VOUT not GND** (0.51 W) | **SOT-223** | 6.50 × 3.50 × 1.80 |
| 1 | U9 | LDO — 3V3 analog (low noise, **needs C127 on BYP**) | SOT-23-5 | 2.90 × 2.80 × 1.45 |
| 1 | C127 | analog LDO noise bypass — 1 µF, **the reason U9 is this part** | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | U11 | single op-amp — TIA mid-rail reference buffer | SOT-23-5 | 2.90 × 2.80 × 1.45 |
| 1 | U13 | **LMR33630BRNXR** (C2071384) 24→5 V synchronous buck, 1.4 MHz, 3 A (was the 600 mA TPS560430, 105 % used worst case once the five converters landed; user 2026-09-22). 1.4 MHz for heat: about 98 °C worst case where the 2.1 MHz variant read 124 °C. No forced-PWM variant is stocked; with 4.7 µH it stays in continuous conduction above 0.30 A | RNX-12 | 2.00 × 3.00 × 1.00 |
| 1 | L1 | buck inductor — **WPN4020H4R7MT** (C98363), 4.7 µH shielded, **Isat 4.0 A** (at or over the converter's typical current limit) | 4040 | 4.00 × 4.00 × 2.00 |
| 1 | C160 | 24 V input bulk — 10 µF/50 V, **1206 for the DC-bias derating** | 1206 | 3.20 × 1.60 × 1.45 |
| 1 | C162 | buck 5 V output bulk — 22 µF/16 V | 0805 | 2.00 × 1.25 × 1.45 |
| 1 | C164 | **U8 input bulk** — 10 µF/16 V; V5_PRE had no local capacitor at all | 0805 | 2.00 × 1.25 × 1.45 |
| 2 | C161, C163 | 24 V HF bypass; buck bootstrap CB→SW, 100 nF | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | R40–R41 | buck feedback divider — 40k2/10k 1%, 5.02 V | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | C112–C113 | H7 core regulator caps (VCAP1/2), 2.2 µF — **required, not optional** | 0805 | 2.00 × 1.25 × 1.45 |
| 1 | R37 | PHY RBIAS — **12k 1%**, sets the USB transmitter's drive current | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R39 | PHY VBUS series — 10k | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R38 | LED gate pull-down — 100k, emitters OFF while the MCU is in reset | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | Y1 | 25 MHz crystal — MCU HSE, **CL 20 pF, ESR ≤ 30 Ω** | 3225 | 3.20 × 2.50 × 0.90 |
| 1 | Y2 | **24 MHz oscillator** — PHY reference, 3.3 V CMOS into XI | OSC3225 | 3.20 × 2.50 × 1.20 |
| 1 | Q1 | N-ch MOSFET — LED row driver | SOT-23 | 2.90 × 2.40 × 1.30 |
| 1 | U10 | USB data-line ESD array — USBLC6-2SC6 | **SOT-23-6** | 2.90 × 2.80 × 1.45 |
| 10 | D1–D10 | IR emitter, 940 nm — `LTE-C9901` (Lite-On), **65° view angle FULL (2θ½)**, Ie **5 min / 8 typ / 10 max** mW/sr @20 mA, VF 1.4, 60 mA DC, MSL 3 | 0603 (opto) | 1.60 × 0.80 × 0.98 |

> ⚠ **Two corrections to this row, both from Everlight's own datasheet, 2026-09-17.**
> It said "narrow beam"; the part is **120°**, which the MPN table has said all
> along ("120 deg CONFIRMED") — the two lines have contradicted each other.
> And its radiant intensity is **0.2 mW/sr minimum against 0.8 typical**, a
> guaranteed fourfold spread on the part the whole optical budget rests on. The
> budget in `elec/optical.py` is computed on the typical, so a worst-case emitter
> gives a quarter of the signal — still **~55 dB** SNR rather than ~67, but it is what
> the per-string Rf tuning has to absorb. (These read 63 and 75 until 2026-09-18, when
> the noise budget in `elec/optical.py` was re-derived: the op-amp's own voltage noise
> is not rolled off by the Rf·Cf pole, so the floor is ~120 µVrms rather than 48.)
>
> ⚠ **Soldering:** `Tsol` 260 °C, ≤5 s. JLCPCB's Economic PCBA reflow is fixed at
> **255 ± 5 °C, not adjustable** — so this part, like the VEMD4110X01 photodiode,
> sits at the top of its rating with no margin. Two of the twenty most
> irreplaceable parts on the board are in that position.
| 20 | PD1A–PD10B | PIN photodiode — **Everlight PD15-22B/TR8** (C161211), black-epoxy daylight filter (730–1100 nm, **peak 940 nm**), ±2.375 across the string. Was the VEMD4110X01 (95 in stock) until 2026-09-21 | 3.3 × 2.8 (4 pads) | 3.30 × 2.80 × 1.10 |
| 5 | R1–R5 | LED current-set — **180R** (21 mA) nominal, plain strings | 0402 | 1.00 × 0.50 × 0.55 |
| 5 | R6–R10 | LED current-set — **180R** (21 mA) nominal, wound strings | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | FB1 | ferrite bead — analog rail isolation | 0603 | 1.60 × 0.80 × 0.95 |
| 4 | C130–C133 | bulk caps — VBUS / 3V3D / 3V3A / reference | 0805 | 2.00 × 1.25 × 1.45 |
| 20 | Rf11–Rf54 | TIA feedback resistor — **1M** nominal (was 4M7), tuned per string — the TIA must now pass the 48 kHz emitter carrier | 0402 | 1.00 × 0.50 × 0.55 |
| 4 | C140–C143 | power-input decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 20 | Cf11–Cf54 | TIA feedback cap — **1 pF** C0G, ~160 kHz pole (was 2.2 pF / 15.4 kHz) | 0402 | 1.00 × 0.50 × 0.55 |
| 12 | C100–C111 | MCU decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 10 | Cd11–Cd52 | op-amp decoupling | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | C123, C124 | crystal load caps (Y1) | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | C125 | 24 MHz oscillator supply bypass, 100 nF | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | C120, C122 | PHY 1.8 V regulator output caps, 4.7 µF (one per rail) | 0805 | 2.00 × 1.25 × 1.45 |
| 7 | C119, C121, C136–C139, C145 | PHY supply bypass, 100 nF at each supply pin | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | R34–R35 | mid-rail divider | 0402 | 1.00 × 0.50 × 0.55 |
| 2 | R32–R33 | USB-C CC pull-downs, 5k1 | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R30 | BOOT0 pull-down | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R31 | NRST pull-up | 0402 | 1.00 × 0.50 × 0.55 |
| 1 | R36 | LED driver gate resistor | 0402 | 1.00 × 0.50 × 0.55 |
| 5 | TP1–TP5 | **SWD pads** — SWDIO, SWCLK, **NRST**, GND, +3V3D target sense. Bare copper: no part, no paste, excluded from the BOM and the CPL | 1.5 mm pad | 1.50 × 1.50 |

> ⚠ **These were a BOM row and nothing else until 2026-09-17.** `SWDIO` and `SWCLK`
> reached the MCU and stopped — single-node nets, which layout drops as unplaceable
> and DRC cannot complain about. **And there was no second way in.** A blank H743
> cannot enumerate over this board's USB (the ULPI PHY needs firmware to start, and
> the ROM bootloader's DFU is on OTG_FS `PA11`/`PA12`, which this board does not
> wire); AN2606's other bootloader interfaces are not brought out either. An
> assembled board would have been a **brick** — nothing about it repairable in
> firmware, because no firmware could be put on it.
>
> `NRST` is on the list for a reason that looks optional and is not: `PA13`/`PA14`
> are ordinary GPIO after reset, so firmware that reconfigures them takes SWD away,
> and **connect-under-reset is the only way back**. `BOOT0` is deliberately *not*
> brought out — it only helps if a ROM bootloader interface exists, and none does.

### Was magnetic ruled out too early? — feasibility check, 2026-08-02

The question asked: *can JLCPCB assemble magnetic coils at specific locations, so
a per-string magnetic board is orderable the way this optical one is?*

**The fabrication answer is better than hoped — and it is not about a part.**

**You do not want an assembled coil, you want an etched one.** Planar spiral
coils are **copper on the board itself**: free, positioned to layout tolerance
(±0.05 mm, far better than a placed part's ±0.2 mm), and perfectly repeatable
between boards. This is established prior art in exactly this application —
the patent literature describes PCB-coil pickups directly (*"manufactured with
high precision and highly reproducible results"*), and Cycfi's hexaphonic work
uses the approach commercially. Positioning, which is the thing the question was
worried about, is the part magnetic does **better** than optical.

An assembled inductor would be strictly worse: JLCPCB's SMD inductors are wound
on ferrite for **power conversion**, and many are **magnetically shielded** —
built to reject external flux, which is precisely backwards for a pickup.

So the question moves from "can it be built" to "would it work". Here the news
is mixed, and worth having on record.

**Turns budget — 44–50 dB down, which is survivable.** Each string owns
**9.40 mm** of pitch at the sensing row. A square spiral filling ~8.5 mm of that:

| Process | Turns/layer | Layers | N | N·A |
|---|--:|--:|--:|--:|
| 0.127/0.127 (standard) | 8 | 4 | 32 | 1,290 mm² |
| 0.09/0.09 (fine) | 11 | 4 | 44 | 1,773 mm² |
| 0.09/0.09 | 11 | 6 | 66 | 2,660 mm² |
| *reference single-coil* | — | — | *6,000* | *432,000 mm²* |

That is **162× down at best (44 dB), 335× at standard process (50 dB)** — so
roughly **0.5–1 mV** against a normal pickup's ~150 mV. That is moving-coil
cartridge territory: entirely amplifiable. And the coil is only ~6 Ω, so its
Johnson noise is ~61 nV over 20 kHz — an **~84 dB** thermal SNR. **Thermal noise
is not the problem.** Six layers instead of four is the obvious lever, at real
but modest cost.

**Interference is the problem, and it is the same objection as before.** The
coil is a 17.7 cm² effective loop antenna sitting above **ten SERVO42D steppers
with PWM current control, directly under the deck**. A rough estimate — 0.1 µT
of switching ripple over a microsecond — gives ~180 µV induced, i.e. only
**10–15 dB below the string signal**. That estimate is soft by an order of
magnitude in either direction, which is exactly why it cannot be settled on
paper. Optical coupling to that source is **zero**, not small.

The standard mitigation is real and is visible in the prior art: hex pickups
carry a **dedicated noise coil** with no string over it, subtracted from every
channel (the 13-coil array in the patent is 6 strings × 2 + 1 noise reference).
That works well against uniform fields and less well against ten independent
near-field sources at varying distances.

**Two things that do *not* favour magnetic, contrary to first instinct:**

1. **It would not halve the channel count.** A single coil over a pole has the
   *same* even-function problem in lateral motion that drove SUM/DIFF here — so
   hex pickups use **two coils per string** for exactly our reason. 10 × 2 + 1
   noise = **21 channels against optical's 20**. No MCU saving, so the LQFP144
   stock problem is not solved by switching.
2. **It does not fix the thin-string deficit.** Output rises with frequency,
   which helps the high strings, but it also scales with ferromagnetic material,
   which hurts them — the two partly cancel. Real pickups still need staggered
   pole heights. This is not the escape from the .014 problem it looks like.

**And one thing that is a genuine strike against it on *this* instrument:**
magnets **pull on the strings**. Damping and pitch-pulling ("Stratitis") are
tolerated on a guitar; on an instrument built around motorised tuning to a few
cents and long sustain, adding a bridge-end magnetic load works directly against
two of its headline goals. Optical exerts **no force on the string at all** —
and there is already a Lace Alumitone in the instrument for the audio path,
which ten new magnets at the bridge would sit right beside.

**Verdict: optical stays, but the case is narrower than "no magnetic crosstalk".**
Magnetic is manufacturable, cheaper in parts (coils free, ~$4 of magnets against
$11.88 of emitters and detectors), and better positioned. It loses on motor
interference, string loading, and — decisively for the effort involved — it
would not simplify the channel count or the MCU.

**The cheap experiment that would settle it**, if the optical prototype
disappoints: etch a two-layer test coil, put it at the sensing station, and
measure the induced voltage with the motors slewing. That is a $2 board and an
afternoon, and it converts the one soft number above into a measurement. Worth
doing *before* any magnetic redesign, not after.

### HISTORY — Orderability, 2026-08-01 — every part is now a real LCSC line

Asked directly: is every part in LCSC's catalogue, in stock, in quantities that
support a preassembled build? **Every part now has a real MPN; two lines are
short on stock; one schematic decision is outstanding.**

The starting position was worse than a stock problem. **Only three of the 35
distinct lines carried a manufacturer part number at all** — the other 32 were a
*functional description plus a package envelope* ("quad op-amp, SOIC-14"), which
is exactly what the geometry model needs and is not something you can put on a
JLCPCB BOM line. And all three that did have numbers failed:

| Line | Was | Now |
|---|---|---|
| U6, MCU | `STM32H743ZIT6` 0 in stock (2026-09-17) → **`STM32H743IIT6`**, 548 | resolved by package swap |
| PD ×20 | `VEMD4110X02`, **not in catalogue** | **`VEMD4110X01`** — same filter, in catalogue ✓ ⚠ 95 in stock 2026-09-17 (need 200); **swept, and it is the only filtered 0805 PIN at LCSC** |
| D ×10 | `VSMB1940X01`, **not in catalogue**, ±60° | **`IR17-21C/TR8`** — in catalogue ✓ but ~120° |

**Two items closed that had been open for a while:** the **ULPI PHY** is
Microchip `USB3343-CP`, in LCSC stock at **$1.78** (C633347; `-TR` reel C112967
at $2.07), QFN-24, matching the modelled envelope — the part the survey table
assumed existed. (Since 2026-10-05 the PHY is `USB3300-EZK`, C108383, QFN-32:
see the optical board's parts table.) And the **quad op-amp** is `TLV9064IDR`, below.

### HISTORY — ⚠ Search snippets report the VOLUME-FLOOR price — every one of them was wrong

Re-checked 2026-08-04 by fetching each LCSC product page directly, after another agent
flagged that they could not read stock and would rather report unresolved than quote an
unread number. That caution was right, and checking proved it: **every price taken from a
web-search snippet was wrong, systematically in the same direction.**

LCSC's pages advertise **"from $X"**, which is the *highest volume break* — the 1,000+ or
6,000+ price. Search snippets quote that figure. It is not the price at the ten or fifty
pieces this project buys. The gap is large:

| Part | Recorded (snippet) | Actual at our qty | |
|---|--:|--:|--|
| `USB3343-CP` PHY | $1.78 | **$2.6398** @10 | +48 %, **and OUT OF STOCK** |
| `TLV9064IDR` ×5 | $0.2161 | **$0.3297** @30 | +53 % |
| `PCM1808PWR` | $0.3419 | **$0.642** @10 | +88 % |
| `MT6701QT-STD` ×11 | $1.1139 | **$1.6815** @10 | +51 % |
| `X322525MSB4SI` ×2 | $0.0334 | **$0.0959** @5 | +187 % |
| `USBLC6-2SC6` | $0.0983 | **$0.1829** @5 | +86 % |
| `AO3400A` | $0.0487 | **$0.0849** @5 | +74 % |
| `SPX3819` | $0.30 | **$0.1903** @10 | −37 % (one of two that went the other way) |

**Two part numbers were outright wrong**, which no amount of price-checking would have
caught: `C693480` is a **P6KE39CA TVS diode**, not the `TLV9061IDCKR` op-amp it was recorded
as (correct code: **`C398357`**); and `C1017`, recorded for the ferrite bead, **404s** — that
part number does not exist. FB1 is now an explicit OPEN.

Board parts cost **$26.96 → $29.07**, per instrument **$42.58 → $44.69**.

**Method that works**, for anyone repeating this:

* **Fetch `lcsc.com/product-detail/C<number>.html`** — the short canonical form. It returns
  the full quantity-break table *and* exact stock. It is not client-side rendered.
* **Never fetch `lcsc.com/search?q=…`** — that one *is* client-side and returns only page
  furniture, which is what makes LCSC look unfetchable.
* **Use web search only to find the C-number**, never to read a price off the snippet.
* **Take the break matching your build quantity**, not the headline. Ten instruments means
  10 of a per-board part and 100–200 of a per-string part — different breaks.
* ⚠ **LCSC stock ≠ JLCPCB assembly stock.** Everything here is LCSC's figure. For a PCBA
  order JLC's own inventory governs, and that is on `jlcpcb.com/partdetail/…`, which *is*
  client-side. Treat these as a strong proxy and confirm at quote time.

### HISTORY — Part selection — done 2026-08-01, and now enforced by the model

**Every one of the 141 placed parts now maps to an orderable line.** The mapping
lives in `src/optical_pickup.py::_MPN_RULES`, and `_assert_every_part_orderable()`
runs at import: **add a part without a sourcing decision and the build fails.**
The 141 parts collapse to **18 distinct order lines**, of which 5 are JLCPCB
Basic classes (no feeder charge):

*(The table of order lines that stood here was kept by hand and had drifted: it listed the emitter, the TIA op-amp and both crystals of earlier revisions beside the current parts. The lines are generated now: [`docs/order-parts.md`](docs/order-parts.md), section `optical`; prices are `elec/prices.json`.)*

**The op-amp is the happy surprise.** `TLV9064IDR` is a 4× CMOS RRIO part with
**10 MHz GBW and 500 fA input bias current** — the bias figure is what a nanoamp
TIA actually needs, and 500 fA against tens of nA is four orders of margin. It is
SOIC-14 (the package already modelled, chosen for its 6.00 mm across-leads in a
14 mm band), 10,148 in stock, and **$0.2161** — so all five cost **$1.08**
against the $4 assumed. Cheapest part of the front end and the one with the most
performance riding on it.

**Parts cost is computed, not estimated: `parts_cost()` = $26.66/board.** The
run of that figure — $29 assumed → $41.60 extrapolated → $36.95 on first
selection → **$26.66 resolved** — is worth reading as a caution about estimates
built from part *counts*: it was wrong by up to 56 % in both directions, and it
only settled once every line had a real part number behind it. BOM.md can no
longer drift from the model here.

### HISTORY — The three blockers, resolved 2026-08-01 — `open_lines()` is now empty

**1. Photodiode — the dilemma was a false alarm.** The choice looked like
"break the no-consignment rule, or give up the daylight filter". Neither is
needed: **`VEMD4110X01` carries the same filter.** Its LCSC page specifies a
*"silicon PIN photodiode with daylight blocking filter"*, 740–1040 nm, matched
to 830–950 nm emitters — the same 0.42 mm² area, same ±55°, same 0805
2.0 × 1.25 × 0.7 as the absent X02. It is a drop-in, and it is the part LCSC
stocks. The whole consignment-vs-filter argument in the previous revision was
built on the assumption that X01 was the unfiltered variant. It is not.

It is also **cheaper than recorded**: 10 boards need 200 pieces, which clears
the 100+ break at **$0.58** (vs $0.9334 @1). That takes the detector line from
$18.67 to **$11.60/board**.

⚠ **Stock is still 72 against 200 needed** — the one genuine constraint left on
this part. It must recover, or be pre-ordered ahead of the run.

**2. Emitter — chosen, and the budget's first lever is confirmed DEAD.**
`IR17-21C/TR8` (C131250), Everlight, 0805, 940 nm, **$0.0283** — against the
$0.35 the BOM assumed, so the emitter line drops from $3.50 to **$0.28/board**.

The important part is not the price. **Narrow-beam is not made in 0805.** Every
candidate checked is wide: Kingbright KP-2012F3C 120°, APT2012F3C 120°, and
Everlight's `IR19-21C` is **150° — and 0603**, wrong on both counts. So lever 1
of the signal budget (*"the largest and it is free"*, +9.5 dB at ±30°, +13.6 at
±20°) is **unavailable in this package**, not merely unchosen.

⚠ **Correction to the previous revision of this file, which proposed
collimating in the printed cover to recover the gain. That does not work, and
the reason is worth stating because the idea is intuitive and wrong.** An
aperture *discards* off-axis flux; it does not redirect it. The on-axis
intensity heading for the string is unchanged, so the returned signal is
unchanged — a tube costs light and gains none. The +9.5/+13.6 dB in the budget
comes from a **lensed** emitter, which redirects the *same total flux* into a
narrower cone and so genuinely raises on-axis intensity. Geometry cannot
substitute for optics here.

What cover apertures *do* buy is real but different: **crosstalk between
adjacent strings, and ambient rejection**. Both worth having, neither is signal.
The cover is therefore left as one slot per string. (A split three-aperture lid
was worked through and rejected on printability: with `PD_DY` = 1.6 and a 0.8 mm
minimum wall, the webs between emitter and detector apertures come out at
0.2–0.4 mm — under one bead.)

So the deficit moves to **levers 2 and 3**, per-string LED current and per-string
TIA gain, which are already ten and twenty independent parts. Both are more
valuable now than when they were ranked second and third. That also raises the
stakes on J2: drive current is the lever, and the 5 V rail is what feeds it.

**3. J2 — refitted and done.** `S2B-XH-SM4-TB` is not a JST part; the SMT
side-entry XH line **starts at 4-way**. Now `S4B-XH-SM4-TB` (C161861) — already
the sensor boards' connector, so **no new part number and no new feeder**, and
four ways suits a rail pulling >500 mA better than two would have (2× 5 V,
2× GND). Cost is **5.0 mm of board length**: 184.4 → **189.4 mm**, area 69.0 →
**70.8 cm²**, about $0.18/board of fab. The model carries the real JST envelope
(`XH-SM-4`, 6.10 × 15.00 × 7.00) and all clearance assertions pass.

### HISTORY — The digital rail — resolved, and NOT with the buck I proposed

The MCU draws 200–300 mA, so 5 V → 3.3 V burns **0.51 W**. In a SOT-23-5 at
~250 °C/W that is a >100 °C rise — past the package, not marginally. So U8 could
not stay an SPX3819. Correct.

**But "make it a buck", which the previous revision recommended, is the wrong
fix for this board.** A switching regulator at ~1 MHz sitting alongside **20
transimpedance amps reading tens of nanoamps** trades a thermal problem for a
noise problem on the axis this design is most sensitive to. The file already
worries about exactly this in another place — the LED driver's switching noise
being *synchronous with sampling* so ambient subtraction cannot remove it. Adding
a second switcher to fix a heat problem is solving the cheap problem with the
expensive one.

**The heat is the cheap problem: spend package area on it.** U8 is now
**`AMS1117-3.3` in SOT-223** (C6186, $0.1045) — a tab package at ~50 °C/W with a
copper pour, so 0.51 W is a **~25 °C rise**. The board stays switcher-free.
Headroom is fine: 1.7 V available against AMS1117's 1.3 V max dropout — though
that is the one number to watch if the 5 V rail sags over the cable and the XH
connector, and it is an argument for keeping J2's doubled pins.

U8 and U9 are now **different parts**, which costs one line: U9 stays the
low-noise `SPX3819` (40 µVrms) on the analog rail, where its **11.7 mA** load makes
SOT-23-5 fine (that figure was guessed at "~40 mA" until the budget below was
itemised; five TLV9064 quads are 538 µA *per amplifier*). The split is the point — the noisy cheap regulator feeds the MCU,
the quiet one feeds the front end. Cost: **+0.7 mm of board**, and parts actually
fall $0.20 because the AMS1117 is cheaper than a second SPX3819.

> **⚠ The 5 V rail was never added up** — itemised 2026-09-17 in
> `elec/optical.py`, every figure from the part's own datasheet. Typical load
> **324 mA against a 600 mA buck (54 %)**; 499 mA (83 %) with maximum-spec parts at
> 25 °C and the emitters on. ST's 85 °C characterisation maximum would put it at
> 679 mA, *over* the buck — but that is 400 mA of MCU with every peripheral on a
> 176-pin part enabled, which this firmware does not do. The real conclusion is
> that **enabling peripherals is a power decision on this board**, and that raising
> emitter drive to the IR17‑21C's 65 mA rating is dead: 650 mA of emitters alone
> exceeds the buck.
>
> ⚠ This paragraph's dropout warning is also stale: it predates the board taking
> **24 V** and generating 5 V locally. The 5 V rail no longer crosses a cable or a
> connector, so cable sag cannot eat U8's dropout margin. J2's doubled pins are
> still right, for the 24 V.

**Nothing is now outstanding on this board's schematic.**

**141 placed parts**, all on ONE side (single-sided, per project rule: one
stencil, one reflow, no back-side placement). The model tracks 35 distinct
(description, package) lines; the table above merges four bulk-cap variants and
the two CC pull-downs into single rows.

**Board**: 4-layer, 1.6 mm FR4, two sections. A **13.6 mm-wide sensing strip**
(X −30.4…−16.8) running the string field, carrying the row, the ten ballast
resistors and all five quad op-amps; then a **30 mm-wide tail** (X −46.8…−16.8,
Y −104.2…−56.1) for the digital block, which widens only past the pickup cavity's
−Y edge where the deck is solid again and nothing is overhead. The MCU is 16 mm
over its leads and simply does not fit the band — that is what forces the tail.
Single-sided, every part on the TOP face, so the whole underside bears on a solid
plinth: no ledges, no floor to fuse back.

### The thin-string signal budget — why the outline steps

Optical signal scales with the string's **diameter**: the string *is* the target,
and what comes back is set by how much of the beam it intercepts. Across this set
that is .014 against .070 = 5.1× = **14.0 dB**, and the thin strings sit up to
0.71 mm further from the sensor plane (which references the *thickest* string's
top), so call it **~16 dB**. That deficit lands on exactly the strings the player
uses most. Note the hard string for *latency* (low C, long analysis window) and
the hard string for *SNR* (string 2, .014) are opposite ends of the set.

Four levers, spent in order of cost:

1. ~~**Emitter beam angle — the largest and it is free.**~~ ⚠ **UNAVAILABLE — see
   the emitter note above.** The arithmetic still holds: at the 3 mm standoff a
   ±60° emitter throws a ~10.4 mm spot and a 0.356 mm string intercepts ~3 % of
   it; ±30° → 3.5 mm spot, ~10 %, **+9.5 dB**; ±20° → **+13.6 dB**. But **narrow
   beam is not made in 0805**, so none of it is purchasable. D1–D10 are
   `IR17-21C/TR8` at ~120°, i.e. the ±60° row of that table — the worst case the
   analysis was written against. **Levers 2 and 3 are therefore the first and
   second levers, not the second and third**, and are correspondingly more
   important than their position here suggests.
2. **Per-string LED current** (R1–R10, already ten independent parts). Roughly
   linear in signal. This is what forces J2 — see below. **Now lever 1.**
3. **Per-string TIA gain** (Rf, already twenty independent parts). Bounded by the
   op-amp's gain–bandwidth product, not by the resistor: thin strings want more
   gain *and* more bandwidth, and Rf × Cin trades one against the other.
4. **Distance from the termination** — the worst lever: signal is linear in
   distance, so gain is only 20·log10(d/d₀) dB. Equalising .014 would need 60 mm.

**The stepped row was dropped, and the 14 mm band is why.** The band holds ONE
sensor row plus the transimpedance amps — not two rows plus the amps. Keeping
every TIA within a few mm of its photodiode beat the step's +5.3 dB: the summing
node is the noise-critical point on a board reading tens of nanoamps, and the
alternative was a ~90 mm trace sharing a board with a 96 kHz LED driver whose
switching noise is **synchronous with sampling**, so ambient subtraction would not
cancel it. The single row sits at **15.5 mm** for all ten — further out than the
old wound row, so every string gains ~+1.9 dB and the thin ones give up 3.4 dB
relative to the stepped plan.

**The cover (printed part `optical_cover`).** Up-firing is what makes this
necessary: the detector looks at the sky, and ambient subtraction fixes flicker
and offset but **not saturation**. An up-firing sensor also collects the skin and
string shed a down-firing one sheds. The lid gives each string its own aperture
and closes the shallow-angle path with a −X wall (from +X the endplate already
does it). Be honest about the limit: at a 3 mm standoff a slot cannot collimate
much — geometric rejection is a few dB. Print it **dark**: it is the one surface
facing the detectors.

**The spectral filtering is NOT in the cover — it is inside the detector**, and
that is the better place for it. An earlier revision of this section named a
bonded IR-pass window as "the obvious next addition if the prototype says sun is
a problem". That is now largely done for free: the `VEMD4110X01` carries a
**daylight-blocking filter, 740–1040 nm**, and the 940 nm emitter sits inside
that window. See "optical filtering" below for what it does and does not cover.

**What the slits actually are.** They are the **optical apertures** — one per
string, 5.0 mm wide in Y and running −X from the triplet, each centred on its
string and serving that string's emitter plus both photodiodes. The lid is
otherwise solid, so without them the sensors see nothing: they are the hole the
light goes out and comes back through, not an optional feature. On a 9.40 mm
string pitch that leaves a **4.40 mm web** between neighbours.

**Their −X end is open, not a flat wall** — see "the aperture's printable end"
below for the two shapes that failed first.

**Why the triplet runs along Y (across the string) and not along X (down it).**
This is forced, and the reason is *not* humbucking — there is no magnetic
circuit here to hum-cancel. It is that **Y is the axis DIFF has to resolve**.

The two detectors flank the emitter so that SUM is an *even* function of lateral
displacement and DIFF is *odd*; DIFF is what tracks the string's Y motion, and
DIFF is the whole defence against the 2f₀ octave error when the vibration plane
precesses toward horizontal. Put the same three parts along **X** instead and
both detectors sit under the *same* point of the string's lateral motion —
they see the same signal, **DIFF collapses to nearly zero**, and the octave-error
defence goes with it. What little difference remained would be the small
amplitude change from sensing at two distances from the termination: common-mode,
not lateral information.

There is a second, weaker reason pointing the same way: the sensing band is only
14 mm in X and has to hold the row *and* the transimpedance amps. Three 2.0 mm
packages in a line would spend 6 mm of it.

Worth noting the one thing an X-wise row would actually do better: it would keep
both detectors on their own string's axis, so **neighbour crosstalk would drop**.
At ±1.6 mm the detectors sit 1.6 mm nearer the adjacent string (7.8 mm away
instead of 9.4). That is a real cost, and it is the right trade — crosstalk is a
few dB of pedestal, while losing DIFF means confidently reporting the wrong
octave.

The nearest thing here to humbucking is real but axis-independent: both
detectors see the **same ambient**, so it appears as common mode and DIFF
rejects it. That works whichever way the pair is oriented, so it is not what
sets the orientation.

They are **not** a filter and not a substitute for one — the two do different
jobs. The detector's filter is **spectral** (which wavelengths get in); the
slits are **geometric** (from which directions, and whether dust lands on the
optics). Their three jobs are: pass the beam; cut the shallow-angle ambient path
and the crosstalk from neighbouring strings; and close the board off as a debris
lid, which up-firing optics need because they collect the skin and string shed a
down-firing sensor would simply drop.

### The aperture's printable end — an open notch, after two shapes that failed

The endplate builds **+X → −X**, so each layer is a Y–Z slice and anything it
adds must sit within 45° of the layer at +X of it. Two shapes were tried and
both were caught from renders before printing:

**1. A closed rectangular slot bridges.** The roof resumes across the full
5.0 × 1.6 mm face over void, anchored only at its two Y edges — a **5 mm bridge
directly over the optics**, the worst place for one, since sag lands in the
aperture. A layer-walk probe measures **33 unsupported samples** along one
aperture.

**2. A 45° V ("/\") fixes the bridge but does not fit.** The void must close in
**Y, not Z** — Z is *in-plane* for these layers, so tapering the roof's thickness
only makes the bridge thinner, still a bridge. Tapering in Y gives the real 45°
stepover. But the apex needs `SLOT_DY`/2 = 2.50 mm of X from the packages' −X
edge at −20.50, landing at −23.00, and **the roof stops at −22.00** because the
quad op-amps stand taller than the roof underside. Truncated there, the flank
crosses the roof's −X boundary at 45° and leaves an acute **wedge of roof
material tapering 1.50 → 0.00 mm** — a knife edge, under the 1.6 mm floor for its
entire length. Measured, not estimated.

**3. What is built: the aperture runs out of the −X edge, sides parallel to X.**
Nothing ever closes over the void, so there is no bridge; the sides are parallel
to the build direction, so there is no stepover at all; and the material outboard
of every aperture is the full 4.40 mm web rather than a taper. The roof becomes a
comb of stubby teeth (4.40 × 5.40 × 1.60) joined at +X, which is where it fuses
into the endplate's comb brace anyway.

Every feature now clears the two-bead floor, including one that did **not**
before and was nothing to do with the V — the strip of roof at +X of the aperture
was **1.40 mm**, left over from the original 3.0 mm-wide slot. The aperture's +X
edge is now derived (`APER_X1 = BAND_X0 − MIN_WALL_2P`) so it is 1.60 by
construction, and it still clears the packages by 0.30 mm:

| Feature | Size |
|---|--:|
| +X strip, roof edge to aperture | **1.60** |
| web between adjacent apertures | 4.40 |
| outboard of the outermost aperture | 1.60 |
| roof thickness (Z) | 1.60 |

**What the open end costs:** the −X end is no longer partly closed. Cheap — the
shallow-angle ambient path was already handled by the 0.30 mm gap over 5.4 mm of
depth rather than by this edge, and −X of the cover is instrument interior, not
sky.

**If a true gable is wanted**, the op-amp column would have to move ~1.5 mm −X so
the roof could reach −23.50. That trades the TIA's distance from its photodiode —
the noise-critical summing node this layout is organised around — for lid
geometry, which is the wrong way round unless something else independently wants
the op-amps moved.

### PCB thickness — 1.6 mm, and the tolerance was landing on a clearance

**1.6 mm is correct and is not a layer-count question:** it is JLCPCB's standard
thickness at 4 layers *and* at 6, so even the 6-layer option raised in the
magnetic study would not move it.

⚠ **But 1.6 is a nominal with ±10 % (±0.16 mm), and the model was using the
nominal on a dimension where the tolerance is a clearance.** The board's *top*
is the design datum, derived downward from the string. The thing that physically
exists is the printed *plinth* underneath. So a board at the +10 % limit carries
its own components **0.16 mm higher than modelled**, straight into the 0.30 mm
gap it has to slide through under the cover — leaving **0.14 mm**, over 5.4 mm of
travel, with parts on the board. The model would have called that fine.

**Fixed by datuming the plinth off the worst-case board, not the nominal one**
(`PLINTH_TOP = PCB_TOP − PCB_T_MAX`, 9.501). That makes the tolerance one-sided
in the harmless direction:

| Board | Sensor face | Roof gap | Optical gap |
|---|--:|--:|--:|
| −10 % (1.44) | 11.79 | **0.62** | 3.32 |
| nominal (1.60) | 11.95 | **0.46** | 3.16 |
| +10 % (1.76) | 12.11 | **0.30** | 3.00 |

Clearance is now **never worse than designed**; what varies instead is standoff,
which is benign — signal is linear in it, and per-string gain trims it anyway.
The cost is ~0.16 mm of extra nominal standoff, about **0.45 dB**. Trading half a
dB against a mechanical interference is the right way round. `PCB_TOP` now means
*the highest the board top can be*, so the roof-clearance assertion tests the
thickest board the fab may ship rather than the one the model draws.

Z stack (nominal board): deck 6.00 → plinth 9.50 → board 9.50–11.10 → sensor
faces 11.95 → cover 12.41–14.01 → lowest string 15.11. That leaves **1.10 mm**
over the cover. Install order is board, cover, then strings.

### The magnetic pickup reaches the Pi through THIS board

The magnetic pickup has to feed two places: the **TS jack** (which must not be degraded)
and the **Pi**. Rather than run a second analog cable the length of the instrument, it is
digitised here and travels to the Pi on the USB link this board already has. **Digitising
early is the point** — once it is bits, the Pi's ground noise has no analog path back into
the audio.

**Split AFTER the buffer, never at the coil.** The tap comes off the AFE's buffer output,
in parallel with the relay → TS branch. This is not fussiness: a magnetic pickup's tone is
set by its L, R and **total C including cable**, so hanging a second cable directly on the
coil adds capacitance, lowers and damps the resonant peak, and **changes the TS output's
tone** with zero added noise. Buffering first makes the tap physically incapable of
affecting the direct path — which is what actually delivers the "TS unaffected" requirement,
not any amount of shielding downstream.

**The audio gets its own ADC (U12), deliberately not the MCU's.** Two independent reasons,
and the first is the real one:

* **Crosstalk.** The MCU's SAR is multiplexed across 20 inputs reading **tens of
  nanoamps**. The magnetic signal is line-level — four to five orders of magnitude louder.
  Through the same sample-and-hold mux, that is exactly the contamination the whole board
  is organised to prevent, and no downstream care undoes it.
* **Pin count.** All 20 ADC channels are already one-per-photodiode. There is no 21st.

`PCM1808PWR` sidesteps both and is better on merit: 24-bit delta-sigma, ~99 dB SNR, on the
signal a listener actually hears — against a 16-bit SAR shared twenty ways. It arrives over
I²S, a *peripheral* rather than an ADC pin. The mid-rail reference the TIAs already use
(U11) is what an audio input wants for biasing, so that infrastructure is free.

### All cabling exits −Y, and it made the board smaller

Both connectors now sit on the **−Y edge with their mouths flush**, so the two plugs present
as a single cable exit instead of two at different depths (a −X exit could not be routed
cleanly). That required widening the compute section **25.40 → 32.34 mm**, derived from the
edge budget rather than typed — the −Y edge, not the LQFP144, is now what sets that width.

**Both changes were free or better than free:**

* The widening costs **nothing in billed area**. The sensing strip already sets the bounding
  box's −X extreme at −30.42; the compute section lands at −25.34, inside it, with 5.08 mm
  of headroom before the box would move.
* The board got **shorter**: 190.1 → **182.1 mm**. Moving J2 off the −X edge freed a whole
  15 mm row; the audio ADC added ~6 mm back. Then the MCU/tail-screw swap below took
  another 9.75 mm, landing at **172.4 mm**, area 71.1 → **64.5 cm²**.

### The MCU and the tail screw swap sides — another 9.75 mm off the cantilever

The MCU used to start *below* `WRAP_Y`, clear of the wrap-band seam, which cost ~9.75 mm of
board for nothing. The wrap band is **wider in X** (−30.42) than the compute section
(−25.34), and the only thing occupying it was the tail M4. So the two now share it: the
LQFP144 tucks hard −X and climbs **into** the band, and the tail screw moves hard +X to get
out of its way.

| | Before | After |
|---|--:|--:|
| MCU | X −20.17…1.83, Y −87.75…−65.75 | **X −24.14…−2.14, Y −78.00…−56.00** |
| Tail screw | (−12.00, −59.60) | **(+2.40, −59.60)** |
| Board | 182.1 mm | **171.6 mm** |
| Cantilever past the tail screw | 51.75 | **48.00 mm** |

Both screws keep the full **4.60 mm of plinth wall**; the MCU clears the tail screw's
keep-out by 1.34 mm and stops 1.00 mm below the seam. Length taken off *this* end is worth
more than the same length taken off anywhere else, because this end is the cantilever.

**The two grips are no longer at the same X, and that is deliberate.** The head screw stays
hard −X, nearest the sensor row; only the tail one moved. The mount-symmetry assertion
caught this immediately — it was written to catch exactly "one of them moved alone" — and
was **narrowed rather than disabled**: mirrored **Y** still matters (equal leverage about the
sensing field; a stale one-sided derivation is how the −Y wrap once ended up 1.05 mm
slacker), but X never was part of the datum — two points at different X locate the board
just as well, the line between them is merely skewed.

It also gained a check it never had: that **each grip actually lands in the wrap plinth**
with its full wall. That is the real requirement — a screw with nothing to thread into is
the failure that matters — and until now the X-equality test had been standing in for it by
accident.

### Routing headroom — the funnel was fine, the MCU escape was not

Two questions that look like one, with opposite answers.

**The sensor → compute funnel was never tight.** Everything from the sensing strip has to
pass through its 13.62 mm width: **20 TIA outputs + ~5 power/reference nets = 25**. At
JLCPCB's standard 0.127/0.127 that is **49 traces per layer**, so ~98 across two
inner/bottom routing layers (L2 stays a solid ground plane for the analog). **~4× margin**,
and the fine 0.09/0.09 tier is not needed. This had been worked out in discussion but never
written down, which is why it kept being re-asked.

⚠ **The MCU's escape annulus was the real constraint**, and briefly it was bad:

| Side | Stepped-in compute | −X edge straightened |
|---|--:|--:|
| **−X** | **1.20 mm** — 4 lanes | **6.62 mm** — 26 lanes |
| +X | 9.14 | 8.80 |
| **+Y** | **1.00** | **1.00** |
| −Y | 29.60 | 28.85 |

1.20 mm on a side carrying **36 pins** is not merely tight — it is under what a staggered via
fanout needs (36 vias at 0.65 mm pitch want 23.4 mm of run against a 22.0 mm package side).
Two of the LQFP144's four sides were effectively blocked.

**Fixed by running the compute section −X to `PCB_X1S`**, so the board's −X side is **one
straight line end to end** rather than stepping in near −Y. Free, because the strip already
sets the bounding box there — and the board came out marginally *shorter* (172.4 → 171.6 mm)
because the wider section packs its rows better.

**The MCU had to be re-anchored for that to help.** It was placed at `x0 + half-width`, i.e.
relative to the section edge — so widening the section would have slid the package along
with it and preserved the same useless 1.20 mm. It is now anchored to the **tail screw's
keep-out**, the only hard obstacle on that row, which is what converts the new width into
annulus instead of travel.

⚠ **+Y is still 1.00 mm and is not fixed.** Only 7.00 mm of the MCU's 22 mm top edge sits
under the sensing strip; the rest has 1 mm before the board ends. Those pins must via down at
their pads and route back south — normal practice, and viable *because* −X and −Y now have
room to receive them. If layout disagrees, the lever is moving the MCU −Y, paid for in board
length, which is the opposite of what straightening the edge just bought.

**J2 is a 4-way `S4B-XH-SM4-TB`** (C161861) carrying ground and 24 V on ways 1 and 2, with ways
3 and 4 empty. (An earlier revision had a 6-way here with 5 V and audio on it.)

⚠ The 6-way's 20.0 mm width is **derived** from XH's 2.5 mm pitch (4-way B = 15.0, plus two
ways). Confirm against JST's drawing before layout, exactly as the S4B figures were.

**Why AUDIO_GND is a dedicated pin.** Not USB ground, and not the power ground either. USB
ground carries the Pi's return and its supply noise; a single-ended ADC measures its input
*relative to its own ground*, so any difference between source and ADC ground **is** signal —
routing the audio return through USB would sum the Pi's noise into the very signal the
architecture exists to keep clean. The power ground is no better here: the **LED row driver
switches at 96 kHz synchronously with sampling**, and that current flows in the power return,
so sharing it would inject the one noise source ambient subtraction cannot remove.

*(A 2-way THT header was considered and rejected: its post tails would protrude through the
board's underside — the face that bears flat on the plinth.)*

### Cable conduit — connectors reach the body without touching the pickup panel

Both plugs leave the board at −Y and have to get down into the instrument. The requirement
was a channel that passes a **connector**, one at a time — not merely a cable — and **no
cut-out in the magnetic pickup's top panel**.

**The deck is never touched, and that falls out of the geometry rather than needing a
dodge:** the deck's +X edge is `TP.PX0` = −16.60 and the **endplate begins exactly there**,
so out past the board the endplate's own top face is open sky. The conduit is a plain
vertical shaft in that face, dropping through the fill slab into the foot box. Verified open
at every z from +5 down to −24, and its −X edge sits **7.85 mm clear of the deck**.

**Sized by what must pass:**

| | Envelope | Source |
|---|--:|---|
| XHP-6 plug | 17.40 × 5.75 | JST's 4-way drawing (12.4) + 2.5 mm pitch × 2 |
| USB-C overmold | 12.35 × 6.50 | **USB-IF maximum** — so *any* cable passes |
| **Shaft** | **9.50 (X) × 23.00 (Y)** | +3.75 / +3.00 clearance |

**Orientation is the whole trick.** Plugs feed through with their **wide axis along Y** —
the direction the endplate has 27 mm to spare — so X only has to clear the plug's *thin*
axis. Sized the other way up the shaft needed 20.40 of X and left **2.40 mm walls in a
structural slab**; this way X needs 9.50 and the walls are **7.85**. Y has to be long
anyway, because the shaft must span past the back face of a *mated* plug so the cable can
turn down without doubling back.

**Cables and male connectors are modelled at true diameter** (`optical_cables`: USB-2 slim
shielded 2.6 mm, 6-way XH bundle 4.0 mm, plus both plug bodies) so the route is *planned*
rather than assumed. They are in the overlap gate — 391 components, no new collisions — so
if the conduit or the plinth ever moves into the cable's path, the gate says so.

The model makes one thing visible that a side view would hide: **the USB-C socket sits
entirely −X of the endplate**, so its lead travels +X as well as −Y to reach the shaft.

### The USB cable — STRAIGHT, and 1 m; the right-angle idea was wrong

A right-angle USB-C looked obviously better and **is not**, because of where J2 sits.

J1 is −X of J2, so its lead must cross J2's footprint to reach the shaft. A right-angle
leaves +X **at the plug** — which is exactly where J2's body is. Modelled, the lead turned
+X at y −112.85, dead inside J2's −120.85…−106.85 span, and drove straight through it
(caught from a render).

**The escape is a longer plug, not a detour.** A straight USB-C's own back face lands at
−126.85, already clear of J2's −120.85, so the lead turns +X in free space with a **single
bend**. The right-angle would have needed exit +X → turn −Y → turn +X: three bends to solve
a problem the straight plug does not have. "Angled saves a bend" was true only in isolation;
with the neighbour in the picture it costs two.

The lead now turns at −128.35, clearing J2 by **7.50 mm**. An assertion enforces it: any lead
crossing a neighbour in X must turn −Y of that neighbour's back face, so a future change to
plug length or socket position fails at import instead of in a render.

**J2 stays straight** for its own reason — it sits nearly over the shaft already.

**Length = 1.0 m**, from the routed path rather than a guess. `usb_run_length()` walks it
orthogonally — a harness follows the box, it does not fly point to point:

| Segment | mm |
|---|--:|
| +X to the shaft | 18.6 |
| down the shaft | 22.8 |
| along Y | 109.3 |
| **−X to the keyhead** | **568.8** |
| up into the Pi | 40.2 |
| **Total** | **759.7** |

| Stock length | |
|---|---|
| 0.5 m | **too short by 260 mm** |
| **1.0 m** | **240 mm spare — 32 % slack** ✅ |
| 1.5 m | 98 % slack — 744 mm to hide |

At 2.6 mm OD it is exactly the **Ø2.6 raceway limit the chassis already publishes**, so it
uses the existing route rather than needing a new one.

**A latent bug this turned up:** the conduit's Y length answers **two** requirements — get a
plug *through* (20.40, set by the XH's 17.40 width) and reach *past* a mated plug's back
face (17.00). It was sized on the span alone, and only happened to be large enough because
the straight USB-C plug was longer than the XH is wide. Shortening a plug — exactly what the
right-angle does — would have quietly made the shaft too narrow to pass one. Now `max()` of
both.

### `PLUG_L` is a PURCHASING SPEC, not a measurement

Nothing is ordered yet, and overmold **length** is not standardised — USB-IF fixes the
cross-section (12.35 × 6.50) but not this, and surveyed parts run **~10–25 mm**. So instead
of guessing a number and hoping, the geometry was made insensitive to it in the direction
that matters, and the number became a rule for what to **buy** — checkable at order time.

**Short plug — the dangerous case, now impossible.** A short boot was exactly what put J1's
lead into J2. A lead crossing a neighbour now turns at **whichever back face is further −Y,
its own or the neighbour's**. A short plug simply runs further in free air before turning.
Deriving the turn from the plug's own length alone caused the clash; deriving it from the
neighbour alone would make a *long* plug double back. Taking the deeper of the two is right
for every length.

**Long plug — only eats conduit depth, and the endplate has a hard limit.** The conduit may
not pass y −132.15 or the −Y exterior wall drops under `MIN_WALL_2P`. That backs out to
**20.3 mm of plug**, so the BOM specifies **≤ 20 mm** and an assertion holds the model to it.

Swept across the plausible range, with the conduit as built:

| Overmold | Turn at | Clears J2 | In conduit | |
|--:|--:|---|---|---|
| 10.0 | −122.35 | yes | yes | ✅ |
| 14.0 | −122.35 | yes | yes | ✅ |
| 18.0 | −126.35 | yes | yes | ✅ |
| 20.0 | −128.35 | yes | yes | ✅ |
| 22.0 | −130.35 | yes | yes | ✅ |
| 25.0 | −133.35 | yes | **no** | too long for the duct |

So **anything from 10 to 22 mm works** and only the extreme fails. Once a real cable is in
hand, set `PLUG_L["J1"]` to the measured value; nothing else has to move.

**Power (J2): 24 V from the instrument trunk, not USB VBUS.** (This said *5 V* until
2026-09-18; the rail moved to 24 V with a local buck on 2026-09-14 and this line did
not follow. `elec/optical.py` wires J2's four ways as `1=GND 2=+24V 3=+24V 4=GND`.)
⚠ **And the current argument that used to sit here was wrong in both directions.** It
read *MCU ~200–300 mA, PHY ~50, 21 op-amp channels ~40 — already past a USB port's
500 mA before a single emitter is lit.* The itemised budget in `elec/optical.py` was
written in the first place because assertions like that one had never been added up, and
it names this line as one of them. Derived from the datasheets:

| | claim | derived |
|---|---|---|
| MCU (DS12110 T30) | ~200–300 mA | **165** typ / 220 max @25 / 400 max @85 |
| PHY (DS00002646 T4-2) | ~50 mA | **41** typ / 51 max |
| 21 op-amp channels | ~40 mA | **11.7** typ / 16.1 max |

The op-amp figure is 2.5× the derived maximum — 21 channels is five TLV9064 quads plus a
TLV9061, and the TLV906x draws 538 µA per amplifier, so 21 × 538 µA = 11.3 mA. And the
conclusion does not survive either: **219 mA at 5 V before any emitter**, 324 mA at the
50 % duty the design assumes, 430 mA with the emitters on continuously. A USB port's
500 mA would in fact carry it.

**The real reasons stand and are elsewhere in this design.** Margin: the worst case in the
budget is 499 mA with maximum parts at 25 °C, which is the limit and not a headroom. And
noise, which is the actual argument — taking 5 V would mean a ~600 mm run sharing a
return with the Pi, on a board whose LED driver switches at 96 kHz *synchronously with
sampling*, where a shared return puts that switching straight onto the reference the TIAs
measure against.
⚠ **LED current is NOT the best SNR lever** — this said "second-best" and
`src/optical_pickup.py` said "first", and the re-derived noise budget says neither.
The dominant term is the op-amp's voltage noise across a plateau that ends at
GBW/noise-gain, so it scales with the amplifier's BANDWIDTH: a slower part cuts it and
a faster one makes it worse. Emitter drive is a real lever and it is not the first one.
J2 is side-entry on the **−X edge**: the −Y edge is taken by the USB receptacle
and the floor-ledge lane, and −X of the board is open air (the optical relief
removes the tie bar's wall there), so that mouth is reachable. It plugs in after
the board slides home.

**All ten emitters are driven by ONE FET.** Ambient subtraction sweeps the whole
row on, then the whole row off, which gives the front end ~10 µs to settle
instead of ~1 µs. Per-string *current* is still set individually by R1–R10; what
is common is only the on/off gate. The cost is optical crosstalk between
neighbouring strings — one of the things the prototype needs to measure.

### HISTORY — Two items that were closed, and are open again after the 2026-08-01 check

**MCU — package still right; price and stock both wrong.** The LQFP100
`STM32H743VIT6` brings out only **16** ADC channels; this board digitises **20**
(one per photodiode). The 144-pin **`STM32H743ZIT6`** has exactly 20, and 22 × 22
over its leads fits the 30 mm tail with 4.0 mm clear. That reasoning stands.

> **2026-09-17 — swapped to the LQFP176 `STM32H743IIT6` (C89597).** The ZIT6 went to
> **0** at JLCPCB; the IIT6 had **548** at **$10.01 @10**. Same die (20 ADC channels,
> OTG_HS, 2 MB flash), so the ADC and ULPI port assignments carry over and only pin
> numbers change — re-derived from KiCad's CubeMX-generated ST symbol and verified on
> the generated netlist. The tail is now 62 mm wide, not 30, so the 26 × 26 package
> fits with room: its −X escape side went from 6.6 mm to 26.9 mm. The board grows
> 5.4 mm at −Y and stays inside the −Y budget (cables clear the instrument edge by
> 5.38 mm). Rejected alternative: the `STM32H750ZBT6` in the same LQFP144 (416 in
> stock) — footprint-identical but 128 KB of flash, needing an external QSPI part and
> a two-stage boot.

⚠ **The ~$7.63 does not.** Verified on LCSC 2026-08-01 (**C114408**): **$11.07
@1, $9.93 @10 — and 7 units in stock.** Ten boards need ten parts. So it is
$2.30 dearer than budgeted *and* not presently orderable at the project's
10-instrument convention. It also loses the "cheaper than the 100-pin part"
argument that justified stopping the search here. Re-check at quote time; if
stock has not recovered, the thing to attack is the **20-channel ADC
requirement**, since that is what forced 144 pins to begin with.

**Photodiode — `VEMD4110X01` (C3211080).** Si **PIN** photodiode (not a
phototransistor, so the linearity the audio path needs survives), 0805, 0.42 mm²
active area, ±55°, with a **daylight-blocking filter, 740–1040 nm**, matched to
830–950 nm emitters. **$0.58** at the 100+ break; ⚠ 72 in stock against 200 for a
run of ten. The X02 named in earlier revisions is not in LCSC's catalogue; the
X01 has the same filter and the same outline, so nothing about the design changes.

### The optical filtering — what it is and what it actually rejects

**There is no separate filter part on this board, and none is needed: the filter
is inside the detector package.** That is the better place for it — a bonded
window in the cover would be an extra part, an extra process, and would sit
3 mm from the sensor instead of on it.

The filter passes **740–1040 nm** and blocks the rest. The emitter is 940 nm,
comfortably inside. So everything the detector sees outside that band — which is
the whole visible spectrum — is gone before it becomes photocurrent.

**Why that matters more than it sounds.** The board's own LED-on/LED-off
subtraction already removes ambient *offset and flicker*. What it cannot remove
is **shot noise** (∝ √photocurrent, irreducible once the photons are converted)
and **saturation** — a detector pinned by sunlight has no headroom left for the
string signal, and subtracting two saturated readings gives zero, not signal.
The filter attacks both at the only point where they can be attacked: before
conversion.

**Ambient sources, ranked by how much trouble they actually cause:**

| Source | Gets through the filter? | Why |
|---|---|---|
| **Sunlight** | ⚠ **the real threat** | ~50 % of solar energy is IR and it is broadband — a large fraction lands inside 740–1040 nm |
| **Incandescent / halogen** | ⚠ **bad** | a ~2800 K blackbody peaks *in the near-IR*; these emit more 940 nm than visible |
| **Fluorescent** | ✅ **almost entirely blocked** | output is overwhelmingly visible phosphor emission plus mercury lines at 405/436/546/578 nm — all outside the passband. Only a weak mercury IR line near 1014 nm creeps in at the band edge |
| **White LED** | ✅ **blocked** | blue pump + phosphor; there is very little IR to pass |

So **modern indoor lighting is the easy case** and the filter handles it. Note
too that fluorescent flicker (100/120 Hz on magnetic ballasts, 20–60 kHz on
electronic ones) is the part that would otherwise be dangerous — the electronic
ballast rate lands squarely in a 48 kHz sampler's band and could alias — and
blocking the light removes the problem at the source rather than relying on
subtraction to catch it.

**Sun and halogen are what remain**, and there the design gets one piece of luck
it did not plan for: **940 nm sits in a water-vapour absorption band**, so solar
irradiance is genuinely depressed there relative to 850 nm. That is a standard
reason to choose 940 nm for IR sensing outdoors, and this design already picked
940 nm for other reasons.

**If the prototype still says sun is a problem**, the next step is a *narrow*
bandpass (940 ± 25 nm interference filter) rather than the broad 300 nm
daylight filter — that would be a bonded window in the cover slots, the part the
earlier revision of this file anticipated. Worth measuring before buying: a
gigging instrument mostly lives under stage and room lighting, which the table
above says is already covered.

**Nothing on this list is open any more** (project rule: NO consignment, all PCB parts
LCSC-library). The PHY, the emitter, the op-amp, J2 and the 3.3 V regulator were each
closed and several have since been replaced; the parts as built are in
[`docs/order-parts.md`](docs/order-parts.md).

**Prototype: the first measurement is now string 2, not `SENSE_D`.** Specifically
a **.014 plain string at 22 mm at a realistic drive current** — and now
necessarily with a **~120° emitter**, since that is what is available. The
earlier version of this note said "with a narrow-beam emitter"; that test cannot
be run with a stocked 0805 part, so the measurement will show the design at its
*worst* case for lever 1 rather than its best. Read the result accordingly: it
is a floor, not a representative figure.

**Cost (resolved 2026-08-01)**: **$26.66/board in parts**, computed by
`parts_cost()` from the table above. The MCU ($9.93) and the 20 photodiodes
($11.60 at the 100+ break) are 81 % of it; everything else together is $5.13.
Assembly follows the same per-*order* economics as the
tee/sensor panel ($25 setup + ~$1.50 per unique feeder), so it should ride the
**same JLCPCB panel** — the 0402 R/C and generic parts overlap with the existing
boards, and only the specialised lines add feeders.

### PCB cost basis — 10 instruments per order (PROJECT CONVENTION)

**Every PCB cost in this BOM is the cost to build 10, divided by 10.** One
JLCPCB order, use what each instrument needs, discard the extras. Other hardware
bought in packs (screws, inserts, dowels) keeps its **per-unit** price as
elsewhere in this file — pack overage is not amortised. PCBs are different because
their fixed costs are large and genuinely per-order.

**Why 10, and why the number matters.** JLCPCB's PCBA quantity ladder is **2, 5,
then multiples of 5** — you cannot order 3. So the per-instrument curve is a
**sawtooth, not a smooth decay**, and three instruments cost *more each* than two:

| Instruments | Order | Waste | Order total | Per instrument |
|--:|--:|--:|--:|--:|
| 1 | 2 | 1 | $155.38 | $155.38 |
| 2 | 2 | 0 | $155.38 | $77.69 |
| 3 | 5 | 2 | $264.70 | **$88.23** ↑ |
| 5 | 5 | 0 | $264.70 | $52.94 |
| 6 | 10 | 4 | $446.90 | **$74.48** ↑ |
| **10** | **10** | **0** | **$446.90** | **$44.69** |
| 15 | 15 | 0 | $629.10 | $41.94 |
| 20 | 20 | 0 | $811.30 | $40.57 |

*(Recomputed on the $82.50 fixed / $36.44 variable. The
**shape** is unchanged — it comes from the quantity ladder, not the rates — so
both conclusions below still hold; only the absolutes moved.)*

Two consequences worth acting on:

* **Build in ladder multiples.** 3 and 5 have the *same order total*; 6 and 10 do
  too. If you are planning 3, build 5 — the boards are already paid for.
* **10 is the knee.** It is the first quantity within 30 % of the variable-cost
  floor; past 15 the gains are slow. Hence the convention.

### Optical pickup board at that basis — $44.69 per instrument

Board is **62.3 × 187.1 mm** bounding, **66.4 cm² of actual outline**, 4-layer,
**155 parts**, ~560 solder joints. (Earlier revisions said 47.5 cm², which predates
the +X wraps and the M4 bands; then 184.4 mm long, which predates J2 becoming a
4-way; then 37.4 × 171.6, which predates the LQFP176.)

⚠ **The two numbers are far apart and the fab bills the LARGER one.** The board is
not a rectangle: a 13.6 mm-wide sensing strip runs the full 187 mm, and only the
two ends open out to 62.3 mm — for the MCU pocket at one end and the connectors at
the other. So the outline is 66.4 cm² (essentially unchanged by the MCU swap, which
is the useful news) while the **billed bounding rectangle is 116.6 cm²**, and the
$6.42 fab line below is computed on the outline. At $0.10/cm² the honest figure is
**$11.66**, about **+$5.24 per board** — 12 % on the $44.69.

That is the strongest argument on this page for panelising, and it is worth
measuring rather than assuming: 50 cm² of each board's billed rectangle is empty
air, and a naïve 2-up head-to-tail nest does *not* recover it (the free region
beside the strip is 43.7 mm wide and 103 mm long, and the other board's pocket is
62.3 × 69.6). An offset or interleaved nest may; that is a layout exercise with a
$5-per-board answer attached.

| | | |
|---|---|---:|
| **Fixed, per order** | PCBA setup $25 + feeder loading **$22.50** (15 Extended lines × $1.50; **5 of the 20 lines are Basic**) + component MOQ overage ~$20 + 4-layer fab tooling ~$15 | **$82.50** |
| **Variable, per board** | parts **$29.07** (computed, quantity-correct) + fab $6.42 (64.2 cm² × $0.10) + assembly $0.95 (~560 joints) | **$36.44** |
| **Order of 10** | 82.50 + 10 × 36.44 | **$446.90** |
| **Per instrument** | ÷ 10 | **$44.69** |

*(The magnetic-pickup channel and the single-ended cable exit together cost **$0.53 per
instrument**. The audio ADC and the 6-way connector add $0.78 of parts and one feeder, and
the board getting 8 mm shorter gives $0.30 of it back.)*

*(History: $46.72 → $59.32 → $52.72 → **$42.61**. The spike was the photodiodes
at their @1 price; the fall is resolution — detectors at the 100+ break, the
op-amps $2.90 under budget, the emitters $3.22 under, and a feeder estimate that
was **overstated by half** because it counted part *variety* before anyone
counted the actual lines. 5 of the 18 lines are Basic and carry no feeder charge
at all. The one thing that went the other way is J2's refit: +5 mm of board,
+$0.18/board of fab.)*

**Soft in this:** the fab terms ($15 tooling + $0.10/cm²) are estimates — worth a
JLC quote before trusting the absolutes, though the *shape* of the curve comes
purely from the quantity ladder and does not depend on them. Parts now use the
**@10 price** where verified ($9.93 MCU) and @1 where not ($0.9334 photodiode,
because LCSC showed no break at the quantity we need — and cannot supply it
anyway).

**Photodiodes alone are now $18.67 of the $41.60** — they have overtaken the MCU
as the most expensive thing on the board, which was not true when the design was
settled. Worth noting the sensitivity: the detector count is **two per string by
choice**, for the SUM/DIFF pair that defends against the 2f₀ octave error. That
choice now costs ~$9.30/board rather than ~$3.50. It is still the right call —
a confident octave-up error is worse than any price — but it is no longer a
rounding error, and a cheaper 0805 PIN diode is the highest-value substitution
on this board.

**Per-string audio remains about $9/board**: pitch-only would fit USB full-speed,
deleting the PHY and allowing a cheaper MCU.

**One free saving at layout:** the outline uses far less copper than its billed
bounding rectangle. Two boards nested head-to-tail on the panel should recover a
useful slice of the $6.90 fab line.

**Layer count is a PANEL decision — and ONE 4-LAYER PANEL WINS.** This board needs
4 layers (20 analog channels wanting a ground reference, a 96 kHz switching driver
to isolate from them, a 60 MHz ULPI bus). The tee and sensor boards do not. But
panelising everything at 4 layers is *cheaper* than splitting the orders:

| | Cost at 10 instruments |
|---|---:|
| Upgrade the 220 small boards (12 tee + 2 carrier + 8 sensor, ×10) to 4-layer | **$2 – $13** |
| Second order to keep them 2-layer ($25 PCBA setup + ~$8 duplicated feeders) | **~$33** |

So one panel saves roughly $20–30 across ten instruments — about $2–3 each, i.e.
marginal, but it also keeps the "one assembly job" simplicity. 4 layers costs a tee
board nothing but planes it does not need.

*This corrects an earlier note in this file that said splitting was cheaper.* That
used a $0.10/cm² fab rate, which is the PROTOTYPE regime; JLCPCB quotes 4-layer at
**$70.60/m²** at panel quantities, an order of magnitude lower, and at that rate
the fixed cost of a second order dominates. The conclusion inverted once the rate
was real rather than assumed.

**Measured, no longer an estimate:** the tee board is **22.0 × 24.0 = 5.28 cm²**
(`electronics.tee_pcb`), so 220 small boards ≈ **0.117 m²** — within 6 % of the
0.11 m² the table above assumes. The conclusion holds with margin; it would take
the small boards being roughly *double* their modelled size to make splitting
worthwhile.

## Tools (shop infrastructure — NOT per-instrument cost)

| **TRRS coil mandrel** (printed, 2 pc) | `tools/coil_mandrel.step` + `tools/coil_mandrel_sleeve.step` — wind the leg's TRRS lead 7 turns between the barrel's pitch ribs, slide the Ø23.0-bore sleeve over it, heat-set | 1 set | PRINT IT | filament only | **Why a tool and not an instruction.** The leg's slack store is a coil in the gap between the two tenon ends, and the TURN COUNT decides how low the leg can go: the coil gets fatter as it compresses, and below ~6.59 turns it swells past the sleeve's Ø24.7 bore before the leg reaches its low stop. At 6.5 turns it binds at a 71.3 mm gap against a 90.8 minimum; at 7 it binds at 26.6, about eleven ladder steps of headroom. Half a turn is the difference, so the count is fixed by a scribe line rather than by counting. **Why TWO pieces (user).** A bare mandrel sets only the coil's inside diameter and leaves the outside to spring-back — a number nobody can quote for an unspecified jacket, against a bore that allows only 20.9 of mean. Capturing the cable in an annulus its own width pins the mean between two surfaces: wound on 15.2, capped at 23.0, mean 19.0 by arithmetic. The outer also holds every turn put through the heat and the cool. **⚠ And it is SET STRETCHED, not turns-touching.** The service span is 90.8–253.2; a coil set at turns-touching (26.6) would live held at 3.4× to 9.5× its own free length, and a coil held like that loses its curl — which is a functional failure here, since 342 mm of uncoiled slack does not fit a Ø24.7 bore. Set at a **80 mm free span** (7 turns at 11.43 pitch, which is why the barrel carries a helical rib) it lives at 1.1×–3.2×, never compressed below free where it would buckle and jam. **⚠ Heat is not optional** — winding cold and leaving it gives creep, not a set. **Print in PA6-GF and set it in an oven at 80 °C for 30+ min** (user has both), then cool fully BEFORE opening — the set happens on cooling. PA6-GF's HDT is far above anything the jacket wants, so the tool stops being the limit and the CABLE becomes it: most TRRS jackets are rated 80 °C continuous, and if 80 relaxes there is room to climb. Dry heat is slower into a wound coil than water, hence 30+ min rather than 15, and keep the two moulded connectors out of the hot zone. **⚠ Heating PVC gives off plasticiser — ventilate, not a food oven.** (PA6-GF was dropped for PETG-GF on cost for *instrument* parts; a one-off tool is exactly where that trade does not apply.) **Only needed if a pre-coiled TRRS lead with a real datasheet cannot be bought** (see docs/leg-trrs-routing.md) |


One-time purchases that outlive this project; documented here so nothing is
a surprise at build time, but **excluded from the cost summary and from
pros/cons when weighing approaches** (project policy).

| Tool | For | ~Price | Notes |
|------|-----|--------|-------|
| **JST crimp tool** | XH harness (contacts SXH-001T-P0.6) | $25–45 | IWISS SN-01BM or Engineer PA-09 (mfr/eBay — not DigiKey); covers XH/PH/most small JST; budget a dozen practice crimps |
| **Soldering iron** | bench-once pigtails (SP-3541, XT30), PCB touch-up | — | presumed owned |
| **Heat-set insert tips** | M4 (94459A150); M2 only for the last two — the bus-B placeholder tees, pending their fold into the lever PCBs | ~$15 | fits the soldering iron |
| **2.5 mm hex key** | ball-end L-key (or a 2.5 mm bit in a driver) | commodity | THE ONE DRIVER the instrument is converging on: every M4 button head and the M3 motor socket caps take it. Not yet sufficient on its own — the two bus-B tees' M2s are the last to migrate; ball end for the angled reach to the pickup's -Y retention screw |
| **Hardened nozzle ≥0.4 (ideally 0.6)** | PETG-GF (vendor recommendation) | ~$15–30 | glass fiber eats brass nozzles |
| **Wire strippers 20–30 AWG** | all harness work | — | presumed owned |
| **Current-limited bench supply** (≥24 V, adjustable current limit) | FIRST POWER on every first-article board | ~$50–80 *(unverified)* | set 24 V / ~100 mA; a short becomes a reading instead of a blown fuse. Never first-power a board from the instrument's own supply. `docs/board-bringup-diagnostics.md` §1 |
| **WCH-LinkE** | flashing + debugging every CH32V board (motor_ctrl, output_panel, 11 lever sensors) | ~$5–10 *(unverified)* | the ONLY probe that talks to CH32V parts — an ST-Link or J-Link will not. Also a USB-serial port |
| **USB-CAN adapter** (CANable-class, works with `candump`) | seeing either CAN bus from outside the instrument | ~$15–30 *(unverified)* | motor_ctrl heads both buses and the Pi is on neither, so if motor_ctrl is the broken thing nothing in the instrument can see the bus |
| **8-channel logic analyser** (24 MHz class) | CAN TX/RX at the MCU, SPI to the volume pot, I2S framing | ~$10–15 *(unverified)* | splits "MCU not transmitting" from "transceiver or wire dead" |
| **Multimeter** | rails, continuity, 60 Ω across CAN_H/CAN_L | — | presumed owned |
| **Oscilloscope** | buck ripple, CAN wave shape, I2S clock | — | only when the cheaper tools say "present but wrong"; presumed owned or borrowed |
| **Lever-board programming jig** (printed nest + 4 pogo pins) | flashing the 11 lever/pedal sensor boards without hand-probing four scattered SWD pads | 1 | PRINT IT (`tools/lever_prog_jig.step`, from `src/lever_jig.py`) + **4× P75-B1 pogo pins** *(price unverified)* | The board drops in component-face down; pin positions are READ from the routed board (TP1–TP4), so rebuild the tool after any `lever_sensor` re-route. J1 is powered through the end window (the board has no +3V3 pad). The nest is exactly one pin-barrel tall, so pushing each pin down to the bench seats it at height — then a drop of CA. **⚠ The three pin dimensions in the module are from memory of the P75 drawing: caliper the pins that arrive before printing.** The board has no room for a standard debug header
| **Bring-up leads, made once** | bus taps and the audio loopback | wire + housings on hand | one **XH** and one **PH** Y-cable (bus tap for the CAN adapter); one **¼″ TS → bare wire** loopback lead (output jack back into the pickup terminal) |

## Cost summary (per instrument)

**One model only** — the basic/pro split is gone, every instrument is fully
populated. PCB lines use the 10-instruments-per-order basis above; everything
else is per-unit. Motors still dominate. **Prices below are approximate and
several are unverified — re-verify the whole file before ordering.**

| Group | Per instrument | Confidence |
|-------|---------------:|------------|
| Filament (printed) | ~$53 | estimate; **spool prices verified**, masses are model estimates |
| Mechanical hardware (motors, screws, bearings, belt, fasteners, dowels) | ~$620 | belt/collar/bearings **verified**; motor + all McMaster **[m]** |
| Wire | ~$35 | estimate, excludes 10 control drops |
| Electronics + UI (motor controller, power + USB panel boards, Pi 4 1 GB, jacks, encoder, OLED, UI board) | ~$97 | **all verified** (2026-09-25: the display is sized to be read at 1 ft, 63.4×32.7 — white-on-black and that size are only had as a module; −$4 on the encoder for sourcing it where it is actually in stock; **+$5 for the UI board, its two 1×20 headers, the ribbon header and the ribbon**) |
| Optical pickup board (148 parts, 4-layer, ÷10 basis) | **~$45** | parts cost **computed from the model**; all 18 lines have real MPNs |
| Control sensors, 10 controls (MT6701 + magnet + board) | ~$50 | IC + magnet **verified**; boards not yet quoted |
| Tee / carrier PCBs | ~$25 | estimate |
| **Total** | **~$1,012** | |

**The total barely moved, and that is a coincidence worth spelling out.** The
optical board went **up** $6 net (photodiodes +$12, part selection −$6) and the
buck up $5; the bearings came **down** about $25 once the MR85ZZ was sourced at
$0.49 instead of $4.38. Those roughly cancel. Do not read the unchanged total as
"the estimate was fine" — six individual lines were wrong, two of them badly,
and the offsets were luck.

**The largest remaining uncertainty is still the motors**, at ~$350 of the
~$620 mechanical figure and **not verified** — see the drive-motor row. If the
MT bundle is not $35, this total moves more than everything found today combined.

Mechanical detail: 10× MKS SERVO42D CAN MT (~$350) is the bulk; +Tr5×1 screw stock
(**$10.97** for 2×350 mm = **12** pieces — 700/52.3 = 13.4 counts the two rods as one continuous 700; each 350 yields floor(350/52.3) = 6, so 6+6 and 10× H-flange nuts (**$65**), **30**× MR85ZZ (3 per screw: two thrust + one top)
(**~$10** at Trianglelab, ~$88 at Bearings Direct — two per screw now, see that row),
**0**× 695ZZ — retired: all 32 bearings are 688ZZ now (bridge, knee levers, foot pedals; 2026-09-10; the old ~$44 Fast Eddy / ~$158 Bearings Direct prices were for 32 × 695ZZ), shaft collars **deleted** (−$25: the retainer is printed),
Ø3 shaft (~$30), dowels (~$22), GT2 belt 6.5 m (**~$3.50–11**
verified at $0.54–1.73/m; the old "$12–130" range was wrong at both ends —
it appears to have conflated per-metre with per-spool), M-hardware packs (~$50).
Electronics detail: the Pi 4 + its buck replace the Pi 5 + 6 A buck (~$130 saved,
since audio→MIDI moved onto the optical board), and the 10-channel PCM1864 ADC
path is **deleted outright** for the same reason — the optical board digitises its
own twenty channels. Those two changes together take roughly **$160** off what
this section previously totalled.

## Cannot verify — needs a manual check [m]

Everything below was attempted on **2026-08-01** and could not be confirmed from
a fetchable listing. These are not "probably fine" — they are unchecked. Ranked
by how much money rides on each.

| # | Row | Why it could not be checked | What to do |
|--:|---|---|---|
| 1 | **Drive motor, SERVO42D CAN MT** — $350/instrument | Price sits behind a **variant dropdown**; all three vendors publish only a "from" price, which is the **MB (board-only)** floor. The ElectroPeak link in the row is the **wrong SKU** — driver only, $12.50, motor explicitly excluded | Add CAN MT to a cart at [P3D](https://p3d.mx/products/makerbase-mks-servo42d-nema17-foc-motor) or [makerbase3d](https://makerbase3d.com/product/servo42d-nema17-closed-loop-stepper-motor-driver-cnc-3d-printer-for-gen_l-foc-quiet-and-efficient/), record the real number, and **replace the ElectroPeak link** |
| 2 | **All eight McMaster rows** — dowels, cup-tip screws, heat-set inserts, mount screws, hold-down, shafts, guide rods, M2 grubs (~$50–70) | mcmaster.com serves **no product content** to automated fetches — every part URL returns the bare catalogue navigation. This is a site-wide block, not a bad URL | Open each part number in a browser. Part numbers themselves are stable and were previously correct |
| 3 | **Tr8×2 H-flange nut — dimensions read off the seller's drawing, not yet measured** | The drivetrain moved Ø5×1 → Tr8×2 (see the Lead screw + nut row). The listing (AliExpress 3256804704147842, SKU "Pitch 2mm Lead 2mm") is unfetchable, so all six numbers in `dimensions.py` — flange 22 × 10.5 × 4, boss Ø10.2 × 11, total 15, ear holes Ø3.5 at ±8 — were read by hand off its drawing, which itself states "a normal error of 0.5–1 mm". The **'Lead 8mm' variant on the same listing is the 4-start** — it looks identical and does not self-lock | **Order ONE first and measure it.** `NUT_FLANGE_L` sets the row spacing (asserted against the flange clearance), `NUT_HOLE_D` sets the guide rod, and `NUT_H` feeds the nut-to-ledge assert. Confirm the variant reads **Pitch 2mm / Lead 2mm** before ordering all 12 |
| 3b | **Anything that TURNS is checked by `tools/check_sweep.py`, not `check_overlaps`** | `check_overlaps` compares parts *where they sit*, which is the wrong question for a rotating part — what must clear is its swept circle. Three real collisions hid behind that gap at once: a Ø20.8-swept retaining collar in a 9.5 mm lane, the drive pulleys buried ~1.7 mm in the endplate foot (allow-listed as an "intended contact" because where they sit they only graze), and a grub-screw lug sweeping Ø17 | Run **both** gates. `check_sweep` registers rotating parts in its `ROTATING` map — **add to it when you add a part on a shaft**, or the gate silently says nothing about it |
| 4 | ~~**2.42" OLED module** — ~$17~~ | **CLOSED 2026-09-25, and this row's own closing note was already out of date when it was written.** It said "there is no module: the UI is one JLC-assembled board carrying a bare panel (C5123566)" — that was the 2.42" bare-panel branch, which the size requirement killed the same day. There IS a module: **NHD-2.7-12864WDW3, $38.08, 2,057 in stock, verified**, white on black at 63.41 × 32.69, because white-on-black at that size is not sold as a bare panel anyone will place. The UI board beside it is real and routed (`elec/ui_board.py`) | Nothing on price. What IS live: the ribbon header **C5156673 at 154 in stock**, and the ribbon header's 10.0 mm height, which is an estimate — see the UI board section |
| 5 | **Ø3 g6/h6 precision shaft** — ~$30 | McMaster (see #2); also the row points at a **category page**, not a part | Pick an actual part number while you are there. *(2026-09-10: the guide rods are no longer this stock — they are Ø3.5 drill blanks sized to the measured nut ear hole; see the Guide rod row)* |
| 6 | **Threadlocker, plastic-rated (e.g. Loctite 425)** — 10 joints/instrument | Price not looked up, and **compatibility with PETG-GF is untested**: the reason for choosing a plastic-rated type is that anaerobic 242/243 can craze thermoplastics, but nothing here has been tried on this filament | Put a drop on a spare printed endcap pulley: check for crazing after 24 h, and try breakaway torque by hand. Record the product and price |
| 7 | ~~**688ZZ screw bearings**~~ | **CLOSED 2026-10-06.** The recommended part is [Bearings Direct 688-ZZ](https://bearingsdirect.com/688-zz-mini-ball-bearing-8x16x5-shielded-mr688zz/) (AMPEC, 587 N static on the listing, $4.38 each, 489 in stock) | On the first one in hand, measure the inner-ring OD (~Ø10.2) and outer-ring ID (~Ø13.8): the pulley boss (Ø9.6) and the rail ledge (Ø14.4) are sized to them by rule of thumb |

Two rows verified but flagged for **availability**, not price:

* **SN65HVD230DR** — $2.45/stock-0 was **DigiKey only**. On LCSC (`C12084`) it is **$0.6185 @10 with 32,557 in stock**. Sourcing a part from one distributor and concluding it is scarce is its own failure mode: check the distributor we actually assemble through first.
* **Tinmorry TPU 95A** — $22.99 correct, but **sold out**. Only ~40 g is needed,
  so any 95A spool substitutes.

Plus **one** optical-board part that cannot supply a run of ten. The
**STM32H743ZIT6** (7 in stock) is closed — the board moved to the **IIT6**, 548 in
stock. What remains is the **VEMD4110X01** photodiode: 95 in stock on 2026-09-17
against 200 for a run of ten.

⚠ **And it has no substitute.** LCSC's catalogue was swept on 2026-09-17 for a
daylight-filtered PIN photodiode in an 0805 land and this is the only one. The
parts that look like alternatives all fail on the filter — `TEMD7000X01` (0805,
3,904 in stock) is 350–1120 nm, `VEMD1060X01` (0805, 1,914) is 350–1070, and
`VEMD8081` (5,501) is 4.8 × 2.5 mm, *visible-enhanced*, and 33 pF. The filter is
not a nicety: at Rf = 4M7 the TIA saturates at 617 nA, and open room light on an
unfiltered diode is already that order. So the choice is **build 2 or 5 now and
re-check stock**, or pre-order — the reel MOQ is 3,000.
