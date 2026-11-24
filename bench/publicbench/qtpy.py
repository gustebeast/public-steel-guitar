"""The Pi's side of the QT Py open-loop bench firmware (firmware/qtpy_bench): find the board by
its USB id, send one command line, get one reply line. The gate tests in bench/OPENLOOP_BENCH.md
are built on this.

    python3 -m publicbench.qtpy            prints `id`, `init`, `st` and `ms`: a wiring check
    python3 -m publicbench.qtpy "cur 1000 0" "en 1" "mv 1600 20000 1000000"
                                           any commands, in order (README.md lists them)
"""
from __future__ import annotations

import glob
import os
import sys
import time

USB_ID = ("cafe", "4009")
STEPS_PER_TURN_09 = 400          # full steps per turn of a 0.9 deg motor


class BenchError(RuntimeError):
    pass


def find_port() -> str:
    for tty in glob.glob("/sys/class/tty/ttyACM*"):
        d = os.path.realpath(tty + "/device/..")
        try:
            ids = tuple(open(os.path.join(d, f)).read().strip() for f in ("idVendor", "idProduct"))
        except OSError:
            continue
        if ids == USB_ID:
            return "/dev/" + os.path.basename(tty)
    raise BenchError("no QT Py bench board on USB (%s:%s)" % USB_ID)


def fields(reply: str) -> dict:
    """'ok pos=3 moving=0' -> {'pos': 3, 'moving': 0}; numbers become ints (hex too)."""
    out = {}
    for w in reply.split()[1:]:
        k, eq, v = w.partition("=")
        if eq:
            try:
                out[k] = int(v, 0)
            except ValueError:
                out[k] = v
    return out


class QtPyBench:
    def __init__(self, port: str | None = None, ser=None, timeout: float = 1.0):
        if ser is None:
            import serial
            ser = serial.Serial(port or find_port(), 115200, timeout=timeout)
        self.ser = ser
        self.ser.reset_input_buffer()

    def ask(self, line: str) -> str:
        self.ser.write((line + "\n").encode())
        r = self.ser.readline().decode(errors="replace").strip()
        if not r:
            raise BenchError("no reply to %r" % line)
        return r

    def do(self, line: str) -> dict:
        """ask(), raising unless the reply is ok; returns the reply's fields"""
        r = self.ask(line)
        if not r.startswith("ok"):
            raise BenchError("%s -> %s" % (line, r))
        return fields(r)

    # the commands, by name
    def init(self, usteps: int = 4) -> dict:
        return self.do("init %d" % usteps)

    def current(self, run_ma: int, hold_ma: int = 0, holddelay: int | None = None) -> dict:
        return self.do("cur %d %d%s" % (run_ma, hold_ma, "" if holddelay is None else " %d" % holddelay))

    def enable(self, on: bool) -> dict:
        return self.do("en %d" % bool(on))

    def move(self, steps: int, vmax: int, acc: int) -> int:
        return self.do("mv %d %d %d" % (steps, vmax, acc))["steps"]

    def goto(self, pos: int, vmax: int, acc: int) -> int:
        return self.do("go %d %d %d" % (pos, vmax, acc))["steps"]

    def status(self) -> dict:
        return self.do("st")

    def wait(self, timeout: float = 10.0, poll: float = 0.005) -> dict:
        t0 = time.monotonic()
        while True:
            s = self.status()
            if not s["moving"]:
                return s
            if time.monotonic() - t0 > timeout:
                self.do("halt")
                raise BenchError("move still running after %.1f s: halted" % timeout)
            time.sleep(poll)

    def mscnt(self) -> dict:
        return self.do("ms")

    def gstat(self) -> dict:
        return self.do("gstat")

    def drv(self) -> dict:
        return self.do("drv")

    def read(self, reg: int) -> int:
        r = self.ask("r 0x%02x" % reg)
        if not r.startswith("ok"):
            raise BenchError(r)
        return int(r.split("=")[1], 16)

    def write(self, reg: int, value: int) -> None:
        self.do("w 0x%02x 0x%08x" % (reg, value))


def mscnt_agrees(ms: dict, mscnt0: int, sign: int) -> bool:
    """Does the driver's MSCNT sit where the steps sent say it should? sign is +1 or -1, which
    way MSCNT runs for a positive step (learned once per wiring)."""
    return ms["mscnt"] == (mscnt0 + sign * ms["pos"] * ms["per"]) % 1024


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    b = QtPyBench()
    for line in argv or ["id", "init", "st", "ms"]:
        print("%-28s %s" % (line, b.ask(line)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
