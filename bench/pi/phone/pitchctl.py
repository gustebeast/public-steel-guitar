"""What the six buttons do to the ten strings, and the two motor backends.

All ten strings move together. A position is a number of SEMITONES above each string's own
open tuning, and each string turns its motor by its own amount for it, from the string model
in src/dimensions.py (the carriage travel between two pitches is DL_OPEN * ((f2/f0)^2 -
(f1/f0)^2); the screw lead is 2 mm and the belt is 14:14, so one motor turn is 2 mm of nut).
0.52 turn is a whole tone up from open, which is what bronner measured the motor doing.

    base    where pitch up / pitch down leave the strings: it creeps while one is held and
            stays where it is let go
    bend    0, +-1 or +-2 on top of base while half / whole step is held; 0 again on release

Limits: base + bend never goes over RAISE_MAX (the pitch-range budget: wire strength holds the
raise to about 4 semitones, docs and src/dimensions.PITCH_UP_ST) nor under LOWER_MIN (lowering
is nearly free; an octave down still leaves a quarter of the open stretch on the string).
"""
from __future__ import annotations

import json
import math
import os
import time

DL_OPEN = 4.0             # mm, src/dimensions.DL_OPEN: the same for every string in the model
LEAD = 2.0                # mm of nut per motor turn: Tr8x2 lead, 14:14 belt
COUNTS_PER_TURN = 0x4000
RAISE_MAX = 4.0           # semitones over open, base + bend
LOWER_MIN = -12.0
CREEP_ST_S = 0.35         # pitch up / down: 35 cents a second
SLOW_RPM_MIN = 1
# half and whole steps: half the 3000 rpm of bronner's 11-02 step (90 % of a whole tone in
# 39 ms), user 2026-11-03
FAST_RPM, FAST_ACC = 1500, 0
STRINGS = tuple(range(1, 11))       # string N = CAN id N on bus A
# Which way a motor turns to RAISE pitch. Not known until a string is on a motor: the bench
# finds it (docs/phone-ui.md) and sets it here, or with --raise-sign.
RAISE_SIGN = +1


def turns(semitones: float, dl_open: float = DL_OPEN) -> float:
    """Motor turns from open pitch to `semitones` above it (negative: below)."""
    return dl_open * (2.0 ** (semitones / 6.0) - 1.0) / LEAD


class Pitch:
    """The buttons' state. Owners are client ids, so one phone's release can only undo what
    that phone pressed, and a client that vanishes takes its holds with it."""

    def __init__(self, base: float = 0.0):
        self.base = base
        self.creep = {}           # owner -> +1 / -1
        self.bend = None          # (owner, semitones)

    @property
    def target(self) -> float:
        return self.base + (self.bend[1] if self.bend else 0.0)

    def can(self, button: str) -> bool:
        n = BENDS.get(button)
        if n is not None:
            t = self.base + n
            return LOWER_MIN - 1e-9 <= t <= RAISE_MAX + 1e-9
        if button == "pu":
            return self.base < RAISE_MAX - 1e-9
        if button == "pd":
            return self.base > LOWER_MIN + 1e-9
        return False

    def press(self, owner, button: str) -> bool:
        if not self.can(button):
            return False
        if button in ("pu", "pd"):
            self.creep[owner] = 1 if button == "pu" else -1
        else:
            self.bend = (owner, BENDS[button])
        return True

    def release(self, owner, button: str | None = None):
        """button None: everything this owner holds (a lost connection, a page hidden)."""
        if button in (None, "pu", "pd"):
            self.creep.pop(owner, None)
        if button is None or button in BENDS:
            if self.bend and self.bend[0] == owner and (button is None or BENDS[button] == self.bend[1]):
                self.bend = None

    def tick(self, dt: float):
        d = sum(self.creep.values())
        if d:
            d = 1 if d > 0 else -1
            hi = RAISE_MAX - (max(self.bend[1], 0.0) if self.bend else 0.0)
            self.base = min(max(self.base + d * CREEP_ST_S * dt, LOWER_MIN), hi)

    def state(self) -> dict:
        return {"base": round(self.base, 4), "bend": self.bend[1] if self.bend else 0,
                "can": {b: self.can(b) for b in BUTTONS}, "max": RAISE_MAX, "min": LOWER_MIN}


