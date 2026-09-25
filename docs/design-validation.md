# Behaviour validation pass

**2026-09-23, lead.** Written to be checked, not believed. Every number below
either comes from the source (file and line named) or from arithmetic shown in
full, so you can disagree with the inputs.

The design has been validated part-by-part for a long time: overlaps, sweeps,
walls, ceilings, beads. This asks a different question — *can the finished
instrument DO the things a pedal steel has to do?* — and it finds gaps that
per-part checking is structurally unable to see.

Nothing here is fixed. This is a list.

---

## The behaviours

| # | The instrument must be able to… | Verdict |
|---|---|---|
| B1 | Move any string to a commanded pitch, over the whole copedent's range | **Holds, on one unverified constant** |
| B2 | Hold that pitch with the motors unpowered | **Holds, with thinner margin than stated** |
| B3 | Store a copedent and per-string calibration, and survive a power cycle | **Not designed yet** |
| B4 | Read every pedal and knee lever | **Holds; the COUNT disagrees across three files** |
| B5 | Have its strings installed, tuned and replaced | **Holds by design; never walked end to end** |
| B6 | Turn string motion into sound | **Holds** |
| B7 | Power everything from one inlet | **Holds after the 2×22 AWG fix; one open item** |
| B8 | Come apart completely, with one hex key, no glue | **Unverifiable today — no checker covers tool access** |
| B9 | Be printable on the target machine | **43 of 67 prints are unchecked** |
| B10 | Fold down and travel | **Holds** |
| B11 | Know where each carriage IS at power-up | **Not designed yet — firmware soft limits + a reference story** |
| B12 | Fail safely (string break, stall, power loss mid-move) | **Not analysed** |

---

## B1 — reach every pitch the copedent asks for

**The travel budget is 8.35 mm** (`CARRIAGE_TRAVEL`, `src/dimensions.py:159-177`),
and it is three terms:

| Term | mm | For |
|---|---|---|
| `DL_OPEN` | 4.00 | slack → open pitch take-up when the string goes on |
| bend | 2.35 | four semitones up, `DL_OPEN·(2^(4/6) − 1)` |
| margin | 2.00 | new-string break-in |

The nut's top face runs from **−7.2** at the top of travel down to **−15.55**;
the nut body reaches −30.55 at the bottom. All of it rests on one global
constant, `DL_OPEN`, the stretch beyond slack at open pitch.

### The sequence the budget actually has to cover (user, 2026-09-23)

Nuts are driven to the **top** of travel; the string is threaded and **hand-tightened
at the keyhead** — around the Ø8 wrap rod, ~3 turns, then clamped
(`src/nut_block.py`). The carriage is then pulled **down** to reach open pitch, and
**down further** for any raise. Down = more tension: the nut descending lengthens the
dead run off the bridge bearing.

Two things follow, and they change which strings are at risk.

**The hand sets the slack, and nothing else can.** The wrap rod does not rotate —
it is the bridge axle's own shaft SKU, shared and fixed — so there is no tuner and no
winding action. You pull, you wrap, you clamp. Whatever tension the player failed to
reach by hand, the carriage must make up out of its 8.35 mm, on top of the raise.
Take-up needed is `DL·(1 − T_hand/T_open)`, so a firm pull costs travel and a weak
pull costs more.

**The +4 case is the cheapest one, not the dearest.** Stretch scales with pitch, so
string 10 — the only string the copedent can drive +4 (P1 +2 and P2 +2 together) —
has the *smallest* ΔL in the set. It needs about 1.2 mm of the 8.35 even at +4. The
+4 question the design has been sized around is not where the risk is.

**Where the risk is:** the fattest-sounding, lowest-pitched *wound* strings that are
still high enough in pitch to stretch a lot — 5 (G3, .024) and 6 (E3, .030). How hard
the player must pull, as a fraction of final string tension, for the carriage to still
reach open pitch plus that string's copedent raise:

| Str | Note | Gauge | Raise | core 0.30 | core 0.35 | core 0.42 | core 0.50 |
|---|---|---|---|---|---|---|---|
| 1–4 | D4–A3 | plain | +1…+3 | **0%** | 0% | 0% | 0% |
| **5** | G3 | .024 | +0 | **49%** | **32%** | 3% | 0% |
| **6** | E3 | .030 | +1 | **41%** | **16%** | 0% | 0% |
| 7 | C3 | .036 | +2 | 12% | 0% | 0% | 0% |
| 8–10 | A2–C2 | .042–.070 | +0…+4 | 0% | 0% | 0% | 0% |

