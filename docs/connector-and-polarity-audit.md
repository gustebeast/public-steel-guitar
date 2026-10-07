# Connector pin sources and part orientation: audit of 2026-10-06

Two faults were found in the fab's previewer on 2026-10-06 and both were the same mistake
in different clothes: **a number was trusted across two makers' numbering.**

* The 24 V inlet's nets were taken from the SUPPLY's pin table and put on the JACK's pad
  numbers. Mean Well and Kycon number the same four contacts differently; the board shorted
  the supply.
* The photodiode's footprint called the anode pair pad 1. Everlight and the fab call the
  cathode lands 1 and 4. The placement frame had been matched by number, and all twenty
  went on a half turn out.

This page asks the same two questions of every other connector and polarised part on the
boards in `elec/` (in sections 1 to 4 the lighting and UI boards' own records are quoted;
section 5 re-derives them).
The rule is now in `cadkit/PCB_QUALITY.md` (M1, M2).

## 1. Where a connector meets somebody else's numbering

Every other joint in the instrument is between two of our own boards on a keyed JST lead
whose way order is ONE constant in `elec/harness.py`, asserted by both generators; those
cannot disagree by construction and are listed in section 2. The joints below are the ones
whose far side is a product with its own pin numbers.

| Joint | The other maker's numbering | Translation, and where it is written | State |
|---|---|---|---|
| `output_panel` J6 (Kycon KPJX-4S-S) <- Mean Well GST160A24-R7B | Mean Well: 1 +V, 2 -V, 3 -V, 4 +V on ITS plug drawing | MW 1 / 2 = Kycon 2 / 1, MW 3 / 4 = Kycon 3 / 4. Into the jack, key up: top left pad 1 PWR_GND, top right pad 2 +24V_IN, bottom left pad 3 PWR_GND, bottom right pad 4 +24V_IN. `output_panel.py` at `j6` | **was wrong, fixed** (ec8feae3). Read off three drawings, not a part: the meter check stays (bring-up step 0) |
| `pi_cap` J1 (2x20 socket, on the face toward the Pi) <- Raspberry Pi header | the Pi's: pin 1 on the inner row at the end away from the USB ports, pin 2 on the edge row | measured on the routed board, seen from its front, the face that goes down onto the Pi: pad 1 (75.87, 103.23), pad 2 (75.87, 105.77), pad 39 (124.13, 103.23) in KiCad's frame. Turned over onto the Pi that is the Pi's own count seen from its component side. Pad for pad the same lands as the board first measured on 2026-10-06, which was drawn with its parts on the back; all 105 pads were compared when it was redrawn. Pad n is header pin n. `pi_cap.py` quality.pinouts | holds |
| `motor_ctrl` J4 (4-way PH) <- a USB-A lead | USB-A plug: 1 VBUS, 2 D-, 3 D+, 4 GND | NOT contact n to way n: GND -> way 1, VBUS -> way 2 (open on the board), D- -> 3, D+ -> 4. The table was missing from the build notes; added to `INSTALL_NOTES.md` today with the meter step | **gap closed today** (documentation; the board was right) |
| `ui_board` J1 (1x20 header) <- Newhaven NHD-2.7-12864WDW3 | the module's own 1..20 | header pin n is module pin n (the board's own record, from Newhaven's table p.4). A single row has no handedness; end for end is fixed by which way up the display reads | holds on that record; not re-derived here |
| `can_tee` J2 -> SERVO42D | screw terminals labelled on the motor (V+, GND, CANH, CANL), no numbers | the drop's motor end is bare wire to a labelled terminal | OPEN since before today (`can_tee` M1: needs a motor in hand) |
| USB-C receptacles (`output_panel` J1-J4, `optical` J1) <- stock USB-C leads | the Type-C contact names A1..B12, which the lead, the receptacle's maker and the footprint all use | nets attached by contact NAME, not by a pad count: A6 / B6 D+, A7 / B7 D-, A5 / B5 CC, A4 / A9 / B4 / B9 VBUS | holds |
| `output_panel` J5 (Neutrik NMJ6HCD2) <- a 6.35 mm plug | none: tip, ring, sleeve are positions on the plug | lands named T / R / S / TN / RN / SN from Neutrik's drawing, checked pad by pad 2026-09-30 | holds |
| `output_panel` J8 (screw terminal) <- the pickup's two leads | none | 1 PICKUP_HOT, 2 GND, on the silk | holds |

## 2. Our own leads: the number is ours at both ends

For these the footprint's pad 1 was compared with JST's own drawing (which post is the
No. 1 circuit, seen from which face) on 2026-10-04, part by part; each board's
`quality.pinouts` carries the page and the view. The ways come from `harness.py`.

