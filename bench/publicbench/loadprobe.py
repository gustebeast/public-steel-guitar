"""The string-and-screw load on string 1's motor, from the SERVO42D's own current reading, in its
normal closed loop (SR_vFOC): steady raises against steady lowers at a few speeds (lead,
2026-11-25: the open-loop torque budget for the 42CM06 needed it measured, not bracketed).

    python3 -m publicbench.loadprobe --probe            does the board answer 38H at all?
    python3 -m publicbench.loadprobe                    the sweep (via tools/pi_bench.py run)

WHAT IS READ. 38H returns the board's real-time voltage (mV) and current (mA) (MKS SERVO42D/57D
CAN manual V1.0.9, 5.1.13). In FOC the current follows the torque asked of the motor, so at a
STEADY speed: raising = load + friction, lowering = friction - load, and at rest with the
self-locking screw holding the string, the baseline. So
    load     ~ (I_raise - I_lower) / 2
    friction ~ (I_raise + I_lower) / 2 - I_rest
each in mA, as reported. What 38H's current IS (a phase peak, an RMS, the q-axis part) is not
stated; and N·m needs the SERVO42D motor's torque constant, which is not published. Both are
reported as assumptions beside the numbers, never folded in silently.

THE MOVES: whole tones out and back inside the string's travel (-2..+2 semitones, pedaldrive's
model), on the ramp the phone uses, polled the whole way (encoder and current alternately); a
sample counts as steady when the encoder's speed is within 10 % of the cruise speed. Every
sample goes to ~/loadprobe.jsonl.

PUT BACK: home (the start position, by the encoder), play as it was. The mode and current are
the board's normal ones and are not changed.
Stop the phone service first; tools/pi_bench.py run does that and restarts it.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import time

from . import servo
from .pedaldrive import throw_counts

T = servo.COUNTS_PER_TURN
READ_VI = 0x38
LOG = os.path.expanduser("~/loadprobe.jsonl")


class Probe:
    def __init__(self, link, can_id=1):
        self.link, self.m = link, servo.Servo(link, can_id)

    def ask(self, body: bytes, timeout=0.3):
        n = len(self.link.rx)
        self.m._send(body)
        f = self.link.wait_frame(self.m._mine(body[0]), n, timeout)
        return None if f is None else f

    def vi(self):
        """(volts, mA) or None when the board does not answer 38H"""
        f = self.ask(bytes([READ_VI]))
        if f is None or len(f.data) < 6:
            return None
        d = bytes(f.data)
        return int.from_bytes(d[1:3], "big") / 1000.0, int.from_bytes(d[3:5], "big")

    def enc(self) -> int:
        return self.m.position()

    def move_logged(self, target, rpm, acc, timeout=4.0):
        """move to `target` (encoder counts) and poll it: [(t, counts, mA)]"""
        out = []
        t0 = time.monotonic()
        self.m.move_abs(int(target), rpm, acc)
        last = None
        while time.monotonic() - t0 < timeout:
            c = self.enc()
            r = self.vi()
            out.append((round(time.monotonic() - t0, 4), c, r[1] if r else None))
            if last is not None and abs(c - target) <= 5 and abs(c - last) <= 1:
                break
            last = c
        return out


def steady(samples, rpm, frac=0.10):
    """the current of the samples taken while the shaft ran within frac of rpm"""
    want = rpm * T / 60.0
    out = []
    for (t0, c0, _), (t1, c1, i1) in zip(samples, samples[1:]):
        if t1 > t0 and i1 is not None and abs(abs(c1 - c0) / (t1 - t0) - want) <= frac * want:
            out.append(i1)
    return out


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--probe", action="store_true", help="read 38H a few times and stop")
    a.add_argument("--rpms", default="60,150,300")
    a.add_argument("--acc", type=int, default=240, help="the board's ramp (higher = steeper)")
    a.add_argument("--reps", type=int, default=5)
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--log", default=LOG)
    o = a.parse_args(argv)
    from .link import MotorCtrlLink
    link = MotorCtrlLink()
    p = Probe(link, o.id)
    was = home = None
    try:
        try:
            r = link.ask("P")
            was = len(r) > 2 and r[0] == "P" and r[2] == "1"
            link.ask("P 0")
        except Exception as e:
            print("play state not read (%s); going on" % e)
        if o.probe:
            f = p.ask(bytes([0x40]))                    # version (manual 5.1.11)
            if f is not None and len(f.data) >= 5:
                d = bytes(f.data)                       # 40H, cal<<4|hw, firmware bytes..., boot, CRC
                print("40H -> calibrated %d, hardware %d (2 = S42D_CAN), raw %s"
                      % (d[1] >> 4, d[1] & 15, d.hex(" ")), flush=True)
            else:
                print("40H -> %s" % (bytes(f.data).hex(" ") if f else "no reply"), flush=True)
            for _ in range(5):
                print("38H ->", p.vi(), " encoder", p.enc(), flush=True)
                time.sleep(0.1)
            return 0
        if p.vi() is None:
            raise SystemExit("the board does not answer 38H (firmware too old?): nothing to measure")
        home = p.enc()
        hi, lo = home + throw_counts(2.0), home + throw_counts(-2.0)
        rest = [x for x in (p.vi() for _ in range(20)) if x]
        i_rest = st.median(i for _, i in rest)
        volts = st.median(v for v, _ in rest)
        print("at rest: %.0f mA, supply %.1f V; travel %+d..%+d counts from home"
              % (i_rest, volts, hi - home, lo - home), flush=True)
        logf = open(o.log, "a")
        for rpm in [int(x) for x in o.rpms.split(",")]:
            up, dn = [], []
            for _ in range(o.reps):
                for tgt, bucket in ((hi, up), (home, dn), (lo, dn), (home, up)):
                    s = p.move_logged(tgt, rpm, o.acc)
                    bucket += steady(s, rpm)
                    logf.write(json.dumps(dict(when=time.strftime("%Y-%m-%d %H:%M:%S"), rpm=rpm,
                                               acc=o.acc, target=tgt - home, samples=s)) + "\n")
                    time.sleep(0.2)
            mu = st.median(up) if up else float("nan")
            md = st.median(dn) if dn else float("nan")
            print("  %4d rpm: raising %.0f mA (n %d), lowering %.0f mA (n %d) -> load ~%.0f mA, "
                  "friction ~%.0f mA over rest" % (rpm, mu, len(up), md, len(dn), (mu - md) / 2,
                                                    (mu + md) / 2 - i_rest), flush=True)
        logf.close()
    finally:
        try:
            if home is not None:
                p.m.move_abs(int(home), 100, 240)
                time.sleep(1.5)
        except Exception as e:
            print("HOME FAILED: %r" % e)
        if was is not None:
            try:
                link.ask("P %d" % (1 if was else 0))
            except Exception:
                pass
        link.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
