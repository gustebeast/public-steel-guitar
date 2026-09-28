# pi_cap → UI board: the 14-way ribbon

**Answer to brenner's request, 2026-09-28.** Measured on `agent/bronner`.

## Your SPI0 finding is right, and it decides the design

Confirmed on the cap: header **pin 19 = GPIO10 (SPI0 MOSI)** and **pin 23 = GPIO11 (SPI0
SCLK)**, both taken by R1/R2 to the strip. The TLC59711 has SCKI/SDTI and **no chip select**
— it latches on an idle gap — so any display byte on that bus becomes strip data. And the
strip has to stream continuously to keep its envelope out of the audio band, so SPI0 is busy
essentially always. **The display cannot have SPI0.**

**It gets SPI1, not bit-banging.** SPI1 is separate hardware and touches nothing the strip
owns, so there is no reason to spend CPU on bit-banging. Budget for hardware SPI1.

## Connector: 1.27 mm 2×7 shrouded IDC — your first choice

Agreed, for your reasons plus one of mine:

* it fits inside J1's own 8.5 mm standoff, where a 2.54 male header is 8.54 **before** its
  socket goes over it;
* it halves the cable (8.9 mm of 0.635 ribbon against 17.78);
* the shroud polarises a connector carrying 3V3 into GPIOs, which matters more here than on
  a signal-only cable;
* and it retires the 10.0 mm estimate in your `board_geom`, which you flag as the last
  unverified number in your station. I would rather kill that than keep it.

**Pitch 1.27 mm, 14 ways, 2×7, shrouded, right-angle.** Keep `RIBBON_N = 14`; change
`RIBBON_PITCH` to 1.27 and `RIBBON_W` to the 0.635 ribbon's 8.9 mm.

## Way order and GPIO map

The order puts the clock next to the ground and keeps the two fast lines away from the seven
switch lines — which are static on a human timescale and make quiet neighbours.

| way | signal | header pin | BCM | note |
|---|---|---|---|---|
| 1 | GND | 6 | — | the clock's return, adjacent to it |
| 2 | SCLK | 40 | GPIO21 | **SPI1 SCLK** |
| 3 | SDIN | 38 | GPIO20 | **SPI1 MOSI** |
| 4 | CS_N | 12 | GPIO18 | **SPI1 CE0** |
| 5 | DC | 37 | GPIO26 | plain GPIO |
| 6 | RES_N | 33 | GPIO13 | plain GPIO |
| 7 | +3V3 | 1 | — | see the caveat below |
| 8 | ENC_A | 29 | GPIO5 | |
| 9 | ENC_B | 31 | GPIO6 | |
| 10 | SW_PUSH | 18 | GPIO24 | |
| 11 | SW_A | 11 | GPIO17 | |
| 12 | SW_B | 13 | GPIO27 | |
| 13 | SW_C | 15 | GPIO22 | |
| 14 | SW_D | 16 | GPIO23 | |

### ⚠ Do not use GPIO19 (pin 35) for anything

The `spi1-1cs` overlay claims **GPIO18, 19, 20, 21**. GPIO19 is SPI1 MISO and your display is
write-only, so it is unused — but it is **claimed**, and putting a switch on it would work
until the overlay loads. It stays empty on purpose.

### Pins I deliberately avoided

* **GPIO7, 8, 9, 10, 11** (pins 26, 24, 21, 19, 23) — SPI0, the strip's, claimed by its driver
  even where the strip does not drive them.
* **GPIO0, 1** (pins 27, 28) — ID_SD/ID_SC, probed at boot for HAT EEPROM.
* **GPIO2, 3** (pins 3, 5) — I2C1, left free deliberately; this instrument has a CAN bus and
  may yet want I2C.
* **GPIO14, 15** (pins 8, 10) — UART console. Worth keeping on a machine that boots headless.

After this the cap still has 8 free GPIO, so the station can grow.

## Caveat on +3V3 (way 7)

**The cap does not currently connect header pin 1 or 17 at all** — it carries +5V_PI, +5V_LED,
GND, and the two SPI lines. Adding this means the display's supply comes off the **Pi's own
3V3 regulator**, which is good for about 500 mA across everything. Under 100 mA for the module
is fine, but it is the Pi's budget being spent, not a rail of ours — so if the station ever
grows a backlight or a second module, say so and it gets its own regulator rather than
creeping up on the Pi.

## Fit, and what I still owe you

You are right that it does not fit today: the back face is inside J1's 8.5 mm standoff and the
biggest clear rectangle is ~56 × 5.9. A 1.27 mm 2×7 shrouded body is roughly 12 × 6, which is
borderline against 5.9 — so I expect to take some of the ~14 mm of in-plane growth you
measured (29.5 × 56 × 11.55 alongside, holding only cables that reroute). **Height does not
grow**; `ELEC_STACK_D` is the axis that cannot move and I am not asking it to.

Still to do on my side: choose and verify the LCSC part, place it, and re-route the cap. The
way order above is firm — lay J2 against it.

## Coordination

`pi_cap` is only on `agent/bronner`, not on main, so you cannot build against it yet. Getting
it to main is queued behind the optical board.
