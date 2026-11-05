"""What was commanded on bus A and what the motors said back, as motor_ctrl reports it.

    python3 -m publicbench.trace                      # until Ctrl-C
    python3 -m publicbench.trace --monitor 1000 --seconds 30

Needs motor_ctrl firmware version 2 (its W lines: every frame it sent, from the host, from play
or from its monitor) and the port to itself: stop public-steel-guitar-phone first. --monitor
sets the board's monitor gap (main.c, MONITOR): every motor moved in the last half second is
asked its encoder and angle error in turn. Each line is one frame, on the board's clock:

       12.345678  s3  >  p move abs -7089 at 125 rpm acc 0     (p play, h host, m monitor)
       12.345901  s3  <  started
       12.351000  s3  >  m ask encoder
       12.351210  s3  <  encoder -7612 (-523 from the last target)
       12.352400  s3  <  error -14.1 deg

At the end, per string: the last target, the last encoder reading, and how far apart.
"""
from __future__ import annotations

import argparse
import time

from . import servo
from .link import MotorCtrlLink

STATUS = {0: "refused", 1: "started", 2: "arrived", 3: "stopped by a limit"}


def _i24(b: bytes) -> int:
    v = int.from_bytes(b, "big")
    return v - (1 << 24) if v & 0x800000 else v


def sent(f, src, last):
    d = f.data
    if not d:
        return "%s ?" % src
    if d[0] in (servo.MOVE_ABS, servo.MOVE_REL) and len(d) >= 8:
        rpm, acc, c = int.from_bytes(d[1:3], "big"), d[3], _i24(d[4:7])
        if d[0] == servo.MOVE_ABS:
            last[f.id] = c
        elif f.id in last:
            last[f.id] += c
        return "%s move %s %+d at %d rpm acc %d" % (src, "abs" if d[0] == servo.MOVE_ABS else "rel",
                                                   c, rpm, acc)
    names = {servo.READ_ENCODER: "ask encoder", servo.READ_ERROR: "ask error",
             servo.READ_SPEED: "ask speed", servo.ENABLE: "enable", servo.SET_RESPOND: "set replies"}
    return "%s %s %s" % (src, names.get(d[0], "0x%02X" % d[0]), d[1:-1].hex())


def heard(f, last, enc):
    p = servo.parse(f.id, f.data)
    if p is None:
        return "bad checksum %s" % f.data.hex()
    code, v = p
    if code in (servo.MOVE_ABS, servo.MOVE_REL):
        return STATUS.get(v, "move reply %r" % v)
    if code == servo.READ_ENCODER:
        enc[f.id] = v
        off = " (%+d from the last target)" % (v - last[f.id]) if f.id in last else ""
        return "encoder %d%s" % (v, off)
    if code == servo.READ_ERROR:
        return "error %+.1f deg" % (v * 360.0 / 51200)
    if code == servo.READ_SPEED:
        return "speed %d rpm" % v
    return "0x%02X %r" % (code, v)


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--monitor", type=int, default=None, help="board monitor gap, us (0 off)")
    a.add_argument("--seconds", type=float, default=None)
    a.add_argument("--port", default=None)
    o = a.parse_args()
    link = MotorCtrlLink(o.port)
    if o.monitor is not None:
        link.ask("M %d" % o.monitor)
    t0, nt, nr = time.monotonic(), 0, 0
    last, enc = {}, {}
    try:
        while o.seconds is None or time.monotonic() - t0 < o.seconds:
            time.sleep(0.05)
            with link._cv:
                tx, rx = link.tx[nt:], link.rx[nr:]
                nt, nr = len(link.tx), len(link.rx)
            out = [(f.t, f.id, ">", sent(f, src, last)) for f, src in tx if f.bus == 0]
            out += [(f.t, f.id, "<", heard(f, last, enc)) for f in rx if f.bus == 0]
            for t, mid, way, text in sorted(out):
                print("%11.6f  s%-2d %s  %s" % (t - t0, mid, way, text), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        if o.monitor:
            try:
                link.ask("M 0")
            except TimeoutError:
                pass
        if not link.tx:
            print("no W lines: is motor_ctrl running firmware version 2?")
        for mid in sorted(last):
            e = enc.get(mid)
            print("s%-2d last target %d, last encoder %s%s" % (
                mid, last[mid], e, "" if e is None else ", %+d counts" % (e - last[mid])))
        link.close()


if __name__ == "__main__":
    main()
