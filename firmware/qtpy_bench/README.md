# QT Py CH32V203 open-loop bench firmware

One TMC2209 (a SilentStepStick) driving one stepper open loop. The Pi commands it over the QT Py's
USB serial port (`cafe:4009`). The procedure it serves is `bench/OPENLOOP_BENCH.md`; the Pi's
client is `bench/publicbench/qtpy.py`.

**Status:** host-tested only (`bench/tests/test_qtpy_bench.py`). It has never been linked for
the chip or run on a board. The first `make` on the Pi is the first real build.

## Wiring

Power off for every wiring change.

| QT Py pad | Pin | SilentStepStick | Note |
|---|---|---|---|
| MI | PA6, TIM3_CH1 | STEP | one edge per step; the driver runs in dedge mode |
| MO | PA7 | DIR | |
| SCK | PA5 | EN (ENN) | high = outputs off. Add a 10 k pull-up to 3V3 so the driver stays off while the QT Py resets |
| TX | PA2, USART2_TX | PDN_UART through **1 k** | TMC2209 datasheet p17, Fig 4.1 |
| RX | PA3, USART2_RX | PDN_UART, direct | every byte sent is heard back and skipped |
| 3V | | VIO | logic runs at VCC_IO, so 3.3 V matches directly |
| GND | | GND | common with the motor supply's GND |
| | | MS1, MS2 to GND | UART address 0 |
| | | VM: bench 24 V, >= 100 uF at the board | VM <= 29 V |

## Pin map, checked against WCH's documents

The firmware uses only default mappings and never writes the remap register.

| Fact | Source |
|---|---|
| QT Py pad to port pin: TX = PA2, RX = PA3, SCK = PA5, MI = PA6, MO = PA7 | Adafruit's QT Py CH32V203 pinout page |
| G6/QFN28 pin 8 = PA2, default alternate function USART2_TX; pin 9 = PA3, USART2_RX; pin 12 = PA6, TIM3_CH1; pins 11 and 13 = PA5 and PA7 | CH32V203 datasheet V3.0, Table 3-1-3, PDF p23 (printed 21) |
| PA2, PA3, PA5, PA6 and PA7 each have their own package pin. The datasheet's note 7 (PDF p29) warns that 20- and 28-pin parts bond some pins together; on the G6 that is PA10 with PA11 (pin 19, the USB D-) and BOOT0 with PB8. Neither involves our pins. PA10 is left at its reset state, floating input (GPIOx_CFGLR/CFGHR reset 0x44444444, RM p144) | same table; RM below |
| AFIO_PCFR1 resets to 0x00000000 | CH32FV2x_V3xRM V2.5, register table, PDF p148 |
| TIM3_RM = 00: "Default map (CH1/PA6, CH2/PA7, ...)" | RM p153, and Table 10-17, p136 |
| USART2_RM = 0: "Default map (... TX/PA2, RX/PA3 ...)" | RM p154, and Table 10-24, p138 |
| Timer compare output and USART TX: push-pull alternate output; USART RX: floating or pull-up input | RM Tables 10-2 and 10-3, p133 |

PA2 and PA3 also carry TIM2_CH3 and TIM2_CH4 by default. Nothing here enables TIM2, so there is
no conflict.

## Build and flash (on the Pi)

```
cd firmware/qtpy_bench
make                 # build/bench.bin; needs ~/src/ch32v20x and ~/src/tinyusb
```

Unplug the QT Py, hold BOOT, plug it back in, release BOOT, then:

```
make isp             # wchisp flash build/bench.bin
```

Unplug and replug the QT Py to run it. Check that it answers:

```
cd bench && python3 -m publicbench.qtpy
```

This prints `id`, `init`, `st` and `ms`. `init` must report `writes=5`. Anything else means the UART
is not reaching the driver: check the 1 k, the RX wire, VIO and VM. The TMC2209 needs VM to answer
at all.

## Commands

Each command is one line in and one line out. A reply starts with `ok`, followed by `key=value`
fields, or with `err`. Units:

| Quantity | Unit |
|---|---|
| Position | driver steps at the current resolution (`usteps` per full step; default 4, i.e. 1/4) |
| Speed | steps/s |
| Acceleration | steps/s² |
| Current | mA RMS |

| Command | What it does |
|---|---|
| `id` | version and the step timer's tick rate |
| `init [usteps]` | write GCONF (UART mode, internal reference, MRES from register), clear GSTAT, then write CHOPCONF (MRES, interpolation to 1/256, dedge), IHOLD_IRUN and TPOWERDOWN. Replies `writes=` (IFCNT's count, which must be 5) and `usteps=`. Changing usteps restarts positions at 0 |
| `cur run hold [holddelay]` | set IRUN and IHOLD from mA. `hold 0` freewheels at rest. Replies the scales and the mA they actually give (110 mOhm sense resistors) |
| `en 0\|1` | ENN: outputs off or on. Moves are allowed with the outputs off: that is gate 1 item (i) |
| `go pos v a` | move to an absolute position: a trapezoid. Replies `steps=` |
| `mv d v a` | move by `d` steps |
| `halt` | stop at once. The target becomes wherever the motor is |
| `zero` | call the current position 0 (only when stopped) |
| `setpos n` | call the current position `n` without moving (only when stopped). Used after the power-up snap of gate (iv) |
| `st` | `pos target moving en usteps irun ihold` |
| `ms` | the driver's MSCNT beside `pos` and `per` (MSCNT counts per step). `moving=1` if it changed during the read |
| `gstat` | read and clear GSTAT: `reset=1` means the driver lost its settings since the last read |
| `drv` | DRV_STATUS, with `otpw ot stst` |
| `r reg` / `w reg val` | raw register access (numbers in decimal or 0x hex) |

**The MSCNT check.** Before a run, `zero` and read `ms` once to get `mscnt0`. After each move,
`mscnt == mscnt0 + sign * pos * per (mod 1024)` must hold, where `sign` (which way MSCNT runs for
a positive step) is learned once per wiring. `publicbench.qtpy.mscnt_agrees()` does this check.
A mismatch is a lost or extra step edge.

## How it works

- **STEP edges come from TIM3's compare output in toggle mode.** The ISR only loads the next
  compare value, and has at least 5 µs to do it, so edge timing does not depend on interrupt
  latency. MicroPlyer needs a jitter-free STEP (datasheet section 13.3).
- **`axis.c` plans each move** as a trapezoid with integer maths (the AVR446 recurrence), one
  step at a time, so the same code can later run 10 axes on the connector board's CH32V203 with
  no FPU.
- **Clock:** 96 MHz from the internal oscillator (the QT Py has no crystal); the USB gets its
  48 MHz from PLL / 2. The step timer runs at 8 MHz, so the shortest step interval is 5 µs and the
  longest 8.2 ms: a top step rate of 200 kHz, and a slowest of 122 steps/s.
- **USB is TinyUSB's FSDEV driver** on root port 0, using the same interrupt arrangement as
  TinyUSB's own ch32v20x board file.
- **The step ISR preempts USB and SysTick.** TIM3's priority is 0x00, the rest 0x80; with nesting
  on, bit 7 is the preemption bit (WCH `core_riscv.h`, `NVIC_SetPriority`). So a USB packet never
  makes it miss a compare. Every handler is naked and relies on the hardware stack, the only safe
  way to nest (TinyUSB's ch32v20x board file explains). This is to confirm on the bench: run full
  speed while the Pi polls `st`, and check the MSCNT.
