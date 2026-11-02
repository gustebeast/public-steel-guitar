"""The output panel (firmware/output_panel): its controls, and samples to its jack.

    python3 -m psgbench.panel tone --hz 440 --seconds 3
    python3 -m psgbench.panel listen --string 3 --duty 32 --seconds 30
    python3 -m psgbench.panel noise --duty 32
    python3 -m psgbench.panel status

The jack hears the DAC only with the relay energised, so both commands throw it on the way
in and let it go on the way out. The lock-in here is the running form of optical.demod(),
which needs the whole take: the carrier's phase follows a slow average of the carrier, so it
finds itself again when something first comes over the sensors. Gain is fixed, in DAC full
scale per converter full scale: scaling to the signal would turn silence into full-level
noise. The panel's clock sets the pace and the optical board's sets the supply, so the
resampling is trimmed to hold what is on its way to the DAC at QUEUE frames. `S` is answered
only after everything sent before it, so its round trip measures the Pi's USB buffers, and
its queue figure the panel's ring.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import time

import numpy as np

from . import optical


QUEUE = 480                             # frames, about 10 ms: the panel's share of the latency


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
    """Linear interpolation from one rate to another, block by block. `trim` is a small
    fractional change of rate, for holding a queue."""

    def __init__(self, fs_in: float, fs_out: float):
        self.step, self.at, self.last = fs_in / fs_out, 0.0, 0.0
        self.nominal = self.step

    def trim(self, fraction: float):
        self.step = self.nominal * (1.0 + fraction)

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
        self.carrier = 0j

    def __call__(self, x: np.ndarray) -> np.ndarray:
        from scipy.signal import sosfilt
        q, self.zi = sosfilt(self.hp, np.asarray(x, dtype=float), zi=self.zi)
        q = q.reshape(-1, 4)
        z = (q[:, 0] - q[:, 2]) + 1j * (q[:, 1] - q[:, 3])
        self.carrier += (np.mean(z) - self.carrier) * min(1.0, len(z) / 48000.0)
        return (z * np.exp(-1j * np.angle(self.carrier))).real / 2.0


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
    o = optical.OpticalLink()
    conv, sa, sb = optical.string_inputs(a.string)
    print("panel:", p.ask("?"), "| optical:", o.command("?"))
    o.duty(a.duty)
    o.select(range(5) if a.common else [conv])
    A, B = Lockin(), Lockin()
    common = optical.CommonNoise(a.string)
    ia, ib = 2 * a.string - 2, 2 * a.string - 1

    def pair(blocks):
        """This string's two inputs, less the common noise if that is in use."""
        if not a.common:
            x = np.concatenate([b[2][conv] for b in blocks])
            return x[:, sa], x[:, sb]
        m = common(np.concatenate([optical.inputs(b[2]) for b in blocks]))
        return m[:, ia], m[:, ib]

    fit = Fit(48000.0, p.fs)
    dc = butter(2, 20.0, btype="high", fs=48000.0, output="sos")
    zi = np.zeros((dc.shape[0], 2))
    p.jack(True)
    p.level(a.level)
    p.relay(True)
    print("string %d on the jack; ctrl-C stops" % a.string)
    # Everything the set-up above took is backlog, and at the trim's pace it would stay for
    # minutes as latency: run the lock-in on it, throw it away, then start at the right depth.
    settle = time.monotonic() + 0.3
    while time.monotonic() < settle:
        blocks = o.take()
        if blocks:
            xa, xb = pair(blocks)
            A(xa), B(xb)
        time.sleep(0.001)
    s0 = p.status()
    p.play(np.zeros(QUEUE))
    o.take()
    t0 = next_check = time.monotonic()
    depth, drops, most = [], 0, 0
    try:
        while not a.seconds or time.monotonic() - t0 < a.seconds:
            blocks = o.take()
            if not blocks:
                time.sleep(0.0005)
                continue
            drops += sum(b[1] & 1 for b in blocks)
            most = max(most, len(blocks))
            xa, xb = pair(blocks)
            y, zi = sosfilt(dc, A(xa) + B(xb), zi=zi)
            p.play(fit(y / 32768.0 * a.gain))
            if time.monotonic() >= next_check:
                next_check = time.monotonic() + 0.25
                t = time.monotonic()
                q = p.status()["queued"]
                ahead = (time.monotonic() - t) * p.fs + q
                depth.append(ahead)
                fit.trim(np.clip((ahead - QUEUE) / p.fs * 0.5, -0.002, 0.002))
    except KeyboardInterrupt:
        pass
    s1 = p.status()
    p.relay(False)
    print("frames %d, short %d, optical blocks dropped %d, most blocks at once %d" % (
        s1["played"] - s0["played"], s1["short"] - s0["short"], drops, most))
    if depth:
        settled = depth[len(depth) // 2:]
        print("on the way to the DAC: first %d, last half min %d mean %.0f max %d frames "
              "(%.1f ms mean)" % (depth[0], min(settled), np.mean(settled), max(settled),
                                  1e3 * np.mean(settled) / p.fs))
    o.select([])
    o.close()
    p.close()


def noise(a):
    """Each string's carrier and noise, audio band: one photodiode against the pair. Units are
    converter counts; `pair` is the gain of SUM / 2 over one alone. A carrier of a few counts
    means the amplifier is saturated, not that it is quiet."""
    from scipy.signal import butter, sosfiltfilt
    band = butter(4, (40.0, 15000.0), btype="band", fs=48000.0, output="sos")
    o = optical.OpticalLink()
    print("optical:", o.command("?"))
    o.duty(a.duty)
    for on in (False, True):
        o.emitters(on)
        o.select(range(5))
        time.sleep(0.2)
        o.take()
        time.sleep(a.seconds)
        blocks = o.take()
        o.select([])
        print("emitters %s, %d blocks, %d dropped" % (
            "gated" if on else "off", len(blocks), sum(b[1] & 1 for b in blocks)))
        print("string carrier A,B      A      B    SUM   DIFF   pair  corr | less common: A  SUM/2")
        clean = [optical.CommonNoise(s) for s in range(1, 11)]
        m = np.concatenate([optical.inputs(b[2]) for b in blocks])
        for s in range(1, 11):
            conv, sa, sb = optical.string_inputs(s)
            _, x = optical.join(blocks, conv)
            f = [sosfiltfilt(band, optical.demod(x[:, n]))[2000:-2000] for n in (sa, sb)]
            r = [np.std(v) for v in (f[0], f[1], f[0] + f[1], f[0] - f[1])]
            pair = 20 * np.log10(0.5 * (r[0] + r[1]) / (r[2] / 2))
            c = clean[s - 1](m)
            g = [sosfiltfilt(band, optical.demod(c[:, n]))[2000:-2000]
                 for n in (2 * s - 2, 2 * s - 1)]
            q = m[:len(m) // 4 * 4].reshape(-1, 4, 20).mean(axis=0)
            amp = np.abs((q[0] - q[2]) + 1j * (q[1] - q[3])) / 2
            print("%6d %7.0f %6.0f %6.2f %6.2f %6.2f %6.2f %5.1fdB %5.2f | %13.2f %6.2f" % (
                s, amp[2 * s - 2], amp[2 * s - 1], *r, pair, np.corrcoef(f[0], f[1])[0, 1],
                g[0].std(), ((g[0] + g[1]) / 2).std()))
    o.emitters(True)
    o.duty(2048)
    o.close()


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
    c.add_argument("--gain", type=float, default=1.0, help="DAC per converter full scale")
    c.add_argument("--level", type=int, default=128)
    c.add_argument("--seconds", type=float, default=0.0, help="0: until ctrl-C")
    c.add_argument("--common", action="store_true",
                   help="all five converters, noise common to them taken out")
    c.add_argument("--duty", type=int, default=32, help="emitters' on-time, of 4096")
    c = sub.add_parser("noise")
    c.add_argument("--seconds", type=float, default=2.0)
    c.add_argument("--duty", type=int, default=32, help="emitters' on-time, of 4096")
    sub.add_parser("status")
    a = ap.parse_args()
    if a.cmd == "tone":
        tone(a)
    elif a.cmd == "listen":
        listen(a)
    elif a.cmd == "noise":
        noise(a)
    else:
        p = Panel()
        print(p.ask("?"))
        print(p.status())
        p.close()


if __name__ == "__main__":
    main()
