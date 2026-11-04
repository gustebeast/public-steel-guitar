# Lever boards: first flash over the bus wires (2026-11-03)

User: wire the whole instrument from factory parts and flash everything from the Pi, with only the
Pi flashed by hand. The lever and pedal boards were the gap. They had no USB, so their first
firmware needed the SWD jig. The user's call: "Go ahead and implement this as the lever board. It
meets our flashing goal which is worth the extra effort." The deal breakers are cost, stock and
size; a USB-C debug port would be added only at $1 or less and only with room to spare.

## The scheme

The bus pair (PH way 3 CAN_H, way 4 CAN_L) is either a CAN bus or a full-speed USB pair. The bus
itself decides which one, so a blank chip needs no help from its own firmware.

| part | job | default (MCU blank, in reset or in WCH's ROM) |
|---|---|---|
| U3 CH32V203C8T6 (LQFP-48, C3001172) | USBFS on PB6 / PB7, CAN1 on PB8 / PB9 (remap 1) | — |
| U5 TS3USB221ARSER (C128396) | the pair goes to PB6 / PB7 (1D) or to the terminator (2D) | **USB** (S pulled low by R12) |
| U6 LMV331IDBVR (C34731) | BOOT0 = "the pair is not a biased CAN bus" | — |
| Q3 AO3401A | the transceiver's 3V3 | **off** (R11) |
| Q1 AO3401A + Q2 2N7002 | the NEXT board's 5 V (J2 way 1) | **off** (R9, R10) |

**BOOT0.** U6 compares 0.32 × CAN_H (R13 1M over R14 470k) against 0.30 V (R15 / R16), so the
pair reads CAN above about 0.94 V. A biased bus holds CAN_H at 2.0–3.0 V recessive (ISO 11898),
which gives at least 0.64 V at U6, twice the threshold, so the board boots its application. A
USB host's 15k pull-downs or a floating pair (R14) hold CAN_H near 0 V, so the board boots WCH's
ROM loader. That loader serves USB on PA11/PA12 or PB6/PB7 (CH32V203 EVT manual,
"WCHISPTool"). PA11/PA12 are left unconnected. BOOT0 is only sampled at reset, so the loader's
own D+ pull-up changes nothing afterwards.

**One ROM loader on the pair at a time.** Every board holds the next one dark until its own
firmware switches Q1 on, so the chain powers up in order.

## Flashing board k (boards 1..k-1 already flashed)

1. motor_ctrl powers the arm with the pair as CAN. Boards 1..k-1 start their applications and
   power the next board. Board k is blank or broken, so board k+1 onwards stay dark.
2. The Pi sends ALL `U` ms (`LC_RELEASE`, lever.h). Every running board then:
   - turns its transceiver off;
   - lets go of PB8 / PB9;
   - cuts the next board's 5 V;
   - restores that 5 V ms later;
   - waits silently.
3. Within that window motor_ctrl hands the arm's pair to the Pi's USB.
4. Board k powers up on a pair held low, so it comes up in the ROM loader and enumerates. The
   Pi writes `full.bin` (the CAN loader and the application) with an ISP tool such as `wchisp`.
   Nothing is installed yet; installing it is the user's call.
5. motor_ctrl power-cycles the arm as CAN, and the process moves on to k+1.

Updates still go over CAN through the board's own loader (`make can`). Recovery is the same as
a first flash. The SWD pads stay as the last resort (M9).

## Signal integrity (`tools/fs_eye.py`)

The model is a lossless 110 ohm differential line with a 90 ohm FS driver. Every board on the
arm is a lumped load (HVD230 about 32 pF, U5 Coff 3.5 pF, clamp 0.5 pF, trace); the far board
is unterminated, as FS is. The eye is measured at the last board, against FS's ±0.2 V receiver.

| load per board | edge | lever arm 0.8 m + 5 × 0.25 | pedal arm 1.5 m + 4 × 0.1 | 2.0 m + 5 × 0.3 |
|---|---|---|---|---|
| 40 pF | 4 ns | 1.63 V, 83 % | 1.65 V, 74 % | 1.64 V, 82 % |
| 40 pF | 20 ns | 1.48 V, 70 % | 1.63 V, 69 % | 1.64 V, 69 % |
| 25 pF | 20 ns | 1.65 V, 75 % | 1.65 V, 74 % | 1.65 V, 75 % |

The worst case keeps 69 % of a bit open. The PH leads are untwisted, so 110 ohm is an estimate.
**Bench proof is still owed**: the ROM loader enumerating through six boards' worth of load.

## What it cost

- **Money:** about +$0.75 a board. The MCU is +$0.16 over the G6U6, U5 $0.24, U6 $0.11, the
  three FETs $0.21, plus resistors and capacitors. The extended parts add a loading fee per
  order.
- **Size:** the board grew 12 mm at −X, to 45.0 × 21.9 (knee_lever `PCB_X0` −29 → −41). The
  knee housings run to −69.9, so they have room. The pedal bay is cut from the posed board.
- **IN and OUT are no longer interchangeable.** J1 is IN and J2 is OUT (silk). If the board is
  plugged in reversed, Q1's body diode still powers it, but the next board is no longer held
  dark.

## Decided

- **No USB-C port.** It would need an opening in every lever and pedal housing, and the −X edge
  is where the harness plugs in. A bench PH-4-to-USB lead (D+ on way 3, D− on way 4) reaches the
  same ROM loader for $0 a board.
- **Rule exception, decided by the user.** USB runs over the crimped PH harness. M43's
  real-receptacle line (and the usb-real-connectors rule) is excepted for this board.
- **The transceiver stays on plain copper.** It is isolated by cutting its supply, so CAN never
  passes through U5's 6 ohm. U5 switches only the MCU's USB pins and the terminator.

## Follow-ups

- **motor_ctrl R2:** switched 5 V on each arm, a host switch on each arm (Pi USB or the CAN
  transceiver), and a Pi USB lane to it.
- **Bench:** a C8T6 board's ROM loader on PB6/PB7 through a TS3USB221A, and then through a
  loaded chain.
- **Pi:** an ISP tool, plus a `levers flash` command that drives steps 1–5.
