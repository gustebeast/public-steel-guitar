"""Tuning: each string's motor counts against its pitch, measured, so the table motor_ctrl plays
from (copedent.py) stops using the model curve, and every string left at its open note.

    python3 -m publicbench.tune                 every string, one after the other
    python3 -m publicbench.tune --strings 3,4   only these
    python3 -m publicbench.tune --dry           measure and report; write nothing

For each string, with the string RINGING (pluck it when asked; a step while it rings is how the
bench measured the motor, 2026-11-02):
  1 SWEEP   move the motor to a few points from SWEEP_CENTS below open to above it, the counts for
            each from the model curve, and read the pitch at each
  2 FIT     counts = a + b r + c r^2, r = (f / f_open)^2. Counts are about linear in r (the
            string's tension goes as f^2, its stretch as the tension); c takes the rest
            (the wrap, the bridge, the screw's lash)
  3 OPEN    go to the fit's counts for r = 1, read, correct along the fit's slope until the
            string is within TOL_CENTS of its open note
  4 VERIFY  play VERIFY_CENTS from there on the curve the fit gives and read each; the worst
            error is the string's mark
Then the curves go into CURVES (copedent.py compiles the table from it), the table is written to
motor_ctrl, every motor sitting at its string's open note is made the base ('P Z') and play is
switched back on ('P 1').

Knots outside the swept range are the fit carried on (extrapolated): the sweep stays inside the
pitch-range budget (RAISE_MAX), and the table's knots reach further than a string should go.
The result says which.

The hardware: motor_ctrl's link (servo frames straight to bus A, play off while tuning) and the
optical board's stream (the string's SUM signal). Rig and Ear are the two halves the tests
replace (bench/tests/test_tune.py).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import sys
import time

import numpy as np

from . import copedent, pitch, servo

CURVES = os.path.join(os.path.dirname(__file__), "curves.json")
SWEEP_CENTS = (-400, -200, 0, 200, 375)    # the top one short of RAISE_MAX: a line aims it a little long
RAISE_MAX = 400                 # cents over open: phone/pitchctl.py RAISE_MAX, the wire's budget
VERIFY_CENTS = (-300, -100, 100, 300, 0)
TOL_CENTS = 1.0
OPEN_TRIES = 5
LISTEN_S = 0.3
RPM, ACC = 600, 0
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_hz(name: str, a4: float = 440.0) -> float:
    """'A4' -> 440, 'C#3', 'Eb2' ..."""
    n, rest = NAMES[name[0].upper()], name[1:]
    while rest and rest[0] in "#b":
        n += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return a4 * 2.0 ** ((n - 9) / 12.0 + int(rest) - 4)


def cents(f: float, ref: float) -> float:
    return 1200.0 * math.log2(f / ref)


class Pluck(Exception):
    """The string has stopped ringing: ask for a pluck and try again."""


class Rig:
    """The motors, through motor_ctrl. Counts are the motor's own (encoder, accumulated).
    sign: which way a motor turns to RAISE pitch (phone/pitchctl.py RAISE_SIGN); only the
    sweep's first guesses use it, the fit takes whichever way the string went."""

    def __init__(self, link, ids=None, sign=+1):
        self.link = link
        self.sign = sign
        self.ids = ids or {n: n for n in range(1, copedent.STRINGS + 1)}
        self.servos = {n: servo.Servo(link, i) for n, i in self.ids.items()}

    def play(self, on: bool):
        r = self.link.ask("P %d" % (1 if on else 0))
        if r[:1] != ["OK"]:
            raise RuntimeError("motor_ctrl: P %d refused: %s" % (on, " ".join(r)))

    def playing(self) -> bool:
        r = self.link.ask("P")
        return len(r) > 2 and r[0] == "P" and r[2] == "1"

    def position(self, n: int) -> int:
        return self.servos[n].position()

    def goto(self, n: int, counts: int, timeout: float = 3.0):
        s = self.servos[n]
        s.enable(True)
        s.move_abs(int(counts), RPM, ACC)
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            if abs(s.position() - counts) <= 2:
                return
            time.sleep(0.02)
        raise TimeoutError("string %d's motor did not reach %d" % (n, counts))

    def rebase(self):
        r = self.link.ask("P Z")
        if r[:1] != ["OK"]:
            raise RuntimeError("motor_ctrl: P Z refused: %s" % " ".join(r))


