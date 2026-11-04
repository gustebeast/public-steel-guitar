# The control path: levers and pedals to motor targets

Lever and pedal positions come in on bus B, go through the copedent, and leave as motor targets
on bus A. This note covers where each piece lives under the
control-architecture split (user, 2026-09-14: the MCU does only sensor → motor, the Pi
does everything else), the table format, the default copedent, and the latency budget against
the C3 target. It is built and tested in simulation; no string has been driven by it yet.

| piece | file |
|---|---|
| the copedent (music) | `bench/publicbench/copedent.json`. `tools/export_rig.py` draws from it too, so there is one copedent for the viewer and the instrument |
| compile + write down (Pi) | `bench/publicbench/copedent.py` (`--write`) |
| the real-time path (MCU) | `firmware/motor_ctrl/play.h`, `play.c`, wired into `main.c` |
| simulation | `bench/publicbench/simplay.py` (play.c via ctypes), `simlever.py` (lever.c), `sim.py` (SimServo) |
| tests | `bench/tests/test_play.py` (9 tests, run on the Pi: they need a C compiler) |

## Where the copedent mapping lives

**The Pi owns the copedent as music, and owns calibration. The MCU owns the arithmetic.**

- **On the Pi:** `copedent.json` gives each control its slot and its moves (string number →
  semitones at full travel, signed). Each string also has a **curve**: motor counts from open
  pitch, measured against pitch during tuning. `copedent.py` compiles the two into one
  1,192-byte `play_table_t` and writes it to motor_ctrl's flash.
- **On motor_ctrl:** `play.c` keeps the latest position of each slot. Whenever a position changes,
  it works out each string's pitch, looks that pitch up on the string's curve, and sends a
  SERVO42D absolute move (F5). It reads the table from flash at power-on, so **the instrument
  plays with the Pi absent**.

There were two other ways to split it. Both were rejected:

- **The Pi precomputes counts and the MCU just adds them up** (the literal reading of "saved
  travel offsets"). Counts do not add, because string tension goes as pitch squared. Take
  P2 + P5 on string 10 in this copedent: +2 then −3 semitones. Adding the two offsets lands
  **74 cents** away from −1 semitone, and two stacked whole-tone raises land 37 cents flat.
  Combining has to happen in pitch, and the lookup to counts has to come after it.
- **The Pi precomputes every combination.** 11 controls make 2,048 on/off combinations, and
  partial travel (half-pedal) makes it continuous. The rule costs about 200 integer operations
  per tick, so the MCU just runs it.

So the MCU still does only sensor → motor. The table is the "saved offsets", in a form that
combines correctly.

## The combine rule

For each string:

- **up** = the largest `position × cents` among the controls that raise it.
- **down** = the most negative `position × cents` among the controls that lower it.
- **pitch** = up + down.

Raises do not stack. P1 and P2 both raise string 10 from C to D, and with both down it stays at
D, not E. On a mechanical changer, two pulls on one finger behave the same way. A raise and a
lower do add, as a changer's raise and lower fingers do. Python carries the same rule
(`copedent.pitch`), so the tuning UI can show what the board will do. A test checks the C and
the Python against each other on 200 random positions.

## Table format (`play.h` `play_table_t`, little-endian, 1,192 bytes)

| field | |
|---|---|
| magic, version | `"PLAY"`, 1 |
| rpm, acc | F5 speed and ramp. Defaults: 3000 rpm, acc 0. acc 0 is the fastest setting (motor step results 11-02, `bench/publicbench/motorquality.py`: acc 240 took 224 ms where acc 0 took 39 ms) |
| min_us | the shortest gap between two F5 frames to one motor. Default 4 ms. The newest target wins, so the first frame of a move goes at once and only the updates of a continuing move wait |
| motor[10] | each string's motor CAN id. Default: string N → id N |
| cents[16][10] | slot × string index, at full travel |
| curve[10][21] | counts from base at −400 … +600 cents, one knot every 50 cents, piecewise linear. Must be 0 at 0 cents |
| crc | zlib crc32 of everything before it |

Loading happens over motor_ctrl's line protocol: `P W <offset> <hex>` 32 bytes at a time, then
`P S`. The board checks the table, writes it to the 4 K sector after the application, and plays
from it at once. `link.h` now ends the application area at 284 K, `TABLE_ORG`. Other commands:
`P` reports status, `P 0` / `P 1` stop or start driving (not kept over a power cycle), and
`P Z` re-bases.

**The default copedent is the user's own C6**, the chart `tools/export_rig.py` was transcribed
from cell by cell, rather than a standard E9. The design bounds are C6, and E9 would have been a
placeholder over a real copedent. Slot 10, the sixth knee lever, has no moves in it yet.
**The default curves are placeholders:** the pitch-range model of `src/dimensions.py`
(DL_OPEN = 4 mm stretch at open pitch for every string, 2 mm screw lead, 1:1 belt). The
measured curve replaces it string by string.

## Base: what "open pitch" is after a power cycle

A SERVO42D loses its turn count when the power goes, but the lead screw holds the carriage where
it was. If every control was at rest at power-off, that position is open pitch. So at power-on
`play.c` asks each motor for its encoder (0x31), takes the answer as that string's base, turns
off its arrival reply (0x8C 01 00, see bus A load below), and enables it (0xF3). A string is not driven until it is based, and an unanswered motor is asked
again every 100 ms. The Pi re-bases (`P Z`) after it tunes.

**Open item:** if the power goes with a pedal down, that string comes back off pitch until it
is retuned. A fix needs a stored turn count or a homing move. Neither is built.

Other safety behaviour:

- A lever not heard from for 150 ms (3 × its 50 ms heartbeat) counts as at rest.
- An uncalibrated lever (`0xFFFF`) counts as at rest.
- A bad table drives nothing.

## Latency budget

**The target:** the A2M detector needs 2–3 periods to read a pitch, which is **15–23 ms at C3**
(the design bounds, C6 tuning). The question is whether the pitch-control path
fits inside that window, or whether it becomes the long pole.

Assumptions: bus A and bus B both at 500 kbit/s (the defaults in lever.h and main.c). A POS frame
is about 90 bits (0.18 ms). An 8-byte F5 frame is about 130 bits with stuffing (0.26 ms).

| # | hop | onset (pedal leaves rest) | following a moving pedal |
|---|---|---|---|
| 1 | sensor sample (`SAMPLE_US` 1 ms) | ≤ 1.0 ms | 0.5 ms avg |
| 2 | median-of-3 + IIR ¼ filter | ≈ 1 ms (the first `DEADBAND` change) | ≈ 4 ms lag (1 median + 3 IIR samples) |
| 3 | lever send rule (`TX_MIN_US` 2 ms) | 0 (idle → sends at once) | ≤ 2 ms, 1 avg |
| 4 | bus B wire + one frame of arbitration | ≈ 0.4 ms | ≈ 0.4 ms |
| 5 | play.c (integer only) | < 0.05 ms | < 0.05 ms |
| 6 | bus A: up to 3 strings of one control, back to back | ≤ 0.8 ms | ≤ 0.8 ms |
| 7 | per-motor `min_us` (4 ms) | 0 (a move's first frame goes at once) | ≤ 4 ms, 2 avg |
| | **electronics** | **≈ 3 ms** | **≈ 9 ms avg, ≈ 13 worst** |
| 8 | the motor itself, unloaded | whole tone to 90 % in **39 ms** (measured 11-02, acc 0) | sim: **13–19 ms** behind an 80 ms press |

What the simulation measured (`test_end_to_end_pedals_and_lever_to_motors`): the real lever.c and
play.c, with SimServo set to 1200 turns/s², which matches the measured unloaded step. Five runs
on the Pi:

- first F5 on bus A **0.9–1.9 ms** after the pedal stepped
- strings within 3 cents of a stamped-down pedal after **50–60 ms**
- **13–19 ms** behind the end of an 80 ms press (one run hit 44 ms; that is Python-thread
  jitter, not the model)

**Verdict:** the electronics take ≈ 3 ms to start a move and run ≈ 9 ms behind a moving pedal,
both inside the 15–23 ms C3 window. The only term that can exceed it is the motor's mechanical
response. A pedal snapped down in one sample takes about 50 ms to settle, longer than the
detector needs to read the pitch. A foot does not move in 1 ms, though, and behind a real
80 ms press the string trails by about 15 ms.

**Nothing has been measured under string load.** The next number to get is the loaded step and
the loaded ramp lag, on the bench with a string on.

If the lag ever matters, these are the knobs, cheapest first:

1. Lever IIR from ¼ to ½ (filter lag 4 → 2 ms, at some cost in noise).
2. Bus A at 1 Mbit/s (the SERVO42D supports it). This halves term 6 and lets `min_us` drop to
   2 ms.
3. A faster motor ramp, which is the dominant term and only the bench can tell us about.

**Bus A load:** while basing, play.c sets each motor to answer a move once, when it starts, and not
again when it arrives (0x8C 01 00, from section 5.2.12 of the MKS CAN manual V1.0.9; the "active"
byte arrived in V1.0.4). A move update is then one F5 frame plus one 3-byte reply, about 0.42 ms
of wire time where it was 0.58. At `min_us` 4 ms, each moving string uses about 10.5 % of a 500 k
bus. Six strings moving at once is about 63 %, and nine or more saturate it. A big pedal plus
two levers moves 6–7 strings.

**Open item:** run bus A at 1 Mbit/s (motor 0x8A 03, and `B 0 1000000` on motor_ctrl), which
halves every figure above. Both ends have to change together, so it is a set-up step on the
bench, not something play.c does by itself. Turning replies off entirely (0x8C 00) would also
silence the encoder reads that basing depends on, so it is not used. The 0x8C setting has not
yet been tried on a motor.

## Not done

- No string has been driven by this. The bench test needs the motor_ctrl board, a motor with a
  string, and a lever board: it needs the user's hands.
- The tuning tool is built and proven only in simulation (`bench/publicbench/tune.py`, 2026-11-04;
  see "Tuning" in `docs/phone-ui.md`). No string has been tuned by it.
- The viewer still sums raises (export_rig's rig.json), where the board takes the largest. This
  is cosmetic and only shows where two raises meet on one string.
