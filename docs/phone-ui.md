# Phone pitch page

A page the Pi serves at **https://public-steel-guitar.home** (also `.local`, and plain
`http://`) with six buttons that move all ten strings together:

| Button | Held | Let go |
| --- | --- | --- |
| PITCH up / down | the strings creep, 35 cents a second | they stay where they are |
| HALF up / down | they go ±1 semitone over 0.25 s | they go back |
| WHOLE up / down | they go ±2 semitones over 0.25 s | they go back |

Each string turns its own motor by its own amount for an interval, from the string model in
`src/dimensions.py`: nut travel = `DL_OPEN · ((f2/f0)² − (f1/f0)²)`, 2 mm of nut per motor
turn. That gives 0.52 turn for a whole tone up from open, the move bronner measured on 11-02.
The model has one `DL_OPEN` (4.0 mm) for every string, so an untuned string turns the same as
the others. A string tuned on /tune plays its MEASURED curve instead (`curves.json`, below):
straight lines between knots, held at the end knot past either end, the same arithmetic as
motor_ctrl's play table. The server reads the curves at start and again after each tune, and
prints which strings have one.

The total raise is capped at **+4 semitones** over open: the pitch-range budget, set by wire
strength (`dimensions.PITCH_UP_ST`). A button that would pass it, or pass **−12**, greys
out: its border goes dashed and its arrow disappears. Lowering is nearly free, and an octave
down still leaves a quarter of the open stretch on the string.

## Look

The page is a bigger panel of the same make as the instrument's screen: 1-bit white on black
like the NHD-2.7-12864WDW3, at about its pixel size (0.48 mm, 3 CSS px), every pixel a whole
number of device pixels, drawn with the 5×7 font in `bench/pi/phone/font.py`. A pressed
button inverts. Nothing draws on the instrument's screen yet, so the font is new. When the
screen gets its own, this one should be replaced by it.

The layout is always portrait, however the phone thinks it is turned (a phone lying flat on
the instrument flips by itself):
- Installed to the home screen on Android, the manifest asks for portrait.
- Everywhere else the page turns itself back by the browser's angle, and touches are judged
  on the turned layout. A press does not go full screen (user, 2026-11-03), and without full
  screen Android will not lock the orientation.

A held button does not buzz the phone: the page cancels each touch at its start, which stops
the phone's long-press timer.

## Safety: no string is left bent

A bend or a creep belongs to the phone that pressed it. It is released when:
- the finger lifts or the touch is cancelled
- the page is hidden or loses focus
- the socket closes
- a holding phone is silent for 1 s (the page pings every 250 ms while held, so a phone that
  sleeps mid-press counts as a release)

## Run it

On a computer, with pretend motors:

```bash
py -3.12 bench/pi/phone/server.py --mock --port 8765
```

then open http://localhost:8765. Tests: `cd bench` then `python -m pytest tests/test_phone.py`.

On the Pi, from the checkout, as your own user with sudo. This names the Pi
`public-steel-guitar`, installs avahi, pyserial and openssl, makes the HTTPS certificates,
copies `bench/` to `/opt/public-steel-guitar/bench`, and starts
`public-steel-guitar-phone.service` on ports 80 and 443 from boot, running as you. Run it
again after any change in `bench/`: the service runs the copy, not the checkout.

```bash
sudo bench/pi/phone/install.sh
```

Then open https://public-steel-guitar.home on a phone on the same network, and use Share,
Add to Home Screen (iPhone) or Install app (Android). The `.home` name is the router's
(a DHCP reservation for the Pi); `.local` is avahi's.

**HTTPS.** install.sh makes a CA on the Pi, once, and a server certificate from it for
`public-steel-guitar.home`, `.local`, the bare name and the Pi's IPv4 addresses at the time
(825 days, the longest a phone accepts). Until a phone trusts the CA it warns on the https
address. To trust it, download http://public-steel-guitar.home/ca.crt on the phone:
- iPhone: install the profile (Settings, Profile Downloaded), then turn it on under
  Settings, General, About, Certificate Trust Settings.
- Android: Settings, Security, Encryption & credentials, Install a certificate, CA certificate.

To remake the certificates (a new IP, a new name), delete `/var/lib/public-steel-guitar-phone/tls` and run
install.sh again. The phones then need the new CA.

