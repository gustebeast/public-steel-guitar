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

## Finding a board, and flashing it (first flash and recovery alike)

Each board powers the next 100 ms after it starts (`NEXT_AFTER_US`), unless the Pi holds the
chain. So the Pi can walk the chain and learn its order:
- ALL `H` holds every board's next board dark.
- CMD `N` 1, sent to one slot at a time, lets one more board up.
- The HELLO that follows a board's `N` comes from the board after it.

A board that stays silent after its predecessor's `N` is the blank or broken one. The Pi knows
which lever that is from the slot it expected there (`levers chain` keeps the order learned
while the chain was healthy).

Flashing board k, where p is the slot of the board before it:

1. motor_ctrl powers the arm with the pair as CAN. The Pi holds the chain and walks it up to p.
2. The Pi sends ALL `U` ms, p (`LC_RELEASE`, lever.h).
   - Every running board turns its transceiver off, lets go of PB8 / PB9 and waits silently.
   - Board p also cuts its next board's 5 V and restores it ms later.
3. Within that window motor_ctrl hands the arm's pair to the Pi's USB.
4. Board k powers up on a pair held low, so it comes up in the ROM loader. BOOT0 comes from the
   bus, so this works whatever firmware is on k. The boards after k stay dark, because k's
   switch defaults off. The Pi writes `full.bin` (loader + application) with an ISP tool such as
   `wchisp`. Nothing is installed yet; installing it is the user's call.
5. motor_ctrl power-cycles the arm as CAN.

For the first board of an arm, motor_ctrl cycles the arm itself (slot 0xFF: nobody cycles). A
board whose firmware jams the bus can't be told anything, but it never needs to be. The Pi
holds the chain before the jammer gets power and then walks it only up to its predecessor.

Updates still go over CAN through each board's own loader (`make can`). The SWD pads stay as the
last resort (M9).

## The host side: motor_ctrl R2 and the Pi (2026-11-04)

motor_ctrl R2 (`elec/motor_ctrl.py`, `_arm_switches` and `_link_select`) splits bus B into its
two arms and adds a lane from the Pi's USB:

| part | job | default (MCU blank, in reset or in WCH's ROM) |
|---|---|---|
| U9 TS3USB221A | the pedal arm (J2): U3's CANB (1D) or the flash lane (2D); S on PD9 | **CAN** (R27) |
| U10 TS3USB221A | the lever arm (J6): the same; S on PD8 | **CAN** (R28) |
| U8 TS3USB221A | J4's pair: U7, the link (1D), or the flash lane (2D); S on PA3 | **the link** (R32) |
| U6 / U11 TPS2553 | each arm's 5 V, limited to 0.52 A; EN on PC12 / PD2 | **on** (R30 / R31) |
| D4 / D5, D10 / D11 | ESD clamps, now on each arm at its connector, outside the switches | — |

**The link drops for the window.** J4 is the link or the lane, never both: a hub (CH334R) would
have kept both, and was drawn first, but no bare patch of this board is big enough for it and
its crystal. So motor_ctrl owns the window (`firmware/motor_ctrl/arms.c`):
- `A <arm> <0|1|2>` turns an arm's 5 V off, on, or cycles it (off for 200 ms).
- `U <arm> <ms> [1]` answers OK, then 20 ms later puts the arm and J4 on the lane for ms. When
  the window ends it hands J4 back to the link, puts both arms on CAN and power-cycles both. Both
  arms are cycled because an ALL 'U' parks every board on bus B, not only the flashed arm's.
  With the `1`, the arm is also cycled at the start, so its first board comes up on the lane
  (lever.h slot 0xFF).

**The Pi:** `python3 -m publicbench.leverisp <levers|pedals> --slots ... --loader boot.bin --app
lever.bin`, one arm at a time with the other dark:
1. Walk the arm. Send ALL 'H', then CMD 'N' to each board in turn. A new board is held the
   moment its HELLO arrives (lever.c: an 'H' leaves a next board that an 'N' let up). Boards
   without a slot get the next one from `--slots`, in chain order.
2. A board in its CAN loader gets the application over CAN (`leverflash.write`).
3. At the first silent place, ALL 'U' with the slot before it, then `U` to motor_ctrl. wchisp
   writes the loader into the ROM, and the window closes. Then walk again.
4. A place still silent after its loader went in is named and left for a hand.

Tested in `bench/tests/test_leverisp.py`, which runs arms.c, lever.c and ldr.c on one simulated
clock (`simchain.py`). wchisp is not installed on the Pi; that is the user's call.

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

## Known issue: the foot pedals (deferred by the user, 2026-11-03)

"Don't worry about foot pedals, we can add a comment flagging it as a known issue and to
revisit when we get to designing them." Each pedal hangs its board connector-down into the
pedal bar. The 45.0 board reaches 41.6 below the axle datum, against the bar's 32.05 to its
trough floor, so the board pokes about 9.6 mm out of the bar's bottom. `src/foot_pedal.py`
carries the flag at `bus_paths`. The fixes, to be chosen then:
- a bar about 10 mm taller;
- the board mounted connector-up into the pedal housing;
- a shorter board (QFN-48 MCU and SC-70 parts, about +6 instead of +12), plus a little bar
  height.

## Follow-ups

- **motor_ctrl R2:** built 2026-11-04, above. Not yet ordered.
- **R2's CAN1 home pins, CONFIRMED 2026-11-04.** To make room for the lever-flash lines, R2 moves
  bus A's CAN1 off its remap (PB8 RX / PB9 TX) onto its home pins: PA11 = CAN1_RX (pin 46) and
  PA12 = CAN1_TX (pin 47). Source: WCH's CH32V303/305/307/317 datasheet V3.4, p.35, table 3-1,
  QFN68 column. Each name was read by its position on the page, not by the extracted text order
  (the misread that once swapped PB8): CAN1_RX lies inside PA11's row with OTG_FS_DM, and
  CAN1_TX inside PA12's with OTG_FS_DP.
- **Bench:** a C8T6 board's ROM loader on PB6/PB7 through a TS3USB221A, and then through a
  loaded chain.
- **Pi:** `publicbench.leverisp` drives steps 1–5 (in the simulator). wchisp is still to be
  installed (the user's call).
