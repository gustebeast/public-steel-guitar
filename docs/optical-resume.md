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

**In flight when this stopped:** a joint search over (via site, waypoint) — the technique that
closed ULPI_D0, and the thing that distinguishes it is that earlier FS sweeps used a *fixed*
MCU-side via, so they never ruled out a joint solution. Re-run it:

```
"/c/Program Files/KiCad/10.0/bin/python.exe" -u scratchpad/joint_search.py SAI_FS -6.55 -27.31 12.65 -3.00
```

(pad U6.3 at `-6.55,-27.31`; target spine point `12.65,-3.00`.) **Do not pipe it through
`tail`** — that buffers until exit and threw away one full run's answer.

**Fallback if the joint search comes back empty:** a placement change to the converter cell fan.
That is the remaining lever, and per [[placement-not-router]] it is the *right* lever — not more
passes, not more layers.

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
