"""Gate 2 by ramp: the steepest acceleration string 1 follows open loop without losing a step,
at a TMC2209's current, for a whole tone on this rig and for the 0.52 turn the closed-loop
39 ms figure was measured on (lead, 2026-11-25).

    python3 -m publicbench.rampsweep                       16 microsteps, acc 250..255, both moves
    python3 -m publicbench.rampsweep --only tone --accs 252,253
    python3 -m publicbench.rampsweep --report

MICROSTEPS (--mstep, default 16). The SERVO42D caps its open-loop modes at 400 rpm, over the
bus (SR_OPEN) and from STEP pulses (CR_OPEN) alike (MKS SERVO42D/57D CAN user manual V1.0.9, 3.2
and p78), and its speeds are "calibrated based on 16/32/64 subdivisions" (p78: at 8, a setting of
1200 runs 2400 rpm). So 4 microsteps should turn the cap's 400 into a real 1600 rpm.
⚠ IT DOES NOT, 2026-11-25: at 4 microsteps every whole tone stopped short by the SAME amount,
14 steps raising and 10 lowering (~75 % of the move), at 400 and at 500 rpm alike, peaking ~340
rpm. A stall is random; a fixed shortfall that ignores the speed setting is the firmware, so
nothing at 4 microsteps measures the motor. Leave it at 16, where the cap is a real 400 rpm and
acc 254 ran clean (49 ms whole tone). Past 400 rpm open loop is the TMC2209 bench's question.

THE MOVES (all in encoder counts from where the motor starts; the encoder does not care about
microsteps):
  tone   whole tones out and back, raising and lowering, inside +-2 semitones (openloop's travel)
  long   0.52 turn between -2 semitones and 0.52 turn above it (+2.36 semitones on this rig's
         model, D4 to about F4; user, 2026-11-25: "try both"), inside --raise-st
Each acc setting gets --reps moves each way; the sweep stops at the first setting that loses a
step. Every move's encoder curve (~3 ms polls) is logged with the move, to ~/rampsweep.jsonl.

PUT BACK, whatever happens: microsteps to what they were (read with the 00H read-parameter
command before anything changes), then openloop.restore (closed loop, default current, homed by
the encoder, zeroed only at home).
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

from . import openloop as OL
from . import servo
from .pedaldrive import throw_counts

T = servo.COUNTS_PER_TURN
READ_PARAM = 0x00                   # 00H code: a write-only parameter's value (manual 5.1.10)
SET_MSTEP = 0x84                    # u8 microsteps (manual 5.2.5)
LOG = os.path.expanduser("~/rampsweep.jsonl")
LONG_TURN = 0.52                    # the closed-loop rig's whole tone, turns
CAP_RPM = 400                       # open loop's cap, as a setting (manual 3.2)


def read_param(rig: OL.Rig, code: int, timeout=0.5) -> bytes:
    n = len(rig.link.rx)
    rig.m._send(bytes([READ_PARAM, code]))
    f = rig.link.wait_frame(lambda f: f.id == rig.m.id and f.data[:1] == bytes([code]), n, timeout)
    if f is None:
        raise TimeoutError("motor did not answer the read of 0x%02X" % code)
    return bytes(f.data[1:-1])


def shape(curve, span: float) -> dict:
    """Peak speed (rpm) and the triangle-equivalent acceleration (rev/s^2) of one move's curve
    [(t s, counts)], from the 2 % and 98 % crossings, as if the move had no cruise."""
    if len(curve) < 4 or not span:
        return {}
    t = [c[0] for c in curve]
    p = [(c[1] - curve[0][1]) / span for c in curve]
    def cross(f):
        return next((t[i] for i in range(len(p)) if p[i] >= f), None)
    a, b = cross(0.02), cross(0.98)
    v = [abs(p[i + 1] - p[i]) * abs(span) / (t[i + 1] - t[i]) for i in range(len(p) - 1) if t[i + 1] > t[i]]
    out = dict(peak_rpm=round(max(v) / T * 60.0, 1) if v else None)
    if a is not None and b is not None and b > a:
        # a triangle crosses f of its distance at sqrt(2f) of its half time, so 2 %..98 % is
        # (1 - 0.2) of the whole: a = 4 s (1 - sqrt(2 f))^2 / d^2
        out["tri_rev_s2"] = round(4.0 * abs(span) / T * (1 - math.sqrt(0.04)) ** 2 / (b - a) ** 2, 1)
    return out


class Sweep:
    def __init__(self, rig: OL.Rig, rpm: int, reps: int, log, mstep: int = 16, long_top: int = 0):
        self.rig, self.rpm, self.reps, self.log = rig, rpm, reps, log
        self.mstep, self.long_top = mstep, long_top

    def move(self, rel, acc, rpm=None):
        r = self.rig
        n0, tc, a = len(r.link.rx), time.monotonic(), r.where()
        d = r.move(rel, rpm or self.rpm, acc)
        d["curve"] = [(round(t - tc, 5), c - r.home) for t, c in r.m.positions(r.link.rx[n0:])]
        d.update(shape(d["curve"], rel - a))
        return d

    def legs(self, kind, acc):
        r = self.rig
        if kind == "tone":                              # out and back, raising then lowering
            return [dict(self.move(x, acc), kind=kind) for x in [r.hi, 0, r.lo, 0] * (self.reps // 2)]
        hi = r.hi                                       # bottom to top and back: the ceiling is
        r.hi = max(hi, self.long_top)                   # raised for these moves only (2026-11-25:
        try:                                            # raised for all, the tones went too far)
            self.move(r.lo, 230, 100)
            rows = [dict(self.move(x, acc), kind=kind) for x in [self.long_top, r.lo] * self.reps]
            self.move(0, 230, 100)
        finally:
            r.hi = hi
        return rows

    def run(self, kinds, rpms, accs):
        """Each kind, each speed setting, the accs in order until one loses a step."""
        out = []
        for kind in kinds:
            for rpm in rpms:
                self.rpm = rpm
                for acc in accs:
                    rows = [dict(x, rpm_setting=rpm) for x in self.legs(kind, acc)]
                    out += rows
                    print(self.summarise(kind, acc, rows, rpm * 16 // self.mstep), flush=True)
                    self.log(dict(kind=kind, acc=acc, rpm_setting=rpm, rows=rows))
                    if any(x["steps_lost"] for x in rows):
                        print("  %s at %d rpm: stopped at acc %d (steps lost)"
                              % (kind, rpm * 16 // self.mstep, acc), flush=True)
                        break
        return out

    @staticmethod
    def summarise(kind, acc, rows, real_rpm=None):
        parts = []
        for up, name in ((True, "raise"), (False, "lower")):
            s = [x for x in rows if x["up"] == up]
            t9 = [1e3 * x["t90"] for x in s if x["t90"]]
            pk = [x["peak_rpm"] for x in s if x.get("peak_rpm")]
            tri = [x["tri_rev_s2"] for x in s if x.get("tri_rev_s2")]
            parts.append("%s t90 %s ms (worst %s), %d lost/%d, peak %s rpm, ~%s rev/s2" % (
                name, "%.1f" % st.mean(t9) if t9 else "-", "%.1f" % max(t9) if t9 else "-",
                sum(abs(x["steps_lost"]) for x in s), len(s),
                "%.0f" % st.median(pk) if pk else "-", "%.0f" % st.median(tri) if tri else "-"))
        return "  %-4s %s acc %3d: %s" % (kind, "%4d rpm" % real_rpm if real_rpm else "", acc, " | ".join(parts))


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--mstep", type=int, default=16, help="see MICROSTEPS: 4 is a firmware artefact")
    a.add_argument("--accs", default="250,251,252,253,254,255")
    a.add_argument("--rpms", default=str(CAP_RPM), help="speed SETTINGS, each swept (x 16/mstep = real rpm)")
    a.add_argument("--ma", type=int, default=1400)
    a.add_argument("--reps", type=int, default=20, help="moves each way per acc setting (even)")
    a.add_argument("--only", default="tone,long")
    a.add_argument("--raise-st", type=float, default=2.4, help="the long moves' travel ceiling, semitones")
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--log", default=LOG)
    a.add_argument("--report", action="store_true")
    o = a.parse_args(argv)
    if o.report:
        if not os.path.exists(o.log):
            print("no runs logged yet (%s)" % o.log)
            return 0
        for line in open(o.log):
            r = json.loads(line)
            if "rows" in r:
                real = r["rpm_setting"] * 16 // r["mstep"] if r.get("rpm_setting") else None
                print(Sweep.summarise(r["kind"], r["acc"], r["rows"], real))
            else:
                print(r)
        return 0
    kinds = [k for k in o.only.split(",") if k]
    accs = [int(x) for x in o.accs.split(",")]
    top = throw_counts(o.raise_st)
    from .link import MotorCtrlLink
    link = MotorCtrlLink()
    rig = OL.Rig(link, o.id)
    if rig.sign != 1:
        raise SystemExit("rampsweep assumes the in-line rig, where the motor raises pitch turning +")
    logf = open(o.log, "a")

    def log(rec):
        logf.write(json.dumps(dict(rec, when=time.strftime("%Y-%m-%d %H:%M:%S"), mstep=o.mstep,
                                   ma=o.ma)) + "\n")
        logf.flush()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    was_mstep = None
    try:
        try:
            link.ask("P 0")
        except Exception as e:
            print("play state not set (%s); going on" % e)
        was_mstep = read_param(rig, SET_MSTEP)[0]
        rig.enable(False)
        rig.mode(servo.SR_OPEN)
        rig.current(o.ma)
        rig.must(bytes([SET_MSTEP, o.mstep]), "microsteps %d" % o.mstep)
        rig.enable(True)
        time.sleep(0.3)
        rig.m.set_zero()
        time.sleep(0.3)
        rig.home, rig.off = rig.enc(), 0.0
        long_top = rig.lo + round(LONG_TURN * T)
        if "long" in kinds and long_top > top:
            raise OL.Abort("0.52 turn from -2 st ends at %+d counts, past --raise-st's %+d" % (long_top, top))
        rpms = [int(x) for x in o.rpms.split(",")]
        print("SR_OPEN, %d mA, %d microsteps (was %d): speeds %s rpm; tone %+d..%+d, long %+d..%+d"
              % (o.ma, o.mstep, was_mstep, ",".join(str(r * 16 // o.mstep) for r in rpms),
                 rig.lo, rig.hi, rig.lo, long_top), flush=True)
        # does a coordinate still mean 16384 a turn at these microsteps? a slow small move says
        sw = Sweep(rig, rpms[0], o.reps, log, o.mstep, long_top)
        probe = sw.move(rig.hi / 8, 230, 25)
        sw.move(0, 230, 25)
        if abs(probe["miss"]) > OL.STEP:
            raise OL.Abort("a %+.0f-count move landed %+.0f off at %d microsteps: coordinates scale"
                           % (rig.hi / 8, probe["miss"], o.mstep))
        sw.run(kinds, rpms, accs)
    except KeyboardInterrupt:
        print("STOPPED", flush=True)
    except Exception as e:
        print("STOPPED: %r" % e, flush=True)
    finally:
        if was_mstep is not None:
            try:
                rig.must(bytes([SET_MSTEP, was_mstep]), "microsteps %d" % was_mstep)
                print("microsteps back to %d" % was_mstep, flush=True)
            except BaseException as e:
                print("MICROSTEPS NOT PUT BACK (%r): set %d by hand" % (e, was_mstep), flush=True)
        OL.restore(rig)
        logf.close()
        link.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
