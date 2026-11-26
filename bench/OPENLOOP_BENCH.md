# Open-loop bench: TMC2209 + CH32V203 on one string

The plan (user, 2026-11-24): a raw NEMA 17 on each string, driven by 10x TMC2209 on the connector
board, with one CH32V203 making the step pulses. No encoder and no motor-side hardware. This bench
answers the questions the datasheets can't, before any layout. The QT Py's firmware is
`firmware/qtpy_bench` (its README has the wiring, flashing and commands), and the Pi drives it with
`publicbench.qtpy`. Gate 1 (i)-(v) runs as `python3 -m publicbench.gates i|ii|iii|iv|v|all`
(add `--truth servo42d` for the encoder's ground truth, and `--fullsteps 200` for a 1.8 deg motor);
its module docstring has the details. Every run is logged to `~/openloop_tmc.jsonl`.

**The motor (user, 2026-11-25): the Leadshine 42CM06 from JLCMC is the official motor.** It is
1.8 deg, so the scripts' default `--fullsteps 200` fits. The SERVO42D stays only as the stand-in on
the user's own instrument, and as this bench's encoder. The 0.9 deg 17HM19 is dropped: 91 in
stock, about 1.2x torque margin at 1600 rpm on the model, and twice the step rate.
**A tune is recommended after every boot** (user, 2026-11-25), so gate 1's restore has to land
within the tuner's reach, not exactly; gate 1 still says how far off a boot starts.

## Kit (the user orders; nothing has been bought)

| Part | Where | Price | Note |
|---|---|---|---|
| TMC2209 SilentStepStick | Digi-Key `TMC2209SILENTSTEPSTICK` | $15.44 | StepStick pinout, sense resistors on board. Option 2: `TMC2209-BOB` $30.47 |
| Adafruit QT Py CH32V203G6 | Digi-Key `5996` | $4.95 | USB-C; the Pi flashes it with wchisp (USB-only flashing rule) |
| Bulk capacitor, >= 100 uF / 35 V | stock | - | across VM/GND at the driver board |
| Motor, first round | the SERVO42D already on string 1 | - | its coil wires moved to the TMC2209 (below) |
| Motor, second round | **Leadshine 42CM06**, JLCMC (BR1841) | $8.78 | THE official motor. 1.8 deg, 42 mm, 47 mm long, 2.5 A, 0.9 ohm / 1.6 mH, 0.6 N·m. In stock at 100 on 2026-11-25 ($878.26, one price at every quantity), ships within 7 days; add a few to the next JLC order |

## Wiring

**Power off for every wiring change. Never connect or disconnect a motor coil while the driver is
powered: an opened coil under current can destroy the driver.**

- **Motor.**
  1. Unscrew the 4 coil wires (red/black/blue/green) from the SERVO42D's blue 4-way terminal.
  2. Land them on the TMC2209's A1/A2/B1/B2.
  3. Check the pairs with a meter first: ~1-2 ohm within a pair, open between pairs.
  4. Leave the SERVO42D board mounted and on CAN. Its magnet sensor still reads the shaft, so
     `READ_ENCODER` gives ground truth. Check first that it still answers with no motor attached;
     if it faults, measure by pitch instead (the same tracker `openloop.py` uses).
- **VM.** Bench 24 V, with the bulk capacitor right at the driver board. VM is limited to 29 V
  (absolute max 32 V); the 24 V supply must not overshoot.
- **VIO.** The QT Py's 3V3. The TMC2209's logic runs at VCC_IO (3.3-5 V), so 3.3 V levels match
  directly and no level shifting is needed.
- **UART.** QT Py TX goes through **1 k** to PDN_UART; QT Py RX goes straight to PDN_UART. This is
  TMC2209 datasheet section 4.3, Figure 4.1 (p17). It is a 1 k series resistor, not a divider; the
  1 k lets the driver overdrive TX when it replies.
- **Address.** MS1 and MS2 to GND, giving address 0.
- **STEP and DIR.** From hardware timer pins. The step edges must come from timer compare
  outputs, never software toggles: MicroPlyer "only works perfectly with a jitter-free STEP
  frequency" (section 13.3).
- **ENN.** A GPIO with a pull-up, so the driver is off until the MCU says otherwise. The datasheet
  says "Start with ENN=high!" (p12).

## Driver settings, written over UART before each run

- `MRES` = 1/4 at speed. `intpol` = 1 interpolates to 1/256. `dedge` = 1 halves the edge rate.
- `IRUN` sets the working current for gate 2, as below. `IHOLD`/freewheel are set per test.
- StealthChop2 (the default).
- After each move, read `MSCNT` (0x6A) and compare it with the MCU's own pulse count mod 1024.
  Any difference is a lost or extra pulse and fails the run.

## Gate 2: a whole tone in ~40 ms, at the current a TMC2209 can hold

The 42CM06 is rated 2.5 A. A TMC2209 on a board holds roughly 1.4 A RMS (lead, 2026-11-24), about
56 % of the rated current and so, roughly, of the torque; its 1.6 mH winding is what keeps that
torque at speed. So gate 2 runs at the driver's thermal current, not at the motor's rating.

**Torque budget (lead, 2026-11-25), 42CM06 on 24 V.**

*What the motor gives.* Leadshine's own spec (leadshine.com, 42CM06, read 2026-11-25): 0.6 N·m,
2.5 A, **0.9 ohm, 1.6 mH, rotor inertia 72 g·cm^2**, 47 mm, Ø5 shaft. Phasor model per phase:
ke = 0.6 / (sqrt2 x 2.5) = 0.17 V·s/rad. **Checked against Leadshine's published 24 V / 2.5 A
speed-torque curve: within 5 % from 500 to 2400 rpm** (0.30 N·m read at 1500 rpm, model 0.297).
Pull-out torque on 24 V:

| Set current (RMS) | 1000 rpm | 1250 rpm | 1600 rpm |
|---|---|---|---|
| 1.0 A | | | 0.19 N·m |
| **1.4 A** (TMC2209 on a board) | 0.33 | 0.30 | **0.25** |
| 1.8 A (ceiling) | | | 0.28 |

The supply cannot rise: the +24 V stack is held at or below 28 V for the TMC2209 (lead).

*What the move needs.*
- **The target, restated.** The closed loop's "39 ms" is a t90 (90 % of a whole tone, 0.52 turn,
  11-02). A constant-acceleration triangle reaches 90 % at 0.776 of its length, so the same t90
  is a **50 ms move: about 820 rev/s^2, peaking at about 1250 rpm**, not 39 ms at 1370 rev/s^2
  and 1600 rpm.