| Part | Where | JST drawing, as recorded | Physical check in the fab's previewer |
|---|---|---|---|
| B4B / B6B / B2B-XH-A (top entry) | `motor_ctrl` J1 J3 J7, `output_panel` J7 J9 J10 | eXH p.5: from the slotted wall, No. 1 is the right-hand post; KiCad has that wall at local -Y, pad 1 at -X | seen today on both boards: in every one the posts sit nearer the wall our footprint calls slotted (2.35 of 5.75 mm), including the 6-way whose frame differs from the 4-way's by a half turn |
| B4B / B6B-PH-K (top entry) | `motor_ctrl` J4 J5 | ePH p.2: the same rule, wall 1.7 mm from the posts | seen today: posts nearer the footprint's slotted wall on both |
| S4B / S8B-XH-A, S4B-XH-SM4-TB (side entry) | `can_tee`, `pi_cap`, `optical`, lighting boards | eXH p.5 / p.6: from above, mouth away, No. 1 is the right-hand post | mouths off the board edge, bodies on their lands (order walk, 2026-10-06) |
| S4B / S6B / S8B-PH-SM4-TB, S4B-ZR-SM4A-TF (side entry) | `motor_ctrl` J2 J6, `pi_cap` J2, `lever_sensor` J1, the four leg boards | ePH p.4, eZH p.5: into the mouth, board below, No. 1 on the left | mouths off the edge (seen again on `motor_ctrl` today) |
| leg pogo pins and lands | the four leg boards | a symmetric row: POSITION decides, not a number | `leg_pogo.py --check` re-run today on the routed boards: GND, +5V, CAN_H, CAN_L along the row on all four, so each pin meets its land (the male_bottom board's pad NUMBERS run the other way, which is why numbers are not what is compared) |
| 2x8 1.27 mm ribbon header | `pi_cap` J5, `ui_board` J2 | no maker numbering; the footprint's, and the same footprint and the same sixteen nets at both ends | the header has no shroud: a reversed socket is an assembly error, guarded by the stripe-to-pin-1 step in the build notes. The fab numbers its rows the other way; it is placed by position |

## 3. Polarised parts: which terminal does the fab call pin 1?

A frame fitted by pad number only proves the two libraries' NUMBERS line up. So for each
polarised part the fab's own footprint and symbol were read (JLCEDA / EasyEDA Official
Library, https://lceda.cn/ , https://easyeda.com , through the browser; nothing but the
answer is kept) and compared with the terminal our pad 1 is.

| Part | Ours | The fab's library | Seen in the previewer | Result |
|---|---|---|---|---|
| PD15-22B/TR8 C161211, x20 `optical` | pad 1 = anode pair, pad 2 = cathode pair (our own numbers) | Everlight's: 1 and 4 cathode (striped side), 2 and 3 anode | stripe on the MID lands before; after the fix, on the summing-node lands, toward the op-amp | **was wrong, fixed** (frame rot 270) |
| LTE-C9901 C2683614, x10 `optical` | KiCad LED_0603: pad 1 = K (LED_ROW) | pin 1 "-", pin 2 "+" | "-" at the LED_ROW end, "+" at the ballast end | holds |
| B5819W C8598, `motor_ctrl` D1, `output_panel` D1 | pad 1 = K (SW) | pin 1 "-", pin 2 "+" | (library only) | holds |
| SMAJ24A C148222, `motor_ctrl` D8, `output_panel` D6 (SMAJ30A until the pre-order review of 2026-10-06: same SMA land, same polarity) | pad 1 = K (+24V) | pins unnamed; the symbol's bar is at pin 1 | `motor_ctrl` D8: "-" at the pad-1 end, at screen resolution | holds for the footprint; the new code has not been seen in the previewer yet, so look at D8 / D6 there |
| SMBJ5.0A C83333, `motor_ctrl` D9 | pad 1 = K (+5V) | pins unnamed; the symbol's bar is at pin 1 | D9: "-" at the pad-1 end, at screen resolution | holds |
| 1N4148WT C917006, `output_panel` D4 | pad 1 = K (+5V, across the relay coil) | pin 1 "K", pin 2 "A" | (library only) | holds |
| BZT52C10T C248313, `output_panel` D8 | pad 1 = K (SW_SENSE) | pin 1 "C", pin 2 "A" | (library only) | holds |
| ESD5B5.0ST1G C93623 (CAN and jack clamps) | either way round | bidirectional | - | no orientation |
| LESD5L5.0CT1G C5274293 (USB clamps) | either way round | no fab footprint yet; LRC's sheet (rev A, 2019) draws two diodes back to back | - | no orientation |

No electrolytic or tantalum capacitor is on any of these boards.

## 4. Hand-entered frames, and what was seen for each

