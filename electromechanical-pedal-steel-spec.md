# Electro-Mechanical Pedal Steel Guitar — Build Specification & Handoff

**Status:** Design converged; ready for 3D modeling. No physical prototype built yet.
**Audience:** A downstream LLM/agent doing CAD/3D modeling on the user's PC.
**Format note:** Kept in Markdown for clean LLM ingestion.

---

## 0. How to use this document (read first)

You are picking up a design that is *fully specified at the decision level* but *not yet modeled*. Your job is to turn the mechanical concept into CAD parts.

Three things to internalize before you start:

1. **Nothing here is arbitrary.** Each choice traces back to a physical constraint or a hard-won lesson from a prior builder (credited in §13). Before you "simplify" or "optimize" any element, check §13 and §14 — several innocuous-looking features are load-bearing (literally).
2. **The single most important physical principle is the self-locking leadscrew (§3).** It is the reason this design beats the two problems that defeated/limited prior builders. Do not substitute a back-drivable mechanism (ball screw, direct-drive, capstan) for it.
3. **The most actionable sections for you are §4 (per-axis assembly), §5 (the spatial/layout problem), §6–§8 (dimensions and the CAD work list), and §9 (manufacturing constraints).** §10–§13 are context so you understand *why*.

The biggest unsolved geometry problem — the one worth tackling first — is the **belt-offset motor brick in §5**. The user explicitly wants to see whether the belt fan angles and end-box depth actually pencil out.

---

## 1. Project overview & goal

A **pedal steel guitar (PSG)** is a 10-string lap instrument where foot pedals and knee levers change the pitch of individual strings mid-play, letting the player slide one chord into a different chord — something no other instrument does. Traditionally this is done with a purely mechanical maze of rods and bellcranks ("the changer"), and reconfiguring which pedal does what ("the copedent") requires cutting/threading rod and sometimes welding. As a result players rarely experiment.

**This project replaces the mechanical changer with one electric actuator per string**, sensed electronically, so the copedent becomes **software-reconfigurable**. Press a pedal → software looks up what that pedal should do → the relevant strings' actuators move to new positions → pitch changes.

**Design priorities (in order):** fast, precise, reliable — and now additionally **quiet** and **compact** (the instrument should be thin enough to sit on top of a keyboard rig).

**Scope of this handoff:** the mechanical instrument and its actuator system. Electronics and firmware are specified at the architecture level for context but are not the modeling target.

---

## 2. System architecture (big picture)

```
PEDALS / KNEE LEVERS                 MAIN BRAIN                 PER-STRING ACTUATORS (×10)
 (AS5600 angle sensors)  ──────►   Teensy 4.1   ──CAN bus──►   MKS SERVO42D (closed-loop)
                                      │                              │ belt
                                      │                          leadscrew (self-locking)
                                      │                              │
                                      │                          carriage → string ball-end
                                      ▼
                            CALIBRATION ONLY (slow loop):
                            Cycfi Nu Multi hex pickup ─► 16ch mux ─► Teensy ADC
                            (pitch detection recalibrates the position→pitch map;
                             NEVER in the playing signal path)
```

**Two nested control loops:**
- **Inner loop (fast):** Each SERVO42D closes its own position loop on its 14-bit encoder. The playing path is pure feed-forward: pedal position → copedent → target string position. **No pitch detection in the fast path → no playing latency.**
- **Outer loop (slow):** The hex pickup measures actual open-string pitch only when the player presses a "calibrate" button, and corrects the position→pitch map. Drift only ever touches the map; the copedent is fixed config.

---

## 3. The core mechanical principle: the self-locking leadscrew

Each string's pitch is set by where a **carriage** sits along a **fine-pitch trapezoidal leadscrew** (T8×2: 8 mm major diameter, 2 mm lead, **single-start**). A single-start fine screw is **non-back-drivable**: pulling on the nut (i.e., string tension) cannot spin the screw.

**Consequences that the entire design depends on:**
- **Zero holding current.** The motor is *off* at rest and the screw holds the pitch. (Validated empirically by a prior builder — see §13.)
- **Zero standing heat.** Prior servo builds run continuously warm because the motor fights string tension forever; this design doesn't.
- **Zero standing noise.** The only acoustic event is the ~50 ms of an actual move, which is masked by the note already sounding. Quietness becomes a *transient* problem, not a steady-state one.
- **Backlash self-eliminates.** String tension preloads the whole drivetrain in one direction, so gear/nut play never "comes into play."

