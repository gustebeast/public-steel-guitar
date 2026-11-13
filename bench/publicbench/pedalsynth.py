"""A synthetic pedal press for publicbench.pedaldrive, the pedal taken out of the loop (2026-11-11).

    python3 -m publicbench.pedalsynth                     500 values a second (our own pedal's rate)
    python3 -m publicbench.pedalsynth --rate 33           the Lehle's rate (it sent every ~20-30 ms)
    python3 -m publicbench.pedalsynth --down 0.1 --up 0.09 --hold 0.5 --presses 3

A logged ordinary press (user, 2026-11-11) went from resting (1.0) to fully over (0.0) in ~0.1 s,
held ~0.5 s and came back in ~0.09 s. This plays that shape as a smooth cosine, at --rate values a
second, to the drive's UDP port, the same "<seq> <value>" datagrams pedal_send.py sends. Stop the
real pedal's sender first, or the two fight.
"""
from __future__ import annotations

import argparse
import math
import socket
import time


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=5005)
    a.add_argument("--rate", type=float, default=500.0, help="values a second")
    a.add_argument("--rest", type=float, default=1.0, help="the pedal's resting value")
    a.add_argument("--over", type=float, default=0.0, help="the value fully pressed")
    a.add_argument("--down", type=float, default=0.1, help="s, rest -> over")
    a.add_argument("--hold", type=float, default=0.5)
    a.add_argument("--up", type=float, default=0.09, help="s, over -> rest")
    a.add_argument("--presses", type=int, default=3)
    a.add_argument("--gap", type=float, default=1.5, help="s at rest between presses")
    o = a.parse_args()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0

    def play(seconds, value_at):
        nonlocal seq
        t0 = time.monotonic()
        k = 0
        while True:
            t = k / o.rate
            if t > seconds:
                break
            while time.monotonic() - t0 < t:
                time.sleep(0.0005)
            seq += 1
            s.sendto(b"%d %.4f" % (seq, value_at(t)), (o.host, o.port))
            k += 1

    def ramp(v0, v1, d):
        return lambda t: v0 + (v1 - v0) * (1 - math.cos(math.pi * min(1.0, t / d))) / 2

    play(o.gap, lambda t: o.rest)
    for i in range(o.presses):
        play(o.down, ramp(o.rest, o.over, o.down))
        play(o.hold, lambda t: o.over)
        play(o.up, ramp(o.over, o.rest, o.up))
        play(o.gap, lambda t: o.rest)
        print("press %d done" % (i + 1), flush=True)


if __name__ == "__main__":
    main()
