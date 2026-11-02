"""First words with a motor, through motor_ctrl.

    python3 -m psgbench.motorcheck                 read the motor, moves nothing
    python3 -m psgbench.motorcheck --move          then SR_vFOC, enable, a quarter turn and back

Prints each raw line from the board, so a frame nobody acknowledged (D ... 0) shows as itself.
"""
from __future__ import annotations

import argparse
import time

import serial

from . import servo
from .link import find_motor_port


class Raw:
    def __init__(self, can_id):
        self.s = serial.Serial(find_motor_port(), 115200, timeout=0.1)
        self.id, self.seq = can_id, 0

    def ask(self, name, body, wait=0.4):
        """Send one command; every reply from the motor, as (code, value)."""
        self.seq += 1
        data = servo.pack(self.id, body)
        print("%-10s -> %s" % (name, data.hex()))
        self.s.reset_input_buffer()
        self.s.write(b"S 0 %X %s\n" % (self.id, data.hex().encode()))
        got, end, buf = [], time.time() + wait, b""
        while time.time() < end:
            buf += self.s.read(256)
            *lines, buf = buf.split(b"\n")
            for raw in lines:
                print("    ", raw.decode("ascii", "replace"))
                p = raw.split()
                if p[:1] == [b"R"] and len(p) > 4:
                    got.append(servo.parse(self.id, bytes.fromhex(p[4].decode())))
        return got


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--id", type=int, default=1)
    a.add_argument("--move", action="store_true")
    a.add_argument("--counts", type=int, default=servo.COUNTS_PER_TURN // 4)
    a.add_argument("--rpm", type=int, default=60)
    a.add_argument("--acc", type=int, default=100)
    o = a.parse_args()
    r = Raw(o.id)
    r.s.write(b"?\n")
    print(r.s.read(80))

    enc = r.ask("position", bytes([servo.READ_ENCODER]))
    r.ask("speed", bytes([servo.READ_SPEED]))
    r.ask("angle err", bytes([servo.READ_ERROR]))
    if not enc:
        print("no answer from motor %d: no move sent" % o.id)
        return 1
    print("motor %d answers, position %s" % (o.id, enc[0]))
    if not o.move:
        return 0

    r.ask("mode", bytes([servo.SET_MODE, servo.SR_VFOC]))
    r.ask("enable", bytes([servo.ENABLE, 1]))
    wait = 1.0 + 2.0 * abs(o.counts) / servo.COUNTS_PER_TURN * 60.0 / o.rpm
    r.ask("forward", servo.move(servo.MOVE_REL, o.counts, o.rpm, o.acc), wait)
    print("now", r.ask("position", bytes([servo.READ_ENCODER])))
    r.ask("back", servo.move(servo.MOVE_REL, -o.counts, o.rpm, o.acc), wait)
    print("now", r.ask("position", bytes([servo.READ_ENCODER])))
    r.ask("disable", bytes([servo.ENABLE, 0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
