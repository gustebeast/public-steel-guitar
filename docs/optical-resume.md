# Optical board — where this was left (2026-09-26, resume Monday)

**State: `8cfb6a9`, worktree clean, branch `agent/bronner`. Nothing submitted — the board is
one net short, so the optical commits stay local.**

## The board

| | |
|---|---|
| Unconnected | **1 — `SAI_FS`** |
| DRC violations | **0** unexpected (20 declared sensor-triplet overlaps) |
| `cad_geom_check` | 237/237 |
| Gate | 0 unintended overlaps |
| BOM / MPN | CAD table, netlist and BOM.md agree, 242 parts |
| ULPI skew | 47.93 / 80 · USB_HS pair 0.18 / 8.30 |
| SI (`check_north_si`) | all four pass — summing node 0.834 mm to LED copper, feedback loops 1.20-4.05 mm² of 5.0, In1.Cu thinnest web 0.266 mm with 0 cuts, MID 1460 mΩ |
| Size | 57.21 x 188.53 mm |

`fab.py optical` **correctly refuses to package** while `SAI_FS` is open, and deleted the stale
09-20 zip. Do not override it.

## The one blocker

`SAI_FS` is **FSYNC: U6 pin 3 to pin 23 of all five converters.** Not a peripheral net — no
converter frames data without it, so **all 20 channels are dead until it closes.** This is the
only thing standing between the board and fabrication.

**Verified structural block:** FS (pin 23) and SCK (pin 22) drop from adjacent converter pins
0.5 mm apart and shadow each other. Two sweeps found no reachable via site anywhere on its
spine. West is blocked by SAI_SD5's pad, east by GND copper.

### ⚠ THE TARGET WAS WRONG FOR TWELVE ROUTES (found 2026-09-27)

Every sweep above aimed at a remembered "spine point" near **(12.65, -3.00)**. That point is
not on the spine. `SAI_FS`’s spine is the F.Cu run at **x = 22.50** laid by `_bus_spines`,
running from y +56.02 down to **–18.89**, and that south end sits exactly on `_SD_BORDER`,
where every other bus on this board hands over. The old target is **9.85 mm west of the
copper it was meant to reach** — a path completing there connects the MCU to nothing, which
is exactly what the unconnected count kept truthfully reporting. Chasing it also dragged
searches 16 mm north into the **analog half**, and `SAI_FS` is a digital frame clock: the
north/south split exists to keep it out of there.

**Aim at (22.50, –18.89), and clamp the search south of –18.60.**

### What was tried against the corrected target, and failed

Declaring the path made the board **worse every time** — see [[declared-copper-costs]]:

| declared | unconnected |
|---|---|
| baseline, none (layout’s own `U6.3` escape via) | **1** |
| full 33 mm path on F.Cu | 4 |
| full 33 mm path on B.Cu | 6 (strangled `SAI_SD1`/`SD4`, whose spines share that corridor) |
| 1.2 mm stub + one eastward via | 3 |

All of them produced **0 DRC violations**: they did not short anything, they crowded
neighbours out of their lanes. The monotone trend as the declared copper shrank is the
finding — declaring is itself costly, whatever the geometry.

### ⚠ THE REAL CONSTRAINT, ISOLATED (2026-09-28, six routes)

Two further experiments moved the SPINE rather than declaring copper, and together they
pin the problem down exactly:

| FS lane | SCK lane | FS | SCK | board |
|---|---|---|---|---|
| F.Cu 22.50 | B.Cu 18.30 | **fails** | connects | 1 unconnected (baseline) |
| F.Cu 22.50 + B.Cu 22.50 | B.Cu 18.30 | connects | connects | 6 — two parallel B.Cu spines became a wall |
| B.Cu 18.30 | F.Cu 22.50 | connects | **fails** | 7 — perfectly symmetric swap |

**The F.Cu lane cannot carry this haul.** Whichever of the two sits on B.Cu connects;
whichever sits on F.Cu does not. That is a property of the LANE, not of `SAI_FS` — which
is why a dozen attempts aimed at the net itself went nowhere.

Why: measured on the ROUTED board over the corridor x[-8,24] y[-31,-16], In2.Cu's widest
gap is **0.40 mm** (a 0.25 mm track needs 0.77) between `ULPI_D7` and `SAI_SD3`, F.Cu is
down to **2.38 mm**, and B.Cu holds **1.22-2.65 mm**. An F.Cu spine forces the 29 mm haul
from U6.3 onto the two spent layers; a B.Cu spine puts it on the one with slack.

And B.Cu cannot simply hold both: two parallel spines 4.2 mm apart wall the corridor off,
which is the failure `_spine_keepout`'s own note already records.