*"core 0.35" = core wire 35% of outside diameter. 0% means the string can be left
barely taut and the carriage still gets there.*

**All four plain strings are fine under every assumption** — plain-string stretch
depends only on pitch and scale length, not on gauge (the diameter cancels in
`ΔL = T·L/(E·A)`), and the worst of them, string 2 at E4, comes to 3.97 mm. That is
almost exactly the modelled `DL_OPEN = 4.0`, which strongly suggests the constant was
derived from the highest plain string — and that wound strings, whose thin cores carry
the tension for a much heavier string, were never in the picture.

So the open question is narrow and concrete: **are strings 5 and 6 plain or wound, and
if wound, how thick is the core?** If .024 is plain (common in C6 sets), the whole
concern evaporates. If they are wound on thin cores, the player has to pull a third to
a half of final tension by hand, one-handed, while managing three wraps — which is the
thing the user has said cannot be relied on.

**There is recoverable travel if the measurement demands it**, which de-risks this: the
nut clears the ledge lip by 1.45 mm and the thrust bearing by 3.05 at the bottom, and
`NUT_TOP_Z` could rise ~3.8 mm before the screw top reaches the bridge bearing's 1.0 mm
keep-out. That is roughly **4 mm of travel** available inside the existing architecture
— enough to cover a doubling of the worst ΔL — at the cost of re-checking the changer
ceiling, the access channels and the asserts that currently bound both ends.

**The copedent's worst case is +4 semitones, and `PITCH_UP_ST` is exactly 4.**
String 10 takes +2 from P1 and +2 from P2; press both and the moves sum, because
with one motor per string nothing stops them summing. So the design assumption
and the requirement meet with **zero headroom**. A future copedent edit stacking
a third raise on one string silently exceeds the travel, and no check would catch
it: `PITCH_UP_ST` is a hand-set constant in `dimensions.py`, the copedent lives
in `tools/export_rig.py:66` (a *viewer exporter*), and the two are never compared.

### Sized against REAL string sets, both tunings (2026-09-23)

