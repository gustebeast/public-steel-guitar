"""Drive string 1's motor from an expression pedal streamed over the network (user, 2026-11-11).

    python3 -m publicbench.pedaldrive                  middle = where the motor is now (neutral),
                                                       fully up +1 st, fully down -1 st
    python3 -m publicbench.pedaldrive --semitones 2    a whole step each way

The pedal is read on another computer (bench/pedal_send.py, on the Mac the pedal is plugged
into) and arrives here as UDP datagrams "<seq> <value 0..1>" on --port. THE PEDAL'S MIDDLE IS
NEUTRAL (user, 2026-11-11): value 0 (fully up) raises --semitones, 1 (fully down) lowers it as far,
and the motor's target is start + that pitch's counts, sent as an absolute move (F5 takes a new target while
the last one is still running, so the motor follows the foot). SAFE BY CONSTRUCTION:
  * the target is CLAMPED to the counts of -semitones .. +semitones: the nut never leaves them;
  * nothing heard for HOLD_S: no new targets, the motor holds where it is;
  * the speed is capped at RPM (the fastest the spring test ran);
  * Ctrl-C: back to start, play as it was.
Stop the phone service first (it shares the serial port): sudo systemctl stop public-steel-guitar-phone
"""
from __future__ import annotations

import argparse
import socket
import time

from . import servo
from .link import MotorCtrlLink
from .springload import RAISE_SIGN

T = servo.COUNTS_PER_TURN
LEAD = 2.0                       # mm per turn, Tr8x2
DL_OPEN = 2.0                    # mm: string 1's model on this bench (phone/pitchctl.py)
RPM = 1200
HOLD_S = 0.5
MIN_DT = 0.004                   # s between targets: ~250 a second at most
DEADBAND = 4                     # counts: smaller changes are not sent


def throw_counts(semitones: float) -> int:
    return int(round(DL_OPEN * (2.0 ** (semitones / 6.0) - 1.0) / LEAD * T))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--port", type=int, default=5005)
    a.add_argument("--semitones", type=float, default=1.0, help="fully up raises this, fully down lowers it")
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--raise-sign", type=int, choices=(1, -1), default=RAISE_SIGN)
    o = a.parse_args()
    up, dn = throw_counts(o.semitones), throw_counts(-o.semitones)     # dn < 0
    assert 0 < up <= T // 2, "a throw over half a turn: give a smaller --semitones"

    link = MotorCtrlLink()
    m = servo.Servo(link, o.id)
    was = None
    try:
        r = link.ask("P")
        was = len(r) > 2 and r[0] == "P" and r[2] == "1"
        link.ask("P 0")
    except Exception as e:
        print("play state not read (%s); going on" % e)
    m.enable(True)
    time.sleep(0.3)
    home = m.position()
    lo, hi = sorted((home + o.raise_sign * up, home + o.raise_sign * dn))
    print("start %d = middle; up %+d, down %+d counts (+-%.2f st); listening on udp %d"
          % (home, o.raise_sign * up, o.raise_sign * dn, o.semitones, o.port), flush=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", o.port))
    sock.settimeout(0.05)
    last_rx, last_tx, sent, n, last_seq = 0.0, 0.0, home, 0, -1
    try:
        while True:
            try:
                data, peer = sock.recvfrom(64)
            except socket.timeout:
                if last_rx and time.monotonic() - last_rx > HOLD_S:
                    print("nothing heard for %.1f s: holding at %+d" % (HOLD_S, sent - home), flush=True)
                    last_rx = 0.0
                continue
            try:
                seq, v = data.decode().split()
                seq, v = int(seq), min(1.0, max(0.0, float(v)))
            except ValueError:
                continue
            if seq <= last_seq and last_seq - seq < 1000:      # late or repeated datagram
                continue
            last_seq, last_rx = seq, time.monotonic()
            tgt = min(hi, max(lo, home + o.raise_sign * throw_counts(o.semitones * (1.0 - 2.0 * v))))
            now = time.monotonic()
            if abs(tgt - sent) < DEADBAND or now - last_tx < MIN_DT:
                continue
            m.move_abs(tgt, RPM, 0)
            sent, last_tx, n = tgt, now, n + 1
            if n % 50 == 1:
                print("pedal %.2f -> %+d counts" % (v, tgt - home), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        m.move_abs(home, 300, 0)
        time.sleep(0.5)
        print("back at start: %+d counts" % (m.position() - home), flush=True)
        if was:
            try:
                link.ask("P 1")
            except Exception:
                pass
        link.close()


if __name__ == "__main__":
    main()