> ⚠️ **Do not** substitute a ball screw (back-drives), a direct-drive motor, or a capstan/winch (back-drives, and needs continuous holding torque). The self-locking property is the keystone.

**Why a leadscrew/carriage and not a winding capstan:** pitch ∝ √(stretch). A taut string is only ~3 mm of stretch away from open pitch even two octaves down. So the actuator only needs to manage a *small linear translation in the taut regime*, not reel in length. The player removes slack by hand at the far-end tuner so the actuator never deals with the floppy regime.

**Travel budget per axis:**
- Bend range needed: **~3–6 mm** of carriage travel.
- Usable carriage travel to model: **~10–12 mm** (bend range + headroom for "lowers" + fresh-string creep).
- **Open tuning sits partway along the travel**, not at an end. Raises move the carriage one way, lowers the other.
- An **over-travel stop** sits at the extreme low-pitch end as a homing datum / guardrail — *not* the operating rest position.

---

## 4. Per-axis actuator assembly (model this 10×)

Kinematic chain, far end → driven end:

1. **Far-end locking tuner** — player hand-tensions here once to remove slack and set the taut regime. Standard guitar locking tuner.
2. **Roller bridge** — defines the speaking length. **The string anchors to the carriage *behind* the bridge**, so the moving/ noisy parts are outside the vibrating length and string height stays constant as pitch changes. (This is why the changer is *not* the bridge — deliberate, see §13.)
3. **Carriage** — the moving element. It:
   - rides a **guide rod** (anti-rotation: keeps the nut from spinning with the screw),
   - captures the **leadscrew nut** (brass or POM),
   - anchors the **string ball-end**,
   - transmits string tension into the nut → screw → thrust bearing.
4. **Leadscrew (T8×2 single-start)** — parallel to the string pull line, ~60–80 mm long.
5. **Screw support bearings (driven end):**
   - a **radial bearing** to locate the screw,
   - a **thrust bearing** to take the axial string load (the string constantly pulls the screw toward the bridge; the thrust bearing reacts it). **This is new vs. a motor-coupled design** — because the motor is now offset (belt-driven), the screw is no longer cantilevered off the motor and needs its own bearing block.
6. **GT2 pulley on the screw** → **GT2 belt** → **GT2 pulley on the motor**.
7. **Motor: MKS SERVO42D** — sits in the offset "motor brick" (§5), not inline with the string.

