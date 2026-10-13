"""The optical stream's parser and lock-in, on made-up samples (no hardware)."""
import numpy as np
import pytest

from psgbench import optical, pitch


def carrier_samples(seconds=0.5, f0=220.0, depth=0.02, phase_shift=1, seed=3):
    """One photodiode as the converter would see it: a 48 kHz on/off carrier whose size a
    string at f0 changes by `depth`, on top of lamp flicker at 120 Hz three times the
    carrier's size, plus noise."""
    n = int(seconds * optical.FS)
    t = np.arange(n) / optical.FS
    on = ((np.arange(n) + phase_shift) % 4 < 2).astype(float)
    light = 4000.0 * (1.0 + depth * np.sin(2 * np.pi * f0 * t))
    lamp = 12000.0 * np.sin(2 * np.pi * 120.0 * t)
    x = light * on + lamp + 20.0 * np.random.default_rng(seed).standard_normal(n)
    return np.clip(np.round(x), -32768, 32767).astype("<i2")


def blocks_of(samples_by_conv, frames=960, first=5 * 960):
    """The byte stream the firmware would send for these converters' (n, 4) arrays."""
    mask = sum(1 << k for k in samples_by_conv)
    n = min(len(a) for a in samples_by_conv.values()) // frames
    out = b""
    for b in range(n):
        out += optical.HEADER.pack(optical.MAGIC, mask, 0, frames, first + b * frames)
        for k in sorted(samples_by_conv):
            out += samples_by_conv[k][b * frames:(b + 1) * frames].astype("<i2").tobytes()
    return out


def test_stream_round_trip_survives_being_cut_anywhere():
    x = np.arange(960 * 3 * 4, dtype="<i2").reshape(-1, 4)
    data = b"junk" + blocks_of({1: x, 3: -x})
    got, rest = [], b""
    for i in range(0, len(data), 1000):                 # as a serial port hands it over
        new, rest = optical.parse(rest + data[i:i + 1000])
        got += new
    assert [b[0] for b in got] == [4800, 5760, 6720]
    first, y = optical.join(got, 3)
    assert first == 4800 and np.array_equal(y, -x)
    with pytest.raises(ValueError):
        optical.join([got[0], got[2]], 1)


def test_lock_in_keeps_the_string_and_drops_the_lamp():
    for shift in range(4):                              # whatever the carrier's phase is
        y = optical.demod(carrier_samples(phase_shift=shift))
        y = y - np.mean(y)
        f, _ = pitch.track(y, 48000.0, 220.0)
        mid = f[2400:-2400]
        assert abs(np.median(mid) - 220.0) < 0.2
        # 120 Hz, three times the carrier before the lock-in, is next to nothing after it
        spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        hz = np.fft.rfftfreq(len(y), 1 / 48000.0)
        assert spec[np.argmin(abs(hz - 120.0))] < 0.05 * spec[np.argmin(abs(hz - 220.0))]
