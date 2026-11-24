# Open-loop bench: TMC2209 + CH32V203 on one string

The plan (user, 2026-11-24): a raw NEMA 17 on each string, driven by 10x TMC2209 on the connector
board, with one CH32V203 making the step pulses. No encoder and no motor-side hardware. This bench
answers the questions the datasheets can't, before any layout. No firmware exists yet; this note
is the procedure the firmware and the test scripts will follow.

## Kit (the user orders; nothing has been bought)

| Part | Where | Price | Note |
|---|---|---|---|
| TMC2209 SilentStepStick | Digi-Key `TMC2209SILENTSTEPSTICK` | $15.44 | StepStick pinout, sense resistors on board. Option 2: `TMC2209-BOB` $30.47 |
| Adafruit QT Py CH32V203G6 | Digi-Key `5996` | $4.95 | USB-C; the Pi flashes it with wchisp (USB-only flashing rule) |
| Bulk capacitor, >= 100 uF / 35 V | stock | - | across VM/GND at the driver board |
| Motor, first round | the SERVO42D already on string 1 | - | its coil wires moved to the TMC2209 (below) |
| Motor, second round | StepperOnline 17HM19-2004S | $11.41 | 0.9 deg, 1.45 ohm, 4.0 mH. China stock only; US backordered |

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

The 17HM19 is rated 2.0 A. A TMC2209 on a board holds roughly 1.4 A RMS, about 70 % of the torque
(lead, 2026-11-24). So gate 2 runs at the driver's thermal current, not at the motor's rating.

1. **Thermal limit first.**
   1. Hold the motor energised at 1.0, 1.2 and 1.4 A RMS for 10 minutes each, with no heatsink.
   2. Log the board temperature and any overtemperature flag (`otpw`, `ot`).
   3. The highest current with no flag, minus 10 %, is **I_run**.
2. **On the SERVO42D first, today, before any TMC2209 arrives:**

   ```
   python3 -m publicbench.openloop --only current,speed --speed-ma 1400,1000
   ```

   The current sweep includes 1400 and 1000 mA, bracketing I_run. The SERVO42D's mA setting may
   be peak, not RMS, which is not documented; read its numbers as a bracket, not a match.
3. **On the TMC2209:**
   1. At I_run, run whole tones out and back at each `SPEEDS` row from `openloop.py`, 3 repetitions.
   2. Log t90 (the time to 90 % of the move) and lost steps, the latter from the encoder, or from
      pitch if the encoder is unavailable.
   3. **Pass:** no lost steps, and t90 <= 45 ms at some row.
   4. Repeat with the 17HM19 when it arrives. Its 4.0 mH slows it at 24 V, so a SERVO42D pass is
      encouraging but not sufficient.

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
