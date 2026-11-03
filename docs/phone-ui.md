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
The model has one `DL_OPEN` (4.0 mm) for every string, so today every string turns the same.
Measured values per string go in `Driver(dl=...)` once a strung instrument gives them.

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
- On Android, the manifest asks for portrait, and the first press goes full screen and locks
  portrait.
- Everywhere else, iPhone Safari included, the page turns itself back by the browser's angle,
  and touches are judged on the turned layout.

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
copies `bench/pi` and `bench/psgbench` to `/opt/psg/bench`, and starts `psg-phone.service`
on ports 80 and 443 from boot, running as you. Run it again after any change to the page or
`psgbench`: the service runs the copy, not the checkout.

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

To remake the certificates (a new IP, a new name), delete `/var/lib/psg-phone/tls` and run
install.sh again. The phones then need the new CA.

**The motor port is shared with the bench scripts.** The service opens motor_ctrl's USB port
only for a press. It closes it 3 s after the last move, once nothing is held. It does not
open the port while another process has it open: the press does nothing and the page shows NO
LINK until a press finds the port free. So a bench script works whenever no one is pressing,
but a script started while a button is held (or in the 3 s after) shares the port with the
page and both get confused. A tty has no lock to stop that. The first press after the port
was closed waits about 0.2 s while the link syncs.

The motors that answer at the first read are the ones it drives: one motor on the bench
works with no flag (`--strings` still narrows it).

The server talks to motor_ctrl on USB
(`bench/psgbench/link.py`, `servo.py`) and sends each motor an absolute move (F5): acc 0, at an even speed
that makes each half or whole step take `STEP_S` (0.25 s, about a pedal press; user
2026-11-03: 3000 and then 1500 rpm both sounded instant), and a speed matched to the creep for pitch up and down. No firmware change
was needed: motor_ctrl's `Q` line carries the frames as they are.

## What open pitch is

Each motor's encoder count at open pitch is its **home**. The first time the server starts, it
takes the strings as they are as open, so **tune first, then start it**. It keeps the homes
and the pitch-up/down position in `/var/lib/psg-phone/state.json`, and picks them up again on
a restart if the motors are still where the file says. To re-home, retune, delete the file
and restart the service.

## Not tested yet: needs the bench

- **Which way raises pitch.** `RAISE_SIGN` in `pitchctl.py` (or `--raise-sign -1`) is a guess
  until a string is on a motor. Try HALF up with one string and listen.
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