class Ear:
    """One string's pitch off the optical board: LISTEN_S of its SUM, tracked round a guess."""

    def __init__(self, optical, floor: float = 13.0):
        self.o = optical
        self.floor = floor          # counts rms: takes.py FLOOR, the R1 board's measured floor

    def record(self, n: int, seconds: float):
        from .optical import string_inputs, string_signal
        self.o.select([string_inputs(n)[0]])
        time.sleep(seconds)
        _first, x, _d = string_signal(self.o.take(), n)
        return x, 48000.0

    def hz(self, n: int, f_guess: float | None) -> float:
        x, sr = self.record(n, LISTEN_S)
        return measure(x, sr, f_guess, self.floor)


def measure(x, sr: float, f_guess: float | None, floor: float) -> float:
    """The fundamental of a ringing string, Hz; Pluck if it is not ringing. With no guess the
    lowest strong peak (pitch.guess) is taken first."""
    x = np.asarray(x, dtype=float)
    if np.sqrt(np.mean(x ** 2)) < 4 * floor:
        raise Pluck()
    if f_guess is None:
        f_guess = pitch.guess(x, sr)
    f, env = pitch.track(x, sr, f_guess, span_semitones=4.0)
    k = len(f) // 5
    mid, e = f[k:-k], env[k:-k]
    loud = mid[e > 0.5 * np.median(e)]
    return float(np.median(loud if len(loud) else mid))


class Fit:
    """counts = a + b r + c r^2 against r = (f / f0)^2."""

    def __init__(self, f0: float, pts, deg: int | None = None):
        self.f0 = f0
        r = np.array([(f / f0) ** 2 for _c, f in pts])
        y = np.array([c for c, _f in pts], dtype=float)
        deg = deg or (2 if len(pts) >= 4 else 1)
        self.p = np.polyfit(r, y, deg)
        self.lo, self.hi = cents(min(f for _c, f in pts), f0), cents(max(f for _c, f in pts), f0)
        self.resid = [cents(self.hz(c), f0) - cents(f, f0) for c, f in pts]

    def counts(self, c: float) -> float:
        return float(np.polyval(self.p, 2.0 ** (c / 600.0)))

    def slope(self, c: float) -> float:
        """counts per cent at c."""
        r = 2.0 ** (c / 600.0)
        return float(np.polyval(np.polyder(self.p), r)) * r * math.log(2) / 600.0

    def hz(self, counts: float) -> float:
        """The inverse, near the swept range: the root of the fit nearest r = 1."""
        q = self.p.copy()
        q[-1] -= counts
        roots = [x.real for x in np.roots(q) if abs(x.imag) < 1e-9 and x.real > 0]
        return self.f0 * math.sqrt(min(roots, key=lambda x: abs(x - 1.0)))

    def shift(self, by: float):
        self.p[-1] += by


def listen(ear, n, f_guess, ask, tries=3):
    for _ in range(tries):
        try:
            return ear.hz(n, f_guess)
        except Pluck:
            ask(n)
    raise RuntimeError("string %d: not ringing after %d plucks" % (n, tries))


def tune_string(rig, ear, n: int, f_open: float, ask, log=print):
    """One string: sweep, fit, open, verify. Leaves the motor at the open note. Returns the
    record CURVES keeps for it."""
    model = copedent.model_curve()
    def mc(c):                                      # the model's counts from open at c cents
        return rig.sign * copedent.counts(model, int(round(c)))
    here = rig.position(n)
    ask(n)
    f = listen(ear, n, None, ask)
    now = cents(f, f_open)
    log("string %d: %.2f Hz, %+.1f cents from %.2f" % (n, f, now, f_open))
    if now > RAISE_MAX + 50:
        raise RuntimeError("string %d is %+.0f cents over open: slacken it by hand first" % (n, now))
    origin = here - mc(now)                         # where open would be, by the model
    pts = [(here, f)]
    for c in SWEEP_CENTS:
        # the model aims the first point; each later one is aimed by a line through the
        # points read so far, so a string stiffer or softer than the model still spans the sweep
        aim = Fit(f_open, pts, deg=1).counts(c) if len(pts) >= 2 else origin + mc(c)
        tgt = int(round(aim))
        rig.goto(n, tgt)
        guess = f_open * 2 ** (c / 1200.0)
        f = listen(ear, n, guess, ask)
        pts.append((tgt, f))
        log("  sweep %+5d c: %d counts, %.2f Hz (%+.1f c)" % (c, tgt, f, cents(f, f_open)))
        if cents(f, f_open) > RAISE_MAX:
            break
    fit = Fit(f_open, pts)
    log("  fit: worst %.2f cents off its points" % max(abs(x) for x in fit.resid))
    at = int(round(fit.counts(0)))
    for _ in range(OPEN_TRIES):
        rig.goto(n, at)
        f = listen(ear, n, f_open, ask)
        e = cents(f, f_open)
        log("  open: %d counts, %+.2f cents" % (at, e))
        if abs(e) <= TOL_CENTS:
            break
        fit.shift(at - fit.counts(e))               # the fit through what was just read
        at = int(round(fit.counts(0)))
    else:
        raise RuntimeError("string %d did not come within %.1f cents of open" % (n, TOL_CENTS))
    fit.shift(at - fit.counts(e))
    curve = [int(round(fit.counts(k) - fit.counts(0))) for k in copedent.KNOT_CENTS]
    curve[copedent.KNOT_CENTS.index(0)] = 0
    worst = 0.0
    for c in VERIFY_CENTS:
        rig.goto(n, at + copedent.counts(curve, c))
        f = listen(ear, n, f_open * 2 ** (c / 1200.0), ask)
        err = cents(f, f_open) - c
        worst = max(worst, abs(err))
        log("  verify %+5d c: %+.2f cents off" % (c, err))
    out = {"open_hz": round(f_open, 3), "open_counts": at, "curve": curve,
           "fit": [float(x) for x in fit.p], "swept": [round(fit.lo, 1), round(fit.hi, 1)],
           "extrapolated": [k for k in copedent.KNOT_CENTS if k < fit.lo - 25 or k > fit.hi + 25],
           "verify_worst_cents": round(worst, 2), "when": time.strftime("%Y-%m-%d %H:%M")}
    log("  string %d: verify worst %.2f cents" % (n, worst))
    return out