**Force / torque sanity check (for sizing brackets, not re-deciding the motor):**
- Max string load at the bridge ≈ 21 lb (~93 N) on the heaviest/lowest string; a balancing spring can cut what the actuator sees to a few lb.
- With a 2 mm-lead screw (~8:1 mechanical advantage class) the motor needs only ~0.01 N·m to drive it — the SERVO42D has *massive* headroom (it's a 48 mm NEMA17). Size the **brackets and bearing blocks** for the full string load, not the motor torque.

**Optional balancing spring (per axis):** a spring opposing string tension reduces the force the actuator handles. **Baseline decision: omit it; use a plain brass/POM nut** (string preload kills backlash anyway). See §14 — this is a deliberate either/or to test, because a balancing spring that *cancels* tension could let net force reverse and reintroduce backlash.

---

## 5. Belt-offset layout & the motor brick ← **KEY PROBLEM TO SOLVE**

### The conflict
- String spacing: **10.5–11 mm** pitch. 10 strings → the screw field is ~99 mm wide (9 gaps × 11 mm).
- The SERVO42D is a **NEMA17 (42.3 mm square)**. It physically cannot sit inline with a string at 11 mm pitch — a single motor spans ~4 string positions.

### Rejected alternatives (do not pursue)
- **4-row inline stagger:** lengthens the instrument by ~20 cm behind the bridge and forces slim back-row screws to route past front motors. Rejected — kills the "thin/short" goal.
- **180° string wrap to underside motors:** friction, tuning drift, wear/squeak at the bend. Rejected.

### Chosen approach: decouple "turn the screw" from "translate the carriage"
The motor only has to *spin* the screw; those two axes need not be collinear.

- **Leadscrews stay inline behind the bridge at the 10.5–11 mm string pitch** (short, ~60–80 mm).
- **Motors relocate into an outboard end-box** ("the brick"), packed at their own ≥42 mm pitch.
- **Short GT2 belts** connect each motor to its screw, fanning from the tight 11 mm screw pitch out to the wide ≥42 mm motor pitch.

**Why belts are safe here (don't second-guess this):** because the screw self-locks and holds the load, the belt only ever carries the brief *move* torque — it never holds string tension. So belt stretch/creep **cannot** affect tuning, and one-directional preload means no belt backlash either. (Cable/belt "feel" objections from traditional builds do not apply to a self-locking, electrically-actuated drivetrain.)

### The geometry you must resolve
This is the open problem. Constraints:
- Screw pulleys: 10 of them on an ~99 mm-wide plane at 11 mm pitch.
- Motor pulleys: 10 of them, motors ≥42 mm wide, so they need ~210 mm of width if in one row of 5 — therefore use **2 stacked layers of 5 motors** (upper/lower), each layer ~210 mm wide.
- **GT2 belts tolerate very little skew** (pulleys for a given belt should be near-coplanar). A large lateral offset between a screw at 11 mm pitch and its motor at 42 mm pitch will skew the belt.

**Recommended solution to model:** *aim each motor at its screw.* Rotate/fan each motor about the vertical so its pulley plane is coplanar with its belt's run to its specific screw. This trades a wider, fan-shaped brick for clean (un-skewed) belt runs. Model it and check:
- the fan angles for the outermost belts,
- the resulting end-box width and depth,
- the longest belt run (keep skew within a few degrees).

If the fan gets too wide, fallbacks: (a) longer belt runs to shrink the skew angle, (b) a small reduction pulley ratio that lets motors spread further, (c) two end-boxes (one per 5 strings) at each end of the instrument.

**Deliverable from you for this section:** a parametric layout of the motor brick + belt routing with the fan angles dimensioned, so the user can judge whether it pencils out before committing.

---

## 6. Key dimensions & specifications (quick reference)

| Parameter | Value | Notes |
|---|---|---|
| Strings | 10 | one independent actuator each |
| String spacing (pitch) | 10.5–11 mm | confirm against chosen roller bridge |
| Carriage travel (usable) | ~10–12 mm | bend range ~3–6 mm + headroom |
| Open tuning position | partway along travel | not at an end stop |
| Leadscrew | T8×2, **single-start**, ~60–80 mm | self-locking — critical |
| Nut | brass or POM | plain (no anti-backlash) baseline |
| Pulleys | GT2, 20T (1:1 baseline) | bore 5 mm (motor), 8 mm (screw) |
| Belt | GT2, 6 mm wide, 2 mm pitch | short runs |
| Motor | MKS SERVO42D (CAN), 48 mm NEMA17 | 42.3 mm sq, 14-bit encoder, 24 V |
| Motor layout | 2 layers × 5, fanned | in outboard end-box |
| Guide rod | 3–4 mm steel | anti-rotation per carriage |
| Build volume limit | 255 × 255 × 255 mm | body must be split + glued |
| Body material | PCTG | non-load structure |
| Load-part material | PA6-GF (glass-filled nylon) | carriage, anchors, bearing blocks |

---

## 7. Bought-component dimensions (model parts *around* these)

Verify all against current vendor datasheets before final fits; these are nominal.

- **MKS SERVO42D + 48 mm NEMA17:** 42.3 mm square faceplate; NEMA17 bolt pattern = 31 mm square, 4× M3, 22 mm center pilot boss. Motor body ~48 mm; **the driver PCB stacks on the rear, add ~20 mm → total length ~68–70 mm.** Output shaft 5 mm dia (often D-cut), ~20–24 mm. Leave clearance at the rear for the board, connectors, and CAN wiring.
- **T8 leadscrew:** 8 mm OD, 2 mm lead, single-start trapezoidal.
- **Leadscrew nut:** brass round/flanged ~10.5 mm OD (or machined POM). Model the carriage pocket to capture it against rotation.
- **GT2 20T pulley:** ~16 mm OD over teeth, ~16 mm overall width with flanges, bore 5 mm or 8 mm, 2× M3 set screws.
- **GT2 belt:** 6 mm wide, ~1.4 mm thick.
- **Thrust bearing:** e.g. F8-16 (8 mm bore × 16 mm OD) washer/cage stack, ~5 mm tall — for the axial string load.
- **Radial bearing:** e.g. 688-2RS (8×16×5) or 608 (8×22×7) — locate the screw.
- **Guide rod:** 3–4 mm dia hardened steel.
- **AS5600 board:** small PCB; pairs with a 6 mm diametric magnet on the moving pedal/lever element.
- **Teensy 4.1:** 61 × 18 mm; built-in CAN controllers (needs an external CAN transceiver).
- **Roller bridge:** select for 10.5–11 mm string spacing; this *sets* the string pitch the screw field must match.

---

## 8. Custom parts to model (the CAD work list)

Priority order roughly matches what unblocks the rest.

1. **Carriage (×10)** — *PA6-GF, load-critical.* Rides the guide rod; captures the leadscrew nut (anti-rotation pocket); anchors the string ball-end (heat-set insert + set screw, or a captured slot). Tension path runs string → carriage → nut. Orient print so tension runs along layer lines, not across them.
2. **Leadscrew bearing block (×10, or a shared rail)** — supports the radial + thrust bearing at each screw's driven end; reacts the full string load. Metal inserts where the bearing seats.
3. **Screw far-end support** — simple radial location for the non-driven end (or integrate into the bridge mount).
4. **Guide-rod mounts / carriage rail** — hold the anti-rotation rods parallel to the screws.
5. **Roller-bridge mount** — holds the bridge at correct height; defines speaking length; provides the behind-the-bridge string anchor geometry.
6. **Motor brick (§5)** — *PCTG.* Holds 10 SERVO42D motors in the fanned 2-layer arrangement; **slotted mounts for belt tensioning**; cable management for CAN daisy-chain. This is the hard one.
7. **Main chassis** — *PCTG, split into ≤255 mm pieces, glued woodworking-style* (dowels/keys for alignment). Houses screw field + bridge; thin profile for the sit-on-keyboard goal.
8. **Outboard end-box** — houses motor brick + electronics tray; PCTG.
9. **Pedal & knee-lever housings** — mount AS5600 sensors + return springs; one analog/I²C sensor per control (~7–8 controls).
10. **Electronics tray** — Teensy 4.1, 24 V→5 V buck, CAN wiring, fuse/switch/inlet.

---

## 9. Manufacturing constraints (read before modeling parts)

- **Printer build volume = 255 × 255 × 255 mm.** The body exceeds this; design it as **multiple pieces joined with glue** (woodworking-style butt/scarf joints), with **dowels or alignment keys** so the screw field stays straight across joints.
- **Materials by role:**
  - **PCTG** — body, brackets, enclosures (dimensionally stable, tough, non-load-critical).
  - **PA6-GF (glass-filled nylon)** — carriage, string anchors, bearing blocks, anything in the sustained tension path. Requires a **hardened nozzle** and a **filament dryer** (assumed already owned).
- **Creep is the enemy.** PCTG/PA creep under sustained load. **Keep printed plastic out of the continuous-tension load path wherever possible** — use metal for the screw, nut, ball-end anchor hardware, fasteners, and bearing races. Printed parts should *hold geometry*, not *carry standing tension*.
- **Print orientation:** route any unavoidable tension **along layer lines**, never pulling across layers (interlayer adhesion is the weak axis).
- **Fastening:** heat-set threaded inserts for screwed joints; set screws to lock string ball-ends and pulleys.
- **Keep the playing portion thin** (sit-on-keyboard goal): bulk lives in the outboard end-box, not under the strings.

---

## 10. Control & electronics architecture (context, not the modeling target)

- **Main brain:** Teensy 4.1. Computes pedal → copedent → target position; sends position commands over **CAN** to the drives.
- **Drives:** 10× MKS SERVO42D, each closing its own position loop on its 14-bit encoder. **CAN daisy-chain** (one bus, minimal wiring — this fixes a prior build's 32-wire harness problem). Multi-drop bus needs a **120 Ω terminator at each physical end**.
- **No DIY PID:** the SERVO42D's loop is handled in its firmware. (Avoiding hand-tuned PID is deliberate — see §13.)
- **Pedal/lever sensing:** AS5600 magnetic angle sensors, one per foot control (~7–8, not 10).
- **Power:** 24 V to the motors (near-zero hold current thanks to the self-locking screw → modest supply, ~10–15 A); 24 V→5 V buck for logic.

**Mapping pipeline (firmware):**
```
pedal travel → (copedent, in semitones) → target PITCH
            → (calibration map, using known √stretch curve anchored by an open-string strum)
            → carriage POSITION → closed-loop motor
```
- Interpolate partial pedal presses **in pitch/cents** (linear-in-pitch), not linear-in-position.
- Always approach a target **from the same direction** so residual backlash is a constant offset the calibration absorbs.
- Store per-string maps in non-volatile memory.

---

## 11. Calibration & software approach (context)

- **Pitch sensing:** Cycfi **Nu Multi** hex pickup (per-string analog outputs) → 16-ch analog mux (CD74HC4067) → Teensy ADC. Because calibration isn't real-time, sequential muxed reads during the ring-out of a strum are sufficient (cheap vs. 10 simultaneous ADCs).
- **Pitch detection:** Cycfi's open-source **Q DSP library** (MIT licensed).
- **When:** calibration runs **only on open strings, only on an explicit player button press.** The bar constantly changes sounding pitch, so non-open notes are ambiguous; open-strings-on-button-press is the one unambiguous condition. At startup the player strums open strings and the system re-anchors the map — no mechanical homing move required, since pitch is the real reference.
- **Pitch is never in the playing signal path** — only the audio pickup is. Pitch detection exists solely to correct the position→pitch map.

---

## 12. Bill of materials

Estimated total **~$1,280** (realistic range **$1,150–1,550**). 3D printer, hardened nozzle, and filament dryer assumed already owned.

| Item | Qty | ~Unit | ~Ext | Notes |
|---|---|---|---|---|
| **Actuation (per-axis ×10)** | | | | |
| MKS SERVO42D (CAN) + 48 mm NEMA17 | 10 | $32 | $320 | board-only + bare motor nets similar |
| GT2 pulley 20T (5 mm & 8 mm bore) | 20 | $2 | $40 | 1:1 baseline |
| GT2 belt (6 mm) + idler/tensioners | — | — | $30 | slotted mounts can replace idlers |
| T8×2 single-start screw + brass/POM nut | 10 | $6 | $60 | self-locking — keystone |
| Radial + thrust bearing (screw support) | 10 | $3 | $30 | thrust takes axial string load |
| Anti-rotation guide rod | 10 | $1.5 | $15 | |
| **Sensing & Control** | | | | |
| Cycfi Nu Multi hex pickup, 10-string custom | 1 | $350 | $350 | **needs live Cycfi quote** + ~$90 custom fee; biggest variable |
| Teensy 4.1 | 1 | $32 | $32 | built-in CAN controllers |
| CAN transceiver + 2×120 Ω term + bus wiring | 1 | $20 | $20 | daisy-chains 10 drives |
| CD74HC4067 16-ch analog mux | 1 | $5 | $5 | sequential calibration read |
| AS5600 sensor + magnet (foot controls) | 8 | $4 | $32 | ~7–8 controls |
| Pedal/lever mechanism (springs, pivots, hw) | — | — | $40 | mostly printed |
| **Power** | | | | |
| 24 V PSU, 10–15 A | 1 | $35 | $35 | modest — near-zero hold current |
| Buck 24→5 V + fuse/switch/inlet/wiring | 1 | $25 | $25 | |
| **Structure & strings** | | | | |
| Roller bridge | 1 | $20 | $20 | string anchors behind it |
| Far-end locking tuners | 10 | $4 | $40 | remove slack / set taut regime |
| Strings (varied gauge) | — | — | $20 | thinner/higher-tension for big excursions |
| Heat-set inserts, set screws, fasteners | — | — | $25 | |
| **Materials** | | | | |
| Filament: PCTG (body) + PA6-GF (load parts) | — | — | $115 | PA6-GF needs hardened nozzle + dryer |
| Misc / consumables | — | — | $30 | |

**Open price variables:** the Nu Multi custom quote (±$100+), SERVO42D seller/kit pricing ($25–40/axis), and filament quantity.

---

## 13. Lessons borrowed from prior builds (rationale & credits)

This design is a deliberate synthesis of two prior efforts on the Maker Forums thread "Building the first Electro-Mechanical Pedal Steel Guitar," plus advice from its engineering contributors. Credits matter because they tell you which features are battle-tested.

- **Self-locking screw → zero holding current/heat/noise.** Eric (@woodslanding) assembled a real motor+screw and found he *could not* back-drive it by pushing on the nut → the device needs no current to hold position. This is empirical, not theoretical. *(The keystone of §3.)*
- **Anchor the string behind a fixed roller bridge.** Keeps motor noise out of the vibrating length and keeps string height constant as pitch changes. *(Why the changer ≠ the bridge, §4.)*
- **Constant one-directional tension makes backlash a non-issue.** Advisor @mcdanlj: the drivetrain is always preloaded one way, so a plain nut is fine. *(Why no anti-backlash nut in the baseline.)*
- **Latency reframed.** A PSG tracks a *continuous pedal gesture*, not a keyboard trigger. ~50 ms/semitone is fine; the string's own response masks it. *(Why "fast" is satisfiable, §1/§3.)*
- **String-gauge strategy.** Use thinner/higher-tension strings on strings needing bigger excursions; keep moves ≤2 semitones. *(Affects which strings travel furthest, §4.)*
- **Avoid DIY PID — it's the failure mode.** Eric stalled permanently on hand-tuning a PID loop for a bare DC motor + encoder. Jacques (@jdebruyn) *completed* a working servo PSG precisely by using sealed closed-loop actuators (RC servos) that needed no PID. **We take Jacques's "no PID" win via the SERVO42D's integrated loop**, then use the self-locking screw to fix Jacques's *two* unsolved problems: servo acoustic noise and continuous holding heat. *(Why integrated closed-loop, §2/§10.)*
- **Software-reconfigurable copedent is proven.** Jacques switches E9↔C6 in ~1 s by redefining servo neutral points in software. *(Validates the whole premise, §1.)*
- **Real mechanical tension change preserves timbre.** A pure-DSP pitch-shifter was proposed and rejected: the bar constantly changes source pitch (hard to track) and DSP loses the timbral change that is the instrument's soul. *(Validates doing real actuation and calibrating on open strings only, §11.)*

---

## 14. Open decisions / things to prototype

1. **Belt fan geometry (§5)** — the main spatial problem. Resolve first.
2. **Spring vs. anti-backlash, per axis** — baseline is *plain nut, no balancing spring*. A balancing spring reduces actuator force but must be re-tuned per string gauge (bounding copedent reconfigurability) and, if it cancels tension enough to reverse net force, would require an anti-backlash nut. Test one axis both ways.
3. **Pulley ratio** — 1:1 baseline; consider a small reduction if you want more resolution/torque at the cost of speed.
4. **Exact carriage travel** — confirm 10–12 mm covers worst-case lowers + fresh-string creep on the heaviest string.
5. **String gauges per copedent** — finalize once the target copedent(s) are chosen.
6. **Future self-calibration** — Jacques's idea of a per-string driver coil that excites then measures a string could enable auto-tuning without a strum. Out of current scope (the Nu pickup is sense-only), but leave room in the electronics bay if you want the option later.

---

## 15. Glossary (PSG terms for the modeler)

- **PSG** — pedal steel guitar.
- **Copedent** — the mapping of which pedal/lever changes which string by how much. The thing this project makes software-defined.
- **Changer / changer finger** — traditional mechanical part that pulls a string to change pitch. Here, replaced by the carriage+screw.
- **Bar** — the metal slide held in the left hand that sets the key; it continuously changes every string's sounding pitch (which is why pitch-based calibration only works on open strings).
- **Raise / lower** — a pedal that increases or decreases a string's pitch.
- **E9 / C6** — the two standard tunings/copedents; switching between them in software is a headline capability.
- **Knee lever** — a lever operated by sideways/forward knee motion, functionally like a pedal.
- **Speaking length** — the vibrating portion of the string, between bridge and bar.