**The motor port is shared with the bench scripts: the page holds it only while it is on
screen.** When a page shows, the server opens motor_ctrl's USB port on a thread, and the page
reads NO LINK, with dead buttons, until the motors answer (about 0.3 s). 3 s after the last
page closes or goes to the background, the port is shut. It is not opened while another
process has it open: the page stays at NO LINK, and the server tries again every 2 s. So run
bench scripts with the page closed or the phone locked. A script started while a page shows
shares the port with it, and both get confused: a tty has no lock to stop that. The link's
clock sync asks the board twice, not 40 times: each ask waits out a 0.1 s read, which made
the port take 4 s to open, and the page sends nothing timed on the board's clock.

The motors that answer at the first read are the ones it drives: one motor on the bench
works with no flag (`--strings` still narrows it).

The server talks to motor_ctrl on USB
(the bench package's `link.py` and `servo.py`, found by the files, not the name) and sends each motor an absolute move (F5): acc 0, at an even speed
that makes each half or whole step take `STEP_S` (0.25 s, about a pedal press; user
2026-11-03: 3000 and then 1500 rpm both sounded instant), and a speed matched to the creep for pitch up and down. No firmware change
was needed: motor_ctrl's `Q` line carries the frames as they are.

## What open pitch is

Each motor's encoder count at open pitch is its **home**. The first time the server starts, it
takes the strings as they are as open, so **tune first, then start it**. It keeps the homes
and the pitch-up/down position in `/var/lib/public-steel-guitar-phone/state.json`, and picks them up again on
a restart if the motors are still where the file says. To re-home, retune, delete the file
and restart the service.

## Tuning: /tune (2026-11-04)

`https://public-steel-guitar.home/tune` is a second page: one button per string, in the
same 1-bit look. A tap tunes that string with `bench/publicbench/tune.py`:

1. **Sweep.** The motor visits five points from 400 cents below open to 375 above, the string
   ringing. The foot of the page says PLUCK N whenever it has rung out.
2. **Fit.** Counts are fitted against r = (f / f_open)^2 as a + b r + c r^2.
3. **Open.** The string goes to the fit's open note and is corrected until within 1 cent.
4. **Verify.** Four points on the new curve are played and read. The worst error shows as
   `N DONE / WORST x.xx C`.

The curve is kept in `bench/publicbench/curves.json` and the string's home becomes its open
note. Play is paused for the tune and restored after. Other buttons do nothing while a string
tunes.

The phone tunes and records. It does not write motor_ctrl's table. With every string on its
open note, write the table and re-base with:

    python3 -m publicbench.tune --table

`python3 -m publicbench.tune` tunes every string from a terminal, then writes the table itself.

Notes:
- The open notes are `copedent.json`'s `open`, at A4 = 440.
- The pitch is read off the optical board's SUM, so that board must be on USB.
- The buttons move a tuned string by its measured curve and the others by the model.
- Proven in simulation only (`bench/tests/test_tune.py`): takes.py's plucked string over the
  R1 board's noise floor, on strings stiffer, softer and more curved than the model, and with a
  motor turning either way.

## Not tested yet: needs the bench

- **Which way raises pitch.** `RAISE_SIGN` in `pitchctl.py` is -1 since the 2026-11-05 bench run
  on string 1 (+1 lowered it). Only string 1 has been tried; check an even string (far row) too.
- **The motors' setup**: CAN id N on string N, SR_vFOC mode, enabled. The server enables
  them; it does not set ids or modes (`docs/bench-order.md` does that).
- **The creep's speed** on a real motor: F5 at 1 to 10 rpm, renewed every 50 ms.
- **A real phone.** The page was checked in a desktop browser at phone size, both ways
  round, and at all four rotation angles emulated. It has not been on an iPhone or an Android
  phone, and the Android full-screen lock has not run on one.
- **Ten motors at once**: one frame each per change, 10 frames at 500 kbit/s, about 2.5 ms.
  Measured on one motor only.
- **The F4 count discrepancy** bronner saw (4096 counts moved 4142) would make every move about
  1 % long, if F5 does the same.

## Open questions, decided for now

- The creep rate is 35 cents a second (`CREEP_ST_S`).
- The floor is an octave down (`LOWER_MIN`).
- A bend pressed while another is held replaces it, last press wins.
- Pitch up and a bend can be held together; the creep stops where base + bend reaches +4.
