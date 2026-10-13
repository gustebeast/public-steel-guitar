"""The optical board's sample stream (firmware/optical), and the lock-in that turns it into
each photodiode's signal.

The board sends the converters' samples untouched: 192 kHz, four inputs per converter, the
emitters switched on and off at 48 kHz. What a photodiode sees of its string rides on that
48 kHz carrier; daylight and lamp flicker do not. demod() multiplies by the carrier and
averages, which keeps the one and throws away the other, and hands back 48 kHz samples.

TIMES. Samples are counted from when the board started its converters, and the board answers
`T` with the count now. OpticalLink.sync() lines that count up with this computer's clock the
way MotorCtrlLink does with the motor controller's, so `time_of(sample)` is on the same clock
as the motor commands.

WHICH INPUT IS WHICH STRING is the board's wiring (elec/optical.py, converter k = U14 + k, and
its SEC table for the four inputs); it is not decoded here. A test names the converter and the
two slots of the string it is looking at.
"""
from __future__ import annotations

import struct
import threading
import time

import numpy as np

FS = 192000
SLOTS = 4
MAGIC = b"PSGO"
HEADER = struct.Struct("<4sBBHQ")


def parse(data: bytes):
    """Split a byte stream into blocks: ([(first_sample, flags, {converter: int16 array of
    shape (frames, 4)})], the bytes left over). Skips to the next header after any damage."""
    out, i = [], 0
    while True:
        j = data.find(MAGIC, i)
        if j < 0:
            return out, data[max(i, len(data) - 3):]
        if len(data) - j < HEADER.size:
            return out, data[j:]
        _, mask, flags, frames, first = HEADER.unpack_from(data, j)
        lanes = [k for k in range(5) if mask >> k & 1]
        size = HEADER.size + len(lanes) * frames * SLOTS * 2
        if mask == 0 or mask > 31 or frames == 0:
            i = j + 1
            continue
        if len(data) - j < size:
            return out, data[j:]
        body = np.frombuffer(data, dtype="<i2", count=len(lanes) * frames * SLOTS, offset=j + HEADER.size)
        body = body.reshape(len(lanes), frames, SLOTS)
        out.append((first, flags, {k: body[n] for n, k in enumerate(lanes)}))
        i = j + size


def join(blocks, converter: int):
    """(first_sample, array (n, 4)) of one converter from consecutive blocks; raises if a
    block is missing in the middle."""
    blocks = [b for b in blocks if converter in b[2]]
    first = blocks[0][0]
    at = first
    for b in blocks:
        if b[0] != at:
            raise ValueError("samples %d..%d are missing" % (at, b[0]))
        at += len(b[2][converter])
    return first, np.concatenate([b[2][converter] for b in blocks])


def demod(x: np.ndarray):
    """Lock-in at a quarter of the sample rate. `x` is one input's samples (a multiple of
    four of them, starting anywhere); returns its signal at 48 kHz, in the same units, as the
    amplitude of the carrier. The carrier's phase against the samples is fixed while the
    board runs but not known beforehand, so it is found from the data."""
    from scipy.signal import butter, sosfiltfilt
    n = len(x) // 4 * 4
    # Everything the string does is within 20 kHz of the 48 kHz carrier. Take out what is
    # far below it first: a slow, large thing like lamp flicker still changes a little
    # within one carrier period, and that little would come through the subtraction below.
    sos = butter(4, 8000.0, btype="high", fs=FS, output="sos")
    q = sosfiltfilt(sos, np.asarray(x[:n], dtype=float)).reshape(-1, 4)
    z = (q[:, 0] - q[:, 2]) + 1j * (q[:, 1] - q[:, 3])
    # the carrier is far bigger than what the string does to it, so its angle is the mean's
    theta = np.angle(np.mean(z))
    return (z * np.exp(-1j * theta)).real / 2.0


class OpticalLink:
    """The board's two serial ports: `control` for commands, `stream` for samples."""

    def __init__(self, control="/dev/ttyACM1", stream="/dev/ttyACM2"):
        import serial
        self.ctl = serial.Serial(control, 115200, timeout=0.2)
        self.dat = serial.Serial(stream, 115200, timeout=0.05)
        self.blocks = []
        self.offset = None              # computer time of sample 0, seconds
        self._lock = threading.Lock()
        self._run = True
        threading.Thread(target=self._reader, daemon=True).start()
        self.sync()

    def command(self, line: str) -> str:
        self.ctl.reset_input_buffer()
        self.ctl.write((line + "\n").encode())
        return self.ctl.readline().decode("ascii", "replace").strip()

    def sync(self, n=40) -> float:
        """Line the sample count up with time.monotonic(); returns the best round trip."""
        best = None
        for _ in range(n):
            t0 = time.monotonic()
            r = self.command("T").split()
            t1 = time.monotonic()
            if len(r) == 2 and r[0] == "T" and (best is None or t1 - t0 < best[0]):
                best = (t1 - t0, (t0 + t1) / 2.0 - int(r[1]) / FS)
        if best is None:
            raise RuntimeError("the optical board does not answer")
        self.offset = best[1]
        return best[0]

    def time_of(self, sample: int) -> float:
        return self.offset + sample / FS

    def select(self, converters):
        """Start sending these converters (0..4); an empty list stops."""
        with self._lock:
            self.blocks = []
        return self.command("L %d" % sum(1 << k for k in converters))

    def emitters(self, on: bool):
        return self.command("E %d" % (1 if on else 0))

    def take(self):
        """Every block received since the last take() or select()."""
        with self._lock:
            b, self.blocks = self.blocks, []
        return b

    def _reader(self):
        rest = b""
        while self._run:
            got = self.dat.read(65536)
            if got:
                new, rest = parse(rest + got)
                if new:
                    with self._lock:
                        self.blocks.extend(new)

    def close(self):
        self._run = False
        self.ctl.close()
        self.dat.close()