**So two nets need one resource and the alternative resource is unusable.** The fix has to
be structural, and the candidates are:
1. ~~**Widen the corridor by placement**~~ — **MEASURED AND RULED OUT.** On the UNROUTED
   board over x[-8,24] y[-31,-16] the tightest cut is **3.14 mm** and most are 5.60 mm,
   and the "parts bounding a tight gap" list is **empty**: no footprint constrains this
   corridor. The parts already leave the room; it is filled by other nets' ROUTED copper.
   Spreading components cannot add capacity where components are not the constraint.
   (`DENS_BOARD=elec/out/optical.unrouted.kicad_pcb ... density.py -8 24 -31 -16 y 0.20`)
2. **Give the F.Cu-lane net a different handover point**, further west, so it never makes
   the full 29 mm crossing.
3. Free In2.Cu in the corridor by re-laning `ULPI_D7` / `SAI_SD3` — they bound the
   0.40 mm gap six cuts running. Note these are TRACKS, so the lever is their spine/lane
   assignment, not a part move.
4. ~~**Re-map the MCU pin**~~ — **RULED OUT.** `SAI_FS` must be a **SAI1 block A** pin,
   because SAI2/SAI3 run as synchronous slaves taking block A's clocks internally (see the
   pin-map note), and `SAI1_FS_A` is PE4. The only alternative is making block B the master,
   moving FS/SCK to **PF8/PF9 = pins 26/27** — the SAME package face as PE4/PE5 (pins 3/4)
   and 11.5 mm FURTHER SOUTH along it, i.e. further from the spine. The haul gets longer.
5. ~~**Permute the SD lane → converter assignment**~~ — **RULED OUT.** Solved exhaustively
   over all 120 permutations: the optimum saves **0.7 mm of 273.5 mm**. The converters are a
   north-south column at x 11.65 and every lane pin sits on the MCU's west face, so the
   assignment is nearly irrelevant.

### Where that leaves it

Every cheap lever is measured out. What remains is a **design decision, not a search**, and
should not be taken unsupervised:

* **Move the PHY (U7) or re-think what crosses this corridor.** The real quantity to reduce
  is the NUMBER of nets crossing, and the ULPI bus (12 nets) is most of them. USB_HS skew
  has huge margin (0.18 of 8.30), so the PHY is not pinned by that.
* **Accept 1 unconnected and hand-route `SAI_FS` in KiCad**, then keep it as declared copper
  measured from the FINISHED board rather than the unrouted one. Every declared path tried
  so far was measured against the unrouted board, which is why each one fitted and then
  strangled its neighbours.
* **Widen the board.** Rejected so far on cost, and it is the one thing that genuinely adds
  the missing capacity.

**Do NOT** declare the path, add a second B.Cu spine, or swap the lanes again. All three
are measured and all three are worse.

**The (via site, waypoint) joint search** — the technique that closed ULPI_D0 — was never
run to completion against the *corrected* target. It prints only after all 40 rings, so
redirect it to a file and **never pipe it through `tail`** (that buffers until exit and
already threw away one full run’s answer):

```
"/c/Program Files/KiCad/10.0/bin/python.exe" -u scratchpad/joint_search_v.py SAI_FS -6.55 -27.31 22.50 -18.89 > out.txt
```

## Hard-won process rules — re-read before touching anything

- **`elec/finish.py` must be launched with the KiCad python** (`/c/Program Files/KiCad/10.0/bin/python.exe`).
  It uses `sys.executable` for its children, so `py -3.12` fails at `import pcbnew`.
- **Never wrap a route in `timeout 900`.** A route is ~30 min; 900 s kills it at pass 9.
- **Keep 10 passes.** Never raise to 50 — a board that needs 50 is a bad design brute-forced.
- **Never write to `elec/out/` while a route is running** — `route.py` copies after freerouting,
  so the file becomes the SES import baseline (cost: 94 shorts, ~33 min).
- **Run `finish.py`, not the stages.** Hand-calling layout/route/_drc skips `export_geom` and the
  CAD then renders a stale board.
- Always `set -o pipefail`, and verify the **artefact** (`elec/out/optical.board.json`), not the log.
- Declared copper is laid with **no clearance check** — measure any pre-laid run into a
  verified-empty lane first, and verify **from the via layout will actually place**, not from the pad.
- Escape vias are settled: `U6.3, U7.5, U7.11, U7.16, U6.38, U6.45` earn their place;
  `U7.4, U7.9, U18.18` do **not** — do not re-add. Any new one goes in **one at a time**.

## When it closes

`opt_audit` → SI groups → `cad_geom_check optical` → `scratch_view --gate` → render and copy
`scratch.step` over `assembly.step` (the user reads the FreeCAD tab, not the commit) → commit →
`agent_sync submit`.

## Then, and only then

`docs/optical-bringup-diagnostics.md` — the debug work list. Items 1-5 are one change and touch
neither the analog region nor the converter fan. **Item 6 waits for a clean baseline**, because it
routes through the same fan as `SAI_FS`.

## Unrelated loose end

`optalt` and `usb_panel` have **21 orphaned files in `elec/out`** with no generator. `fab.py`
flags them every run. Left alone deliberately during a validation pass; they want deleting.
