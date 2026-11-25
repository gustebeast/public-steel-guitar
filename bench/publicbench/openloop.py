"""Can a stepper run OPEN LOOP do this instrument's job? Asked of the SERVO42D we already have, in
its open-loop bus mode (SR_OPEN, mode 3), on string 1 through motor_ctrl (user, 2026-11-24).

    python3 -m publicbench.openloop                     the automatic tests (below), ~10 min
    python3 -m publicbench.openloop --only speed,lag    some of them
    python3 -m publicbench.openloop --only speed --speed-ma 1400,1000
                                                        gate 2 at a TMC2209's current
    python3 -m publicbench.openloop --reenable 20       + 20 coils-off/on cycles, power left on
    python3 -m publicbench.openloop --powercycle 5      + 5 power cycles: it asks you to switch the
                                                        motor's 24 V off and on, and waits
    python3 -m publicbench.openloop --listen            + a listening pass: it asks you each step
    python3 -m publicbench.openloop --report            the runs logged so far
    python3 -m publicbench.openloop --sim               the same code against publicbench.sim

WHAT IT IS FOR: the plan is a raw NEMA 17 on our own TMC5240-class drivers, no encoder. The two
bench gates before that design is modelled (lead, 2026-11-24) are
  GATE 1  the driver keeps its coil phase while its outputs are off, so a restore at power-up
          pulls the rotor back to where it was (the TMC5240 half is a driver-board test);
  GATE 2  a whole tone under string load in about the 39 ms the closed loop does.
The SERVO42D cannot answer either for the TMC5240, but in SR_OPEN it is an open-loop stepper with
an encoder we can still read, so it measures the MOTOR and STRING half of both, today:
  current    lost steps against working current (whole tones out and back, a ramp): the torque
             margin under string load.                                     -> GATE 2 (margin)
  lag        where open loop settles against where it was told, raising vs lowering, per
             current, in counts and model cents: the accuracy cost.        -> both (accuracy)
  speed      90 % time and lost steps for a whole tone per rpm/acc, full current. Its firmware's
             open-loop speed cap is NOT the motor's: a time here is an upper bound.  -> GATE 2
  reenable   coils off (F3 0) with power on, then on: the settle while off, and whether the
             motor's own driver pulls it back when the coils come on.      -> GATE 1 (analogue)
  powercycle 24 V off and on (prompted): the settle, and the jump when the driver starts at its
             own phase, which is what a phase restore has to undo.         -> GATE 1 (size)
  listen     open-loop standstill noise at each current, by ear (prompted): the reason for the
             change (only coils OFF was quiet in closed loop, 2026-11-19).
Every number is appended to ~/openloop.jsonl.

SAFE BY CONSTRUCTION (lead, 2026-11-24):
  * THE MOTOR IS PUT BACK, whatever happens: SR_vFOC, DEFAULT_MA working current, enabled and
    zeroed, in a `finally` (an error, Ctrl-C and SIGTERM all reach it). The hold-current
    setting (0x9B) is never sent: its default is not known, so it could not be put back.
  * EVERY TARGET IS INSIDE THE STRING'S TRAVEL: start +- a whole tone (pedaldrive's throw at
    --semitones 2, its widest), checked before each move; and IN ENCODER TERMS, so lost steps
    cannot walk the nut: open loop's axis drifts from the shaft when it loses steps, so each
    target is sent through the offset last measured, and a reading past the limit by more than
    a step stops the run.
Stop the phone service first (it shares the serial port): sudo systemctl stop public-steel-guitar-phone
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import statistics as st
import time

from . import servo
from .pedaldrive import DL_OPEN, LEAD, throw_counts
from .springload import RAISE_SIGN

T = servo.COUNTS_PER_TURN
STEP = T / 200.0                        # one full step of a 1.8 deg motor: 81.92 counts
LOG = os.path.expanduser("~/openloop.jsonl")
SEMITONES = 2.0                         # a whole tone: the widest pedaldrive throws
CURRENTS = (1600, 1400, 1200, 1000, 800, 500, 300, 200)   # mA, down from the default; 1400 and 1000
                                        # bracket what a TMC2209 holds on a board (lead, 11-24)
LAG_RPM, LAG_ACC = 600, 230             # the current/lag moves: a ramp open loop can follow
SPEEDS = ((300, 230), (600, 230), (1000, 230), (1500, 230), (600, 0), (1200, 0))
TESTS = ("current", "lag", "speed")
WINDOW, SETTLE = 0.6, 0.4                # s: polled through a move, then left to settle


class Abort(RuntimeError):
    pass


def cents(counts: float) -> float:
    """Model cents of a raise of `counts` from open on this rig (pedaldrive's string model)."""
    x = 1.0 + counts * LEAD / (T * DL_OPEN)
    return 1200.0 * 6.0 * math.log2(x) / 12.0 if x > 0 else float("nan")


class Rig:
    """String 1's motor in SR_OPEN, every move kept inside start +- a whole tone."""

    def __init__(self, link, can_id=1, raise_sign=RAISE_SIGN, semitones=SEMITONES):
        self.link, self.m = link, servo.Servo(link, can_id)
        self.sign = raise_sign
        self.lo, self.hi = sorted((raise_sign * throw_counts(-semitones),
                                   raise_sign * throw_counts(semitones)))
        self.home = None                # encoder counts at the start
        self.off = 0.0                  # encoder - axis, as last measured
        self.sent = []                  # every target sent, in encoder counts from home

    # ── the bus ──
    def ask(self, body: bytes, timeout=0.5):
        """Send a command and wait for its reply: its value."""
        n = len(self.link.rx)
        self.m._send(body)
        f = self.link.wait_frame(self.m._mine(body[0]), n, timeout)
        if f is None:
            raise TimeoutError("motor did not answer 0x%02X" % body[0])
        return servo.parse(self.m.id, f.data)[1]

    def must(self, body: bytes, what: str):
        v = self.ask(body)
        if v != 1:
            raise Abort("%s refused (reply %r)" % (what, v))

    def enc(self) -> int:
        return self.ask(bytes([servo.READ_ENCODER]))

    def enable(self, on: bool):
        self.must(bytes([servo.ENABLE, 1 if on else 0]), "enable %d" % on)

    def current(self, ma: int):
        self.must(bytes([servo.SET_CURRENT]) + int(ma).to_bytes(2, "big"), "current %d mA" % ma)

    def mode(self, m: int):
        self.must(bytes([servo.SET_MODE, m]), "mode %d" % m)

    # ── moves, in encoder counts from home ──
    def check(self, rel: float):
        if not self.lo <= rel <= self.hi:
            raise Abort("target %+.0f counts is outside the string's travel %+d..%+d"
                        % (rel, self.lo, self.hi))

    def where(self) -> float:
        rel = self.enc() - self.home
        if not self.lo - 2 * STEP <= rel <= self.hi + 2 * STEP:
            raise Abort("the shaft is at %+.0f counts, past the travel %+d..%+d: stopped"
                        % (rel, self.lo, self.hi))
        return rel

    def move(self, rel: float, rpm: int, acc: int) -> dict:
        """One absolute move to `rel` (encoder counts from home), polled the whole way."""
        self.check(rel)
        a = self.where()
        axis = int(round(self.home + rel - self.off))
        self.sent.append(rel)
        n0 = len(self.link.rx)
        seq = self.m.move_abs(axis, rpm, acc)
        end = time.monotonic() + WINDOW
        while time.monotonic() < end:
            self.m._send(bytes([servo.READ_ENCODER]))
            time.sleep(0.003)
        time.sleep(SETTLE)
        fin = [self.where() for _ in range(5)]
        got = st.mean(fin)
        self.off = (self.home + got) - axis
        frames = self.link.rx[n0:]
        t0 = self.link.sent.get(seq)
        enc = [(t, c - self.home) for t, c in self.m.positions(frames)]
        span = rel - a
        t90 = next((t - t0 for t, c in enc if t0 and span and (c - a) / span >= 0.9), None)
        arr = self.m.arrived(frames)
        miss = got - rel
        return dict(target=rel, rpm=rpm, acc=acc, t90=t90, polls=len(enc),
                    arrived=(arr[0] - t0) if arr and t0 else None,
                    miss=miss, steps_lost=int(round(miss / STEP)),
                    up=(span * self.sign) > 0)

    def tone(self, rpm, acc, reps):
        """Whole tones out and straight back, raising then lowering: the nut never walks."""
        out = []
        for _ in range(reps):
            for d in (self.hi, self.lo):
                out.append(dict(self.move(d, rpm, acc), leg="out"))
                out.append(dict(self.move(0, rpm, acc), leg="back"))
        return out

    # ── the tests ──
    def t_current(self, reps):
        rows = []
        for ma in CURRENTS:
            self.current(ma)
            time.sleep(0.3)
            r = self.tone(LAG_RPM, LAG_ACC, reps)
            for x in r:
                x["ma"] = ma
            rows += r
            lost = sum(abs(x["steps_lost"]) for x in r)
            print("  %4d mA: %d step(s) lost over %d moves, worst miss %+.0f counts"
                  % (ma, lost, len(r), max((x["miss"] for x in r), key=abs)), flush=True)
        self.current(servo.DEFAULT_MA)
        return rows

    def t_speed(self, reps, currents=(servo.DEFAULT_MA,)):
        """Whole tones per rpm/acc at each working current in `currents`: gate 2 has to pass at
        the current the production driver can hold, not at the motor's rating."""
        rows = []
        for ma in currents:
            self.current(ma)
            time.sleep(0.3)
            for rpm, acc in SPEEDS:
                r = [dict(x, ma=ma) for x in self.tone(rpm, acc, reps)]
                rows += r
                t9 = [x["t90"] for x in r if x["t90"] is not None]
                print("  %4d mA %4d rpm acc %3d: t90 %s ms, %d step(s) lost"
                      % (ma, rpm, acc, "%.1f" % (1e3 * st.mean(t9)) if t9 else "-",
                         sum(abs(x["steps_lost"]) for x in r)), flush=True)
        self.current(servo.DEFAULT_MA)
        return rows

    def t_reenable(self, n):
        """Coils off then on, power left on: the settle, and where enabling puts it."""
        rows = []
        for k in range(n):
            target = self.hi if k % 2 == 0 else self.lo
            self.move(target, LAG_RPM, LAG_ACC)
            time.sleep(1.0)                     # a settled hold, as the 11-19 tests learned
            e0 = self.where()
            self.enable(False)
            time.sleep(0.5)
            e1 = self.where()
            self.enable(True)
            time.sleep(0.5)
            e2 = self.where()
            rows.append(dict(target=target, held=e0 - target, settle=e1 - e0, back=e2 - e0))
            self.move(0, LAG_RPM, LAG_ACC)
            print("  cycle %2d: settled %+.0f while off, %+.0f from the hold after enabling"
                  % (k + 1, e1 - e0, e2 - e0), flush=True)
        return rows

    def t_powercycle(self, n):
        """The motor's 24 V off and on, by hand. Its encoder count does not survive, so the
        before/after compare is the angle within a turn."""
        rows = []
        for k in range(n):
            target = self.hi if k % 2 == 0 else self.lo
            self.move(target, LAG_RPM, LAG_ACC)
            time.sleep(1.0)
            e0 = self.enc()
            input("  [%d/%d] switch the MOTOR's 24 V OFF, wait 2 s, ON again, then press Enter: "
                  % (k + 1, n))
            time.sleep(1.0)
            e1 = self.enc()                      # coils as the driver starts them
            self.mode(servo.SR_OPEN)             # kept over a restart; said again, harmlessly
            self.enable(True)
            time.sleep(0.5)
            e2 = self.enc()
            w = lambda d: (d + T / 2) % T - T / 2
            row = dict(target=target, after_power=w(e1 - e0), after_enable=w(e2 - e0))
            rows.append(row)
            print("  cycle %d: %+.0f counts after power-up, %+.0f after enabling"
                  % (k + 1, row["after_power"], row["after_enable"]), flush=True)
            # the axis and the reading disagree after a power cycle (servo.SET_ZERO): zero both
            # where the shaft now is, which is the hold plus the jump, and re-take home from it
            self.m.set_zero()
            time.sleep(0.3)
            self.home = self.enc() - (target + row["after_enable"])
            self.off = 0.0
            self.move(0, LAG_RPM, LAG_ACC)
        return rows

    def t_listen(self):
        notes = []
        for ma in CURRENTS:
            self.current(ma)
            time.sleep(0.5)
            notes.append(dict(ma=ma, note=input("  holding at %d mA: listen, type a word, Enter: " % ma)))
        self.enable(False)
        notes.append(dict(ma=0, note=input("  coils OFF: listen, type a word, Enter: ")))
        self.enable(True)
        self.current(servo.DEFAULT_MA)
        return notes


def home_closed(rig: Rig, tries: int = 4):
    """Back to home by the encoder, in closed loop (after mode 5). Unlike move(), this starts
    from OUTSIDE the travel too, up to a whole travel beyond it: that is where a lowering move that
    lost steps leaves the shaft (the string pulls the nut on, 2026-11-25: -3724 past -3380). The
    axis and the encoder differ by an offset, so the target is corrected from each reading."""
    span = rig.hi - rig.lo
    e = rig.enc()
    if not rig.lo - span <= e - rig.home <= rig.hi + span:
        raise Abort("the shaft is at %+d counts from home: too far to bring back blind" % (e - rig.home))
    axis = e
    for _ in range(tries):
        if abs(e - rig.home) <= 3:
            return
        axis += rig.home - e
        rig.m.move_abs(int(axis), 100, 230)
        end = time.monotonic() + 3.0 + abs(rig.home - e) / (100 * T / 60.0)
        last = None
        while time.monotonic() < end:              # until the shaft stands still
            time.sleep(0.15)
            e = rig.enc()
            if last is not None and abs(e - last) <= 1:
                break
            last = e
    if abs(e - rig.home) > 3:
        raise Abort("home missed by %+d counts" % (e - rig.home))


def restore(rig: Rig):
    """Back to how the motor is run everywhere else. Every step tried even if one fails, except
    the zero: zeroing where the shaft is only makes sense AT home. After a failed homing the zero
    is skipped and the shaft's place from home printed, so the start can still be found
    (2026-11-25: a zero at -3724 lost it)."""
    homed = []
    steps = (("mode 5", lambda: rig.mode(servo.SR_VFOC)),
             ("current", lambda: rig.current(servo.DEFAULT_MA)),
             ("enable", lambda: rig.enable(True)),
             ("home", lambda: rig.home is not None and (home_closed(rig), homed.append(1))),
             ("zero", lambda: homed and rig.m.set_zero()))
    bad = []
    for name, fn in steps:
        try:
            fn()
        except BaseException as e:                     # a second Ctrl-C must not skip mode 5
            bad.append("%s: %r" % (name, e))
    if rig.home is not None and not homed:
        try:
            bad.append("NOT zeroed: the shaft is %+d counts from the start" % (rig.enc() - rig.home))
        except BaseException as e:
            bad.append("NOT zeroed; the encoder did not answer (%r)" % e)
    print("motor restored: SR_vFOC, %d mA, enabled%s" % (servo.DEFAULT_MA,
          "" if not bad else " -- BUT: " + "; ".join(bad)))
    return bad


def run(o, link=None) -> dict:
    own = link is None
    if own:
        from .link import MotorCtrlLink
        link = MotorCtrlLink()
    rig = Rig(link, o.id, o.raise_sign)
    was = None
    if hasattr(link, "ask"):
        try:
            r = link.ask("P")
            was = len(r) > 2 and r[0] == "P" and r[2] == "1"
            link.ask("P 0")
        except Exception as e:
            print("play state not read (%s); going on" % e)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    rec = dict(label=o.label, when=time.strftime("%Y-%m-%d %H:%M:%S"), raise_sign=o.raise_sign,
               travel=(rig.lo, rig.hi))
    only = set(o.only.split(",")) if o.only else set(TESTS)
    try:
        rig.enable(False)
        rig.mode(servo.SR_OPEN)
        rig.current(servo.DEFAULT_MA)
        rig.enable(True)
        time.sleep(0.3)
        rig.m.set_zero()
        time.sleep(0.3)
        rig.home = rig.enc()
        rig.off = 0.0
        print("SR_OPEN, %d mA; start %d counts; travel %+d..%+d counts (a whole tone each way)"
              % (servo.DEFAULT_MA, rig.home, rig.lo, rig.hi), flush=True)
        # the encoder must still read in open loop, or nothing here means anything
        sanity = rig.move(rig.hi / 4, 300, 230)
        rig.move(0, 300, 230)
        if abs(sanity["miss"]) > STEP:
            raise Abort("the encoder does not follow an open-loop move (missed by %+.0f counts)"
                        % sanity["miss"])
        if "current" in only or "lag" in only:
            print("current / lag: whole tones at %d rpm acc %d" % (LAG_RPM, LAG_ACC), flush=True)
            rec["current"] = rig.t_current(o.reps)
        if "speed" in only:
            print("speed: whole tones at %s mA" % ",".join(map(str, o.speed_ma)), flush=True)
            rec["speed"] = rig.t_speed(o.reps, o.speed_ma)
        if o.reenable:
            print("reenable: coils off/on, power on", flush=True)
            rec["reenable"] = rig.t_reenable(o.reenable)
        if o.powercycle:
            print("powercycle: by hand", flush=True)
            rec["powercycle"] = rig.t_powercycle(o.powercycle)
        if o.listen:
            print("listen: by ear", flush=True)
            rec["listen"] = rig.t_listen()
    except (Abort, KeyboardInterrupt, TimeoutError) as e:
        rec["stopped"] = repr(e)
        print("STOPPED: %r" % e)
    finally:
        rec["restore_failed"] = restore(rig)
        if was:
            try:
                link.ask("P 1")
            except Exception:
                pass
        rec["sent"] = (min(rig.sent, default=0), max(rig.sent, default=0))
        with open(o.log, "a") as f:
            f.write(json.dumps(rec) + "\n")
        if own:
            link.close()
    summary(rec)
    return rec


def summary(rec):
    print("\n%s  %s%s" % (rec["label"], rec["when"],
                          "  STOPPED: " + rec["stopped"] if rec.get("stopped") else ""))
    if rec.get("current"):
        print("  mA    lost/moves  settled up      settled down     (counts, model cents)")
        for ma in CURRENTS:
            rs = [r for r in rec["current"] if r["ma"] == ma]
            if not rs:
                continue
            up = [r["miss"] for r in rs if r["up"]]
            dn = [r["miss"] for r in rs if not r["up"]]
            f = lambda xs: "%+6.1f (%+.2f c)" % (st.mean(xs), cents(abs(st.mean(xs))) *
                                                  (1 if st.mean(xs) >= 0 else -1)) if xs else "-"
            print("  %4d  %3d/%-3d     %-16s %-16s" % (ma, sum(abs(r["steps_lost"]) for r in rs),
                                                      len(rs), f(up), f(dn)))
    if rec.get("speed"):
        print("    mA  rpm  acc   t90 ms mean/max   lost")
        for ma, rpm, acc in sorted({(r.get("ma", servo.DEFAULT_MA), r["rpm"], r["acc"]) for r in rec["speed"]},
                                   key=lambda k: (-k[0], k[1], -k[2])):
            rs = [r for r in rec["speed"] if r.get("ma", servo.DEFAULT_MA) == ma and r["rpm"] == rpm and r["acc"] == acc]
            t9 = [r["t90"] for r in rs if r["t90"] is not None]
            if rs:
                print("  %4d %4d %3d   %s   %d" % (ma, rpm, acc, "%6.1f / %6.1f" % (1e3 * st.mean(t9), 1e3 * max(t9))
                                              if t9 else "     -        ", sum(abs(r["steps_lost"]) for r in rs)))
    for k in ("reenable", "powercycle"):
        if rec.get(k):
            print("  %s: %s" % (k, ", ".join("%+.0f/%+.0f" % ((r.get("settle"), r.get("back")) if k == "reenable"
                                                              else (r["after_power"], r["after_enable"]))
                                             for r in rec[k])))
    print("  targets sent %+.0f..%+.0f counts, travel %+d..%+d; restore %s"
          % (rec["sent"][0], rec["sent"][1], rec["travel"][0], rec["travel"][1],
             "OK" if not rec["restore_failed"] else "FAILED: %s" % rec["restore_failed"]))


def parser():
    a = argparse.ArgumentParser()
    a.add_argument("--label", default="run")
    a.add_argument("--only", default="", help="comma list of %s" % ",".join(TESTS))
    a.add_argument("--reps", type=int, default=3)
    a.add_argument("--speed-ma", type=lambda v: [int(x) for x in v.split(",")], default=[servo.DEFAULT_MA],
                   metavar="MA[,MA]", help="working current(s) for the speed test, e.g. 1400,1000")
    a.add_argument("--reenable", type=int, default=0, metavar="N")
    a.add_argument("--powercycle", type=int, default=0, metavar="N")
    a.add_argument("--listen", action="store_true")
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--raise-sign", type=int, choices=(1, -1), default=RAISE_SIGN)
    a.add_argument("--log", default=LOG)
    a.add_argument("--report", action="store_true")
    a.add_argument("--sim", action="store_true", help="against publicbench.sim, no hardware")
    return a


def main(argv=None):
    o = parser().parse_args(argv)
    if o.report:
        if not os.path.exists(o.log):
            print("no runs logged yet (%s)" % o.log)
            return 0
        for line in open(o.log):
            summary(json.loads(line))
        return 0
    if o.sim:
        from .link import CanLink
        from .sim import SimServo
        sim = SimServo(can_id=o.id)
        sim.start()
        link = CanLink(channel="public-sim", interface="virtual")
        try:
            run(o, link)
        finally:
            link.close()
            sim.stop()
        return 0
    run(o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