def load(path: str = CURVES) -> dict:
    if not os.path.isfile(path):
        return {"note": "", "strings": {}}
    return json.load(open(path))


def curves_for(data: dict) -> list[list[int]]:
    """Every string's curve for copedent.compile_table: the measured one, else the model's."""
    return [data["strings"].get(str(n), {}).get("curve") or copedent.model_curve()
            for n in range(1, copedent.STRINGS + 1)]


def save(data: dict, path: str = CURVES):
    data["note"] = ("Written by publicbench.tune: each string's measured motor counts from its open "
                    "note at copedent.KNOT_CENTS (curve), and how it was found. copedent.py compiles "
                    "the table from it; a string not here plays the model curve.")
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, path)


@contextlib.contextmanager
def paused(rig, on_after: bool | None = True):
    """Play off for the block (the tuner has the motors to itself), then on again -- or, with
    on_after None, as it was before."""
    was = rig.playing() if on_after is None else on_after
    rig.play(False)
    try:
        yield
    finally:
        rig.play(was)


def write_table(rig, data: dict, cop: dict, log=print):
    """The table from CURVES into motor_ctrl, and every motor's place now made open pitch
    ('P Z'): only right with every string sitting on its open note."""
    st = copedent.write(rig.link, copedent.compile_table(cop, curves=curves_for(data)))
    log("motor_ctrl: table %s" % st[5])
    rig.rebase()


def tune(rig, ear, strings, cop, ask, path=CURVES, write=True, log=print):
    """Tune `strings`; then (write) the table to motor_ctrl, the base, play back on. Every
    string asked for is left at its open note, also when write is off."""
    data = load(path)
    with paused(rig):
        for n in strings:
            data["strings"][str(n)] = tune_string(rig, ear, n, note_hz(cop["open"][n - 1]), ask, log)
            if write:
                save(data, path)
        if write:
            write_table(rig, data, cop, log)
    return data


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("--strings", default=",".join(str(n) for n in range(1, copedent.STRINGS + 1)))
    a.add_argument("--copedent", default=copedent.DEFAULT)
    a.add_argument("--curves", default=CURVES)
    a.add_argument("--dry", action="store_true", help="tune, but write neither CURVES nor the table")
    a.add_argument("--raise-sign", type=int, choices=(-1, 1), default=1)
    a.add_argument("--table", action="store_true",
                   help="tune nothing: write the table from CURVES and make every motor's place "
                        "open pitch (after strings were tuned one at a time, e.g. from the phone)")
    o = a.parse_args(argv)
    from .link import MotorCtrlLink
    if o.table:
        link = MotorCtrlLink()
        try:
            rig = Rig(link)
            with paused(rig, None):
                write_table(rig, load(o.curves), copedent.load(o.copedent))
        finally:
            link.close()
        return 0
    from .optical import OpticalLink
    link, opt = MotorCtrlLink(), OpticalLink()
    try:
        def ask(n):
            print(">>> pluck string %d" % n, flush=True)
            time.sleep(1.0)
        tune(Rig(link, sign=o.raise_sign), Ear(opt), [int(x) for x in o.strings.split(",")], copedent.load(o.copedent),
             ask, o.curves, write=not o.dry)
    finally:
        opt.close()
        link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
