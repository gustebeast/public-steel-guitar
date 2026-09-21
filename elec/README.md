# `elec/` — the instrument's six PCBs, from source to a JLCPCB order

Everything here is **generated**. No board was drawn in a GUI, and none should be:
the point is that changing a parameter — the string spacing, the number of strings,
a connector — and re-running produces a new, orderable board with no one having to
open a layout editor and nudge things.

If you are reading this because you want to change something, read
**"What to change, and what regenerates itself"** at the bottom first.

## The six boards

| board | what it is | qty |
|---|---|---|
| `can_tee` | CAN trunk junction, one per motor | 11 |
| `lever_sensor` | MT6701 angle sensor on a pedal/knee lever | 8 |
| `motor_ctrl` | CH32V307 + dual CAN + the 24→5 V supply | 1 |
| `output_panel` | the front panel, both audio conversions, a USB hub | 1 |
| `optical` | 10-string optical pickup: 20 photodiodes, 20 TIAs, USB HS | 1 |

## Two Pythons, and it is not optional

* `py -3.12` runs the **board modules** (`elec/<board>.py`) and `fab.py`. They need
  `skidl` and, for the optical board, `cadquery`.
* KiCad's own Python (`C:\Program Files\KiCad\10.0\bin\python.exe`) runs
  `layout.py`, `route.py` and `verify.py`, because those need `pcbnew`, which ships
  only inside the KiCad install and cannot be pip-installed.

They share nothing but files. A board module writes `<board>.net` and
`<board>.board.json`; everything downstream reads that pair. **This is why
`layout.py` can never `import src/`** — KiCad's Python has no cadquery.

## Running it

```bash
py -3.12 elec/optical.py                      # -> out/optical.{net,board.json}
```

```bash
cd elec/out && "C:/Program Files/KiCad/10.0/bin/python.exe" ../layout.py optical
```

```bash
cd elec/out && "C:/Program Files/KiCad/10.0/bin/python.exe" ../route.py optical
```

```bash
py -3.12 elec/fab.py
```

`fab.py` does the last three checks itself and **refuses to package a board that
fails any of them**: DRC, "is this actually routed", and `verify.py`'s declared
high-speed budgets. It writes `out/fab/<board>.zip` — gerbers, a merged Excellon
drill, and JLCPCB-column BOM and CPL.

`elec/out/` is **not** under version control. Everything in it is a build artifact
and is meant to be reproducible from the board modules; the routed `.kicad_pcb`
especially, because freerouting is non-deterministic and two runs differ.

## What each stage owns

**`<board>.py`** — the design. Parts, nets, footprints, and where each part goes.
For five boards the outline is an *output* of the part list. The optical board is
the exception: its geometry is dictated by the instrument, so it **imports its
placements from `src/optical_pickup.py`** and asserts the two agree part-for-part.

**`layout.py`** — netlist + placement → `.kicad_pcb`. Also does the things a router
should not be asked to do:
* pours the zones (and **builds the connectivity graph first** — without it the
  filler discards every island and a pour silently fills to zero area),
* gives every pad on a plane net **its own via down to the plane**, so a ground
  connection does not depend on pour islands the router will later fragment,
* drops single-pad nets, which cannot be routed and only bloat the search space,
* moves silkscreen to `F.Fab` for parts whose outlines collide by design.

**`route.py`** — Specctra DSN → freerouting → SES → board. Declares `plane_layers`
to the router as `(type power)` so it **stops routing through the ground plane**,
clamps any track it necks below the fab floor, and refills the pours afterwards.

**`verify.py`** — what DRC cannot answer. DRC says "manufacturable"; this says
"correct": matched-length groups, differential pairs staying on the same layers,
via budgets on high-speed nets. Budgets live in `board.json` and each carries a
`why`, because a limit with no stated basis is one someone later relaxes.

**`fab.py`** — the handoff, plus the sourcing gate. A part value that is neither
sourced, nor a generic passive, nor **declared open** fails the build. That exists
because nothing else in the pipeline reads the `value` field, so a stale part number
is invisible right up until the wrong parts arrive.

## What to change, and what regenerates itself

**Change the board module.** Everything downstream follows. In particular:

* **String spacing / count** — change `src/dimensions.py`, then re-run
  `elec/optical.py`. The sensor row, the board outline, the deck-band assertions and
  the conduit clearance are all derived; they will either follow or **fail loudly**.
  A failing assertion here is the system working, not breaking: it means the new
  spacing broke a constraint someone wrote down, and the message says which.
* **A connector or a part** — edit the board module. `fab.py` will stop until the new
  value is sourced or declared.
* **Anything in `elec/out/`** — don't. It is regenerated.

## Known limits — read these before trusting a regenerated board

1. **Freerouting is non-deterministic and does not always converge.** The optical
   board (153 parts) lands around 20 unconnected of ~380; the other five reach zero.
   Pass count is *optimiser* passes: the curve is flat past about 10, and high counts
   can exceed the timeout and produce **no** result. `route.py` now says so rather
   than leaving a board that looks like it failed to connect.
2. **The optical board's twenty summing nodes are routed by the autorouter**, so the
   most performance-critical geometry on the instrument differs between runs and is
   invisible to DRC. Pre-routing them was attempted and abandoned — see the note in
   `optical.py`. If analog performance disappoints, start there.
3. **Rotations are not verified.** The CPL carries KiCad's convention; JLCPCB's
   placement machine wants the LCSC part's, and they differ per part. Check every
   rotation in JLCPCB's previewer before paying. This is the one step that is still
   genuinely manual, and it is a *review* step, not a design one.
4. **Sourcing is open on several parts** — `fab.py` lists them. Two are blocking:
   the USB3343 PHY was out of stock at LCSC, and the STM32H743ZIT6 stock was thin.
