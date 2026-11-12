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
SMOOTH SLOW PRESSES (user, 2026-11-11: the grind is the motor vibrating on SLOW, delicate pedal
work; a slammed pedal may be noisy). The pedal arrives in 128 steps (~30 counts each), and each
step sent as its own full-speed move with no ramp made a slow press a train of sprint-and-stop
jolts. Now, on a steady TICK:
  * a big change (SLAM_STEPS pedal steps at once: a slammed pedal) goes at full RPM;
  * otherwise the motor is aimed at where the pedal IS (ahead of it while the foot moves) at the
    pedal's own recent SPEED (smoothed over TAU) plus a catch-up of the lag over T_CATCH: it never
    gets there early and stops, so a press is one continuous move. (2026-11-11 v1 aimed at a
    smoothed point each tick at 1.5x the speed to reach it: the motor arrived early and stopped
    every tick, notchy at ordinary speeds.)
--rpm-fixed sends every target at RPM as before (to compare).
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
TICK = 0.01                      # s: targets go out on this tick, ~100 a second
DEADBAND = 2                     # counts: smaller changes are not sent
TAU = 0.08                       # s: the pedal's speed is smoothed over about this
T_CATCH = 0.06                   # s: the lag behind the pedal is made up over about this
SLAM_STEPS = 6                   # pedal steps (of 127) at once: a slam, full speed
RPM_MIN = 1                      # the driver takes 1 rpm: a slow foot is never outrun
RPM_RESEND = 0.15                # a new speed goes out when it differs by this fraction


def throw_counts(semitones: float) -> int:
    return int(round(DL_OPEN * (2.0 ** (semitones / 6.0) - 1.0) / LEAD * T))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--port", type=int, default=5005)
    a.add_argument("--semitones", type=float, default=1.0, help="fully up raises this, fully down lowers it")
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--raise-sign", type=int, choices=(1, -1), default=RAISE_SIGN)
    a.add_argument("--rpm-fixed", action="store_true", help="every target at RPM, unsmoothed (the old way)")
    a.add_argument("--acc", type=int, default=0, help="the motor's ramp, 0 (none) .. 255")
    a.add_argument("--tau", type=float, default=TAU, help="s: the pedal's speed smoothed over this")
    a.add_argument("--catch", type=float, default=T_CATCH, help="s: the lag made up over this")
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
    sock.setblocking(False)
    per_rpm = T / 60.0                               # counts a second at 1 rpm
    last_rx, sent, sent_rpm, n, last_seq = 0.0, home, 0, 0, -1
    v_raw = None
    est = float(home)                                # where the motor should be by now
    rate = 0.0                                       # the pedal's speed, counts a second, smoothed
    prev_tgt = None
    t_prev = time.monotonic()
    try:
        while True:
            time.sleep(max(0.0, TICK - (time.monotonic() - t_prev)))
            now = time.monotonic()
            dt, t_prev = max(1e-3, now - t_prev), now
            while True:                              # everything that arrived since the last tick
                try:
                    data, peer = sock.recvfrom(64)
                except (BlockingIOError, socket.timeout):
                    break
                try:
                    seq, v = data.decode().split()
                    seq, v = int(seq), min(1.0, max(0.0, float(v)))
                except ValueError:
                    continue
                if seq <= last_seq and last_seq - seq < 1000:      # late or repeated datagram
                    continue
                last_seq, last_rx, v_raw = seq, now, v
            if v_raw is None:
                continue
            if last_rx and now - last_rx > HOLD_S:
                print("nothing heard for %.1f s: holding at %+d" % (HOLD_S, sent - home), flush=True)
                last_rx, v_raw, prev_tgt = 0.0, None, None
                continue
            tgt = min(hi, max(lo, home + o.raise_sign * throw_counts(o.semitones * (1.0 - 2.0 * v_raw))))
            step = 0 if prev_tgt is None else tgt - prev_tgt
            prev_tgt = tgt
            rate += (step / dt - rate) * min(1.0, dt / o.tau)
            # where the motor got to since the last tick, at the speed it was sent
            go = sent - est
            est += max(-abs(go), min(abs(go), (1 if go > 0 else -1) * sent_rpm * per_rpm * dt))
            lag = tgt - est
            if abs(lag) < DEADBAND and tgt == sent:
                continue
            if o.rpm_fixed or abs(step) >= SLAM_STEPS * up / 63.5 / 2:
                rpm = RPM                            # the old way, or a slam
            else:
                rpm = int(min(RPM, max(RPM_MIN, (abs(rate) + abs(lag) / o.catch) / per_rpm)))
            if tgt == sent and sent_rpm and abs(rpm - sent_rpm) <= RPM_RESEND * sent_rpm:
                continue
            m.move_abs(tgt, rpm, o.acc)
            sent, sent_rpm, n = tgt, rpm, n + 1
            if n % 50 == 1:
                print("pedal %.2f -> %+d counts at %d rpm" % (v_raw, tgt - home, rpm), flush=True)
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
