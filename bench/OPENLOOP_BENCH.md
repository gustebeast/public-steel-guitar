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

**Torque budget at the gate's peak (lead, 2026-11-25): 42CM06, 1600 rpm, 24 V.** Phasor model per
phase: back-EMF constant ke = 0.6 N·m / (sqrt2 x 2.5 A) = 0.17 V·s/rad, so the back-EMF is 28.4 V
peak at 1600 rpm, over the supply. With 0.9 ohm and 13.4 ohm reactance (1.6 mH at 1333 Hz), the
pull-out torque is the best the 24 V bridge can drive, the current leading the back-EMF (the load
angle open loop settles at):

| Set current (RMS) | Low speed | 1600 rpm, 24 V |
|---|---|---|
| 1.0 A | 0.24 N·m | 0.19 N·m |
| **1.4 A** (TMC2209 on a board) | 0.34 N·m | **0.25 N·m** |
| 1.8 A (ceiling) | 0.43 N·m | 0.28 N·m |

At 1.4 A it falls off as 0.31 / 0.28 / 0.25 / 0.23 / 0.21 N·m at 1200 / 1400 / 1600 / 1800 / 2000 rpm.
The model takes the bridge's fundamental as 24 V peak; R and L are the 11-24 report's (JLCMC's
page shows neither), so the whole table is a model, not a measurement.

What the move needs, all ESTIMATES:
- Rotor inertia: 0.52 turn in 39 ms as a triangle is 8,600 rad/s^2. The 42CM06's rotor inertia
  was not read. Typical 40-48 mm motors have 54-82 g·cm^2: **0.046-0.070 N·m**.
- String and screw: the SERVO42D's motor held whole tones at 600 rpm on a gentle ramp at 500 mA
  and lost steps at 300 mA (2026-11-25). Scaled from a typical 0.40-0.48 N·m / 2 A motor (its own
  is unpublished), the load is between **0.06 and 0.12 N·m**. That is pessimistic: the motor's
  torque at 600 rpm is below its low-speed figure, so the real load is lower. Raising carries it;
  lowering is helped by it.
- Pulley, belt and screw inertia: not counted.

So the move needs roughly **0.11-0.19 N·m** against 0.25 at 1.4 A: a margin of **1.3-2.3x**
(1.5-2.5x at 1.8 A). The worst case is under 2x. Gate 2 on the real motor is what settles it.
Two cheap readings would narrow it before then: the 42CM06's rotor inertia from its JLCMC SPEC
sheet, and the string load from the SERVO42D's phase current during a loaded raise (closed loop).
More supply voltage is the lever if it is short: the same model gives 0.30 N·m at 1.4 A with
about 31 V of fundamental.

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