- Rotor: 72 g·cm^2 (measured by Leadshine), plus about 10 g·cm^2 for the pulleys, belt and screw
  *(estimate)*: 0.042 N·m at 820 rev/s^2.
- **String and screw: ~0.07-0.16 N·m, estimated, not measured.** String 1 is about 100 N at D4
  and about 128 N two semitones up (615 mm scale). Through the Tr8x2 (5.2° lead angle) at the
  1:1 belt, raising takes F·lead / (2 pi efficiency): about **0.07-0.09 N·m with thread friction
  ~0.1**, up to 0.16 at 0.25. Friction near 0.1 fits what the bench saw (11-25: a slipping motor
  let the string pull the nut on, so the screw is only just self-locking, which it stops being
  below about 0.09). Today's bracket from the SERVO42D's motor (held at 500 mA, lost steps at
  300 mA, 600 rpm) gives 0.06-0.12 N·m on the same footing.
  The SERVO42D can't measure it directly: its current read (38H) does not answer on our board's
  firmware (40H reports 1.0.9, hardware S42D_CAN; motor_ctrl passes every frame), and its motor's
  torque constant is unpublished. `publicbench.loadprobe` is ready for a board that answers.

*The floor under the load: self-locking (lead, 2026-11-25).* The Tr8x2 must hold the string with
the power off, so the nut thread may not be smoother than self-locking allows: friction
mu >= tan(lead angle) x cos(15°) = 0.091 x 0.966 = **0.088**, whatever the tension (both sides
scale with it; the thrust bearing adds nothing, it rolls). A screw that self-locks runs at 50 %
efficiency or less, so raising always takes at least F x lead / pi at the screw:

| Nut friction | String at +2 st (128 N) | at +4 st, the raise budget (158 N) | t90 39 ms margin, 128 / 158 N |
|---|---|---|---|
| 0.088 (exactly self-locking) | 0.085 N·m | 0.105 N·m | 2.3x / 2.0x |
| 0.110 (1.25x) | 0.095 | 0.118 | 2.2x / 1.9x |
| **0.132 (1.5x, a sane safety factor)** | **0.106** | **0.131** | **2.0x / 1.7x** |
| 0.176 (2x) | 0.128 | 0.158 | 1.7x / 1.5x |

