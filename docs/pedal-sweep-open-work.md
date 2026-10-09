# Pedal bar — parked work, 2026-09-24

Parked mid-investigation so it can be picked up cold. Nothing here is fixed yet;
the geometry is exactly as it was found.

## Resume in one command

```bash
py -3.12 -m cadkit.tools.agent_sync scope --set src.build --attr pedal_bar_work_components
```

Then `py -3.12 -m tools.scratch_view` (the 263 live parts rebuilt, the rest from the
lead's last build). A warm `--gate` cycle is 76 s, ~44 s of which is
`import src.build`.

## What the user asked for

1. The pedal must sweep **5° up from rest** and **down as far as it takes to reach
   the floor** — the floor being the bottom of the TPU feet, z **−813.75**.
2. An **installation path for the feel cartridges cut from −Z**.

Neither is done.

## What was measured (posed, world coordinates, pedal 0)

`swing(+θ)` presses the pedal DOWN: the arm tip descends monotonically,
−758.95 → −775.31 (+10°) → −791.37 (+20°) → −801.43 (+26.5°). Rest is +0°.

| swing | lowest point above floor | intersection with `pedal_bar_a` |
|-------|--------------------------|---------------------------------|
| −5° (up) | — | 238 mm³ |
| rest | 41.20 | 109 mm³ ← baseline, designed |
| +10° | 25.05 | 122 mm³ |
| +15° | 17.21 | 217 mm³ |
| **+20°** (`THROW_P`, its own rated throw) | 9.60 | **550 mm³** |
| +26.5° (touches the floor) | 0.15 | 1073 mm³ |

Two things fall out of that table:

* **The pedal fouls the bar at its own rated throw, today.** 440 mm³ past the
  rest baseline at +20°, before anything the user asked for is attempted. The
  overlap gate cannot see it — it only ever poses parts at rest, where this is
  clean.
* **Full throw stops 9.6 mm short of the floor.** Touching it needs ≈ +26.5°.

## The open question — which way does `lever_room()` sweep?

`foot_pedal.lever_room()` exists to carve exactly this envelope, and its comment
records this same bug being found and fixed once already ("the room was carved out
of the half of the arc the arm never visits"). It sweeps `swing(env, -i)` for
`i in 0..THROW_P`, i.e. NEGATIVE angles. The measurements above say the pedal
presses at POSITIVE ones.

So either that fix went in with the sign inverted, or `_lever_envelope()` is
authored in a frame that differs from `_lever()`'s. **Settle which before touching
it** — flipping a sign and re-measuring would probably look right for the wrong
reason, and this is the second time the sign has been in question. The empirical
shape of the fouling (clear to ≈ +10°, then growing fast) does not match a
straightforward "carved on the wrong side", which would foul from a degree or two.

## Then

Widen the carved range to **−5° … +26.5°** and make sure it comes out of the BAR
piece as well as the housing — `lever_room`'s docstring notes the arm swings past
the housing's floor into the bar's top −Y corner, which is how 111 mm³ survived
the last fix.

`THROW_P` and `LOBE_RC_P` need not change for any of this. The 20° working throw
and its feel tuning stand; the requirement is clearance, not travel.

## Spring budget, for when the throw itself comes up

Asked whether 20° is a spring-travel limit. It is not:

* uxcell blue die spring, 30 free, **12.0 mm max deflection** (40 %, JIS — "never exceed")
* tension-screw preload range `HS_TEN_ADV` = **4.8**
* stroke at the lobe, 20°: 13.2·sin20° = **4.51**
* worst case today = 4.8 + 4.51 = **9.31 of 12 (78 %)** — inside the 80 % long-life band, 2.7 mm spare

At 26.5° the stroke becomes 5.89, so full preload would be 10.69 of 12 (**89 %**) —
past the long-life band though short of the limit. Staying at 80 % would cap
preload at 3.71, costing the **top ~23 % of the tension range**, not all of it.

## Also found, untouched

`check_ceilings` on the bar (these are pre-existing, and none is mine):

* `pedal_bar_c` — **1405.6 mm² bridging a 36.4 mm span, 7.4 mm off the bed**. The
  largest unsupported ceiling anywhere in the model.
* 170.4 mm², span 6.0, at the bar ends (`pedal_bar_a` and `_c`, the same feature)
* 82.7 mm², span 7.45 — one per pedal station, five in all
* 26.6 mm², span 5.63, **1.6 mm from the bed** — bridging at about layer two

`check_beads` reports nothing in `pedal_bar.py`. The overlap gate is clean at rest.

`tools/check_sweep.py` cannot check any of this: its `ROTATING`/`envelope()` model
only handles rotation about VERTICAL axes, and a pedal turns about a horizontal
axle. The table above came from a throwaway probe. Folding a horizontal-axle case
into that tool would have caught the +20° fouling on its own.
