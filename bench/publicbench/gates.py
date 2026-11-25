"""Gate 1, items (i)-(v) of bench/OPENLOOP_BENCH.md, on the QT Py bench board (publicbench.qtpy):
can a TMC2209 driven open loop restore its phase after a power cut?

    python3 -m publicbench.gates i              does MSCNT count STEP edges with the outputs off?
    python3 -m publicbench.gates ii             freewheel at rest, then move: lands where told?
    python3 -m publicbench.gates iii --moves 1000   MSCNT against the pulses sent, at speed
    python3 -m publicbench.gates iv --reps 20   THE HEADLINE: power cut, snap at MSCNT 0, move
                                                back (it asks you to switch the 24 V off and on)
    python3 -m publicbench.gates v              a brownout: dip VM, keep the QT Py on USB
    python3 -m publicbench.gates all --truth servo42d   everything, with ground truth
    python3 -m publicbench.gates 2 --truth servo42d     GATE 2: the ramp, 400..1600 rev/s^2 at
                                                1.4 A, whole tones and 0.52 turns (OPENLOOP_BENCH.md)

GROUND TRUTH (--truth servo42d): the SERVO42D's own board left mounted on CAN with its motor
wires moved to the TMC2209 still reads the shaft's magnet (OPENLOOP_BENCH.md, Wiring). Check
first that it answers with no motor attached. With --truth none, (ii) and (iv) report what the
driver and firmware say, and the snap itself is not measured.

SAFE: every target is within +- a whole tone of where the run starts (TONE_TURNS: this rig's
string model, the smaller side), checked before each move; a run that would leave that range
stops. Gate 2 learns which way raises pitch from the encoder and keeps to -2..+2 semitones, and
-2..--raise-st for its 0.52-turn moves; a shaft found outside that stops it. Every run is
appended to ~/openloop_tmc.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from .pedaldrive import throw_counts
from .qtpy import BenchError, QtPyBench, mscnt_agrees
from .springload import RAISE_SIGN

LOG = os.path.expanduser("~/openloop_tmc.jsonl")
COUNTS_TURN = 16384                     # the SERVO42D encoder (servo.COUNTS_PER_TURN)
# Gate 1's travel: a whole tone each way on THIS rig's string model (pedaldrive, the same
# +-2 semitones openloop runs in), the smaller side of it, so it is safe whichever way the coils
# are wired. Was 0.52 turn until 2026-11-25: the closed-loop rig's whole tone, which on the
# in-line rig is +3.6 / -6.4 semitones.
TONE_TURNS = min(throw_counts(2.0), -throw_counts(-2.0)) / COUNTS_TURN     # 0.206
LONG_TURNS = 0.52                       # gate 2: the closed-loop rig's whole tone (39 ms figure)


class Abort(RuntimeError):
    pass


def wrap(units: int) -> int:
    """an MSCNT difference into (-512, 512]"""
    u = units % 1024
    return u - 1024 if u > 512 else u


class Gate:
    def __init__(self, b: QtPyBench, truth=None, prompt=input, *, usteps=4, fullsteps=200,
                 run_ma=1000, rpm=600, ramp_ms=20, settle=0.3, sleep=time.sleep):
        self.b, self.truth, self.prompt, self.sleep = b, truth, prompt, sleep
        self.usteps, self.run_ma, self.settle = usteps, run_ma, settle
        self.steps_turn = fullsteps * usteps
        self.tone = round(TONE_TURNS * self.steps_turn)
        self.v = max(1, round(rpm / 60 * self.steps_turn))
        self.a = max(1, round(self.v / (ramp_ms / 1000)))
        self.per = 256 // usteps
        self.sign = None
        self.ref = None                 # (mscnt, pos) the MSCNT check counts from

    # ── basics ──
    def setup(self, hold_ma=None):
        r = self.b.init(self.usteps)
        if r["writes"] != 5:
            raise Abort("init: the driver took %s of 5 writes: check the UART wiring" % r["writes"])
        self.b.current(self.run_ma, self.run_ma // 2 if hold_ma is None else hold_ma)
        self.b.gstat()
        self.b.enable(True)
        self.sleep(self.settle)
        self.b.do("zero")
        self.learn_sign()

    def learn_sign(self):
        """which way MSCNT runs for a positive step, from one step out and back"""
        m0 = self.b.mscnt()["mscnt"]
        self.go(1)
        m1 = self.b.mscnt()["mscnt"]
        self.go(0)
        d = (m1 - m0) % 1024
        if d == self.per:
            self.sign = 1
        elif d == 1024 - self.per:
            self.sign = -1
        else:
            raise Abort("one step moved MSCNT by %d, not +-%d: steps are being lost or doubled"
                        % (d, self.per))
        self.mark()

    def mark(self):
        ms = self.b.mscnt()
        self.ref = (ms["mscnt"], ms["pos"])

    def agrees(self, ms=None) -> bool:
        ms = ms or self.b.mscnt()
        m0, p0 = self.ref
        return mscnt_agrees(dict(ms, pos=ms["pos"] - p0), m0, self.sign)

    def check(self, target: int):
        if abs(target) > self.tone:
            raise Abort("target %d is past a whole tone (%d steps) from the start" % (target, self.tone))

    def go(self, target: int, v=None, a=None) -> dict:
        self.check(target)
        self.b.goto(target, v or self.v, a or self.a)
        return self.b.wait()

    def where(self):
        return None if self.truth is None else self.truth()

    # ── (i) ──
    def gate_i(self, n=3) -> dict:
        """Send n steps with the outputs off, ENN high and then TOFF = 0, and read MSCNT.
        Counted: the phase can be restored before the coils come on (plan A). Frozen: snap and
        move back (plan B, gate iv). Each case steps back before turning on again, so the field
        returns where the rotor is."""
        out = {}
        chop = self.b.read(0x6C)
        for how in ("enn", "toff"):
            self.go(0)
            m0 = self.b.mscnt()["mscnt"]
            if how == "enn":
                self.b.enable(False)
            else:
                self.b.write(0x6C, chop & ~0xF)
            self.b.move(n, self.v, self.a)
            self.b.wait()
            m1 = self.b.mscnt()["mscnt"]
            self.b.move(-n, self.v, self.a)
            self.b.wait()
            m2 = self.b.mscnt()["mscnt"]
            if how == "enn":
                self.b.enable(True)
            else:
                self.b.write(0x6C, chop)
            moved = (self.sign * (m1 - m0)) % 1024
            verdict = ("counts" if moved == (n * self.per) % 1024 else
                       "frozen" if moved == 0 else "other")
            out[how] = dict(mscnt=(m0, m1, m2), moved=moved, expect=(n * self.per) % 1024,
                            verdict=verdict, back=m2 == m0)
            print("  (i) outputs off by %-4s: MSCNT moved %d for %d steps (%d each): %s"
                  % (how.upper(), moved, n, self.per, verdict), flush=True)
            self.sleep(self.settle)
            self.mark()
        out["plan"] = "A" if out["enn"]["verdict"] == "counts" else "B"
        return out

    # ── (ii) ──
    def gate_ii(self, cycles=10, rest=1.0) -> dict:
        """Freewheel at rest (IHOLD 0: coils off, no current), then move. Does it land where told?
        Truth error per cycle, after each move, in steps."""
        self.b.current(self.run_ma, 0)
        rows = []
        for k in range(cycles):
            target = self.tone if k % 2 == 0 else -self.tone
            for t in (target, 0):
                self.go(t)
                self.sleep(rest)
                w = self.where()
                rows.append(dict(target=t, err=None if w is None else w - t, mscnt_ok=self.agrees()))
        errs = [abs(r["err"]) for r in rows if r["err"] is not None]
        bad = sum(not r["mscnt_ok"] for r in rows)
        print("  (ii) freewheel restarts: %d moves, worst error %s steps, %d MSCNT mismatches"
              % (len(rows), "%.2f" % max(errs) if errs else "-", bad), flush=True)
        self.b.current(self.run_ma, self.run_ma // 2)
        return dict(rows=rows, worst=max(errs) if errs else None, mscnt_bad=bad)

    # ── (iii) ──
    def gate_iii(self, moves=1000, rpm=None) -> dict:
        """Whole tones out and back at speed; after each, MSCNT against the pulses sent."""
        v = self.v if rpm is None else max(1, round(rpm / 60 * self.steps_turn))
        a = max(self.a, v * 50)
        bad, worst = 0, 0.0
        for k in range(moves):
            t = (self.tone if k % 4 == 0 else -self.tone if k % 4 == 2 else 0)
            self.go(t, v, a)
            if not self.agrees():
                bad += 1
            w = self.where()
            if w is not None:
                worst = max(worst, abs(w - t))
        print("  (iii) %d moves at %d steps/s: %d MSCNT mismatches, worst truth error %.2f steps"
              % (moves, v, bad, worst), flush=True)
        return dict(moves=moves, v=v, mscnt_bad=bad, worst=worst if self.truth else None)

    # -- gate 2: the ramp --
    def gate_2(self, accs=(400, 800, 1200, 1600), kinds=("tone", "long"), reps=20, rpm=1600,
               ma=1400, raise_st=2.4) -> dict:
        """Whole tones (+-2 semitones) and 0.52-turn moves (-2 st up to raise_st) at each
        acceleration in `accs` (rev/s^2), vmax `rpm`, `ma` working current; `reps` moves each
        way. Lost steps by the SERVO42D encoder; t90 from encoder polls. Each kind stops at the
        first acceleration that loses a step. See OPENLOOP_BENCH.md, gate 2."""
        if self.truth is None:
            raise Abort("gate 2 needs --truth servo42d: a stall shows on the shaft, not in MSCNT")
        self.b.current(ma, ma // 2)
        self.sleep(self.settle)
        spt = self.steps_turn
        # which way raises pitch: a small move, read by the encoder (+ raises on this rig)
        k = max(4, spt // 50)
        w0 = self.truth()
        self.go(k)
        w1 = self.truth()
        self.go(0)
        if abs(abs(w1 - w0) - k) > k / 2:
            raise Abort("a %d-step move turned the shaft %.1f steps: is the encoder on this motor?"
                        % (k, w1 - w0))
        up = (1 if w1 > w0 else -1) * RAISE_SIGN
        ref = self.truth()                      # the shaft at bench position 0, in steps

        def steps(counts):                      # model counts -> steps, raise positive
            return counts / COUNTS_TURN * spt
        lo, hi = steps(throw_counts(-2.0)), steps(throw_counts(2.0))
        top = lo + LONG_TURNS * spt
        ceiling = steps(throw_counts(raise_st))
        if "long" in kinds and top > ceiling:
            raise Abort("0.52 turn from -2 st reaches %.0f steps, past --raise-st (%.0f)" % (top, ceiling))
        high = max(hi, top) if "long" in kinds else hi
        v = max(1, round(rpm / 60 * spt))
        out = dict(up=up, steps_turn=spt, rpm=rpm, ma=ma, lo=lo, hi=hi, top=top, kinds={})

        def at():                               # the shaft, steps from bench 0, raise positive
            return (self.truth() - ref) * up

        def move(pos, a_rev):
            """to `pos` (raise-positive steps), polled the whole way; then the shaft's error"""
            pos = round(pos)
            if not lo - 1 <= pos <= high + 1:
                raise Abort("target %d is outside the travel" % pos)
            a0, t0 = at(), time.monotonic()
            self.b.goto(pos * up, v, max(1, round(a_rev * spt)))
            curve = []
            while True:
                curve.append((round(time.monotonic() - t0, 5), round(at(), 2)))
                if not self.b.status()["moving"]:
                    break
                if time.monotonic() - t0 > 5:
                    self.b.do("halt")
                    raise Abort("a move ran past 5 s")
            self.sleep(0.1)
            w = at()
            curve.append((round(time.monotonic() - t0, 5), round(w, 2)))
            span = pos - a0
            t90 = next((t for t, x in curve if span and (x - a0) / span >= 0.9), None)
            if not lo - 2 * self.usteps <= w <= high + 2 * self.usteps:
                self.b.do("setpos %d" % round(w * up))
                raise Abort("the shaft is at %.0f steps, past the travel: re-aligned, stopped" % w)
            err = w - pos
            return dict(target=pos, t90=t90, err=round(err, 2), lost=round(err / self.usteps),
                        up=span > 0, curve=curve, mscnt_ok=self.agrees())

        def ms(rows, up_):
            t9 = [1e3 * r["t90"] for r in rows if r["up"] == up_ and r["t90"] is not None]
            return ("%.1f/%.1f" % (sum(t9) / len(t9), max(t9))) if t9 else "-"

        try:
            for kind in kinds:
                rows_k = []
                for a_rev in accs:
                    if kind == "tone":
                        seq = [hi, 0, lo, 0] * (reps // 2)
                    else:
                        move(lo, accs[0])
                        seq = [top, lo] * reps
                    rows = []
                    for p in seq:               # the first lost step ends this acceleration:
                        rows.append(dict(move(p, a_rev), acc=a_rev, kind=kind))
                        if rows[-1]["lost"]:    # the next moves would carry the shaft's offset
                            break               # past the travel
                    if kind == "long" and not rows[-1]["lost"]:
                        move(0, accs[0])
                    rows_k += rows
                    lost = sum(abs(r["lost"]) for r in rows)
                    print("  (2) %-4s %5d rev/s2: t90 raise %s ms, lower %s ms (mean/worst); "
                          "%d full step(s) lost, MSCNT bad %d"
                          % (kind, a_rev, ms(rows, True), ms(rows, False), lost,
                             sum(not r["mscnt_ok"] for r in rows)), flush=True)
                    if lost:
                        self.b.do("setpos %d" % round(at() * up))   # where the shaft really is
                        self.go(0)
                        print("  (2) %s: stopped at %d rev/s2" % (kind, a_rev), flush=True)
                        break
                out["kinds"][kind] = rows_k
        finally:
            self.b.current(self.run_ma, self.run_ma // 2)
        return out

    # ── (iv) and (v) ──
    def restore(self, target: int, ask: str) -> dict:
        """one power cut and restore at `target`; returns predicted against measured snap"""
        self.go(target)
        self.sleep(self.settle)
        ms = self.b.mscnt()
        phase, pos = ms["mscnt"], ms["pos"]
        w0 = self.where()
        self.b.enable(False)
        self.prompt(ask)
        g = self.b.gstat()
        init = self.b.init(self.usteps)
        self.b.do("setpos %d" % pos)            # init keeps pos unless usteps changed
        m_after = self.b.mscnt()["mscnt"]
        d = wrap(phase - m_after)                 # where the rotor is, from the new field
        ambiguous = abs(d) == 512
        snap_steps = -self.sign * d / self.per    # predicted, in steps
        w1 = self.where()
        self.b.enable(True)
        self.sleep(self.settle)
        w2 = self.where()
        rotor = pos + snap_steps
        self.b.do("setpos %d" % round(rotor))
        self.mark()
        self.go(target)
        self.sleep(self.settle)
        w3 = self.where()
        row = dict(target=target, phase=phase, mscnt_after=m_after, reset=g["reset"],
                   writes=init["writes"], predicted=snap_steps, ambiguous=ambiguous,
                   measured=None if w1 is None else w2 - w1,
                   off_while_cut=None if w0 is None else w1 - w0,
                   final_err=None if w0 is None else w3 - w0)
        if row["measured"] is not None:
            row["snap_ok"] = abs(row["measured"] - snap_steps) <= 0.5
        if row["final_err"] is not None and abs(row["final_err"]) > 0.5:
            # recorded above; with ground truth on the bench, put the count right so the next
            # restore starts true (a wrong snap at +-512 leaves it a whole cycle, 4 full steps, off)
            self.b.do("setpos %d" % round(target + row["final_err"]))
            self.mark()
            self.go(target)
        return row

    def targets_iv(self):
        """the ends, the middle and quarter points, and the stored phases nearest +-512 (the
        ambiguous half cycle) and one step either side of it"""
        ts = [-self.tone, -self.tone // 2, 0, self.tone // 2, self.tone]
        m0, p0 = self.ref
        for want in (512 - self.per, 512, 512 + self.per):
            best = min((k for k in range(-self.tone, self.tone + 1)
                        if (m0 + self.sign * (k - p0) * self.per) % 1024 == want), key=abs, default=None)
            if best is not None:
                ts.append(best)
        return ts

    def gate_iv(self, reps=20) -> dict:
        rows = []
        for t in self.targets_iv():
            for k in range(reps):
                rows.append(self.restore(t, "  [iv %+d, %d/%d] switch the 24 V OFF, wait 2 s, ON, then press Enter: "
                                         % (t, k + 1, reps)))
        return self.summarise("iv", rows)

    def gate_v(self, reps=3) -> dict:
        rows = [self.restore(0, "  [v %d/%d] DIP the 24 V below ~4 V for a moment, QT Py still on USB, "
                                "then press Enter: " % (k + 1, reps)) for k in range(reps)]
        return self.summarise("v", rows)

    def summarise(self, name, rows) -> dict:
        unseen = sum(not r["reset"] for r in rows)
        short = sum(r["writes"] != 5 for r in rows)
        meas = [r for r in rows if r["measured"] is not None and not r["ambiguous"]]
        ok = sum(r["snap_ok"] for r in meas)
        # a phase stored exactly half a cycle (2 full steps) from the new field can snap either
        # way: its restore is a coin toss, reported apart from the rest
        fin = [abs(r["final_err"]) for r in rows if r["final_err"] is not None and not r["ambiguous"]]
        amb = [r for r in rows if r["ambiguous"] and r["final_err"] is not None]
        amb_wrong = sum(abs(r["final_err"]) > 0.5 for r in amb)
        print("  (%s) %d restores: reset unseen %d, re-init short %d, snap as predicted %s, "
              "worst final error %s steps; at the +-512 phase %d/%d off"
              % (name, len(rows), unseen, short, "%d/%d" % (ok, len(meas)) if meas else "- (no truth)",
                 "%.2f" % max(fin) if fin else "-", amb_wrong, len(amb)), flush=True)
        return dict(rows=rows, reset_unseen=unseen, reinit_short=short,
                    snap_ok=ok if meas else None, snap_n=len(meas), worst=max(fin) if fin else None,
                    ambiguous_n=len(amb), ambiguous_wrong=amb_wrong)


class Servo42Truth:
    """the SERVO42D's encoder as ground truth, in driver steps"""

    def __init__(self, can_id=1, steps_turn=800):
        from . import servo
        from .link import MotorCtrlLink
        self.m = servo.Servo(MotorCtrlLink(), can_id)
        self.k = steps_turn / servo.COUNTS_PER_TURN
        self.c0 = self.m.position()

    def __call__(self) -> float:
        return (self.m.position() - self.c0) * self.k


def parser():
    a = argparse.ArgumentParser()
    a.add_argument("which", choices=("i", "ii", "iii", "iv", "v", "all", "2"))
    a.add_argument("--truth", choices=("none", "servo42d"), default="none")
    a.add_argument("--can-id", type=int, default=1)
    a.add_argument("--fullsteps", type=int, default=200, help="per turn: 200 = 1.8 deg, 400 = 0.9")
    a.add_argument("--usteps", type=int, default=4)
    a.add_argument("--run-ma", type=int, default=1000)
    a.add_argument("--rpm", type=int, default=600)
    a.add_argument("--reps", type=int, default=20)
    a.add_argument("--moves", type=int, default=1000)
    a.add_argument("--top-rpm", type=int, default=1600)
    a.add_argument("--accs", default="400,800,1200,1600", help="gate 2: rev/s^2")
    a.add_argument("--kinds", default="tone,long", help="gate 2: tone (+-2 st), long (0.52 turn)")
    a.add_argument("--ma", type=int, default=1400, help="gate 2's working current")
    a.add_argument("--raise-st", type=float, default=2.4, help="gate 2: the long moves' ceiling")
    a.add_argument("--log", default=LOG)
    a.add_argument("--label", default="run")
    return a


def run(o, b=None, truth=None, prompt=input, sleep=time.sleep) -> dict:
    b = b or QtPyBench()
    if truth is None and o.truth == "servo42d":
        truth = Servo42Truth(o.can_id, o.fullsteps * o.usteps)
    g = Gate(b, truth, prompt, usteps=o.usteps, fullsteps=o.fullsteps, run_ma=o.run_ma,
             rpm=o.rpm, sleep=sleep)
    rec = dict(label=o.label, when=time.strftime("%Y-%m-%d %H:%M:%S"), which=o.which,
               truth=o.truth, fullsteps=o.fullsteps, usteps=o.usteps, run_ma=o.run_ma, rpm=o.rpm)
    todo = ("i", "ii", "iii", "iv", "v") if o.which == "all" else (o.which,)
    try:
        g.setup()
        rec["sign"] = g.sign
        for k in todo:
            rec[k] = {"i": g.gate_i, "ii": g.gate_ii, "iii": lambda: g.gate_iii(o.moves, o.top_rpm),
                      "iv": lambda: g.gate_iv(o.reps), "v": g.gate_v,
                      "2": lambda: g.gate_2([int(x) for x in o.accs.split(",")], o.kinds.split(","),
                                            o.reps, o.top_rpm, o.ma, o.raise_st)}[k]()
    except (Abort, BenchError, KeyboardInterrupt) as e:
        rec["stopped"] = "%s: %s" % (type(e).__name__, e)
        print("STOPPED:", rec["stopped"], flush=True)
        try:
            b.do("halt")
        except Exception:
            pass
    finally:
        try:
            g.go(0)
        except Exception as e:
            rec["home_failed"] = str(e)
        with open(o.log, "a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def main(argv=None):
    run(parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
