# TRRS routing down the adjustable leg

**Parked 2026-09-16 by the user. UNPARKED 2026-09-17** — the leg↔pedal-bar joint it
waited on now exists (both halves, `src/bar_trrs.py`), so the numbers below are measured
rather than assumed. This is a plan, not a build.

## The problem

The leg is length-adjustable. One continuous TRRS lead runs its whole length — female
(jack) floating at the top joint, male (plug) floating at the bottom — and it has to
survive maximum extension → minimum without being crimped, pinched or dragged. The
user's framing:

> Ideally the TRRS cable could be sized such that the leg can be set to its maximum
> length, then you can adjust the leg down to the minimum length and the TRRS cable will
> cleanly shrink without getting crimped.

---

## What changed once it was measured

### 1. The slack is TWICE what this document assumed

The parked version said the slack "is the full adjustment range". It is not. The
adjustment range is only the **swing**; the **baseline** is surplus bought cable:

| | |
|---|---|
| lead exits the top jack at | z −129.55 |
| lead exits the bottom plug at | z −742.55 |
| end-to-end as modelled | **613.0** |
| adjustment range (30 holes × 5.6) | **162.4** |
| span at max / min extension | 694.2 / 531.8 |
| 10-02135 usable jacket (914 − the two moulded ends) | **874.2** |
| **slack to store at MAX extension** | **180.0** |
| **slack to store at MIN extension** | **342.4** |

So the store must hold **342 mm** and give back 162.4 of it, not hold 162.4. The bought
cable is ~220 longer than the leg's longest path, and that surplus never goes away.

### 2. The cavity that could hold it is Ø24.7, and that caps the bend radius

The slack wants to live in the **adjust sleeve above the adjust tenon's top** — the one
space in the leg whose length grows as the leg extends (tenon withdraws → cavity grows).
Measured clear bore: **Ø24.7**, over 212 mm at the modelled setting.

A Ø3.8 jacketed lead wants ≥3×OD = **11.4 mm bend radius** static. A coil inside Ø24.7
tops out at mean Ø20.9 — **radius 10.4, already 2.7×OD before it stretches**, and
stretching narrows it further. Worked solution for the real numbers: 5.6 turns, Ø20.9
relaxed → **Ø18.0 stretched (2.4×OD)**, spanning 23 → 186 mm. Under the static rule, on
a foil-shielded cable whose shield cracks before the jacket complains.

### 3. A shorter cable makes the coil WORSE, not better

This is the counter-intuitive one and it kills the obvious first move. The coil must
stretch 162.4 whatever its length, and that stretch is shared between its turns. Fewer
turns ⇒ more stretch each ⇒ a tighter helix at full extension:

| lead | turns | Ø stretched | bend radius |
|---|---|---|---|
| ~740 mm (slack 200/40) | 3.2 | 12.2 | **1.6×OD** |
| 914 mm (slack 342/180) | 5.6 | 18.0 | 2.4×OD |
| ~1070 mm (slack 500/338) | 8.1 | 19.5 | 2.6×OD |

So "buy a shorter cable" — the first thing anyone would try, and what I assumed before
computing it — is exactly backwards. **More cable is gentler.** Only the cavity's Ø24.7
caps how gentle it can get, and no cable length beats ~2.7×OD there.

---

## The plan

**Sub-problem A and sub-problem B are independent.** Do A first; it is ordinary work
with a known answer, and B may still change.

### A. Get the lead past the ladder (the blocker that already exists)

`bar_trrs.PASS_TOP` stops the Ø6.6 bore at z −708.15 — **62.4 above the tenon's bottom,
190 short of its top** — because the ladder holes sit on the tenon's centre line and the
signal spine is only 3.2 off it, leaving a 0.30 web at all 31 holes. Above there the
lead has no channel at all. Options, cheapest first:

1. **A corner channel.** The tenon is a 32.3 octagon; its corners are ~16 from centre.
   A channel at a corner clears a centre-line ladder completely, and the lead jogs ~10
   laterally over its length, which a cable does for free. Check the wall to the
   octagon's flat.
2. **Move the ladder off centre.** Cleanest topologically, but the ladder is a load path
   and its owner is `leg_stack`, not this joint.
3. **Run outside the leg.** Rejected on sight — snag risk on a touring instrument.

### B. Store the slack

Ranked by how well they survive the Ø24.7 cap:

1. **A purpose-made CURLY (heat-set) TRRS lead.** The user's own option 2, and the
   measurements promote it from "alternative" to *front runner*: a curly cord's relaxed
   state IS the coil, so it is not a straight cable forced to 2.4×OD — it is a cable
   manufactured at that radius and rated for repeated extension. The entire bend-radius
   objection above only applies to forcing a straight lead. **Open: find one with a real
   datasheet** (the user's caveat, and this project has been bitten twice by unpublished
   numbers — both leg springs still carry a measure-on-arrival step). Needs: 4-conductor
   TRRS, jack-to-plug, retracted ≤ ~60, extended ≥ 200.
2. **Store it where the radius is not capped.** The Ø24.7 is the *sleeve's* bore; the
   slack does not have to be in the leg at all. A loop in the pedal bar's own wiring
   chamber/trough — already built, already lidded, already the place the lead arrives —
   has no Ø24.7 limit. Costs nothing structurally; the question is whether 342 mm of
   bight fits the trough's run.
3. **A wrapping rod (the user's option 1).** Works, but note what the measurements say:
   the rod's job is not to make the coil, it is to stop the coil collapsing. And at
   Ø20.9 mean the rod itself can only be ~Ø13, leaving the lead to do the bending
   anyway. Weakest of the three.

### Decide in this order

1. Does a curly TRRS lead exist with published retracted/extended lengths and a bend
   radius? That answer alone may end B.
2. If not: does 342 mm of bight fit the bar's wiring chamber? Measure before designing.
3. Only if both fail: accept ~2.4×OD in the sleeve and specify a lead whose shield can
   take it (braid, not foil) — which is a BOM change, not a geometry change.

## Still true from the original parking

* **The lead must be CONTINUOUS from the pedal bar to the top joint** (user). Both
  joints are finished and each floats a moulded end of the same cable.
* **The coil is already threaded onto that lead** (`leg_trrs.SPR_ID` 6.6 clears the far
  plug's Ø6.1). Any scheme that changes which moulded end goes where must be re-checked
  against it — that constraint made an earlier version of the joint unbuildable.
* **The tenon's core is spoken for**: the latch pocket owns the −Y middle, which is why
  the spine is off-axis in the first place.
* **A jacketed Ø3.8 lead bends worse than bare leads** — the 90° fold at the top joint
  had to be moved into stripped 28 AWG for exactly this reason.
