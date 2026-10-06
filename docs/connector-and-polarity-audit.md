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
boards in `elec/` (the lighting and UI boards' own records are quoted, not re-derived).
The rule is now in `cadkit/PCB_QUALITY.md` (M1, M2).

## 1. Where a connector meets somebody else's numbering

Every other joint in the instrument is between two of our own boards on a keyed JST lead
whose way order is ONE constant in `elec/harness.py`, asserted by both generators; those
cannot disagree by construction and are listed in section 2. The joints below are the ones
whose far side is a product with its own pin numbers.

| Joint | The other maker's numbering | Translation, and where it is written | State |
|---|---|---|---|
| `output_panel` J6 (Kycon KPJX-4S-S) <- Mean Well GST160A24-R7B | Mean Well: 1 +V, 2 -V, 3 -V, 4 +V on ITS plug drawing | MW 1 / 2 = Kycon 2 / 1, MW 3 / 4 = Kycon 3 / 4. Into the jack, key up: top left pad 1 PWR_GND, top right pad 2 +24V_IN, bottom left pad 3 PWR_GND, bottom right pad 4 +24V_IN. `output_panel.py` at `j6` | **was wrong, fixed** (ec8feae3). Read off three drawings, not a part: the meter check stays (bring-up step 0) |
| `pi_cap` J1 (2x20 socket, back side) <- Raspberry Pi header | the Pi's: pin 1 on the inner row at the end away from the USB ports, pin 2 on the edge row | re-measured today on the routed board, seen from above: pad 1 (124.13, 103.23), pad 2 (124.13, 105.77), pad 39 (75.87, 103.23) in KiCad's frame, so from pad 1 the even row is to one side and the count runs the way the Pi's does seen from its component side (the same handedness; a mirrored socket would give the opposite sign). Pad n is header pin n. `pi_cap.py` quality.pinouts | holds |
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
| SMAJ30A C148230, `motor_ctrl` D8, `output_panel` D6 | pad 1 = K (+24V) | pins unnamed; the symbol's bar is at pin 1 | `motor_ctrl` D8: "-" at the pad-1 end, at screen resolution | holds |
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
| 2x20 socket | the fab numbers its rows the other way | a symmetric field: position only | on its holes, `pi_cap` |
| 2x8 1.27 header | as above | pins leave one side only | pins off the board edge, `pi_cap` |
| AP2114H SOT-223 | the fab calls the tab 4 | three leads one side, tab the other: no second way to sit | on its lands, `optical` |
| PD15-22B | the fab splits each terminal in two | **nothing but the stripe** | the stripe; this is the one that was wrong |
| single spring pin (lighting boards) | one pad | nothing to orient | - |

The lesson in the last column: a hand frame is safe where the part's shape allows one
orientation, and is a guess where it does not. The photodiode was the only hand frame of
the second kind.