| Frame | Why by hand | What fixes the orientation | Seen |
|---|---|---|---|
| Kycon KPJX-4S-S | the fab numbers pins 3 and 4 the other way | the part goes one way only: nose off the edge, pegs in their holes | body in its outline, nose off the +X edge (2026-10-06, twice) |
| Neutrik NMJ6HCD2 | the fab numbers 1-6, ours are letters | sleeve off the edge, two 3 x 2 hole fields | in its outline after the frame was entered |
| 2x20 socket | the fab numbers its rows the other way | a symmetric field: position only | on its holes, `pi_cap` (seen before the board was redrawn parts-on-front; to be seen again) |
| 2x8 1.27 header | as above | pins leave one side only | pins off the board edge, `pi_cap` |
| AP2114H SOT-223 | the fab calls the tab 4 | three leads one side, tab the other: no second way to sit | on its lands, `optical` |
| PD15-22B | the fab splits each terminal in two | **nothing but the stripe** | the stripe; this is the one that was wrong |
| single spring pin (lighting boards) | one pad | nothing to orient | - |

The lesson in the last column: a hand frame is safe where the part's shape allows one
orientation, and is a guess where it does not. The photodiode was the only hand frame of
the second kind.

## 5. The lighting and UI boards, re-derived (2026-10-06)

Sections 1 to 4 quote these five boards' own records. This section is the same question
asked again from the makers' drawings and the routed boards: **physical position -> our pad
-> net.** Positions are read off the routed `.kicad_pcb` (component side, board +Y up);
the drawings are named with the view they are drawn in.

### 5.1 `ui_board` J1 (1x20 header) <- Newhaven NHD-2.7-12864WDW3

Newhaven's mechanical drawing (sheet dated 08/18/2023, third angle) numbers the row only
in its REAR view: header row along the top edge, **"1" at the left end, "20" at the
right**. Seen from the display face that is pin 1 at the RIGHT with the header edge up.
The row is centred on the module (16.87 + 19 x 2.54 + 16.87 = 82.00), so nothing but that
view says which end is which.

The module stands over our board display face up, header edge toward -Y (the deck pocket
and the two mounting holes allow no other way: turned end for end the module's body would
lie over the knob). A half turn from the drawing's front view puts pin 1 at **-X**.
Routed board: J1 pad 1 at local x -24.13, pad 20 at +24.13, row at y +14.02. **Module pin
n lands on pad n.**

| Module pin (Newhaven p.4, Serial Interface) | Our pad, local x | Net |
|---|---|---|
| 1 VSS | 1, -24.13 | GND |
| 2 VDD | 2, -21.59 | +3V3 |
| 3 NC (BC_VDD) | 3 | open |
| 4 D/C | 4, -16.51 | DC |
| 5-6 VSS | 5, 6 | GND |
| 7 SCLK | 7, -8.89 | SCLK |
| 8 SDIN | 8, -6.35 | SDIN |
| 9 NC | 9 | open |
| 10-14 VSS | 10-14 | GND |
| 15 NC (VCC) | 15 | open |
| 16 /RES | 16, +13.97 | RES_N |
| 17 /CS | 17, +16.51 | CS_N |
| 18 /SHDN | 18, +19.05 | +3V3 |
| 19 BS1, 20 BS0 | 19, 20 (+24.13) | GND: 0 / 0 is 4-wire serial ("MPU Interface Pin Selections", the page after the pin tables) |

State: **holds.** It depends on the socket being soldered to the module's BACK, which
is INSTALL_NOTES' step 2 for this assembly.

### 5.2 `ui_board` SW1 <- Alps RKJXT1F42001