(1:1 belt at ~97 %; 50 ms triangle at 1.4 A, rotor + ~10 g·cm^2.) **So the 0.07 end of the
estimate below is impossible**: the real range is about 0.085-0.16 N·m. With any safety factor on
self-locking (vibration, a slipping motor already back-drove it once), the 39 ms t90 sits at
**about 2x for a whole tone from open, and under it (1.7x) near the top of the raise budget**.
"Less screw friction" is therefore not a fallback: the only one left is a slower t90 (or a
holding means other than the thread, which is a design change).

*Margin at 1.4 A* (pull-out torque at the move's peak speed / need):

| Move | String load 0.07 | 0.12 | 0.16 N·m |
|---|---|---|---|
| **t90 39 ms** (50 ms triangle, ~1250 rpm) | **2.6x** | **1.8x** | **1.5x** |
| t90 30 ms (39 ms triangle, 1600 rpm) | 1.8x | 1.3x | 1.1x |
| t90 47 ms (60 ms triangle, ~1040 rpm) | 3.3x | 2.2x | 1.7x |

So matching the closed loop's 39 ms clears 2x only at the light end of the load estimate.
**Fallbacks**, if the kit shows it short:
- **A slower t90.** This is the strong lever: 2x needs t90 about 33 ms at a 0.07 N·m load and
  about 43 ms at 0.12. At 0.16 no speed reaches 2x: the load alone is half the motor's low-speed
  torque at 1.4 A (0.33 N·m), so there the only cure is less screw friction.
- **The drive ratio is not a lever.** Gearing the motor down makes it spin faster into the
  voltage limit (1.5:1 drops the margin below 1x). A step-up (the motor turning 0.75 turn per
  screw turn) gains about 10-15 %.
- ~~Less thread friction~~: ruled out by self-locking (above); at best it recovers the gap between
  the measured friction and 0.088 x the safety factor.

**Measure the margin directly on the 42CM06** in gate 2: after the 1.4 A sweep passes at an
acceleration, re-run that one acceleration at 1.2, 1.0, 0.8 ... A until it loses a step. The
pull-out ratio between 1.4 A and that current (this table's model) is the measured margin.

1. **Thermal limit first.**
   1. Hold the motor energised at 1.0, 1.2 and 1.4 A RMS for 10 minutes each, with no heatsink.
   2. Log the board temperature and any overtemperature flag (`otpw`, `ot`).
   3. The highest current with no flag, minus 10 %, is **I_run**.
2. **What the SERVO42D said (2026-11-25), driving itself open loop.** String 1 at pitch, 1400 mA,
   20 whole tones each way per setting, encoder as truth (`publicbench.openloop`,
   `publicbench.rampsweep`):
   - Torque: 0 steps lost from 1600 down to 500 mA at 600 rpm; 300 mA lost 3, 200 mA stalled.
   - Open-loop lag: about +-0.3 cent at 1000-1400 mA, the same raising and lowering.
   - Ramp: its own `acc` setting (higher = steeper, 0 = none) gave t90 183 ms at 230, 89 ms at
     250 and **49 ms at 254 with 0 lost**; 255 lost steps. Raising and lowering within 1 ms.
     acc 254 is about 400 rev/s^2 (a 0.233-turn triangle in 48 ms).
   - **It cannot go further.** Its open-loop modes are capped at 400 rpm, by the bus and from
     STEP pulses alike (MKS manual V1.0.9, 3.2), and 4 microsteps to lift the cap is a firmware
     artefact (every move ~75 % short by a fixed amount). Its ramp also rises in audible
     speed steps (a steady tone, 160-770 Hz with `acc`).
   - So gate 2 proper needs **~1370 rev/s^2 peaking at 1600 rpm** (0.52 turn in 39 ms as a
     triangle, lead 11-25), and only the TMC2209 kit can show it.
3. **On the TMC2209: the ramp sweep.** The QT Py's planner is the constant-acceleration profile
   (`firmware/qtpy_bench/axis.c`: settable vmax and acceleration, integer AVR446 recurrence,
   per-step intervals from a timer, no speed staircase). Keep the SERVO42D board mounted on CAN
   as the encoder (Wiring, above): gate 2 refuses to run without it, because a stall shows on
   the shaft, not in MSCNT.

   ```
   python3 -m publicbench.gates 2 --truth servo42d --ma 1400 --accs 400,800,1200,1600
   ```

   1. **Thermal first** (step 1): run gate 2 at I_run if it comes out under 1.4 A.
   2. It learns which way raises pitch from a small move and the encoder, then for each
      acceleration (400, 800, 1200, 1600 rev/s^2; vmax 1600 rpm):
      - **tone**: 20 whole tones each way on this rig (0.233 turn, -2..+2 semitones);
      - **long**: 20 moves each way of 0.52 turn, from -2 semitones to +2.36 (D4 to about F4,
        user 11-25; `--raise-st 2.4` is the ceiling), so the time compares directly with the
        closed loop's 39 ms.
   3. Per move it logs the encoder curve (polled while the QT Py reports moving), t90 from the
      command, the shaft's error, full steps lost (error / microsteps per full step) and the
      MSCNT check. **The first lost step ends that acceleration** (the shaft is re-aligned with
      `setpos` and sent home): the next moves would carry the offset past the travel.
   4. **Pass:** 0 lost over the 40 moves of each kind, at the acceleration whose t90 meets the
      target: <= 45 ms on 0.52 turn (the closed loop's 39 ms plus margin); on the 0.233-turn tone
      that is about 2 x sqrt(0.233 / 1370) = 26 ms.
   5. Planner time for the WHOLE move (a triangle; only 1600 rev/s^2 on 0.52 turn reaches the
      1600 rpm vmax and cruises). t90 comes in under these, plus the USB command latency:

      | rev/s^2 | 0.233 turn | 0.52 turn |
      |---|---|---|
      | 400 | 48 ms | 72 ms |
      | 800 | 34 ms | 51 ms |
      | 1200 | 28 ms | 42 ms |
      | 1600 | 24 ms | 36 ms (vmax-capped) |

   6. **Repeat with the 42CM06** when it arrives: it is the one that has to pass. A pass on the
      SERVO42D's own motor (winding unpublished) is encouraging but not sufficient.

## Gate 1: phase restore at power-up (items i-v)

The TMC2209 has no direct mode, so there is no way to set coil currents to the stored phase
directly. The restore is: **enable at MSCNT 0, let the rotor snap to the nearest MSCNT-0
equilibrium (at most +-2 full steps, repeating every 4), then move back** by the predicted
difference. It works if the MCU stores its phase on power-fail.

**(iv) The headline test: does the snap land where predicted under string load and the
self-locking screw?**
1. Move to a stored target and note the encoder position and MSCNT.
2. Cut the 24 V, wait 2 s, and power up. Enable with ENN low at MSCNT 0 and IRUN.
3. Read the encoder.
4. **Pass:** the snap lands on the predicted equilibrium every time, and does not stick in a
   detent between. Then move back by the difference and confirm the target within one microstep.
5. Repeat 20 times at each of: the low end, the high end, and phases near +-512 microsteps (the
   ambiguous midpoint).
6. Run it with the string at pitch. The screw's friction is what might stop a clean snap.

`openloop.py --powercycle 5` on the SERVO42D (SR_OPEN) gives a first analogue today.

**(i) Does MSCNT advance on STEP edges while the outputs are off?**
1. With ENN high (outputs floating), send N steps and read MSCNT.
2. Repeat with ENN low and TOFF=0.
3. If MSCNT advanced, the snap can be avoided: at power-up keep ENN high, step to the stored
   phase, then enable (plan A). If not, plan B as in (iv).

**(ii) Freewheel to move.**
1. Stop with IHOLD=0 and freewheel, so the coils are off at rest.
2. Start the next move.
3. **Pass:** no jerk at the restart, and MSCNT and the encoder agree.
4. StealthChop's automatic tuning learns during "the first motion after power up" (p7); check that
   the first move after each power-up isn't the noisy or weak one.

**(iii) Pulse count against MSCNT at speed.** This replaces the TMC5240's direct-mode question.
1. At top speed and I_run, run 1000 whole tones.
2. After each move, compare MSCNT with the MCU's pulse count.
3. **Pass:** zero mismatches, and every move ends on the target microstep. Interpolation lags
   while accelerating and catches up with a small jump (section 13.3); the final position must
   still be exact.

**(v) A brownout that resets the driver.**
1. Dip VM below the undervoltage threshold with the MCU kept up.
2. **Pass:** the MCU sees `GSTAT.reset` (bit 0), re-writes the settings, and restores through the
   (iv) path from its stored phase.

## Logging

Every run appends JSON lines to `~/openloop_tmc.jsonl`, in the same shape as `openloop.jsonl`.
Stop the phone service before using CAN:

```
sudo systemctl stop public-steel-guitar-phone
```