The requirement is any standard E9 or C6 setup, so the gauges below are the published
ones (S.I.T. Strings' pedal-steel gauge chart), not remembered ones, and the notes are
the standard assignments.

**E9 puts its highest string on string 3, not string 1** (user) — G#4 on an .011, the
thinnest in the set. Since plain-string stretch depends only on pitch, *that* is the
binding string for the whole instrument, in either tuning:

| | Note | Gauge | ΔL (mm) | T at pitch | Hand pull for +1 / +2 / +4 |
|---|---|---|---|---|---|
| **E9 str 3** | **G#4** | **.011p** | **6.30** | 126 N | **1.5 / 3.2 / 7.4 kgf** |
| E9 str 1 | F#4 | .012p | 5.00 | 119 N | none / none / 3.8 kgf |
| C6 str 5 | G3 | **.024w** | 4.71 | 112 N | none / none / 2.7 kgf |
| C6 str 2 | E4 | .014p | 3.97 | 128 N | none / none / none |
| C6 str 1 | D4 | .017p | 3.15 | 150 N | none / none / none |

*(A tension check caught a mis-pairing on the way: S.I.T.'s C6 chart gives string 1 as
.017, which at G4 would be 267 N — far too high. It belongs to the **D4-top** C6
variant, which is the one this project already models.)*

**The .024 IS wound** — S.I.T. lists it as `.024W` — which settles the question left
open above. But a thin wound string has a proportionally *fat* core (~0.5 of outside
diameter, versus ~0.3 on a .068), so its ΔL lands near 4.7 mm rather than the 9–14 mm
the thin-core assumption produced. C6 is comfortable. E9's .011 is not.

**Core diameter cannot be designed against precisely: string makers treat it as a
trade secret**, and it varies by brand (Steel Guitar Forum, "Core gauge of wound
strings" — players there note the same core variation changes changer travel on
*conventional* steels too, so this is a known real-world effect, not an artefact of
this design).

**What the numbers say.** With 2.0 mm reserved for break-in, E9's string 3 needs a
1.5 kgf hand pull for its standard +1 (pedal B, G#→A) — fine — but 7.4 kgf for a
hypothetical +4, which is not achievable bare-handed on an .011. No standard copedent
asks for that. Note also that the .011 is the string that breaks most often on E9, so
it is restrung most and is simultaneously the fussiest to tension.

**Spending the break-in reserve instead of reserving it removes almost all of it.**
Install, let the string take its set, re-clamp — and +1 and +2 are free on every string
in both tunings; only the hypothetical +4 on E9 string 3 still wants 3.4 kgf. That is
an ordinary stringing habit, and it converts a mechanism margin into a procedure step.

**`DL_OPEN` is one number for ten very different strings, and the comment above
it says so** — *"Varies with gauge → size for the largest in the set."* It was
never sized that way. Worked out per string (T = μ·(2fL)², ΔL = T·L/(E·A_core),
L = 615 mm, E = 200 GPa, C6 gauges and open notes from `export_rig.py`):

| Str | Note | Gauge | ΔL at open (mm) | Copedent span (mm) | Travel needed (mm) |
|---|---|---|---|---|---|
| 1 | D4 | .015 plain | 3.15 | 0.39 | 3.54 |
| 2 | E4 | .014 plain | 3.97 | 0.92 | 4.89 |
| 3 | C4 | .017 plain | 2.50 | 1.31 | 3.81 |
| 4 | A3 | .020 plain | 1.77 | 0.92 | 2.69 |
| **5** | **G3** | **.024 wound** | **6.54** | **0.71** | **7.26** |
| 6 | E3 | .030 wound | 4.63 | 1.07 | 5.70 |
| 7 | C3 | .036 wound | 2.92 | 0.76 | 3.67 |
| 8 | A2 | .042 wound | 2.06 | 0.22 | 2.29 |
| 9 | F2 | .054 wound | 1.30 | 0.30 | 1.60 |
| 10 | C2 | .070 wound | 0.73 | 0.64 | 1.37 |

Against 8.35 mm of travel, the worst string needs an estimated **7.26 mm**. It
fits, but it eats the 2.0 mm break-in margin down to about 1.1 mm, and the
modelled 4.0 is neither the largest value (6.54) nor a typical one.

**Treat the wound-string numbers as indicative, not settled.** They depend on a
core fraction I assumed (0.42 of outside diameter) and on where the plain/wound
boundary falls — .024 could be either, and if string 5 is plain its ΔL drops to
about 1.4 mm and the worry disappears. That sensitivity is itself the finding:
**the travel budget turns on a string-construction detail nobody has measured.**
`dimensions.py` already prescribes the experiment — *"measure: anchor travel from
barely-taut to pitch"* — on the real set, per string. It is a ruler-and-an-
afternoon test that either retires this or changes the mechanism.

Note the shape of the table: **ΔL is largest on the high strings and smallest on
the low ones.** That inverts the usual intuition, and it drives B11.

## B2 — hold pitch unpowered

The README's claim that "the motors are completely unpowered at rest" rests
entirely on the Tr8×2 screw being self-locking. That is a friction argument, so:
mean diameter 7.0 mm, lead 2 mm, lead angle **5.20°**; thread half-angle 15°, so
self-locking needs **μ ≥ tan(5.20°)·cos(15°) = 0.088**.

- Dry steel on bronze, μ ≈ 0.15–0.25 → locked, 1.7–2.8× margin.
- Greased, μ ≈ 0.10–0.15 → locked, 1.1–1.7× margin.
- PTFE-loaded or oiled, μ ≈ 0.08 → **not locked.**

The instrument therefore holds tune *because of what is not on the screw*.
Nothing in `BOM.md` or `INSTALL_NOTES.md` says "do not lubricate these screws",
and the BOM states "self-locking" as a property of the part. It is a property of
the assembly. Worth one line in the install notes.

## B3 — set and save the copedent

**There is no firmware, controller code or configuration format in this
repository.** No `.c`, `.cpp`, `.ino`, no firmware directory. The behaviours the
instrument exists for — command a pitch, store an offset, map a lever to a set of
string moves — are all software, and none of it is written.

The copedent exists in exactly one place: a Python dict in
`tools/export_rig.py:66`, whose job is feeding the web viewer's animation. It is
not a data file, and nothing but the viewer can read it.

This is not a complaint about sequencing — CAD first is reasonable. It matters
because **decisions that are cheap now get expensive once boards are ordered**:
where calibration lives, what the MCU keeps in flash versus what the Pi owns,
and B11 below.

## B4 — read every control

The sensing chain is sound: a diametric Ø6 magnet on the axle end, an MT6701
reading across a **1.5 mm** air gap against a datasheet window of 0.5 / 1.0 / 2.0
min/typ/max (`src/knee_lever.py:88-130`), absolute over 360° where the lever
sweeps ~30°. No issue.

**The number of controls disagrees across the repo:**

| Source | Says |
|---|---|
| `BOM.md:857` (power budget, corrected 2026-09-18) | **11** sensor boards — "6 knee levers + 5 pedals" |
| `BOM.md:560` (angle-sensor row) | **11** MT6701 |
| `tools/export_rig.py:66` | **10** controls — 5 pedals, 5 levers (ILKL removed 2026-09-11) |
| `docs/rig.json`, every build | **10** controls |
| `src/build.py:832` | "The copedent needs six (user): ILKL, LKL, VKL, LKR, RKL, RKR" |

ILKL left the copedent on 2026-09-11; the BOM's sensor count was corrected
*upward* to 11 a week later, on 2026-09-18, citing six levers. One of those is
stale. If the instrument really has five levers, the BOM over-buys one sensor
board, one MT6701 and a connector set — trivial in money, but it means **the
board quantity and the control list have no single source of truth**, and the
same ambiguity reaches the firmware as "how many nodes on bus B".

## B5 — string install, tune, replace

Well handled, and the awkward case is explicitly designed for: strings whose
channel is blocked by a leg get no channel at all and thread in from +X through
the changer room's open face, with the leg slid out first
(`src/bridge_endplate.py:91`, `legs.SERVICE_SLIDE`). The ball end anchors under
the H-nut's +X ear, reachable through the same opening.

No finding, with one caveat: the procedure has never been walked end to end —
thread, seat the ball, take up slack, reach pitch, trim — and `INSTALL_NOTES.md`
holds a single entry (KL-1, thread-lock the position screws). Restringing is the
most repeated task on a steel guitar.

## B6 — make sound

Magnetic pickup and per-string optical pickup both land on the output + panel
board; ADC, DAC, hub, true-bypass relay and buffers were rewired from the makers'
datasheets on 2026-09-21, 0 unconnected nets and 0 DRC errors. The pickup sees a
1 MΩ load, flagged in the BOM as the tone-setting choice. Nothing to add.

## B7 — one power inlet

The 24 V trunk analysis in `BOM.md:750-870` is the most rigorous work in the
repo: the 2×22 AWG doubling fixes gauge, contact rating and voltage drop at once,
and the XH/PH split keeps the high-current bus on XH. Bus B's 105 mA at 24 V
against PH's 2 A rating is 5%. The open item is the fleet slew budget — "<5 A"
assumes the ten motors never draw peak together, which is a **firmware**
guarantee (B3), not a hardware one.

## B8 — come apart, one key, no glue

The fastener family is disciplined: M4 button heads, 2.5 mm hex, called out as
"THE ONE DRIVER" (`BOM.md:2379`), heat-set inserts rather than tapped plastic,
and cadkit's ScrewJoint renders screw and insert so the gate can see them.

**But no checker covers tool access.** The overlap gate proves parts do not
intersect at rest; the sweep gate proves rotating parts clear through a turn;
`check_ceilings` proves overhangs print. Nothing proves a 2.5 mm key can reach a
screw head, that it has swing room, or that a part can travel out along its
install axis without fouling a neighbour — the nearest thing is the THT-connector
install sweep, which covers connector tails only. Every "it comes apart" claim in
this project is currently a human eyeballing the viewer.

Related: `INSTALL_NOTES.md` KL-1 specifies **thread-lock** on the knee lever's
position screws. Blue threadlocker is removable, so parts still separate, but it
sits close enough to the no-glue rule to deserve an explicit ruling.

## B9 — printability

`tools/check_ceilings` covers **25 of 67** prints. Two more declare a diagonal
build direction it cannot handle (`adjust_tenon`, `fixed_tenon`). **43 have never
declared a print orientation at all**, so nothing checks their overhangs —
including the three largest parts in the instrument:

> `chassis_0`, `chassis_1`, `chassis_2` (and their `_light` variants),
> `knee_housing`, `knee_lever`, `kv_housing`, `kv_lever`, `cart_base`,
> `cart_piston`, `pedal_lever`, `pedal_lid_a/b`, `leg_foot`, `motor_pulley`,
> `screw_pulley_hi/lo`, `tension_fork`, `coil_mandrel*`, the test coupons, and
> every `top_plate_*_color` inlay.

The declaration is one vector per part, read by the checker from the part's own
source, so this is bookkeeping rather than analysis. It is also the cheapest
coverage win available: the checker found a real defect the moment its coverage
went from 5 parts to 25 — a cradle fused to nothing, printing in two pieces.

## B10 — fold down and travel

Legs blind-mate on pogo boards on the tenon diagonal with ScrewJoint retention
and no flat ceilings on either tenon; the harness runs in an octagonal section
with a volume-checked fuse per segment. Sound.

## B11 — know where the carriage is at power-up

**The largest undesigned behaviour, and a consequence of B1's table.**

There is **no homing reference, no limit switch, no index mark and no hard stop**
anywhere in the string drivetrain. `src/bridge_endplate.py:666-670` says the
guide rod's upper retention and **both** travel stops are deferred ("user: ignore
stops for now"); the rod top "rides free in the open field". Meanwhile
`src/build.py:437` poses four strings "feet on the bottom stop" — a stop that
does not exist in the geometry.

Three consequences:

1. **Nothing bounds a commanded move in software** — but the mechanism is far
   more forgiving about it than this document first claimed, and the correction
   is worth keeping. ~~A miscommanded move a few millimetres long runs the nut
   off the end of its screw.~~ **Wrong** (user, 2026-09-23). The nut is **15.0 mm**
   tall and `SCREW_RUNOUT` stands the screw 2.4 mm *above* the nut's top face at
   the top of travel, so it is 100% engaged there; over-travel only shortens
   engagement from the top, gradually. Full disengagement needs **17.4 mm of
   over-travel, 2.08× the entire travel**; 4 mm of over-travel still leaves 89%
   engagement and a whole extra travel's worth leaves 60%. And the nut's ears
   reach the changer-room ceiling **4.0 mm** above the top of travel
   (`CHANGER_CEIL_Z`), so a runaway stalls against structure — which a
   closed-loop driver reports — long before thread engagement is interesting.
   Downward there is 11.95 mm of screw below the nut at the bottom of travel.
   So the real requirement is a firmware one: **soft limits that refuse to
   command the nut above or below its travel** (user: to be built with the
   firmware). There is no mechanical stop to catch a bad command, only structure
   to crash into.
2. **Position after power-up is a stored number, not a measurement.** The screw
   being non-backdrivable (B2) means the carriage cannot drift while the
   instrument is off, which is what makes a stored count plausible at all. But
   any event that breaks the stored-to-actual correspondence — a snapped string,
   a screw turned by hand during service, a flash write interrupted mid-move —
   leaves the controller confidently wrong with no way to detect it.
3. **The error is worst where it is least expected.** From B1's table, ΔL is
   smallest on the low strings, so position error becomes pitch error fastest
   there: at 0.01 mm of error, string 10 is out by roughly **12 cents** and
   string 5 by about **1.3**. The bass strings hold the tight tolerance, not the
   treble.

The instrument does have a way out that a mechanical steel does not: the optical
pickup measures per-string pitch directly, so the machine can hear where it
actually is and re-reference itself. That closes the loop — but it is firmware
(B3), it needs a defined startup behaviour, and it wants a mechanical stop as a
backstop against runaway regardless.

## B12 — failure modes

Not analysed anywhere in the repo, and worth a pass before boards are ordered:

- **String break.** ~150 N released instantly. Where does the energy go, what
  does the carriage do, and does the controller notice the pitch has gone?
- **Stall or jam.** The SERVO42D closes its own loop and reports following error;
  nothing says what the system does with that.
- **Power loss mid-move.** Self-locking holds position; the stored count is
  mid-write. Exactly the case that de-syncs B11.
- **Thermal.** Ten steppers, a Pi and a buck in a closed PETG-GF box, motors
  unpowered at rest — likely fine, never checked.

---

## Suggested order

1. **Measure ΔL per string on the real set** (B1). Cheapest test here, and it
   either retires the travel worry or moves the mechanism.
2. **Declare print orientations for the 43** (B9). Bookkeeping; unblocks a
   checker that has already earned its keep.
3. **Reconcile the control count** (B4). One number, three files.
4. **Decide the startup and reference story** (B11 + B3) before boards are
   ordered. Soft travel limits are a firmware requirement the user has already
   accepted; the open part is how a carriage re-references itself after the
   stored count and the real position disagree.
5. **A tool-access check** (B8), so "it comes apart" stops being an opinion.