Alps name the terminals and draw the hole pattern "seen from the insertion side", which
is our component side. Every hole was compared by position, from the pattern's centre
(the 15.6 x 15.6 square's): x to the right, y up.

| Alps terminal, position on their drawing | Our pad, at | Net |
|---|---|---|
| Encoder com: top pair, left (-1.5, +7.8) | 9 (-1.5, +7.8) | GND |
| C: top pair, right (+1.5, +7.8) | C (+1.5, +7.8) | SW_C |
| com: under the top pair (-1.0, +5.78) | 6 (-1.0, +5.78) | GND |
| D: left pair, upper (-7.8, +1.5) | D (-7.8, +1.5) | SW_D |
| Encoder A: left pair, lower (-7.8, -1.5) | 8 (-7.8, -1.5) | ENC_A |
| locating hole (-3.8, -1.5) | unnumbered (-3.8, -1.5) | none |
| Encoder B: right pair, upper (+7.8, +1.5) | 7 (+7.8, +1.5) | ENC_B |
| B: right pair, lower (+7.8, -1.5) | B (+7.8, -1.5) | SW_B |
| ground lug (+6.86, -3.75) | 10 (+6.86, -3.75) | GND |
| A: bottom, left (-1.5, -7.8) | A (-1.5, -7.8) | SW_A |
| Push: bottom, right (+1.0, -6.98) | 5 (+1.0, -6.98) | SW_PUSH |

State: **holds**, and the part cannot be fitted another way (eleven holes with no
symmetry). The letters are contacts, not directions: Alps' outline view has the lever
moving toward "A" at the side AWAY from terminal A. Which way is "up" is the Pi's table.

### 5.3 `ui_board` SW2 <- Legion PB-22E85

Six holes, 2 x 3 at 2.50 x 5.40. Our pads 1-2-3 are one row and 4-5-6 the other, and the
two poles carry the same three nets (1 and 4 PWR_SW_DN, 2 and 5 GND, 3 and 6
PWR_SW_UP), so a maker who numbers the rows the other way round -- the fab's footprint
does -- changes nothing. End for end swaps UP and DN: the button's sense, which the
output board's JP1 picks either way. State: **holds by construction**; which throw is
closed with the button out is still a meter reading on the first part.

### 5.4 The seam pogo pins (C5203987) against the lands they meet

One land each, so there is no number: POSITION decides. Both boards of a pair lie in the
same plane the same way up, and the pins meet tip to tip across the seam.

| Pair | Position across the board (local y) | Sending board | Receiving board |
|---|---|---|---|
| foot A +X end -> foot B -X end | +8.88 | J21 +24V | J11 +24V_IN |
| | +5.08 | J22 GND | J12 GND |
| | +1.28 | J23 SCK_OUT | J13 SCK_IN |
| | -2.53 | J24 SDT_OUT | J14 SDT_IN |
| fret key +X end -> fret mid -X end | -9.05 | J11 +14V5 | J11 +14V5 |
| | -4.55 | J12 GND | J12 GND |
| | +11.35 | J13 SCK_SEAM | J13 SCK_SEAM |
| | +15.85 | J14 SDT_SEAM | J14 SDT_SEAM |

State: **holds on the routed boards**, given what the CAD draws: each pair end to end,
both faces the same way. A board of a pair turned over would cross every way.
The pin itself has one pad but is NOT without orientation (section 4 says "nothing to
orient"): the barrel must point off the board's end. Seen in the previewer on all four
boards, 2026-10-06, every row pointing off its own end.

### 5.5 The cable sockets and the ribbon

* `foot_led_a` J1, `fret_led_key` J1 (S4B-XH-SM4-TB): our own lead, `harness.LED_DROP`
  = V24, GND, SCK, SDT (2026-10-07: power, ground, data, data on every JST lead). Routed pads 1 to 4 carry +24V_IN, GND, SCK_CABLE, SDT_CABLE on
  both. Covered by section 2's JST row.
* `ui_board` J2 (2x8, 1.27): `harness.UI_RIBBON` way n on pad n, read back off the routed
  board (1 SW_A ... 8 GND, 9 SCLK, 10 +3V3 ... 16 PWR_SW_DN). Pad 1 is the -Y end of the
  inner row; the even pads are the row at the board's -X edge. The far end is `pi_cap`
  J5, the same footprint.

### 5.6 The RGBW LED (XL-5050RGBW C7371891): which mark was seen

XINGLIGHT's outline drawing (p.9, top view): pins 1 to 4 down the left side (anodes R, G,
B, W), 5 to 8 down the right (their cathodes), and **the "mark" is the cut corner beside
pin 8**, diagonally opposite pin 1. Our footprint is drawn from that view: pad 1 top
left, pad 8 bottom right.

In the fab's previewer (2026-10-06, 2D view) every LED looked at carried the fab model's
cut corner at **our pad 8's corner** and its "1" at our pad 1, beside the board's own
pin-1 tick, for both placements (0 and 180): `foot_led_a` D1-D4 and D15-D18,
`foot_led_b` D1-D5 and D17-D20, `fret_led_key` D11-D20, `fret_led_mid` about ten. The
frame is a measured one, rotation 0.
⚠ What that proves: the fab's model and ours agree on where the cut corner goes. That
the PHYSICAL part's cut corner is at pin 8 is XINGLIGHT's drawing, not something seen;
the fab's assembly review (Confirm Parts Placement) is the check that sees the part.

### 5.7 The LED driver and the regulator

* TLC5971RGER (C543004, VQFN-24): pin 1 by TI's Pin Functions table (SBVS146D). Seen in
  the fab's placement preview on `foot_led_a`, `foot_led_b`, `fret_led_key` and
  `fret_led_mid` (2026-10-06, the re-routed packages): body centred on its lands, the
  fab's pin-1 dot on the board's pin-1 mark, at the angle KiCad wrote (90). Holds.
  `fab_frames.json` carries it by hand (rotation 0, no offset).
* LMR33630BRNXR (C2071384): pin 1 seen at the board's mark on `foot_led_a`,
  `foot_led_b` and `fret_led_key` (2026-10-06).