BENDS = {"hu": 1.0, "hd": -1.0, "wu": 2.0, "wd": -2.0}
BUTTONS = ("pu", "pd", "hu", "hd", "wu", "wd")


# ── backends ──────────────────────────────────────────────────────────────────────────────
class MockMotors:
    """Ten pretend motors that go where they are told at the speed asked."""
    name = "mock"

    def __init__(self, strings=STRINGS):
        self.strings = tuple(strings)
        self.pos = {s: 0 for s in self.strings}       # counts
        self.goal = dict(self.pos)
        self.rpm = {s: 0 for s in self.strings}
        self.log = []                                  # (t, string, counts, rpm, acc)
        self._t = time.monotonic()
        self.ok = True

    def home(self):
        return dict(self.pos)

    def move(self, string: int, counts: int, rpm: int, acc: int):
        self._advance()
        self.goal[string], self.rpm[string] = counts, rpm
        self.log.append((time.monotonic(), string, counts, rpm, acc))

    def _advance(self):
        now = time.monotonic()
        dt, self._t = now - self._t, now
        for s in self.strings:
            step = self.rpm[s] / 60.0 * COUNTS_PER_TURN * dt
            d = self.goal[s] - self.pos[s]
            self.pos[s] = self.goal[s] if abs(d) <= step else self.pos[s] + int(math.copysign(step, d))

    def positions(self):
        self._advance()
        return dict(self.pos)

    def close(self):
        pass


class PortBusy(RuntimeError):
    pass


def port_holders(dev: str) -> list[int]:
    """Pids of other processes with `dev` open (Linux /proc). A tty has no lock of its own:
    two processes can both open it, and then each reads half the other's replies."""
    real, out = os.path.realpath(dev), []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            fds = os.listdir("/proc/%s/fd" % pid)
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink("/proc/%s/fd/%s" % (pid, fd)) == real:
                    out.append(int(pid))
                    break
            except OSError:
                pass
    return out


class MotorCtrlMotors:
    """The SERVO42Ds through motor_ctrl's USB link (bench/psgbench: link.py, servo.py).

    THE PORT IS OPENED ONLY TO MOVE (user, 2026-11-03): the bench scripts use the same USB
    port, so it is opened on a move and closed IDLE_CLOSE after the last one (the caller
    says when nothing is held, `idle`). It is not opened while another process has it: the
    move fails, and the page shows NO LINK. The motors hold their place with the port shut."""
    name = "motor_ctrl"
    IDLE_CLOSE = 3.0

    def __init__(self, strings=STRINGS, port=None):
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.normpath(os.path.join(here, "..", "..")))     # bench/
        from psgbench import servo
        from psgbench import link
        self.servo, self._link_mod, self.port = servo, link, port
        self.strings = tuple(strings)
        self.link, self.motors = None, {}
        self._used = 0.0
        self.ok = True

    def _open(self):
        if self.link is None:
            dev = self.port or self._link_mod.find_motor_port()
            who = port_holders(dev)
            if who:
                raise PortBusy("%s is open in pid %s" % (dev, ",".join(map(str, who))))
            self.link = self._link_mod.MotorCtrlLink(dev)
            self.motors = {s: self.servo.Servo(self.link, s) for s in self.strings}
            for m in self.motors.values():
                m.enable(True)
            self.ok = True
        self._used = time.monotonic()

    def idle(self):
        if self.link is not None and time.monotonic() - self._used > self.IDLE_CLOSE:
            self.close()

    def home(self):
        """Where each motor is. A motor that does not answer is dropped, so the bench runs
        with however many are on the bus; none answering is an error."""
        self._open()
        out = {}
        for s, m in self.motors.items():
            try:
                out[s] = m.position()
            except (TimeoutError, RuntimeError):
                pass
        if not out:
            raise RuntimeError("no motor answered (strings %s)" % (self.strings,))
        if len(out) < len(self.strings):
            print("motors answering: strings %s" % sorted(out), flush=True)
            self.strings = tuple(sorted(out))
            self.motors = {s: self.motors[s] for s in self.strings}
        return out

    def move(self, string: int, counts: int, rpm: int, acc: int):
        self._open()
        if string in self.motors:
            self.motors[string].move_abs(counts, rpm, acc)

    def positions(self):
        self._open()
        out = {}
        for s, m in self.motors.items():
            try:
                out[s] = m.position(timeout=0.2)
            except TimeoutError:
                self.ok = False
        return out

    def close(self):
        if self.link is not None:
            self.link._run = False
            time.sleep(0.15)                       # the reader's read times out at 0.1
            self.link.ser.close()
            self.link, self.motors = None, {}


