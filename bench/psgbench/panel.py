"""The output panel (firmware/output_panel): its controls, and samples to its jack.

    python3 -m psgbench.panel tone --hz 440 --seconds 3
    python3 -m psgbench.panel listen --string 3 --optical /dev/ttyACM2,/dev/ttyACM3 --gain 0.5
    python3 -m psgbench.panel status

The jack hears the DAC only with the relay energised, so both commands throw it on the way
in and let it go on the way out. The lock-in here is the running form of optical.demod(),
which needs the whole take: the carrier's phase is set from the first block, then each block
goes straight out. The panel's clock sets the pace, because a write to it waits for room.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import time

import numpy as np

from . import optical


def find_port() -> str:
    for tty in glob.glob("/sys/class/tty/ttyACM*"):
        d = os.path.realpath(tty + "/device/..")
        try:
            ids = [open(os.path.join(d, f)).read().strip() for f in ("idVendor", "idProduct")]
        except OSError:
            continue
        if ids == ["1a86", "fe0c"]:
            return "/dev/" + os.path.basename(tty)
    raise RuntimeError("no output panel on USB (1a86:fe0c)")


class Panel:
    def __init__(self, port=None):
        import serial
        self.s = serial.Serial(port or find_port(), 115200, timeout=0.5)
        self.s.reset_input_buffer()
        r = self.ask("?")
        m = re.search(r"fs=(\d+)", r)
        if not m:
            raise RuntimeError("not the bench firmware: %r" % r)
        self.fs = int(m.group(1))

    def ask(self, line: str) -> str:
        self.s.write((line + "\n").encode())
        return self.s.readline().decode("ascii", "replace").strip()

    def relay(self, on: bool):
        return self.ask("R %d" % on)

    def level(self, tip: int, ring: int | None = None):
        return self.ask("P %d %d" % (tip, tip if ring is None else ring))

    def jack(self, stereo: bool):
        return self.ask("J %d" % stereo)

    def status(self) -> dict:
        v = self.ask("S").split()
        k = ("played", "queued", "short", "peak_l", "peak_r", "t_us")
        return dict(zip(k, map(int, v[1:])))

    def play(self, x: np.ndarray):
        """Float samples, +-1, mono or (n, 2). Returns when the last has been written."""
        x = np.asarray(x)
        if x.ndim == 1:
            x = np.stack((x, x), axis=1)
        b = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
        self.s.write(b"A %d\n" % len(b) + b)

    def close(self):
        self.s.close()


class Fit:
    """Linear interpolation from one fixed rate to another, block by block."""

    def __init__(self, fs_in: float, fs_out: float):
        self.step, self.at, self.last = fs_in / fs_out, 0.0, 0.0

    def __call__(self, x: np.ndarray) -> np.ndarray:
        x = np.concatenate(([self.last], x))
        i = np.arange(self.at, len(x) - 1, self.step)
        self.at = (i[-1] + self.step if len(i) else self.at) - (len(x) - 1)
        self.last = x[-1]
        return np.interp(i, np.arange(len(x)), x)


class Lockin:
    """optical.demod() a block at a time, for one input, to 48 kHz."""

    def __init__(self):
        from scipy.signal import butter
        self.hp = butter(4, 8000.0, btype="high", fs=optical.FS, output="sos")
        self.zi = np.zeros((self.hp.shape[0], 2))
        self.phase = None

    def __call__(self, x: np.ndarray) -> np.ndarray:
        from scipy.signal import sosfilt
        q, self.zi = sosfilt(self.hp, np.asarray(x, dtype=float), zi=self.zi)
        q = q.reshape(-1, 4)
        z = (q[:, 0] - q[:, 2]) + 1j * (q[:, 1] - q[:, 3])
        if self.phase is None:
            self.phase = np.angle(np.mean(z))
        return (z * np.exp(-1j * self.phase)).real / 2.0


def tone(a):
    p = Panel()
    print("panel:", p.ask("?"))
    p.jack(True)
    p.level(a.level)
    p.relay(True)
    t = np.arange(int(p.fs * a.seconds)) / p.fs
    x = a.amp * np.sin(2 * np.pi * a.hz * t)
    s0 = p.status()
    for at in range(0, len(x), 960):
        p.play(x[at:at + 960])
    s1 = p.status()
    time.sleep(0.05)
    p.relay(False)
    print("frames %d in %.3f s, short %d, adc peak %d %d" % (
        s1["played"] - s0["played"], (s1["t_us"] - s0["t_us"]) / 1e6,
        s1["short"] - s0["short"], s1["peak_l"], s1["peak_r"]))
    p.close()


def listen(a):
    from scipy.signal import butter, sosfilt
    p = Panel()
    ctl, dat = a.optical.split(",")
    o = optical.OpticalLink(ctl, dat)
    conv, sa, sb = optical.string_inputs(a.string)
    print("panel:", p.ask("?"), "| optical:", o.command("?"))
    o.select([conv])
    A, B = Lockin(), Lockin()
    fit = Fit(48000.0, p.fs)
    dc = butter(2, 20.0, btype="high", fs=48000.0, output="sos")
    zi = np.zeros((dc.shape[0], 2))
    p.jack(True)
    p.level(a.level)
    p.relay(True)
    print("string %d on the jack; ctrl-C stops" % a.string)
    # a block's worth of the carrier's own level sets full scale; --gain goes from there
    scale = None
    try:
        while True:
            blocks = o.take()
            if not blocks:
                time.sleep(0.001)
                continue
            x = np.concatenate([b[2][conv] for b in blocks])
            raw = A(x[:, sa]) + B(x[:, sb])
            if scale is None:
                scale = 1.0 / max(float(np.max(np.abs(raw))), 1.0)
            y, zi = sosfilt(dc, raw, zi=zi)
            p.play(fit(y * scale * a.gain))
    except KeyboardInterrupt:
        pass
    p.relay(False)
    o.select([])
    o.close()
    p.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("tone")
    c.add_argument("--hz", type=float, default=440.0)
    c.add_argument("--seconds", type=float, default=2.0)
    c.add_argument("--amp", type=float, default=0.25)
    c.add_argument("--level", type=int, default=128)
    c = sub.add_parser("listen")
    c.add_argument("--string", type=int, required=True)
    c.add_argument("--optical", required=True, help="<control port>,<sample port>")
    c.add_argument("--gain", type=float, default=1.0)
    c.add_argument("--level", type=int, default=128)
    sub.add_parser("status")
    a = ap.parse_args()
    if a.cmd == "tone":
        tone(a)
    elif a.cmd == "listen":
        listen(a)
    else:
        p = Panel()
        print(p.ask("?"))
        print(p.status())
        p.close()


if __name__ == "__main__":
    main()
