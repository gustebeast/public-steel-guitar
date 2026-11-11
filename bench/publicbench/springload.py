"""How much do the counter springs help the motor? One run per spring setting, on string 1.

    python3 -m publicbench.springload --label off
    python3 -m publicbench.springload --label t20 --turns 20      (the M4 20 turns in from fully out)

Reads the motor's own effort through motor_ctrl, changing NO motor setting:
  HOLD    the SERVO42D's angle error (0x39) standing still at the start position.
  MOVES   steps of --step turns OUT FROM THE START AND STRAIGHT BACK, alternating raise and
          lower (user, 2026-11-11: the nut's travel is short -- it must never walk), so the nut
          never leaves start +- step, and only at RPMS: what a quick pedal press needs. Each
          move is timed (command left -> 90 % of the way, from the encoder) and its angle error sampled the whole way: peak, and where it settles.
          A move is UP when it raises pitch (RAISE_SIGN, this rig's), i.e. AGAINST the
          string; the springs should shrink the up/down difference.
Prints a summary and appends every number to ~/springload.jsonl; `--report` compares runs.
Stop the phone service first (it shares the serial port): sudo systemctl stop public-steel-guitar-phone
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import time

from . import servo
from .link import MotorCtrlLink

T = servo.COUNTS_PER_TURN
ERR_PER_TURN = 51200                    # 0x39's units
# which way the motor turns to RAISE pitch: +1 on the plank's in-line rig (user, 2026-11-11: the
# phone's -1, found on the belt rig 11-05, is backwards here). --raise-sign overrides it.
RAISE_SIGN = +1
LOG = os.path.expanduser("~/springload.jsonl")
# ONLY WHAT A PEDAL PRESS NEEDS (user, 2026-11-11): a whole tone is ~0.5 turn, a quick press
# 50..150 ms, so 200..600 rpm on average and ~1200 at its peak. No ramp (acc 0), as play.c moves.
RPMS = (1200, 600, 300)


def err_counts(v):
    return v * T / ERR_PER_TURN


class Probe:
    def __init__(self, link, can_id=1):
        self.link, self.m = link, servo.Servo(link, can_id)

    def ask(self, code, timeout=0.3):
        n = len(self.link.rx)
        self.m._send(bytes([code]))
        f = self.link.wait_frame(self.m._mine(code), n, timeout)
        if f is None:
            raise TimeoutError("motor did not answer 0x%02X" % code)
        return servo.parse(self.m.id, f.data)[1]

    def hold(self, n=150):
        e = []
        for _ in range(n):
            e.append(err_counts(self.ask(servo.READ_ERROR)))
            time.sleep(0.003)
        return dict(mean=st.mean(e), sd=st.pstdev(e), peak=max(abs(x) for x in e))

    def move(self, target, rpm, acc, window=1.0, settle=0.3):
        """One absolute move, the encoder and the angle error polled through it."""
        a = self.ask(servo.READ_ENCODER)
        n0 = len(self.link.rx)
        seq = self.m.move_abs(target, rpm, acc)
        end = time.monotonic() + window
        while time.monotonic() < end:
            self.m._send(bytes([servo.READ_ENCODER]))
            self.m._send(bytes([servo.READ_ERROR]))
            time.sleep(0.003)
        time.sleep(settle)
        fin = [err_counts(self.ask(servo.READ_ERROR)) for _ in range(20)]
        pos = self.ask(servo.READ_ENCODER)
        frames = self.link.rx[n0:]
        t0 = self.link.sent.get(seq)
        enc = self.m.positions(frames)
        errs = [(f.t, err_counts(servo.parse(self.m.id, f.data)[1])) for f in frames
                if self.m._mine(servo.READ_ERROR)(f) and servo.parse(self.m.id, f.data)]
        arr = self.m.arrived(frames)
        span = target - a
        t90 = next((t - t0 for t, c in enc if t0 and (c - a) / span >= 0.9), None) if span else None
        return dict(t90=t90, arrived=(arr[0] - t0) if arr and t0 else None,
                    peak_err=max((abs(e) for _, e in errs), default=None),
                    settled_err=st.mean(fin), final_miss=pos - target, polls=len(enc))


def run(o):
    link = MotorCtrlLink()
    p = Probe(link, o.id)
    was = None
    try:
        r = link.ask("P")
        was = len(r) > 2 and r[0] == "P" and r[2] == "1"
        link.ask("P 0")
    except Exception as e:
        print("play state not read (%s); going on" % e)
    try:
        n = len(link.rx)
        p.m.enable(True)                                 # driven, in the mode it keeps (SR_vFOC)
        if link.wait_frame(p.m._mine(servo.ENABLE), n, 0.5) is None:
            raise TimeoutError("the motor did not answer ENABLE")
        time.sleep(0.3)
        home = p.ask(servo.READ_ENCODER)
        step = int(round(o.step * T))
        lim = step
        print("start %d counts; steps +-%d (%.2f turn, %.2f mm of nut)" % (home, step, o.step, o.step * 2))
        hold0 = p.hold()
        print("hold: angle error mean %+.1f sd %.1f peak %.1f counts" % (hold0["mean"], hold0["sd"], hold0["peak"]))
        rows = []
        for rpm, acc in ((rpm, 0) for rpm in RPMS):
            for rep in range(o.reps):
                for d in (o.raise_sign, -o.raise_sign):      # out raising, back; out lowering, back
                    for tgt, kind in ((home + d * step, "out"), (home, "back")):
                        assert abs(tgt - home) <= lim, "a target past start +- step"
                        r = p.move(tgt, rpm, acc)
                        sgn = (tgt - (home if kind == "out" else home + d * step))
                        r.update(rpm=rpm, dir="up" if sgn * o.raise_sign > 0 else "down")
                        rows.append(r)
        end = p.ask(servo.READ_ENCODER)
        hold1 = p.hold()
    finally:
        if was:
            try:
                link.ask("P 1")
            except Exception:
                pass
    rec = dict(label=o.label, turns=o.turns, raise_sign=o.raise_sign, when=time.strftime("%Y-%m-%d %H:%M:%S"), step=o.step,
               home=home, end=end, hold0=hold0, hold1=hold1, moves=rows)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    summary(rec)
    link.close()


def _m(xs):
    xs = [x for x in xs if x is not None]
    return (st.mean(xs), max(xs)) if xs else (float("nan"), float("nan"))


def summary(rec):
    print("\n%s (M4 turns %s)  %s  start %d end %d" % (rec["label"], rec["turns"], rec["when"], rec["home"], rec["end"]))
    print("  hold: error mean %+.1f sd %.1f counts" % (rec["hold0"]["mean"], rec["hold0"]["sd"]))
    print("  rpm  dir   t90 ms mean/max   arrived ms   peak err   settled err   miss")
    for rpm in sorted({r["rpm"] for r in rec["moves"]}, reverse=True):
        for d in ("up", "down"):
            rs = [r for r in rec["moves"] if r["rpm"] == rpm and r["dir"] == d]
            t9, a, pk, se = _m([r["t90"] for r in rs]), _m([r["arrived"] for r in rs]), \
                _m([r["peak_err"] for r in rs]), _m([abs(r["settled_err"]) for r in rs])
            miss = max(abs(r["final_miss"]) for r in rs)
            print("  %4d %-4s  %6.1f / %6.1f    %6.1f      %7.1f      %6.1f      %4d" %
                  (rpm, d, 1e3 * t9[0], 1e3 * t9[1], 1e3 * a[0], pk[0], se[0], miss))


def report():
    for line in open(LOG):
        summary(json.loads(line))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--label", default="run")
    a.add_argument("--turns", type=float, default=None, help="M4 turns in from fully backed out")
    a.add_argument("--step", type=float, default=0.25, help="turns out and back (default 0.25 = 0.5 mm)")
    a.add_argument("--reps", type=int, default=4)
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--raise-sign", type=int, choices=(1, -1), default=RAISE_SIGN)
    a.add_argument("--report", action="store_true")
    o = a.parse_args()
    report() if o.report else run(o)