# ── the driver: Pitch -> motor targets ────────────────────────────────────────────────────
class Driver:
    """Turns a Pitch into absolute motor targets. `home` is each motor's count at OPEN pitch,
    kept in `state_path` so a restart mid-creep does not take the creep as open."""

    def __init__(self, motors, pitch: Pitch, state_path=None, raise_sign=RAISE_SIGN, dl=None):
        self.m, self.p, self.sign = motors, pitch, raise_sign
        self.dl = dl or {s: DL_OPEN for s in motors.strings}
        self.state_path = state_path
        self.home = None
        self.sent = None
        self._bend_sent = 0.0
        self._saved = None
        try:
            self.ensure_home()
        except Exception as e:              # the port is busy or the board is off: on a press
            print("motors not read at start:", e, flush=True)

    def ensure_home(self):
        """Read where the motors are, once. They are at base (no bend is held on them), so
        nothing is sent until the target leaves it."""
        if self.home is None:
            self.home = self._load_home()
            self.sent = self.p.base

    def counts(self, s: int, semitones: float) -> int:
        return self.home[s] + int(round(self.sign * turns(semitones, self.dl[s]) * COUNTS_PER_TURN))

    def _load_home(self):
        now = self.m.home()
        if self.state_path and os.path.exists(self.state_path):
            try:
                st = json.load(open(self.state_path))
                home = {int(k): v for k, v in st["home"].items()}
                base = float(st["base"])
                ok = all(s in home and abs(now[s] - (home[s] + self.sign * turns(base, self.dl[s]) * COUNTS_PER_TURN))
                         < 0.02 * COUNTS_PER_TURN for s in self.m.strings)
                if ok:
                    self.p.base = base
                    return home
            except (ValueError, KeyError, OSError):
                pass
        return dict(now)          # where the strings are now is open pitch

    def save(self):
        if not self.state_path or self.home is None:
            return
        st = {"home": self.home, "base": round(self.p.base, 4)}
        if st != self._saved:
            tmp = self.state_path + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(st, fh)
            os.replace(tmp, self.state_path)
            self._saved = st

    def step(self, dt: float):
        """Called every tick: send new targets when the target moved."""
        if self.home is None:
            if not self.p.creep and self.p.bend is None:
                return                      # no press to read them for: leave the port alone
            self.ensure_home()
        was = self.sent
        t = self.p.target
        bend = self.p.bend[1] if self.p.bend else 0.0
        if was is not None and abs(t - was) < 1e-6:
            return
        fast = was is None or bend != self._bend_sent      # a step pressed or let go: quick
        self._bend_sent = bend
        for s in self.m.strings:
            c = self.counts(s, t)
            if fast:
                rpm, acc = FAST_RPM, FAST_ACC
            else:
                d = abs(c - self.counts(s, was)) / COUNTS_PER_TURN
                rpm = int(min(FAST_RPM, max(SLOW_RPM_MIN, math.ceil(1.5 * d / max(dt, 1e-3) * 60.0))))
                acc = FAST_ACC
            self.m.move(s, c, rpm, acc)
        self.sent = t
